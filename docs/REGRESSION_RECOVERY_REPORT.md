# Phase 2 regression recovery and architecture stabilization

## A. Assessment and exact source identities

**NO-GO for scientific acceptance.** Recovery reduced the recorded 593 failure/error
reports to six numerical failures. The final complete run has **1,692 passed,
six failed, zero errors and 62 independently justified skips**. Source registration,
ordinary GUI/application checks and unintended memory-admission failures have
recovered. The newly built Windows development EXE passed the native workflows
listed below. Six unchanged scientific assertions still fail; this is not a
clean regression result.

No physical equation, scattering coefficient, scientific kernel, numerical
reference array, scientific test tolerance or calculation budget was changed.
The main corrections concern test-owned Qt teardown, current API/Material
transactions, verified saved-source restoration and opt-in QA consumers.

| Identity | Exact value |
| --- | --- |
| Working directory and Git worktree root | `C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute` |
| Branch | `refactor/physics-readability` |
| Phase 2 starting source | `6817d644d3e9dcc3f06d02d1ad733e36b331d0f2` |
| Actual pre-refactor source | `cdb8836388c5ccc5ae7a614b47894c0ab158a824` |
| First complete recovery candidate | `313e2fd1ed16f0aea1b5825711f1e8dff36a45f5` |
| Final complete-regression source | `91aff158d7c6ec17a45196200830d3e1f7c178a3` |
| Subsequent resource-QA-only source correction | `4b5dc2bef22d9a5a283546cfb16420c055b581c9` |
| Final frozen application/test/build source | `6d98694b2367fdb9586f33287f9a09c159c7ef27` |
| Completion documentation | This report is a documentation-only successor to the build source; its commit is reported separately at completion. |

Git identifies `f7affbf3328fb3cee3e6efa4f722d65f9d1a5bfa` as the first readability
refactor commit; its direct parent is the exact `cdb8836...` baseline above.
The original [complexity audit](REFACTOR_COMPLEXITY_AUDIT.md), comparing that
baseline with `6817d64`, is preserved unchanged. This report adds a separate
post-recovery measurement.

The complete run is **not relabeled as the later build commit**. After it ended,
only `gui/parallel_acceptance.py`, its reviewed registration metadata/pin, and
this report changed before the build freeze. That opt-in QA correction was
verified by a real four-worker source run, 48 affected passing checks, and the
actual frozen EXE. Normal production calculation code and scientific assertions
are identical to the full-run candidate. A third complete run was not started
for that QA-only change.

## B. Regression recovery

### Complete inventories

| Outcome | Recorded Phase 1 | First Phase 2 complete run | Final complete run | Final change from Phase 1 |
| --- | ---: | ---: | ---: | ---: |
| Collected | 1,747 | 1,760 | 1,760 | +13 (+0.74%) |
| Passed | 1,091 | 1,634 | 1,692 | +601 (+55.09%) |
| Failed | 388 | 64 | 6 | -382 (-98.45%) |
| Errors | 205 | 0 | 0 | -205 (-100.00%) |
| Skipped | 63 | 62 | 62 | -1 (-1.59%) |
| Bad | 593 | 64 | 6 | -587 (-98.99%) |
| Seconds | 19,907.56 | 4,771.27 | 4,311.19 | -15,596.37 (-78.34%) |

“Bad” combines failures and errors. “Seconds” uses pytest's reported duration,
not the launcher's additional startup/exit time. The final launcher duration was
4,318.11 s; pytest reported 4,311.19 s, or 71m 51s. Duration changes are observations
across different inventories/recovery states, not a scientific-kernel speedup
claim. The final run emitted 1,178 warnings, principally Qt deprecations and
small/offscreen Matplotlib layout warnings; warnings are not counted as passes.

The original raw Phase 1 log/XML do **not** embed an exact Git ID or complete
environment. The name-map document records `db63dcf` at that run's start and
later test-only fixes. Therefore its 1,747-case result is historical evidence,
not a reconstructed clean run of `6817d64`. Fresh Phase 2 collection found
1,747 cases with zero collection errors.

Evidence under `build/regression-recovery/`:

- `phase1-complete-suite.log/xml` and `phase1-inventory.json`: inspected original evidence.
- `phase2-complete-suite-candidate-313e2fd.*`: clean first complete recovery run.
- `phase2-final-complete-suite-91aff15.log/xml`, `-run.json`, and `-lifecycle.jsonl`: final complete run, initial Git status empty, no selection or early stopping.
- `phase2-final-inventory.json`: every final failing node, full traceback and skipped node/reason.
- `phase1-final-classification.json`: primary classification and reason for each of the original 593 reports.

Each new `*-run.json` records the **exact emitted argv**, source HEAD, initial
dirty paths, working directory, Python version, relevant environment, owned
subprocess PID, timeout, exit code and timing. Adjacent raw logs/XML are retained,
including unsuccessful intermediate attempts. The selection for the final
complete run was `pytest -q --tb=short`, with a unique `--basetemp`,
`-p no:cacheprovider`, JUnit output, and an actual-payload peak-memory probe
around `pytest.main`. The exact probe and paths are in that run record.
Overlapping focused results are never added to the full-suite totals.

### Primary failure categories

These are **failure/error reports**, not counts of independent user-visible bugs.
A registration/setup or memory rejection often prevented later assertions from
running. The final classification supersedes the initial symptom-only grouping
of 202 registration, 71 draft, 244 memory and 76 unclassified reports.

| Category | Before | After | Change | Demonstrated cause | Resolution |
| --- | ---: | ---: | ---: | --- | --- |
| A Registration/import/API | 211 | 0 | -211 (-100.00%) | One stale registration cascaded into 156 reports; removed dispatcher/scheduler spies also failed setup. | Current owners and authenticated historical source; no retired production facades restored. |
| B GUI/application expectations | 127 | 0 | -127 (-100.00%) | Missing explicit Material acceptance; old controls, labels, plotting axes, resource assumptions and inactive-draft behavior. | Behavioral consumer migrations preserve numerical assertions and exercise actual accepted configuration. |
| C Application restoration | 5 | 0 | -5 (-100.00%) | Verified relocated sources lost provider/accepted state or were rebound to regenerated cache inputs. | Restore verified portable overrides and stable model/source/frame state. Additional latent restoration defects were found after earlier blockers cleared. |
| D Memory admission | 244 | 0 | -244 (-100.00%) | Closed test-owned Qt objects survived close(), accumulating process memory before later admission. | Destroy owned native top-level widgets at teardown; retain shared fixtures and active-worker safeguard. Budgets/estimators unchanged. |
| E Scientific numerical | 1 | 6 | +5 (+500.00%) | Strict older-reference and cancellation-sensitive derived-signal discrepancies; several were previously hidden by earlier failures. | All six remain failing; no reference regeneration or tolerance change. See C. |
| F Other infrastructure | 5 | 0 | -5 (-100.00%) | Repeated unittest class setup attempted to create the same temporary output directory. | Correct idempotent test-owned setup; no production filesystem relaxation. |

Representative original symptoms were `Unreviewed current source:
scripts/mdff_corrective_walkthrough.py`, a setup spy on removed
`forward_pipeline.calculate_multisite`, `Apply or Cancel the Global MDFF draft`,
`atomic_provider_info is None` after relocation, over-budget process RSS with
zero active calculations, and `FileExistsError [WinError 183]` in repeated
test class setup. The raw inventory retains the complete tracebacks.

Actual application fixes preserve the selected model description, avoid
remembering an inactive manual draft during restoration, bind accepted
configuration to the loader's verified portable source, reuse an unchanged
verified manual source instead of generating a phantom new draft, and preserve
saved inactive/full-frame editor state. Relocated-source calculations again
reproduce their saved arrays exactly. Original result provenance is retained;
the loading layer supplies verified path overrides.

Current consumers now perform MDFF **Done** and Material **Apply**, set
material-owned magnetization explicitly, use semantic edge-selection data,
inspect the actual primary/secondary plotting axes, and spy on active
orchestration/cohort boundaries. No old facade was restored for a stale test.
The 512 MiB rejection test now controls process RSS to exercise the same real
admission guard; it retains its budget, scientific dimensions and rejection
assertion. The supported five-worker configuration is no longer used as an
“invalid worker” example; zero is rejected before propagation instead.

One planning-only multisite test requests the complete angular field so its
unchanged 512 MiB budget actually limits worker count. Its previous
aperture-only task set already limited useful workers before memory did; the
old memory-message assertion therefore missed its intended condition. No
scientific arrays are propagated in that planning test. The responsive-layout
check similarly measures the scroll space released by maximizing a plot at its
existing minimum height, then checks restored controls and unchanged settings,
rather than requiring growth beyond a binding widget minimum.

### Inventory reconciliation and skips

The +13 collected cases are eight current-owner mutation cases, one additive
declaration mutation, one native-widget teardown regression, and three extra
independent-kernel negative controls with ordinary registration already approved.
Renamed functions/path parameters are paired, not counted as deleted coverage.
The final two name changes from the first Phase 2 complete run are:

| Before | After | Reason |
| --- | --- | --- |
| `test_restored_proper_frame_direction_is_derived` | `test_restored_frame_preserves_material_direction_and_full_basis` | Preserve accepted Material M and saved full/inactive frame state. |
| `test_cancellation_between_site_events` | `test_cancellation_between_grouped_energy_events` | Observe the real shared grouped-energy boundary. |

Earlier migrations renamed the rotated-frame test to
`test_rotated_frame_requires_matching_material_magnetization`, the invalid
geometry test to `test_supported_orientation_and_invalid_geometry_no_fallback`,
and the standalone worker-policy test to
`test_standalone_requests_remain_serial_without_an_admitted_plan`.
Those names describe current responsibilities; their effective scientific
assertions remain. Approval of the already declared ZOLZ source path did not
add another collected case. The final inventory remains **1,760**, not 1,761.

| Final skip reason group | Count |
| --- | ---: |
| Optional saved projects/benchmark outputs unavailable | 37 |
| Explicit native Windows checks excluded from the offscreen pytest selection | 8 |
| Reviewed external legacy atomic table unavailable | 13 |
| Undistributed original WIEN2k companions | 2 |
| Pinned offline HDF5 inputs unavailable | 1 |
| Optional external 160-array evidence unavailable | 1 |
| Total | 62 |

The 62 skipped identities/reasons match the first Phase 2 complete run exactly.
Compared with Phase 1, one prior optional GUI artifact became available:
`test_generalized_117_saved_gui_export_retains_raw_relative_data`. No failing
test was newly skipped or xfailed. Native acceptance below complements the
offscreen checks; it is not inserted into the pytest pass count.

### Environment and affected checks

Windows Python 3.11.17; NumPy 2.4.6; SciPy 1.17.1; PySide6 6.12.0;
Matplotlib 3.11.2; ASE 3.29.0; spglib 2.7.0; pytest 9.1.1; PyInstaller 6.22.3.
The selected interpreter is
`C:/Users/peng863/EMCD-Sim/build/windows-rc/venv/Scripts/python.exe`.
`psutil` and `threadpoolctl` are absent; existing native/ctypes controls are used.

Source runs use explicit worktree `src;tests` in `PYTHONPATH`,
`PYTHONDONTWRITEBYTECODE=1`, `PYTHONHASHSEED=0`,
`OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, and offscreen Qt except
native runs. Operations run serially. Timeouts target only owned subprocess
trees. Initial sandbox/pytest temporary-directory ACL failures were
infrastructure issues; subsequent GUI checks used the normal user token and
unique workspace basetemps without changing ACLs or budgets.

Decisive focused records include `phase2-current-registration-normalized`,
`phase2-historical-current-workflow-bridges`,
`phase2-final-registration-and-canonical-api` (10 passed),
`phase2-source-cancellation-current-kernel-hooks` (nine real cases),
and `phase2-resource-qa-affected-checks` (**48 passed, one unchanged optional
project skip**, 17.62 s). All exact selections/results, including intermediate
failures, are retained in their run records and earlier report commits.

## C. Scientific verification and remaining blockers

The unchanged comparison driver executed the actual `cdb8836...` source in
memory with the established import/name translation, original case inputs and
unchanged comparisons. On clean `91aff15`, it passed **22 cases and 2,294 arrays
exactly**, including the checked physical metadata and selected-edge metrics,
in 14.406 s. This covers the existing Ni presets, explicit declared materials,
grouped cases, geometry, Single/Double and Bloch/FFT combinations represented
by that driver. Evidence:
`phase2-final-frozen-source-equivalence.log` and `-run.json`.
No expected arrays were regenerated from candidate output.

This is equivalence to frozen pre-refactor **source**, not experimental
calibration or proof that two implementations share no assumptions.
Independent event/matrix, phase/coherence, no-outgoing-potential, atomic-model,
serial/parallel, geometry and detector assertions also pass in the final suite.
The external 160-array/HDF5/table/companion artifacts listed under skips were
not available and are not replaced with current production output.

| Failing test | Reference/assertion | Maximum absolute discrepancy | Maximum relative discrepancy |
| --- | --- | ---: | ---: |
| `test_double_cancellation::test_bw_unchanged_and_depth_cancel[numerical]` | Exact arrays against `7bebdce` | 1.38780808e-17 | 1.84825173e-16 |
| `test_double_cancellation::test_full_spectrum_unchanged[bloch]` | Exact arrays with archived `7bebdce` kernels | 6.9388939e-18 | 8.52275132e-16 |
| `test_double_cancellation::test_full_spectrum_unchanged[both]` | Same strict comparison with both methods | 6.9388939e-18 | 8.52275132e-16 |
| `test_multisite_scientific_validation::test_bcc_cr_independent_events_and_symmetry[unequal-mdff-double-bloch]` | Weighted derived-signal parity; unchanged rtol 3e-13, atol 1e-18 | 1.08420217e-18 | 8.68578842e-11 |
| `test_single_element_ni_compatibility::test_original_ni_all_numeric_arrays_exact[double-xmcd]` | Immutable `2f9c130099dce5df4e4609b521c42f53c5385518` | 1.3010426069826053e-18 | 5.0519996e-16 |
| `test_single_element_ni_compatibility::test_original_ni_all_numeric_arrays_exact[double-atomic]` | Same immutable earlier source | 2.6469779601696886e-23 | 1.16368886e-16 |

The two Ni differences are reproduced by the source comparison at the starting
source. The identical Cr assertion, inputs and numbers also fail when executing
the actual pre-refactor source:
`phase2-cr-current-and-pre-refactor-assertion.*`.
The three `7bebdce` comparisons substitute older kernels into the same
orchestration or compare the kernel directly. Current kernels are identical to
the pre-refactor kernel source. Thus their differences are between that
pre-refactor implementation and the earlier reference, rather than a Phase 2
kernel edit; this attribution follows source identity and the test structure.
Their numerical-contract resolution remains open.

The old-reference adapter removes only software arguments unknown to the
archived API, including `prepared_outgoing`; the reference prepares its own
outgoing basis and the adapter verifies its original site positions. No
equation, reference value or equality assertion is altered.

Existing original convention/data pins remain intact. The old
`legacy_kernel_source` text-reconstruction helper failed before authenticating
kernels because its deletion markers no longer existed. Its two consumers,
`tests/physics_source_guard.py` and `tests/test_unit_labels.py`, now use
authenticated historical bytes and complete current kernel identities tied to
the user-specified `cdb8836...` source. The additive
`physics_readability_current_v1.json` preserves exact prior bytes from
`effb755b7ed907cb2b8d386c1b7b67d9c8c53ffc`; original v4 archives/declarations
are untouched. Existing tests require no-Git/no-process operation, so Git alone
cannot supply that offline boundary. This is the concrete reason for preserving
it with recorded source identities rather than weakening the old safeguards.
Ordinary current-UI approval cannot approve altered scientific kernels; the
independent negative controls, including already-approved ordinary registration,
pass.

**Minimal remaining scientific work:** determine the authoritative numerical
contract with independent scientific/numerical review, retaining these failures
as evidence. Matching older strict values may change the current frozen
baseline; simply widening tolerances or updating expected values is forbidden
in this task. Any justified correction needs its reproducible defect,
independent invariant/reference, affected numerical revalidation and a new
complete frozen-candidate run. No new physics is implemented here.

Generality remains bounded by the existing models: MDFF/source declarations and
magnetic-site assignments must be explicit; synthetic Fe/O/Cr examples do not
establish material calibration. Fixed-source-axis requests that the provider
cannot represent are rejected. Broader electronic-structure/source calibration
or genuinely different physical models require scientific development/data,
not material-specific copies of the calculation engine.

## D. Memory and lifecycle diagnostics

The original 244 admission reports included tiny predicted working arrays with
process RSS already beyond the unchanged 2,048 MiB budget and zero active
calculations. A representative 0.5 nm FFT interval passed fresh. Grouped and
original-order runs exposed native Qt retention: `QWidget.close()` hid objects
without destroying them, while teardown previously destroyed only MainWindows.

The correction calls deferred destruction for all test-owned native top-level
widgets, preserves pre-existing/shared fixtures, checks Shiboken validity,
processes deferred deletion and retains the active-MainWindow-worker safeguard.
A new regression first failed under old teardown, then passed while proving
that an owned closed widget dies and a shared widget survives. Worker
admission, array estimates, numerical sampling and budgets were unchanged.

| Original-order process | Intended cases | Unintended memory-admission failures | Actual payload peak RSS MiB | Peak commit MiB |
| --- | ---: | ---: | ---: | ---: |
| Historical Phase 1 | 1,747 | 244 | Not independently measured; over-budget RSS appears in failure traces | Not recorded |
| First complete Phase 2 | 1,760 | 0 | 944.348 | 1,000.824 |
| Final complete Phase 2 | 1,760 | 0 | 972.133 | 1,030.082 |

The two complete recovery runs are separate original-order process observations,
not added pass counts. The final 0.5 nm case also passed in accumulated order.
Later GUI-heavy tests still retain legitimate fixtures/caches, but the budget
cascade did not recur. No production estimator or worker-retention defect was
demonstrated; expected rejection tests still exercise real guards.

Representative fresh-process measurement used the existing explicit Ni case:
0.3 nm; cutoffs 0.9/1.8 inverse angstrom; grid/depth 9; subpixels 8; FFT 16;
slice step 0.01 nm; one Manual worker; 2,048 MiB budget.

| Mode | Predicted working MiB | Predicted process peak MiB | RSS before → after MiB | Observed lifetime peak RSS MiB |
| --- | ---: | ---: | ---: | ---: |
| Bloch Single | 0.067 | 203.022 | 75.113 → 77.871 | 94.520 |
| Bloch Double | 8.119 | 216.023 | 77.875 → 78.035 | 94.520 |
| FFT Single | 0.159 | 206.238 | 78.070 → 78.117 | 94.520 |
| FFT Double | 9.806 | 218.374 | 78.117 → 78.156 | 94.520 |

Evidence: `phase2-representative-memory-modes.*` and
`measure_representative_memory.py`. PSAPI was queried in the **actual payload**.
The 94.520 MiB lifetime peak is cumulative across four short cases and includes
imports, not a separate per-kernel incremental peak. Peak commit was
109.602 MiB. Every case left zero reservations, no detector executor threads
and an unlocked Windows Bloch executor. These measurements support conservative
admission for the measured cases, not an arbitrary-size estimator guarantee.

The final pytest payload was PID 8620. Its venv launcher PID 1700 peaked at only
4.375 MiB RSS and is explicitly not substituted for application memory.
The frozen 16-case provider runner peaked at 1,284.781 MiB while retaining its
QA windows for final checks; the four-worker frozen resource case peaked at
278.156 MiB. Both completed below their unchanged request.

The source cancellation QA initially watched an obsolete depth helper while
production used the grouped kernel, then stalled on its Retain Calculation
dialog after completion. Its owned window/PID and creation identity were
confirmed before terminating only that process tree. Current probes observe
real grouped BW/MS checkpoints and clear temporary browser selection. The
source nine-case run passed with worst idle 0.255919 s; the frozen nine-case
run passed at 0.313614 s, below the unchanged 2 s assertion. Queued completion,
restart, prior arrays/projects, reservation release and responsive timers are
checked. Production cancellation code is unchanged.

## E. Frozen Windows development build

The previous development EXE at `3f9112a` differs from `6817d64` only by 51
documentation lines in the name map. No application changes were omitted
between those two IDs. Phase 2 nevertheless rebuilt the actual corrected
source rather than reusing that binary.

The build uses a clean `git archive` source copy at
`build/regression-recovery/native-candidate-6d98694/source-snapshot`, not a new
registered Git worktree or a moved checkout. A scoped Git work-tree/index
context ties that build copy to the same frozen commit without touching the
real checkout's index. Preflight caught the otherwise empty archive produced
from a nested ignored directory and verified the complete archive before
building. Scientific byte-exact `-text` inputs remain unchanged.

`packaging/build_windows.ps1` ran with the existing Python, a new build root,
the development label, and the previously reviewed Qt corresponding-source
archives. Mandatory metadata, environment, package assets, Qt binary/license,
source-kit and inventory checks were retained. PyInstaller and archive creation
completed successfully in **297.109 s**. Public version remains **0.9.0b2**.

Executable:

`C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\build\regression-recovery\native-candidate-6d98694\native-build\dist\EMCD-Sim\EMCD-Sim.exe`

Artifacts under that `native-build` directory:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `EMCD-Sim-Phase2-6d98694-Windows-dev.zip` | 106,042,320 | `7030b62a0ce208df907ca93da558c0158249a7a2a896f235fefa7c3eb7a693c0` |
| `EMCD-Sim-Phase2-6d98694-Qt-sources-dev.zip` | 102,414,788 | `faf2842bc4c10272d60cafc793d4dd1bd5d56c739e809dd529027d8a7a8dca09` |
| `dist/EMCD-Sim/EMCD-Sim.exe` | See existing inventory | `cefb4b7880930dba38e966f9f437d6b2a4fc90af9ceb0814feccddcebcccaaaa` |

Identity verification found **zero mismatches** across 646 inventoried package
files and all 109 runtime source hashes against the corresponding application
source ZIP. The source ZIP has the correct Git commit comment, 839 entries
and 784 files. Reviewed byte-exact Ni input and BCC CIF were also compared with
their Git blobs. Package checks report 34 Qt binary components, 99 translations
and all 41 required assets. Evidence: `phase2-native-package-verification.json`,
the existing `build_manifest.json`/`SHA256SUMS.txt`, and
`phase2-frozen-development-build-6d98694.*`.

All native commands executed the EXE directly from its distribution, with empty
`PYTHONPATH`, native Windows Qt requested, and isolated user/workspace data.
The desktop report confirms the BLAS DLL is loaded from the distribution's
`_internal/numpy.libs`. Reports record `frozen=true`, the expected clean
commit, completed assertions and clean shutdown where applicable.

| Frozen command/workflow | Result | Driver seconds | Evidence prefix/folder under build/regression-recovery |
| --- | --- | ---: | --- |
| Normal `--smoke-screenshot` startup | Real default elastic preview; 185,892-byte screenshot | 6.734 | `phase2-frozen-normal-startup` / `frozen-normal-startup` |
| `--desktop-acceptance` | Single/Double BW/MS, Bragg/preview, Save/Open fingerprints, plots and exports; two channeling cases | 48.359 | `phase2-frozen-desktop` / `frozen-desktop` |
| `--release-acceptance` | 14 Ni/Fe/O provider cases plus two manual spectral cases; real calculations, project restore/recalculation, source tamper rejection and exports | 197.375 | `phase2-frozen-ni-fe-projects` / `frozen-ni-fe-projects` |
| `--release-acceptance --grouping` | Fe3O4 structural grouping/Save/Open; actual Cr independent-group BW Single calculation, reversal restore, unsupported-axis rejection | 26.219 | `phase2-frozen-multisite-grouping` / `frozen-multisite-grouping` |
| `--parallel-acceptance --parallel-workers 4` | Four workers, original 2,048 MiB request, saved arrays and visible worker/memory controls restored after deliberate unexecuted UI edits | 36.546 | `phase2-frozen-resource-persistence` / `frozen-resource-persistence` |
| `--cancellation-acceptance` with bundled Ni source | Nine cases, queued-result suppression, immediate restart and project integrity | 20.094 | `phase2-frozen-cancellation` / `frozen-cancellation` |

Fe3O4 validation here is structural: actual 8/16/32 ASE site counts,
8a/16d/32e identities, 4/6 coordination, initially unset M/MDFF, and structural
Save/Open. The **genuine calculated multisite native case is Cr**; this report
does not mislabel the Fe3O4 structural check as a calculation. Fe/O/Cr sources
are synthetic software validation cases, not material-accuracy claims.

The resource profile does not record a `qt_platform` JSON field; its run
records the explicit Windows platform request and its backend records Win32.
The other four acceptance reports record `qt_platform=windows` directly.
All report schemas were checked on their actual fields, rather than treating
exit code alone as acceptance. Aggregate evidence is
`phase2-native-validation-summary.json`. The native desktop screenshot was
visually inspected; the deliberate 1092×600 layout requires existing scroll/
maximize controls and emits small-layout warnings.

**Clean-machine installation is NOT TESTED.** The existing manifest retains that
limitation. Nothing was published, installed over the Research Beta, tagged or
promoted to a release.

## F. Complexity, centralization and Phase 3 handoff

The same Git/AST/tokenization methodology as the original audit was rerun.
P counts physical lines, N counts nonblank/noncomment token-bearing lines
including docstrings, and S also excludes formal module/class/function
docstrings. Graph edges are unique literal internal imports, including deferred
imports; dynamic import strings and implicit package initialization are excluded.
Generated outputs and dependency environments are excluded. Final evidence:
`phase2-build-complexity.json`; `phase2-final-complexity.json` separately
records the complete-run candidate before the QA-only correction.

| Production metric | Pre-refactor cdb8836 | Phase 1 6817d64 | Final build 6d98694 | Phase 2 change |
| --- | ---: | ---: | ---: | ---: |
| Production Python files | 104 | 109 | 109 | +0 (+0.00%) |
| Physical LOC (P) | 19,298 | 19,436 | 19,515 | +79 (+0.41%) |
| Nonblank/noncomment LOC (N) | 17,260 | 17,392 | 17,466 | +74 (+0.43%) |
| Source LOC excluding formal docstrings (S) | 16,423 | 16,456 | 16,530 | +74 (+0.45%) |
| Internal import edges | 479 | 495 | 497 | +2 (+0.40%) |
| Cyclic dependency groups | 4 | 4 | 4 | 0 (0.00%) |
| Modules in cycles | 37 | 37 | 37 | 0 (0.00%) |
| Production files >500 physical LOC | 10 | 9 | 9 | 0 (0.00%) |
| Production files >1,000 physical LOC | 0 | 0 | 0 | 0 (0.00%) |

No production module or architecture layer was added. The two extra import
edges are `app → forward_settings` and `app → saved_atomic_ui`, used by
explicit opt-in smoke presets. A private Material-transaction helper in the
existing native QA script avoids repeated QA setup; it is not a production
calculation facade. No new cycle was introduced.

| Scope | Before files | After files | File change | Physical LOC | N LOC | S LOC |
| --- | ---: | ---: | ---: | --- | --- | --- |
| All tracked Python | 318 | 326 | +8 (+2.52%) | 47,150 → 47,756 | 41,588 → 42,144 | 40,314 → 40,760 |
| src / inclusive emcd_sim | 104 | 109 | +5 (+4.81%) | 19,298 → 19,515 | 17,260 → 17,466 | 16,423 → 16,530 |
| gui (nested in src) | 60 | 64 | +4 (+6.67%) | 14,210 → 14,376 | 12,856 → 13,018 | 12,555 → 12,637 |
| emcd_sim excluding gui | 44 | 45 | +1 (+2.27%) | 5,088 → 5,139 | 4,404 → 4,448 | 3,868 → 3,893 |
| Tests | 158 | 161 | +3 (+1.90%) | 20,836 → 21,184 | 18,020 → 18,331 | 17,732 → 18,033 |
| Scripts | 49 | 49 | +0 (+0.00%) | 6,100 → 6,121 | 5,461 → 5,482 | 5,337 → 5,358 |
| Packaging | 5 | 5 | +0 (+0.00%) | 856 → 876 | 793 → 811 | 774 → 791 |

The gui row is nested in src; it is **not added again** to overall totals.
The non-gui application row is disjoint. Relative to Phase 1, all Python file
counts remain unchanged. Relative to the actual pre-refactor source, production
files rise 104→109 and S LOC 16,423→16,530; this is not code-volume reduction.

Largest current production files:

| Module | P | S |
| --- | ---: | ---: |
| gui/app.py | 674 | 618 |
| gui/results.py | 643 | 604 |
| gui/group_mdff.py | 641 | 584 |
| gui/atomic_editor.py | 627 | 574 |
| gui/responsive.py | 614 | 531 |
| gui/project_io.py | 603 | 505 |
| gui/calculation_controls.py | 570 | 529 |
| gui/site_group_editor.py | 559 | 486 |
| gui/project_session.py | 504 | 465 |
| gui/structure_viewer.py | 486 | 427 |

The public forward boundary is centralized at
`emcd_sim.gui.forward_pipeline.calculate(structure, settings, cfg, sites=...)`.
Maintained worker/caller migrations reach it with explicit structure,
material/model, geometry and site inputs. Ni presets remain explicit inputs.
Uniform and grouped execution retain separate substantive scheduling,
normalization and accumulation code; common response kernels already existed
before Phase 1. Single-group BW/MS response adapters delegate to the shared
group-response implementations. Different physical models, Bloch/FFT methods,
and useful independent references remain distinct.

Thus **one public entry point does not mean one flattened execution schedule**,
nor does source movement prove algorithm deduplication. Phase 1's shared detector
reversal algebra is genuine deduplication; moving orchestration/spectrum helpers
and renaming facades primarily clarifies ownership. Phase 2 recovers correctness
and validation, not broad structural simplification.

Scientific services still live under `gui`: `forward_pipeline`, `channeling`,
`multisite_integration`, `propagation`, `geometry`,
`provider_preparation` and `forward_results`. Core providers/kernels import
GUI-owned configuration, material helpers or memory admission. Most of those
services do not construct Qt widgets, but the dependency directions and
26-module service cycle are real. General settings still inherit the Ni-shaped
settings record; current provider validation prevents that from proving a
silent Ni substitution. The canonical path supplies explicit provider sites;
lower-level optional Ni site defaults remain a separately reviewable contract,
not a demonstrated fallback on that canonical path.

Prioritized **future** cleanup candidates; none was performed in this phase:

| Priority / files | Specific evidence/problem | Suggested focused change / benefit | Risk and required verification |
| --- | --- | --- | --- |
| 1. `forward_settings`, `material_inputs`, `project_configuration`, `project_session` | Ni-shaped general records; 26-module cycle; actual accepted/draft/source/frame restoration defects | Establish neutral input/state ownership using existing records; remove duplicate configuration translation after consumer review. Fewer source-rebinding and state-order bugs. | Saved schema, Material M and provenance risks. All historical/relocated roundtrips, Global/Local A-B-A, source rejection and 22-case equality. |
| 2. `gui.forward_pipeline/channeling/multisite_integration/propagation/provider_preparation`, `gui.memory_budget` | Scientific orchestration and resource services beneath gui; reverse core→gui imports | Move actual service/data ownership below presentation and break imports, rather than just moving files or adding wrappers. Clear headless engine boundary. | Scheduling, summation order, admission and cancellation risks. Existing scientific references, four modes, serial/parallel, memory and cancellation checks. |
| 3. `app` 674 P, `results` 643 P, `group_mdff` 641 P, `atomic_editor` 627 P, `project_io` 603 P | Oversized widgets plus repeated accepted/draft/provider presentation transitions | Consolidate shared editor/state transactions and separate rendering/I/O responsibilities where evidence supports it. Smaller review surfaces. | GUI/project/source-frame compatibility. Behavioral GUI checks and native Ni/Fe/O/Cr projects, exact save/recalculation fingerprints. |
| 4. `app` and its opt-in acceptance modules | Existing five-module app/QA cycle; two new deferred preset imports | Place QA dispatch in the existing launcher/tool boundary where feasible; retain only identified command consumers. Reduce normal-window dependency on QA. | Frozen discovery/entry points. Normal startup/help and every intentionally retained native command, source inventory and package checks. |
| 5. Existing source-scope helpers and archived reference resources | One stale scope cascaded into 156 reports; nested current/prior declarations and obsolete source reconstruction | Clarify current versus historical evidence ownership and consolidate duplicate registration translation without losing independent scientific authentication. Easier review/maintenance. | No-Git and mutation protection can be weakened accidentally. All original archive, negative, no-process, already-approved-current and kernel/data identity controls must remain. |

The unchanged three-module elastic-data cycle and three-module
atomic/imported/manual-provider cycle also merit focused ownership review.
They do not justify merging genuinely different physics models. Kernel
consolidation requires demonstrated numerical equivalence; unresolved strict
scientific comparisons should be settled first.

## G. Legacy decisions, Git deliverables and final state

The full old-to-new physical/software responsibility map remains in
[REFACTOR_NAME_MAP.md](REFACTOR_NAME_MAP.md) and
[PHYSICS_CODE_MAP.md](PHYSICS_CODE_MAP.md). Clear interfaces and framework callback
names were not renamed for stylistic consistency.

| Removed interface | Identified consumers / current replacement | Decision |
| --- | --- | --- |
| `gui.stage_b.StageB/setup_stage_b` and its worker re-export | MainWindow and maintained GUI/tests use `CalculationControls/setup_calculation_controls` and `calculation_worker.EMCDWorker` | Stage facade retired; no supported old production consumer identified. |
| `emcd_forward.calculate`, `generalized_forward.calculate`, public `calculate_multisite` | GUI worker, maintained drivers and tests use canonical `forward_pipeline.calculate(..., sites=...)` | No wrapper restored for obsolete imports/spies. |
| `emcd_forward.ForwardSettings` and mixed export re-exports | Explicit Ni cases use `NiForwardSettings`; export callers use `forward_results` | Names/owners expose actual preset/result responsibility; no historical class alias. |
| `channeling.contract`, `run_multisite_with_coherence` and old grouped helper names | Current scheduler/cohort consumers use `calculate_detector_signals`, `integrate_ionization_groups` and `multisite_integration` owners | Tests target actual execution, not a retired hook. |
| `Registry/IOWorker/setup_stage_d` | Workspace callers use `ResultRegistry/ProjectIOWorker/setup_project_workspace` | Clear ownership; JSON/index schemas retained. |
| `study_geometry.StudyGeometry/rotated_tensor` | Ni study scripts use `study_presets.NickelStudyGeometry/xmcd_tensor_in_frame` | Explicit Ni/XMCD responsibilities; no second material engine. |
| Optional Ni geometry fallback in `projected_geometry_for` | Canonical callers provide the actual oriented crystal to `projected_geometry_from_oriented_crystal` | Unsupported/missing geometry does not substitute Ni. |
| Test `legacy_kernel_source` reconstruction | `physics_source_guard.py` and `test_unit_labels.py` use authenticated source evidence | Obsolete helper removed; independent scientific reference bytes and checks retained. |

| Retained interface/evidence | Concrete consumer and purpose |
| --- | --- |
| `NiForwardSettings`, historical Ni input/source helpers and explicit Ni study presets | Current Ni GUI examples, maintained Ni studies, supported saved Ni data and numerical validation; inputs reach shared production calculation, not a new Ni kernel. |
| Single-group response adapters and clear scientific model/provider classes | Current uniform scheduler and independent scientific tests; response adapters delegate common grouped kernels. Distinct physical/numerical/reference implementations remain useful. |
| Saved-file keys, loader/schema migration and verified source-path overrides | Supported historical/current projects, including relocated managed inputs. Data compatibility is handled here, not by retired Python import names. External arbitrary sources are not silently made portable. |
| Qt callbacks/signals, `run`, `closeEvent`, `requestInterruption`, `isInterruptionRequested`; console entry points | Framework and intentionally supported application consumers. Names are required or already clear. |
| Existing resource view bindings such as `shared_resources_group` | Current CalculationControls/NumericalSettingsUI presentation consumers; one existing panel, no second scheduler or calculation route. No new compatibility layer was added. |
| Immutable source/data pins, prior source archives, independent references and existing release inventories | Scientific regression, offline/no-process guards and formal package/source traceability. No historical Python production facade is exposed by private archived workflow fixtures. |

Relative to the starting `6817d64`, the build candidate changes **62 tracked
files**: eight gui source files, one existing packaging QA script, 51
tests/registration files, and two documentation files. No non-GUI scientific
engine file changed. The GUI source files are `app.py`,
`calculation_controls.py`, `cancellation_acceptance.py`,
`desktop_acceptance.py`, `imported_tensor_ui.py`, `manual_l23_editor.py`,
`parallel_acceptance.py`, and `results_browser.py`.
The original complexity audit's content remains unchanged from its first
recording commit; the other document is this recovery report.

Local commits in order:

| Commit | Verified change/checkpoint |
| --- | --- |
| `070edf33c19c1742d235f22db562376dc9766578` | Migrate numerical-control tests to explicit Material acceptance |
| `db9f6e1cee78c5290201e27ea74f06e76851c193` | Release closed test-owned Qt widgets between regression cases |
| `79714d755883e183f00bda9266565c75a7a5b2f5` | Keep restored MDFF model presentation and manual source identity stable |
| `6f6425053c588c2646aca7f2a4472268d7b52536` | Align maintained GUI contracts with current Material and result workflows |
| `1dd95ff5c81ce2e9ed06e24f2f41d979a405c568` | Register canonical sources while retaining independent kernel identities |
| `49a37c849e75847ce025e84895c2df933821d33e` | Restore accepted MDFF inputs from verified portable project sources |
| `06687ac04b233fed39053b740ec82dda580d3a83` | Align remaining GUI and worker checks with accepted Material inputs |
| `313e2fd1ed16f0aea1b5825711f1e8dff36a45f5` | Record complexity baseline and ongoing regression recovery evidence |
| `550eeec1054a2ecb6f066286e18118405690faaf` | Preserve inactive manual tensor frames when restoring verified sources |
| `cd86ede2725c339bee171b436b4d332ff32b956a` | Migrate native acceptance to current Material and kernel interfaces |
| `91aff158d7c6ec17a45196200830d3e1f7c178a3` | Verify canonical GUI and grouped execution contracts without weakening numerics |
| `4b5dc2bef22d9a5a283546cfb16420c055b581c9` | Verify native resource controls through current Material and restore APIs |
| `6d98694b2367fdb9586f33287f9a09c159c7ef27` | Record complete recovery result and reviewed resource QA source |

The completion commit only updates this report. The application artifact
continues to identify the exact `6d98694...` source; no report-only successor
is misrepresented as compiled. The tracked worktree is clean after committing
the report; generated evidence/artifacts remain in ignored build directories.
The checkout and branch were not moved. No push, merge, tag, publication,
public-version bump or installed-release replacement occurred.

## Acceptance decision

Criteria covering current API migrations, ordinary GUI/project behavior,
memory admission, preserved assertions/references/budgets, retired facades,
unchanged dependency-cycle groups, native development build/identity and local
committed delivery are supported by the evidence above.

**GO is blocked by the six scientific numerical comparisons in C.** They are
not hidden by selection, source-pin relaxation, reference regeneration, skip
changes or tolerance broadening. Unavailable external evidence is listed
explicitly rather than manufactured from production output.

The refactor genuinely improved local API clarity, source ownership and
workflow correctness. It did **not** broadly reduce code volume or dependency
complexity: production S LOC and import edges increased, and the large cyclic
GUI/service boundary remains. Phase 3 should address those measured boundaries
after the numerical contract is resolved.
