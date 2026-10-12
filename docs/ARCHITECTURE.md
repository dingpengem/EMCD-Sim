# EMCD-Sim architecture and theory development plan

**Status:** design proposal, October 2026. This document describes intended interfaces and validation gates; it does **not** imply that the listed physics engines already exist. The implemented code remains a research-stage FCC Ni benchmark with a finite-beam elastic entrance solver, illustrative dipole MDFF, and approximate 2BC/3BC geometry.

## 1. Mission and non-negotiable principles

Build a **material-independent, reproducible, quantitative EMCD forward/inverse simulation platform**, first validated on FCC Ni L2,3 and then extended to voltage/electric-field-driven magnetism and nonuniform devices. Windows must be a first-class native platform alongside macOS and Linux/HPC.

1. **Separate material physics, electron propagation, experimental optics, and analysis.** A material or voltage provider must not contain microscope/detector logic.
2. **Separate approximations explicitly:** IAM versus self-consistent elastic potentials; dipole versus full-momentum MDFF; entrance-only versus double-channeling; equilibrium versus nonequilibrium bias.
3. **Keep the CPU scientific core portable.** Standard Python 3.11+, NumPy/SciPy, stable formats, and no required CUDA, Unix-only executables, DFT installation, compiled Fortran, WSL, or machine-specific paths.
4. **Provide optional accelerators and external solvers** behind stable adapters, not in the base package. Native Windows operation must work without a Linux toolchain.
5. **Track provenance and uncertainty** for every scientific result. Never label an illustrative line shape or heuristic voltage-to-moment law a quantitative DFT prediction.
6. **Stay independent of QCBED.** Share well-validated algorithms later via a standalone package if genuinely useful; do not import QCBED internals or reuse its Conda environment.
7. During small changes use focused tests and update Markdown docs; demand deeper reference and convergence checks when changing core physics.

## 2. Long-term physics and software pipeline

```text
Experiment / microscope / detector / specimen / device / applied bias
   |                                              |
   v                                              v
Optics & geometry                         MaterialStateProvider(V, B, T, time)
(incident probe, orientations,              charge, potential, atoms/strain,
apertures, aberrations)                     magnetic texture, chemical states
   |                                              |
   v                                     +--------+----------------+
ElasticPotentialProvider <---------------+                         |
   |                                     |                         v
   v                                     |              ElectronicStructureAdapter
Incoming + outgoing                      |              (all-electron DFT/SOC, core states,
propagation backends                      |               transition matrix elements)
(Bloch-wave, multislice)                  |                         |
   |                                     |                         v
   |                                     |                  MDFFSource(site, E, q, q')
   |                                     |                   dipole tensor or full-q
   +-------------------+-----------------+-------------------------+
                       v
              Inelastic forward solver
              (depth/site/beam interference, channeling,
               2BC/3BC/zone axis, physical sign conventions)
                       |
                       v
               Detector and EELS model
              (acceptance, energy resolution, exposure/noise)
                       |
                       v
               Results and inverse analysis
              (diffraction, EELS, EMCD maps, differences,
               sum-rule-aware analysis, fits, uncertainty)
```

**Key insight:** Bias does not directly multiply the EMCD spectrum in a predictive model. Bias changes the material state **and potentially the fast-electron optical trajectory**, which together change the measured signal.

## 3. Scientific data contracts (designed now; implemented incrementally)

| Domain object | Minimum fields | Required semantics |
|---|---|---|
| `CrystalStructure` | lattice, fractional sites, species, occupancies | Original crystal frame and orientation are explicit |
| `Specimen` | oriented geometry, regions/layers, thickness, site groups | Spatially resolved structures; not only a perfect bulk cell |
| `ExperimentGeometry` | acceleration kV, incident probe/tilt, orientation, detector geometry | Coordinate transforms and 2BC/3BC chirality convention explicit |
| `BiasCondition` | bias V, electrode boundary conditions, field mode, optional sweep/time | Acceleration voltage is separate from sample bias |
| `MaterialState` | atomic/strain state, electrostatic potential, magnetization vector, charge/valence, provenance | Spatial and optionally temporal dependence; state may be supplied by experiment, DFT, or transport |
| `TransitionDataset` | core-state identity/j, unoccupied-state energies, complex transition amplitudes, occupancy, k weights, site, broadening | Complex phases, SOC, axes, spin convention, units and data provenance preserved |
| `MDFFSource` | `evaluate(q, q_prime, E, site, state)` | Complex Hermitian kernel; backends: illustrative, dipole tensor, full momentum |
| `ElasticPropagator` | `propagate(state, geometry, energy, depths, direction)` | Incoming and outgoing boundary conditions; explicit normalization |
| `DetectorModel` | physical aperture(s), spectrometer response, acquisition/noise | Does not hard-code 2BC/3BC apertures into MDFF |
| `SimulationResult` | energies, reciprocal axes, spectra/maps, diffraction indices, units, approximation/provenance | Self-describing, machine-readable and reproducible |

Keep coordinates separate: crystallographic **g** is currently in cycles/Angstrom (no 2 pi), while dipole plane-wave exponents must use **Q = 2 pi g** in inverse Angstrom if writing exp(i Q·r). Document conversions at interfaces; do not silently mix momentum-transfer conventions. Explicitly distinguish a physical `MDFF` from the Coulomb denominators `1/(q² q'²)` multiplying it in the cross section.

Recommended base serialization: JSON metadata + NPZ arrays for no-extra-dependency compatibility; optional HDF5/Zarr for high-dimensional or HPC calculations. Record software/DFT versions, potential source, sample state, orientation, beam basis, units, broadening, detector definitions, approximation level and convergence settings. Avoid Python pickle for shared scientific datasets.

## 4. Theory engines and their boundaries

### 4.1 Elastic propagation

**Initial benchmark:** multi-beam Bloch-wave with a physical potential for FCC Ni. Validate against an independent solver and beam/thickness/tilt convergence before upgrading to quantitative interpretations.

**Backends:** (a) finite-basis Bloch-wave for perfect/periodic benchmarks; (b) multislice for convergent probes, spatial inhomogeneity and heterostructures; (c) optional accelerated solvers. Both should consume a defined elastic potential and produce compatible incoming/outgoing propagator outputs. Real IAM potentials and optional self-consistent potentials must be labeled differently. Explicitly model or bound absorption/TDS when required.

### 4.2 Electronic transitions and MDFF

`TransitionDataset` must be the physics boundary between an external electronic-structure calculation and the EMCD forward solver.

The first rigorous implementation should construct a **complex, energy-resolved, site-aware dipole tensor** from complex core-to-unoccupied-state transition amplitudes:

`T_ab(E) = sum_(i,f,k) w_k p_i (1-f_f) d*_(fi,a) d_(fi,b) L(E - (epsilon_f - epsilon_i))`.

In the angular-wavevector convention, `S_dip(Q,Q',E) = Q^T T(E) Q'` (conjugation/sign must match the chosen transition definition). Preserve Hermiticity and positive semidefiniteness. For a magnetic cubic material, `N(E),M(E)` can be *derived* from tensor symmetry under clear conventions; do not use a globally imposed scalar magnetic fraction for quantitative studies.

For arbitrary momentum transfers, later implement `<f|exp(i Q·r)|i>` directly. Preserve site positions and corresponding crystal phase factors, core-level 2p SOC, magnetization axes and optional inter-site coherence. Do not convert DOS alone into an MDFF. Investigate core-hole, multiplet and other beyond-DFT corrections where needed. DFT importers (e.g. Elk, WIEN2k, exciting) are optional and must be verified for actual wavefunction/transition-data export; no package should be presumed to output full MDFF automatically.

### 4.3 Double channeling and measured signals

Use the incoming wave at the inelastic event depth and the outgoing/back-propagated detector channel (including the post-loss electron energy), contracted with the *local* transition/MDFF kernel. Sum amplitudes/coherences with the correct site/depth phase conventions and detector integration. Treat elastic propagation, inelastic transition physics, and final instrument convolution as separate operators.

Test the two-beam limit, propagation reciprocity where applicable, nonnegative physical intensities, magnetic reversal and aperture handedness. The existing 2BC/3BC labels are finite-beam approximations, not proof of full experimental alignment.

### 4.4 Bias and magnetism: distinct mechanisms

A bare `Voltage -> moment scaling` remains a labeled sensitivity/demo provider only. Research-level providers depend on the *specific sample and circuit*:

- **Electrostatic gating (equilibrium or quasi-static):** electrostatic boundary conditions/screening -> interface charge and possibly structural changes -> self-consistent magnetic electronic structure and transition data.
- **Ferroelectric/ionic/electrochemical response:** polarization, atomic migration, valence, phase/strain and hysteresis -> changed sample geometry and electronic transitions.
- **Current-driven response:** spin accumulation, spin torque, Joule heating and temporal magnetic dynamics; equilibrium ground-state DFT alone is insufficient. Use optional transport/NEGF, spin-diffusion or magnetization-dynamics adapters as justified.
- **Direct electron-optical bias effects:** beam deflection/phase shift, charging, diffraction/tilt changes and EELS drift must be modeled or controlled separately from genuine magnetic changes.

For metals such as bulk Ni, electrostatic fields are strongly screened; do not assume a uniform internal field or uniform depth-dependent magnetic response. Future time-resolved calculations must keep elapsed/sweep time distinct from specimen thickness.

### 4.5 Analysis and quantitative claims

Return absolute cross sections/counts only when prefactors, transition data, illumination, acquisition time, detector efficiency and calibration warrant them; otherwise label arbitrary units. Support energy-resolved reciprocal maps, difference and normalized asymmetry, site/depth sensitivity, voltage loops and instrument-noise simulation.

EMCD magnetic sum rules require appropriate background and L-edge integration, channeling geometry and dynamical-diffraction weighting, plus consideration of effective spin and magnetic dipole terms. Ratios can be more accessible than absolute moments, but neither is automatically quantitative. Return uncertainty budgets and identifiability warnings.

## 5. Suggested source layout (future; not a request to restructure v0.3 today)

```text
src/emcd_sim/
  core/                   # units, frames, immutable model contracts, provenance
  materials/              # crystals, specimens, site groups, orientation
  electrostatics/         # device boundary conditions, screening, bias fields
  magnetism/              # state providers; optional equilibrium/dynamics adapters
  electronic/             # transition datasets and external DFT importers
  mdff/                   # illustrative, complex dipole tensors, full-q kernels
  elastic/                # potential providers, Bloch-wave, multislice, reciprocity
  inelastic/              # double-channeling and transition operator
  optics/                 # probes, diffraction conditions, detector/spectrometer
  analysis/               # maps, magnetic differences, sum rules, fits, uncertainty
  io/                     # NPZ/JSON, optional HDF5, structured configurations
  cli/                    # portable application entry point
tests/
  unit/                   # invariants, contracts, and sign/units
  reference/              # independent physics benchmark datasets
  integration/            # representative end-to-end workflows
  crossplatform/          # Windows/macOS/Linux smoke tests
examples/
  ni_bulk/                # reproducible FCC Ni starting point
  ni_interface_bias/      # clearly marked future research example
docs/
  ARCHITECTURE.md
  PHYSICS.md
  ROADMAP.md
```

Avoid restructuring the current flat package solely for aesthetics: migrate modules only when a real new physics backend or interface needs the separation. Keep the small, runnable FCC Ni CLI benchmark throughout.

## 6. Windows-first portability and acceleration strategy

**Portable core (mandatory):** CPython 3.11+, NumPy/SciPy, Matplotlib, explicit CPU implementations, `pathlib`, package-relative resources, OS-neutral `python -m emcd_sim`. Support Python wheels on Windows x64 and macOS/Linux; no dependence on WSL, POSIX shell scripts, GCC/Clang, conda executable locations, or specific shared libraries.

**DFT adapter layer (optional):** run an external solver where available (commonly Linux/HPC), export portable `TransitionDataset`/MDFF tensor files and load the same results on native Windows or Mac. Windows users must never need to build a DFT solver just to perform diffraction/EMCD forward runs.

**Accelerators (optional):** vectorized CPU first; then backend interfaces for CuPy/JAX/PyTorch or compiled numerical kernels only if benchmarks justify them. Check identical physics/sign conventions across backends with tolerances. No platform-specific code in the MDFF mathematical definitions.

**Automation:** maintain a GitHub Actions Windows/macOS/Linux matrix for installation, small CLI examples and contract tests; run independent/convergence physics benchmarks separately at milestones. A green Windows CI test proves packaging/portability of the tested subset, not quantitative EMCD.

**User interface:** stable Python API + CLI/configuration first, optional standalone Windows executable and GUI only once data schemas and scientific workflows stabilize. Do not couple physics modules to VS Code, a GUI or Codex.

## 7. Development milestones with acceptance gates

| Phase | Primary deliverable | Acceptance gate |
|---|---|---|
| P0 — Geometry and definitions | Freeze coordinate frames, sign conventions, sample/electron voltages and benchmark metadata | 2BC/3BC detector symmetry, index/frame/unit and magnetization reversal tests; independent elastic reference |
| P1 — Complex MDFF tensor | Generic site-aware dipole tensor and imported complex transition amplitudes; keep Gaussian model labeled illustrative | Hermiticity, PSD, correct limits, magnetic reversal, benchmark atomic transitions |
| P2 — Double channeling | Incoming + outgoing Bloch-wave solver; optional multislice adapter later | Reference two-beam limits, detector reciprocity and beam/thickness/depth/angle convergence |
| P3 — DFT Ni L2,3 | First validated Ni 2p core -> unoccupied band transitions with SOC and calibrated spectral treatment | k/band/broadening convergence; compare nonmag and magnetic edge shape; robust magnetic sum-rule interpretation |
| P4 — Quantitative baseline | Detector/instrument response, reference Ni data, uncertainty, inverse analysis | Controlled measured-versus-simulated thickness/tilt/aperture benchmarks with error budgets |
| P5 — Bias-dependent states | Site/layer-resolved electric-field, electronic and magnetic state providers for a **specified device** | Show predicted effects survive charge/structure/beam-deflection confounds; hysteresis/time path when relevant |
| P6 — Scaling and distribution | Full/efficient MDFF, device heterogeneity, optimized CPU/optional GPU, Windows delivery | Same scientific benchmarks on Windows/macOS/Linux; reproducible files and release artifacts |

P1 and P2 can progress in parallel if they share the contract from P0. DFT is **not** a prerequisite for developing/testing double channeling with synthetic positive-semidefinite tensors. Conversely, implementing a high-fidelity tensor does not by itself establish a quantitative EMCD forward signal.

## 8. Immediate next decisions

1. **Freeze P0 interfaces and coordinate/sign conventions** without changing the numerical solver.
2. Implement P1 with a hand-checked atomic reference transition dataset before choosing or integrating a DFT package.
3. Develop P2 against the same `MDFFSource` contract, keeping 2BC, 3BC and 2D ZOLZ comparisons.
4. Define the first **real bias-device geometry** before making a predictive `VoltageDependentMaterialStateProvider`: gating, ferroelectric polarization, or current-driven transport require different physics.
5. Keep the portable Windows CPU path runnable through every phase.

**Scientific rule:** measured EMCD asymmetry, fit moments or voltage-induced magnetic changes must not be presented as ab initio predictions until each required theory, geometry, instrument and validation gate is satisfied.
