"""Snapshot (particle) loading: subsets, single and batched halos/subhalos."""

import os
import numpy as np

from . import util, _backend, units as _units, derived as _derived


def loadHeader(basePath, snapNum):
    """Load the snapshot header."""
    stub = util.snapPath(basePath, snapNum)
    if os.path.isfile(stub):
        return _backend.read_attrs(stub, 'Header')
    header = {'_synthesized': True, 'NumPart_Total': np.zeros(6, dtype=np.uint64)}
    for pt in range(6):
        npart = _numPartFromFields(basePath, snapNum, pt)
        if npart is not None:
            header['NumPart_Total'][pt] = npart
    return header


def getNumPart(header):
    """Calculate number of particles of all types given a snapshot header."""
    return np.array(header['NumPart_Total'], dtype=np.int64)


def _numPartFromFields(basePath, snapNum, ptNum):
    kind = 'PartType%d' % ptNum
    fields = util.listFields(basePath, kind, snapNum)
    if not fields:
        return None
    path, dset = util.fieldPath(basePath, kind, fields[0], snapNum)
    return _backend.dataset_info(path, dset)['shape'][0]


def _resolveField(basePath, kind, field, snapNum):
    """Locate a particle field, handling the Coordinates alias."""
    path, dset = util.fieldPath(basePath, kind, field, snapNum)
    if path is not None:
        return path, dset, False
    if field == 'Coordinates':
        path, dset = util.fieldPath(basePath, kind, 'IntCoordinates', snapNum)
        if path is not None:
            return path, dset, True
    avail = util.listFields(basePath, kind, snapNum)
    if 'IntCoordinates' in avail:
        avail = avail + ['Coordinates (from IntCoordinates)']
    raise ValueError("No field [%s] for %s at snapshot %d; it has %s"
                     % (field, kind, snapNum, avail))


def _postprocess(arr, basePath, snapNum, field, convert, mdiIndex, float32,
                 units='code', nthreads=0):
    if mdiIndex is not None:
        if arr.ndim != 2:
            raise ValueError("mdi requested for a non-2D field")
        arr = np.ascontiguousarray(arr[:, mdiIndex])
    if convert:
        arr = _backend.convert_int_coords(arr, util.boxSize(basePath, snapNum), nthreads)
    if units != 'code':
        arr = _units.convert(arr, field, basePath, snapNum, target=units)
    if float32 and arr.dtype == np.float64:
        arr = arr.astype(np.float32)
    return arr


def _normalizeFields(basePath, kind, fields, snapNum, mdi):
    singleField = isinstance(fields, str)
    if singleField:
        fields = [fields]
    if fields is None:
        fields = util.listFields(basePath, kind, snapNum)
        if not fields:
            raise ValueError("No fields found for %s at snapshot %d" % (kind, snapNum))
    if mdi is not None and len(mdi) != len(fields):
        raise ValueError("mdi must have one entry per field")
    return fields, singleField


def _assembleResult(basePath, snapNum, kind, fields, readFields, derivedNames,
                    rawDict, convertDict, mdi, float32, units, nthreads=0):
    """Build the output dict for the requested `fields` from raw arrays."""
    result = {}
    for idx, field in enumerate(fields):
        mdiIndex = mdi[idx] if mdi is not None else None
        if field in derivedNames:
            if mdiIndex is not None:
                raise ValueError("mdi is not supported for derived field [%s]" % field)
            arr = _derived.compute(field, rawDict, basePath, snapNum)
            if float32 and arr.dtype == np.float64:
                arr = arr.astype(np.float32)
            result[field] = arr
        else:
            result[field] = _postprocess(rawDict[field], basePath, snapNum, field,
                                         convertDict[field], mdiIndex, float32,
                                         units, nthreads)
    return result


def loadSubset(basePath, snapNum, partType, fields=None, subset=None,
               mdi=None, sq=True, float32=False, units='code', nthreads=0):
    """Load a subset of one particle type."""
    ptNum = util.partTypeNum(partType)
    kind = 'PartType%d' % ptNum
    fields, singleField = _normalizeFields(basePath, kind, fields, snapNum, mdi)

    start, count = 0, -1
    if subset is not None:
        start, count = int(subset['start']), int(subset['count'])

    readFields, derivedNames = _derived.expandFields(
        fields, util.listFields(basePath, kind, snapNum))

    rawDict, convertDict = {}, {}
    if count == 0:
        for field in readFields:
            path, dset, convert = _resolveField(basePath, kind, field, snapNum)
            info = _backend.dataset_info(path, dset)
            rawDict[field] = np.empty((0,) + tuple(info['shape'][1:]),
                                      dtype=np.dtype(info['dtype']))
            convertDict[field] = convert
        result = {'count': 0}
    else:
        jobs = []
        for field in readFields:
            path, dset, convert = _resolveField(basePath, kind, field, snapNum)
            jobs.append((path, dset, start, count))
            convertDict[field] = convert
        arrays = _backend.read_many(jobs, nthreads_per_read=nthreads)
        rawDict = dict(zip(readFields, arrays))
        result = {'count': len(arrays[0]) if arrays else 0}

    result.update(_assembleResult(basePath, snapNum, kind, fields, readFields,
                                  derivedNames, rawDict, convertDict, mdi,
                                  float32, units, nthreads))

    if sq and singleField:
        return result[fields[0]]
    return result


def iterSubset(basePath, snapNum, partType, fields=None, chunkSize=50_000_000,
               subset=None, mdi=None, float32=False, units='code', nthreads=0,
               prefetch=True):
    """Iterate over a particle type in memory-bounded chunks."""
    ptNum = util.partTypeNum(partType)
    if isinstance(fields, str):
        fields = [fields]
    if subset is not None:
        start, count = int(subset['start']), int(subset['count'])
    else:
        start = 0
        count = _numPartFromFields(basePath, snapNum, ptNum)
        if count is None:
            raise ValueError("No fields found for PartType%d at snapshot %d"
                             % (ptNum, snapNum))

    def loadFn(chunkStart, chunkCount):
        return loadSubset(basePath, snapNum, partType, fields,
                          subset={'start': chunkStart, 'count': chunkCount},
                          mdi=mdi, sq=False, float32=float32, units=units,
                          nthreads=nthreads)

    yield from _backend.iter_chunks(loadFn, start, count, chunkSize, prefetch)


def getSnapOffsets(basePath, snapNum, id, type):
    """Per-type start row and length of one group or subhalo's particles."""
    if type not in ('Group', 'Subhalo'):
        raise ValueError("type must be 'Group' or 'Subhalo'")
    offPath, offDset = util.fieldPath(basePath, type, type + 'OffsetType', snapNum)
    lenPath, lenDset = util.fieldPath(basePath, type, type + 'LenType', snapNum)
    if offPath is None or lenPath is None:
        raise ValueError("%sOffsetType/%sLenType not found for snap %d under %s"
                         % (type, type, snapNum, basePath))
    ids = np.atleast_1d(np.asarray(id, dtype=np.int64))
    ones = np.ones_like(ids)
    offsetsType = _backend.read_multi(offPath, offDset, ids, ones).astype(np.int64)
    lenType = _backend.read_multi(lenPath, lenDset, ids, ones).astype(np.int64)
    if np.isscalar(id) or np.ndim(id) == 0:
        return {'offsetType': offsetsType[0], 'lenType': lenType[0]}
    return {'offsetType': offsetsType, 'lenType': lenType}


def _loadObjects(basePath, snapNum, ids, partType, fields, objType,
                 mdi=None, sq=True, float32=False, units='code', nthreads=0):
    """Batched particle loading for many groups/subhalos in few I/O passes."""
    ptNum = util.partTypeNum(partType)
    kind = 'PartType%d' % ptNum
    fields, singleField = _normalizeFields(basePath, kind, fields, snapNum, mdi)

    offsets = getSnapOffsets(basePath, snapNum, np.atleast_1d(np.asarray(ids)), objType)
    starts = offsets['offsetType'][:, ptNum]
    counts = offsets['lenType'][:, ptNum]

    readFields, derivedNames = _derived.expandFields(
        fields, util.listFields(basePath, kind, snapNum))

    rawDict, convertDict = {}, {}
    for field in readFields:
        path, dset, convert = _resolveField(basePath, kind, field, snapNum)
        rawDict[field] = _backend.read_multi(path, dset, starts, counts, nthreads)
        convertDict[field] = convert

    result = {'count': int(counts.sum()), 'lens': counts.copy()}
    result.update(_assembleResult(basePath, snapNum, kind, fields, readFields,
                                  derivedNames, rawDict, convertDict, mdi,
                                  float32, units, nthreads))

    if sq and singleField:
        return result[fields[0]]
    return result


def loadHalo(basePath, snapNum, id, partType, fields=None, **kwargs):
    """Load all particles of one type belonging to a FoF halo."""
    subset = getSnapOffsets(basePath, snapNum, id, 'Group')
    ptNum = util.partTypeNum(partType)
    sub = {'start': subset['offsetType'][ptNum], 'count': subset['lenType'][ptNum]}
    return loadSubset(basePath, snapNum, partType, fields, subset=sub, **kwargs)


def loadSubhalo(basePath, snapNum, id, partType, fields=None, **kwargs):
    """Load all particles of one type belonging to a subhalo."""
    subset = getSnapOffsets(basePath, snapNum, id, 'Subhalo')
    ptNum = util.partTypeNum(partType)
    sub = {'start': subset['offsetType'][ptNum], 'count': subset['lenType'][ptNum]}
    return loadSubset(basePath, snapNum, partType, fields, subset=sub, **kwargs)


def loadHalos(basePath, snapNum, ids, partType, fields=None, **kwargs):
    """Load particles of one type for MANY FoF halos in a few parallel reads."""
    return _loadObjects(basePath, snapNum, ids, partType, fields, 'Group', **kwargs)


def loadSubhalos(basePath, snapNum, ids, partType, fields=None, **kwargs):
    """Load particles of one type for MANY subhalos in a few parallel reads."""
    return _loadObjects(basePath, snapNum, ids, partType, fields, 'Subhalo', **kwargs)
