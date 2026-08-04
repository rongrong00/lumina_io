"""I/O backend: C++ when available, h5py otherwise."""

import os
from concurrent.futures import ThreadPoolExecutor
from itertools import product

import numpy as np

try:
    import hdf5plugin as _hdf5plugin
    os.environ.setdefault('HDF5_PLUGIN_PATH', _hdf5plugin.PLUGIN_PATH)
except ImportError:
    pass

import h5py

try:
    from . import _core
    HAVE_CORE = True
except ImportError:
    _core = None
    HAVE_CORE = False

def read(path, dataset, start=0, count=-1, nthreads=0):
    """Read a contiguous row range"""
    if HAVE_CORE:
        return _core.read(path, dataset, start, count, nthreads)
    with h5py.File(path, 'r') as hf:
        dset = hf[dataset]
        stop = dset.shape[0] if count < 0 else start + count
        return dset[start:stop]


def read_multi(path, dataset, starts, counts, nthreads=0):
    """Read several row ranges and concatenate them into one array."""
    starts = np.ascontiguousarray(starts, dtype=np.int64)
    counts = np.ascontiguousarray(counts, dtype=np.int64)
    if HAVE_CORE:
        return _core.read_multi(path, dataset, starts, counts, nthreads)
    with h5py.File(path, 'r') as hf:
        dset = hf[dataset]
        parts = [dset[start:start + count]
                 for start, count in zip(starts, counts)]
        if not parts:
            return np.empty((0,) + dset.shape[1:], dtype=dset.dtype)
        return np.concatenate(parts, axis=0)


def read_box(path, dataset, starts, counts, nthreads=0):
    """Read one n-dimensional hyperslab"""
    starts, counts = list(starts), list(counts)
    if HAVE_CORE:
        return _core.read_box(path, dataset, starts, counts, nthreads)
    with h5py.File(path, 'r') as hf:
        dset = hf[dataset]
        slices = tuple(slice(start, (None if count < 0 else start + count))
                       for start, count in zip(starts, counts))
        return dset[slices]


def read_box_runs(path, dataset, runs, nthreads=0):
    """Gather the cartesian product of per-axis (start, count) runs into one array."""
    if all(len(run) == 1 for run in runs):
        starts = [run[0][0] for run in runs]
        counts = [run[0][1] for run in runs]
        info = dataset_info(path, dataset)
        starts += [0] * (len(info['shape']) - len(runs))
        counts += [-1] * (len(info['shape']) - len(runs))
        return read_box(path, dataset, starts, counts, nthreads)
    info = dataset_info(path, dataset)
    shape = tuple(info['shape'])
    trailing = shape[len(runs):]
    outShape = tuple(sum(count for _, count in run) for run in runs) + trailing
    out = np.empty(outShape, dtype=np.dtype(info['dtype']))
    offsets = []
    for run in runs:
        runOffsets, offset = [], 0
        for _, count in run:
            runOffsets.append(offset)
            offset += count
        offsets.append(runOffsets)
    for combo in product(*[range(len(run)) for run in runs]):
        starts = ([runs[dim][idx][0] for dim, idx in enumerate(combo)]
                  + [0] * len(trailing))
        counts = ([runs[dim][idx][1] for dim, idx in enumerate(combo)]
                  + [-1] * len(trailing))
        slices = tuple(slice(offsets[dim][idx], offsets[dim][idx] + counts[dim])
                       for dim, idx in enumerate(combo))
        out[slices] = read_box(path, dataset, starts, counts, nthreads)
    return out


def convert_int_coords(arr, box, nthreads=0):
    """converts unsigned integer coordinates to box units."""
    if HAVE_CORE:
        return _core.convert_int_coords(arr, box, nthreads)
    return arr.astype('f8') * (box / 2.0**32)


def dataset_info(path, dataset):
    """Shape, dtype, layout and chunking of a dataset, without reading it."""
    if HAVE_CORE:
        return _core.dataset_info(path, dataset)
    with h5py.File(path, 'r') as hf:
        dset = hf[dataset]
        return {'shape': dset.shape, 'dtype': dset.dtype.str,
                'layout': 'chunked' if dset.chunks else 'contiguous',
                'nfilters': 0, 'chunks': dset.chunks}


def list_datasets(path, group='/'):
    if HAVE_CORE:
        return _core.list_datasets(path, group)
    with h5py.File(path, 'r') as hf:
        return sorted(hf[group].keys())


def read_attrs(path, obj='Header'):
    """Attributes of obj as a dict, or None if absent; h5py only, the core has no reader."""
    with h5py.File(path, 'r') as hf:
        if obj not in hf:
            return None
        return dict(hf[obj].attrs)


def num_threads():
    if HAVE_CORE:
        return _core.get_num_threads()
    return 1


def iter_chunks(loadFn, start, count, chunkSize, prefetch=True):
    """Yield loadFn(start, count) per chunk, loading the next one in a background thread."""
    if chunkSize <= 0:
        raise ValueError("chunkSize must be positive")
    ranges = [(chunkStart, min(chunkSize, start + count - chunkStart))
              for chunkStart in range(start, start + count, chunkSize)]
    if not ranges:
        return
    if not prefetch:
        for chunkStart, chunkCount in ranges:
            result = loadFn(chunkStart, chunkCount)
            result['start'] = chunkStart
            yield result
        return
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(loadFn, *ranges[0])
        for index, (chunkStart, _) in enumerate(ranges):
            result = future.result()
            if index + 1 < len(ranges):
                future = executor.submit(loadFn, *ranges[index + 1])
            result['start'] = chunkStart
            yield result


def read_many(jobs, nthreads_per_read=0):
    """Read several datasets concurrently"""
    if len(jobs) <= 1 or not HAVE_CORE:
        return [read(*job) for job in jobs]
    nfields = len(jobs)
    threadsPerRead = nthreads_per_read or max(1, num_threads() // min(nfields, 4))
    with ThreadPoolExecutor(max_workers=min(nfields, 8)) as executor:
        futures = [executor.submit(read, path, dataset, start, count, threadsPerRead)
                   for (path, dataset, start, count) in jobs]
        return [future.result() for future in futures]
