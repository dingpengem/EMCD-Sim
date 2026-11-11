# EMCD-Sim

Research software for electron magnetic circular dichroism (EMCD), core-loss EELS, and dynamical electron diffraction in transmission electron microscopy.

**[v0.9.0-beta.1 Windows Research Beta](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.9.0-beta.1) — prerelease.** Download the complete Windows ZIP from its release assets. This version includes multi-site calculations and crystallographic-grouping, Material/MDFF, sampling, results and persistence workflows. See the [release notes and verification limits](docs/RELEASE_NOTES_0_9_0_BETA_1.md). Older binaries do not acquire these changes automatically.

[Windows download](https://github.com/dingpengem/EMCD-Sim/releases/download/v0.9.0-beta.1/EMCD-Sim-v0.9.0-beta.1-Windows.zip) | [Installation](docs/INSTALL_WINDOWS.md) | [Quick Start](docs/QUICK_START.md) | [Tutorial](docs/TUTORIAL.md) | [User Guide](docs/USER_GUIDE.md) | [MDFF workflows](docs/MDFF_WORKFLOWS.md)

**Development source: v0.9.0-beta.2 Windows candidate — not published.**
It adds the unified Compute Resources panel, adaptive CPU/memory admission and
corrected sampling/resource reporting. The current guides use the representative
243-energy, selected-97×97 Ni example. See [candidate notes](docs/RELEASE_NOTES_0_9_0_BETA_2.md)
and [numerical evidence/missing datasets](docs/WINDOWS_MACOS_NUMERICAL_EQUIVALENCE.md).
The beta.1 download above remains unchanged; its [tagged guide](https://github.com/dingpengem/EMCD-Sim/blob/v0.9.0-beta.1/docs/QUICK_START.md)
describes that older binary.

The independent [published macOS ARM64 Research Beta](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.9.0-beta.1-macos-arm64.1),
[macOS installation](https://github.com/dingpengem/EMCD-Sim/blob/main/docs/INSTALL_MACOS.md)
and [macOS Quick Start](https://github.com/dingpengem/EMCD-Sim/blob/main/docs/QUICK_START_MACOS.md)
are preserved; the Windows candidate is not a macOS update.

## Capabilities

| Area | Current scope |
| --- | --- |
| Structure | ASE/CIF import; general 3D viewer; crystallographic orbit suggestions with original atom indices, Wyckoff/provenance information and manual magnetic subgroup editing. Ordinary CIFs supply neither magnetic order nor MDFF. |
| Elastic scattering | Adaptive Dirac-Pade neutral Z=1–118; Ni Lobato compatibility for historical calculations; explicit finite diffraction support and geometry. |
| Inelastic response | Independent element/site-group XMCD-constrained, synthetic Atomic Ionization, or Manual tensor providers; explicit magnetic reversal pairs and independent modeled energy windows. |
| Propagation | BW and FFT Multislice Single/Double Channeling. Independent localized ionization events sum incoherently; elastic paths within each event remain coherent. BW/MS comparison mode is available for Single Channeling. |
| Results and projects | Shared Global/Local Total, Element, Group Mean, weighted Group Contribution and comparison views; numerical/figure export; multiple saved calculations, restoration and two-run comparison. |

## Current workflow

1. **Material → Open CIF…**, then **3D Structure Viewer… → Site groups**. Inspect suggested structural groups and original atom indices. Split or assign magnetic groups manually where necessary.
2. Select **Global Magnetization Mode** or **Local Site Magnetization Mode**. Material owns target M; MDFF Configuration displays that target read-only. Local mode locks Global M. Exclude non-ionizing groups without removing their atoms from the elastic structure.
3. Use **Configure MDFF…** in the explicit Global/group context. Supply compatible source/model parameters, magnetic-state declarations and full tensor frames. Complete validation/acknowledgement, **Done**, and outer **Apply and Close**. Failed Apply retains accepted settings and the draft; Cancel discards unaccepted changes.
4. Set geometry, propagation, sampling, detectors and resources explicitly. Default uniform sampling requests 241 points per modeled source window and inserts exact selected energies. **Full angular maps at selected energies** uses detector support elsewhere; **Full angular field at every energy (advanced)** is a separate opt-in. The angular detector grid is not the MS FFT mesh.
5. **Run EMCD / EELS**. Automatic internal BLAS limits are verified for the calculation and restored afterward; users need no environment-variable workaround. Manual outer workers remain subject to CPU/memory admission. Progress reports actual work and elapsed time; **Cancel** stops cooperatively.
6. Inspect Results without recalculating. Save the complete project with **File → Save / Save As…**; restore a run or compare exactly two calculations from **Project Results**. Export controls are beside the corresponding results.

Use the [Quick Start](docs/QUICK_START.md) for a representative Ni first case. Extract the complete Windows package and keep `_internal` beside `EMCD-Sim.exe`. Install the documented Microsoft x64 v14 runtime separately. Python, Conda and WIEN2k are not required to run the EXE. The accompanying source kit contains the matching application source and required dependency sources/replacement instructions.

## Scientific and verification limits

Signals preserve declared relative provider amplitudes; they are not automatically calibrated cross-element intensities, electron counts, or magnetic moments. Synthetic Atomic/Manual inputs do not establish quantitative Fe₃O₄, NiFe₂O₄ or Cr spectra. The model retains finite ZOLZ, projected IAM and continuous-depth localized ionization approximations. General beam/FFT/depth/detector convergence and complex-condition BW/MS convergence are incomplete. Magnetization direction is not a complete anisotropic tensor frame; unsupported fixed-source rotations remain rejected. General tensor rotation, magCIF and automatic magnetic-order inference are absent.

The Research Beta has bounded numerical/native evidence, **not a new complete regression pass**. Historical failed/incomplete application-regression and source-guard coverage remains recorded separately. Original-size Fe₃O₄ MS completion and independent clean-PC/VM acceptance remain unverified. See [release evidence](docs/RELEASE_NOTES_0_9_0_BETA_1.md) before interpreting readiness. Linux/macOS packages are not certified.

## Documentation and citation

[Physics and references](docs/PHYSICS.md) · [Units](docs/PHYSICAL_UNITS.md) · [Changelog](docs/CHANGELOG.md) · [Documentation index](docs/INDEX.md). Historical published-binary instructions remain available at their release tags. Earlier magnetic-sign conventions and unknown provenance must not be silently relabeled as current.

Cite the exact release/commit, crystal, MDFF source and declarations, elastic provider and numerical settings. No software-paper DOI or universal material calibration is claimed.

Application source is [MIT](LICENSE). Adaptive coefficients retain their [Apache-2.0 license](src/emcd_sim/data/adaptive_dirac_pade_2026/LICENSE), [NOTICE](src/emcd_sim/data/adaptive_dirac_pade_2026/NOTICE) and provenance. Dependency licenses apply separately; see [Qt redistribution and source arrangements](packaging/assets/qt-licenses/README.txt).
