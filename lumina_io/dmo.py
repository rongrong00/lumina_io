"""Dark-matter-only run loading (the LUMINA `DM_only_*` products)."""

import os
import glob
import numpy as np

from . import _backend, units as _units
import h5py
from h5py import h5s, h5t

_DEFAULT_ROOT = '/orcd/data/mvogelsb/005/Lumina'

# short run name -> run directory
RUNS = {
    '1500': os.path.join(_DEFAULT_ROOT, 'DM_only_1500'),
    '3000': os.path.join(_DEFAULT_ROOT, 'DM_only_3000'),
}

_countCache = {}      # (outdir, snap, base) -> (files, cumPartType[6+1] per type)
_catCountCache = {}   # (outdir, snap, kind) -> (files, cumRows)


# --------------------------------------------------------------------------
# path / run resolution
# --------------------------------------------------------------------------
def runPath(run):
    """Resolve a run spec to its run directory."""
    key = str(run)
    if key in RUNS:
        return RUNS[key]
    if key.startswith('DM_only_') and os.path.isdir(os.path.join(_DEFAULT_ROOT, key)):
        return os.path.join(_DEFAULT_ROOT, key)
    if os.path.isdir(run):
        # accept either the run dir or its output/ dir
        return os.path.dirname(run) if os.path.basename(run) == 'output' else run
    raise ValueError("Unknown DM-only run [%r]. Known short names: %s, or pass a "
                     "run/output directory path." % (run, sorted(RUNS)))


def outputDir(run):
    """The output directory of a run (contains snapdir_*/ and groups_*/)."""
    base = runPath(run)
    out = os.path.join(base, 'output')
    return out if os.path.isdir(out) else base


def _partIndex(path):
    parts = os.path.basename(path).split('.')
    return int(parts[-2]) if len(parts) >= 3 and parts[-2].isdigit() else 0


def _snapFiles(run, snapNum, base):
    out = outputDir(run)
    snapDir = os.path.join(out, 'snapdir_%03d' % snapNum)
    files = sorted(glob.glob(os.path.join(snapDir, '%s_%03d.*.hdf5' % (base, snapNum))),
                   key=_partIndex)
    if files:
        return files
    for cand in (os.path.join(snapDir, '%s_%03d.hdf5' % (base, snapNum)),
                 os.path.join(out, '%s_%03d.hdf5' % (base, snapNum))):
        if os.path.isfile(cand):
            return [cand]
    return []


def _groupFiles(run, snapNum):
    out = outputDir(run)
    groupDir = os.path.join(out, 'groups_%03d' % snapNum)
    files = sorted(glob.glob(os.path.join(groupDir,
                                          'fof_subhalo_tab_%03d.*.hdf5' % snapNum)),
                   key=_partIndex)
    if files:
        return files
    cand = os.path.join(groupDir, 'fof_subhalo_tab_%03d.hdf5' % snapNum)
    return [cand] if os.path.isfile(cand) else []


def listSnaps(run, base='snapshot'):
    """Output numbers that have a (full, by default) snapshot."""
    out = outputDir(run)
    snaps = []
    for dirPath in glob.glob(os.path.join(out, 'snapdir_[0-9]*')):
        num = int(os.path.basename(dirPath).rsplit('_', 1)[1])
        if _snapFiles(run, num, base):
            snaps.append(num)
    return sorted(snaps)


def listGroupSnaps(run):
    """Output numbers that have a Subfind group catalog."""
    out = outputDir(run)
    snaps = [int(os.path.basename(dirPath).rsplit('_', 1)[1])
             for dirPath in glob.glob(os.path.join(out, 'groups_[0-9]*'))]
    return sorted(snaps)


# --------------------------------------------------------------------------
# headers / particle types
# --------------------------------------------------------------------------
def _firstSnapFile(run, snapNum, base):
    files = _snapFiles(run, snapNum, base)
    if not files:
        raise ValueError("No '%s' snapshot for output %d in %s (have full snaps: %s)"
                         % (base, snapNum, outputDir(run), listSnaps(run, base)))
    return files


def loadHeader(run, snapNum, base='snapshot'):
    """Snapshot Header, plus HubbleParam/Omega* from the Parameters group."""
    firstFile = _firstSnapFile(run, snapNum, base)[0]
    header = _backend.read_attrs(firstFile, 'Header')
    params = _backend.read_attrs(firstFile, 'Parameters') or {}
    for name in ('HubbleParam', 'Omega0', 'OmegaLambda', 'OmegaBaryon',
                 'UnitLength_in_cm', 'UnitMass_in_g', 'UnitVelocity_in_cm_per_s'):
        if name in params and name not in header:
            header[name] = params[name]
    return header


def groupHeader(run, snapNum):
    """fof_subhalo_tab Header (Ngroups_Total, Nsubhalos_Total, NumFiles, ...)."""
    files = _groupFiles(run, snapNum)
    if not files:
        raise ValueError("No group catalog for output %d in %s" % (snapNum, outputDir(run)))
    return _backend.read_attrs(files[0], 'Header')


_PT_ALIASES = {'dm': 1, 'dark': 1, 'darkmatter': 1, 'gas': 0, 'stars': 4, 'bh': 5}


def partTypeNum(partType):
    """Map 'dm'/'gas'/... or 'PartTypeN'/N to an integer particle type."""
    if isinstance(partType, (int, np.integer)):
        return int(partType)
    text = str(partType)
    if text.startswith('PartType'):
        return int(text[len('PartType'):])
    if text.lower() in _PT_ALIASES:
        return _PT_ALIASES[text.lower()]
    if text.isdigit():
        return int(text)
    raise ValueError("Unknown particle type [%r]" % partType)


def particleMass(run, snapNum, partType='dm', base='snapshot'):
    """Per-particle mass (code units) from the Header MassTable."""
    pt = partTypeNum(partType)
    return float(loadHeader(run, snapNum, base)['MassTable'][pt])


# --------------------------------------------------------------------------
# multi-file particle reads
# --------------------------------------------------------------------------
def _read48(path, dset, start, count):
    """Read a 48-bit (6-byte) integer dataset as uint64 via HDF5 conversion."""
    with h5py.File(path, 'r') as hf:
        dsid = hf[dset].id
        out = np.empty((int(count),), dtype='u8')
        if count:
            fileSpace = dsid.get_space()
            fileSpace.select_hyperslab((np.uint64(start),), (np.uint64(count),))
            memSpace = h5s.create_simple((int(count),))
            dsid.read(memSpace, fileSpace, out, h5t.py_create(np.dtype('u8')))
        return out


def _readPiece(path, dset, start, count):
    info = _backend.dataset_info(path, dset)
    if info['dtype'] == '':          # backend can't type it -> 48-bit integer
        return _read48(path, dset, start, count)
    if count == 0:
        return np.empty((0,) + tuple(info['shape'][1:]), dtype=np.dtype(info['dtype']))
    return _backend.read(path, dset, start, count)


def _snapCounts(run, snapNum, base, pt):
    """(files, cumulative file boundaries) for particle type pt at this snap."""
    out = outputDir(run)
    key = (out, snapNum, base, pt)
    if key not in _countCache:
        files = _firstSnapFile(run, snapNum, base)
        counts = [int(_backend.read_attrs(path, 'Header')['NumPart_ThisFile'][pt])
                  for path in files]
        _countCache[key] = (files, np.concatenate([[0], np.cumsum(counts)]))
    return _countCache[key]


def _readRange(files, cum, dset, start, count):
    """Concatenate dset[start:start+count] across the multi-file pieces."""
    if count <= 0:
        return _readPiece(files[0], dset, 0, 0)
    pieces, globalPos, rem = [], int(start), int(count)
    fileIdx = int(np.searchsorted(cum, globalPos, side='right') - 1)
    while rem > 0 and fileIdx < len(files):
        local = globalPos - int(cum[fileIdx])
        avail = int(cum[fileIdx + 1] - cum[fileIdx]) - local
        take = min(avail, rem)
        if take > 0:
            pieces.append(_readPiece(files[fileIdx], dset, local, take))
        globalPos += take
        rem -= take
        fileIdx += 1
    return pieces[0] if len(pieces) == 1 else np.concatenate(pieces)


def listFields(run, snapNum, partType='dm', base='snapshot'):
    """Particle field names present for a type at this snapshot."""
    pt = partTypeNum(partType)
    firstFile = _firstSnapFile(run, snapNum, base)[0]
    return sorted(_backend.list_datasets(firstFile, 'PartType%d' % pt))


def loadSubset(run, snapNum, partType='dm', fields=None, subset=None,
               base='snapshot', units='code', sq=True):
    """Load particle fields of one type across the snapshot's files."""
    if units not in ('code', 'cgs'):
        raise ValueError("units must be 'code' or 'cgs'")
    pt = partTypeNum(partType)
    files, cum = _snapCounts(run, snapNum, base, pt)
    grp = 'PartType%d' % pt

    singleField = isinstance(fields, str)
    if singleField:
        fields = [fields]
    if fields is None:
        fields = sorted(_backend.list_datasets(files[0], grp))
        if not fields:
            raise ValueError("PartType%d has no fields at output %d" % (pt, snapNum))

    if subset is not None:
        start, count = int(subset['start']), int(subset['count'])
    else:
        start, count = 0, int(cum[-1])

    header = _backend.read_attrs(files[0], 'Header')
    if 'HubbleParam' not in header and units == 'cgs':
        header = loadHeader(run, snapNum, base)

    result = {'count': count}
    for field in fields:
        dset = '%s/%s' % (grp, field)
        arr = _readRange(files, cum, dset, start, count)
        if units == 'cgs':
            factor = _units.cgsFactor(_backend.read_attrs(files[0], dset), header)
            if factor != 1.0:
                arr = arr.astype(np.float64) * factor
        result[field] = arr

    if sq and singleField:
        return result[fields[0]]
    return result


# --------------------------------------------------------------------------
# group catalog
# --------------------------------------------------------------------------
def _catCounts(run, snapNum, kind):
    """(files, cumulative row boundaries) for 'Group' or 'Subhalo' rows."""
    out = outputDir(run)
    key = (out, snapNum, kind)
    if key not in _catCountCache:
        files = _groupFiles(run, snapNum)
        if not files:
            raise ValueError("No group catalog for output %d in %s" % (snapNum, out))
        attr = 'Ngroups_ThisFile' if kind == 'Group' else 'Nsubhalos_ThisFile'
        counts = [int(_backend.read_attrs(path, 'Header')[attr]) for path in files]
        _catCountCache[key] = (files, np.concatenate([[0], np.cumsum(counts)]))
    return _catCountCache[key]


def _loadCatColumn(run, snapNum, kind, field):
    """Concatenate one catalog column across all group files."""
    files, cum = _catCounts(run, snapNum, kind)
    dset = '%s/%s' % (kind, field)
    return _readRange(files, cum, dset, 0, int(cum[-1]))


def _catRow(run, snapNum, kind, field, gid):
    """Read a single catalog row `gid` from whichever file holds it."""
    files, cum = _catCounts(run, snapNum, kind)
    gid = int(gid)
    if gid < 0 or gid >= int(cum[-1]):
        raise IndexError("%s id %d out of range [0, %d)" % (kind, gid, int(cum[-1])))
    fileIdx = int(np.searchsorted(cum, gid, side='right') - 1)
    return _readPiece(files[fileIdx], '%s/%s' % (kind, field),
                      gid - int(cum[fileIdx]), 1)[0]


def _loadCat(run, snapNum, kind, fields, sq):
    files, cum = _catCounts(run, snapNum, kind)
    singleField = isinstance(fields, str)
    if singleField:
        fields = [fields]
    if fields is None:
        fields = sorted(_backend.list_datasets(files[0], kind))
    result = {'count': int(cum[-1])}
    for field in fields:
        result[field] = _loadCatColumn(run, snapNum, kind, field)
    if sq and singleField:
        return result[fields[0]]
    return result


def loadGroups(run, snapNum, fields=None, sq=True):
    """Load FoF group-catalog fields (the `Group` table)."""
    return _loadCat(run, snapNum, 'Group', fields, sq)


def loadSubhalos(run, snapNum, fields=None, sq=True):
    """Load Subfind subhalo-catalog fields (the `Subhalo` table)."""
    return _loadCat(run, snapNum, 'Subhalo', fields, sq)


def loadSingle(run, snapNum, id, kind='Subhalo', fields=None):
    """Load a single catalog row (one group or subhalo) by id."""
    if kind not in ('Group', 'Subhalo'):
        raise ValueError("kind must be 'Group' or 'Subhalo'")
    files, _ = _catCounts(run, snapNum, kind)
    if fields is None:
        fields = sorted(_backend.list_datasets(files[0], kind))
    singleField = isinstance(fields, str)
    if singleField:
        fields = [fields]
    out = {field: _catRow(run, snapNum, kind, field, id) for field in fields}
    return out[fields[0]] if singleField else out


# --------------------------------------------------------------------------
# particles of one halo / subhalo (offsets from the catalog)
# --------------------------------------------------------------------------
def getSnapOffsets(run, snapNum, id, kind):
    """(start, count) per particle type for a group or subhalo."""
    if kind not in ('Group', 'Subhalo'):
        raise ValueError("kind must be 'Group' or 'Subhalo'")
    offsets = _catRow(run, snapNum, kind, kind + 'OffsetType', id)
    lengths = _catRow(run, snapNum, kind, kind + 'LenType', id)
    return {'offsetType': np.asarray(offsets, dtype=np.int64),
            'lenType': np.asarray(lengths, dtype=np.int64)}


def loadHalo(run, snapNum, id, partType='dm', fields=None, base='snapshot',
             units='code', sq=True):
    """Load all particles of one type belonging to FoF halo `id`."""
    pt = partTypeNum(partType)
    offsets = getSnapOffsets(run, snapNum, id, 'Group')
    sub = {'start': offsets['offsetType'][pt], 'count': offsets['lenType'][pt]}
    return loadSubset(run, snapNum, pt, fields, subset=sub, base=base,
                      units=units, sq=sq)


def loadSubhalo(run, snapNum, id, partType='dm', fields=None, base='snapshot',
                units='code', sq=True):
    """Load all particles of one type belonging to subhalo `id`."""
    pt = partTypeNum(partType)
    offsets = getSnapOffsets(run, snapNum, id, 'Subhalo')
    sub = {'start': offsets['offsetType'][pt], 'count': offsets['lenType'][pt]}
    return loadSubset(run, snapNum, pt, fields, subset=sub, base=base,
                      units=units, sq=sq)
