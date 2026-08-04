"""Derived gas/star fields for LUMINA, computed from raw on-disk fields."""

import numpy as np

from . import units as _units

X_H = 0.76                     # primordial hydrogen mass fraction
GAMMA = 5.0 / 3.0
M_PROTON = 1.67262192e-24      # g
K_BOLTZMANN = 1.380649e-16     # erg/K
KM_PER_MPC = 3.0856776e19
SEC_PER_MYR = 3.1556952e13


def electronAbundance(HII_Fraction, HeII_Fraction, HeIII_Fraction):
    """n_e/n_H. Helium fractions are per hydrogen nucleus on disk."""
    return HII_Fraction + HeII_Fraction + 2.0 * HeIII_Fraction


def meanMolecularWeight(x_e, X_H=X_H):
    """Mean molecular weight mu given x_e = n_e/n_H."""
    return 4.0 / (1.0 + 3.0 * X_H + 4.0 * X_H * x_e)


def temperature(InternalEnergy, x_e, X_H=X_H):
    """Gas temperature in K. InternalEnergy in code units ((km/s)^2)."""
    mu = meanMolecularWeight(x_e, X_H)
    return (GAMMA - 1.0) * InternalEnergy * 1e10 * mu * M_PROTON / K_BOLTZMANN


def soundSpeed(InternalEnergy):
    """Adiabatic sound speed in km/s from code-unit internal energy."""
    return np.sqrt(GAMMA * (GAMMA - 1.0) * InternalEnergy)


def cosmicTime(a, h, Omega0, OmegaLambda):
    """Age of a flat LCDM universe at scale factor a, in Myr."""
    H0 = 100.0 * h / KM_PER_MPC                       # 1/s
    ageSec = (2.0 / (3.0 * H0 * np.sqrt(OmegaLambda)) *
              np.arcsinh(np.sqrt(OmegaLambda / Omega0) * np.asarray(a, dtype=np.float64) ** 1.5))
    return ageSec / SEC_PER_MYR


def stellarAge(GFM_StellarFormationTime, a_now, h, Omega0, OmegaLambda):
    """Age in Myr of star particles at scale factor a_now."""
    tform = np.asarray(GFM_StellarFormationTime, dtype=np.float64)
    age = cosmicTime(a_now, h, Omega0, OmegaLambda) - \
        cosmicTime(np.clip(tform, 1e-10, None), h, Omega0, OmegaLambda)
    return np.where(tform > 0, age, np.nan)


def cellVolume(Masses, Density):
    """Gas cell volume in code units ((ckpc/h)^3) from code-unit inputs."""
    return Masses / Density


def cellSize(Masses, Density):
    """Equivalent spherical cell radius in code units (ckpc/h)."""
    return (3.0 * cellVolume(Masses, Density) / (4.0 * np.pi)) ** (1.0 / 3.0)


# --- loader integration -------------------------------------------------------

def _ctx_cosmo(basePath, snapNum):
    cosmo = _units.getCosmology(basePath)
    return (_units.getScaleFactor(basePath, snapNum), float(cosmo['HubbleParam']),
            float(cosmo['Omega0']), float(cosmo['OmegaLambda']))


def _d_xe(raw, basePath, snapNum):
    return electronAbundance(raw['HII_Fraction'], raw['HeII_Fraction'],
                             raw['HeIII_Fraction'])


def _d_mu(raw, basePath, snapNum):
    return meanMolecularWeight(_d_xe(raw, basePath, snapNum))


def _d_temp(raw, basePath, snapNum):
    return temperature(raw['InternalEnergy'], _d_xe(raw, basePath, snapNum))


def _d_cs(raw, basePath, snapNum):
    return soundSpeed(raw['InternalEnergy'])


def _d_hi(raw, basePath, snapNum):
    return 1.0 - raw['HII_Fraction']


def _d_age(raw, basePath, snapNum):
    a_now, h, omega0, omegaLambda = _ctx_cosmo(basePath, snapNum)
    return stellarAge(raw['GFM_StellarFormationTime'], a_now, h, omega0, omegaLambda)


_ION_FIELDS = ['HII_Fraction', 'HeII_Fraction', 'HeIII_Fraction']

# name -> (required raw fields, compute(rawDict, basePath, snapNum))
DERIVED_FIELDS = {
    'ElectronAbundance':       (_ION_FIELDS, _d_xe),
    'MeanMolecularWeight':     (_ION_FIELDS, _d_mu),
    'Temperature':             (['InternalEnergy'] + _ION_FIELDS, _d_temp),
    'SoundSpeed':              (['InternalEnergy'], _d_cs),
    'NeutralHydrogenFraction': (['HII_Fraction'], _d_hi),
    'StellarAge':              (['GFM_StellarFormationTime'], _d_age),
}


def expandFields(fields, available):
    """Split a requested field list into raw fields to read and derived fields."""
    derivedNames = [field for field in fields
                    if field in DERIVED_FIELDS and field not in available]
    readList = [field for field in fields if field not in derivedNames]
    for name in derivedNames:
        for req in DERIVED_FIELDS[name][0]:
            if req not in readList:
                readList.append(req)
    return readList, derivedNames


def compute(name, raw, basePath, snapNum):
    """Compute derived field `name` from the dict of raw arrays."""
    return DERIVED_FIELDS[name][1](raw, basePath, snapNum)
