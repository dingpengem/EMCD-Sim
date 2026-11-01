# Physics conventions and formula-to-source map

Audit date: 2026-11-01. Source: local `main` at
`a77f7455f5fe57dad6bae5d948477b2390433bb0`, worktree
`build/source-cleanup-integration`. Line numbers refer to this unchanged source.
See [findings](PHYSICS_MATRIX_IMPLEMENTATION_AUDIT.md) and
[validation evidence](PHYSICS_VALIDATION_RESULTS.md). No production corrections
have been applied. **Confirmed implementation does not mean confirmed physics.**

## Literature and access boundaries

The [Rusz–Rubino–Schattschneider author manuscript](https://arxiv.org/pdf/0704.1407)
for [PRB 75, 214425](https://doi.org/10.1103/PhysRevB.75.214425) was inspected:
Eqs. (3–5) define Bloch waves and the MDFF; (13–18) specify boundaries,
independent exit waves and transfers; (24–26) give site and thickness factors.
Its MDFF uses initial-to-final dipoles; matching this symbol alone does not
establish the ordering of a forward transition contraction.

[Negi–Idrobo–Rusz, Scientific Reports 8, 4019](https://www.nature.com/articles/s41598-018-22234-8.pdf),
Methods, pp. 2–4, Eqs. (1–5), supplies the target-excitation scattering operator,
transfer-pair MDFF and magnetic cross-product decomposition. It uses a combined
multislice/Bloch approach, not an independent numerical validation of these
two code backends. Eq. (2) writes explicit Fourier factors with `2*pi`.

[Dwyer, Ultramicroscopy 104, 141–151](https://doi.org/10.1016/j.ultramic.2005.03.005)
was consulted through the publisher abstract and author-affiliated publication
record. Full text was inaccessible (publisher HTTP 403). Its equation-level
operator/conjugation comparison is **unverified**, and no equation numbers are
invented here. Access to that paper remains a review requirement.

`EMCD-Sim_Current_Algorithm_Matrix_Derivation_2026-11-01.md` was not found by
filename search in the repository or supplied attachment directories. The
request's equations were audited directly, not treated as authoritative.

## Implemented chain

Here `Ni` and `No` denote the independent incoming/outgoing beam counts, `p`
a detector pixel, `n` a target transition, and `a,b` Cartesian components.
All following formulas in the table describe inspected code, unless marked
as the proposed microscopic interpretation.

The final [correction proposal](PHYSICS_MINIMAL_CORRECTION_PROPOSAL.md) maps
the shared Single BW/MS contraction and both Double wrappers explicitly,
and preserves `T=L L^dagger` while conjugating forward excitation modes only.

| Stage / units and shape | Exact implementation | Source and evidence | Status / consequence |
|---|---|---|---|
| Reciprocal frame | `g=hkl @ inv(cell).T`, cycles/Å; row-vector cell. `k_perp=tilt_mrad*1e-3/lambda` | `crystal.py:28`, `geometry.py:40`; existing geometry tests | Confirmed. No implicit `2*pi` in lattice coordinates. |
| Elastic generator, `(Ni,Ni)`, rad/nm | `H_gg=-10*pi*lambda*(g²+2*k_perp.g)`; `H_gh=10*gamma*lambda*F(g-h)/volume`; Hermitian lower triangle | `physical_elastic.py:50`; `scattering.py:81` uses negative Fourier site phase | Confirmed real IAM, no absorption. Omitted common mean-potential phase cancels in intensities. |
| Excitation errors | `s_g=lambda*(g²+2*k_perp.g)/2`; `H_gg=-20*pi*s_g` | `physical_elastic.py:92`, `bragg_tilt_mrad:88` | Confirmed paraxial ZOLZ convention. |
| Incoming ket, `(Ni,)` | `a_g=sum_j C_gj C_0j* exp(i*lambda_j*z)` | `physical_elastic.py:74`; `double_channeling.py:25,31`; new `exp2` control | Confirmed finite Hermitian model, complex eigenvectors included. |
| Single coherence, `(Ni,Ni)` | `C_gg'=integral a_g a_g'* dz/t`, trapezoidal depth average | `elastic.py:65`, `multislice_reference.coherence_from_amplitudes` | Confirmed. Single multiplies by `t` exactly once. |
| Outgoing generator | New energy `E0-loss`, carrier `k_in_perp+q_detector`; detector correction `-20*pi*lambda_out*h.q` | `double_channeling.py:130,199`; existing `test_outgoing_energy_boundary_and_carrier` | Confirmed. Outgoing eigenvectors are not incoming eigenvectors. |
| Exit bra, `(No,)` | `e0^dagger U_out(t-z) = [U_out(z-t)e0]*` for Hermitian H | `double_channeling.py:109,115`; new rectangular-kernel and complex-H controls | Confirmed. `conj(U_out(+distance)e0)` would generally be wrong. |
| Transfer, `(Ni,No,3)` | `Q=2*pi*(q_detector+h-g, -E_loss/(h*v_in))` | `double_channeling.py:208`, `geometry.py:25`; `single_channeling_tensor.py:45` | Confirmed frozen longitudinal characteristic-loss approximation; not full branch-dependent kinematics. |
| Coulomb kernel | `K_a=Q_a/Q²`, units Å; two path factors supply `1/(Q² Q'²)` | `double_channeling.py:71`; new independent kernel/MDFF unit test | Confirmed one `2*pi` conversion; proper MDFF excludes denominators. |
| Double site amplitude | `exp(+2*pi*i*(h-g).u)`; site groups retain multiplicities | `double_channeling.py:148`; shared by MS | **Inconsistent with Single in the free-exit limit for nontrivial phases.** FCC allowed phases hide it. |
| Single site pair | `average exp(+2*pi*i*(g-g').u)` | `single_channeling_tensor.py:19` | Opposite of Double's free-exit pair phase; independently reproduced. |
| Event vector, `(3,)` | `v_a=sum_gh a_g bra_h K_gh,a phase_gh` | `double_channeling.py:110`; `multislice_double_channeling.py:341` | Coherent paths at one site/depth only. Shared transition-convention issue below. |
| Response, `(p,3,3)` | `R_ab=average_sites integral v_a conj(v_b) dz` | `double_channeling.py:84`; MS depth loop | Confirmed Hermitian PSD response. Depth/site events add incoherently, not as amplitudes. |
| Analytic depth integral | `omega_jl=lambda_j-mu_l`; `J_mn=t*exp(i*(omega_m-omega_n)*t/2)*sinc((omega_m-omega_n)*t/(2*pi))`; `R=F.T @ J @ F.conj()` | `double_channeling.py:114`; independent 96-node Gauss control | Confirmed for real eigenvalues, including degeneracy; continuous depth density. Absorptive eigenvalues unsupported. |
| Transition tensor, `(E,3,3)` | Declares `d=<i|r|f>`; `T_ab=sum_n w_n d_na conj(d_nb) G(E-E_n)` | `mdff_tensor.py:132`; new explicit Gaussian Gram test | Confirmed algebra, PSD for nonnegative transition weights. `DipoleTensor` constructor checks Hermiticity, not PSD of arbitrary supplied tensors. |
| Proper MDFF | `S(Q,Q')=sum_ab Q_a T_ab Q'_b` | `mdff_tensor.py:111` | Confirmed Hermitian transfer-pair matrix; nonnegative diagonal for PSD T. Does not settle which pair order multiplies fast-electron coherence. |
| Production intensity | `I=Re sum_ab R_ab T_ab = Re Tr(R T^T)` | `double_channeling.py:218`, `contract_cartesian:79`, Single `:57`, MS wrapper `:390` | Algebraically equals `sum_n w_n |sum_a v_a d_na|²`. **Not the forward Born contraction for the declared `d=<i|r|f>` with fixed forward fields.** |
| Microscopic forward interpretation | Target factor `<f|exp(-i Q.r)|i> = -i Q.d* + O(Q²)` | Independent derivation in audit report and minimal failing test | Requires conjugated target amplitudes, or consistently redefining imported dipoles. Approval required before changing a kernel/schema. |
| FFT elastic propagation | `c=fft(psi)/N`; symmetric kinetic-half / potential / kinetic-half, `exp(+i H dz)`; adjoint uses negative dz and reverse slice order | `multislice_double_channeling.py:36,83,117`; independent DFT/Pauli controls | Confirmed split-step convergence in small model. Full FFT elastic support differs from finite BW support; selected MDFF paths are not a projection at every step. |
| Target modes | `T=L L^dagger`, modes multiplied as `K @ L`; sum squared exit amplitudes over modes | `multislice_double_channeling.py:15,125` | Confirms current same-index algebra, but shares the Born-convention discrepancy. |
| Tensor rotation / reversal | Crystal reversal first; `A=R @ Q_axis`; `T_local=A T_crystal A.T`; second state checked against `T_local.conj()` | `gui/emcd_forward.py:93,101`; existing orientation/reversal tests | Confirmed real proper rotations. Does not implicitly beam-align magnetization. RP/LP sign mapping remains uncalibrated. |
| XMCD effective source | `N=(RP+LP)/2`, `D=(RP-LP)/2`, `Txy=i*eta*D`, `Tzz=beta*N`; common maximum normalization | `wien2k_xmcd.py:23`, `xmcd_effective_mdff.py:8` | Confirmed source identities and PSD bound, but no genuine complex DFT transition reconstruction or verified absolute handedness. |
| Detector and GUI | Fractional weights fixed across energy/reversal; integrate raw intensity with `dq²`, then compute differences/percentages | `geometry.py:60`, `gui/channeling.py:52,62,163`, `gui/emcd_forward.py:220` | Confirmed. No additional thickness factor for Double. Paired display maps must not be evidence of physical mirror parity. |

## Dimensions, normalization and physical scope

For length-gauge transition data, `d` is Å, `T` is Å²/eV, proper `S` is
1/eV, `K` is Å, and integrated `R` is nm·Å². Before aperture integration the
relative contraction carries nm·Å⁴/eV. Physical density and scattering
prefactors are not calibrated; aperture integration adds reciprocal area.
XMCD-effective tensors instead use normalized spectral intensities, not
measured length-gauge dipole units. Neither path supplies absolute electron
counts. Positivity and BW/MS agreement do not establish the magnetic sign.

No absorption/TDS, HOLZ, atomic-3D potential, double ionization, complete DFT
MDFF, or absolute energy calibration is established by this audit. Supported
complex Hamiltonians here are **Hermitian**, with real eigenvalues. The
Hermitian sinc formula must not be extended to absorptive eigenvalues without
changing its conjugated frequency differences and reciprocal propagation.
