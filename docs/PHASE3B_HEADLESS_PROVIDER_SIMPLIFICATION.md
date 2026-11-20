# Phase 3B: headless MDFF provider ownership

Date: 2026-11-20. Decision and final verification are recorded below.

## Scope and source identity

Working directory and Git root:
`C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute`.
Branch: `refactor/physics-readability`.
Starting commit: `5367d01fa7c8b220da64315d660811338b653a67`; ordinary Git status
was clean. Final application and maintained-test implementation commit:
`fe5a0eaab34ab1bb251d19893de2c08af0ae0c4e`.
The final registration/report successor is identified in the completion response
and Git history. No application source changes follow this implementation.

This is an incremental provider/configuration change. It follows the Phase 3A
report and preserves the earlier complexity audit, regression recovery,
numerical-contract investigation/corrections and their scientific evidence.
The earlier 1,768 distinct tests had combined passing coverage, not one clean
full-suite invocation. Phase 3B does not run a complete suite or establish
release acceptance.

The actual pre-refactor scientific comparison source remains
`cdb8836388c5ccc5ae7a614b47894c0ab158a824`. Structural metrics in this report
instead compare the Phase 3B starting commit with the final implementation.

## Implemented ownership changes

`mdff_providers` is now the existing common service owner for source-backed
declaration, source authentication, material binding and provider preparation.
It continues to use the accepted Atomic/XMCD converters and tensor/source
models. No new provider manager, registry, calculation engine or dependency is
introduced.

| Responsibility | Before | After |
|---|---|---|
| Saved source-backed dataclasses | `gui.material_inputs.ImportedSettings` / `ProviderSettings` | Same definitions, names, module identities, bases, fields and defaults; record module no longer imports source/provider operations. |
| Source-to-settings conversion | Private `gui.material_inputs._source_settings`, plus a separate Manual-editor translation | Public `mdff_providers.settings_from_source`, reused by file/provider constructors and the Manual editor. |
| Source constructors and identity validation | `gui.material_inputs.settings_for_source`, `settings_for_provider`, `source_for`, `is_declared` | Same service operations in `mdff_providers`; no forwarding functions at the former owner. |
| Common configuration-level eligibility, energy and tensors | Three functions in `gui.material_inputs` | `mdff_providers.material_reason`, `energy_grid`, `tensors`; concrete consumers include calculation controls, eligibility checks, previews and maintained scientific callers. |
| Declared provider preparation | `gui.provider_preparation` | Existing functions and `DeclaredMDFFProvider` in `mdff_providers`; the former module is deleted. |
| Explicit physical minus-pair selection | `gui.provider_direction.ReversedProviderPair` | Same class implementation in `mdff_providers`; the former module is deleted. |
| Historical Ni eligibility reference cell | `historical_ni -> gui.geometry.Structure.nickel().atoms` | Identical `ase.build.bulk('Ni','fcc',a=3.524,cubic=True)` call in the historical preset's gate, removing the dependency on GUI geometry. |

The renamed private constructor now describes its public responsibility:
building a saved settings record from an already validated provider source.
It does not replace source validation. Explicit caller declarations still pass
through `source_for` and physical binding checks before calculation.
No alias for `_source_settings` is retained.

The Manual editor formerly repeated selected-energy validation/packing,
source identity assignment and record construction. It now supplies its
explicit target/declarations and ordinary controls to `settings_from_source`.
The service retains the authoritative source checksum and selected energies;
the editor retains the entered path, acknowledgment, site selection and Material
direction. In particular, an entered original path is not silently replaced by
a resolved path. The existing original/effective portable-source distinction
remains in project loading.

The two deleted GUI modules are consolidations of nonvisual service ownership,
not deletion of scientific methods. Historical direct evaluation and
declared-grid interpolation remain separate providers behind the same existing
preparation interface. Both continue to use the common forward engine.
The former GUI-namespaced helpers were already nonvisual; this phase does not
claim that their mathematics previously required widgets. The gains are a
single supported service owner, fewer reverse dependencies, shared conversion
and fresh-process behavioral enforcement of the headless boundary.

### Consumers and retained interfaces

Maintained production, test, script and native-acceptance imports use the new
service owner. Record-only consumers continue to import the original
dataclasses. `tests/reference_imports.py` translates identified archived imports
only inside reference namespaces; historical source bytes are untouched.
The maintained numerical-contract diagnostic script's archived import
translation is updated, without rerunning that closed investigation.

The retained configuration-level `material_reason`, `energy_grid` and `tensors`
functions are current service operations used by calculation controls and
scientific/preview consumers, not wrappers left at retired module paths.
`provider_energy_grid` also remains necessary for callers that have already
prepared a provider and must retain native-grid selection behavior.

The canonical public calculation signature and behavior remain
`emcd_sim.gui.forward_pipeline.calculate(structure, settings, cfg, sites=...)`
with its existing optional arguments. In `forward_pipeline`, `propagation`
and the multisite numerical modules, only dependency imports change. Numerical
execution stays at its existing owner.

## Ni-derived settings: preserved schema, smaller dependency surface

The hierarchy remains:

```
NiForwardSettings
  MultiSiteForwardSettings
  ImportedSettings
    ProviderSettings
```

No base class or parallel generic settings representation is added.
`NiForwardSettings` and `MultiSiteForwardSettings` stay in `gui.forward_settings`;
`ImportedSettings` and `ProviderSettings` stay in `gui.material_inputs`.
Runtime/dataclass identity, `asdict` output fields and constructor defaults are
preserved. `NiLocalConfig` itself is unchanged.

| Fields / interpretation | Authoritative use and preservation |
|---|---|
| Sampling, detector and numerical/resource controls | Existing `energy_points`, grid/depth/subpixels, detector support, solver/slice controls, energy/angular choices, memory/worker requests and recorded allocation. Phase 3A's single control snapshot remains untouched. |
| Source identity and explicit material state | `source`, checksum, acknowledgment, magnetization, element/edge/state, site indices, selections and pair state; declared sources remain authoritative. |
| Declared Atomic/XMCD parameters | Original authenticated source and `provider_declaration`/schema; unrelated inherited Ni fields do not become material inputs. |
| Historical Ni-only parameters | `NiLocalConfig`, eta/beta, broadening/radial controls, old peak/correction/window fields retain their existing stored values and explicit historical interpretation. |
| General source selections | Existing source constructors supply selected native energies and labels, overriding inherited peak placeholders. Single-edge declarations still use their explicit labels, not Ni L2,3 energies. |
| Missing saved fields | Unchanged `project_io.config_from_dict`: old Atomic peaks derive from saved atomic parameters when absent; old Local full/native and angular-all interpretation is retained; tuples, provider schema and old resource requests are reconstructed as before. |

The general record module now directly depends only on dataclass construction and its
existing base record. It no longer imports NumPy, tensor loading, edge
validation, conversion or provider preparation. Thus it no longer creates a
return dependency from configuration definitions to services.
The historical Ni gate also no longer imports GUI geometry or persistence
indirectly. Generic provider preparation still depends on two GUI-namespaced
**record modules**; it does not depend on widgets or GUI execution. This is a
remaining namespace/schema limitation, not complete neutral-record extraction.
Ni default-source resolution and the inherited historical atomic field factory
also remain; they are not claimed as removed or as general material inputs.

A complete inheritance replacement is deferred. Removing the inherited fields,
retyping `atomic`, changing defaults or moving class identities would alter
existing construction/serialization contracts. This phase does not redesign
that schema merely to remove an uncomfortable class name. Existing project
loaders and all scalar settings are preserved instead. No path silently falls
back to Ni: the dispatch still accepts only explicit supported record types,
and malformed or incompatible declarations fail validation.

## Dependency findings and metrics

The Phase 3A AST methodology is reused: tracked production `.py` files;
unique directed literal internal imports including deferred imports; relative
imports resolved to actual modules; self edges, external modules, dynamic
strings and implicit package initialization excluded. SCCs use that same graph.
P is physical LOC, N is nonblank noncomment token-bearing LOC, and S excludes
formal module/class/function docstrings. GUI is a subset of production and
is not counted twice. Deleted paths are excluded from the final working tree.
The before measurement reproduces all supplied starting metrics.

| Metric | Before | After | Change |
|---|---:|---:|---:|
| Production Python files | 109 | 107 | -2 (-1.83%) |
| GUI Python files | 64 | 62 | -2 (-3.13%) |
| Production P LOC | 19,516 | 19,502 | -14 (-0.07%) |
| Production N LOC | 17,465 | 17,450 | -15 (-0.09%) |
| Production S LOC | 16,524 | 16,506 | -18 (-0.11%) |
| Internal import edges | 496 | 482 | -14 (-2.82%) |
| Cyclic groups | 4 | 4 | 0 (0.00%) |
| Modules in cycles | 30 | 22 | -8 (-26.67%) |
| Largest SCC | 19 | 11 | -8 (-42.11%) |
| Common control builders | 1 | 1 | 0 (0.00%) |
| GUI → non-GUI import edges | 119 | 119 | 0 (0.00%) |
| Non-GUI → GUI import edges | 12 | 8 | -4 (-33.33%) |
| GUI → `mdff_providers` edges | 9 | 15 | +6 (+66.67%) |
| `mdff_providers` → GUI-namespaced modules | 3 | 2 | -1 (-33.33%) |

The local graph/measurement evidence is in `build/phase3b/before.json`,
`after.json` and the reused measurement script. More GUI consumers now depend
directly on the common provider owner; that is the intended dependency
direction, not additional independent provider implementations. The two
remaining provider-to-GUI edges are to the saved-record modules. The other
six non-GUI-to-GUI edges are the intentional GUI launch, four unchanged
memory-budget imports and multisite Double's unchanged channeling dependency.
These are explicit remaining Phase 3C boundaries, not hidden edges.

### Paths that kept the old component cyclic

| Starting path | Correction |
|---|---|
| `material_inputs -> mdff_providers -> material_inputs` | Records no longer import provider services; service operations have one implementation at `mdff_providers`. |
| `material_inputs -> provider_preparation -> material_inputs` | Source validation and preparation now share the service owner; the intermediate GUI module is removed. |
| `forward_settings -> historical_ni -> gui.geometry -> project_io -> forward_settings` | Ni's explicit reference gate constructs the identical ASE reference directly; no geometry/persistence dependency is needed. |
| `multisite_* -> gui.material_inputs.source_for` | Kernels now import the same source-validation operation from the provider service; their numerical bodies are unchanged. |

No cycle was hidden with importlib, registries or strings. New service record
imports are ordinary top-level imports. Existing conditional converter imports
remain counted by the graph. The relevant removed dependencies were runtime
responsibilities, not type-only annotations.

The remaining largest SCC is exactly:

```
gui.channeling                  gui.forward_results
gui.geometry                    gui.multisite_export
gui.multisite_project            gui.multisite_results
gui.multisite_results_controls   gui.project_configuration
gui.project_io                  gui.propagation
gui.results
```

`forward_settings`, `material_inputs`, `historical_ni`, `mdff_providers`,
`multisite_single_channeling`, `multisite_spectrum` and `xmcd_source` leave the
old 19-module component; `provider_preparation` is removed. The other SCCs
remain the five-module application/acceptance group, the three-module elastic
provider/scattering group, and the three-module atomic/imported/manual source
conversion group. No new cyclic group is introduced.

File consolidation alone is not the architectural claim. The substantive
changes are the removal of return edges into configuration definitions,
headless service use, one shared source-to-settings translation and removal of
the historical preset's dependency on GUI geometry. Application size falls
only slightly and substantial GUI/service coupling remains.

## Verification and integrity

All checks use the existing
Windows source-validation Python, short main-repository `build/nc-tmp` paths,
Qt offscreen and one BLAS/OMP thread. Owned test subprocesses are tracked by
the existing bounded launcher; searches and tests run sequentially.

Evidence prefixes under `build/phase3b/` include `.log`, pytest `.xml` and
`-run.json` records of exact executable/arguments, source HEAD, pending files,
environment, PID, elapsed time and exit status. The unchanged exact comparison
driver writes no new reference arrays.

| Evidence prefix | Result | Runner seconds |
|---|---|---:|
| `headless` | 4 passed | 8.047 |
| `science` | 65 passed; the 4 already-passed headless cases deselected | 78.390 |
| `exact` | 22 cases / all 2,294 arrays exactly equal; physical metadata and edge metrics equal | 25.265 |
| `workflows` | 192 passed, 2 existing native-only skips | 789.015 |
| `contracts-guards` | 138 passed | 192.672 |
| `final-map` | 2 already-counted registration cases rechecked after recording the implementation commit | 6.000 |

The pytest groups cover **401 distinct cases: 399 passed and two skipped**,
with no failures or errors. The skips are `test_native_group_mdff` and
`test_native_windows_project_history_and_menus`; neither is claimed as a pass.
The exact-array driver is additional evidence, not a pytest case count.
No scientific discrepancy or test failure required a correction/retry.
The final-map recheck is limited to metadata that changed after the
implementation commit; it does not increase the distinct-case count.
All earlier checks record starting HEAD `5367d01` and the pending changes that
became `fe5a0eaab34ab1bb251d19893de2c08af0ae0c4e`. The final-map checks run at
that implementation commit with only registration/report metadata pending.
No application source changes or numerical re-execution follow the verified
implementation.

`science` includes the six corrected comparisons:

```
test_double_cancellation.py::test_bw_unchanged_and_depth_cancel[numerical]
test_double_cancellation.py::test_full_spectrum_unchanged[bloch]
test_double_cancellation.py::test_full_spectrum_unchanged[both]
test_multisite_scientific_validation.py::test_bcc_cr_independent_events_and_symmetry[unequal-mdff-double-bloch]
test_single_element_ni_compatibility.py::test_original_ni_all_numeric_arrays_exact[double-xmcd]
test_single_element_ni_compatibility.py::test_original_ni_all_numeric_arrays_exact[double-atomic]
```

The Cr case is included through the complete multisite scientific-validation
module. The same invocation runs the existing negative roundoff tests, MDFF
tensor/reference and provider tests, canonical calculation API checks and
strict scientific kernel mutation controls. All original reference arrays,
equations and comparison tolerances are unchanged. The exact driver retains
its original source and comparison logic; its older-reference roundoff notices
are the already documented pre-refactor differences, not Phase 3B mismatches.

The broader workflow group runs once near completion. It covers Material and
Global/Local MDFF Apply/Cancel, source identity and directions, Atomic/Manual/
XMCD editors, portable and historical Save/Open, selected-run and draft-state
restoration, numerical sampling and remembered Compute Resources requests.
The existing registered Atomic editor bridge retains its separate historical
and current contracts. No old regression/investigation, build or acceptance
workflow is resumed.

`contracts-guards` runs the existing current-map positive and mutation tests,
historical authentication and independent source/frame validation, plus
`test_offline_no_git_network_or_snapshot_execution` and
`test_historical_and_current_guards_work_without_git`. These controls explicitly
block subprocesses/Git, and the former also blocks network and archived-code
execution. Source authentication therefore continues to work without those
execution mechanisms. The numerical kernel controls also reject reversions
when ordinary current-source approval is deliberately bypassed.

### Source registration and review

The existing current map has 25 changed entries plus an approved current entry
for the previously protected `historical_ni` path. Its existing relocation map
records `gui/provider_preparation.py -> mdff_providers.py`; no forwarding module
is kept. The old preparation source remains authenticated through the existing
prior-source mechanism. The current path count remains 141. No new schema,
whitelist, guard framework or scientific baseline is introduced.

Every existing prior-source payload is byte-for-byte unchanged. One payload
for the previously registered historical Ni source is added from the starting
Git tree, authenticated against its unchanged historical declaration. The
historical registration, reference/kernel archives, original kernel source
and all scientific/reference pins remain unchanged. Only reviewed current
identities and the existing current-map loader pin change.

AST review confirms:

- Exact unchanged dataclass definitions at both existing record owners.
- Imports-only changes in `forward_pipeline`, `propagation` and both multisite
  numerical modules.
- Equivalent moved bodies for all 14 service functions/classes, after excluding
  import relocation, docstrings and the factory/parameter rename. This includes
  declared energy-grid calculations and the explicit reversal-pair class.

The provider service is 323 physical lines, below the 500-line oversized-module
threshold. No propagation kernel is moved into it. The Manual editor's shared
conversion and the Ni reference-cell constructor are the only substantive
application-body changes beyond those ownership/import adjustments.
`git diff --check` passes, and maintained source/scripts/tests/packaging contain
no imports of operations from their retired owners. Source and result
traceability remain separate from a release build.

### New headless contracts

Three parameterized fresh-process cases use the existing validated fixtures:
Manual complex Fe tensor pairs, explicit Fe Atomic parameters and declared O
K-edge XMCD. Each child rejects Qt and GUI geometry/project-I/O imports and
actually constructs source-backed settings, authenticates its source, binds
explicit sites, checks material compatibility, prepares energy/tensor inputs,
compares tensor access with the same validated source and revalidates identity.
Manual reversal is exercised through explicit physical-pair binding. Each case
rejects another material declaration, a changed source checksum and invalid
source JSON. A separate child verifies accepted/rejected historical Ni cells
without GUI geometry. These tests exercise work, not just module imports.

The existing Phase 3A headless configuration Save/Open contract remains part
of the affected workflow group.

## Phase 3C preparation

| Service | Dependencies to resolve before a focused move |
|---|---|
| `forward_pipeline` | Keep the canonical API stable; retain source/model preparation, admission, cancellation, schedules and result association. Provider preparation is now headless, but result/persistence and geometry dependencies remain. |
| `channeling` / `multisite_integration` | Preserve distinct uniform/grouped schedules, detector support, independent-site normalization and accumulation order. Resolve their `propagation`/geometry/result coupling first. |
| `propagation` | Still couples numerical validation, geometry, channeling and result/view helpers. Separate presentation of diagnostics from numerical planning without changing bounds, FFT recipes or admission. |
| `geometry` | `preview` still imports project serialization for `structure_snapshot`; resolve snapshot ownership before moving geometry services. The historical Ni return dependency has been removed. |
| `forward_results` | Split plotting/persistence responsibilities from result assembly carefully; retain source/result traceability, metadata, frame conventions and saved-array interpretation. |
| `memory_budget` | Already headless, but record property/runtime admission consumers remain GUI-namespaced. Move only with reviewed accounting, reservation and resource-policy checks; do not change thresholds. |

These services are not moved in Phase 3B. The next stage should address the
11-module result/geometry/persistence component with a narrow boundary and its
own behavioral/numerical evidence, rather than extracting an entire engine at
once. Neutral-record migration should first specify the existing historical
field/type and missing-value loading contract.

Unsupported scientific conditions remain explicit limitations. New magnetic
models, anisotropic tensor-frame inference, extrapolation or absolute
cross-material calibration require scientific development and are outside
these ownership changes.

## Exact validation commands

Commands below were executed from the stated worktree. The launcher sets
`PYTHONPATH` to its `src` and `tests`, `PYTHONDONTWRITEBYTECODE=1`,
`PYTHONHASHSEED=0`, `QT_QPA_PLATFORM=offscreen`, and
`OPENBLAS_NUM_THREADS=OMP_NUM_THREADS=1`. `TEMP`/`TMP` use
`C:\Users\peng863\EMCD-Sim\build\nc-tmp`. Literal temporary UUID paths and
JUnit destinations are preserved here; launch records also capture the
source status and durations.

`headless`:

```powershell
& C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe -u -m pytest tests/test_unified_mdff_providers.py::test_provider_declaration_validation_and_preparation_without_qt tests/test_unified_mdff_providers.py::test_historical_ni_eligibility_without_gui_geometry -q --tb=short --basetemp=C:\Users\peng863\EMCD-Sim\build\nc-tmp\headless-b57835e1 -p no:cacheprovider --junitxml=C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\build\phase3b\headless.xml
```

`science`:

```powershell
& C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe -u -m pytest tests/test_double_cancellation.py::test_bw_unchanged_and_depth_cancel[numerical] tests/test_double_cancellation.py::test_full_spectrum_unchanged[bloch] tests/test_double_cancellation.py::test_full_spectrum_unchanged[both] tests/test_multisite_scientific_validation.py tests/test_single_element_ni_compatibility.py::test_original_ni_all_numeric_arrays_exact[double-xmcd] tests/test_single_element_ni_compatibility.py::test_original_ni_all_numeric_arrays_exact[double-atomic] tests/test_numerical_roundoff.py tests/test_calculation_api.py tests/test_physics_source_guard.py tests/test_mdff_tensor.py tests/test_unified_mdff_providers.py -k "not provider_declaration_validation_and_preparation_without_qt and not historical_ni_eligibility_without_gui_geometry" -q --tb=short --basetemp=C:\Users\peng863\EMCD-Sim\build\nc-tmp\science-a0a797b4 -p no:cacheprovider --junitxml=C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\build\phase3b\science.xml
```

`exact`:

```powershell
& C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe -u -B build/regression-recovery/verify_equivalence.py
```

`workflows`:

```powershell
& C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe -u -m pytest tests/test_multisite_configuration.py tests/test_group_direction_binding.py tests/test_group_mdff.py tests/test_material_mdff_workflow.py tests/test_material_magnetization.py tests/test_local_mdff_workflow.py tests/test_project_workflow.py tests/test_run_selection_restoration.py tests/test_atomic_parameter_editor.py tests/test_manual_l23.py tests/test_unified_provider_gui.py tests/test_xmcd_editor_selections.py tests/test_mdff_workspace_participation.py tests/test_sampling_workflow.py tests/test_compute_resources.py::test_project_roundtrip_retains_modes_and_remembered_manual_values tests/test_compute_resources.py::test_gui_run_submits_displayed_allocation_without_replacing_manual_requests -q --tb=short --basetemp=C:\Users\peng863\EMCD-Sim\build\nc-tmp\workflows-28abb515 -p no:cacheprovider --junitxml=C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\build\phase3b\workflows.xml
```

`contracts-guards`:

```powershell
& C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe -u -m pytest tests/test_single_element_contracts.py tests/test_single_element_forward.py tests/test_part1c_provider_interface.py tests/test_mdff_usability_source_scope.py tests/test_mdff_editor_source_scope.py::test_offline_no_git_network_or_snapshot_execution tests/test_unit_labels.py::test_historical_and_current_guards_work_without_git -q --tb=short --basetemp=C:\Users\peng863\EMCD-Sim\build\nc-tmp\contracts-guards-9ac4767c -p no:cacheprovider --junitxml=C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\build\phase3b\contracts-guards.xml
```

`final-map` (source-identity metadata recheck only):

```powershell
& C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe -u -m pytest tests/test_mdff_usability_source_scope.py::test_positive_and_independent_historical_queries tests/test_mdff_usability_source_scope.py::test_pinned_declaration_and_archive_mutation[tests/fixtures/physics_readability_current_v1.json] -q --tb=short --basetemp=C:\Users\peng863\EMCD-Sim\build\nc-tmp\final-map-e7c80c68 -p no:cacheprovider --junitxml=C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute\build\phase3b\final-map.xml
```

## Focused decision

**GO for the focused Phase 3B changes.** The provider operations have one
headless owner, duplicated Manual configuration conversion is removed, all
targeted checks pass and the largest SCC falls from 19 to 11 without changing
scientific results. This is a genuine local dependency improvement with only
small LOC reduction, not complete engine extraction or complete Ni-record
decoupling.

No full regression, EXE rebuild/replacement, public version change, push,
merge, tag or publication is performed. This focused GO does not establish
full-suite or release acceptance.

Final ordinary Git status is clean after the local registration/report successor.
Ignored local measurement and test evidence remains under `build/phase3b/`.
