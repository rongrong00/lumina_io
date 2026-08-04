"""Stitched access to the LUMINA lightcone across both epoch trees."""

import os
import glob
import numpy as np

from . import _backend
import h5py

LC_SUBDIR = 'lightcone'

_lcDirsCache = {}
_segmentsCache = {}
_dsetsCache = {}


def lightconeDirs(basePath):
    """List the lightcone directories reachable from basePath."""
    if basePath in _lcDirsCache:
        return _lcDirsCache[basePath]
    if glob.glob(os.path.join(basePath, 'rlc_*')):
        dirs = [basePath]
    elif os.path.isdir(os.path.join(basePath, LC_SUBDIR)):
        dirs = [os.path.join(basePath, LC_SUBDIR)]
    else:
        dirs = sorted(glob.glob(os.path.join(basePath, '*', LC_SUBDIR)))
    if not dirs:
        raise ValueError(f"No {LC_SUBDIR} directories found under {basePath}")
    _lcDirsCache[basePath] = dirs
    return dirs


def listResolutions(basePath):
    """Transverse resolutions (pixels per side) available under basePath."""
    out = set()
    for lcDir in lightconeDirs(basePath):
        for dirPath in glob.glob(os.path.join(lcDir, 'rlc_*')):
            tail = os.path.basename(dirPath)[4:]
            if tail.isdigit():
                out.add(int(tail))
    return sorted(out)


def _resolveRes(basePath, res):
    if res is not None:
        text = str(res)
        if text.startswith('rlc_'):
            text = text[4:]
        return int(text)
    avail = listResolutions(basePath)
    if len(avail) == 1:
        return avail[0]
    raise ValueError("Ambiguous lightcone resolution: %s has %s. Specify res=."
                     % (basePath, avail))


def _segments(basePath, res):
    """Segment table for one resolution, ordered far -> near."""
    key = (tuple(lightconeDirs(basePath)), res)
    if key in _segmentsCache:
        return _segmentsCache[key]
    segs = []
    for lcDir in lightconeDirs(basePath):
        renDir = os.path.join(lcDir, 'rlc_%d' % res)
        allPath = os.path.join(renDir, 'All.hdf5')
        if not os.path.isfile(allPath):
            continue
        with h5py.File(allPath, 'r') as hf:
            segs.append({
                'dir': renDir, 'allPath': allPath,
                'header': dict(hf['Header'].attrs),
                'Redshifts': hf['Redshifts'][()],
                'Distances': hf['Distances'][()],
                'Segments': hf['Segments'][()],
            })
            segs[-1]['n'] = int(segs[-1]['header']['NumDepth'])
    if not segs:
        raise ValueError("No lightcone at res %d under %s (available: %s)"
                         % (res, basePath, listResolutions(basePath)))
    segs.sort(key=lambda seg: -float(seg['Redshifts'][0]))   # far -> near
    off = 0
    for seg in segs:
        seg['offset'] = off
        off += seg['n']
    _segmentsCache[key] = segs
    return segs


def losCoordinates(basePath, res=None):
    """Stitched LOS coordinates of the whole lightcone."""
    res = _resolveRes(basePath, res)
    segs = _segments(basePath, res)
    redshifts = np.concatenate([segs[0]['Redshifts']] +
                               [seg['Redshifts'][1:] for seg in segs[1:]])
    distances = np.concatenate([segs[0]['Distances']] +
                               [seg['Distances'][1:] for seg in segs[1:]])
    segLengths = np.concatenate([seg['Segments'] for seg in segs])
    return {'Redshifts': redshifts, 'Distances': distances,
            'Segments': segLengths, 'NumDepth': len(segLengths)}


def loadHeader(basePath, res=None, datasets=False):
    """Lightcone header, stitched across the epoch segments."""
    res = _resolveRes(basePath, res)
    segs = _segments(basePath, res)
    header = dict(segs[0]['header'])
    header['NumDepth'] = sum(seg['n'] for seg in segs)
    header['SegmentNumDepth'] = np.array([seg['n'] for seg in segs])
    if datasets:
        with h5py.File(segs[0]['allPath'], 'r') as hf:
            for name, dset in hf['Header'].items():
                header[name] = dset[()]
    return header


def _datasetsIn(path):
    if path not in _dsetsCache:
        _dsetsCache[path] = [name for name in _backend.list_datasets(path)
                             if name not in ('Header', 'Redshifts', 'Distances',
                                             'Segments')]
    return _dsetsCache[path]


def listFields(basePath, res=None):
    """List lightcone field names available at this resolution."""
    res = _resolveRes(basePath, res)
    fields = set()
    for seg in _segments(basePath, res):
        for path in glob.glob(os.path.join(seg['dir'], '*.hdf5')):
            name = os.path.basename(path)[:-5]
            if name == 'All':
                fields.update(_datasetsIn(path))
            else:
                fields.add(name)
    return sorted(fields)


def _fieldFile(seg, field):
    """(filePath, datasetName) of a field within one segment, or (None, None)."""
    path = os.path.join(seg['dir'], field + '.hdf5')
    if os.path.isfile(path):
        dsets = _datasetsIn(path)
        if field in dsets:
            return path, field
        if len(dsets) == 1:
            return path, dsets[0]
    if field in _datasetsIn(seg['allPath']):
        return seg['allPath'], field
    return None, None


def losIndexRange(basePath, res=None, zRange=None, dRange=None):
    """Global LOS cell index range (i0, i1) overlapping a z or distance cut."""
    coords = losCoordinates(basePath, res)
    edges, (lo, hi) = ((coords['Redshifts'], sorted(zRange)) if zRange is not None
                       else (coords['Distances'], sorted(dRange)))
    idx = np.flatnonzero((edges[:-1] > lo) & (edges[1:] < hi))
    if len(idx) == 0:
        raise ValueError("No lightcone cells in range [%g, %g]; the lightcone "
                         "covers [%g, %g]" % (lo, hi, edges[-1], edges[0]))
    return int(idx[0]), int(idx[-1]) + 1


def _cgsFactor(attrs, zEdges, h):
    """code -> physical cgs factor for a LOS cut, scalar or per-LOS-cell."""
    if not attrs or 'to_cgs' not in attrs:
        return 1.0
    factor = float(attrs['to_cgs']) or 1.0
    factor *= float(h) ** float(attrs.get('h_scaling', 0.0))
    aexp = float(attrs.get('a_scaling', 0.0))
    if aexp == 0.0:
        return factor
    aCell = 1.0 / (1.0 + 0.5 * (zEdges[:-1] + zEdges[1:]))   # cell-center scale factor
    return factor * aCell ** aexp


def loadLightcone(basePath, fields=None, res=None, region=None, zRange=None,
                  dRange=None, losRange=None, units='code', sq=True, nthreads=0):
    """Load lightcone fields, optionally cut transversely and along the LOS."""
    if units not in ('code', 'cgs'):
        raise ValueError("lightcone units must be 'code' (as stored) or 'cgs' (physical cgs)")
    if sum(rng is not None for rng in (zRange, dRange, losRange)) > 1:
        raise ValueError("Give at most one of zRange, dRange, losRange")
    res = _resolveRes(basePath, res)
    segs = _segments(basePath, res)
    coords = losCoordinates(basePath, res)
    npix = int(segs[0]['header']['NumPixels'])
    nlosTotal = coords['NumDepth']

    singleField = isinstance(fields, str)
    if singleField:
        fields = [fields]
    if fields is None:
        fields = listFields(basePath, res)

    if losRange is not None:
        i0, i1 = int(losRange[0]), int(losRange[1])
        if not (0 <= i0 < i1 <= nlosTotal):
            raise ValueError("losRange (%d, %d) outside [0, %d)" % (i0, i1, nlosTotal))
    elif zRange is not None or dRange is not None:
        i0, i1 = losIndexRange(basePath, res, zRange=zRange, dRange=dRange)
    else:
        i0, i1 = 0, nlosTotal

    if region is not None:
        (x0, x1), (y0, y1) = region
        x0, x1 = max(0, int(x0)), min(npix, int(x1))
        y0, y1 = max(0, int(y0)), min(npix, int(y1))
        if x1 <= x0 or y1 <= y0:
            raise ValueError("Empty transverse region after clamping to [0, %d)" % npix)
    else:
        x0, x1, y0, y1 = 0, npix, 0, npix

    result = {'losRange': (i0, i1), 'pixelRegion': ((x0, x1), (y0, y1)),
              'Redshifts': coords['Redshifts'][i0:i1 + 1],
              'Distances': coords['Distances'][i0:i1 + 1],
              'Segments': coords['Segments'][i0:i1]}

    h = float(segs[0]['header']['HubbleParam'])
    for field in fields:
        parts = []
        for seg in segs:
            s0 = max(i0, seg['offset'])
            s1 = min(i1, seg['offset'] + seg['n'])
            if s1 <= s0:
                continue
            path, dset = _fieldFile(seg, field)
            if path is None:
                raise ValueError("Lightcone field [%s] missing from %s at res "
                                 "%d; have %s" % (field, seg['dir'], res,
                                                  listFields(basePath, res)))
            parts.append(_backend.read_box(
                path, dset,
                [x0, y0, s0 - seg['offset']], [x1 - x0, y1 - y0, s1 - s0],
                nthreads))
        arr = parts[0] if len(parts) == 1 else np.concatenate(parts, axis=2)
        if units == 'cgs':
            attrs = _backend.read_attrs(segs[0]['allPath'], field)
            factor = _cgsFactor(attrs, result['Redshifts'], h)
            if not np.isscalar(factor):
                factor = factor.reshape((1, 1, -1) + (1,) * (arr.ndim - 3))
            if np.ndim(factor) or factor != 1.0:
                arr = arr.astype(np.float64) * factor
        result[field] = arr

    if sq and singleField:
        return result[fields[0]]
    return result


def iterLightcone(basePath, fields=None, res=None, chunkSize=128, units='code',
                  nthreads=0, prefetch=True):
    """Iterate over the stitched lightcone in memory-bounded LOS slabs."""
    res = _resolveRes(basePath, res)
    if isinstance(fields, str):
        fields = [fields]
    nlos = losCoordinates(basePath, res)['NumDepth']

    def loadFn(slabStart, slabCount):
        return loadLightcone(basePath, fields, res=res,
                             losRange=(slabStart, slabStart + slabCount),
                             units=units, sq=False, nthreads=nthreads)

    yield from _backend.iter_chunks(loadFn, 0, nlos, chunkSize, prefetch)
