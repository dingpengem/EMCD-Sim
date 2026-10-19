# Full-field EMCD and complete 200 kV thickness study

**All eight series have 51 actual thickness points (0:2:100 nm).** Zero inelastic intensity is exact; its percentage is NaN.
No MS interpolation, BW copying, rescaling, peak retuning or full-energy-per-thickness recomputation was used.

Full-field maps use original I_plus/I_minus at actual (qx,qy)/(qx,-qy) pairs. Detector outlines do not limit the field or require mirrored manual apertures. This mathematical pairing does not assume a symmetric nonmagnetic diffraction field. Raw maps show M(q)-M(q') and N(q)-N(q'); total asymmetry is 100*(I_plus(q)-I_plus(q'))/(I_plus(q)+I_plus(q')). Invalid denominators remain NaN with the existing floor. No aperture weighting is used as a full-field mask.
Legacy aperture-restricted/corrected maps remain Advanced Diagnostics. The earlier primary formula already used the full grid when its physical-detector prerequisite passed; this patch removes that prerequisite and dependence on historical D_* fields, and explicitly identifies the full-field view.
Detector-integrated spectra remain different observables: integrate raw A/B intensities first, then take their difference/sum. Moving overlays cannot change the original intensity field or its point-pair ratios. Existing EELS/solver arrays are unchanged.

## Runtime, reuse and provenance

Initial audit reused 102 BW and 16 MS geometry/thickness checkpoints (both models per checkpoint), leaving 86 joint MS jobs: 86 Single plus 86 Double cases. The initial sequential wall-time estimate was 7.64 hours, with a conservative 4.97-12.23 hour workload interval. Timings already existed at 8/12, 50 and 100 nm, so no completed case was restarted for profiling.
Parameters/tensors/frame/energies/detectors/weights must match exactly. Historical byte hashes differ because of optional prepared-incoming and cancellation support; a default-path AST audit proves equivalence to the recorded baseline. Only that audited source equivalence and the previously audited scheduler change are allowed. Original checkpoint bytes are hash-checked unchanged.
Fixed profile: Ni [017] full finite ZOLZ and [001] explicit (200) systematic-row approximation; 200 kV; potential 6.2 and incoming/outgoing beam 4.6 inverse Angstrom; FFT 48; 257 depth nodes; maximum MS step 0.04 nm; float64/complex128; fractional 193-grid apertures with 64 subpixels; crystal [001] magnetization rotated into each local frame; eta=beta=1; fixed native 831.4778/848.698 eV. No experimental energy calibration or geometry optimization by thickness.

## Sampled extrema

| Zone | Solver | Model | Edge | Thickness (nm) | Signed asymmetry (%) |
| --- | --- | --- | --- | ---: | ---: |
| 001 | bw | single | L3 | 12 | -11.8572649 |
| 001 | bw | double | L3 | 8 | -13.22777304 |
| 001 | ms | single | L3 | 12 | -11.85719451 |
| 001 | ms | double | L3 | 8 | -13.22778653 |
| 001 | bw | single | L2 | 12 | 20.11327018 |
| 001 | bw | double | L2 | 8 | 22.41544106 |
| 001 | ms | single | L2 | 12 | 20.113151 |
| 001 | ms | double | L2 | 8 | 22.41546383 |
| 017 | bw | single | L3 | 12 | -11.65564115 |
| 017 | bw | double | L3 | 8 | -13.06008297 |
| 017 | ms | single | L3 | 12 | -11.65543241 |
| 017 | ms | double | L3 | 8 | -13.06103222 |
| 017 | bw | single | L2 | 12 | 20.09789902 |
| 017 | bw | double | L2 | 8 | 22.54492355 |
| 017 | ms | single | L2 | 12 | 20.09753696 |
| 017 | ms | double | L2 | 8 | 22.54660178 |

These are maxima of the requested 2 nm samples, not globally converged or experimentally optimal thicknesses.

Numerical BW/MS gate: **PASS**. Maximum difference 0.009656016805 percentage points; maximum raw-state relative difference 0.01509737648%. Thresholds remain 0.01 pp and 0.1%.
Worst cases, per-thickness errors, magnetic-only/even diagnostics, sign-reversal brackets and any targeted depth/slice controls are recorded in summary.json and bw_ms_comparison.csv. A failed production-profile gate remains failed even when a focused control improves agreement; production curves are never silently replaced.
Outgoing-channeling effects are assessed by the separate Single/Double sampled extrema and sign-bracket lists. BW/MS differences are numerical solver comparisons; neither solver agreement nor this profile establishes global parameter convergence or physical MDFF accuracy.

## Representative values

| Zone | Solver | Model | nm | L3 (%) | L2 (%) |
| --- | --- | --- | ---: | ---: | ---: |
| 001 | bw | single | 8 | -10.2743448 | 17.4288622 |
| 001 | bw | single | 12 | -11.8572649 | 20.1132702 |
| 001 | bw | single | 20 | -7.62693211 | 12.9378094 |
| 001 | bw | single | 30 | -0.368256335 | 0.624694636 |
| 001 | bw | single | 50 | -3.41573721 | 5.79425604 |
| 001 | bw | single | 80 | -2.09332959 | 3.5510409 |
| 001 | bw | single | 100 | -0.0515062087 | 0.0874746507 |
| 001 | bw | double | 8 | -13.227773 | 22.4154411 |
| 001 | bw | double | 12 | -9.91703349 | 16.8062737 |
| 001 | bw | double | 20 | -2.37715013 | 4.04109043 |
| 001 | bw | double | 30 | -3.00948692 | 5.0945587 |
| 001 | bw | double | 50 | -2.13956168 | 3.62910722 |
| 001 | bw | double | 80 | -0.967085042 | 1.64131932 |
| 001 | bw | double | 100 | -0.481078219 | 0.814590339 |
| 001 | ms | single | 8 | -10.2743657 | 17.428898 |
| 001 | ms | single | 12 | -11.8571945 | 20.113151 |
| 001 | ms | single | 20 | -7.62677381 | 12.937541 |
| 001 | ms | single | 30 | -0.368238974 | 0.624665212 |
| 001 | ms | single | 50 | -3.41534109 | 5.79358413 |
| 001 | ms | single | 80 | -2.09273517 | 3.55003258 |
| 001 | ms | single | 100 | -0.0515493239 | 0.0875479215 |
| 001 | ms | double | 8 | -13.2277865 | 22.4154638 |
| 001 | ms | double | 12 | -9.91686891 | 16.8059952 |
| 001 | ms | double | 20 | -2.37704439 | 4.04091129 |
| 001 | ms | double | 30 | -3.00943447 | 5.0944698 |
| 001 | ms | double | 50 | -2.13935332 | 3.62875399 |
| 001 | ms | double | 80 | -0.96687311 | 1.64096002 |
| 001 | ms | double | 100 | -0.480955817 | 0.814382972 |
| 017 | bw | single | 8 | -10.1782472 | 17.5143903 |
| 017 | bw | single | 12 | -11.6556412 | 20.097899 |
| 017 | bw | single | 20 | -7.29560591 | 12.5029007 |
| 017 | bw | single | 30 | -0.268202405 | 0.45513749 |
| 017 | bw | single | 50 | -3.28230355 | 5.59346144 |
| 017 | bw | single | 80 | -2.08435617 | 3.54608207 |
| 017 | bw | single | 100 | -0.139244181 | 0.236338992 |
| 017 | bw | double | 8 | -13.060083 | 22.5449235 |
| 017 | bw | double | 12 | -9.69179071 | 16.6496238 |
| 017 | bw | double | 20 | -2.17670561 | 3.71211331 |
| 017 | bw | double | 30 | -3.00858302 | 5.11423043 |
| 017 | bw | double | 50 | -2.09517519 | 3.56393372 |
| 017 | bw | double | 80 | -0.909507605 | 1.5457715 |
| 017 | bw | double | 100 | -0.488924435 | 0.828596251 |
| 017 | ms | single | 8 | -10.1797186 | 17.5169627 |
| 017 | ms | single | 12 | -11.6554324 | 20.097537 |
| 017 | ms | single | 20 | -7.29111481 | 12.4951275 |
| 017 | ms | single | 30 | -0.266469515 | 0.452195876 |
| 017 | ms | single | 50 | -3.27994924 | 5.58943151 |
| 017 | ms | single | 80 | -2.08372389 | 3.54500335 |
| 017 | ms | single | 100 | -0.141397183 | 0.239992728 |
| 017 | ms | double | 8 | -13.0610322 | 22.5466018 |
| 017 | ms | double | 12 | -9.68889403 | 16.6445873 |
| 017 | ms | double | 20 | -2.17263402 | 3.7051723 |
| 017 | ms | double | 30 | -3.00945044 | 5.11570609 |
| 017 | ms | double | 50 | -2.09446424 | 3.56271804 |
| 017 | ms | double | 80 | -0.908403257 | 1.5438984 |
| 017 | ms | double | 100 | -0.489280735 | 0.829205115 |

## Outputs and limits

Angular examples/arrays: outputs/full_field_emcd_maps/ (saved BW/MS Single/Double L3/L2 references; no new energy-spectrum calculations).
Thickness outputs: outputs/ni_emcd_asymmetry_thickness_200kv/. Full-precision thickness_series.csv/npz, comparison CSV, configuration/provenance, runtime assessment, immutable per-case checkpoints and summary.json remain local. Twelve separate standalone figures are saved in PNG and SVG under figures/: ni{017,001}_{L3,L2}_{BW_single_double,MS_single_double,BW_MS_all_models}. Each has fixed energy, geometry, signed axes, zero baseline and real calculated samples.
Focused full-field tests and final data-only integrity tests are saved under the output validation folders. No broad regression suite, voltage scan, 1 nm refinement, packaging, push or release modification is performed.
The MDFF remains XMCD-constrained and approximate, without a complete DFT transition tensor. Potentials remain projected IAM, longitudinal transfer uses the existing approximation, absolute EELS/counts are uncalibrated, and numerical convergence is representative. Arbitrary intensities/percentages are not experimental SNR.
