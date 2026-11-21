# Phase 3E-2: GUI simplification and state management

## A. Executive summary

Starting HEAD: `4670f35e816138c39ca504cc70f2fdd48bb1c60e`, clean on
`refactor/physics-readability`, containing the verified Phase 3E-1 implementation
`8be3b5e6eda9a019ba4406aa0fe7ddd4ae86e8a6`. Working directory and worktree root:
`C:/Users/peng863/EMCD-Sim/.worktrees/windows-adaptive-compute`.
Both source-registration controls passed before editing. The 3E-1 report,
3D-2B-2 engine report, 3C persistence report, 3A simplification report,
physics/name maps, regression recovery and numerical contracts remain prior
evidence. Their completed regressions/investigations are not resumed.

Implementation commit: `20009f4ac138731e04b1a479acc6b76ce5a5717b`.
Decision: **focused GO for Phase 3E-2**. The bounded implementation and its
required focused/scientific checks pass. Full integration and native Windows
candidate acceptance remain the separate Phase 3F task.

This is a bounded client-side cleanup, not a new controller framework. Global,
Local and configuration save now use the existing common control collector.
Saved seven-control values share one field set and translation. Two redundant
sampling writes are removed. Four project-I/O cancellation/progress callbacks
share one existing-owner implementation. No production module is moved, split,
created or deleted, and no new public calculation adapter is added.

The scope is intentionally modest: source LOC falls by nine and one internal
edge is removed. All four dependency cycles remain. Large modules with genuine
independent responsibilities are retained; no size-only architecture claim is
made. Scientific engines/models, settings, data, numerical contracts, resource
admission/scheduling, physical cancellation, layouts and labels are unchanged.

## B. GUI complexity audit

The pre-edit prioritized inventory is `build/phase3e2/CLEANUP_INVENTORY.md`.
`baseline-audit.log` records the 13 required module inspections, exact-body
candidates and passing source controls. Each selected item identifies both
implementations, maintained consumers, risks, tests and intended improvement.
Exact similar Qt hooks were retained; similarity alone was not treated as
permission to merge different state contracts.

| Module | Physical LOC before / after | Source LOC before / after | Duplication removed / remaining responsibility |
|---|---:|---:|---|
| `gui/app.py` | 676 / 676 | 620 / 620 | Retained: window/layout, coordinate interaction and existing launch/QA consumers; setters extend saved precision/ranges and track dirty state. |
| `gui/calculation_controls.py` | 570 / 562 | 529 / 521 | Removed the duplicate Global control collector; accepted Material/window/M handling and submission/validation sequence remain. |
| `gui/project_session.py` | 500 / 499 | 461 / 460 | Uses the common seven-control value map; removes the second angular-map write. Capture, local/global contracts and selected-run restoration remain. |
| `gui/results_browser.py` | 429 / 429 | 410 / 410 | Uses the same saved-control translation; removes a repeated angular-map write. Original/effective source handling and result selection remain. |
| `gui/project_io.py` | 584 / 587 | 493 / 493 | Four I/O callback bodies now share its project progress checkpoint. Exact arrays, transactional writes, schemas and source evidence remain. |
| `gui/project_configuration.py` | 274 / 270 | 237 / 233 | Uses the existing I/O owner checkpoint, removing its direct cancellation import and two callback bodies. Editable-state compatibility remains. |
| `gui/atomic_editor.py` | 627 / 627 | 574 / 574 | Retained: source-specific draft/reference/loading/generation/preview/export roles are distinct; no safe transaction merge demonstrated. |
| `gui/group_mdff.py` | 599 / 599 | 547 / 547 | Retained: source acknowledgment, physical pair binding, window validation and parent draft commit are separate boundaries. |
| `gui/site_group_editor.py` | 529 / 529 | 461 / 461 | Retained: parent accepted rows and MDFF draft snapshots differ from per-dialog Done; cancel must restore both. |
| `gui/provider_ui.py` | 263 / 263 | 238 / 238 | Retained: existing common source declaration/binding owner already delegates scientific validation; no copied model validator added. |
| `gui/numerical_settings.py` | 197 / 205 | 162 / 166 | One shared spin-key set and inverse value translation; its existing collector now supplies Global as well as Local/save. |
| `gui/responsive.py` | 614 / 614 | 531 / 531 | Retained: layout/reflow/resize/wheel and figure presentation roles, no layout redesign or new mixin for required Qt show callbacks. |
| `gui/result_presentation.py` | 472 / 472 | 432 / 432 | Retained: stored result quantities, map/spectrum/component rendering and export contexts are independent; scientific reductions unchanged. |

Measurement reuses the established `measure.py` AST/token methodology. Physical
lines include all lines; nonblank/noncomment includes docstrings; source LOC
also excludes docstrings. Literal internal imports include deferred imports,
with one edge per module pair. GUI is a subset of production and is not counted
twice. There is no new metric gate, frozen baseline or identity framework.
Artifacts: `build/phase3e2/before.json`, `after.json`, `metrics.log`.

| Metric | Before | After | Absolute / percentage change |
|---|---:|---:|---:|
| Production Python files | 111 | 111 | +0 / +0.00% |
| GUI Python files | 53 | 53 | +0 / +0.00% |
| Non-GUI Python files | 58 | 58 | +0 / +0.00% |
| Physical production lines | 19,602 | 19,600 | -2 / -0.01% |
| Nonblank/noncomment lines including docstrings | 17,512 | 17,505 | -7 / -0.04% |
| Production source LOC | 16,547 | 16,538 | -9 / -0.05% |
| GUI source LOC | 10,717 | 10,708 | -9 / -0.08% |
| Internal import edges | 498 | 497 | -1 / -0.20% |
| SCC groups | 4 | 4 | +0 / +0.00% |
| Modules in SCCs | 13 | 13 | +0 / +0.00% |
| Largest SCC | 5 | 5 | +0 / +0.00% |
| Non-GUI to GUI edges | 5 | 5 | +0 / +0.00% |

## C. State ownership

`NumericalSettingsUI.forward_control_fields` remains the single collector for
shared propagation, channeling, sampling, apertures and resource requests.
`CalculationControls.forward_settings` uses that collector instead of rebuilding
the same 23 fields. Global window and Material M remain explicit extras; all
pending-draft checks, accepted-source selection, source binding and FFT
validation stay in their original positions. The resource getter reads requests
without carrying forward a prior runtime allocation; it never admits workers.

The seven spin keys now live once in `FORWARD_SPIN_KEYS` in the existing
numerical-controls owner. `forward_control_values` translates those values from
a saved request for both Global and Local restoration. Energy remains at each
caller's original ordered position, and geometry, source fields, precision/range
extension and resource controls retain their separate existing operations.
`restore_sampling_controls` already restored angular maps, so the two later
identical signal-blocked assignments were removed. Row projection remains at
its original point. Widget hierarchy, labels and wheel behavior are unchanged.

Accepted Global MDFF belongs to the Material transaction. Local group records
and accepted/draft dialog snapshots belong to the site-group editor. Source
acknowledgment, a dialog's Done and the parent's Apply are different commits.
Atomic generation/preview/loading/export and Manual/XMCD source declarations
are not one universal editor. No accepted or inactive draft is promoted by
reading common controls. Repeated source/window validation is retained because
its identity and transaction boundaries are not proven interchangeable.

Project restoration still goes through `restore_configuration` and the existing
selected-run restoration entry. Original declarations and verified effective
portable paths remain distinct. The existing Global snapshot/frame restoration
is retained; avoiding that reconstruction could change geometry precision or
historical interpretation. Stored results remain immutable display inputs.
Selecting a method, raw/relative component or an earlier run does not recompute
scientific arrays or replace saved requests with observed allocations.

`project_io.progress_checkpoint` owns the identical cancellation-before-progress
body formerly nested in four save/load functions. Four `partial` bindings
preserve each operation's callbacks, stage strings and checkpoint locations.
This is project-file I/O only. No numerical checkpoint, worker scheduling or
physical cancellation code changes. New API-level tests cancel after the first
reported stage, require cancellation before another report, and check rollback
or preservation of an existing manifest for result/configuration Save/Open.

## D. Dependencies and retained interfaces

The only removed import edge is `gui.project_configuration -> cancellation`.
Configuration I/O already depends on `project_io`, which now owns the shared
project-file checkpoint and the same `Cancelled` class. No maintained consumer
imports the former incidental cancellation alias from configuration. No new
internal edge or unintended cycle is introduced.

Four duplicated nested callback definitions become one shared definition.
One duplicate Global run-control builder and two restoration field-set copies
are removed. There are no speculative public API removals or dead-code claims.
The supported GUI calculation re-export, Qt callbacks and schema compatibility
remain. `MainWindow.set_values` is retained: its precision/range extension and
dirty tracking differ from numerical-policy filtering in `set_numerical_values`.

The five-module `app`/`cancellation_acceptance`/`desktop_acceptance`/
`parallel_acceptance`/`unified_elastic_acceptance` cycle remains. The packaged
`packaging/launcher.py` directly imports `app.main`; the task explicitly permits
deferral when breaking this cycle changes packaged startup. No new adapter,
registry, dynamic-import hiding or acceptance-command removal is introduced.
The exact CLI options and startup paths are untouched. The other SCCs remain:
atomic/imported/manual provider services, project configuration/I/O/multisite,
and elastic provider/scattering. The five non-GUI-to-GUI edges are unchanged.

The production forward engine remains `emcd_sim.forward_pipeline.calculate`;
`emcd_sim.gui.forward_pipeline.calculate` is the same direct re-export. Generic
settings and material/source services retain Phase 3E-1 neutrality. No non-GUI
scientific implementation is edited and no material-specific solver is added.

## E. Scientific verification

`science-headless` passed 71 tests (283.05 s pytest; 287.484 s owned run).
This includes all eight real strict-headless Ni/Cr BW/FFT Single/Double cases,
the six corrected numerical-contract cases, tensor/source validation,
multisite scientific invariants, cancellation, Cr serial allocation checks
and the material-independent input contracts. The original scientific tests,
reference arrays, equations, tolerances and settings were not changed.

The six numerical contracts are the numerical depth-cancellation case, the
Bloch and Both full-spectrum cases, the unequal-MDFF Cr Double Bloch symmetry
case, and Ni Double XMCD/Atomic cases. Strict-headless children reject GUI
imports except the intentionally supported calculation bridge.

The unchanged `build/regression-recovery/verify_equivalence.py`, executed through
the established reference-import relocation helper, passed **22 cases / 2,294
arrays exactly equal** against `cdb8836388c5ccc5ae7a614b47894c0ab158a824`
(26.968 s). Physical metadata and edge metrics are equal too. The driver's
separate older-reference deltas (XMCD `1.3010426069826053e-18`, Atomic
`2.6469779601696886e-23`) are identified by the unchanged driver as already
present at the starting commit; they are not changes against the required
reference. The driver, reference source and tolerance contracts are unchanged.

`source-auth` passed 13 tests (120.18 s pytest; 122.125 s owned run): positive
current/independent historical queries; current-manifest and historical
archive/manifest mutation rejection; rejection of old parent bytes as current
overrides; offline controls without Git/network/snapshot execution; reciprocal
display/legacy-key and immutable-kernel controls; supported console options,
packaging imports without building, and public exports without Qt launch.

The existing registry still has 173 entries. Only four already-protected GUI
file identities and the existing registry loader checksum are updated for
the implementation. No historical archive, immutable scientific pin, source
array or tolerance changes. `changed-gui-mutations` passed in 26.687 s: both
existing source guards reject virtual edits to `calculation_controls`,
`numerical_settings`, `project_io` and `results_browser`; real current and
historical controls pass before and after. No source file is mutated on disk.
The two ordinary GUI modules remain verified behaviorally without new pins.
The existing `production_source` pointer now identifies the implementation
commit above. `final-registration` passed both existing positive/current-
manifest mutation controls after that pointer and its loader checksum changed
(10.95 s pytest; 11.610 s owned run). These two identities already appear in
the 13-test group and are not counted twice. The report/registration successor
contains only this report, that pointer and its required loader checksum;
application source remains the verified implementation.

## F. GUI and project verification

`control-state` passed eight tests (136.74 s pytest; 142.375 s owned run):
Global/Local A-B-A restoration, displayed allocation versus saved requests,
manual/automatic numerical round trips, inactive Material fields and Local
worker restoration. `project-progress` passed six tests (21.27 s pytest;
24.765 s owned run): four added cancellation-before-progress transaction cases
and existing cancelled/failed save preservation checks.

The single broader workflow selection deselects those 14 completed cases.
Its combined outcome is **197 passed, five skipped, zero failed**, covering
202 distinct cases. The 116 unfinished cases completed as 114 passes and two
skips (702.83 s pytest; 710.031 s owned run). No completed outcome is counted
twice. Commands, environment, identities and XML/verbose results are retained
under `build/phase3e2/`.

The first `gui-workflows` payload reached its 1,800 s bound after 83 passes
and three configured skips. Its owned process tree was terminated; this is a
verification interruption, not a test assertion failure. The interrupted case
and the other uncompleted cases continue in `gui-workflows-unfinished`, with
all 86 completed node IDs deselected. The original verbose log and run record
are preserved separately. The remaining-run bound follows the measured runtime
of the first payload.

An initial continuation (`gui-workflows-remaining`, 153.687 s) was stopped
because its log parser missed one passed result split by a diagnostic dump.
It began that completed case again; no duplicate result completed or is counted.
The corrected continuation parses multiline outcomes and excludes that case.
No completed baseline or scientific check was restarted.

Passing areas include Global Apply/Cancel, Local Done/Apply, Manual/Atomic/XMCD
sources, independent site-group drafts, source acknowledgment and frame
validation; New/Save/Open/Save As, missing/changed portable sources, historical
Ni and source-backed restoration, original/effective source identity and exact
stored arrays; requested resources versus displayed/submitted allocations,
cancellation and captured worker inputs; BW/FFT Single/Double results,
raw/relative components, magnetic/nonmagnetic displays, spectral/angular
selection and figure/CSV/NPZ export without recalculation. Responsive tests
preserve wheel/layout behavior, section state and saved display samples.

The continuation reports 723 warnings, including repeated Matplotlib
constrained-layout warnings during offscreen rendering. Those tests pass;
warnings are retained in the log rather than treated as native visual
certification. Native/profile and optional saved-result fixture skips remain
limitations, not passes.

| Selection | Passed | Skipped | Pytest duration / owned duration (s) |
|---|---:|---:|---:|
| Common control/restoration state | 8 | 0 | 136.74 / 142.375 |
| Project progress/cancellation | 6 | 0 | 21.27 / 24.765 |
| Scientific/headless/contracts | 71 | 0 | 283.05 / 287.484 |
| Broader GUI before bound | 83 | 3 | interrupted / 1,800.843 |
| Broader GUI unfinished cases | 114 | 2 | 702.83 / 710.031 |
| Source/runtime interfaces | 13 | 0 | 120.18 / 122.125 |
| **Distinct completed cases** | **295** | **5** | **No full-regression claim** |

Counts are deduplicated by test identity across XML and the preserved original
verbose log, including its multiline diagnostic/result. The stopped duplicate
attempt has no completed outcome and is excluded. Baseline/final repetitions
of source controls are not added again. The 22-case exact driver and four
changed-file mutation probes are separate evidence, not additional pytest
cases.

The five skips are the explicit native group-MDFF profile, native Windows
project history/menus, the solver-settings saved-array fixture, explicit native
Windows multisite calculation, and the responsive saved BW/MS fixture. Missing
saved-result fixtures do not trigger a fallback simulation. Offscreen rendering
and API-level exports pass, but native menus, desktop visibility and frozen
package behavior remain unverified in this phase.

The existing cleanup fixture recorded 207 lifecycle events across common-state
and broader-GUI runs. Maximum remaining MainWindows and top-level widgets are
both zero. Maximum observed cleanup RSS is 458.8 MiB, a sampled observation
rather than a new budget or measurement of the true process peak.

## G. Phase 3F handoff

Phase 3F is not started here. No complete regression, Windows EXE
build/replacement, application version bump, installed Research Beta change,
push, merge, tag or publication is performed.

**Readiness: focused GO to hand off the existing implementation for a separately
authorized Phase 3F.** This is a modest GUI maintenance improvement with
preserved scientific ownership, not wholesale GUI decoupling or packaged
release acceptance. Local implementation and report/registration commits
preserve the current worktree and branch.

Completion uses a local implementation commit followed by the existing-source
pointer/report successor. The final worktree is checked clean; no application
source changes between those commits. All owned verification payloads have
ended, including the explicitly stopped bounded/duplicate attempts.

The integration boundaries are the six changed GUI modules, their existing
MainWindow/mixin callers and project I/O consumers. The non-GUI engine,
packaged launcher, CLI and native acceptance dispatch remain unchanged.
The app/acceptance SCC and the large editor/layout modules are explicit
future focused-cleanup candidates; their behavior is not replaced by a new
state framework in this phase.

Before candidate acceptance, Phase 3F must perform the complete integration
regression and explicitly configured native/frozen-package workflows,
including startup/CLI, cancellation, DPI/layout, exports and current QA
profile/default compatibility. Existing source, provenance and release
inventories still apply. Offscreen behavioral checks do not certify the
installed EXE or native desktop appearance.

All completed focused checks pass; there is no demonstrated new regression
in the executed coverage. The five skipped workflows and native/frozen-package
behavior remain unverified. The original broader-run timeout and stopped
duplicate attempt remain recorded in section F and are not counted as test
assertion failures or hidden by a successful continuation.

Existing native QA profiles retain their current fixture/default assumptions.
Phase 3F must explicitly configure and assess those profiles against the
current accepted settings; this cleanup does not change GUI defaults to match
a historical acceptance profile. Repeated offscreen constrained-layout
warnings also require native visual review before candidate acceptance.

Historical projects still depend on their recorded source identity, original
versus effective paths, tensor frame and saved numerical precision. This
cleanup deliberately preserves those loader and restoration branches; focused
fixtures cannot prove compatibility with every private project ever saved.
Unavailable or changed scientific sources continue to block reruns while
allowing stored-result viewing. No schema migration or source substitution
is introduced.

Ordinary `project_session` and `project_configuration` changes remain under
behavioral validation. The other four changed GUI source files retain their
existing current-source registration. No previously unprotected GUI file gets
a new identity pin. Historical archives and immutable kernel/data pins remain
unchanged; current registration is reviewed-source evidence rather than a
substitute for scientific or desktop tests.
