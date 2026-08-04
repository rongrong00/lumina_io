"""Black hole outputs (the `Lumina_combined_outputs` data products)."""

import os
import re
import glob
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from . import _backend, units as _units
import h5py

FREQ_SUBDIR = 'BH_frequent_output'
TREE_SUBDIR = 'BH_merger_tree'
COMBINED_SUBDIR = 'Lumina_combined_outputs'

_dirsCache = {}
_hCache = {}
_lifetimesCache = {}


def bhDirs(basePath):
    """Locate the BH output directories: dict with 'frequent' and 'tree' paths."""
    if basePath in _dirsCache:
        return _dirsCache[basePath]
    candidates = [basePath, os.path.join(basePath, COMBINED_SUBDIR)]
    base = os.path.basename(os.path.normpath(basePath))
    if base in (FREQ_SUBDIR, TREE_SUBDIR):
        candidates.append(os.path.dirname(os.path.normpath(basePath)))
    out = {'frequent': None, 'tree': None}
    for cand in candidates:
        if out['frequent'] is None:
            freqDir = (cand if os.path.basename(cand) == FREQ_SUBDIR
                       else os.path.join(cand, FREQ_SUBDIR))
            if glob.glob(os.path.join(freqDir, 'bh_snap*.hdf5')):
                out['frequent'] = freqDir
        if out['tree'] is None:
            treeDir = (cand if os.path.basename(cand) == TREE_SUBDIR
                       else os.path.join(cand, TREE_SUBDIR))
            if os.path.isdir(treeDir):
                out['tree'] = treeDir
    if out['frequent'] is None and out['tree'] is None:
        raise ValueError("No %s/%s found under %s" %
                         (FREQ_SUBDIR, TREE_SUBDIR, basePath))
    _dirsCache[basePath] = out
    return out


def snapPath(basePath, snapNum):
    """Path to one frequent-output file."""
    freqDir = bhDirs(basePath)['frequent']
    if freqDir is None:
        raise ValueError("No %s under %s" % (FREQ_SUBDIR, basePath))
    return os.path.join(freqDir, 'bh_snap%04d.hdf5' % snapNum)


def listSnaps(basePath):
    """Frequent-output numbers available."""
    freqDir = bhDirs(basePath)['frequent']
    snaps = []
    for path in glob.glob(os.path.join(freqDir or '', 'bh_snap*.hdf5')):
        match = re.match(r'bh_snap(\d+)\.hdf5$', os.path.basename(path))
        if match:
            snaps.append(int(match.group(1)))
    return sorted(snaps)


def loadHeader(basePath, snapNum):
    """Header of one frequent output (BoxSize, Redshift, Time)."""
    hdr = _backend.read_attrs(snapPath(basePath, snapNum), 'Header')
    if hdr is None:
        raise ValueError("No Header in %s" % snapPath(basePath, snapNum))
    return hdr


def listFields(basePath, snapNum=None):
    """BH field names in the frequent outputs."""
    if snapNum is None:
        snaps = listSnaps(basePath)
        if not snaps:
            raise ValueError("No frequent outputs under %s" % basePath)
        snapNum = snaps[-1]
    return sorted(_backend.list_datasets(snapPath(basePath, snapNum), 'BH'))


def hubbleParam(basePath, h=None):
    """HubbleParam for unit conversions; pass h= to override."""
    if h is not None:
        return float(h)
    dirs = bhDirs(basePath)
    anchor = os.path.normpath(dirs['frequent'] or dirs['tree'])
    if anchor in _hCache:
        return _hCache[anchor]
    roots = [os.path.dirname(anchor),                    # Lumina_combined_outputs
             os.path.dirname(os.path.dirname(anchor))]   # Lumina root
    patterns = ['lightcone/rlc_*/All.hdf5', '*/lightcone/rlc_*/All.hdf5',
                '3d_cartesian_grid/ren_*/All/All_*.hdf5',
                '*/3d_cartesian_grid/ren_*/All/All_*.hdf5']
    for root in roots:
        for pattern in patterns:
            for path in sorted(glob.glob(os.path.join(root, pattern)))[:1]:
                hdr = _backend.read_attrs(path, 'Header')
                if hdr and 'HubbleParam' in hdr:
                    _hCache[anchor] = float(hdr['HubbleParam'])
                    return _hCache[anchor]
    raise ValueError("Cannot locate HubbleParam near %s; pass h= explicitly, "
                     "or stay in units='code'" % anchor)


def loadSnap(basePath, snapNum, fields=None, units='code', h=None, sq=True,
             nthreads=0):
    """Load the full BH population of one frequent output."""
    singleField = isinstance(fields, str)
    if singleField:
        fields = [fields]
    if fields is None:
        fields = listFields(basePath, snapNum)
    path = snapPath(basePath, snapNum)
    hdr = loadHeader(basePath, snapNum)

    arrays = _backend.read_many([(path, 'BH/' + field, 0, -1)
                                 for field in fields],
                                nthreads_per_read=nthreads)
    result = {'count': len(arrays[0]) if arrays else 0,
              'Time': float(hdr['Time']), 'Redshift': float(hdr['Redshift'])}
    if units != 'code':
        h = hubbleParam(basePath, h)
    for field, arr in zip(fields, arrays):
        if units != 'code':
            arr = _units.convert(arr, field, target=units,
                                 a=float(hdr['Time']), h=h)
        result[field] = arr
    if sq and singleField:
        return result[fields[0]]
    return result


def loadLifetimes(basePath, ids=None):
    """The bh_lifetimes table: first/last frequent output of every BH."""
    key = bhDirs(basePath)['tree']
    if key is None:
        raise ValueError("No %s under %s" % (TREE_SUBDIR, basePath))
    if key not in _lifetimesCache:
        with h5py.File(os.path.join(key, 'full_merger_tree.hdf5'), 'r') as hf:
            grp = hf['bh_lifetimes']
            _lifetimesCache[key] = {name: grp[name][()] for name in grp}
    lifetimes = _lifetimesCache[key]
    if ids is None:
        return dict(lifetimes)
    scalar = np.ndim(ids) == 0
    idArr = np.atleast_1d(np.asarray(ids, dtype=np.int64))
    order = np.argsort(lifetimes['particle_id'])
    pos = np.searchsorted(lifetimes['particle_id'], idArr, sorter=order)
    pos = np.clip(pos, 0, len(order) - 1)
    hit = lifetimes['particle_id'][order[pos]] == idArr
    first = np.where(hit, lifetimes['first_snap'][order[pos]], -1)
    last = np.where(hit, lifetimes['last_snap'][order[pos]], -1)
    if scalar:
        return {'first_snap': int(first[0]), 'last_snap': int(last[0])}
    return {'first_snap': first, 'last_snap': last}


def _warmFile(path):
    """Pull a file through the page cache with plain reads."""
    try:
        with open(path, 'rb') as fh:
            while fh.read(1 << 24):
                pass
    except OSError:
        pass


def trackBH(basePath, ids, fields=None, snapRange=None, units='code', h=None,
            sq=True, nthreads=0, prefetch=True, verbose=False):
    """Time series of individual black holes across the frequent outputs."""
    scalar = np.ndim(ids) == 0
    idArr = np.atleast_1d(np.asarray(ids, dtype=np.int64))
    singleField = isinstance(fields, str)
    if singleField:
        fields = [fields]
    if fields is None:
        fields = listFields(basePath)

    snaps = np.array(listSnaps(basePath))
    if snapRange is not None:
        snaps = snaps[(snaps >= snapRange[0]) & (snaps <= snapRange[1])]
    if bhDirs(basePath)['tree'] is not None:
        lifetimes = loadLifetimes(basePath, idArr)
        alive = lifetimes['first_snap'] >= 0
        if not alive.any():
            raise ValueError("None of the requested IDs appear in bh_lifetimes")
        snaps = snaps[(snaps >= lifetimes['first_snap'][alive].min()) &
                      (snaps <= lifetimes['last_snap'][alive].max())]
    if len(snaps) == 0:
        raise ValueError("No frequent outputs in the requested range")

    nsnap, nid = len(snaps), len(idArr)
    info = {field: _backend.dataset_info(snapPath(basePath, snaps[0]),
                                         'BH/' + field)
            for field in fields}
    result = {'snaps': snaps,
              'Time': np.empty(nsnap), 'Redshift': np.empty(nsnap),
              'found': np.zeros((nsnap, nid), dtype=bool)}
    for field in fields:
        dtype = np.dtype(info[field]['dtype'])
        trailing = tuple(info[field]['shape'][1:])
        if dtype.kind == 'f':
            result[field] = np.full((nsnap, nid) + trailing, np.nan, dtype=dtype)
        else:
            result[field] = np.full((nsnap, nid) + trailing, -1, dtype=dtype)

    if units != 'code':
        h = hubbleParam(basePath, h)

    executor = ThreadPoolExecutor(max_workers=6) if prefetch and nsnap > 1 else None
    warm = {}
    try:
        for row, snapNum in enumerate(snaps):
            if executor is not None:
                for ahead in range(row, min(row + 18, nsnap)):
                    if ahead not in warm:
                        warm[ahead] = executor.submit(
                            _warmFile, snapPath(basePath, snaps[ahead]))
                warm.pop(row).result()
            _trackOne(basePath, row, snapNum, idArr, fields, units, h,
                      nthreads, result)
            if verbose and row % 100 == 0:
                print('  trackBH: %d / %d outputs' % (row, nsnap))
    finally:
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)

    if scalar:
        for field in fields:
            result[field] = result[field][:, 0]
        result['found'] = result['found'][:, 0]
    if sq and singleField and scalar:
        return result[fields[0]]
    return result


def _trackOne(basePath, row, snapNum, idArr, fields, units, h, nthreads,
              result):
    """Fill row of the trackBH result arrays from one frequent output."""
    path = snapPath(basePath, snapNum)
    hdr = _backend.read_attrs(path, 'Header')
    result['Time'][row] = float(hdr['Time'])
    result['Redshift'][row] = float(hdr['Redshift'])
    pids = _backend.read(path, 'BH/ParticleIDs', 0, -1, nthreads)
    rows = np.flatnonzero(np.isin(pids, idArr))
    if len(rows) == 0:
        return
    rowOfId = {pid: idx for idx, pid in enumerate(pids[rows])}
    cols = np.array([rowOfId.get(pid, -1) for pid in idArr])
    ones = np.ones(len(rows), dtype=np.int64)
    for field in fields:
        data = _backend.read_multi(path, 'BH/' + field, rows, ones, nthreads)
        if units != 'code':
            data = _units.convert(data, field, target=units,
                                  a=float(hdr['Time']), h=h)
        for idIdx in np.flatnonzero(cols >= 0):
            result[field][row, idIdx] = data[cols[idIdx]]
    result['found'][row, cols >= 0] = True


def _readGroup(path, group):
    """All datasets of one HDF5 group as a dict."""
    out = {}
    with h5py.File(path, 'r') as hf:
        if group not in hf:
            return out
        for name, dset in hf[group].items():
            out[name] = dset[()]
    return out


def loadMergerTree(basePath, groups=('mergers', 'bh_lifetimes', 'indices')):
    """The full merger catalog as nested dicts."""
    treeDir = bhDirs(basePath)['tree']
    if treeDir is None:
        raise ValueError("No %s under %s" % (TREE_SUBDIR, basePath))
    path = os.path.join(treeDir, 'full_merger_tree.hdf5')
    if isinstance(groups, str):
        return _readGroup(path, groups)
    return {name: _readGroup(path, name) for name in groups}


def loadMergers(basePath, snapNum):
    """Mergers of one frequent-output interval."""
    treeDir = bhDirs(basePath)['tree']
    if treeDir is None:
        raise ValueError("No %s under %s" % (TREE_SUBDIR, basePath))
    out = _readGroup(os.path.join(treeDir, 'mergers_%04d.hdf5' % snapNum),
                     'mergers')
    out['count'] = len(out['remnant_id']) if 'remnant_id' in out else 0
    return out


_treeCache = {}


def _tree(basePath):
    """Cached mergers + indices groups of the full tree."""
    key = bhDirs(basePath)['tree']
    if key not in _treeCache:
        _treeCache[key] = loadMergerTree(basePath, groups=('mergers', 'indices'))
    return _treeCache[key]


def findMergers(basePath, id):
    """All merger events involving one BH."""
    tree = _tree(basePath)
    mergers, indices = tree['mergers'], tree['indices']
    id = np.int64(id)

    asRemnant = {}
    hits = np.flatnonzero(indices['remnant_id'] == id)
    idxs = (np.asarray(indices['remnant_merger_idxs'][hits[0]], dtype=np.int64)
            if len(hits) else np.empty(0, dtype=np.int64))
    for name, col in mergers.items():
        asRemnant[name] = col[idxs]
    asRemnant['count'] = len(idxs)

    asVictim = None
    hits = np.flatnonzero(indices['victim_id'] == id)
    if len(hits):
        rowIdx = int(indices['victim_merger_idx'][hits[0]])
        asVictim = {name: col[rowIdx] for name, col in mergers.items()}
    return {'asRemnant': asRemnant, 'asVictim': asVictim}


def mainProgenitorChain(basePath, id):
    """The main-progenitor ID chain of one BH, walking the catalog backwards.

    At a BH-BH merger the surviving ParticleID can be the LIGHTER partner's,
    so tracking one ID does not follow the physically growing object.
    Wherever the remnant's pre-merger mass is below the most massive
    victim's, the main branch continues backwards on that victim's ID."""
    chain = []
    curId = int(id)
    hiSnap = int(loadLifetimes(basePath, curId)['last_snap'])
    for _ in range(10000):
        events = findMergers(basePath, curId)['asRemnant']
        switch = None
        for idx in np.argsort(np.asarray(events['snap_to']))[::-1]:
            if int(events['snap_to'][idx]) > hiSnap:
                continue                    # after this segment's window
            victimMasses = np.asarray(events['victim_masses'][idx],
                                      dtype=np.float64)
            if victimMasses.size and victimMasses.max() > float(events['mass_before'][idx]):
                victimId = int(np.asarray(events['victim_ids'][idx])
                               [int(np.argmax(victimMasses))])
                switch = (int(events['snap_from'][idx]),
                          int(events['snap_to'][idx]), victimId)
                break
        if switch is None:
            chain.append((curId,
                          int(loadLifetimes(basePath, curId)['first_snap']),
                          hiSnap))
            break
        snapFrom, snapTo, victimId = switch
        chain.append((curId, snapTo, hiSnap))   # curId is the main branch from the merger on
        curId, hiSnap = victimId, snapFrom      # the victim carries it before the merger
    return chain[::-1]


def trackMainProgenitor(basePath, id, fields=None, units='code', h=None,
                        nthreads=0, prefetch=True, verbose=False):
    """Like trackBH, but stitched along the main progenitor branch."""
    chain = mainProgenitorChain(basePath, id)
    parts = [trackBH(basePath, cid, fields, snapRange=(loSnap, hiSnap),
                     units=units, h=h, sq=False, nthreads=nthreads,
                     prefetch=prefetch, verbose=verbose)
             for cid, loSnap, hiSnap in chain]
    out = {'chain': chain,
           'ids': np.concatenate([np.full(len(part['snaps']), cid,
                                          dtype=np.int64)
                                  for part, (cid, _, _) in zip(parts, chain)])}
    for key in parts[0]:
        if key != 'snaps' and not isinstance(parts[0][key], np.ndarray):
            continue
        out[key] = np.concatenate([part[key] for part in parts])
    return out
