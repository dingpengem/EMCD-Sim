# EMCD-Sim v0.6.1-beta.3 Windows candidate

Package version: **0.6.1b3**. Display/ProductVersion: **v0.6.1-beta.3**.
Windows numeric file/product version: **0.6.1.3**, marked prerelease.
This candidate is distributed through [Windows Beta candidate Actions](https://github.com/dingpengem/EMCD-Sim/actions/workflows/windows-build.yml).
No Beta 3 GitHub Release or Git tag is created. Historical releases and assets remain unchanged.

## Download and install

Select a successful run for the source commit you want, download the
`EMCD-Sim-v0.6.1-beta.3-Windows` artifact, then extract its contained
`EMCD-Sim-v0.6.1-beta.3-Windows.zip`. Verify that ZIP against the accompanying
`SHA256SUMS.txt`. Open `EMCD-Sim/EMCD-Sim.exe`; keep `_internal` beside it.
Actions artifacts require GitHub sign-in and expire according to retention.
A pending/failed workflow is not a validated downloadable candidate.

The ZIP bundles its runtime. Python/Conda/WIEN2k activation is unnecessary.
The app is unsigned; independent clean-machine acceptance remains **NOT TESTED**.
About/build identifies the exact source commit, versions and runtime hashes.
The artifact also contains `build_manifest.json` and a frozen `acceptance.json`.
These identify build UTC, Python, PyInstaller, dependencies, environment,
archive integrity and the actual acceptance results. Separate builds can have
different ZIP hashes; use each build's own checksum.

## Responsive scientific layout

Settings, interactive Diffraction and Results share an adjustable horizontal
splitter, initially 30% / 35% / 35%. Settings and Diffraction stay visible
together. Drag splitters to give a plot more width. Below 1050 logical pixels,
Results can become a labeled strip; click it once to restore Results.
The existing scientific result-view tabs remain inside the Results panel.

Chevron headers collapse existing widgets without recalculation. Sections
include crystal/geometry options, advanced MDFF, elastic/sampling controls,
computational resources, resource estimates, diffraction details, result
diagnostics/navigation/export, PRB benchmarks and the entire bottom Project
Results browser. Tilt X/Y, Tilt Step and common Bragg controls stay accessible.
Splitters, window geometry and section states persist in GUI preferences,
independently of scientific projects. Restore Default Layout resets splitter
preferences. Invalid preferences safely fall back to defaults.

Narrow Results panels stack magnetic/nonmagnetic maps. Compact plot captions
keep full context under Details; exports restore full captions and readable
dimensions. Actual arrays, grids, energies, detector outlines and overlays
remain unchanged. Large legacy diagnostics can still need extra panel width
or collapsed controls. Native Qt DPI handling and resize debounce are retained.

## Defaults and scientific scope

Defaults remain 300 kV, beam/potential cutoffs **3.2/2.5 cycles/Angstrom**,
97x97 angular sampling, 2048 MiB memory budget, Automatic numerical settings,
and Automatic worker selection. Windows BW Double keeps one detector worker
by default; no global BLAS thread policy is changed. Saved projects preserve
their explicit parameters. This candidate does not change scattering physics.

Acceptance covers focused GUI/version checks, same-host executable launch,
About, layouts, tilt/preview interaction, tiny real BW/MS Single/Double jobs,
saved-project reopening, raw/percentage display and PNG/SVG/CSV/NPZ exports.
The opt-in command is `EMCD-Sim.exe --desktop-acceptance NEW_OUTPUT_DIRECTORY`.
It deliberately uses a 1 nm, small-basis, 9x9 selected-energy profile and
records all settings. It is not a production convergence benchmark. CI uses
offscreen Qt geometry; logical-size tests are not physical multi-monitor DPI
acceptance. Local native acceptance and CI acceptance have separate reports.

Production checkpoint integrity is checked without regeneration. No full
thickness or voltage scan is required for this GUI candidate. Retained model
limits include projected IAM potentials, incomplete DFT-derived MDFF,
uncalibrated native energy/intensity scales, arbitrary-unit detectability,
and convergence established only for previously tested representative cases.
See the [User Manual](USER_GUIDE.md) and [scientific analysis](NI_EMCD_THICKNESS_SCIENTIFIC_ANALYSIS.md).
