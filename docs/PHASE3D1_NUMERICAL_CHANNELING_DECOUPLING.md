# Phase 3D-1: numerical planning and channeling decoupling

## A. Scope and decision

Starting commit: `604902313e4eb76a900a5f163ba64bbedcda5ee7` on
`refactor/physics-readability`, in
`C:/Users/peng863/EMCD-Sim/.worktrees/windows-adaptive-compute` (both working
directory and Git worktree root). The starting tree was clean and contains
Phase 3C implementation `cb20b718b26a75368b21b1151622311717e06704`.
The checkout was neither moved nor reset.

Final implementation commit: `f29d7bec072b54f13b552ae3e7db9db4cdbb8ea1`.
The report/registration successor is recorded in Git history and the completion
response; it changes no application or test implementation.
**Decision: focused GO.** The numerical cycle is eliminated, the tested canonical
API paths run headlessly, and no new scientific discrepancy remains. Full-suite,
native desktop and release acceptance are outside this decision.

Two functions move to existing owners, with unchanged signatures and numerical
statements. `projected_geometry_from_oriented_crystal` moves from `gui.propagation`
to `gui.geometry`; `propagate` moves from `gui.propagation` to `gui.channeling`.
Planning retains its allocation constants and memory estimates. No production
module, compatibility facade, scheduler, scientific model or public API is added.
The exact signature and behavior of `gui.forward_pipeline.calculate` remain.

This is application-source work with focused test and documentation updates.
It is not a full migration out of the `gui` namespace or release acceptance.

## B. Numerical responsibility and actual call graph

| Responsibility | Owner and calls |
|---|---|
| Structure, orientation, finite diffraction basis | `gui.geometry.geometry`, `elastic_model`; existing `CrystalOrientation`, elastic providers and Hamiltonian |
| Projected periodic cell | `gui.geometry.projected_geometry_from_oriented_crystal` delegates directly to `projected_geometry.ProjectedGeometry.from_oriented` |
| Numerical planning | `gui.propagation.resolve_fft_configuration`, `numerical_info`, `multisite_memory_terms`, `multisite_bw_double_memory_terms`; shared allocation constants remain here |
| Incoming propagation | `gui.channeling.propagate`: BW calls `elastic.amplitudes(z)`; FFT calls `fft_geometry` then existing `incident_fields` |
| FFT support preparation | `gui.channeling.fft_geometry` calls `ProjectedFFT.build` with the explicit oriented crystal/cell, basis, cutoffs, memory limit and cancellation callback |
| BW Double Channeling | `double_channeling.prepare_incoming_bloch`, `prepare_outgoing_bloch`, `double_channeling_response`; grouped path uses `multisite_double_channeling.contract_multisite_bloch_double` |
| FFT Double Channeling | `multislice_double_channeling.incident_fields`, `multislice_double_channeling_response`; grouped path uses `multisite_double_channeling.contract_multisite_ms_double` |
| Uniform detector scheduling | `gui.channeling.calculate_detector_signals`, `angular_schedule`, `map_detector_batches`; existing Single tensor and Double response kernels |
| Grouped scheduling | `gui.forward_pipeline._calculate_multisite`, `multisite_spectrum.prepare_multisite_spectrum`, `gui.multisite_integration.integrate_single_channeling_spectrum` / `integrate_double_channeling_spectrum` |
| Grouped Single contraction | `multisite_single_channeling._group_intensity_pair`, `run_multisite_with_coherence`; independent localized-event intensities and original group weights |
| Detector reduction | `detector_signals.integrate_detector_block` and existing uniform reduction; original fractional weights, pixel support and summation order |
| Admission | `gui.propagation.numerical_info` calls `gui.parallel_resources.worker_plan` / `require_supported`; execution uses `bind_allocation` and `gui.memory_budget.reserve_memory` |
| Cancellation and cleanup | Original `check_cancelled` calls, kernel callbacks, executor guard, joined thread pools and memory-reservation context managers |
| Scientific result assembly | `gui.forward_results.assemble_forward_result`; existing parity, source revalidation, metadata and method diagnostics |

The public entry branches into uniform and grouped orchestration. Uniform
execution validates the provider, resolves FFT settings, obtains admission,
then `_calculate_uniform_prepared` iterates solvers in the original order. Each
solver prepares incoming waves, constructs coherence, calculates detector signals
and assembles results. Grouped execution validates source/group association and
energy coverage before admission and retains its distinct bounded energy and
detector-support schedule. Double grouped BW prepares its own incoming Bloch state;
other supported branches use incoming propagation as before. None of these
branches were merged or reordered.

`calculate_detector_signals` still uses `SINGLE_CHANNELING_PIXEL_BATCH` from
planning; grouped integration still uses `MULTISITE_ENERGY_BATCH`. These are
shared allocation/execution bounds, not duplicate implementations. Their values
and use are unchanged. `numerical_info` still owns FFT coverage validation,
resource estimates and advisory convergence warnings, including existing
orientation-specific evidence; those warnings do not select another solver or
material.

## C. Dependency correction

Before, `channeling.fft_geometry` and `calculate_detector_signals` imported the
projected-cell helper from propagation. Detector execution also imported its
batch bound there. In the reverse direction, `propagation.propagate` imported
`channeling.fft_geometry` and the imported kernel binding `incident_fields`.
The cycle therefore combined geometry/planning and execution responsibilities.

After, geometry has the one projected-cell adapter, and channeling has the one
incoming-execution adapter. Propagation no longer imports channeling, including
inside functions. The remaining `channeling -> propagation` edge supplies only
the unchanged allocation bound. No deferred import was introduced to conceal a
cycle. Original deferred imports that still serve existing dependency boundaries
remain.

Consumers migrated: both uniform and grouped forward-pipeline branches;
`gui.numerical_settings`; the scheduling/cancellation spies in
`test_multisite_forward` and `test_multisite_spectrum`; UI no-calculation spies
in runtime fixtures, automatic settings, diffraction toggles, Stage F and Laue
overlays; and the energy/angular benchmark instrumentation. The archived-source
translation in `tests/reference_imports.py` routes the historical named imports
to these owners without altering archived mathematical statements.

Removed function definitions at the legacy owner: `gui.propagation.propagate` and
`gui.propagation.projected_geometry_from_oriented_crystal`. No identified current
consumer needs production aliases. The historical `projected_geometry_for`
translation remains only for authenticated research/test source consumers.
Planning necessarily imports the geometry helper for its own calls; that ordinary
import binding is not a retained compatibility interface or a second definition.

| Interface / compatibility decision | Identified consumers and reason |
|---|---|
| Retain exact `gui.forward_pipeline.calculate` API | Production GUI, maintained scripts/tests and explicit programmatic calculations; required canonical public entry |
| Remove old `propagation.propagate` definition; no wrapper | Both forward schedules, test spies and benchmark now call `channeling.propagate`; no remaining supported old-owner consumer |
| Move projected-cell definition to geometry; no compatibility wrapper | Planning, channeling, numerical controls and reference-import adapter use the geometry owner; one scientific implementation |
| Retain reference-only historical import translations | Existing archived Ni/scheduling/scientific comparison fixtures and the unchanged exact driver; authenticates original sources and translates dependencies only |
| Retain saved settings/record identities and project loaders | Existing projects, `NiForwardSettings` and source-backed records; saved-file compatibility does not require an old execution function alias |

## D. Headless scientific execution

`tests/test_headless_calculation.py` launches eight fresh Python processes: Ni
and synthetic ordered BCC Cr, each with BW/FFT and Single/Double Channeling.
Every process calls the unchanged public `gui.forward_pipeline.calculate` API;
none stops at request preparation or uses an alternative public API.

| Material/configuration | Solver | Channeling | Established comparison | Fresh process |
|---|---|---|---|---|
| Ni XMCD preset, original small Ni geometry | BW | Single | Archived detector kernel; exact arrays | Passed |
| Ni XMCD preset, original small Ni geometry | BW | Double | Archived detector kernel; unchanged established roundoff contract | Passed |
| Ni XMCD preset, original small Ni geometry | FFT multislice | Single | Archived detector kernel; exact arrays | Passed |
| Ni XMCD preset, original small Ni geometry | FFT multislice | Double | Archived detector kernel; exact arrays | Passed |
| Cr BCC, explicit up/down sites, unequal synthetic MDFF | BW | Single | Independent event amplitudes, group normalization, reversal | Passed |
| Cr BCC, explicit up/down sites, unequal synthetic MDFF | BW | Double | Independent event amplitudes, group normalization, reversal | Passed |
| Cr BCC, explicit up/down sites, unequal synthetic MDFF | FFT multislice | Single | Independent event amplitudes, group normalization, reversal | Passed |
| Cr BCC, explicit up/down sites, unequal synthetic MDFF | FFT multislice | Double | Independent event amplitudes, group normalization, reversal | Passed |

The Cr fixture supplies explicit structure, opposite unit magnetic directions,
separate imported MDFF files and unequal sublattice tensor pairs. It is an
existing software validation fixture, not a physical model for bulk Cr magnetic
order or an absolute spectroscopy claim. Ni uses the existing explicit Ni preset
and historical XMCD source; no new material parameters are introduced.

Before scientific imports, a meta-path finder rejects PySide/PyQt, the explicit
widget/presentation module set, and Matplotlib Qt backends. The child removes
`QT_QPA_PLATFORM`; offscreen Qt is not used to claim headlessness. Both rejected
attempts and the final imported-module set must be empty of forbidden modules.

Each child verifies solver/channel selection, energy ordering, detector/grid,
beam/coherence/depth dimensions, finite spectra and raw maps, and the original
aperture-supported NaN mask of derived paired maps. Existing metadata must
contain the actual source identities and software/physics provenance. Ni reuses
the authenticated archived-kernel comparisons and established numerical-roundoff
helper; Cr executes the maintained independent-event, reversal and independent
site-normalization assertions. On completion there are no memory reservations,
new live Python threads, multiprocessing children or held Windows BW executor
lock. The parent owns its child timeout and terminates only that process tree.

This establishes headless public scientific execution for these supported small
uniform and grouped paths. It does not claim native desktop acceptance, arbitrary
model convergence or proof for every configuration. Scientific services and
configuration types still have `gui`-namespaced imports; those names alone do
not require Qt. Presentation, project I/O and Qt worker wrappers remain separate.

## E. Verification

Logs, JUnit XML, source/run identities and static
dependency evidence are retained under ignored `build/phase3d1/`.

| Selection / evidence stem | Result | Seconds | Scope |
|---|---|---:|---|
| `ownership` | 9 passed | 6.000 | Canonical API, propagation reuse, cancellation |
| `headless` | 8 passed | 25.813 | Eight fresh blocked-import scientific processes |
| `science` | 156 passed, 1 skipped, 13 failed before calculation | 232.422 | All six numerical-contract cases passed; the 13 failures were test import migration errors |
| `consumer-fix` | 13 passed | 2.797 | Only those invalid-input cases after restoring their planning-spy import |
| `exact` | 22 cases / 2,294 arrays exactly equal | 13.781 | Unchanged comparison driver, physical metadata and edge metrics |
| `workflows` | Collection error, no tests ran | 21.344 | Two node names incorrectly included a class prefix; command corrected |
| `workflows-corrected` | 148 passed, 14 skipped, 1 stale structural assertion failed | 259.063 | The one broader affected GUI/project selection |
| `workflow-fix-parallel` | 19 passed, 1 stale docstring assertion failed | 19.469 | Real serial/parallel execution, group weights, reversal, cancellation/BLAS restoration; narrowed assertion correction |
| `assertion-fix` | 1 passed | 4.812 | Remaining structural assertion after accounting for Phase 3C docstrings |
| `registration` | 124 passed, 1 skipped | 191.422 | Current-source positive/mutation and offline historical controls, unit labels, static build metadata |
| `final-map` | 2 passed (already counted above) | 5.594 | Existing positive/map-mutation controls after recording the implementation commit |

Durations are driver wall times. Failed evidence remains under its original
name. The import error affected only the test module, not execution. The GUI
assertion still assumed the pre-Phase-3B GUI-dependent Ni constructor and
pre-Phase-3C geometry helper locations/docstrings. Its migration permits exactly
the reviewed ASE cell constructor, selects the actual geometry owner and omits
formal descriptive docstrings from executable comparison. The full eligibility
conditions, executable structure, errors, scientific expressions and tolerances
remain compared; kernel/data checks are retained. No application change was
needed to resolve either test-consumer problem.

Across the selections, deduplicating pytest node IDs and taking the final result
of each affected rerun gives **492 distinct cases: 476 passed, 16 existing skips,
zero unresolved failures**. This is combined focused coverage, not one clean
full-suite invocation. Skips comprise five unavailable saved-result/project
controls, eight optional existing Stage D visualization cases, two opt-in native
workflows and one optional external 160-array unit-label evidence check. The
22-case exact driver is separate from these pytest totals.

The broader GUI selection covers actual Ni solver/kernel routes, solver and
Single/Double controls, Global/Local MDFF acceptance/drafts, material/group
magnetization, Auto/Manual resources, Save/Open/history, restored settings, result
selection, raw/relative display, maps, CSV/figure export and cancellation. Existing
optional native/saved-reference cases remain skips, not passes. Core supported
workflows are checked using available source fixtures; this is not native Windows
desktop or release acceptance. A separate existing parallel selection exercises
grouped BW/FFT with 2/4 workers, uniform Double parallel execution, and AFM Cr
Auto/Manual execution with five Double workers, while preserving serial outputs.

All six corrected numerical-contract nodes passed in `science.xml`:

- `test_double_cancellation::test_bw_unchanged_and_depth_cancel[numerical]`
- `test_double_cancellation::test_full_spectrum_unchanged[bloch]`
- `test_double_cancellation::test_full_spectrum_unchanged[both]`
- `test_multisite_scientific_validation::test_bcc_cr_independent_events_and_symmetry[unequal-mdff-double-bloch]`
- `test_single_element_ni_compatibility::test_original_ni_all_numeric_arrays_exact[double-xmcd]`
- `test_single_element_ni_compatibility::test_original_ni_all_numeric_arrays_exact[double-atomic]`

The unchanged `build/regression-recovery/verify_equivalence.py` reported
**22 cases passed / 2,294 arrays exactly equal** against actual pre-refactor
source `cdb8836388c5ccc5ae7a614b47894c0ab158a824`; physical metadata and edge
metrics also match. Its two explicitly labeled older-reference deltas
(XMCD `1.3010426069826053e-18`, atomic `2.6469779601696886e-23`) predate this
phase and are not new discrepancies. No comparison contract was adjusted.

A direct static comparison of the changed application owners found 42 existing
function/class ASTs identical after excluding import statements. The sole
excluded function, `runtime.build_info`, only adds `channeling.py` to its existing
implementation inventory because traced incoming execution moved there from
`propagation.py`. Geometry remains covered by its existing inventory entry.
This preserves result traceability without a new authentication framework or
frozen baseline. Previously saved build/source dictionaries remain unchanged.

The reviewed current-source map and its existing loader pin are updated for
affected registered files. Original historical maps/archives, authenticated
previous-source payloads, reference arrays and strict numerical kernel/data
identities remain intact. Archived dependency translations use existing
reference-only infrastructure; no production fallback route is restored.
The reviewed map still has 147 entries. Direct comparison with the starting
commit confirms all existing authenticated previous-source payloads and
historical metadata are unchanged. No new historical archive or baseline is
introduced. `git diff --check` passes; final post-test application edits only
remove two blank lines introduced by the move, without any executable AST change.

No complete regression, Windows EXE build, application version change, push,
merge, tag, package publication or release-artifact replacement was performed.

## F. Structural measurements

Use the established
Phase 3A–3C AST import methodology, including literal imports inside functions.
Production is `src/**/*.py`, counting each file once. Source LOC excludes blank
lines, comments and formal docstrings; noncomment LOC includes docstrings.

| Metric | Before | After | Change |
|---|---:|---:|---:|
| Production Python files | 107 | 107 | 0 (0%) |
| GUI Python files | 62 | 62 | 0 (0%) |
| Physical production LOC | 19,517 | 19,519 | +2 (+0.010%) |
| Nonblank, noncomment LOC (including docstrings) | 17,459 | 17,461 | +2 (+0.011%) |
| Production source LOC (excluding formal docstrings) | 16,512 | 16,514 | +2 (+0.012%) |
| Internal module import edges | 482 | 482 | 0 (0%) |
| Cyclic dependency groups | 5 | 4 | −1 (−20%) |
| Modules in cycles | 16 | 14 | −2 (−12.5%) |
| Largest SCC | 5 | 5 | 0 (0%) |
| Channeling/propagation SCC size | 2 | 0 | −2 (cycle eliminated) |
| Non-GUI → GUI edges | 8 | 8 | 0 (0%) |

The two modules now occupy separate singleton SCCs; zero in the table means no
shared cyclic component. Exact unique module edges removed:

- `gui.propagation -> gui.channeling`
- `gui.propagation -> projected_geometry`

Exact edges added:

- `gui.channeling -> gui.geometry`
- `gui.geometry -> projected_geometry`

All names above are within `emcd_sim`. The existing `propagation -> geometry`
edge now also supplies the cell adapter. Literal imports are counted whether
eager or deferred, so moving an import inside a function would not erase an edge.
The baseline/after graph evidence is `build/phase3d1/{before,after}.json`.
The focused static call graph records 80 function owners across 13 inspected
modules in `calls-before.json` and `calls-after.json`, including source lines and
resolved imported/local bindings. Instance methods and callbacks are explicitly
marked unresolved by static binding analysis; the responsibility map above and
actual execution tests establish those paths without claiming a complete dynamic
call graph.

This removes one actual architectural cycle and clarifies planning versus
execution ownership. It does not reduce overall import count, module count or
code volume, eliminate the other four SCCs, or remove the eight non-GUI → GUI
edges. No numerical/planning duplication was created or consolidated: the two
original bodies each have one owner. Independent scientific references remain
independent; BW/FFT, Single/Double and uniform/grouped scheduling retain distinct
responsibilities. The extra source lines are explicit consumer imports.

## G. Phase 3D-2 handoff

1. `gui.geometry` and `gui.forward_results` have neutral data/scientific
   responsibilities and are the clearest next engine-ownership candidates.
   Preserve structure/settings serialization identities in the loading layer;
   result assembly still records configuration and build provenance.
2. Review `memory_budget` with its pinned kernel consumers before changing its
   import path. Its admission/cleanup responsibilities are already numerical;
   do not casually modify kernel identities to obtain a namespace cleanup.
3. Planning (`propagation`) and execution (`channeling`) can then migrate with
   their actual one-way dependencies. Shared settings, resource planning and
   hardware/native-runtime services must accompany a deliberate ownership plan.
4. `multisite_integration` is a numerical schedule/reduction service, but preserve
   its distinct source/group, energy-coverage and independent-site accumulation
   responsibilities. Its use of GUI-namespaced configuration and planning bounds
   must be addressed together with the current callers.
5. `forward_pipeline` should follow the lower services. It remains the sole
   public forward entry and depends on settings, result assembly, geometry,
   admission, providers and both scheduling paths. Do not create a competing API.

This phase performs none of that full package migration. It also leaves the
remaining application/acceptance, persistence and scientific-provider cycles for
separate focused work. Different BW/FFT numerical methods and Single/Double
physical approximations remain distinct. Existing projected-ZOLZ, finite-basis,
model/source, normalization and convergence limitations require scientific work,
not more function renaming.
