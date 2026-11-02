# EMCD-Sim v0.7.0-beta.1 Windows candidate acceptance

## Clean-commit rebuild milestone

The accepted precommit candidate documented below remains preserved, including
ZIP SHA256 `6e11598ddaf97e793210a65fc5140acca6f904b83d9dbf04f154cbad8067f9ed`.
Its byte-identified runtime and tests are being committed without further
algorithm changes. A new, distinct clean-commit Windows build and repeated
native/full-suite acceptance are pending for this milestone. The precommit
PASS below is not a claim that the forthcoming binary has already passed.
Final clean-build evidence will be recorded after execution, with the build
source commit distinguished from any later documentation-only commit.

Earlier released v0.6.1 Windows betas used the superseded Born/MDFF convention;
their signed magnetic EMCD results require revalidation. Preserve historical
arrays and provenance. Intermediate corrected source identifying as 0.6.1b3
must be distinguished by its exact source/convention, not relabeled blindly.
Independent clean-machine installation remains untested.

**PASSED: automated same-host native Windows candidate acceptance. GO for local candidate testing/review.** Independent clean-machine installation and exhaustive manual usability acceptance remain NOT TESTED. No formal release is published.

## Source, build and artifact identity

- Application: `0.7.0b1` / `v0.7.0-beta.1`; PE File/Product numeric tuple `(0,7,0,1)`, FileVersion `0.7.0.1`.
- Active convention: `forward_born_dagger_g_minus_h_v1`.
- Branch: `release/v0.7.0-beta.1-candidate`.
- Base commit: `8d55721dcb05aaa01eb0c750837089e0363f9eb7` plus the approved uncommitted harness correction and new tests. No new commit was created. Build dirty state is truthfully recorded as `true`.
- Exact raw runtime-source tree SHA256: `e66ee196ef7b55ee0e623a89f50f9d04b573d0e13505279de7c1757affa473e6`.
- Build/test input-tree SHA256: `af5853b4347edf5cc6e988b893b37b744a82ecd6909000f162f71caa4edad4e1`.
- Tree digests use SHA256 of canonical JSON (sorted keys, compact separators) mapping relative paths to raw-file SHA256. Complete inventories are in `harness_fix_v3/source_fingerprint.json`; bundled build info contains every runtime module hash.
- Validated physics ancestor/main remains `4f57815646d023957a81ad15fdaa684c02a54442`.
- Worktree: `C:\Users\peng863\EMCD-Sim\build\v070b1-candidate-source`.
- Distinct build root: `build/windows-v0.7.0-beta.1-harness-fix-1/`.
- Build time (UTC): `2026-11-02T05:09:00.412211+00:00`. Existing Python3.11.17/PyInstaller6.22.3 Windows packaging environment reused, without dependency changes.

This is a local portable candidate, not a GitHub Actions artifact or GitHub release. No push, tag, release, main merge or Stage4.2 rerun occurred. The previous EXE and preacceptance archive were preserved.

## Root cause and exact harness-only correction

The original bundled cancellation harness stayed in Automatic numerical mode while assigning its intended tiny test profile. Solver/geometry refresh and start_emcd resolution legitimately replaced that profile with Automatic starting values. It then timed out waiting90seconds for the initial Double calculation, before cancellation probes. This was a harness setup error; production Automatic behavior was not faulty.

The unchanged original EXE independently reproduced exit1 at102.150seconds after showing a responsive window at6.961seconds. Normal launch/WM_CLOSE exited0 at15.460seconds. Direct-file stdout/stderr ruled out full PIPE blockage as the explanation. Original failure evidence remains in native_v1 and cancellation_diagnosis_v2. Fine-grained original frozen initialization stages were not internally timestamped and have not been fabricated.

Only `src/emcd_sim/gui/cancellation_acceptance.py` changed among runtime modules. It selects Manual after reset/source setup and before assigning numerical controls; checks Manual mode and every requested profile value after refresh; constructs the actual reciprocal basis, asserts exactly three retained beams; and records requested/actual values plus signed hkl. A mismatch fails before start_emcd. The applied diff is `harness_fix_v3/harness_applied.diff`.

| Parameter | Requested and actual in all three new EXE runs | Old Automatic setup |
|---|---:|---:|
| Beam cutoff (cycles/Angstrom) | 0.9 | 3.2 |
| Potential cutoff (cycles/Angstrom) | 1.8 | 2.5 |
| Retained basis | 3: (000),(-200),(200) | 27 |
| Angular grid | 9 | 97 |
| Depth nodes | 17 | 64 |
| FFT mesh | 24 | 32 |
| Aperture subpixels | 16 | 64 |
| Energy samples control | 9 | 241 |
| Energy halfwidth (eV) | 0.5 | 1.0 |

Maximum slice step2nm and RAM budget2048MiB remain unchanged and are recorded in the actual settings. Numerical controls are not a claim that every energy-mode path consumes every control value. No timeout, latency assertion, worker policy, memory admission, physical propagation, MDFF, production Automatic behavior, GUI layout or default changed. Existing bounded90-second completion waits and the under2-second measured cancellation condition were retained.

## Actual native cancellation and repeatability

The extracted EXE ran in three fresh processes using native Qt windows and Windows-only PATH with Conda/Python runtime paths removed. External monitoring recorded UTC process start, verified visible responsive windows using Win32 WM_NULL, process trees, memory and return codes. No fixed sleep alone was treated as readiness. Existing harness predicates waited for entry into real numerical work before cancel requests.

| Run / PID | Responsive window (s) | Whole harness (s) | Worst cancel-to-idle (s) | Peak working set (MiB) | Exit |
|---|---:|---:|---:|---:|---:|
| 1 / 30628 | 8.614 | 35.451 | 0.470878 | 208.25 | 0 |
| 2 / 15012 | 42.659 | 74.681 | 0.372537 | 206.97 | 0 |
| 3 / 5240 | 13.466 | 28.141 | 0.321297 | 208.73 | 0 |

Each process passed nine existing scenarios: BW Double depth, MS Double outgoing/depth, Both first-solver cancellation, near-completion, repeat request, Single BW, and uninstrumented BW/MS paths. Controlled scenarios retain the existing180ms synchronization delay at real work checkpoints; they do not substitute mocked calculations. Separate uninstrumented work also passed. Near-completion and queued-result races are reported separately from active-kernel evidence; not every one of the27 scenario checks is described as mid-kernel cancellation.

Recorded requested/acknowledged/stopped/idle times and GUI timer ticks establish delivery and safe termination. A completed-before-cancel result cannot pass the required acknowledgement and cancelled-terminal-state assertions. Previous result object/array fingerprints, browser record count, saved-project SHA and load integrity remained intact; no incomplete result was registered. Reservations were released and controls restored. Real BW restart and MS completion after cancellation passed; completed BW/MS fingerprints were identical across all three fresh processes. Each EXE exited0, with no native crash or remaining owned process; no forced termination was needed. These bounded checks observed no resource leak, rather than proving arbitrary-duration memory behavior.

Evidence: `harness_fix_v3/cancellation_latencies.csv`, `cancellation_repeatability.json`, and native_harness_fix_v3 cancellation reports, process JSONL and direct logs. Monotonic worker timestamps and UTC process observations are retained without manufacturing internal frozen stage timestamps. Fresh-process tests are not an OS-cache-cold boot or independent clean-machine test.

## Regression, packaged GUI and scientific comparisons

- **Full practical suite:611 passed,2 expected optional WIEN2k-companion skips,0 failures/errors**;613 collected. Source/test fingerprint unchanged throughout. Result: `outputs/physics_correction_final_integration/v070b1_harness_fix_v3_run1/`.
- **Focused:37 passed** (the requested35 plus two new wrong-grid/wrong-basis fail-before-worker regressions). Source native preflight also passed all nine cancellation scenarios, worst idle0.496671seconds.
- First focused launch had27passes/10fixture setup errors because its new basetemp parent did not yet exist. That report is retained as focused.xml; creating the output parent and running a fresh directory produced focused_retry1.xml. No test, assertion or tolerance was weakened.
- Five new native packaged GUI cases passed: [001],[017],[117],[710],[111], each Single/Double with Both BW/MS. Includes diffraction/Bragg, signed(2,-2,0), maps/EELS, About/version, resource warnings, requested slice-step editing/defaults, exports, project save/reopen and array preservation.
- Native legacy-project/two-detector-worker validation passed; no worker-limit or execution-policy change.
- Eight **new** matched source/EXE Ni[017] comparisons passed, rerun because the binary changed. Raw source/EXE differences, magnetic percentage-point and PRB differences are all zero. Unchanged acceptance bounds:0.001 raw relative and0.01pp.

The scientific reference is300kV,10nm,+15mradY with exact(200)Bragg X, crystal[001] magnetization rotated into local frame; beam3.2,potential3.8 cycles/Angstrom, grid17,depth33,FFT32,subpixels32,max step0.04nm,eta=beta=1. Native L3/L2 energies831.271/848.698eV remain unshifted. This explicit bounded profile does not change production defaults.

| Channel | Solver | Edge | Python magnetic (%) | EXE magnetic (%) |
|---|---|---|---:|---:|
| single | bloch | L3 | 11.492356 | 11.492356 |
| single | bloch | L2 | -18.6284725 | -18.6284725 |
| single | fft-multislice | L3 | 11.4963713 | 11.4963713 |
| single | fft-multislice | L2 | -18.6349952 | -18.6349952 |
| double | bloch | L3 | 13.8391021 | 13.8391021 |
| double | bloch | L2 | -22.4122785 | -22.4122785 |
| double | fft-multislice | L3 | 13.8394472 | 13.8394472 |
| double | fft-multislice | L2 | -22.4128653 | -22.4128653 |

All four raw reversal intensities, N/M, Flip-M and conventional differences and configurations are retained in JSON/CSV/NPZ. The prior physics correction reverses magnetic-odd signs for conventional Ni references while preserving their reversal-even signals; general site interference must be recalculated, not fixed by arbitrary historical sign flipping. Absolute experimental RP/LP handedness remains uncalibrated.

Warnings were retained: existing small-viewport constrained_layout and Qt deprecation warnings in tests; nonfatal conda-meta/optional scipy.special._cdflib build hooks. No required import or native crash occurred. These warnings were not suppressed or used to change physics/layout. Build invocation through CMD returned0.

## Integrity and artifacts

The three approved raw physics-kernel SHA256 values remain:

- single_channeling_tensor.py: `3c47bd37c8da7ec881441cb9cdee66c537b36b86dd2e5b0838251c04ce9e3d61`.
- double_channeling.py: `713945ace6630f95f8b4f461e6c137a8806b60212f744a81aec51cc46fb8f3de`.
- multislice_double_channeling.py: `9ec1ba6c071ff751540f9ef4ac4c864d139cb8a458eb85cddc9ad04ba0a880df`.

All323 protected files including204 production checkpoints,9756 historical research files,19 original scientific working files,8 audit files and preserved dirty-worktree379checked files/9user changes/index were freshly verified unchanged. Main and other preserved branches/worktrees retain their identities. No references or Stage1–4.2 outputs were regenerated.

- Final extracted EXE: `C:\Users\peng863\EMCD-Sim\build\v070b1-candidate-source\build\windows-v0.7.0-beta.1-harness-fix-1\final-extracted\EMCD-Sim\EMCD-Sim.exe`.
- Final ZIP: `C:\Users\peng863\EMCD-Sim\build\v070b1-candidate-source\build\windows-v0.7.0-beta.1-harness-fix-1\EMCD-Sim-v0.7.0-beta.1-harness-fix-1-Windows.zip`.
- Final ZIP SHA256: `6e11598ddaf97e793210a65fc5140acca6f904b83d9dbf04f154cbad8067f9ed`.
- New EXE SHA256: `fb2cd37dab3e71437592011ff825abd67b6db4760962b2a9616c33d1565750ac`.
- New preacceptance ZIP SHA256: `35d1809c9259e7b936d3bad929d3ace1aca3cb7828a4a2b57244e515b6eddbed`.
- Original EXE SHA256 preserved: `ae003ee94f09b9e658087286df997912faec12824d7fa595c46a4867670ec459`.
- Original preacceptance ZIP SHA256 preserved: `70a2a00bf0006ffab3eb03d209642f3a383194bcfc0f83d1e018be335229902f`.

Final ZIP was assembled only after mandatory gates passed. It includes complete portable runtime,README,build_manifest.json,SHA256SUMS.txt and native/regression/provenance evidence. Re-extraction verified every payload file, and EXE bytes match the tested binary. The final extracted application was separately launched, observed responsive, and closed cleanly with exit0/no owned process left. External final_build_manifest.json,FINAL_SHA256SUMS.txt and candidate_provenance.json identify the archive without self-referential ZIP hashes.

Tracked changes in this continuation: cancellation_acceptance.py and this acceptance document; new test_cancellation_acceptance_profile.py remains untracked. All changes are uncommitted. Ignored candidate-only diagnostics/builds are separate. Applied source diff, test hash, full input inventory and pre-correction report copy are preserved in harness_fix_v3.

## Remaining limits and recommendation

**GO for this bounded, automated same-host Windows candidate validation and local user testing.** A formal prerelease/push/tag remains separately authorized work. Independent clean-machine installation/manual usability and OS-cold-boot acceptance have not been performed. The source is intentionally identified by exact dirty-tree hashes, not falsely attributed to a new clean commit.

Scientific limitations remain: effective XMCD-constrained MDFF is not full complex-transition DFT MDFF; absolute energy/magnetic-handedness calibration remains unverified; [111] numerical convergence is incomplete; known Stage4.2 30nm/delta-X=-5mrad/Y=+15mrad/L2 detector-grid failure persists. Projected IAM,finite ZOLZ/frozen longitudinal transfer, incomplete absorption/TDS and absent electron-count/SNR calibration remain. BW/MS agreement or these small acceptance profiles do not certify general convergence.

Rollback needs no destructive operation: retain and launch the original portable directories, or use a separate worktree at the validated ancestor. Preserve old signed results with original/legacy provenance rather than relabeling or overwriting them.
