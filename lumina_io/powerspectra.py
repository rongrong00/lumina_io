"""Gadget4 power-spectrum text files, with the folds merged into one k series."""

import os
import glob
import numpy as np

PS_SUBDIR = 'powerspectra'

# friendly name -> on-disk filename prefix
_KIND_PREFIX = {
    'matter': 'powerspec', 'total': 'powerspec', 'all': 'powerspec',
    'gas': 'powerspec_type0', 'type0': 'powerspec_type0',
    'dm': 'powerspec_type1', 'darkmatter': 'powerspec_type1', 'type1': 'powerspec_type1',
    'stars': 'powerspec_type4', 'type4': 'powerspec_type4',
    'bh': 'powerspec_type5', 'blackholes': 'powerspec_type5', 'type5': 'powerspec_type5',
    '21cm': 'powerspec_21cm',
    'hii': 'powerspec_HII_frac', 'hii_frac': 'powerspec_HII_frac',
    'hii_fraction': 'powerspec_HII_frac',
}

_COLS = ('k', 'Delta2', 'Power', 'CountModes', 'ShotLimit')

_psDirsCache = {}


def _prefix(kind):
    if kind.startswith('powerspec'):
        return kind
    key = kind.lower().replace(' ', '')
    if key not in _KIND_PREFIX:
        raise ValueError("Unknown power-spectrum kind [%s]. Known: %s (or pass a "
                         "raw 'powerspec*' prefix)" % (kind, sorted(set(_KIND_PREFIX))))
    return _KIND_PREFIX[key]


def psDirs(basePath):
    """List the `powerspectra` directories reachable from basePath."""
    if basePath in _psDirsCache:
        return _psDirsCache[basePath]
    if glob.glob(os.path.join(basePath, 'powerspec*.txt')):
        dirs = [basePath]
    elif os.path.isdir(os.path.join(basePath, PS_SUBDIR)):
        dirs = [os.path.join(basePath, PS_SUBDIR)]
    else:
        dirs = sorted(glob.glob(os.path.join(basePath, '*', PS_SUBDIR)))
    if not dirs:
        raise ValueError("No %s directories found under %s" % (PS_SUBDIR, basePath))
    _psDirsCache[basePath] = dirs
    return dirs


def listKinds(basePath):
    """Power-spectrum prefixes present under basePath."""
    out = set()
    for dirPath in psDirs(basePath):
        for path in glob.glob(os.path.join(dirPath, 'powerspec*.txt')):
            name = os.path.basename(path)[:-4]
            head = name.rsplit('_', 1)
            if len(head) == 2 and head[1].isdigit():
                out.add(head[0])
    return sorted(out)


def listOutputs(basePath, kind='matter'):
    """Output numbers available for a given kind, across the epoch trees."""
    prefix = _prefix(kind)
    nums = set()
    for dirPath in psDirs(basePath):
        for path in glob.glob(os.path.join(dirPath, prefix + '_[0-9]*.txt')):
            tail = os.path.basename(path)[:-4][len(prefix) + 1:]
            if tail.isdigit():
                nums.add(int(tail))
    return sorted(nums)


def filePath(basePath, num, kind='matter'):
    """Path to the power-spectrum file for one output number/kind, or None."""
    prefix = _prefix(kind)
    for dirPath in psDirs(basePath):
        for pattern in ('%s_%03d.txt', '%s_%02d.txt', '%s_%d.txt'):
            path = os.path.join(dirPath, pattern % (prefix, num))
            if os.path.isfile(path):
                return path
    return None


def _parse(path):
    """Parse a Gadget4 power-spectrum file into (folds, trailing)."""
    groups = []          # (is_data, [rows]) contiguous runs
    with open(path) as fh:
        for line in fh:
            toks = line.split()
            if not toks:
                continue
            is_data = len(toks) == 5
            vals = [float(tok) for tok in toks]
            if groups and groups[-1][0] == is_data:
                groups[-1][1].append(vals)
            else:
                groups.append((is_data, [vals]))

    folds, trailing = [], []
    pending = None       # the most recent header (1-column) run
    for is_data, rows in groups:
        if is_data:
            if pending is None:
                raise ValueError("Power-spectrum data block without header in %s" % path)
            hdr = [row[0] for row in pending]  # Time, Nbins, BoxSize, PMGRID[, Growth]
            data = np.asarray(rows, dtype=np.float64)
            fold = {'Time': hdr[0], 'BoxSize': hdr[2], 'PMGRID': int(hdr[3]),
                    'GrowthFactor': hdr[4] if len(hdr) > 4 else None,
                    'nbins': data.shape[0]}
            for idx, name in enumerate(_COLS):
                fold[name] = data[:, idx]
            fold['CountModes'] = fold['CountModes'].astype(np.int64)
            folds.append(fold)
            pending = None
        else:
            # a header precedes data; the last headerless 1-column run is trailing
            if pending is not None:
                trailing = [row[0] for row in pending]
            pending = rows
    if pending is not None:
        trailing = [row[0] for row in pending]
    return folds, trailing


def loadPowerSpectrum(basePath, num, kind='matter', fold=None):
    """Load one power spectrum."""
    path = filePath(basePath, num, kind)
    if path is None:
        raise ValueError("%s has no %s spectrum at output %d; outputs present: %s"
                         % (basePath, _prefix(kind), num, listOutputs(basePath, kind)))
    folds, trailing = _parse(path)
    if not folds:
        raise ValueError("No power-spectrum folds parsed from %s" % path)

    first = folds[0]
    result = {'Time': first['Time'], 'Redshift': 1.0 / first['Time'] - 1.0,
              'BoxSize': first['BoxSize'], 'PMGRID': first['PMGRID'],
              'GrowthFactor': first['GrowthFactor'], 'nfolds': len(folds),
              'folds': folds}
    if len(trailing) >= 3:
        result['Mass'], result['Count'], result['MassCorrection'] = trailing[:3]

    if fold is not None:
        sel = folds[fold]
        for name in _COLS:
            result[name] = sel[name]
        return result

    order = np.argsort(np.concatenate([item['k'] for item in folds]), kind='stable')
    for name in _COLS:
        result[name] = np.concatenate([item[name] for item in folds])[order]
    return result
