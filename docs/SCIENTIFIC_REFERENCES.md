# Scientific References and Theoretical Foundations

[Home](../README.md) · [Software citation](CITATION.md) · [Physics](PHYSICS.md) · [Elastic factors](ELASTIC_ATOMIC_FACTORS.md)

## Overview

EMCD-Sim integrates established electron-scattering theory, finite numerical solvers and declared material-response inputs. Bloch waves, multislice, mixed dynamic form factors (MDFF), EMCD and atomic scattering parameterizations are not new theories invented by this software. Its software contributions include site/provider bookkeeping, explicit reversal and normalization, shared BW/MS orchestration, resource admission, visualization and persistence. Their correctness requires implementation-specific evidence; citing a foundation is not validation.

Bibliographic metadata below were checked on 11 November 2026 against publisher-registered Crossref records, author/institutional records and the linked primary sources. The 2026 manuscript is a **preprint**, not an established journal publication. DOI capitalization does not change identity. The historical [convention map](PHYSICS_CONVENTIONS_AND_SOURCE_MAP.md) and [correction acceptance](PHYSICS_CORRECTION_ACCEPTANCE.md) retain their dated source identities; their old line numbers and pre-correction statements must not be read as current code.

## EMCD and MDFF

**[1] Ján Rusz, Stefano Rubino and Peter Schattschneider (2007).** “First-principles theory of chiral dichroism in electron microscopy applied to 3d ferromagnets.” *Physical Review B* **75**(21), 214425. [DOI: 10.1103/PhysRevB.75.214425](https://doi.org/10.1103/PhysRevB.75.214425); [author manuscript](https://arxiv.org/abs/0704.1407).

**Role: direct theoretical foundation / method reference.** Bloch-wave dynamical diffraction, transfer-pair MDFF, independent ionization sites and thickness/exit-wave factors inform the EMCD formulation. Relevant modules: `physical_elastic.py`, `single_channeling_tensor.py`, `double_channeling.py`, `ionization_sites.py` and multi-site wrappers. EMCD-Sim uses finite ZOLZ, frozen longitudinal transfer and effective/synthetic or imported tensors; it does not reproduce the paper's ab-initio Fe/Co/Ni electronic-structure calculations. A PRB-style difference/sum display is not reproduction of its figures or conditions.

**[2] Devendra Singh Negi, Juan Carlos Idrobo and Ján Rusz (2018).** “Probing the localization of magnetic dichroism by atomic-size astigmatic and vortex electron beams.” *Scientific Reports* **8**, 4019. [DOI: 10.1038/s41598-018-22234-8](https://doi.org/10.1038/s41598-018-22234-8).

**Role: consulted theoretical reference / alternative numerical method.** The target-excitation operator, MDFF and magnetic transfer-pair structure inform the convention discussion. The paper's combined multislice/Bloch treatment and shaped probes are not identical to EMCD-Sim's independent BW/MS implementations or plane-wave diagnostic illumination. Relevant modules: `mdff_tensor.py`, `single_channeling_tensor.py`, `multislice_double_channeling.py`. The existing literature audit inspected its Methods equations; this release metadata review does not claim a new equation-by-equation validation.

**[3] Peter Schattschneider, Stefano Rubino, Christian Hébert, Ján Rusz, Ján Kuneš, Pavel Novák, E. Carlino, M. Fabrizioli, G. Panaccione and G. Rossi (2006).** “Detection of magnetic circular dichroism using a transmission electron microscope.” *Nature* **441**, 486–488. [DOI: 10.1038/nature04778](https://doi.org/10.1038/nature04778).

**Role: experimental foundation / consulted background.** Establishes the EMCD experimental context, not a numerical reference array for this program. Detector A/B geometry and EMCD interpretation in `geometry.py` and GUI Results relate to that context; no quantitative reproduction of the experiment or magnetic moments is claimed.

## Bloch-wave scattering; Single and Double Channeling

Reference [1] supplies the relevant published Bloch/MDFF context. `physical_elastic.py` evolves finite Hermitian IAM eigenmodes. `single_channeling_tensor.py` contracts incoming coherence with the Cartesian tensor, while `double_channeling.py` also prepares detector-dependent outgoing propagation at **E_out = E_incident − E_loss**. Single and Double are different physical approximations, not spectra expected to coincide.

Independent localized events add **intensities**, not complex event amplitudes. `multisite_single_channeling.py` and `multisite_double_channeling.py` reuse propagation, apply actual selected-site phases and explicit physical reversal pairs, and weight group means once by validated multiplicity. The fixed denominator counts selected ionizing atoms, including across modeled energy-window exclusions. None of these software bookkeeping choices implies crystallographic equivalence is magnetic/spectroscopic equivalence.

The current convention uses crystallographic `g=1/d`, Fourier phase `exp(−2πi g·r)`, angular transfer `Q=2πq`, and the established forward-excitation contraction. The response/transition-mode conjugation is documented in [correction acceptance](PHYSICS_CORRECTION_ACCEPTANCE.md); matching the symbol “MDFF” in a paper alone does not establish conjugation order. Historical pre-correction conventions remain archived, not endorsed as the current algorithm.

## Multislice propagation

**[4] J. M. Cowley and A. F. Moodie (1957).** “The scattering of electrons by atoms and crystals. I. A new theoretical approach.” *Acta Crystallographica* **10**(10), 609–619. [DOI: 10.1107/S0365110X57002194](https://doi.org/10.1107/S0365110X57002194).

**Role: numerical-method foundation / background.** Foundational multislice treatment. EMCD-Sim's `multislice_reference.py`, `projected_geometry.py`, `projected_potential.py` and `multislice_double_channeling.py` use a symmetric FFT kinetic-half/potential/kinetic-half split step in an actual projected reciprocal cell. No claim is made that the 1957 implementation used this program's exact FFT discretization or modern site-resolved contraction.

**[5] Christian Dwyer (2005).** “Multislice theory of fast electron scattering incorporating atomic inner-shell ionization.” *Ultramicroscopy* **104**(2), 141–151. [DOI: 10.1016/j.ultramic.2005.03.005](https://doi.org/10.1016/j.ultramic.2005.03.005); [author-affiliated publication record](https://research.monash.edu/en/publications/multislice-theory-of-fast-electron-scattering-incorporating-atomi/).

**Role: consulted inelastic-multislice reference.** Relevant to coherent elastic propagation before/after localized inner-shell excitation (`multislice_double_channeling.py`). Bibliography and abstract were accessible; full-text equation/operator comparison remains **unverified**. No equation numbers, exact derivation or quantitative equivalence to Dwyer's implementation are asserted.

The [generalized MS architecture](GENERALIZED_MULTISLICE_ARCHITECTURE.md) describes the actual structure-derived oblique FFT cell, IAM Fourier potential, incoming fields and outgoing adjoint propagation. The current finite ZOLZ/continuous-depth localized-event approximation is not a full atomic-z transition-potential calculation. FFT, slice and depth convergence remain case-dependent.

## Elastic scattering factors and third-party data

**[6] Ivan Lobato and Dirk Van Dyck (2014).** “An accurate parameterization for scattering factors, electron densities and electrostatic potentials for neutral atoms that obey all physical constraints.” *Acta Crystallographica Section A: Foundations and Advances* **70**(6), 636–649. [DOI: 10.1107/S205327331401643X](https://doi.org/10.1107/S205327331401643X); [author-hosted paper](https://nano.uantwerpen.be/nanorefs/pdfs/OA_10.1107_S205327331401643X.pdf).

**Role: historical elastic-provider method/data reference.** `scattering.py` retains the Ni Lobato parameterization and old-project compatibility. The current GUI/factory default is [7], not a silently altered historical Ni fit. Neutral IAM omits bonding/charge redistribution and other specimen-specific corrections. Historical extinction-distance values in [physical elastic notes](PHYSICAL_ELASTIC.md) are model outputs, not experimentally validated Ni constants.

**[7] Ivan Lobato, Zezhong Zhang, Sandra Van Aert and Angus I. Kirkland (2026).** “Updated all-electron Dirac–Fock densities and an element-adaptive parameterisation of scattering factors and potentials for neutral atoms.” **arXiv:2608.14934v1**, submitted 14 August 2026; manuscript submitted to *Acta Crystallographica Section A*. [Persistent preprint](https://arxiv.org/abs/2608.14934v1); [DOI: 10.48550/arXiv.2608.14934](https://doi.org/10.48550/arXiv.2608.14934). Journal acceptance is not established.

**Role: current elastic-factor method reference.** `adaptive_scattering.py` evaluates neutral Z=1–118 Adaptive Dirac–Padé coefficients. It does not run `atomx`, regenerate relativistic densities or refit the published coefficients. This manuscript's atomic accuracy does not validate a finite-basis crystal calculation or supply an MDFF.

**[8] Ivan Lobato / NeuralSoftX (2026).** *adaptive_dirac_pade_scattering_factor_2026*, coefficient/software deposit, exact revision **1667babb2c5bdb44a0535438b846eb1bbfbc03ac**. [Pinned source and README](https://github.com/NeuralSoftX/adaptive_dirac_pade_scattering_factor_2026/tree/1667babb2c5bdb44a0535438b846eb1bbfbc03ac). **Apache-2.0**, separate from EMCD-Sim's MIT license.

**Role: third-party data source.** `src/emcd_sim/data/adaptive_dirac_pade_2026/` retains coefficients, LICENSE, NOTICE and provenance. Existing extraction preserves float32 coefficient values as exact binary64 JSON values, without interpolation/refitting. Only the deposited adaptive model is bundled; the code uses crystallographic inverse-Å inputs and electron amplitudes in Å without a second potential conversion or relativistic factor. The upstream preprint acknowledges its unpublished `atomx` reference-density source; no fabricated separate publication is cited. [Elastic-factor documentation](ELASTIC_ATOMIC_FACTORS.md) records exact data identities, extraction and the distinct external legacy provider.

## XMCD and atomic models

References [1–3] provide EMCD/MDFF and magnetic-response context, not a claim that XMCD uniquely determines a full anisotropic MDFF. `generalized_xmcd.py` constructs an **effective axisymmetric** response with shared XAS and declared reversal-odd XMCD, explicit RP/LP convention, source axis, scale and energy assignments. Its declared native source features are not generic tabulated edge positions. No new DFT calculation or automatically calibrated magnetic moment is produced.

`atomic_dipole.py`, `atomic_ionization.py` and `mdff_tensor.py` implement explicitly parameterized independent-electron 2p→3d dipole transitions: core spinors, cubic orbitals, radial input, spin-resolved holes, exchange/crystal-field shifts and broadening. They retain coherent orbital components and sum independent transitions incoherently. This is not a full multiplet, many-body or material-specific DFT solver; its synthetic/physical-source-unvalidated labels are scientifically necessary. No unverified atomic-theory paper is invented as a direct derivation.

The full `frame_to_crystal` is independent of the declared magnetic direction. `mdff_providers.py` and `imported_mdff.py` validate source identity, Hermiticity/PSD, frames and explicit reversal assumptions. Physical ±M pairs are contracted before forming even/odd intensities; real parts are not automatically “nonmagnetic,” nor imaginary parts automatically “magnetic.” General arbitrary tensor rotation is not implemented. User/imported spectroscopy data must be cited separately with their actual provenance; a file named `Ni_fm.xmcd` alone is not proof of calibrated bulk-Ni DFT accuracy.

## Structure and numerical software

**[9] Ask Hjorth Larsen and coauthors (2017).** “The atomic simulation environment—a Python library for working with atoms.” *Journal of Physics: Condensed Matter* **29**(27), 273002. [DOI: 10.1088/1361-648X/aa680e](https://doi.org/10.1088/1361-648X/aa680e); [author manuscript/complete author record](https://backend.orbit.dtu.dk/ws/files/130802447/main.pdf).

**Role: implemented third-party structure library.** ASE supplies CIF parsing/Atoms consumed by the ASE CIF importer and `gui/structure_scene.py`. Its availability does not make partially occupied/disordered structures executable in the ordered-site MDFF model. Original indices are preserved; visualization is separate from calculation eligibility.

**[10] Atsushi Togo, Kohei Shinohara and Isao Tanaka (2024).** “Spglib: a software library for crystal symmetry search.” *Science and Technology of Advanced Materials: Methods* **4**(1), 2384822. [DOI: 10.1080/27660400.2024.2384822](https://doi.org/10.1080/27660400.2024.2384822); [official reference](https://spglib.readthedocs.io/en/stable/).

**Role: implemented crystallographic grouping library.** `crystallographic_sites.py` uses structural symmetry/orbit/Wyckoff information as suggestions. This does not infer magnetic order, spectroscopy equivalence, oxidation states or MDFF. The magnetic-space-group algorithm mentioned in spglib's documentation is not a claim that EMCD-Sim implements magCIF.

NumPy/SciPy linear algebra/FFT and Matplotlib/Qt plotting are implementation dependencies, not new physical theories. The code uses finite Hermitian eigensystems, symmetric FFT stepping, trapezoidal depth quadrature and fractional-aperture integration. [Source conventions](PHYSICS_CONVENTIONS_AND_SOURCE_MAP.md), [generalized architecture](GENERALIZED_MULTISLICE_ARCHITECTURE.md) and [full-spectrum notes](DOUBLE_CHANNELING_FULL_SPECTRA.md) document these choices; no unrelated numerical bibliography is added merely to enlarge the list.

## Verification and citation boundaries

Algebraic checks, within-platform worker equality, selected matched BW/MS comparisons, native workflow acceptance and direct Windows/macOS BW Single arrays are distinct evidence. Direct Mac BW Double/MS Single/MS Double raw-array comparisons remain **INCOMPLETE**. General convergence, experimental calibration, absolute cross sections and quantitative magnetic moments remain unestablished. Historical references retain their original inputs and conventions.

These ten records cover scientific foundations, method/background context and actual third-party structure/data sources. They do not replace the [EMCD-Sim software citation](CITATION.md), and citing the software does not replace the relevant original literature and material-specific data citations.
