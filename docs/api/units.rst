lumina_io.units
===============

.. currentmodule:: lumina_io.units

.. automodule:: lumina_io.units
   :no-members:

Code units
----------

::

  lengths      ckpc/h            (BoxSize, positions, radii)
  masses       1e10 Msun/h
  velocities   km/s * sqrt(a)    (particle velocities; catalog velocities are km/s)
  densities    1e10 Msun/h / (ckpc/h)^3
  Mdot         1e10 Msun/h (km/s)/(kpc/h)
  energies     1e10 Msun/h (km/s)^2
  ang. mom.    (1e10 Msun/h)(kpc/h)(km/s), physical;  SubhaloSpin: (kpc/h)(km/s)

Particle conventions follow IllustrisTNG. Where TNG is silent the authority is
the simulation source: ``snap_io.cc`` for particles, ``subfind_properties.cc``
for the group catalog. ``Group_J*``/``Subhalo_J*`` are physical, like
``SubhaloSpin``, so ``|J| = |Spin| * M`` holds in every target.

Conversion targets
------------------

``'code'``
    As stored (the default everywhere).

``'comoving'``
    ``h`` and 1e10 factors removed; lengths stay comoving: Msun, ckpc,
    Msun/ckpc^3, Msun/yr, ... Velocities are converted to peculiar km/s.

``'physical'``
    Additionally scale-factor factors applied: kpc, Msun/kpc^3, ...

Velocity conventions
--------------------

Peculiar velocity = stored * sqrt(a) for particle ``Velocities`` (the standard
Gadget/Arepo/TNG convention), ``GroupVel`` peculiar = stored / a,
``SubhaloVel`` is already km/s, and ``Potential`` physical = stored / a.

``Acceleration`` is not written by either LUMINA run and has no conversion
class.

Cosmological parameters (``HubbleParam``, ``Omega0``, ...) are read from the
``Parameters`` group of any header stub file; the scale factor of a snapshot
comes from its ``Header``. Both are cached per ``basePath``.

Functions
---------

.. autosummary::

   fieldConversionClass
   fieldUnits
   getCosmology
   getScaleFactor
   conversionFactor
   convert

Reference
---------

.. autofunction:: fieldConversionClass

.. autofunction:: fieldUnits

.. autofunction:: getCosmology

.. autofunction:: getScaleFactor

.. autofunction:: conversionFactor

   ``target`` is ``'code'``, ``'comoving'`` or ``'physical'``. Returns ``1.0``
   for dimensionless or unknown fields.

.. autofunction:: convert

   ``a`` / ``h`` may be given explicitly; otherwise they are read from the
   header stubs of ``(basePath, snapNum)``. Dimensionless and unknown fields
   pass through unchanged.
