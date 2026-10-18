# Windows candidate build

Prepared source version **0.6.0**, Double-Channeling EMCD Simulation (unpublished).
No 0.6.0 build has been made. The commands below are for a separately authorized
future acceptance/packaging milestone. Default labels, archive name and manifest
version derive from the source package version; the published 0.4.5 ZIP is intact.
No installer, signing or publication is performed.

From an environment containing the GUI runtime dependencies:

```powershell
python -m venv --system-site-packages build/windows-rc/venv
build/windows-rc/venv/Scripts/python.exe -m pip install pyinstaller==6.22.3
powershell -NoProfile -ExecutionPolicy Bypass -File packaging/build_windows.ps1
```

The separate build venv shares scientific packages without modifying them.
The spec uses explicit GUI imports and normal dependency hooks, rather than
whole-environment collection. It includes NumPy/SciPy native libraries, Qt
platforms, Agg/QtAgg, Matplotlib resources, ASE CIF support and its space-group table, licenses, build
provenance and only the Git-tracked five-column Ni example. The modified
working copy, WIEN2k companions and simulation outputs are excluded. Git is
needed to build, not to run. Conda-backed builds explicitly supply base
OpenSSL/Expat DLLs.

Historical Stage E outputs: `build/windows-rc/dist/EMCD-Sim/` and
`build/windows-rc/EMCD-Sim-Windows-RC.zip`. The command now defaults to the
separate Stage F paths below. Copy/extract the **whole folder**;
keep `_internal` beside the EXE. User files belong outside the program folder.

Opt-in native acceptance uses actual widgets and numerical workers:

```powershell
EMCD-Sim.exe --rc-acceptance C:/RC-validation --rc-source C:/inputs/Ni_fm.xmcd
EMCD-Sim.exe --rc-acceptance C:/RC-validation --rc-reopen
```

Use a fresh calculation directory. Six model/method combinations and one
mistilt produce real exports and saved projects. A second process reopens,
checks fingerprints, compares saved tilts, exports PNG/SVG/NPZ and checks
missing sources. Reports contain local provenance paths; nothing is uploaded.

Use the comparison tab's **Export NPZ/CSV** action for CSV spectra and scalar
metrics. The build command above uses a process-only script-policy override;
it does not change the user or machine execution policy.


Stage F uses the same specification in a fresh location:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File packaging/build_windows.ps1
```

Defaults are `build/windows-stage-f/dist/EMCD-Sim/` and
`build/windows-stage-f/EMCD-Sim-Stage-F-Windows-RC.zip`, labeled
`EMCD-Sim GUI Stage F RC (unreleased)`. Existing distributions are refused;
use `-BuildRoot` and `-BuildLabel` for a new candidate. Stage E remains untouched.
Package version is unchanged.

Display-only acceptance reopens existing projects, guards forward calls and
exports derived figures/data (fresh output paths required):

```powershell
EMCD-Sim.exe --stage-f-acceptance C:/F-validation --stage-f-project C:/saved/reference_project --stage-f-comparison C:/saved/mistilt_project
```

This does not invoke the expensive Stage E physics acceptance.
