lumina_io.util
==============

.. currentmodule:: lumina_io.util

.. automodule:: lumina_io.util
   :no-members:

On-disk layout
--------------

One directory per snapshot-set, e.g. ``<run>/output_subfind`` ::

    snap_NNN.hdf5                       header stub + virtual datasets (may be absent)
    fof_subhalo_tab_NNN.hdf5            catalog header stub + virtual datasets
    PartType0/<Field>_NNN.hdf5          one field per file, dataset named <Field>
    PartType4/PartType4_NNN.hdf5        all fields of the type in one file
    Group/<Field>/<Field>_NNN.hdf5      catalog fields, incl. GroupOffsetType
    Subhalo/<Field>/<Field>_NNN.hdf5    catalog fields, incl. SubhaloOffsetType

The repackaged /orcd 005 trees split the same layout into two sibling
subdirectories -- ``snapshots/`` (snap stubs + ``PartType*``) and
``group_files/`` (``fof_subhalo_tab`` stubs + ``Group``/``Subhalo``).
``basePath`` may be the epoch directory (e.g.
``<root>/Lumina_above_z_4p75``); both subdirectories are searched
transparently.

Functions
---------

.. autosummary::

   partTypeNum
   resolveBasePath
   searchDirs
   snapPath
   gcPath
   fieldPath
   listFields
   boxSize
   listSnaps

Reference
---------

.. autofunction:: partTypeNum

.. autofunction:: resolveBasePath

   Accepts either the run directory or the output directory itself, which may
   be a split ``snapshots/`` + ``group_files/`` epoch directory of the 005
   layout.

.. autofunction:: searchDirs

   The resolved base itself, plus the ``snapshots/`` and ``group_files/``
   subdirectories of the split 005 layout when present.

.. autofunction:: snapPath

.. autofunction:: gcPath

.. autofunction:: fieldPath

   ``kind`` is ``'Group'``, ``'Subhalo'``, or ``'PartTypeN'``. Returns
   ``(None, None)`` if the field cannot be found.

.. autofunction:: listFields

.. autofunction:: boxSize

   The box size is constant across snapshots, so any stub will do.

.. autofunction:: listSnaps
