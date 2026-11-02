# Unit-label standardization acceptance

This section records the original pre-integration evidence, when the patch was uncommitted. Baseline `cf8fa647d1cbe7457362f54fbd4ecdce5c65cea5`, tree `3bd9978cfed62b3551216e0aadf7d3535b380dbb`; isolated worktree `C:\Users\peng863\EMCD-Sim\build\v070b1-unit-standardization`. Original reviewed patch SHA256 `a2192bfb3d95bf073fd9e8a11966040422f9aa2a33f3d3f3cafa917bf2a6dd0c`. No commit, push, version change, EXE build or release occurred during that validation.

## Changes

Display labels, warnings, help strings, export unit descriptions and current guides use kV/eV/nm/mrad/Å/Å⁻¹/nm⁻¹/%/a.u./MiB. The diffraction table now states reciprocal units on qx/qy/s_g, and the target detail uses Å⁻¹ for excitation error. Lattice and atomic radial labels use Å. The PRB scalar export unit is %. Spectral/raw-intensity provenance explicitly states a.u.

Crystallographic |g|=1/d and angular Q=2πg share inverse-length dimensions but have different numeric definitions. PHYSICAL_UNITS.md documents this distinction. No additional2π conversion is applied. API/project keys with legacy reciprocal names remain for backward compatibility. Historical outputs/accepted-package reports are not edited. Current docs are updated only in this new worktree.

## Verification

- All nine edited Python files have identical ASTs to the baseline after replacing string literals with placeholders. Numeric literals, operations, calls, branches, numerical defaults and worker policies are unchanged.
- All three corrected physics-kernel byte hashes remain identical to their approved values.
- A small independent before/after calculation covered BW/MS, Single/Double, both native energies, raw spectra, maps, incoming amplitudes and coherences:160 numerical arrays are exactly equal, including existing NaN masks. The computation explicitly imports each source tree in a fresh process.
- Focused unit/PRB/project/source-guard run:36 passed,1 skipped,0 failed. The skip is an optional pre-existing saved Ni project absent from the new isolated worktree.
- After final display/export-description wording updates:20 label/project checks passed,0 failed. Numerical equality remains protected by the string-only AST test.
- Save/open compatibility and existing configuration values are preserved. Creating/refreshing the GUI in the focused check starts no calculation workers.
- Two constrained-layout warnings came from existing offscreen project tests; they are retained in logs. No native frozen-EXE or clean-machine acceptance is claimed.

The first test attempt exposed a test harness importing the installed baseline instead of the isolated package, plus a remaining help docstring. The source path is now explicit and asserted, and the help wording was standardized. The original failed log is preserved; no tolerance was weakened.

## Final integration review additions

The production Python diff remains identical to the reviewed patch. Final review
clarifies that historical Beta 3 binaries do not contain the new unit labels,
preserves their original version/default wording, and explains that historical
figure axes have not been redrawn. The accepted v0.7.0-beta.1 EXE also predates
these labels; a separately approved build is required.

The 160-array check can read an explicitly supplied external evidence directory
(`EMCD_UNIT_IDENTITY_DIRECTORY`). Generated arrays are not committed. An isolated
checkout without this optional evidence reports an explicit skip; both the full
integration run and clean-preview checks supply the evidence and execute the
unchanged exact-equality assertions. Final regression/preview results and exact
commit identity are recorded separately in UNIT_STANDARDIZATION_FINAL_INTEGRATION.md.

The first final-regression run exposed two legacy AST assertions that included
the old reciprocal/intensity metadata wording. Their comparisons now recognize
only the exact reviewed metadata aliases in their original keyword contexts.
All computational AST structure remains exact. Four mutation controls reject
numeric, call, branch and unapproved-label changes; no tolerance or physics
source was changed. The initial failure logs are retained for the final report.

## Files

- README.md
- docs/ARCHITECTURE.md
- docs/NI_017_CASE_STUDY_GUIDE.md
- docs/QUICK_START.md
- docs/ROADMAP.md
- docs/SINGLE_CHANNELING_QUANTITATIVE.md
- docs/SINGLE_CHANNELING_TENSOR.md
- docs/USER_GUIDE.md
- docs/WINDOWS_BETA_3.md
- src/emcd_sim/gui/app.py
- src/emcd_sim/gui/emcd_forward.py
- src/emcd_sim/gui/geometry.py
- src/emcd_sim/gui/prb_benchmark.py
- src/emcd_sim/gui/project_io.py
- src/emcd_sim/gui/propagation.py
- src/emcd_sim/gui/results.py
- src/emcd_sim/gui/stage_b.py
- src/emcd_sim/scattering.py
- docs/PHYSICAL_UNITS.md (new)
- docs/UNIT_LABEL_STANDARDIZATION.md (new)
- tests/test_unit_labels.py (new)

Full evidence: `C:\Users\peng863\EMCD-Sim\build\v070b1-unit-standardization\outputs\unit_labels`; acceptance.json, both NPZ snapshots, source-identified test logs and reviewed_label_changes.patch. Scientific200 kV results use the clean pinned source independently, with an unchanged numerical model.
