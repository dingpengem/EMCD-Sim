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
