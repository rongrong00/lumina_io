# lumina_io.snapshot

Snapshot (particle) loading: subsets, single and batched halos/subhalos.

In the LUMINA layout each field is one logical dataset over the whole
snapshot, and group/subhalo particle offsets are stored in the group catalog
itself (Group/GroupOffsetType, Subhalo/SubhaloOffsetType) rather than in
postprocessing/offsets.

Field aliases: requesting ‘Coordinates’ transparently reads the on-disk
‘IntCoordinates’ (uint32) and converts to float64 box units
(BoxSize \* i / 2^32) when no ‘Coordinates’ dataset exists.

## Functions

| [`loadHeader`](#lumina_io.snapshot.loadHeader)(basePath, snapNum)                    | Load the snapshot header.                                                                                        |
|------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| [`getNumPart`](#lumina_io.snapshot.getNumPart)(header)                               | Calculate number of particles of all types given a snapshot header.                                              |
| [`loadSubset`](#lumina_io.snapshot.loadSubset)(basePath, snapNum, partType[, ...])   | Load a subset of one particle type.                                                                              |
| [`iterSubset`](#lumina_io.snapshot.iterSubset)(basePath, snapNum, partType[, ...])   | Iterate over a particle type in memory-bounded chunks.                                                           |
| [`getSnapOffsets`](#lumina_io.snapshot.getSnapOffsets)(basePath, snapNum, id, type)  | Compute offsets within the snapshot for a particular group/subgroup.                                             |
| [`loadHalo`](#lumina_io.snapshot.loadHalo)(basePath, snapNum, id, partType[, ...])   | Load all particles of one type belonging to a FoF halo.                                                          |
| [`loadSubhalo`](#lumina_io.snapshot.loadSubhalo)(basePath, snapNum, id, partType)    | Load all particles of one type belonging to a subhalo.                                                           |
| [`loadHalos`](#lumina_io.snapshot.loadHalos)(basePath, snapNum, ids, partType)       | Load particles of one type for MANY FoF halos in a few large parallel reads (much faster than looping loadHalo). |
| [`loadSubhalos`](#lumina_io.snapshot.loadSubhalos)(basePath, snapNum, ids, partType) | Load particles of one type for MANY subhalos in a few large parallel reads.                                      |

## Reference

### lumina_io.snapshot.loadHeader(basePath, snapNum)

Load the snapshot header. Falls back to a synthesized header (with
NumPart_Total from dataset shapes) if the snap stub is absent.

### lumina_io.snapshot.getNumPart(header)

Calculate number of particles of all types given a snapshot header.

### lumina_io.snapshot.loadSubset(basePath, snapNum, partType, fields=None, subset=None, mdi=None, sq=True, float32=False, units='code', nthreads=0)

Load a subset of one particle type.

subset: dict with ‘start’ and ‘count’ (rows along the snapshot-global
: particle axis), e.g. as returned by getSnapOffsets(); None loads
  the full snapshot for this type.

mdi: list of multi-dimensional indices, one per field (None entries
: load the full field); `fields=['Coordinates'], mdi=[1]` loads
  the y-coordinate only.

sq: if True and a single field is requested, return the bare array.

float32: convert float64 fields to float32 on return.

units: ‘code’ (as stored), ‘comoving’ (h/1e10 factors removed), or
: ‘physical’ (scale-factor factors applied as well; velocities
  become peculiar km/s). See lumina_io.units.

### lumina_io.snapshot.iterSubset(basePath, snapNum, partType, fields=None, chunkSize=50000000, subset=None, mdi=None, float32=False, units='code', nthreads=0, prefetch=True)

Iterate over a particle type in memory-bounded chunks.

Yields dicts like loadSubset(sq=False) – requested fields plus ‘count’
(rows in this chunk) and ‘start’ (global row offset of the chunk) – for
consecutive chunkSize-row windows covering the whole snapshot (or the
given subset). With prefetch=True (default) the next chunk is read in
the background while you process the current one, so up to two chunks
are in memory at a time. Example:

```default
for chunk in lumina.snapshot.iterSubset(base, 116, 'gas',
                                        ['Coordinates', 'Masses'],
                                        chunkSize=50_000_000):
    process(chunk['Coordinates'], chunk['Masses'])
```

### lumina_io.snapshot.getSnapOffsets(basePath, snapNum, id, type)

Compute offsets within the snapshot for a particular group/subgroup.

Offsets are read from the new location inside the catalog output:
Group/GroupOffsetType and Subhalo/SubhaloOffsetType. id may be a scalar
or an array of IDs (then offsetType/lenType have shape (len(id), 6)).

### lumina_io.snapshot.loadHalo(basePath, snapNum, id, partType, fields=None, \*\*kwargs)

Load all particles of one type belonging to a FoF halo.

### lumina_io.snapshot.loadSubhalo(basePath, snapNum, id, partType, fields=None, \*\*kwargs)

Load all particles of one type belonging to a subhalo.

### lumina_io.snapshot.loadHalos(basePath, snapNum, ids, partType, fields=None, \*\*kwargs)

Load particles of one type for MANY FoF halos in a few large parallel
reads (much faster than looping loadHalo).

Returns a dict with the requested fields concatenated in the order of
ids, plus ‘count’ (total particles) and ‘lens’ (particles per halo).
Split per halo with: np.split(arr, np.cumsum(result[‘lens’])[:-1]).
With a single field name and sq=True (default) only the bare concatenated
array is returned.

### lumina_io.snapshot.loadSubhalos(basePath, snapNum, ids, partType, fields=None, \*\*kwargs)

Load particles of one type for MANY subhalos in a few large parallel
reads. See loadHalos for the return convention.
