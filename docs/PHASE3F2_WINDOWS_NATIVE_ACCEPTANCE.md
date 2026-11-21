# Phase 3F-2: Windows Native Build and Final Acceptance

## A. Decision and source identity

**CONDITIONAL NATIVE GO** for the final development bundle on the recorded Windows host and bounded supported workflows. All final native profiles passed, their logs contain no exception/failure traces, and independently validated saved numerical arrays match exactly. Clean full-suite, clean-machine, unrestricted runtime certification and formal release acceptance remain separate.

| Identity | Exact value |
| --- | --- |
| Absolute working directory / Git worktree root | `C:/Users/peng863/EMCD-Sim/.worktrees/windows-adaptive-compute` |
| Branch throughout | refactor/physics-readability |
| Starting HEAD | 81d13ebd3120cc4977feaeba87a079e0e13c019b |
| Phase 3F-1 corrected source candidate | ce7677ed9cec6ba9e53b24fe6c592aafe64bf004 |
| Previously verified application implementation | 20009f4ac138731e04b1a479acc6b76ce5a5717b |
| Final stabilization implementation | 41e376c3b891df2ef225c43a5db0e1f6bc1794b8 |
| **Frozen build/source-archive commit** | **473ac666592e11fc962ecb64d27354ccb18d4ba0** |
| Public version | 0.9.0b2 / v0.9.0-beta.2, unchanged |
| Development label | EMCD-Sim v0.9.0-beta.2 - Phase 3F-2 native development 473ac66 |

The final commit updates the existing registration pointer to its reviewed implementation. This report is a documentation-only successor; it does not change the built source. No checkout move, reset or new Git worktree occurred. Starting ancestry, clean status and registered identities were verified.

Final candidate root: `C:/Users/peng863/EMCD-Sim/.worktrees/windows-adaptive-compute/build/phase3f2/candidate-473ac66`.

Runner logs and exact commands: `C:/Users/peng863/EMCD-Sim/.worktrees/windows-adaptive-compute/build/phase3f2`.

The existing packaging/build_windows.ps1 ran from a clean Git archive snapshot with a fresh native-build directory, an isolated alternate index, explicit development archive names and the existing reviewed Qt corresponding sources. Exactly 808 tracked files, the archive commit comment, scientific input bytes and clean snapshot/index were verified. The original checkout/index was not replaced.

Final build wall time: **627.734 seconds**, exit 0. Build UTC: 2026-11-21T09:03:10.023666+00:00. The existing interpreter was C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe: Python 3.11.17, NumPy 2.4.6, SciPy 1.17.1, PySide6/Qt 6.12.0, PyInstaller 6.22.3, ASE 3.29.0 and spglib 2.7.0. No dependency upgrade or version bump occurred. Source, environment and commands are traceable repeatable inputs; byte-for-byte rebuild reproducibility was not separately tested.

## B. Final artifacts

All artifacts below identify frozen source 473ac666592e11fc962ecb64d27354ccb18d4ba0. The EXE is an onedir application: use the Windows ZIP containing its adjacent _internal directory.

| Artifact / absolute path | Bytes | SHA-256 |
| --- | --- | --- |
| Windows EXE<br>`C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\build\phase3f2\candidate-473ac66\native-build\dist\EMCD-Sim\EMCD-Sim.exe` | 14,833,519 | `8c2da6fc0f6df6cfba8035efdfb989ec1c3b1a84808bb4d0e64bab544a1a497a` |
| Windows ZIP<br>`C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\build\phase3f2\candidate-473ac66\native-build\EMCD-Sim-Phase3F2-473ac66-Windows-dev.zip` | 106,047,219 | `aed8d51164e19107778bbe9aeb27ced19e0a6f4cfcd67b2e932ebecce8536ad1` |
| Application source ZIP<br>`C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\build\phase3f2\candidate-473ac66\native-build\corresponding-source\EMCD-Sim-source.zip` | 27,090,742 | `4c0a5c09755961970b90eb6f21a1310c01f3a8f32c62d8c9bed9178ef91c30e3` |
| Qt source kit<br>`C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\build\phase3f2\candidate-473ac66\native-build\EMCD-Sim-Phase3F2-473ac66-Qt-sources-dev.zip` | 102,673,935 | `e3c9fa8c535852ed4c836d9f26615f04a9212ddf659e0bf45776332b368656eb` |

Exact arguments, source trees and environment are in candidate.json and windows-build-473ac66-run.json. Detailed inventories are native-build/build_manifest.json, the existing SHA256SUMS.txt files and package-verification.json. After native execution, all 646 inventoried files and all four artifact identities were rechecked unchanged; no extra files appeared inside the bundle.

## C. Actual frozen Windows workflows

Every row executed the final EXE sequentially on Qt's **windows** platform, from the bundle directory, with empty PYTHONPATH, PATH restricted to the bundle/Windows directories and isolated workspace/user/cache directories. Widgets, workers, solvers and persistence are real. File-dialog choices and confirmation answers are automated.

Each evidence stem has a .log and -run.json recording argv, cwd, source HEAD, environment, PID, timeout and exit. Workflow JSON, saved projects and screenshots are in the corresponding native-* candidate directory. Source-only entry points emcd-gui, emcd-import-transitions and emcd-ni-local-mdff also passed help/import checks before freezing.

| Profile / evidence stem | Launch-to-exit seconds | Observed final result |
| --- | --- | --- |
| `native-help-473ac66` | 30.219 | Application CLI help; exit 0. |
| `native-release-help-473ac66` | 5.265 | Existing native QA CLI help; exit 0. |
| `native-startup-473ac66` | 14.172 | Normal main-application startup and default elastic preview; screenshot and automatic clean shutdown. |
| `native-desktop-473ac66` | 73.375 | Ni [017] Single/Double BW + FFT, Bragg/elastic preview, About/version, slice-step edits in both numerical modes, Save/Open and exports. |
| `native-providers-473ac66` | 433.563 | 14 Ni/Fe/O cases + 2 manual spectral cases, BW/FFT and Single/Double; source selection/preview, restore/recalculate, invalid/source-tamper rejection and exports. |
| `native-grouping-473ac66` | 59.282 | Full 56-atom Fe3O4 structural grouping and Save/Open; actual Cr BW Single, reversal restoration and unsupported-axis rejection. |
| `native-multisite-473ac66` | 332.406 | 10 real calculations: Ni BW Single/Double plus four Cr and four Fe3O4-motif combinations; normalization, CSV, history, comparison, delete, Save As/reopen; no callback errors. |
| `native-resources-473ac66` | 22.875 | Actual 4 workers, original 2,048 MiB request/allocation; saved arrays and resource settings restored after deliberate unexecuted edits. |
| `native-cancellation-473ac66` | 40.093 | All 9 cases, queued completion, immediate restart and saved-result integrity PASS. |
| `native-scientific-473ac66` | 8.500 | Explicit Ni [017] raw-reversal Single/Double x BW/FFT; canonical GUI/root callable identity and unchanged decompositions. |
| `native-desktop-dpi100-473ac66` | 70.797 | Bounded desktop workflow with process-only Qt scale 2/3; recorded effective DPR 1.0. |

Every applicable completion/closed-window assertion passed. Cancellation uses its own outcome/restart/integrity schema, rather than an invented complete field. Final native acceptance had no timeout or forced termination. A final path-filtered process query found no remaining final-candidate GUI process.

## D. Scientific inputs, invariants and independent numerical comparison

The canonical calculation remains emcd_sim.forward_pipeline.calculate(structure, settings, cfg, ...). The retained GUI import re-exports the same callable, asserted inside the frozen scientific profile. No propagation/contraction kernel, equation, accumulation order, geometry convention, sampling setting, memory/worker policy, cancellation checkpoint, reference array or floating-point tolerance changed during this phase.

Full structure, geometry, provider, detector and numerical inputs are recorded in each project's input_parameters.json and metadata/source manifests. The raw scientific profile records frame, hkl, energies and configs: explicit Ni [017], target (200), 300 kV, 10 nm, tilt (-5.586688140406263, 15) mrad, grid 17, depth 33, subpixels 32, FFT 32 and maximum slice step 0.04 nm. Bragg alignment, flip-M, raw A/B and magnetic-odd decomposition checks pass the unchanged original assertions for Single/Double and BW/FFT.

Cr and the seven-atom Fe3O4 magnetic motif use explicit synthetic PSD tensor pairs, local directions and source frames. All four solver/channel combinations and selected-atom denominators 2/3 pass. These are software/scientific-consistency fixtures, not quantitative experimental Cr or magnetite spectra. The separate full 56-atom inverse-spinel CIF check verifies structural 8/16/32 grouping and persistence; it does not infer magnetic order or constitute a magnetic Fe3O4 calculation.

| Independent comparison | Reference | Result |
| --- | --- | --- |
| Existing pre-refactor source equivalence | cdb8836388c5ccc5ae7a614b47894c0ab158a824 | **22 cases / 2,294 arrays exactly equal**; exact-after-qa-fix.log, 29.813 seconds |
| Actual final EXE saved outputs | Previously validated Phase 2 frozen source 6d98694b2367fdb9586f33287f9a09c159c7ef27 | **19 projects / 57 NPZ files / 1,763 arrays exactly equal**, including 448 arrays containing NaNs |

The native comparison uses existing build/regression-recovery/frozen-desktop, frozen-ni-fe-projects (including full-K and manual cases) and frozen-resource-persistence results. References were not regenerated from this candidate. Decoded values, dtype, shape, finite/NaN masks and separate complex components were compared exactly. Both generations' saved manifests were verified and projects loaded through the current schema without rerunning forward calculations. All geometry settings agree.

The initial metadata comparison conservatively flagged one field: 14 old declared/imported cases carried an inactive inherited Ni atomic-parameter dictionary; neutral current settings store None. Reviewing both source versions' mdff_providers.prepare_provider/load_provider confirms these cases consume declared source bytes, not this field. Meaningful historical Ni atomic parameters remain compared.

Seventeen source identities are identical. The two Fe imported-source hashes differ solely because JSON atomic_parameter_path names a different absolute output directory. Removing that one provenance leaf gives exactly equal tensor documents; the original parameter files are byte-identical.

The initial record, including its conservative metadata flags, remains native-reference-comparison.json. native-reference-review.json records the narrowly justified classification and final PASS. No array mismatch was excluded, and no numerical comparison, reference or tolerance was changed.

Eight lightweight preflight tests passed, including strict-headless Ni/Cr BW calculations, canonical API/resource checks, neutral versus explicit Ni geometry and source controls. Phase 3F-1's eight strict-headless solver/channel calculations, six numerical-contract tests and scientific invariants remain prior evidence. The complete regression was not restarted. Subsequent application changes concern persistence and result controls; their affected behavioral checks and final native workflows passed.

## E. Actual screenshot inspection and DPI

These **final-candidate** images were opened and visually inspected, not merely checked for existence:

| Final image actually opened | Visual inspection |
| --- | --- |
| `native-startup.png` | Final frozen default elastic preview renders diffraction spots, beam table, units, legend, Material/geometry controls, toolbar and status. Scrollbars handle long tables and settings. Elastic-provider combo text is elided; no blank figure/error dialog. |
| `native-desktop/double_completed.png` | Final Double BW Ni [017] EELS points, geometry, toolbar and progress/status render at the smaller 1092x600 logical layout. Long reciprocal title is clipped and full spectrum axis/legend requires existing scrolling/maximize controls; no blank result/error dialog. |
| `native-desktop/double_maps.png` | Final exported angular map has complete titles, detector circles, physical units, beam/ZA annotations, magnetic/nonmagnetic panels, color scales and legends. No cropping/blank figure. |
| `native-providers/Fe_declared-xmcd_single_source-preview.png` | Final Global Fe MDFF dialog renders material/edge context, explicit magnetization/handedness declaration, populated source spectra and tensor preview, scrollbars and accessible Cancel/Done. Draft status precedes the profile's subsequent acceptance transaction. |
| `native-grouping/Fe3O4-structural-groups.png` | Final full 56-atom structural inverse-spinel CIF renders atoms/bonds/cell and Fe(A)/Fe(B)/O orbit rows, 8/16/32 counts and 8a/16d/32e labels. Unconfigured local M/MDFF and absence of inferred magnetic order are explicit. Scrollbars and Apply/Cancel are visible. |
| `native-multisite/Cr-manual-pair.png` | Final Local Cr MDFF dialog shows the original ASE site/group, read-only declared M, independent +/-M Hermitian PSD matrices, explicit edges/sampling/frame and reachable Done/Cancel. No Ni context or manufactured opposite tensor. |
| `native-multisite/Fe3O4-results.png` | Final Fe3O4 synthetic motif displays Fe(A)/Fe(B) group comparison, selected-atom N=3 normalization, completed FFT Double result and finite group curves. No stale Cr label/error dialog. Long geometry title is clipped and the full plot requires panel scrolling/maximizing. |
| `native-resources/worker_controls.png` | Final pre-run resource view shows CPU/RAM discovery, Manual requested workers=4 and effective BW workers=4, scrollable controls and geometry-only preview. Empty results table is expected before execution; memory request/restoration is verified in the acceptance JSON. |
| `native-desktop-dpi100/double_completed.png` | Final effective DPR1.0 native capture renders compact controls and Double BW Ni EELS; same long-title clipping/scrolling limits as DPR1.5. No blank plot or blocking overlap. |
| `native-cancellation/restarted.png` | Final post-cancellation restart screenshot renders completed FFT Ni detector A/B curves and magnetic/even traces, enabled Run and disabled Cancel, with no error dialog. Long geometry title and lower panels require scrolling; quantitative cancellation/restart/integrity outcomes are recorded separately. |

At the actual OS scale, Qt recorded available geometry **1280 x 805 logical pixels, logical DPI 96, DPR 1.5**. The process-only QT_SCALE_FACTOR=2/3 check recorded **1920 x 1208, DPI 96, effective DPR 1.0**. Desktop profiles also resized the application to 1280 x 720 and an explicitly marked simulated smaller 1092 x 600 logical window. OS display settings were not changed. Multi-monitor and other-machine modes were not tested.

Remaining visual limitations: long reciprocal-geometry titles clip in narrow panels; some combo/table text is elided or scrollable; complete tall spectra require scrolling or the existing maximize control. Standalone exported maps render full titles, axes, units, legends and color scales. Matplotlib emitted constrained_layout warnings during widget reflow and an automatic-legend-placement performance warning. No blank completed result, blocking overlap or unusable required action was demonstrated. No GUI redesign was performed. Widget captures do not validate every OS decoration or manually operated file-picker appearance.

## F. Resources, cancellation and cleanup

Final resource PID **3092** matches the runner's EXE PID, so its Windows process counters measure the actual frozen application. Manual request/effective BW workers were **4/4**, with policy CPU limit 5 on 12 available logical processors. Requested and bound memory allocation remained **2,048 MiB**. Preflight displayed **Admission: Ready**, estimated peak process memory 411.7 MiB. Save/Open restored resource settings and preserved arrays after deliberate unexecuted control edits.

Both NumPy/SciPy OpenBLAS library paths resolve under the final distribution. NumPy reports OpenBLAS 0.3.31.188.0; both runtimes report one BLAS thread during calculation, retaining the existing restore-after-work policy. The runtime policy still labels this **UNVERIFIED COMBINATION / Warning** and permits conservative execution. This bounded successful run does not promote an arbitrary runtime combination to general native-stability certification.

| Final native process | Peak RSS MiB | Peak process commit MiB |
| --- | --- | --- |
| desktop | 314.11 | 295.89 |
| providers | 1287.51 | 1288.92 |
| multisite | 1150.15 | 1145.69 |
| resources | 279.05 | 256.16 |
| cancellation | 281.58 | 227.74 |

These are whole-process peaks including GUI/history/figures, not kernel-only or aggregate system/process-tree measurements. The multiwindow provider harness retains results until cleanup. The build runner's PowerShell peak is not presented as compiler-tree memory.

All nine cancellation cases passed: bw_full, ms_outgoing, ms_depth, both_first, near_completion, repeat_cancel, single, bw_uninstrumented and ms_uninstrumented. Queued-completion suppression, immediate restart, saved-result integrity and fingerprints passed; errors were empty. Worst observed cancellation-to-idle was **0.524382 seconds**. Controlled-block and uninstrumented cases are separately identified in the evidence; this is not a latency guarantee for arbitrary larger workloads.

Final EXE processes exited and no candidate GUI remained. No unrelated process was terminated.

## G. Package, source, Qt, assets and licenses

| Verified property | Final result |
| --- | --- |
| Source/dirty/version | 473ac66; dirty=false; 0.9.0b2; development label |
| Binary inventory | 646 files; existing sizes/SHA inventories match, including after execution |
| Runtime source correspondence | 111 identities match snapshot and application source ZIP |
| Application source archive | 808 exact tracked files, matching commit comment and snapshot |
| Frozen application/native-QA modules | 108; required_missing=[]; supported GUI forward import included |
| Compiled source origins | 107 application origins checked, all under clean snapshot |
| Scientific packaged data | 8 required files byte-exact, including original Ni input and adaptive coefficients |
| Qt components / translations / assets | 34 / 99 / 41 |
| Corresponding-source kit | 5 reviewed upstream source archives match existing pinned provenance; embedded application ZIP identical |
| Archives/licenses | Windows, application-source and Qt-source ZIP CRC/content checks passed; required application, third-party and Qt notices/replacement-source guides present |

Details are in package-verification.json, build inventories and the existing packaging/check_package_contents.py checks. Reviewed Qt sources match the selected 6.12.0 environment. Source-only utilities need not all be reachable in the GUI EXE; the explicitly retained emcd_sim.gui.forward_pipeline import was specifically verified in the actual PYZ.

The existing venv-over-Conda warning about an absent local conda-meta directory is retained in build logs. Existing packaging handled base-environment libraries; actual final frozen backend paths are bundled and native execution passed. No dependency upgrade or undocumented substitution occurred.

## H. Acceptance boundaries

| Boundary | Status |
| --- | --- |
| Native Windows development acceptance | **CONDITIONAL GO** for the final artifact, recorded host and bounded workflows; no unresolved functional/numerical native defect observed |
| One clean full regression invocation | **NOT ESTABLISHED**: Phase 3F-1 original 1,757 pass / 2 fixture failures / 62 skips, followed by focused recovery, gives combined 1,759 distinct pass / 62 skips; this remains combined coverage |
| Clean-machine acceptance | **NOT TESTED**: isolated PATH/user data on the existing host is not a fresh Windows installation |
| Optional external scientific/ELSEPA/companion datasets | No new evidence claimed; historical optional omissions remain separate, without substitute Ni assumptions or regenerated references |
| Global runtime/convergence/experimental certification | **NOT GRANTED**; existing caution and physical-model limitations remain; synthetic fixtures do not establish experimental calibration |
| Formal release, publication or Research Beta replacement | **NO-GO / not performed**; development artifacts only, with existing release/security requirements still applicable |

No full pytest invocation was restarted. No new physics, architecture cleanup, material fallback, relaxed numerical contract or replacement scientific baseline was introduced.

## I. Stabilization, local commits and handoff

Three candidate/evidence trees remain preserved. **5819efc was not accepted**: the actual PYZ omitted the supported GUI forward import, and its multisite QA did not complete the current Material transaction. Source-native recovery additionally demonstrated the retained-run input-directory save defect. **d9b98c9 was not accepted** because switching Cr to Fe logged a Qt KeyError despite a successful profile exit. **473ac66 is the final accepted candidate**, with callback capture and final log review clean.

Small justified corrections:

- [src/emcd_sim/gui/scientific_acceptance.py](../src/emcd_sim/gui/scientific_acceptance.py) restores its documented Ni [017] reference case through the existing explicit preset after generic defaults became neutral; the canonical GUI/root callable check also makes that supported import reachable to PyInstaller.
- [packaging/native_acceptance.py](../packaging/native_acceptance.py) explicitly accepts the Ni source through Material Apply, replaces automatic structural groups with the same fixture's explicit magnetic groups through the editor, and records uncaught Qt callbacks in its existing error list while restoring the previous hook.
- [src/emcd_sim/gui/project_collection.py](../src/emcd_sim/gui/project_collection.py) recognizes manifest-owned run_inputs, preserves unrelated nested attachments, removes deleted owned inputs and retains link/transaction safeguards. A stored-array behavioral check covers replacement, notes, deletion and exact results.
- [src/emcd_sim/gui/result_presentation.py](../src/emcd_sim/gui/result_presentation.py) blocks intermediate normalization/include-total signals while replacing result/group controls. A behavioral test reproduced the native stale-group KeyError before correction; both comparison states, method/group switching and saved display restoration then passed.
- Only existing reviewed current-source identities, loader checksum and production-source pointer were updated. Original historical archives, kernel/data pins, negative controls and release inventories remain intact.

Application source edits are the persistence and result-control fixes. Acceptance tooling, its targeted tests and existing registration metadata also changed. This report is documentation. Scientific engine source did not change.

The initial augmented GUI-I/O reproduction reached its existing 25-second GUI wait limit. It was replaced by a direct persistence behavior test, without increasing that wait. The final focused persistence pair passed in 65.90 seconds, alongside the other 11 project checks and one existing skip from the preceding affected-file run: combined focused evidence, not a falsely claimed clean whole-file invocation. Four callback-related checks passed in 13.39 seconds. Both existing guards rejected changed-file mutations, with current/historical positives; final registration and source entry points passed.

| Local commit | Purpose |
| --- | --- |
| e3dc6aaea1fb78781e520ee8e297d6a4a7cd1572 | Explicit historical Ni geometry for matched-source QA |
| 5819efcfa2230d12163892c8686741115e0ed675 | Reviewed initial QA source pointer |
| acc8576c258ccc30b74bf3a4090ae8858087d3b8 | Recorded-input persistence fix, targeted test and native QA/public-import corrections |
| d9b98c9af46a2f3ea8f126183e81fb4653c1cc6e | Intermediate persistence-stabilized source pointer |
| 41e376c3b891df2ef225c43a5db0e1f6bc1794b8 | Result-control callback fix, behavioral cases and QA exception capture |
| 473ac666592e11fc962ecb64d27354ccb18d4ba0 | Final source pointer and exact build/source-archive identity |

The report is committed as a documentation-only successor; its exact commit is identified by Git history for docs/PHASE3F2_WINDOWS_NATIVE_ACCEPTANCE.md and the final handoff. Source was clean through final native verification and the post-run inventory check. The final documentation commit contains only this report, with a clean handoff working tree.

No push, merge, tag, publication, version change or Research Beta installation/archive overwrite occurred. Development builds and acceptance outputs stay under the dedicated ignored build/phase3f2 paths. Separate clean-full-suite/clean-machine acceptance and optional narrow-panel layout cleanup remain future work.
