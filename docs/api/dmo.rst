lumina_io.dmo
=============

.. currentmodule:: lumina_io.dmo

.. automodule:: lumina_io.dmo
   :no-members:

Layout
------

These are standard **Gadget4** outputs -- a different on-disk layout from the
main Arepo run (see :mod:`lumina_io.snapshot` and
:mod:`lumina_io.groupcat`): multi-file snapshots with ``PartTypeN`` groups
inside each file, and Subfind ``fof_subhalo_tab`` catalogs ::

    <run>/output/snapdir_NNN/snapshot_NNN.<f>.hdf5                (full snapshot)
    <run>/output/snapdir_NNN/snapshot-prevmostboundonly_NNN.<f>.hdf5
    <run>/output/groups_NNN/fof_subhalo_tab_NNN.<f>.hdf5          (group catalog)

Two runs ship with the data. Pass the run by short name and the path is
filled in (``'1500'`` -> ``DM_only_1500``, a 1500^3 box; ``'3000'`` ->
``DM_only_3000``), or pass an explicit run / output directory.

Example
-------

.. code-block:: python

    import lumina_io as lumina
    lumina.dmo.RUNS                       # {'1500': '/orcd/.../DM_only_1500', ...}

    hdr  = lumina.dmo.loadHeader('1500', 298)
    # all DM particles of subhalo 17 (uses SubhaloOffsetType from the catalog)
    pos  = lumina.dmo.loadSubhalo('1500', 298, 17, fields='Coordinates')
    # the Subfind group table
    grp  = lumina.dmo.loadGroups('1500', 298, ['GroupPos', 'Group_M_Crit200'])
    sub  = lumina.dmo.loadSubhalos('1500', 298, ['SubhaloPos', 'SubhaloMass'])

Notes
-----

* Full snapshots are written at only a subset of outputs, while the group
  catalogs exist at every output -- see :func:`listSnaps` vs
  :func:`listGroupSnaps`. Particle loaders need a full snapshot at that
  output.
* ``ParticleIDs`` / ``SubhaloIDMostbound`` are 48-bit integers (the Gadget4
  ``IDS_48BIT`` option); they are read through HDF5's type conversion and
  returned as uint64. ``Velocities`` / ``Acceleration`` are stored
  half-precision (float16).
* DM particles carry no per-particle mass; use :func:`particleMass` (Header
  ``MassTable``). Particle fields support ``units='cgs'``; catalog datasets
  carry no unit attributes and are returned in code units.

Functions
---------

.. autosummary::

   runPath
   outputDir
   listSnaps
   listGroupSnaps
   loadHeader
   groupHeader
   partTypeNum
   particleMass
   listFields
   loadSubset
   loadGroups
   loadSubhalos
   loadSingle
   getSnapOffsets
   loadHalo
   loadSubhalo

Reference
---------

.. autofunction:: runPath

   Accepts a short name (``'1500'``, ``1500``, ``'3000'``), the
   ``'DM_only_NNNN'`` directory name, or an explicit path to the run or its
   output directory.

.. autofunction:: outputDir

.. autofunction:: listSnaps

.. autofunction:: listGroupSnaps

.. autofunction:: loadHeader

   ``BoxSize``, ``Redshift``, ``Time``, ``MassTable``, ``NumPart_Total``, ...

.. autofunction:: groupHeader

   ``Ngroups_Total``, ``Nsubhalos_Total``, ``NumFiles``, ...

.. autofunction:: partTypeNum

   DM-only runs only populate type 1.

.. autofunction:: particleMass

   DM particles have no ``Masses`` dataset, so the mass comes from the
   header.

.. autofunction:: listFields

.. autofunction:: loadSubset

   ``subset``
       ``{'start', 'count'}`` range on the snapshot-global particle axis of
       this type, as from :func:`getSnapOffsets`. ``None`` loads the whole
       type.

   ``units``
       ``'code'`` or ``'cgs'`` (physical cgs via the field's ``to_cgs`` /
       ``a_scaling`` / ``h_scaling`` attrs; returned float64).

   ``sq``
       Bare array if a single field name was given.

.. autofunction:: loadGroups

   Concatenated across the catalog files. ``fields`` is a name, a list, or
   ``None`` for all. Returns a dict with the fields plus ``'count'``, or a
   bare array for a single field with ``sq``.

.. autofunction:: loadSubhalos

   See :func:`loadGroups` for the return convention.

.. autofunction:: loadSingle

   Reads only the file that holds the row. ``kind`` is ``'Group'`` or
   ``'Subhalo'``.

.. autofunction:: getSnapOffsets

   From the catalog's ``{Group,Subhalo}OffsetType`` / ``LenType``. ``kind``
   is ``'Group'`` or ``'Subhalo'``.

.. autofunction:: loadHalo

   Uses ``GroupOffsetType`` from the catalog; needs a full snapshot at this
   output.

.. autofunction:: loadSubhalo

   Uses ``SubhaloOffsetType`` from the catalog; needs a full snapshot at this
   output.
