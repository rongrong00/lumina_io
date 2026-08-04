# lumina_io.projections

2D projection-map loading (the LUMINA projections data product).

Layout (one tree per epoch, e.g. `<root>`/Lumina_above_z_4p75):

> projections/projections`<DDD>`/projections_NNN.hdf5
> : one file per snapshot NNN, holding several 2D maps (NumPixelsX x
>   NumPixelsY, float32) as top-level datasets – Density, Temperature,
>   the ionization fractions, etc. – plus a Header group with the
>   projection geometry (BoxSize, Width, Height, Depth, Center,
>   cosmology) and a few small datasets (Center, FrequencyRanges,
>   LumNorm, MeanPhotonEnergy). Map datasets carry the same unit
>   attributes as the grids (to_cgs, a_scaling, h_scaling, …).

The `<DDD>` suffix is the projection depth in units of BoxSize/100, i.e.
projections002 integrates through a 2%-of-box slab, 004 through 4%, 008
through 8% (Depth = DDD/100 \* BoxSize, in ckpc/h). All depths share the
NumPixelsX x NumPixelsY face resolution (4096^2 for the 500cMpc run).

Maps are snapshot-indexed exactly like the snapshots/grids: snaps 0-428 live
in Lumina_above_z_4p75, 429-708 in Lumina_below_z_4p75, and basePath may be
the projections directory itself, an epoch directory, or the root holding the
epoch trees – the epoch is resolved per snapshot. Example:

```default
import lumina_io as lumina
base = '/orcd/data/mvogelsb/005/Lumina'

rho = lumina.projections.loadProjection(base, 100, 'Density')          # depth=2
d   = lumina.projections.loadProjection(base, 100,
                                        ['Density', 'Temperature'], depth=8)

# physical cgs units (float64; factor = to_cgs * a^a_scaling * h^h_scaling)
rho = lumina.projections.loadProjection(base, 100, 'Density', units='cgs')

# sub-image: ((i0,i1),(j0,j1)) pixel ranges (periodic wrap handled)
cut = lumina.projections.loadProjection(base, 100, 'Temperature',
                                        region=((0, 512), (0, 512)))
```

## Functions

| [`projDirs`](#lumina_io.projections.projDirs)(basePath)                                      | List the projections directories reachable from basePath.                                                 |
|--------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| [`listDepths`](#lumina_io.projections.listDepths)(basePath)                                  | Projection depths available under basePath (the `<DDD>` directory suffixes, e.g. [2, 4, 8]).                |
| [`filePath`](#lumina_io.projections.filePath)(basePath, snapNum[, depth])                    | Path to the projection file for one snapshot/depth, or None.                                              |
| [`listFields`](#lumina_io.projections.listFields)(basePath, snapNum[, depth])                | Map field names available in a snapshot's projection file.                                                |
| [`listSnaps`](#lumina_io.projections.listSnaps)(basePath[, depth])                           | Snapshot numbers for which projection files exist (at the given depth, or any depth).                     |
| [`loadHeader`](#lumina_io.projections.loadHeader)(basePath, snapNum[, depth, datasets])      | Projection header (BoxSize, Width, Height, Depth, Redshift, Time, cosmology) for one snapshot/depth.      |
| [`fieldUnitAttrs`](#lumina_io.projections.fieldUnitAttrs)(basePath, snapNum, field[, depth]) | Unit scaling attributes of a projection map (to_cgs, a_scaling, h_scaling, length/mass/velocity_scaling). |
| [`loadProjection`](#lumina_io.projections.loadProjection)(basePath, snapNum[, fields, ...])  | Load 2D projection maps of one snapshot.                                                                  |

## Reference

### lumina_io.projections.projDirs(basePath)

List the projections directories reachable from basePath.

basePath may be a projections directory itself (contains
projections`<DDD>`), an epoch directory containing projections, or a root
whose subdirectories do (the epoch trees hold disjoint snapshot ranges,
so all are searched).

### lumina_io.projections.listDepths(basePath)

Projection depths available under basePath (the `<DDD>` directory
suffixes, e.g. [2, 4, 8]).

### lumina_io.projections.filePath(basePath, snapNum, depth=None)

Path to the projection file for one snapshot/depth, or None.

### lumina_io.projections.listFields(basePath, snapNum, depth=None)

Map field names available in a snapshot’s projection file.

### lumina_io.projections.listSnaps(basePath, depth=None)

Snapshot numbers for which projection files exist (at the given depth,
or any depth).

### lumina_io.projections.loadHeader(basePath, snapNum, depth=None, datasets=False)

Projection header (BoxSize, Width, Height, Depth, Redshift, Time,
cosmology) for one snapshot/depth. With datasets=True the small datasets
inside the Header group (Center, FrequencyRanges, LumNorm,
MeanPhotonEnergy, …) are included as arrays.

### lumina_io.projections.fieldUnitAttrs(basePath, snapNum, field, depth=None)

Unit scaling attributes of a projection map (to_cgs, a_scaling,
h_scaling, length/mass/velocity_scaling). Returns None if absent.

### lumina_io.projections.loadProjection(basePath, snapNum, fields=None, depth=None, region=None, units='code', sq=True, nthreads=0)

Load 2D projection maps of one snapshot.

fields: map name, list of names, or None for every map in the file
: (one 4096^2 float32 map is 67 MB).

depth:  projection slab depth as the `<DDD>` suffix (2, 4, or 8 -> 2/4/8 %
: of the box); may be omitted if only one depth exists (else
  defaults to the thinnest, 2).

region: load only a sub-image – ((i0,i1),(j0,j1)) half-open pixel ranges;
: periodic wrap is handled and only the intersecting file chunks are
  read.

units:  ‘code’ (as stored) or ‘cgs’ (physical cgs via the to_cgs /
: a_scaling / h_scaling attrs; returned as float64).

sq:     if True and a single field name was given, return the bare array.

Returns a (NumPixelsX, NumPixelsY) array per field (a sub-shape when
region is given). The dict form includes ‘pixelRegion’, the pixel ranges
actually loaded.
