# lumina_io.powerspectra

Power-spectrum loading (the LUMINA powerspectra data product).

Layout (one tree per epoch, e.g. `<root>`/Lumina_above_z_4p75):

> powerspectra/`<prefix>`_NNN.txt

These are Gadget4 power-spectrum text files. Several species/observables are
written under different prefixes:

> powerspec            total matter
> powerspec_type0      gas         powerspec_type1   dark matter
> powerspec_type4      stars       powerspec_type5   black holes
> powerspec_21cm       21 cm brightness temperature
> powerspec_HII_frac   HII fraction

(Which prefixes exist depends on the epoch.) Unlike the snapshots/grids, the
NNN index is the power-spectrum *output* counter – its own, coarser cadence
that runs continuously across the epoch trees (it is not the snapshot number),
so match outputs by redshift via the per-file header if needed.

Each file holds up to three Fourier “folds” concatenated (Gadget4 writes the
unfolded spectrum, then two successively folded ones that extend the
measurement to higher k). Every fold is a 4- or 5-line header followed by
`count_non_zero_bins` rows of:

```default
k   Delta2   Power   CountModes   ShotLimit
```

(`Delta2` and `Power` are the shot-noise-uncorrected dimensionless and raw
power; `ShotLimit` is the shot-noise level). After the last fold three
scalars are appended: total mass, particle count, and mass^2/sum(mass^2).

basePath may be the powerspectra directory itself, an epoch directory, or
the root holding the epoch trees. Example:

```default
import lumina_io as lumina
base = '/orcd/data/mvogelsb/005/Lumina'

ps = lumina.powerspectra.loadPowerSpectrum(base, 100)         # total matter
k, P = ps['k'], ps['Power']                                   # all folds, k-sorted
print(ps['Redshift'], ps['BoxSize'])

gas = lumina.powerspectra.loadPowerSpectrum(base, 100, 'gas')
f0  = lumina.powerspectra.loadPowerSpectrum(base, 100, fold=0)['Power']  # unfolded only

nums = lumina.powerspectra.listOutputs(base, 'dm')
```

## Functions

| [`psDirs`](#lumina_io.powerspectra.psDirs)(basePath)                                          | List the powerspectra directories reachable from basePath.                                   |
|---------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------|
| [`listKinds`](#lumina_io.powerspectra.listKinds)(basePath)                                    | Power-spectrum prefixes present under basePath (e.g. ['powerspec', 'powerspec_type0', ...]). |
| [`listOutputs`](#lumina_io.powerspectra.listOutputs)(basePath[, kind])                        | Output numbers available for a given kind, across the epoch trees.                           |
| [`filePath`](#lumina_io.powerspectra.filePath)(basePath, num[, kind])                         | Path to the power-spectrum file for one output number/kind, or None.                         |
| [`loadPowerSpectrum`](#lumina_io.powerspectra.loadPowerSpectrum)(basePath, num[, kind, fold]) | Load one power spectrum.                                                                     |

## Reference

### lumina_io.powerspectra.psDirs(basePath)

List the powerspectra directories reachable from basePath.

basePath may be a powerspectra directory itself (contains powerspec\*.txt),
an epoch directory containing powerspectra, or a root whose
subdirectories do (output numbering runs across the epoch trees, so all
are searched).

### lumina_io.powerspectra.listKinds(basePath)

Power-spectrum prefixes present under basePath (e.g.
[‘powerspec’, ‘powerspec_type0’, …]).

### lumina_io.powerspectra.listOutputs(basePath, kind='matter')

Output numbers available for a given kind, across the epoch trees.

### lumina_io.powerspectra.filePath(basePath, num, kind='matter')

Path to the power-spectrum file for one output number/kind, or None.

### lumina_io.powerspectra.loadPowerSpectrum(basePath, num, kind='matter', fold=None)

Load one power spectrum.

num:  power-spectrum output number (its own counter; see listOutputs).

kind: species/observable – ‘matter’ (default), ‘gas’, ‘dm’, ‘stars’,
: ‘bh’, ‘21cm’, ‘HII_frac’, a ‘typeN’ alias, or a raw ‘powerspec\*’
  prefix.

fold: None (default) returns all folds unioned and sorted by k; an int
: 0/1/2 returns just that Fourier fold (0 = unfolded). Folds overlap
  in k – use the per-fold arrays in result[‘folds’] for rigorous,
  non-duplicated work.

Returns a dict with column arrays ‘k’, ‘Delta2’, ‘Power’, ‘CountModes’,
‘ShotLimit’; header scalars ‘Time’, ‘Redshift’, ‘BoxSize’, ‘PMGRID’,
‘GrowthFactor’; the trailing ‘Mass’, ‘Count’, ‘MassCorrection’ (when
present); ‘nfolds’; and ‘folds’ (the list of per-fold dicts).
