# Current-runtime source cleanup

## Scope and ancestry

Started on `cleanup/source-package` at
`df0e089b45c8e2051fe0ff6f9f668e3d91ca3f2f`. A fresh `git fetch origin`
confirmed that the previous cleanup was already included in `origin/main`.
This deeper cleanup uses the separate local branch `cleanup/current-runtime-only`.
No main merge, push, release/tag, version change, EXE rebuild or production
recalculation is part of this task.

The package shrank from **78 to 46 Python files**: **32 modules deleted**,
with required primitives extracted before deleting mixed drivers. The earlier
83-to-78 cleanup remains integrated. No archive directory or compatibility
wrapper modules were added. Git history retains historical implementations.

The [78-module inventory](SOURCE_MODULE_INVENTORY.csv) records classification,
production callers, disposition, reason, original symbols and remaining imports.
The [complete file change list](SOURCE_FILE_CHANGES.csv) covers source, tests,
tools, documentation and directly affected workflows. The
[numerical validation record](SOURCE_CLEANUP_VALIDATION.json) records configurations,
counts and array digests.

## Application roots and dependency review

The audit starts at the current GUI launcher/app, not all tests or old CLI
registrations. Static AST inspection includes function-local imports and
`from package import module` forms. The current GUI closure contains 43 files;
the two module launchers and the supported transition-import interface account
for the other three. Every remaining module is reachable from these current
roots or explicitly supported interfaces. No internal dynamic module loader
remains. Qt signal connections, lazy imports, project serialization and the
five PyInstaller hidden imports were reviewed; all hidden imports resolve.
Both `__main__` modules are launchers, not ordinary import-only libraries.

Every GUI module was included. `gui.stage_b` is the current worker/control mixin,
despite its historical name. Current native worker and cancellation diagnostics
remain supported launch options; obsolete Beta/RC/Stage-F orchestration does not.
Live advanced normalization widgets remain because current results/comparison
views call them. No beam, memory, cancellation or threading guard was removed.

Mixed modules were reviewed below the file level: the old scalar contraction
fallback in private `gui.emcd_forward._contract` was unreachable from the current
scheduler and removed; the active prepared-result/parity path is unchanged.
`benchmark` now constructs physical models/apertures, `simulation` holds current
model/result containers, `elastic` holds beam support/coherence, and
`xmcd_postedge_normalization` contains normalization/diagnostics only. The obsolete
extinction-distance surrogate, scalar Gaussian MDFF and voltage-bias model are
retired; accelerating-voltage controls and the physical IAM engines remain.

## Deleted package modules

- `atomic_multislice_geometry.py`
- `cli.py`
- `compare_conditions.py`
- `convergence.py`
- `elastic_reference.py`
- `mdff_reference.py`
- `multislice_emcd_reference.py`
- `ni_017_high_mistilt_analysis.py`
- `ni_017_high_mistilt_convergence.py`
- `ni_017_high_mistilt_plots.py`
- `ni_017_high_mistilt_xy.py`
- `ni_017_mistilt.py`
- `ni_710_geometry.py`
- `ni_710_mistilt.py`
- `ni_atomic_reference.py`
- `ni_data_audit.py`
- `ni_mistilt_diffraction.py`
- `ni_mistilt_eels.py`
- `ni_mistilt_series.py`
- `postedge_emcd_maps.py`
- `scan.py`
- `xmcd_basis_convergence.py`
- `xmcd_geometry_decomposition.py`
- `xmcd_indexed_maps.py`
- `xmcd_postedge_robustness.py`
- `xmcd_reversal.py`
- `gui.beta_acceptance.py`
- `gui.rc_acceptance.py`
- `gui.stage_f_acceptance.py`
- `inelastic.py`
- `voltage.py`
- `diffraction.py`

Historical [710] and mistilt scan/report factories, P1 slicing diagnostics,
old research CLI frontends and their workflow-only dependencies are no longer
distributed in `src`. Historical scientific outputs, reports, datasets and
published distributions are preserved. Old reproduction commands require their
recorded Git revision; this audit does not claim all historical scripts run on
the cleaned package.

## Extracted production primitives

| Former module | Current module | Unchanged primitive |
| --- | --- | --- |
| `elastic_reference` | `scattering` | `FourierCutoffPotential` |
| `multislice_emcd_reference` | `multislice_reference` | `project_fft_amplitudes` |
| `multislice_emcd_reference` | `multislice_reference` | `coherence_from_amplitudes` |
| `multislice_emcd_reference` | `multislice_reference` | `complex_wave_diagnostics` |
| `postedge_emcd_maps` | `emcd_angular_plots` | `paired_geometry` |
| `postedge_emcd_maps` | `emcd_angular_plots` | `paired_maps` |
| `postedge_emcd_maps` | `emcd_angular_plots` | `integrate_paired` |
| `ni_710_geometry` | `ni_017_geometry` | `crystal` |
| `ni_710_geometry` | `ni_017_geometry` | `beams → `Ni017Geometry._basis_beams` (private name only)` |
| `ni_atomic_reference` | `ni_local_mdff` | `core_spinor_amplitude` |
| `ni_atomic_reference` | `ni_local_mdff` | `ni_2p_to_3d_dipole` |
| `gui.rc_acceptance` | `gui.project_io` | `fingerprints` |
| `diffraction` | `physical_elastic` | `bragg_tilt_mrad` |
| `diffraction` | `physical_elastic` | `excitation_errors_angstrom_inv` |

All 14 extracted class/function ASTs match exactly, allowing only the private
basis-helper rename. The inherited [710] support is inlined in `Ni017Geometry`,
without retaining a [710] class or adding an abstraction layer. Its original
intermediate-index construction and [017] remapping are preserved exactly.
Unused historical map-export/coordinate helpers and reference drivers were
deleted; actual GUI ZA/Thales/index/detector decoration remains.

## Supported interfaces and intentional retirements

Installed commands retained: `emcd-gui`, `emcd-import-transitions`,
`emcd-ni-local-mdff`. The first launches the desktop; the others prepare
validated complex-transition datasets and the same atomic model used by the
GUI. They do not run DFT or parse missing complex WIEN2k amplitudes.
`python -m emcd_sim` now launches the desktop, as does `python -m emcd_sim.gui`.
The supported low-level API exposes physical BW, beam/coherence, tensor,
detector and model/result primitives. The old scalar `EMCDSimulation.run`,
`ElasticModel`, scalar spectrum and voltage-bias interfaces are retired.

Removed installed commands:

`emcd-ni`, `emcd-scan`, `emcd-convergence`, `emcd-compare`, `emcd-elastic-reference`, `emcd-mdff`, `emcd-ni-atomic`, `emcd-audit-ni-data`, `emcd-xmcd-maps`.

Removed GUI options: `--rc-acceptance`, `--rc-source`, `--rc-reopen`,
`--beta-acceptance`, `--beta-source`, `--beta-production`,
`--stage-f-acceptance`, `--stage-f-project`, `--stage-f-comparison`.
Current preview/smoke, parallel-worker and cancellation options remain.

The two workflows that regenerated old condition/indexed-map studies were
deleted. Cross-platform CI now smoke-tests the supported desktop launcher.
No workflow was run and no generated scientific example was modified.

## Tests and historical tooling

Historical-only test files deleted:

- `tests/test_angular_map_convergence.py`
- `tests/test_atomic_multislice_geometry.py`
- `tests/test_compare_conditions.py`
- `tests/test_convergence.py`
- `tests/test_double_channeling_cutoff_study.py`
- `tests/test_double_channeling_final_200kv.py`
- `tests/test_double_channeling_uniform_basis.py`
- `tests/test_ni_017_high_mistilt_xy.py`
- `tests/test_ni_017_thickness_scan.py`
- `tests/test_ni_710_geometry.py`
- `tests/test_ni_data_audit.py`
- `tests/test_ni_mistilt_diffraction.py`
- `tests/test_ni_mistilt_eels.py`
- `tests/test_ni_mistilt_series.py`
- `tests/test_ni_prb2007_validation.py`
- `tests/test_ni_voltage_dependence.py`
- `tests/test_research_scripts.py`
- `tests/test_tilt_thickness_scan.py`
- `tests/test_xmcd_basis_convergence.py`
- `tests/test_xmcd_geometry_decomposition.py`
- `tests/test_xmcd_postedge_robustness.py`

Mixed test files retain their physical checks: FFT phase/coherence, shared tensor
contraction, fractional area/bounds/grouping/parity, SOC selection rules, CSV
conjugation, post-edge algebra, reciprocal signs and actual GUI overlays. Their
retired CLI/scan/export assertions were removed. Existing scalar demonstrations
were replaced with current physical tensor paths where the scientific check
still applies. Test-only synthetic transitions, reversal fixtures, display
assertions and old-source import translation live in `tests/runtime_fixtures.py`
or the specific regression, not in installed runtime code. Historical numerical
baselines loaded from Git keep their mathematical statements and tolerances;
only extracted dependency import paths are translated. Persistence's AST guard
permits only the added, exactly extracted fingerprint helper.

The obsolete voltage-study driver and its hash-gate test are retired together.
Its independently useful relativistic wavelength / SI interaction-constant /
extinction-distance checks are retained directly in `test_physical_elastic.py`,
with the original numerical expectations and tolerances; no voltage scan runs.
The prior one-test failure is therefore no longer an applicable current-runtime
gate. This does **not** certify old results against new source: original hashes
and archived provenance remain unmodified. Current project file hashes, array
shape/dtype validation, source-change checks and rerun admission are unchanged.

Directly dependent historical tools deleted (not moved to another archive):

- `scripts/angular_map_convergence.py`
- `scripts/audit_historical_ms_source.py`
- `scripts/finish_ni_emcd_thickness.py`
- `scripts/gui_stage_c_validation.py`
- `scripts/gui_stage_g_validation.py`
- `scripts/ni_017_thickness_scan.py`
- `scripts/ni_double_channeling_bw.py`
- `scripts/ni_double_channeling_cutoff_report.py`
- `scripts/ni_double_channeling_cutoff_study.py`
- `scripts/ni_double_channeling_final_200kv.py`
- `scripts/ni_double_channeling_final_report.py`
- `scripts/ni_double_channeling_full_benchmark.py`
- `scripts/ni_double_channeling_full_report.py`
- `scripts/ni_double_channeling_full_spectra.py`
- `scripts/ni_double_channeling_gui_validation.py`
- `scripts/ni_double_channeling_ms_validation.py`
- `scripts/ni_double_channeling_spectral_report.py`
- `scripts/ni_double_channeling_uniform_basis.py`
- `scripts/ni_double_channeling_uniform_basis_report.py`
- `scripts/ni_emcd_complete_thickness.py`
- `scripts/ni_full_spectra_gui_validation.py`
- `scripts/ni_prb2007_geometry_validation.py`
- `scripts/ni_two_beam_geometry_comparison.py`
- `scripts/ni_voltage_dependence.py`
- `scripts/report_angular_convergence.py`
- `scripts/research/atomic_slicing_diagnostics.py`
- `scripts/research/fractional_aperture_validation.py`
- `scripts/research/ni_017_comparison.py`
- `scripts/validate_v060_presentation.py`
- `scripts/verify_v061_candidate.py`
- `scripts/windows_beta_reference_audit.py`

Other repository-only tools are outside the installed package. Remaining compact
profiling, safety, saved-result and source-spectrum helpers use current engines;
their presence does not root extra source modules. Archival documentation is
preserved as historical context, not a promise that retired commands still run.

## Numerical equivalence

Two before/after comparisons used the integrated `df0e089` runtime and the same
working source spectrum, float64/complex128 and single native thread:

| Comparison | Arrays | Values | Result |
| --- | ---: | ---: | --- |
| GUI: XMCD/atomic × Single/Double × BW/MS | 376 | 42,826 | Identical dtype, shape and bytes |
| Direct complex responses, basis/Hamiltonians, post-edge | 54 | 19,122 | Identical dtype, shape and bytes |

The first records hkl, Hamiltonian, complex waves, depth coherences, all detector
states and spectral components/asymmetries, L3/L2 full maps and fractional weights.
Configuration: Ni [017], 300 kV, 8 nm, 0.9/1.8 cycles/Å beam/potential cutoffs,
9×9 angular grid, 24×24 FFT, 9 depth nodes, maximum 0.2 nm slice, 16 aperture
subpixels, nine full-range spectral base samples plus locked edges; both MDFFs
and both channeling modes, with BW and MS independent. No post-edge fit is enabled
in this reference; its algebra is checked separately.

The direct comparison checks ordered bases/Hamiltonians at 0.9, 3.2, 4.6 and
6.2 cycles/Å with potential cutoff 2.5, plus Single even/odd integrands and direct
complex BW/MS Double Cartesian responses at both native edges. Response settings:
200 kV, 8 nm, 0.9/1.8 support, FFT 24, 9 depth nodes, three detector directions.
Synthetic nonzero post-edge spectra exercise all normalization arrays without
changing any source energy axis. These are equivalence checks, not new convergence
claims for these deliberately compact numerical configurations.

The underlying BW Hamiltonian, MS Single and Double propagation, MDFF, Coulomb,
site phases, tensor contractions, precision and integration formulas are unchanged.
Core solver and safety files were also checked directly against the baseline.

## Current application validation

- Real Python-source Qt window launched offscreen and completed the default
  elastic preview; screenshot saved locally. Default Ni, target/ZA/Thales markers,
  detector placement, tilt coordinates and reversible view remain functional.
- Actual modest BW/MS Single/Double and Both calculations, XMCD and atomic MDFF,
  native L3/L2 maps, detector EELS and parity: checked by reference runs and tests.
- Raw/Relative/Asymmetry and advanced corrected displays, derived exports,
  save/reopen, source relocation, cancellation, memory admission and native BLAS
  worker guards: retained regression checks pass.
- An existing user project at `C:/data/EMCD_sim_data/Ni017_20261020_041237Z`
  loads and renders diffraction, L3/L2 maps and EELS with all forward entries
  forbidden; its 11 files and detector arrays remain unchanged.
- All 44 ordinary modules and three installed CLI targets import; both module
  launchers work; all five packaging hidden imports resolve without building.

Final full current-production regression run: **415 passed, 32 plotting/Qt
warnings in 275.43 s**. Six focused core-physics tests also pass, including
the independent wavelength, SI interaction-constant and extinction-distance
regression retained from the retired voltage study. Thus all **416 unique
retained tests** are verified, with no unresolved failures. The 46-test
import-migration/GUI/baseline group and the two untracked local Tilt-Y tests also
passed. Numerical tolerances and expected scientific values were not relaxed.

An earlier migration run found that a [001] geometry test called the GUI preview
API for a 213-beam basis. The corrected test explicitly asserts the unchanged
121-beam interactive rejection and checks the full 4.6 cycles/Å basis through
the supported low-level `BeamSet.zolz` API. All four geometry tests pass;
neither cutoff nor safety cap was changed. The final full run includes this fix.

Windows sandbox permissions prevented pytest temporary-directory access even
inside the workspace; verification used normal Windows permissions. This is not
a solver or test-tolerance workaround. No broad historical sweep was executed.

## Preservation, provenance and limitations

All **204 production checkpoints** match their original SHA256 manifest. Three
Windows archives match their prior hashes, including Beta 1 `9fd5e714…94f`,
published Beta 2 `04511b73…8d9` and the local 3.2/2.5 build `4be5b465…c03`.
The modified working Ni source remains unchanged at SHA256
`a0e28ea6423b6c7832bb3cce6d69d71aa59336a221baeee3d2556b49ba501283`.
No user companion data or historical figure/NPZ was staged or rewritten.
New calculations keep honest current source/commit hashes; no aliases for the
old provenance were forged. The published executables are not rebuilt and still
contain their original source/CLI interfaces.

Untracked Tilt-Y work remains outside this commit. Three import paths in its
existing `scripts/ni_raw_tilt_spectra.py` were migrated to the extracted helpers;
all function/class ASTs are identical, and its two tests pass. Other untracked
files, including the old convergence-finishing runner, were preserved; historical
runners may require their original Git revision after intentional study retirement.

Application version remains `0.6.1b2`. GUI starting cutoffs remain **3.2/2.5**,
with 300 kV, 97×97 angular grid and 2048 MiB; existing explicit saved settings
remain unchanged. Potential/basis/sampling convergence is geometry-dependent;
method agreement is not independent physical validation. The potential remains
projected IAM, the effective/atomic MDFF approximate rather than full DFT-derived,
and outgoing channeling present only for Double. Absolute intensities, native
energy calibration and experimental electron-count/SNR calibration remain
unvalidated. No new physics or global convergence claim is made.

**Is every remaining Python module necessary for the current application or
supported runtime interfaces? Yes, within the documented support boundary.**
Forty-three are in the actual GUI dependency closure; the other three are the
two supported module launchers and complex-transition import interface. There
are no `UNCERTAIN` modules and no historical scan driver retained solely for its
tests. Current diagnostic launch modes and numerical APIs are explicit supported
interfaces, not compatibility wrappers.
