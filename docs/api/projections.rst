lumina_io.projections
=====================

.. currentmodule:: lumina_io.projections

.. automodule:: lumina_io.projections
   :no-members:

Layout
------

One tree per epoch, e.g. ``<root>/Lumina_above_z_4p75``:

``projections/projections<DDD>/projections_NNN.hdf5``
    One file per snapshot ``NNN``, holding several 2D maps (``NumPixelsX`` x
    ``NumPixelsY``, float32) as top-level datasets -- ``Density``,
    ``Temperature``, the ionization fractions, etc. -- plus a ``Header``
    group with the projection geometry (``BoxSize``, ``Width``, ``Height``,
    ``Depth``, ``Center``, cosmology) and a few small datasets (``Center``,
    ``FrequencyRanges``, ``LumNorm``, ``MeanPhotonEnergy``). Map datasets
    carry the same unit attributes as the grids (``to_cgs``, ``a_scaling``,
    ``h_scaling``, ...).

The ``<DDD>`` suffix is the projection depth in units of ``BoxSize/100``:
``projections002`` integrates through a 2%-of-box slab, ``004`` through 4%,
``008`` through 8% (``Depth = DDD/100 * BoxSize``, in ckpc/h). All depths
share the ``NumPixelsX`` x ``NumPixelsY`` face resolution (4096^2 for the
500cMpc run).

Maps are snapshot-indexed exactly like the snapshots and grids: snaps 0-428
live in ``Lumina_above_z_4p75``, 429-708 in ``Lumina_below_z_4p75``.
``basePath`` may be the projections directory itself, an epoch directory, or
the root holding the epoch trees; the epoch is resolved per snapshot.

Example
-------

.. code-block:: python

    import lumina_io as lumina
    base = '/orcd/data/mvogelsb/005/Lumina'

    rho = lumina.projections.loadProjection(base, 100, 'Density')          # depth=2
    d   = lumina.projections.loadProjection(base, 100,
                                            ['Density', 'Temperature'], depth=8)

    # physical cgs units (float64; factor = to_cgs * a^a_scaling * h^h_scaling)
    rho = lumina.projections.loadProjection(base, 100, 'Density', units='cgs')

    # sub-image: ((i0,i1),(j0,j1)) pixel ranges (periodic wrap handled)
    cut = lumina.projections.loadProjection(base, 100, 'Temperature',
                                            region=((0, 512), (0, 512)))

Functions
---------

.. autosummary::

   projDirs
   listDepths
   filePath
   listFields
   listSnaps
   loadHeader
   fieldUnitAttrs
   loadProjection

Reference
---------

.. autofunction:: projDirs

   ``basePath`` may be a projections directory itself (contains
   ``projections<DDD>``), an epoch directory containing ``projections``, or a
   root whose subdirectories do. The epoch trees hold disjoint snapshot
   ranges, so all are searched.

.. autofunction:: listDepths

   The ``<DDD>`` directory suffixes, e.g. ``[2, 4, 8]``.

.. autofunction:: filePath

.. autofunction:: listFields

.. autofunction:: listSnaps

   At the given depth, or any depth when ``depth`` is omitted.

.. autofunction:: loadHeader

   With ``datasets=True`` the small datasets inside the ``Header`` group
   (``Center``, ``FrequencyRanges``, ``LumNorm``, ``MeanPhotonEnergy``, ...)
   are included as arrays.

.. autofunction:: fieldUnitAttrs

   Returns ``to_cgs``, ``a_scaling``, ``h_scaling``,
   ``length``/``mass``/``velocity_scaling``.

.. autofunction:: loadProjection

   ``fields``
       Map name, list of names, or ``None`` for every map in the file. One
       4096^2 float32 map is 67 MB.

   ``depth``
       Projection slab depth as the ``<DDD>`` suffix (2, 4, or 8 -> 2/4/8% of
       the box). May be omitted if only one depth exists, otherwise defaults
       to the thinnest, 2.

   ``region``
       Load only a sub-image -- ``((i0,i1),(j0,j1))`` half-open pixel ranges.
       Periodic wrap is handled and only the intersecting file chunks are
       read.

   ``units``
       ``'code'`` (as stored) or ``'cgs'`` (physical cgs via the ``to_cgs`` /
       ``a_scaling`` / ``h_scaling`` attrs; returned as float64).

   ``sq``
       If ``True`` and a single field name was given, return the bare array.

   Returns a ``(NumPixelsX, NumPixelsY)`` array per field, or a sub-shape
   when ``region`` is given. The dict form includes ``'pixelRegion'``, the
   pixel ranges actually loaded.
