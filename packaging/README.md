# Windows candidate build

Windows only; package version 0.4.5, **EMCD-Sim GUI RC (unreleased)**.
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

Outputs: `build/windows-rc/dist/EMCD-Sim/` and
`build/windows-rc/EMCD-Sim-Windows-RC.zip`. Copy/extract the **whole folder**;
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
