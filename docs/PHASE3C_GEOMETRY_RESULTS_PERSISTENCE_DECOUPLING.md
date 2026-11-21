# Phase 3C: geometry, scientific results and persistence

Date: 2026-11-20. Final verification and decision are recorded below.

## Source identity and scope

Working directory and Git worktree root:
`C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute`.
Branch: `refactor/physics-readability`.
Starting commit: `a4315dc379db5c7f71acdccb3aafd266bd05b937`; Git status was clean.
Final application and maintained-test implementation commit:
`cb20b718b26a75368b21b1151622311717e06704`.
The final registration/report successor is identified in the completion response
and Git history. No application changes follow this verified implementation.

The Phase 3A/3B reports, physics/name maps, regression recovery and numerical
contract corrections remain the prior evidence. The earlier 1,768 distinct
tests had combined passing coverage, not one clean full-suite invocation.
No complete regression or release acceptance is performed here.
The scientific comparison source remains the actual pre-refactor commit
`cdb8836388c5ccc5ae7a614b47894c0ab158a824`.

This phase changes ownership and dependencies, not the scientific engine.
The canonical `emcd_sim.gui.forward_pipeline.calculate(structure, settings,
cfg, sites=...)` API, arguments, supported physical inputs and errors remain.
Ni-derived record classes/defaults, MDFF services, numerical kernels,
admission/scheduling and cancellation are outside the implementation changes.

## Original dependency diagnosis

The reused AST measurement reproduces all supplied starting metrics, including
482 literal internal edges and the 11-module SCC. Its exact internal edges
and their roles are:

| Source | Targets inside the component | Responsibility |
|---|---|---|
| `channeling` | `propagation` | Numerical execution/planning. |
| `forward_results` | `geometry`, `project_io`, `propagation`, `results` | Scientific geometry plus misplaced serialization/rendering exports. |
| `geometry` | `project_io` | Preview requested a neutral snapshot from a persistence owner. |
| `multisite_export` | `multisite_results` | Stored data selection and scientific export metadata. |
| `multisite_project` | `multisite_results`, `project_configuration`, `project_io` | Group array layout, configuration codec, source attachment and restoration. |
| `multisite_results` | `results` | One rendering dispatcher in an otherwise nonvisual data module. |
| `multisite_results_controls` | `multisite_export`, `multisite_results` | Controls read quantity definitions from an export owner and result selection data. |
| `project_configuration` | `project_io` | Schema conversion, path/checksum and transactional file helpers. |
| `project_io` | `forward_results`, `geometry`, `multisite_project`, `project_configuration` | Metrics, structure/geometry types, grouped result layout and editable configuration persistence. |
| `propagation` | `channeling`, `forward_results`, `geometry`, `results` | Execution, comparison metrics and geometry, plus misplaced image/comparison export. |
| `results` | `forward_results`, `multisite_export`, `multisite_results`, `multisite_results_controls`, `project_io`, `propagation` | Qt result presentation, export actions, Save and method labels. |

Names in that table are under `emcd_sim.gui`. The full graph includes deferred
imports and is recorded under `build/phase3c/`. Not every apparent relationship
was direct: `project_configuration` did not import a result widget or geometry
module directly at the start. Its return path ran through `project_io`.
The cycle-breaking edges were executable responsibilities, not type-only imports.
Historical schema handling and resource imports were not deleted to improve
the counts.

## Geometry and structure data

`structure_snapshot`, `restore_structure` and `structures_match` move from
`gui.project_io` to the existing `gui.geometry` module. The functions operate
on ASE structures and dictionaries; they do not access project files. Geometry
preview now calls its neutral snapshot owner directly. Project I/O owns reading
and writing that same dictionary, rather than providing geometry services.

Maintained calculation, project/session/collection, browser, script, packaging
and test callers use the neutral owner. Internal project-I/O calls use a module
reference rather than an old public forwarding function. Archived named imports
are translated only by the existing reference-import adapter.

The snapshot/restore/matching bodies retain their existing operations and
tolerances. Species order, cell, fractional coordinates, pbc, occupancy,
source/hash/warnings, crystallographic annotations and stored original-index
arrays retain their prior meanings. The existing richer configuration snapshot
also stores original Cartesian positions and all supported ASE arrays; its
extension stays in configuration persistence. It is intentionally distinct
from the established base result/preview snapshot and is not collapsed into a
new format. No primitive reduction, coordinate normalization or geometry
equation is changed.

Three new fresh-process cases use built-in Ni and existing Fe and inverse-spinel
Fe3O4 CIF fixtures. They construct snapshots, restore base and actual saved
configuration dictionaries, compare orientation/cell data, preserve original
species order, unwrapped Cartesian positions, tags and stored arrays, and
reject empty/reserved-array input. The children prohibit Qt and project-I/O
imports. The existing headless configuration Save/Open check also passes.

This preserves fields already supported by the schema. It does not invent
serialization of arbitrary ASE info/constraints or reconstruct an unstored
ASE Spacegroup object from descriptive text.

## Scientific result and presentation ownership

| Operation | Previous owner | Current owner / reason |
|---|---|---|
| Completed-method selection and BW-minus-MS view (`method_result`) | Qt `results` module | `forward_results`; a scientific array view does not need widgets. Its subtraction order and metadata are unchanged. |
| Plotting, display labels/comparison text and interactive spectral controls | `results` functions plus `multisite_results_controls` | `result_presentation`; presentation consumes completed data. `results.ResultsView` retains widget orchestration. |
| Multi-site panel dispatch (`draw_totals`) | `multisite_results` | `result_presentation.draw_multisite_panel`; the name now reflects selected group/element/total panels rather than only totals. No old alias is retained. |
| Scientific quantity definitions (`DEFINITIONS`) | `multisite_export` | `multisite_results`, beside `SPECTRAL_KEYS`/`QUANTITIES`; both controls and exports consume the same descriptions. |
| Method/full-result/image/comparison export | `forward_results` and `propagation` | `result_export`, alongside existing multi-site CSV export. The old `multisite_export` module is renamed for its broader responsibility. |

`multisite_results` now contains only read-only data selection, existing
scientific transformations and provenance descriptions. Its return dependency
on Qt results is removed. `forward_results` assembles scientific results and
metrics without importing persistence or presentation. `propagation` retains
numerical planning/execution and comparison diagnostics; it no longer imports
Qt plotting to export files.

`result_presentation` replaces the former controls module and owns the existing
renderer functions and `MultisiteSpectraControls`. This is not a GUI rewrite:
the plot/normalization bodies, widget fields, signals and callbacks are retained.
`ResultsView` calls their new owner. Plain matrix/data operations remain at
their existing owners except the relocated unchanged method view.

File exports keep their existing entry-point signatures, advanced/normal
layouts, filenames, component options, scientific units and metadata. Primary
and method-prefixed arrays, mean and independently accumulated weighted-sum
arrays, masks and dimensions are not recomputed using alternative formulas.
The ordinary and advanced exports have different established contracts and
are not merged simply because both write JSON/NPZ files.

No numerical algorithm duplication is claimed removed. The gains are corrected
ownership, one authoritative implementation per operation and elimination of
reverse dependencies. No new result manager, facade, registry or engine is
introduced. There are no production modules at the two retired filenames.

## Persistence and state semantics

Project I/O continues to own existing JSON/NPZ schemas, integrity checks,
transactional Save/Open and historical interpretation. Group result layout
remains in `multisite_project`; editable configuration remains in
`project_configuration`. Result metadata and arrays are restored directly,
without invoking a propagation solver or regenerating stored observables.

| State | Preserved distinction |
|---|---|
| Scientific data | Saved primary/method/group arrays, original weighted sums, masks, dimensions, source and geometry association. |
| Calculation configuration | Existing dataclasses, defaults and historical missing-field interpretation; no Ni schema redesign. |
| Original/effective sources | Saved declarations remain separate from verified portable path overrides and rerun diagnostics. |
| Accepted inputs/drafts | Applied Global/Local Material/MDFF state, inactive editors and unapplied snapshots remain distinct. |
| Display preferences | Plot/control selection consumes result data; it does not become another scientific result implementation. |
| Resource requests/allocation | Remembered requests and mode settings remain separate from runtime resolved allocations and their existing restore rules. |

The new headless result cases use established Cr, Fe3O4 and Fe/Ni stored-result
fixtures with both solver identities. Fresh children prohibit Qt, presentation,
exports and calculation execution while performing real Load/view/Save/Open.
All stored arrays are compared exactly with matching dtypes, shapes and
numeric NaN/Inf masks; scientific metadata and method association are checked.
The existing fixtures include an independently accumulated weighted-sum
last-bit difference, which remains preserved. These are software fixtures,
not claims of predicted or experimental material spectra.

The old helpers were partly nonvisual already. Headless tests establish the
supported boundary and actual operations; they do not imply that every prior
save required a widget or that new physics was implemented.

## Dependency metrics

Measurements reuse the Phase 3B conventions: Git production Python paths;
unique literal internal AST imports, including function-local imports;
resolved relative imports; no implicit package-init, external, self or dynamic
string edges. GUI is a subset of production. Pending intended additions are
included in the worktree measurement and verified against the final committed
tree. P is physical LOC; N excludes blanks/comments; S additionally excludes
formal module/class/function docstrings.

| Metric | Before | After | Change |
|---|---:|---:|---:|
| Production Python files | 107 | 107 | 0 (0.00%) |
| GUI Python files | 62 | 62 | 0 (0.00%) |
| Production P LOC | 19,502 | 19,517 | +15 (+0.08%) |
| Production N LOC | 17,450 | 17,459 | +9 (+0.05%) |
| Production S LOC | 16,506 | 16,512 | +6 (+0.04%) |
| Internal import edges | 482 | 482 | 0 (0.00%) |
| Cyclic dependency groups | 4 | 5 | +1 (+25.00%) |
| Modules in cycles | 22 | 16 | -6 (-27.27%) |
| Largest SCC | 11 | 5 | -6 (-54.55%) |
| Largest remaining group within the former 11-module component | 11 | 3 | -8 (-72.73%) |
| Non-GUI → GUI edges | 8 | 8 | 0 (0.00%) |
| `forward_results`/`propagation` → Qt `results` edges | 2 | 0 | -2 (-100.00%) |
| Geometry → project-I/O edges | 1 | 0 | -1 (-100.00%) |

The remaining component topology is:

```
application / acceptance entry points: 5 modules (unchanged)
elastic providers / scattering:       3 modules (unchanged)
atomic / imported / manual sources:   3 modules (unchanged)
project I/O / configuration / groups: 3 modules
channeling / propagation:            2 modules
```

The former 11-module component splits into 3 and 2; the other six members are
no longer cyclic. Consequently SCC count increases from four to five through
fragmentation, while cyclic membership falls from 22 to 16. No previously
acyclic module becomes cyclic. The largest overall group is the unchanged
five-module application/acceptance group; the largest remaining group from
the old knot has three modules. This is not described as elimination of all
cycles or a reduction in every complexity statistic.

Scientific `forward_results`/`propagation` to Qt `results` dependencies fall
from two to zero. Geometry-to-project-I/O falls from one to zero. The remaining
non-GUI-to-GUI edges are explicit and retained, not hidden with dynamic imports.
The module count stays constant through two responsibility-based owner renames.
`results.py` falls to 310 physical lines; `forward_results.py` to 108;
`propagation.py` to 335; `project_io.py` to 572. The new presentation owner is
472 lines and export owner 197. Project I/O remains oversized; it is not hidden
by a new manager. Total LOC and edge count show no broad size reduction.

## Source authentication, references and provenance

Current-source registration follows the existing reviewed-current mechanism.
The new presentation/export owners contain bodies formerly protected at their
old files and are therefore included in the same closed registration scope.
Without that relocation, changing a moved normalization/export body could evade
the former file's byte check. No new hash gate, frozen numerical baseline or
authentication framework is added. Historical source/kernel/reference pins,
archives and existing prior-source payloads remain unchanged.

The existing historical GUI bridge had concrete imports of the two retired
support filenames. Reference-only support namespaces now extract the unchanged
canonical control class and CSV functions, authenticated against the current
map, with minimal dependency imports. They exist only in the isolated parent
test tree. Authenticated historical protected files and test assertions are not
rewritten. This preserves the five identified legacy Atomic editor contracts
without keeping production compatibility modules or duplicating science.

The existing runtime `implementation_sha256` inventory retains all three
original entries and includes `result_export.py`: comparison-export code was
previously covered through `propagation.py`. Git commit plus a dirty flag does
not identify the bytes of changed uncommitted export code, so dropping that
coverage would lose existing traceability. The digest algorithm and metadata
field remain the same; no acceptance gate is added. Stored old provenance
dictionaries are read as recorded, not relabeled. No public version or release
inventory/artifact is replaced.

## Verification evidence

Evidence is under `build/phase3c/`: logs, JUnit XML and `-run.json` records with
exact arguments, environment, source HEAD/status, owned PID, exit and duration.
The established Windows Python uses short main-repository `build/nc-tmp` paths,
Qt offscreen, deterministic hash seed and one BLAS/OMP thread. Searches/tests
run sequentially. Exact commands and final results are recorded below after
the broader affected group and current-source controls finish.

The completed scientific group passes all six corrected comparisons plus
multisite invariants, MDFF/reference/API and strict kernel mutation controls.
The unchanged driver passes 22 cases / 2,294 arrays exactly against the actual
pre-refactor source. Original reference arrays and floating-point contracts
are untouched. The already-documented older-reference notices are
not new mismatches.

Incremental checks caught two import-scope regressions during extraction:
the restoration module's geometry alias was initially local to another
function, and widget layout imports originally below the plotting functions
were missed. Both were corrected without changing equations or assertions;
affected persistence and construction checks were rerun. Initial failure
records are retained rather than presented as passing runs.

The broader group ran once: 189 passed, three skipped, five failed. The five
failures stopped before scientific comparisons: one test still expected a
geometry helper from a project-I/O wildcard import, and four renderer spies
targeted the former plotting namespace. The explicit geometry import and spy
targets were migrated without changing their assertions. All five cases pass
on the targeted recheck. The 189 already-passing cases were not restarted.

After preserving the moved export's provenance coverage and correcting widget
imports, the unchanged exact driver runs again on the final application tree:
22 cases / all 2,294 arrays remain exactly equal. No numerical discrepancy,
reference regeneration or tolerance adjustment occurs.

The final registration group passes with 124 tests and one optional-evidence
skip, including moved-owner mutations, unchanged historical/kernel identity,
no-Git/no-process/no-network authentication and source packaging metadata.

### Executed checks and outcomes

Durations are launcher wall seconds. Initial failure evidence remains in place.

| Evidence prefix | Result | Seconds |
|---|---|---:|
| `geometry` | 4 passed: three fresh structure cases and existing headless configuration Save/Open | 11.703 |
| `results` | 2 passed, 11 failed at the same missing geometry binding | 20.157 |
| `results-fix` | 13 passed after that application import-scope fix | 27.297 |
| `science` | 65 passed; four unrelated Phase 3B provider headless cases deselected | 51.157 |
| `exact` | 22 cases / 2,294 arrays exactly equal | 15.453 |
| `metadata-bridge` | 7 passed, 1 existing skip; one GUI setup error plus its cleanup error | 42.657 |
| `bridge-fix` | The failed construction/registered historical-current contract passed | 54.203 |
| `workflows` | 189 passed, 3 existing skips, 5 stale test-consumer failures | 752.859 |
| `consumer-fix` | All five affected cases passed after import/spy migration | 9.797 |
| `exact-final` | Final application tree: 22 cases / all 2,294 arrays exactly equal | 16.407 |
| `registration` | 124 passed, 1 existing optional-evidence skip | 161.516 |
| `final-map` | 2 already-counted authentication/mutation cases rechecked after recording the implementation commit | 29.234 |

Across these pytest invocations, **413 distinct cases have 408 passes and five
existing skips**, after the documented affected rechecks. No unresolved failure
or error remains. The exact driver is additional evidence, not a pytest count.
The final-map checks run at implementation commit
`cb20b718b26a75368b21b1151622311717e06704`; earlier launch records identify
starting HEAD `a4315dc` and the pending changes that became that implementation.
Only registration/report metadata changes afterward, so completed numerical
and GUI checks are not restarted for the final source-identity update.
The five skips are:

- `test_old_project_roundtrip_preserves_arrays_and_provenance`: optional
  historical saved project unavailable.
- `test_native_windows_group_element_comparison`: explicit native-only check.
- `test_native_windows_comparison_csv_export`: explicit native-only check.
- `test_native_windows_project_history_and_menus`: explicit native-only check.
- `test_unit_changes_give_identical_bw_ms_single_double_numerical_arrays`:
  external 160-array evidence unavailable (`EMCD_UNIT_IDENTITY_DIRECTORY`).

These are not claimed as passes. Existing historical Save/Open coverage in
the other project, result and restoration cases passes; the unavailable
optional fixture is not reconstructed or replaced.

The six corrected scientific cases are:

```
test_double_cancellation.py::test_bw_unchanged_and_depth_cancel[numerical]
test_double_cancellation.py::test_full_spectrum_unchanged[bloch]
test_double_cancellation.py::test_full_spectrum_unchanged[both]
test_multisite_scientific_validation.py::test_bcc_cr_independent_events_and_symmetry[unequal-mdff-double-bloch]
test_single_element_ni_compatibility.py::test_original_ni_all_numeric_arrays_exact[double-xmcd]
test_single_element_ni_compatibility.py::test_original_ni_all_numeric_arrays_exact[double-atomic]
```

The full multisite scientific-validation module includes the Cr case. The same
group includes negative roundoff checks, MDFF/reference/provider invariants,
canonical calculation API checks and strict kernel mutation controls.
Geometry/Bragg, fractional detector integration, raw/relative displays,
single/double and BW/MS identity, grouped/total views, exports, Save/Open,
selected runs, source availability, editor state and resource-request
restoration are covered by the broader selections.

Review independently compares AST bodies against the starting tree: all 22
moved operations are equivalent after excluding imports/docs and the declared
owner/name qualifications. Remaining definitions in `forward_pipeline`,
`propagation`, `geometry`, `project_io` and `multisite_project` also match after
those qualifications. `ResultsView` orchestration matches after resolving its
presentation namespace. Thus renderer arithmetic, data normalization,
comparison/export expressions and geometry algorithms retain their statement
and evaluation order. `git diff --check` passes.

The existing current source map grows from 141 to 147 paths: two relocated
protected presentation/export owners and four previously protected caller
paths now requiring reviewed current revisions. There are 34 changed existing
current entries. Every pre-existing archived prior-source payload and every
historical/reference/kernel declaration remains unchanged. Four authenticated
prior caller payloads are added through the existing mechanism. The original
three complete scientific kernel pins are untouched. No new registration
schema or numerical baseline is introduced.

## Remaining architecture and migration order

1. **Persistence utilities:** `project_io` delegates configuration and group
   extensions; those modules call its path/checksum/atomic-write and schema
   helpers. The remaining three-module component is wholly persistence/data
   handling. A later narrow change can review utility/codec ownership while
   retaining transaction, cancellation and historical format behavior. It is
   not concealed by wrappers or merged into an oversized single writer here.
2. **Numerical planning:** `channeling` uses projected/numerical planning from
   `propagation`, whose execution path uses channeling FFT geometry/incident
   fields. Breaking this two-module component requires a separate reviewed
   numerical-service boundary; this phase does not move execution or resource
   calculations merely for graph counts.
3. **Geometry:** neutral structure/snapshot handling no longer imports
   persistence; orientation, Bragg, elastic and preview preparation can be
   considered together for a later move, with the same explicit ASE inputs.
4. **Result data:** `forward_results` and `multisite_results` can move with
   their geometry, provider, diagnostics and provenance dependencies. Retain
   exact array operations and the canonical GUI-namespaced calculation API.
   Presentation and export remain consumers of these data services.
5. **Forward orchestration:** `forward_pipeline` can follow data/geometry and
   a reviewed channeling/planning boundary. Keep Single/Double, BW/MS,
   grouped schedules, physical model distinctions and cancellation/admission
   intact. `multisite_integration` should move only with its complete bounded
   scheduling and normalization dependencies.
6. **Resource and settings namespaces:** `memory_budget` is already headless,
   but four numerical modules still import that GUI-namespaced owner. Two
   provider dependencies on the existing GUI-namespaced records and the
   historical Ni inheritance also remain. Coordinate any later relocation
   with strict source identities and loading semantics; no policy/default or
   full record migration is attempted here.

Existing source coverage, tensor-frame/magnetic-structure and calibration
limitations remain scientific-development work. They are not solved by
module movement or new material-specific calculation routes.

## Exact validation commands

Commands below were run from the stated worktree with its `src`/`tests` on
`PYTHONPATH`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONHASHSEED=0`,
`QT_QPA_PLATFORM=offscreen`, and one OpenBLAS/OMP thread. `TEMP`/`TMP` use
`C:\Users\peng863\EMCD-Sim\build\nc-tmp`. Literal argument arrays, short
temporary UUID paths, JUnit destinations and source status are retained in
the corresponding launch records.

`geometry`:

```powershell
& C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe -u -m pytest tests/test_multisite_configuration.py::test_structure_snapshot_restore_without_qt_or_project_io tests/test_multisite_configuration.py::test_local_configuration_roundtrip_without_widget_dependencies -q --tb=short --basetemp=C:\Users\peng863\EMCD-Sim\build\nc-tmp\geometry-1c799996 -p no:cacheprovider --junitxml=C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\build\phase3c\geometry.xml
```

`results`:

```powershell
& C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe -u -m pytest tests/test_multisite_result_persistence.py -q --tb=short --basetemp=C:\Users\peng863\EMCD-Sim\build\nc-tmp\results-036ea427 -p no:cacheprovider --junitxml=C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\build\phase3c\results.xml
```

`results-fix`:

```powershell
& C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe -u -m pytest tests/test_multisite_result_persistence.py -q --tb=short --basetemp=C:\Users\peng863\EMCD-Sim\build\nc-tmp\results-fix-1661b9bb -p no:cacheprovider --junitxml=C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\build\phase3c\results-fix.xml
```

`science`:

```powershell
& C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe -u -m pytest tests/test_double_cancellation.py::test_bw_unchanged_and_depth_cancel[numerical] tests/test_double_cancellation.py::test_full_spectrum_unchanged[bloch] tests/test_double_cancellation.py::test_full_spectrum_unchanged[both] tests/test_multisite_scientific_validation.py tests/test_single_element_ni_compatibility.py::test_original_ni_all_numeric_arrays_exact[double-xmcd] tests/test_single_element_ni_compatibility.py::test_original_ni_all_numeric_arrays_exact[double-atomic] tests/test_numerical_roundoff.py tests/test_calculation_api.py tests/test_physics_source_guard.py tests/test_mdff_tensor.py tests/test_unified_mdff_providers.py -k "not provider_declaration_validation_and_preparation_without_qt and not historical_ni_eligibility_without_gui_geometry" -q --tb=short --basetemp=C:\Users\peng863\EMCD-Sim\build\nc-tmp\science-ddb45908 -p no:cacheprovider --junitxml=C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\build\phase3c\science.xml
```

`exact`:

```powershell
& C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe -u -B build/regression-recovery/verify_equivalence.py
```

`metadata-bridge`:

```powershell
& C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe -u -m pytest tests/test_atomic_parameter_editor.py::test_unified_starting_choices_have_no_material_electronic_defaults tests/test_v070_metadata.py -q --tb=short --basetemp=C:\Users\peng863\EMCD-Sim\build\nc-tmp\metadata-bridge-4acf096b -p no:cacheprovider --junitxml=C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\build\phase3c\metadata-bridge.xml
```

`bridge-fix`:

```powershell
& C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe -u -m pytest tests/test_atomic_parameter_editor.py::test_unified_starting_choices_have_no_material_electronic_defaults -q --tb=short --basetemp=C:\Users\peng863\EMCD-Sim\build\nc-tmp\bridge-fix-09726255 -p no:cacheprovider --junitxml=C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\build\phase3c\bridge-fix.xml
```

`workflows`:

```powershell
& C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe -u -m pytest tests/test_gui_stage_a.py tests/test_two_beam_geometry_comparison.py tests/test_detector_signals.py tests/test_gui_stage_c.py tests/test_gui_component_display.py tests/test_gui_stage_d.py tests/test_multisite_result_selection.py tests/test_multisite_result_export.py tests/test_total_result_selection.py tests/test_project_workflow.py tests/test_run_selection_restoration.py tests/test_multisite_configuration.py tests/test_atomic_parameter_editor.py tests/test_result_freshness.py -k "not structure_snapshot_restore_without_qt_or_project_io and not local_configuration_roundtrip_without_widget_dependencies and not unified_starting_choices_have_no_material_electronic_defaults" -q --tb=short --basetemp=C:\Users\peng863\EMCD-Sim\build\nc-tmp\workflows-497bafb2 -p no:cacheprovider --junitxml=C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\build\phase3c\workflows.xml
```

`consumer-fix`:

```powershell
& C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe -u -m pytest tests/test_gui_stage_d.py::ProjectTests::test_all_four_modes_roundtrip_complex_and_structure tests/test_multisite_result_selection.py::test_angular_group_energy_binding_matches_image_arrays tests/test_total_result_selection.py::test_alias_restore_switching_context_and_export tests/test_total_result_selection.py::test_global_metadata_and_spectral_zoom_aliases -q --tb=short --basetemp=C:\Users\peng863\EMCD-Sim\build\nc-tmp\consumer-fix-6082766a -p no:cacheprovider --junitxml=C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\build\phase3c\consumer-fix.xml
```

`exact-final`:

```powershell
& C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe -u -B build/regression-recovery/verify_equivalence.py
```

`registration`:

```powershell
& C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe -u -m pytest tests/test_mdff_usability_source_scope.py tests/test_unit_labels.py tests/test_mdff_editor_source_scope.py::test_offline_no_git_network_or_snapshot_execution tests/test_windows_build_metadata.py -q --tb=short --basetemp=C:\Users\peng863\EMCD-Sim\build\nc-tmp\registration-872a90df -p no:cacheprovider --junitxml=C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\build\phase3c\registration.xml
```

`final-map` (source-identity metadata recheck):

```powershell
& C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe -u -m pytest tests/test_mdff_usability_source_scope.py::test_positive_and_independent_historical_queries tests/test_mdff_usability_source_scope.py::test_pinned_declaration_and_archive_mutation[tests/fixtures/physics_readability_current_v1.json] -q --tb=short --basetemp=C:\Users\peng863\EMCD-Sim\build\nc-tmp\final-map-63c11996 -p no:cacheprovider --junitxml=C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\build\phase3c\final-map.xml
```

## Decision

**GO for the focused Phase 3C implementation.** Geometry data no longer depends
on persistence; scientific result assembly no longer depends on Qt rendering
or export; headless structure and stored-result operations work; affected
workflows and integrity controls pass; numerical results remain exact in the
established 22-case comparison.

This is a real boundary/cycle improvement with almost no size reduction.
The remaining numerical-planning and persistence groups are explicit future
work. This focused development GO does not establish a clean full-suite run or
release acceptance. No full regression, EXE rebuild, merge, tag, push or
publication is performed.

The final registration/report successor adds no application changes. Ordinary
Git status is clean after that local commit; ignored local measurement/test
evidence remains under `build/phase3c/`.
