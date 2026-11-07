# Manual L2,3 spectral tensor

Implemented in `C:\Users\peng863\EMCD-Sim\build\mdff-usability`, continuing the existing redesign and XMCD preview restoration. No commit, merge, EXE build, push, version change, tag or release occurred.

## Physical convention

`T(E) = f3(E) T_L3 + f2(E) T_L2`, with independent Hermitian PSD integrated strength matrices and Lorentzian profiles

`f_j(E) = (Γ_j/2) / [π ((E−E_j)^2 + (Γ_j/2)^2)]`.

Γ is FWHM, not Gaussian sigma. Each profile integrates to one on the full real energy axis. The implementation uses an algebraically equivalent scaled expression to avoid squaring extreme widths. Finite positive windows omit tails, including the mathematical negative-energy tail; they are **never renormalized**. The exact retained fraction is displayed using the arctangent integral.

Integrated matrices have relative per-atom Å² units; the solver receives spectral density in relative per-atom Å²/eV. The simple model-frame mapping is `N_perp=A`, `N_parallel=Ar`, `M=Ap`, with `Txy=+iM`, `A>=0`, `r>=0`, `|p|<=1`. The integrated trace is `A(2+r)`; A is not trace or total isotropic intensity. Both edges' energies, widths, A, r and signed p are independent. There is no imposed branching ratio, sign relation or magnetic-moment interpretation.

The existing `d=<i|r|f>; T=d*d_dagger; I=ReTr(RT)` convention is preserved. The unchanged solver consumes the density once, with no extra profile, radial factor, trace normalization or Gaussian broadening. Existing application display/reference-intensity normalization stays separate. The old constant `I/3` example is a density with trace one throughout its window, not an integrated edge matrix; it is never silently converted.

This is a phenomenological dipole response, not first principles, band structure or a full atomic multiplet calculation.

## Interface and state

The manual model selector offers **Constant tensor (original semantics)** and **L2,3 Lorentzian tensor spectrum**. The spectral draft starts with a two-column parameter table, element, magnetization/frame diagram and preview. Both complete 3×3 matrices, explicit proper frame and energy window are under Advanced.

Every matrix cell remains editable independently with real, i or j syntax using the safe parser. Existing finite/Hermiticity/PSD checks are applied at each matrix's own scale. No symmetry repair, clipping or implicit projection occurs. A general matrix stays in full mode if A/r/p cannot represent it, with explicit N/A values and an explanation. Compatible view switches do not rewrite matrices. Zero-strength edges retain their inactive simple choices.

The verified `mdff_orientation.axis_rotation` rotates the rigid model frame into the crystal direction. An explicit proper frame is also supported; its derived direction is read-only, preventing an apparently editable but ignored input. Reopening a verified-axis draft preserves that mode when it exactly reproduces the saved frame.

Authenticated elemental edge references supply starting peak energies, not fitted maxima. Missing data get a clearly identified synthetic estimate for that element, never another element's values. Widths, strengths and magnetic fractions are generic examples. Drafts, arbitrary matrices and view choices persist per element; reset affects only the active element.

The upper live schematic shows unit-area profiles (1/eV), peak positions and FWHM markers. The separate numerical spectrum and selectable-energy real/imaginary heatmaps use actual provider output in crystal coordinates. Reversal/even/odd controls remain available. The declared reversal assumption is conjugation in the fixed model frame followed by the same real proper rotation; imaginary/off-diagonal entries are not universally classified as magnetic.

Parameter edits mark numerical spectra/heatmaps STALE while the schematic may update. Invalid preview input is reported inline. Source identity changes are detected. The heatmap is evaluated analytically at its selected energy, not interpolated from display samples.

## Provider and persistence

`manual_l23.py` implements the model and an `ImportedMDFF` subclass. The existing loader changes only its reserved `manual_l23_*` dispatch; ordinary/constant sources keep their existing behavior. Reserved provenance must be complete; frames, selections and sampled evidence must match the analytical declaration. Stripping only model or editor provenance is rejected.

The existing provider/solver interface evaluates the model at actual requested energies. Stored sampled tensors are authenticated evidence/display samples, not the analytical definition. Full parameters, both matrices, frame, element, window, view and per-element drafts are serialized internally. Existing authenticated portable manual-source attachments now include spectral sources. No ordinary operation requires a JSON file chooser.

Constant projects explicitly restore constant mode. Atomic and XMCD providers/previews remain intact. XMCD projects retain their existing original-source authentication rules; the separate XMCD preview follow-up did not introduce a new portable-XMCD attachment policy.

## Verification

- `outputs/manual-l23-regression.log` / `.xml`: **90 passed**, no deselection. Includes spectral, constant/Atomic usability, XMCD previews and existing tensor/provider regressions.
- `outputs/manual-l23-verified.log` / `.xml`: **26 passed** for the final spectral implementation, including stable profiles, inline failures, arbitrary matrices, zero-strength choices, exact frames and reserved provenance.
- Checks cover full-domain area/FWHM, independent edge parameters, off-grid analytical output, no window renormalization, PSD, rotation, reversal, heatmap/provider agreement, simple/full/constant state, per-element reset, save/reopen and relocation.
- Independent ordinary sampled inputs at exact solver energies agree with analytical-model Single/Double BW/MS results, showing profiles and strengths are applied once. Relocated-project rerun spectra agree **exactly** after deleting the original source.
- Early new-test diagnostics used an unavailable `np.trapz` API and an excessively strict narrow-width subtraction assertion. Explicit trapezoid sums and an ulp-aware new-test tolerance corrected these. No historical numerical tolerance changed.

The five historical tests requiring blank defaults or the old Ni-only normal workflow remain unchanged and are listed in `MDFF_USABILITY_REDESIGN.md`. They are outside this 90-test focused selection. Constant-specific tests in the new usability suite now explicitly select constant mode; their coverage is preserved.

## Native GUI evidence

`scripts/manual_l23_native_walkthrough.py` uses the modified source and Windows Qt platform at the existing 150% scaling. It checks basic controls, both expanded matrices, complex general-matrix edits and refusal to project them. It completes Single and Double Channeling calculations with both BW and FFT Multislice, relocates/reopens a project after deleting the original source, restores the complete spectral draft and leaves the GUI open.

Metadata: `outputs/native-manual-l23/walkthrough.json`. Screenshots in the same folder:

- `spectral-basic.png`
- `spectral-reversal.png`
- `spectral-expanded-matrices.png`
- `spectral-general-matrix-retained.png`
- `spectral-heatmaps.png`
- `spectral-restored-final.png`

Basic parameters and spectra are side by side; advanced matrices and lower heatmap/window content scroll at normal scaling. Background/hidden Matplotlib figures can issue constrained-layout warnings during project restoration; visible screenshots are inspected separately.

## Launch and remaining acceptance

```powershell
Set-Location C:\Users\peng863\EMCD-Sim\build\mdff-usability
$env:PYTHONPATH = "$PWD\src"
& C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe -m emcd_sim.gui
```

Run `scripts/manual_l23_native_walkthrough.py` instead of `-m emcd_sim.gui` to repeat the demonstration. The GUI left open uses this interpreter and worktree.

Complete patch/inventory: `outputs/mdff-usability-complete.patch`, `outputs/mdff-usability-inventory.json`. Earlier delivered identities are retained in `outputs/before-xmcd-*`. The source-scope proposal includes the new analytical module and narrow reserved-loader dispatch; its candidate hashes are evidence only, never adopted by existing validators.

Remaining limitations: explicit conjugation reversal is a model assumption, Lorentzian tails extend over the real axis, finite windows/sampling require scientific convergence choices, and existing single-element/equivalent-site execution restrictions remain. Independent additive source-scope acceptance and the five superseded historical UI assertions remain pending. No full-suite or release acceptance is claimed.
