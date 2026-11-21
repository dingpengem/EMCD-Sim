# Phase 3D-2A: scientific data and geometry ownership

## A. Scope and source identity

Starting commit: `836c0deff082b729548eacdd02dfb6674163315c`, a clean successor
of Phase 3D-1 implementation `f29d7bec072b54f13b552ae3e7db9db4cdbb8ea1`.
Working directory and worktree root are both
`C:/Users/peng863/EMCD-Sim/.worktrees/windows-adaptive-compute`, branch
`refactor/physics-readability`. Ancestry and the existing 147-entry source map
were checked before editing. No checkout move or reset occurred.

Final implementation commit: `c2790aa0820581775c84f28b7033bcc376b9a44f`.
The registration/report successor is identified in Git history and the completion
response; it changes no application or scientific-test implementation.

**Focused GO.** Both scientific geometry and result-data services have genuine
non-GUI ownership; all required scientific checks and affected rechecks pass.
This is not full-suite, native EXE or release acceptance.

This phase gives significant scientific data services genuine non-GUI owners.
It does not relocate forward orchestration, channeling execution, propagation
planning or multisite scheduling. The exact public
`emcd_sim.gui.forward_pipeline.calculate` signature and behavior remain.
No second calculation API, engine implementation or organizational package tree
is introduced. The existing flat scientific package receives the new owners.

Prior Phase 3A–3D-1 reports, the active physics/name maps, numerical-contract
corrections and regression recovery remain the earlier evidence. Actual scientific
comparison source remains `cdb8836388c5ccc5ae7a614b47894c0ab158a824`.

## B. Responsibility and dependency decisions

| Responsibility | Previous owner | New/current owner | Remaining dependencies |
|---|---|---|---|
| ASE-backed structure and geometry settings | `gui.geometry.Structure`, `Settings` | `structure_geometry`, one definition of each class | ASE, existing scattering/elastic models; historical explicit Ni record defaults retained |
| Orientation, finite beam basis, projected cell, Bragg geometry | `gui.geometry` | `structure_geometry` | Existing crystal/crystallography/projected-geometry and physical elastic implementations |
| Structure snapshots, restoration and matching | `gui.geometry` | `structure_geometry` | Existing ASE ordering, fields, arrays, tolerances and validation |
| Index-text parsing and GUI elastic preview orchestration | `gui.geometry` | Retained in `gui.geometry` | Calls scientific geometry; no old scientific class/function facade is added |
| Scientific result assembly and selected-edge metrics | `gui.forward_results` | `forward_results` | Neutral geometry, detector observables, source inspection and provenance |
| Scientific method views, including BW–MS differences | `gui.forward_results.method_result` | `forward_results.method_result` | Existing dictionaries/NumPy arrays; no new result schema |
| Denominator masks, signed percentages and benchmark spectral arrays | `gui.signal_normalization`, `gui.prb_benchmark` | Existing `detector_signals` | Pure NumPy; original constants and numerical bodies |
| Source identity and optional original-Ni companion audit | `gui.xmcd_source` | `xmcd_source` | Existing WIEN2k source/audit, unchanged explicit source input and optional preset audit |
| Build/source provenance and resource locations | Part of `gui.runtime` | `provenance` | Standard library and package versions; existing frozen/source behavior |
| Writable GUI directories and logging | `gui.runtime` | Retained in `gui.runtime` | Desktop paths/logging and neutral build information |
| Group/total data selection and UI labels | `gui.multisite_results` | Retained for this phase | Mixed selection/label responsibilities; not a second calculation engine |
| Saved projects and configuration codecs | `gui.project_io`, `project_configuration`, `multisite_project` | Retained; import neutral geometry/results | Existing JSON/NPZ schemas, settings records, source association and accepted/draft state |
| Memory admission/reservations and worker policy | `gui.memory_budget`, `parallel_resources` | Deferred, unchanged | Pinned kernel consumers and shared reservation/thread state |

Geometry moves first. All maintained named imports, module-alias consumers,
calculation/persistence callers, test spies and current analysis inventories use
the actual new owner. GUI parsing/preview and the remaining readout/rendering
functions retain their useful implementations. `gui.forward_results` and
`gui.xmcd_source` are removed; no forwarding files replace them.

The result dependency closure requires more than a file rename. Build provenance,
source inspection and the existing percentage mathematics previously lived under
GUI names. Moving their pure responsibilities removes those GUI imports from the
result owner. Display settings, peak/window choices, readout formatting, Qt widgets,
plotting, export and project I/O remain outside the scientific result module.
`gui.prb_benchmark` and `gui.signal_normalization` consume the shared detector
operations for their own work; they contain no copied percentage algorithm.

Static comparison found **21 moved function/class ASTs identical apart from
imports**, including geometry, snapshots, result assembly, method selection,
source audit and percentage/mask mathematics. Provenance changes only source-file
locations and inventory coverage, not physical metadata or saved-array formulas.
Task evidence is under ignored `build/phase3d2a/`.

### Class identity and persistence

Supported project persistence uses JSON record fields and NumPy arrays with
`allow_pickle=False`; it stores no Python module identity for `Structure` or
geometry `Settings`. The consumer audit found no supported pickled geometry
objects or dispatch requiring their old module names. Both definitions therefore
move together and all current constructors/loaders import the same new classes.
Their `__module__` changes; there are no duplicate production classes or aliases
asserted to preserve the old Python import path.

Their fields/defaults, ASE ordering/site indices, coordinates, cell/PBC,
crystallographic identity, snapshot contents, error checks and tolerances remain.
`NiForwardSettings`, `ImportedSettings`, `ProviderSettings`, their inheritance and
historical serialized fields stay in their existing modules. Material-specific
default cleanup is explicitly outside this phase.

### Resource deferral

`double_channeling.py` and `multislice_double_channeling.py` import
`gui.memory_budget.reserve_memory` and are strictly pinned numerical kernels.
`multislice_reference.py` and `projected_potential.py` also consume the same service.
Moving it would require altering pinned consumers or retaining a forwarding
owner for the shared reservation state. Neither is justified here. No memory
budget, threshold, estimate, worker admission, BLAS behavior, cancellation or
reservation implementation is changed. Parallel/resource policy remains a
Phase 3D-2B boundary to resolve deliberately.

## C. Headless verification

The existing Ni, Fe and Fe₃O₄ fixture tests now reject the entire
`emcd_sim.gui` namespace as well as PySide/PyQt imports. Fresh processes actually
construct structures, restore ordinary/rich snapshots, preserve original sites,
ASE arrays/tags and metadata, prepare geometry and projected cells, check Bragg
alignment and reject invalid geometry/snapshots. Their allowed targets are
Ni `(200)`, Fe `(110)`, and Fe₃O₄ `(220)` in the existing `[001]` test geometry.

The existing Cr, Fe₃O₄ and Fe/Ni stored-result fixtures are saved in the parent
and reopened in fresh processes. Before persistence imports, the scientific
`forward_results` owner must import with the whole GUI namespace forbidden.
The test then permits existing configuration/persistence namespaces while still
rejecting all Qt/presentation/execution dependencies. It exercises method views,
Save/Open, exact metadata, shape/dtype, all stored arrays, and NaN/Inf locations.
Result viewing never invokes propagation or alternative recomputation.

All eight established Phase 3D-1 cases passed through the unchanged canonical
API: Ni and explicit synthetic ordered BCC Cr, each with BW/FFT Single/Double
Channeling. Existing archived Ni and independent Cr event/reversal/normalization
assertions, selected solver identity, dimensions, finite/undefined masks, source
provenance and resource lifecycle checks remain. The Cr fixture is a synthetic
software benchmark, not a bulk-Cr magnetic-order or absolute spectroscopy model.

The new scientific owners contain no GUI imports. Full package independence is
not claimed for project loading or the canonical forward engine: historical
settings/configuration codecs and the orchestration/resource services still have
GUI namespace locations. Source-mode provenance deliberately reads the existing
GUI scientific/export source inventory; that is a retained build-layout and
traceability dependency, not a widget import. Frozen/stored provenance is not
rewritten.

## D. Structural measurements

The same Phase 3A–3D-1 AST methodology includes literal imports inside functions.
Production is `src/**/*.py`, counted once. GUI is a subset of production; GUI plus
non-GUI counts equal the total, without double-counting nested directories.

| Metric | Before | After | Absolute / percentage change |
|---|---:|---:|---:|
| Production Python files | 107 | 109 | +2 / +1.87% |
| GUI Python files | 62 | 60 | −2 / −3.23% |
| Non-GUI Python files | 45 | 49 | +4 / +8.89% |
| Physical production lines | 19,519 | 19,571 | +52 / +0.27% |
| Nonblank, noncomment lines including docstrings | 17,461 | 17,482 | +21 / +0.12% |
| Source LOC excluding formal docstrings | 16,514 | 16,527 | +13 / +0.08% |
| Unique internal import edges | 482 | 493 | +11 / +2.28% |
| Cyclic dependency groups | 4 | 4 | 0 / 0% |
| Modules in cycles | 14 | 14 | 0 / 0% |
| Largest SCC | 5 | 5 | 0 / 0% |
| Non-GUI → GUI edges | 8 | 8 | 0 / 0% |
| Core scientific-data → presentation/readout edges | 1 | 0 | −1 / −100% |
| Shared channeling/propagation cyclic component | Absent | Absent | Preserved |

The data/readout measure compares geometry and result assembly owners before and
after. Readout/presentation targets include `gui.prb_benchmark`,
`gui.signal_normalization`, `gui.result_presentation`, `gui.results` and
`gui.responsive`. The sole old edge is `gui.forward_results -> gui.prb_benchmark`,
a mixed mathematics/readout owner. This is not evidence of a former Qt import:
Phase 3D-1 already demonstrated Qt-free execution. All five neutral owners
(`structure_geometry`, `forward_results`, `xmcd_source`, `provenance`,
`detector_signals`) now have zero GUI imports, including inside functions.

Exactly **56 unique edges are removed and 67 added**; Appendix H lists the full
difference. Many are owner rewiring. The net increase comes from splitting mixed
modules: GUI parsing/preview, readouts and logging remain useful implementations
and now import their neutral counterparts. Some callers need both remaining GUI
operations and extracted data operations. These are explicit dependencies, not
imports hidden behind runtime calls to improve metrics.

Production file count, source LOC and total import count do not decrease. The
benefit is actual ownership and dependency direction: geometry/result operations
can be reused without GUI namespace imports, and readout formatting no longer
supplies their mathematics. Each moved operation still has one implementation.

The four unchanged SCCs are the five-module GUI app/acceptance cluster;
`elastic_providers`/`legacy_atomic_factors`/`scattering`;
`atomic_ionization`/`imported_mdff`/`manual_l23`; and
`gui.multisite_project`/`project_configuration`/`project_io`. No new cycle appears.
The eight retained non-GUI → GUI edges are the CLI launcher; four kernel memory
imports; `mdff_providers` imports of `gui.forward_settings` and
`gui.material_inputs`; and `multisite_double_channeling -> gui.channeling`.

The existing low-level `geometry.py` supplies wavelength, microscope and detector
primitives used by physical models. Putting higher-level ASE structure/model
construction into that owner would reverse model responsibilities. The focused
`structure_geometry` module follows the existing flat scientific package and
does not add an empty package, forwarding layer or universal engine service.

## E. Scientific verification and evidence

| Evidence stem under build/phase3d2a/ | Actual result | Driver seconds |
|---|---|---:|
| geometry | 7 passed; 3 invalid-target test failures | 24.953 |
| geometry-targets | All 3 headless geometry cases passed | 11.968 |
| results | 33 passed; 1 existing skip; 6 missing-import readout failures | 30.843 |
| readout-fix | All 6 affected readouts passed | 2.844 |
| headless | All 8 canonical scientific calculation cases passed | 22.031 |
| exact | 22 cases / 2,294 arrays exactly equal | 13.031 |
| science | 71 passed; 7 source-map validation failures; all six numerical comparisons passed | 32.375 |
| registration-fix | 8 source/kernel controls passed | 13.734 |
| workflows | 159 passed; 14 skips; 2 stale expectations; 3 already-covered geometry cases deselected | 456.515 |
| workflow-fix | Both affected cases passed | 7.000 |
| authentication | 152 passed; 1 skip; 1 stale mutation target | 198.797 |
| mutation-target-fix | Same geometry mutation rejected at the new owner | 0.984 |
| final-map | 2 existing positive/map-mutation controls passed after recording the implementation commit; already counted above | 29.813 |

Deduplicating pytest node IDs and taking each final affected recheck gives
**465 distinct cases: 449 passed, 16 existing skips, zero unresolved failures**.
This is combined focused coverage, not one clean full-suite invocation. The exact
22-case driver is separate from those pytest totals. Skips comprise two unavailable
saved Ni/reference projects, eight optional existing Stage D visualization cases,
five opt-in native workflows and one optional external 160-array unit evidence
check. They are not relabeled as passes.

All six unchanged numerical-contract nodes passed in science.xml:

- test_double_cancellation::test_bw_unchanged_and_depth_cancel[numerical]
- test_double_cancellation::test_full_spectrum_unchanged[bloch]
- test_double_cancellation::test_full_spectrum_unchanged[both]
- test_multisite_scientific_validation::test_bcc_cr_independent_events_and_symmetry[unequal-mdff-double-bloch]
- test_single_element_ni_compatibility::test_original_ni_all_numeric_arrays_exact[double-xmcd]
- test_single_element_ni_compatibility::test_original_ni_all_numeric_arrays_exact[double-atomic]

Independent multisite event, reversal/group-normalization, MDFF/tensor, detector,
mask/percentage and resource/cancellation execution checks pass. GUI/project
coverage includes available historical schemas, selected-run restoration, source
relocation/authentication, accepted/draft material state, display/export, CIF/site
identity and source/frozen resources. Historical workflow support was inspected:
it retains authenticated historical geometry/classes and unchanged extracted
support bodies; no new production compatibility route is required.

The seven science-group failures were source-registration validation errors: the
updater initially omitted the renamed result owner. It was corrected in the
existing closed map. The later GUI failures were an old import AST expectation
and an inventory assertion still expecting three files; the corrected test checks
required coverage and digest format without forbidding additive entries. The
final authentication failure used the old GUI path for an unchanged geometry
mutation; the target moved, and the same rejection assertion passes.

No failure required changing an equation, kernel, array, reference, scientific
setting, tolerance or error budget. Static review additionally confirmed 26
existing engine/input function/class ASTs unchanged apart from imports, and the
original percentage constants and mask policy unchanged. The later result-module
docstring edit only qualifies the GUI export/presentation owner names.


The unchanged comparison driver file reported **22 cases passed / 2,294 arrays
exactly equal** against `cdb8836388c5ccc5ae7a614b47894c0ab158a824`, including physical
metadata and edge metrics. Its obsolete GUI result import is translated in memory
by the existing test-only `reference_imports.relocate_reference_imports`; cases,
assertions, calculations, reference arrays and comparison contracts are unchanged.
No production compatibility alias is retained for that identified reference
consumer. The already-recorded older-reference XMCD/atomic roundoff deltas are
not new discrepancies.

Failed evidence remains intact. Initial geometry isolation tests correctly
rejected a test `(100)` target outside the selected reciprocal lattice; only test
targets were corrected. Result/readout checks exposed an omitted import of the
moved `benchmark_spectra`; the GUI consumer was corrected without altering the
algorithm, references or tolerances. All affected rechecks are recorded below.

## F. Authentication, compatibility and traceability

The existing reviewed current-source map and its loader pin were updated, not historical
archives, kernel/data pins or previous-source payloads. The original
`emcd_forward.py` relocation now identifies root `forward_results.py`; the source
audit relocation and newly split geometry/provenance owners remain in the same
closed registration mechanism. Existing positive/mutation and offline controls
passed for the new owners. The current map contains 168 entries; comparison
with the starting map confirms every existing historical metadata field and
authenticated previous-source payload remains intact.

The existing runtime inventory retains its prior GUI keys and adds
`structure_geometry.py` because previously traced geometry bodies moved there.
Current analysis inventories follow moved result/geometry bodies too. This
preserves required coverage without a new hash framework or frozen baseline.
Frozen `build_info.json` and previously saved provenance are returned unchanged.

Project schemas, field names, original/effective sources, accepted/draft state,
remembered resource requests and selected-run associations remain. Archived
import translations serve identified independent references and preserve original
source authentication. They are test/research support, not a production facade.


| Interface decision | Concrete consumer and reason |
|---|---|
| Retain exact gui.forward_pipeline.calculate | Required public API, current GUI and maintained scripts/tests; no second calculation API |
| Remove old scientific definitions from gui.geometry | Current consumers use structure_geometry; supported JSON/NPZ stores fields, not Python module names |
| Remove gui.forward_results and gui.xmcd_source | Maintained consumers use neutral owners; archived imports translate only in existing reference support |
| Retain gui.geometry.indices and preview | Actual GUI parsing/preview callers; meaningful implementation remains, not a facade |
| Retain GUI display/readout and desktop logging/path interfaces | Concrete UI/desktop callers consume neutral operations; no copied percentage mathematics |
| Retain Ni-derived settings records and project loaders | Existing schema/editor/provider consumers and type-sensitive dispatch; inheritance and fields unchanged |
| Retain memory/reservation and scheduling owners | Pinned consumers and single process-wide state; policy migration outside scope |
| Retain reference-import translations | Authenticated scientific reference sources and unchanged 22-case driver; no production alias |

The settings records' remaining GUI location is a future ownership decision,
not proof that JSON requires those Python module paths. Dispatch, editors and
schema consumers must migrate together. Setuptools discovers the new flat modules
under src; maintained native/analysis imports and inventories were migrated. ASE
and spglib remain in the existing GUI extra: headless tests use those installed
scientific dependencies with Qt/GUI imports blocked. No separate minimal headless
distribution or installation extra is introduced; packaging separation is distinct
from changing scientific models.

Git diff --check passes. No full regression, EXE build/replacement, application
version change, push, merge, tag or publication was performed. The final
report/registration successor records the verified code commit and reruns the
existing positive/map-mutation controls for that metadata-only source pointer.

## G. Phase 3D-2B handoff

1. Resolve the settings and resource boundaries before moving the remaining
   forward engine. `gui.forward_settings` and `gui.material_inputs` retain
   Ni-derived record identities; do not treat that as a reason to select Ni for
   an explicit non-Ni request. Existing schema loading must continue accepting
   historical records.
2. Review kernel memory imports and the single reservation state with strict
   source authentication. Preserve actual policy, worker plans, cancellation and
   BLAS/thread guards; a namespace change is not authority to change kernel pins.
3. Move channeling and propagation only after those leaf dependencies are ready.
   Their Phase 3D-1 one-way planning-bound dependency remains; no cycle is restored.
4. Move `multisite_integration` with its distinct energy/support schedule and
   independent-site accumulation. Group result additions remain with that
   orchestration, not a competing material engine.
5. Move `forward_pipeline` last, retaining one canonical public entry and both
   established schedules. Resolve source-mode inventory paths as actual owners
   move. The remaining `gui.multisite_results` mixes data projections/selection
   labels and should receive a focused consumer-based split, not wholesale
   rendering migration into the scientific package.

None of those engine migrations, new physics, full regression, Windows EXE
rebuild, version change, push, merge, tag or publication belongs to this phase.

## H. Exact unique import-edge differences

All source/target names below are within emcd_sim (emcd_sim alone means its package
initializer). Each row lists all removed/added targets for that exact source.
Unlisted edges are unchanged. Deferred literal imports are included.

| Source module | Removed targets | Added targets |
|---|---|---|
| forward_results | ? | detector_signals, elastic_providers, emcd_angular_plots, geometry, mdff_edges, provenance, structure_geometry, xmcd_postedge_normalization, xmcd_source |
| gui.app | ? | provenance, structure_geometry |
| gui.atomic_editor | gui.runtime | provenance |
| gui.calculation_controls | gui.geometry, gui.runtime, gui.xmcd_source | provenance, structure_geometry, xmcd_source |
| gui.cancellation_acceptance | gui.geometry, gui.runtime | provenance, structure_geometry |
| gui.channeling | gui.geometry | structure_geometry |
| gui.compare_results | gui.forward_results | forward_results |
| gui.component_display | ? | detector_signals |
| gui.desktop_acceptance | gui.geometry, gui.runtime | provenance, structure_geometry |
| gui.forward_pipeline | gui.forward_results, gui.geometry | forward_results, structure_geometry |
| gui.forward_results | detector_signals, elastic_providers, emcd_angular_plots, geometry, gui.geometry, gui.prb_benchmark, gui.runtime, gui.xmcd_source, mdff_edges, xmcd_postedge_normalization | ? |
| gui.forward_settings | gui.runtime | provenance |
| gui.geometry | crystal, crystallographic_sites, crystallography, elastic, geometry, projected_geometry, scattering | structure_geometry |
| gui.group_mdff | gui.xmcd_source | xmcd_source |
| gui.multisite_project | gui.geometry | structure_geometry |
| gui.normalization_export | ? | detector_signals |
| gui.numerical_settings | gui.geometry | structure_geometry |
| gui.parallel_acceptance | gui.runtime | provenance |
| gui.prb_benchmark | ? | detector_signals |
| gui.project_collection | gui.geometry | structure_geometry |
| gui.project_configuration | gui.geometry | structure_geometry |
| gui.project_io | gui.forward_results, gui.geometry, gui.prb_benchmark, gui.runtime | detector_signals, forward_results, provenance, structure_geometry |
| gui.project_session | gui.geometry, gui.runtime | provenance, structure_geometry |
| gui.propagation | gui.forward_results, gui.geometry | forward_results, structure_geometry |
| gui.result_export | gui.forward_results, gui.prb_benchmark | detector_signals, forward_results |
| gui.result_presentation | gui.forward_results | forward_results |
| gui.results_browser | gui.geometry, gui.xmcd_source | provenance, structure_geometry, xmcd_source |
| gui.runtime | emcd_sim | provenance |
| gui.scientific_acceptance | gui.geometry, gui.runtime | provenance, structure_geometry |
| gui.signal_normalization | ? | detector_signals |
| gui.unified_elastic_acceptance | gui.runtime | provenance, structure_geometry |
| gui.xmcd_source | gui.forward_settings, wien2k_source_audit, wien2k_xmcd | ? |
| provenance | ? | emcd_sim |
| structure_geometry | ? | crystal, crystallographic_sites, crystallography, elastic, elastic_providers, geometry, physical_elastic, projected_geometry, scattering |
| xmcd_source | ? | provenance, wien2k_source_audit, wien2k_xmcd |
