# Install EMCD-Sim on Windows

For a first calculation, continue with [Quick Start](QUICK_START.md). The
[User Manual](USER_GUIDE.md) explains the science and controls. This is an
research Beta; read the [release notes](RELEASE_0_4_5_BETA.md) and [Beta acceptance report](WINDOWS_BETA_RELEASE_ACCEPTANCE.md)
before using it for a research comparison.

## Recommended: portable Windows application

**The standalone Windows application does not require Python, Conda, VS Code
or WIEN2k to be installed.** WIEN2k is a separate electronic-structure program,
not a GUI runtime dependency. This application does not install or provide a
complete DFT calculation environment.

The Windows distribution is **EMCD-Sim 0.4.5 Beta**, tagged `v0.4.5-beta.1`,
built from `9937d3b820e4225fdf06b7f3ed33c7083d0f35ea`. Older Stage F
candidates and the original Beta RC are preserved separately and are not the current build.
See the [cancellation acceptance report](DOUBLE_CHANNELING_CANCELLATION.md) for the replacement.

1. Open the [GitHub Windows Beta release](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.4.5-beta.1) and
   download `EMCD-Sim-0.4.5-Beta-RC-Cancellation-Fix-Windows.zip` from its
   GitHub release assets. The retained RC filename identifies the exact
   tested archive; the distributed bytes were not rebuilt or repacked.
2. Download/copy the ZIP and verify its SHA256 below.
3. Right-click it in File Explorer, choose **Extract All**, and select a folder
   you control, for example `C:\Users\YourName\Applications\EMCD-Sim-RC`.
4. Open the extracted `EMCD-Sim` folder. Keep the EXE and `_internal` together:

   ```text
   EMCD-Sim/
       EMCD-Sim.exe
       _internal/
           build_info.json
           data/
           ...
   ```

5. Double-click **EMCD-Sim.exe**. Do not launch inside the ZIP or copy only the
   EXE elsewhere. There is no MSI or installer to run.
6. Allow initialization to finish; startup time depends on the host and is
   not a fixed timeout guarantee. Do not repeatedly start duplicate instances.
7. Confirm the FCC Ni interface: **Nominal zone [uvw]** `0 1 7`, **Target (hkl)**
   `2 0 0`, indexed reciprocal geometry and physical A/B circles. Startup shows
   geometry; click **Preview diffraction** for calculated elastic intensities.
8. Optionally create a desktop shortcut to the extracted EXE; leave the
   complete application folder in place.

### Verify the archive

The current Beta archive SHA256 is recorded in the
[acceptance report](WINDOWS_BETA_RELEASE_ACCEPTANCE.md) and its sibling
`SHA256SUMS.txt`. The application's own `SHA256SUMS.txt` lists individual
runtime files. The current Beta ZIP SHA256 is:

```text
309438c4a049773a6e99948477c8d52051cd8f1de632a762c795656e6c5a2216
```

For example, in PowerShell:

```powershell
Get-FileHash "$HOME\Downloads\EMCD-Sim-0.4.5-Beta-RC-Cancellation-Fix-Windows.zip" -Algorithm SHA256
```

Substitute the actual download path. A checksum match confirms the archive
matches this reviewed file, not that it has a digital signature. The candidate
is **unsigned**. Windows SmartScreen may warn about it. Check its origin and
checksum and consult your institution's IT policy if blocked; do not disable
Windows Defender or other system security protections.

### Projects, workspace and logs

Save projects and exports in your own writable research folders, outside the
application installation directory. A project is a complete folder, not just
one NPZ file. Back up that folder and the original external source files.

`gui/runtime.py` resolves defaults as follows:

| Data | Default |
| --- | --- |
| Workspace, browser index and UI preferences | `%LOCALAPPDATA%\EMCD-Sim\workspace` |
| Rotating runtime logs | `%LOCALAPPDATA%\EMCD-Sim\logs\runtime.log` |
| Advanced workspace override | `EMCD_GUI_WORKSPACE` |

If `LOCALAPPDATA` is unavailable, the fallback is the user's home
`.local\share\EMCD-Sim`. The override changes the workspace, not the log
directory. It does not relocate already saved projects or copy their inputs.
For a one-session override:

```powershell
$env:EMCD_GUI_WORKSPACE = 'D:\EMCD-Projects\workspace'
& 'C:\Users\YourName\Applications\EMCD-Sim-RC\EMCD-Sim\EMCD-Sim.exe'
```

Choose an existing writable parent or a location the application can create.
Logs can contain local input paths and hashes; review them before sharing.
There is no automatic upload.

### Tested Windows environment and size

The x64 candidate was tested on **Windows 11 Enterprise, build 26200.9457**,
Intel Core i7-1365U, approximately 31.58 GiB host RAM, at 150% display scaling.
The current archive is **108,689,021 bytes (103.65 MiB)**. Provenance and
checksums are in the [release report](RELEASE_0_4_5_BETA.md). Earlier Stage F
sizes are not measurements of this new build. Keep additional space for
projects and exports.

Earlier accepted default workloads peaked near **297 MiB process working
set** and took roughly 49–119 seconds for XMCD BW/MS/Both; timing varied
between runs. Larger grids and beam sets can require substantially more RAM
and time. These are measurements, **not minimum hardware requirements**.
The dense contraction has a memory guard; do not bypass it by blindly enlarging
beam and detector grids. Calculations can take tens of seconds or longer.

Other Windows versions, ARM/32-bit systems and native 100%/125% display settings
have not been validated for this binary. A fresh extraction launched outside
the repository with Python/Conda removed from PATH passed on the same host.
**NOT TESTED — independent clean-machine validation pending.** This is not
equivalent to a second Windows installation or a clean VM.

## Advanced: run from Python source

Obtain the source repository from [dingpengem/EMCD-Sim](https://github.com/dingpengem/EMCD-Sim).
The current GUI is integrated into `main`; the Beta tag identifies its release
source. Record the commit you use. The local path below is an example,
not a required installation location.

For the existing development Conda environment:

```powershell
conda activate emcd-python
cd C:\Research\EMCD-Sim
python -m pip install -e ".[gui]"
python -m emcd_sim.gui
```

The established `emcd-python` Python 3.11.17 environment and source GUI launch
have been exercised; Stage G acceptance uses its interpreter explicitly.
The environment was reused, not recreated from scratch in Stage G.

For a new Python installation, the package declares Python **>=3.10**;
Python **3.11 x64** matches the tested major/minor version. From an extracted
source tree, for example `C:\Research\EMCD-Sim`:

```powershell
cd C:\Research\EMCD-Sim
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[gui]"
.\.venv\Scripts\python.exe -m emcd_sim.gui
```

This clean-venv recipe is **NOT TESTED in a new environment in Stage G**.
It invokes the venv interpreter directly, without changing PowerShell's
execution policy. Internet access or an approved package mirror is needed to
install dependencies. The GUI extra installs PySide6 and ASE alongside the
NumPy/Matplotlib base dependencies and their dependencies. Pytest is optional
development tooling (`.[gui,dev]`); PyInstaller is for maintainers building a
candidate, not for users running from source. Neither route requires WIEN2k.

## Troubleshooting

| Symptom | Practical check |
| --- | --- |
| No window | Wait through initialization; confirm full extraction and EXE/_internal adjacency. Check `runtime.log` if created. If import fails before logging starts, report the Windows error and checksum to the maintainer. |
| Slow startup | First starts can include filesystem/security scanning. Do not repeatedly launch copies. Compare with the host observations above, without treating them as a fixed timeout. |
| Missing DLL / Qt plugin | Extract the complete trusted ZIP again into a fresh folder and retain its structure. Do not download individual DLLs from unrelated sites. Report the exact message. |
| CIF import fails | Use **Load CIF…**, inspect the error and supplied cell/occupancies. A periodic nonsingular cell is required; compare with a known conventional Ni CIF. Structure import is separate from supported scattering. |
| Missing/invalid XMCD | In **D. MDFF Model**, use **Browse XMCD...**, then **Validate source / native features**. A valid five-column source and explicit convention declaration are required. Select the bundled example or the original matching input. |
| Unsupported crystal for EMCD | Reciprocal indexing can be available even when IAM/MDFF support is absent. Current MDFF calculations require the verified conventional FCC Ni cell, a=3.524 Å. Do not reinterpret another element as Ni. |
| Multislice unavailable | Verified FFT support is FCC Ni [017] or the explicit [001] (200) systematic-row approximation. There is no silent fallback. FFT grids must be even and contain the exact common basis. |
| Project will not reopen | Select the project folder containing `project.json`, retain all companion files, and check completeness/checksum errors. Use **Import Existing Result** only for legacy B/C exports. Restore a complete backup rather than editing checksums. |
| Saved data viewable but Run disabled | Viewing needs saved arrays; rerunning also needs original source provenance. Use **Results → Locate Original Source...** and **Use These Settings**. Same filename is insufficient: the SHA256 must match. |
| Cannot write output | Choose a writable user folder and a new export/project name; avoid protected installation directories and disconnected drives. Check disk space and log errors. |
| Slow / memory-heavy simulation | Check the separate dense-kernel and estimated process-peak values. Budgets are 512/1024/2048(default)/4096/8192 MiB, with a 50%-of-available-RAM guard. Estimates are not measured peaks. Settings are never silently reduced. |
| Clipped layout at high DPI | Use **Maximize / restore results** or **Maximize / restore viewer**, scroll the canvas/input panel, collapse unused input sections, or use **View → Restore Default Layout**. Export the figure for its complete scientific panels. |

## Scientific scope

This uses projected IAM potentials. Single is entrance-only; Double includes
incoming, depth-distributed ionization and reduced-energy outgoing channeling.
The GUI does not implement atomic-3D electrostatic multislice. Longitudinal
transfer remains branch-frozen. XMCD constrains an effective tensor,
not a complete complex DFT MDFF; the atomic model is non-DFT. Absolute cross
sections and the native WIEN2k energy axis are not experimentally calibrated.
GUI FFT supports [017] and the explicit [001] row approximation; these are
distinct physical bases. Representative convergence controls do not establish
convergence at every thickness, geometry or energy, or quantitative
experimental EMCD for arbitrary CIF structures. Absolute intensities are
arbitrary units, without electron-count/SNR calibration.
