# Native energy-resolved double-channeling EELS and EMCD

This development extends production validation and resumable execution of the
existing BW/MS double-channeling adapters. It does not replace either elastic
solver or the XMCD-constrained MDFF. The preceding thickness benchmark saved
two native-energy samples; it did not establish full-spectrum validation.

## Energy and model conventions

The active Ni source contains 4329 samples over **823.625–882.521 eV**. These are
unshifted calculated energies, not an experimental Ni energy calibration. The
standard GUI setting requests 241 uniform samples plus the selected evaluation
energies 831.4778 and 848.698 eV, yielding 242 distinct samples at this setting
(831.4778 is already a uniform-grid sample). Uniform spacing is 0.2454 eV.

The active source SHA-256 is
`a0e28ea6423b6c7832bb3cce6d69d71aa59336a221baeee3d2556b49ba501283`.
The calculations ran from milestone
`fcfa4902ffa7eab600cd026ce50a746363704574` plus the explicitly hashed development
implementation recorded in each `profile.json` and performance record. The
user's source file and the prior benchmark outputs are preserved separately
from the development commit; no source spectrum is silently replaced.

Each requested point uses the existing interpolation of the original 4329-row
MDFF source. No spectrum is inferred from the two previous benchmark outputs.
The source-maximum tensor normalization is independent of the requested energy
grid. Extrapolation, nonfinite/nonincreasing grids and absent selected edge
anchors are rejected. Extra refinement samples can be requested explicitly;
the actual native energy array is always saved.

At each loss E, outgoing elastic propagation uses **E_out = 200000−E eV**, with
the appropriate outgoing wavelength and interaction constant. The longitudinal
transfer remains q_z=−E/(h v_in): it changes with loss energy but remains frozen
across Bloch branches. No branch- or transverse-angle correction to q_z is
introduced. Full complex MDFF interference, site averaging, depth integration
and fractional-aperture integration are retained.

The reference profile is unchanged: potential Fourier cutoff 6.2 Å⁻¹, incoming
and outgoing beam cutoff 4.6 Å⁻¹, FFT 48, 257 depth nodes, maximum MS step
0.04 nm, eta=beta=1, 193² detector grid over ±0.5 Å⁻¹ and 64 boundary subpixels.
Crystallographic reciprocal vectors use g=1/d. [001] uses the explicit (200)
systematic row with the previous fixed off-zone y tilt; [017] retains its full
oriented 2D diffraction basis. Crystal [001] magnetization is rotated into each
local frame. No physical/numerical parameter is reduced for runtime.

## Streaming and reuse

BW now accepts an optional prepared incoming eigensystem/depth field, bound to
the exact elastic object, thickness and depth grid. Its arrays are read-only
and shared across energy/detector workers. The default unprepared core API is
unchanged. Numerical depth contraction reuses the same incoming field; outgoing
eigenproblems remain independent at each loss and detector direction.

MS continues to prepare its full incoming FFT fields once and reuses them
across energies and reversals. It propagates each outgoing reciprocal field
at the actual reduced energy. Both methods compute a Cartesian response once
per energy/direction and contract it with the two verified reversal tensors.
There is no empirical Single-to-Double spectral correction.

The shared GUI adapter can stream compact four-state detector results through
an optional energy-checkpoint callback. Completed energy points are reused;
no dense energy × depth × beam × detector stack is retained. Selected angular
maps, when requested, remain distinct from the full energy-resolved detector
spectra. Memory budgets and available-RAM admission remain active, including
concurrent reservations and allocation margin. Precision remains
float64/complex128. Cancellation keeps completed CLI energy checkpoints.

## Definitions and interpretation

N_J=(I_J(+M)+I_J(−M))/2 and M_J=(I_J(+M)−I_J(−M))/2.
The signed raw differences are D_mag=M_A−M_B and D_nonmag=N_A−N_B; their sum
equals D_raw=I_A(+M)−I_B(+M). Relative components use the common denominator
N_A+N_B. PRB dichroism separately uses 100 D_raw/(I_A(+M)+I_B(+M)). Ratios are
formed after depth and detector integration; undefined values remain NaN.

The GUI retains raw A/B EELS, magnetic/nonmagnetic components, one Raw/Relative
toggle, and a separate PRB readout. Advanced reversal, correction and locking
controls retain their documented meanings. A legacy two-point Double result
remains a two-point result; opening it does not interpolate a full spectrum or
run a new calculation. CSV/NPZ preserve raw and relative quantities regardless
of the displayed mode.

Raw intensities are arbitrary units, not electron counts. Neither a relative
percentage nor an uncalibrated raw curve is experimental SNR. No dose, detector,
background or noise model is added. The MDFF remains XMCD-constrained rather
than a complete complex DFT-derived MDFF; projected IAM and the existing ZOLZ
approximations remain.

## Reproduction

Results are isolated under `outputs/ni_double_channeling_full_spectra/`.

```powershell
python scripts/ni_double_channeling_full_spectra.py --stage pilot
python scripts/ni_double_channeling_full_spectra.py --stage bw
python scripts/ni_double_channeling_full_spectra.py --stage ms
python scripts/ni_double_channeling_full_spectra.py --stage single
python scripts/ni_double_channeling_full_spectra.py --stage ms-full
python scripts/ni_double_channeling_full_spectra.py --stage bw-pilot --case 001_012
python scripts/ni_double_channeling_full_spectra.py --stage bw-pilot --case 017_008
python scripts/ni_double_channeling_full_spectra.py --stage refine --case 001_008
python scripts/ni_double_channeling_spectral_report.py
python scripts/ni_full_spectra_gui_validation.py
```

The initial pilot is preserved separately from the prepared-incoming execution
profile. Every compact checkpoint records its exact energy and profile
identity; source, geometry, integration and implementation provenance accompany
the saved project. A narrowly verified compatibility case accepts only the
addition of cached-row validation, proving all remaining adapter bytes and
other implementation hashes unchanged. Other mismatches reject reuse.

The pilot compares the L3 background (826 eV), locked L3 (831.4778 eV), L3
shoulder (833 eV), locked L2 (848.698 eV), and L2 shoulder (850 eV). Fixed-energy
four-state references reproduce to floating-point precision. Its maximum BW/MS
PRB difference is 0.000022772 pp and raw relative discrepancy 0.000187505%.
Limits remain 0.01 pp and 0.1% raw relative error.

Full-spectrum BW/MS agreement, where calculated, is distinct from independent
beam/potential/FFT/depth convergence over the complete energy range. Selected
MS controls do not certify untested energies. Energy-grid refinement likewise
must distinguish pointwise invariance from the resolution of spectral peak
locations and heights.

## Full-spectrum and GUI acceptance

The complete [001] 8 nm BW/MS comparison passes at **all 242 actual samples**.
The maximum PRB discrepancy is **0.0000228810 percentage points**, and the
maximum four-state raw relative discrepancy is **0.000187573%**. The two old
locked-energy BW references reproduce with maximum relative error
2.12×10⁻¹⁵. This establishes agreement of the two implementations at the stated
profile, not independent full-spectrum cutoff convergence.

At the locked L3/L2 energies, [001] 8 nm Double BW gives:

| Native energy | D_mag (a.u.) | D_nonmag (a.u.) | Magnetic (%) | PRB (%) |
| --- | ---: | ---: | ---: | ---: |
| L3 831.4778 eV | −0.00897982977 | −1.39×10⁻¹⁷ | −13.22777304 | −13.22777304 |
| L2 848.6980 eV | +0.01009555672 | 0 | +22.41544106 | +22.41544106 |

The matched BW comparison retains different observables rather than equating
relative dichroism with raw strength:

| Geometry; thickness | Model | L3 D_mag (a.u.) | L3 magnetic (%) | L3 PRB (%) | L2 D_mag (a.u.) | L2 magnetic (%) | L2 PRB (%) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| [001] row; 8 nm | Single | −0.006901463 | −10.274319 | −10.274319 | +0.007758801 | +17.428818 | +17.428818 |
| [001] row; 8 nm | Double | −0.008979830 | −13.227773 | −13.227773 | +0.010095557 | +22.415441 | +22.415441 |
| [001] row; 12 nm | Single | −0.011961906 | −11.857196 | −11.857196 | +0.013447033 | +20.113153 | +20.113153 |
| [001] row; 12 nm | Double | −0.011017106 | −9.917033 | −9.917033 | +0.012391330 | +16.806274 | +16.806274 |
| [017]; 8 nm | Single | −0.006862520 | −10.231413 | −10.178223 | +0.007715029 | +17.355887 | +17.514347 |
| [017]; 8 nm | Double | −0.008833741 | −13.148782 | −13.060083 | +0.009931250 | +22.280120 | +22.544924 |

In the two sampled [001] thicknesses, the relative L3 signal is stronger at
12 nm for Single and at 8 nm for Double. The Double raw |D_mag| at 12 nm is
nevertheless larger than at 8 nm. The earlier sampled thickness maxima concern
the defined percentage benchmark, not maxima of absolute magnetic intensity
or experimental detectability. These three full-spectrum cases cannot establish
global thickness extrema. For [017], the locked-energy reversal-even A/B
difference is numerically zero, yet PRB and magnetic-only percentages differ.
PRB uses ΣN+M_A+M_B in its denominator, whereas the component percentages use
ΣN. The nonzero common-mode magnetic sum M_A+M_B changes the PRB denominator;
this difference must not be misidentified as reversal-even contamination.
In general PRB = 100(D_mag+D_nonmag)/(ΣN+M_A+M_B).

These selected evaluation energies remain fixed. They are not automatically
the maxima of every observable. In the local refinement, 28 actual samples
are added, including source white-line extrema and 0.1227 eV interleaved
samples near the edges. Every shared coarse-grid raw value is unchanged.
The sampled L3 |D_mag| maximum moves from 831.2324 to **831.2710 eV**, with
magnitude 0.00929138826 → 0.00929993354 a.u. (0.0920% increase).
The sampled L3 B-EELS peak increases by 0.337%; the L2 B-EELS peak increases
by 0.613% at 848.752 eV. Thus 242-point sampling resolves the white lines but
does not establish sub-0.1% accuracy of every sampled spectral maximum.
The L3 PRB extremum changes by 0.00056849 pp and 0.1227 eV; its energy differs
from the raw magnetic maximum. `energy_refinement.json` preserves each result.
Refinement sensitivity is not compared against, or used to relax, the
independent BW/MS agreement thresholds.

Fresh offscreen **EMCDWorker** calculations produce 19 actual native-range
samples for each Single/Double × BW/MS combination. This small GUI validation
uses beam cutoff 0.9 Å⁻¹, potential cutoff 1.8 Å⁻¹, FFT 24, nine depth nodes,
detector grid 9 and 16 aperture subpixels; it is a dispatch/presentation test,
not the production convergence profile. Separately, the saved full 242-point
production spectra are opened in the existing desktop interface without any
recalculation. Both primary modes, Full/L3/L2 zooms, a separate PRB readout,
and PNG/SVG/CSV/NPZ exports are verified. Numerical arrays in Raw and Relative
exports are identical. Screenshots and `checkpoint_2.json` are in
`gui_validation/` beneath the output root.

The production [001] reference is explicitly **class C: [001]-derived,
exact-(200)-Bragg with a systematic-row-restricted basis**. Its absolute tilt
is (−7.11672544, +35.0) mrad, not exact [001] incidence. It contains 17 beams;
the [017] reference contains 59 full finite ZOLZ beams at
(−7.11672544, 0) mrad. The separate
[geometry report](NI_TWO_BEAM_GEOMETRY_COMPARISON.md) tests omitted off-row
elastic populations rather than relabelling the row spectra as full-ZOLZ.

All three Double BW full spectra and the [001] 8 nm Double MS full spectrum
are complete. Matched Single BW full spectra are saved for the three reference
cases; the existing [017] Single project is reused after exact configuration,
crystal and energy checks. Five actual BW/MS pilot energies are compared at
[001] 12 nm and [017] 8 nm, including off-grid shoulders/background calculated
independently rather than interpolated from output spectra.

| BW/MS coverage | Maximum PRB difference (pp) | Maximum raw relative error (%) |
| --- | ---: | ---: |
| [001] 8 nm, all 242 energies | 0.0000228810 | 0.000187573 |
| [001] 12 nm, five energies | 0.000278590 | 0.000430957 |
| [017] 8 nm, five energies | 0.001678231 | 0.007407136 |

All pass the unchanged 0.01 pp / 0.1% limits. The three Double BW cases also
reproduce their previous four-state locked-energy references with maximum raw
relative error 2.12×10⁻¹⁵. `spectral_acceptance.json` records 252 energy-pair
comparisons. Selected controls do not establish full-spectrum MS agreement
at [001] 12 nm or [017] 8 nm.

Across these comparisons, the maximum magnetic-only discrepancy is
0.001631171 pp. The maximum absolute raw D_mag discrepancy is
2.18787×10⁻⁷ a.u.; the maximum D_nonmag discrepancy is 4.16×10⁻¹⁷ a.u.
Raw intensity differences and percentage agreement remain separate diagnostics.

### Runtime, memory and saved deliverables

| Full Double case | Wall time (min) | Dense estimate (MiB) | Approximate total-process estimate (MiB) |
| --- | ---: | ---: | ---: |
| [001] 8 nm BW | 22.22 | 6.37 | 415.5 |
| [001] 12 nm BW | 21.95 | 6.37 | 429.3 |
| [017] 8 nm BW | 104.42 | 924.48 | 1693.3 |
| [001] 8 nm MS | 60.82 | 0.85 | 377.1 |

These timings include reuse of compatible pilot energy points and overlap of
independent BW/MS processes; they are machine/load-dependent, not benchmarks
of isolated execution. The total-process estimates are reconstructed from
pre-run RSS plus the unchanged estimator's working allocation, 25% margin and
128 MiB reserve. They are not measured memory peaks. The dense estimate is
particularly conservative for numerical BW depth integration. Process/RAM
snapshots and available-memory checks are retained; the observed shared BW
process peak working set reached about 169.4 MiB, while MS end-of-run RSS was
205.4 MiB. Neither snapshot certifies the complete allocator high-water mark.
The 2 GiB selected budget and 50%-of-available-RAM guard remained active.
The `memory_admission` subrecord refers to the retained-results reservation;
the complete allocation estimate is in `numerics` / `performance.csv`.

The output root contains:

- Per-case `prepared_v1/full/`: checksummed projects with all raw reversal
  spectra, derived raw/percentage arrays, original energy coordinates,
  detector weights, incoming fields and full numerical/source provenance.
- Per-case `full.csv`, compact reusable `energies/*.npz`, and performance
  records. Cache checks reject incompatible profiles; completed spectra are
  returned directly after validation without repeating scattering calculations.
- `full_spectral_comparison.npz`, `edge_metrics.csv`,
  `bw_ms_comparison.csv`, `single_double_comparison.csv` and
  `energy_refinement.json`: compact full-precision comparisons.
- `*_eels_emcd.png/.svg`: one default two-panel raw spectral figure per
  geometry/model; `001_008_double_bw_ms.png/.svg` adds the matched full-spectrum
  solver overlay. Raw and percentage data remain available in either view.
- `gui_validation/`: actual worker projects, desktop/zoom screenshots,
  both display-mode export checks and `checkpoint_2.json`.

Seventy-one focused tests pass, including prepared/default BW equivalence,
unchanged common energy samples, source bounds, outgoing energy/qz,
magnetic reversal, nonnegative raw intensities, Single compatibility,
checkpoint cancellation/resume, display/export invariance, separate PRB
denominators, memory admission and the separate finite-ZOLZ geometry audit.
See `focused_tests.json` for the exact focused runs. No broad suite, Windows
build, package version change, push or release is performed.

The existing [001] row-model spectra must not be interpreted as full-ZOLZ
[001] predictions: the new elastic audit measures substantial omitted off-row
population. This physical-model limitation is separate from the passing
BW/MS implementation agreement. No full-ZOLZ [001] EMCD correction or global
thickness/voltage convergence is inferred.
