# Phase 3D-2B-2: forward scientific engine extraction

## A. Scope and decision

Starting HEAD: `688de5085dcdef48f154c175cfb995055b4075ab`, clean on
`refactor/physics-readability`, containing verified Phase 3D-2B-1 implementation
`05a9fb196b819dbb7310019d4432a6c19271f2c8`.
Working directory and worktree root are both
`C:/Users/peng863/EMCD-Sim/.worktrees/windows-adaptive-compute`.
The starting 170-file current source registration was verified before editing.
The existing ownership maps and Phase 3B–3D-2B-1, regression-recovery and
numerical-contract reports remain prior evidence; no checkout move/reset occurs.

Implementation commit: `55a1aa941f53f9cf1efe7d3cf505bf94a5af53bf`.
**Focused GO for Phase 3D-2B-2.** All required extraction and focused
verification criteria pass. Complete-regression and release acceptance remain
outside this phase.

This phase moves existing implementations in order: propagation planning,
channeling execution, grouped integration, forward orchestration. Numerical
expressions, physical assumptions, settings/defaults and uniform/grouped
scheduling remain distinct and unchanged. Material cleanup and GUI redesign
are deferred. Independent archived scientific references remain validation
implementations, not production engines.

Remaining boundaries are explicit: the public GUI re-export, four unchanged
kernel/reference imports through the memory adapter, and GUI source files read
as provenance inventory data. No GUI application service is imported by the
engine. Ni-derived defaults/inheritance and the four existing SCCs remain for
later review; no new cycle or physical capability is introduced.

## B. Scientific ownership

| Responsibility | Previous owner | Final owner | Compatibility |
|---|---|---|---|
| Numerical planning, FFT coverage, memory estimates, method diagnostics | `gui.propagation` | `propagation` | Maintained consumers migrate; no old planning facade |
| Incoming BW/FFT propagation | `gui.channeling` | `channeling` | Same preparation, array layouts and callback semantics |
| BW/FFT Single/Double execution and detector batches | `gui.channeling` | `channeling` plus unchanged numerical kernels | One Windows BW guard; separate mathematical methods |
| Uniform energy/angular schedule | `gui.channeling`, `gui.forward_pipeline` | `channeling`, `forward_pipeline` | Existing reduction order/checkpoints |
| Grouped energy/pixel schedule | `gui.multisite_integration`, `gui.forward_pipeline` | `multisite_integration`, `forward_pipeline` | Separate grouped implementation and independent-site normalization |
| Fractional detector integration | `detector_signals` | Unchanged | Scheduling clients move; integration equations do not |
| Forward calculation | `gui.forward_pipeline` | `forward_pipeline` | Only public `calculate` remains at GUI path |
| Memory admission and worker/BLAS policy | `memory_budget`, `parallel_resources` | Unchanged | One reservation dictionary/lock and existing kernel import adapter |
| Scientific result assembly | `forward_results` | Unchanged | Source/geometry/model provenance retained |

## C. Public API and consumers

The supported interface remains
`emcd_sim.gui.forward_pipeline.calculate(structure, settings, cfg, sites=...)`,
including all progress/cancellation, energy, checkpoint and execution-policy
parameters. The GUI module is a direct re-export of the authoritative
scientific callable, with no private orchestration aliases or calculation body.
Maintained GUI workers, preflight, scientific consumers, scripts and test spies
use the actual owners. Qt thread callbacks and signals remain in the GUI worker.
Callable identity/signature and real public-entry execution pass in the focused API test. The three former private GUI modules are deleted; no compatibility aliases for their helpers remain.

## D. Headless execution

| Material/configuration | Solver | Channeling | Result and independent control |
|---|---|---|---|
| Ni | bloch | single | Passed: Historical exact incoming/spectral/map comparisons |
| Ni | bloch | double | Passed: Historical exact arrays, with the existing bounded optimized-BW comparison |
| Ni | fft-multislice | single | Passed: Historical exact incoming/spectral/map comparisons |
| Ni | fft-multislice | double | Passed: Historical exact incoming/spectral/map comparisons |
| Cr | bloch | single | Passed: Explicit synthetic BCC; independent events, reversal, normalization and unequal-MDFF contract |
| Cr | bloch | double | Passed: Explicit synthetic BCC; independent events, reversal, normalization and unequal-MDFF contract |
| Cr | fft-multislice | single | Passed: Explicit synthetic BCC; independent events, reversal, normalization and unequal-MDFF contract |
| Cr | fft-multislice | double | Passed: Explicit synthetic BCC; independent events, reversal, normalization and unequal-MDFF contract |

All eight run in fresh processes with the Qt platform environment removed.
The import finder rejects attempted Qt or GUI imports even if an importer catches
the exception; the final module audit also rejects disallowed entries. Only
`emcd_sim.gui` and `emcd_sim.gui.memory_budget` are permitted. No additional
exception is needed. The real new root entry is used in every case.

Every case checks raw/derived spectra, energy/detector dimensions, angular-map
validity, declared source checksums and geometry provenance. All four current
engine hashes must identify the root implementation files. Immediate
cancellation is exercised per case; independent depth/worker cancellation is
covered by the scientific selections. Reservations/child processes are empty
after execution, Python threads return to baseline, the Windows executor lock
is available and the BLAS reentrant lock is tested from a separate thread.
The existing kernel-bridge fresh-process check separately verifies exact
function/global dictionary/lock identity.

The GUI public entry is tested separately: it is the same callable and signature
as `emcd_sim.forward_pipeline.calculate`, and real Ni calculation arrays match
exactly through both import paths. This supported client import is not an
extra transitive dependency of the scientific engine.


The required cases use existing Ni and explicit synthetic ordered BCC Cr
fixtures with BW/FFT and Single/Double Channeling. Synthetic Cr is not a claim
about bulk Cr spin-density-wave order or calibrated spectroscopy. No Fe3O4
headless calculation or additional physical model is introduced.

The final runtime fence rejects PySide/PyQt, Qt backends, GUI editing,
presentation and the entire GUI namespace except its package and the documented
state-free memory adapter. Actual calculations, spectra/maps, masks,
source/geometry provenance, workers, reservations and executor locks are checked.

## E. Scientific and application verification

**Combined focused coverage: 354 passed, 6 existing skips; 360 distinct pytest cases, no unresolved failure/error.**
This is combined focused coverage, not a complete regression or a single
clean invocation. The table preserves failures, interrupted work and targeted
rechecks separately. Overlapping checkpoints and final-map rechecks count once.
The 22-case comparison and import-only diagnostic smoke are separate, not added
to the pytest total. The repeated exact invocation still represents 22 distinct
cases and 2,294 arrays, not 44 cases or twice as many arrays.

All logs, completed-run JUnit XML, commands, environment, HEAD/status, owned PID
and durations are under ignored `build/phase3d2b2/`. The linked metadata stores
each exact command as its `command` argv array, including selectors, temporary
paths and XML destinations; no shell reconstruction is needed.

| Invocation and exact argv/environment/source record | Actual outcome | Seconds |
|---|---|---:|
| [planning](../build/phase3d2b2/planning-run.json) | 55 passed, 0 skipped, 1 failed | 121.360 |
| [planning-reference-import-fix](../build/phase3d2b2/planning-reference-import-fix-run.json) | 1 passed, 0 skipped | 7.219 |
| [channeling](../build/phase3d2b2/channeling-run.json) | Stopped after 49 pass marks at first GUI test; no assertion failure; remaining cases continued separately | 362.516 |
| [channeling-collection](../build/phase3d2b2/channeling-collection-run.json) | 53 ordered cases collected; none executed | 9.938 |
| [channeling-remainder](../build/phase3d2b2/channeling-remainder-run.json) | 4 passed, 0 skipped | 31.188 |
| [multisite](../build/phase3d2b2/multisite-run.json) | 44 passed, 0 skipped | 131.109 |
| [forward-headless-api](../build/phase3d2b2/forward-headless-api-run.json) | 24 passed, 1 skipped | 74.438 |
| [science](../build/phase3d2b2/science-run.json) | 52 passed, 0 skipped | 55.734 |
| [exact](../build/phase3d2b2/exact-run.json) | 22 cases / 2,294 arrays exactly equal; physical metadata/edge metrics equal | 34.797 |
| [workflows](../build/phase3d2b2/workflows-run.json) | 115 passed, 4 skipped | 729.047 |
| [diagnostic-reference-imports](../build/phase3d2b2/diagnostic-reference-imports-run.json) | Import-only smoke failed on retired ProjectedNiFFT binding; no project/calculation | 2.922 |
| [diagnostic-reference-import-fix](../build/phase3d2b2/diagnostic-reference-import-fix-run.json) | Import/domain smoke passed; no project/calculation | 2.219 |
| [authentication](../build/phase3d2b2/authentication-run.json) | 45 passed, 1 skipped | 84.047 |
| [exact-final-reference-imports](../build/phase3d2b2/exact-final-reference-imports-run.json) | 22 cases / 2,294 arrays exactly equal; physical metadata/edge metrics equal | 26.500 |
| [final-map](../build/phase3d2b2/final-map-run.json) | 2 passed, 0 skipped | 55.016 |

The first planning invocation had 55 passes and one historical import failure:
its generic planning translation shadowed the earlier projected-geometry helper
rename. The existing specific translation was moved ahead of the generic route;
only that failed real-calculation case was rechecked, and passed. No numerical
difference or tolerance change was involved.

Channeling initially completed 49 cases, including all eight real calculations.
The next case was the first GUI/resource test in that selection; Qt was imported
after the existing cleanup fixture configured its message-box hooks, allowing
cleanup of the modified window to wait on an unsaved-changes dialog. The owned
payload/descendants were stopped. The test module now imports its existing Qt
dependencies before fixture setup. Ordered collection confirms the 49 completed
IDs; only four interrupted/unrun cases were resumed, all passing. No JUnit XML
is claimed for the stopped invocation; its progress, collection and completion
IDs remain evidence. The application close workflow is unchanged.

The one broader GUI/project invocation passed **115 cases with four skips**.
Its skips are three opt-in native Windows checks and the optional solver
saved-result fixture. Material Apply/Cancel, Global/Local/group declarations,
complex Manual/Atomic/XMCD inputs, magnetic groups, actual Ni/Cr submissions,
cancellation, resources, Save/Open, source relocation/tamper rejection, selected
run restoration, displays/maps and exports retain their behavioral checks.
All completed GUI cases released their test-owned windows.

The other two distinct skips are the optional old saved-project fixture in
metadata checks and the external 160-array unit-label evidence. They are not
reported as successful calculations and do not replace the required successful
2,294-array comparison.

All six corrected scientific contracts passed against the final root owner:

- `test_bw_unchanged_and_depth_cancel[numerical]`
- `test_full_spectrum_unchanged[bloch]` and `[both]`
- `test_bcc_cr_independent_events_and_symmetry[unequal-mdff-double-bloch]`
- `test_original_ni_all_numeric_arrays_exact[double-xmcd]` and `[double-atomic]`

Existing cancellation-sensitive Cr parent-scale allowances, shapes/dtypes,
undefined masks, original arrays and lossless serialization assertions remain.
The scientific selections also retain independent localized events, reversal,
normalization, quadrature, MDFF/detector checks, bounded storage, actual
serial/parallel execution, BLAS restoration and roundoff negative controls.

The unchanged `build/regression-recovery/verify_equivalence.py` is executed
through the existing test-only named-import translator. All 22 cases and 2,294
arrays equal `cdb8836388c5ccc5ae7a614b47894c0ab158a824` exactly. Its separately
printed older-reference deltas (1.3010426069826053e-18 XMCD and
2.6469779601696886e-23 Atomic) remain prior evidence, not new differences.

Final source audit found the maintained opt-in cutoff diagnostic still compiling
old imports directly. It now uses the existing reference translator, including
the concrete retired ProjectedNiFFT, FCC phase helper and Ni017 reference names.
Its reference adapter accepts the explicit historical Ni site type and rejects
general site inputs rather than using Ni assumptions. The smoke checked import
resolution and this boundary only, stopping before project loading. Closed
scientific investigations, calculations and candidate acceptance were not resumed.
The exact driver was rechecked after these final helper changes and again passed
all 22 cases / 2,294 arrays. No production alias or algorithm is added for them.

Authentication passed **45 cases with one optional external-evidence skip**,
including mutations of all four authoritative scientific owners, provenance,
the public and memory adapters, historical evidence and the current source map;
plus unit/schema, offline/no-Git/no-process, runtime CLI/export and packaging
metadata controls. Two final pointer/manifest controls passed against the
implementation commit after registration. Existing historical payloads and
immutable kernel/data identities remain unchanged.

Validation uses Python 3.11.17, NumPy 2.4.6 and SciPy 1.17.1; deterministic
`PYTHONHASHSEED=0`, `OPENBLAS_NUM_THREADS=1` and `OMP_NUM_THREADS=1`, with
short temporary paths under `C:/Users/peng863/EMCD-Sim/build/nc-tmp`. Parent
GUI runs use offscreen Qt; strict headless children remove that environment
and prohibit the actual imports. No complete regression, EXE build/replacement,
version change, push, merge, tag, publication or installed-beta change occurs.

## F. Source authentication and provenance

Only the established reviewed current-source mechanism is updated for moved
owners and consumers. Historical kernel/data identities, archived bytes and
previous-source payloads stay intact. Named historical import translations
continue in the existing test-only helper; no archived equation is edited.

`double_channeling` and `multislice_double_channeling` retain their immutable
whole-file imports of `gui.memory_budget.reserve_memory`. The other unchanged
reference/potential consumers also retain that import. The adapter exposes the
identical root function and owns no state. Ordinary reviewed current-source
`multisite_double_channeling` may migrate its execution import to root channeling;
it is distinct from the strictly pinned kernels.

Runtime source inventories must resolve moved implementation bodies rather
than the public GUI adapter. Existing keys and frozen/saved dictionaries remain
preserved; new current grouped-owner coverage is recorded explicitly.
The existing packaging inventory already discovers all production Python files.

The current map covers 171 files, previously 170: the three removed private GUI
owners map to their scientific owners, and the root forward implementation is
covered alongside the existing public adapter path. The current implementation
inventory retains its six existing keys, resolves moved execution bodies at root,
and adds `multisite_integration.py` as a seventh key for new current results.
Source mode still covers the existing GUI geometry/export files; frozen metadata
is returned untouched, and project loading does not stamp new hashes into old
dictionaries. The existing PyInstaller source traversal already covers all root
owners, so no build/spec inventory framework or new release hash layer is added.

The reference-only archived channel harness registers at
`emcd_sim._single_element_channel_reference` rather than a GUI test namespace.
Its original Git source path, compile filename, equations and assertions remain;
its historical package context and the existing named import translator resolve
archived imports. This is an isolated test-namespace change, not a concealed
production edge or another runtime exception.

Positive/mutation/offline authentication and the final registration-pointer controls pass (E). No immutable source identity is repinned.


## G. Dependency and complexity measurements

The reused AST/token analysis reproduces the supplied starting metrics.
Production files partition `src/**/*.py` once. Source LOC excludes blank/
comment lines and formal docstrings; noncomment lines include docstrings.
Deferred literal imports count as distinct directed edges. Before/after graphs
and per-file LOC are retained under `build/phase3d2b2/`.

| Metric | Before | After | Change | Percent |
|---|---:|---:|---:|---:|
| Production files | 110 | 111 | +1 | +0.91% |
| GUI files | 56 | 53 | -3 | -5.36% |
| Non-GUI files | 54 | 58 | +4 | +7.41% |
| Physical lines | 19,567 | 19,571 | +4 | +0.02% |
| Nonblank/noncomment lines including docstrings | 17,478 | 17,481 | +3 | +0.02% |
| Source LOC excluding formal docstrings | 16,517 | 16,519 | +2 | +0.01% |
| GUI source LOC | 11,632 | 10,695 | -937 | -8.06% |
| Non-GUI source LOC | 4,885 | 5,824 | +939 | +19.22% |
| GUI physical lines | 13,114 | 11,986 | -1,128 | -8.60% |
| Non-GUI physical lines | 6,453 | 7,585 | +1,132 | +17.54% |
| Distinct internal import edges | 494 | 495 | +1 | +0.20% |
| Cyclic groups | 4 | 4 | +0 | +0.00% |
| Modules in cycles | 14 | 14 | +0 | +0.00% |
| Largest SCC | 5 | 5 | +0 | +0.00% |
| Non-GUI to GUI edges | 6 | 5 | -1 | -16.67% |

GUI forward-execution implementation modules: **four to zero**; one public
re-export remains. One authoritative forward orchestrator remains, with zero
new duplicate production algorithms. Distinct BW/FFT, Single/Double and
uniform/grouped implementations preserve different models or scheduling.

The net extra file/import edge is the public GUI adapter; its two statements
explain the net two source lines. This relocates 1,133 physical implementation
lines; it does not remove their algorithms. The architectural improvement is
verified ownership, migrated consumers, runtime isolation and provenance of
the actual bodies. All four SCC memberships are unchanged; no new cycle.

### Engine import closure

| Scientific owner | Direct GUI imports | Other extracted owners imported |
|---|---|---|
| `propagation` | None | None |
| `channeling` | None | `propagation` |
| `multisite_integration` | None | `propagation` |
| `forward_pipeline` | None | `channeling`, `multisite_integration`, `propagation` |

The only transitive GUI implementation is `gui.memory_budget`. Python also
initializes its empty GUI package; both are explicitly permitted by the runtime
fence. No Qt/editor/presentation/application service is allowed. Source
provenance still reads existing GUI geometry/export files as inventory data,
retaining those keys; it does not import or execute them.

### Remaining reverse edges

| Edge | Concrete purpose |
|---|---|
| `__main__ -> gui` | Desktop launcher, outside scientific closure |
| `double_channeling -> gui.memory_budget` | Unchanged authenticated kernel/reference import to the shared-memory adapter |
| `multislice_double_channeling -> gui.memory_budget` | Unchanged authenticated kernel/reference import to the shared-memory adapter |
| `multislice_reference -> gui.memory_budget` | Unchanged authenticated kernel/reference import to the shared-memory adapter |
| `projected_potential -> gui.memory_budget` | Unchanged authenticated kernel/reference import to the shared-memory adapter |

### Complete literal edge changes

These independent removed/added target sets include owner moves. Literal
rewiring is not counted as deletion of physics.

| Consumer | Removed targets | Added targets |
|---|---|---|
| `channeling` | ? | `cancellation`, `double_channeling`, `hardware_resources`, `mdff_edges`, `multislice_double_channeling`, `parallel_resources`, `propagation`, `single_channeling_tensor`, `structure_geometry` |
| `forward_pipeline` | ? | `cancellation`, `channeling`, `detector_signals`, `double_channeling`, `forward_results`, `forward_settings`, `geometry`, `mdff_providers`, `memory_budget`, `multisite`, `multisite_double_channeling`, `multisite_integration`, `multisite_spectrum`, `multislice_reference`, `parallel_resources`, `propagation`, `simulation`, `structure_geometry` |
| `gui.calculation_controls` | `gui.propagation` | `propagation` |
| `gui.calculation_worker` | `gui.forward_pipeline` | `forward_pipeline` |
| `gui.cancellation_acceptance` | `gui.channeling` | `channeling` |
| `gui.channeling` | `cancellation`, `double_channeling`, `gui.propagation`, `hardware_resources`, `mdff_edges`, `multislice_double_channeling`, `parallel_resources`, `single_channeling_tensor`, `structure_geometry` | ? |
| `gui.forward_pipeline` | `cancellation`, `detector_signals`, `double_channeling`, `forward_results`, `forward_settings`, `geometry`, `gui.channeling`, `gui.multisite_integration`, `gui.propagation`, `mdff_providers`, `memory_budget`, `multisite`, `multisite_double_channeling`, `multisite_spectrum`, `multislice_reference`, `parallel_resources`, `simulation`, `structure_geometry` | `forward_pipeline` |
| `gui.multisite_integration` | `detector_signals`, `gui.propagation`, `ionization_sites`, `mdff_providers`, `multisite`, `multisite_double_channeling`, `multisite_single_channeling`, `multisite_spectrum` | ? |
| `gui.multisite_run` | `gui.propagation` | `propagation` |
| `gui.numerical_settings` | `gui.propagation` | `propagation` |
| `gui.propagation` | `crystallography`, `double_channeling`, `forward_results`, `geometry`, `hardware_resources`, `mdff_edges`, `mdff_providers`, `memory_budget`, `multisite`, `multislice_reference`, `parallel_resources`, `structure_geometry` | ? |
| `gui.results` | `gui.propagation` | `propagation` |
| `gui.scientific_acceptance` | `gui.forward_pipeline` | `forward_pipeline` |
| `multisite_double_channeling` | `gui.channeling` | `channeling` |
| `multisite_integration` | ? | `detector_signals`, `ionization_sites`, `mdff_providers`, `multisite`, `multisite_double_channeling`, `multisite_single_channeling`, `multisite_spectrum`, `propagation` |
| `propagation` | ? | `crystallography`, `double_channeling`, `forward_results`, `geometry`, `hardware_resources`, `mdff_edges`, `mdff_providers`, `memory_budget`, `multisite`, `multislice_reference`, `parallel_resources`, `structure_geometry` |

## H. Phase 3E handoff

| Category | Remaining components and responsibility |
|---|---|
| General functionality | Four extracted owners; explicit structures/sites/frames; declared MDFF providers; common detector/results/resource services. Distinct physical methods remain distinct. |
| Examples/presets | `NiForwardSettings`, `DEFAULT_NI_SOURCE`, `NiLocalConfig`, `NickelStudyGeometry` and `Structure.nickel()` supply explicit historical Ni inputs to shared implementations. No orientation-specific propagation algorithm is introduced. |
| Saved-project compatibility | `historical_ni.HistoricalNiProvider` and `HistoricalNiSites` retain direct historical tensor evaluation and original source/atomic semantics. Imported/provider/multisite records still inherit stored Ni fields and the `NiLocalConfig` factory. Redesign requires schema/default/missing-field analysis, not duplicate generic records. |
| Case-oriented geometry/provenance defaults | `structure_geometry.Settings` retains zone (0,1,7), target (2,0,0), and a 300 kV tilt derived using 3.524 angstrom. `Structure.source` still defaults to a built-in Ni label if arbitrary atoms are supplied without an explicit source. Settings retain Ni source/edge/window/detector examples. These real neutrality/provenance cleanup items remain unchanged here. |
| Legacy Ni-only helper domain | `historical_ni_site_phase_matrix` explicitly rejects non-Ni atoms. `channeling.calculate_detector_signals` retains that fallback when sites are omitted; the canonical pipeline supplies provider sites. Standalone tensor APIs retain 852.7 eV defaults. Future cleanup must distinguish this compatibility domain from the explicit general-site route and preserve strict pins. |
| Obsolete interfaces | The three old private GUI engine modules and private GUI forward-helper exports are removed. No remaining material component is declared obsolete just because its name contains Ni; audit concrete consumers first. |
| Independent evidence | Archived pre-refactor calculations, independent event/quadrature tests, `multislice_reference` and historical study/acceptance tools remain reference/QA implementations, not competing production engines. The historical fixed-candidate research verifier is preserved and not resumed. |

The canonical engine continues requiring explicit accepted inputs and preserves
errors for missing groups, unsupported sources, inconsistent material identity
and unsupported geometry. Cr validation uses an explicitly synthetic ordered
BCC fixture, not bulk spin-density-wave spectroscopy. No Fe3O4 numerical
validation is newly claimed.

Software cleanup of inheritance, example geometry and source labels is separate
from scientific development. Calibrated absolute cross sections, first-principles
magnetic ground states, many-body multiplet/charge-transfer physics and broader
projection/disorder models require additional scientific work. Existing dipole,
independent-atom/source-coverage, ordered periodic structure and ZOLZ assumptions
remain. Unsupported conditions retain their established errors.

### Oversized GUI modules for later focused cleanup

| Module | Physical lines | Source LOC |
|---|---:|---:|
| `src/emcd_sim/gui/app.py` | 675 | 619 |
| `src/emcd_sim/gui/atomic_editor.py` | 627 | 574 |
| `src/emcd_sim/gui/group_mdff.py` | 599 | 547 |
| `src/emcd_sim/gui/responsive.py` | 614 | 531 |
| `src/emcd_sim/gui/calculation_controls.py` | 569 | 528 |
| `src/emcd_sim/gui/project_io.py` | 572 | 480 |
| `src/emcd_sim/gui/project_session.py` | 500 | 461 |
| `src/emcd_sim/gui/site_group_editor.py` | 529 | 461 |

Window/controller/editor coordination, project reconstruction and result
browsing remain future focused GUI work. Preserve accepted/draft transactions,
schemas and independent acceptance/reference responsibilities. Size alone does
not justify deleting or merging distinct scientific or QA logic.
