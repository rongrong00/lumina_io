# lumina_io.bh

Black hole outputs (the Lumina_combined_outputs data products).

BH_frequent_output/bh_snapNNNN.hdf5
: High-cadence outputs of the FULL black hole population (group ‘BH’:
  BH_Mass, BH_Mdot, …, Coordinates, Velocities, ParticleIDs). The
  counter (0307..1216, z = 14.3 -> 3.0) is the frequent-output counter,
  NOT the simulation snapshot number. Header: BoxSize, Redshift, Time.
  Datasets are gzip-compressed.

BH_merger_tree/full_merger_tree.hdf5

```default
'mergers'      one row per merger event between consecutive frequent
               outputs (remnant_id, snap_from/to, mass_before/after,
               consistency flags); victim_ids / victim_masses /
               victim_dists are ragged per-event lists.
'bh_lifetimes' first_snap / last_snap of every BH that ever existed.
'indices'      remnant_id -> merger rows, victim_id -> merger row.
```

BH_merger_tree/mergers_NNNN.hdf5
: The per-interval merger tables (empty file when no mergers).

basePath may be the Lumina root, Lumina_combined_outputs, or either
subdirectory. Example:

```default
import lumina_io as lumina
base = '/orcd/data/mvogelsb/005/Lumina'

bhs = lumina.bh.loadSnap(base, 1216, ['BH_Mass', 'BH_Mdot'])
hdr = lumina.bh.loadHeader(base, 1216)            # Time, Redshift

# time series of individual BHs across the frequent outputs (the file
# range is pruned with the bh_lifetimes table when available)
tr = lumina.bh.trackBH(base, bhID, ['BH_Mass', 'BH_CumMassGrowth_RM'])
plt.plot(tr['Redshift'], tr['BH_Mass'])

tree = lumina.bh.loadMergerTree(base)             # full catalog, ~43 MB
ev   = lumina.bh.findMergers(base, bhID)          # this BH's mergers
```

Units: the frequent outputs store the standard LUMINA code units, and the
fields carry the same names as PartType5 snapshot fields, so the
units=’comoving’ / ‘physical’ conversions of lumina_io.units apply (the
scale factor is taken per output time; trackBH applies a per-output factor
along the time axis). HubbleParam is not stored in these files – it is
located from a grid/lightcone header in the same tree, or pass h= explicitly.
Merger-tree masses are code masses (1e10 Msun/h).

## Functions

| [`bhDirs`](#lumina_io.bh.bhDirs)(basePath)                                              | Locate the BH output directories: dict with 'frequent' and 'tree' paths (either may be None).                                                                                                                                                                                  |
|---------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`snapPath`](#lumina_io.bh.snapPath)(basePath, snapNum)                                 | Path to one frequent-output file.                                                                                                                                                                                                                                              |
| [`listSnaps`](#lumina_io.bh.listSnaps)(basePath)                                        | Frequent-output numbers available (the high-cadence counter, not the simulation snapshot number).                                                                                                                                                                              |
| [`loadHeader`](#lumina_io.bh.loadHeader)(basePath, snapNum)                             | Header of one frequent output (BoxSize, Redshift, Time).                                                                                                                                                                                                                       |
| [`listFields`](#lumina_io.bh.listFields)(basePath[, snapNum])                           | BH field names in the frequent outputs.                                                                                                                                                                                                                                        |
| [`hubbleParam`](#lumina_io.bh.hubbleParam)(basePath[, h])                               | HubbleParam for unit conversions.                                                                                                                                                                                                                                              |
| [`loadSnap`](#lumina_io.bh.loadSnap)(basePath, snapNum[, fields, units, ...])           | Load the full BH population of one frequent output.                                                                                                                                                                                                                            |
| [`loadLifetimes`](#lumina_io.bh.loadLifetimes)(basePath[, ids])                         | The bh_lifetimes table: first/last frequent output of every BH.                                                                                                                                                                                                                |
| [`trackBH`](#lumina_io.bh.trackBH)(basePath, ids[, fields, snapRange, ...])             | Time series of individual black holes across the frequent outputs.                                                                                                                                                                                                             |
| [`loadMergerTree`](#lumina_io.bh.loadMergerTree)(basePath[, groups])                    | The full merger catalog (BH_merger_tree/full_merger_tree.hdf5) as nested dicts.                                                                                                                                                                                                |
| [`loadMergers`](#lumina_io.bh.loadMergers)(basePath, snapNum)                           | Mergers of one frequent-output interval (mergers_NNNN.hdf5 holds the events between outputs NNNN-1 and NNNN).                                                                                                                                                                  |
| [`findMergers`](#lumina_io.bh.findMergers)(basePath, id)                                | All merger events involving one BH.                                                                                                                                                                                                                                            |
| [`mainProgenitorChain`](#lumina_io.bh.mainProgenitorChain)(basePath, id)                | The main-progenitor ID chain of one BH, walking the merger catalog backwards in time.                                                                                                                                                                                          |
| [`trackMainProgenitor`](#lumina_io.bh.trackMainProgenitor)(basePath, id[, fields, ...]) | Like trackBH for a single BH, but stitched along the main progenitor branch: the time series follows mainProgenitorChain across the mergers where the surviving ParticleID was the lighter partner's, so the mass history is that of the growing object rather than of one ID. |

## Reference

### lumina_io.bh.bhDirs(basePath)

Locate the BH output directories: dict with ‘frequent’ and ‘tree’
paths (either may be None). basePath may be the Lumina root,
Lumina_combined_outputs, or one of the two subdirectories.

### lumina_io.bh.snapPath(basePath, snapNum)

Path to one frequent-output file.

### lumina_io.bh.listSnaps(basePath)

Frequent-output numbers available (the high-cadence counter, not the
simulation snapshot number).

### lumina_io.bh.loadHeader(basePath, snapNum)

Header of one frequent output (BoxSize, Redshift, Time).

### lumina_io.bh.listFields(basePath, snapNum=None)

BH field names in the frequent outputs.

### lumina_io.bh.hubbleParam(basePath, h=None)

HubbleParam for unit conversions. The frequent outputs do not store
it, so it is read from a grid or lightcone header in the same Lumina
tree; pass h= to override (raises if neither is possible).

### lumina_io.bh.loadSnap(basePath, snapNum, fields=None, units='code', h=None, sq=True, nthreads=0)

Load the full BH population of one frequent output.

fields: field name, list, or None for all. units: ‘code’ | ‘comoving’ |
‘physical’ (see lumina_io.units; the scale factor is this output’s
Header Time). With a single field name and sq=True the bare array is
returned; the dict form includes ‘count’, ‘Time’ and ‘Redshift’.

### lumina_io.bh.loadLifetimes(basePath, ids=None)

The bh_lifetimes table: first/last frequent output of every BH.
With ids given (scalar or array), returns ‘first_snap’/’last_snap’
aligned to ids (-1 where the ID never existed).

### lumina_io.bh.trackBH(basePath, ids, fields=None, snapRange=None, units='code', h=None, sq=True, nthreads=0, prefetch=True, verbose=False)

Time series of individual black holes across the frequent outputs.

ids: one ParticleID or a list. fields: name, list, or None for all.
snapRange: (lo, hi) inclusive frequent-output window; additionally the
window is pruned with the bh_lifetimes table when the merger tree is
present (so tracking a short-lived BH does not scan all ~900 files).
units: ‘code’ | ‘comoving’ | ‘physical’ – a-dependent conversions use
each output’s own scale factor. prefetch=True warms upcoming files into
the page cache with parallel raw reads (hides Lustre latency; the HDF5
reads themselves are serialized by a global lock).

Returns a dict with ‘snaps’, ‘Time’, ‘Redshift’ (per retained output),
‘found’ (whether the BH exists in that output), and one array per field
of shape (nsnaps, …) for a single id or (nsnaps, nids, …) for a
list. Outputs where a BH is absent hold NaN (float fields) or -1
(integer fields). With a single id AND a single field name (sq=True),
only the bare time-series array is returned.

### lumina_io.bh.loadMergerTree(basePath, groups=('mergers', 'bh_lifetimes', 'indices'))

The full merger catalog (BH_merger_tree/full_merger_tree.hdf5) as
nested dicts. Ragged columns (victim_ids, victim_masses, victim_dists,
remnant_merger_idxs) come back as object arrays of per-event arrays.
Masses are code units (1e10 Msun/h).

### lumina_io.bh.loadMergers(basePath, snapNum)

Mergers of one frequent-output interval (mergers_NNNN.hdf5 holds the
events between outputs NNNN-1 and NNNN). Returns the table columns plus
‘count’ (0 with no events; the file may then have no datasets at all).

### lumina_io.bh.findMergers(basePath, id)

All merger events involving one BH.

Returns {‘asRemnant’: dict of mergers-table columns for the events this
BH survived (possibly empty), ‘asVictim’: the single event in which it
was consumed, or None}. Uses the precomputed indices of the tree file.

### lumina_io.bh.mainProgenitorChain(basePath, id)

The main-progenitor ID chain of one BH, walking the merger catalog
backwards in time.

At a BH-BH merger the surviving ParticleID can be the LIGHTER partner’s
(in this catalog it usually is: every top-mass BH at the final output
carries a late-seeded ID that jumped by a factor 100-3000 in one event),
so tracking one ID does not follow the physically growing object.
Wherever the remnant’s pre-merger mass is below the most massive
victim’s, the main branch continues backwards on that victim’s ID.

Returns [(id, firstSnap, lastSnap), …] ordered early -> late with
contiguous, non-overlapping frequent-output windows.

### lumina_io.bh.trackMainProgenitor(basePath, id, fields=None, units='code', h=None, nthreads=0, prefetch=True, verbose=False)

Like trackBH for a single BH, but stitched along the main progenitor
branch: the time series follows mainProgenitorChain across the mergers
where the surviving ParticleID was the lighter partner’s, so the mass
history is that of the growing object rather than of one ID.

Returns the trackBH dict (single-id form) plus ‘ids’ (the ParticleID
tracked at each output) and ‘chain’.
