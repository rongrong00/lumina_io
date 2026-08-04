lumina_io.derived
=================

.. currentmodule:: lumina_io.derived

.. automodule:: lumina_io.derived
   :no-members:

Available derived fields
------------------------

These are not stored on disk but computed from raw fields. The loader-facing
names, usable in any snapshot loader (e.g.
``loadHalo(..., 'gas', ['Temperature'])``) ::

  ElectronAbundance        n_e/n_H from the ionization fractions
  MeanMolecularWeight      mu
  Temperature              K
  SoundSpeed               km/s
  NeutralHydrogenFraction  1 - HII_Fraction
  StellarAge               Myr since formation (stars; wind -> NaN)

Derived outputs are in physical units already (K, km/s, Myr, dimensionless),
so they are unaffected by the ``units=`` setting of the loaders.

Ionization conventions
----------------------

The on-disk helium fractions are already normalized per hydrogen nucleus --
``HeI+HeII+HeIII = (1-X_H)/(4 X_H) = n_He/n_H``, verified empirically as
``max(HeII+HeIII) = 0.078947`` in the 500cMpc run. Hence

.. math::

   x_e = n_e/n_H = \mathrm{HII\_Fraction} + \mathrm{HeII\_Fraction}
         + 2\,\mathrm{HeIII\_Fraction}

with NO extra ``n_He/n_H`` factor. Note that ``disk_analysis/load_data.py``
multiplies the He terms by another ``n_He/n_H``, which double-counts the
normalization.

Functions
---------

.. autosummary::

   electronAbundance
   meanMolecularWeight
   temperature
   soundSpeed
   cosmicTime
   stellarAge
   cellVolume
   cellSize
   expandFields
   compute

Reference
---------

.. autofunction:: electronAbundance

.. autofunction:: meanMolecularWeight

.. autofunction:: temperature

.. autofunction:: soundSpeed

.. autofunction:: cosmicTime

.. autofunction:: stellarAge

   Entries with formation time <= 0 are wind particles and return ``NaN``.

.. autofunction:: cellVolume

.. autofunction:: cellSize

.. autofunction:: expandFields

   Returns ``(readList, derivedNames)``, where ``readList`` covers all raw
   requests plus derived requirements, deduplicated. A derived name shadowed
   by a real on-disk field is treated as raw.

.. autofunction:: compute
