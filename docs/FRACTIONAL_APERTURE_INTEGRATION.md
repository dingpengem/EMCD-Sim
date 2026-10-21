# Shared fractional circular-aperture integration

The tensor single-channeling paths now support optional `fractional` aperture
integration alongside the historical default `binary` mode. This patch
changes detector quadrature only. Bloch/FFT propagation, incident coherence,
site phases, XMCD-effective tensors and normalization, angular-Q conversion
and Coulomb factors are unchanged.

Results remain **XMCD-constrained effective MDFF, entrance-only, relative
intensity, not quantitatively validated Ni EMCD**.

## Geometry and interfaces

For a pixel centered at q_p with spacing dx,dy, the fractional weight is an
approximation to its circular-aperture overlap area divided by dx*dy:

```text
w_p = area(pixel intersect aperture) / area(pixel)
I_D(E) = sum_p w_p I(q_p,E) dq^2
```

The existing tensor grids are square, so dx=dy=dq. A geometric nearest/farthest
corner test assigns weight 1 to fully inside pixels and 0 to wholly outside
pixels. Only boundary pixels use deterministic midpoint sampling: by default
64 subpixels per axis (4096 samples per boundary pixel). Weights stay in
[0,1]; they are never scaled to force the analytic area pi*r^2. A bounded
geometry-only cache keyed by the physical circle, exact grid axes, mode and
subpixel resolution reuses read-only arrays across energies, eta/-eta states,
and BW/MS coherences. Temporary sampling arrays are limited to boundary
pixels and one row of subpixel samples at a time.

`VirtualDetector.mask` remains Boolean center membership, unchanged.
`VirtualDetector.integration_weights(qx,qy,mode=...,subpixels=...)` is a
separate API for increasing uniform Cartesian xy grids. Pixel cells extend
half a spacing beyond the outer centers. `integration_info` reports effective
and analytic area, error, weight sum, nonzero-weight pixel count and whether
the circle is fully covered by that domain. A clipped aperture is reported
as clipped; its weights are not renormalized to an unclipped circle.
Finite subpixel sampling can miss extremely small intersections; increasing
the subpixel resolution controls this separate geometric approximation.

`run_tensor_with_coherence`, `run_tensor_single_channeling` and
`run_xmcd_reversal` accept optional `integration_mode='binary'` and
`aperture_subpixels=64` keywords. Their existing arguments remain valid.
Binary mode retains the original `total[mask].sum()*dq^2` reduction, including
its summation order. Fractional mode uses `sum(total*weights)*dq^2`.
`SimulationResult.detector_masks` retains its original meaning; new optional
`detector_weights`, `integration_mode` and `aperture_subpixels` fields record
tensor integration separately. Existing positional constructors remain valid.
The legacy Gaussian simulation/CLI behavior is unchanged.

Geometry-decomposition and multislice-reference configuration objects append
the same optional controls. Their CLIs, and the reversal CLI, accept
`--integration-mode binary|fractional` and `--aperture-subpixels N`.
The same chosen mode applies to all physical apertures and both reversal
states; BW and MS use the same geometry cache. Four-aperture symmetric-3BC
still groups A=RU+LD and B=RD+LU. Existing commands remain binary unless the
new option is selected. New metadata records the method, subpixel resolution
and effective areas without changing old detector positions or radii.

## Reproduce the focused validation

From the repository root, using the existing Python environment, this
single-line command works in Windows CMD, macOS and Linux:

```text
python scripts/research/fractional_aperture_validation.py --xmcd-file data/wien2k_ni/Ni_fm.xmcd --aperture-subpixels 64 --output outputs/ni_fractional_aperture_validation
```

Install first with `python -m pip install -e ".[dev]"` if needed.
The validation first integrates a uniform field at 33,65,97 points. It then
calls the geometry-decomposition workflow for near-2BC, 200 kV, 30 nm,
eta=beta=1, 21 ZOLZ beams (cutoff 1.4 cycles/angstrom), selected source L3,
64 depth steps and grids 65/97 in each mode. The geometry workflow also
computes its small legacy two-beam reference, but this validation table
retains only its matched 2D near-2BC case. Optional `--grids 65 97 129` adds
129; this was not needed or run for the patch.

The final method check uses the existing matched-potential BW/MS reference:
near-2BC, 30 nm, potential cutoff 0.75 cycles/angstrom, common beam cutoff
2.2 (45 beams), FFT grid 32, maximum slice step 0.04 nm, 64 depth samples and
**detector grid 33**. Its pair-array estimate stays at 134.6 MiB, below the
existing 512-MiB guard. The full FFT basis is not expanded into a dense
inelastic contraction. This case has a deliberately different potential
from the 21-beam geometry example: compare methods within each case, not
physical values between the two benchmarks.

For normal workflow use, for example:

```text
python -m emcd_sim.xmcd_geometry_decomposition --xmcd-file data/wien2k_ni/Ni_fm.xmcd --conditions near-2bc --integration-mode fractional --aperture-subpixels 64 --grid 65 --steps 64 --finer-grid 97 --output outputs/ni_fractional_aperture_validation/geometry
python -m emcd_sim.multislice_emcd_reference --xmcd-file data/wien2k_ni/Ni_fm.xmcd --conditions near-2bc --thickness-nm 30 --integration-mode fractional --detector-grid 33 --output outputs/ni_fractional_aperture_validation/methods
```

These illustrative commands are not additional executed campaigns. The
validation module provides calculation, saving and plotting functions
separately: `run_fractional_aperture_validation`,
`save_fractional_aperture_validation`, `plot_fractional_aperture_validation`.

## Executed numerical comparisons

The near-2BC radius is unchanged at 0.09080590238365494 cycles/angstrom;
its analytic area is **0.025904667952879202 (cycles/angstrom)^2**. A/B circles
have the same effective areas within numerical precision.

| Grid | Binary area | Binary error (%) | Fractional area | Fractional error (%) |
| --- | ---: | ---: | ---: | ---: |
| 33 | 0.01562500 | -39.6827 | 0.02589512 | -0.0368630 |
| 65 | 0.02343750 | -9.52403 | 0.02590442 | -0.000968609 |
| 97 | 0.02517361 | -2.82210 | 0.02590402 | -0.00250256 |

These are uniform-field area errors, not intensity or asymmetry errors.
The fractional area error is small but not strictly monotonic with grid
size; the subpixel geometric approximation also has finite resolution.

The selected L3 source sample was **852.698 eV**, with near-2BC tilt
(-7.116725439974256,25) mrad. The geometry workflow gave:

| Mode / grid | Sigma_ref | A_mag | A_nonmag | A_raw_plus | f_mag |
| --- | ---: | ---: | ---: | ---: | ---: |
| Binary / 65 | 0.02294439 | 0.03247551 | -0.13957544 | -0.10832021 | 0.18875522 |
| Binary / 97 | 0.02474346 | 0.03237589 | -0.13925577 | -0.10809595 | 0.18863586 |
| Fractional / 65 | 0.02546727 | 0.03231727 | -0.13943014 | -0.10832913 | 0.18816743 |
| Fractional / 97 | 0.02544933 | 0.03234921 | -0.13945000 | -0.10831773 | 0.18829662 |

Signed 65-to-97 changes are:

| Quantity | Binary change | Fractional change |
| --- | ---: | ---: |
| Sigma_ref | +0.00179907 (+7.84098%) | -0.0000179399 (-0.0704431%) |
| A_mag | -9.96295e-5 | +3.19420e-5 |
| A_nonmag | +3.19668e-4 | -1.98586e-5 |
| A_raw_plus | +2.24263e-4 | +1.14048e-5 |
| f_mag | -1.19354e-4 | +1.29191e-4 |

The collected-intensity grid change is roughly **111 times smaller** in
magnitude. The normalized contrast changes also decrease for the three
asymmetries, but **not every derived metric becomes less sensitive**:
f_mag changes slightly more in magnitude. It is a ratio of two detector-
difference magnitudes; cancellation and field sampling still matter. No
monotonic convergence guarantee is inferred from two grids.

In the matched-potential 33-point BW/MS check:

| Mode | abs BW-MS A_mag difference | abs BW-MS A_nonmag difference | abs BW-MS Sigma_ref difference |
| --- | ---: | ---: | ---: |
| Binary | 4.89316e-7 | 8.83682e-5 | 9.13761e-7 |
| Fractional | 5.24478e-7 | 8.82602e-5 | 1.53710e-6 |

Both incident amplitude arrays and coherence matrices are bitwise identical
between binary and fractional runs; reciprocal maps are also unchanged.
Only aperture integration differs. Agreement between propagation methods
is preserved at a similar discrepancy level. The original finite Bloch
basis and split-step residuals remain; fractional weights do not fix those.

## Outputs, tests and limits

All new validation artifacts are separate from published examples:

- `aperture_area_comparison.csv`: both detector areas/errors at 33/65/97.
- `emcd_comparison.csv`: geometry and BW/MS metrics with signed successive-
  grid changes. Detector-area details are retained as JSON columns.
- `fractional_aperture_comparison.npz`: the same compact tables, prefixed
  `area_` and `emcd_`, without pickled objects.
- `validation_metadata.json`: physical configurations, integration method,
  subpixel resolution, actual areas, source hash, software commit/dirty flag,
  common beam bases, sampling and method-discrepancy diagnostics.
- `fractional_aperture_validation.png`: one area-error, collected-intensity,
  asymmetry-change and contribution-index comparison figure.

The exact source SHA256 in this Windows CRLF checkout remains
`bb9bdd478d54cc8de60403409f4d90e63deb11a64891bbac6754f867be14deda`.
Source data and existing published examples were not changed.

```text
python -m pytest -q tests/test_fractional_aperture.py tests/test_single_channeling_tensor.py tests/test_multislice_emcd_reference.py
```

**21 focused tests passed on Python 3.10.9** (8 new cases plus existing tensor
and multislice checks). They cover analytic area accuracy, bounds, exact
inside/outside weights, clipping, nonnegative integration, A/B symmetry,
four-aperture grouping, magnetic parity, cache reuse, unchanged Boolean
masks and binary reductions, unchanged waves/maps/coherences and matched
fractional BW/MS consistency. CSV/NPZ sizes/areas and the generated figure
were also inspected. Python 3.11 was unavailable for direct runtime testing.
No broad regression suite or major sweep ran.

Good area integration does **not** establish convergence of a spatially
varying intensity field: this method holds I(q) constant over each pixel,
including fractional boundary pixels. It resolves geometric boundary area
more accurately while leaving center-sample quadrature error in that field.
Subpixel geometry, detector-grid field sampling, depth integration, beam
basis, FFT resolution and potential cutoff remain distinct controls. The
projected-potential/entrance-only effective model still omits outgoing
channeling, full DFT-MDFF and quantitative experimental calibration. This
patch introduces no new physical model or claim of optimal experimental
geometry and stops after the focused integration milestone.
