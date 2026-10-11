# Physics, definitions, and validation status

**Status: v0.2 research-stage, *physical Ni elastic entrance propagation* with illustrative magnetic/ELNES scattering; NOT a predictive quantitative EMCD solver.**

## 1. Coordinate conventions

- Crystal direct lattice vectors as rows in Angstroms. Reciprocal vectors as rows in **cycles/Angstrom** (`b_i · a_j = delta_ij`, no 2π). This is intentionally compatible with common crystallography conventions.
- Lab z axis is parallel to the nominal incident beam and Ni [001]. In the v0 solver, reflections must have g_z = 0 and the crystal must already be oriented in the lab frame. Generic tilted zone-axis projection/orientation transforms are not implemented yet.
- In-plane momentum transfer: `q_j,xy = k_out,xy − k_inc,xy − g_j`. Inelastic longitudinal transfer: `q_z ≈ −E/(h v)` (small-loss approximation for `q = k_out − k_in − g`; the helper returns positive magnitude). These are *momentum transfer frequencies*, not angular wavevectors.
- Sample bias `V` and microscope acceleration `kV` are intentionally separate variables.

## 2. Elastic beam propagation (physical Ni backend; surrogate retained)

The **default** solver is the finite-basis **physical Bloch-wave backend** (`PhysicalElasticModel`), with FCC Ni scattering factors from Lobato–Van Dyck (2014), real independent-atom crystal potential and relativistic interaction constant. Default basis `000, ±200, ±400, ±600`. Details and numerical unit derivation are in [PHYSICAL_ELASTIC.md](PHYSICAL_ELASTIC.md).

`H_gg = -10πλ(|k⊥+g|²−|k⊥|²)` and `H_gh = 10γλ F_(g−h) / Ω`, with z in nm; `ψ(z)=exp(iHz)ψ(0)`. The extinction distance is derived rather than set by `--xi-nm`. For neutral 200-kV FCC Ni, a=3.524 Å and B=0 the calculated *two-beam* ξ200 ≈ 37.58 nm. This estimate is **not measured or independently validated**.

The original `ElasticModel` surrogate is still available by `--elastic-backend surrogate` with its legacy `H_gg = +2π s_g`, `H_gh = π/xi` and power-law couplings. It is kept solely to reproduce and compare early results and is not a physical crystal-potential computation.

Depth integration uses `C_ij(t) = (1/t)∫₀ᵗ ψ_i(z)ψ_j*(z)dz`. The Hermitian nonabsorptive model conserves the elastic norm. **Neither backend includes outgoing channeling**, absorptive loss, convergent probe or arbitrary crystal orientation.

## 3. Inelastic scattering and chiral term

In a cubic dipole approximation, parameterize:

`S(q_i,q_j,E) = [N(E) (q_i · q_j) + i M(E) m_hat · (q_i × q_j)] / (|q_i|² |q_j|²)`

`I(q,E) ∝ Re[sum_ij C_ij S(q_i,q_j,E)]`.

`N(E)` is the illustrative *nonmagnetic* Ni L2,3 white-line contribution plus flat baseline; `M(E)` is the illustrative chiral term, with opposite L3 and L2 signs. `m_hat` is a unit magnetic direction. Negative moment is permitted as a way to reverse this direction. Conjugate symmetry guarantees a real intensity. For `|M| <= N` the tensor kernel is positive semidefinite at fixed E (assuming the basis/normalization used here).

For numerical angular kernels, denote `N`-free geometry `K_N` and `M`-free geometry `K_M`. Then `I(q,E) ∝ t [N(E) K_N(q,E) + M(E) K_M(q,E)]` (a single-inelastic-scattering thickness factor t, with K computed from the *depth-averaged* coherence). The relative `A-B` dichroism must reverse under magnetization reversal, and the `N` term must not.

**No absolute cross-section prefactor** has been applied: data are dimensionless arbitrary integrated intensities, not counts or physical cross section. Matrix elements, core-hole interactions, polarization- and band-structure-sensitive fine structure are not provided by Gaussian peaks. **L3=852.7 eV, L2=870.0 eV are nominal representative positions.** The default magnetic fraction `0.12` and L2 magnetic amplitude ratio `-0.5` are illustrative, not measured or DFT-derived nickel spectral strengths.

## 4. EMCD virtual apertures

Beam geometry: [001] / symmetric 3-beam systematic row `±(200)`; detectors A/B located in mirrored positions on opposite sides of the horizontal diffraction row, with positive x offset to avoid symmetry cancellation. Their reciprocal radius is user adjustable. Integrating over finite circular apertures yields `A(E), B(E)`, `Delta(E)=A-B`, `asymmetry(E)=Delta/(A+B)`.

A `TabulatedEdgeSpectrum` adapter can replace the illustrative Gaussian line shapes with independently supplied nonmagnetic/magnetic energy channels (interpolation only within calibrated energies). Its magnetic channel is still scaled linearly by the user-selected moment under the present `DipoleMDFF` model.

The nominal outputs are **geometry-dependent forward examples**. Physical Ni elastic scattering is now implemented, but experimentally relevant simulations still require measured tilt and thickness, beam convergence, sufficient diffraction-beam convergence, spectrometer acceptance and drift, outgoing propagation, and quantitative inelastic scattering.

## 5. Voltage-to-magnetization parameterization

`MagnetizationLaw(V)->muB/atom` is an interchangeable interface; `ConstantMagnetization` and `TabulatedMagnetization` are supplied. `TabulatedMagnetization` linearly interpolates *user-supplied* magnetic moments only **within** the tabulated range; it does not extrapolate. `DipoleMDFF` scales the chiral spectral strength linearly with the moment relative to 0.60 µB/atom. This is a **controlled hypothesis** for a first-pass sensitivity study, *not* a magnetoelectric or electronic-structure prediction.

Electrostatic bias can cause magnetic anisotropy changes, domains/reversal, charge transfer, strain, oxidation/electrochemical reactions and altered ELNES backgrounds, depending on heterostructure and circuit. A bias applied to bulk metallic Ni by itself has **no universal voltage-to-moment law**. Predicting signal changes needs a model or measurements of the actual electrically gated structure; ideally `M(E, V)` and `N(E,V)` independent of fixed moment scaling.

## 6. Implemented checks

1. FCC allowed/forbidden reflections and reciprocal units; measured Ni electron scattering factor (2014 table) reference numbers.
2. 200-keV electron relativistic wavelength and qz positivity.
3. Hermitian physical Bloch-wave Hamiltonian, unitary propagation, PSD depth coherence and exact two-beam Bragg Pendellösung benchmark.
4. Magnetic reversal changes chiral signal sign, but does not change its symmetric background.
5. L3/L2 have opposite chiral signs in the illustrative line-shape model.
6. Bias model interpolation/bounds; invalid inputs rejected.

## 7. Essential missing physics before quantitative EMCD

- **Now implemented:** neutral Ni independent-atom scattering factors, Fourier potential, selected-beam propagation, optional B/occupancies. **Still missing:** experimental B/occupancies, absorptive potentials, bonding/DFT charge density and independent convergence validation.
- Full wave-optical convergent probe, systematic-row and arbitrary zone orientation, multi-beam Bloch-wave or multislice propagator for **both pre- and post-core-loss trajectories**.
- DFT/ELNES-calibrated, site- and edge-resolved `S(q,q',E)` with magnetization orientation, realistic L2/L3 line-shapes, spin–orbit and dynamical correlation effects.
- Finite detector acceptance, spectrometer energy response and realistic noise / dose model; measured Ni thickness, tilt and field.
- Sum-rule analysis with consistent post-edge background and validation against measured EMCD spectra.
- Bias-dependent electronic structure and spin/orbital moments or measured `M(V)`; magnetic configuration and hysteresis with realistic device geometry.

## References for formulations and benchmarks

- Schattschneider et al., *Ultramicroscopy* **108**, 433–438 (2008), DOI: 10.1016/j.ultramic.2007.07.002 (MDFF q·q′ and i q×q′ structure).
- Rusz et al., *Nature Communications* **7**, 12672 (2016), https://pmc.ncbi.nlm.nih.gov/articles/PMC5013673/ (beam amplitudes, chiral term, dynamical scattering).
- *Quantitative characterization of nanoscale polycrystalline magnets with electron magnetic circular dichroism*, *Nature Communications* **5**, 3138 (2014), https://www.nature.com/articles/ncomms4138 (diffraction-plane signal, dichroism geometry).
- Fang et al., *Physical Review B* **86**, 134114 (2012), https://web.science.uu.nl/SCM/Articles/2012/Fang_PhysRevB_2012.pdf (FCC Ni `a≈3.524 Å`, ~0.60 µB/Ni benchmark). This value is not a calibration of EMCD strength.

- Elastic implementation reference: [PHYSICAL_ELASTIC.md](PHYSICAL_ELASTIC.md).
