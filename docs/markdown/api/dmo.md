# lumina_io.dmo

Dark-matter-only run loading (the LUMINA DM_only_\* products).

These are standard **Gadget4** outputs – a different on-disk layout from the
main Arepo run (see lumina.snapshot/lumina.groupcat): multi-file snapshots
with PartTypeN groups inside each file, and Subfind fof_subhalo_tab
catalogs. Layout:

```default
<run>/output/snapdir_NNN/snapshot_NNN.<f>.hdf5                (full snapshot)
<run>/output/snapdir_NNN/snapshot-prevmostboundonly_NNN.<f>.hdf5
<run>/output/groups_NNN/fof_subhalo_tab_NNN.<f>.hdf5          (group catalog)
```

Two runs ship with the data; pass the run by short name and the path is filled
in (‘1500’ -> DM_only_1500, a 1500^3 box; ‘3000’ -> DM_only_3000), or pass
an explicit run / output directory:

```default
import lumina_io as lumina
lumina.dmo.RUNS                       # {'1500': '/orcd/.../DM_only_1500', ...}

hdr  = lumina.dmo.loadHeader('1500', 298)
# all DM particles of subhalo 17 (uses SubhaloOffsetType from the catalog)
pos  = lumina.dmo.loadSubhalo('1500', 298, 17, fields='Coordinates')
# the Subfind group table
grp  = lumina.dmo.loadGroups('1500', 298, ['GroupPos', 'Group_M_Crit200'])
sub  = lumina.dmo.loadSubhalos('1500', 298, ['SubhaloPos', 'SubhaloMass'])
```

### Notes

* Full snapshots are written at only a subset of outputs (the group catalogs
  exist at every output); listSnaps vs listGroupSnaps. Particle loaders
  need a full snapshot at that output.
* ParticleIDs / SubhaloIDMostbound are 48-bit integers (the Gadget4
  IDS_48BIT option); they are read through HDF5’s type conversion and returned
  as uint64. Velocities/Acceleration are stored half-precision (float16).
* DM particles carry no per-particle mass; use particleMass(run, snap)
  (Header MassTable). Particle fields support units=’cgs’; catalog datasets
  carry no unit attributes and are returned in code units.

## Functions

| [`runPath`](#lumina_io.dmo.runPath)(run)                                         | Resolve a run spec to its run directory.                                                                                                |
|--------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| [`outputDir`](#lumina_io.dmo.outputDir)(run)                                     | The output directory of a run (contains snapdir_\*/ and groups_\*/).                                                                    |
| [`listSnaps`](#lumina_io.dmo.listSnaps)(run[, base])                             | Output numbers that have a (full, by default) snapshot.                                                                                 |
| [`listGroupSnaps`](#lumina_io.dmo.listGroupSnaps)(run)                           | Output numbers that have a Subfind group catalog.                                                                                       |
| [`loadHeader`](#lumina_io.dmo.loadHeader)(run, snapNum[, base])                  | Snapshot Header (BoxSize, Redshift, Time, MassTable, NumPart_Total, ...) plus HubbleParam/Omega\* pulled from the Parameters group.     |
| [`groupHeader`](#lumina_io.dmo.groupHeader)(run, snapNum)                        | fof_subhalo_tab Header (Ngroups_Total, Nsubhalos_Total, NumFiles, ...).                                                                 |
| [`partTypeNum`](#lumina_io.dmo.partTypeNum)(partType)                            | Map 'dm'/'gas'/.                                                                                                                        |
| [`particleMass`](#lumina_io.dmo.particleMass)(run, snapNum[, partType, base])    | Per-particle mass (code units) from Header MassTable -- DM particles have no Masses dataset.                                            |
| [`listFields`](#lumina_io.dmo.listFields)(run, snapNum[, partType, base])        | Particle field names present for a type at this snapshot.                                                                               |
| [`loadSubset`](#lumina_io.dmo.loadSubset)(run, snapNum[, partType, fields, ...]) | Load particle fields of one type, concatenated across the snapshot's files.                                                             |
| [`loadGroups`](#lumina_io.dmo.loadGroups)(run, snapNum[, fields, sq])            | Load FoF group-catalog fields (the Group table), concatenated across the catalog files.                                                 |
| [`loadSubhalos`](#lumina_io.dmo.loadSubhalos)(run, snapNum[, fields, sq])        | Load Subfind subhalo-catalog fields (the Subhalo table).                                                                                |
| [`loadSingle`](#lumina_io.dmo.loadSingle)(run, snapNum, id[, kind, fields])      | Load a single catalog row (one group or subhalo) by id, reading only the file that holds it.                                            |
| [`getSnapOffsets`](#lumina_io.dmo.getSnapOffsets)(run, snapNum, id, kind)        | (start, count) per particle type for a group/subhalo, from the catalog's {Group,Subhalo}OffsetType / LenType.                           |
| [`loadHalo`](#lumina_io.dmo.loadHalo)(run, snapNum, id[, partType, ...])         | Load all particles of one type belonging to FoF halo id (uses GroupOffsetType from the catalog; needs a full snapshot at this output).  |
| [`loadSubhalo`](#lumina_io.dmo.loadSubhalo)(run, snapNum, id[, partType, ...])   | Load all particles of one type belonging to subhalo id (uses SubhaloOffsetType from the catalog; needs a full snapshot at this output). |

## Reference

### lumina_io.dmo.runPath(run)

Resolve a run spec to its run directory. Accepts a short name (‘1500’,
1500, ‘3000’), the ‘DM_only_NNNN’ directory name, or an explicit path to
the run or its output directory.

### lumina_io.dmo.outputDir(run)

The output directory of a run (contains snapdir_\*/ and groups_\*/).

### lumina_io.dmo.listSnaps(run, base='snapshot')

Output numbers that have a (full, by default) snapshot.

### lumina_io.dmo.listGroupSnaps(run)

Output numbers that have a Subfind group catalog.

### lumina_io.dmo.loadHeader(run, snapNum, base='snapshot')

Snapshot Header (BoxSize, Redshift, Time, MassTable, NumPart_Total, …)
plus HubbleParam/Omega\* pulled from the Parameters group.

### lumina_io.dmo.groupHeader(run, snapNum)

fof_subhalo_tab Header (Ngroups_Total, Nsubhalos_Total, NumFiles, …).

### lumina_io.dmo.partTypeNum(partType)

Map ‘dm’/’gas’/… or ‘PartTypeN’/N to an integer particle type (DM-only
runs only populate type 1).

### lumina_io.dmo.particleMass(run, snapNum, partType='dm', base='snapshot')

Per-particle mass (code units) from Header MassTable – DM particles
have no Masses dataset.

### lumina_io.dmo.listFields(run, snapNum, partType='dm', base='snapshot')

Particle field names present for a type at this snapshot.

### lumina_io.dmo.loadSubset(run, snapNum, partType='dm', fields=None, subset=None, base='snapshot', units='code', sq=True)

Load particle fields of one type, concatenated across the snapshot’s
files.

subset: {‘start’, ‘count’} range on the snapshot-global particle axis of
: this type (as from getSnapOffsets); None loads the whole type.

units:  ‘code’ or ‘cgs’ (physical cgs via the field’s to_cgs/a_scaling/
: h_scaling attrs; returned float64).

sq:     bare array if a single field name was given.

### lumina_io.dmo.loadGroups(run, snapNum, fields=None, sq=True)

Load FoF group-catalog fields (the Group table), concatenated across
the catalog files. fields: name, list, or None for all. Returns a dict
with the fields plus ‘count’ (a bare array for a single field with sq).

### lumina_io.dmo.loadSubhalos(run, snapNum, fields=None, sq=True)

Load Subfind subhalo-catalog fields (the Subhalo table). See
loadGroups for the return convention.

### lumina_io.dmo.loadSingle(run, snapNum, id, kind='Subhalo', fields=None)

Load a single catalog row (one group or subhalo) by id, reading only
the file that holds it. kind: ‘Group’ or ‘Subhalo’.

### lumina_io.dmo.getSnapOffsets(run, snapNum, id, kind)

(start, count) per particle type for a group/subhalo, from the
catalog’s {Group,Subhalo}OffsetType / LenType. kind: ‘Group’ or ‘Subhalo’.

### lumina_io.dmo.loadHalo(run, snapNum, id, partType='dm', fields=None, base='snapshot', units='code', sq=True)

Load all particles of one type belonging to FoF halo id (uses
GroupOffsetType from the catalog; needs a full snapshot at this output).

### lumina_io.dmo.loadSubhalo(run, snapNum, id, partType='dm', fields=None, base='snapshot', units='code', sq=True)

Load all particles of one type belonging to subhalo id (uses
SubhaloOffsetType from the catalog; needs a full snapshot at this output).
