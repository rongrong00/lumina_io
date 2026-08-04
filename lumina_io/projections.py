"""2D projection maps, one file per snapshot and slab depth."""

import os
import glob
import numpy as np

from . import _backend, units as _units
import h5py

PROJ_SUBDIR = 'projections'

_projDirsCache = {}
_dsetsCache = {}


def projDirs(basePath):
    """List the `projections` directories reachable from basePath."""
    if basePath in _projDirsCache:
        return _projDirsCache[basePath]
    if glob.glob(os.path.join(basePath, 'projections[0-9]*')):
        dirs = [basePath]
    elif os.path.isdir(os.path.join(basePath, PROJ_SUBDIR)):
        dirs = [os.path.join(basePath, PROJ_SUBDIR)]
    else:
        dirs = sorted(glob.glob(os.path.join(basePath, '*', PROJ_SUBDIR)))
    if not dirs:
        raise ValueError(f"No {PROJ_SUBDIR} directories found under {basePath}")
    _projDirsCache[basePath] = dirs
    return dirs


def listDepths(basePath):
    """Projection depths available under basePath."""
    out = set()
    for projDir in projDirs(basePath):
        for dirPath in glob.glob(os.path.join(projDir, 'projections[0-9]*')):
            tail = os.path.basename(dirPath)[len('projections'):]
            if tail.isdigit():
                out.add(int(tail))
    return sorted(out)


def _resolveDepth(basePath, depth):
    if depth is not None:
        text = str(depth)
        if text.startswith('projections'):
            text = text[len('projections'):]
        return int(text)
    avail = listDepths(basePath)
    if len(avail) == 1:
        return avail[0]
    if 2 in avail:                       # the thinnest slab is the natural default
        return 2
    raise ValueError("Cannot guess a projection depth: %s offers %s. "
                     "Pass depth=." % (basePath, avail))


def _depthDirs(basePath, depth):
    name = 'projections%03d' % depth
    dirs = [os.path.join(projDir, name) for projDir in projDirs(basePath)]
    return [dirPath for dirPath in dirs if os.path.isdir(dirPath)]


_NUM_PATTERNS = ('projections_%03d.hdf5', 'projections_%02d.hdf5',
                 'projections_%d.hdf5')


def filePath(basePath, snapNum, depth=None):
    """Path to the projection file for one snapshot/depth, or None."""
    depth = _resolveDepth(basePath, depth)
    for dirPath in _depthDirs(basePath, depth):
        for pattern in _NUM_PATTERNS:
            path = os.path.join(dirPath, pattern % snapNum)
            if os.path.isfile(path):
                return path
    return None


def _requireFile(basePath, snapNum, depth):
    path = filePath(basePath, snapNum, depth)
    if path is None:
        raise ValueError("No projection file for snapshot %d at depth %d under %s"
                         % (snapNum, depth, basePath))
    return path


def _datasetsIn(path):
    if path not in _dsetsCache:
        _dsetsCache[path] = [name for name in _backend.list_datasets(path)
                             if name != 'Header']
    return _dsetsCache[path]


def listFields(basePath, snapNum, depth=None):
    """Map field names available in a snapshot's projection file."""
    depth = _resolveDepth(basePath, depth)
    return sorted(_datasetsIn(_requireFile(basePath, snapNum, depth)))


def listSnaps(basePath, depth=None):
    """Snapshot numbers for which projection files exist."""
    depths = [_resolveDepth(basePath, depth)] if depth is not None else listDepths(basePath)
    snaps = set()
    for dep in depths:
        for dirPath in _depthDirs(basePath, dep):
            for path in glob.glob(os.path.join(dirPath, 'projections_[0-9]*.hdf5')):
                tail = os.path.basename(path)[:-5].rsplit('_', 1)[1]
                if tail.isdigit():
                    snaps.add(int(tail))
    return sorted(snaps)


def loadHeader(basePath, snapNum, depth=None, datasets=False):
    """Projection header (BoxSize, Width, Height, Depth, Redshift, Time)."""
    depth = _resolveDepth(basePath, depth)
    path = _requireFile(basePath, snapNum, depth)
    header = _backend.read_attrs(path, 'Header')
    if datasets:
        with h5py.File(path, 'r') as hf:
            for name, dset in hf['Header'].items():
                header[name] = dset[()]
    return header


def fieldUnitAttrs(basePath, snapNum, field, depth=None):
    """Unit scaling attributes of a projection map, or None if absent."""
    depth = _resolveDepth(basePath, depth)
    return _backend.read_attrs(_requireFile(basePath, snapNum, depth), field)


def _axisRuns(lo, hi, npix):
    """Row runs [(start, count), ...] covering [lo, hi) modulo npix."""
    span = hi - lo
    if span > npix:
        return [(0, npix)]
    lo = lo % npix
    if lo + span <= npix:
        return [(lo, span)]
    return [(lo, npix - lo), (0, span - (npix - lo))]


def _regionRuns(region, header):
    """Per-axis (start, count) run lists for a ((i0,i1),(j0,j1)) pixel region."""
    nx = int(header.get('NumPixelsX', header.get('NumPixels')))
    ny = int(header.get('NumPixelsY', header.get('NumPixels')))
    runs = []
    for (lo, hi), npix in zip(region, (nx, ny)):
        lo, hi = int(lo), int(hi)
        if hi <= lo:
            raise ValueError("Empty pixel range (%d, %d) in region" % (lo, hi))
        runs.append(_axisRuns(lo, hi, npix))
    return runs


def loadProjection(basePath, snapNum, fields=None, depth=None, region=None,
                   units='code', sq=True, nthreads=0):
    """Load 2D projection maps of one snapshot."""
    if units not in ('code', 'cgs'):
        raise ValueError("projection units must be 'code' (as stored) or 'cgs' (physical cgs)")
    depth = _resolveDepth(basePath, depth)
    path = _requireFile(basePath, snapNum, depth)
    avail = _datasetsIn(path)

    singleField = isinstance(fields, str)
    if singleField:
        fields = [fields]
    if fields is None:
        fields = sorted(avail)
    for field in fields:
        if field not in avail:
            raise ValueError("Snap %d at depth %d has no projection [%s]; it "
                             "holds %s" % (snapNum, depth, field, sorted(avail)))

    header = _backend.read_attrs(path, 'Header')
    nx = int(header.get('NumPixelsX', header.get('NumPixels')))
    ny = int(header.get('NumPixelsY', header.get('NumPixels')))
    if region is not None:
        runs = _regionRuns(region, header)
        pix = tuple((int(lo), int(hi)) for lo, hi in region)
    else:
        runs = [[(0, nx)], [(0, ny)]]
        pix = ((0, nx), (0, ny))

    result = {'pixelRegion': pix}
    for field in fields:
        arr = _backend.read_box_runs(path, field, runs, nthreads)
        if units == 'cgs':
            factor = _units.cgsFactor(fieldUnitAttrs(basePath, snapNum, field, depth), header)
            if factor != 1.0:
                arr = arr.astype(np.float64) * factor
        result[field] = arr

    if sq and singleField:
        return result[fields[0]]
    return result
