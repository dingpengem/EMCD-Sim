# EMCD-Sim v0.7.0-beta.1 clean-commit Windows acceptance

**PASSED for bounded same-host native Windows release-candidate validation.** No tag, release, push or publication has occurred. Independent clean-machine installation and comprehensive manual usability remain **NOT TESTED**.

## Committed source and reproducibility

- Existing version/packaging commit retained: `8d55721dcb05aaa01eb0c750837089e0363f9eb7`.
- Clean build-source/harness commit: `f80a96f6e9f36c63dd6f673e70bc54ce4030963e`.
- Exact build Git tree: `88d2fac2c5358578f0dbf0adc3f260a441c0cf49`.
- Raw runtime-source tree SHA256: `e66ee196ef7b55ee0e623a89f50f9d04b573d0e13505279de7c1757affa473e6`.
- Build/test input-tree SHA256: `af5853b4347edf5cc6e988b893b37b744a82ecd6909000f162f71caa4edad4e1`.
- Application `0.7.0b1`, display `v0.7.0-beta.1`, PE tuple `(0,7,0,1)` / FileVersion `0.7.0.1`.
- Convention `forward_born_dagger_g_minus_h_v1`.
- Branch/worktree: `release/v0.7.0-beta.1-candidate` / `C:\Users\peng863\EMCD-Sim\build\v070b1-candidate-source`.
- The source worktree was clean and HEAD fixed at the build-source commit throughout build, Python suite and native acceptance. Runtime/tests/packaging matched the previously validated source contents; committed text equality was verified with CRLF normalization.
- Build timestamp (UTC): `2026-11-02T05:42:35.300581+00:00`.

Raw SHA256 inventories and digest definitions (SHA256 of compact, sorted JSON path/hash mappings) are in `outputs/windows_v070b1_acceptance/clean_commit_rc1/clean_source.json`. Bundled build_info records exact module hashes, clean state, source commit and toolchain. A subsequent documentation-only acceptance commit records these outcomes; it is not represented as the executable build commit. Source/provenance reproducibility is established; bit-for-bit rebuilding of timestamped Windows binaries/ZIPs across machines is not claimed.

Build environment: `{"platform": "Windows-10-10.0.26200-SP0", "python_executable": "C:\\Users\\peng863\\EMCD-Sim\\build\\windows-rc\\venv\\Scripts\\python.exe", "python_prefix": "C:\\Users\\peng863\\EMCD-Sim\\build\\windows-rc\\venv", "python_version": "3.11.17"}`.

Dependency/tool versions: `{"PySide6": "6.12.0", "ase": "3.29.0", "matplotlib": "3.11.2", "numpy": "2.4.6", "pyinstaller": "6.22.3", "scipy": "1.17.1"}`.

## Critical v0.6.1 scientific compatibility warning

Earlier released v0.6.1 Windows betas used the superseded Born/MDFF convention. Their signed magnetic EMCD results require revalidation or recalculation. Preserve raw historical arrays and original source/version/convention; do not blindly flip or relabel results. Intermediate corrected source4f578156 still identified as0.6.1b3, so exact source/convention overrides version-name inference. This does not imply that every old nonmagnetic spectrum, diffraction intensity or thickness trend is invalid.

## Exact reviewed changes

The original version commit is preserved. The harness commit changes four files only: cancellation_acceptance.py, its two negative regression tests, release notes and this acceptance document. The final evidence update changes documentation only. No generated output, checkpoint, EXE or ZIP is included in these commits.

The harness explicitly selects Manual before assigning its tiny profile; asserts mode and all requested controls after refresh; constructs and verifies the actual three-beam basis; records requested/actual settings and signed hkl. A wrong grid or beam count fails before a worker starts. Production Automatic mode is unchanged. Existing 90-second completion waits, under2-second measured cancellation condition, real numerical kernels and existing synchronization probes are retained. No threshold was relaxed.

The original error was Automatic resolution replacing intended3-beam/grid9 settings with27-beam/grid97 before the initial Double calculation. The original EXE reproduced a responsive window at6.961s and initial wait failure/exit1 at102.150s, before cancellation probes. Original failures, precommit acceptance and SHA256 are preserved separately; the new clean binary is independently tested rather than relabeled.

| Numerical control | Requested / actual in every new EXE cancellation run |
|---|---:|
| Beam / potential cutoff (cycles/Angstrom) | 0.9 / 1.8 |
| Actual retained hkl | (000),(-200),(200):3 beams |
| Angular grid / depth nodes | 9 / 17 |
| FFT mesh / aperture subpixels | 24 / 16 |
| Energy samples control / halfwidth (eV) | 9 / 0.5 |
| Maximum slice step / RAM budget | 2nm / 2048MiB (unchanged) |

Controls do not imply that every selected energy mode consumes every value. This bounded diagnostic profile is not a converged production recommendation. No default, memory limit, worker policy, GUI layout or scientific algorithm changed.

## New native EXE acceptance

Five fresh native GUI cases passed: [001],[017],[117],[710],[111]. Each exercised Single/Double with Both BW/MS, diffraction/Bragg and signed indexing, magnetic/nonmagnetic maps, EELS, raw/relative displays, save/reopen, scientific exports, default/editable slice controls, numerical/resource warnings and About/build metadata. Native legacy-project/two-worker safety also passed. No offscreen test is substituted for these frozen Windows checks.

Three fresh native cancellation processes ran against the newly extracted package:

| Run/PID | Responsive Qt window(s) | Harness duration(s) | Worst cancel-to-idle(s) | Peak working set(MiB) | Exit |
|---|---:|---:|---:|---:|---:|
| 1/6048 | 8.109 | 28.972 | 0.330141 | 208.50 | 0 |
| 2/9524 | 6.513 | 26.661 | 0.353588 | 208.02 | 0 |
| 3/12952 | 6.607 | 26.868 | 0.345363 | 209.03 | 0 |

All three runs passed9/9 scenarios. Actual BW/MS Double depth/outgoing work and uninstrumented work were cancelled, with acknowledgement/stopped/idle timestamps, GUI timer responsiveness and restored controls. Near-completion and queued-result races are distinguished from active-kernel tests: the27 scenario checks are not all described as mid-kernel cancellation. The existing180ms controlled checkpoint delay synchronizes requests and does not mock calculations; uninstrumented paths also passed. A finished-before-request case cannot satisfy the required acknowledgement/cancelled-terminal-state assertions.

Previous completed results, exact array fingerprints, browser record counts, saved-project SHA and load integrity remained intact. No incomplete result was registered. Memory reservations cleared; BW restart and MS completion succeeded after cancellation. Completed BW/MS fingerprints were identical across fresh processes. All processes exited0, with no remaining owned child or observed native crash. Short bounded runs observed no reservation/process leak, not proof of unlimited-duration resource behavior.

External observations use native Qt windows, Windows-only PATH, removed Python/Conda runtime paths, direct log files, actual responsive-window checks and bounded owned-process cleanup. Worker-entry predicates establish computing readiness, not a fixed sleep alone. UTC process observations and monotonic request/acknowledge/stop/idle times are retained. Fresh process and first extracted launch are not independent clean-machine or OS-cache-cold-boot acceptance.

## Python and scientific validation

- Full practical suite: **611 passed,2 expected optional WIEN2k-companion skips,0 failures/errors** (613 collected); source/test fingerprint unchanged.
- Affected focused suite: **37 passed** (requested35 plus two wrong-profile guards).
- Saved corrected scientific evidence: **32/32 BW/MS comparisons revalidated**, read-only and without rerunning historical simulations.
- Eight **new** matched Python/EXE Ni[017] comparisons passed. Raw intensities and magnetic/PRB differences are zero; existing bounds remain0.001 raw relative and0.01pp.

Reference profile:300kV,10nm,+15mradY with exact(200)Bragg X; crystal[001] magnetization rotated to local coordinates; beam3.2/potential3.8 cycles/Angstrom,grid17,depth33,FFT32,subpixels32,max step0.04nm,eta=beta=1. Native energies831.271/848.698eV remain unshifted. All four raw reversal intensities, even/odd components, Flip-M/conventional differences, configurations and source hashes are retained in JSON/CSV/NPZ.

| Channel | Solver | Edge | Python magnetic(%) | EXE magnetic(%) |
|---|---|---|---:|---:|
| single | bloch | L3 | 11.492356 | 11.492356 |
| single | bloch | L2 | -18.6284725 | -18.6284725 |
| single | fft-multislice | L3 | 11.4963713 | 11.4963713 |
| single | fft-multislice | L2 | -18.6349952 | -18.6349952 |
| double | bloch | L3 | 13.8391021 | 13.8391021 |
| double | bloch | L2 | -22.4122785 | -22.4122785 |
| double | fft-multislice | L3 | 13.8394472 | 13.8394472 |
| double | fft-multislice | L2 | -22.4128653 | -22.4128653 |

Scientific convention audit: contractions use `Re sum_ab R_ab T_ba = Re Tr(RT)`; `T=L L†` remains and forward transition amplitudes use `L*`; Double atomic-site phase is `exp(+2πi(g−h)·u)`. The legacy sign convention is not restored. Independent Born, phase/free-outgoing, parity and source-guard tests are included in the full suite. The three approved raw kernel SHA256 values remain:

- single_channeling_tensor.py: `3c47bd37c8da7ec881441cb9cdee66c537b36b86dd2e5b0838251c04ce9e3d61`.
- double_channeling.py: `713945ace6630f95f8b4f461e6c137a8806b60212f744a81aec51cc46fb8f3de`.
- multislice_double_channeling.py: `9ec1ba6c071ff751540f9ef4ac4c864d139cb8a458eb85cddc9ad04ba0a880df`.

## Artifacts and preservation

- Final EXE: `C:\Users\peng863\EMCD-Sim\build\v070b1-candidate-source\build\windows-v0.7.0-beta.1-clean-commit-rc1\final-extracted\EMCD-Sim\EMCD-Sim.exe`.
- EXE SHA256: `2455cc3407f2098daae1387d3b4d1c640f558d4a9bfcdd1411be9c2c35767e90`.
- Final ZIP: `C:\Users\peng863\EMCD-Sim\build\v070b1-candidate-source\build\windows-v0.7.0-beta.1-clean-commit-rc1\EMCD-Sim-v0.7.0-beta.1-clean-commit-rc1-Windows.zip`.
- ZIP SHA256: `be224e9ee68f94ef81439fd7672631c21f6c104d5dcc39ea866cff8ded936fae`.
- Preserved precommit ZIP: `C:\Users\peng863\EMCD-Sim\build\v070b1-candidate-source\build\windows-v0.7.0-beta.1-harness-fix-1\EMCD-Sim-v0.7.0-beta.1-harness-fix-1-Windows.zip`.
- Preserved precommit ZIP SHA256: `6e11598ddaf97e793210a65fc5140acca6f904b83d9dbf04f154cbad8067f9ed`.

The new ZIP includes complete runtime,README,build_manifest.json,SHA256SUMS.txt and compact native/regression/provenance logs. Every final extracted payload file matches; final EXE bytes match the independently accepted binary. A final direct launch and WM_CLOSE exited0 without an orphan. Final manifest/checksum/provenance are outside and inside the package as appropriate, without self-referential archive hashes.

All323 protected files including204 checkpoints,9756 historical research files,19 original scientific working files,8 audit files and preserved worktree379checked files/9user changes/index were freshly verified unchanged. All earlier candidates remain intact; no Stage4.2 or historical regeneration. Local main stays4f578156 and the original user branch/worktree are untouched.

Complete changed-file list relative to validated physics ancestor4f578156 (version commit plus harness commit; final evidence commit is documentation-only):

- `.github/workflows/windows-build.yml`.
- `README.md`.
- `docs/CHANGELOG.md`.
- `docs/INSTALL_WINDOWS.md`.
- `docs/QUICK_START.md`.
- `docs/RELEASE_NOTES_0_7_0_BETA_1.md`.
- `docs/USER_GUIDE.md`.
- `docs/WINDOWS_0_7_0_BETA_1_ACCEPTANCE.md`.
- `packaging/BETA_README.txt`.
- `packaging/README.md`.
- `packaging/build_windows.ps1`.
- `packaging/windows_version_info.txt`.
- `pyproject.toml`.
- `src/emcd_sim/__init__.py`.
- `src/emcd_sim/gui/app.py`.
- `src/emcd_sim/gui/cancellation_acceptance.py`.
- `src/emcd_sim/gui/desktop_acceptance.py`.
- `src/emcd_sim/gui/emcd_forward.py`.
- `src/emcd_sim/gui/project_io.py`.
- `src/emcd_sim/gui/runtime.py`.
- `src/emcd_sim/gui/scientific_acceptance.py`.
- `tests/test_cancellation_acceptance_profile.py`.
- `tests/test_portability.py`.
- `tests/test_v070_metadata.py`.

Evidence: `outputs/windows_v070b1_acceptance/clean_commit_rc1/`, `native_clean_commit_rc1/`, and `outputs/physics_correction_final_integration/v070b1_clean_commit_rc1_run1/`. Exact commit receipt including the later documentation-only HEAD is saved as clean_commit_rc1/final_commit_receipt.json. No build artifact or generated evidence is committed.

## Limitations and GO/NO-GO

**GO for the reproducible local Windows research release candidate and reviewed GitHub source push after separate authorization and a fresh remote-ancestry check. No push was performed.** No main merge was performed.

**NO-GO recommendation for formal GitHub prerelease publication until independent clean-machine/manual Windows acceptance is completed or explicitly waived for a disclosed research beta.** The native automated same-host candidate gate passed; clean-machine installation remains untested. No tag/release/publication was performed.

Effective XMCD-constrained MDFF is not genuine full complex-transition DFT MDFF. Absolute energy and RP/LP magnetic handedness remain experimentally uncalibrated. [111] convergence is incomplete; Stage4.2 30nm/delta-X=−5mrad/Y=+15mrad/L2 detector-grid failure persists. Finite projected ZOLZ/IAM/frozen longitudinal transfer, incomplete absorption/TDS and absent calibrated electron-count/SNR remain. BW/MS agreement and these small profiles do not establish universal numerical convergence or experimental validation.

Existing conda-meta/optional scipy.special._cdflib packaging warnings and small-viewport constrained_layout/Qt deprecation warnings are retained. One external final-launch observer initially failed Python parsing because a prior UTF-8 BOM was copied through the Windows locale; it was regenerated explicitly as UTF-8 before launching the EXE. That external-only correction changed no packaged byte or criterion; the actual final EXE then launched and exited0. The diagnostic note is retained in clean_commit_rc1. No required application import failure or native crash occurred. No threshold, dependency, layout or physical model was changed to silence warnings. Rollback uses preserved directories or a separate worktree; no reset or historical relabeling is required.
