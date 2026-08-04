"""Path resolution and naming conventions for the LUMINA on-disk layout."""

import os
import glob

from . import _backend

OUTPUT_DIR_CANDIDATES = ['output_subfind', 'output']


_PART_TYPE_NAMES = {
    0: ('gas', 'cells'),
    1: ('dm', 'darkmatter'),
    3: ('tracer', 'tracers', 'tracermc', 'trmc'),
    4: ('star', 'stars', 'stellar', 'wind'),
    5: ('bh', 'bhs', 'blackhole', 'blackholes'),
}

_PART_TYPE_BY_NAME = {alias: num
                      for num, aliases in _PART_TYPE_NAMES.items()
                      for alias in aliases}


def partTypeNum(partType):
    """Particle type number from an alias, a digit string, or an int."""
    text = str(partType)
    if text.isdigit():
        return int(text)
    try:
        return _PART_TYPE_BY_NAME[text.lower()]
    except KeyError:
        raise ValueError("Unknown particle type [%s]; known names are %s"
                         % (partType, sorted(_PART_TYPE_BY_NAME))) from None


def resolveBasePath(basePath):
    """Return the snapshot-set directory for a run or output directory."""
    if os.path.isdir(os.path.join(basePath, 'PartType0')) or \
       os.path.isdir(os.path.join(basePath, 'Group')) or \
       os.path.isdir(os.path.join(basePath, 'snapshots')) or \
       os.path.isdir(os.path.join(basePath, 'group_files')) or \
       glob.glob(os.path.join(basePath, 'snap_*.hdf5')):
        return basePath
    for cand in OUTPUT_DIR_CANDIDATES:
        path = os.path.join(basePath, cand)
        if os.path.isdir(path):
            return path
    raise ValueError("Could not locate LUMINA output under basePath: " + basePath)


def searchDirs(basePath):
    """Directories that may hold kind subdirs or stub files."""
    base = resolveBasePath(basePath)
    dirs = [base]
    for sub in ('snapshots', 'group_files'):
        path = os.path.join(base, sub)
        if os.path.isdir(path):
            dirs.append(path)
    return dirs


def _stubPath(basePath, fileName):
    dirs = searchDirs(basePath)
    for dirPath in dirs:
        path = os.path.join(dirPath, fileName)
        if os.path.isfile(path):
            return path
    return os.path.join(dirs[0], fileName)


def snapPath(basePath, snapNum):
    """Path to the snapshot header stub file (may not exist for all snaps)."""
    return _stubPath(basePath, 'snap_%03d.hdf5' % snapNum)


def gcPath(basePath, snapNum):
    """Path to the group catalog header stub file."""
    return _stubPath(basePath, 'fof_subhalo_tab_%03d.hdf5' % snapNum)


_datasetsCache = {}


def _datasetsIn(path):
    if path not in _datasetsCache:
        _datasetsCache[path] = set(_backend.list_datasets(path))
    return _datasetsCache[path]


def fieldPath(basePath, kind, field, snapNum):
    """Locate the file holding `field` and return (filePath, datasetName)."""
    # per-field file: <kind>/<field>_NNN.hdf5  (catalogs nest one level deeper)
    for base in searchDirs(basePath):
        if kind in ('Group', 'Subhalo'):
            path = os.path.join(base, kind, field, '%s_%03d.hdf5' % (field, snapNum))
            if os.path.isfile(path):
                return path, field
        else:
            path = os.path.join(base, kind, '%s_%03d.hdf5' % (field, snapNum))
            if os.path.isfile(path):
                return path, field
            # combined file: PartTypeN/PartTypeN_NNN.hdf5 with all fields
            path = os.path.join(base, kind, '%s_%03d.hdf5' % (kind, snapNum))
            if os.path.isfile(path) and field in _datasetsIn(path):
                return path, field
    # last resort: the stub file with virtual datasets
    stub = gcPath(basePath, snapNum) if kind in ('Group', 'Subhalo') else snapPath(basePath, snapNum)
    if os.path.isfile(stub):
        try:
            if field in _backend.list_datasets(stub, kind):
                return stub, kind + '/' + field
        except (RuntimeError, KeyError):
            pass
    return None, None


def listFields(basePath, kind, snapNum):
    """List field names available for `kind` at this snapshot."""
    fields = set()
    for base in searchDirs(basePath):
        if kind in ('Group', 'Subhalo'):
            for dirPath in glob.glob(os.path.join(base, kind, '*')):
                fieldName = os.path.basename(dirPath)
                if os.path.isfile(os.path.join(dirPath,
                                               '%s_%03d.hdf5' % (fieldName, snapNum))):
                    fields.add(fieldName)
        else:
            for path in glob.glob(os.path.join(base, kind, '*_%03d.hdf5' % snapNum)):
                name = os.path.basename(path).rsplit('_', 1)[0]
                if name == kind:  # combined file: list its datasets
                    fields.update(_backend.list_datasets(path))
                else:
                    fields.add(name)
    return sorted(fields)


_boxSizeCache = {}


def boxSize(basePath, snapNum=None):
    """BoxSize in code units, read from any available header stub."""
    base = resolveBasePath(basePath)
    if base in _boxSizeCache:
        return _boxSizeCache[base]
    stubs = []
    if snapNum is not None:
        stubs += [snapPath(basePath, snapNum), gcPath(basePath, snapNum)]
    for dirPath in searchDirs(basePath):
        stubs += sorted(glob.glob(os.path.join(dirPath, 'snap_*.hdf5')), reverse=True)
        stubs += sorted(glob.glob(os.path.join(dirPath, 'fof_subhalo_tab_*.hdf5')),
                        reverse=True)
    for stub in stubs:
        if os.path.isfile(stub):
            hdr = _backend.read_attrs(stub, 'Header')
            if hdr and 'BoxSize' in hdr:
                _boxSizeCache[base] = float(hdr['BoxSize'])
                return _boxSizeCache[base]
    raise ValueError("Could not determine BoxSize: no header stub found under " + base)


def listSnaps(basePath, kind=None):
    """List snapshot numbers for which field files exist."""
    snaps = set()
    for base in searchDirs(basePath):
        patterns = [os.path.join(base, kind or 'PartType*', '*_[0-9][0-9][0-9].hdf5'),
                    os.path.join(base, (kind or 'Group'), '*', '*_[0-9][0-9][0-9].hdf5')]
        for pattern in patterns:
            for path in glob.glob(pattern):
                snaps.add(int(os.path.basename(path).rsplit('_', 1)[1][:-5]))
    return sorted(snaps)
