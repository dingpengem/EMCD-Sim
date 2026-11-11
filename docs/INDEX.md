# Documentation index

[Home](../README.md) · [Windows Research Beta](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.9.0-beta.1) · [macOS ARM64 Research Beta](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.9.0-beta.1-macos-arm64.1)

## Current user documentation

|Document|Use it for|
|---|---|
|[Windows Installation](INSTALL_WINDOWS.md)|Correct Windows ZIP, requirements and troubleshooting|
|[macOS ARM64 Installation](INSTALL_MACOS.md)|Apple Silicon Finder installation, signing limitations and examples|
|[macOS ARM64 Quick Start](QUICK_START_MACOS.md)|Representative Ni energy spectrum and 97×97 momentum maps; complete settings and limits|
|[Quick Start](QUICK_START.md)|Small first Ni simulation, explicitly not converged research settings|
|[MDFF construction and workflows](MDFF_WORKFLOWS.md)|Current XMCD, Atomic, constant/manual spectral and imported methods; explicit selections, units/defaults, existing-input example, and normal project creation|
|[Complete Tutorial](TUTORIAL.md)|From crystal/diffraction through MDFF, channeling and measurement definitions|
|[User Manual](USER_GUIDE.md)|Control-by-control reference, projects, warnings and exports|
|[Physics and numerical methods](PHYSICS.md)|Current corrected convention, support, approximations and source map|
|[Physical units](PHYSICAL_UNITS.md)|g=1/d versus Q=2πg; unchanged saved numbers|
|[GUI technical navigation (historical baseline)](EMCD_GUI.md)|Original source map and diagnostic boundaries; use the current MDFF guide for the redesigned interface|
|[Local Part 1B provider consolidation](GENERALIZED_CODE_CONSOLIDATION_0_8_1.md)|Unified MDFF architecture, compatibility inventory, exact source/native acceptance and limits; separate from publication|
|[Verified figure provenance](images/v070b1/README.md)|Actual EXE captures, case-study figures and source/data hashes|
|[Recalculated Ni example provenance](images/ni017_flipm_recomputed/README.md)|Fresh 9/30 nm spectra, twelve portraits, conventional versus fixed-detector Flip-M|
|[Changelog](CHANGELOG.md)|Version/milestone and documentation history|

The existing [Windows Quick Start](QUICK_START.md) and cross-platform scientific Tutorial/User Guide originated from the **Windows v0.9.0-beta.1** workflow and may contain Windows paths. Mac users should start with the dedicated [macOS Installation](INSTALL_MACOS.md) and [macOS Quick Start](QUICK_START_MACOS.md). Each release's documentation defines its own acceptance scope. Older v0.8 binaries retain their tagged documentation. Historical acceptance/release records below keep their original source, artifact and verification identities.

## Scientific validation and acceptance

- [Neutral-atom elastic providers](ELASTIC_ATOMIC_FACTORS.md): bundled Apache-2.0 Z=1–118 Adaptive default, named Ni Lobato compatibility, external Z=1–98 table and strict Mott limits, CIF indexing and [local acceptance](acceptance/unified-elastic-2026-11-03/FINAL_INTEGRATION_RECOMMENDATION.md).

- [v0.9.0-beta.1 Windows prerelease](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.9.0-beta.1): [Windows evidence and limitations](RELEASE_NOTES_0_9_0_BETA_1.md).
- [v0.9.0-beta.1 macOS ARM64 prerelease](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.9.0-beta.1-macos-arm64.1): [Mac release notes](https://github.com/dingpengem/EMCD-Sim/blob/v0.9.0-beta.1-macos-arm64.1/docs/RELEASE_NOTES_MACOS_ARM64_1.md) and attached acceptance review.
- [Historical v0.8.1-beta.2 release](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.8.1-beta.2): beta.2 assets and publication status; [release validation](RELEASE_NOTES_0_8_1_BETA_2.md#validation-evidence-and-scoped-exception) keeps its original verification scope.
- [Historical v0.8.0-beta.1 release](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.8.0-beta.1): that milestone's assets, hashes and limitations.
- [Original candidate/native acceptance](WINDOWS_ZOLZ_97B2220_CANDIDATE_ACCEPTANCE.md): recorded build `41516996056`, exact binary provenance and bounded native outcomes. Its prepublication status is historical.
- [Physics correction acceptance](PHYSICS_CORRECTION_ACCEPTANCE.md) and [final integration](PHYSICS_CORRECTION_FINAL_INTEGRATION.md): corrected forward-Born conventions and independent controls.
- [Generalized Multislice merge review](GENERALIZED_MULTISLICE_MERGE_READINESS.md): bounded five-orientation support and unresolved [111] convergence, not unrestricted certification.
- [Ni [117] symmetry validation](NI_117_FINAL_SYMMETRY_VALIDATION.md): geometry/magnetization/parity interpretation with its original settings and limits.
- [Uniform beam-basis study](DOUBLE_CHANNELING_UNIFORM_BASIS.md): tested configurations, independent sensitivity and comparison scope.
- [Historical 9/30 nm case-study tutorial](https://github.com/dingpengem/EMCD-Sim/blob/v0.8.1-beta.2/docs/TUTORIAL.md#part-vii-practical-ni-017-case-study): existing BW Double spectra and measurement denominators, retained unchanged; no rerun required.

Windows native acceptance is recorded per release; independent clean-machine acceptance is **not tested**. Linux has an unresolved Python shutdown `bool_dealloc` abort; macOS tests stall in a Qt modal preflight dialog. Those failures are not suppressed and are not Windows-only release gates. Functional support, BW/MS agreement, numerical convergence and physical validation are separate claims.

## Historical records

Historical reports retain their original version, sign convention, settings, labels and publication-status statements. They are evidence about those milestones, not current instructions or automatic validation of old signed data.

- [v0.7.0 milestone release notes](RELEASE_NOTES_0_7_0_BETA_1.md) and [earlier local acceptance](WINDOWS_0_7_0_BETA_1_ACCEPTANCE.md).
- [Pre-correction physics/source audit](PHYSICS_CONVENTIONS_AND_SOURCE_MAP.md): explicitly uncorrected source at its audit date; do not use its same-index contraction as today's rule.
- [Earlier physics overview](https://github.com/dingpengem/EMCD-Sim/blob/08d04fc35fca2071cc7e73af0aaa1de45e49a3f4/docs/PHYSICS.md), [manual](https://github.com/dingpengem/EMCD-Sim/blob/08d04fc35fca2071cc7e73af0aaa1de45e49a3f4/docs/USER_GUIDE.md) and [GUI milestone record](https://github.com/dingpengem/EMCD-Sim/blob/08d04fc35fca2071cc7e73af0aaa1de45e49a3f4/docs/EMCD_GUI.md), preserved at immutable revision `08d04fc3`.
- [Beta 3 Actions instructions](WINDOWS_BETA_3.md), [earlier Windows installation/acceptance](V061_BETA_ACCEPTANCE.md) and [performance integration](GUI_PERFORMANCE_INTEGRATION.md).
- [Earlier Ni [017] gallery](NI_017_CASE_STUDY_GUIDE.md) and [original source audit](SOURCE_CLEANUP.md). Legacy figures must not be silently relabeled with the corrected magnetic convention.

## Experimental and planned work

The [generalized Multislice architecture](GENERALIZED_MULTISLICE_ARCHITECTURE.md) describes the engine now used by the bounded projected backend. The [Atomic 3D development plan](ATOMIC_3D_MULTISLICE_DEVELOPMENT.md) is a plan, **not a released atomic-3D implementation**. Complete complex DFT-derived Ni MDFF, comprehensive HOLZ/TDS/absorption, calibrated experimental handedness/counts and arbitrary-material quantitative EMCD are not established by these documents.

Retired/source-only research drivers are not buttons in the released GUI. To reproduce a historical study, preserve its exact source/settings/checkpoints and resolve its convention/convergence warnings; do not rerun it merely to read the current guides.

## v0.8.1-beta.1 declared-source research workflows

- [Release notes](RELEASE_NOTES_0_8_1_BETA_1.md)
- [Generalized single-element source contract](GENERALIZED_SINGLE_ELEMENT_EMCD_DESIGN.md)
- [Explicit approximate atomic model](GENERALIZED_ATOMIC_IONIZATION.md)
- [Independent local merge acceptance](GENERALIZED_ATOMIC_IONIZATION_MERGE_ACCEPTANCE.md)
- [Cleanup inventory and acceptance](SOURCE_CODE_CLEANUP_0_8_1.md)

Synthetic non-Ni examples are mathematical software tests, not validated material
EMCD. Historical figure and release acceptance records retain their original scope.
