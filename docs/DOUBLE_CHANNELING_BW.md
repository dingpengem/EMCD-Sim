# Bloch-wave double-channeling EMCD

This opt-in solver includes coherent elastic propagation before and after one
core-loss event. It leaves the entrance-only solver, its defaults, source
spectrum, and previous numerical outputs unchanged. No multislice or GUI
implementation is included.

## Theory checkpoint and source inspection

The theoretical source checked directly was the authors' original manuscript of
Rusz, Rubino and Schattschneider, *Physical Review B* **75**, 214425 (2007),
[arXiv:0704.1407](https://arxiv.org/pdf/0704.1407), especially Eqs. (3)-(4),
(13)-(18), and (24)-(26), pp. 2-4. The
[journal DOI](https://doi.org/10.1103/PhysRevB.75.214425) identifies the published
paper; the publisher PDF returned HTTP 401, so the equations were inspected in
the original author manuscript rather than a secondary summary. Separate
entrance/exit eigenproblems and surface boundary conditions determine the
coefficients. The thickness factor retains both sets of eigenvalue differences.
The implementation retains the paper's branch-independent MDFF approximation.

Implementation references were inspected independently:
[abTEM core-loss tutorial](https://abtem.github.io/doc/user_guide/tutorials/core_loss.html),
including its single/double-channel distinction, and
[py_multislice Ionization.py](https://github.com/HamishGBrown/py_multislice/blob/master/pyms/Ionization.py),
particularly the event-to-exit propagation and intensity accumulation in
`transition_potential_multislice`. They provide conceptual cross-checks, not
numerical validation against those packages. Their code was not copied.

## Implemented conventions and derivation

The following defines this implementation in the repository's existing units.
`PhysicalElasticModel` uses `d psi/dz = i H psi`, with H in radians/nm,
reciprocal vectors in cycles/angstrom, and an omitted common mean-potential
phase. Its ZOLZ basis has g_z=h_z=0. The same potential object supplies both
Hamiltonians, but their eigenproblems are solved independently.

Write `H_i=C diag(lambda) C^dagger` and
`H_o=D diag(mu) D^dagger`. The incoming boundary is `a(0)=e000`:

```
a_g(z) = sum_j C_gj C_0j* exp(i lambda_j z).
```

At exit thickness t, the reciprocal ket is `b(t)=e000`:

```
b_h(z) = [exp(i H_o (z-t)) e000]_h
b_h*(z) = [exp(i H_o (t-z))]_0h
        = sum_l D_0l D_hl* exp(i mu_l (t-z)).
```

The second line is the detector bra for propagation from the event to the
exit. Using the incoming eigenvectors or simply conjugating a forward ket at
positive distance would give incorrect coefficients for a general complex
Hermitian potential. The independent two-beam test uses complex off-diagonal
couplings specifically to expose this distinction.

The outgoing kinetic energy is `E0 - loss`, separately for every spectral
energy. Its transverse carrier is `k_in_perp + q_detector`; its tilt is derived
using the **outgoing** wavelength. Thus fixing the carrier does not mean copying
the incoming absolute tilt. For efficiency, the outgoing potential couplings
are constructed once per loss energy. The detector shift changes only its
kinetic diagonal by `-20*pi*lambda_out*(h dot q_detector)` in inverse nm.
This identity is tested against full construction by `PhysicalElasticModel`.

For each incoming/outgoing pathway, define:

```
q_gh = (q_detector + h - g, -loss/(h*v_in))  [cycles/angstrom]
Q_gh = 2*pi*q_gh                           [angular inverse angstrom]
K_gha(u) = Q_gh,a / |Q_gh|^2 * exp(2*pi*i*(h-g).u)
v_a(z,u) = sum_gh a_g(z) b_h*(z) K_gha(u)
T_ab = sum_f w_f d_fa d_fb*, d_fa = <core|r_a|final_f>
I(q,E,t) = average_u integral_0^t dz sum_ab v_a T_ab v_b*
```

Here `(h-g).u` uses integer Miller indices and fractional basis positions.
The detector carrier's common site phase cancels in intensity. For allowed
FCC Ni beams, the site phases are unity to floating-point roundoff; the
implementation nevertheless sums individual equivalent-site **responses**, not
site amplitudes. Independent target final states are already summed in T;
different ionization events are independent intensity contributions. Coherence
between all g,h pathways at one event remains intact.

The shared Cartesian response is
`R_ab = average_u integral v_a v_b* dz`. Contract as **sum_ab R_ab T_ab**,
equivalently `Tr(R T^T)`, not `Tr(R T)`. This distinction fixes the magnetic
sign for the repository's dipole convention. Hermitian PSD T gives nonnegative
intensity because it is a sum of squared transition amplitudes. No q-q'
interference is discarded and no empirical outgoing correction is applied.

### Analytical and numerical depth integration

For each mode pair m=(j,l), write
`v_a(z)=sum_m F_ma exp(i omega_m z)`, where
`omega_jl=lambda_j-mu_l` and F includes `exp(i mu_l t)` and the beam sums.
Then:

```
J_mn(t) = t exp(i*(omega_m-omega_n)*t/2)
          * sinc((omega_m-omega_n)*t/(2*pi))
R_ab = sum_mn F_ma J_mn F_nb*
```

NumPy's normalized sinc supplies the stable coincident-eigenvalue limit. The
factor t gives linear thin-specimen inelastic yield on the same relative scale
as the entrance-only backend. There is no coherent summation over events at
different depths. At t=0, raw intensities are zero and paired percentages are
undefined. A separate trapezoidal reference evaluates propagated states at
individual depths and integrates their complex Cartesian outer products.

## Minimal reusable interfaces

New module: `src/emcd_sim/double_channeling.py`.

- `BlochStates.solve(H, boundary_index)` and `.ket(distance_nm)` represent a
  boundary-conditioned finite Bloch field. Negative distance is intentional
  for the reciprocal exit state.
- `dipole_kernel(q_cycles)` converts to angular momentum and returns Q/Q^2.
- `depth_response(incoming, outgoing, kernel, t, method=...)` integrates the
  complete complex response for one detector direction and one site.
- `outgoing_elastic(...)` constructs a physically separate exit eigenproblem.
- `double_channeling_response(...)` returns detector-resolved `(pixels,3,3)`
  responses, averaging equivalent Ni sites. Arbitrary finite oriented ZOLZ
  incoming/outgoing beam sets are supported; they can differ.
- `intensities_from_response(response, tensor)` contracts a PSD complex tensor.
- `run_tensor_double_channeling(model, tensor, ...)` returns the existing
  `SimulationResult` with maps, spectra, Boolean masks, and separate detector
  weights. Binary integration remains its default; fractional mode is explicit.

A future multislice implementation can supply the incoming ket and exit bra at
each depth and use the same Cartesian kernel/response and tensor conventions.
Its independent transition-to-exit propagation should reproduce the closed
small-model tests before comparison with Ni. No multislice work starts here.

## Validation checkpoints

Checkpoint A ran before the Ni benchmark: direct transition-amplitude sums
versus the complex MDFF contraction; Hermitian symmetry; reversal; magnetic
antisymmetric sign; phase conjugation; positivity; and the 2*pi momentum units.

Checkpoint B also ran before the Ni benchmark: an independent closed-form
2x2 matrix exponential with complex couplings and Gauss-Legendre depth
quadrature; analytical versus trapezoidal complex responses; correct exit
boundary; invariance under independent common Hamiltonian phases; zero outgoing
potential reduction to the unchanged entrance-only kernel; symmetric detector
reversal; zero/thin thickness; and separate incoming/outgoing basis checks.

The 2x2 reference agrees at approximately machine precision (test tolerance
`rtol=2e-13, atol=1e-14`). Trapezoid errors decrease by approximately four on
node doubling; the 2049-node result uses `rtol=3e-6, atol=1e-8`. The free-outgoing
comparison uses `rtol=1e-12, atol=1e-14` on underlying intensities. A/B symmetry
is tested in a geometry where it is physically expected, not imposed on general
geometries. Foundation and solver tests are separate files and commands.

## Four-point Ni benchmark

The executable study is `scripts/ni_double_channeling_bw.py`. Results are local
under `outputs/ni_double_channeling_bw/`; large generated files are not committed.
The physical setup matches the preceding voltage study at 200 kV: FCC Ni
(a=3.524 angstrom), nominal [001], (200) systematic row, 11 incoming and 11
outgoing beams, potential cutoff 2.2 cycles/angstrom, basis cutoff 3.2,
Debye-Waller B=0, exact incoming Bragg x tilt -7.11672544 mrad and fixed y tilt
+35 mrad. This is a systematic-row model, not a literal isolated two-beam
Hamiltonian and not a full 2D diffraction convergence claim.

The unchanged XMCD-constrained tensor has eta=beta=1 and cubic [001]
magnetization. Native energies are L3=831.4778 and L2=848.698 eV, with no
experimental energy shift or post-edge normalization. Both reversal tensors
are contracted against identical elastic responses.

Fixed reciprocal-space Thales detector centers are
A=(0.283768445,+0.283768445), B=(0.283768445,-0.283768445) cycles/angstrom,
radius 0.0908059024. The primary grid is 193x193 over [-0.5,0.5] in each
coordinate, with 64 boundary subpixels per axis and the existing fractional
weights. Effective areas and the full configuration are exported.

Entrance-only numbers use the existing kernel with **analytical** finite-BW
depth coherence. Earlier voltage-study numbers used 64 trapezoid nodes, so small
differences from that saved curve reflect depth quadrature, not a change to the
entrance-only model. No prior output is overwritten. Incoming/outgoing propagation
and the main double-channel integral both use float64/complex128.

The signed raw PRB contrast is `100*(A+ - B+)/(A+ + B+)`. Magnetic-only
asymmetry uses the reversal-even sum as its denominator. In this symmetric row
geometry, reversal-even imbalance is below 1.2e-13%, so magnetic-only and raw
PRB percentages coincide to roundoff. This is a tested symmetry of this setup,
not an assumed property of general double-channel calculations.

| t (nm) | Edge | Method | A+ (relative units) | B+ (relative units) | Raw PRB (%) | Magnetic-only (%) | Even imbalance (%) |
|---:|:---:|:---|---:|---:|---:|---:|---:|
| 10 | L3 | entrance | 0.037431683 | 0.047126780 | -11.465555 | -11.465555 | 0.00e+00 |
| 10 | L2 | entrance | 0.033469090 | 0.022569809 | +19.449492 | +19.449492 | 1.24e-14 |
| 10 | L3 | double | 0.039328872 | 0.050157174 | -12.100549 | -12.100549 | 1.55e-14 |
| 10 | L2 | double | 0.035779252 | 0.023603328 | +20.504202 | +20.504202 | 0.00e+00 |
| 12 | L3 | entrance | 0.044571469 | 0.056560579 | -11.854907 | -11.854907 | 1.37e-14 |
| 12 | L2 | entrance | 0.040249752 | 0.026772115 | +20.109313 | +20.109313 | 1.04e-14 |
| 12 | L3 | double | 0.050062692 | 0.061182556 | -9.995811 | -9.995811 | 6.24e-14 |
| 12 | L2 | double | 0.043168685 | 0.030661836 | +16.939944 | +16.939944 | -2.82e-14 |
| 20 | L3 | entrance | 0.076912812 | 0.089817937 | -7.740099 | -7.740099 | 1.66e-14 |
| 20 | L2 | entrance | 0.062502146 | 0.047994185 | +13.129812 | +13.129812 | 6.28e-15 |
| 20 | L3 | double | 0.087662256 | 0.092278744 | -2.565556 | -2.565556 | 0.00e+00 |
| 20 | L2 | double | 0.062304072 | 0.057097614 | +4.360456 | +4.360456 | 1.74e-14 |
| 30 | L3 | entrance | 0.124495957 | 0.125549788 | -0.421456 | -0.421456 | 1.11e-14 |
| 30 | L2 | entrance | 0.083447942 | 0.082263213 | +0.714937 | +0.714937 | 1.67e-14 |
| 30 | L3 | double | 0.132578998 | 0.140622531 | -2.944176 | -2.944176 | -1.12e-13 |
| 30 | L2 | double | 0.095159153 | 0.086123805 | +4.984113 | +4.984113 | -1.53e-14 |

Both raw reversal states and all unrounded diagnostic numerators/denominators
are preserved in `results.csv`, `results.npz`, and per-thickness NPZ checkpoints.
All intensity and observable differences are in `differences.csv`.

| t (nm) | Double minus entrance L3 (pp) | Double minus entrance L2 (pp) |
|---:|---:|---:|
| 10 | -0.634994 | +1.054710 |
| 12 | +1.859097 | -3.169370 |
| 20 | +5.174543 | -8.769357 |
| 30 | -2.522720 | +4.269177 |

Double channeling strengthens the sampled 10 nm and 30 nm signals and weakens
the 12 nm and 20 nm signals. Neither edge reverses sign at these four points.
The strongest sampled double-channel L3 magnitude is at 10 nm, whereas the
strongest sampled entrance-only magnitude is at 12 nm. These four samples do
not locate a continuous global maximum. The effect is not a constant
multiplicative outgoing factor.

### Numerical controls and preservation

At 12 nm, expanding incoming/outgoing bases separately from 11 to 13 beams
changes all raw detector states/edges by at most 1.64e-5 / 2.32e-6 relative,
respectively. Expanding both gives 1.76e-5 relative and at most 0.000271 pp in
PRB contrast. Reducing the incoming basis to 9 gives 1.49e-4 relative; reducing
the outgoing basis to 9 gives 2.40e-5. These explicit row expansions keep the
elastic potential cutoff fixed; the 13-beam control adds (12,0,0) and (-12,0,0) beyond the
primary beam cutoff. It does not silently change the primary model.

The 193-to-385 grid control changes raw intensities by at most 1.93e-5 relative
and PRB contrast by 0.000178 pp. Numerical depth response errors at detector A/B
centers and both native energies are approximately 1.96e-6, 4.90e-7 and 1.23e-7
relative for 257, 513 and 1025 nodes, respectively. These are Frobenius errors
of the full complex Cartesian response, rather than errors in a final ratio.

All **14 focused tests passed**. In addition to the mathematical checks above,
the final checks reproduce the previous 200 kV entrance-only raw intensities
at all four thicknesses with matched 64-node quadrature (`rtol=1e-13`), verify
map/spectrum fractional weighting, and compare an existing atomic transition
provider against an explicit final-state amplitude sum. The direct-Hamiltonian
and exact-diagonal-update implementations agree in saved 10/12 nm raw arrays
within `rtol=2e-13`. Previous voltage-study file hashes and the source spectrum
are verified unchanged in `preservation.json`.

Run only the focused checks:

```powershell
python -m pytest tests/test_double_channeling_foundation.py -q
python -m pytest tests/test_double_channeling_bw.py -q
python -m pytest tests/test_ni_double_channeling_bw.py -q
```

The last file uses local benchmark results and skips on a clean checkout
without generated data. Regenerate the four-point study with
`python scripts/ni_double_channeling_bw.py` using the existing local saved
reference project and Ni source. It writes only its own output folder.

`comparison.png` and `comparison.svg` show the sampled L3/L2 values with
connecting lines as guides to the eye. `configuration.json` records the
calculation base commit, source/code hashes, actual grid, detector geometry,
beam list and excitation errors. Its nested `config` retains the loaded
project defaults; the top-level grid, energies and analytical-depth method
record the actual overrides used here. `convergence.csv` and
`depth_convergence.csv` retain the raw numerical checks. `results.npz` includes
the analytical and numerical complex responses. No previous study was rerun
or overwritten.


## Remaining physical and numerical scope

The solver is a reference **within its stated finite-ZOLZ, paraxial,
branch-independent dipole-MDFF model**. It is not an absolutely calibrated Ni
cross-section or a reproduction of the full first-principles calculation.

The XMCD tensor remains an approximate constrained model, including its original
polarization-sign assumptions and unmeasured longitudinal response. Its native
energy axis is unchanged and has not been calibrated to experiment. The atomic
MDFF provider is also an independent-electron approximation, not a Ni band MDFF;
both providers share the same complex dipole interface.

The longitudinal transfer is frozen at the existing loss/(h*v_in) value. Changes
of Bloch-branch longitudinal momentum inside the MDFF/Coulomb factors, and
transverse-angle corrections to q_z, are neglected; the dynamical propagation
phases themselves are retained. Uniform continuous depth density replaces a
plane-by-plane atomic ionization sum. These assumptions make analytical depth
integration possible and keep the entrance-only limit matched. HOLZ, absorption,
thermal diffuse scattering, multiple inelastic events, and surface potentials
are absent. The potential is the existing projected IAM, not a new DFT potential.

Representative beam/depth/grid sensitivity tests do not establish full 2D basis
or potential-cutoff convergence. Extending the row or potential model may alter
both absolute yield and dichroism. The publication's accelerating voltage has
not been independently established. Its Figure 5 is not an implementation test
or a fitting target. A four-point sample cannot identify a global thickness
maximum or a full oscillation period.

Memory admission reuses the existing configurable budget and current-RAM checks,
with default 2048 MiB. Estimates include mode-pair complex temporaries, numerical
reference arrays, and detector responses. Only one pixel's dense mode-pair matrix
is retained at a time; thicknesses are sequential and compact results are saved
after each point. No physical sampling or precision is reduced on admission
failure. No full thickness/voltage scan, GUI update, executable build, package,
release, or push is part of this task.
