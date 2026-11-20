# Phase 3A: configuration ownership and dependency cleanup

Date: 2026-11-20. Scope: incremental configuration/state simplification only.

## Revisions and scope

Working directory and Git worktree root:
`C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute`.
Branch: `refactor/physics-readability`.
Starting commit: `ab1dc11c5b39e5e01d7884e4fa8a1ae7164db4d0`.
Final application and maintained-test implementation commit:
`0e881e32d2bf4349b6be39fb6259c5a20557a83a`.
The final current-registration/report commit is its successor, identified in
the completion response and Git history. No application source changes follow
the implementation commit.

This phase builds on the completed regression recovery and numerical-contract
work. The earlier 1,768 distinct tests had **combined passing coverage**, not
one clean full-suite invocation. This phase does not change that description.
The actual pre-refactor scientific source remains
`cdb8836388c5ccc5ae7a614b47894c0ab158a824`; the structural comparison in this
report instead starts at the Phase 3A starting commit above.

Investigated `gui.forward_settings`, `gui.material_inputs`,
`gui.project_configuration`, `gui.project_session`, `gui.project_io`,
`gui.numerical_settings`, `gui.calculation_controls`, `gui.multisite_run`,
`gui.multisite_project`, `gui.site_group_editor`, `gui.group_mdff`,
`gui.provider_ui`, `gui.provider_preparation`, `multisite`, `mdff_providers`,
and their recorded static dependencies. Reviewed the prior complexity audit,
regression recovery, physics/name maps and both numerical-contract reports.

## What changed

1. **Structural group validation belongs to the existing group model.**
   `validate_site_rows` moves from `gui.site_group_editor` to `multisite`.
   It still accepts incomplete editor rows without inventing a magnetic
   direction or provider, and returns an executable model only for complete
   rows. Editor, configuration loader, result-group restoration and maintained
   tests use that same validator. Its validation and normalization are unchanged.
2. **Acknowledged provider binding belongs to the existing provider service.**
   `validate_group_reference` and `bind_group_direction` move from
   `gui.group_mdff` to `mdff_providers`. Global and Local editors, the site editor,
   configuration restoration and tests use these shared implementations.
   Source identity, native axis/frame validation, explicit reversal pairs,
   nonmagnetic handling and modeled-window coverage checks are retained.
   No tensor formula or evaluation order changes.
3. **One snapshot of common run controls replaces three builders.**
   `NumericalSettingsUI.forward_control_fields()` reads the existing sampling,
   detector, solver and Compute Resources widgets. Global configuration
   construction, Local configuration construction and configuration-only save
   now call it. It does not read Material/MDFF drafts, run automatic parameter
   selection, resolve allocations or admit workers. Existing caller-specific
   validation remains in place, including the odd-grid and supported solver
   combination checks.
4. Removed unused imports of `NiForwardSettings` in `numerical_settings` and
   `validate_site_rows` in `project_session`.

No Python module, compatibility facade, configuration record, solver or
calculation route was added. The validator moves themselves reduce no
algorithm duplication: there was one implementation of each before and after.
Their substantive benefit is correcting dependency direction and permitting
headless persistence. The control snapshot consolidation removes actual
duplicated field selection and translation.

An AST comparison against the starting commit confirms all three moved
functions are identical after excluding import statements. The final graph
removes seven unique edges and adds six; the net reduction is one edge.

### Names and maintained consumers

The helper names already describe their responsibilities and are retained.
No obsolete wrapper is introduced at an old owner.

| Previous owner/name | Current owner/name | Consumers and reason |
|---|---|---|
| `gui.site_group_editor.validate_site_rows` | `multisite.validate_site_rows` | Site editor, project configuration, saved group restoration, crystallographic and binding tests; structural validation must not require a widget. |
| `gui.group_mdff.validate_group_reference` | `mdff_providers.validate_group_reference` | Group/site editors, project configuration and MDFF tests; verified source binding belongs beside provider loading. |
| `gui.group_mdff.bind_group_direction` | `mdff_providers.bind_group_direction` | Global/Local provider UI, site editor and direction-binding tests; both modes need the same physical-pair validation. |
| Three inline common-control dictionaries | `NumericalSettingsUI.forward_control_fields` | `calculation_controls`, `multisite_run`, `project_session`; one owner for the same widget-to-input translation. |

The editor modules import the validators they use; Python can consequently
still expose those imported names as attributes. No maintained caller relies
on that incidental exposure and there is no supported compatibility adapter.
The supported canonical API remains exactly
`emcd_sim.gui.forward_pipeline.calculate(structure, settings, cfg, sites=...)`
with its existing optional parameters, dispatch, errors and numerical behavior.

## Dependency evidence

Measurements use the original complexity audit's conventions: tracked `src/`
Python files, unique internal module-to-module AST import edges, including
function-local/deferred imports, and strongly connected components (SCCs).
`from package import module` resolves to that module rather than adding a
spurious dependency on the package initializer. No application import is used
for measurement. P counts physical lines; N counts nonblank lines bearing
noncomment Python tokens including docstrings; S excludes formal docstrings.
Multiline tokens contribute their nonblank physical lines. GUI counts are a
subset of production, never added again to totals. Percentage changes use the
starting value as denominator.

The implementation reproduces every supplied starting metric, including
497 edges, 37 cyclic modules and the 26-module largest SCC. Reproduction
script and full before/after graphs are local evidence in `build/phase3a/`.

| Metric | Before | After | Change |
|---|---:|---:|---:|
| Production Python files | 109 | 109 | 0 (0.00%) |
| GUI Python files | 64 | 64 | 0 (0.00%) |
| Production P LOC | 19,515 | 19,516 | +1 (+0.01%) |
| Production N LOC | 17,466 | 17,465 | -1 (-0.01%) |
| Production S LOC | 16,530 | 16,524 | -6 (-0.04%) |
| Internal import edges | 497 | 496 | -1 (-0.20%) |
| Cyclic dependency groups | 4 | 4 | 0 (0.00%) |
| Modules in cycles | 37 | 30 | -7 (-18.92%) |
| Largest cycle | 26 | 19 | -7 (-26.92%) |
| Common run-control builders | 3 | 1 | -2 (-66.67%) |

These numbers show a useful local layering improvement, not a broad reduction
in application size or elimination of the dependency knot.

### Exact starting 26-module component

All names below are under `emcd_sim`:

```
gui.atomic_editor               gui.channeling
gui.forward_results             gui.forward_settings
gui.geometry                    gui.group_mdff
gui.manual_l23_editor            gui.material_inputs
gui.mdff_usability               gui.multisite_export
gui.multisite_project            gui.multisite_results
gui.multisite_results_controls   gui.project_configuration
gui.project_io                  gui.propagation
gui.provider_preparation         gui.provider_ui
gui.results                     gui.site_group_editor
gui.xmcd_preview                 gui.xmcd_source
historical_ni                    mdff_providers
multisite_single_channeling      multisite_spectrum
```

`project_session` is an important consumer of the cycle but was **not** one of
its 26 members. Merely editing it or changing its import style would not
demonstrate that the cycle was reduced.

| Starting edge | Responsibility/final disposition |
|---|---|
| `project_configuration -> site_group_editor` | Reverse dependency from persistence to widgets solely for row validation; now depends on `multisite`. |
| `project_configuration -> group_mdff` | Deferred reverse dependency for provider validation; now depends on `mdff_providers`. |
| `multisite_project -> site_group_editor` | Deferred reverse dependency while restoring saved groups; now depends on `multisite`. |
| `provider_ui -> group_mdff` | Deferred reverse dependency from shared editor behavior to one concrete dialog for pair binding; now depends on `mdff_providers`. |
| `site_group_editor -> group_mdff` | Still necessary to construct dialogs; its validation/binding imports now use `mdff_providers`. |
| `material_inputs <-> provider_preparation` and `material_inputs <-> mdff_providers` | Still present: record construction/source validation and provider preparation are intertwined. Deferred imports here remain counted. |
| `forward_settings -> historical_ni -> gui.geometry -> project_io -> forward_settings` | Still present: historical fields/preset, geometry result persistence and schema loading form a separate ownership knot. |
| `forward_results/results/propagation/project_io` | Still present: service, persistence, plotting/result controls and numerical execution remain coupled. Numerical extraction is outside this phase. |

The seven modules leaving the SCC are `atomic_editor`, `group_mdff`,
`manual_l23_editor`, `mdff_usability`, `provider_ui`, `site_group_editor`,
and `xmcd_preview`, all under `gui`. The other 19 listed modules remain in
that SCC. The other groups remain unchanged: the five-module window/acceptance
group; the three-module elastic-provider/scattering group; and the
three-module atomic/imported/manual MDFF group. No new cyclic group appears.

No investigated cycle-breaking edge was merely a typing dependency. The
removed imports executed concrete validation/binding code, including the
function-local imports that previously concealed the widget dependency.
Imports were redirected to the implementation's actual owner, rather than
converted to dynamic imports. Newly needed model imports in provider validation
remain visible to the same AST analysis.

## State ownership and deliberately preserved distinctions

| State | Owner and Phase 3A decision |
|---|---|
| Structure, original ASE indices, geometry | Existing `gui.geometry.Structure`/`Settings` and `multisite` records; no inferred sites, moments, frames or geometry. |
| Detector, sampling, solver and resource requests | Existing forward records; GUI now has one common control snapshot. Resource settings are still obtained through `compute_resources.settings()`. |
| Global Material direction | Material/editor accepted state; provider binding checks compatibility with the acknowledged physical pair. Source axes cannot set Material direction. |
| Local directions and provider references | Existing row tuples and `IonizationSiteGroup`/`MultiSiteIonization`; the existing structural validator is now model-owned. |
| Applied Global versus Local MDFF | Existing immutable applied references; their separate provider assignments and mode-specific requirements are preserved. |
| Accepted inputs versus drafts | Dialog/editor accepted snapshots remain separate from unapplied/inactive drafts. Save guards, Apply/Cancel and atomic multi-group binding are preserved. These are intentionally different states, not redundant records. |
| Original versus effective source paths | `project_configuration` keeps saved declarations, verified overrides, source-state diagnostics and effective configurations separate. Portable relocation must not rewrite declared source identity or bless an unverified source. |
| Saved projects and restoration | `project_io.config_from_dict` remains the schema reconstruction point; `project_configuration` validates loaded configuration; `project_session` binds it to widgets. Existing formats and legacy interpretation are unchanged. |
| Resource requests versus resolved allocations | Compute Resources owns requests/admission; an old machine allocation is still cleared on selected-run restoration. The common snapshot performs no allocation or memory policy change. |

### Ni-oriented records: investigated, not silently generalized

`ImportedSettings` and `MultiSiteForwardSettings` still inherit
`NiForwardSettings`. This is a remaining design limitation, not a completed
neutral-record migration. The inherited `atomic`, peak/correction fields and
historical preset values participate in existing `asdict` snapshots and
`config_from_dict` reconstruction; the latter builds `NiLocalConfig` and
interprets old missing fields. Removing/retyping those fields or introducing
different defaults is a separate saved-input compatibility decision.

This phase therefore preserves the record schema rather than adding a second
parallel settings representation or changing saved values. Generic providers
continue to use explicit source/element/edge/state and validated source samples;
missing/unsupported declarations still fail. The generic calculation does not
fall back to Ni. Numerical automatic presets remain restricted to their
existing explicitly matched historical cases; general materials still require
their existing Manual settings. Historical Ni remains a distinct requested-energy
provider/preset. No supported physics is expanded or substituted.

## Verification

Evidence lives in `build/phase3a/` with bounded command logs,
JUnit XML for pytest groups and launch records containing exact arguments,
starting HEAD, dirty-file inventory, environment, owned PID, duration and exit
status. Short temporary paths use the established main-repository `build/nc-tmp`
root, with normal-user temporary-file access. Tests/searches run sequentially.

### Executed checks

All pytest groups use `-q --tb=short`, a unique short `--basetemp`,
`-p no:cacheprovider` and JUnit XML. Environment: the existing Windows source
validation Python 3.11 environment, Qt offscreen, deterministic hash seed,
OpenBLAS/OMP threads fixed to one, and the worktree `src`/`tests` on
`PYTHONPATH`. The exact executable, argument arrays and environment are in the
corresponding `*-run.json` launch records. Durations below are runner wall time.

| Evidence prefix / command scope | Result | Seconds |
|---|---|---:|
| `groups`: complete `test_multisite_configuration`, `test_group_direction_binding`, `test_crystallographic_sites`, `test_group_mdff` modules | 49 passed, 1 Windows sharing violation, 1 native-only skip | 85.828 |
| `portable`: the single sharing-violation case, unchanged | 1 passed | 2.781 |
| `science`: selections and complete modules listed below | 65 passed | 83.657 |
| `exact`: unchanged `build/regression-recovery/verify_equivalence.py` | 22 cases / 2,294 arrays exactly equal; physical metadata and edge metrics equal | 30.797 |
| `workflows`: complete modules listed below | 77 passed, 2 existing skips | 706.250 |
| `registration`: existing positive current-source/scientific guards and isolated overrides for all four updated current source entries | 2 positive controls and 8 mutation rejections passed | 3.750 |
| `final-map`: existing positive historical-query and current-map mutation tests after recording the implementation commit | 2 passed | 15.344 |

`groups` includes the new
`test_local_configuration_roundtrip_without_widget_dependencies`. A fresh
Python child explicitly rejects any `PySide6` import, loads a valid Local
configuration, saves/reopens it, verifies executable groups/settings and
confirms no Qt module loaded. Existing configuration tests retain their exact
saved-field, source-identity, array and physical assertions.

The one initial failure was
`test_fe3o4_manual_pair_portable_relocation_and_exact_amplitudes`: Windows
reported `WinError 32` while the test deleted its temporary `Fe_B.json`.
It failed before the relocation assertions and passed on one isolated rerun
without any source/test change. No retry logic or relaxed assertion was added.
This was a file-sharing failure, not a numerical mismatch.

`science` runs these six required comparisons:

```
test_double_cancellation.py::test_bw_unchanged_and_depth_cancel[numerical]
test_double_cancellation.py::test_full_spectrum_unchanged[bloch]
test_double_cancellation.py::test_full_spectrum_unchanged[both]
test_multisite_scientific_validation.py::test_bcc_cr_independent_events_and_symmetry[unequal-mdff-double-bloch]
test_single_element_ni_compatibility.py::test_original_ni_all_numeric_arrays_exact[double-xmcd]
test_single_element_ni_compatibility.py::test_original_ni_all_numeric_arrays_exact[double-atomic]
```

The Cr case is included by running **all** of
`tests/test_multisite_scientific_validation.py`. The same invocation also runs
the complete `test_numerical_roundoff`, `test_calculation_api`,
`test_physics_source_guard`, `test_mdff_tensor` and
`test_unified_mdff_providers` modules. Thus independent-event/reversal/symmetry
invariants, provider/reference comparisons, general-material geometry,
unsupported-input rejection and the strict kernel/convention mutation tests
remain exercised. The exact driver covers both numerical methods, explicit
declared inputs, historical Ni and grouped material cases, including [017].
Its printed older-reference roundoff notices are the already documented
pre-Phase-3A differences; all 2,294 requested comparisons are exact.

`workflows` runs the complete following modules under `tests/`:

```
test_material_mdff_workflow.py   test_material_magnetization.py
test_local_mdff_workflow.py      test_project_workflow.py
test_run_selection_restoration.py
test_compute_resources.py       test_sampling_workflow.py
test_solver_settings_ui.py
```

Across these pytest groups, **197 distinct cases have 194 passes and three
existing skips**, with the single file-sharing failure resolved by its unchanged
recheck. The skips are `test_native_group_mdff`,
`test_native_windows_project_history_and_menus` and
`test_saved_settings_and_arrays_preserved_without_solver` (optional saved GUI
reference unavailable). These are not claimed as passes. The exact driver and
standalone registration controls are additional checks, not pytest case counts.

The final-map pytest selections are
`tests/test_mdff_usability_source_scope.py::test_positive_and_independent_historical_queries`
and
`tests/test_mdff_usability_source_scope.py::test_pinned_declaration_and_archive_mutation[tests/fixtures/physics_readability_current_v1.json]`.
They run after the source-identity metadata changes, at implementation commit
`0e881e32d2bf4349b6be39fb6259c5a20557a83a`; all earlier test groups run on the
recorded pending implementation changes at starting HEAD `ab1dc11`. The final
application/test sources match those verified pending changes. No scientific
comparison is restarted for the metadata/report-only successor.

### Source integrity and final review

The existing reviewed-current map updates only its four changed application
entries: `gui/calculation_controls.py`, `gui/numerical_settings.py`,
`gui/provider_ui.py` and `mdff_providers.py`. Its existing loader pin is updated
accordingly. Existing historical registrations, compressed prior source,
kernel/reference identities, archives and scientific assertion helpers remain
unchanged. No new registration format, whitelist, hash gate or baseline is added.
The source commit identity is updated to the verified implementation commit
in the final registration/report successor.

A structural comparison of the current-map JSON against `ab1dc11` confirms
exact equality of every field except those four current-file entries and
`production_source`, with no change in the registered path set. The current
map's existing loader pin changes to authenticate those approved contents.

The registration check first executes
`physics_source_guard.assert_registered_sources()` and
`unit_source_snapshots.assert_reviewed_current_sources()`. It then appends
unauthorized bytes to an **in-memory override**, separately for each of the
four updated application entries. Both existing guards reject every override
and identify its path; disk sources are never mutated. This supplements the
existing numerical-kernel mutation tests in `science`.

`git diff --check` passes. Maintained tests/scripts/packaging have no remaining
imports of these helpers from their former widget owners. No files moved,
packaging inputs or dependencies changed; all owners are existing packaged
modules. Application edits are limited to configuration validation ownership
and the common control snapshot. `forward_pipeline`, all Bloch/FFT/detector/
propagation/multisite numerical kernels, equations, reference data, comparison
rules, resource policies and saved-project schema code remain unchanged.

No complete regression, EXE rebuild, release acceptance, push, merge, tag or
publication is part of Phase 3A.
The final registration/report successor adds no application changes; ordinary
Git status is clean after that local commit. Ignored local test/measurement
evidence remains under `build/phase3a/`.

## Remaining coupling and proposed Phase 3B

1. Separate neutral numerical/detector/resource request fields from explicit
   provider/preset fields using the existing records where possible. Design
   the saved-input loading translation first, retaining original keys/values
   and historical missing-field interpretation. Do not keep parallel generic
   and Ni calculation engines or add a universal configuration facade.
2. Give source declaration/validation and preparation a consistent headless
   ownership boundary. Resolve `material_inputs`, `mdff_providers` and
   `provider_preparation` dependencies together; preserve historical direct
   evaluation versus declared-grid interpolation as different models.
3. Address the remaining geometry/persistence and result-service/widget
   dependencies with separately scoped behavioral checks. Large `app`,
   `results`, `project_io`, `project_session` and editor modules still warrant
   focused work. Smaller import cycles in scattering and MDFF conversion also
   remain; collapsing distinct scientific implementations is not justified.
4. Treat any eventual numerical service migration separately: retain the
   canonical public calculation API and independently verify kernels,
   schedules, normalization, source/result association and exact comparison
   cases. Phase 3A supplies no license to change numerical arithmetic.

Scientific generality limitations (unsupported magnetic structures/tensor
frames, source coverage or absolute cross-material normalization) require
scientific development and remain separate from this ownership cleanup.

## Phase 3A decision

**GO for Phase 3A's focused structural changes.** Seven widget modules leave
the large cycle, persistence gains an enforced headless path, and three
equivalent control builders become one. Scientific checks and the 22-case
exact comparison pass; affected workflows preserve their contracts.

This is a bounded architectural improvement with almost no size reduction.
The 19-module service cycle and Ni-derived record schema remain concrete work
for Phase 3B. This GO does not represent a clean full-regression run, a new
Windows build or a release/candidate acceptance decision.
