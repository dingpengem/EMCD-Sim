# Physics-readability refactor: structural complexity audit

Audit date: 2026-11-19. This report measures committed Python source and inspects its responsibilities and dependencies. The audit changes only this document; it does not change code, tests, Git history, release artifacts or scientific reference data. No test, simulation, build, regression or candidate-acceptance work was started or restarted.

## Assessment

The refactor achieved **modest, genuine local simplification**: a canonical public forward entry point, more accurate responsibility names, separation of the background worker from widgets, removal of obsolete import routes, stricter explicit-material input handling, and one shared implementation of detector reversal algebra.

It did **not** achieve a broad reduction in application size, dependency coupling or long-function complexity. Production Python files rose **104 → 109 (+4.81%)**, physical lines **19,298 → 19,436 (+0.72%)**, and source lines excluding comments/docstrings **16,423 → 16,456 (+0.20%)**. Internal import edges rose **479 → 495 (+3.34%)**. Four cyclic dependency groups containing 37 modules remain. Production files over 500 physical lines fell **10 → 9**, but the largest files and the count of long functions are largely unchanged.

The baseline already used common scientific kernels and common uniform-forward orchestration. Describing this change as the replacement of separate Ni, Cr and Fe3O4 scientific engines would overstate what the source comparison demonstrates. Most of the structural change is decomposition, ownership clarification and caller migration, with limited actual algorithm deduplication.

## 1. Exact revisions and scope

| Item | Audited value |
| --- | --- |
| Absolute working directory | `C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute` |
| Git worktree root | `C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute` |
| Branch | `refactor/physics-readability` |
| Before: actual pre-refactor source | `cdb8836388c5ccc5ae7a614b47894c0ab158a824` |
| First refactor commit | `f7affbf3328fb3cee3e6efa4f722d65f9d1a5bfa` |
| After: current HEAD | `6817d644d3e9dcc3f06d02d1ad733e36b331d0f2` |

Git history identifies `f7affbf` (“Name calculation and project controls by responsibility”) as the first refactor commit. Its direct parent is **`cdb8836388c5ccc5ae7a614b47894c0ab158a824`**, whose subject is “Restore inputs when the current saved run is clicked again”. The ancestry was checked with `git rev-parse f7affbf^`, not inferred solely from the refactor notes. The after revision includes the subsequent extraction, API cleanup, consumer corrections and final documentation commits through `6817d64`. Using only the parent of the final documentation commit would miss the actual refactor.

The worktree was clean at audit start. Measurements read the two committed trees through `git ls-tree -r --name-only REV` and `git cat-file --batch`; the current worktree source therefore matched the measured after revision at the start. No checkout was moved.

### Counting rules

- Count every Git-tracked path ending in `.py`, once per revision. Include package initializers, tests, research scripts and packaging Python. Exclude dependency environments, build output, other worktrees, untracked files, archive contents, `.pyi` and Python-like `.spec` files.
- **P (physical LOC):** newline-delimited physical lines, including blank lines, comments and docstrings. A final newline does not add a phantom blank line.
- **N (nonblank/non-comment LOC):** physical lines bearing Python tokens other than whitespace and comments; includes docstrings. Python tokenization preserves `#` inside strings and code preceding inline comments.
- **S (source LOC):** N with formal module/class/function docstrings excluded using the AST. Other string literals remain source. This extra column removes ambiguity about whether documentation strings count as “source lines”.
- Multiline tokens contribute their nonblank physical lines. Counts are line counts, not logical statement counts or cyclomatic complexity.
- Percent change is `100 × (after − before) / before`. “—” means a zero denominator with no change. Size thresholds use strict **greater than**, not greater than or equal to.
- Static structural findings do not establish numerical equivalence. No application modules were imported or executed for measurement. This audit does not replace the validation record in [REFACTOR_NAME_MAP.md](REFACTOR_NAME_MAP.md), which records a full regression with failures/errors.

## 2. Python file counts without double-counting

The only application package trees are `src/emcd_sim` and its nested `src/emcd_sim/gui`. Every tracked production Python file is under `src/emcd_sim`, so `src/` and the inclusive main package have identical counts.

| Disjoint scope | Before files | After files | Absolute change | Change |
| --- | --- | --- | --- | --- |
| emcd_sim excluding gui | 44 | 45 | +1 | +2.27% |
| gui | 60 | 64 | +4 | +6.67% |
| tests/ | 158 | 161 | +3 | +1.90% |
| scripts/ | 49 | 49 | 0 | 0.00% |
| packaging/ | 5 | 5 | 0 | 0.00% |
| Other tracked Python | 2 | 2 | 0 | 0.00% |
| **Overall total** | 318 | 326 | +8 | +2.52% |

| Inclusive package/subset (do not add again) | Before files | After files | Absolute change | Change |
| --- | --- | --- | --- | --- |
| `src/` | 104 | 109 | +5 | +4.81% |
| `src/emcd_sim/` | 104 | 109 | +5 | +4.81% |
| `src/emcd_sim/gui/` | 60 | 64 | +4 | +6.67% |

Arithmetic: before `44 + 60 + 158 + 49 + 5 + 2 = 318`; after `45 + 64 + 161 + 49 + 5 + 2 = 326`. GUI files are included once in the overall count, not added on top of `src/`.

## 3. Python LOC

| Scope | P before | P after | P change | S before | S after | S change |
| --- | --- | --- | --- | --- | --- | --- |
| All tracked Python | 47,150 | 47,431 | +281 (+0.60%) | 40,314 | 40,470 | +156 (+0.39%) |
| Production src/ = emcd_sim (inclusive) | 19,298 | 19,436 | +138 (+0.72%) | 16,423 | 16,456 | +33 (+0.20%) |
| gui subset | 14,210 | 14,297 | +87 (+0.61%) | 12,555 | 12,563 | +8 (+0.06%) |
| emcd_sim outside gui | 5,088 | 5,139 | +51 (+1.00%) | 3,868 | 3,893 | +25 (+0.65%) |
| tests/ | 20,836 | 20,958 | +122 (+0.59%) | 17,732 | 17,834 | +102 (+0.58%) |
| scripts/ | 6,100 | 6,121 | +21 (+0.34%) | 5,337 | 5,358 | +21 (+0.39%) |
| packaging/ (.py only) | 856 | 856 | 0 (0.00%) | 774 | 774 | 0 (0.00%) |
| Other tracked Python | 60 | 60 | 0 (0.00%) | 48 | 48 | 0 (0.00%) |

For the alternate convention that includes docstrings:

| Scope | N before | N after | N change |
| --- | --- | --- | --- |
| All tracked Python | 41,588 | 41,851 | +263 (+0.63%) |
| Production src/ = emcd_sim (inclusive) | 17,260 | 17,392 | +132 (+0.76%) |
| gui subset | 12,856 | 12,944 | +88 (+0.68%) |
| emcd_sim outside gui | 4,404 | 4,448 | +44 (+1.00%) |
| tests/ | 18,020 | 18,130 | +110 (+0.61%) |
| scripts/ | 5,461 | 5,482 | +21 (+0.38%) |
| packaging/ (.py only) | 793 | 793 | 0 (0.00%) |
| Other tracked Python | 54 | 54 | 0 (0.00%) |

Of the production increase of 138 physical lines, 33 are S lines, 99 are additional lines counted only when docstrings are included, and six are additional blank/comment-only lines. The source did not shrink, but much of its small physical increase is documentation.

### A fair comparison of the split calculation/control family

Comparing only a shrunken file hides the newly extracted files. The following groups count each related file once.

| Combined family metric | Before | After | Change |
| --- | --- | --- | --- |
| Python files | 6 | 11 | +5 (+83.33%) |
| Physical LOC (P) | 1,806 | 1,932 | +126 (+6.98%) |
| Source LOC (S) | 1,573 | 1,602 | +29 (+1.84%) |
| Nonblank/non-comment LOC (N) | 1,639 | 1,760 | +121 (+7.38%) |

Before: `gui/{stage_b,emcd_forward,forward_pipeline,generalized_forward,channeling}.py` and `study_geometry.py`.

After: `gui/{calculation_controls,calculation_worker,forward_results,forward_settings,xmcd_source,forward_pipeline,multisite_integration,material_inputs,channeling}.py`, `detector_signals.py` and `study_presets.py`.

This family grew from 1,806 to 1,932 physical lines. Its boundaries and names improved; its total implementation volume did not decrease.

## 4. File additions, removals, renames and substantial rewrites

Git rename detection (`git diff --name-status -M BEFORE AFTER -- '*.py'`) yields:

| Scope | Added files | Deleted files | Renamed files | Modified at same path |
| --- | --- | --- | --- | --- |
| packaging | 0 | 0 | 0 | 1 |
| scripts | 0 | 0 | 0 | 21 |
| src | 5 | 0 | 4 | 32 |
| tests | 3 | 0 | 0 | 83 |
| **Total** | 8 | 0 | 4 | 137 |

There are **149 changed Python file records**. At the raw path-set level, four old paths disappeared and 12 new paths appeared; Git recognizes four of those pairs as renames, leaving eight genuinely additional files. **There is no unmatched whole-Python-file deletion.** Removal of a facade or alias is therefore not evidence that an entire scientific implementation was deleted. Across the Python patch, 1,354 lines were added and 1,073 removed, net +281 P lines.

### Renamed old paths, including splits

Paths in the next table are relative to `src/emcd_sim/`. Similarity is Git's textual rename heuristic, not a scientific-equivalence measurement.

| Old path | New principal path | Git similarity | P before → after | P change | Structural interpretation |
| --- | --- | --- | --- | --- | --- |
| `gui/stage_b.py` | `gui/calculation_controls.py` | 088% | 628 → 570 | -58 (-9.24%) | Control owner renamed; background worker extracted, most widget methods retained. |
| `gui/emcd_forward.py` | `gui/forward_results.py` | 061% | 258 → 158 | -100 (-38.76%) | Mixed owner split among results, settings, source inspection and pipeline; not a simple one-to-one move. |
| `gui/generalized_forward.py` | `gui/material_inputs.py` | 087% | 101 → 103 | +2 (+1.98%) | Mostly a responsibility rename; redundant calculate re-export removed. |
| `study_geometry.py` | `study_presets.py` | 092% | 46 → 46 | 0 (0.00%) | Ni preset named honestly; same-sized implementation and clearer helper names. |

### Newly created Python files

| New path | P | S | Responsibility |
| --- | --- | --- | --- |
| `src/emcd_sim/detector_signals.py` | 48 | 22 | Shared reversal algebra and grouped detector-block reduction. |
| `src/emcd_sim/gui/calculation_worker.py` | 81 | 69 | Extracted Qt worker, progress, cancellation and execution dispatch. |
| `src/emcd_sim/gui/forward_settings.py` | 85 | 55 | Extracted serializable request records and explicit Ni preset. |
| `src/emcd_sim/gui/multisite_integration.py` | 184 | 152 | Extracted bounded grouped Single/Double scheduling and reduction. |
| `src/emcd_sim/gui/xmcd_source.py` | 34 | 25 | Extracted five-column XMCD source inspection. |
| `tests/reference_imports.py` | 52 | 43 | Test-only translation of old dependencies in isolated scientific reference loaders. |
| `tests/test_calculation_api.py` | 23 | 16 | Canonical API input/error assertions. |
| `tests/test_detector_signals.py` | 46 | 39 | Shared detector parity/reduction assertions. |

The five new production files contain 432 physical lines in total. Most of those lines were extracted from existing owners.

### Substantially rewritten or structurally split files

For this audit, “substantial rewrite” means at least 50 added-plus-deleted patch lines and churn of at least 20% of the larger before/after file. This is a descriptive threshold for identifying files to inspect, not a new repository gate and not a claim that equations changed.

| File | P before → after | Added / removed | Churn / larger size | Finding |
| --- | --- | --- | --- | --- |
| src/emcd_sim/gui/forward_pipeline.py | 522 → 368 | 78 / 232 | 59.39% | Substantial restructuring: grouped helpers moved out, uniform admission moved in, canonical dispatcher added. Kernels remain elsewhere. |
| src/emcd_sim/gui/emcd_forward.py → forward_results.py | 258 → 158 | 36 / 136 | 66.67% | Substantial split despite Git rename classification; results body retained while settings, inspection and execution responsibilities move. |
| tests/test_v070_metadata.py | 162 → 106 | 31 / 87 | 72.84% | Maintained test restructuring; does not reduce production complexity. |

`stage_b.py → calculation_controls.py` also has a meaningful worker extraction despite 16.56% patch churn falling below that threshold. Remaining same-path production changes are predominantly caller/import/name migrations plus input checks. For scale, `app.py` changes only five added/five removed lines, `results.py` three/three, and `group_mdff.py` six/six; their large bodies remain.

## 5. The 20 largest Python files before and after

Ranked by physical lines across **all tracked Python**, including tests and packaging; ties use path order. S excludes formal docstrings as defined above. These are independent rankings, not a row-by-row rename map.

### Before: cdb8836388c5ccc5ae7a614b47894c0ab158a824

| Rank | Python file | P | S |
| --- | --- | --- | --- |
| 1 | `src/emcd_sim/gui/app.py` | 664 | 609 |
| 2 | `src/emcd_sim/gui/results.py` | 643 | 604 |
| 3 | `src/emcd_sim/gui/group_mdff.py` | 641 | 584 |
| 4 | `src/emcd_sim/gui/stage_b.py` | 628 | 591 |
| 5 | `src/emcd_sim/gui/atomic_editor.py` | 627 | 574 |
| 6 | `src/emcd_sim/gui/responsive.py` | 614 | 531 |
| 7 | `src/emcd_sim/gui/project_io.py` | 602 | 504 |
| 8 | `packaging/native_acceptance.py` | 598 | 570 |
| 9 | `src/emcd_sim/gui/site_group_editor.py` | 559 | 486 |
| 10 | `tests/test_atomic_parameter_editor.py` | 537 | 447 |
| 11 | `src/emcd_sim/gui/forward_pipeline.py` | 522 | 438 |
| 12 | `src/emcd_sim/gui/project_session.py` | 504 | 465 |
| 13 | `src/emcd_sim/gui/structure_viewer.py` | 486 | 427 |
| 14 | `src/emcd_sim/double_channeling.py` | 427 | 316 |
| 15 | `src/emcd_sim/gui/results_browser.py` | 421 | 404 |
| 16 | `src/emcd_sim/multislice_double_channeling.py` | 419 | 332 |
| 17 | `scripts/finalize_physics_integration_report.py` | 380 | 319 |
| 18 | `src/emcd_sim/gui/manual_l23_editor.py` | 374 | 342 |
| 19 | `src/emcd_sim/gui/propagation.py` | 371 | 321 |
| 20 | `tests/test_nickel_ferrite_site_benchmark.py` | 368 | 306 |

### After: 6817d644d3e9dcc3f06d02d1ad733e36b331d0f2

| Rank | Python file | P | S |
| --- | --- | --- | --- |
| 1 | `src/emcd_sim/gui/app.py` | 664 | 609 |
| 2 | `src/emcd_sim/gui/results.py` | 643 | 604 |
| 3 | `src/emcd_sim/gui/group_mdff.py` | 641 | 584 |
| 4 | `src/emcd_sim/gui/atomic_editor.py` | 627 | 574 |
| 5 | `src/emcd_sim/gui/responsive.py` | 614 | 531 |
| 6 | `src/emcd_sim/gui/project_io.py` | 603 | 505 |
| 7 | `packaging/native_acceptance.py` | 598 | 570 |
| 8 | `src/emcd_sim/gui/calculation_controls.py` | 570 | 529 |
| 9 | `src/emcd_sim/gui/site_group_editor.py` | 559 | 486 |
| 10 | `tests/test_atomic_parameter_editor.py` | 537 | 447 |
| 11 | `src/emcd_sim/gui/project_session.py` | 504 | 465 |
| 12 | `src/emcd_sim/gui/structure_viewer.py` | 486 | 427 |
| 13 | `src/emcd_sim/double_channeling.py` | 427 | 316 |
| 14 | `src/emcd_sim/gui/results_browser.py` | 423 | 404 |
| 15 | `src/emcd_sim/multislice_double_channeling.py` | 419 | 332 |
| 16 | `scripts/finalize_physics_integration_report.py` | 380 | 319 |
| 17 | `src/emcd_sim/gui/propagation.py` | 375 | 319 |
| 18 | `src/emcd_sim/gui/manual_l23_editor.py` | 374 | 342 |
| 19 | `src/emcd_sim/gui/forward_pipeline.py` | 368 | 305 |
| 20 | `tests/test_nickel_ferrite_site_benchmark.py` | 366 | 304 |

The repository maximum is **664 P lines at both revisions (0.00% change)**. The first three files are the same sizes before and after. Source-only rankings exclude the packaging file, the two test files and the research script above; the remaining production files filling out its top 20 are `gui/mdff_usability.py` (340 P, unchanged), `gui/imported_tensor_ui.py` (281, unchanged), `gui/project_configuration.py` (271, unchanged), and `historical_ni.py` (262, unchanged).

## 6. Files over 500 and 1,000 LOC

| Scope / strict threshold | Before | After | Absolute change | Change |
| --- | --- | --- | --- | --- |
| All tracked Python: P > 500 | 12 | 11 | -1 | -8.33% |
| Production src/: P > 500 | 10 | 9 | -1 | -10.00% |
| All tracked Python: P > 1,000 | 0 | 0 | 0 | — |
| Production src/: P > 1,000 | 0 | 0 | 0 | — |
| All tracked Python: S > 500 | 8 | 8 | 0 | 0.00% |
| Production src/: S > 500 | 7 | 7 | 0 | 0.00% |
| All tracked Python: S > 1,000 | 0 | 0 | 0 | — |
| Production src/: S > 1,000 | 0 | 0 | 0 | — |

All files exceeding 500 physical lines at either revision are listed below; none are omitted. Paths beginning `gui/` are under `src/emcd_sim/`.

| File / rename pair | P before | P after | Change | Over 500 after? |
| --- | --- | --- | --- | --- |
| `gui/app.py` | 664 | 664 | 0 (0.00%) | Yes |
| `gui/results.py` | 643 | 643 | 0 (0.00%) | Yes |
| `gui/group_mdff.py` | 641 | 641 | 0 (0.00%) | Yes |
| `gui/stage_b.py → gui/calculation_controls.py` | 628 | 570 | -58 (-9.24%) | Yes |
| `gui/atomic_editor.py` | 627 | 627 | 0 (0.00%) | Yes |
| `gui/responsive.py` | 614 | 614 | 0 (0.00%) | Yes |
| `gui/project_io.py` | 602 | 603 | +1 (+0.17%) | Yes |
| `packaging/native_acceptance.py` | 598 | 598 | 0 (0.00%) | Yes |
| `gui/site_group_editor.py` | 559 | 559 | 0 (0.00%) | Yes |
| `tests/test_atomic_parameter_editor.py` | 537 | 537 | 0 (0.00%) | Yes |
| `gui/forward_pipeline.py` | 522 | 368 | -154 (-29.50%) | No |
| `gui/project_session.py` | 504 | 504 | 0 (0.00%) | Yes |

All nine current oversized production files are in `gui/`. They account for a large part of the maintenance surface that this refactor did not substantially change.

## 7. What was actually removed or consolidated

| Old interface or path | Current disposition | Architectural significance |
| --- | --- | --- |
| `gui.generalized_forward.calculate` | Re-export removed; use `gui.forward_pipeline.calculate`. | Genuine API-surface reduction. In the baseline it already imported the very same `emcd_forward.calculate` callable; this was **not an independent generalized calculation algorithm**. |
| `gui.emcd_forward.calculate` and its `_calculate` delegate | Old module path and delegate removed; canonical dispatcher and private uniform stages now live in `forward_pipeline`. | Removes an accidental mixed-purpose public owner. Baseline `_calculate` already delegated to `forward_pipeline.calculate_prepared`; shared uniform orchestration predates this refactor. |
| Public `forward_pipeline.calculate_multisite` | Replaced by `calculate(..., sites=...)` dispatch to private `_calculate_multisite`. | One supported public request API; the underlying grouped schedule remains (191 → 190 P function span). |
| Repeated uniform/grouped detector even/odd algebra | `detector_signals.reversal_components`, used by result assembly and grouped detector reduction. | A concrete instance of algorithm-block deduplication, not just renaming. |
| `_multisite_detector_data`, `_multisite_single_block`, `_multisite_single_detector_data`, `_multisite_double_detector_data` | Owned by `detector_signals` and `gui.multisite_integration` under accurate names. | Mostly extraction of existing algorithms; uniform/grouped scheduling is not collapsed into one implementation. |
| `gui.emcd_forward._contract` | `gui.forward_results.assemble_forward_result`. | Corrects a misleading name: it assembles already calculated signals, parity, diagnostics and metadata. Mostly relocation with shared parity helper. |
| `gui.stage_b.StageB`, `setup_stage_b` | `CalculationControls`, `setup_calculation_controls`. | Clearer control ownership and worker separation; most widget logic remains. |
| `gui.stage_b.EMCDWorker` import path | Worker moved to `gui.calculation_worker`, with clear class name retained. | Real cohesion improvement. The Qt `run` callback body is unchanged; its internal dispatcher now invokes the canonical API. |
| `Registry`, `IOWorker`, `setup_stage_d` | `ResultRegistry`, `ProjectIOWorker`, `setup_project_workspace`. | Semantic interface clarification, not removal of result indexing, project IO or GUI workflows. |
| Optional-crystal `projected_geometry_for` | `projected_geometry_from_oriented_crystal` requires the actual crystal. | Removes an unused implicit Ni geometry fallback from that API. |
| `ForwardSettings`, `DEFAULT_SOURCE`, `StudyGeometry` generic-looking Ni names | Explicit `NiForwardSettings`, `DEFAULT_NI_SOURCE`, `NickelStudyGeometry` preset owners. | Honest material responsibility and improved explicit inputs; not elimination of a second scientific engine. |
| Mixed-module tensor, energy and orientation re-exports | Maintained callers import the real scientific owner directly. | Fewer accidental interfaces; numerical implementations retained. |

No user-facing dialog, editor, tab or supported workflow was shown to have been eliminated by these changes. “Obsolete GUI interfaces removed” means old Python names/import paths were removed and current consumers migrated; it does not mean the GUI itself became much smaller. Framework callbacks and signals remain.

### Legacy and reference code that remains intentionally

- `historical_ni` has concrete Ni CLI, maintained study/validation and saved-input consumers. Direct requested-energy evaluation and its established tiny-amplitude policy differ from converted-grid interpolation. It is an explicit material provider/preset, not a substitute general-material engine.
- Saved project keys and legacy interpretation remain in loading/schema code. They do not require the old Python facade names.
- `tests/reference_imports.py` translates old names only inside isolated archived scientific reference loaders. This is a new test adapter, not a production fallback.
- Independent depth integration, reference FFT/transition implementations and immutable accepted sources remain useful scientific oracles. Distinct Single/Double models, Bloch/FFT methods and explicit legacy scattering providers should not be collapsed merely to lower a file count.

## 8. Is the forward calculation actually centralized?

**At the public request boundary, yes. At the level of all execution schedules and scientific methods, no. Shared core scientific kernels already existed before this change.**

Current `gui.forward_pipeline.calculate(structure, settings, cfg, ..., sites=...)` explicitly requires a material/model declaration, chooses uniform versus grouped requests, and rejects missing assignments and unsupported option combinations. `gui.calculation_worker.EMCDWorker._run_calculation` calls that boundary rather than selecting separate public uniform/grouped functions. Unknown provider settings fail explicitly in `mdff_providers.prepare_provider`.

The source comparison gives the following paths:

| Layer | Before | After |
| --- | --- | --- |
| Uniform request | `emcd_forward.calculate → emcd_forward._calculate → forward_pipeline.calculate_prepared → channeling.contract` | `forward_pipeline.calculate → _calculate_uniform → _calculate_uniform_prepared → channeling.calculate_detector_signals` |
| Grouped request | Worker/driver calls public `forward_pipeline.calculate_multisite`. | Canonical `calculate` dispatches to private `_calculate_multisite`. |
| Grouped detector scheduling | Helpers inside `forward_pipeline`. | Extracted `gui.multisite_integration` helpers. |
| Tensor/source preparation | Shared provider boundary with historical Ni or declared source provider. | Same boundary, with stricter explicit-setting selection and more accurate owners. |
| Scientific propagation/contraction | Shared Single/Double and Bloch/FFT kernel modules. | Same scientific kernel modules. |

Deleting the old one-line delegation does not reduce the uniform path's overall four-stage request/orchestration/scheduler depth: a public dispatcher was added while the delegate was removed. The improvement is the supported API and ownership, not a dramatic flattening of the call chain.

Uniform and grouped paths still have separate energy/support scheduling, source normalization, group accumulation and detector integration. `channeling.calculate_detector_signals` and `multisite_integration.integrate_*_channeling_spectrum` are not mere compatibility adapters. They retain substantive production logic. Some reduction concepts overlap, but group semantics and floating-point summation order differ, so their presence alone does not demonstrate dispensable duplicate engines.

No removal of independent Cr- or Fe3O4-specific production kernel files was found. Source-backed cases already supplied tensors/sites to shared kernels. Eight representative scientific modules are unchanged between the two revisions: `atomic_dipole.py`, `atomic_ionization.py`, `mdff_tensor.py`, `double_channeling.py`, `multislice_double_channeling.py`, `single_channeling_tensor.py`, `scattering.py` and `physical_elastic.py`. The non-GUI grouped channeling files each change only one import line.

There remain independent implementations for different numerical methods, physical models and validation references. This is compatible with a shared production engine and should not be represented as redundant material-specific implementations.

## 9. Physics and calculation services still under gui

**Yes: substantial scientific calculations and model orchestration remain in the GUI package.** These files are mostly non-widget services, which limits what the namespace alone proves; their responsibilities nevertheless belong naturally at a scientific/application-service boundary accessible without the presentation layer.

| Current module (src/emcd_sim/) | P | Remaining scientific/service responsibility |
| --- | --- | --- |
| `gui/forward_pipeline.py` | 368 | Uniform/grouped execution, tensor/provider preparation, depth coherence, propagation selection, group weighting and physical-result assembly. |
| `gui/channeling.py` | 255 | Energy/pixel scheduling, Single/Double response calls, aperture reduction, FFT preparation and scientific diagnostics. |
| `gui/multisite_integration.py` | 184 | Group tensor contraction, multiplicity-weighted accumulation and bounded energy/aperture integration; imports private backend contraction/result helpers. |
| `gui/propagation.py` | 375 | Physical projected geometry, incoming wave propagation, coherence/diagnostics and numerical/memory validation; also comparison/export duties. |
| `gui/geometry.py` | 166 | Builds oriented geometry and elastic model inputs from a complete structure. |
| `gui/provider_preparation.py` | 88 | Source energy-grid resolution, tensor preparation, material eligibility and site preparation. |
| `gui/forward_results.py` | 158 | Detector reversal observables, normalization/correction, selected-edge metrics, diagnostics and export. |

This is more than a naming concern. Non-GUI scientific modules import those service owners: `mdff_providers → gui.material_inputs/gui.forward_settings/gui.provider_preparation`, `historical_ni → gui.geometry`, and grouped backend contraction modules `→ gui.material_inputs`. Several propagation kernels import `gui.memory_budget`. These are real dependency directions, although they do not all import Qt or construct widgets.

General-material inputs remain coupled to the Ni-shaped request schema: `ImportedSettings(NiForwardSettings)` and `MultiSiteForwardSettings(NiForwardSettings)` override material fields rather than deriving from a neutral base. The current provider boundary makes the Ni preset explicit and rejects unknown inputs; inheritance itself is therefore **not proof of silent Ni substitution**, but it leaves avoidable conceptual coupling.

A lower-level residual is `channeling.calculate_detector_signals(..., ionization_sites=None)`, which selects `historical_ni_site_phase_matrix` when sites are absent. The canonical uniform path supplies `provider.sites(structure)`: declared providers return explicit `IonizationSites`, and the explicit Ni provider returns `HistoricalNiSites`. Thus the residual optional argument does not establish a silent fallback on the inspected canonical path, but the lower-level API still carries a material-specific default worth reviewing separately.

The production FFT path uses the common projected-potential/incident-field implementation; the Ni FFT convenience/reference should not be mistaken for a second production implementation.

## 10. Coupling, duplication and maintenance complexity

### Literal internal import graph

Graph nodes are tracked `src/` modules. Edges are unique directed literal internal imports, including lazy imports inside functions and resolved relative imports. Self-edges, external dependencies, dynamic import strings and implicit package-initializer execution are excluded. A top-level edge is syntactically outside a function, including imports behind guards; “deferred-only” means the edge occurs only inside functions.

| Metric | Before | After | Absolute change | Change |
| --- | --- | --- | --- | --- |
| Production module nodes | 104 | 109 | +5 | +4.81% |
| Unique internal import edges | 479 | 495 | +16 | +3.34% |
| Top-level edges | 248 | 260 | +12 | +4.84% |
| Deferred-only edges | 231 | 235 | +4 | +1.73% |
| GUI → non-GUI edges | 104 | 115 | +11 | +10.58% |
| Non-GUI → GUI edges | 10 | 11 | +1 | +10.00% |
| Cyclic strongly connected groups | 4 | 4 | 0 | 0.00% |
| Modules in cyclic groups | 37 | 37 | 0 | 0.00% |
| Largest cyclic group (modules) | 26 | 26 | 0 | 0.00% |
| Maximum module fan-out | 23 | 25 | +2 | +8.70% |
| Maximum module fan-in | 21 | 19 | -2 | -9.52% |
| MainWindow/app module fan-out | 18 | 18 | 0 | 0.00% |

Average outgoing edges per module falls slightly, 4.61 → 4.54, because the implementation is split into more modules. That does not offset the increase in total edges or demonstrate reduced layering dependencies. Maximum fan-in does improve, consistent with splitting the old `emcd_forward` hub; maximum fan-out grows.

| Cyclic group | Before size | After size | Interpretation |
| --- | --- | --- | --- |
| Mixed provider/geometry/calculation/results/project services | 26 | 26 | Membership changes. `forward_pipeline` and backend `multisite_double_channeling` leave this group; extracted settings/results/source modules enter it. A useful local boundary improvement without removal of the large dependency knot. |
| Main window and GUI acceptance entry points | 5 | 5 | Same group; lazy launch/acceptance dependencies remain. |
| Elastic providers / legacy atomic factors / scattering | 3 | 3 | Same group. |
| Atomic ionization / imported MDFF / manual L2,3 | 3 | 3 | Same group. |

These are cycles in the static dependency graph, not a claim that Python currently fails to import them. Lazy imports can make such relationships executable while preserving architectural coupling.

The control owner still has the largest fan-out: `stage_b` 23 dependencies becomes `calculation_controls` 25. `forward_pipeline` grows 20 → 21; `app` remains at 18. The refactor redistributed the old mixed hub rather than globally decoupling the program.

### Bodies and duplication

| Production definition metric | Before | After | Absolute change | Change |
| --- | --- | --- | --- | --- |
| Function definitions, including nested | 1,077 | 1,078 | +1 | +0.09% |
| Class definitions | 92 | 92 | 0 | 0.00% |
| Top-level functions/class methods catalogued | 1,009 | 1,010 | +1 | +0.10% |
| Catalogued function spans > 100 P lines | 12 | 12 | 0 | 0.00% |
| Catalogued function spans > 200 P lines | 1 | 1 | 0 | 0.00% |
| Qualifying exact whole-body duplicate groups | 0 | 0 | 0 | — |

For the 1,010 current non-nested function/method bodies, AST comparison excluding leading docstrings finds **888 (87.92%) unchanged at the same path/name**, **57 (5.64%) matching a baseline body elsewhere**, and **65 (6.44%) changed or newly unmatched**. In total, 945 bodies (93.56%) have an exact baseline-body match. Signatures, decorators and surrounding context are not included; a match does not prove equivalent runtime behavior. Matches elsewhere can include boilerplate rather than an intentional move.

Concrete intact-body moves include `EMCDWorker.run`, `source_for`, the renamed selected-edge metric function, several calculation-control methods, and `contract_single_channeling_block`. This supports a conclusion of mostly reorganization with targeted changes, rather than widespread implementation simplification.

The exact duplicate screen compares complete AST bodies while retaining internal identifiers/literals; candidates must span at least 12 P lines, five statements and 80 AST nodes. No qualifying duplicate group exists at either revision. This narrow result does **not** rule out duplicated blocks, near-duplicates or algorithms expressed differently. In particular, the removed detector reversal block is a partial-body duplicate and is established by direct source comparison, not this whole-function screen.

Long bodies remain: `propagation.numerical_info` is 199 P lines at both revisions; grouped orchestration is 191 → 190; `multisite_double_channeling._contract_multisite_double` remains 158; project loading/restoration and layout methods remain over 100. The largest catalogued function remains the 227-line desktop acceptance `run`, which is verification infrastructure rather than a scientific kernel.

### Architectural versus editorial changes

| Change | Classification | Net maintenance effect supported by the comparison |
| --- | --- | --- |
| Canonical public request dispatch and removal of obsolete aliases | Architectural/API improvement | Fewer supported forward call routes and clearer input/error behavior. |
| Worker extracted from calculation controls | Responsibility/cohesion improvement | Background lifetime/cancellation can be read independently of widget construction. |
| Shared detector reversal helper | Actual algorithm-block deduplication | One owner for parity/difference equations used in both result paths. |
| Settings/source/results/group integration extraction | Mostly decomposition | Easier local navigation; more files/import edges and most bodies retained. |
| Stage, registry, workspace and preset renaming | Semantic clarity | Improves intent; does not by itself reduce dependencies or algorithms. |
| Shared scientific kernels | Largely pre-existing architecture | Preserved capability, not a new engine consolidation attributable to this refactor. |
| Large GUI modules and cyclic service dependencies | Little overall improvement | Oversized-module count drops by one; major dependency groups and long-function counts persist. |

## 11. Candidates for future focused cleanup (not performed)

| Candidate | Current size / evidence | Appropriate focused direction |
| --- | --- | --- |
| `gui/app.py` | 664 P; unchanged size, fan-out 18 | Separate application composition and workflow wiring where a concrete responsibility boundary exists. |
| `gui/results.py` | 643 P; unchanged | Separate plot/data preparation from widget actions and export interaction. |
| `gui/group_mdff.py` | 641 P; unchanged | Separate group input state/provider validation from editor behavior. |
| `gui/atomic_editor.py` | 627 P; unchanged | Consolidate editor/model responsibilities using the existing editor model, without merging distinct material models. |
| `gui/responsive.py` | 614 P; unchanged; 122-line reflow | Review layout responsibility and long methods only where behavior can be isolated; file size alone does not justify a split. |
| `gui/project_io.py` | 603 P; 131-line load, 122-line save | Separate schema/compatibility reconstruction, file IO and Qt-facing operations while preserving saved-project semantics. |
| `gui/calculation_controls.py` | 570 P; maximum fan-out 25 | Split state/preflight coordination from widget construction if the resulting interfaces reduce dependencies. |
| `gui/site_group_editor.py` | 559 P; unchanged | Separate group-editing state/validation from presentation. |
| `gui/project_session.py` | 504 P; unchanged; 122-line restoration | Clarify session restoration versus widget population, preserving all saved-run workflows. |
| Scientific services currently under `gui/` | Pipeline, channeling, propagation, providers and integration | Establish a neutral calculation/service boundary; migrate actual ownership/import direction, rather than only renaming the package. |
| Uniform/grouped scheduler reductions | Separate substantive schedules with overlapping concepts | Investigate small, equivalent reduction/preparation primitives; consolidate only after demonstrating preserved order, normalization, group semantics and numerical results. |
| Ni-derived general settings and optional lower-level site default | Explicit guards work, but schema/API still carries historical material shape | Introduce a neutral request schema and explicit site policy if justified, preserving compatibility in loaders and intentionally supported low-level consumers. |
| Backend/provider cyclic groups and private helper imports | Four groups/37 modules; grouped GUI integration imports backend private helpers | Use small explicit provider/contraction interfaces where they remove mutual dependencies; preserve independent scientific references. |

`packaging/native_acceptance.py` (598 P) and `tests/test_atomic_parameter_editor.py` (537 P) also exceed 500 lines. Their sizes are verification-maintenance concerns, not evidence of duplicate production physics; they should not be pruned simply to improve application metrics.

These are software-organization candidates. Extending physical approximations, supporting new source models/conditions, or increasing scientific generality beyond the existing validated envelope requires separate scientific development and validation. This audit neither implements that work nor treats distinct models/references as expendable duplication.

## Final assessment

**The refactor genuinely improved API clarity and local responsibility boundaries, with a small amount of real deduplication. It did not materially shrink or broadly decouple the application.** Its strongest result is a clearer route into an already substantially shared engine. File extraction and renaming account for much of the visible simplification; oversized GUI owners, mixed scientific/presentation layering, separate substantial schedules and cyclic dependencies remain suitable targets for later, narrowly scoped work.

