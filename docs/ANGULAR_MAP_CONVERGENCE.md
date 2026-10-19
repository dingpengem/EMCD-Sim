# Ni [017] angular-map convergence and historical source audit

**Status: all six requested numerical maps completed.**

Branch feat/full-field-emcd-thickness, task-start HEAD 737e3f9. Existing prepared work is preserved. No version change, Windows rebuild, broad release acceptance, push, merge or tag.

## Profile and actual samples

FCC Ni [017], full finite 2D ZOLZ, exact (200) Bragg; 200 kV, 8 nm, native L3 831.4778 eV, Double channeling. Both incoming/outgoing bases contain 59 beams at 4.6 inverse Angstrom; potential cutoff 6.2; FFT48, 257 depth nodes, maximum MS step 0.04 nm; float64/complex128; eta=beta=1. Crystal [001] magnetization is rotated into the original [017] local frame. Detector centers/radius, fractional weights and 64 subpixels are unchanged from the validated study. Only this one energy/thickness is propagated. The 4096 MiB resource budget does not alter physics.

The actual centered axis is (integer index minus 96)/192 cycles/Angstrom, from -0.5 to +0.5. The 33 and 97 grids are exact subsets of 193, with spacing 1/32, 1/96 and 1/192. This differs from linspace by at most floating-point roundoff, not by a physical geometry change. Actual common response samples are reused; no high-resolution values are interpolated from coarse data. Therefore common-point equality is expected by construction and is not an independent convergence test. Added sample extrema and detector quadrature provide the sampling test.

Each positive/zero qy direction is genuinely propagated. Negative qy Cartesian responses use the same exact crystal-mirror tensor transformation as the production reference, before contraction with each rotated magnetization tensor. This does not force symmetry of magnetized intensities or assume general nonmagnetic diffraction symmetry.

The saved-output inventory found 193-grid coordinate arrays in several older jobs, but the matching full-field intensity arrays were absent (angular_maps=false), or the job geometry/model differed. Those arrays cannot substitute for the requested full-field Double maps. The prior small Single 33/97 assessment is not this validated profile.

## Detector integration

For every state, sum fractional weight times raw intensity times dq squared before any ratio. A_raw uses the +M A+B denominator; A_mag and A_nonmag use the common reversal-even N_A+N_B denominator. These percentages need not add to A_raw. No pixelwise percentage averaging or post-edge normalization is used.

| Method | N | A_raw (%) | A_mag (%) | A_nonmag (%) | D_mag (a.u.) | D_nonmag (a.u.) | A area |
|---|---:|---:|---:|---:|---:|---:|---:|
| bw | 33 | -13.045030987 | -13.133677167 | 0 | -0.0088289044399 | 0 | 0.025904417038 |
| bw | 97 | -13.059135397 | -13.147831177 | 2.06567e-14 | -0.0088331163627 | 1.38778e-17 | 0.025903728273 |
| bw | 193 | -13.060082971 | -13.148782462 | 0 | -0.008833741287 | 0 | 0.025904840893 |
| ms | 33 | -13.045977586 | -13.134639342 | 0 | -0.0088290981953 | 0 | 0.025904417038 |
| ms | 97 | -13.060084426 | -13.148795819 | 2.06577e-14 | -0.0088333094931 | 1.38778e-17 | 0.025903728273 |
| ms | 193 | -13.061032221 | -13.149747329 | 7.23022e-14 | -0.008833934371 | 4.85723e-17 | 0.025904840893 |

| Method | Grid increment | Change A_raw (pp) | Change A_mag (pp) | Max relative raw-state change (%) |
|---|---|---:|---:|---:|
| bw | 33 to 97 | -0.01410441042 | -0.01415400958 | 0.07661886028 |
| bw | 97 to 193 | -0.0009475739636 | -0.0009512854651 | 0.001271141692 |
| ms | 33 to 97 | -0.01410684069 | -0.01415647735 | 0.0766407418 |
| ms | 97 to 193 | -0.0009477949934 | -0.0009515098613 | 0.001273253295 |

These increments quantify grid sensitivity; the thickness-study BW/MS 0.01 pp agreement threshold is not applied as a grid-convergence gate. Effective circle areas and intensity-field quadrature are distinct convergence questions. All raw states and signed differences remain in detector_convergence.csv.

## Map extrema, features and solver comparison

| Method/grid | Observable | Minimum | Maximum | Maximum qx,qy | Valid/NaN |
|---|---|---:|---:|---|---|
| bw_33 | I_plus | 0.3501837342 | 10.45234844 | [0.0, 0.0] | 1089/0 |
| bw_33 | I_minus | 0.3504936511 | 10.45255098 | [0.0, 0.0] | 1089/0 |
| bw_33 | D_mag | -0.7466298697 | 0.7466298697 | [0.5, -0.125] | 1089/0 |
| bw_33 | D_nonmag | -1.776356839e-15 | 1.776356839e-15 | [-0.03125, -0.03125] | 1089/0 |
| bw_33 | asymmetry | -15.1520309 | 15.1520309 | [0.375, -0.25] | 1089/0 |
| bw_97 | I_plus | 0.3501837342 | 10.45234844 | [0.0, 0.0] | 9409/0 |
| bw_97 | I_minus | 0.3504936511 | 10.45255098 | [0.0, 0.0] | 9409/0 |
| bw_97 | D_mag | -0.7519659804 | 0.7519659804 | [0.5, -0.11458333333333333] | 9409/0 |
| bw_97 | D_nonmag | -1.776356839e-15 | 1.776356839e-15 | [-0.03125, -0.03125] | 9409/0 |
| bw_97 | asymmetry | -15.1603848 | 15.1603848 | [0.375, -0.23958333333333334] | 9409/0 |
| bw_193 | I_plus | 0.3501837342 | 10.45234844 | [0.0, 0.0] | 37249/0 |
| bw_193 | I_minus | 0.3504936511 | 10.45255098 | [0.0, 0.0] | 37249/0 |
| bw_193 | D_mag | -0.7522196486 | 0.7522196486 | [0.5, -0.109375] | 37249/0 |
| bw_193 | D_nonmag | -1.776356839e-15 | 1.776356839e-15 | [-0.026041666666666668, -0.046875] | 37249/0 |
| bw_193 | asymmetry | -15.16391473 | 15.16391473 | [0.3697916666666667, -0.23958333333333334] | 37249/0 |
| ms_33 | I_plus | 0.3501316565 | 10.44786286 | [0.0, 0.0] | 1089/0 |
| ms_33 | I_minus | 0.3504414825 | 10.44806534 | [0.0, 0.0] | 1089/0 |
| ms_33 | D_mag | -0.7466638894 | 0.7466638894 | [0.5, -0.125] | 1089/0 |
| ms_33 | D_nonmag | -8.881784197e-16 | 8.881784197e-16 | [0.4375, -0.15625] | 1089/0 |
| ms_33 | asymmetry | -15.15116026 | 15.15116026 | [0.375, -0.25] | 1089/0 |
| ms_97 | I_plus | 0.3501316565 | 10.44786286 | [0.0, 0.0] | 9409/0 |
| ms_97 | I_minus | 0.3504414825 | 10.44806534 | [0.0, 0.0] | 9409/0 |
| ms_97 | D_mag | -0.7519994636 | 0.7519994636 | [0.5, -0.11458333333333333] | 9409/0 |
| ms_97 | D_nonmag | -1.776356839e-15 | 1.776356839e-15 | [-0.020833333333333332, -0.020833333333333332] | 9409/0 |
| ms_97 | asymmetry | -15.15942823 | 15.15942823 | [0.375, -0.23958333333333334] | 9409/0 |
| ms_193 | I_plus | 0.3501316565 | 10.44786286 | [0.0, 0.0] | 37249/0 |
| ms_193 | I_minus | 0.3504414825 | 10.44806534 | [0.0, 0.0] | 37249/0 |
| ms_193 | D_mag | -0.7522527751 | 0.7522527751 | [0.5, -0.109375] | 37249/0 |
| ms_193 | D_nonmag | -1.776356839e-15 | 1.776356839e-15 | [0.015625, -0.052083333333333336] | 37249/0 |
| ms_193 | asymmetry | -15.16306292 | 15.16306292 | [0.3697916666666667, -0.23958333333333334] | 37249/0 |

Intensity-supported diagnostics use pair denominator greater than 1% of its map maximum, separately from the unchanged primary map floor (1e-6 times positive finite 95th percentile). BW/MS comparisons include unweighted and supported maximum absolute error, relative L2 and intensity-weighted RMS. Relative errors of roundoff-level nonmagnetic components are explicitly undefined, not interpreted as physical discrepancies. Full diagnostics and actual sampled sign-change brackets, including exactly sampled zero axes, are in comparison.json. Fixed-domain trapezoid integrals are sampling diagnostics, never detector asymmetries.

The raw magnetic maximum lies on the qx=+0.5 boundary for the coarse/standard maps. It is a domain-limited extremum, not proof of a global angular optimum outside the displayed field. A_raw percentage extrema are also checked on signal support; percentages near tiny denominators are not the sole criterion. The reversal-even paired residual is near floating-point roundoff for this symmetric geometry, so its bright rescaled image colors must not be read as a large contamination signal.

| Grid | BW/MS maximum angular asymmetry difference (pp) | Supported maximum (pp) | Intensity-weighted RMS (pp) |
|---:|---:|---:|---:|
| 33 | 0.002665119596 | 0.002665119596 | 0.001055578275 |
| 97 | 0.002677311335 | 0.002677311335 | 0.001039469783 |
| 193 | 0.002677910007 | 0.002677910007 | 0.001035276955 |

## Runtime, memory and outputs

Initial profile chunks were retained, not rerun. Compatible coincident samples are reused across grids. Stage wall times below cover additional samples at each level; summed per-chunk times count concurrent workers and are not wall time. Methods ran concurrently, so stage times must not be summed as total elapsed wall time. Peak RSS is measured by 0.25-second sampling and can miss brief spikes; admission estimates are separate conservative bounds. Four MS workers and one BW worker retain the original numerical settings and active memory checks.

| Method | N | Additional stage wall seconds | Sampled process peak RSS (MiB) |
|---|---:|---:|---:|
| bw | 33 | 44.622 | 109.449 |
| bw | 97 | 442.075 | 125.094 |
| bw | 193 | 1634.977 | 186.527 |
| ms | 33 | 56.990 | 186.492 |
| ms | 97 | 614.981 | 213.000 |
| ms | 193 | 1905.812 | 266.301 |

outputs/angular_resolution_convergence/ contains immutable response chunks, all six numerical NPZ maps when complete, comparison.npz/json, detector CSV, exact settings/provenance and runtime estimates. figures/ contains common-scale BW/MS maps, real sampling-point plots, solver differences and detector-convergence PNG/SVG. Source snapshot and the complete production metadata/hash audit are retained separately. Original 204 checkpoints are never overwritten.

## Recommendations and limitations

The tested 97-to-193 detector increment is at most 0.000947795 pp. Standard 97 is a reasonable routine starting point for this measured geometry/thickness/energy at that observed sensitivity, not a universal accuracy guarantee. Preview 33 is useful for broad feature placement. Use 193 and an explicit convergence comparison for publication claims sensitive to fine extrema, boundaries or detector quadrature; a high preset alone does not certify publication-quality physics.
For BW, 97-to-193 changes the angular asymmetry maximum by 0.0035299331 pp and raw magnetic maximum by 0.0337226%. Peak location shifts are [-0.005208333333333315, 0.0] cycles/Angstrom for asymmetry and [0.0, 0.005208333333333329] for the magnetic difference. I_plus/I_minus extrema are unchanged. These are actual added-node effects, not common-point interpolation errors.
For MS, 97-to-193 changes the angular asymmetry maximum by 0.0036346924 pp and raw magnetic maximum by 0.0336737%. Peak location shifts are [-0.005208333333333315, 0.0] cycles/Angstrom for asymmetry and [0.0, 0.005208333333333329] for the magnetic difference. I_plus/I_minus extrema are unchanged. These are actual added-node effects, not common-point interpolation errors.

The test covers one thickness and edge only. Basis/potential/FFT/depth convergence is inherited from limited representative studies, not re-established here. Approximate XMCD-constrained MDFF, no complete DFT transition tensor, projected IAM, existing longitudinal transfer and uncalibrated intensities remain. No experimental SNR or global optimum is inferred.

## Historical MS fingerprint

The exact historical SHA256 625fdc503711f06f3eeaad37893d9464fc108e4b47b8fa3dc9354d65a798d3df is recoverable from commit be8c3c34477f2a197646bf07f01a64d38fde1b33 by restoring two PowerShell CRLF boundaries with the UTF-8 BOM. The recovered source AST equals that committed historical source. Current MS hash is 1d6e84a7b3b0e27a0ebc88f5329f60cebd1a75c2a28f670e897845ee2750dba1.

Exact test: tests/test_ni_double_channeling_ms_validation.py::test_figures_source_and_previous_outputs_preserved. The recorded fingerprints are separate SHA256 values for scripts/ni_double_channeling_ms_validation.py, src/emcd_sim/multislice_double_channeling.py, src/emcd_sim/double_channeling.py and src/emcd_sim/multislice_reference.py. They are not a single combined hash. The old BW companion fingerprint also reconstructs exactly from its original committed source with CRLF. Every recorded fingerprint is preserved in historical_source_audit.json and the original output metadata.

Classification is mixed A/B: nonphysical encoding, optional signatures and cancellation changes; numerical multiplicity-weighted equivalent-site grouping and redundant default FCC selection. Oriented-potential support is an explicit extension outside the old cubic baseline. Existing four-thickness old/current raw reproduction differs by at most 5.56e-17 a.u.; an independent two-direction execution of exact recovered versus current MS differs by 2.45e-15 or less in Cartesian response. The current default AST must still match the pinned later validated baseline. These checks justify narrow compatibility, not a blanket claim that any hash change is harmless.

The historical test remains enabled, preserves its original expected hashes and now calls the narrow audit only for identified old MS/BW fingerprints. A deliberate qz sign mutation is rejected. Initial focused suite: 30 passed; three additional preparation/site/reflection equivalence tests passed; final completed-data/source checks: six passed. These selections overlap and must not be added as unique tests. That focused study did not rerun broad release acceptance. The subsequent complete regression passed 426/426 tests; local Windows acceptance passed and independent clean-machine installation remains NOT TESTED. See [final acceptance](V061_BETA_ACCEPTANCE.md).

The subsequent local release finalization, complete regression run and rebuilt-candidate status are recorded separately in [release acceptance](V061_BETA_ACCEPTANCE.md).
