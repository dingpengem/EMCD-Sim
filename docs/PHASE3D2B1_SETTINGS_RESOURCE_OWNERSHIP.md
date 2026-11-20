# Phase 3D-2B-1: scientific settings and resource ownership

## A. Scope and source identity

Starting commit: `60f453de323b37cdf13f1e085acb46a95707f4b0`, clean on
`refactor/physics-readability`. Working directory and Git worktree root are both
`C:/Users/peng863/EMCD-Sim/.worktrees/windows-adaptive-compute`. Its ancestry to
Phase 3D-2A implementation `c2790aa0820581775c84f28b7033bcc376b9a44f` and the
168 registered current files were verified before editing. No reset or checkout
move occurred. Prior reports, physics/name maps, numerical-contract corrections
and regression-recovery evidence remain the starting record.

Final implementation commit: `05a9fb196b819dbb7310019d4432a6c19271f2c8`.
**Focused GO for Phase 3D-2B-1.** Required focused checks and both final
registration-pointer controls pass. This is focused development acceptance;
complete-regression and release acceptance were outside this phase.

Five existing responsibilities acquire non-GUI owners: `memory_budget`,
`hardware_resources`, `parallel_resources`, `forward_settings`, `material_inputs`.
No calculation engine or scheduler is added. Forward orchestration, channeling,
propagation and multisite scheduling stay at their existing owners. The exact
public `gui.forward_pipeline.calculate` API remains.

## B. Resource ownership and actual state

| Operation/state | Previous owner | Current owner | Consumers and disposition |
|---|---|---|---|
| Memory measurements, limits, estimates/admission, reserve/release | `gui.memory_budget` | `memory_budget` | Current GUI, calculation and test callers import the real owner |
| Reservation dictionary and its reentrant lock | `gui.memory_budget._reservations`, `_lock` | `memory_budget`, one dictionary and one lock | Every request, including pinned kernels, reaches these same globals |
| Hardware/CPU topology and snapshots | `gui.hardware_resources` | `hardware_resources` | Uses the common memory measurement service and unchanged CPU logic/cache |
| BLAS introspection and serialized thread control | `gui.parallel_resources` | `parallel_resources` | One `_blas_control_lock`; original introspection, cancellation and restoration |
| Worker planning, admitted allocation and memory contributors | `gui.parallel_resources` | `parallel_resources` | Same Auto/Manual requests, limits, thresholds and diagnostics |
| Old kernel import of `reserve_memory` | `gui.memory_budget` | Minimal import adapter retained there | Four concrete authenticated kernel consumers; no state or calculation body in adapter |
| Unused legacy preview formatter | `gui.parallel_resources.preview_text` | Removed | No maintained consumer found; not a scientific reference or reason to preserve a facade |

### Why the kernel imports remain

The exact numerical source guard checks complete current kernel files against
the immutable pre-refactor identities, including imports. Current-source
registration for ordinary reviewed files and historical numerical identity are
different mechanisms; updating the former does not authorize changing the
latter. Altering the two strictly pinned kernels' import lines would require
repinning full numerical source, which is not justified for a namespace change.

No import or other byte is changed in `double_channeling.py`,
`multislice_double_channeling.py`, `multislice_reference.py` or
`projected_potential.py` (compared with the starting source after line-ending
normalization). The first two retain their strict kernel pins, and all historical
kernel/data identities and archives remain unchanged.

Their only needed old import is `reserve_memory`. The existing GUI module now
imports that exact function from the real owner; it defines no wrapper function,
lock, registry, admission formula or policy. This adapter serves those four
identified scientific consumers. It does not make their reverse edges disappear
and is not counted as doing so. All other maintained consumers use the non-GUI
owner directly. No module aliasing, string imports or hidden dependency registry
is used.

The real resource module owns all state and all implementation. The adapter and
the two eager kernel imports must have identical function-object identity; the
function's globals identify the same dictionary/lock. Nested BW/MS reservations
must be visible to admission and must release to an empty registry. The lazy
imports in the other two unchanged consumers resolve to that same adapter.

The complete moved memory/hardware/policy executable ASTs match their previous
implementations apart from imports and removal of the unused display formatter.
Budget constants, process RSS/commit accounting, 50% headroom guards, peak-array
estimates, worker admission, BLAS restrictions, Windows executor locking,
cancellation and error messages are unchanged. No second resource manager exists.

## C. Scientific settings

| Responsibility | Current owner and compatibility |
|---|---|
| Historical Ni preset and common stored numerical/detector/resource fields | `forward_settings.NiForwardSettings` |
| Existing grouped calculation record | `forward_settings.MultiSiteForwardSettings`, still derived from `NiForwardSettings` |
| Explicit imported source identity/element/frame/selection fields | `material_inputs.ImportedSettings`, still derived from `NiForwardSettings` |
| Source-backed Manual/Atomic/XMCD provider declaration | `material_inputs.ProviderSettings`, still derived from `ImportedSettings` |
| Source declaration, checksum/material validation and provider preparation | Existing `mdff_providers`; imports the same canonical record classes |
| Accepted/draft GUI editing and project reconstruction | Existing GUI/editor/project modules, consuming those records |

Numerical/detector/resource controls include grids, depths, slice spacing,
solver/channeling selection, apertures, energy/angular sampling, worker requests,
memory modes and the optional accepted allocation. Source-backed inputs also
record element/core edge, original checksum, site selection, pair/frame and
provider declaration. Historical Ni inputs retain their explicit Ni source,
edge defaults, atom-model default factory and material-specific parameters.

This moves the existing hierarchy, not a parallel generic schema. Field names,
order, defaults, constructor parameters, `asdict` layout and default factories
remain. The calculation-budget property still distinguishes the remembered
Manual budget from an accepted allocation and now resolves through the real
non-GUI memory owner. Existing loader interpretations of missing energy,
angular/resource fields and legacy Atomic peaks are unchanged.

Runtime dispatch uses `isinstance` against `ImportedSettings`/`ProviderSettings`;
providers, editors, loaders and calculations all import the same definitions.
The Python `__module__` changes to the actual owner; no duplicate old classes are
created. Supported projects use JSON fields and NPZ with pickle disabled, not
Python module paths. No supported pickled-settings contract was identified.
Saved class names and semantic keys continue reconstructing the intended record.

Inherited Ni storage fields are not a claim of general-material Ni physics. The
explicit source declaration selects a provider; empty/invalid non-Ni inputs
still reject rather than selecting Ni. Removing that historical inheritance is
a distinct material-independent schema cleanup, deferred here. No new material,
magnetic, sampling or resource default is inferred.

No further settings extraction is required to unblock the next phase: the
records and their resource-budget accessor now import without the GUI package.
Separating common numerical fields from inherited Ni preset fields could improve
the schema later, but would require a separate compatibility design and is not
part of this ownership change.

### Interface disposition

| Former/current interface | Decision | Identified consumers and reason |
|---|---|---|
| `gui.forward_settings` and `gui.material_inputs` | Removed; current callers migrated to root owners | Providers, project loaders, editors, maintained scripts and tests use the same four canonical classes; no supported old module-path serialization was found |
| `gui.hardware_resources` and `gui.parallel_resources` | Removed; current callers migrated to root owners | GUI preflight/worker controls, engine planning, acceptance tools and resource tests; no independent old implementation retained |
| `gui.memory_budget.reserve_memory` | Retained as one direct import | Four unchanged kernel consumers listed above; two enforce immutable complete-source identities |
| Other old `gui.memory_budget` names | Removed from that module; current consumers migrated | No identified consumer needs these old paths |
| `gui.parallel_resources.preview_text` | Removed | Unused presentation formatter, with no maintained consumer |
| `gui.forward_pipeline.calculate` | Retained unchanged | Current documented public calculation API, GUI run workflows and headless scientific tests; engine extraction is deferred |

Historical reference implementations and their archived import translation are
validation consumers, not additional production calculation routes. They remain
independent scientific evidence.

## D. Dependency and complexity measurements

The established audit script counts tracked/current `src/**/*.py` once, uses
AST imports including literal deferred imports, and reports distinct directed
module edges and strongly connected components. Token-based noncomment lines
include strings; the source measure additionally removes formal module/class/
function docstrings. These are the Phase 3D-2A definitions, not new baselines.

| Metric | Before | After | Absolute change | Change |
|---|---:|---:|---:|---:|
| Production Python files | 109 | 110 | +1 | +0.92% |
| GUI Python files | 60 | 56 | -4 | -6.67% |
| Non-GUI Python files | 49 | 54 | +5 | +10.20% |
| Physical Python lines | 19,571 | 19,567 | -4 | -0.02% |
| Nonblank, noncomment lines, including docstrings | 17,482 | 17,478 | -4 | -0.02% |
| Source lines excluding formal docstrings | 16,527 | 16,517 | -10 | -0.06% |
| Distinct internal import edges | 493 | 494 | +1 | +0.20% |
| Cyclic groups | 4 | 4 | +0 | +0.00% |
| Modules in cycles | 14 | 14 | +0 | +0.00% |
| Largest SCC | 5 | 5 | +0 | +0.00% |
| Non-GUI to GUI edges | 8 | 6 | -2 | -25.00% |

The net extra file is the necessary pinned-kernel import adapter; four old GUI
owners disappear and all five real owners move outside GUI. Total imports rise
by one because that adapter imports the true owner. The ten-line source reduction
comes from removing an unused formatter while retaining the small adapter.
This is a responsibility/dependency improvement, not substantial code shrinkage.
No duplicated scientific algorithm is removed in this phase, and the four
forward-engine modules are not structurally simplified.

All five extracted owners have **zero GUI import targets**. The two removed
reverse edges are `mdff_providers -> gui.forward_settings` and
`mdff_providers -> gui.material_inputs`; providers now use the canonical records.
Four adapter edges remain visible and counted.

| Retained reverse edge | Reason |
|---|---|
| `__main__ -> gui` | Desktop entry point |
| `double_channeling -> gui.memory_budget` | Unchanged authenticated kernel import; direct state-free adapter |
| `multisite_double_channeling -> gui.channeling` | Execution extraction deferred to Phase 3D-2B-2 |
| `multislice_double_channeling -> gui.memory_budget` | Unchanged authenticated kernel import; direct state-free adapter |
| `multislice_reference -> gui.memory_budget` | Unchanged authenticated kernel import; direct state-free adapter |
| `projected_potential -> gui.memory_budget` | Unchanged authenticated kernel import; direct state-free adapter |

The four SCC memberships are unchanged:

| Size | Members |
|---:|---|
| 5 | `gui.app`, `gui.cancellation_acceptance`, `gui.desktop_acceptance`, `gui.parallel_acceptance`, `gui.unified_elastic_acceptance` |
| 3 | `atomic_ionization`, `imported_mdff`, `manual_l23` |
| 3 | `elastic_providers`, `legacy_atomic_factors`, `scattering` |
| 3 | `gui.multisite_project`, `gui.project_configuration`, `gui.project_io` |

### Complete literal import-edge changes

These are physical source graph changes, including owner moves. Rows list
independent removed/added target sets for each consumer; they do not assert
algorithmic simplification from renaming. No dynamic imports were introduced.

| Consumer | Removed targets | Added targets |
|---|---|---|
| `forward_settings` | ? | `historical_ni`, `memory_budget`, `provenance` |
| `gui.app` | `gui.forward_settings` | `forward_settings` |
| `gui.calculation_controls` | `gui.forward_settings`, `gui.material_inputs`, `gui.parallel_resources` | `forward_settings`, `material_inputs`, `parallel_resources` |
| `gui.calculation_worker` | `gui.parallel_resources` | `parallel_resources` |
| `gui.cancellation_acceptance` | `gui.memory_budget` | `memory_budget` |
| `gui.channeling` | `gui.hardware_resources`, `gui.parallel_resources` | `hardware_resources`, `parallel_resources` |
| `gui.compute_resources` | `gui.hardware_resources`, `gui.memory_budget`, `gui.parallel_resources` | `hardware_resources`, `memory_budget`, `parallel_resources` |
| `gui.desktop_acceptance` | `gui.parallel_resources` | `parallel_resources` |
| `gui.forward_pipeline` | `gui.forward_settings`, `gui.memory_budget`, `gui.parallel_resources` | `forward_settings`, `memory_budget`, `parallel_resources` |
| `gui.forward_settings` | `gui.memory_budget`, `historical_ni`, `provenance` | ? |
| `gui.group_mdff` | `gui.forward_settings`, `gui.material_inputs` | `forward_settings`, `material_inputs` |
| `gui.hardware_resources` | `gui.memory_budget` | ? |
| `gui.material_inputs` | `gui.forward_settings` | ? |
| `gui.memory_budget` | ? | `memory_budget` |
| `gui.multisite_run` | `gui.forward_settings` | `forward_settings` |
| `gui.parallel_acceptance` | `gui.parallel_resources` | `parallel_resources` |
| `gui.parallel_resources` | `cancellation`, `gui.hardware_resources` | ? |
| `gui.project_configuration` | `gui.material_inputs` | `material_inputs` |
| `gui.project_io` | `gui.forward_settings`, `gui.material_inputs` | `forward_settings`, `material_inputs` |
| `gui.project_session` | `gui.forward_settings`, `gui.material_inputs` | `forward_settings`, `material_inputs` |
| `gui.propagation` | `gui.hardware_resources`, `gui.memory_budget`, `gui.parallel_resources` | `hardware_resources`, `memory_budget`, `parallel_resources` |
| `gui.provider_ui` | `gui.forward_settings`, `gui.material_inputs` | `forward_settings`, `material_inputs` |
| `gui.results_browser` | `gui.forward_settings`, `gui.memory_budget` | `forward_settings`, `memory_budget` |
| `gui.scientific_acceptance` | `gui.forward_settings` | `forward_settings` |
| `gui.site_group_editor` | `gui.material_inputs` | `material_inputs` |
| `gui.xmcd_preview` | `gui.forward_settings` | `forward_settings` |
| `hardware_resources` | ? | `memory_budget` |
| `material_inputs` | ? | `forward_settings` |
| `mdff_providers` | `gui.forward_settings`, `gui.material_inputs` | `forward_settings`, `material_inputs` |
| `parallel_resources` | ? | `cancellation`, `hardware_resources` |

## E. Verification and source authentication

Logs, exact argv/environment, HEAD/status, working directory, owned PID,
duration and exit status are retained under ignored `build/phase3d2b1/`.
Normally completed pytest runs also have JUnit XML. Interrupted evidence remains.

| Invocation | Outcome | Seconds |
|---|---|---:|
| `resources` | 69 passed, 1 skipped, 4 failed | 108.453 |
| `resource-import-fix` | 4 passed, 0 skipped | 50.844 |
| `settings-headless` | 54 passed, 0 skipped | 83.265 |
| `headless-calculations` | 8 passed, 0 skipped | 82.047 |
| `science` | 54 passed, 0 skipped | 137.953 |
| `exact` | 22 cases / 2,294 arrays exactly equal; metadata/metrics equal | 52.984 |
| `workflows` | Timed out at 1,200 s; 75 pass / 3 skip progress marks; no assertion failure | 1200.891 |
| `workflows-remainder` | 48 passed, 5 skipped | 355.422 |
| `authentication` | Stopped by agent after 33 pass marks to focus an overbroad legacy mutation selection | 231.843 |
| `authentication-focused` | 42 passed, 1 skipped | 201.719 |
| `final-map` | 2 passed, 0 skipped | 30.031 |

**Combined focused pytest coverage: 349 passed, 8 existing skips; 357 distinct cases, no unresolved failure/error.**
This is combined focused coverage, not a complete regression or a single clean
invocation. The stopped broad authentication progress is excluded from the
total. Overlapping Cr serial/parallel checks and final-map rechecks count once.
The exact driver is reported separately, not added to the pytest count.

The first resource selection exposed four stale direct module imports in tests.
Those imports were migrated to the canonical owner without changing assertions;
exactly those four failures passed on recheck.

The broader GUI/project selection covers **122 passed / six existing skips**
across 128 distinct cases. Its first invocation reached a bounded deadline
while making progress; the owned payload and descendants were terminated.
Its 75 lifecycle records identify 74 passed cases and one runtime fixture skip;
all 75 records were excluded from the continuation. One completed pure case
without a GUI lifecycle record was rechecked for complete evidence and counted
once. Initial native marker skips were encountered again and count once.
The continuation passed 48 cases and skipped five. No JUnit XML was generated
by the timed-out run; its progress and lifecycle evidence are retained.

The six GUI-selection skips are two opt-in native Windows checks, one optional
solver saved-result fixture, two automatic/manual saved-project fixtures and
one legacy manual-settings fixture. Explicit Save/Open, missing/changed-source
handling, result/settings restoration, selected-run export, Global/Local/group
Apply/Cancel, magnetization, Fe validation and single-element workflows passed.
Optional fixture cases are not reported as successful calculations.

All six corrected numerical contracts passed in `science`:

- `test_bw_unchanged_and_depth_cancel[numerical]`
- `test_full_spectrum_unchanged[bloch]` and `[both]`
- `test_bcc_cr_independent_events_and_symmetry[unequal-mdff-double-bloch]`
- `test_original_ni_all_numeric_arrays_exact[double-xmcd]` and `[double-atomic]`

No comparison budget, weak-signal parent scale, expected array, undefined mask
or lossless serialization equality changed. The selection also passes
independent Cr event/reversal/parity, Ni quadrature/multisite, detector/MDFF,
roundoff negative, cancellation and strict physics-source controls, plus real
Cr Auto/Manual serial/parallel preservation.

The eight real headless cases are Ni and explicit synthetic BCC Cr, each with
BW/FFT and Single/Double Channeling, through the unchanged canonical API.

The unchanged `build/regression-recovery/verify_equivalence.py` is executed
with named imports translated in memory by the existing `reference_imports`
helper. Its file, cases, arrays and assertions are unchanged: all 2,294 arrays
match the independent source `cdb8836388c5ccc5ae7a614b47894c0ab158a824` exactly.
Separately printed older-source deltas (1.3010426069826053e-18 XMCD and
2.6469779601696886e-23 Atomic) remain previous evidence, not new differences.

The existing current source map now covers **170 files**, previously 168.
Relocation declarations and reviewed entries follow the actual owners. Every
existing historical/previous-source payload, historical manifest/archive and
immutable kernel/data pin remains intact. All four kernel consumers of the
memory adapter are source-identical after line-ending normalization. Complete
executable AST comparisons of the five moved modules and four engine modules
pass apart from named imports, the documented settings doc reference and
unused formatter removal. There is no new hash framework or scientific baseline.

Existing mutation controls reject changes to all five extracted owners and
the retained adapter. Historical/unit/schema, offline/no-Git/no-process and
Windows packaging metadata controls pass. The only authentication skip is the
optional external 160-array evidence; this does not replace the successful
required 2,294-array comparison.

The new fresh-process checks prohibit PySide/PyQt, Qt backends and presentation
imports. Fully independent settings/resource tests also prohibit the entire GUI
namespace and actually construct/serialize settings, prepare an explicit Fe
provider, measure memory, reserve/release, reject invalid requests and restore
state after cancellation/failure. The pinned-kernel bridge check permits only
the GUI namespace and its single memory adapter, then verifies actual shared
function/global-state identity and nested request accounting.

The existing Manual/Atomic/XMCD provider subprocess tests are strengthened to
reject the entire GUI namespace while preserving their tensor, direction,
source-identity and invalid-input assertions. No offscreen Qt setup substitutes
for those import restrictions.

### Exact verification commands

Commands ran in the worktree in A with Python 3.11.17, NumPy 2.4.6 and SciPy
1.17.1. These shared PowerShell variables/environment reproduce the exact argv:

```powershell
$py = 'C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe'
$e = 'C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\build\phase3d2b1'
$temp = 'C:\Users\peng863\EMCD-Sim\build\nc-tmp'
$env:PYTHONPATH = 'C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\src;C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\tests'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONHASHSEED = '0'
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:QT_QPA_PLATFORM = 'offscreen'
$env:TEMP = $temp
$env:TMP = $temp
```

Headless child tests remove the Qt platform setting and reject GUI/Qt imports.

**resources**

```powershell
Remove-Item Env:\EMCD_TEST_LIFECYCLE_LOG -ErrorAction SilentlyContinue
& $py -u -m pytest `
  'tests/test_memory_budget.py' `
  'tests/test_parallel_resources.py' `
  'tests/test_compute_resources.py' `
  'tests/test_compute_execution.py' `
  'tests/test_bloch_memory.py' `
  '-q' `
  '--tb=short' `
  "--basetemp=$temp\resources-4df0fbd2" `
  '-p' `
  'no:cacheprovider' `
  "--junitxml=$e\resources.xml"
```

**resource-import-fix**

```powershell
Remove-Item Env:\EMCD_TEST_LIFECYCLE_LOG -ErrorAction SilentlyContinue
& $py -u -m pytest `
  'tests/test_parallel_resources.py::test_backend_unknown_is_not_guessed_from_cpu' `
  'tests/test_parallel_resources.py::test_introspection_is_read_only_and_queries_actual_threads' `
  'tests/test_parallel_resources.py::test_memory_uses_actual_manual_concurrency_and_rejects_without_reduction' `
  'tests/test_parallel_resources.py::test_gui_defaults_worker_independence_and_blocked_run' `
  '-q' `
  '--tb=short' `
  "--basetemp=$temp\resource-import-fix-555381d5" `
  '-p' `
  'no:cacheprovider' `
  "--junitxml=$e\resource-import-fix.xml"
```

**settings-headless**

```powershell
Remove-Item Env:\EMCD_TEST_LIFECYCLE_LOG -ErrorAction SilentlyContinue
& $py -u -m pytest `
  'tests/test_headless_settings_resources.py' `
  'tests/test_unified_mdff_providers.py' `
  'tests/test_multisite_configuration.py' `
  'tests/test_calculation_api.py' `
  '-q' `
  '--tb=short' `
  "--basetemp=$temp\settings-headless-792154fd" `
  '-p' `
  'no:cacheprovider' `
  "--junitxml=$e\settings-headless.xml"
```

**headless-calculations**

```powershell
Remove-Item Env:\EMCD_TEST_LIFECYCLE_LOG -ErrorAction SilentlyContinue
& $py -u -m pytest `
  'tests/test_headless_calculation.py' `
  '-q' `
  '--tb=short' `
  "--basetemp=$temp\headless-calculations-a3c1b482" `
  '-p' `
  'no:cacheprovider' `
  "--junitxml=$e\headless-calculations.xml"
```

**science**

```powershell
Remove-Item Env:\EMCD_TEST_LIFECYCLE_LOG -ErrorAction SilentlyContinue
& $py -u -m pytest `
  'tests/test_double_cancellation.py' `
  'tests/test_single_element_ni_compatibility.py::test_original_ni_all_numeric_arrays_exact[double-xmcd]' `
  'tests/test_single_element_ni_compatibility.py::test_original_ni_all_numeric_arrays_exact[double-atomic]' `
  'tests/test_multisite_scientific_validation.py' `
  'tests/test_numerical_roundoff.py' `
  'tests/test_detector_signals.py' `
  'tests/test_mdff_tensor.py' `
  'tests/test_physics_source_guard.py' `
  'tests/test_compute_execution.py::test_cr_auto_and_manual_preserve_existing_serial_intensities' `
  '-q' `
  '--tb=short' `
  "--basetemp=$temp\science-f1d8ad52" `
  '-p' `
  'no:cacheprovider' `
  "--junitxml=$e\science.xml"
```

**exact**

The exact `-c` argument (`$code`) is:

```python
from pathlib import Path
from reference_imports import relocate_reference_imports
p=Path('build/regression-recovery/verify_equivalence.py').resolve()
exec(compile(relocate_reference_imports(p.read_text(encoding='utf-8-sig')),str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
```

```powershell
& $py -u -B -c $code
```

**workflows**

```powershell
$env:EMCD_TEST_LIFECYCLE_LOG = "$e\workflows-lifecycle.jsonl"
& $py -u -m pytest `
  'tests/test_material_mdff_workflow.py' `
  'tests/test_local_mdff_workflow.py' `
  'tests/test_material_magnetization.py' `
  'tests/test_group_mdff.py' `
  'tests/test_project_workflow.py' `
  'tests/test_run_selection_restoration.py' `
  'tests/test_solver_settings_ui.py' `
  'tests/test_multisite_result_persistence.py' `
  'tests/test_multisite_result_selection.py::test_gui_switching_means_comparison_elements_and_methods_without_recalculation' `
  'tests/test_multisite_result_export.py::test_gui_exports_selected_method_comparison_without_recalculation' `
  'tests/test_bcc_fe_cif_gui.py' `
  'tests/test_single_element_gui.py' `
  'tests/test_gui_double_channeling.py::test_saved_model_label_and_restored_controls' `
  'tests/test_automatic_numerical_settings.py' `
  '-q' `
  '--tb=short' `
  "--basetemp=$temp\workflows-1a8f9509" `
  '-p' `
  'no:cacheprovider' `
  "--junitxml=$e\workflows.xml"
```

**workflows-remainder**

```powershell
$env:EMCD_TEST_LIFECYCLE_LOG = "$e\workflows-remainder-lifecycle.jsonl"
$completed = @(Get-Content "$e\workflows-lifecycle.jsonl" | ForEach-Object { "--deselect=" + ($_ | ConvertFrom-Json).test })
& $py -u -m pytest `
  'tests/test_material_mdff_workflow.py' `
  'tests/test_local_mdff_workflow.py' `
  'tests/test_material_magnetization.py' `
  'tests/test_group_mdff.py' `
  'tests/test_project_workflow.py' `
  'tests/test_run_selection_restoration.py' `
  'tests/test_solver_settings_ui.py' `
  'tests/test_multisite_result_persistence.py' `
  'tests/test_multisite_result_selection.py::test_gui_switching_means_comparison_elements_and_methods_without_recalculation' `
  'tests/test_multisite_result_export.py::test_gui_exports_selected_method_comparison_without_recalculation' `
  'tests/test_bcc_fe_cif_gui.py' `
  'tests/test_single_element_gui.py' `
  'tests/test_gui_double_channeling.py::test_saved_model_label_and_restored_controls' `
  'tests/test_automatic_numerical_settings.py' `
  '-q' `
  '--tb=short' `
  @completed `
  "--basetemp=$temp\workflows-remainder-a867996f" `
  '-p' `
  'no:cacheprovider' `
  "--junitxml=$e\workflows-remainder.xml"
```

**authentication**

```powershell
Remove-Item Env:\EMCD_TEST_LIFECYCLE_LOG -ErrorAction SilentlyContinue
& $py -u -m pytest `
  'tests/test_mdff_usability_source_scope.py' `
  'tests/test_unit_labels.py' `
  'tests/test_bcc_fe_gui_source_scope.py' `
  'tests/test_mdff_editor_source_scope.py::test_offline_no_git_network_or_snapshot_execution' `
  'tests/test_windows_build_metadata.py' `
  '-q' `
  '--tb=short' `
  "--basetemp=$temp\authentication-65721ad4" `
  '-p' `
  'no:cacheprovider' `
  "--junitxml=$e\authentication.xml"
```

**authentication-focused**

```powershell
Remove-Item Env:\EMCD_TEST_LIFECYCLE_LOG -ErrorAction SilentlyContinue
& $py -u -m pytest `
  'tests/test_mdff_usability_source_scope.py::test_positive_and_independent_historical_queries' `
  'tests/test_mdff_usability_source_scope.py::test_each_candidate_mutation[src/emcd_sim/memory_budget.py]' `
  'tests/test_mdff_usability_source_scope.py::test_each_candidate_mutation[src/emcd_sim/hardware_resources.py]' `
  'tests/test_mdff_usability_source_scope.py::test_each_candidate_mutation[src/emcd_sim/parallel_resources.py]' `
  'tests/test_mdff_usability_source_scope.py::test_each_candidate_mutation[src/emcd_sim/forward_settings.py]' `
  'tests/test_mdff_usability_source_scope.py::test_each_candidate_mutation[src/emcd_sim/material_inputs.py]' `
  'tests/test_mdff_usability_source_scope.py::test_each_candidate_mutation[src/emcd_sim/gui/memory_budget.py]' `
  'tests/test_mdff_usability_source_scope.py::test_pinned_declaration_and_archive_mutation[tests/fixtures/physics_readability_current_v1.json]' `
  'tests/test_mdff_usability_source_scope.py::test_registration_support_mutation[tests/conftest.py]' `
  'tests/test_mdff_usability_source_scope.py::test_registration_support_mutation[tests/test_mdff_usability_source_scope.py]' `
  'tests/test_mdff_usability_source_scope.py::test_historical_evidence_mutation' `
  'tests/test_mdff_usability_source_scope.py::test_parent_bytes_are_not_valid_current_overrides' `
  'tests/test_unit_labels.py' `
  'tests/test_mdff_editor_source_scope.py::test_offline_no_git_network_or_snapshot_execution' `
  'tests/test_windows_build_metadata.py' `
  '-q' `
  '--tb=short' `
  "--basetemp=$temp\authentication-focused-838ec824" `
  '-p' `
  'no:cacheprovider' `
  "--junitxml=$e\authentication-focused.xml"
```

**final-map**

```powershell
Remove-Item Env:\EMCD_TEST_LIFECYCLE_LOG -ErrorAction SilentlyContinue
& $py -u -m pytest `
  'tests/test_mdff_usability_source_scope.py::test_positive_and_independent_historical_queries' `
  'tests/test_mdff_usability_source_scope.py::test_pinned_declaration_and_archive_mutation[tests/fixtures/physics_readability_current_v1.json]' `
  '-q' `
  '--tb=short' `
  "--basetemp=$temp\final-map-a1b1f230" `
  '-p' `
  'no:cacheprovider' `
  "--junitxml=$e\final-map.xml"
```

## F. Phase 3D-2B-2 handoff

The exact remaining GUI targets of the four engine modules are:

| Module | GUI dependency targets still present |
|---|---|
| `gui.propagation` | None; its own namespace is the remaining GUI ownership |
| `gui.channeling` | `gui.propagation` |
| `gui.multisite_integration` | `gui.propagation` |
| `gui.forward_pipeline` | `gui.channeling`, `gui.multisite_integration`, `gui.propagation` |

1. Scientific settings, hardware measurements, memory state/admission and worker
   policy now have non-GUI owners. Editors and schema interpretation remain GUI
   responsibilities; do not merge unapplied drafts with accepted inputs.
2. Move `propagation` planning/estimates first: its scientific geometry,
   diagnostics and resource dependencies already have non-GUI owners. Move
   `channeling` next and redirect its planning-bound imports to that owner.
   Preserve the single Windows BW executor guard and original callback,
   checkpoint and resource behavior. The two mathematical methods stay distinct.
3. Migrate multisite integration with its existing bounded energy/pixel scheduling,
   independent-site normalization and source/group association. Do not merge it
   with uniform scheduling merely because kernels are shared.
4. Move forward orchestration last. The documented GUI-namespaced calculation
   API can remain a minimal adapter for its concrete public/GUI consumers while
   delegating all calculation to one scientific implementation. Do not add a
   competing production API or retain unrelated obsolete private aliases.
5. Four kernel imports still reach the memory adapter. Two consumers,
   `double_channeling` and `multislice_double_channeling`, have immutable
   whole-file pins; changing those imports needs a separately justified
   source-contract decision. The registered reference/potential consumers
   `multislice_reference` and `projected_potential` are also left unchanged here;
   their current import migrations can be reviewed separately while preserving
   the historical references. The adapter has no duplicate state or calculation.
6. Redirect `multisite_double_channeling` from `gui.channeling` when channeling
   moves. The CLI launcher may still load the desktop GUI intentionally; that
   application entry edge is separate from headless numerical execution.

No forward-engine migration, new physics, complete regression, Windows EXE build,
version bump, push, merge, tag, publication or installed-beta replacement is
performed in this phase.
