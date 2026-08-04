"""Unit handling and comoving/physical conversion for LUMINA data."""

import os
import glob
import numpy as np

from . import util, _backend

KPC_PER_KMS_IN_YR = 0.977793e9   # kpc / (km/s) expressed in years

# conversion classes: target value = code value * 10^ten * h^hexp * a^aexp.
# aexp applies only for target='physical'; vel_a is an a-exponent applied for
# BOTH 'comoving' and 'physical' (velocities are always made peculiar).
_CLASSES = {
    #  name          ten  hexp aexp  vel_a  units (comoving)         units (physical)
    'length':       (0,   -1,   1,   None,  'ckpc',                  'kpc'),
    'mass':         (10,  -1,   0,   None,  'Msun',                  'Msun'),
    'vel_sqrt_a':   (0,    0,   0,   0.5,   'km/s (peculiar)',       'km/s (peculiar)'),
    'vel_group':    (0,    0,   0,   -1.0,  'km/s (peculiar)',       'km/s (peculiar)'),
    'potential':    (0,    0,  -1,   None,  '(km/s)^2/a',            '(km/s)^2'),
    'density':      (10,   2,  -3,   None,  'Msun/ckpc^3',           'Msun/kpc^3'),
    'mdot':         (10,   0,   0,   None,  'Msun/yr',               'Msun/yr'),
    'energy':       (10,  -1,   0,   None,  'Msun (km/s)^2',         'Msun (km/s)^2'),
    # aexp=0: subfind builds J from physical dx x dv, so |J| = |Spin|*M holds
    'angmom':       (10,  -2,   0,   None,  'Msun kpc km/s',         'Msun kpc km/s'),
    'spin':         (0,   -1,   0,   None,  'kpc km/s',              'kpc km/s'),
    # snap_io.cc declares both wrong (PhotonDensity [M V^2/h], BH_Pressure a=1)
    'photondens':   (10,   2,  -3,   None,  'Msun (km/s)^2/ckpc^3',  'Msun (km/s)^2/kpc^3'),
    'pressure':     (10,   2,  -3,   None,  'Msun (km/s)^2/ckpc^3',  'Msun (km/s)^2/kpc^3'),
}

# field name -> conversion class; fields not listed are returned unchanged
# (dimensionless, IDs, counts, K, mag, erg/s/Hz, Msun/yr-already, ...)
_FIELD_CLASS = {
    # particles (all types)
    'Coordinates': 'length',            # via the IntCoordinates alias -> ckpc/h
    'Velocities': 'vel_sqrt_a',
    'Potential': 'potential',
    'Masses': 'mass',
    'GFM_InitialMass': 'mass',
    'Density': 'density',
    'PhotonDensity': 'photondens',
    'BH_Mass': 'mass',
    'BH_CumMassGrowth_QM': 'mass',
    'BH_CumMassGrowth_RM': 'mass',
    'BH_Mdot': 'mdot',
    'BH_MdotBondi': 'mdot',
    'BH_MdotEddington': 'mdot',
    'BH_CumEgyInjection_QM': 'energy',
    'BH_CumEgyInjection_RM': 'energy',
    'BH_CumPhotReleased': 'energy',
    'BH_MPB_CumEgyHigh': 'energy',
    'BH_MPB_CumEgyLow': 'energy',
    'BH_Density': 'density',
    'BH_Hsml': 'length',
    'BH_Pressure': 'pressure',
    # group catalog
    'GroupBHMass': 'mass',
    'GroupBHMdot': 'mdot',
    'GroupMass': 'mass',
    'GroupMassType': 'mass',
    'GroupWindMass': 'mass',
    'GroupPos': 'length',
    'GroupVel': 'vel_group',            # code km/s/a (peculiar = /a), per team analysis code
    'GroupEkin': 'energy',
    'GroupEpot': 'energy',
    'GroupEthr': 'energy',
    # subhalo catalog
    'SubhaloBHMass': 'mass',
    'SubhaloBHMdot': 'mdot',
    'SubhaloCM': 'length',
    'SubhaloPos': 'length',
    'SubhaloEkin': 'energy',
    'SubhaloEpot': 'energy',
    'SubhaloEthr': 'energy',
    'SubhaloKineticEnergyStars': 'energy',
    'SubhaloRotationalEnergyStars': 'energy',
    'SubhaloGasMassSFR': 'mass',
    'SubhaloHalfmassRad': 'length',
    'SubhaloHalfmassRadType': 'length',
    'SubhaloMass': 'mass',
    'SubhaloMassInHalfRad': 'mass',
    'SubhaloMassInHalfRadType': 'mass',
    'SubhaloMassInMaxRad': 'mass',
    'SubhaloMassInMaxRadType': 'mass',
    'SubhaloMassInRad': 'mass',
    'SubhaloMassInRadType': 'mass',
    'SubhaloMassType': 'mass',
    'SubhaloSpin': 'spin',
    'SubhaloSpinType': 'spin',
    'SubhaloStellarPhotometricsMassInRad': 'mass',
    'SubhaloStellarPhotometricsRad': 'length',
    'SubhaloVmaxRad': 'length',
    'SubhaloWindMass': 'mass',
}

# family rules for SO-halo variants etc. (prefix match)
_PREFIX_CLASS = [
    ('Group_M_', 'mass'),
    ('Group_MassType_', 'mass'),
    ('Group_R_', 'length'),
    ('Group_J', 'angmom'),          # Group_J, Group_Jdm/gas/stars (+_Crit200 ...)
    ('Group_Ekin', 'energy'),
    ('Group_Epot', 'energy'),
    ('Group_Ethr', 'energy'),
    ('Subhalo_J', 'angmom'),
    ('SubPerc', 'length'),          # SubPercNNMassRad
]


def fieldConversionClass(field):
    """Conversion class name for a field, or None if dimensionless/unknown."""
    if field in _FIELD_CLASS:
        return _FIELD_CLASS[field]
    for prefix, cls in _PREFIX_CLASS:
        if field.startswith(prefix):
            return cls
    return None


def fieldUnits(field, target='code'):
    """Human-readable units of a field under a conversion target."""
    cls = fieldConversionClass(field)
    if cls is None:
        return None
    ten, hexp, aexp, sqrt_a, u_com, u_phys = _CLASSES[cls]
    if target == 'code':
        return {'length': 'ckpc/h', 'mass': '1e10 Msun/h',
                'vel_sqrt_a': 'km/s / sqrt(a)', 'vel_group': 'km/s / a',
                'potential': '(km/s)^2/a', 'density': '1e10 Msun/h/(ckpc/h)^3',
                'mdot': '1e10 Msun/h (km/s)/(kpc/h)', 'energy': '1e10 Msun/h (km/s)^2',
                'angmom': '(1e10 Msun/h)(kpc/h)(km/s)', 'spin': '(kpc/h)(km/s)',
                'photondens': '1e10 Msun/h (km/s)^2/(ckpc/h)^3',
                'pressure': '1e10 Msun/h/(ckpc/h)^3 (km/s)^2'}[cls]
    return u_phys if target == 'physical' else u_com


_cosmoCache = {}


def getCosmology(basePath):
    """Cosmological/code parameters from any header stub's Parameters group."""
    base = util.resolveBasePath(basePath)
    if base in _cosmoCache:
        return _cosmoCache[base]
    stubs = []
    for dirPath in util.searchDirs(basePath):
        stubs += sorted(glob.glob(os.path.join(dirPath, 'snap_*.hdf5')), reverse=True) + \
                 sorted(glob.glob(os.path.join(dirPath, 'fof_subhalo_tab_*.hdf5')), reverse=True)
    for stub in stubs:
        pars = _backend.read_attrs(stub, 'Parameters')
        if pars and 'HubbleParam' in pars:
            cosmo = {name: pars[name] for name in
                     ('HubbleParam', 'Omega0', 'OmegaLambda', 'OmegaBaryon', 'BoxSize',
                      'UnitLength_in_cm', 'UnitMass_in_g', 'UnitVelocity_in_cm_per_s')
                     if name in pars}
            _cosmoCache[base] = cosmo
            return cosmo
    raise ValueError("No header stub with a Parameters group found under " + base)


_scaleFactorCache = {}


def getScaleFactor(basePath, snapNum):
    """Scale factor a of a snapshot, from its snap or fof_subhalo_tab stub."""
    base = util.resolveBasePath(basePath)
    key = (base, snapNum)
    if key in _scaleFactorCache:
        return _scaleFactorCache[key]
    for stub in (util.snapPath(basePath, snapNum), util.gcPath(basePath, snapNum)):
        if os.path.isfile(stub):
            hdr = _backend.read_attrs(stub, 'Header')
            if hdr and 'Time' in hdr:
                _scaleFactorCache[key] = float(hdr['Time'])
                return _scaleFactorCache[key]
    raise ValueError(
        "Cannot determine the scale factor of snapshot %d: no snap_%03d.hdf5 or "
        "fof_subhalo_tab_%03d.hdf5 header stub exists. Pass a= explicitly to "
        "units.convert, or use units='code'." % (snapNum, snapNum, snapNum))


def conversionFactor(field, target, a=None, h=None, basePath=None, snapNum=None):
    """Multiplicative factor taking a field from code units to `target`."""
    if target == 'code':
        return 1.0
    if target not in ('comoving', 'physical'):
        raise ValueError("units target must be 'code', 'comoving' or 'physical'")
    cls = fieldConversionClass(field)
    if cls is None:
        return 1.0
    ten, hexp, aexp, vel_a, _, _ = _CLASSES[cls]
    if h is None:
        h = float(getCosmology(basePath)['HubbleParam'])
    need_a = (vel_a is not None) or (target == 'physical' and aexp != 0)
    if need_a and a is None:
        a = getScaleFactor(basePath, snapNum)
    factor = (10.0 ** ten) * (h ** hexp)
    if cls == 'mdot':
        factor /= KPC_PER_KMS_IN_YR      # -> Msun/yr (h cancels exactly)
    if target == 'physical' and aexp != 0:
        factor *= float(a) ** aexp
    if vel_a is not None:
        # velocities become peculiar km/s for both 'comoving' and 'physical'
        factor *= float(a) ** vel_a
    return factor


def convert(arr, field, basePath=None, snapNum=None, target='physical', a=None,
            h=None, copy=False):
    """Convert an array of `field` from code units to `target` units."""
    factor = conversionFactor(field, target, a=a, h=h, basePath=basePath, snapNum=snapNum)
    if factor == 1.0:
        return arr.copy() if copy else arr
    if arr.dtype == np.float16:      # avoid compounding half-precision rounding
        return arr.astype(np.float32) * np.float32(factor)
    return arr * arr.dtype.type(factor) if arr.dtype.kind == 'f' else arr * factor


def cgsFactor(attrs, header):
    """Factor taking a stored grid/projection/DM-only field to physical cgs."""
    if not attrs or 'to_cgs' not in attrs:
        return 1.0
    factor = float(attrs['to_cgs']) or 1.0
    factor *= float(header.get('Time', 1.0)) ** float(attrs.get('a_scaling', 0.0))
    factor *= float(header['HubbleParam']) ** float(attrs.get('h_scaling', 0.0))
    return factor
