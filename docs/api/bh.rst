lumina_io.bh
============

.. currentmodule:: lumina_io.bh

.. automodule:: lumina_io.bh
   :no-members:

Data products
-------------

``BH_frequent_output/bh_snapNNNN.hdf5``
    High-cadence outputs of the FULL black hole population (group ``BH``:
    ``BH_Mass``, ``BH_Mdot``, ..., ``Coordinates``, ``Velocities``,
    ``ParticleIDs``). The counter (0307..1216, z = 14.3 -> 3.0) is the
    frequent-output counter, NOT the simulation snapshot number. Header:
    ``BoxSize``, ``Redshift``, ``Time``. Datasets are gzip-compressed.

``BH_merger_tree/full_merger_tree.hdf5``
    ::

        'mergers'      one row per merger event between consecutive frequent
                       outputs (remnant_id, snap_from/to, mass_before/after,
                       consistency flags); victim_ids / victim_masses /
                       victim_dists are ragged per-event lists.
        'bh_lifetimes' first_snap / last_snap of every BH that ever existed.
        'indices'      remnant_id -> merger rows, victim_id -> merger row.

``BH_merger_tree/mergers_NNNN.hdf5``
    The per-interval merger tables (empty file when no mergers).

``basePath`` may be the Lumina root, ``Lumina_combined_outputs``, or either
subdirectory.

Example
-------

.. code-block:: python

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

Units
-----

The frequent outputs store the standard LUMINA code units, and the fields
carry the same names as PartType5 snapshot fields, so the
``units='comoving'`` / ``'physical'`` conversions of :mod:`lumina_io.units`
apply (the scale factor is taken per output time; :func:`trackBH` applies a
per-output factor along the time axis). ``HubbleParam`` is not stored in these
files -- it is located from a grid/lightcone header in the same tree, or pass
``h=`` explicitly. Merger-tree masses are code masses (1e10 Msun/h).

Functions
---------

.. autosummary::

   bhDirs
   snapPath
   listSnaps
   loadHeader
   listFields
   hubbleParam
   loadSnap
   loadLifetimes
   trackBH
   loadMergerTree
   loadMergers
   findMergers
   mainProgenitorChain
   trackMainProgenitor

Reference
---------

.. autofunction:: bhDirs

   Either entry may be ``None``. ``basePath`` may be the Lumina root,
   ``Lumina_combined_outputs``, or one of the two subdirectories.

.. autofunction:: snapPath

.. autofunction:: listSnaps

   These are the high-cadence counter values, not simulation snapshot
   numbers.

.. autofunction:: loadHeader

.. autofunction:: listFields

.. autofunction:: hubbleParam

   The frequent outputs do not store ``HubbleParam``, so it is read from a
   grid or lightcone header in the same Lumina tree. Pass ``h=`` to override;
   raises if neither is possible.

.. autofunction:: loadSnap

   ``fields`` is a field name, a list, or ``None`` for all. ``units`` is
   ``'code'``, ``'comoving'`` or ``'physical'`` (see
   :mod:`lumina_io.units`; the scale factor is this output's header
   ``Time``). With a single field name and ``sq=True`` the bare array is
   returned; the dict form includes ``'count'``, ``'Time'`` and
   ``'Redshift'``.

.. autofunction:: loadLifetimes

   With ``ids`` given (scalar or array), returns ``'first_snap'`` /
   ``'last_snap'`` aligned to ``ids``, with ``-1`` where the ID never
   existed.

.. autofunction:: trackBH

   ``ids`` is one ``ParticleID`` or a list; ``fields`` a name, a list, or
   ``None`` for all. ``snapRange`` is an inclusive ``(lo, hi)``
   frequent-output window; the window is additionally pruned with the
   ``bh_lifetimes`` table when the merger tree is present, so tracking a
   short-lived BH does not scan all ~900 files. For ``units``, the
   a-dependent conversions use each output's own scale factor.
   ``prefetch=True`` warms upcoming files into the page cache with parallel
   raw reads, hiding Lustre latency (the HDF5 reads themselves are
   serialized by a global lock).

   Returns a dict with ``'snaps'``, ``'Time'``, ``'Redshift'`` (per retained
   output), ``'found'`` (whether the BH exists in that output), and one
   array per field of shape ``(nsnaps, ...)`` for a single id or
   ``(nsnaps, nids, ...)`` for a list. Outputs where a BH is absent hold
   ``NaN`` for float fields and ``-1`` for integer fields. With a single id
   AND a single field name (``sq=True``), only the bare time-series array is
   returned.

.. autofunction:: loadMergerTree

   Reads ``BH_merger_tree/full_merger_tree.hdf5``. Ragged columns
   (``victim_ids``, ``victim_masses``, ``victim_dists``,
   ``remnant_merger_idxs``) come back as object arrays of per-event arrays.
   Masses are code units (1e10 Msun/h).

.. autofunction:: loadMergers

   ``mergers_NNNN.hdf5`` holds the events between outputs ``NNNN-1`` and
   ``NNNN``. Returns the table columns plus ``'count'``, which is 0 when
   there are no events -- the file may then contain no datasets at all.

.. autofunction:: findMergers

   Returns ``{'asRemnant': ..., 'asVictim': ...}``, where ``asRemnant`` is a
   dict of mergers-table columns for the events this BH survived (possibly
   empty) and ``asVictim`` is the single event in which it was consumed, or
   ``None``. Uses the precomputed indices of the tree file.

.. autofunction:: mainProgenitorChain

   In this catalog the ID switch is the common case: every top-mass BH at
   the final output carries a late-seeded ID that jumped by a factor
   100-3000 in one event.

   Returns ``[(id, firstSnap, lastSnap), ...]`` ordered early -> late with
   contiguous, non-overlapping frequent-output windows.

.. autofunction:: trackMainProgenitor

   The time series follows :func:`mainProgenitorChain` across the mergers
   where the surviving ``ParticleID`` was the lighter partner's, so the mass
   history is that of the growing object rather than of one ID. Returns the
   :func:`trackBH` dict (single-id form) plus ``'ids'`` (the ``ParticleID``
   tracked at each output) and ``'chain'``.
