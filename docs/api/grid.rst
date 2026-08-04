lumina_io.grid
==============

.. currentmodule:: lumina_io.grid

.. automodule:: lumina_io.grid
   :no-members:

Layout
------

One tree per epoch, e.g. ``<root>/Lumina_below_z_4p75``:

``3d_cartesian_grid/ren_<N>/<Field>/<Field>_NNN.hdf5``
    One field per file, dataset named after the field, plus a ``Header``
    group (``BoxSize``, ``NumPixels``, ``Redshift``, ``Time``, cosmology).
    Most are chunked/uncompressed; some are blosc2-compressed, handled via
    the ``hdf5plugin`` package.

``3d_cartesian_grid/ren_<N>/All/All_NNN.hdf5``
    All fields of the snapshot in one file; each dataset carries unit
    attributes (``to_cgs``, ``a_scaling``, ``h_scaling``, ...) which drive
    the ``units='cgs'`` conversion.

Grids are ``NumPixels^3`` cells (axes x, y, z; cell size
``BoxSize/NumPixels``, in ckpc/h), float32. Vector fields (``Velocities``,
``IonFlux``, ``IonEnergies``) carry a trailing component axis.

``basePath`` may be the grid directory itself, an epoch directory containing
``3d_cartesian_grid``, or the root holding several epoch trees (e.g.
``/orcd/data/mvogelsb/005/Lumina``, where snaps 0-428 live in
``Lumina_above_z_4p75`` and 429-708 in ``Lumina_below_z_4p75``). The epoch is
resolved per snapshot.

Example
-------

.. code-block:: python

    import lumina_io as lumina
    base = '/orcd/data/mvogelsb/005/Lumina'

    rho = lumina.grid.loadGrid(base, 600, 'Density', res=640)
    d   = lumina.grid.loadGrid(base, 600, ['Density', 'Temperature'], res=640)

    # sub-volume around a position (code units, periodic wrap handled);
    # region may also be ((i0,i1), (j0,j1), (k0,k1)) in pixel indices
    cut = lumina.grid.loadGrid(base, 600, 'Temperature', res=2560,
                               region={'center': pos, 'size': 5000.})

    # memory-bounded loop over a 2560^3 field (67 GB) in x-slabs
    for chunk in lumina.grid.iterGrid(base, 600, 'Density', res=2560):
        process(chunk['Density'])      # chunk['start'] = first x-plane

    # physical cgs units (float64; factor = to_cgs * a^a_scaling * h^h_scaling)
    rho = lumina.grid.loadGrid(base, 600, 'Density', res=640, units='cgs')

Functions
---------

.. autosummary::

   gridDirs
   listResolutions
   fieldPath
   listFields
   listSnaps
   loadHeader
   fieldUnitAttrs
   loadGrid
   iterGrid

Reference
---------

.. autofunction:: gridDirs

   ``basePath`` may be a grid directory itself (contains ``ren_*``), a
   directory containing ``3d_cartesian_grid``, or a root whose
   subdirectories do. The epoch trees hold disjoint snapshot ranges, so all
   are searched.

.. autofunction:: listResolutions

.. autofunction:: fieldPath

   Prefers the per-field file (chunked, fast path); falls back to files of
   other naming (``z_reion_V_50.hdf5`` lives in ``z_reion/``) and to the
   combined ``All`` file. Returns ``(None, None)`` if the field cannot be
   found.

.. autofunction:: listFields

.. autofunction:: listSnaps

   For ``z_reion`` the "snapshot" numbers are reionization percentiles:
   1, 10, 50, 90, 99.

.. autofunction:: loadHeader

   With ``datasets=True`` the datasets stored inside the ``All`` file's
   ``Header`` group (``Center``, ``FrequencyRanges``, ``LumNorm``,
   ``MeanPhotonEnergy``, ...) are included as arrays.

.. autofunction:: fieldUnitAttrs

   Returns ``to_cgs``, ``a_scaling``, ``h_scaling``,
   ``length``/``mass``/``velocity_scaling``. Per-field files carry no such
   attributes, so they are read from the ``All`` file. Returns ``None`` for
   fields without attributes, e.g. ``z_reion``.

.. autofunction:: loadGrid

   ``fields``
       Field name, list of names, or ``None`` for every available field.
       Mind the memory: one 2560^3 scalar field is 67 GB.

   ``res``
       Cells per side (e.g. 640); may be omitted if only one resolution
       exists under ``basePath``.

   ``region``
       Load only a sub-volume -- ``((i0,i1),(j0,j1),(k0,k1))`` pixel ranges,
       or ``{'center': (x,y,z), 'size': s}`` in code units. Periodic wrap is
       handled, and only the file chunks intersecting the region are read.
       Pixel ranges may extend outside ``[0, NumPixels)``; a full-span range
       keeps its rolled order (cells come back as
       ``np.arange(lo, hi) % NumPixels``), and ranges spanning more than the
       whole axis are clamped to ``(0, NumPixels)``.

   ``units``
       ``'code'`` (as stored) or ``'cgs'`` (physical cgs via the ``to_cgs`` /
       ``a_scaling`` / ``h_scaling`` attrs; returned as float64).

   ``sq``
       If ``True`` and a single field name was given, return the bare array.

   Returns array shape ``(nx, ny, nz)``, plus a component axis for vector
   fields, axes ordered x, y, z. The dict form includes ``'pixelRegion'``,
   the pixel ranges actually loaded.

.. autofunction:: iterGrid

   Yields dicts of the requested fields plus ``'start'`` (first x-plane of
   the slab); arrays have shape ``(<=chunkSize, npix, npix, ...)``. With
   ``prefetch=True`` the next slab loads in the background, so two slabs are
   in memory at a time. One 2560^2 plane is 26 MB/field, so the default
   ``chunkSize=64`` holds ~1.7 GB per field per slab.
