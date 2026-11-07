# v0.8.1-beta.2 - Windows Research Beta prerelease draft

**Research Beta prerelease: v0.8.1-beta.2.** Package version `0.8.1b2`, Windows version `0.8.1.2`. This is a development/research candidate, not formal scientific release acceptance. The previous beta.1 assets remain unchanged.

## MDFF feature additions

This update covers the complete feature difference from published `v0.8.1-beta.1` to local integration `aaa69a1`, not only the last ambiguity fix.

- **Dedicated MDFF configuration:** three consistent choices, XMCD-constrained MDFF, Atomic Ionization MDFF, and Manual tensor, with basic controls, advanced inputs, explanations, and frame/transition diagrams.
- **Element-aware Atomic editor:** cubic independent-electron Sc-Zn 2p-to-3d L2,3 construction; elemental reference starts, explicit Gaussian width, magnetization/frame, crystal-field/exchange splitting, spin-resolved holes, radial input, provenance, and per-element drafts. Generic electronic defaults remain visibly synthetic.
- **Manual construction:** nine editable complex cells for a constant Hermitian PSD density, plus separate L3/L2 integrated tensors broadened with Lorentzian FWHM profiles. Simple transverse/longitudinal/magnetic controls and full matrices retain their distinct meanings. Finite-window tail loss is displayed, not renormalized away. Advanced imported source exchange remains available.
- **Actual provider previews:** XMCD shows original five-column input beside the provider-generated tensor; Atomic/manual show numerical spectra, components, reversal/even/odd states, and applicable heatmaps. Schematics are distinguished from numerical output and detector spectra.
- **Preparation and persistence:** inline draft validation, stale snapshots, explicit generation/preview, source checks, per-element state, portable editor-generated project inputs, and restoration of the intended model/parameters.

Construction methods, required inputs, parameter meanings/defaults, units, physical assumptions, and a complete existing-input example are in [MDFF workflows](MDFF_WORKFLOWS.md). Normal project creation does not require an existing JSON: run a calculation and use **File > Save Project**.

## Usability and correctness fixes

- One XMCD source selection supplies preview and calculation; preview does not prompt for a second MDFF source.
- Ambiguous XMCD requires both explicit edge selections. Default, inherited, or stale controls do not automatically qualify, and selecting just L3 is insufficient.
- Fe 710/723 eV explicit choices survive normal save/reopen and govern subsequent preview/calculation; stale JSON cannot override later visible L2,3 control edits.
- Failed external Atomic validation blocks Run as well as computation. A pending generalized draft does not overwrite a valid historical saved Atomic provider.
- Model switching preserves intended drafts, axes, and display state; restored inputs remain tied to verified source bytes.
- BCC Fe diffraction preview is separate from inelastic-source validation; a missing/unsupported MDFF does not block otherwise supported elastic inspection.
- Responsive controls and provider selection remain usable at the tested screen/scaling configurations.

Shared propagation kernels, tensor contraction convention, scientific reference data, and numerical tolerances were not changed by the final repair. Existing safeguards remain applicable.

## Compatibility and model boundaries

The third normal model label is now **Manual tensor**; advanced imported exchange remains under it. Historical saved Atomic/Ni routes retain their meanings instead of receiving generic new defaults. Preserve original data and source identities when reopening old projects. The convention remains `forward_born_dagger_g_minus_h_v1`; earlier v0.6.1 signed magnetic results need revalidation.

Elastic multi-element structure support does not imply multi-element MDFF. Inelastic execution remains limited to supported single-element/equivalent-site cases. No general inequivalent-site sum, noncollinear texture, AFM/SDW material model, multiplet/band solver, full ab-initio MDFF, absolute cross section, or quantitative Fe spectroscopy is established. Relative intensities and coarse examples are not convergence or experimental SNR certificates.

Windows x64 is the tested packaged platform. Linux/macOS packaged support and independent clean-PC/VM installation remain unverified; recorded non-Windows CI problems are not hidden by the prerelease exception.

## Installation and first calculation

Download its complete Windows ZIP and release checksum, verify and fully extract it into a new directory, and run `EMCD-Sim/EMCD-Sim.exe` with `_internal` and all support files intact. Do not upload or distribute a lone EXE. Binary users do not need Python, Conda, WIEN2k, or a project JSON.

The beta.2 package is rebuilt with its own embedded version, rather than relabeling the earlier development EXE. Install the official Microsoft x64 v14 runtime (14.44.35211 or newer) directly from Microsoft before launch. No runtime installer or Microsoft runtime DLL copies are bundled. See [installation](INSTALL_WINDOWS.md), [first calculation](QUICK_START.md), and [MDFF examples](MDFF_WORKFLOWS.md#worked-example-synthetic-fe-from-existing-inputs).

Only the cleared complete distribution and its existing required release inventory/checksum artifacts may become release assets. Exclude temporary projects, private WIEN2k companions/research data, credentials, investigation logs, and unrelated working changes.

## Validation evidence and scoped exception

| Evidence | Actual result |
| --- | --- |
| Complete Windows suite on `7730e38` | **FAILED**: 1,191 passed, 1 failed, 54 skipped; exit 1; 1:17:53. The failure was ambiguous XMCD accepting populated controls without explicit selections. |
| Repair `4f15a4d` | Four focused cases passed in 44.78 seconds, preserving the original failed assertion and checking explicit-selection/save-reopen behavior. |
| Local merge/development EXE `aaa69a1` | Built once, exit 0, clean embedded source, version `0.8.1b1`; required package-content checks passed. |
| Actual native EXE | Ambiguous and L3-only input rejected; explicit Fe 710/723 eV preview and small calculation passed. The EXE created and saved a project through normal dialogs; after application restart, reopening and recalculation passed without re-entering selections. Existing synthetic fixtures were used, not scientific Fe calibration data. |
| User trial | User reported the development EXE passed their trial. |

The user explicitly extended the earlier local-development exception to **this Research Beta prerelease only**, permitting the previous full-run evidence plus completed focused/native verification without another complete regression. This does **not** turn the failed run into a pass, waive scientific/security requirements, or establish formal scientific release readiness. Interrupted historical runs are not counted as passing. No new full regression or historical audit was run for this preparation.

## Publication status

The former binary redistribution blockers are addressed by explicit packaging changes:

- Unused Qt PDF and Virtual Keyboard bindings/plugins are excluded, along with the QML/Quick/OpenGL module dependency chain. Retained Qt modules are Core, Gui, Widgets, Network and Svg. Historical notices remain; GPL components have not been relabeled LGPL.
- Matching official Qt/PySide/Shiboken 6.12.0 source archives are supplied in **EMCD-Sim-v0.8.1-beta.2-Qt-sources.zip**, alongside the exact application source, build/replacement instructions and upstream provenance. Retained Qt/PySide/Shiboken use their LGPL v3 alternatives, with separate third-party terms. The application remains MIT licensed; no commercial license is claimed.
- Microsoft runtime redistribution rights were not established for inherited wheel copies, so **none are shipped**, including the renamed NumPy copy and UCRT/API-set copies. Users install Microsoft's official x64 v14 runtime directly. Two staged NumPy PE import strings are normalized to the standard system DLL name; executable code and installed wheels are unchanged.

See [installation prerequisites](INSTALL_WINDOWS.md) and [source/build/replacement instructions](../packaging/assets/qt-licenses/SOURCE_AND_REPLACEMENT.md). No dependency versions, scientific kernels or numerical tolerances changed for dependency trimming. Package inventories and directly affected existing pins are updated; earlier releases remain untouched.

Final package/native verification is recorded below before publication.
