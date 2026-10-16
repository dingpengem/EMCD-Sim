# EMCD-Sim desktop GUI - Stage C

Stage C adds independent **FFT multislice incoming-wave EMCD/EELS** and
**Both (BW/MS comparison)** to the existing Stage A/B application. Both
XMCD-constrained and non-DFT atomic Ni MDFF models are supported. The default
remains Bloch-wave. FFT support is gated to the verified FCC Ni [017] projected
geometry. Full history/reopening remains Stage D. Package version 0.4.5 and
existing CLI workflows are unchanged.

![Actual native Windows BW/MS comparison](images/gui/stage_c_windows.png)

The Stage C screenshot shows actual default [017] magnetic maps, numerical
solver differences and full EELS overlays. The following Stage B/A sections
retain their original workflows and milestone screenshots; the final Stage C
section explains the new propagation and comparison controls.

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

Stages B and C are implemented. Stage D full save/reopen and result
registration are not enabled.

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

## Stage C: independent incoming multislice and comparison

Select **E. Propagation Method**:

- **Bloch-wave** preserves Stage B propagation and numerical results for
  identical settings. Other supported pure-Ni orientations remain available,
  subject to the original finite-basis and memory gates.
- **FFT Multislice** executes the existing real-space split-step propagator;
  it does not evaluate a BW Hamiltonian as a substitute.
- **Both (BW / MS comparison)** computes independent BW and FFT wavefields on
  identical depth nodes, then applies the same already-constructed ±M tensors,
  fractional apertures and EELS/parity/post-edge contraction to each coherence.

Expand **Multislice numerical settings** for FFT size (default **32**, even
12–128) and maximum slice step (default **0.04 nm**, 0.001–1 nm). The existing
64 depth nodes, voltage, thickness, tilt, beam cutoff, physical potential
cutoff and Debye–Waller B are shared. Switching solvers does not change those
physical parameters or move detectors. Runs exceeding 200000 split steps are
rejected rather than silently coarsened.

**Verified FFT orientation: FCC Ni [017] only.** The existing oriented cell
has local x=[100], y=[0,7,−1]/sqrt(50), z=[0,1,7]/sqrt(50). The projected mesh
maps FFT indices (m,n) to actual cubic hkl=(m,7n,−n), includes FCC selection
rules, and uses the same IAM Fourier coefficients, cutoff and B as BW. It is
not the old even-only [001] projected potential. The complete requested finite
2D BW basis remains in propagation; exact (200) Bragg does not imply an
isolated two-beam wavefield. Both MDFF models retain crystal-[001] magnetization
and their existing crystal-to-local tensor rotation and reversal rules.

[001], [710], arbitrary zone axes and general CIF FFT meshes are not enabled
in this milestone. Unsupported requests give an explicit explanation; there
is no automatic BW fallback or cutoff alteration. The conservative Stage B
material/site gate still applies. Exact common hkl inclusion, reciprocal
coordinates and potential coverage below the FFT boundary are checked before
propagation. The GUI shows common beam count, full FFT harmonic count and
nonzero physical-potential harmonic count.

FFT coefficients are the raw complex `fft2(wave)/N²` values projected by exact
integer hkl lookup. No conjugation, sign reversal, amplitude renormalization
or matching factor is applied. Excluded population is the sum over FFT modes
outside the common basis, recorded at every depth. Consequently the projected
FFT coherence need not have unit trace. Each propagator runs once per run and
its trapezoidal depth coherence is reused across the full spectrum, both edges
and both magnetic states. Methods contract sequentially, retaining only
selected L3/L2 maps and full detector spectra.

### Stage C result views

- **EMCD Angular Maps:** select BW, MS or **BW−MS numerical difference**, L3/L2,
  and either the six-field layout or one field. Physical BW/MS maps share
  signed color limits across methods and edges for each field. Difference
  maps retain actual intensity units and are explicitly numerical differences.
- **Virtual Detector EELS:** choose BW, MS or an overlay; BW is solid, MS dashed,
  with corresponding curves in matching colors. Full/L3/L2 views, curve
  toggles, native source axis, selected-energy markers and correction-window
  shading remain. Neither solver is peak-normalized or refitted. Alpha is
  obtained separately from each method's observed +M A/B spectra; it is not
  optimized to match methods. Raw magnetic and even signals remain available.
- **BW/MS Diffraction:** switch methods or BW−MS differences, and exit
  intensity versus depth-averaged intensity `diag(C)`. Indexed spots use the
  exact common hkl basis. Full FFT indexing/exit intensities and excluded
  population are also exported. Marker size visualizes discrete intensity;
  it is not a physical CBED disk. Exit diffraction alone does not describe the
  internal depth-dependent wavefield.
- **BW/MS Overview:** displays magnetic L3 BW/MS maps and their numerical
  difference alongside full detector EELS, intrinsic magnetic difference and
  raw/corrected A−B overlays. The difference colorbar may use its own actual
  signed scale to resolve small errors; the two physical maps share limits.
- **Magnetic / Nonmagnetic:** retains signed edge metrics for each method and
  adds amplitude, coherence, elastic, spectral and selected-map discrepancies,
  FFT norm error and common-basis leakage. Absolute errors accompany relative
  errors. Near-cancelled magnetic/even references give `null`/undefined relative
  errors, not a fabricated zero. Complex global-phase alignment is reported
  only as a diagnostic and is never applied to propagated amplitudes or C.

All reciprocal views preserve (000), indexed hkl, target, projected ZA, Thales
circle and physical A/B apertures using the completed snapshot. Results become
stale when inputs change. Manual nonmirrored detectors still give direct EELS
and reversal decomposition; mirrored paired maps require the original exact
physical-pair check. Post-edge correction remains processed magnetic plus
residual even contamination, not a pure magnetic signal.

The worker reports propagation, projection, coherence and per-method EELS
stages with indeterminate progress. Cancellation is cooperative between stages
and contraction calls; it waits for an active FFT propagation/kernel call to
finish. A cancelled/failed Both run never replaces the previous completed
result with a partial BW result. No numerical stage mutates live inputs.

### Stage C memory, export and validation

The GUI reports one complex pixel×beam×beam array separately from the
conservative dense working estimate (four such arrays), FFT storage/scratch,
coherence temporaries and an aggregate array estimate. Dense working estimates
above **512 MiB** or aggregate estimates above **1024 MiB** are rejected. These
are array estimates, **not a complete peak process/RSS measurement**. The
physical potential is never simplified silently to pass a memory check.

The Stage B top-level result keys remain a primary-method view: BW when present,
otherwise MS. `methods['bloch']` and `methods['fft-multislice']` contain explicit
independent maps, spectra, coherence and complex amplitudes. Diagnostics live
in `comparison`; method results do not recursively contain the collection.

Export retains the Stage B files and adds:

```text
diffraction_pattern.npz
comparison_metadata.json
bw_ms_comparison.png                 # Both only
L3_bw_minus_ms.png, L2_bw_minus_ms.png
bloch/, fft-multislice/               # Both: separate method PNG/NPZ/metadata
```

Top-level angular/EELS NPZs preserve unprefixed primary-method arrays and add
explicit `method_labels`, `method__field` / `method__edge__field` names. Maps
are (qy,qx), spectra (energy), amplitudes (depth,ordered common beam). Diffraction
NPZ includes full FFT amplitudes, hkl, reciprocal vectors, exit intensity,
norm/excluded-population histories, common-method exit/depth-average intensities
and complex-wave diagnostic arrays. All NPZs load without pickle. Comparison
JSON records the schema, actual solver settings, source/model/geometry provenance
and signed edge metrics. Primary and per-method outputs are unambiguous;
Both-mode physical map PNGs use shared color limits. Exports are explicit new
folders, without a Stage D database, reopen browser or installer.

Focused checks and native Windows milestone:

```powershell
python -m unittest discover -s tests -p 'test_gui_stage_*.py'
# Normal native Qt platform, not QT_QPA_PLATFORM=offscreen:
python scripts/gui_stage_c_validation.py
```

The native script runs both MDFF selections with BW-only, MS-only and Both at
200 kV, 30 nm, default exact (200) Bragg, crystal-[001] M, beam cutoff 3.2,
potential cutoff 2.2 cycles/angstrom, FFT32, depth64, maximum step 0.04 nm,
33×33 detector grid and 243 sampled energies. It saves actual window captures,
exports and matched standalone numerical checks under `outputs/gui_stage_c/`.
It verifies identical spectra between each standalone GUI choice and its
Both-mode counterpart, then independently runs the established standalone
[017] FFT/complex projection and BW numerical paths with identical controls.
No 43-orientation sweep or broad regression suite is run.

**Scientific scope:** this is depth-resolved propagation through a
z-independent projected potential followed by localized incoming-channeling
ionization. The post-ionization electron is not propagated through the
remaining specimen. There is no atom-layer-resolved 3D potential, outgoing
channeling, double channeling, new DFT tensor or calibrated absolute cross
section. Excellent BW/MS agreement at one fixed cutoff demonstrates numerical
agreement of incoming propagators; unresolved physical Fourier-potential
cutoff sensitivity and MDFF/energy-calibration limitations remain. It does
not establish physical convergence or quantitative experimental Ni EMCD.

### Stage C measured default results

All **25 focused GUI tests pass** (Stage A: 6, B: 10, C: 9). They cover the
actual [017] IAM coefficient correspondence, exact complex FFT hkl projection,
no forced normalization, Hermitian/PSD coherences, one tensor construction per
comparison, unchanged BW output, both MDFF paths, parity and aperture-integral
identities, manual detectors, shared scales, pickle-free exports, unsupported
geometry/mesh/memory rejection, method switching, and preservation of the last
completed result on failure/cancellation. The existing atomic transition-level
hole/exchange reversal is unchanged. Small calculations are used for these
checks; native acceptance uses the full default numerical controls above.

The six native Windows runs and independent standalone checks passed. All
four A/B ±M spectra were **bitwise identical** to their corresponding
standalone numerical path for both MDFF models. BW-only and MS-only results
were also bitwise identical to the corresponding method in Both. The actual
Stage C BW default spectra match the previous Stage B native run exactly.

| MDFF / edge | Method | Sigma_ref | D_mag | A_mag |
| --- | --- | ---: | ---: | ---: |
| XMCD L3, 831.271 eV | BW | 0.2481701746 | −9.422031175e−4 | −0.00379660094 |
| XMCD L3 | MS | 0.2481709356 | −9.425438672e−4 | −0.00379796234 |
| XMCD L2, 848.698 eV | BW | 0.1662582163 | +1.022746402e−3 | +0.00615155404 |
| XMCD L2 | MS | 0.1662587268 | +1.023116340e−3 | +0.00615376023 |
| Atomic L3, 852.7 eV | BW | 1.463431066e−5 | +2.456363271e−8 | +0.00167849605 |
| Atomic L3 | MS | 1.463435561e−5 | +2.457251799e−8 | +0.00167909805 |
| Atomic L2, 870.0 eV | BW | 7.299292676e−6 | −2.445000509e−8 | −0.00334964032 |
| Atomic L2 | MS | 7.299315123e−6 | −2.445885073e−8 | −0.00335084187 |

The models have different physical approximations and intensity scales; their
rows are not an absolute intermodel comparison. Default even detector imbalance
is roundoff-level, so its relative BW/MS discrepancy is undefined. XMCD alpha
is **1.0001764206684878 (BW)** and **1.0001764839635159 (MS)**. Atomic correction
is disabled by default; no XMCD post-edge window is imposed on it.

For these default runs, common elastic/coherence diagnostics are identical
between MDFF choices because propagation is reused independently of the tensor:

- Maximum raw complex-amplitude discrepancy: **6.2740e−5**.
- Coherence Frobenius absolute/relative discrepancy: **2.1216e−5 / 3.0737e−5**.
- Exit elastic-intensity maximum absolute / relative L2 discrepancy:
  **1.9941e−5 / 2.8484e−5**.
- Largest L3/L2 magnetic-map relative L2 discrepancy across both models:
  **3.7063e−4 (0.0371%)**.
- Largest magnetic detector-difference relative discrepancy:
  **3.6165e−4 (0.0362%)**.
- FFT norm error: **1.7097e−14**; maximum excluded common-basis population:
  **1.4443e−7** (exit **1.9117e−8**). Projection is not renormalized.

Detailed default reports and numerical exports remain local at
`outputs/gui_stage_c/windows_20261016_000116/validation.json` and its six case
folders. The committed screenshot is a genuine native Qt view of those
completed numerical results. Layout-only recapture uses the saved arrays;
it does not rerun or change scattering calculations. All previous [017]
results are preserved. These discrepancies characterize matched numerical
methods at the stated potential cutoff, not a new physical convergence claim.
