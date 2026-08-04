lumina_io.snapshot
==================

.. currentmodule:: lumina_io.snapshot

.. automodule:: lumina_io.snapshot
   :no-members:

Layout notes
------------

In the LUMINA layout each field is one logical dataset over the whole
snapshot, and group/subhalo particle offsets are stored in the group catalog
itself (``Group/GroupOffsetType``, ``Subhalo/SubhaloOffsetType``) rather than
in ``postprocessing/offsets``.

Field aliases: requesting ``'Coordinates'`` transparently reads the on-disk
``'IntCoordinates'`` (uint32) and converts to float64 box units
(``BoxSize * i / 2^32``) when no ``'Coordinates'`` dataset exists.

Functions
---------

.. autosummary::

   loadHeader
   getNumPart
   loadSubset
   iterSubset
   getSnapOffsets
   loadHalo
   loadSubhalo
   loadHalos
   loadSubhalos

Reference
---------

.. autofunction:: loadHeader

   Falls back to a synthesized header, with ``NumPart_Total`` taken from
   dataset shapes, if the snap stub is absent.

.. autofunction:: getNumPart

.. autofunction:: loadSubset

   ``subset``
       Dict with ``'start'`` and ``'count'`` (rows along the snapshot-global
       particle axis), e.g. as returned by :func:`getSnapOffsets`. ``None``
       loads the full snapshot for this type.

   ``mdi``
       List of multi-dimensional indices, one per field (``None`` entries
       load the full field). ``fields=['Coordinates'], mdi=[1]`` loads the
       y-coordinate only.

   ``sq``
       If ``True`` and a single field is requested, return the bare array.

   ``float32``
       Convert float64 fields to float32 on return.

   ``units``
       ``'code'`` (as stored), ``'comoving'`` (h/1e10 factors removed), or
       ``'physical'`` (scale-factor factors applied as well; velocities
       become peculiar km/s). See :mod:`lumina_io.units`.

.. autofunction:: iterSubset

   Yields dicts like ``loadSubset(sq=False)`` -- requested fields plus
   ``'count'`` (rows in this chunk) and ``'start'`` (global row offset of the
   chunk) -- for consecutive ``chunkSize``-row windows covering the whole
   snapshot, or the given subset. With ``prefetch=True`` (the default) the
   next chunk is read in the background while you process the current one, so
   up to two chunks are in memory at a time.

   .. code-block:: python

       for chunk in lumina.snapshot.iterSubset(base, 116, 'gas',
                                               ['Coordinates', 'Masses'],
                                               chunkSize=50_000_000):
           process(chunk['Coordinates'], chunk['Masses'])

.. autofunction:: getSnapOffsets

   Offsets are read from the location inside the catalog output:
   ``Group/GroupOffsetType`` and ``Subhalo/SubhaloOffsetType``. ``id`` may be
   a scalar or an array of IDs, in which case ``offsetType``/``lenType`` have
   shape ``(len(id), 6)``.

.. autofunction:: loadHalo

.. autofunction:: loadSubhalo

.. autofunction:: loadHalos

   Much faster than looping :func:`loadHalo`. Returns a dict with the
   requested fields concatenated in the order of ``ids``, plus ``'count'``
   (total particles) and ``'lens'`` (particles per halo). Split per halo with
   ``np.split(arr, np.cumsum(result['lens'])[:-1])``. With a single field name
   and ``sq=True`` (the default) only the bare concatenated array is returned.

.. autofunction:: loadSubhalos

   See :func:`loadHalos` for the return convention.
