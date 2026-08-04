"""Group (FoF halo) and subhalo catalog loading."""

import os

import numpy as np

from . import util, _backend, units as _units


def _loadObjects(basePath, snapNum, kind, fields, start=0, count=-1, units='code'):
    """Load fields of 'Group' or 'Subhalo' as a dict (+ 'count')."""
    singleField = isinstance(fields, str)
    if singleField:
        fields = [fields]
    if fields is None:
        fields = util.listFields(basePath, kind, snapNum)
        if not fields:
            raise ValueError("No %s fields found for snapshot %d under %s"
                             % (kind, snapNum, basePath))

    jobs = []
    for field in fields:
        path, dset = util.fieldPath(basePath, kind, field, snapNum)
        if path is None:
            avail = util.listFields(basePath, kind, snapNum)
            raise ValueError("%s catalog has no [%s] at snapshot %d (fields: %s)"
                             % (kind, field, snapNum, avail))
        jobs.append((path, dset, start, count))

    arrays = _backend.read_many(jobs)
    result = {'count': len(arrays[0]) if arrays else 0}
    for field, arr in zip(fields, arrays):
        if units != 'code':
            arr = _units.convert(arr, field, basePath, snapNum, target=units)
        result[field] = arr

    if singleField:
        return result[fields[0]]
    return result


def loadHalos(basePath, snapNum, fields=None, units='code'):
    """Load all FoF groups for one snapshot."""
    return _loadObjects(basePath, snapNum, 'Group', fields, units=units)


def loadSubhalos(basePath, snapNum, fields=None, units='code'):
    """Load all subhalos for one snapshot."""
    return _loadObjects(basePath, snapNum, 'Subhalo', fields, units=units)


def _numObjects(basePath, snapNum, kind):
    fields = util.listFields(basePath, kind, snapNum)
    if not fields:
        raise ValueError("No %s fields found for snapshot %d" % (kind, snapNum))
    path, dset = util.fieldPath(basePath, kind, fields[0], snapNum)
    return _backend.dataset_info(path, dset)['shape'][0]


def _iterObjects(basePath, snapNum, kind, fields, chunkSize, units, prefetch):
    if isinstance(fields, str):
        fields = [fields]

    def loadFn(start, count):
        return _loadObjects(basePath, snapNum, kind, fields, start=start,
                            count=count, units=units)

    nobj = _numObjects(basePath, snapNum, kind)
    yield from _backend.iter_chunks(loadFn, 0, nobj, chunkSize, prefetch)


def iterHalos(basePath, snapNum, fields=None, chunkSize=5_000_000, units='code',
              prefetch=True):
    """Iterate over the FoF group catalog in memory-bounded chunks."""
    yield from _iterObjects(basePath, snapNum, 'Group', fields, chunkSize, units, prefetch)


def iterSubhalos(basePath, snapNum, fields=None, chunkSize=5_000_000, units='code',
                 prefetch=True):
    """Iterate over the subhalo catalog in memory-bounded chunks; see iterHalos."""
    yield from _iterObjects(basePath, snapNum, 'Subhalo', fields, chunkSize, units, prefetch)


def loadHeader(basePath, snapNum):
    """Load the group catalog header."""
    stub = util.gcPath(basePath, snapNum)
    if os.path.isfile(stub):
        return _backend.read_attrs(stub, 'Header')
    header = {'_synthesized': True}
    for kind, key in (('Group', 'Ngroups_Total'), ('Subhalo', 'Nsubhalos_Total')):
        for probe in ('GroupLenType', 'SubhaloLenType', 'GroupPos', 'SubhaloPos'):
            if not probe.startswith(kind[:3]):
                continue
            path, dset = util.fieldPath(basePath, kind, probe, snapNum)
            if path:
                header[key] = _backend.dataset_info(path, dset)['shape'][0]
                break
    return header


def load(basePath, snapNum):
    """Load complete group catalog: halos, subhalos, and header."""
    return {'halos': loadHalos(basePath, snapNum),
            'subhalos': loadSubhalos(basePath, snapNum),
            'header': loadHeader(basePath, snapNum)}


def loadSingle(basePath, snapNum, haloID=-1, subhaloID=-1, units='code'):
    """Load complete catalog information for one halo or subhalo."""
    if (haloID < 0) == (subhaloID < 0):
        raise ValueError("Must specify exactly one of haloID and subhaloID.")
    kind = 'Subhalo' if subhaloID >= 0 else 'Group'
    objID = subhaloID if subhaloID >= 0 else haloID
    result = _loadObjects(basePath, snapNum, kind, None, start=objID, count=1, units=units)
    del result['count']
    return {name: (val[0] if isinstance(val, np.ndarray) else val)
            for name, val in result.items()}
