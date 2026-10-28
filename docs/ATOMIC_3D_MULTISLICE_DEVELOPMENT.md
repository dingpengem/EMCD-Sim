# Atomic 3D multislice — integration plan, not implemented capability

Milestone A supplies a shared crystallographic engine. B1, B2, C and D are
**not implemented or enabled** by this change. Review Milestone A evidence
before beginning B1. No atomic backend selector or projected fallback is added.

## Geometry boundary: mandatory before B1

Recover the existing P1 structure/subslicing implementation from the recorded
atomic development branch, retain its numerical fixtures, and replace its GUI
orientation import and FCC-specific construction algorithm. Atomic geometry must
consume `CrystalOrientation` plus actual ASE/CIF structure, species, occupancies,
Cartesian positions, PBC and an explicitly bounded commensurate-cell construction.
It must never obtain atoms or geometry through `ProjectedGeometry` or an old
Ni orientation module. Reference configurations may be data; new axes must not
require new geometry source code.

An atomic commensurate cell must preserve all translations/atomic positions at
each z, including longitudinal modulation. A projected primitive repeat cannot
be substituted. For example, the documented [017] P1 transverse area is about
43.906 Å², versus about 0.8781 Å² for the primitive *depth-averaged* projected
potential (1.7562 Å² for its historical rectangular FFT cell). The smaller
projected repeat cannot represent the full depth-dependent atomic arrangement.
Reject impractical/noncommensurate periodic cases explicitly; never introduce
strain to force a small periodic box. Finite-cell alternatives require separately
documented boundary conditions and validation.

## B1: atomic potential and slice units

1. Define bounded atomic geometry and physical slice boundaries, independently
   of incident tilt and of the projected backend. Revalidate P1 [017] positions,
   density and plane boundaries; add [001], [117] and a nonpreset direction.
2. Establish a supported real 3D IAM atomic parametrization whose full-space
   Fourier transform agrees with the existing scattering-factor convention.
   Do not infer a finite-z atomic potential from ZOLZ coefficients alone.
3. Finite projection computes `V_n(x,y)=integral_slice V(x,y,z) dz` with neighboring
   atoms/slices included until tail/integration convergence is established.
   Infinite projection assigns a full projected atom to a designated slice as
   an explicit approximation; do not label that finite projection.
4. Store slice-integrated potential in V·nm, or equivalently phase
   `sigma * integral V dz` in radians. Transmission is `exp(i phase_n)`;
   **do not multiply by dz again**. Projected A instead stores radians/nm.
5. Test integrated potential, atom translations, overlap/tails, Fourier units,
   thermal/occupancy labels, boundary continuity and finite/infinite limits.
   Compare matched parametrizations with optional abTEM; differing parametrizations
   are a physical-model difference, not an error to eliminate by fitting.

The finite/infinite distinction and integrated-potential transmission follow
the documented multislice principles, without copying implementation code or
adding a mandatory dependency. See [abTEM potential documentation](https://abtem.github.io/doc/user_guide/walkthrough/potentials.html)
and [multislice derivation](https://abtem.github.io/doc/user_guide/appendix/multislice_derivation.html).
No abTEM numerical comparison has been performed in Milestone A.

## B2: elastic propagation

Reuse the existing FFT stepper with a sequence of genuinely depth-dependent
transmissions, physical nonuniform dz, incoming energy and reduced outgoing
energy. Expose prepared geometry/potential, incoming/outgoing propagation,
wavefield-at-depth, diffraction and numerical diagnostics through small adapters
around existing plans; avoid an unnecessary new plotting/solver framework.

Requested event depths must not move to nearby slice centers. Split propagation
at requested depths with consistent potential integration. Verify reverse slice
order and adjoint signs against direct finite-model propagation, conservation
for a real potential, raw complex amplitudes, and the constant projected limit.
Bound atom count, slice count, integration work, FFT storage and concurrent
workers before allocation; preserve cancellation and per-case checkpoints.

HOLZ requires demonstrated longitudinal diffraction effects and independent
convergence/reference checks. Atomic z coordinates alone are not evidence.
ZOLZ BW agreement is required in the projected limit, not as an equality target
when longitudinal modulation adds physical scattering.

## C: site/depth-aware EMCD and Double Channeling

Audit the suitability of the existing equivalent-site, beam-space inelastic
contraction before coupling it to atomic fields. Implement localized site/depth
ionization if required; elastic atomic propagation alone is not atomic EMCD.
Keep the Hermitian XMCD-effective tensor, crystal-frame magnetization and reversal
conventions. Do not fabricate a full DFT MDFF or refit amplitudes.

Test Single independently, then Double with outgoing propagation from each
physical event depth through the correct downstream slice sequence and post-loss
energy. Check reciprocity/adjoints, phase/site sums, projected-limit recovery,
magnetic odd/even identities and independent numerical convergence.
An elastic-only result must remain explicitly elastic-only until these pass.

## D: GUI and release gate

Only after scientific review expose Projected ZOLZ / Atomic 3D and Finite /
Infinite controls with backend-specific enablement, metadata and compatibility
checks. Reject unsupported Atomic EMCD rather than falling back. Retain raw
EELS/EMCD and relative common-denominator displays. Full regression, independent
reference evidence and Windows acceptance precede any packaging/release request.

Current limitations remain: approximate XMCD-effective MDFF, no complete
complex-transition DFT tensor, no validated atomic ionization coupling, no
experimental count/SNR calibration and no unrestricted orientation-convergence
claim. Native calculated source energies are not an absolute experimental
energy calibration. The projected Double model includes outgoing channeling
within its existing finite-support, depth-averaged approximation.
