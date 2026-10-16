# Install EMCD-Sim on Windows

For a first calculation, continue with [Quick Start](QUICK_START.md). The
[User Manual](USER_GUIDE.md) explains the science and controls. This is an
unreleased research application; read the [readiness report](STAGE_G_RELEASE_READINESS.md)
before using it for a research comparison.

## Recommended: portable Windows application

**The standalone Windows application does not require Python, Conda, VS Code
or WIEN2k to be installed.** WIEN2k is a separate electronic-structure program,
not a GUI runtime dependency. This application does not install or provide a
complete DFT calculation environment.

The reviewed candidate is **EMCD-Sim GUI Stage F RC (unreleased)**, package
version **0.4.5**, built from `618789717303cbea246cdb0fbccfe6a44040ecb7`.
Stage G reviews this existing candidate without rebuilding it.

1. Obtain `EMCD-Sim-Stage-F-Windows-RC.zip` from the project maintainer through
   a trusted project-provided transfer location. **It is currently a local
   review artifact, not a published GitHub download.** On the build machine it
   is `build/windows-stage-f/EMCD-Sim-Stage-F-Windows-RC.zip`. There is no public
   binary download URL to follow yet; request the reviewed archive from the maintainer.
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
6. Allow initialization to finish. Previous development-host launches took
   about 24–43 seconds; this is an observation, not a timeout guarantee.
7. Confirm the FCC Ni interface: **Nominal zone [uvw]** `0 1 7`, **Target (hkl)**
   `2 0 0`, indexed reciprocal geometry and physical A/B circles. Startup shows
   geometry; click **Preview diffraction** for calculated elastic intensities.
8. Optionally create a desktop shortcut to the extracted EXE; leave the
   complete application folder in place.

### Verify the archive

The final candidate under review is the accepted Stage F archive, unchanged:

```text
523cc3a087a92b4dc7aa790daeefca3399dbe35d0974ad78c7cbb4913cda9ca8
```

For example, in PowerShell:

```powershell
Get-FileHash "$HOME\Downloads\EMCD-Sim-Stage-F-Windows-RC.zip" -Algorithm SHA256
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
The archive is **108,541,536 bytes** (about 104 MiB); the extracted application
has **608 files**, **261,851,292 bytes** (about 250 MiB). Keep additional space
for projects and exports.

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
The current GUI is on `feat/emcd-desktop-gui`; it has not been merged or
released. Record the commit you use. The local path below is an example,
not a required installation location.

For the existing development Conda environment:

```powershell
conda activate emcd-python
cd C:\Users\peng863\EMCD-Sim
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
| Multislice unavailable | Current verified FFT support is FCC Ni [017]. Use that geometry or explicitly choose **Bloch-wave** where supported. There is no silent method fallback. FFT grids must be even and contain the common basis. |
| Project will not reopen | Select the project folder containing `project.json`, retain all companion files, and check completeness/checksum errors. Use **Import Existing Result** only for legacy B/C exports. Restore a complete backup rather than editing checksums. |
| Saved data viewable but Run disabled | Viewing needs saved arrays; rerunning also needs original source provenance. Use **Results → Locate Original Source...** and **Use These Settings**. Same filename is insufficient: the SHA256 must match. |
| Cannot write output | Choose a writable user folder and a new export/project name; avoid protected installation directories and disconnected drives. Check disk space and log errors. |
| Slow / memory-heavy simulation | Check **Calculation Information** and the memory estimate. Start with the tutorial defaults, use **Cancel** if needed, and change one numerical setting at a time. Estimates are not total peak RAM. |
| Clipped layout at high DPI | Use **Maximize / restore results** or **Maximize / restore viewer**, scroll the canvas/input panel, collapse unused input sections, or use **View → Restore Default Layout**. Export the figure for its complete scientific panels. |

## Scientific scope

This is a projected independent-atom potential with entrance-only,
depth-integrated ionization: no outgoing channeling, full double channeling,
or atom-layer-resolved 3D multislice. XMCD constrains an effective tensor,
not a complete complex DFT MDFF; the atomic model is non-DFT. Absolute cross
sections and the native WIEN2k energy axis are not experimentally calibrated.
GUI FFT support is verified only for FCC Ni [017]. Physical potential
Fourier-cutoff convergence remains unresolved. BW/MS agreement does not
establish that convergence or quantitative EMCD for arbitrary CIF structures.
