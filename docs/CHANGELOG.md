# v0.6.0-beta.1 - Double-Channeling EMCD Simulation

Windows research prerelease; application/package version **0.6.0**.
See [acceptance and provenance](WINDOWS_V060_BETA_ACCEPTANCE.md).
Double Channeling already shipped in 0.4.5-beta.1. This milestone consolidates
its incoming/depth-integrated/outgoing BW and FFT framework and full-energy
EELS/EMCD interpretation within the existing model and convergence limits.

- Unified primary Raw (a.u.) / EMCD Asymmetry (%) controls for spectra and maps.
- Preserved signed raw magnetic/nonmagnetic differences; total asymmetry is
  the unchanged +M difference/sum, not a magnetic-only quantity.
- Retained magnetic-only/even common-denominator components and other legacy
  diagnostics in Advanced Diagnostics; explicit saved Relative migration.
- Added descriptive CSV/NPZ sidecars while preserving original project arrays,
  PRB fields, provenance and original numerical definitions.
- Added a fresh Windows x64 standalone build with source/frozen acceptance,
  manifest, checksums and original-array comparison.
- Focused hand-reference, GUI, geometry, export and compatibility validation:
  see [validation report](EMCD_V060_VALIDATION.md).
- Physical solvers, MDFF, apertures, precision, memory and cancellation unchanged.
  Published 0.4.5-beta.1 remains intact. No global convergence or calibrated
  intensity/SNR claim is added.

---

# v0.4.5-beta.1 - Windows research Beta

Package version remains `0.4.5`; this is a GitHub Pre-release, not a stable release.
See [release notes and exact binary provenance](RELEASE_0_4_5_BETA.md).

- Added genuine BW and independent FFT Double Channeling with post-loss outgoing propagation and depth-distributed ionization.
- Added full-energy Ni L3/L2 EELS/EMCD, preserved four raw A/B reversal spectra, signed magnetic/nonmagnetic Raw and Relative displays, and separate PRB dichroism.
- Clarified crystallographic g=1/d beam/potential cutoffs, zone-axis versus tilt, physical detectors and restricted-row versus full finite ZOLZ geometry.
- Preserved checksummed projects, Results Browser and PNG/SVG/CSV/NPZ export, including raw/percentage data and saved display state.
- Added configurable 512/1024/2048/4096/8192 MiB process-memory budgets and cooperative cancellation through BW/MS kernels; Both stops before the second solver starts.
- Reused the accepted cancellation-fixed Windows ZIP without rebuilding. Main/tag documentation can be newer than its explicit build-source commit.
- Validation and limitations: earlier 115-test acceptance and 42 focused cancellation tests are separate, overlapping inventories. Native Windows 150% testing passed; independent clean-machine testing remains NOT TESTED. Approximate XMCD MDFF, projected potentials, frozen longitudinal transfer, uncalibrated counts/native energies and representative convergence scope remain.

---

## Historical post-v0.4.5 research record

The sections below retain the original milestone assumptions and numerical results.

# Unreleased research main — Ni [017] high-mistilt XY and native WIEN2k edge audit (post-v0.4.5)

**This records research work already merged into `main`; no new version tag, package-version bump, or experimental/quantitative accuracy claim is implied.** The package metadata is still `0.4.5`.

- Added real oriented projected FCC Ni **[710]** and **[017]** crystal geometries with genuine cubic hkl, matched physical Bloch-wave / FFT-multislice elastic potentials, indexed diffraction, and explicit ZA markers and Thales-circle apertures. Target **(200)** for [017]; `s200=0` defines the reference but the internal wavefield is not an isolated two-beam state.
- Added [017] cubic-[001]-magnetization **tensor rotation** (`T_local=R T_crystal R^T`) and native WIEN2k source-energy feature assignment. Native XAS maxima are **831.421/848.752 eV** (L3/L2); selected signed magnetic extrema are **831.271/848.698 eV**. The archived SOC core splitting ≈**17.48 eV** supports the relative assignment. The ~+21.25 eV discrepancy between native XAS maxima and older nominal 852.7/870 eV references **does not establish experimental absolute energy calibration**. Source spectrum is unchanged and unshifted.
- Completed **43 distinct X/Y mistilt orientations** around exact paraxial (200) Bragg with independently preserved native full BW/MS A/B EELS, plus/minus magnetization states, parity-odd/even contrast, raw and post-edge-corrected differences, selected L3/L2 angular maps, indexed diffraction and plot-only regeneration. Definitions: `theta_x=-7.11672544+delta_x`, `theta_y=delta_y` (mrad) in local [017] coordinates. Generated numerical/figure outputs remain local under `outputs/ni_017_high_mistilt_xy/` and are not necessarily Git tracked.
- Selected low-cutoff candidates: **(delta_x,delta_y)=(-6,0)** maximizes sampled absolute magnetic detector differences; **(0,-25)** maximizes sampled absolute magnetic asymmetry and relative ideal-counting proxy. Intrinsic even A–B follows the predicted Y-reflection relation in the present model; at nonzero Y, post-edge scaling often improves recovery but introduces an artificial even residual on the Y=0 symmetry plane.
- **Critical limitation:** physically changing Fourier potential cutoff 2.2→3.2 cycles/Å changes the exact-Bragg selected magnetic signal by about **21.8%** and reverses ranking of two absolute-signal candidate orientations. BW/FFT matched-model agreement (maximum magnetic-map relative discrepancy about **0.6025%** in the 43-case production survey) is *not* physical potential convergence. No full 3D ionization/outgoing channeling, complete DFT MDFF, experimental energy/dose calibration or validated quantitative Ni EMCD is provided.
- Added [Ni [017] case-study explanation and figure guide](NI_017_CASE_STUDY_GUIDE.md): separates computed spectral features from experimental absolute edge energies; explains why [017] and (200) were selected; documents all X/Y tilt conventions and special conditions; identifies exactly which saved plots show magnetic, even, raw/corrected and convergence effects. The guide also points to [high-mistilt technical data](NI_017_HIGH_MISTILT_XY.md) and [oriented [017] baseline](NI_017_MINORZONE.md).
- The recorded high-mistilt milestone passed **20 focused tests**, including magnetic parity, selected map/EELS integral reconstruction and byte-identical prior-output preservation. The documentation-only updates here do not alter the numerical engine or rerun the forward simulations.

---

# v0.4.4 — Metallic Ni transition-data provenance gate

- Audited public Ni L2/L3 datasets and distinguished phase-correct FCC Ni **complex transitions** from EELS/XAS/XMCD intensity datasets and NiO models. No suitable publicly downloadable complex FCC-Ni transition table was verified; no automatic physics replacement was performed.
- Added `ni_data_audit.py` to check NPZ dipoles, L2/L3 labels, core-SOC/spin/phase declarations, phase-specific source metadata and algebraic tensor consistency. Audit pass is **not** scientific validation.
- Added optional `--mdff-model ni-metal-external --mdff-provenance path.json`; it refuses missing/mismatched inputs and continues to report relative/nonquantitative units.
- Preserved all prior EMCD modes and Windows/macOS/Linux compatibility.

# v0.4.3 — Complex MDFF in entrance-only Ni EMCD

- Added a transition-derived complex tensor backend to the physical Bloch-wave single-channeling forward calculation, preserving the legacy Gaussian model as a selectable default.
- Coupled coherent incoming beam amplitudes to localized FCC Ni core-loss site phases; kept the **proper** dipole MDFF separate from fast-electron Coulomb denominators, with explicit cycles-to-angular-Q conversion.
- Added `--mdff-model {gaussian,ni-local,transitions}` and portable complex transition NPZ support; disabled unsupported tensor voltage-to-moment scaling.
- Added matched L₂/L₃ reciprocal component figures and data, source/approximation metadata and focused positive-intensity, phase, and chirality-reversal tests.
- No claim of Ni-specific quantitative MDFF, absolute cross sections, DFT, voltage response or double channeling.

# v0.4.2 — Non-DFT local atomic MDFF option (P2)

- Added independently written Ni core-SOC + cubic-orbital local dipole transitions with analytic normalized screened-hydrogenic 2p/3d radial integral.
- Added optional imported radial wavefunction CSV and normalized numerical radial dipole integral for external atomic Hartree-Fock data.
- Preserved complex amplitudes and transition-derived tensor; added cubic basis, radial quadrature, chirality and cross-platform CLI checks.
- Documented atomic multiplet/Quanty route and explicit non-DFT versus quantitative limitations. Existing Gaussian-MDFF `emcd-ni` is unchanged.

# v0.4.1 — Ni 2p core-SOC angular reference and portable transition data bridge

- Computed 2p3/2 and 2p1/2 core angular spinors and 2p->3d complex Cartesian
  dipole amplitudes using Clebsch-Gordan coefficients and spin selection.
- Illustrative Ni 3d spin-hole weights, L3/L2 onset energies and radial dipole
  integral remain explicitly user-specified. **Not** DFT or calibrated Ni MDFF.
- Added strict external complex dipole CSV -> TransitionDataset NPZ converter
  (with explicit input bra convention), platform-neutral command line and tests.
- Preserved legacy Gaussian EMCD CLI unchanged. Double channeling deferred.

# v0.4.0 — P2 complex MDFF tensor foundation

- Added `TransitionDataset` for externally supplied complex dipole matrix elements, energy losses, site/edge labels and transition weights. Portable NPZ with strict explicit conventions and provenance.
- Added spectrally broadened Hermitian dipole tensor `T_ab(E)` and full complex `S_dip(Q,Q',E)` contraction, separate from Coulomb factors.
- Added `emcd-mdff` / `python -m emcd_sim.mdff_reference` synthetic-only demonstration and basic physics tests.
- No real Ni DFT/SOC transitions provided; no claim of quantitative Ni EMCD and no changes to existing Gaussian EMCD results.

# v0.3.6 — Independent elastic Fourier multislice reference (P1)

- Added pure NumPy projected FCC Ni [001] periodic FFT split-step elastic propagation, independent of finite-beam eigendecomposition.
- Added matched Fourier-truncated IAM potentials for Bloch/FFT propagation, and cross-method comparisons under zone-axis and illustrative 3BC geometry, multiple cutoffs and thicknesses.
- Exported elastic intensity, full distribution total-variation discrepancy, source parameters and PNG/CSV/JSON reference; no EMCD or outgoing-wave changes.
- Added convergence-sensitive tests for Fourier potential normalization, unitary propagation, tilt response, matched Bloch/FFT diffraction and Windows-safe CLI.
- Documented residual physical potential/basis cutoff sensitivity and limitation of the 2D z-independent projected reference. No quantitative Ni EMCD claim.

# v0.3.5 — Entrance Bloch-wave 2D basis convergence diagnostic

- Added `python -m emcd_sim.convergence` / `emcd-convergence` to compare growing FCC Ni 2D ZOLZ bases under fixed 2BC/3BC/zone-axis incident geometry.
- Compare elastic 000/±200 intensities, norm, full beam-distribution total variation against largest *finite* basis, and illustrative L3 EMCD difference/asymmetry.
- Export CSV, NPZ, metadata and labeled PNG; shared detector and tilt within each condition, platform-neutral paths.
- No modifications to elastic Hamiltonian, scattering factors or Gaussian MDFF. **No convergence certificate or quantitative EMCD claim**.
- Added focused validations for reference alignment, normalization, CLI output and path portability.

# v0.3.4 — EMCD reciprocal maps by diffraction condition

- Added portable `emcd-compare` / `python -m emcd_sim.compare_conditions` to generate a side-by-side FCC Ni L3 reciprocal-map comparison for 2BC, near-2BC, symmetric-3BC and zone-axis.
- Shared q axes and color limits across conditions; indexed diffracted beams, condition-specific apertures/tilts, illustrative local magnetic/nonmagnetic ratio, integrated A−B metadata and machine-readable NPZ.
- Reproducible example and deliberately non-quantitative provenance; no changes to Bloch-wave or MDFF physics.

# v0.3.3 — Tilt and thickness EMCD diagnostic

- Added `python -m emcd_sim.scan` / `emcd-scan`: 3D tilt-x × tilt-y × thickness scans at Ni L3 using existing entrance-only illustrative MDFF.
- CSV and NPZ numerical results, fixed color scales for comparison heatmaps and magnetic/nonmagnetic reciprocal maps.
- Explicitly demonstrate that systematic-row Y tilt insensitivity is a basis truncation artifact, while finite 2D ZOLZ can vary with Y tilt.
- Portable Windows/macOS/Linux CLI, focused symmetry/data-shape regression tests; no changes to existing Bloch-wave, MDFF or EELS equations.

# v0.3.2 — Windows/macOS/Linux portability

- Added an OS-neutral entry point: `python -m emcd_sim`.
- Added PowerShell/Conda/VS Code setup instructions for Windows and portable commands for macOS/Linux.
- Added GitHub Actions Python 3.11 test matrix for Windows, macOS and Linux and a CLI smoke test.
- Added regression coverage for paths with spaces and version consistency.
- No changes to electron diffraction physics or MDFF; quantitative limitations remain unchanged.

# v0.3.1 — Chiral aperture geometry fix

- Corrected 000-centered transverse momentum coordinate for tilted 2BC/3BC EMCD maps (removed erroneous extra incident-tilt subtraction).
- Exact transverse Thales-circle detector centers for 2BC/near-2BC; four physical 3BC apertures and symmetry-correct double difference.
- Added detector overlays and standalone `aperture_geometry.png`, per-aperture spectra, group metadata and focused regression tests.
- Still illustrative: truncated systematic rows, simplified MDFF, no outgoing channeling or SNR optimization.

# Changelog

## 0.2.0 — Ni physical elastic Bloch-wave solver

- Added a neutral-Ni (Z=28) Lobato–Van Dyck 2014 elastic electron scattering-factor implementation.
- Added general independent-atom periodic crystal Fourier factors with optional per-site Debye–Waller B and occupancy, and a physical Fourier-potential adapter.
- Added finite-basis relativistic Bloch-wave elastic propagation with derived beam couplings and ξ200 (no fitted extinction distance in this backend).
- Added systematic-row and Friedel-paired in-plane ZOLZ beam generation; seven-beam Ni systematic row is the default physical reference.
- Switched `emcd-ni` CLI default to `--elastic-backend physical`. Original `--elastic-backend surrogate` is retained for comparison, with `--xi-nm` applying only to the surrogate.
- Added plots and NPZ for each elastic beam's thickness-dependent intensity and a row-order convergence diagnostic.
- Added five physical tests (12 tests total) for form factor, FCC extinctions, DW, Hermiticity/unitarity, ξ200 and exact two-beam Bragg Pendellösung.
- Documented units, modeling assumptions, citations, and remaining outgoing-channeling/MDFF limitations.

This version **does not** validate quantitative EMCD: magnetic L-edge MDFF remains illustrative and the electron does not undergo outgoing channeling after its core-loss event.

## 0.1.0 — Initial proof of concept

- Phenomenological entrance-channeling elastic coupling; illustrative magnetic core-loss MDFF; Ni 3-beam virtual-aperture workflow; bias-to-moment data interface.

## 0.3.0 — Indexed diffraction geometry and patterns

- Added `--diffraction-condition {systematic-row,zone-axis,two-beam,near-2bc,symmetric-3bc}`.
- Added `--diffraction-only` for elastic diffraction without costly illustrative MDFF/EELS integration.
- Added reproducible indexed reciprocal-space diffraction PNG, NPZ and CSV with `(h,k,l)`, nominal `[001]` zone axis, tilt and signed excitation errors.
- Preserved the v0.2 default systematic row, physical Ni elastic solver and existing EELS API.
- The 2BC/3BC presets explicitly state their finite-basis/systematic-row assumptions; diffraction spot broadening is graphical only.
- Added focused tests of s_g, Bragg condition, ±200 symmetry, ZOLZ indexing and elastic conservation.
