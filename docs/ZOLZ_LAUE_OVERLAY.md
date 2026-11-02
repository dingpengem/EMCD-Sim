# Live ZOLZ Laue circle

The diffraction viewer shows the zero-excitation-error circle centered on the
projected zone axis. With the existing cycles-per-length reciprocal convention,
`q_ZA = -tilt_rad / lambda`, the center is `q_ZA` and the radius is `|q_ZA|`,
both in Å⁻¹. No extra 2π factor is used. This follows directly from the existing
`s_g = lambda/2 * (|g - q_ZA|² - |q_ZA|²)` convention.

The circle passes through (000), and through any target with zero excitation
error. At zero tilt it collapses to a point: the ring is hidden and Diffraction
details reports **On zone axis**. It is not an intensity contour, HOLZ ring,
CBED disk or convergence certificate.

## Use

- **Show ZOLZ Laue circle** is enabled by default in Orientation / ZA options.
  Disabling it hides only this overlay.
- Edit either tilt or projected ZA coordinate, align Bragg, reset the geometry,
  or apply another orientation to update the circle without starting a worker.
- In **Set projected ZA** click mode, click as before or hold the left button
  and drag. The existing ZA marker and circle update during motion; release
  applies the final geometry. Detector positions stay unchanged. Matplotlib
  pan/zoom modes take priority over ZA positioning.
- Diffraction details reports the Laue center and radius. Large circles can
  extend outside the viewport; the overlay never changes the zoom to fit itself.
- Export current diffraction PNG/SVG to include the visible overlays.

## Visual convention

| Overlay | Color | Line | Width | Alpha | Z order |
|---|---|---|---:|---:|---:|
| Thales circle (000–target) | teal | dotted | 1.2 | 0.75 | 1 |
| ZOLZ Laue circle (s_g = 0) | darkorange | dashed | 1.8 | 0.95 | 2 |
| Diffraction spots | existing | existing | existing | existing | 3 |
| hkl annotations / transmitted marker | existing | existing | existing | existing | 4 |
| Detector apertures / labels | purple | existing | existing | existing | 5 |
| Projected ZA / target marker | existing | existing | existing | existing | 6 |

Both circles retain their own dash patterns and transparency when coincident.
The same figure artists serve the live canvas and PNG/SVG export.

The checkbox is a session display preference; it introduces no saved-project
field, numerical setting or solver change. Older projects remain readable and
use the enabled overlay by default in a new window. This source feature is not
present in the previously accepted Windows executable until a separate build.

## Focused validation

Implemented from local main `b3edf65e8f539b6f4e37e35b8b35144566b7838a`
in the isolated `feat/zolz-laue-overlay` worktree.

- Overlay, existing Stage A geometry/interactions and physics source guards:
  **19 passed**, no skips or failures.
- Overlay with explicit no-solver guards, existing viewport controls and project
  persistence/compatibility: **32 passed**, no skips or failures.
- Eight overlay cases overlap the runs, giving **43 distinct passing tests**.
  The strengthened guards ran in the second suite. Qt high-DPI deprecation and
  offscreen constrained-layout warnings remain visible in the logs.
- Geometry controls include zero tilt, nonzero X/Y, wavelength changes, exact
  Ni [017] (200) Bragg at both 200 and 300 kV, and zero excitation error at
  101 sampled positions on each circle. GUI checks include [117], click/drag,
  release outside the axes, pan mode, detector moves, basis toggling, unchanged
  viewport/aspect, visibility and actual PNG/SVG exports.
- All three corrected physics kernels retain their approved raw SHA256 values:

| Kernel | SHA256 |
|---|---|
| `single_channeling_tensor.py` | `3c47bd37c8da7ec881441cb9cdee66c537b36b86dd2e5b0838251c04ce9e3d61` |
| `double_channeling.py` | `713945ace6630f95f8b4f461e6c137a8806b60212f744a81aec51cc46fb8f3de` |
| `multislice_double_channeling.py` | `9ec1ba6c071ff751540f9ef4ac4c864d139cb8a458eb85cddc9ad04ba0a880df` |

Local screenshot, PNG/SVG exports, JUnit XML, logs and hash provenance are under
`outputs/laue_overlay/` in the feature worktree, excluded from Git. The screenshot
is the source Qt diffraction panel rendered offscreen at nonzero tilt; it is
not packaged-EXE acceptance. Only `gui/app.py`, this document and the focused
overlay test file are changed. Geometry functions, solver kernels, numerical
defaults, worker policies, saved-project schemas and historical scientific
outputs are untouched. No large calculation or production scan was run.

## Live-drag correction and acceptance

The integration review of `e12f8acbfc929e1c8fadff840528da7dec1dcd99`
identified two GUI defects, both independently reproduced before correction:

1. Motion updated the ZA artists but bypassed cached-result freshness handling,
   leaving a current diffraction tab and old intensity colors for changed inputs.
2. Release refreshed the last motion position without reading release coordinates.

Normal refresh and motion now share `preview_is_current()`, comparing the complete
cached settings, systematic-row mode and structure source identity. During motion,
stale spots become neutral outlines, the diffraction tab/readout/information say
last preview or uncomputed, and completed EMCD views are marked stale. The table
remains explicitly the last completed preview. Cached arrays and results are kept
intact; returning exactly to their configuration restores current status and the
original intensity rendering. Dependent preflight/status checks run on freshness
transitions, not every stale-to-stale motion event. Existing Automatic-mode
refreshes retain valid active positioning without changing the numerical policy.

Motion and release share a finite-coordinate and ±100 mrad validation path using
the existing ZA-to-tilt conversion. An in-axes left-button release applies its own
position before the final refresh. Outside/missing/nonfinite/out-of-range release
coordinates retain the last valid position. An unchanged click or repeated release
does not commit the same position twice. Detector positions and toolbar priority
remain unchanged. No solver or worker starts through these interactions.

The original two review probes first reproduced **2 failures**. After correction,
the targeted set passed **28 tests**. The combined acceptance set passed **63
tests, 0 failures, 0 skips**: the original 43 focused regressions, nine new drag-state
cases and eleven unchanged independent review probes. This includes geometry,
source guards, viewport controls, project save/reopen and real PNG/SVG export.
The run reported 170 Qt high-DPI deprecation/offscreen layout warnings, retained
in the logs; assertions and numerical tolerances were not changed.

Geometry and visual definitions above remain unchanged. At exact Bragg, the Laue
and Thales circles both pass through (000) and the target, but fully coincide only
when `q_ZA = g_target/2`. Perpendicular off-row tilt can preserve `s_g=0` without
complete circle overlap. Controls cover both cases at 200/300 kV for [017] and [117].

Fix evidence is in the feature worktree's ignored `outputs/laue_drag_fix/`.
The isolated integration preview is refreshed separately; actual main remains
unchanged. The three physics-kernel hashes above still apply. No numerical default,
project schema, physical algorithm, scientific output or Windows binary changed.
These are source/offscreen GUI checks, not native packaged-EXE acceptance; a
separately authorized build and native testing remain required for distribution.
