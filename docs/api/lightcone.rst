lumina_io.lightcone
===================

.. currentmodule:: lumina_io.lightcone

.. automodule:: lumina_io.lightcone
   :no-members:

Layout
------

One tree per epoch, e.g. ``<root>/Lumina_above_z_4p75``:

``lightcone/rlc_<N>/<Field>.hdf5``
    One field per file, dataset named after the field, shape
    ``(NumPixels, NumPixels, NumDepth)``: transverse x, y pixels of an
    angular grid (``OpeningAngle`` radians across), line of sight LAST,
    ordered far -> near (decreasing redshift). Chunked 128^3; some fields
    blosc2-compressed.

``lightcone/rlc_<N>/All.hdf5``
    All fields in one file (contiguous) with unit attrs (``to_cgs``,
    ``a_scaling``, ``h_scaling``), the ``Header``, and the LOS coordinate
    arrays ::

        Redshifts  (NumDepth+1,)  cell edges, decreasing
        Distances  (NumDepth+1,)  comoving-distance edges, code units
        Segments   (NumDepth,)    per-cell comoving path length

The epoch trees are SEGMENTS of one lightcone (above: z = 30 -> 4.753,
below: z = 4.753 -> 2.99, sharing the boundary edge). Pass the Lumina root
and they are stitched along the LOS into a single global cell index space,
ordered far -> near. An epoch directory or a lightcone directory itself also
works, in which case only that segment is visible.

Example
-------

.. code-block:: python

    import lumina_io as lumina
    base = '/orcd/data/mvogelsb/005/Lumina'

    # all cells with 6 <= z <= 7, all transverse pixels
    cut = lumina.lightcone.loadLightcone(base, 'Density', res=640, zRange=(6, 7))

    # dict form returns the LOS coordinates of the cut as well
    cut = lumina.lightcone.loadLightcone(base, ['Density', 'Temperature'], res=640,
                                         zRange=(6, 7), region=((0, 64), (0, 64)))
    z_edges = cut['Redshifts']           # (nlos+1,) decreasing

    # physical cgs: the scale factor varies ALONG the LOS, so a-dependent
    # fields get a per-cell factor (broadcast over the LOS axis), float64
    rho = lumina.lightcone.loadLightcone(base, 'Density', res=640,
                                         zRange=(6, 6.2), units='cgs')

    # memory-bounded loop over the full LOS in slabs (198 GB/field at 2560)
    for chunk in lumina.lightcone.iterLightcone(base, 'Density', res=2560):
        process(chunk['Density'], chunk['Redshifts'])

Functions
---------

.. autosummary::

   lightconeDirs
   listResolutions
   losCoordinates
   loadHeader
   listFields
   losIndexRange
   loadLightcone
   iterLightcone

Reference
---------

.. autofunction:: lightconeDirs

   The lightcone directory itself, a directory containing ``lightcone``, or a
   root whose subdirectories do.

.. autofunction:: listResolutions

.. autofunction:: losCoordinates

   Returns ``'Redshifts'`` and ``'Distances'`` (``NumDepth+1`` cell edges,
   decreasing -- segment-boundary edges are shared), ``'Segments'``
   (``NumDepth`` per-cell path lengths, code units), and ``'NumDepth'``.

.. autofunction:: loadHeader

   For a stitched lightcone the attrs come from the farthest segment, with
   ``NumDepth`` replaced by the stitched total and the per-segment depths
   added as ``'SegmentNumDepth'``. With ``datasets=True`` the farthest
   segment's ``Header`` datasets (``Center``, ``FrequencyRanges``,
   ``LumNorm``, ...) are included; per-segment values are available by
   passing the epoch directory as ``basePath``.

.. autofunction:: listFields

.. autofunction:: losIndexRange

   Cells whose interior overlaps a redshift interval ``zRange=(z1, z2)`` or
   comoving-distance interval ``dRange=(d1, d2)`` (code units, like the
   ``Distances`` edges). Cells only touching an interval endpoint are
   excluded.

.. autofunction:: loadLightcone

   ``fields``
       Field name, list of names, or ``None`` for every available field.

   ``res``
       Transverse pixels per side (e.g. 640); may be omitted if only one
       resolution exists under ``basePath``.

   ``region``
       Transverse cut ``((x0,x1), (y0,y1))`` in pixels of the angular grid,
       clamped to the field of view (not periodic).

   ``zRange`` / ``dRange`` / ``losRange``
       LOS cut -- a redshift interval, a comoving distance interval (code
       units), or global cell indices ``(i0, i1)``. At most one may be given.
       Cells overlapping the interval are included, and cuts spanning the
       epoch boundary read from both segment trees and are concatenated.

   ``units``
       ``'code'`` (as stored) or ``'cgs'`` (physical cgs via the stored
       attrs; a-dependent fields get a per-LOS-cell factor; returned
       float64).

   ``sq``
       If ``True`` and a single field name was given, return the bare array.

   Returns arrays of shape ``(nx, ny, nlos)``, plus a component axis for
   vector fields, LOS ordered far -> near. The dict form adds ``'losRange'``
   (global ``(i0, i1)``), ``'pixelRegion'``, and the
   ``'Redshifts'``/``'Distances'`` edges (``nlos+1``) and ``'Segments'`` path
   lengths of the cut.

.. autofunction:: iterLightcone

   Slabs of ``chunkSize`` cells, far -> near. Yields dicts like
   ``loadLightcone(sq=False)`` plus ``'start'`` (global LOS index of the
   slab); the per-slab ``'Redshifts'`` / ``'Distances'`` edges are included.
   With ``prefetch=True`` the next slab loads in the background. One 2560^2
   LOS plane is 26 MB/field.
