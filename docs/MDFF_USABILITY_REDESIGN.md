# MDFF usability redesign

The latest manual L2,3 spectral extension is documented in [MANUAL_L23_TENSOR_MODEL.md](MANUAL_L23_TENSOR_MODEL.md). It adds an analytical energy-dependent option while retaining the constant option and the restored XMCD preview below. The current GUI is left open on the spectral interface; earlier phase screenshots and test evidence remain preserved.

Implementation is in `C:\Users\peng863\EMCD-Sim\build\mdff-usability`, based on accepted local main `3b0ce6c`. The existing clean `feature/mdff-usability` worktree was reused. No commit, merge, push, version change, EXE build, tag or release was performed. Unrelated main-worktree work and packaged artifacts were not edited.

## Interface

Open **Configure MDFF…** in the main window. The dedicated, scrollable configuration window uses the actual provider controls and has Material, Model, Main parameters and Preview areas. Open CIF is generic. Atomic ionization is the initial normal model. Historical Ni controls remain internal and hidden; saved historical settings still restore through the existing compatibility path.

Atomic main controls are element, L3/L2 reference energies, Gaussian standard deviation and crystal Cartesian magnetization direction. Apply direction constructs a proper rigid frame, rotating the orbital model and spin axis together; this does not implement independent noncollinear spin rotation. An advanced proper frame remains editable. Reset defaults resets the active element. Switching elements preserves complete editable drafts.

All supported Sc–Zn elements receive complete initial drafts. Edge references use the existing authenticated offline elemental library. Electronic defaults are explicitly synthetic: zero cubic splitting, 0.5 eV exchange, unit radial integral, and 0.2/0.4 up/down hole weights. They are demonstrations, not measured material parameters. Broadening/grid/frame are numerical or coordinate choices. If trusted references are missing, an explicitly identified synthetic hydrogenic energy scale is supplied; no other element's data are substituted. Unsupported transitions/elements still cannot calculate.

Advanced controls retain holes, cubic/exchange splitting, radial inputs, proper frames, grid, provenance, detailed definitions and optional parameter-file exchange. Normal preview and calculation create authenticated immutable internal sources automatically. A refresh or preview does not reload over the current draft.

The original constant manual option has all nine editable Cartesian tensor cells, real/complex parsing with `i` or `j`, a trace-one `I/3` initial example, and real/imaginary heatmaps. It defines a **constant tensor over [L3−10, L2+10] eV**, not arbitrary energy-dependent spectroscopy. L3/L2 are evaluation selections, not generated peaks. Units are relative per-atom Å²/eV. Its explicitly displayed synthetic reversal assumption is `T_minus = conjugate(T_plus)`, with shared even part `Re(T_plus)`. This assumption is part of the manual model; it does not change the imported provider's requirement for explicit authenticated tensor pairs. General imported spectra and their reversal declarations are retained through advanced exchange/restoration.

Parsing never calls eval. All cells stay editable; malformed/nonfinite, non-Hermitian and negative-eigenvalue drafts fail inline without changing previous authenticated bytes. Relative Hermiticity/PSD thresholds match the existing provider. No symmetry repair, clipping or normalization is applied.

Atomic schematics show L3/L2 core transitions and broadening, a crystal-frame magnetization/beam projection, and reversible displayed magnetization. The spectral drawing is schematic; the separate numerical curve comes from the existing generator, including its cubic/exchange shifts. Focused parameters change the explanation and graphical emphasis. Advanced hole weights are schematic, not electron density. Manual cells highlight their matrix position; off-diagonal is not synonymous with magnetic. Numerical previews clearly become stale when inputs change.

## Verification

- `outputs/final-validation.log` and `.xml`: **117 passed, 5 deselected**. Includes new workflows and existing atomic editor, unified providers, tensor and historical Ni numerical tests. Atomic and manual calculations exercised BW and MS; portable projects reran with exactly equal spectra after deleting their original sources. Source-tampering rejection and actual restored tensor delivery are covered.
- `outputs/redesign-final.log` and `.xml`: **33 passed** against the final functional editor code, including additional passive-edit/source-authentication tests and Hermiticity/PSD checks at scales 1e−25, 1 and 1e25.
- Earlier diagnostic results remain in outputs. The broader diagnostic had 113 passes and nine failures. Four acknowledgement/frame failures were corrected while preserving those existing assertions; the remaining five tests deliberately assert the superseded blank-input or historical-Ni normal UI. They were left unchanged, excluded explicitly from the final focused selection, and replaced behaviorally by the new redesign suite. This is not a claim that the unchanged full suite passes.
- Numerical solver, tensor convention, atomic generator, edge reference data, historical numerical fixtures and tolerances were not edited. Existing authenticated historical evidence remains meaningful. No new full-suite run or production source-scope acceptance is claimed.
- Warnings: Qt high-DPI API deprecation and three existing background GUI-preview constrained-layout warnings in relocated-project tests. Native configuration screenshots were separately inspected for readability.

The five historical UI assertions awaiting an additive review are:

1. `test_unified_starting_choices_have_no_material_electronic_defaults`
2. `test_required_physical_definitions_and_blank_material_inputs`
3. `test_element_drafts_do_not_transfer_or_restore_validation`
4. `test_missing_references_and_unsupported_element`
5. `test_historical_ni_is_not_silently_migrated`

The last test concerns the previous default new-window workflow; existing historical saved-project restoration remains internal and its numerical implementation was preserved.

## Native Windows walkthrough

`scripts/mdff_native_walkthrough.py` launches the modified source using the Windows Qt platform, opens a CIF through the real load handler (the CIF chooser result is supplied by the harness), edits real controls, previews, expands advanced occupations, checks an inline PSD error and starts actual GUI calculation workers for both manual and Atomic models. It captures the exposed native window with `QScreen.grabWindow`, not an offscreen renderer. It leaves the application and Atomic configuration window open.

The actual monitor is 1280×853 logical pixels at **150% scaling**; the configuration window is 1120×800 logical pixels. Scrolling is intentional for advanced and lower heatmap content. Normal Atomic parameters and numerical preview are side by side. Native screenshots and interpreter/PID/display metadata are in `outputs/native-usability/walkthrough.json`:

- `atomic-basic.png`: basic Atomic controls and live preview.
- `atomic-advanced.png`: expanded specialist controls.
- `atomic-occupations.png`: scrolled occupation/hole schematic.
- `manual-tensor.png`: nine editable cells and numerical spectrum.
- `manual-heatmaps.png`: scrolled real/imaginary heatmaps.
- `manual-inline-error.png`: invalid draft and stale previous preview.
- `final-atomic.png`: final screen left open after native calculations.

## Launch

PowerShell, using the verified project Python 3.11 environment:

```powershell
Set-Location C:\Users\peng863\EMCD-Sim\build\mdff-usability
$env:PYTHONPATH = "$PWD\src"
& C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe -m emcd_sim.gui
```

To repeat the visible walkthrough and leave it open, use the same environment with `scripts/mdff_native_walkthrough.py` instead of `-m emcd_sim.gui`. The interpreter's environment libraries resolve into the existing `emcd-python` environment; the reported executable is the project's `build/windows-rc/venv/Scripts/python.exe`.

## Deliverables and remaining acceptance

Complete patch: `outputs/mdff-usability-complete.patch`. Changed-file inventory, parent/candidate identities and unchanged historical evidence: `outputs/mdff-usability-inventory.json`.

The source guards correctly reject the modified UI/I/O files as unreviewed. `docs/MDFF_USABILITY_SCOPE_PROPOSAL.md` describes the narrowly additive review required. No existing guard, historical manifest, archive or pinned hash was weakened or replaced. This acceptance step and the five superseded workflow assertions remain open; the working source implementation, focused tests and native walkthrough are complete.

The underlying model retains its existing scientific limits: approximate cubic independent-electron Sc–Zn L2,3 transitions, relative intensities, and one executable element/equivalent-site group. Manual constant tensors are synthetic examples unless the user supplies suitable physical inputs; nine numbers alone do not establish an experimental spectrum.

## XMCD preview follow-up

XMCD-constrained mode retains an embedded Preview area beside the source/main controls, including when no valid source is available. Preview reuses the source selected and validated in the main XMCD input, without a second file chooser. If unavailable, its message directs the user to that main input. Specialist source declarations remain collapsed. A mismatched bundled Ni source is rejected for another material; no replacement source is selected automatically.

The upper plot shows the exact RP, LP, XAS and XMCD input columns after validation. The lower plot shows the actual tensor pair returned by `mdff_providers.prepare_provider(cfg).tensors(...)`, the same provider selection used in calculation. Declared sources and the historical numerical path are both covered. No XMCD tensor formula, normalization implementation or reversal implementation was copied into the UI. Tensor components are crystal Cartesian; labels distinguish raw input intensity from the provider's relative tensor scale.

The preview offers +M, −M, Even, Odd, paired reversal, paired even/odd, all nine tensor components, trace/3 and real/imaginary display. These controls redraw the authenticated snapshot without recalculating physics. Source identity, file bytes, declarations, element context, selected energies, eta, beta and axis changes invalidate that snapshot. An invalid or missing source leaves old curves explicitly marked STALE, with an inline explanation and direct source-selection action. A visibility-aware timer also detects external source changes. Each model retains its own reference axis when switching; restored projects update model-description and axis-visibility presentation even when restoration blocks model-selector signals.

Focused follow-up checks and their final counts are recorded in `outputs/xmcd-preview-final.log` / `.xml` and `outputs/xmcd-preview-input-columns.log` / `.xml`. The latter verifies exact input-column delivery, including accepted rounding differences in redundant source columns. Existing all-model usability and provider checks are included in the combined run. Three-model calculation/save/reopen tests restore through the real **Use These Settings** handler and compare rerun spectra exactly. XMCD projects retain the existing authenticated original-text-source rules; this follow-up does not introduce a new portable XMCD attachment policy.

`scripts/xmcd_native_walkthrough.py` demonstrates the modified source on the Windows platform, including an explicitly selected Ni source for a displayed Ni material, real GUI calculation, save/reopen and restored XMCD preview. It exercises all three model switches, reversal/even–odd, stale eta edits and missing-source selection. The latest GUI remains open in XMCD mode. Native screenshots and interpreter/PID metadata are in `outputs/native-xmcd-preview/walkthrough.json`:

- `xmcd-source-and-tensor.png`
- `xmcd-even-odd.png`
- `xmcd-stale.png`
- `xmcd-missing-source.png`
- `xmcd-restored-final.png`

Launch with the same source/interpreter command above, or run `scripts/xmcd_native_walkthrough.py` to repeat the demonstration. No commit, merge, EXE rebuild or release was performed. The additive source-scope proposal now also lists the XMCD preview module, its tests and native walkthrough; the historical guards remain unchanged.
