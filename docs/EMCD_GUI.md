# EMCD-Sim desktop GUI ? Stage B

Stage B adds genuine **Bloch-wave entrance-channeling EMCD and EELS** to the
existing Stage A diffraction interface. Both XMCD-constrained and atomic
2p?3d MDFF models are implemented and tested. Multislice GUI execution remains
disabled until Stage C; full history/reopening remains Stage D. Package
version 0.4.5 and the existing CLI workflows are unchanged.

![Actual Windows GUI after a default Ni [017] BW EMCD calculation](images/gui/stage_b_windows.png)

The screenshot shows computed A/B ?M EELS, reversal-odd/even differences and
raw/corrected contrast. **Maximize / restore results** expands the scientific
figures; it does not rerun or rescale the calculation. The earlier elastic
preview is retained below as a Stage A reference.

![Actual Windows Qt application after a numerical Ni [017] elastic preview](images/gui/stage_a_windows.png)

The screenshot is an actual PySide6 window on Windows, after the existing
Bloch-wave solver calculated the default Ni [017] exit intensities. The
central view is zoomed to the systematic-row region; **Show full basis**
reveals off-row points. All 27 included beams remain in propagation and
in the result table even when some fall outside the current view.

## Windows setup and launch

In PowerShell from the repository:

```powershell
conda activate emcd-python
python -m pip install -e ".[gui]"
python -m emcd_sim.gui
# Equivalent installed entry point:
emcd-gui
```

Only PySide6 and ASE are added as direct optional GUI dependencies;
Matplotlib/numpy are already core dependencies. A CLI-only installation
does not import Qt or require the GUI extra. No executable or installer
is built. For small previews, optionally set OPENBLAS_NUM_THREADS=1 and
OMP_NUM_THREADS=1 before launching.

For an automated **real default elastic preview**, screenshot and clean exit:

```powershell
python -m emcd_sim.gui --smoke-screenshot outputs/gui_stage_a/stage_a_windows.png
```

Normal launch does not automatically calculate intensities. A geometry-only
view uses open reciprocal reference markers until **Preview diffraction**
is pressed. Screenshot mode explicitly runs that preview. Qt offscreen
testing is supported through QT_QPA_PLATFORM=offscreen; a bundled Matplotlib
font is loaded if that platform exposes no system fonts. The committed
screenshot was captured using the native Windows platform.

## Stage A workflow

1. Start with built-in FCC Ni (a=3.524 angstrom), zone [017], target (200),
   200 kV and 30 nm. Initial absolute tilt is approximately
   (-7.116725439974256,0) mrad: exact paraxial (200) Bragg, **not** zone-axis
   incidence. Preview uses beam cutoff3.2, potential cutoff2.2 cycles/angstrom,
   27 beams, and B=0. Exit intensities use the existing physical BW solver.
2. **Preview diffraction** starts a worker thread. Inputs and scientific
   click edits are disabled during its calculation. The plot/table report
   actual exit intensities and excitation errors, without Gaussian CBED
   disks or fitted peak widths. Scatter marker area/color is a visualization
   of discrete beam intensity, not a physical disk size.
3. In **Select reflection** mode, click within 16 display pixels of an indexed
   nonzero spot. Its hkl becomes the target. Selection alone does not change
   zone axis or incident tilt. It restores the symmetric Thales A/B centers
   for that selected reflection. The bottom readout shows reciprocal position,
   magnitude, excitation error, and a calculated intensity only when the
   saved preview matches current physical inputs.
4. **Align to selected Bragg** solves s_g=0 using the existing paraxial
   excitation-error convention. With no locked component it applies the
   minimum-norm transverse tilt correction. Lock X or Y to retain that
   component. An incompatible lock produces an error instead of silently
   unlocking it. **Reset to zone axis** sets both incident tilts to zero;
   **Reset to reference geometry** restores nominal [017], target200, y=0
   and its exact Bragg x tilt at the currently selected voltage.
5. In **Set projected ZA** mode, click any reciprocal-space coordinate.
   This sets tilt=-1000*lambda*q_ZA in mrad, with the existing relativistic
   wavelength in angstrom. Conversely, editing absolute Tilt X/Y updates
   q_ZA=-tilt*0.001/lambda. These edits never change the nominal zone axis.
   The numerical q and tilt fields are linked using blocked Qt signals to
   avoid recursive updates. Direct keyboard entry and 0.01/0.1/1 mrad steps
   are available. The GUI range is +/-100 mrad, not a claim of physical
   paraxial accuracy out to that limit.
6. Zoom/pan with the Matplotlib toolbar. Scientific clicks use the event's
   data coordinates after the current axes transformation, so zooming and
   resizing do not change the physical mapping. Selection is suspended
   while toolbar pan/zoom is active. **Maximize / restore viewer** collapses
   and restores the side panels without replacing the canvas.

Changing physical inputs updates geometry but never starts another numerical
preview automatically. Completed values remain explicitly labeled **last
preview** on the right when inputs become stale; central markers revert to
unweighted references. The calculation-information tab records the current
structure, orientation and settings, and whether they match the last result.
The diffraction preview is elastic only; the separate Stage B run uses source
magnetization to calculate the ionization tensor and magnetic signal.

## CIF import, orientation and capability boundaries

**Load CIF...** uses ASE and opens a structure-inspection window containing
formula, cell lengths/angles, species, atom count, fractional positions,
source path/SHA256, import warnings and any space group supplied by the CIF.
Space group is not independently inferred or validated. CIF Miller and zone
indices refer to the actual imported cell, not an automatically standardized
conventional FCC cell.

Enter integer [u v w] and target h k l with spaces; [017] compact notation
also works. Integer directions are reduced by their common divisor without
reversing their sign. The local z direction is constructed from [uvw] in
the ASE direct cell; Gram-Schmidt and a cross product construct a proper
orthonormal frame. The [017]/[001]/[710] choices match the established cubic
frame conventions. The cell itself is rotated, not merely its labels.
The full finite ZOLZ set satisfies h*u+k*v+l*w=0 and the radial cutoff.
For Ni, actual structure-factor extinctions are applied. No arbitrary
two-beam truncation is used. Targets outside that basis must be replaced
by typing/clicking an included reflection before a preview is enabled.

Only Ni elastic factors are bundled in the core. Fully occupied ordered
Ni CIFs can use BW with their actual oriented cell and fractional positions;
they are not silently replaced by the built-in FCC geometry. Other materials
and partial/disordered occupancies are **inspection/reciprocal-geometry only**.
Their markers do not represent calculated intensities or reliable atomic
extinction rules, and elastic preview is disabled with an explanation.
This is not material-general magnetic EELS support.

An interactive preview is limited to 121 included beams and a bounded hkl
search. Excessive requests produce an actionable error; the code does not
drop beams to fit the limit. General-orientation FFT potentials and arbitrary
material MDFFs are not substituted for unsupported models.

## Detectors and scientific overlays

The (000) origin, real hkl spots, target reflection, Thales circle and physical
A/B outlines use transmitted-beam-centered **cycles/angstrom** coordinates.
Only the projected ZA moves when incident tilt changes. Its correct location
can lie outside a zoomed view; use the numerical ZA readout or zoom out.
The left panel also exposes radius and center coordinates, show/hide,
**Move detector A/B** click modes and **Restore Thales A/B**. The latter puts
centers at g/2 +/- the transverse perpendicular g/2 for the current target.
Manual centers stay fixed during subsequent tilt edits. A status label
distinguishes an exact y-mirrored pair from a manual/non-y-mirrored pair.
The lightweight elastic preview does not integrate EELS. Stage B uses shared
fractional-aperture weights and validates physical reflection pairing before
enabling mirrored pixel maps. Direct EELS integrates the actual manual A/B
apertures even when mirror pairing fails.

## Progress, cancellation and exports

The expensive eigenproblem runs in a QThread. Cancellation is cooperative
before/after the current elastic stage; an eigensolve is not forcibly killed.
Cancelled and failed runs are not registered as completed previews. Closing
while busy requests cancellation and keeps the window alive until the worker
stops; close again afterward. The worker uses an isolated structure/settings
snapshot. Progress is indeterminate during the elastic stage, then complete
only on success. This is not fabricated percentage progress.

**Export current plot PNG/SVG** exports the currently labeled viewer, including
geometry-only or stale-state labeling. **Save elastic preview** writes the
last completed elastic result into a new timestamped subdirectory:

```text
elastic_YYYYMMDD_HHMMSS_microseconds/
    diffraction_pattern.npz
    metadata.json
```

The NPZ contains real hkl, reciprocal positions, excitation errors, sampled
depths [0,t], complex amplitudes, exit intensities and orientation matrix;
it loads with allow_pickle=False. JSON records the computed input snapshot,
source hash/description and elastic-model scope. Plot export and result export
are separate so a changed current geometry cannot be silently saved as the
last calculation's image. Full result reopening, registered-result browser,
CIF export and complete EMCD run packages belong to Stage D.

## Validation and next milestones

Six focused tests cover default Ni [017] frame/Hamiltonian/exit-wave agreement
with the established engine; arbitrary proper ZOLZ orientations; tilt/ZA
round trips, Bragg locks; ASE Ni/Cu CIF import and occupancy/material gating;
reflection/ZA events after zooming; fixed detectors; cancellation and failures.
The native Windows smoke preview verifies launch, a real worker result and
window capture. No broad regression suite or previous EMCD sweep was run.

```powershell
python -m unittest discover -s tests -p test_gui_stage_a.py
```

The prior QCBED desktop source was not identified in the checked sibling,
source/repos, PycharmProjects, python_script, anaconda_projects, Desktop,
Documents and Downloads locations. The local qem Matplotlib/Tk helper was
inspected but is not that desktop application; no code was copied from it.
This standalone interface follows the requested left-input / center-viewer /
right-results organization, with no QCBED dependency.

Stage B is implemented below. Stage C will add matched incoming FFT coherences;
Stage D will add full save/reopen and result registration. Neither is enabled.

The EMCD GUI retains projected IAM, entrance-only ionization,
XMCD-effective rather than complete DFT-derived MDFF, no outgoing channeling,
HOLZ/TDS/absorption, uncalibrated absolute cross sections/energies and unresolved
potential-cutoff convergence. An attractive preview or BW agreement cannot
establish quantitative experimental accuracy. See the [case-study guide](NI_017_CASE_STUDY_GUIDE.md).

Implementation references: [Qt threads](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html),
[Matplotlib Qt canvas](https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_qt_sgskip.html).

## Stage B: MDFF selection and source preview

Expand **D. MDFF Model**. Switching models leaves the crystal, tilt and
physical detector positions unchanged.

**XMCD-constrained (WIEN2k):** select a compatible five-column file
`energy, RP, LP, XMCD, XAS`, then **Validate source / native features**.
Validation checks positivity, ascending energies, XMCD=RP−LP and XAS=RP+LP.
The preview displays those original sums/differences with full/L3/L2 zoom;
there is no source energy shift. For the bundled audited Ni source the
selected magnetic features are **831.271 / 848.698 eV**. They are native
calculated L3/L2 features, not calibrated experimental edge energies.

When the original Ni companion files exist, the existing energy/core and
magnetic-axis audit runs. Independent five-column imports do not require
those files. The GUI distinguishes format validation from provenance,
suggests two separated source-dependent magnetic features when possible,
and allows explicit L3/L2 selection. For an ambiguous assignment the user
must select the energies and declare them. The declaration checkbox covers
the crystal Cartesian magnetic axis, RP/LP handedness and edge identity;
independent files are never silently assigned verified [001] provenance.

The effective tensor has Txy=+i eta (RP−LP)/2, transverse response proportional
to (RP+LP)/2, and longitudinal response beta times that response. It uses the
existing source-maximum normalization, not experimental absolute units.
Eta/beta and the declared axis must satisfy positivity. This is an
XMCD-constrained effective tensor, **not** a full complex DFT MDFF.

**Atomic ionization:** L3/L2 default independently to 852.7/870.0 eV.
Controls expose Gaussian sigma (default 0.8 eV), 10Dq, exchange and eg/t2g
spin holes. Advanced controls expose effective nuclear charges and an
optional explicit radial dipole in angstrom; otherwise the existing
normalized screened-hydrogenic radial functions are used. The preview shows
Re Tr(T)/3, Im Txy and Re Tzz. This is an **atomic 2p–3d approximation,
non-DFT, not quantitative metallic Ni**, without multiplets, core-hole or
band dispersion. Atomic magnetization is currently restricted to crystal
[001], preserving the existing cubic orbital conventions.

Atomic reversal is performed **before tensor construction**: spin-up/down
holes swap and the exchange-energy shift reverses for each fixed spin
channel. The complex 2p core-SOC amplitudes remain in their established basis.
For the supported real cubic orbital model this gives T(−M)=conj(T(+M));
real even response is invariant and imaginary odd response changes sign.
Nonzero-exchange tests check occupations, transition energies, Hermiticity,
PSD and nonnegative EELS. A failed reversal-symmetry check rejects the run.
For both models the final transformation is **R T_crystal R^T**, using the
actual Stage A orientation. Default [017] local M is
(0, −0.1414213562, 0.9899494937), rather than the local beam axis.

## Stage B: run, inspect and interpret

1. Choose the verified conventional FCC Ni cell (a=3.524 angstrom). Other
   zone directions/finite ZOLZ bases of this same cell are supported; arbitrary
   Ni-containing CIFs are not given a bulk-Ni MDFF automatically. An equivalent
   conventional Ni CIF may pass the conservative cell/site gate; other cells
   retain Stage A inspection and supported elastic previews.
2. Set geometry and physical A/B apertures. **Preview diffraction** remains
   separate and lightweight. **Run EMCD / EELS** snapshots structure,
   orientation, MDFF, tilt, detectors and numerics in a QThread. It propagates
   depth amplitudes once (64 nodes by default), constructs the existing
   trapezoidal coherence and reuses `run_tensor_with_coherence` for all
   energies, both edges and reversal states. Full spectra include the exact
   selected map energies. Progress reports actual stages, not fitted timing
   percentages. Cancellation is checked between contraction calls; an active
   eigensolve/contraction finishes before stopping. Failed/cancelled runs
   never replace the last completed result.
3. Numerical controls default to 241 uniform energy samples plus selected
   energies, 33×33 reciprocal pixels and 64×64 boundary subpixels. Energy,
   grid, depth and subpixel counts are bounded. The existing dense kernel
   estimate is shown; configurations above 512 MiB are rejected. Apertures
   must be fully covered by the map. Beam/potential cutoffs are explicit;
   they are never reduced silently for performance.
4. **EMCD Angular Maps** switches L3/L2 in a 2×3 layout: odd magnetic,
   reversal-even, total +M, raw paired, corrected paired and residual even.
   Signed fields use shared absolute scales across edges for each field;
   no per-map peak normalization is applied. Every available map uses its
   completed-run 000/hkl/target/ZA/Thales/A/B geometry. Out-of-view ZA is
   reported by coordinates. Use the toolbar or maximize results for detailed
   inspection. Edits mark retained results **STALE** until recalculation.
5. **Virtual Detector EELS** shows A/B ±M, odd/even differences and
   raw/corrected/intrinsic magnetic contrasts. Choose full/L3/L2 zoom and click
   legend entries to toggle curves. Markers show the selected energies and a
   shaded band shows a valid correction window. Intensities are not peak
   normalized. **Magnetic / Nonmagnetic** gives signed edge metrics; negligible
   denominators display `undefined`.

For each physical detector, N=(I_plus+I_minus)/2 and
M=(I_plus−I_minus)/2. Then D_mag=M_A−M_B, D_nonmag=N_A−N_B and
D_raw=I_A_plus−I_B_plus=D_mag+D_nonmag. Nonmagnetic/even **intensity** is not
its A/B **imbalance**. Direct integration uses each actual aperture even
when manually moved. Only exactly validated y-reflection pairs receive
pixelwise paired maps; otherwise those panels explain why they are disabled,
while intrinsic angular maps and integrated spectral decomposition remain.

Post-edge correction is optional. For the audited XMCD source, 878–882 eV is
the established default. Other sources/atomic mode default to correction
off until a scientifically suitable window is chosen. An invalid/out-of-range
or insufficiently sampled/zero-signal window disables correction with an
explanation and preserves all original spectra. Alpha is obtained from the
observed +M A/B integral ratio. Corrected contrast is
I_A_plus−alpha I_B_plus = (M_A−alpha M_B)+(N_A−alpha N_B).
The latter term is residual even contamination; correction also changes the
magnetic term. Neither corrected contrast nor its improved visual symmetry
establishes an intrinsic magnetic signal. The comparison tab reports alpha,
magnetic bias and residual even signal separately.

## Stage B: explicit export and validation

**Export completed EMCD / EELS** writes a new timestamped subdirectory:

```text
input_parameters.json
metadata.json
angular_maps.npz
virtual_detector_eels.npz
L3_angular_maps.png
L2_angular_maps.png
virtual_detector_eels.png
```

NPZs load with `allow_pickle=False`; they include original ±M spectra,
odd/even decomposition, valid corrected fields, detector weights, coherence,
depths and amplitudes. JSON records source path/hash and optional companion
audit, atomic parameters, native energy grid, R, cubic/local M, reversal,
actual tilt, target excitation error, hkl, detector positions/areas,
wavelength/ZA/000, thickness, cutoffs, sampling, solver, software commit,
worktree state and adapter hashes. Plots use the completed snapshot even
after live input edits. This is explicit export, without Stage D reopening
or a result database. Previous elastic/[017] output files are preserved.

Focused validation on Windows in `emcd-python`:

```powershell
python -m unittest discover -s tests -p 'test_gui_stage_*.py'
python -m pytest tests/test_ni_local_mdff.py -q
python scripts/gui_stage_b_validation.py
# Optional direct check of a completed native default [017] XMCD GUI export:
python scripts/gui_stage_b_validation.py --gui-export outputs/gui_stage_b/<xmcd_run_folder>
python -m emcd_sim.gui --smoke-emcd-screenshot docs/images/gui/stage_b_windows.png
python -m emcd_sim.gui --smoke-emcd-screenshot outputs/gui_stage_b/stage_b_atomic_windows.png --smoke-atomic
```

The 16 focused GUI tests pass (6 Stage A, 10 Stage B), including real-worker
manual-detector recalculation and cancelled/failed result rejection. All eight
existing local-atomic MDFF tests also pass, including radial/CLI round trips
and the historical default construction. Native
Windows XMCD and atomic runs both calculated full default 243-energy,
27-beam, 33×33, 64-depth-node results. A separate established CLI [017] model,
rotation and depth coherence produced **bitwise-identical full A/B ±M
spectra and coherence** with matched source/energies/numerics. The same check
against the native Windows export, using its saved spinbox tilt and apertures,
also gave exactly zero differences for all four spectra and coherence. Alpha was
1.0001764206684876. Local artifacts are in `outputs/gui_stage_b/`; the
repeatable comparison writes `default_cli_validation/cli_comparison.json`.

| Model / selected feature | Sigma_ref | D_mag | A_mag |
| --- | ---: | ---: | ---: |
| XMCD L3, 831.271 eV | 0.2481701746 | −9.422031175e−4 | −0.00379660094 |
| XMCD L2, 848.698 eV | 0.1662582163 | +1.022746402e−3 | +0.00615155404 |
| Atomic L3, 852.7 eV | 1.463431066e−5 | +2.456363271e−8 | +0.00167849605 |
| Atomic L2, 870.0 eV | 7.299292676e−6 | −2.445000509e−8 | −0.00334964032 |

These two models have different spectral/operator approximations and scales;
the table is not a quantitative intermodel comparison. At symmetric default
A/B the reversal-even imbalance is numerical roundoff. Nevertheless XMCD
post-edge correction creates residual even terms of −2.189117405e−5 (L3)
and −1.466569283e−5 (L2), demonstrating why corrected is not pure magnetic.

Research limitations remain: projected independent-atom elastic potential,
depth-integrated localized single-ionization approximation, entrance-only
channeling, no outgoing/double channeling, no complete DFT-derived MDFF,
nonquantitative atomic model, no experimental absolute EELS cross-section
normalization, uncertain experimental energy calibration and unresolved
global physical-potential Fourier-cutoff convergence. No broad regression
suite, multislice GUI integration or 43-orientation sweep was performed.
