# Phase 2 regression recovery and architecture stabilization

Status: **IN PROGRESS; NO acceptance claim.** Starting source is
`6817d644d3e9dcc3f06d02d1ad733e36b331d0f2`, on
`refactor/physics-readability`, in
`C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute`.
The existing uncommitted complexity audit is preserved. Nothing has been pushed,
merged, tagged, published or installed over a release.

## Evidence and authoritative starting inventory

Raw Phase 1 `complete-suite.log` and `complete-suite.xml` were inspected and
copied, unchanged, to `build/regression-recovery/phase1-complete-suite.*`.
The XML and terminal summary agree:

| Inventory | Collected | Passed | Failed | Errors | Skipped | Duration |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Recorded full Phase 1 run | 1,747 | 1,091 | 388 | 205 | 63 | 19,907.56 s |
| Fresh Phase 2 collection | 1,747 | n/a | n/a | 0 collection errors | n/a | 43.06 s |

The original raw log/XML do not embed a Git revision or a complete environment
record. `REFACTOR_NAME_MAP.md` records `db63dcf` at the start of that run and
subsequent test-only corrections. This is documentary provenance, not an exact
snapshot reconstructed from the log. Current collection and each new run have
their own explicit Git/environment records. The historical 593 failure/error
reports must not be relabeled as the current HEAD's full-suite result.

`build/regression-recovery/phase1-inventory.json` preserves all failure/error
node identities, messages and tracebacks, plus the inspection environment.
Initial symptom classification finds 244 explicit memory-admission reports,
202 source-registration/removed-scheduler reports, 71 Global MDFF draft reports
and 76 requiring individual classification. These categories describe observed
symptoms; they are not yet final root-cause or acceptance counts.

## Runtime and reproducible commands

Python: `C:/Users/peng863/EMCD-Sim/build/windows-rc/venv/Scripts/python.exe`,
3.11.17, Windows 10 build 26200, 64-bit. Installed versions: pytest 9.1.1,
NumPy 2.4.6, SciPy 1.17.1, PySide6 6.12.0, Matplotlib 3.11.2, ASE 3.29.0,
spglib 2.7.0, PyInstaller 6.22.3. `psutil` and `threadpoolctl` are not installed;
their presence is not assumed.

New pytest runs use explicit worktree `src;tests` in `PYTHONPATH`,
`PYTHONDONTWRITEBYTECODE=1`, `PYTHONHASHSEED=0`, `OPENBLAS_NUM_THREADS=1`,
`OMP_NUM_THREADS=1`, and `QT_QPA_PLATFORM=offscreen` unless a native run says
otherwise. Each `*-run.json` records the exact argument vector, environment,
HEAD, dirty paths, owned subprocess PID, timing and exit code; adjacent `.log`
and `.xml` files are raw evidence. Runs execute serially. A timeout terminates
only the owned pytest process tree.

Two initial GUI attempts exposed pytest temporary-directory permission failures
inside the execution sandbox, including owner-only directories created inside
the writable workspace. The GUI checks then ran under the normal Windows user
token with unique workspace `--basetemp` paths. Those permission errors are
infrastructure failures, not application regressions or successful GUI checks.
No ACL, machine policy or scientific resource budget was changed.

## Verified correction checkpoint 1

Local commit: `070edf3` — Migrate numerical-control tests to explicit Material
acceptance. Only three test files changed; production application source is
unchanged.

- Automatic-setting unit checks now assert the already implemented starting
  cutoffs, 2.5/2.0 inverse angstrom, rather than older 3.2/2.5 values.
- The saved historical Ni automatic-mode fixture explicitly accepts that Ni
  configuration through MDFF Done and Material Apply. Declared source providers
  remain restricted to Manual settings; no Ni fallback was added.
- Resource-widget tests exercise the existing integer memory request, Manual
  selection, unchanged 512 MiB request and 2,048 MiB reset, rather than a retired
  combo box. This does not increase calculation budgets.
- The original [011] orientation is checked as supported by the existing
  engine; a real invalid [000] direction must be rejected without fallback.
- The real Fe atomic GUI integration now performs MDFF Done and Material Apply
  before calculation, preserving its calculation, save/reopen, embedded-source
  and missing-source assertions.

Evidence: `phase2-gui-migration-check` completed 24 passed, seven failed, four
pre-existing optional-artifact skips. The real Fe integration passed. After
correcting the historical-Ni fixture, `phase2-numerical-controls-migration`
completed 29 passed, one failed (only the invalid-direction message spelling),
four unchanged skips. The exact invalid-direction assertion was corrected and
`phase2-geometry-rejection-check` passed. These overlapping focused results are
not added together or represented as a full-suite pass.

## Memory investigation so far

The historical failures include tiny predicted calculation arrays rejected
because process RSS had already exceeded the unchanged 2,048 MiB budget, with
zero active calculations reported. A representative 0.5 nm FFT interval case
passed in the fresh `phase2-root-cause-baseline` process. Fresh versus grouped
versus original-order lifecycle investigation remains open; this does not yet
prove a memory leak, exclude estimator defects or justify increasing budgets.
Per-test lifecycle observations are retained in the applicable `*-lifecycle.jsonl`
evidence files.

The new closed-widget regression first failed under the original cleanup:
`QWidget.close()` left its native object alive. Cleanup previously destroyed
only test-owned MainWindows, leaving other closed top-level widgets and their
signal/plot objects alive. Commit `db9f6e1` extends destruction to all test-owned
top-level widgets while preserving pre-existing module/class windows and the
running-MainWindow-worker rejection. The focused memory/restoration batch then
passed 20 cases, including every memory-budget test and this regression; its
sole remaining failure was an obsolete solver-label assertion. Original-order
full-suite behavior still needs verification; this is a demonstrated retention
defect, not proof that it explains every historical memory rejection.

## Verified correction checkpoint 2: saved-model restoration

Commit `79714d7` corrects two demonstrated ordinary application defects:

- Restoring an XMCD run after viewing Atomic inputs left the Atomic description
  visible, although the restored model and data were XMCD. Restoration now uses
  the existing model-change presentation path; that callback avoids capturing
  partially restored manual state.
- Previewing a restored manual constant tensor regenerated identical bytes in
  the workspace, replacing the verified project path/status and creating an
  unapplied draft. Matching generated content now retains the existing source
  path after checking it with the existing MDFF authentication. Changed input
  still produces a new draft; missing/tampered source is not silently accepted.

All three model restoration/preview/recalculation cases passed, including exact
spectral-array equality. The original source/input assertions remain; additional
checks require that restoration and preview leave accepted MDFF input unchanged.

## Additive source-registration recovery

This is a necessary exception to the default against new identity records.
The concrete failure is that the existing closed registration names four
removed Python paths and stale current files, preventing both positive controls
and their mutation tests. Existing tests explicitly require validation with
`subprocess.Popen` forbidden, so Git alone cannot supply their historical bytes
at runtime. Removing the guards or updating historical identities would lose
existing safeguards.

The additive `tests/fixtures/physics_readability_current_v1.json` records the
reviewed current owners and compressed exact prior source bytes. Every prior
file was recovered from actual registration commit
`effb755b7ed907cb2b8d386c1b7b67d9c8c53ffc` and checked against its unchanged
existing canonical identity. The original v4 manifest/archive, older maps and
scientific kernel/data pins are not rewritten. Current bytes are authenticated
before prior bytes are used inside the original historical guard chain.
Historical workflow trees use those authenticated prior files; production
exposes none of the retired facades.

The comparison also identified registration drift predating Phase 1, including
the already implemented beta.1 → beta.2 packaging metadata. Phase 2 does not
change or bump that version. The new declaration records the current metadata
separately rather than relabeling the historical packaging query. Positive,
negative, archive-integrity and no-Git controls are being verified.

Positive controls exposed a second pre-existing registration defect: the
`legacy_kernel_source` helper tried to reconstruct the original kernels by
deleting source text around markers no longer present after earlier grouped
Bloch/buffer work. It failed before checking the scientific identity. That
obsolete reconstruction is removed; it is not replaced with a physics change.

The guard now independently checks complete current kernel identities against
exact Git source at the required pre-refactor commit `cdb8836`, in addition to
ordinary current-file registration. These three scientific identities are a
necessary preservation of the existing boundary: an ordinary UI registration
update must not authorize changed kernels, and the original earlier hashes
describe a different recorded software version. Git cannot supply this control
when the existing no-process/no-Git tests run. The values were read from the
actual frozen Git commit, not adopted from modified candidate source.

All original convention-version hashes remain unchanged and authenticate the
exact corrected source from `2f9c130099dce5df4e4609b521c42f53c5385518`, whose
bytes match every original pin. Current and historical line-ending variants
remain checked. Reverted scientific-convention mutations are also tested with
ordinary registration treated as already approved, so the independent current
kernel check cannot be replaced by an application-scope approval. No scientific
kernel file, formula, input, expected numerical array or tolerance is changed.

Registration verification completed 183 passed, one failed and one existing
optional-array skip in 568.33 s. All source-mutation, archive, closed-declaration,
no-Git and independent kernel-boundary checks passed. The sole failure was a
display-label scanner treating a function docstring as displayed UI text; it now
excludes only formal Python docstrings and still checks actual string literals
and behavioral table labels.

The follow-up `phase2-historical-current-workflow-bridges` batch passed all seven
outer cases in 102.75 s. Five of those invoke the existing paired historical and
current contracts in separate recorded subprocesses; both sides must pass. The
other two verify the corrected label scan and the already implemented beta.2
Windows metadata. Source-registration recovery is not yet a full-suite pass.

## Complete frozen-candidate regression

The first complete Phase 2 regression ran on clean commit
`313e2fd1ed16f0aea1b5825711f1e8dff36a45f5`, without selection or early stopping.
Evidence is `build/regression-recovery/phase2-complete-suite-candidate-313e2fd.*`;
its `-run.json` records the exact command, environment, initial clean status,
process and timing. The XML-derived remaining inventory is
`phase2-candidate-313e2fd-inventory.json`.

| Outcome | Recorded Phase 1 | Phase 2 frozen candidate | Absolute change | Change |
| --- | ---: | ---: | ---: | ---: |
| Collected | 1,747 | 1,760 | +13 | +0.74% |
| Passed | 1,091 | 1,634 | +543 | +49.77% |
| Failed | 388 | 64 | -324 | -83.51% |
| Errors | 205 | 0 | -205 | -100% |
| Failures and errors | 593 | 64 | -529 | -89.21% |
| Skipped | 63 | 62 | -1 | -1.59% |
| Duration, seconds | 19,907.56 | 4,771.27 | -15,136.29 | -76.03% |

These are observed inventories, not a controlled performance comparison or a
claim that historical logs identify an exact current source snapshot. No new
skips or relaxed numerical tolerances were introduced. Inventory differences
and skip reasons still require final reconciliation.

The actual pytest payload PID was 7892, distinct from launcher PID 18524.
Windows measured **944.35 MiB peak RSS** and **1,000.82 MiB peak commit**.
There were **zero memory-admission failures** among the 64 failures, compared
with 244 explicit historical admission reports. Current-process GUI lifecycle
records show destruction of test-owned widgets; logs also include short-lived
historical workflow subprocesses, so rows must not all be interpreted as one
process. The final payload peak is the authoritative main-process peak.

The 64 failures include obsolete draft accessors, incomplete Material acceptance
in fixtures, previous widget/plot expectations, old execution-hook assumptions,
and independent numerical discrepancies. They are being corrected and verified;
the frozen run is not represented as a clean pass.

Further focused recovery completed 141 passed, 21 failed and one unchanged skip
in 306.03 s (`phase2-post-suite-gui-consumer-recovery`). Most editor/draft and
current GUI contracts passed. Follow-up `phase2-manual-frame-and-current-plot-contracts`
completed 15 passed and eight failed in 119.33 s; both relocated analytical
manual-tensor projects now recalculate exactly, and every requested slice-step
case passed. Remaining presentation and external-source expectations continue
under investigation.

The manual-tensor investigation found an actual restoration bug at non-[001]
Material M: `manual_l23_editor.load_source` replaced the saved **inactive** full
frame draft with the active physical frame. The next generation changed editor
provenance/file identity and produced a phantom unapplied draft. Restoration
now preserves a saved inactive frame (or an active frame exactly matching the
authoritative model). Physical frame selection, tensors and equations are
unchanged. Existing exact recalculation and independent sampled-tensor assertions
remain intact.

Portable persistence remains deliberately different for editor-managed sources
and arbitrary external files. Generated Atomic/manual inputs can be embedded;
external JSON/XMCD files retain their original-source requirements. Recovery
does not silently make every external file portable or substitute another
source after loss/corruption.

## Portable Atomic source restoration

The next material/GUI batch completed 138 passed, 25 failed and three skipped
in 283.07 s (`phase2-remaining-material-workflows.*`). Its failures were
investigated separately rather than relabeled as obsolete tests.

A non-destructive trace demonstrated a real restoration defect: provider
validation correctly loads and authenticates `atomic_input.json`, but the
accepted Global configuration retained the unavailable original source path.
The final Run eligibility check then invalidated the restored Atomic provider.
`results_browser._restore_single_settings` now binds the accepted input source
to the loader's project-source override. The result's recorded original
configuration is preserved; expected source hashes and file validation remain
unchanged. Existing relocated-project tests retain all three browser mappings,
exact spectrum comparisons after recalculation, and altered-file rejection.

Draft-only editor tests now inspect `global_mdff_draft_settings`, while tests
that run GUI workers accept MDFF through the real Material transaction. The
rotated Atomic frame test explicitly assigns Material M and verifies that a
source frame cannot silently overwrite it. Manual-model switching also changes
Material M explicitly. Multielement rejection is checked at MDFF Done rather
than against a generic earlier Run tooltip. Numerical grids and tolerances are
unchanged. Focused verification is in progress.

`phase2-portable-source-and-draft-workflows` completed 14 passed and 12 failed
in 168.44 s. All relocated Atomic, tensor-equivalence, frame-binding and manual
draft cases passed. All ten geometry cases completed real calculations and
saved-data checks; their remaining comparison incorrectly expected restoration
of the old machine's resolved resource allocation. Current project restoration
deliberately retains the saved request and discards that machine-specific
allocation. The assertion now compares every configuration field with only
`resource_allocation=None`, and checks that the saved result still records its
original allocation. No calculation result or resource limit is altered.

`phase2-current-geometry-selection-contracts` then completed 12 passed and one
failed in 119.82 s: all ten geometry cases and the complete Fe source-selection
workflow passed; the remaining failure referred to an obsolete presentation
widget in the Global/Local lock test. Windows measured the actual pytest
payload's peak RSS as 255.98 MiB and peak commit as 247.52 MiB. Its PID was
23724, distinct from the venv launcher PID 8064. The launcher's approximately
4 MiB counters are not evidence for calculation memory. Raw stdout records the
payload counters under `PHASE2_PAYLOAD_MEMORY`; per-test lifecycle evidence
continues to record actual in-process RSS and remaining Qt objects.

The portable binding correction is committed as
`49a37c849e75847ce025e84895c2df933821d33e` (two application-source lines).
The worker/resource/historical-Ni batch completed 19 passed, four failed and
one independently optional historical-project skip in 57.25 s. Its actual
payload peak was 247.79 MiB RSS. The worker lifecycle, explicit Material
acceptance, Global/Local lock, and controlled multisite worker-limit tests
passed. Two ordinary failures were subsequently corrected and passed in
`phase2-release-controls-and-pressure-rejection`: the Custom label now includes
the grid count, and a legacy memory test wrongly assumed its bounded Single
Channeling request necessarily exceeds 512 MiB in a fresh process. That test
now supplies an explicit 512 MiB RSS measurement to exercise real over-budget
admission, retaining the identical calculation sizes, 512 MiB budget and
rejection assertion. This is deterministic resource-state control, not a
production admission change.

The multisite resource-only test requests the complete angular field so the
unchanged 512 MiB budget limits worker count. With aperture-only task capacity,
the current scheduler already chose one useful worker before memory limiting;
the old message assertion therefore never exercised its intended condition.
No estimated scientific arrays are allocated in that test.

Two historical Ni Double Channeling exact-array failures remain open:
`test_original_ni_all_numeric_arrays_exact[double-xmcd]` differs by
`1.3010426069826053e-18` (relative `5.0519996e-16`), and `[double-atomic]` by
`2.6469779601696886e-23` (relative `1.16368886e-16`). Both Single Channeling
cases passed. The reference is the untouched source at `2f9c130...`; these
differences already occur at the required pre-refactor baseline. Neither the
strict assertions nor scientific source was changed to conceal them. They
remain explicit acceptance blockers pending final classification.

The first registration follow-up caught an incorrect raw-CRLF digest used
while updating the current declaration; canonical newline normalization
corrected it. `phase2-current-registration-normalized` then passed the positive
current and independent historical queries in 18.76 s. The original kernel and
data identities remain unchanged.

| Test name before | Test name now | Reason |
| --- | --- | --- |
| `test_rotated_frame_derived_axis_and_top_level_consistency` | `test_rotated_frame_requires_matching_material_magnetization` | A source frame must match explicitly assigned Material M, rather than overwrite it. |
| `test_worker_policy_only_changes_windows_bw` | `test_standalone_requests_remain_serial_without_an_admitted_plan` | An unplanned standalone request stays serial on either platform; admitted production concurrency is checked separately. |

## Scientific evidence and native identity

The independent pre-refactor source remains
`cdb8836388c5ccc5ae7a614b47894c0ab158a824`. The existing 22-case comparison
driver and its recorded 2,294-array result are available under
`build/physics-readability/`. A verbatim copy of the existing driver ran again
against application commit `79714d755883e183f00bda9266565c75a7a5b2f5`:
**22 cases and 2,294 arrays exactly equal**, with matching checked physical
metadata and selected-edge metrics, in 14.593 s. Evidence:
`build/regression-recovery/phase2-independent-source-equivalence.log` and its
`-run.json`. No expected numerical arrays were regenerated from current code.
This is pre-refactor-source equivalence, not a claim that both backends constitute
independent physical validation. The independent earlier Ni reference deltas
are already present at the starting source: approximately 1.30e-18 (XMCD) and
2.65e-23 (Atomic); their existing checks/tolerances are not changed.

`git diff --stat 3f9112a 6817d64` shows only 51 added lines in
`docs/REFACTOR_NAME_MAP.md`. Thus the earlier EXE excluded documentation changes,
not application/packaging changes, between those two identities. This explains
their differing commit IDs but does not satisfy final candidate EXE rebuilding
or native acceptance. Rebuild/validation follows regression recovery; it has
not yet been performed in Phase 2.

## Outstanding acceptance work

Recover current source registration while preserving strict scientific pins,
migrate remaining obsolete GUI consumers with behavioral coverage, investigate
actual regressions and memory lifecycle, revalidate independent numerics, run
the complete intended suite on frozen source, rebuild and validate the native
development EXE, compare complexity with the preserved original audit, and
record final local commits and status. GO requires all requested criteria;
selected passing batches are insufficient.

## Additional recovery checkpoint after the first complete run

The remaining ordinary GUI consumers were migrated to explicit MDFF Done and
Material Apply, current resource controls, result-owned input restoration, and
semantic edge-selection data. Effective scientific assertions remain in place.
Plot checks now count the actual primary and secondary axes (four for the
ordinary EELS view, six for component views), rather than treating every axis
as an independent panel. Responsive-layout checks measure the scroll range
released by maximizing the plot while retaining its minimum legend height.

Cancellation and cohort spies now target the active canonical orchestration
and grouped kernels. An old-reference call adapter removes only the new
`prepared_outgoing` software argument; the historical reference still computes
its own outgoing states and retains its original numerical assertions.

| Previous test name | Current test name | Reason |
| --- | --- | --- |
| `test_restored_proper_frame_direction_is_derived` | `test_restored_frame_preserves_material_direction_and_full_basis` | Loading verified data must preserve both the accepted Material direction and saved inactive full-frame editor state. |
| `test_cancellation_between_site_events` | `test_cancellation_between_grouped_energy_events` | The production dispatcher shares grouped energy events; cancellation is checked at the real event boundary. |

No test was removed or skipped to conceal a failure.

`phase2-final-explicit-ni-guard` passed both the real imported Fe workflow with
explicit Ni-on-Fe rejection and positive current/historical source registration
in 28.44 s. `phase2-source-desktop-native-qa-current-workers` passed native Qt
Single/Double, BW/MS, Save/Open fingerprints and exports in 35.719 s.

The existing cancellation acceptance required current kernel instrumentation:
the old probe watched `depth_response` while production uses the shared grouped
response. The initial owned QA process stalled on a Retain Calculation dialog;
the exact payload window title and runtime log confirmed it. Only its recorded
process tree was stopped. The migrated QA clears temporary browser selection,
observes actual BW/MS group/depth checkpoints, and discards only temporary QA
drafts at shutdown. Production cancellation and kernels are unchanged.
`phase2-source-cancellation-current-kernel-hooks` then passed all nine cases,
queued-completion suppression, immediate restart and project integrity in
19.547 s. Worst request-to-idle latency was 0.255919 s, below the unchanged 2 s
assertion. Reservations and prior completed arrays are checked throughout.

The four representative memory modes use identical explicit Ni preset inputs:
0.3 nm, cutoffs 0.9/1.8 inverse angstrom, angular grid 9, depth 9, aperture
subpixels 8, FFT 16, slice step 0.01 nm, one requested worker, 2,048 MiB budget.

| Mode | Predicted working MiB | Predicted process peak MiB | RSS before/after MiB | Lifetime peak RSS MiB |
| --- | ---: | ---: | ---: | ---: |
| Bloch Single | 0.067 | 203.022 | 75.113 / 77.871 | 94.520 |
| Bloch Double | 8.119 | 216.023 | 77.875 / 78.035 | 94.520 |
| FFT Single | 0.159 | 206.238 | 78.070 / 78.117 | 94.520 |
| FFT Double | 9.806 | 218.374 | 78.117 / 78.156 | 94.520 |

Evidence: `phase2-representative-memory-modes.log` and `-run.json`.
The Windows PSAPI measurements come from the actual calculation process;
the venv launcher peak is a different process and is not substituted for it.
The lifetime peak is cumulative across these four short cases and includes
imports; it is not a per-kernel incremental peak. Peak commit was 109.602 MiB.
Every case left zero active reservations, no detector executor threads and an
unlocked Windows Bloch executor. These small cases support correct conservative
admission, not an arbitrary-size accuracy claim for the estimator.

Six strict numerical failures are currently exposed. In addition to the two
older Ni Double exact comparisons already recorded, the historical cancellation
reference has one numerical-depth and two full-spectrum exact-array failures
(maximum differences about 1.39e-17 and 6.94e-18). The weighted Cr grouped parity
case differs by 1.08420217e-18 at a cancellation-sensitive derived signal, just
outside its unchanged absolute tolerance of 1e-18. The exact same Cr assertion
and numbers fail when running the actual pre-refactor source in memory:
`phase2-cr-current-and-pre-refactor-assertion.log`. These failures are retained;
no tolerances, input sizes, equations or expected arrays are altered.

Raw old/current XML node comparison explains the first complete run's +13
collected cases: eight added current-owner mutation cases, one additive
declaration mutation, one native-widget teardown regression and three extra
independent-kernel negative controls with ordinary registration already
approved. Renamed tests/path parameters are paired rather than treated as
deleted coverage. One prior optional GUI artifact became available; no skip was
added, giving 63 to 62 skips. Final XML confirms 1,760 cases: adding the current
approval for the already declared ZOLZ path did not create a collected case.
Relative to the first Phase 2 full run, exactly two test names changed and no
case was added or removed. The 62 skipped node identities are unchanged.

`phase1-final-classification.json` gives a primary category and reason for every
one of the original 593 failure/error reports: A registration/API 211,
B GUI/application contracts 127, C source/project restoration 5, D memory
admission 244, E observed numerical 1, F test infrastructure 5. This supersedes
the preliminary symptom grouping. Memory or registration failures frequently
prevented downstream assertions from running, so the initial single observed
numerical failure does not mean other numerical comparisons had passed.

Local native-QA checkpoint: `cd86ede2725c339bee171b436b4d332ff32b956a`.
It updates only opt-in QA routes/callbacks and the packaging acceptance script;
no scientific engine or normal GUI execution calculation is changed.
The independently run changed provider stage passed six Fe/O cases in 82.766 s,
using the current MDFF workspace labels, scroll owner and semantic map choices.
The eight core Ni/Fe cases passed calculation, Save/Open and recalculation in
both full source attempts before their obsolete provider-stage widgets failed.
These partial run records are not relabeled complete native acceptance.

## Final complete regression and subsequent QA-only checkpoint

The complete, unselected regression on clean
`91aff158d7c6ec17a45196200830d3e1f7c178a3` finished with **1,692 passed,
six failed, zero errors and 62 skipped** (1,760 total) in **4,311.19 s**.
The recorded launcher duration, including startup/exit, is 4,318.11 s.
`phase2-final-complete-suite-91aff15.log`, `.xml`, `-run.json` and
`-lifecycle.jsonl` are the raw evidence; `phase2-final-inventory.json` contains
all six full tracebacks and all skip identities/reasons. No early stopping or
test selection was used. Its initial Git status was clean.

All six failures are exactly the numerical checks already identified:
`test_bw_unchanged_and_depth_cancel[numerical]`,
`test_full_spectrum_unchanged[bloch]`, `[both]`, the unequal-MDFF Double Bloch
Cr parity assertion, and the two older Ni Double exact-array comparisons.
There are **zero registration, ordinary GUI/application, infrastructure or
memory-admission failures** in this run. This is **NO-GO**, not a green suite.

Actual calculation/pytest payload PID 8620 peaked at **972.1328125 MiB RSS**
and **1,030.08203125 MiB commit**. The separate venv launcher PID 1700 peaked
at 4.375 MiB RSS and is not used as the application measurement. The additional
58 passing cases versus the first Phase 2 full run did not restore the original
process-budget cascade. No budget, numerical dimensions or admission rule was
relaxed.

After that full run, local commit
`4b5dc2bef22d9a5a283546cfb16420c055b581c9` corrects only the opt-in
`gui.parallel_acceptance` QA route: current startup/control APIs, explicit Ni
Material acceptance, controllable BLAS policy, admitted worker assertions and
actual Save/Open restoration of visible resource fields. Its real four-worker
source run passed with its original grid/dimensions and **2,048 MiB** request,
unchanged output fingerprints and restored Manual memory/worker controls.
The temporary 512 MiB value is only an unexecuted UI draft before restoration;
no calculation or saved result is relabeled with that value. Evidence:
`phase2-source-resource-current-api.*` and its `acceptance.json`.

The affected current/historical registration and resource-control modules then
passed **48 tests, one unchanged optional-project skip**, in 17.62 s
(`phase2-resource-qa-affected-checks.*`). Current approval metadata is updated
for that reviewed QA source. Scientific source, numerical fixtures, assertions,
normal production GUI execution and all shared calculation kernels are unchanged
from the full-run candidate. The full result remains attributed to `91aff15`;
it is not silently relabeled as the later QA/build commit.
