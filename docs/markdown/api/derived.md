# lumina_io.derived

Derived gas/star fields for LUMINA.

These are not stored on disk but computed from raw fields. The loader-facing
names (usable in any snapshot loader, e.g.
`loadHalo(..., 'gas', ['Temperature'])`) are:

> ElectronAbundance        n_e/n_H from the ionization fractions
> MeanMolecularWeight      mu
> Temperature              K
> SoundSpeed               km/s
> NeutralHydrogenFraction  1 - HII_Fraction
> StellarAge               Myr since formation (stars; wind -> NaN)

Conventions: the on-disk helium fractions are already normalized per hydrogen
nucleus – HeI+HeII+HeIII = (1-X_H)/(4 X_H) = n_He/n_H (verified empirically:
max(HeII+HeIII) = 0.078947 in the 500cMpc run). Hence

> x_e = n_e/n_H = HII_Fraction + HeII_Fraction + 2 HeIII_Fraction

with NO extra n_He/n_H factor. (Note: disk_analysis/load_data.py multiplies
the He terms by another n_He/n_H – that double-counts the normalization.)

Derived outputs are in physical units already (K, km/s, Myr, dimensionless),
so they are unaffected by the units= setting of the loaders.

## Functions

| [`electronAbundance`](#lumina_io.derived.electronAbundance)(HII_Fraction, ...)      | n_e/n_H.                                                                                    |
|-----------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| [`meanMolecularWeight`](#lumina_io.derived.meanMolecularWeight)(x_e[, X_H])         | Mean molecular weight mu given x_e = n_e/n_H.                                               |
| [`temperature`](#lumina_io.derived.temperature)(InternalEnergy, x_e[, X_H])         | Gas temperature in K.                                                                       |
| [`soundSpeed`](#lumina_io.derived.soundSpeed)(InternalEnergy)                       | Adiabatic sound speed in km/s from code-unit internal energy.                               |
| [`cosmicTime`](#lumina_io.derived.cosmicTime)(a, h, Omega0, OmegaLambda)            | Age of a flat LCDM universe at scale factor a, in Myr.                                      |
| [`stellarAge`](#lumina_io.derived.stellarAge)(GFM_StellarFormationTime, a_now, ...) | Age in Myr of star particles at scale factor a_now.                                         |
| [`cellVolume`](#lumina_io.derived.cellVolume)(Masses, Density)                      | Gas cell volume in code units ((ckpc/h)^3) from code-unit inputs.                           |
| [`cellSize`](#lumina_io.derived.cellSize)(Masses, Density)                          | Equivalent spherical cell radius in code units (ckpc/h).                                    |
| [`expandFields`](#lumina_io.derived.expandFields)(fields, available)                | Split a requested field list into the raw fields to read and the derived fields to compute. |
| [`compute`](#lumina_io.derived.compute)(name, raw, basePath, snapNum)               | Compute derived field name from the dict of raw arrays.                                     |

## Reference

### lumina_io.derived.electronAbundance(HII_Fraction, HeII_Fraction, HeIII_Fraction)

n_e/n_H. Helium fractions are per hydrogen nucleus on disk.

### lumina_io.derived.meanMolecularWeight(x_e, X_H=0.76)

Mean molecular weight mu given x_e = n_e/n_H.

### lumina_io.derived.temperature(InternalEnergy, x_e, X_H=0.76)

Gas temperature in K. InternalEnergy in code units ((km/s)^2).

### lumina_io.derived.soundSpeed(InternalEnergy)

Adiabatic sound speed in km/s from code-unit internal energy.

### lumina_io.derived.cosmicTime(a, h, Omega0, OmegaLambda)

Age of a flat LCDM universe at scale factor a, in Myr.

### lumina_io.derived.stellarAge(GFM_StellarFormationTime, a_now, h, Omega0, OmegaLambda)

Age in Myr of star particles at scale factor a_now. Entries with
formation time <= 0 are wind particles and return NaN.

### lumina_io.derived.cellVolume(Masses, Density)

Gas cell volume in code units ((ckpc/h)^3) from code-unit inputs.

### lumina_io.derived.cellSize(Masses, Density)

Equivalent spherical cell radius in code units (ckpc/h).

### lumina_io.derived.expandFields(fields, available)

Split a requested field list into the raw fields to read and the
derived fields to compute. Returns (readList, derivedNames) where
readList covers all raw requests plus derived requirements (deduped).
A derived name shadowed by a real on-disk field is treated as raw.

### lumina_io.derived.compute(name, raw, basePath, snapNum)

Compute derived field name from the dict of raw arrays.
