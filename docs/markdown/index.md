# lumina_io

Fast data loading for LUMINA simulations: a Python API on top of a
parallel C++ HDF5 reader, written for the LUMINA on-disk layout
(field-per-file datasets, offsets inside the group catalog, the repackaged
005 data products).

```python
import lumina_io as lumina

basePath = '/orcd/data/mvogelsb/005/Lumina/Lumina_above_z_4p75'
halos = lumina.groupcat.loadHalos(basePath, 116, ['GroupPos', 'GroupMass'])
stars = lumina.snapshot.loadHalo(basePath, 116, id=42, partType='stars')

root = '/orcd/data/mvogelsb/005/Lumina'
rho  = lumina.grid.loadGrid(root, 600, 'Density', res=640)
cut  = lumina.lightcone.loadLightcone(root, 'Density', res=2560,
                                      zRange=(6.0, 6.05))
tr   = lumina.bh.trackMainProgenitor(root, bhID, ['BH_Mass'])
img  = lumina.projections.loadProjection(root, 100, 'Density', depth=2)
ps   = lumina.powerspectra.loadPowerSpectrum(root, 100)
sub  = lumina.dmo.loadSubhalo('1500', 298, 17, fields='Coordinates')
```

Every loader accepts `units='code' | 'comoving' | 'physical'` (grids and
lightcones: `'code' | 'cgs'`). A complete walkthrough with figures is in
`examples/tutorial.ipynb`; build and layout notes are in the README.

# API reference

* [lumina_io.groupcat](api/groupcat.md)
  * [Functions](api/groupcat.md#functions)
  * [Reference](api/groupcat.md#reference)
* [lumina_io.snapshot](api/snapshot.md)
  * [Functions](api/snapshot.md#functions)
  * [Reference](api/snapshot.md#reference)
* [lumina_io.grid](api/grid.md)
  * [Functions](api/grid.md#functions)
  * [Reference](api/grid.md#reference)
* [lumina_io.lightcone](api/lightcone.md)
  * [Functions](api/lightcone.md#functions)
  * [Reference](api/lightcone.md#reference)
* [lumina_io.bh](api/bh.md)
  * [Functions](api/bh.md#functions)
  * [Reference](api/bh.md#reference)
* [lumina_io.projections](api/projections.md)
  * [Functions](api/projections.md#functions)
  * [Reference](api/projections.md#reference)
* [lumina_io.powerspectra](api/powerspectra.md)
  * [Functions](api/powerspectra.md#functions)
  * [Reference](api/powerspectra.md#reference)
* [lumina_io.dmo](api/dmo.md)
  * [Functions](api/dmo.md#functions)
  * [Reference](api/dmo.md#reference)
* [lumina_io.units](api/units.md)
  * [Functions](api/units.md#functions)
  * [Reference](api/units.md#reference)
* [lumina_io.derived](api/derived.md)
  * [Functions](api/derived.md#functions)
  * [Reference](api/derived.md#reference)
* [lumina_io.util](api/util.md)
  * [Functions](api/util.md#functions)
  * [Reference](api/util.md#reference)

## Index

* [Index](genindex.md)
* [Search Page](search.md)
