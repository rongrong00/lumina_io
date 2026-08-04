# lumina_io.util

Path resolution and naming conventions for the LUMINA on-disk layout.

Layout (one directory per snapshot-set, e.g. `<run>`/output_subfind):

> snap_NNN.hdf5                       header stub + virtual datasets (may be absent)
> fof_subhalo_tab_NNN.hdf5            catalog header stub + virtual datasets
> PartType0/`<Field>`_NNN.hdf5          one field per file, dataset named `<Field>`
> PartType4/PartType4_NNN.hdf5        all fields of the type in one file
> Group/`<Field>`/`<Field>`_NNN.hdf5      catalog fields, incl. GroupOffsetType
> Subhalo/`<Field>`/`<Field>`_NNN.hdf5    catalog fields, incl. SubhaloOffsetType

The repackaged /orcd 005 trees split the same layout into two sibling
subdirectories – snapshots/ (snap stubs + PartType\*) and group_files/
(fof_subhalo_tab stubs + Group/Subhalo). basePath may be the epoch directory
(e.g. `<root>`/Lumina_above_z_4p75); both subdirs are searched transparently.

## Functions

| [`partTypeNum`](#lumina_io.util.partTypeNum)(partType)                   | Mapping between common names and particle type numbers.                                                                                                                         |
|------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`resolveBasePath`](#lumina_io.util.resolveBasePath)(basePath)           | Return the snapshot-set directory given either the run directory or the output directory itself (which may be a split snapshots/group_files epoch directory of the 005 layout). |
| [`searchDirs`](#lumina_io.util.searchDirs)(basePath)                     | Directories that may hold kind subdirs / stub files: the resolved base itself, plus the snapshots/ and group_files/ subdirs of the split 005 layout when present.               |
| [`snapPath`](#lumina_io.util.snapPath)(basePath, snapNum)                | Path to the snapshot header stub file (may not exist for all snaps).                                                                                                            |
| [`gcPath`](#lumina_io.util.gcPath)(basePath, snapNum)                    | Path to the group catalog header stub file.                                                                                                                                     |
| [`fieldPath`](#lumina_io.util.fieldPath)(basePath, kind, field, snapNum) | Locate the file holding field and return (filePath, datasetName).                                                                                                               |
| [`listFields`](#lumina_io.util.listFields)(basePath, kind, snapNum)      | List field names available for kind at this snapshot.                                                                                                                           |
| [`boxSize`](#lumina_io.util.boxSize)(basePath[, snapNum])                | BoxSize in code units, read from any available header stub (the box size is constant across snapshots, so any stub will do).                                                    |
| [`listSnaps`](#lumina_io.util.listSnaps)(basePath[, kind])               | List snapshot numbers for which field files exist.                                                                                                                              |

## Reference

### lumina_io.util.partTypeNum(partType)

Mapping between common names and particle type numbers.

### lumina_io.util.resolveBasePath(basePath)

Return the snapshot-set directory given either the run directory or
the output directory itself (which may be a split snapshots/group_files
epoch directory of the 005 layout).

### lumina_io.util.searchDirs(basePath)

Directories that may hold kind subdirs / stub files: the resolved base
itself, plus the snapshots/ and group_files/ subdirs of the split 005
layout when present.

### lumina_io.util.snapPath(basePath, snapNum)

Path to the snapshot header stub file (may not exist for all snaps).

### lumina_io.util.gcPath(basePath, snapNum)

Path to the group catalog header stub file.

### lumina_io.util.fieldPath(basePath, kind, field, snapNum)

Locate the file holding field and return (filePath, datasetName).

kind: ‘Group’, ‘Subhalo’, or ‘PartTypeN’.
Returns (None, None) if the field cannot be found.

### lumina_io.util.listFields(basePath, kind, snapNum)

List field names available for kind at this snapshot.

### lumina_io.util.boxSize(basePath, snapNum=None)

BoxSize in code units, read from any available header stub (the box
size is constant across snapshots, so any stub will do).

### lumina_io.util.listSnaps(basePath, kind=None)

List snapshot numbers for which field files exist.
