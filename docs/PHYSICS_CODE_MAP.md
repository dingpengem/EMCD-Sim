# Current physics and implementation map

This document describes the local production calculation. Historical audits,
accepted reference sources and release reports describe their recorded revisions;
they are not specifications of today's implementation. In particular, the
current forward contraction is **Re Tr(R T)**, with the material indices reversed
in the elementwise contraction. See also [the refactor name map](REFACTOR_NAME_MAP.md).

## Reading the calculation

1. `gui.geometry.Structure`, `Settings` and `geometry` supply the complete ASE
   crystal, proper crystal-to-beam rotation, ordered ZOLZ basis and microscope.
   `crystal`, `crystallography`, `crystallographic_sites`, `multisite` and
   `ionization_sites` own lattice, site and assignment rules.
   Neutral `structure_snapshot`, `restore_structure` and `structures_match`
   belong to `gui.geometry`; previews do not depend on project-file I/O.
   `projected_geometry_from_oriented_crystal` also belongs here and delegates
   to the existing `ProjectedGeometry.from_oriented` implementation.
2. `gui.forward_settings.NiForwardSettings`, `gui.material_inputs` and
   `gui.forward_settings.MultiSiteForwardSettings` record existing model and
   sampling requests. A site-group provider reference owns its material source;
   the complete crystal, including elastic-only atoms, owns the elastic potential.
3. `scattering`, `elastic_providers` and `projected_potential` prepare the IAM.
   `physical_elastic`, `multislice_reference` and `multislice_double_channeling`
   propagate the incident wave and, for Double Channeling, reciprocal exit waves.
4. `mdff_providers` owns source declaration, identity/material validation and
   provider preparation, independently of widgets and the elastic wave.
   `prepare_provider` and `load_site_group_provider` retain distinct declared
   interpolation and historical direct-evaluation models. `atomic_ionization`,
   `generalized_xmcd`, `manual_l23` and `imported_mdff` implement distinct sources.
5. `gui.forward_pipeline.calculate` is the canonical entry point for explicit
   structure, geometry, source/model and optional site-group inputs; it orchestrates
   resource admission, propagation and result assembly.
   `gui.propagation` owns numerical preflight, allocation estimates and method
   diagnostics; `gui.channeling.propagate` owns incoming BW/FFT execution.
   `gui.channeling.calculate_detector_signals`
   schedules single-provider energies; `gui.multisite_integration` schedules and
   reduces bounded multisite blocks. These application services do not use widgets.
6. The Single/Double kernels below form intensities; `detector_signals` integrates
   fractional apertures and constructs reversal components. `gui.forward_results`
   assembles result metadata, selected-edge metrics and completed-method views.
   `gui.multisite_results` owns stored group/element data projections and
   quantity definitions. `gui.result_export` serializes completed results;
   `gui.result_presentation` owns plotting and spectral controls.
7. `gui.calculation_controls.CalculationControls` collects widget inputs and
   controls workers; `gui.results.ResultsView` coordinates result widgets.
   `gui.project_io`,
   `project_configuration`, `project_session` and `project_collection` own saved
   results, editable inputs, per-run restoration and project collections.

Paths above are relative to `src/emcd_sim/`. There are no retired production
import aliases. GUI package placement is historical:
`forward_pipeline` and `propagation` are application
services, not alternate scientific engines. No backend framework is implied.
The planning/execution cycle is removed in
[Phase 3D-1](PHASE3D1_NUMERICAL_CHANNELING_DECOUPLING.md). Fresh-process tests
execute the canonical API for Ni and explicit synthetic Cr multisite cases in
all four BW/FFT Single/Double modes while rejecting Qt and presentation imports.
GUI-namespaced settings and service ownership remain a later migration concern.

## Inputs and their authoritative owners

The execution API is `gui.forward_pipeline.calculate(structure, settings, cfg,
sites=...)`. The caller supplies structure and geometry; a missing material
configuration or missing local assignment is an error. The explicit
`NiForwardSettings` preset and `study_presets.NickelStudyGeometry` remain outside
the engine. Source-backed configurations are built by `mdff_providers`;
`gui.material_inputs` retains only the saved record definitions and their
existing historical field identities. The provider services no longer reside
in `gui.provider_preparation` or `gui.provider_direction`. See the
[Phase 3B report](PHASE3B_HEADLESS_PROVIDER_SIMPLIFICATION.md) for the ownership
mapping and remaining settings-schema limitation.

| Input | Origin and calculation entry |
| --- | --- |
| Cell, positions, species, occupancy and site indices | ASE/CIF or an explicit preset → `gui.geometry.Structure` → `geometry`/`elastic_model`; all structural atoms contribute to the supplied elastic potential, including elastic-only groups. |
| Zone/target, basis mode and beam cutoff | `gui.geometry.Settings` → `CrystalOrientation`, finite hkl selection and `ProjectedGeometry`. The target fixes beam-frame x, not material M. Default settings describe the starting Ni example; the engine never constructs a default crystal or geometry. |
| Voltage and tilt | `Settings.voltage` in kV and `.tilt` in mrad → `Microscope`, relativistic wavelength/gamma, Hamiltonian/FFT kinetic phase, longitudinal transfer and post-loss exit energy. |
| Thickness | `Settings.thickness` in nm → incoming depth samples and outgoing propagation distances; Single multiplies its depth mean once, while Double response already integrates depth. |
| Elastic provider, B and potential cutoff | `Settings.elastic_provider`, `.b_factor` and `.potential_cutoff` → explicit per-species scattering factors, IAM structure factors and Fourier support. No material-specific propagation kernel is selected. |
| Declared atomic/XMCD source | `ProviderSettings.source`, exact checksum and `provider_declaration`, with the original source JSON/bytes → `load_provider` and its generator/converter. Embedded atomic parameters and acknowledged XMCD declarations are authoritative; unrelated inherited Ni compatibility fields do not become material inputs. |
| Imported or manual tensor | `ImportedSettings` and the validated source document → `ImportedMDFF`/`AnalyticalL23MDFF`. Tensor pairs, native edges, frames, coverage and source scale are explicit. |
| Legacy Ni material inputs | Explicit `NiForwardSettings`/`NiLocalConfig` → `HistoricalNiProvider` → common transition/tensor and propagation kernels. Direct Ni evaluation keeps its established requested-energy and amplitude policy; non-Ni use is rejected. |
| Local material/M assignments | `MultiSiteIonization.groups`, each group's provider reference, indices, multiplicity, frame and M → shared complete-crystal waves plus group-specific target tensors/site phases. `energy_windows` declares modeled coverage and never requests extrapolation. |
| Detectors | `cfg.centers`, `.radius`, `.halfwidth` in cycles/Å → `VirtualDetector`, the original reciprocal grid and fractional aperture weights. Material response and incident waves do not choose apertures. |
| Numerical sampling | Energy scope/grid/selection, angular grid/evaluation, depth count, subpixels, FFT grid and slice step → provider sampling and bounded application schedules. These retain existing defaults and supported choices; no probe/backend framework is introduced. |
| Resource request vs observation | Worker/memory modes and requested counts/budget enter existing admission/executor policy. `resource_allocation` records the resolved runtime allocation; it is not an additional physical input or a substitution for another run's request. |

Shared serialized request records still contain historical fields used for
complete project restoration. For declared providers, source documents and
acknowledged declarations determine physics; changing an unused legacy field
alone does not change that source. This distinction preserves the current
calculation and is not a new material model or calibration rule.

## Shared mathematical conventions

| Quantity | Convention and axes |
| --- | --- |
| Lattice | `Crystal.lattice_angstrom` has direct-cell vectors in rows, in Å; fractional atom positions are `(n_atom,3)` in the same ordered cell. No automatic primitive reduction. |
| Reciprocal coordinates | `g` and detector `q=(qx,qy)` are cycles/Å. `Q=2πq` is angular transfer in rad/Å. Fourier phases use `exp(+2πi g·r)`. The transfer kernel explicitly applies the conversion before its Coulomb denominator. |
| Frames | `gui.geometry.orientation` returns a proper real orthogonal matrix `R`, with crystal Cartesian vectors transformed as `v_beam=R v_crystal`; beam z follows the declared direct-lattice zone, and the reciprocal target fixes x. Lattice rows transform as `cell @ R.T`. |
| Tensor frame | For a local-to-crystal proper frame `A`, `T_crystal=A T_local A.T`, then `T_beam=R T_crystal R.T`. Transposes here are ordinary transposes because rotations are real. The dagger belongs to complex amplitudes and wave propagation. |
| Transition convention | `d_a=<initial|r_a|final>=∫Ψ_initial* r_a Ψ_final d³r`. `T_ab=Σ_n w_n d_na conj(d_nb) G(E−E_n)`. Forward excitation therefore uses conjugated material dipoles. |
| Array precision | Production NumPy arithmetic uses float64/complex128. Energy is the first axis of spectral tensors `(n_energy,3,3)`; the last axes are Cartesian x,y,z in the declared frame. |
| Spatial sampling | Depth is nm; momentum maps use `(ny,nx)` from `meshgrid(...,indexing='xy')`; intensity blocks use `(n_energy,n_pixel)` with flattened map order. Incoming amplitudes are `(n_depth,n_beam)` with explicit ordered hkl. |
| Longitudinal transfer | `q_z=−E_loss/(hc β)` in cycles/Å, from the incident velocity, frozen across branches at each loss. The outgoing electron energy is `1000*voltage_kV−E_loss` eV. No extra branch-dependent longitudinal correction is implemented. |
| Absolute scale | Length-gauge `d` is Å, `T` is Å²/eV, proper dipole `S` is 1/eV. `K=Q/Q²` has units Å and depth-integrated `R` has nm·Å². Intensities remain arbitrary units: no electron-count, density or absolute-cross-section calibration is supplied. XMCD-effective data additionally have an explicitly relative source scale. |

## Atomic ionization: from a core spinor to a material tensor

The current generalized generator is an independent-electron **2p→3d**, real
cubic `eg/t2g` model for explicitly declared Sc–Zn parameters. It is not a
band, multiplet, core-hole or general spinor electronic-structure solver.

| Physical step / equation | Actual implementation | Inputs, outputs and validation |
| --- | --- | --- |
| Core SOC coefficient `c=<1 m_l,½ m_s|j m_j>`, `m_l=m_j−m_s` | `atomic_dipole.core_spinor_amplitude` | Integer `two_j`, `two_mj`, `two_ms` encode half integers. `j=3/2` labels L3 and `j=1/2` L2; output is a real coefficient with the established Condon–Shortley phase. `test_atomic_ionization`, `test_part1c_refactor`. |
| Orbital angular coefficient `<2 m_f|n_q|1 m_i>=√(2/5) C(1 m_i,1 q|2 m_f)` | `_CG_P_TO_D`, `atomic_dipole.dipole_2p_to_3d` | Allowed spherical components `q=−1,0,+1`, orbital `m_f=−2…2`, spin conserved. The generator coherently combines pure `m` components using `cubic_orbital_coefficients`; it never adds their intensities before forming a real cubic orbital. |
| Radial length `r_pd=∫R_3d(r)R_2p(r)r³ dr` | `hydrogenic_radial_dipole_angstrom`, `radial_dipole_from_table` in `atomic_dipole` | Screened hydrogenic option uses normalized radial functions and `6! A_p A_d/β_r^7`, evaluated in log space. Tabulated inputs are full `R(r)`, not reduced `u(r)`, on the same Å grid; each is normalized with `∫R²r²dr`. The declared model ultimately receives one positive `radial_integral_angstrom`; no self-consistent radial state is inferred. |
| Cartesian amplitude: form `<final|r|core>` using `x=(n_−−n_+)/√2`, `y=i(n_−+n_+)/√2`, `z=n_0`, then conjugate | `atomic_dipole.dipole_2p_to_3d` | Returns `(3,)` complex Å in the atomic frame, satisfying the declared `<core|r|final>` convention. Core-SOC and orbital phases interfere inside each amplitude. Exact moved-algebra comparisons in `test_part1c_refactor`. |
| Hole weights and shifted losses `E_n=E_edge+c_orb Δ_CF−½ spin·sign(M) Δ_ex` | `atomic_ionization.transitions_for_material` | `AtomicMaterialParameters` comes from the explicit JSON/editor declaration; holes `(5,2)` use `ORBITALS` order and up/down columns. `c_orb=0.6` for `z2,x2_y2`, `−0.4` otherwise. Returns `TransitionDataset`: losses/weights `(n_transition,)`, dipoles `(n_transition,3)`, edge/site labels `(n_transition,)`. |
| Reversal | `transitions_for_material(...,magnetization_sign=−1)` | Swaps up/down hole weights **and** reverses exchange shifts in the fixed core-SOC basis. The declared frame rotates the entire cubic orbital/spin model. No independent spin-only rotation is claimed. The historical Ni adapter retains its established amplitude omission policy; generalized strict generation rejects unsupported nonzero tiny amplitudes. |
| Spectral broadening `Gσ(ΔE)=exp[−ΔE²/(2σ²)]/(√(2π)σ)` | `mdff_tensor.gaussian_broadening_ev` | `sigma_ev` is the Gaussian standard deviation, not FWHM. Widths are `(n_energy,n_transition)` in 1/eV. Finite displayed energy windows do not cause renormalization of truncated Gaussian tails. |
| Tensor `T_ab(E)=Σ_n w_n Gσ(E−E_n)d_na conj(d_nb)` | `mdff_tensor.dipole_tensor_from_transitions` | Optional edge/site filters select events before `einsum('en,na,nb->eab',weighted,d,d.conj())`. Returns `DipoleTensor` with `(n_energy,3,3)` complex Å²/eV. Positive weights give a Hermitian PSD Gram tensor. `test_mdff_tensor`, `test_atomic_ionization`, `test_part1c_refactor`. |

For one core state, the x/y/z amplitudes can be arranged mathematically as a
`3×10` matrix `D_core`: five up-spin and five down-spin final orbitals. With
diagonal hole/broadening weights `W(E)`,

```text
T(E) = Σ_core D_core W(E) D_core†
     = Σ_transition w_n(E) d_n d_n†.
```

**The implementation enumerates transitions; it does not store a 3×10 matrix.**
It omits zero-hole events and handles its existing amplitude threshold, then
forms the weighted outer products with the einsum above. This is the same
mathematics without changing the validated event order or accumulation method.
`export_atomic_parameters` embeds the original parameter bytes, provenance and
explicit reversal tensors; `validate_embedded_atomic` checks those claims on
import. The editor is an input builder, not a second scientific generator.

## Other material providers

| Provider and assumptions | Entry points and flow | Shapes, checks and reference tests |
| --- | --- | --- |
| XMCD-constrained axisymmetric tensor | `wien2k_xmcd.load_wien2k_xmcd` → `xmcd_effective_mdff.effective_tensor_from_xmcd`; explicit element declarations through `generalized_xmcd.export_declared_xmcd` | `N=(RP+LP)/2`, `D=(RP−LP)/2`; local tensor has `Txx=Tyy=N`, `Txy=+i ηD`, `Tyx=−i ηD`, `Tzz=βN`, with the established shared source-maximum normalization and declared reference scale. Reversal changes the odd XMCD term; both states share XAS. Proper rotations follow the frame table. `test_xmcd_effective_mdff`, `test_unified_mdff_providers`, `test_generalized_xmcd_atomic`. This is not reconstructed full DFT transition information or verified absolute handedness. |
| Manual constant tensor | `gui.mdff_usability.ManualTensorEditor.document` packages the user-entered matrix as an input declaration; `ImportedMDFF.load` validates the resulting provider | `T_plus(E)=A`, `T_minus(E)=conj(A)`, `T_even=Re(A)` over the explicitly declared interval. The editor checks a Hermitian PSD draft for feedback; the external provider boundary validates the complete declaration again. No peaks, material calibration or extrapolated tails are inferred. `test_mdff_usability`, `test_material_mdff_workflow`. |
| Manual spectral L2,3 tensor | `manual_l23.evaluate`, `.lorentzian`, `.AnalyticalL23MDFF.tensors`; `gui.manual_l23_editor` collects its parameters | `T(E)=Σ_edge L(E;E_edge,Γ_edge) A_edge`, where `L=(Γ/2)/[π((E−E_edge)²+(Γ/2)²)]` and Γ is FWHM in eV. Integrated Hermitian PSD strengths `A_edge` are relative Å²; `T` is Å²/eV. The profile integrates to one on the whole real energy axis; finite positive windows are not renormalized. Reversal conjugates the model-frame tensor before the same proper rotation. The provider evaluates the analytical profile at requested energies, preserving its difference from ordinary imported-grid interpolation. `test_manual_l23`, `test_material_mdff_workflow`. |
| Imported material tensor | `imported_mdff.ImportedMDFF.load`, `.tensors`; `mdff_providers.load_provider`, `load_site_group_provider` | Spectral `(n_energy,3,3)` pairs, strictly increasing native energies, source identity, schema/convention, real proper frames, Hermiticity/positivity and reversal claims are validated at the import boundary. Source interpolation stays inside declared coverage. `test_single_element_contracts`, `test_multisite_spectrum`. |
| Historical Ni | `historical_ni.NiLocalConfig`, `ni_local_transitions`, `tensors`; provider adapter from `mdff_providers.prepare_provider` | Retained supported Ni CLI/API and saved-project defaults. Shares atomic angular/radial algebra but preserves historical parameter and threshold policy. It must not substitute for an unavailable explicit source. `test_part1c_refactor`, `test_single_element_ni_compatibility`, `test_run_selection_restoration`. |

The constant row above describes the single-matrix synthetic model.
`gui.group_mdff` also offers an explicit constant pair: its `candidate` builder
retains independently entered Hermitian PSD matrices `T_plus=A`, `T_minus=B`,
with their declared full frame and coverage. It does not manufacture the other
state by conjugation in that mode. Both modes enter the same `ImportedMDFF`
validation/provider path. Arbitrary imported pairs likewise need not satisfy
`T_minus=conj(T_plus)`; the physical pair and its validity are source declarations.
See `test_group_direction_binding` and `test_multisite_single_channeling` for
real reversal-odd and noncollinear cases.

Material transition information (`TransitionDataset`) is distinct from its
dipole scattering representation (`DipoleTensor`/explicit imported pair).
Neither owns incident waves, elastic propagation or detector apertures.

## Elastic propagation and inelastic response

| Physical step / equation | Implementation | Inputs, output axes, validation and limitations |
| --- | --- | --- |
| IAM structure factor `F_G=Σ_s f_s(|G|) exp(−B_s |G|²/4) exp(−2πi h·u_s)` | `scattering.IndependentAtomPotential`, `FourierCutoffPotential`; `elastic_providers.factors_for_provider` | Full crystal species, fractional sites, occupancies, B in Å² and selected scattering provider; G is cycles/Å and `F_G` is Å. Adaptive Dirac/Padé and historical Ni/Lobato identities remain distinct. Cutoff and extinction checks are retained. `test_species_weighted_elastic`, `test_unified_elastic_acceptance`, `test_species_weighted_elastic`. |
| ZOLZ Hamiltonian `dψ/dz=iHψ`; `Hgg=−10πλ(|k⊥+g|²−|k⊥|²)`, `Hgh=10γλF_(g−h)/Ω` | `physical_elastic.PhysicalElasticModel.hamiltonian_nm_inv` | λ in Å, Ω in Å³, γ=`1+1000 kV/510998.95`; output `(n_beam,n_beam)` in nm⁻¹. Mean G=0 potential is omitted as a global phase; Hermitian nonabsorbing IAM only. `test_physical_elastic`, `test_physics_correction_engines`, `test_general_crystallography`. |
| Incident boundary and Bloch propagation `ψ(z)=V exp(iΛz)V† e_000` | `PhysicalElasticModel.amplitudes`; `double_channeling.BlochStates.ket`, `prepare_incoming_bloch` | Incident beam is one tilted plane wave: transmitted boundary coefficient one, all other retained beam coefficients zero. Tilt enters `Microscope.incident_k_xy=tilt_mrad·10⁻³/λ`; it is not a scanning probe. Eigenvalues are nm⁻¹; depths `(n_depth,)` produce `(n_depth,n_beam)` amplitudes. `test_physical_elastic`, `test_bloch_memory`. |
| FFT projected potential `U(x,y)=σ V_projected(x,y)` | `projected_potential.prepare_projected_potential`, `ProjectedPotential`; `projected_geometry.ProjectedGeometry` | `phase_nm_inv` and its FFT coefficients have transverse mesh axes `(ny,nx)`; 3D source-cell volume fixes density. G=0 phase is removed. This is a z-independent projected IAM, not atomically sliced 3D potential. `test_general_projected_equivalence`, `test_species_weighted_elastic`. |
| Symmetric split step `exp(iD dz/2) exp(iU dz) exp(iD dz/2)` | `multislice_double_channeling.FFTSplitStep`; `multislice_reference.fft_multislice_ni` | Real-space incident envelope is unity; Fourier coefficients use `fft2/N_pixel`, with no renormalization of selected-beam leakage. Tilt is in the kinetic operator. Negative dz supplies the adjoint; two-beam projected support is an explicit existing option. `test_general_projected_equivalence`, `test_ni_double_channeling_ms_validation`. |
| Incoming coherence `Cgg′=(1/t)∫ψ_g(z)conj(ψ_g′(z))dz` | `elastic.depth_coherence`, `multislice_reference.coherence_from_amplitudes` | `(n_depth,n_beam)` → `(n_beam,n_beam)` complex Hermitian depth mean. Existing trapezoidal depth integration is preserved. `test_single_channeling_tensor`, `test_multisite_single_channeling`. |
| Single Channeling localized events | `single_channeling_tensor._tensor_angular_maps`, `run_tensor_with_coherence`; `multisite_single_channeling.run_multisite_with_coherence` | Incoming C, tensor, site-pair phase `mean_s exp(+2πi(h−h′)·u_s)` and `Q=(2π(qx−gx),2π(qy−gy),2πqz)`. The kernel uses reversed tensor indices in the MDFF and divides by `Q_g² Q_g′²`. Multiply the depth mean by t once; outgoing wave is free. Independent transition-amplitude tests and `test_single_channeling_tensor`. |
| Post-loss reciprocal exit wave | `double_channeling.outgoing_elastic`, `BlochStates.ket`; `multislice_double_channeling.incident_fields` and Double response routines | Outgoing carrier is incident transverse carrier plus detector q. Its energy is E0−loss; reciprocal ket is `U_out(z−t)e_000`, conjugated to obtain the forward detector bra. Incoming and outgoing eigensystems are solved separately. `test_double_channeling_foundation`, `test_physics_correction_engines`. |
| Event coupling `K_gh,a=(Q_gh,a/Q_gh²) exp[+2πi(h−h_out)·u_s]` | `double_channeling` and `multislice_double_channeling` response routines; `equivalent_site_phases` | Q is angular transfer formed from detector minus incoming/outgoing beam difference and qz. The site factor is `exp(−i Q·R)` after removing its common detector/longitudinal phase. Coherent elastic paths interfere **inside** each localized site/depth event; distinct ionizations add intensities. Coulomb factors belong to this coupling, not the material MDFF. `test_physics_matrix_audit`, `test_multisite_double_channeling`. |
| Double response `R_ab=mean_s ∫v_a(z)conj(v_b(z))dz`, `v_a=Σ_gh ψ_g bra_h K_gh,a` | `double_channeling.depth_response`, `double_channeling_response`, `double_channeling_group_responses`; FFT counterparts in `multislice_double_channeling` | Output `(n_pixel,3,3)` complex Hermitian PSD. Numerical depth integration remains independent of the analytic mode-pair formula. For real mode frequencies, `Jmn=t exp[i(ωm−ωn)t/2] sinc[(ωm−ωn)t/(2π)]`; this assumes Hermitian propagation. No extra t after forming R. `test_double_channeling_foundation`, `test_multisite_ms_double_channeling`. |
| Corrected contraction `I=Re Tr(R T)=Re Σ_ab R_ab T_ba` | `double_channeling.intensities_from_response`, `contract_cartesian`; FFT transition modes use conjugated material modes | Material pair and wave response are separate. A magnetic imaginary antisymmetric tensor makes the index reversal observable; ordinary same-index multiplication has a different sign. `test_physics_correction_engines`, `test_single_channeling_tensor`, `test_physics_source_guard`. The strict kernel/source pins are retained. |
| Multisite aggregation `I_total=(Σ_g n_g I_g)/(Σ_selected n_g)` | `multisite_single_channeling`, `multisite_double_channeling`, `multisite_spectrum`; scheduling in `gui.multisite_integration` | Each group is a mean per group atom. `weighted_sum` preserves the unnormalized selected-atom sum; results also retain group means. Excluded/window-omitted groups follow explicit recorded denominator rules. Complete-crystal elastic propagation is shared. No cross-provider rescaling or inter-site coherent target excitation is introduced. `test_multisite_numerical_validation`, `test_multisite_scientific_validation`, `test_multisite_spectrum`. |

The independent numerical depth path, elastic FFT reference, accepted historical
sources and native acceptance entry points are retained. Agreement of two
production backends alone is not independent scientific validation.

## Detector observables, persistence and restoration

For fixed fractional aperture weights `w_d[y,x]` from
`geometry.VirtualDetector.integration_weights`, integration is
`I_d(E)=Σ_yx w_d[y,x] I(E,y,x) Δqx Δqy`. Current maps use a square grid, so the
code uses `dq²`. Boundary subpixel sampling estimates fractional pixel area;
weights are identical for both reversal states and all energies. Detector-only
evaluation removes exactly zero-weight pixels, then restores zeros into the
original full grid before the established sum. No interpolation is introduced.
See `detector_signals.integrate_detector_block`, `gui.channeling` and
`test_energy_angular_schedule`, `test_multisite_forward`, `test_sampling_workflow`.

```text
N_d = (I_d_plus + I_d_minus)/2       M_d = (I_d_plus − I_d_minus)/2
D_mag = M_A − M_B                  D_nonmag = N_A − N_B
D_raw = I_A_plus − I_B_plus        Sigma_ref = N_A + N_B
D_raw = D_mag + D_nonmag
```

`detector_signals.reversal_components` owns these algebraic derived fields.
`gui.forward_results.assemble_forward_result` retains the parity assertion,
paired-map diagnostics, source revalidation and existing metadata.
`gui.component_display` reports signed component percentages
`100 D_component/Sigma_ref` with its existing denominator-floor policy.
The separate PRB observable is `100 (I_A_plus−I_B_plus)/(I_A_plus+I_B_plus)`.
These denominators are distinct. `xmcd_postedge_normalization.analyze_postedge_spectra`
optionally obtains `alpha=∫window I_A_plus/∫window I_B_plus` and the existing
observed post-edge correction; corrected detector contrast is not intrinsically
magnetic. No normalization is added to saved arrays.

`gui.project_io` retains schema-1 numeric structure snapshots, NPZ arrays,
checksums and source provenance; `runtime.build_info` supplies source/binary
identity. `project_configuration` validates editable configurations, while
`project_session` captures/restores each run's own configuration and handles
project actions. Result selection, View Results, import and opening a project
must use that same restoration path. A comparison selection restores no
arbitrary run. Missing or changed sources leave arrays viewable and block
reruns; incomplete historical settings remain explicitly unavailable.

Material magnetization belongs to Material/site groups. MDFF target directions
remain read-only derived displays. Restoration must not start a solver or
numerical preview and must preserve saved arrays exactly. Behavioral coverage:
`test_run_selection_restoration`, `test_project_workflow`,
`test_multisite_configuration`, `test_multisite_result_persistence`,
`test_group_mdff_native_controls`, `test_local_mdff_workflow` and
`test_material_mdff_workflow`.

## Present limits

The calculation uses a periodic crystal, finite oriented ZOLZ elastic support,
projected nonabsorbing IAM, one incident plane wave and localized single
ionization. Double Channeling adds outgoing elastic propagation, not multiple
inelastic events. Existing energy windows, finite FFT meshes and depth grids
need configuration-specific convergence. No new depth-dependent 3D potential,
scanning probe, absorption/TDS, full momentum-dependent target MDFF, band
structure, multiplets, absolute calibration or future physics is implemented by
the readability refactor. Possible physics issues discovered during mapping
must be reported separately rather than corrected inside a refactor.
