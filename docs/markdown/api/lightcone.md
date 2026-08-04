# lumina_io.lightcone

Lightcone loading (the LUMINA lightcone data product).

Layout (one tree per epoch, e.g. `<root>`/Lumina_above_z_4p75):

> lightcone/rlc_`<N>`/`<Field>`.hdf5
> : one field per file, dataset named after the field, shape
>   (NumPixels, NumPixels, NumDepth): transverse x, y pixels of an
>   angular grid (OpeningAngle radians across), line of sight LAST,
>   ordered far -> near (decreasing redshift). Chunked 128^3; some
>   fields blosc2-compressed.

> lightcone/rlc_`<N>`/All.hdf5
> : all fields in one file (contiguous) with unit attrs
>   (to_cgs, a_scaling, h_scaling), the Header, and the LOS coordinate
>   arrays:
>   `<br/>`
>   ```default
>   Redshifts  (NumDepth+1,)  cell edges, decreasing
>   Distances  (NumDepth+1,)  comoving-distance edges, code units
>   Segments   (NumDepth,)    per-cell comoving path length
>   ```

The epoch trees are SEGMENTS of one lightcone (above: z = 30 -> 4.753,
below: z = 4.753 -> 2.99, sharing the boundary edge). Pass the Lumina root
and they are stitched along the LOS into a single global cell index space,
ordered far -> near; an epoch directory or a lightcone directory itself also
works (then only that segment is visible). Example:

```default
import lumina_io as lumina
base = '/orcd/data/mvogelsb/005/Lumina'

# all cells with 6 <= z <= 7, all transverse pixels
cut = lumina.lightcone.loadLightcone(base, 'Density', res=640, zRange=(6, 7))

# dict form returns the LOS coordinates of the cut as well
cut = lumina.lightcone.loadLightcone(base, ['Density', 'Temperature'], res=640,
                                     zRange=(6, 7), region=((0, 64), (0, 64)))
z_edges = cut['Redshifts']           # (nlos+1,) decreasing

# physical cgs: the scale factor varies ALONG the LOS, so a-dependent
# fields get a per-cell factor (broadcast over the LOS axis), float64
rho = lumina.lightcone.loadLightcone(base, 'Density', res=640,
                                     zRange=(6, 6.2), units='cgs')

# memory-bounded loop over the full LOS in slabs (198 GB/field at 2560)
for chunk in lumina.lightcone.iterLightcone(base, 'Density', res=2560):
    process(chunk['Density'], chunk['Redshifts'])
```

## Functions

| [`lightconeDirs`](#lumina_io.lightcone.lightconeDirs)(basePath)                        | List the lightcone directories reachable from basePath (the lightcone dir itself, a directory containing lightcone, or a root whose subdirectories do).                                                                                                    |
|--------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`listResolutions`](#lumina_io.lightcone.listResolutions)(basePath)                    | Transverse resolutions (pixels per side) available under basePath.                                                                                                                                                                                         |
| [`losCoordinates`](#lumina_io.lightcone.losCoordinates)(basePath[, res])               | Stitched LOS coordinates: dict with 'Redshifts' and 'Distances' (NumDepth+1 cell edges, decreasing -- segment-boundary edges are shared), 'Segments' (NumDepth per-cell path lengths, code units), and 'NumDepth'.                                         |
| [`loadHeader`](#lumina_io.lightcone.loadHeader)(basePath[, res, datasets])             | Lightcone header.                                                                                                                                                                                                                                          |
| [`listFields`](#lumina_io.lightcone.listFields)(basePath[, res])                       | List lightcone field names available at this resolution.                                                                                                                                                                                                   |
| [`losIndexRange`](#lumina_io.lightcone.losIndexRange)(basePath[, res, zRange, dRange]) | Global LOS cell index range (i0, i1) of the cells whose interior overlaps a redshift interval zRange=(z1, z2) or comoving-distance interval dRange=(d1, d2) (code units, like the Distances edges); cells only touching an interval endpoint are excluded. |
| [`loadLightcone`](#lumina_io.lightcone.loadLightcone)(basePath[, fields, res, ...])    | Load lightcone fields, optionally cut transversely and along the LOS.                                                                                                                                                                                      |
| [`iterLightcone`](#lumina_io.lightcone.iterLightcone)(basePath[, fields, res, ...])    | Iterate over the (stitched) lightcone in memory-bounded LOS slabs of chunkSize cells, far -> near.                                                                                                                                                         |

## Reference

### lumina_io.lightcone.lightconeDirs(basePath)

List the lightcone directories reachable from basePath (the lightcone
dir itself, a directory containing lightcone, or a root whose
subdirectories do).

### lumina_io.lightcone.listResolutions(basePath)

Transverse resolutions (pixels per side) available under basePath.

### lumina_io.lightcone.losCoordinates(basePath, res=None)

Stitched LOS coordinates: dict with ‘Redshifts’ and ‘Distances’
(NumDepth+1 cell edges, decreasing – segment-boundary edges are shared),
‘Segments’ (NumDepth per-cell path lengths, code units), and ‘NumDepth’.

### lumina_io.lightcone.loadHeader(basePath, res=None, datasets=False)

Lightcone header. For a stitched lightcone the attrs come from the
farthest segment with NumDepth replaced by the stitched total (the
per-segment depths are added as ‘SegmentNumDepth’). With datasets=True
the farthest segment’s Header datasets (Center, FrequencyRanges,
LumNorm, …) are included; per-segment values are available by passing
the epoch directory as basePath.

### lumina_io.lightcone.listFields(basePath, res=None)

List lightcone field names available at this resolution.

### lumina_io.lightcone.losIndexRange(basePath, res=None, zRange=None, dRange=None)

Global LOS cell index range (i0, i1) of the cells whose interior
overlaps a redshift interval zRange=(z1, z2) or comoving-distance
interval dRange=(d1, d2) (code units, like the Distances edges); cells
only touching an interval endpoint are excluded.

### lumina_io.lightcone.loadLightcone(basePath, fields=None, res=None, region=None, zRange=None, dRange=None, losRange=None, units='code', sq=True, nthreads=0)

Load lightcone fields, optionally cut transversely and along the LOS.

fields: field name, list of names, or None for every available field.

res:    transverse pixels per side (e.g. 640); may be omitted if only one
: resolution exists under basePath.

region: transverse cut ((x0,x1), (y0,y1)) in pixels of the angular grid,
: clamped to the field of view (not periodic).

zRange / dRange / losRange: LOS cut – a redshift interval, a comoving
: distance interval (code units), or global cell indices (i0, i1).
  At most one may be given; cells overlapping the interval are
  included, and cuts spanning the epoch boundary read from both
  segment trees and are concatenated.

units:  ‘code’ (as stored) or ‘cgs’ (physical cgs via the stored attrs;
: a-dependent fields get a per-LOS-cell factor; returned float64).

sq:     if True and a single field name was given, return the bare array.

Returns arrays of shape (nx, ny, nlos) (+ component axis for vector
fields), LOS ordered far -> near. The dict form adds ‘losRange’ (global
(i0, i1)), ‘pixelRegion’, and the ‘Redshifts’/’Distances’ edges (nlos+1)
and ‘Segments’ path lengths of the cut.

### lumina_io.lightcone.iterLightcone(basePath, fields=None, res=None, chunkSize=128, units='code', nthreads=0, prefetch=True)

Iterate over the (stitched) lightcone in memory-bounded LOS slabs of
chunkSize cells, far -> near. Yields dicts like loadLightcone(sq=False)
plus ‘start’ (global LOS index of the slab); the per-slab ‘Redshifts’ /
‘Distances’ edges are included. With prefetch=True the next slab loads in
the background. One 2560^2 LOS plane is 26 MB/field.
