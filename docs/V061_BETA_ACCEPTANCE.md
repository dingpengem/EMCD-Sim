# EMCD-Sim v0.6.1-beta.1 Windows acceptance and provenance

This record documents the validated Windows Beta and its precise acceptance scope. The user subsequently authorized the v0.6.1-beta.1 documentation update, fast-forward integration into main, tag and GitHub prerelease using the unchanged ZIP. This does not authorize a stable/Latest release or a claim of clean-machine validation. Existing v0.6.0-beta.1 assets are preserved. PEP 440 package version: `0.6.1b1`.

| Gate | Status | Evidence |
| --- | --- | --- |
| Saved 200 kV scientific numerical acceptance | PASSED | 204 complete joint checkpoints; 816 model/edge records; unchanged 0.01 pp / 0.1% raw thresholds |
| Representative angular-map convergence | PASSED | Saved Ni [017], 8 nm, L3, Double; actual 33/97/193 samples |
| Historical MS regression | PASSED | Original enabled hash-preservation test rerun explicitly; 1 passed in 15.19 s |
| Complete regression | PASSED | 426 collected / 426 passed / 0 failed / 0 skipped; 31 warnings; 799.24 s |
| Fresh Windows packaging | PASSED | Fresh PyInstaller executable; ZIP CRC and every archived file hash verified |
| Rebuilt executable smoke test | PASSED | Native Windows Qt; saved BW/MS Single and Double; zero solver calls; unchanged arrays/projects |
| Final local Windows acceptance | PASSED | User approved acceptance; validated EXE running/responding on the recorded local Windows 11 host |
| Independent clean-machine installation | NOT TESTED | The specified local computer has Python/Conda and prior EMCD-Sim installations |
| User-approved local release acceptance | PASSED | Scientific, regression, package and local Windows gates pass; independent clean-machine acceptance is not claimed; publication is limited to the separately authorized v0.6.1-beta.1 prerelease |

## Scientific evidence and scope

All 204 checkpoint SHA256 values match the pre-existing integrity manifest. No production propagation was rerun. Read-only saved-data analysis independently confirms maximum BW/MS detector asymmetry difference **0.009656016804930445 pp**, at [017], 22 nm, Single L2. Maximum relative raw-state difference is **0.015097376484967838%**, at [017], 18 nm, Double L2. The acceptance thresholds remain 0.01 pp and 0.1%; neither was relaxed.

The saved study covers BW/MS, Single/Double, L3/L2, and 0-100 nm in 2 nm steps for [017] full finite ZOLZ and [001] restricted systematic-row comparison. The latter is not a validated full-ZOLZ physical two-beam condition. Native unshifted selected energies are 831.4778 and 848.698 eV. [017] magnetization is cubic [001] rotated into the actual local frame. See [scientific analysis](NI_EMCD_THICKNESS_SCIENTIFIC_ANALYSIS.md) for source hashes, physical configuration, decomposition and extrema.

For [017] BW, the largest sampled L3 raw +M detector asymmetry magnitude is 11.6556411502% at 12 nm for Single and 13.0600829714% at 8 nm for Double. Magnetic-only extrema are 11.7254550236% and 13.1487824624% at those same sampled thicknesses. The largest raw magnetic difference instead occurs at 48 nm Single and 12 nm Double. These observations were computed from saved states, not imposed. Sampled extrema are not globally converged thickness optima.

Raw magnetic difference is `D_mag=M_A-M_B`; reversal-even difference is `D_nonmag=N_A-N_B`. Their common-even-denominator percentages add. Raw +M detector asymmetry uses a different denominator, `I_A_plus+I_B_plus`. Post-edge-corrected contrast is not intrinsically magnetic. Full-field maps use physical mirrored point samples, whereas EELS integrates original intensity over finite apertures before forming a ratio. Arbitrary-unit differences are not electron counts or experimental SNR.

## Angular sampling

| Actual grid | BW detector asymmetry (%) | MS detector asymmetry (%) |
| --- | ---: | ---: |
| 33 x 33 | -13.045030986992693 | -13.045977585564046 |
| 97 x 97 | -13.059135397412767 | -13.060084426252510 |
| 193 x 193 | -13.060082971376335 | -13.061032221245947 |

The 97-to-193 detector increments are 0.000947574 pp BW and 0.000947795 pp MS in magnitude. Angular asymmetry maxima change by 0.0035299331 / 0.0036346924 pp, with a 0.00520833 inverse-Angstrom peak shift. Nested common samples were reused exactly; their agreement by construction is not independent convergence evidence. Added-node extrema and detector quadrature supply the meaningful comparisons. See [angular convergence](ANGULAR_MAP_CONVERGENCE.md).

Standard 97 is recommended for routine work under this tested configuration. Use 193 for finer peak analysis and case-specific convergence checks; 33 is a preview. These measurements certify one thickness/edge/profile, not other geometries, energies or a globally converged physical model.

## Historical source protection

The original expected MS SHA256 remains `625fdc503711f06f3eeaad37893d9464fc108e4b47b8fa3dc9354d65a798d3df`. Exact bytes were recovered from pinned historical Git source by retaining the UTF-8 BOM and restoring two PowerShell CRLF boundaries. Expected historical hashes were not replaced.

Subsequent equivalent-site multiplicity grouping is a numerical change, separately checked through phase algebra, four-thickness raw-state reproduction (maximum 5.56e-17 a.u.), and direct recovered/current-kernel comparison (maximum 2.45e-15 Cartesian response). Current default-path AST checks remain strict; a qz sign mutation fails. The original test is enabled, with no skip, xfail or threshold relaxation. Legacy loaders still reject unmatched byte provenance; no general compatibility waiver was added.

The complete final run passed all 426 collected tests (0 failures, 0 errors, 0 skips) in 799.24 seconds. Its 31 warnings comprise 24 Qt high-DPI deprecation warnings and seven constrained-layout warnings from small/closing test widgets; no physics warning or failed numerical gate was reported. Tests use the locally retained optional benchmark references. The earlier 408-pass/7-failure run is historical evidence, not the final result. Corrections address strict-loader test expectations, a historical GUI-diff endpoint, isolated GUI layout fixtures, package version, and the narrowly audited original hash. No solver physics was changed to make tests pass.

## GUI and build checks

New Project defaults to actual 97 x 97 angular sampling and 2048 MiB. Presets are 33/97/193 plus odd Custom sizes; memory choices remain 512/1024/2048/4096/8192 MiB. Explicit old grid/budget settings are retained. FFT sampling and aperture boundary subpixels remain independent. Angular/EELS quadrature remains shared. Saved results report their actual dimensions and q spacing and render nearest samples, with unchanged physical q axes and color-scale policy.

Source saved-project acceptance exercised BW/MS Double, presets, Custom, New Project reset, saved 512 MiB compatibility, actual 9 x 9 stored samples despite larger input controls, mirror formula, zero-denominator NaNs, rejection of incomplete data, raw/percentage display, exports and project reopening. Forward calls stayed zero; original project and array hashes were unchanged. The references are small real saved calculations, not new production simulations.

Fresh candidate: `build/windows-v061-beta-final/EMCD-Sim-0.6.1-beta.1-Windows-RC.zip` (108,703,899 bytes). SHA256: `9fd5e71437d2c26d4595abb7adde9436e4c333ce18f3a57cf381b0c541bfd94f`. Exact source hashes, commit/dirty state, build UTC, Python environment and dependency versions are recorded in `build_manifest.json` and the frozen About/build information. ZIP integrity and file hashes are checked by `scripts/verify_v061_candidate.py`. Production datasets, logs and licensed WIEN2k companion files are excluded; the package uses the tracked repository Ni example rather than the separate modified study source.

Final machine-readable evidence is saved in `outputs/v061_final_acceptance/`, including regression XML/log, explicit historical test, source/frozen GUI reports, screenshots, exports and package verification. No candidate is described as committed unless its actual provenance establishes that.

## Remaining limitations

The user's subsequent instruction specifies execution on the existing local computer. This is not an independent clean-machine installation: Python/Conda and earlier EMCD-Sim builds are already present. Clean-machine installation remains NOT TESTED, and SmartScreen reputation and signing are not certified. PASSED applies to the user-approved local Windows release scope. Scientific agreement concerns matched sampled profiles, with limited representative basis/potential/FFT/depth checks. Approximate XMCD-constrained MDFF, incomplete DFT transition tensor, projected IAM, longitudinal-transfer approximation, absolute energy calibration and uncalibrated intensity remain. No new voltage scan, experimental validation or absolute EELS calibration is claimed.


## Final build provenance and local Git state

Branch: `feat/full-field-emcd-thickness`. The fresh executable was built from the reviewed runtime code committed as `e66c97923bd4838188ed03c424dc9973ada55c25`, at `2026-10-19T16:04:43.531526+00:00`. The final local commit is a documentation-only amendment of that revision; its runtime source and packaging specification are identical to the build revision. The executable correctly retains the original build commit rather than claiming a later build. See `outputs/v061_final_acceptance/final_git.json` for final HEAD and the complete 34-file change list.

The build records `dirty=true` because unrelated local input/development files were preserved and excluded. All packaged runtime source hashes match the final working source exactly. No production dataset, licensed companion data, temporary watcher, raw-tilt development script or unrelated test was staged. The user-owned modified Ni source remains unchanged. No push, merge, release tag or publication occurred during the original local acceptance; subsequent publication is separately authorized.

Build Python: 3.11.17, `build/windows-rc/venv/Scripts/python.exe`. Recorded dependencies: NumPy 2.4.6, SciPy 1.17.1, Matplotlib 3.11.2, ASE 3.29.0, PySide6 6.12.0, PyInstaller 6.22.3. No dependencies were upgraded for this task.

The frozen executable was launched with a Windows-only PATH (no development Python/Conda on PATH) and native Windows Qt. Both saved-model checks passed presets/defaults, explicit legacy 512 MiB restoration, true stored 9 x 9 dimensions and spacing, full-field mirrored samples, detector overlays, raw/percentage immutability, zero-denominator NaNs, rejection of incomplete maps, EELS/Angular separation, PNG/SVG and CSV/NPZ exports, and saved-project loading/reopening. Source/frozen array fingerprints match. Both reports record zero forward calls and unchanged original arrays and project files. Actual exported frozen angular figures were visually inspected.

Frozen runs emitted a Matplotlib temporary font-cache permission warning and a small acceptance-widget layout warning; readable figures and all numerical checks completed. An initial ZIP attempt failed because smoke testing had started while Windows archiving still needed exclusive access to the executable. After both checks finished, the same completed distribution was archived successfully; no second build or simulation was launched. The final ZIP passed CRC, per-file manifest, source-hash and archive checksum verification. Initial logs remain available rather than being discarded.

The earlier v0.6.0 ZIP remains SHA256 `6adda35a3b52ac35a06681a8cf5fca753aae2f03387feda57373c78ad8be2b5e`; the earlier v0.6.1 candidate remains `97c8aad8c035995720864ce1ed5b8c24340d4209a08b61755cf75bc6189146bd`.

No unresolved local numerical, regression or package-integrity blocker remains. User-approved local Windows acceptance is PASSED following the user's confirmation and approval on 2026-10-19. Independent clean-machine acceptance remains NOT TESTED. Publication remains a separate manual action.

## Final local Windows acceptance

Result: **PASSED** for the local Windows scope, approved by the user on 2026-10-19. The user then specified opening/executing the GUI locally on their existing computer. This clarification does not establish a clean-machine test.

Actual environment, inspected on 2026-10-19 at 15:13 EDT:

- Microsoft Windows 11 Enterprise, version 10.0.26200, build 26200, 64-bit.
- Intel Core i7-1365U, 10 cores / 12 logical processors; 31.58 GiB OS-visible RAM (approximately 32 GiB installed).
- Python/Conda is installed at `C:/Users/peng863/AppData/Local/miniconda3/envs/emcd-python/`; previous EMCD-Sim builds are present. The earlier standalone smoke tests excluded Python/Conda from PATH, but that is not a clean OS installation.
- Validated executable: `build/windows-v061-beta-final/dist/EMCD-Sim/EMCD-Sim.exe`, version 0.6.1b1, already running as PID 38332. Its window title reports the Beta version and Windows reports it as responding. The existing window was restored and successfully brought to the foreground; no duplicate instance was launched and no calculation was started, cancelled or interrupted.

Verified function coverage comes from the existing source/frozen reports: About/build provenance, 97 x 97 / 2048 MiB defaults, 33/97/193 and Custom controls, explicit saved 512 MiB compatibility, saved BW/MS Single/Double results, full-field maps and detector overlays, mirrored asymmetry and valid/NaN behavior, raw/percentage immutability, EELS, save/open and PNG/SVG/CSV/NPZ exports. These reports retain zero solver calls and unchanged result/project fingerprints. The present interactive check confirms the running local window; it does not independently repeat that entire checklist or assert completion of the user's current calculations. Evidence: `outputs/v061_final_acceptance/local_windows_environment.json` and the existing `source_double_final`, `frozen_single` and `frozen_double` reports.

Independent integrity recheck for this documentation update confirms 426/426 regression passes in the saved XML (zero failures/errors/skips), 204/204 unchanged production checkpoint hashes, and the unchanged ZIP SHA256 `9fd5e71437d2c26d4595abb7adde9436e4c333ce18f3a57cf381b0c541bfd94f`; ZIP CRC also passes. No tests or simulations were rerun and no rebuild was required. Evidence: `outputs/v061_final_acceptance/final_release_integrity.json`.

## Authorized publication and reproducibility

The publication task authorizes merging the validated development history into **main**, pushing main, creating annotated tag **v0.6.1-beta.1** at final main HEAD, and publishing a GitHub **prerelease** (not stable/Latest). Preflight found origin/main to be an ancestor of the validated branch, with no existing v0.6.1-beta.1 tag or release. Main must be fetched and rechecked immediately before the fast-forward push; branch protection must be respected. Unrelated local files and production checkpoints must not be staged or changed.

The [release notes](RELEASE_NOTES_0_6_1_BETA_1.md), [README](../README.md), [Windows installation](INSTALL_WINDOWS.md) and [User Manual](USER_GUIDE.md) identify the current version, real `EMCD-Sim/EMCD-Sim.exe` archive path, 97-grid/2048-MiB defaults, scientific scope and clean-machine limitation. The runtime source remains identical to build revision `e66c97923bd4838188ed03c424dc9973ada55c25`; subsequent changes concern documentation and acceptance only. The frozen About dialog correctly retains that actual build revision.

The original ZIP (108,703,899 bytes, SHA256 `9fd5e71437d2c26d4595abb7adde9436e4c333ce18f3a57cf381b0c541bfd94f`) and its external `SHA256SUMS.txt` are the only requested release assets. The archive is not rebuilt or modified. The publication audit checks final remote main/tag, release flags, asset downloads/checksum and preserved v0.6.0 metadata; its local machine-readable records are stored separately under `outputs/v061_publication/`. A release tag/source revision can therefore be newer than the binary's recorded runtime build revision without changing the numerical code.

Public release location: [v0.6.1-beta.1](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.6.1-beta.1). Release publication does not promote experimental validation, global convergence or independent clean-machine testing to PASSED.
