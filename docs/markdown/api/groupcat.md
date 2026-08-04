# lumina_io.groupcat

Group (FoF halo) and subhalo catalog loading.

## Functions

| [`loadHalos`](#lumina_io.groupcat.loadHalos)(basePath, snapNum[, fields, units])       | Load all FoF groups for one snapshot.                                     |
|--------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| [`loadSubhalos`](#lumina_io.groupcat.loadSubhalos)(basePath, snapNum[, fields, units]) | Load all subhalos for one snapshot.                                       |
| [`iterHalos`](#lumina_io.groupcat.iterHalos)(basePath, snapNum[, fields, ...])         | Iterate over the FoF group catalog in memory-bounded chunks.              |
| [`iterSubhalos`](#lumina_io.groupcat.iterSubhalos)(basePath, snapNum[, fields, ...])   | Iterate over the subhalo catalog in memory-bounded chunks; see iterHalos. |
| [`loadHeader`](#lumina_io.groupcat.loadHeader)(basePath, snapNum)                      | Load the group catalog header.                                            |
| [`load`](#lumina_io.groupcat.load)(basePath, snapNum)                                  | Load complete group catalog: halos, subhalos, and header.                 |
| [`loadSingle`](#lumina_io.groupcat.loadSingle)(basePath, snapNum[, haloID, ...])       | Load complete catalog information for one halo or subhalo.                |

## Reference

### lumina_io.groupcat.loadHalos(basePath, snapNum, fields=None, units='code')

Load all FoF groups for one snapshot. fields=None loads everything;
a single field name returns the bare array.
units: ‘code’ (as stored), ‘comoving’ (h factors removed), or ‘physical’.

### lumina_io.groupcat.loadSubhalos(basePath, snapNum, fields=None, units='code')

Load all subhalos for one snapshot.

### lumina_io.groupcat.iterHalos(basePath, snapNum, fields=None, chunkSize=5000000, units='code', prefetch=True)

Iterate over the FoF group catalog in memory-bounded chunks. Yields
dicts of the requested fields plus ‘count’ (rows in this chunk) and
‘start’ (global row offset). With prefetch=True the next chunk loads in
the background (two chunks in memory at a time).

### lumina_io.groupcat.iterSubhalos(basePath, snapNum, fields=None, chunkSize=5000000, units='code', prefetch=True)

Iterate over the subhalo catalog in memory-bounded chunks; see iterHalos.

### lumina_io.groupcat.loadHeader(basePath, snapNum)

Load the group catalog header. Falls back to a synthesized header if
the fof_subhalo_tab stub file is absent for this snapshot.

### lumina_io.groupcat.load(basePath, snapNum)

Load complete group catalog: halos, subhalos, and header.

### lumina_io.groupcat.loadSingle(basePath, snapNum, haloID=-1, subhaloID=-1, units='code')

Load complete catalog information for one halo or subhalo.
