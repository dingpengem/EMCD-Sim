# Matched-basis XMCD magnetic-parity diagnostics

`emcd_sim.xmcd_basis_convergence` compares the existing systematic-row and
2D ZOLZ incoming Bloch-wave approximations at identical physical geometry.
It reuses `BeamSet.zolz`, the Ni physical independent-atom potential,
`run_xmcd_reversal` and the existing tensor contraction. The historical
Gaussian convergence workflow and published examples are unchanged.

The default geometry is FCC Ni [001], 200 kV, 30 nm, the near-2BC x tilt
(-7.116725439974256 mrad at 200 kV), and the existing near-2BC A/B apertures.
The y tilts are 0 and 25 mrad. Only the beam basis changes within each
fixed-tilt comparison. The seven-beam systematic row is compared with 2D
cutoffs 0.75, 1.2 and 1.4 cycles/angstrom, selecting 5, 13 and 21 beams.
The seven-beam row extends to +/-600, so it is not a subset of all these 2D
bases. Its comparison measures differences between finite approximations,
not the effect of simply adding off-row beams to an otherwise identical set.
Only the increasing 2D cutoff sequence is nested.

A near-2BC incident geometry propagated with a 2D ZOLZ basis is not an exact
two-beam truncation. `condition=near-2bc` names the incident geometry and
apertures; `basis_kind` separately identifies the propagated channels.

## Tilt dependence

The unchanged physical Hamiltonian has diagonal

```text
H_gg = -10*pi*lambda*(|g|^2 + 2*k_perp dot g)  [nm^-1]
```

Its off-diagonal potential terms do not depend on incident tilt. At fixed
x tilt, changing y tilt gives

```text
delta H_gg = -20*pi*lambda*delta k_y*g_y
           = -0.02*pi*delta tilt_y_mrad*g_y.
```

All systematic-row beams have gy=0: the Hamiltonian and incoming propagation
are y-tilt independent, up to floating-point cancellation in the implemented
squared-norm expression. A 2D basis with off-row reflections has nonzero gy
and can respond. The inelastic map coordinates remain referenced to 000;
the diagnostic does not add another incident-tilt subtraction.

The focused test verifies the full Hamiltonian difference against the
analytic diagonal, row propagation invariance, and a change in elastic
intensities for an off-row basis. Saved `hamiltonian_change_vs_y0` is the
maximum absolute matrix-element change (nm^-1) at fixed basis/x tilt.
Zero y tilt is the reference even when not included among requested runs.

## Magnetic parity and sampling

The paired tensors use eta and -eta with identical N=(RP+LP)/2, beta and
source-peak normalization. Only the effective antisymmetric magnetic tensor
changes. This is not a separately computed DFT reversed magnetic state.
The [reversal guide](XMCD_MAGNETIC_REVERSAL_DIAGNOSTICS.md) defines all parity
quantities and sign conventions.

Each record contains A_raw_plus/minus, A_odd, A_even, the individual detector
spectra, unnormalized differences, sigma_plus/minus/ref, and validity masks.
A_odd and A_even share sigma_ref; raw asymmetries use their own denominators.
Their separately normalized odd part is generally not A_odd. Undefined
normalization remains NaN with a false mask; even asymmetry is not required
to be nonzero at every tilt or cutoff.

The nearest original source sample to 852.7 eV is selected by default.
Optional L2 selects the nearest source sample to its requested reference.
Both requested and actual energies are recorded. Only these selected samples
are used, with an adjacent source support sample if needed to satisfy the
existing two-point tensor interface. No 185-energy spectrum is calculated.
Both map reference arguments passed to the existing reversal function point
to the selected L3 sample when L2 is omitted. This preserves that function's
API without interpreting the support sample as an L2 measurement.

Defaults use a deliberately small 25x25 grid and 20 depth steps. These are
smoke-test sampling settings, not evidence of numerical convergence. They
can underresolve fast oscillations, particularly for strongly excited
high-order beams at large tilt. Refine sampling separately before physical
interpretation; do not attribute sampling sensitivity to physical effects.

## Run on Windows CMD, macOS or Linux

From the repository root in the existing Python environment:

```text
python -m pip install -e ".[dev]"
python -m emcd_sim.xmcd_basis_convergence --xmcd-file data/wien2k_ni/Ni_fm.xmcd --g-cutoffs 0.75 1.2 1.4 --y-tilts-mrad 0 25 --grid 25 --steps 20 --output outputs/ni_xmcd_basis_convergence
```

These single-line commands require no platform-specific continuation syntax.
Additional y tilts can be supplied with `--y-tilts-mrad 0 5 25`.
`--l2-energy-ev 870` includes L2. The CLI also exposes `--eta`, `--beta`,
`--thickness-nm`, `--acceleration-kv`, `--beam-order`, `--max-beams`,
`--l3-energy-ev`, `--grid` and `--steps`. Changing voltage recalculates the
near-2BC x tilt using the existing preset; x tilt is then fixed across bases.
The selected full cutoff sets are checked for beam-cap clipping, including
pair truncation below an even cap. Increase `--max-beams` if rejected.

The reusable Python API separates calculation from saving and plotting:

```python
from emcd_sim.xmcd_basis_convergence import (
    BasisConvergenceConfig, run_basis_convergence, save_basis_convergence,
)
config = BasisConvergenceConfig(y_tilts_mrad=(0., 25.))
records, metadata = run_basis_convergence("data/wien2k_ni/Ni_fm.xmcd", config)
save_basis_convergence(records, metadata, "outputs/ni_xmcd_basis_convergence")
```

## Outputs and comparisons

The output directory contains:

- `convergence_results.csv`: one row per basis, y tilt and selected edge;
  actual basis and full elastic intensities are JSON columns.
- `convergence_results.npz`: the same scalar records and padded `beam_hkl`,
  `elastic_intensity`, `beam_valid` arrays. Slice by `beam_valid` or beam
  count; padded 000 entries are not physical extra transmitted beams.
- `convergence_metadata.json`: input-byte SHA256, common source peak N,
  basis definitions, actual energies, shared apertures, physical settings,
  numerical sampling, approximation flags, Python version and Git commit.
- `basis_parity_comparison.png`: raw-plus, odd and even asymmetry versus
  beam count, with y tilt indicated separately and row points as crosses.

`*_abs_diff_previous` compares successive **ZOLZ** cutoffs at the same
energy/tilt; it is NaN for the row and first ZOLZ set. `*_abs_diff_largest`
compares every basis against the last ZOLZ set. `*_abs_diff_row` compares
against the systematic row. These are absolute differences in the
fractional asymmetries or selected normalized elastic intensities, not
relative errors. Differences are retained for raw-plus, raw-minus, odd,
even and elastic 000, +200, -200, +020 intensities. Missing selected
reflections have NaN intensity and NaN scalar discrepancy.

`elastic_tv_previous/largest/row` reuse the existing full elastic-intensity
total-variation convention: half the sum of absolute intensity differences
on the union of hkl, treating absent channels as zero. This is a measure of
finite-basis disagreement, not an experimental or infinite-basis error bound.
Cutoffs selecting identical bases can agree trivially; such agreement does
not establish convergence.

## Executed small reference result

One CLI smoke test ran the default eight geometries with the repository
source, eta=beta=1, 25x25 grid and 20 depth steps. Selected L3 was **852.698 eV**.
The four generated artifacts were copied unchanged from that test's temporary
directory to `outputs/ni_xmcd_basis_convergence/`; no additional campaign ran.

| Basis | y tilt (mrad) | A_raw_plus | A_odd | A_even |
| --- | ---: | ---: | ---: | ---: |
| Row, 7 beams | 0 | 0.00166982 | 0.00166982 | 1.59e-16 |
| Row, 7 beams | 25 | 0.00166982 | 0.00166982 | 1.19e-16 |
| ZOLZ 0.75, 5 beams | 0 | 0.00234952 | 0.00234952 | 2.53e-16 |
| ZOLZ 0.75, 5 beams | 25 | -0.131619 | 0.0103211 | -0.141850 |
| ZOLZ 1.2, 13 beams | 0 | -0.0193456 | -0.0193456 | 4.89e-16 |
| ZOLZ 1.2, 13 beams | 25 | -0.100664 | 0.0139464 | -0.114325 |
| ZOLZ 1.4, 21 beams | 0 | -0.0294123 | -0.0294123 | 2.12e-16 |
| ZOLZ 1.4, 21 beams | 25 | -0.112572 | 0.0328921 | -0.144192 |

At fixed y=0, the absolute odd-asymmetry change from 13 to 21 ZOLZ beams is
0.0100667; at fixed y=25 mrad it is 0.0189457. Corresponding elastic total
variation is 0.274503 and 0.333298. At fixed 21-beam basis, changing y from
0 to 25 mrad changes A_odd by 0.0623044 and elastic I000 from 0.262677 to
0.0773044. The row Hamiltonian changes by at most 2.22e-16 nm^-1; the 21-beam
Hamiltonian changes by 1.78297 nm^-1. Thus basis truncation and incident
y tilt have separable, substantial effects in this small sampled calculation.
The row prediction is not stable across the tested alternative bases;
additional sampling/beam checks would be needed to establish convergence.

The default selected energy differs from the earlier reversal command's
852.6522 eV (185-point resampled grid). These are not identical-energy
cross-run comparisons. All records within this diagnostic share 852.698 eV.

The exact Windows source-byte SHA256 was
`bb9bdd478d54cc8de60403409f4d90e63deb11a64891bbac6754f867be14deda`.
This is the CRLF checkout of the committed LF blob `4fd517af...`; see the
existing reversal provenance investigation. Source data were not rewritten.

## Focused verification and limitations

```text
python -m pytest -q tests/test_xmcd_basis_convergence.py
```

Four tests passed using **Python 3.10.9**, including analytic/numerical tilt
checks, synthetic eta=0 and reversal checks, matched detector/source settings,
beam-cap checks, optional L2 selection and one real-source temporary-directory
CLI smoke test with CSV/NPZ/metadata verification. Python 3.11 was unavailable
for direct testing; the code uses compatible standard-library interfaces.

All output remains **XMCD-effective, entrance-only, relative intensity, not
quantitatively validated Ni EMCD**. Finite ZOLZ omits higher Laue zones;
perfect-crystal independent-atom propagation omits absorption/TDS; the tensor
is an axisymmetric XMCD proxy with assumed beta and uncalibrated eta sign.
No outgoing channeling, full DFT-MDFF, absolute calibration, magnetic moments
or validated quantitative reference is added. The largest finite basis is
only a comparison point. This patch does not perform broad convergence
sweeps, regenerate published examples, merge into main or create a release.
