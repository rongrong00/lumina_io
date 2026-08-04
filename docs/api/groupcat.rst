lumina_io.groupcat
==================

.. currentmodule:: lumina_io.groupcat

.. automodule:: lumina_io.groupcat
   :no-members:

Functions
---------

.. autosummary::

   loadHalos
   loadSubhalos
   iterHalos
   iterSubhalos
   loadHeader
   load
   loadSingle

Reference
---------

.. autofunction:: loadHalos

   ``fields=None`` loads everything; a single field name returns the bare
   array. ``units`` is ``'code'`` (as stored), ``'comoving'`` (h factors
   removed), or ``'physical'``.

.. autofunction:: loadSubhalos

.. autofunction:: iterHalos

   Yields dicts of the requested fields plus ``'count'`` (rows in this chunk)
   and ``'start'`` (global row offset). With ``prefetch=True`` the next chunk
   loads in the background, so two chunks are in memory at a time.

.. autofunction:: iterSubhalos

   See :func:`iterHalos`.

.. autofunction:: loadHeader

   Falls back to a synthesized header if the ``fof_subhalo_tab`` stub file is
   absent for this snapshot.

.. autofunction:: load

.. autofunction:: loadSingle
