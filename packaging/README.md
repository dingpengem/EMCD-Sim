# Windows candidate build

Current candidate: **v0.6.1-beta.3 / 0.6.1b3**. Use the existing Conda-backed build venv or the pinned `requirements-windows.txt`.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File packaging/build_windows.ps1 -BuildRoot build/windows-v061-beta3
```

The default archive is `EMCD-Sim-v0.6.1-beta.3-Windows.zip`. Native metadata uses numeric 0.6.1.3 and display v0.6.1-beta.3. Run the extracted EXE with `--desktop-acceptance NEW_OUTPUT_DIRECTORY` for bounded actual BW/MS Single/Double and GUI checks. See [scope and Actions artifacts](../docs/WINDOWS_BETA_3.md). No release/tag is created. Older commands below are historical.


Current source packaging still uses `emcd_gui.spec` and `launcher.py`; all
hidden imports resolve after the [runtime cleanup](../docs/SOURCE_CLEANUP.md).
The source-cleanup stage did not rebuild an executable or ZIP. Older acceptance commands and removed
verification scripts below are historical build records. Current source
acceptance uses the retained GUI/physics tests and native worker/cancellation
diagnostics, not the retired Stage E/F/Beta orchestration modules.


Windows x64 research Beta, package version **0.6.0**. Build the standalone
Double-Channeling EMCD Simulation in a fresh directory; previous 0.4.5
artifacts must remain untouched. Labels, archive names and manifests derive
from the source package version. Publication requires the release acceptance
gates in [the report](../docs/WINDOWS_V060_BETA_ACCEPTANCE.md).

From an environment containing the GUI runtime dependencies:

```powershell
python -m venv --system-site-packages build/windows-rc/venv
build/windows-rc/venv/Scripts/python.exe -m pip install pyinstaller==6.22.3
powershell -NoProfile -ExecutionPolicy Bypass -File packaging/build_windows.ps1 -BuildRoot build/windows-v060-beta-rc -ArchiveName EMCD-Sim-0.6.0-Beta-Windows.zip
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

Historical Stage F defaults were `build/windows-stage-f/dist/EMCD-Sim/` and
`build/windows-stage-f/EMCD-Sim-Stage-F-Windows-RC.zip`, labeled
`EMCD-Sim GUI Stage F RC (unreleased)`. Existing distributions are refused;
use `-BuildRoot` and `-BuildLabel` for a new candidate. Stage E remains untouched.
The current release workflow uses the separate v0.6.0 directory above.

Display-only acceptance reopens existing projects, guards forward calls and
exports derived figures/data (fresh output paths required):

```powershell
EMCD-Sim.exe --stage-f-acceptance C:/F-validation --stage-f-project C:/saved/reference_project --stage-f-comparison C:/saved/mistilt_project
```

This does not invoke the expensive Stage E physics acceptance.
## Local v0.6.1-beta.1 candidate

The local candidate and its scope are documented in
[V061_BETA_ACCEPTANCE.md](../docs/V061_BETA_ACCEPTANCE.md). The existing public
v0.6.0 assets are preserved. Build into a fresh directory:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File packaging/build_windows.ps1 -BuildRoot build/windows-v061-beta-final -BuildLabel 'EMCD-Sim v0.6.1-beta.1 local candidate' -ArchiveName EMCD-Sim-0.6.1-beta.1-Windows-RC.zip
```

Package version `0.6.1b1` uses PEP 440 prerelease notation. Verify archived
content and saved-data native GUI acceptance with
`python scripts/verify_v061_candidate.py`. This does not calculate spectra.
