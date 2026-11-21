# Next-Gen A: depth, coherent probe and STEM physics design

Date: 2026-11-21. This is a design, not an implemented scientific capability.
Source identity, call graph and inherited acceptance are recorded in the
[architecture audit](NEXTGEN_A_ARCHITECTURE_READINESS.md). The current
`forward_pipeline.calculate` API, kernels and reference arrays are unchanged.

## Three different meanings of depth

| Capability | Scientific meaning | Current status |
|---|---|---|
| A: thickness-integrated calculation | Change total specimen thickness `t`; integrate local independent ionization contributions over `0 <= z <= t` | Production BW and FFT Single/Double support this within projected ZOLZ assumptions. |
| B: contribution versus integration depth | Retain the existing integrand, e.g. a Cartesian response or detector contribution at each quadrature node | Internally available in Double assembly, but not a public depth-resolved output. Exposing it would be useful diagnostics under the same projected model. It would not create a 3D specimen. |
| C: physically localized specimen/events | Propagate through an ordered, potentially varying slice stack; place an event at a declared atom/depth and propagate the post-loss state through the remaining specimen | Reference transport primitives exist; production specimen/event inputs, orchestration and scientific validation are missing. Required before claims of genuine localized depth/scan response. |

The current model is more than a thickness label: the incoming and outgoing
complex waves change with `z`, and their overlap affects intensity. Its limits
are the repeated projected potential and event distribution, not an absence of
outgoing wave propagation.

## What the present kernels calculate

Authoritative evidence is
[`multislice_double_channeling.py`](../src/emcd_sim/multislice_double_channeling.py),
`incident_fields` (232–251), `ProjectedFFT.plan` (216–229) and
`multislice_double_channeling_group_responses` (289–384), together with
[`projected_potential.py`](../src/emcd_sim/projected_potential.py),
`prepare_projected_potential` (48–92).

1. The complete structure supplies IAM ZOLZ Fourier coefficients. Their inverse
   FFT defines one real projected potential; its mean is removed as a common
   phase. The same potential is reused along the specimen. This is not an
   ordered series of 3D atom-derived slice potentials.
2. The incident boundary is a plane wave: Fourier coefficients `c[0]=1`, all
   other coefficients zero. Full FFT harmonics are propagated by symmetric
   kinetic/potential split steps. A trapezoid grid samples depth; physical split
   steps and integration nodes are different controls.
3. For each outgoing direction and actual energy loss, the outgoing plan uses
   `E_out = E_in - E_loss`, including its wavelength and potential-interaction
   scaling. The outgoing carrier is the incident carrier plus detector `q`.
4. A reciprocal detector wave is propagated backward from the exit. At each
   depth the retained outgoing coefficients are conjugated and contracted with
   the complex incoming coefficients, dipole momentum kernel and site phases.
   Schematically, `v_a(z,s,q)=sum(g,h) psi_g(z) phi_h(z,q)* K_gh,a P_s,gh`.
5. The kernel adds `w_z * w_s * v_a v_b*` to a depth-integrated response, then
   contracts the response with the declared energy-dependent tensor. Within an
   event, beam/path and Cartesian interference is retained. Contributions from
   independent target events are added as intensities/density operators.

Current site phases use periodic positions and reciprocal differences. They
select relative beam phases, not distinct physical event depths: selected sites
contribute throughout the continuum quadrature. Equivalent periodic phase
classes may be combined by `double_channeling.equivalent_site_phases`
(208–220). This is valid for the present independent-event periodic model;
it cannot be carried unchanged into arbitrary coherent/nonperiodic specimens.

Full FFT harmonics are propagated, while inelastic coupling retains a finite
incoming/outgoing Bragg support. Excluded population is measured and is not
renormalized away. A small retained Bragg set cannot automatically represent a
broad convergent aperture. The existing per-direction carrier treatment is not
a general probe scattering matrix.

BW Double uses the same incoming/post-loss-outgoing physical distinction with
finite Hermitian Hamiltonians. `double_channeling.depth_response` (88–131)
uses an analytic frequency-pair/sinc integral for the systematic-row case and
numerical depth quadrature otherwise. Single Channeling instead contracts the
depth-averaged incoming coherence with the local tensor and multiplies by its
depth measure; it omits post-loss elastic propagation. Keep these model and
method distinctions explicit.

## Local-event model and operator contract

Use a first-order, single core-loss event with elastic propagation before and
after it. Let `U_in(z,0)` transport the incident electron to event depth `z` and
`U_out(t,z;E_loss)` transport it to the exit at the reduced energy. Let `J_s,mu`
be the local transition operator for independent target final channel `mu` at
event `s`, and `D_d` a positive detector operator. Then

```text
rho_in(z) = U_in(z,0) rho_0 U_in(z,0)†
I_d(E) = sum(s,mu) w_s Tr[
    D_d U_out(t,z_s;E) J_s,mu(E) rho_in(z_s)
        J_s,mu(E)† U_out(t,z_s;E)† ]
```

For a coherent incident state this is the sum of detected squared amplitudes
of the independent transition modes. Keep each mode's complex phase through
the outgoing propagation. For mixed illumination, sum positive weighted
incident density components, not a single arbitrary coherent superposition.
The target-state trace and PSD MDFF factorization are supported by the primary
[MDFF pure-state decomposition](https://arxiv.org/abs/1210.2947). Coupling
elastic transport and local core-loss transitions is the relevant physical
starting point in [Dwyer's multislice treatment](https://doi.org/10.1016/j.ultramic.2005.03.005).
These references justify the model class; they do not validate this application's
unimplemented specimen builder or a quantitative magnetic spectrum.

For the existing Cartesian dipole convention, a Hermitian PSD tensor admits
`T=L L†`. Current `transition_modes` (15–29) and
`forward_event_amplitudes` (125–136) use the required conjugation of `L` for the
stored forward dipole `d=<i|r|f>`. Keep that convention and independently compare
the dense MDFF contraction; do not replace a complex tensor by component
intensities, keep only a dominant mode, or infer every `T_minus` by conjugation.
Only roundoff-scale negative eigenvalues within the existing contract may be
treated as numerical error; physically indefinite input must fail.

Different sites are incoherent only when their final target excitations are
orthogonal/local and unobserved. Correlated or nonlocal excitations require an
explicit cross-site response/covariance, not `abs(sum(site amplitudes))**2` by
default. A new coherent intersite model is outside the first prototype. Likewise
magnetic texture requires physically justified local tensors or a declared
covariant model; a spatial vector field alone does not specify an anisotropic
SOC-dependent MDFF.

### Ordered slices, event depth and adjoints

For slice boundaries `0=z_0<...<z_N=t`, define the ordered elastic products once.
Place the first prototype's event exactly at a boundary, after the preceding
slice and before the following slice. For event boundary `j`:

```text
incoming = U_in,j ... U_in,1 psi_0
exit_mode = U_out,N ... U_out,j+1 J_s,mu incoming
reciprocal_at_event = U_out,j+1† ... U_out,N† detector_exit
amplitude = reciprocal_at_event† J_s,mu incoming
```

The rightmost operator acts first. Direct and reciprocal evaluations must agree.
Noncommuting slice potentials make order observable. Existing
`propagate_slices` (117–122) reverses the slice sequence for adjoint propagation;
it and `forward_event_amplitudes` are useful reference primitives, not a complete
production arbitrary-depth specimen API.

Start with real potentials/Hermitian elastic generators. Negative split-step
distance gives an adjoint only under that assumption. A later complex absorptive
potential needs the actual adjoint with conjugate coefficients, not an assumed
inverse or a sign change. A physical event inside a finite slice later requires
splitting that slice consistently; assigning it to the nearest boundary without
an error/convergence analysis would change the event model.

### Event measures and normalization

Keep continuum `w_z` (nm) distinct from discrete event occupancy/multiplicity
(dimensionless). Do not apply both measures to the same atom. A response per
selected equivalent atom, a weighted site sum, and a per-volume signal are
different outputs. A discrete event of fixed occupancy need not vanish as an
unrelated slab thickness tends to zero; an empty event set does vanish. A
continuum model must vanish with its integration measure when thickness is zero.

Current tensors carry their declared source normalization, but intensities are
relative/arbitrary units and have no electron-count or absolute cross-section
calibration. Matching the current integrated limit requires the same event
density, site averaging, source tensor units, Fourier convention and detector
measure. Absolute dose, channel width and source-to-event normalization require
separate derivation before experimental claims.

## Coordinates, units and phase conventions

| Quantity | Required convention / current evidence |
|---|---|
| Cell/sites | ASE cell vectors are rows in Å; `r_crystal = fractional @ cell`. Fractional coordinates are not Cartesian magnetic components. |
| Nominal microscope frame | `R` has the proper orthonormal microscope axes as rows: nominal zone axis maps to `+z`, target reciprocal direction to `+x`, with a right-handed `y`. Row coordinates transform by `r_local=r_crystal @ R.T`. |
| Crystal rotation vs incident tilt | The frame uses the nominal orientation; current small-angle carrier is `tilt_mrad*1e-3/lambda` in cycles/Å. Do not rotate `R` again for the same tilt. This is the implemented paraxial approximation, not an exact large-angle sine rule. |
| Detector coordinates | `q_xy` is relative to the reference incident carrier; outgoing absolute carrier is `k_in+q`. For a future probe, one fixed laboratory detector must not move with every illumination component. |
| Fourier coordinates | Crystallographic `g,q` are cycles/Å; dipole momentum `Q=2*pi*q` is angular Å⁻¹. Current longitudinal transfer is `q_z=-E_loss/(h*c*beta)`, frozen across branches at a given loss, not across energies. |
| FFT grid | Reciprocal generator axes use `ij` ordering and may be oblique. The real dual cell is `inv(reciprocal_xy).T` in Å; grid indices are not automatically laboratory x/y. |
| Display maps | Current `(qy,qx)` arrays use xy mesh construction; a new wavefield layout must declare its axis order rather than copying the display-map convention. |
| Depth | Public thickness/integration depth nm; atom Cartesian positions Å. Conversion is explicit at the specimen/event adapter, exactly once. |
| Tensor frame | Source-frame-to-crystal rotation `F`, then crystal-to-microscope `R`: `T_local=(R F) T_source (R F).T` for real proper rotations. Magnetic directions are crystal Cartesian. |
| Magnetism | Passive coordinate transformation of a tensor differs from actively rotating magnetization in a crystal with SOC/anisotropy. Use declared ± states; retain symmetric real magnetic terms when present. Improper transforms need axial-vector handling, not ordinary vector rotation. |

Independent tests must rotate the cell, probe, detector and tensor consistently;
rotating only one object tests a different experiment. Site permutation symmetry
requires matching site weights/providers/events, not arbitrary merging of
magnetically distinct atoms.

## Convergent beam and real-space probe

Define a coherent angular spectrum in a single common transverse coordinate
frame. With cycles/Å wavevector `k`, a translated probe has

```text
c_R(k) = A(k) exp[-i chi(k)] exp[-2*pi*i k dot R_probe]
psi_R(x,y,0) = inverse_Fourier[c_R(k)]
```

Declare aperture shape/convergence semiangle, voltage, carrier/tilt, defocus,
aberration coefficients and phase convention, real cell, sampling and incident
normalization. The coherent aperture/aberration description is also used in
the primary [abTEM wave-function documentation](https://abtem.github.io/doc/user_guide/walkthrough/wave_functions.html).
Source size, partial coherence and frozen phonons would require separate
positive mixtures/ensembles and are not implicit in a coherent probe.

For one event and final mode, illumination components interfere **before** the
modulus is squared. Summing the intensities of independently tilted plane-wave
runs loses cross terms and is not convergent-beam STEM-EMCD. Reuse transport and
transition primitives with a new complex boundary state; do not create a second
material-specific STEM kernel. A scattering-matrix basis can reuse linear
transport, but its basis completeness, convergence and memory trade-off must
be validated. [Brown, Ciston and Ophus](https://doi.org/10.1103/PhysRevResearch.1.033186)
provide a relevant independent inelastic multiple-scattering method; their
published acceleration is not a measured EMCD-Sim speedup.

The current FFT convention is `c=fft(psi)/F`, `psi=ifft(c)*F`.
Thus `sum|c|^2 = mean|psi|^2`; a transmitted plane wave has `psi=1`.
A per-electron real-space integral normalization instead includes pixel/cell
area. Record the chosen norm and area explicitly; changing FFT library defaults
or forcing unit sum in one representation can silently rescale the signal.

Probe positions are physical transverse Å coordinates in the declared real
cell or laboratory plane. A raster is a view of a flat position list, not a new
physical axis convention. Translating the probe through a fixed specimen is
different from translating both specimen and probe or merely shifting a map.
Periodic wraparound, supercell adequacy, probe tails, aperture aliasing and
inelastic support must be converged before claiming atomic-resolution contrast.

## Depth/scan result semantics

Future results need named dimensions and coordinates: `probe(position,xy)` Å,
`energy` eV, `interaction_depth` nm or discrete `event_id`, `detector(qy,qx)`
cycles/Å, optional `site/group`, magnetic state, method and channeling labels.
Total specimen `thickness` is a separate parameter/ensemble coordinate.
Variable-thickness/event grids can be ragged or represented by auxiliary
coordinates; do not force every axis into one enormous rectangular array.

Raw independent-event contributions can be summed over depth/sites, but derived
ratios must be recomputed from summed parent signals, not averaged across bins.
Density/coherence matrices and wavefields are complex quantities, not extra
intensity channels. Save them only as explicit diagnostics with norm/phase
metadata. Default useful outputs are reduced detector spectra and selected
diffraction/depth diagnostics, not every transient wavefield.

## Five validation levels

| Level | Required evidence | What it does not establish |
|---|---|---|
| 1: invariants | Hermitian/PSD tensors; unitary real-potential transport; Parseval; correct ± reversal; valid site permutations; coordinate covariance; only physically applicable detector symmetries | That a correct invariant gives the intended material or specimen model |
| 2: independent mathematics/computation | Analytic two-state/noncommuting slice products, independent dense SciPy exponentials, direct event propagation versus reciprocal amplitude, dense MDFF versus PSD modes | Experimental agreement or basis convergence |
| 3: current limiting cases | Uniform repeated potential, plane incidence, identical support, event measure and detector normalization reproduce current BW/MS Single/Double limits within established numerical contracts | Equality when the new model adds physical z dependence or changes approximations |
| 4: external methods | Match potential, energy, transition operator, sampling, boundaries, aperture and norm against a published method/independent implementation | A comparison of unlike MDFFs, projected vs 3D specimens, or magnetic vs nonmagnetic sources |
| 5: experiment | Measured/validated material tensors, magnetism, thickness, orientation, probe aberrations/coherence, detector response, background/noise and dose calibration | Synthetic Cr/Fe3O4 fixtures validating measured spectra |

Suitable first external comparisons are nonmagnetic elastic and local core-loss
limits in [abTEM's core-loss treatment](https://abtem.github.io/doc/user_guide/tutorials/core_loss.html),
with fully matched physical inputs and normalization. Magnetic EMCD then needs
a compatible full complex tensor/provider and calibrated geometry; external
nonmagnetic agreement alone cannot certify it.

The eight existing targeted tests passed here include dense complex-MDFF
factorization, direct/adjoint complex amplitudes with reversed slice order,
vacuum FFT/Parseval/free-exit phase and the complete forward depth sum. They
exercise existing primitives, not an unimplemented general specimen interface.
The [roadmap](NEXTGEN_A_IMPLEMENTATION_ROADMAP.md) specifies the additional
independent tests and stopping criteria for B.

## Open scientific questions before broader claims

1. Which validated 3D IAM slice builder and longitudinal event representation
   will connect physical atoms to the prototype's explicit slice/event inputs?
   Resolve depth discretization, potential units, zero-mean convention and cell
   boundaries without copying a total projected potential into every physical slice.
2. How does each declared source tensor's per-atom/relative normalization map to
   discrete local operators and continuum density? Which absolute prefactors
   remain uncalibrated? This must be explicit before comparing amplitudes to experiment.
3. What momentum/FFT support and boundary conditions are sufficient for a
   convergent probe and local transition kernel, including oblique cells and
   post-loss energy? Current retained Bragg paths do not answer this.
4. Which magnetic rotations are justified by the provider model? Arbitrary local
   anisotropy, textures, nonlocal excitation and non-dipole effects need scientific
   development, not fallback to Ni or a generic tensor rotation.
5. What ensemble describes thermal scattering, source incoherence, finite
   specimen and noise? These are separately scoped physics; keep the initial
   real-potential, coherent, independent single-event prototype bounded.
