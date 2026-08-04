# lumina_io.units

Unit handling and comoving/physical conversion for LUMINA data.

Code units (from [https://lumina-simulation.com/data-access](https://lumina-simulation.com/data-access)):
: lengths      ckpc/h            (BoxSize, positions, radii)
  masses       1e10 Msun/h
  velocities   km/s \* sqrt(a)    (particle velocities; catalog velocities are km/s)
  densities    1e10 Msun/h / (ckpc/h)^3
  Mdot         1e10 Msun/h (km/s)/(kpc/h)
  energies     1e10 Msun/h (km/s)^2
  ang. mom.    (1e10 Msun/h)(ckpc/h)(km/s);  SubhaloSpin: (kpc/h)(km/s), physical

Conversion targets:

```default
'code'      as stored (default everywhere).
'comoving'  h and 1e10 factors removed; lengths stay comoving:
            Msun, ckpc, Msun/ckpc^3, Msun/yr, ... Velocities are
            converted to peculiar km/s.
'physical'  additionally scale-factor factors applied: kpc, Msun/kpc^3, ...
```

Velocity conventions (verified against the LUMINA team’s analysis code,
disk_analysis/load_data.py – the website’s “divide by sqrt(a)” wording is
misleading): peculiar velocity = stored \* sqrt(a) for particle Velocities
(standard Gadget/Arepo/TNG convention), GroupVel peculiar = stored / a,
SubhaloVel is already km/s, Potential physical = stored / a.

Cosmological parameters (HubbleParam, Omega0, …) are read from the
Parameters group of any header stub file; the scale factor of a snapshot from
its Header. Both are cached per basePath.

## Functions

| [`fieldConversionClass`](#lumina_io.units.fieldConversionClass)(field)              | Conversion class name for a field, or None if dimensionless/unknown.                               |
|-----------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| [`fieldUnits`](#lumina_io.units.fieldUnits)(field[, target])                        | Human-readable units of a field under a conversion target.                                         |
| [`getCosmology`](#lumina_io.units.getCosmology)(basePath)                           | Cosmological/code parameters from any header stub's Parameters group.                              |
| [`getScaleFactor`](#lumina_io.units.getScaleFactor)(basePath, snapNum)              | Scale factor a of a snapshot, from its snap or fof_subhalo_tab stub.                               |
| [`conversionFactor`](#lumina_io.units.conversionFactor)(field, target[, a, h, ...]) | Multiplicative factor taking a field from code units to target ('code' | 'comoving' | 'physical'). |
| [`convert`](#lumina_io.units.convert)(arr, field[, basePath, snapNum, ...])         | Convert an array of field from code units to target units.                                         |

## Reference

### lumina_io.units.fieldConversionClass(field)

Conversion class name for a field, or None if dimensionless/unknown.

### lumina_io.units.fieldUnits(field, target='code')

Human-readable units of a field under a conversion target.

### lumina_io.units.getCosmology(basePath)

Cosmological/code parameters from any header stub’s Parameters group.

### lumina_io.units.getScaleFactor(basePath, snapNum)

Scale factor a of a snapshot, from its snap or fof_subhalo_tab stub.

### lumina_io.units.conversionFactor(field, target, a=None, h=None, basePath=None, snapNum=None)

Multiplicative factor taking a field from code units to target
(‘code’ | ‘comoving’ | ‘physical’). Returns 1.0 for dimensionless/unknown
fields.

### lumina_io.units.convert(arr, field, basePath=None, snapNum=None, target='physical', a=None, h=None)

Convert an array of field from code units to target units.
a/h may be given explicitly; otherwise they are read from the header
stubs of (basePath, snapNum). Dimensionless/unknown fields pass through.
