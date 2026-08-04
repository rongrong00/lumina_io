lumina_io
=============

Fast data loading for LUMINA simulations: a Python API on top of a
parallel C++ HDF5 reader, written for the LUMINA on-disk layout
(field-per-file datasets, offsets inside the group catalog, the repackaged
005 data products).

.. code-block:: python

   import lumina_io as lumina

   basePath = '/orcd/data/mvogelsb/005/Lumina/Lumina_above_z_4p75'
   halos = lumina.groupcat.loadHalos(basePath, 116, ['GroupPos', 'GroupMass'])
   stars = lumina.snapshot.loadHalo(basePath, 116, id=42, partType='stars')

   root = '/orcd/data/mvogelsb/005/Lumina'
   rho  = lumina.grid.loadGrid(root, 600, 'Density', res=640)
   cut  = lumina.lightcone.loadLightcone(root, 'Density', res=2560,
                                         zRange=(6.0, 6.05))
   tr   = lumina.bh.trackMainProgenitor(root, bhID, ['BH_Mass'])
   img  = lumina.projections.loadProjection(root, 100, 'Density', depth=2)
   ps   = lumina.powerspectra.loadPowerSpectrum(root, 100)
   sub  = lumina.dmo.loadSubhalo('1500', 298, 17, fields='Coordinates')

Every loader accepts ``units='code' | 'comoving' | 'physical'`` (grids and
lightcones: ``'code' | 'cgs'``). A complete walkthrough with figures is in
``examples/tutorial.ipynb``; build and layout notes are in the README.

Modules
-------

.. list-table::
   :widths: 28 72

   * - :mod:`lumina_io.groupcat`
     - FoF group and subhalo catalogs
   * - :mod:`lumina_io.snapshot`
     - particle data: full snapshots, subsets, single or batched halos
   * - :mod:`lumina_io.grid`
     - 3D cartesian grids (``ren_5`` ... ``ren_2560``), periodic regions
   * - :mod:`lumina_io.lightcone`
     - the stitched lightcone, cut by redshift / distance / pixels
   * - :mod:`lumina_io.bh`
     - high-cadence black hole outputs, tracking, merger trees
   * - :mod:`lumina_io.projections`
     - 2D projection maps per snapshot and slab depth
   * - :mod:`lumina_io.powerspectra`
     - Gadget4 power spectra, folds merged
   * - :mod:`lumina_io.dmo`
     - the DM-only Gadget4 companion runs
   * - :mod:`lumina_io.units`
     - code / comoving / physical conversion for every field
   * - :mod:`lumina_io.derived`
     - Temperature, ElectronAbundance, StellarAge, ... on the fly
   * - :mod:`lumina_io.util`
     - path resolution, field/snapshot discovery

.. toctree::
   :maxdepth: 2
   :caption: Simulation run
   :hidden:

   api/groupcat
   api/snapshot

.. toctree::
   :maxdepth: 2
   :caption: Data products
   :hidden:

   api/grid
   api/lightcone
   api/bh
   api/projections
   api/powerspectra
   api/dmo

.. toctree::
   :maxdepth: 2
   :caption: Units & helpers
   :hidden:

   api/units
   api/derived
   api/util

Index
-----

* :ref:`genindex`
* :ref:`search`
