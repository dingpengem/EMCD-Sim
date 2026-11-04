# Generalized single-element EELS/EMCD development contract

Development baseline: main `2f9c130099dce5df4e4609b521c42f53c5385518` (v0.8.0 Windows release remains unchanged). This feature is local and unpublished. No version bump, package, push or release is implied.

## Architecture audit before implementation

- `gui/emcd_forward.py`: conventional FCC Ni gate, Ni benchmark container, Ni XMCD source and L3/L2 selections, Ni atomic parameters; tensor reversal requires complex conjugation. Keep this historical route unchanged. Its arithmetic/parity/project metadata implementation can be reused after supplying independently validated tensors and a generic simulation container.
- `single_channeling_tensor.py`: Cartesian contraction is already general and uses the corrected transposed tensor. `fcc_site_phase_matrix` is Ni-gated but reads actual positions; preserve it and provide an explicit generic phase matrix for the new route.
- `double_channeling.py`: coherent incoming/outgoing amplitudes, post-loss propagation, Coulomb kernel and depth integration are general. Site selection is Ni-gated. Add only an opt-in validated site argument; retain the complete historical default branch.
- `multislice_double_channeling.py`: projected elastic propagation is generic (`ProjectedNiFFT` is a historical alias). Site phases already use actual fractional positions, but need explicit validated site selection. Preserve transition conjugation, quadrature and event accumulation.
- `gui/channeling.py`: calls the Ni phase function and both existing Double kernels. Thread the explicit site object into these calls; preserve the default path and detector reduction order.
- `mdff_tensor.py`: reusable Hermitian tensor and transition Gram algebra. PSD is checked at the imported-provider boundary as well as kernel contraction. Do not change this implementation.
- `ni_local_mdff.py`: shared angular mathematics is mixed with explicitly Ni-specific occupations, radial charges, broadening and edge energies. Preserve every Ni default and function. A separate material-parameter interface will reuse these angular functions without inventing non-Ni parameters.
- `gui/stage_b.py`, `propagation.py`: conservative Ni source/material/preflight gates. Add an explicit imported-provider route; keep the Ni gate for legacy XMCD/atomic providers. The import must validate source identity, element, edge, magnetic state and equivalent sites before enabling calculation.
- `project_io.py`, `results_browser.py`, `results.py`: retain old config defaults and read-only saved arrays. New config/source metadata must survive save/open; missing external sources block rerunning, never viewing. Labels must distinguish synthetic/imported tensors from Ni atomic and XMCD models.

## Invariants and intended implementation

Keep `I=Re sum_ab R_ab T_ba`, `T=L L†`, conjugated forward transition modes, angular `Q=2*pi*g`, the existing Coulomb denominators, reduced-energy outgoing propagation, depth quadrature, cancellation/resource guards and fixed-detector raw parity. No IAM provider or default changes.

Use a validated `IonizationSites` object built from actual single-element full-occupancy coordinates. Conservatively certify equivalence through translations preserving the entire decorated periodic cell. Rotation-related sites needing different tensor frames and any detected inequivalent sites are rejected. This deliberately supports conventional/primitive Bravais crystals, not an unsupported assumption that every same-element site shares a spectrum. Selection is explicit; intensity is the **mean per selected equivalent atom**, preserving historical Ni normalization. It is not a per-cell atom-count factor.

Available ASE initial moments/charges must be uniform over the complete cell; selecting one atom does not bypass AFM, mixed-charge or other inequivalent-site rejection. Explicit vector moments must align with the declared crystal +M axis. Positive collinear scalar moments are interpreted along that declared axis; negative collinear signs and nonmagnetic tensors conflicting with nonzero structure moments are rejected. These starting annotations are recorded, not used as fabricated transition strengths. A CIF is a geometric source, not an automatic magnetic-structure determination; magnetic-CIF/AFM inference is not implemented.

Single-site interference uses `P_ij=mean_s exp(+2*pi*i*(g_i-g_j).u_s)`. Double uses `K_gh,s=K_gh exp(+2*pi*i*(g-h).u_s)`, then averages event **intensities/responses**, never site amplitudes. A common detector/longitudinal phase cancels within each localized event. Elastic propagation continues to use the complete cell.

As in the original Ni model, events use continuous uniform depth density and projected/ZOLZ site phases. This is not a discrete atomic-layer/finite-surface event model. Primitive/conventional-cell comparisons refer to the same periodic projected model, not different physical surface terminations.

Imported tensors declare element, L2,3 edge/selected energies, positive increasing energy axis, units, normalization, Cartesian/local basis, proper frame rotation, source/provenance, synthetic/physical status, validity assumptions and magnetic orientation. Nonmagnetic data supply one time-reversal-even tensor. Uniform FM supplies two independently given PSD tensors and an explicit shared-even tensor, checked against their mean. Never infer a missing state by conjugation. Arbitrary Hermitian odd components are allowed under the declared pair; no Ni-specific imaginary-only symmetry is imposed. Interpolation is piecewise linear (convex PSD interpolation), without extrapolation or repair/clipping.

No trustworthy Fe-specific MDFF dataset was supplied. BCC Fe demonstrations therefore use an original, explicitly synthetic PSD pair and establish software/numerical checks only. Physically sourced tensors require their own provenance and independent scientific validation; importing a file is not that validation. Co/Cr atomic parameters and AFM/SDW are unsupported.

Historical source manifests and snapshots remain immutable. Any source guards affected by the explicit site interface will gain a separately pinned extension record and a check that removing only that reviewed interface reconstructs the original default kernel exactly. Protected Ni fixtures and archived outputs are not regenerated or relabeled.

## Import schema and source API

`ImportedMDFF.load(path, expected_sha256='')` reads UTF-8 JSON, never Python/pickle. The exact file-byte SHA256 is computed at import, recorded in settings/projects, rechecked before running and checked again before accepting a completed result. A file cannot contain its own complete-byte hash; that identity lives in project provenance. A valid import needs:

Real and imaginary components must each have the complete `(n_energy,3,3)` shape; scalar or missing-energy-axis broadcasting is rejected. Element-specific XMCD conversion reads its declared input bytes once, hashes that snapshot, and evaluates both states from a private copy. Replacing the original path during conversion cannot change either tensor or mislabel its source digest. Original source/validity declarations must be nonempty before generated explanatory text is appended.

|Field|Required value/meaning|
|---|---|
|`schema`, `element`, `edge`|`1`, an ASE periodic-table symbol with filled 2p core (Z>=10), `L2,3`|
|`energy_ev`|Finite positive strictly increasing eV samples; no automatic energy shift|
|`selected_ev`|Explicit `L3` and `L2` selections inside coverage, in that order|
|`units`, `normalization`|`angstrom^2/eV`, `per_atom_relative`; not a calibrated cross section|
|`basis`|`crystal_cartesian` or `declared_local`|
|`frame_to_crystal`|Proper orthonormal 3x3 rotation; identity for crystal Cartesian input|
|`convention`|`d=<i|r|f>;T=d*d_dagger;I=ReTr(RT);angular_Q=2*pi*g`|
|`source`, `validity`|Nonempty provenance and explicit model/validity assumptions|
|`status`|`synthetic` or `physical_source_unvalidated`; importing cannot assign VALIDATED|
|`magnetization_crystal`|Finite nonzero crystal Cartesian +M axis, or nonmagnetic reference axis|
|`magnetic_state`, `reversal`|`nonmagnetic` / `identical_nonmagnetic`, or `uniform_fm` / `explicit_pair_shared_even`|
|Tensor arrays|Each is an object with `real` and `imag` arrays shaped `(n_energy,3,3)`|

Nonmagnetic data require `T`, real symmetric under the declared time-reversal-invariant electric-dipole assumption. Uniform-FM data require **all three** `T_plus`, `T_minus`, `T_even`; neither magnetic state is manufactured. Hermiticity/PSD checks use explicit numerical tolerances, including a relative spectral-scale Hermiticity check for very small amplitudes. No eigenvalue clipping or tensor repair occurs. `T_even` must equal the average of the supplied states. This permits real as well as imaginary magnetic-odd terms, without imposing Ni conjugation symmetry. A declared proper frame is applied as `A=R_crystal_to_microscope @ frame_to_crystal`, `T_microscope=A T_source A^T`.

The original Ni `gui.emcd_forward.calculate` remains Ni-specific. The opt-in API is:

```python
from emcd_sim.gui.generalized_forward import settings_for_source, calculate
cfg = settings_for_source("my_declared_tensor.json", energy_scope="edges",
                          site_indices=(0, 1), grid=17, depth=17)
result = calculate(imported_structure, microscope_settings, cfg)
```

`microscope_settings` and `imported_structure` are existing `Settings`/`Structure` objects. The complete structure determines the unchanged IAM elastic potential. Site indices must refer to actual imported ASE atom ordering. The default `site_indices=None` means an explicit recorded selection of all certified equivalent sites. The mean is over selected sites; it never adds a hidden per-cell multiplicity or absorption factor. The selected subset does not bypass rejection of other inequivalent sites in the crystal. The initial certification limit is 256 explicit sites.

Selecting a different magnetic axis for an anisotropic imported tensor is rejected; supply a new source with the appropriate physical tensor/frame declaration. This prevents treating arbitrary anisotropy as an axisymmetric tensor. A physical source's declaration is checked for internal consistency, not independently authenticated as a true Fe calculation. This distinction is retained in result status.

The GUI adds a third MDFF provider panel with source, element, edge, state, site selection and explicit acknowledgement. Use **Manual** numerical settings: historical Ni automatic presets are not transferred to another material. The current side-by-side layout and Results layout are retained. Imported/synthetic plots and browser entries carry the correct element/status. A missing/changed source blocks rerun while leaving checksummed saved arrays viewable. Old projects restore their original Ni provider; no migration is performed.

`ImportedSettings` inherits the legacy serialization envelope. `atomic`, `sigma`, `radial`, `eta` and `beta` remain serialized for compatibility but are explicitly recorded as **unused** for imported tensors. Their Ni defaults are not applied to Fe. L3/L2 selections, axis, state and normalization come exclusively from the validated source. Post-edge correction defaults off for imports; it is an optional processing diagnostic, not an intrinsic magnetic signal.

## Element-specific XMCD and atomic subphase

`generalized_xmcd.export_declared_xmcd` reuses the unchanged five-column reader and effective-tensor algebra. It requires element/edge, source SHA256, native selected energies, RP-minus-LP handedness, crystal magnetic axis, eta/beta, source-maximum normalization, an explicit positive **relative reference tensor amplitude in angstrom²/eV**, corrected tensor convention, provenance/status, uniform FM and the `axisymmetric_XMCD_odd_shared_XAS` reversal assumption. There are no Fe spectral energies, occupations or radial defaults. The exported explicit pair records these assumptions and the original source checksum. This model is an axisymmetric approximation; arbitrary-crystal anisotropy may be missing, and it is not a complete DFT MDFF or an absolute transition-strength calibration.

`atomic_ionization.py` exposes the existing core SOC/Clebsch–Gordan/complex dipole, cubic-orbital, radial-integral and broadening mathematics through shared names. `AtomicMaterialParameters` requires every material field explicitly; generalized spectra remain disabled. The Ni source implementation and `NiLocalConfig` defaults are byte-for-byte unchanged. Spin-hole/exchange/material-specific spectroscopy is not invented for Fe, Co or Cr.

Remaining approximations include dipole-only response, projected neutral IAM, finite ZOLZ/basis/cutoffs, branch-frozen longitudinal momentum transfer, relative intensity, no experimental cross-section or absolute handedness calibration, no AFM/ferrimagnetic/SDW structure and no multi-element/site-resolved MDFF. The original [Fe EMCD literature](https://www.nature.com/articles/ncomms4138) motivates comparisons but is not substituted for a machine-readable, declared complex BCC-Fe tensor pair. No such dataset was obtained for this milestone. The [available ferrite data record](https://opara.zih.tu-dresden.de/items/238057cb-5b19-4de5-999a-439fe77f093f) concerns a different material/magnetic structure and is not adopted as uniform-FM BCC Fe.
