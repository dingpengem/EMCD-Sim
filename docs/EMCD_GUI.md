# Desktop GUI: technical navigation

[User Manual](USER_GUIDE.md) · [Tutorial](TUTORIAL.md) · [Physics](PHYSICS.md) · [Index](INDEX.md)

This page maps the current user workflow to the **released v0.7.0-beta.1** implementation (binary source `97b2220e`). It replaces append-only milestone navigation; the complete [earlier technical/milestone record](https://github.com/dingpengem/EMCD-Sim/blob/08d04fc35fca2071cc7e73af0aaa1de45e49a3f4/docs/EMCD_GUI.md) is preserved at its immutable revision. Acceptance reports and release notes are not rewritten.

## Start with the user workflow

Structure → orientation/target/tilt → physical detectors → source/axis declaration → channeling/propagation → effective numerics/resources → preview/run → inspect → save/export.

**Preview diffraction** is an elastic calculation. Geometry refresh, overlay dragging and display switching are not scientific recalculations. **Run EMCD / EELS** produces the selected or full spectral calculation. **Open Project** views saved arrays; **Use These Settings** separately restores controls.

The small [Quick Start](QUICK_START.md) uses a Manual Single/BW demonstration. The advanced [9/30 nm tutorial case](TUTORIAL.md#part-vii-practical-ni-017-case-study) uses existing results, not a new GUI sweep. Current shared defaults and MS-only settings are in the [manual](USER_GUIDE.md#automatic-and-manual-numerical-settings).

## Source responsibilities

|Area|Module / responsibility|
|---|---|
|Window, controls, diffraction interaction|`src/emcd_sim/gui/app.py`|
|Responsive layout and collapsible panels|`src/emcd_sim/gui/responsive.py`|
|Structure, signed indices and frame adapters|`src/emcd_sim/gui/geometry.py`; general engine in `crystallography.py`|
|MDFF/solver/sampling/resource controls|`src/emcd_sim/gui/stage_b.py`|
|Automatic/Manual starting configuration|`src/emcd_sim/gui/numerical_settings.py` (configuration checks, not a convergence solver)|
|Read-only worker policy and RAM admission|`src/emcd_sim/gui/parallel_resources.py`, `memory_budget.py`|
|Forward configuration, tensor rotation and metadata|`src/emcd_sim/gui/emcd_forward.py`|
|Propagation/support adapters|`src/emcd_sim/gui/propagation.py`; unchanged core BW/FFT kernels|
|Per-energy contraction and aperture support|`src/emcd_sim/gui/channeling.py`|
|Raw/percentage definitions and masking|`component_display.py`, `prb_benchmark.py`, `signal_normalization.py` in the GUI package|
|Result figures / derived export|`results.py`, `normalization_controls.py`, `normalization_export.py`|
|Saved projects and Results Browser|`project_io.py`, `results_browser.py`, `compare_results.py`|
|Runtime identity/logging|`runtime.py`|

## Released display and interaction contracts

- Live ZA is a yellow star; Thales is teal dotted; Laue is darkorange dashed. Laue center/radius follow the implemented excitation-error convention, not an intensity contour.
- Set-ZA click/drag updates geometry and invalidates cached coloring without starting a worker or moving detectors. Final release/fallback and Pan/Zoom priority are covered by focused tests.
- Full-basis viewing is reversible for compatible geometry; it does not reset numerical settings or results.
- Primary EELS display offers **Raw (a.u.)** components and conventional **EMCD Asymmetry (%)**. Advanced magnetic/nonmagnetic percentages use the even denominator; the tutorial's common-conventional-denominator/Flip-M curves are derived analysis, not invented controls.
- Primary angular maps use actual qy-mirrored saved samples, not finite-aperture integrals. Full raw odd/even fields are separate advanced data. Missing fields are not reconstructed from sparse detectors.
- Explicit MS maximum-step overrides remain editable in both numerical modes; requested/effective steps are recorded where applicable. Defaults and worker policies are not changed by this documentation.

## Supported launch and diagnostic scope

Normal source launch is `python -m emcd_sim.gui` (or installed `emcd-gui`; `python -m emcd_sim` also launches the desktop). The [Installation Guide](INSTALL_WINDOWS.md#j-advanced-installation-from-python-source) covers dependencies. Portable users run the EXE and need no separate Python.

Current opt-in development acceptance routes include `--desktop-acceptance`, `--scientific-acceptance`, `--cancellation-acceptance` and `--parallel-acceptance`, with their bounded profiles and destination arguments. They are diagnostic harnesses, not generic survey interfaces or substitutes for the user tutorial. Retired research commands require their original source revision; do not reuse historical flags from milestone pages as current API.

## Current acceptance and unresolved scope

The [native Windows record](WINDOWS_ZOLZ_97B2220_CANDIDATE_ACCEPTANCE.md) identifies the original candidate before public prerelease publication: five orientations, eight exact reference comparisons, eighteen worker/cancellation scenarios and native interaction/export checks passed. Its old publication-status sentences are historical; [the public release](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.7.0-beta.1) records current distribution state.

Same-host native acceptance is not independent clean-machine acceptance, code signing, experimental validation or global convergence. Linux has outstanding CI issues and macOS is not certified by this Windows release. See [scientific scope](PHYSICS.md) and [manual limitations](USER_GUIDE.md#scientific-limitations-and-responsible-interpretation).
