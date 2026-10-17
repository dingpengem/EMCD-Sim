# FFT-multislice double-channeling EMCD

The new opt-in CPU implementation propagates both the incident and post-loss
wavefields by FFT split steps in the existing projected Ni IAM potential. It
uses no elastic eigenmode decomposition. The BW solver and legacy entrance-only
MS implementation are unchanged.

## Checkpoint A: compatible physics

Before implementation, the completed BW code, its 14 focused tests, and
[DOUBLE_CHANNELING_BW.md](DOUBLE_CHANNELING_BW.md) were reviewed. Both methods
use Fourier phases exp(+2*pi*i*g.r), reciprocal vectors in cycles/angstrom,
propagation distances in nm, and `d psi/dz = i H psi`. They share the same
relative per-atom intensity scale, tensor, Coulomb factors, equivalent-site
average, and independent-depth event sum.

The primary comparison deliberately freezes the longitudinal transfer at
`q_z=-E_loss/(h*v_in)` in both solvers. Bloch-branch shifts and transverse-angle
corrections inside the MDFF are not added to MS. Outgoing *elastic propagation*
nevertheless uses the actual post-loss energy, wavelength and interaction
constant. No eta/beta, source-energy, detector, gain, or magnetic scale is fitted.

The original theoretical reference remains Rusz, Rubino and Schattschneider,
[PRB 75, 214425 (2007)](https://doi.org/10.1103/PhysRevB.75.214425), inspected in
the [authors' original manuscript](https://arxiv.org/pdf/0704.1407), particularly
the entrance/exit boundary conditions and depth factor in Eqs. (16)-(26).
The same model approximations used in the BW reference are retained here.

## Relationship to the implementation references

[py_multislice, pyms/Ionization.py](https://github.com/HamishGBrown/py_multislice/blob/master/pyms/Ionization.py)
was inspected, especially `transition_potential_multislice`: individual target
transitions create scattered waves which are propagated to the exit; their
intensities accumulate independently. The small-grid direct reference here
implements that event-to-exit construction using the existing complex tensor
rather than importing atomic transition potentials from that package.

The [abTEM core-loss tutorial](https://abtem.github.io/doc/user_guide/tutorials/core_loss.html),
[core_loss.py](https://github.com/abTEM/abTEM/blob/main/abtem/inelastic/core_loss.py),
and [multislice.py](https://github.com/abTEM/abTEM/blob/main/abtem/multislice.py)
were inspected. Relevant routines include `get_transition_potentials`,
`transition_potential_multislice_and_detect`, and `conventional_multislice_step`,
including the double-channel branch and conjugate/transpose propagation options.
These are conceptual implementation cross-checks. Neither external package was
installed or used to supply the benchmark numbers. This code was implemented
independently and is not a numerical validation against abTEM or py_multislice.
The reference sources were accessed on 2026-10-17.

## Propagation and FFT normalization

For each step dz, the coefficient-space operator is

```
U_step = exp(i D dz/2) F exp(i V(r) dz) F^-1 exp(i D dz/2)
D_g = -10*pi*lambda*(|g+k_perp|^2-|k_perp|^2)     [radians/nm]
V_G = 10*gamma*lambda*F_G/Omega                  [radians/nm]
c_g = FFT(psi)_g / N_samples
psi(r) = N_samples * IFFT(c)(r)
```

The ordering of the symmetric split agrees with the existing projected FFT
reference. Its implementation retains Fourier coefficients between steps,
requiring one forward/inverse FFT pair per step. Parseval is
`sum_g |c_g|^2 = mean_r |psi(r)|^2`. Neither leakage nor inelastic intensity is
renormalized. No antialias aperture removes propagated amplitudes.

The exit carrier for a detector coordinate q is `k_in_perp + q`. Its kinetic
operator uses `E_out=E_incident-E_loss`. The real-potential Fourier couplings
scale with `gamma_out*lambda_out`, using the same elastic Fourier coefficients
as incoming propagation. The detector boundary is unit amplitude in exit 000
in that carrier's frame, representing the actual selected external momentum.

The adjoint detector state at an event is `b(z)=U_out(t,z)^dagger e000`.
Negative split-step distances conjugate both kinetic and transmission factors.
For nonidentical slices, `propagate_slices(..., adjoint=True)` also reverses the
slice sequence. Production uses a z-independent projected potential, but the
small reference test deliberately uses nonidentical, noncommuting slices to
verify that ordering rather than relying on a special constant-potential case.

## Complex MDFF and independent events

The supplied tensor obeys `T_ab=sum_f d_fa*d_fb*`, where
`d_fa=<core|r_a|final_f>`. Its full Hermitian eigendecomposition gives
`T=L L^dagger`. Only eigenvalues within `64*eps*norm(T)` of zero are rounded to
zero; a substantial negative eigenvalue raises an explicit error. No physical
mode is dropped by a strength threshold.

For an event at site u, the shared kernel is

```
q_gh = (q_detector + h - g, q_z)                  [cycles/angstrom]
K_gha(u) = (2*pi*q_gh,a)/|2*pi*q_gh|^2
           * exp(2*pi*i*(h-g).u)
psi_f,h(z) = sum_ga a_g(z)*K_gha(u)*L_af
A_f(exit) = [U_out(t,z) psi_f(z)]_000
```

The direct reference propagates each complex transition-mode wave forward to
the exit. The production adjoint formulation evaluates exactly the same linear
amplitudes through `b_h*(z)`, retaining interference across all g,h paths.
It accumulates the Cartesian response

```
v_a(z,u) = sum_gh a_g(z)*b_h*(z)*K_gha(u)
R_ab(q,E,t) = average_sites sum_z w_z v_a(z,u)*v_b*(z,u)
I(q,E,t) = sum_ab R_ab*T_ab = sum_z,sites,f w_z*|A_f(exit)|^2 / N_sites
```

The contraction uses `sum_ab R_ab*T_ab`, equivalently `Tr(R*T^T)`, to preserve
the repository's magnetic sign. It is not `Tr(R*T)`. Independent core final
states, distinct sites and distinct depths are summed as **intensities**.
Coherent mode amplitudes at separate depths are never added. Imaginary magnetic
antisymmetric terms remain intact. Magnetization reversal uses `T -> T.conj()`
against the same response, detector weights and elastic states.

Depth nodes include both surfaces with half endpoint weights and full interior
weights. The weights sum to specimen thickness. Raw zero-thickness intensity
is zero and paired percentages are NaN. Small positive thickness gives a linear
inelastic yield. This is the same uniform continuous-depth approximation as
the BW reference, not atomic-plane-resolved ionization.

## Basis and potential representation

The general new projected Ni [001] path performs 2D FFT propagation. The
benchmark's explicit systematic-row potential retains only (h00) Fourier
components; the envelope's h_y=0 sector is exactly invariant. Production uses
an explicitly requested 1D FFT of that sector. Tests compare it with the full
2D FFT calculation before benchmarking. This reduces redundant work without
changing the potential, beam cutoff, numerical precision or physical model.
It is not valid for a full 2D potential or an arbitrary zone axis, and requesting
it without the systematic-row approximation raises an error.

BW propagation uses a finite 11-beam incoming/outgoing Hamiltonian. MS retains
all 32 FFT harmonics in its invariant sector during propagation. Both use the
same 11 incoming/outgoing beams in the inelastic contraction. Thus propagation
is not strictly identical at finite bandwidth: feedback through harmonics
outside the BW basis is retained by MS. Its populations outside the common
MDFF basis and its norm errors are reported, without projection at every slice
or leakage renormalization. Basis and FFT controls assess this distinction.
The FFT potential cutoff is also bounded by the supplied potential object's
Fourier support; the controlled cutoff study changes that bound explicitly.

## Checkpoint B and focused tests

Tests in `tests/test_multislice_double_channeling.py` cover:

- Factorized transition modes against a direct dense complex MDFF, including
  a nonzero magnetic antisymmetric tensor and rejection of non-PSD input.
- Complex event-to-exit amplitudes against adjoint propagation and an explicit
  DFT-matrix product, with nonidentical slices and reversed adjoint ordering.
- A complete small-grid forward event/depth intensity sum against the adjoint
  response, with matched endpoints and outgoing energy.
- Vacuum phases, Parseval normalization, adjoint inversion, and a genuinely
  nonseparable 2D FFT step against a direct DFT matrix.
- Existing projected-potential coefficients and entrance-only FFT amplitudes.
- Disabled outgoing elastic scattering reducing to the existing entrance-only
  tensor kernel at matched depth quadrature.
- Reversal parity, nonmagnetic response, detector mirror symmetry, positivity,
  zero/thin thickness, and map/spectrum detector weights.
- Slice refinement, FFT bandwidth, retained beam basis, potential cutoff, and
  the full-2D versus invariant-sector equivalence.

Complex amplitude tolerances are `rtol=1e-13, atol=1e-13` for the independent
DFT-product comparison; the complete forward-depth versus adjoint intensity
comparison uses `rtol=1e-12, atol=1e-14`. These checks passed before Ni
production. They validate amplitudes and raw responses, not only ratios.
The old 14 focused BW checks were also rerun; no BW source was modified.

## Four-point Ni cross-validation

The calculation uses FCC Ni [001], a=3.524 angstrom, 200 kV, target (200),
absolute incident tilt (-7.116725439974256,+35) mrad, and exact incoming
s200=0 to numerical precision. The potential cutoff is 2.2 cycles/angstrom,
B=0, and the common basis has 11 h00 beams through (10,0,0) and (-10,0,0). The tensor retains
eta=beta=1 and cubic [001] magnetization. Native energies are 831.4778 eV (L3)
and 848.698 eV (L2), with no energy shift or post-edge normalization.

A/B apertures are at (0.283768445,+/-0.283768445) cycles/angstrom with radius
0.0908059024. The identical 193x193 integration grid covers [-0.5,0.5] and uses
64-subpixel fractional boundaries. Geometry weights are computed once and
reused for both edges, both reversal states, and both solvers. Angular previews
use a separate 49x49 grid over [-0.7,0.7]; they are not used for detector
integration. They retain 000, diffraction indexing, ZA coordinates, Thales
circle and physical detector overlays from `emcd_angular_plots.py`.

MS production uses 257 trapezoid nodes and maximum split-step thickness 0.04 nm;
actual equal steps divide each depth interval exactly. Both solvers evaluate
the same requested specimen thickness; there is no unit-cell rounding. BW
uses its analytical depth integral. Corresponding quadrature error is included
in the controlled analysis rather than treated as a model disagreement.

Before any new double-channel production, all four legacy 64-node MS detector
arrays were reproduced within 2.8e-17 absolute error. The saved BW source,
geometry, beam list, tensor settings, detector areas and implementation hashes
were checked against the new calculation. Compatible BW entrance/double values
were reused from `outputs/ni_double_channeling_bw/` instead of rerunning them.

| t (nm) | Edge | BW entrance (%) | MS entrance (%) | BW double (%) | MS double (%) |
|---:|:---:|---:|---:|---:|---:|
| 10 | L3 | -11.46555520 | -11.46548007 | -12.10054913 | -12.10056387 |
| 10 | L2 | +19.44949181 | +19.44936456 | +20.50420202 | +20.50422700 |
| 12 | L3 | -11.85490731 | -11.85484151 | -9.99581066 | -9.99581836 |
| 12 | L2 | +20.10931337 | +20.10920186 | +16.93994371 | +16.93995680 |
| 20 | L3 | -7.74009901 | -7.74008384 | -2.56555631 | -2.56558704 |
| 20 | L2 | +13.12981234 | +13.12978669 | +4.36045567 | +4.36050782 |
| 30 | L3 | -0.42145562 | -0.42151405 | -2.94417572 | -2.94411695 |
| 30 | L2 | +0.71493672 | +0.71503588 | +4.98411322 | +4.98401387 |

These are signed **raw** paired PRB percentages, `100*(A+ - B+)/(A+ + B+)`.
The magnetic-only percentage agrees to roundoff in this symmetric geometry;
the reversal-even paired imbalance is below 2e-13%. This equality is a tested
geometry symmetry, not an assumption made by the solver.

Underlying double-channel raw intensities (relative units; the exports retain
full float64 precision) and magnetic differences are:

| t (nm) | Edge | Method | A+ | B+ | A- | B- | Magnetic-odd difference |
|---:|:---:|:---:|---:|---:|---:|---:|---:|
| 10 | L3 | BW | 0.039328872 | 0.050157174 | 0.050157174 | 0.039328872 | -0.010828303 |
| 10 | L2 | BW | 0.035779252 | 0.023603328 | 0.023603328 | 0.035779252 | 0.012175924 |
| 10 | L3 | MS | 0.039329014 | 0.050157371 | 0.050157371 | 0.039329014 | -0.010828357 |
| 10 | L2 | MS | 0.035779396 | 0.023603410 | 0.023603410 | 0.035779396 | 0.012175985 |
| 12 | L3 | BW | 0.050062692 | 0.061182556 | 0.061182556 | 0.050062692 | -0.011119864 |
| 12 | L2 | BW | 0.043168685 | 0.030661836 | 0.030661836 | 0.043168685 | 0.012506849 |
| 12 | L3 | MS | 0.050062784 | 0.061182678 | 0.061182678 | 0.050062784 | -0.011119894 |
| 12 | L2 | MS | 0.043168773 | 0.030661890 | 0.030661890 | 0.043168773 | 0.012506882 |
| 20 | L3 | BW | 0.087662256 | 0.092278744 | 0.092278744 | 0.087662256 | -0.004616488 |
| 20 | L2 | BW | 0.062304072 | 0.057097614 | 0.057097614 | 0.062304072 | 0.005206458 |
| 20 | L3 | MS | 0.087662757 | 0.092279328 | 0.092279328 | 0.087662757 | -0.004616571 |
| 20 | L2 | MS | 0.062304480 | 0.057097928 | 0.057097928 | 0.062304480 | 0.005206551 |
| 30 | L3 | BW | 0.132578998 | 0.140622531 | 0.140622531 | 0.132578998 | -0.008043533 |
| 30 | L2 | BW | 0.095159153 | 0.086123805 | 0.086123805 | 0.095159153 | 0.009035348 |
| 30 | L3 | MS | 0.132579740 | 0.140623153 | 0.140623153 | 0.132579740 | -0.008043413 |
| 30 | L2 | MS | 0.095159539 | 0.086124326 | 0.086124326 | 0.095159539 | 0.009035213 |

The reversal-even **difference** is at floating-point roundoff (about 1e-16
in these relative intensity units), although the reversal-even **intensity
map** is large. Figure 4 explicitly labels the tiny paired-even difference
as roundoff. Do not confuse the even intensity with a nonzero detector imbalance.

### Quantitative BW/MS agreement

For double channeling, across all four thicknesses, both edges and all reversal
states, the maximum raw absolute discrepancy is 7.43e-7 and maximum symmetric
relative discrepancy is 6.55e-6 (0.000655%). The largest raw PRB difference is
0.00009935 percentage points. The magnetic-odd difference agrees within
1.35e-7 absolute and 1.81e-5 relative. Relative errors in the symmetry-zero even
difference are marked NaN rather than reporting meaningless percentages.

For entrance-only results, comparing analytical BW depth integration against
257-node MS gives at most 3.78e-6 relative raw error and 0.0001273 pp PRB error.
The larger relative magnetic-difference error (1.42e-4) occurs where the
entrance-only dichroism is small; absolute errors remain exported.

On the representative 12 nm angular grid, relative L2-norm map errors are
7.47e-6 / 7.51e-6 for magnetic L3/L2 maps and below 4.52e-6 for even/total maps.
These whole-map norms complement the detector intensity comparison; they do
not imply that pointwise relative errors near nodal lines are well defined.

### Controlled numerical/model differences

All controls below are at 12 nm with both edges and reversal states.

| Control | Maximum relative raw change | Maximum PRB change (pp) |
|:---|---:|---:|
| Maximum step 0.04 -> 0.02 nm | 1.0414567e-06 | 2.5178005e-05 |
| Depth nodes 257 -> 513 | 7.8392147e-07 | 3.8599468e-05 |
| FFT harmonics 32 -> 48 | 8.5352268e-14 | 2.0961011e-13 |
| Inelastic path basis 11 -> 13 | 1.6417545e-05 | 0.00025319335 |
| Potential cutoff 2.2 -> 1.8 cycles/A | 0 | 0 |
| Potential cutoff 2.2 -> 2.6 cycles/A | 0.0018147422 | 0.090859468 |

The step/depth controls are independent: changing depth spacing also changes
the exact substep sizes needed to land on each node, so their residuals can
partially cancel in a single observable. They are not a unique decomposition
of the total error. The 32-to-48 FFT change is at roundoff.

For matched enlarged 13-beam BW/MS calculations, the reused BW basis control
and new MS result differ by at most 1.03e-6 relative raw intensity and
0.000003982 pp PRB contrast at 12 nm, compared with 2.04e-6 and 0.00001310 pp
for the primary 11-beam case there. This supports the expected contribution
from finite BW propagation/basis feedback. The shared boundary, conjugation,
normalization and frozen-qz conventions passed their independent small-problem
checks; these residuals provide no indication of a sign or reciprocity error.

The potential-cutoff controls are a separate physical/numerical-model check.
Cutoffs 1.8 and 2.2 retain the same discrete h00 harmonics through (600), so
their identity is expected. Raising the cutoff to 2.6 adds (800) harmonics and
changes raw intensities by 0.1815% and PRB contrast by 0.09086 pp. Therefore
**potential-cutoff convergence is not established**, despite excellent BW/MS
agreement at the matched 2.2 cutoff. No parameters were adjusted to hide this
model sensitivity or to reproduce published amplitudes.

### CPU and RAM

On this local CPU with one BLAS/OpenMP thread, each primary thickness took
26.3-29.3 seconds for both edges/reversal states, including the entrance
diagnostic. The 513-node control took 54.2 seconds. These timings exclude
figure export and cached BW reference generation. Saved checkpoints resume
without repeating propagation. They are local measurements, not general
performance guarantees.

Primary admitted array working estimates are about 9.64 MiB per engine call;
the dense batched Cartesian pathway estimate is 0.355 MiB. Conservative total
process peak estimates were at most 258 MiB, including RSS, allocation margin,
128 MiB reserve and active reservations. Sampled post-point RSS was 112-115 MiB;
this is not a measured high-water mark. The configured budget remains 2048 MiB.

Incoming/outgoing norm errors remain below 8.1e-14. Maximum populations outside
the common inelastic basis are 4.51e-8 incoming and 2.03e-8 outgoing. No
renormalization removes those tails. The algorithm retains one incoming
depth-by-FFT array, processes at most 32 detector pixels per outgoing batch,
and accumulates only 3x3 Cartesian responses. It does not keep a full
depth-by-transition-by-detector wavefield stack.

Existing configurable budgets (512/1024/2048/4096/8192 MiB) and current physical
RAM admission checks are reused. Available-RAM rejection and all five budget
values are tested. The preparation path reserves memory before constructing
retained fields, and the engine reserves outgoing/pathway temporaries.
No grid, precision, slice count, basis or physical cutoff is reduced on failure.

### Final validation

All **31 focused tests passed**: 13 new core MS tests, four local output tests,
and the 14 existing BW checks. The local tests validate all raw reversal states,
masked discrepancies, convergence controls, norm/leakage diagnostics, memory
admission, figures, and source/previous-output hashes. See `focused_tests.xml`.


## Outputs, reproducibility and interfaces

Results are local under `outputs/ni_double_channeling_ms_validation/`:

- `results.csv` / `results.npz`: all four methods, both edges, raw A/B(+/-M),
  reversal decompositions and signed PRB percentages at each thickness.
- `discrepancies.csv`: absolute, signed and masked relative discrepancies for
  raw intensities, magnetic/even differences and normalized observables.
- `legacy_reproduction.csv`, `convergence.csv`, and
  `controlled_basis_comparison.csv`: distinct numerical/model checks.
- `angular_maps.npz`: intrinsic odd, even and total maps for BW/MS and both edges.
- Seven PNG/SVG figure pairs: L3, L2, entrance/double, reversal components,
  L3/L2 angular maps and discrepancy summary. Connecting lines join sampled
  points only; no thickness curve is fitted or smoothed.
- `configuration.json`, `performance.json`, compact `checkpoints/`, and
  `preservation.json`: source/code provenance, actual numerical settings,
  norm/leakage diagnostics, memory admission and preservation evidence.

New public interfaces are in `src/emcd_sim/multislice_double_channeling.py`.
`FFTSplitStep` and `propagate_slices` supply independent FFT propagation;
`transition_modes` and `forward_event_amplitudes` supply the direct reference;
`ProjectedNiFFT`, `incident_fields`, and
`multislice_double_channeling_response` supply the batched adjoint engine.
`run_tensor_multislice_double_channeling` returns the existing map/spectrum
`SimulationResult` with separate Boolean masks and integration weights. Its
binary default preserves the historical meaning of masks; fractional weighting
is explicit. No existing solver or GUI path is switched to the new backend.

Run the four-point study using the existing local Ni source and reference
outputs/project with `python scripts/ni_double_channeling_ms_validation.py`.
Exact-settings checkpoints support resuming only this study's computations.
Local output checks skip if the generated study is unavailable on a clean
checkout. Run the focused tests listed in the validation record; no broad
regression, full thickness scan, voltage sweep, GUI change, packaging or push
was performed.

## Limits and readiness

The implementation adds outgoing dynamical scattering; it does not remove the
approximate XMCD-constrained dipole MDFF, native-energy calibration uncertainty,
frozen q_z, continuous-depth site average, finite beam/path cutoffs, or real
projected IAM assumptions shared with BW. There are no atomic-3D potentials,
HOLZ, absorption, thermal diffuse scattering, multiple ionization events, or
calibrated absolute DDSCS prefactors. An arbitrary non-[001] orientation is not
yet supported by this FFT construction. Agreement is validation within the
matched model, not evidence that its absolute Ni magnetic amplitude is exact.

The solver is ready to undertake a controlled full 0-100 nm benchmark of this
projected model. The present validation covers 10-30 nm; it does not certify
fixed 257-node quadrature or a fixed beam basis at all larger thicknesses.
Upper-range depth/slice/basis convergence must be established in that subsequent
benchmark before interpreting finely resolved extrema or zero crossings.
No full scan or GUI integration starts automatically here.
