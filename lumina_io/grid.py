"""Readers for the gridded LUMINA output under `3d_cartesian_grid`."""

import os
import glob
import numpy as np

from . import _backend, units as _units
import h5py

GRID_SUBDIR = '3d_cartesian_grid'

_gridDirsCache = {}
_dsetsCache = {}
_unitAttrsCache = {}


def gridDirs(basePath):
    """List the 3d_cartesian_grid directories reachable from basePath."""
    if basePath in _gridDirsCache:
        return _gridDirsCache[basePath]
    if glob.glob(os.path.join(basePath, 'ren_*')):
        dirs = [basePath]
    elif os.path.isdir(os.path.join(basePath, GRID_SUBDIR)):
        dirs = [os.path.join(basePath, GRID_SUBDIR)]
    else:
        dirs = sorted(glob.glob(os.path.join(basePath, '*', GRID_SUBDIR)))
    if not dirs:
        raise ValueError(f"No {GRID_SUBDIR} directories found under {basePath}")
    _gridDirsCache[basePath] = dirs
    return dirs


def _renDirs(basePath, res):
    dirs = [os.path.join(gridDir, 'ren_%d' % res) for gridDir in gridDirs(basePath)]
    return [dirPath for dirPath in dirs if os.path.isdir(dirPath)]


def listResolutions(basePath):
    """Grid resolutions (cells per side) available under basePath."""
    out = set()
    for gridDir in gridDirs(basePath):
        for dirPath in glob.glob(os.path.join(gridDir, 'ren_*')):
            tail = os.path.basename(dirPath)[4:]
            if tail.isdigit():
                out.add(int(tail))
    return sorted(out)


def _resolveRes(basePath, res):
    if res is not None:
        text = str(res)
        if text.startswith('ren_'):
            text = text[4:]
        return int(text)
    avail = listResolutions(basePath)
    if len(avail) == 1:
        return avail[0]
    raise ValueError("%s holds grids at more than one resolution (%s); "
                     "pass res= to choose." % (basePath, avail))


_NUM_PATTERNS = ('%s_%03d.hdf5', '%s_%02d.hdf5', '%s_%d.hdf5')


def _findNumbered(dirPath, prefix, num):
    """Path <dirPath>/<prefix>_<num>.hdf5, trying common zero paddings."""
    for pattern in _NUM_PATTERNS:
        path = os.path.join(dirPath, pattern % (prefix, num))
        if os.path.isfile(path):
            return path
    return None


def _datasetsIn(path):
    if path not in _dsetsCache:
        _dsetsCache[path] = [name for name in _backend.list_datasets(path)
                             if name != 'Header']
    return _dsetsCache[path]


def fieldPath(basePath, snapNum, field, res=None):
    """Locate the file holding a grid field; returns (filePath, datasetName)."""
    res = _resolveRes(basePath, res)
    for ren in _renDirs(basePath, res):
        dirPath = os.path.join(ren, field)
        path = _findNumbered(dirPath, field, snapNum) if os.path.isdir(dirPath) else None
        if path is None:
            for pattern in _NUM_PATTERNS:
                hits = glob.glob(os.path.join(ren, '*', pattern % (field, snapNum)))
                if hits:
                    path = hits[0]
                    break
        if path is not None:
            dsets = _datasetsIn(path)
            if field in dsets:
                return path, field
            if len(dsets) == 1:        # e.g. z_reion_50.hdf5 -> ReionizationRedshift
                return path, dsets[0]
        path = _findNumbered(os.path.join(ren, 'All'), 'All', snapNum)
        if path is not None and field in _datasetsIn(path):
            return path, field
    return None, None


def listFields(basePath, snapNum, res=None):
    """List grid field names available at this snapshot/resolution."""
    res = _resolveRes(basePath, res)
    fields = set()
    for ren in _renDirs(basePath, res):
        for dirPath in glob.glob(os.path.join(ren, '*')):
            if not os.path.isdir(dirPath):
                continue
            for pattern in _NUM_PATTERNS:
                for path in glob.glob(os.path.join(dirPath, pattern % ('*', snapNum))):
                    name = os.path.basename(path)[:-5].rsplit('_', 1)[0]
                    if name == 'All':
                        fields.update(_datasetsIn(path))
                    else:
                        fields.add(name)
    return sorted(fields)


def listSnaps(basePath, res=None, field=None):
    """List snapshot numbers for which grid files exist."""
    resList = [_resolveRes(basePath, res)] if res is not None else listResolutions(basePath)
    snaps = set()
    for resVal in resList:
        for ren in _renDirs(basePath, resVal):
            fieldDir = os.path.join(ren, field or 'All')
            dirs = [fieldDir] if os.path.isdir(fieldDir) else \
                [entry for entry in glob.glob(os.path.join(ren, '*'))
                 if os.path.isdir(entry)]
            for dirPath in dirs:
                for path in glob.glob(os.path.join(dirPath, '*_[0-9]*.hdf5')):
                    tail = os.path.basename(path)[:-5].rsplit('_', 1)[1]
                    if tail.isdigit():
                        snaps.add(int(tail))
    return sorted(snaps)


def loadHeader(basePath, snapNum, res=None, datasets=False):
    """Grid header (BoxSize, NumPixels, Redshift, Time, cosmology)."""
    res = _resolveRes(basePath, res)
    for ren in _renDirs(basePath, res):
        path = _findNumbered(os.path.join(ren, 'All'), 'All', snapNum)
        if path is None and not datasets:
            for dirPath in sorted(glob.glob(os.path.join(ren, '*'))):
                if os.path.isdir(dirPath):
                    path = _findNumbered(dirPath, os.path.basename(dirPath), snapNum)
                    if path:
                        break
        if path is None:
            continue
        header = _backend.read_attrs(path, 'Header')
        if header is None:
            continue
        if datasets:
            with h5py.File(path, 'r') as hf:
                for name, dset in hf['Header'].items():
                    header[name] = dset[()]
        return header
    raise ValueError("No grid files for snapshot %d at res %d under %s"
                     % (snapNum, res, basePath))


def fieldUnitAttrs(basePath, snapNum, field, res=None):
    """Unit scaling attributes of a grid field, read from the All file."""
    res = _resolveRes(basePath, res)
    for ren in _renDirs(basePath, res):
        key = (ren, field)
        if key not in _unitAttrsCache:
            path = _findNumbered(os.path.join(ren, 'All'), 'All', snapNum)
            if path is None:
                hits = sorted(glob.glob(os.path.join(ren, 'All', 'All_*.hdf5')))
                path = hits[0] if hits else None
            _unitAttrsCache[key] = _backend.read_attrs(path, field) if path else None
        if _unitAttrsCache[key] is not None:
            return _unitAttrsCache[key]
    return None


def _regionToPixels(region, header):
    """Normalize a region spec to three half-open pixel ranges (lo, hi)."""
    npix = int(header['NumPixels'])
    if isinstance(region, dict):
        cell = float(header['BoxSize']) / npix
        center = np.asarray(region['center'], dtype=np.float64)
        size = np.broadcast_to(np.asarray(region['size'], dtype=np.float64), (3,))
        los = np.floor((center - size / 2.0) / cell).astype(np.int64)
        his = np.ceil((center + size / 2.0) / cell).astype(np.int64)
        pairs = list(zip(los, his))
    else:
        pairs = [(int(lo), int(hi)) for lo, hi in region]
    out = []
    for lo, hi in pairs:
        if hi <= lo:
            raise ValueError("Empty pixel range (%d, %d) in region" % (lo, hi))
        out.append((0, npix) if hi - lo > npix else (lo, hi))
    return out


def _axisRuns(lo, hi, npix):
    """Row runs [(start, count), ...] covering [lo, hi) modulo npix."""
    span = hi - lo
    if span > npix:
        return [(0, npix)]
    lo = lo % npix
    if lo + span <= npix:
        return [(lo, span)]
    return [(lo, npix - lo), (0, span - (npix - lo))]




def loadGrid(basePath, snapNum, fields=None, res=None, region=None,
             units='code', sq=True, nthreads=0):
    """Load 3D cartesian grid fields of one snapshot."""
    if units not in ('code', 'cgs'):
        raise ValueError("grid units must be 'code' (as stored) or 'cgs' (physical cgs)")
    res = _resolveRes(basePath, res)
    singleField = isinstance(fields, str)
    if singleField:
        fields = [fields]
    if fields is None:
        fields = listFields(basePath, snapNum, res)
        if not fields:
            raise ValueError("No grid fields found for snapshot %d at res %d under %s"
                             % (snapNum, res, basePath))

    located = {}
    for field in fields:
        path, dset = fieldPath(basePath, snapNum, field, res)
        if path is None:
            raise ValueError("No grid field [%s] at snap %d, res %d; this "
                             "resolution has %s"
                             % (field, snapNum, res, listFields(basePath, snapNum, res)))
        located[field] = (path, dset)

    header = _backend.read_attrs(located[fields[0]][0], 'Header')
    npix = int(header['NumPixels'])
    pix = _regionToPixels(region, header) if region is not None else [(0, npix)] * 3
    runs = [_axisRuns(lo, hi, npix) for lo, hi in pix]

    result = {'pixelRegion': tuple(pix)}
    for field in fields:
        arr = _backend.read_box_runs(located[field][0], located[field][1],
                                     runs, nthreads)
        if units == 'cgs':
            factor = _units.cgsFactor(fieldUnitAttrs(basePath, snapNum, field, res), header)
            if factor != 1.0:
                arr = arr.astype(np.float64) * factor
        result[field] = arr

    if sq and singleField:
        return result[fields[0]]
    return result


def iterGrid(basePath, snapNum, fields=None, res=None, chunkSize=64,
             units='code', nthreads=0, prefetch=True):
    """Iterate over a grid in memory-bounded slabs of chunkSize x-planes."""
    res = _resolveRes(basePath, res)
    if isinstance(fields, str):
        fields = [fields]
    npix = int(loadHeader(basePath, snapNum, res)['NumPixels'])

    def loadFn(slabStart, slabCount):
        return loadGrid(basePath, snapNum, fields, res=res,
                        region=((slabStart, slabStart + slabCount),
                                (0, npix), (0, npix)),
                        units=units, sq=False, nthreads=nthreads)

    yield from _backend.iter_chunks(loadFn, 0, npix, chunkSize, prefetch)
