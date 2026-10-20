# Install EMCD-Sim on Windows

Current package: **EMCD-Sim v0.6.1-beta.1 Windows research Beta**, not a stable release. Continue with [Quick Start](QUICK_START.md), the [User Manual](USER_GUIDE.md), [release notes](RELEASE_NOTES_0_6_1_BETA_1.md) and [acceptance report](V061_BETA_ACCEPTANCE.md).

## Recommended: portable Windows application

The package bundles a Python runtime and is intended to work without a separately installed Python, Conda, VS Code or WIEN2k. Same-host standalone tests with development Python removed from PATH passed. **Independent clean-machine installation has NOT been tested.** WIEN2k is not a runtime dependency, and the package does not supply a complete DFT calculation environment.

1. Open the [GitHub Releases page](https://github.com/dingpengem/EMCD-Sim/releases) and select [v0.6.1-beta.1](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.6.1-beta.1).
2. Download **EMCD-Sim-0.6.1-beta.1-Windows-RC.zip** and **SHA256SUMS.txt** from that release's assets. The validated archive retains its RC filename; it is the selected Beta asset, not GitHub's automatic source-code ZIP.
3. Verify the archive checksum below.
4. Right-click the ZIP, choose **Extract All**, and select a normal writable folder, for example `C:/Users/YourName/Applications/EMCD-Sim-0.6.1-beta.1`.
5. Open the extracted **EMCD-Sim** directory and double-click **EMCD-Sim.exe**. The actual validated ZIP structure is:

   ```text
   EMCD-Sim/
       EMCD-Sim.exe
       README.txt
       SHA256SUMS.txt
       _internal/
           build_info.json
           data/wien2k_ni/Ni_fm.xmcd
           ...
   ```

6. Keep all extracted files together. Do not run inside the ZIP, move only the EXE, or remove `_internal`. There is no MSI or system installer.
7. Let initialization finish before starting another instance. Open **Help → About / build** to inspect package version `0.6.1b1` (PEP 440 spelling of v0.6.1-beta.1), build label and source provenance.
8. **File → New** resets actual angular sampling to **97 x 97** and the process memory budget to **2048 MiB**. Existing projects retain explicit saved settings. Use [Quick Start](QUICK_START.md) for the Ni [017] reference.

### Verify the archive

In PowerShell, substituting your actual download path:

```powershell
Get-FileHash "$HOME/Downloads/EMCD-Sim-0.6.1-beta.1-Windows-RC.zip" -Algorithm SHA256
```

Require an exact match to the release's `SHA256SUMS.txt`:

```text
9fd5e71437d2c26d4595abb7adde9436e4c333ce18f3a57cf381b0c541bfd94f
```

Archive size: **108,703,899 bytes**. The external `SHA256SUMS.txt` verifies the ZIP; the extracted file of the same name lists individual application files. The original validated ZIP has not been rebuilt. Build runtime source revision: `e66c97923bd4838188ed03c424dc9973ada55c25`; subsequent accepted commits changed documentation/acceptance metadata only. Exact runtime hashes and dependency versions remain in `_internal/build_info.json`.

A checksum identifies the archive; it is not a digital signature. The package is **unsigned**. If Windows or institutional security blocks it, check the release origin/checksum and consult your IT policy. Do not disable security protections.

### Projects, workspace and logs

Use **File → Save Project As...** to save a complete project in a writable research folder outside the application. Reopen it with **Open Project**, selecting the whole project folder, or **Results Browser → View Selected**. Keep `project.json` and all NPZ/JSON/CIF companions together. Loading saved results does not run the solvers. **Use These Settings** restores inputs separately; rerunning requires the original matching source hash, while viewing arrays does not.

| Data | Default location |
| --- | --- |
| Workspace, browser index and preferences | `%LOCALAPPDATA%/EMCD-Sim/workspace` |
| Runtime logs | `%LOCALAPPDATA%/EMCD-Sim/logs/runtime.log` |
| Optional workspace override | Environment variable `EMCD_GUI_WORKSPACE` |

The override changes the workspace, not the log directory or existing saved-project locations. Logs can contain local paths and hashes; review them before sharing. No automatic upload occurs.

### Tested Windows environment and size

Local Windows acceptance passed on Windows 11 Enterprise, version 10.0.26200, 64-bit, Intel Core i7-1365U (10 cores / 12 logical processors), approximately 31.58 GiB OS-visible RAM. This host already contains Python/Conda and earlier EMCD-Sim builds. Native frozen saved-project tests cover BW/MS Single/Double, defaults/presets, maps/EELS, projects and exports; detailed scope is in [acceptance](V061_BETA_ACCEPTANCE.md). **Independent clean-machine Windows/VM installation: NOT TESTED.** Signing, SmartScreen reputation and other Windows architectures are not certified.

Memory budgets are 512/1024/**2048 default**/4096/8192 MiB. A budget is a ceiling, not a fixed allocation. Estimated process peak and available RAM are checked independently from the dense kernel. Larger actual angular grids may need more budget, and High 193 is not guaranteed to fit 2048 MiB. The app never silently changes beams, cutoff, grid, energy sampling, depth, slice count or precision to fit. See [resolution guidance](ANGULAR_MAP_RESOLUTION.md); runtime is workload-dependent.

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

## Local Windows development build

Current main includes newer GUI and execution improvements than the published Beta. The local package is under `build/windows-main-dev/`; its ZIP is named `EMCD-Sim-main-dev-<source-short-SHA>-Windows.zip`. It is not a release asset. Extract the complete ZIP: its top-level directory is `EMCD-Sim`, containing `EMCD-Sim.exe`, `README.txt`, `SHA256SUMS.txt` and `_internal/`. The unarchived executable is `build/windows-main-dev/dist/EMCD-Sim/EMCD-Sim.exe` relative to the repository. Keep all files together.

Check the ZIP against `build/windows-main-dev/SHA256SUMS.txt`. **Help → About / build** and `_internal/build_info.json` identify the exact source commit, build timestamp, dependency versions and development label; `build_manifest.json` beside the ZIP records file hashes. The application version remains `0.6.1b1` and alone does not identify this newer development build.

For current Python source, use `python -m pip install -e ".[gui]"`, then `python -m emcd_sim.gui` from the repository. In either current source or the development EXE:

1. Choose physical conditions, MDFF, magnetization and detectors.
2. Select BW/MS/Both and Single/Double Channeling.
3. Keep **Automatic** Numerical Settings; inspect **View Numerical Parameters**.
4. Switch to **Manual (Advanced)** to edit numerical controls if needed. Legacy projects retain their original values in Manual.
5. Choose full spectra and/or selected L3/L2 angular maps, then run once.
6. Inspect Raw/percentage components and save the complete project folder.
7. Reopen saved projects with **File → Open Project** or Results Browser. Viewing does not calculate new results. Use **Use These Settings** separately to restore inputs.
8. Export numerical CSV/NPZ and PNG/SVG figures as described in the [User Manual](USER_GUIDE.md#export-figures-and-data).

Automatic uses configuration and FFT-support checks, not trial calculations or a universal convergence guarantee. Full maps are calculated at selected edge energies; all other requested energies retain exact detector-support integration. Full native spectra are neither interpolated nor replaced by two selected energies. Same-host acceptance of this particular build is recorded separately in the [integration report](GUI_PERFORMANCE_INTEGRATION.md); it does not establish independent clean-machine acceptance.

## Scientific scope of both distributions

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
