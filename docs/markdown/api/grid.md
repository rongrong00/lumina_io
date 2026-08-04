# lumina_io.grid

3D cartesian grid loading (the LUMINA 3d_cartesian_grid data product).

Layout (one tree per epoch, e.g. `<root>`/Lumina_below_z_4p75):

> 3d_cartesian_grid/ren_`<N>`/`<Field>`/`<Field>`_NNN.hdf5
> : one field per file, dataset named after the field, plus a Header
>   group (BoxSize, NumPixels, Redshift, Time, cosmology). Most are
>   chunked/uncompressed; some are blosc2-compressed (handled via the
>   hdf5plugin package).

> 3d_cartesian_grid/ren_`<N>`/All/All_NNN.hdf5
> : all fields of the snapshot in one file; each dataset carries unit
>   attributes (to_cgs, a_scaling, h_scaling, …) which drive the
>   units=’cgs’ conversion below.

Grids are NumPixels^3 cells (axes x, y, z; cell size BoxSize/NumPixels, in
ckpc/h), float32. Vector fields (Velocities, IonFlux, IonEnergies) carry a
trailing component axis.

basePath may be the grid directory itself, an epoch directory containing
3d_cartesian_grid, or the root holding several epoch trees (e.g.
/orcd/data/mvogelsb/005/Lumina, where snaps 0-428 live in Lumina_above_z_4p75
and 429-708 in Lumina_below_z_4p75); the epoch is resolved per snapshot. Example:

```default
import lumina_io as lumina
base = '/orcd/data/mvogelsb/005/Lumina'

rho = lumina.grid.loadGrid(base, 600, 'Density', res=640)
d   = lumina.grid.loadGrid(base, 600, ['Density', 'Temperature'], res=640)

# sub-volume around a position (code units, periodic wrap handled);
# region may also be ((i0,i1), (j0,j1), (k0,k1)) in pixel indices
cut = lumina.grid.loadGrid(base, 600, 'Temperature', res=2560,
                           region={'center': pos, 'size': 5000.})

# memory-bounded loop over a 2560^3 field (67 GB) in x-slabs
for chunk in lumina.grid.iterGrid(base, 600, 'Density', res=2560):
    process(chunk['Density'])      # chunk['start'] = first x-plane

# physical cgs units (float64; factor = to_cgs * a^a_scaling * h^h_scaling)
rho = lumina.grid.loadGrid(base, 600, 'Density', res=640, units='cgs')
```

## Functions

| [`gridDirs`](#lumina_io.grid.gridDirs)(basePath)                                    | List the 3d_cartesian_grid directories reachable from basePath.                                                                                             |
|-----------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`listResolutions`](#lumina_io.grid.listResolutions)(basePath)                      | Grid resolutions (cells per side) available under basePath.                                                                                                 |
| [`fieldPath`](#lumina_io.grid.fieldPath)(basePath, snapNum, field[, res])           | Locate the file holding a grid field; returns (filePath, datasetName).                                                                                      |
| [`listFields`](#lumina_io.grid.listFields)(basePath, snapNum[, res])                | List grid field names available at this snapshot/resolution.                                                                                                |
| [`listSnaps`](#lumina_io.grid.listSnaps)(basePath[, res, field])                    | List snapshot numbers for which grid files exist.                                                                                                           |
| [`loadHeader`](#lumina_io.grid.loadHeader)(basePath, snapNum[, res, datasets])      | Grid header (BoxSize, NumPixels, Redshift, Time, cosmology) for one snapshot/resolution.                                                                    |
| [`fieldUnitAttrs`](#lumina_io.grid.fieldUnitAttrs)(basePath, snapNum, field[, res]) | Unit scaling attributes of a grid field (to_cgs, a_scaling, h_scaling, length/mass/velocity_scaling), read from the All file -- per-field files carry none. |
| [`loadGrid`](#lumina_io.grid.loadGrid)(basePath, snapNum[, fields, res, ...])       | Load 3D cartesian grid fields of one snapshot.                                                                                                              |
| [`iterGrid`](#lumina_io.grid.iterGrid)(basePath, snapNum[, fields, res, ...])       | Iterate over a grid in memory-bounded slabs of chunkSize x-planes.                                                                                          |

## Reference

### lumina_io.grid.gridDirs(basePath)

List the 3d_cartesian_grid directories reachable from basePath.

basePath may be a grid directory itself (contains ren_\*), a directory
containing 3d_cartesian_grid, or a root whose subdirectories do (the
epoch trees hold disjoint snapshot ranges, so all are searched).

### lumina_io.grid.listResolutions(basePath)

Grid resolutions (cells per side) available under basePath.

### lumina_io.grid.fieldPath(basePath, snapNum, field, res=None)

Locate the file holding a grid field; returns (filePath, datasetName).

Prefers the per-field file (chunked, fast path); falls back to files of
other naming (z_reion_V_50.hdf5 lives in z_reion/) and to the combined
All file. Returns (None, None) if the field cannot be found.

### lumina_io.grid.listFields(basePath, snapNum, res=None)

List grid field names available at this snapshot/resolution.

### lumina_io.grid.listSnaps(basePath, res=None, field=None)

List snapshot numbers for which grid files exist. (For z_reion the
‘snapshot’ numbers are reionization percentiles: 1, 10, 50, 90, 99.)

### lumina_io.grid.loadHeader(basePath, snapNum, res=None, datasets=False)

Grid header (BoxSize, NumPixels, Redshift, Time, cosmology) for one
snapshot/resolution. With datasets=True the datasets stored inside the
All file’s Header group (Center, FrequencyRanges, LumNorm,
MeanPhotonEnergy, …) are included as arrays.

### lumina_io.grid.fieldUnitAttrs(basePath, snapNum, field, res=None)

Unit scaling attributes of a grid field (to_cgs, a_scaling, h_scaling,
length/mass/velocity_scaling), read from the All file – per-field files
carry none. Returns None for fields without attributes (e.g. z_reion).

### lumina_io.grid.loadGrid(basePath, snapNum, fields=None, res=None, region=None, units='code', sq=True, nthreads=0)

Load 3D cartesian grid fields of one snapshot.

fields: field name, list of names, or None for every available field
: (mind the memory: one 2560^3 scalar field is 67 GB).

res:    cells per side (e.g. 640); may be omitted if only one resolution
: exists under basePath.

region: load only a sub-volume – ((i0,i1),(j0,j1),(k0,k1)) pixel ranges
: or {‘center’: (x,y,z), ‘size’: s} in code units; periodic wrap
  is handled. Only the file chunks intersecting the region are
  read.

units:  ‘code’ (as stored) or ‘cgs’ (physical cgs via the to_cgs /
: a_scaling / h_scaling attrs; returned as float64).

sq:     if True and a single field name was given, return the bare array.

Returns array shape (nx, ny, nz) (+ component axis for vector fields),
axes ordered x, y, z. The dict form includes ‘pixelRegion’, the pixel
ranges actually loaded.

### lumina_io.grid.iterGrid(basePath, snapNum, fields=None, res=None, chunkSize=64, units='code', nthreads=0, prefetch=True)

Iterate over a grid in memory-bounded slabs of chunkSize x-planes.

Yields dicts of the requested fields plus ‘start’ (first x-plane of the
slab); arrays have shape (<=chunkSize, npix, npix, …). With
prefetch=True the next slab loads in the background (two slabs in memory
at a time). One 2560^2 plane is 26 MB/field, so the default chunkSize=64
holds ~1.7 GB per field per slab.
