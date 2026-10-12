# Quantitative single-channeling EMCD: design and validation gates

**Priority:** first establish a quantitatively controlled, physically calibrated **entrance-channeling-only** forward model for FCC Ni L2,3. Implement outgoing/double channeling **after** this baseline is independently verified. This is a development specification, not a claim of achieved accuracy.

## Scope: two different meanings of "quantitative"

1. **Quantitative within the single-channeling approximation:** real elastic crystal potential and converged incident wave, calculated core-loss transition matrix elements / complex MDFF, known normalizations and units, well-defined crystal orientation, apertures, and numerical convergence. Compute physically defined single-channeling cross sections (or explicitly normalized relative observables with traceable prefactors).
2. **Quantitative prediction of a measured experimental EMCD spectrum:** additionally requires checking the neglected outgoing propagation, absorption/TDS, probe and spectrometer effects, specimen structure, thickness/tilt and uncertainty. Single-channeling alone does **not** establish this stronger claim. Report the model discrepancy independently, rather than hiding it by fitting magnetic scaling.

Use a visibly labeled `approximation: entrance_only` in all saved results. Never rename the existing phenomenological Gaussian MDFF as DFT-derived, or treat `magnetic_fraction=0.12` as a fitted Ni material constant.

## Calculation hierarchy

### Stage SC0 — Freeze units, coordinate and chiral signs

- Fix `g` in cycles/Angstrom for diffraction; use angular wavevector `Q=2*pi*g` in `exp(i Q·r)`. Document `q_z(E)`, energy-loss sign, 000-centered detector coordinate, crystal/lab frames and detector handedness.
- Distinguish sample bias in V from microscope accelerating voltage in kV, and keep sample magnetization as a vector.
- Test ideal 2BC, near-2BC, symmetric-3BC and 2D ZOLZ indexing, tilt/excitation errors, Thales positions, four-quadrant differences and magnetic reversal. A nominal 3BC systematic row is **not** an experimentally validated 3BC alignment.
- Test nonmagnetic symmetry cancellation for ideal paired apertures and observe when finite-basis/tilt geometry legitimately breaks it.

### Stage SC1 — Validate incoming elastic channeling independently

- Use the current Ni independent-atom potential as the baseline, with a documented Debye-Waller model; allow optional self-consistent/absorptive potentials without mixing them.
- Compare Bloch-wave `I_g(t)` and excitation errors against an independently implemented multislice or published reference using matching inputs. Verify 2BC analytical limits, unitary norm when absorption is off, and beam-set/tilt/thickness convergence.
- Progress from row-only to a controlled two-dimensional ZOLZ basis; quantify omission of off-row/higher-order beams. Include finite probe convergence/incident-angle integration only when needed for the specific experimental benchmark.
- Do not retune potential strength or extinction distance merely to force EMCD agreement.

### Stage SC2 — Replace assumed N(E), M(E) with physically sourced complex MDFF

- Introduce a `TransitionDataset` containing Ni 2p1/2 and 2p3/2 core states (SOC), unoccupied final-state energies, **complex** transition matrix elements, k-point weights, occupancies, sites, spin/magnetization axes, broadening and provenance.
- Use an atomic/reference transition model to verify the mathematics first; then import converged spin-polarized DFT+SOC transitions from an all-electron or suitably reconstructed-core workflow (DFT need not run inside the Windows app).
- Construct a Hermitian positive-semidefinite dipole tensor `T_ab(E)` and evaluate `S_dip(Q,Q',E) = Q^T T(E) Q'` with a single documented phase convention. Keep higher-multipole/full-q as future backends.
- Keep the *MDFF proper* separate from the Coulomb factors `1/(q² q'²)`, prefactors and detector projection in the cross section.
- Verify k-point, bands, core spin-orbit splitting, radial matrix elements, energy resolution/broadening and (as needed) core-hole/many-body sensitivity. Compare Ni ELNES and magnetic L3/L2 signal shape with reliable experimental/theoretical reference spectra. Do not derive full off-diagonal MDFF merely by subtracting spin DOS.

### Stage SC3 — Couple the MDFF to incoming channeling with physical normalization

For an electron detected at reciprocal coordinate `Q_det` and energy loss `E`, a schematic entrance-only contraction is:

`I_SC(Q_det,E) = C(E) sum_sites ∫_0^t dz sum_(g,h) W^(in)_(gh,site)(z; Q_det) S_site(q_g,q_h,E) / (|q_g|² |q_h|²)`.

`W^(in)` includes calculated incident Bloch-wave amplitudes/coherences, site coordinates, phase conventions and the *chosen free-flight/no-outgoing-channeling* exit assumption. `C(E)` contains the electron-scattering normalization consistently derived for the chosen `q` units. This is an architectural expression, not an implementation-ready universal formula.

- Contract the **complex** MDFF with coherent incident amplitudes, preserving complex phase and local/site depth weights.
- Use outgoing momentum/energy in `q_z`, but do not accidentally propagate a dynamical outgoing wave in the entrance-only backend.
- Return absolute differential cross sections only after the fast-electron prefactors, local atom density, normalization, units and detector solid angle are checked. Until then explicitly label results `relative_intensity` and identify missing factors.
- Produce indexed elastic diffraction, nonmagnetic and magnetic reciprocal maps, A/B or four-quadrant spectra, L2/L3 difference and asymmetry from the **same** reciprocal-coordinate convention.
- Keep electrostatic beam deflection, detector response and nonmagnetic background distinct from intrinsic magnetic changes.

### Stage SC4 — Convergence and reference Ni benchmark

A single-configuration numerical result is not validation. Establish a reference matrix of Ni thickness, incident tilt, two-/three-beam and 2D ZOLZ conditions, detector centers/radii and magnetization reversal:

- Numerics: beam count/cutoff, depth steps, reciprocal grid, energy grid, k points, unoccupied bands and broadening.
- Physics invariants: Hermitian/PSD MDFF, nonnegative total cross section, correct magnetic reversal, chirality interchange, proper nonmagnetic symmetry cancellation in ideal limits, 2BC analytical or independently computed benchmarks.
- Literature/experiment: compare diffraction `I_g(t)`, Ni L2/L3 edge positions and spectral shape, EMCD sign maps, thickness/tilt dependencies and (with correct corrections) orbital/effective-spin sum-rule integrals.
- Uncertainty: quantify which errors are numerical, from electronic structure, specimen/optics, and **from omitting outgoing channeling**; do not absorb them into a phenomenological magnetic fraction.
- Publish a reproducible `examples/ni_single_channeling/` benchmark and machine-readable metadata with convergence tables and references.

**Acceptance for "validated single channeling":** all chosen Ni benchmark calculations are converged to declared tolerances and compared to independent reference calculations; physical constants and outputs are traceable; remaining approximations are explicit; comparisons to measurement do not claim the missing outgoing channel is negligible without evidence.

## When to add double channeling

Only after the above entrance-only reference is stable, introduce a second `ExitChannelPropagator` that reuses the same material state, MDFF contract, detector geometry and metadata. Make `channeling_mode={entrance_only,double}` explicit.

Validate the double backend first against its **entrance-only limit**, then independent solutions. Examine changes in Ni L2/L3 reciprocal maps, contrast, magnetic sign and thickness dependence; **never silently apply an empirical correction factor to the single-channeling result**. Full experiment-level quantitative claims require this omission to be bounded or addressed.

## Voltage-field compatibility without premature voltage physics

Save the baseline material state and `MDFFSource` with an explicit external-condition identifier `state_id`. Later, `MaterialState(V, position, time)` may replace the reference state and produce new site-resolved complex transition tensors, elastic potentials and magnetic textures. Keep `N(E,V)=N(E,0)` and `M(E,V)=M(E,0)f(V)` confined to a clearly labeled sensitivity/demo backend. Real gating, ferroelectric, ionic and current-driven states require different physics, and sample bias may also alter microscope optics/beam trajectory.

## Engineering and portability

- Portable CPU core on Windows, macOS, Linux; optional DFT/HPC/Linux workers export structured transition data.
- Keep `python -m emcd_sim` and the current FCC Ni benchmark runnable while new backends are developed.
- During incremental patches, use focused unit/physics tests and document changes; at each scientific milestone, run larger independent reference and convergence suites.
- Do **not** start double-channeling implementation as a prerequisite for developing the MDFF tensor, normalization, or single-channeling benchmark.
