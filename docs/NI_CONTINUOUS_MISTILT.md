# Continuous Ni (200) mistilt series

The dedicated driver `emcd_sim.ni_mistilt_series` varies incident x tilt around
the paraxial (200) Bragg condition while keeping y tilt at **+25 mrad**. It
reuses the existing BW and independent FFT propagators, depth coherences,
XMCD-effective tensor contraction, fractional apertures, paired-map geometry
and post-edge analysis. It introduces no scattering model changes.

## Geometry and physical settings

The reference is calculated from the existing relativistic wavelength and Ni
reciprocal vector. At 200 kV, wavelength = 0.02507934045046928 Å and
theta_Bragg,x = -7.116725439974256 mrad. The scan offsets are
`[-2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2]` mrad; these are **relative x offsets**.
Absolute x tilt is theta_Bragg,x + offset. The earlier y=15 mrad case is excluded.

All points use FCC Ni [001], 30 nm, eta=beta=1, zero Debye-Waller B,
potential Fourier cutoff 0.75 cycles/Å, common beam cutoff 2.2 cycles/Å
(45 ZOLZ beams), FFT 32×32, maximum slice step 0.04 nm, 64 depth samples,
detector grid 33×33, and fractional aperture weights with 64 subpixels per
pixel side. The existing dense-pair-array estimate is 134.6 MiB; the limit
is 512 MiB. This estimate is a kernel working-array estimate, not a total
process-memory guarantee.

The A/B circles are fixed at (g200/2, ±g200/2), radius 0.16 g200. The Thales
circle has diameter (000)–(200), center (g200/2, 0), radius g200/2.
Actual indexed beam positions are retained. ZA [001] = -k_incident,perp;
its qy stays fixed and qx changes with the incident x tilt. Overlays alter
only plotting artists. BW and MS use the same geometry and detector weights.

The recorded signed excitation error is
`s200 = lambda/2 * (|k_perp+g200|² - |k_perp|²)` in inverse Å.
It is zero to roundoff at offset zero and negative/positive on the
negative/positive sides. These are Bragg-aligned **multibeam** calculations,
not an ideal 000/200-only propagation model.

| Delta x (mrad) | Absolute x (mrad) | Absolute y (mrad) | s200 (Å^-1) | ZA qx (Å^-1) | ZA qy (Å^-1) |
|---:|---:|---:|---:|---:|---:|
| -2.0 | -9.116725 | 25.0 | -0.001135074 | 0.363515 | -0.996836 |
| -1.5 | -8.616725 | 25.0 | -0.000851305 | 0.343579 | -0.996836 |
| -1.0 | -8.116725 | 25.0 | -0.000567537 | 0.323642 | -0.996836 |
| -0.5 | -7.616725 | 25.0 | -0.000283768 | 0.303705 | -0.996836 |
| 0.0 | -7.116725 | 25.0 | 0.000000000 | 0.283768 | -0.996836 |
| +0.5 | -6.616725 | 25.0 | +0.000283768 | 0.263832 | -0.996836 |
| +1.0 | -6.116725 | 25.0 | +0.000567537 | 0.243895 | -0.996836 |
| +1.5 | -5.616725 | 25.0 | +0.000851305 | 0.223958 | -0.996836 |
| +2.0 | -5.116725 | 25.0 | +0.001135074 | 0.204022 | -0.996836 |

## Source energy and normalization

The source is `data/wien2k_ni/Ni_fm.xmcd`; SHA256 is saved in run metadata.
The full native interval is 823.625–882.521 eV. A common grid combines 241
uniform samples with the actual source samples nearest the requested
852.7/870.0 eV references: **852.698 and 870.004 eV** (243 distinct energies).
This deliberately follows the requested references. The source's two strongest
native peaks are instead near 831.421/848.752 eV; no energy shift or experimental
alignment is inferred. The previous four-case peak-energy figures are preserved.

For each case and method, alpha is determined solely from its own plus-state
A/B spectra: `alpha = integral_878^882 A+ / integral_878^882 B+`, using the
existing exact-endpoint interpolation and trapezoidal integration. No fit
between mistilts or methods is made. The same alpha is used for the processed
magnetic and even terms. Intrinsic magnetic maps are never post-edge-scaled.

Definitions:

- Intrinsic odd/even fields: `(I+ - I-)/2`, `(I+ + I-)/2`.
- Raw detector contrast: `A+ - B+`; corrected: `A+ - alpha B+`.
- Magnetic/even detector differences: reversal odd/even parts of raw contrast.
- `Sigma_ref = (A+ + B+ + A- + B-)/2`.
- Raw asymmetry: `(A+ - B+)/(A+ + B+)`; magnetic asymmetry: `D_mag/Sigma_ref`.
- Paired maps compare `(qx,qy)` with `(qx,-qy)` only on the A fractional
  aperture support; NaN elsewhere. They are processed contrasts, distinct
  from full-grid intrinsic scattering distributions.

Summary columns retain signed magnetic/even signals and their absolute
magnitudes separately. Single-energy suppression is
`1 - abs(even_residual)/abs(original_even_difference)`. Magnetic magnitude
change is `(abs(processed_mag)-abs(original_mag))/abs(original_mag)`; the
signed processing change is also saved. Denominators below `1e-10 * peak
Sigma_ref` produce NaN, rather than large unreliable relative percentages.
Existing edge-window spectral-norm recovery metrics are retained separately.
BW/MS map error uses full-grid area-weighted L2 norms, relative to the larger
compared magnetic-map norm with the existing intensity-based floor.

## Execution, checkpointing and outputs

PowerShell, with the `emcd-python` environment active:

```powershell
$env:PYTHONPATH='src'
python -m emcd_sim.ni_mistilt_series
python -m emcd_sim.ni_mistilt_series --plot-only
python -m emcd_sim.ni_mistilt_diffraction
```

Use `--start-mrad`, `--stop-mrad`, `--step-mrad`, `--fixed-y-mrad`,
`--thickness-nm`, `--potential-cutoff`, `--beam-cutoff`, `--max-beams`,
`--fft-grid`, `--slice-step-nm`, `--depth-steps`, `--detector-grid`,
`--energy-points`, `--aperture-subpixels`, `--source`, and `--output`
for controlled refinements. `--help` lists all settings. The range includes
both endpoints and requires an integer number of steps.

Each offset propagates once per method; coherences are reused for the full
spectrum and selected maps. Projected FFT amplitudes are not renormalized.
Completed cases are stored atomically under `checkpoints/`. Reuse verifies
source, configuration, code hashes, NPZ checksum and parity. Incompatible
settings are rejected without overwriting results. The offset range itself
is excluded from the per-case signature so completed matching points can be
reused when refining a scan. Plot-only requires completed matching checkpoints
and changes figure files only. It performs no propagation or tensor contraction.

Main results are in `outputs/ni_continuous_mistilt/`:

- `mistilt_maps.npz`: arrays `[mistilt, method, edge, qy, qx]`, plus shared
  grids, aperture weights, validity support, offsets and labels.
- `mistilt_eels.npz`: detector and difference arrays `[mistilt, method, energy]`,
  common energies, offsets, labels, and alpha `[mistilt, method]`.
- `mistilt_summary.csv`: 36 rows (9 offsets × 2 methods × 2 edges), including
  signed signals, asymmetries, processing effects and BW/MS errors.
- `mistilt_metadata.json`: geometry at every offset, source/code provenance,
  physical settings, normalization details, leakage and coherence diagnostics.
- `L3/L2_magnetic_mistilt_series.png`, `L3/L2_nonmagnetic_mistilt_series.png`:
  ordered 3×3 BW mosaics; `_multislice` versions use identical color scales.
- Total and corrected 3×3 mosaics are also supplied for both methods.
- `raw_corrected_mistilt.png`, `L2_raw_corrected_mistilt.png`: -1/0/+1 mrad
  paired raw/corrected maps with shared scales across both methods.
- `virtual_detector_eels_mistilt.png`: quantitative unoffset spectra.
- `virtual_detector_eels_stacked.png`: explicitly labeled constant display
  offsets without curve rescaling.
- `emcd_vs_mistilt.png`, `bloch_multislice_vs_mistilt.png`: signed trends,
  processing behavior and numerical map discrepancies.

All NPZ files use numeric or Unicode arrays and load with `allow_pickle=False`.
The old `outputs/ni_raw_eels_emcd_tilt_series/` is never an output target;
its complete file hashes were recorded before this work for preservation checks.

## Validation and limitations

Focused checks cover exact/reference absolute tilts, fixed y, excitation-error
sign, ZA coordinates, fixed Thales/detector geometry, parity, processing
separation, map/EELS integration, memory controls and provenance rejection.
A reduced -1/0/+1 mrad, 1 nm, 21-beam, FFT16, detector17 test sweep ran before
the nine-point production sweep. Checkpoint-only reuse was tested with forward
calculation disabled. Production cases assert selected-map integration against
the same detector spectra at the exact selected source energies.

These results use an **XMCD-effective** dipole tensor, entrance-only channeling
and a Fourier-truncated projected IAM potential. They do not establish potential,
beam-basis, spatial-grid, depth/slice or global convergence, and are not calibrated
cross sections or quantitative experimental Ni EMCD predictions. Post-edge
scaling can change the magnetic contribution as well as suppressing an even
background; the unprocessed reversal-odd reference remains available throughout.

## Completed nine-point results

The reference is the off-zone (200) exact Bragg geometry
`(-7.11672544, +25) mrad`, **not [001] zone-axis incidence**. Nominal [001]
identifies the projected crystal frame and ZA marker. No additional rational
crystallographic minor-zone index is assumed from these tilt values. The full
45-beam basis is used throughout; no ideal two-beam truncation is made.

The following BW asymmetries are percentages (ratios multiplied by 100):

| Delta x (mrad) | L3 magnetic (%) | L2 magnetic (%) | L3 raw (%) | Observed alpha |
|---:|---:|---:|---:|---:|
| -2.0 | 0.368482 | 0.090634 | 2.387311 | 1.042019 |
| -1.5 | 0.619488 | 0.152373 | 1.166305 | 1.012198 |
| -1.0 | 0.863006 | 0.212243 | -0.686443 | 0.971102 |
| -0.5 | 1.042296 | 0.256283 | -3.082518 | 0.922766 |
| 0.0 | 1.109846 | 0.272820 | -5.816859 | 0.872718 |
| +0.5 | 1.047033 | 0.257303 | -8.615649 | 0.826223 |
| +1.0 | 0.873474 | 0.214590 | -11.212365 | 0.786861 |
| +1.5 | 0.637083 | 0.156480 | -13.414963 | 0.756086 |
| +2.0 | 0.391673 | 0.096193 | -15.116398 | 0.733914 |

At these requested source energies, magnetic asymmetry peaks at the sampled
Bragg reference and decreases toward either end; the two sides are not exactly
symmetric. Raw asymmetry changes sign on the negative-offset side while the
magnetic signal retains its sign. The even diffraction contribution therefore
cannot be interpreted as a magnetic reversal. These statements concern the
specified source samples, not energy-aligned experimental Ni peak positions.

Across both methods and edges, alpha ranges from 0.733914 to 1.042162;
single-energy even-difference suppression ranges from 88.91% to 99.61%.
Processing changes magnetic **magnitude** by -15.56% to +2.44%.
Good even suppression is consequently not proof of unbiased magnetic recovery.
Absolute/signed signals and denominator floors remain in the CSV.

Maximum BW/MS full-grid magnetic-map relative L2 difference is **0.2108%**;
coherence differences range from 0.08390% to 0.09091%. Maximum absolute
magnetic-asymmetry differences are 3.93e-6 for L3 and 9.67e-7 for L2 (fractions,
or 0.000393/0.0000967 percentage points). Maximum excluded FFT intensity is
1.146e-5 of incident intensity; FFT norm error is below 7.64e-14. These are
matched numerical comparisons, not global convergence statements.

## How closely does the reference approximate two-beam diffraction?

`ni_mistilt_diffraction` reuses saved complex amplitudes and coherences,
verifies their provenance/checksums and exports all 45 indexed excitation
errors and elastic populations at every mistilt. It performs no propagation.
`s200=0` exactly in the saved reference calculation, but this alone does not
prove isolated two-beam scattering.

At 30 nm, the 000+200 pair carries 96.0753% (BW) and 96.0878% (MS) of incident
intensity at the exit. Its depth-average is only 90.5885% / 90.5892%; its
minimum on the 64 saved depths is 84.4299% / 84.4294%. Other modes therefore
carry up to **15.57%** at sampled depths. This is a two-beam-dominated,
Bragg-aligned off-zone reference with appreciable multibeam channeling,
not a strictly isolated physical two-beam state. The depth average matters
because entrance-channeling EMCD contracts the depth-averaged coherence.

Selected BW competitors at the reference; intensities are percentages of
incident intensity, not percentages of the retained subspace:

| Reflection | s_g (Å^-1) | Exit (%) | Depth average (%) | Sampled maximum (%) |
|---|---:|---:|---:|---:|
| (-2,0,0) | +0.008078008 | 0.277628 | 3.362544 | 8.666173 |
| (4,0,0) | +0.008078008 | 1.353308 | 1.541925 | 3.376175 |
| (0,-2,0) | -0.010149418 | 0.114064 | 1.146365 | 4.900382 |
| (2,-2,0) | -0.010149418 | 0.074495 | 1.662103 | 4.682371 |
| (0,2,0) | +0.018227426 | 1.226074 | 0.391855 | 1.861023 |
| (2,2,0) | +0.018227426 | 0.801110 | 0.587180 | 1.931663 |

The closest non-target excitation errors are (−2,−6,0) and (4,−6,0),
both +0.001863780 Å^-1, yet their depth-averaged populations are only
0.001518% and 0.001087% in this truncated-potential calculation. Excitation
error proximity alone does not rank the dynamically populated competitors.

Additional outputs:

- `competing_reflections.csv`: every offset × method × indexed reflection.
- `reference_competing_reflections.csv`: complete reference reflection table.
- `two_beam_quality.csv`: exit, depth-average and minimum sampled pair
  populations, plus competing and excluded-mode populations.
- `elastic_mistilt_diagnostics.npz`: intensities `[mistilt, method, depth, beam]`,
  excitation errors `[mistilt, beam]`, actual hkl and depth coordinates.
- `two_beam_reference_diagnostics.png`, `two_beam_readiness.json`: the reference
  assessment. Sampled maxima/minima are not continuous-depth bounds.

The production sweep passed all map/spectrum reconstruction assertions;
maximum selected-map detector reconstruction error is 6.13e-18 in relative
model intensity units. Twelve focused tests passed: four driver tests,
three geometry-overlay tests, three existing propagation tests, and two
elastic-population diagnostics tests. The full checkpoint CLI was exercised
with forward calculations disabled; all nine cases were reused, and saved
physical arrays remained byte-for-byte unchanged. All 38 earlier results
also remain byte-for-byte unchanged. `validation_summary.json` records these
checks, and every generated NPZ was opened with `allow_pickle=False`.
