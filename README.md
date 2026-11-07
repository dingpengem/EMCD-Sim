# EMCD-Sim

Research software for **electron magnetic circular dichroism (EMCD)**, core-loss EELS, and dynamical electron diffraction in transmission electron microscopy. EMCD-Sim connects crystal geometry, elastic propagation, a declared mixed dynamic form factor (MDFF), and virtual detectors to examine magnetization reversal and model sensitivity.

[Published Windows Research Beta](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.8.1-beta.1) | [Installation](docs/INSTALL_WINDOWS.md) | [First calculation](docs/QUICK_START.md) | [MDFF workflows](docs/MDFF_WORKFLOWS.md) | [User manual](docs/USER_GUIDE.md)

**Next prerelease: v0.8.1-beta.2, draft only.** Current main contains the MDFF update below. Its local Windows development EXE passed native verification and the user's trial, but redistribution of that bundle remains blocked by the dependency-license requirements in the [draft release notes](docs/RELEASE_NOTES_0_8_1_BETA_2.md#publication-status). No beta.2 binary or tag is available yet. The published beta.1 binary predates the editor redesign; its controls differ from current main.

## Main capabilities

| Area | Implemented scope |
| --- | --- |
| Structure and geometry | CIF import, oriented reciprocal indexing, excitation errors, diffraction previews, projected zone-axis interaction, and virtual detectors. Elastic-preview eligibility is separate from MDFF eligibility. |
| Elastic scattering | Bundled Adaptive Dirac-Pade neutral-atom factors for Z=1-118; named Ni Lobato compatibility route for historical projects. Ordered, fully occupied multi-element crystals can support elastic diffraction. |
| Propagation | Bloch-wave and FFT Multislice, with Single or Double Channeling and matched BW/MS comparisons. |
| Inelastic response | XMCD-constrained MDFF, approximate Atomic Ionization MDFF, or Manual tensor construction, including a two-edge Lorentzian spectrum and advanced imported tensor exchange. |
| Inspection and projects | Source/tensor previews, reversal and even/odd views, stale-state warnings, completed-project save/reopen, Results Browser, and figure/CSV/NPZ exports. |

MDFF execution requires an eligible fully occupied single-element crystal with supported equivalent ionization sites. A CIF does not supply electronic transitions. Selecting a preparation element in a mixed crystal does not implement a multi-element MDFF sum.

## New MDFF configuration and parameter editor

Open **Model > Configure MDFF...** to use the same three choices for every crystal:

- **XMCD-constrained MDFF:** select one five-column XAS/XMCD source, validate it, and declare its element, edges, magnetic axis, convention, provenance, and relative scale as required. Preview displays the original input columns and the actual calculation-provider tensor. Ambiguous input requires explicit choices for both edge energies; default or inherited numbers do not qualify.
- **Atomic Ionization MDFF:** prepare a cubic, independent-electron Sc-Zn 2p-to-3d L2,3 model through an element-aware editor. Edit references, Gaussian width, magnetization/frame, crystal-field and exchange splitting, spin-resolved holes, and radial input. Generic electronic defaults are labeled synthetic, not inferred material properties. Elemental edge references do not predict chemical shifts.
- **Manual tensor:** edit nine complex entries of a constant Hermitian positive-semidefinite tensor, or construct an L2,3 spectrum from two independent integrated-strength tensors and Lorentzian profiles. Advanced source exchange retains imported tensor workflows. Invalid drafts are rejected without silently repairing matrices or executing old input.

Per-element drafts, parameter explanations, frame diagrams, component plots, and numerical previews make assumptions inspectable before calculation. A schematic is not a numerical spectrum; a tensor preview is not detector EELS. See [construction methods, inputs, defaults, units, and examples](docs/MDFF_WORKFLOWS.md).

## Installation to a first result

For a published binary, download the complete Windows ZIP and supplied checksum from its [version-specific release](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.8.1-beta.1), verify it, and extract the entire `EMCD-Sim` folder. Keep `_internal` beside `EMCD-Sim.exe`. Binary users need neither Python, Conda, WIEN2k, nor an existing project JSON. Use the documentation for that binary version.

For the new editor while beta.2 is unpublished, use the tested local development build or [install current main from source](docs/INSTALL_WINDOWS.md#source-installation). Then:

1. Choose **File > New** for the bundled Ni structure, or **Open CIF...** for a supported structure.
2. Set zone and target. Open **Configure MDFF...**, choose a model, and validate its inputs.
3. Use the small, explicitly coarse [Quick Start](docs/QUICK_START.md) profile.
4. Update the MDFF preview, run, and inspect EELS and selected-energy maps.
5. Use **File > Save Project** to create a completed project folder. Reopen the whole folder and select **Use These Settings** before rerunning.

The [installation guide](docs/INSTALL_WINDOWS.md) separates binary use from source/build setup, and explains extraction, platform status, source reconnection, and troubleshooting.

## Scientific methods and limits

Bloch-wave propagation diagonalizes a finite reciprocal-space elastic generator. FFT Multislice propagates through a sampled projected independent-atom potential. Single Channeling includes incoming elastic channeling; Double Channeling also includes depth-distributed inelastic transitions and outgoing propagation at reduced electron energy. It does not mean two inelastic events. The convention is `forward_born_dagger_g_minus_h_v1`, with intensity `Re Tr(RT)`.

XMCD supplies an axisymmetric effective response constrained by intensities, not full complex core-to-band DFT data. Atomic Ionization is cubic and independent-electron, not a full multiplet or band calculation. Manual tensors are phenomenological input, not automatically calibrated material responses. Relative intensities are not absolute electron counts or experimental signal-to-noise predictions.

There is no general multi-element/inequivalent-site MDFF, noncollinear magnetic texture, AFM/SDW material model, or certified quantitative Fe spectroscopy. Convergence requires separate basis, potential, FFT, depth/slice, and detector studies. BW/MS agreement does not eliminate shared approximations. [Planned work](docs/INDEX.md#experimental-and-planned-work) is separate from implemented functionality.

Windows is the tested packaged platform. The development EXE passed a real application-created Fe fixture project, application restart, and recalculation on the development host; independent clean-machine installation remains unverified. Linux/macOS packages are not supplied or certified. Recorded Linux interpreter-shutdown and macOS Qt-modal CI problems remain limitations.

**The validation history is not a clean full-suite pass:** `7730e38` completed with **1,191 passed, 1 failed, 54 skipped**. Repair `4f15a4d` passed **four focused cases** with the original failed assertion preserved. Development EXE `aaa69a1` passed native ambiguity, Fe 710/723 eV preview/calculation, normal saving, restart, reopen, and recalculation checks. A specific user exception permits this evidence for the proposed prerelease without another complete regression. The full run remains **FAILED**. See [scope, evidence, and publication status](docs/RELEASE_NOTES_0_8_1_BETA_2.md).

Earlier v0.6.1 binaries used a superseded magnetic-sign convention. Preserve original arrays/provenance and revalidate signed results; opening a project does not upgrade its physics. Historical [Ni Lobato examples](docs/images/ni017_flipm_recomputed/README.md) retain their original provider and are not relabeled as Adaptive calculations.

## Documentation and citation

| Document | Purpose |
| --- | --- |
| [Installation](docs/INSTALL_WINDOWS.md) / [Quick Start](docs/QUICK_START.md) | Setup and a small first calculation. |
| [MDFF workflows](docs/MDFF_WORKFLOWS.md) | Construction methods, parameter meanings, synthetic example, preview, and project creation. |
| [User manual](docs/USER_GUIDE.md) / [Tutorial](docs/TUTORIAL.md) | Controls, propagation, detectors, normalization, and interpretation. |
| [Atomic parameter reference](docs/ATOMIC_PARAMETER_EDITOR.md) / [Manual spectral model](docs/MANUAL_L23_TENSOR_MODEL.md) | Detailed definitions and implementation-era evidence. |
| [Physics](docs/PHYSICS.md) / [Units](docs/PHYSICAL_UNITS.md) / [Limitations](docs/USER_GUIDE.md#scientific-limitations-and-responsible-interpretation) | Equations, conventions, and responsible use. |
| [Draft beta.2 notes](docs/RELEASE_NOTES_0_8_1_BETA_2.md) / [Changelog](docs/CHANGELOG.md) / [Index](docs/INDEX.md) | Full feature update, compatibility, accurate validation history, and references. |

Cite the repository, exact release/commit, MDFF source, elastic provider, and numerical configuration. No software-paper DOI is claimed. Existing theory/normalization references are in [Physics: references and historical records](docs/PHYSICS.md#references-and-historical-records).

Application source is [MIT](LICENSE). Adaptive coefficients have separate [Apache-2.0 licensing](src/emcd_sim/data/adaptive_dirac_pade_2026/LICENSE), [NOTICE](src/emcd_sim/data/adaptive_dirac_pade_2026/NOTICE), and provenance. Edge-reference data and dependencies retain their own licenses. The [Qt distribution notes](packaging/assets/qt-licenses/README.txt) identify unresolved redistribution requirements for the development bundle; application licensing does not override dependency terms.
