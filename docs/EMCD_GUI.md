# EMCD-Sim desktop GUI — Stage A

Stage A is a functional **crystal/orientation and elastic-diffraction GUI**.
It does not yet run EMCD, construct an MDFF, calculate EELS, or propagate
FFT multislice. Those controls/tabs are explicitly disabled for the next
milestones; no synthetic magnetic curves are displayed. Package version
0.4.5 and existing CLI workflows are unchanged.

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
The preview is elastic only: the GUI does not yet use the source magnetization
to calculate an ionization tensor or magnetic signal.

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
No paired-map subtraction or fractional integration is performed in Stage A;
later EMCD integration must use the existing fractional weights and validate
the reflection-bijection assumptions before enabling mirrored pixel maps.

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

Stage B will integrate both MDFF paths with an audited atomic-reversal adapter;
Stage C will wire matched incoming FFT coherences into the existing EELS
contraction; Stage D will add full save/reopen and result registration. They
are intentionally not offered as working calculations in this Stage A report.

The eventual EMCD GUI retains projected IAM, entrance-only ionization,
XMCD-effective rather than complete DFT-derived MDFF, no outgoing channeling,
HOLZ/TDS/absorption, uncalibrated absolute cross sections/energies and unresolved
potential-cutoff convergence. An attractive preview or BW agreement cannot
establish quantitative experimental accuracy. See the [case-study guide](NI_017_CASE_STUDY_GUIDE.md).

Implementation references: [Qt threads](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html),
[Matplotlib Qt canvas](https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_qt_sgskip.html).
