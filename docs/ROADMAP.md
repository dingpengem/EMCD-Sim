# Magnetic EMCD project roadmap

EMCD-Sim is independent of QCBED (separate code, Git history and `emcd-python` environment) and must remain native on Windows, macOS and Linux.

## Scope and quantitative terminology

**Immediate physics priority: make single-channeling EMCD quantitatively correct and validated first.** Outgoing/double channeling is the **next** major solver step, but should not disrupt incoming-wave and MDFF validation.

"Quantitative single channeling" means real atomic/DFT transition matrix elements, correctly normalized incident channeling and finite-aperture cross sections, tested physical symmetries, independent benchmarks and declared numerical convergence. It **does not** imply fully quantitative measured EMCD, because post-inelastic dynamical scattering is omitted. See [detailed acceptance plan](SINGLE_CHANNELING_QUANTITATIVE.md) and [architecture](ARCHITECTURE.md).

## Implemented baseline (v0.3.x; demonstrator, NOT quantitative EMCD)

- FCC Ni [001] lattice and neutral-atom physical elastic potential; finite-beam Bloch-wave incoming propagation.
- Selected 2BC, near-2BC, symmetric-3BC and 2D ZOLZ settings with indexed elastic diffraction images. Current 2BC/3BC presets are finite-beam approximations.
- Thales-paired/4-quadrant apertures, reciprocal-space maps, L2/L3 detector EELS and chiral differences.
- **Illustrative** Gaussian `N(E)`, `M(E)` (magnetic fraction arbitrarily set to 0.12), not DFT-based Ni MDFF.
- Reproducible outputs, focused tests, platform-neutral `python -m emcd_sim` and Windows/macOS/Linux CI checks.

## P0 — Geometry / physical definitions

- Freeze 000-centered reciprocal maps, [uvw]/(hkl), specimen orientation, electron angular versus cycles/Angstrom wavevector, diffraction excitation error and magnetic sign conventions.
- Verify 2BC and 3BC Thales/double-difference apertures including systematic-row truncation limitations.
- Separate pure MDFF from fast-electron Coulomb denominators, cross-section normalization and detector integration.

## P1 — Reliable incident elastic channeling

- Validate Ni Bloch-wave diffraction against an independent solver and matched experimental/reference cases.
- Converge diffraction beam basis, specimen tilt, sample thickness, depth integration and 2D off-row reflections; incorporate beam convergence/thermal effects when warranted.
- Support general crystal orientations and reproducible reference diffraction intensities.

## P2 — Physical Ni L2,3 MDFF, before double channeling

- Implement a complex, Hermitian, positive-semidefinite site-aware 3x3 dipole transition tensor.
- Use atomic reference transitions first; then export spin-polarized SOC-DFT Ni 2p -> unoccupied-state complex transition matrix elements.
- Converge k points, empty bands, energy broadening, SOC/core states and matrix-element definitions; benchmark nonmagnetic ELNES and magnetic energy dependence.
- Keep full momentum-dependent MDFF as a future backend. Keep the current Gaussian model explicitly labeled illustrative.

## P3 — **Quantitative single-channeling EMCD benchmark (main immediate goal)**

- Contract the actual Ni complex MDFF with depth-dependent *incoming* Bloch waves, retaining site and beam coherence phases.
- Fix relative/absolute normalization, energy/momentum-transfer units, reciprocal maps, energy-resolved L2/L3 signals and aperture geometry.
- Compare 2BC, near-2BC, 3BC and zone-axis scans; converge thickness, tilt, beam count, detector area, reciprocal grid, depth grid and spectrum resolution.
- Independently verify numerical and physics invariants; compare Ni L-edge spectra/EMCD sign/geometry with reliable references and, when available, experiment.
- **Acceptance:** traceable inputs and units, independent calculations, convergence tolerances, reported uncertainty, and an unambiguous `entrance_only` label. Do not describe results as fully quantitative experiment-level EMCD until outgoing propagation and other missing effects are bounded or incorporated.

## P4 — Double channeling (after P3)

- Add outgoing Bloch-wave propagation at the post-loss electron energy using the same MDFF and detector contracts; multislice optional later.
- Directly compare single versus double channeling for identical Ni parameters; quantify changes in EMCD sign, L2/L3 contrast, thickness and reciprocal maps.
- Verify reciprocity/boundary conditions, beam/depth convergence and correct physical normalization; never compensate for outgoing dynamics by refitting an arbitrary magnetic fraction.

## P5 — Measurement-level quantitative validation

- Include finite probe source, specimen-specific strain/thickness, aperture calibration, spectrometer/energy response, backgrounds, dose/noise and artifacts.
- Compare experimental Ni data to model predictions; test sum rules and uncertainty/identifiability of effective spin and orbital contributions.

## P6 — Electrically tunable EMCD

- Implement spatially resolved `MaterialState(V, position, time)`: screening, charge, structure, magnetization/orientation and site-resolved transition tensors.
- Attach external DFT/electrostatic/ferroelectric/nonequilibrium transport providers depending on the actual device.
- Distinguish intrinsic magnetic changes from beam deflection, drift, ELNES/oxidation and structural effects; preserve hysteresis and history.

## P7 — Scale and deploy

- Larger/inhomogeneous structures and optional full-q MDFF, CPU optimization, GPU adapters and GUI/Windows packaging where useful.
- Maintain one portable core on Windows, macOS and Linux; external DFT calculations may run on Linux/HPC and export portable transition data.

**Development cadence:** focused tests/docs per patch, milestone reference/convergence suites when physics changes. Do not change implemented solver physics just to reorder this roadmap.
