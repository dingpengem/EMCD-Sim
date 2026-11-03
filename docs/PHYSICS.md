# Physics and numerical methods

[Home](../README.md) · [Tutorial](TUTORIAL.md) · [User Manual](USER_GUIDE.md) · [Physical units](PHYSICAL_UNITS.md) · [Index](INDEX.md)

This reference describes the **released v0.7.0-beta.1** model, binary source `97b2220e`, convention **forward_born_dagger_g_minus_h_v1**. It replaces the old entrance-only overview as the current-facing explanation. The complete [pre-overhaul physics document](https://github.com/dingpengem/EMCD-Sim/blob/08d04fc35fca2071cc7e73af0aaa1de45e49a3f4/docs/PHYSICS.md) remains available at its immutable revision; its explicitly historical v0.2 statements are not the current model.

## Model boundaries

The active GUI models a plane-wave incident electron, an oriented projected independent-atom-model (IAM) Ni potential, a finite zero-order Laue-zone (ZOLZ) basis and localized single inelastic transitions. BW and FFT MS provide independent elastic propagation routes within these matched approximations. Single retains entrance channeling; Double additionally propagates the post-loss outgoing wave.

The principal Ni target response is an XMCD-constrained effective dipole tensor. The optional atomic 2p→3d approximation is non-DFT. Neither is a complete complex DFT-derived metallic-Ni MDFF or a calibrated absolute cross section. CIF parsing and generalized orientation support do not automatically extend the inelastic material model beyond the verified conventional FCC Ni cell.

## Coordinates, units and Bragg geometry

Direct-cell vectors are rows in Å. Crystallographic reciprocal vectors satisfy `b_i·a_j = δ_ij`, so **norm(g_hkl) = 1/d_hkl**, with no 2π factor. Detector q is relative to transmitted (000), also in Å⁻¹. Angular momentum transfer is **Q = 2πq**, dimensionally Å⁻¹ but numerically different. Bloch propagation uses depth in nm and eigenvalues in nm⁻¹. See [units](PHYSICAL_UNITS.md).

A structure-derived proper rotation R maps crystal Cartesian vectors into a target-aligned local frame. The nominal direct zone [uvw] defines local z; the selected reciprocal target defines x, and y completes a right-handed frame. Signed Miller indices and zone/FCC selection are retained. The crystal magnetic axis is transformed by the same R, not implicitly replaced by the incident direction.

The implemented paraxial ZOLZ relations are:

```text
k_perp = tilt_mrad * 0.001 / lambda
s_g = (lambda/2) * (g·g + 2*k_perp·g)
q_ZA = -k_perp
```

“Exact Bragg” means `s_target = 0` in this convention. It does not mean full 3D Ewald-sphere/HOLZ kinematics or physical isolation of two beams. At finite tilt, competing zone-plane reflections can remain excited.

The ZOLZ Laue circle has center q_ZA and radius norm(q_ZA); its reciprocal positions satisfy `s_g = 0`. Thales has center G/2 and radius norm(G)/2. Exact target Bragg makes G lie on Laue; off-row tilt generally prevents complete overlap with Thales. The circles do not determine a uniform EMCD intensity or enforce raw magnetic mirror parity.

## Elastic propagation

### Bloch-wave

`PhysicalElasticModel.hamiltonian_nm_inv()` forms a finite Hermitian generator with the existing IAM Fourier couplings and diagonal `−20π s_g`. Propagation is `psi(z) = exp(i H z) psi(0)`, starting at transmitted 000. This real nonabsorptive model conserves elastic norm within its finite support. It is not a complete absorption/TDS description.

### FFT Multislice

The generalized projected ZOLZ engine builds the oriented periodic cell and sampled projected IAM potential directly from structure/orientation. FFT propagation uses symmetric kinetic-half / potential / kinetic-half steps. Reciprocal indexing, potential bandwidth and the retained MDFF beam support must fit the FFT representation; unsupported configurations fail explicitly rather than substituting [001] or a (200) row.

The FFT mesh and retained basis are distinct. Additional FFT harmonics may participate in propagation; agreement at one basis does not prove independent basis convergence. **Max slice step** bounds propagation splits between requested depth planes:

```text
Delta_z_interval = t / (N_depth - 1)
n_substeps = ceil(Delta_z_interval / Delta_z_max)
actual_step = Delta_z_interval / n_substeps
```

The released requested maximum defaults to **2 nm**, with **0.001–10 nm** configurable. The actual step is bounded by the requested maximum and depth intervals; the existing 200,000-step guard remains. A coarse-step warning is advisory, not a universal physical threshold. Depth quadrature and propagation split-step convergence must be assessed independently.

## Localized inelastic scattering and channeling

Paths through reciprocal beams interfere coherently for one localized event. Independent sites/events add at the **intensity** level, with the existing equivalent-site/per-atom normalization. No second inelastic event or plural scattering is added by Double Channeling.

- **Single:** form the depth-averaged incoming coherence, contract the localized inelastic tensor and multiply by thickness once. No outgoing elastic diffraction.
- **Double:** form a depth-integrated Cartesian response from incoming and outgoing waves. The outgoing elastic energy is `E0 − E_loss`, independently evaluated at each requested loss. Its transverse carrier is `k_incident,perp + q_detector`. The response already includes depth integration; do not multiply by thickness a second time.

For incoming g and outgoing h, transverse transfer is `q_detector + h − g`. The longitudinal component is the signed negative characteristic loss transfer, approximately `−E_loss/(h_Planck*v_in)`, with the existing units/conversion. It varies with energy but remains frozen across branches; this is not full branch-dependent momentum conservation. The Cartesian Coulomb/dipole kernel uses `K_a = Q_a / Q²` and performs its angular 2π conversion internally.

BW Double uses the existing analytic depth response for the explicit systematic row and sampled trapezoidal integration otherwise; MS uses depth planes and bounded propagation substeps. Incoming/outgoing physical support, integration and boundary conditions must be matched when comparing methods.

## Corrected forward-Born convention

For the documented dipole convention `d_a = <i|r_a|f>` and transfer `Q = k_out − k_in`, forward target excitation involves the conjugated dipole. The tensor factory remains:

```text
T_ab = sum_n w_n d_na conj(d_nb)
T = L L†
R_ab = average_sites integral v_a(z) conj(v_b(z)) dz
I = Re sum_ab R_ab T_ba = Re Tr(RT)
```

Forward transition-amplitude propagation uses **L***, not L. The corrected Double atomic-site amplitude phase is **exp(+2πi(g−h)·u)**; Single's corresponding convention is preserved. All four Single/Double BW/MS routes use the coordinated corrected convention. Full Hermitian PSD tensors yield nonnegative intensities; the signed magnetic-odd component need not itself be PSD.

Legacy same-index contraction and the opposite Double site phase are superseded. Conventional FCC allowed phases can hide the latter discrepancy; it is not safe to replace correction by a universal sign flip of old arrays. Independent complex-dipole, nontrivial-site-phase and Double-to-Single controls are recorded in the [correction integration evidence](PHYSICS_CORRECTION_FINAL_INTEGRATION.md). Hermiticity/positivity alone do not calibrate the absolute experimental magnetic sign.

## Effective and atomic MDFF models

The XMCD adapter forms `N=(RP+LP)/2`, `D=(RP−LP)/2`, with effective `Txx=Tyy=N`, `Txy=i*eta*D`, `Tzz=beta*N`, normalized to a common original source maximum. It interpolates **original spectral input** at requested energies without extrapolation. This does not reconstruct genuine complex core/band/k/site transition amplitudes or establish absolute length-gauge matrix elements. Reversal occurs before `T_local = R T_crystal Rᵀ` (including the declared axis rotation).

The atomic alternative constructs an approximate Ni 2p→3d transition tensor using its atomic/crystal-field/exchange/hole/radial assumptions and model broadening. It is non-DFT, supports the documented [001] axis constraint and is not quantitative metallic Ni. A separate utility for user-supplied complex transitions does not itself run DFT or validate a complete Ni DFT MDFF.

Native energies are model/source-specific. No experimental edge shift or absolute RP/LP handedness calibration follows from a source filename, a Hermitian tensor or a successful run.

## Detectors, decomposition and normalization

Circular detector intensity is integrated as `I_D(E)=sum_p w_p I(q_p,E) dq²`, using deterministic fractional weights fixed for the grid/aperture and shared across reversal states. Raw intensity is integrated **before** detector ratios are formed. Area weighting convergence is distinct from intensity-field convergence; averaging local angular percentages is not detector integration.

For fixed A/B apertures, `N_A=(ap+am)/2`, `M_A=(ap−am)/2`, and similarly for B. Then `D_conv=ap−bp=(M_A−M_B)+(N_A−N_B)`. The conventional sum-normalized percentage is `100*D_conv/(ap+bp)`. Its common-denominator magnetic/nonmagnetic contributions use the **same ap+bp** and reconstruct it exactly.

The released GUI's advanced component diagnostics instead use `N_A+N_B`; these are separate observables and must not be added to reconstruct the conventional percentage. Fixed-detector Flip-M A is the full `ap−am=2*M_A`, normalized by `ap+am`. It is not the magnetic A/B difference. Half-sum/mean normalization doubles the corresponding percentage. See the [tutorial equations](TUTORIAL.md#part-vi-conventional-emcd-versus-flip-m) and [actual GUI/export definitions](USER_GUIDE.md#16-raw-and-normalized-signal-definitions).

Angular mirrored-point differences are also distinct from raw reversal-odd fields and finite detector integrals. Constructed mirror differences do not prove physical antisymmetry of an original map. Post-edge A/B scaling is derived processing, not intrinsically magnetic recovery. All denominator and invalid-support masking policies must accompany exported percentages.

## Convergence and physical limitations

Distinguish **functional support**, **BW/MS agreement**, **independent numerical convergence** and **physical/experimental validation**. Vary beam support, potential cutoff, FFT mesh, depth quadrature, MS step, detector grid/extent, aperture weighting and energy sampling independently before combined controls. A sampled peak or passed representative point does not certify untested thicknesses or global maxima. Keep failed checks and the original thresholds.

The [111] lower-support profile remains quantitatively uncertified; [117] default potential support can omit off-row harmonics. Existing native acceptance uses small bounded profiles and does not erase those warnings. Neither an accurate elastic pattern nor aperture area guarantees converged EMCD. See [generalized merge readiness](GENERALIZED_MULTISLICE_MERGE_READINESS.md) and [current manual limitations](USER_GUIDE.md#scientific-limitations-and-responsible-interpretation).

Missing/incomplete scope includes full complex DFT MDFF, bonding/DFT potential, genuine atomic-3D multislice, full HOLZ, comprehensive TDS/absorption, convergent-probe/physical CBED, plural inelastic events, equilibrium magnetic/domain modeling and experimental energy/handedness/count/dose/noise calibration. Arbitrary-unit raw intensities and percentages are not experimental SNR.

## Formula-to-source map

Paths refer to the unchanged released implementation; function names are preferable to historical line numbers.

|Responsibility|Production module / entry points|
|---|---|
|Crystal frame and ZOLZ indexing|`crystallography.py`; `gui/geometry.py`: `orientation`, `geometry`, `align_bragg`, `excitation`|
|IAM/BW generator|`scattering.py`; `physical_elastic.py`: `PhysicalElasticModel`|
|Single shared tensor contraction|`single_channeling_tensor.py`: `_tensor_angular_maps`|
|BW Double response, phase and trace|`double_channeling.py`: `double_channeling_response`, `depth_response`, `equivalent_site_phases`, `intensities_from_response`|
|Projected FFT and Double modes|`multislice_double_channeling.py`; `projected_geometry.py`, `projected_potential.py`|
|MDFF construction / rotation|`mdff_tensor.py`, `xmcd_effective_mdff.py`, `ni_local_mdff.py`; `gui/emcd_forward.py`: `tensors`|
|Loss scheduling, fixed weights, spectra|`gui/channeling.py`: `angular_schedule`, `contract`|
|Display definitions / masks|`gui/component_display.py`, `gui/prb_benchmark.py`, `gui/signal_normalization.py`|
|Project/export provenance|`gui/project_io.py`; `gui/emcd_forward.py`: `export_result`; `gui/normalization_export.py`|

See [GUI technical navigation](EMCD_GUI.md). This table is a documentation map, not an instruction to modify any kernel.

## References and historical records

- Rusz, Rubino and Schattschneider, *Physical Review B* **75**, 214425 (2007), [DOI](https://doi.org/10.1103/PhysRevB.75.214425): existing theory/normalization reference. A PRB-compatible difference/sum readout is not quantitative reproduction of its conditions or figures.
- [IAM elastic formulation](PHYSICAL_ELASTIC.md), [Double full spectra](DOUBLE_CHANNELING_FULL_SPECTRA.md), [correction acceptance](PHYSICS_CORRECTION_ACCEPTANCE.md), and [uniform basis study](DOUBLE_CHANNELING_UNIFORM_BASIS.md) retain their original validation scopes.
- [Physics conventions/source map audit](PHYSICS_CONVENTIONS_AND_SOURCE_MAP.md) explicitly records the **pre-correction** source and discrepancies. Its same-index formulas are historical findings, not current production rules. The [approved correction proposal](PHYSICS_MINIMAL_CORRECTION_PROPOSAL.md) and subsequent integration evidence supersede those code paths.
- The [documentation index](INDEX.md) separates current guides, scientific validation, historical records and planned architecture. No new experimental, literature-digitization or convergence study is performed by these docs.
