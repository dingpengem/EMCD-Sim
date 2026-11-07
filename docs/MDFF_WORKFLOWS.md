# MDFF construction, preview, and projects

[Home](../README.md) | [Installation](INSTALL_WINDOWS.md) | [Quick Start](QUICK_START.md) | [User manual](USER_GUIDE.md)

This guide describes the **Configure MDFF...** dialog shipped in [v0.8.1-beta.2](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.8.1-beta.2). The published beta.1 interface is older; use its tag-specific documentation for that binary. See [release status and validation history](RELEASE_NOTES_0_8_1_BETA_2.md#publication-status) for the beta.2 package and its recorded verification.

## Choose a construction method

The normal choices are **XMCD-constrained MDFF**, **Atomic Ionization MDFF**, and **Manual tensor**. They construct a spectral complex 3x3 dipole tensor; propagation and detector contraction remain shared. Elastic Bloch-wave or FFT Multislice, and Single or Double Channeling, are separate choices.

| Method | Required input | Meaning and principal limitation |
| --- | --- | --- |
| XMCD-constrained | Compatible five-column XAS/XMCD data; native edge selections; magnetic/convention declarations; material provenance and relative reference scale outside historical Ni. | Axisymmetric effective dipole response constrained by intensities, not full complex DFT transitions or measured longitudinal response. |
| Atomic Ionization | Sc-Zn element; L2,3 references; cubic/exchange parameters; spin-resolved holes; radial input; proper frame, broadening, grid, and source assumptions. | Independent-electron cubic 2p-to-3d model, not bands, multiplets, or quantitative material calibration. |
| Manual: constant | All nine complex matrix entries, selections, element, direction/frame, and required declarations. | Energy-independent spectral density across its declared window; selecting L3/L2 does not create peaks. |
| Manual: L2,3 Lorentzian spectrum | Separate L3/L2 energies, FWHM widths, and integrated Hermitian PSD strength matrices; frame and energy window/grid. | Phenomenological two-edge spectrum, with no imposed material-specific branching ratio or magnetic-moment interpretation. |
| Advanced imported exchange | Compatible tensor JSON with its declared frame, units, element/edge, magnetic state, explicit reversal information, and provenance. | Reuses the supplied data and existing validation; does not infer missing states, extrapolate energies, or convert arbitrary DFT output. |

All physical tensors must be finite, Hermitian, and positive semidefinite (PSD). Invalid inputs are rejected rather than symmetrized, clipped, or projected to an allowed matrix. A signed magnetic-odd component need not be PSD; that does not relax the physical-state checks. The contraction convention remains `I = Re Tr(R T)`. Off-diagonal entries alone do not define magnetic oddness.

## Structure, element, edge, and frame

Open your CIF before choosing material-specific input. Structure identity, eligibility of an ionizing element, and availability of a model are separate questions. Calculations support the implemented fully occupied single-element/equivalent-site case; a mixed-material preparation selector is not a multi-element sum. Inequivalent-site, AFM/SDW, noncollinear texture, and general complex magnetic structures are not supplied by this editor.

Atomic generation is Sc-Zn **L2,3 only**. Declared/imported dipole providers also implement the supported **K** edge route with native selections and data appropriate to the declared element. Other edge names require implementation, not merely typing a label. Do not transfer Ni spectra, energies, radial values, or electronic parameters to a different material.

Magnetization is a crystal Cartesian direction, not automatically the beam or surface normal. Local-to-crystal frames must be proper rotations. Atomic and manual editors expose direction/frame information; in explicit-frame mode the derived direction is read-only. Refer to [orientation and tensor definitions](MDFF_TENSOR.md) and [units](PHYSICAL_UNITS.md).

## XMCD-constrained MDFF

### Input and construction

Select the source once in **Five-column XMCD** and click **Validate source / native features**. The supported text columns are energy in eV, RP, LP, RP-LP, and RP+LP. The loader checks finite values, the native energy grid and redundant columns. Validation reports source identity and native coverage. No energy shift or extrapolation is introduced.

For the declared axis, define `N=(RP+LP)/2` and `D=(RP-LP)/2`. The effective tensor has transverse diagonal entries N, `Txy=+i*eta*D`, `Tyx=-i*eta*D`, and longitudinal entry `beta*N`, before its declared rotation and relative reference scaling. The model normalizes against the source maximum nonmagnetic response. It assumes an axisymmetric response; XMCD does not determine a full phase-resolved tensor or finite-momentum multipoles.

| Parameter | Units/default | Meaning |
| --- | --- | --- |
| L3/L2 native features, or explicit K selection | eV; source validation can propose L3/L2 values | Samples of the native source, not experimentally calibrated thresholds. |
| `eta` | Dimensionless; 1 | Dichroic sign/scale in the declared RP-minus-LP convention. |
| `beta` | Dimensionless; 1 | Assumed longitudinal/nonmagnetic ratio; not measured by this input. |
| Reference tensor scale | Relative Angstrom squared/eV; explicit for generalized declarations | Supplies the declared relative density scale, not absolute cross-section calibration. |
| Magnetic axis and handedness | Crystal Cartesian direction and explicit convention | Must agree with source interpretation; reversal shares the assumed XAS and changes the odd response. |
| Provenance, assumptions, status | Required declarations where applicable | Distinguish a synthetic demonstration from a physical source that is still unvalidated. |

The source/provider checks enforce the physical positivity conditions, including a nonnegative longitudinal response and allowable dichroic weight. A numerical fit is not a license to violate them.

### Ambiguous input and explicit selections

An ambiguous source does not acquire edge assignments merely because controls already contain numbers. Explicitly edit **both** L3 and L2 controls, or enter their existing JSON selection input, for example `{"L3":710,"L2":723}`. Selecting just L3 leaves L2 undeclared. New source selection clears previous choices; revalidating unchanged source bytes can retain valid explicit choices.

For L2,3, JSON entry initializes the visible energy controls. Subsequent genuine control edits remain authoritative, including after reopening a verified project; old JSON text cannot silently override them. For K, use the corresponding explicit selection JSON. A value must be ordered correctly and within the source's native range. **710/723 eV is an explicit Fe-labelled software example here, not a generally validated Fe calibration.**

Review **Advanced source declarations** when using a source outside the historical Ni workflow. Confirm element/edge, source, assumptions, scale, and status; acknowledge axis, RP/LP convention, and edge assignment only when appropriate. Default Ni input cannot execute as Fe simply by changing its label.

### Preview and calculation

**Update preview** shows original input columns and provider-generated tensor components in crystal coordinates. Select +M, -M, reversal, even/odd, tensor component, and real/imaginary view. Source/declaration/energy changes mark a previous snapshot stale. Preview does not open a second source chooser and does not calculate detector EELS. Calculation uses the same declared provider and selections. See [effective XMCD scope](WIEN2K_XMCD_MDFF_ROADMAP.md) for what the input cannot establish.

## Atomic Ionization editor

The basic panel exposes element, L3/L2 references, Gaussian sigma, and crystal magnetization. Advanced controls provide electronic, radial, frame, grid, and provenance parameters. Per-parameter help explains units and origin; **Reset defaults** changes the active element's draft. Changing elements does not authorize another element's previous source.

| Input | Units and current starting choice | Interpretation |
| --- | --- | --- |
| L3/L2 reference | eV; pinned elemental xraylib subset where supported | Elemental absorption-edge reference, not a chemical-shift prediction or fitted EELS maximum. Fe tabulated starts are 708.1/721.1 eV. |
| Cubic splitting, 10Dq | eV; 0 | `eg` shift +0.6*10Dq and `t2g` shift -0.4*10Dq about the weighted centroid. |
| Exchange splitting | eV; 0.5 | Effective independent-electron spin splitting, not total exchange energy or a magnetic moment. |
| Spin-resolved holes | Dimensionless per orbital/spin, 0..1; five rows initially [0.2,0.4] | Unoccupied weights in the declared real cubic orbital/spin basis, not electron populations or density plots. |
| Radial dipole integral D | Angstrom; synthetic 1 | Multiplies transition amplitudes; intensity scales with D squared. Requires a radial source/assumption. |
| Gaussian sigma | eV; 1 | Standard deviation; FWHM = `2*sqrt(2*ln(2))*sigma`. Not an inferred experimental resolution. |
| Frame | Proper rigid rotation; identity starting frame | Rotates the complete orbital/spin frame; no arbitrary reflection or noncollinear texture. |
| Source energy grid | Positive eV, explicit or numerical starting grid | When initialized from references: 10 eV margins and 201 samples. Review range/resolution; these are not convergence certificates. |
| Electronic provenance/status | Synthetic default | Generic examples are not inferred from CIF chemistry, oxidation state, or magnetic moments. |

Construction combines the existing core 2p SOC/angular dipoles, radial amplitude, explicit nonnegative hole weights, cubic/exchange energy shifts, and normalized Gaussian broadening. It constructs both magnetic states, with spectral density in relative per-atom Angstrom squared/eV. Element-dependent defaults do not establish quantitative comparisons between independently prepared materials.

**Update numerical preview** prepares the current explicit parameters and displays generator output; the nearby transition drawing is a schematic. Detailed components/reversal views use the actual tensor. Editing invalidates old validation. A pending external parameter import must be validated; failed validation cannot silently execute an old editor source. Complete parameter JSON can be imported/exported, and editor-managed source bytes and metadata support portable completed projects. See the [detailed parameter reference](ATOMIC_PARAMETER_EDITOR.md), whose original implementation-era acceptance statements remain historical.

## Manual tensors and advanced exchange

### Constant tensor

Edit all nine cells independently using real numbers or complex `i`/`j` notation. The starting density is `I/3`: trace one, constant across `[L3-10,L2+10]` eV. Initial 708.1/721.1 eV selections are Fe examples and must be reviewed for your element. A selection locates evaluation energy; it does not add an absorption peak. Numerical component plots and real/imaginary heatmaps show the actual validated density.

### L2,3 Lorentzian spectrum

The spectral model is `T(E)=f3(E)*T_L3 + f2(E)*T_L2`, with independent integrated-strength matrices. Each profile is

`f_j(E) = (Gamma_j/2) / (pi*((E-E_j)^2 + (Gamma_j/2)^2))`.

Gamma is **FWHM in eV**, not the Atomic model's Gaussian sigma. Each profile integrates to one on the full real axis. The finite window omits tails and is **not renormalized**; the retained fraction is displayed. Integrated strengths are relative per-atom Angstrom squared; the generated density is per eV.

Simple mode uses `N_perp=A`, `N_parallel=A*r`, `M=A*p`, and `Txy=+i*M`, with `A>=0`, `r>=0`, and `abs(p)<=1`. A is transverse strength, not trace; trace is `A*(2+r)`. Full mode retains arbitrary valid matrices when that simple form cannot represent them.

Starting widths are 1 eV, A = r = 1 for both edges, p = 0.1 for L3 and -0.05 for L2. Energies use the elemental reference when available; a missing reference yields an explicitly labeled synthetic estimate for that element. The starting frame/direction is identity/+z, grid 401 points, and window 25 eV beyond each reference. These are demonstrations, not measured widths, sign relations, or branching ratios. There is no imposed magnetic-moment interpretation. See [full model definitions](MANUAL_L23_TENSOR_MODEL.md).

This manual spectral model explicitly constructs `T_minus = conjugate(T_plus)` in its fixed model frame, then applies the same real proper rotation to both states. That is a declared phenomenological reversal assumption, not a general reconstruction rule for imported data or arbitrary magnetic materials.

### Imported exchange

Advanced source exchange retains compatible imported tensors and declarations. Constant-model convenience reversal assumptions do not waive the general importer's explicit state/pair requirements. Keep energy coverage, source/frame, element/edge, units, magnetic state, and reversal declarations consistent. Nothing here constructs missing core-to-band phases from a spectrum or runs WIEN2k/DFT for you.

## Worked example: synthetic Fe from existing inputs

This example exercises software behavior, not scientific Fe accuracy. It requires no existing project JSON and no private research data.

1. Open the supplied `Fe_BCC_a2.8665.cif` (`_internal/examples` in the development binary; `packaging/assets/examples` in source).
2. Set nominal zone **0 0 1**, target **1 1 0**, and apply orientation/target. Set **200 kV**, **0.2 nm**, and tilts **-5, +7 mrad**. Restore Thales detectors after setting the geometry.
3. In **Configure MDFF...**, choose **Atomic Ionization MDFF** and import the complete existing `synthetic_fe_atomic_parameters.json` through the editor's import action. It is under `_internal/examples` in the beta.2 Windows package and [docs/examples](examples/synthetic_fe_atomic_parameters.json) in source. Confirm draft replacement if prompted. Its explicit references are **710/723 eV**; retain its synthetic provenance and remaining complete parameters.
4. Use **Update numerical preview**. Confirm Fe, synthetic status, and current numerical tensor output. A schematic alone does not establish successful generation.
5. Choose **Single Channeling**, **Bloch-wave**, and **Numerical Settings > Manual (Advanced)**. Use beam cutoff **0.6 inverse Angstrom**, potential cutoff **1.2 inverse Angstrom**, odd angular grid **9**, depth nodes **5**, aperture subpixels **4**, map halfwidth **0.7 inverse Angstrom**, and requested workers **1** in Manual worker mode. Use selected declared edge samples for a short run. These are coarse demonstration settings, not a convergence result or full EELS spectrum.
6. Run **EMCD / EELS**. Inspect L3/L2 maps and the two selected detector samples. Do not call two points a resolved white-line spectrum.
7. Use **File > Save Project**, choose a writable parent and new folder name, and let the application create its project JSON and arrays. Close the application, relaunch, open that complete folder, and select **Use These Settings**. Update preview and rerun the small case. Preserve the original inputs and complete project folder.

For an XMCD workflow without manufacturing Fe data, use **File > New**, choose XMCD, retain the bundled Ni source, validate, and use the Ni [Quick Start](QUICK_START.md). A material-specific Fe XMCD calculation requires your own suitable five-column Fe source and declarations. The repository's synthetic test spectra establish software behavior, not an experimental Fe reference library; the public binary does not promise to ship all test fixtures.

## Persistence and scientific interpretation

Model switches preserve the implemented drafts and display choices. Numerical snapshots become stale when relevant input changes. Completed projects retain model/settings, source identity, structure, and arrays; **Use These Settings** restores executable settings only when required sources verify. Keep external XMCD files and original imported data; portable editor attachments do not imply universal embedding of external inputs.

The convention, existing kernel/reference safeguards, and old numerical arrays remain meaningful. Historical saved Atomic settings use their compatibility route rather than being overwritten by new generic defaults. Opening old data does not revalidate its physics. Follow [project management](USER_GUIDE.md#project-management), [scientific limitations](USER_GUIDE.md#scientific-limitations-and-responsible-interpretation), and [existing theory references](PHYSICS.md#references-and-historical-records).
