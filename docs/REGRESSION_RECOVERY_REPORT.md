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
