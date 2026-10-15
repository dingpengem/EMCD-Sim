# Diffraction-resolved magnetic and nonmagnetic EMCD decomposition

The new `emcd_sim.xmcd_geometry_decomposition` workflow compares diffraction-
modulated magnetic contrast with reversal-even detector asymmetry. It uses
an **XMCD-constrained effective MDFF, entrance-only single-channeling and
relative intensity**. Results are **not quantitatively validated Ni EMCD**.

A magnetic MDFF alone does not determine measured EMCD. The incoming Bloch
waves interfere through the crystal and modulate both the magnetic contrast
and collected nonmagnetic intensity. Reversal parity separates their
contributions within the existing model; it does not remove diffraction
from magnetic EMCD or establish a geometry-independent magnetic response.

## Definitions and metrics

The existing `run_xmcd_reversal` constructs effective tensors at eta and -eta:
Tplus=Tnonmag+Tmag, Tminus=Tnonmag-Tmag. The diagonals remain (N,N,beta*N),
where N=(RP+LP)/2; Txy=+i*eta*(RP-LP)/2 changes sign, with Tyx=-Txy.
Both tensors use the same source peak N normalization. This is a model-level
sign reversal, not a separately calculated DFT magnetic state.

For the existing physical A/B detector groups:

```text
Delta_plus  = I_A_plus - I_B_plus
Delta_minus = I_A_minus - I_B_minus
Delta_mag    = (Delta_plus - Delta_minus)/2
Delta_nonmag = (Delta_plus + Delta_minus)/2
Sigma_ref = [(I_A_plus + I_B_plus) + (I_A_minus + I_B_minus)]/2
A_mag    = Delta_mag / Sigma_ref
A_nonmag = Delta_nonmag / Sigma_ref
```

`Delta_plus=Delta_mag+Delta_nonmag` exactly up to numerical precision.
`A_raw_plus` and `A_raw_minus` retain their own detector-sum denominators.
Thus `A_raw_plus` need not equal `A_mag+A_nonmag`. Inherited normalized
signals are NaN, with false validity masks, for denominators at or below
1e-12 times the peak over the tiny evaluated energy grid.

The complementary contribution diagnostics are:

```text
f_mag = abs(Delta_mag) / [abs(Delta_mag) + abs(Delta_nonmag)]
R_mag_nonmag = abs(Delta_mag) / abs(Delta_nonmag)
```

`f_mag` is a bounded index of the magnitudes of detector-difference
contributions. It is not a fraction of detected electrons and does not
retain their relative signs or cancellations. `R_mag_nonmag` is a contrast
ratio, not an experimental detectability or signal-to-noise measure.
`Sigma_ref` is retained alongside both metrics: a large normalized contrast
may have little collected intensity.

For numerical robustness, each metric's denominator must exceed
`1e-12*max(abs(Sigma_ref),abs(Delta_mag),abs(Delta_nonmag))` at that sample.
Otherwise it is NaN with a false `valid_f_mag` or `valid_R_mag_nonmag` mask.
Both zero contributions give undefined f_mag. A negligible even denominator
gives an undefined ratio rather than a misleading enormous finite value.
No calibrated count rates, noise estimates, or magnetic moments are inferred.

The reciprocal maps separately contain
`I_mag(q)=(I_plus(q)-I_minus(q))/2` and
`I_nonmag(q)=(I_plus(q)+I_minus(q))/2`.
The latter is an even **intensity map**, not the detector difference
Delta_nonmag. A large even map can integrate to almost zero even difference
between symmetric detector groups. Map aliases I_odd/I_even and the paired
total maps are retained for reconstruction.

## Physical geometry versus basis approximation

Group A (`A-matched-2d`) uses one common, untruncated-by-cap 2D ZOLZ selection
for all nominal geometries. The default cutoff of 1.4 cycles/angstrom selects
21 beams. `BeamSet.zolz` and the existing Ni physical elastic potential are
used directly; there is no new propagation or MDFF kernel.

- Zone-axis: zero incident tilt by default, with the existing zone-axis A/B
  aperture positions.
- Two-beam and near-2BC: identical near-2BC nominal tilt and A/B apertures.
  At 200 kV the default tilt is (-7.11672544,25) mrad. Their Group A numerical
  inputs and results coincide. These labels are not independent physical
  geometries when the same 2D basis is propagated.
- Symmetric-3BC: nominal tilt (0,25) mrad and four apertures with
  A=RU+LD, B=RD+LU. This remains an illustrative finite-basis geometry,
  not an independently established experimental three-beam alignment.

Group B (`B-truncation-reference`) retains the original two-beam basis
(000,+200) at the same 2BC physical tilt and apertures. Its difference from
matched-2D 2BC isolates the **change of finite basis**, not a new incident
geometry. Plots and data distinguish the two groups. No systematic-row or
largest-ZOLZ result is treated as a validated reference. The existing
[basis comparison guide](XMCD_BASIS_CONVERGENCE.md) explains systematic-row
versus 2D truncation and their sensitivity to off-row diffraction.

## Reproduce on Windows CMD, macOS and Linux

Use the existing environment or install the package from the repository root:

```text
python -m pip install -e ".[dev]"
python -m emcd_sim.xmcd_geometry_decomposition --xmcd-file data/wien2k_ni/Ni_fm.xmcd --cutoff 1.4 --grid 65 --steps 64 --finer-grid 97 --output outputs/ni_xmcd_geometry_decomposition
```

These are single-line commands without platform-specific continuations.
Default thickness is 30 nm, acceleration 200 kV, eta=beta=1. The source sample
nearest L3=852.7 eV is selected; `--l2-energy-ev 870` adds L2. Only the selected
edge samples and, if needed, one adjacent support sample are calculated.
No full 185-energy spectrum or parameter sweep is run.

`--conditions near-2bc symmetric-3bc` selects a subset of Group A; Group B
is still included separately. `--thickness-nm`, `--acceleration-kv`, `--eta`,
`--beta`, `--cutoff` and `--max-beams` expose the physical/model controls.
The beam cap is checked for pair clipping. `--offzone-tilt-mrad` changes the
non-zone preset y component. Optional `--tilt-x-mrad` and `--tilt-y-mrad` are
absolute overrides applied to every selected nominal geometry, including
zone-axis; actual tilts are always recorded. One thickness and one tilt per
geometry are calculated, with no multidimensional scan.

By default a single matched near-2BC case is repeated on a 97x97 grid at the
same depth sampling, basis and physical parameters. If near-2BC is omitted,
the first selected Group A geometry is used. `--skip-finer-grid` disables
this check and records `not-checked`. Refinement must be larger than the
baseline grid. `--grid-atol` (default 1e-4 fractional asymmetry) and
`--grid-rtol` (default 0.05) control the explicit sensitivity flag:

```text
abs(A_fine-A_base) > grid_atol + grid_rtol*max(abs(A_fine),abs(A_base))
```

Sigma_ref uses only the relative tolerance, since it has different units.
Any failed or undefined tested observable marks the grid check `unresolved`.
Passing means limited agreement for **only the tested geometry and grids**;
it does not verify grid, depth, or beam-basis convergence for the workflow.
The numerical thresholds are configurable diagnostics, not experimental
error tolerances. Every aperture's coordinates, physical radius and included
grid-point count are saved. Aperture radii are never enlarged to fit a grid.

The Python API separates computation, comparison, saving and plotting:

```python
from emcd_sim.xmcd_geometry_decomposition import (
    GeometryDecompositionConfig, run_geometry_decomposition,
    save_geometry_decomposition, plot_geometry_decomposition,
)
result = run_geometry_decomposition("data/wien2k_ni/Ni_fm.xmcd",
                                   GeometryDecompositionConfig())
save_geometry_decomposition(result, "outputs/ni_xmcd_geometry_decomposition")
plot_geometry_decomposition(result, "outputs/ni_xmcd_geometry_decomposition")
```

`compare_geometry_results` reports coincident-geometry equality, absolute
matched-versus-truncated differences and the grid refinement. Calculation
returns `GeometryDecompositionResult(records, maps, metadata)` without writes.

## Outputs

The output directory contains `geometry_comparison.csv`,
`geometry_comparison.npz`, and `geometry_metadata.json`, plus one
`<group>_<condition>_<sampling-role>_<edge>_maps.npz` per calculated map.
Records include both raw asymmetries, all paired detector intensities,
magnetic/even differences and normalized signals, Sigma_ref, both contribution
metrics, validity masks, detector geometry/pixel counts, actual tilt, basis
hkl/count, energy and sampling. Existing parity field names are retained
alongside the new A_mag/A_nonmag aliases. NPZ uses no pickled objects;
structured detector/basis fields are JSON strings in the flat table.

Metadata records the exact XMCD byte SHA256, source normalization, selected
and requested energies, all geometries/bases and exit elastic intensities,
software commit and dirty-worktree flag, Python version, numerical settings,
comparison checks and approximation flags. Development-run metadata correctly
identifies its base commit with a dirty worktree, rather than claiming the
new module was present in that base commit. The unchanged Windows CRLF source
hash is `bb9bdd478d54cc8de60403409f4d90e63deb11a64891bbac6754f867be14deda`;
see the [existing provenance investigation](XMCD_MAGNETIC_REVERSAL_DIAGNOSTICS.md#source-provenance).

`magnetic_odd_maps.png` and `nonmagnetic_even_maps.png` share reciprocal axes
and a common color scale per energy across all baseline conditions. Odd maps
use a diverging scale centered at zero. Elastic spot markers (size indicates
exit elastic intensity), hkl annotations and aperture outlines are overlaid;
only reflections inside the fixed +/-1 cycles/angstrom map window are shown.
All basis reflections remain in metadata/NPZ. Weak panels under the shared
scale do not establish zero magnetic response. `geometry_asymmetry_comparison.png`
compares the three normalized contrasts with separate panels for Groups A/B.
`magnetic_contribution_comparison.png` presents f_mag, ratio and Sigma_ref in
separate columns to avoid combining different units on a single vertical axis.
Finer-grid data are retained separately from baseline geometry comparisons.

## Executed selected-L3 example

One integration smoke test ran five baseline cases and one grid refinement
with the command's defaults, at the actual source sample **852.698 eV**.
Its artifacts were copied unchanged from the temporary test directory to
`outputs/ni_xmcd_geometry_decomposition/`. No extra production sweep ran.

| Group / condition | A_raw_plus | A_mag | A_nonmag | Sigma_ref | f_mag |
| --- | ---: | ---: | ---: | ---: | ---: |
| A / zone-axis | 0.000257793 | 0.000257793 | -3.74e-16 | 0.0185667 | ~1 |
| A / two-beam = near-2BC | -0.108320 | 0.0324755 | -0.139575 | 0.0229444 | 0.188755 |
| A / nominal symmetric-3BC | 0.00606865 | 0.00606865 | -5.33e-17 | 0.0651345 | ~1 |
| B / truncated two-beam | 0.00982992 | 0.00982992 | 9.70e-17 | 0.0357793 | ~1 |

The matched near-2BC detector difference is predominantly even by the defined
magnitude index (R_mag_nonmag=0.232674), despite its substantial odd contrast.
Zone-axis and nominal symmetric-3BC differences are predominantly odd in this
calculation; their even contrast ratios are undefined because the even
contribution is at roundoff level. These results do not rank experimental
signal-to-noise or establish an optimal alignment. The four-aperture
symmetric-3BC Sigma_ref includes four physical apertures, while zone-axis
and near-2BC collect through two; collected intensities reflect that geometry.
The truncated two-beam approximation changes A_mag by 0.0226456 and A_nonmag
by 0.139575 relative to matched 2D at the same incident geometry.

At baseline, zone-axis A/B each include **26 pixels**; all 2BC apertures and
all four symmetric-3BC apertures each include **24 pixels**. The 97x97
near-2BC check includes **58 pixels per aperture**. It gives A_mag=0.0323759,
A_nonmag=-0.139256, and Sigma_ref=0.0247435. The magnetic asymmetry changes
by 9.96e-5, while Sigma_ref increases by approximately **7.84%** relative
to baseline. The workflow therefore marks sampling **unresolved**, driven
by collected intensity even though normalized asymmetries change modestly.
No refinement result for the other geometries is inferred from this check.

Earlier 25x25/20-step values used different grid and depth sampling. Differences
from those values cannot be attributed to grid alone. This 65-to-97 comparison
holds depth sampling fixed at 64; depth and beam-basis convergence remain
unverified, and cancellation or weak components can require further checks.

## Focused verification and remaining physical limits

```text
python -m pytest -q tests/test_xmcd_geometry_decomposition.py
```

**5 tests passed** using **Python 3.10.9**, including synthetic eta reversal,
eta=0, odd/even reconstruction, map parity/axes, source normalization, four-
aperture grouping, coincident matched 2BC/near-2BC, the distinct truncation
reference, numerical floor/invalid metrics, grid-status policy, and one
real-source integration smoke test checking saved CSV/NPZ/metadata/figures.
Python 3.11 was unavailable for direct runtime testing; compatible language
and standard-library interfaces are used. No broad regression campaign ran.

The existing scattering conventions, potential, site phases, angular-Q
conversion, Coulomb factors and longitudinal-transfer approximation are
unchanged. Limits include finite ZOLZ bases, a perfect-crystal independent-
atom elastic model without absorption/TDS, the axisymmetric dipole proxy,
assumed beta and uncalibrated eta handedness. There is no outgoing channeling,
full DFT-MDFF, absolute cross section, quantitative magnetization or verified
experimental Ni prediction. No existing published results were modified;
this focused patch does not merge, tag a release or initiate further scans.
