# lumina_io

Fast data loading for the [LUMINA](https://lumina-simulation.com/)
radiation-hydrodynamic simulations of reionization: group catalogs,
particle snapshots, 3D grids, lightcones, black holes, projections,
power spectra, and the DM-only companion runs, with built-in unit
conversion. A parallel C++ HDF5 core makes the big reads fast; without
it everything still works through `h5py`.

## Install

```bash
pip install .        # needs Python >= 3.8, numpy, h5py
```

To get the fast C++ reader, build it **before** the install so it gets
packaged (needs `pybind11`, a C++17 compiler, and a static HDF5):

```bash
pip install '.[core]'
HDF5_PREFIX=/path/to/hdf5 ./build.sh    # or leave unset to try `module load hdf5`
pip install .
```

`pip` never compiles anything itself -- it just copies an already-built
`lumina_io/_core*.so`. The fallback is silent, so check
`lumina_io.HAVE_CORE` if you expect the fast path.

## Quick start

```python
import lumina_io as lumina

base = '/orcd/data/mvogelsb/005/Lumina/Lumina_above_z_4p75'

halos = lumina.groupcat.loadHalos(base, 116, ['GroupPos', 'GroupMass'])
stars = lumina.snapshot.loadHalo(base, 116, id=42, partType='stars')
batch = lumina.snapshot.loadHalos(base, 116, ids, 'gas', 'Density')  # many halos, one read
gas   = lumina.snapshot.loadHalo(base, 116, 42, 'gas',
                                 ['Temperature', 'Masses'],          # derived on the fly
                                 units='physical')

root = '/orcd/data/mvogelsb/005/Lumina'
rho = lumina.grid.loadGrid(root, 600, 'Density', res=640)
cut = lumina.lightcone.loadLightcone(root, 'Density', res=2560, zRange=(6.0, 6.05))
tr  = lumina.bh.trackMainProgenitor(root, bhID, ['BH_Mass'])
img = lumina.projections.loadProjection(root, 100, 'Density', depth=2)
ps  = lumina.powerspectra.loadPowerSpectrum(root, 116)
sub = lumina.dmo.loadSubhalo('1500', 298, 17, fields='Coordinates')
```

Every loader takes `units='code' | 'comoving' | 'physical'` (grids and
lightcones: `'code' | 'cgs'`). Huge datasets have chunked, prefetching
iterators (`iterSubset`, `iterGrid`, `iterLightcone`, `iterHalos`).
`basePath` can be the Lumina root, an epoch directory, or the data-product
directory itself -- the layout is resolved automatically, including the
above/below z=4.75 epoch split.

## Learn more

- **Tutorial notebook** with output and figures:
  [`examples/tutorial.ipynb`](examples/tutorial.ipynb) -- walks the whole
  API from discovery to the low-level core.
- **API reference**: <https://rongrong00.github.io/lumina_io/>, or browse
  [docs/markdown](docs/markdown/index.md) right on GitHub. Function
  signatures, per-module layout notes, and everything the loaders accept
  live there.

## What each module reads

| module | data product |
|---|---|
| `lumina.groupcat` | FoF group and subhalo catalogs |
| `lumina.snapshot` | particle data: subsets, single or batched halos/subhalos |
| `lumina.grid` | 3D cartesian grids, 5^3 ... 2560^3, periodic regions |
| `lumina.lightcone` | the stitched z = 30 -> 3 lightcone, cut by z/distance/pixels |
| `lumina.bh` | high-cadence BH outputs, tracking, merger trees |
| `lumina.projections` | 2D maps per snapshot, 2/4/8%-of-box slab depths |
| `lumina.powerspectra` | Gadget4 power spectra, Fourier folds merged |
| `lumina.dmo` | the DM-only Gadget4 companion runs |
| `lumina.units`, `lumina.derived`, `lumina.util` | unit conversion, derived fields, discovery |

## Units

Code units follow the [data release](https://lumina-simulation.com/data-access):
ckpc/h, 1e10 Msun/h, km/s sqrt(a). The `units=` keyword converts every
documented field; dimensionless and already-physical fields pass through
unchanged. Velocity conventions differ per field and are handled for you
(particle `Velocities` scale with sqrt(a), `GroupVel` with 1/a,
`SubhaloVel` is already peculiar km/s) -- all conversions verified against
member-particle recomputation and physical identities on the real data.
Grids, lightcones, projections and DM-only fields instead carry `to_cgs`
attributes on disk, applied by `units='cgs'`.

Derived gas/star fields (`Temperature`, `ElectronAbundance`, `SoundSpeed`,
`NeutralHydrogenFraction`, `StellarAge`, ...) can be requested in any
snapshot loader like on-disk fields; the raw inputs are read automatically.

## Notes

- Build `./build.sh` inside the environment you will import from; the
  extension links HDF5 statically, so it needs no modules at runtime.
  Threads: `lumina.set_num_threads(n)` or `LUMINA_NTHREADS` (default
  min(cores, 16)).
- On MIT ORCD (Engaging):
  `module load community-modules` then
  `HDF5_PREFIX=/orcd/software/community/001/spack/pkg/hdf5/1.14.2/apvvdzl ./build.sh`.
- Group/subhalo particle offsets live inside the catalog
  (`GroupOffsetType` / `SubhaloOffsetType`), not in
  `postprocessing/offsets` as in TNG.

## Citation

If you use LUMINA data or this package, please cite the Lumina reference
paper, [arXiv:2605.15310](https://arxiv.org/abs/2605.15310):

```bibtex
@article{Zier2026,
  title         = {Introducing the Lumina project: large-volume
                   radiation-hydrodynamic simulations of the epochs of
                   hydrogen and helium reionization},
  author        = {Zier, Oliver and Smith, Aaron and Shen, Xuejian and
                   Liu, Rongrong and Kannan, Rahul and Koehler, Sonja M. and
                   Springel, Volker and Pakmor, R{\"u}diger and
                   Vogelsberger, Mark and Bulichi, Teodora-Elena and
                   Hernquist, Lars},
  journal       = {arXiv e-prints},
  year          = {2026},
  eprint        = {2605.15310},
  archivePrefix = {arXiv},
  primaryClass  = {astro-ph.CO},
  doi           = {10.48550/arXiv.2605.15310}
}
```
