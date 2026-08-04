lumina_io.powerspectra
======================

.. currentmodule:: lumina_io.powerspectra

.. automodule:: lumina_io.powerspectra
   :no-members:

Layout
------

One tree per epoch, e.g. ``<root>/Lumina_above_z_4p75`` ::

    powerspectra/<prefix>_NNN.txt

These are Gadget4 power-spectrum text files. Several species/observables are
written under different prefixes ::

    powerspec            total matter
    powerspec_type0      gas         powerspec_type1   dark matter
    powerspec_type4      stars       powerspec_type5   black holes
    powerspec_21cm       21 cm brightness temperature
    powerspec_HII_frac   HII fraction

Which prefixes exist depends on the epoch. Unlike the snapshots and grids,
the ``NNN`` index is the power-spectrum *output* counter -- its own, coarser
cadence that runs continuously across the epoch trees, and NOT the snapshot
number. Match outputs by redshift via the per-file header if needed.

File format
-----------

Each file holds up to three Fourier "folds" concatenated: Gadget4 writes the
unfolded spectrum, then two successively folded ones that extend the
measurement to higher k. Every fold is a 4- or 5-line header followed by
``count_non_zero_bins`` rows of ::

    k   Delta2   Power   CountModes   ShotLimit

``Delta2`` and ``Power`` are the shot-noise-uncorrected dimensionless and raw
power; ``ShotLimit`` is the shot-noise level. After the last fold three
scalars are appended: total mass, particle count, and
``mass^2/sum(mass^2)``.

``basePath`` may be the powerspectra directory itself, an epoch directory, or
the root holding the epoch trees.

Example
-------

.. code-block:: python

    import lumina_io as lumina
    base = '/orcd/data/mvogelsb/005/Lumina'

    ps = lumina.powerspectra.loadPowerSpectrum(base, 100)         # total matter
    k, P = ps['k'], ps['Power']                                   # all folds, k-sorted
    print(ps['Redshift'], ps['BoxSize'])

    gas = lumina.powerspectra.loadPowerSpectrum(base, 100, 'gas')
    f0  = lumina.powerspectra.loadPowerSpectrum(base, 100, fold=0)['Power']  # unfolded only

    nums = lumina.powerspectra.listOutputs(base, 'dm')

Functions
---------

.. autosummary::

   psDirs
   listKinds
   listOutputs
   filePath
   loadPowerSpectrum

Reference
---------

.. autofunction:: psDirs

   ``basePath`` may be a powerspectra directory itself (contains
   ``powerspec*.txt``), an epoch directory containing ``powerspectra``, or a
   root whose subdirectories do. Output numbering runs across the epoch
   trees, so all are searched.

.. autofunction:: listKinds

   For example ``['powerspec', 'powerspec_type0', ...]``.

.. autofunction:: listOutputs

.. autofunction:: filePath

.. autofunction:: loadPowerSpectrum

   ``num``
       Power-spectrum output number -- its own counter, see
       :func:`listOutputs`.

   ``kind``
       Species/observable: ``'matter'`` (default), ``'gas'``, ``'dm'``,
       ``'stars'``, ``'bh'``, ``'21cm'``, ``'HII_frac'``, a ``'typeN'``
       alias, or a raw ``'powerspec*'`` prefix.

   ``fold``
       ``None`` (default) returns all folds unioned and sorted by k; an int
       0/1/2 returns just that Fourier fold (0 = unfolded). Folds overlap in
       k -- use the per-fold arrays in ``result['folds']`` for rigorous,
       non-duplicated work.

   Returns a dict with column arrays ``'k'``, ``'Delta2'``, ``'Power'``,
   ``'CountModes'``, ``'ShotLimit'``; header scalars ``'Time'``,
   ``'Redshift'``, ``'BoxSize'``, ``'PMGRID'``, ``'GrowthFactor'``; the
   trailing ``'Mass'``, ``'Count'``, ``'MassCorrection'`` when present;
   ``'nfolds'``; and ``'folds'``, the list of per-fold dicts.
