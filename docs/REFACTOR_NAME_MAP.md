# Current calculation API and refactor decisions

The local refactor starts from `cdb8836388c5ccc5ae7a614b47894c0ab158a824` in
`C:/Users/peng863/EMCD-Sim/.worktrees/windows-adaptive-compute`, on
`refactor/physics-readability`. That development worktree was clean. The shell
initially opened in the separate `main` worktree at `28db183`; its unrelated
changes were preserved. No reset, merge, push, publication, version change or
installed-release replacement is part of this work.

## Canonical production API

```python
from emcd_sim.gui.forward_pipeline import calculate

# Acknowledged uniform source/model and explicit experimental geometry.
result = calculate(structure, geometry_settings, material_settings)

# The same entry point, with explicit local groups and modeled windows.
local = calculate(structure, geometry_settings, numerical_settings,
                  sites=site_groups, energy_windows=windows)
```

`gui.material_inputs.ImportedSettings` and `ProviderSettings` describe explicit
source-backed materials. `gui.forward_settings.MultiSiteForwardSettings` records
grouped numerical/detector requests. The explicitly named `NiForwardSettings`
is the retained Ni parameter preset, outside the engine. Settings and sources
must be supplied; missing groups, unknown provider objects or invalid sources
never select Ni. Uniform and grouped internal schedules retain their existing
numerical order and share the same scientific kernels.

The latest task clarification prioritizes this current API over blanket name
compatibility. No obsolete production facade is kept for hypothetical external
callers. Saved-file compatibility belongs to the existing schema loaders, not
to retired Python module names.

## Old-to-new names and removals

Paths below are relative to `src/emcd_sim/`.

| Previous name | Current owner/name | Reason and disposition |
| --- | --- | --- |
| `gui.stage_b.StageB` | `gui.calculation_controls.CalculationControls` | Collects MDFF/numerical inputs and manages calculation/result state. The stage name and facade are removed; app and maintained tests use the current class. |
| `gui.stage_b.EMCDWorker` | `gui.calculation_worker.EMCDWorker` | Background execution, progress, BLAS control and cancellation are separate from widgets. The already clear class name is retained at its actual owner; the old re-export is removed. |
| `setup_stage_b` | `setup_calculation_controls` | Initializes calculation controls/signals. All current calls are migrated; no old alias remains. |
| `gui.emcd_forward.calculate`, `gui.generalized_forward.calculate`, `gui.forward_pipeline.calculate_multisite` | `gui.forward_pipeline.calculate` | One public execution entry point for explicit material/structure/geometry requests. Group assignments are passed as `sites=`. Old aliases and wrappers are removed. Uniform/grouped schedules remain private implementation steps rather than material-specific engines. |
| `gui.emcd_forward.ForwardSettings` | `gui.forward_settings.NiForwardSettings` | The defaults are a Ni example, so its name must say so. Values and serialized fields are preserved; no old class alias remains. |
| `gui.forward_pipeline.MultiSiteForwardSettings` | `gui.forward_settings.MultiSiteForwardSettings` | Input records belong to the settings owner, not calculation orchestration. Maintained imports use that owner. |
| `gui.generalized_forward` | `gui.material_inputs` | Owns source declarations, eligibility, frames and coverage. The old module and calculation re-export are removed. Existing clear provider class/factory names are retained. |
| `gui.emcd_forward.inspect_source` / `DEFAULT_SOURCE` | `gui.xmcd_source.inspect_xmcd_source` / `gui.forward_settings.DEFAULT_NI_SOURCE` | Distinguish five-column XMCD inspection from a general material provider and identify the bundled Ni preset explicitly. Old names are removed. |
| `gui.emcd_forward._calculate` / `calculate_prepared` | Internal `_calculate_uniform` / `_calculate_uniform_prepared` in `gui.forward_pipeline` | Remove an unnecessary delegation wrapper. Admission and prepared execution remain explicit stages of the canonical engine. |
| `gui.emcd_forward._contract` | `gui.forward_results.assemble_forward_result` | Receives already calculated signals and assembles parity, diagnostics and metadata; it does not contract tensors. The old wrapper and its unused compatibility arguments are removed. |
| `gui.emcd_forward.metrics` | `gui.forward_results.selected_edge_metrics` | Identifies selected-energy observables and dimensionless ratios. Current consumers use the new owner/name; no alias remains. |
| `gui.emcd_forward._export_single` | `gui.forward_results.export_method_result` | Exports one completed propagation-method result; "single" was ambiguous with Single Channeling. The old alias is removed. |
| `gui.emcd_forward.export_result` | `gui.forward_results.export_result` | Export belongs to completed result handling. The clear function name remains, with all imports migrated. The old mixed module is deleted. |
| `gui.channeling.contract` | `gui.channeling.calculate_detector_signals` | Schedules energy/pixel supports, invokes kernels and integrates signals. The vague alias is removed; actual tensor contraction remains in the scientific kernels. |
| `_multisite_detector_data` in `gui.forward_pipeline` | `detector_signals.integrate_detector_block` | Pure NumPy aperture reduction and selected-map retention are independent of resource admission/source preparation. Internal and validation callers are migrated. |
| Repeated detector even/odd algebra | `detector_signals.reversal_components` | One implementation owns N/M, detector differences and the reference sum. Arithmetic/evaluation order and raw inputs are preserved. |
| `_multisite_single_block` | `gui.multisite_integration.contract_single_channeling_block` | Contracts one bounded energy/support cohort with already prepared groups. Memory-lifetime tests target this owner. |
| `_multisite_single_detector_data` / `_multisite_double_detector_data` | `gui.multisite_integration.integrate_single_channeling_spectrum` / `integrate_double_channeling_spectrum` | Separate bounded spectrum scheduling/reduction from request validation and propagation setup. Workers, source normalization and cancellation behavior are retained. |
| `gui.propagation.projected_geometry_for` | `projected_geometry_from_oriented_crystal` in the same module | Production always supplied the actual oriented crystal. Make it required; remove the unused optional Ni fallback instead of preserving it as a facade. |
| `gui.results_browser.Registry` / `IOWorker` | `ResultRegistry` / `ProjectIOWorker` | Identify the result-path index and project-file worker. All current calls/imports are migrated; old aliases are removed. Index/project JSON schemas are unchanged. |
| `ProjectWorkspace.setup_stage_d` | `setup_project_workspace` | Initializes project actions, result browsing and layout. The old alias is removed. |
| `study_geometry.StudyGeometry` | `study_presets.NickelStudyGeometry` | This is an FCC Ni preset builder over the common structural engine, not a general crystal implementation. Maintained Ni studies use the explicit name; the old module is removed. |
| `study_geometry.rotated_tensor` | `study_presets.xmcd_tensor_in_frame` | Constructs an XMCD-effective tensor in an explicit frame; it does not rotate an arbitrary tensor. Its calculation and provenance string are unchanged. |
| `gui.emcd_forward` tensor/energy/orientation re-exports | Direct imports from `historical_ni` or `mdff_orientation` | Ni studies explicitly use Ni preset helpers; generic material inputs use the provider boundary. Accidental re-exports are removed. |

Framework callbacks (`run`, `closeEvent`, `resizeEvent`, `eventFilter`,
`requestInterruption`, `isInterruptionRequested`), Qt signals/slots, saved field
names and console entry points are preserved. Clear numerical interfaces such
as `PhysicalElasticModel`, `TransitionDataset`, `DipoleTensor`,
`AtomicMaterialParameters`, `ImportedMDFF` and `MultiSiteIonization` are retained.

## Concrete retained legacy/reference requirements

| Interface or data | Identified consumer | Why retained |
| --- | --- | --- |
| `historical_ni.NiLocalConfig`, `ni_local_transitions` and related Ni preset helpers | Supported `emcd-ni-local-mdff` console command; maintained Ni research/validation drivers; saved legacy Ni settings | Translate explicit Ni inputs into shared angular/radial/transition code and the canonical calculation. Preserve direct requested-energy evaluation and the established tiny-amplitude policy, which differ from converted-grid interpolation. Non-Ni use is rejected. |
| Original configuration keys and legacy interpretation rules in `project_io.config_from_dict` / project configuration loaders | Existing Global/Local project folders, saved-run snapshots and source declarations | Keep recorded field values, model identities and explicitly missing historical settings. JSON stores values, not old Python function names, so retired module aliases are unnecessary. |
| Old import bindings inside `tests/reference_imports.py` | Archived energy-scheduler, pre-feature Ni, Part 1C and released-controls reference loaders; optional Git-reference benchmark replay | A test/research-only translator binds removed dependency names inside isolated recorded-source namespaces. Numerical statements and immutable archives remain unchanged; production exposes no compatibility facade. |
| Numerical depth integration, `multislice_reference`, direct transition/event controls and immutable accepted sources | Existing independent scientific validation tests | Preserve independent oracles rather than consolidating them into the code they validate. The named Ni FFT convenience/reference is not the general production path. |
| Root package `__all__` numerical interfaces and neutral-atom provider identities | Existing supported Python math API, benchmarks and explicit provider selections | These are intentional current capabilities, not obsolete aliases. The common production engine supplies complete-crystal potentials explicitly. |
| External legacy atomic-table adapter | Explicit opt-in elastic provider and its validation tests | A distinct input/scattering model with an identified source, not a material fallback. Missing/unlicensed external data are not bundled or substituted. |

Shared settings retain some historical serialized fields for complete project
restoration. Explicit source providers do not interpret those fields as material
physics; existing metadata identifies unused legacy fields. Missing/changed
sources block reruns while saved arrays remain viewable.

## Audit and removal reasoning

The initial review parsed 104 production Python modules and 315 source/test/
script/packaging consumers, including lazy imports. Console roots, PyInstaller
imports, native acceptance dispatch, Qt callbacks and serialization were checked.
Static non-use alone was not treated as proof of dead code.

Active kernels and shared numerical/GUI utilities remain. Packaging/native
acceptance routes remain because application launchers dispatch them lazily.
Historical reports, archives and source pins are evidence of their recorded
revisions, not current import requirements. No independent scientific module or
reference data is deleted. No kernel formula, precision or scientific tolerance
is changed.

Unused imports removed from touched owners include `comparison_text`, an
unneeded control-mixin cancellation import, `hashlib`, `subprocess`,
`perf_counter`, obsolete geometry/model imports, and unused result-browser
`os`/`save_project`/`FlowLayout` imports. Result-only dependencies moved with their
implementation. Two wildcard GUI tests now import their actual dependencies
explicitly instead of depending on accidental module exports.

The existing runtime provenance entry follows the renamed canonical module
(`forward_pipeline.py` replaces the removed `emcd_forward.py` entry); existing
research/source inventories follow moved owners. No new hash layer, stored
numerical baseline or acceptance gate is introduced. Strict scientific kernel
and reference-data pins and immutable historical evidence remain intact.

## Generality and limits

Ni, AFM Cr, Fe3O4 and particular orientations are explicit input/preset/validation
cases. Complete structure/species and the selected elastic provider determine
the potential; per-group source tensors, frames, M, multiplicity and modeled
windows determine material response. The same BW/FFT Single/Double kernels are
used. There is no Cr, magnetite or orientation-specific scientific engine.

Ni `auto` elastic compatibility, default Ni GUI/study examples and known Ni
convergence warnings are distinguished from a calculation choice. Generic
production receives the actual crystal and acknowledged material declaration;
unknown source objects cannot fall through to the historical Ni provider.

Real limits remain: periodic finite ZOLZ support, projected nonabsorbing IAM,
one incident plane wave and localized single ionization; cubic independent-
electron atomic 2p?3d only; XMCD proxy assumptions; explicit source coverage,
frames and scales; no automatic cross-source calibration. The single-provider
site-equivalence gate is narrower than the multisite route. Multi-site Double
`propagation='both'` remains unsupported and requires separate solver runs.
The small Fe3O4 numerical fixture is synthetic stoichiometry-only geometry,
not a quantitative magnetite/Wyckoff benchmark. No future physics is implemented.

## Verification status

The untouched-source focused baseline completed **83 passed, 1 failed** in
375.27 s; all 11 saved-run restoration cases passed. The failure was the existing
historical current-source pin on `gui/app.py`. Earlier sandbox attempts failed in
pytest temporary-file setup and are environment errors, not application results.

The final canonical API matched **2,294 named arrays across 22 cases exactly**
against starting commit `cdb8836388c5ccc5ae7a614b47894c0ab158a824` in memory,
including dtype, both methods' arrays, physical metadata and selected-edge
metrics. Cases include Ni, AFM Cr and synthetic Fe3O4 declarations, Single/Double
Channeling, Bloch/FFT, [001]/[017] and the explicit historical Ni XMCD/atomic
presets. This extends the first extraction's 1,754 arrays across 18 cases.
No numerical baseline files are written and no published benchmark is regenerated.

Eight kernel files remain unchanged from the starting commit: `atomic_dipole.py`,
`atomic_ionization.py`, `mdff_tensor.py`, `double_channeling.py`,
`multislice_double_channeling.py`, `single_channeling_tensor.py`, `scattering.py`
and `physical_elastic.py`. Application source is frozen at
`db3a015aba91f32f90638e987416c19dd0388c32`.

The older `2f9c130` Ni oracle has two strict Double Channeling array failures
already reproduced at the starting commit: maximum absolute differences
`1.3010426069826053e-18` (XMCD) and `2.6469779601696886e-23` (atomic).
Their exact assertions remain unchanged. The refactored output equals the
starting output exactly in these cases.

Affected-check results, final complete regression, native GUI and development
package identities are recorded after the final source is frozen. The earlier
in-progress full run was stopped for the user's API clarification; it is not a
completed regression and must not be counted as one. Historical current-source
registration blockers are reported rather than bypassed or repinned.
