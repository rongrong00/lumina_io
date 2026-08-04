"""Benchmark lumina_io._core vs h5py on the real 500cMpc data.

Each measurement reads a distinct, previously untouched slice of the 850 GB
PartType0/Density dataset so the OS page cache cannot serve any request.
Sized to stay well under the 32 GB per-user memory limit on login nodes.

Run:  python benchmarks/bench.py
"""

import os
import sys
import time
import numpy as np
import h5py

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lumina_io import _core, util, groupcat

BASE = os.environ.get('LUMINA_TEST_BASE',
                      '/orcd/data/mvogelsb/005/Lumina/Lumina_above_z_4p75')
SNAP = 116
DENS, DENS_DSET = util.fieldPath(BASE, 'PartType0', 'Density', SNAP)

GB = 1e9
SLICE_ROWS = 500_000_000     # 2 GB of float32 per measurement
ntotal = _core.dataset_info(DENS, DENS_DSET)['shape'][0]

slice_idx = [0]
def fresh_slice():
    i = slice_idx[0]
    slice_idx[0] += 1
    # Start deep into the file: the first bytes of a large file can sit on
    # differently-striped storage than the bulk, so measure in the bulk.
    start = 40_000_000_000 + i * SLICE_ROWS
    assert start + SLICE_ROWS <= ntotal
    return start, SLICE_ROWS


def bench(label, fn):
    start, count = fresh_slice()
    t0 = time.time()
    a = fn(start, count)
    dt = time.time() - t0
    print('  %-28s %7.2f s   %6.2f GB/s' % (label, dt, a.nbytes / GB / dt))
    del a


def read_h5py(start, count):
    with h5py.File(DENS, 'r') as f:
        return f[DENS_DSET][start:start + count]


print('== 2 GB cold slices of PartType0/Density (%d total rows) ==' % ntotal)
bench('h5py', read_h5py)
for nt in (1, 4, 8, 16, 32):
    bench('_core %2d threads' % nt, lambda s, c, nt=nt: _core.read(DENS, DENS_DSET, s, c, nt))
bench('h5py (again)', read_h5py)

print('== full group catalog fields in one call ==')
fields = ['GroupPos', 'GroupMass', 'GroupVel', 'Group_M_Crit200']
t0 = time.time()
halos = groupcat.loadHalos(BASE, SNAP, fields)
dt = time.time() - t0
nb = sum(halos[f].nbytes for f in fields)
print('  lumina loadHalos             %7.2f s   %6.2f GB/s  (%.1f GB)' % (dt, nb / GB / dt, nb / GB))

t0 = time.time()
ok = True
for f in fields:
    p, d = util.fieldPath(BASE, 'Group', f, SNAP)
    with h5py.File(p, 'r') as hf:
        ref = hf[d][:]
    ok = ok and np.array_equal(halos[f], ref)
    del ref
dt = time.time() - t0
print('  h5py field loop              %7.2f s   %6.2f GB/s' % (dt, nb / GB / dt))
print('  results identical:', ok)
