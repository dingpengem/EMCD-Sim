# Source code cleanup for v0.8.1-beta.1

Baseline: `82bd58098cf5722b342c2d92b2395c223faa4cde`, clean accepted main.
Branch: `cleanup/v081-source-review`; isolated `build/v081-source-cleanup` worktree.

## Inventory and call graph

All **64 src Python files** were read and parsed, including function-local imports.
The [complete inventory](SOURCE_CODE_CLEANUP_0_8_1_INVENTORY.csv) records each file,
classification, incoming package imports, external references, reason and baseline
source digest. The graph includes GUI callbacks/lazy acceptance branches, public
exports, both module launchers and the three registered console entry points.
Tests, study scripts, documentation, project serialization, PyInstaller Analysis and
its five explicit ASE/Matplotlib hidden imports were also searched. Static textual
references are supporting evidence, not proof of use or disuse.

Categories: A active production; B active compatibility/public API; C packaging/runtime
or explicitly supported native acceptance; D active scientific reference; E historical;
F unused development; G duplicate/superseded; H uncertain. No whole module qualified
for E/F/G removal. Uncertain import bindings were retained rather than force-deleted.
The earlier cleanup already removed 32 obsolete modules; the subsequent additions
are active generalized physics, numerical safety, source-contract and acceptance code.

## Safe changes and retained implementations

No Python file or scientific function was deleted. Five unused import bindings were
removed: `os` and `np` in `gui/cancellation_acceptance.py`, `datetime` and `timezone`
in `gui/runtime.py`, and `asdict` in `gui/unified_elastic_acceptance.py`. All functions,
expressions and numerical defaults in those files are unchanged. No tests were removed.

`benchmark`, `crystal`, `elastic`, `geometry`, `scattering`, `ni_local_mdff`,
`wien2k_xmcd` and `xmcd_effective_mdff` still provide current or historical Ni/API
behavior. The old-looking `study_geometry` helpers remain used by scientific study
scripts; `wien2k_source_audit` is an independent optional source reference.
`multislice_reference` is the actual independent elastic FFT route, not a discarded
Bloch implementation. BW, MS, Single and Double kernels remain separate useful
implementations. GUI Stage B is the active controller. Diagnostic acceptance modules
are public opt-in CLI routes used by packaging/CI and are not dead GUI helpers.

Apparent unused imports in `__init__` and `atomic_ionization` are intentional public
exports. Other questionable aliases in protected adapters were retained: cleanup is
not a reason to rewrite or relax historical source guards or API behavior. No solver
math, kernel, reference fixture, source-convention identifier, historical figure,
research output/checkpoint, IAM provider/default or version was changed.

## Native acceptance support

`packaging/native_acceptance.py` and the opt-in launcher `--release-acceptance` route
exercise actual Qt widgets/workers in the frozen executable: eight small Ni/synthetic
Fe cases, original Ni providers, Single/Double BW/MS, CIF parsing, tensor generation,
import validation, project roundtrip, stale-generation state, checksums, magnetic
state and source-provenance rejection. The original explicit synthetic parameter
example is collected as data so users and frozen QA share the same declared input.
This is packaging QA, not a new scientific feature. No broad hidden-import workaround
is introduced. Standard GUI launch behavior remains unchanged.

## Baseline and acceptance

The exact accepted main was used before edits to record **1,080 numerical arrays**
from Ni XMCD/atomic and synthetic Fe imported/atomic cases, each Single/Double and
BW/MS with maps/spectra. After cleanup every array is **exactly equal**, including
NaN placement. Valid Ni (200) and Fe (110) targets are used; the rejected initial
Ni (110) diagnostic was preserved, not treated as evidence.

Exact tested cleanup source: **`e601e04540a06ed490466680bc4fa151146c1eaa`**.
The subsequent acceptance-document commit changes no executable source.

|Gate|Result|
|---|---|
|Full native Windows source suite|**754 passed, 39 skipped, 0 failures/errors**, 1297.24 s; 1013 warnings retained|
|Skip comparison with accepted baseline|Same 39 test identities/reasons; no newly failing or skipped tests|
|Accepted-main API baseline vs cleanup|**1,080 arrays exactly equal** across eight Ni/synthetic Fe provider/channel cases, each BW/MS|
|Extracted standalone EXE|**8/8 actual GUI worker cases passed**, frozen=true, Qt platform=windows, process exit 0, clean shutdown|
|Source GUI vs extracted EXE|**1,080/1,080 arrays bitwise equal**, max absolute difference 0|
|Manifest|**614 files** verified against names/sizes/SHA256; bundled sample input, coefficient notices and Windows platform DLL verified|
|Historical Ni|Exact source regression and protected 160-array evidence pass; genuine archived Lobato project reproduced natively within its existing 2e-12 elastic criterion|
|Console/public imports|Complete suite verifies all registered console entry points, public exports and explicit hidden imports|

Cleanup candidate ZIP SHA256:
`4e321cfce9d7d9d0d30066be23f0b20370cfccd45143d7ffbeb46ac62ed0537a`.
This is an **unpublished cleanup candidate at the old application version**, not the
v0.8.1 release asset. Native validation used a freshly extracted ZIP, minimal system
PATH, no Python/Conda paths and a separate writable profile. It is same-host native
acceptance, not an independent clean-PC/VM certification.

The EXE generated atomic tensors from complete declared parameters, validated source
hashes/element/state, exercised both old Ni providers and generalized imported/atomic
Single/Double BW/MS, saved/reopened projects, rejected partial provenance and failed
generation with stale state invalidation, and exported scientific PNG/SVG/CSV data.
Synthetic Fe remains a software fixture; quantitative material accuracy is not claimed.

Local evidence: `outputs/release-review/cleanup-full.{log,xml}`,
`cleanup-package-verification.json`, `cleanup-source-frozen-comparison.json`,
`cleanup-frozen/acceptance.json`, and the baseline/after-cleanup NPZ snapshots.
Source and EXE source-SHA markers agree. The native module/license notices remain
unchanged apart from the explicitly included original synthetic parameter example.

Additional function-level review found four definitions without direct Python
references: `takeAt`, `expandingDirections`, `hasHeightForWidth` and `eventFilter`
in `gui/responsive.py`. These are Qt virtual callbacks invoked from C++, and were
correctly retained. AST comparison confirms that all non-import module code and all
function bodies/defaults in the three cleaned modules are unchanged.

**GO for conservative cleanup integration.** No source module qualified for safe
removal; no compatibility/reference function or test was deleted. The later release
requires a separate versioned build and complete release acceptance.

Remaining opportunities are explicitly unsupported removals of public aliases or
historical API interfaces; they need a separately scoped deprecation policy and
consumer evidence. No uncertain module should be deleted to meet a file-count target.

## Per-file classification

|Module|Class|Disposition|
|---|---|---|
|`src/emcd_sim/__init__.py`|A|retain|
|`src/emcd_sim/__main__.py`|C|retain|
|`src/emcd_sim/adaptive_scattering.py`|A|retain|
|`src/emcd_sim/atomic_ionization.py`|A|retain|
|`src/emcd_sim/benchmark.py`|B|retain|
|`src/emcd_sim/cancellation.py`|A|retain|
|`src/emcd_sim/crystal.py`|B|retain|
|`src/emcd_sim/crystallography.py`|A|retain|
|`src/emcd_sim/double_channeling.py`|A|retain|
|`src/emcd_sim/elastic.py`|B|retain|
|`src/emcd_sim/elastic_providers.py`|A|retain|
|`src/emcd_sim/emcd_angular_plots.py`|A|retain|
|`src/emcd_sim/generalized_xmcd.py`|A|retain|
|`src/emcd_sim/geometry.py`|B|retain|
|`src/emcd_sim/gui/__init__.py`|C|retain|
|`src/emcd_sim/gui/__main__.py`|C|retain|
|`src/emcd_sim/gui/app.py`|A|retain|
|`src/emcd_sim/gui/cancellation_acceptance.py`|C|retain|
|`src/emcd_sim/gui/channeling.py`|A|retain|
|`src/emcd_sim/gui/compare_results.py`|A|retain|
|`src/emcd_sim/gui/component_display.py`|A|retain|
|`src/emcd_sim/gui/desktop_acceptance.py`|C|retain|
|`src/emcd_sim/gui/emcd_forward.py`|A|retain|
|`src/emcd_sim/gui/generalized_forward.py`|A|retain|
|`src/emcd_sim/gui/geometry.py`|A|retain|
|`src/emcd_sim/gui/imported_tensor_ui.py`|A|retain|
|`src/emcd_sim/gui/memory_budget.py`|A|retain|
|`src/emcd_sim/gui/normalization_controls.py`|A|retain|
|`src/emcd_sim/gui/normalization_export.py`|A|retain|
|`src/emcd_sim/gui/numerical_settings.py`|A|retain|
|`src/emcd_sim/gui/parallel_acceptance.py`|C|retain|
|`src/emcd_sim/gui/parallel_resources.py`|A|retain|
|`src/emcd_sim/gui/prb_benchmark.py`|A|retain|
|`src/emcd_sim/gui/prb_controls.py`|A|retain|
|`src/emcd_sim/gui/project_io.py`|A|retain|
|`src/emcd_sim/gui/propagation.py`|A|retain|
|`src/emcd_sim/gui/responsive.py`|A|retain|
|`src/emcd_sim/gui/results.py`|A|retain|
|`src/emcd_sim/gui/results_browser.py`|A|retain|
|`src/emcd_sim/gui/runtime.py`|C|retain|
|`src/emcd_sim/gui/scientific_acceptance.py`|C|retain|
|`src/emcd_sim/gui/signal_normalization.py`|A|retain|
|`src/emcd_sim/gui/stage_b.py`|A|retain|
|`src/emcd_sim/gui/unified_elastic_acceptance.py`|C|retain|
|`src/emcd_sim/imported_mdff.py`|A|retain|
|`src/emcd_sim/ionization_sites.py`|A|retain|
|`src/emcd_sim/legacy_atomic_factors.py`|A|retain|
|`src/emcd_sim/mdff_tensor.py`|A|retain|
|`src/emcd_sim/mirror_parity.py`|A|retain|
|`src/emcd_sim/multislice_double_channeling.py`|A|retain|
|`src/emcd_sim/multislice_reference.py`|A|retain|
|`src/emcd_sim/ni_local_mdff.py`|B|retain|
|`src/emcd_sim/physical_elastic.py`|A|retain|
|`src/emcd_sim/projected_geometry.py`|A|retain|
|`src/emcd_sim/projected_potential.py`|A|retain|
|`src/emcd_sim/scattering.py`|B|retain|
|`src/emcd_sim/simulation.py`|A|retain|
|`src/emcd_sim/single_channeling_tensor.py`|A|retain|
|`src/emcd_sim/study_geometry.py`|D|retain|
|`src/emcd_sim/transition_csv.py`|A|retain|
|`src/emcd_sim/wien2k_source_audit.py`|D|retain|
|`src/emcd_sim/wien2k_xmcd.py`|B|retain|
|`src/emcd_sim/xmcd_effective_mdff.py`|B|retain|
|`src/emcd_sim/xmcd_postedge_normalization.py`|A|retain|
