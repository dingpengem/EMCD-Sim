# Windows installation and source setup

[Home](../README.md) | [Quick Start](QUICK_START.md) | [MDFF workflows](MDFF_WORKFLOWS.md) | [User manual](USER_GUIDE.md)

## Choose the correct version

The Windows Research Beta is [v0.8.1-beta.2](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.8.1-beta.2), package version `0.8.1b2`. It includes the MDFF editor redesign and explicit XMCD selection repair. Earlier beta.1 assets and their matching documentation remain available.

## Local v0.9 release candidate

This checkout's [Quick Start](QUICK_START.md) and [User Guide](USER_GUIDE.md) describe the **unpublished v0.9.0-beta.1 candidate**. Use the supplied `EMCD-Sim-v0.9.0-beta.1-Windows-RC1.zip`, its existing checksum file and matching `EMCD-Sim-v0.9.0-beta.1-Corresponding-Source-RC1.zip`; do not look for an unpublished GitHub asset. Extract the complete folder, install the same Microsoft runtime prerequisite below, and keep `_internal` beside the EXE. No development Python environment is needed. Exact source/dependencies are in `_internal/build_info.json` and the existing manifest; clean-PC/VM acceptance remains unverified. The source kit contains both `EMCD-Sim-source.zip` and the matching dependency source/replacement materials. For published v0.8 binaries, the filenames and release links below remain historical version-specific instructions.

## Windows binary installation

On Windows 10/11 x64, first install the **official Microsoft x64 Visual C++ v14 Redistributable, 14.44.35211 or newer**, directly from [Microsoft's runtime page](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) ([official x64 download](https://aka.ms/vc14/vc_redist.x64.exe)). The package includes no Microsoft runtime DLL copies or installer. Windows supplies the UCRT/API sets. A missing `MSVCP140.dll` or `VCRUNTIME140*.dll` means this prerequisite needs installation/repair; do not copy DLLs from download sites.

The accompanying **EMCD-Sim-v0.8.1-beta.2-Qt-sources.zip** supplies matching Qt/PySide/Shiboken sources and [build/replacement instructions](../packaging/assets/qt-licenses/SOURCE_AND_REPLACEMENT.md). It is separate from the runnable ZIP. Qt PDF and Virtual Keyboard are excluded as unused; included dependency licenses remain separate from the application's MIT license.

1. Open the intended version's release page and download its **complete Windows ZIP**. GitHub's automatic source archive and an outer Actions artifact wrapper are not the portable application. Beta.2 supplies `EMCD-Sim-v0.8.1-beta.2-Windows.zip`.
2. Download the checksum file from that same release and compare the matching ZIP entry:

   ```powershell
   Get-FileHash -LiteralPath '.\EMCD-Sim-v0.8.1-beta.2-Windows.zip' -Algorithm SHA256
   Get-Content -LiteralPath '.\SHA256SUMS.txt'
   ```

   Do not reuse an older release's checksum. On mismatch, obtain a fresh copy from the intended release.
3. Use **Extract All...** into a new writable directory. Preserve the complete structure:

   ```text
   EMCD-Sim/
       EMCD-Sim.exe
       _internal/
       README.txt
       ...other bundled files...
   ```

4. Launch the extracted `EMCD-Sim.exe`. Keep every supporting file and `_internal` beside it. Do not run inside the ZIP, copy only the EXE, combine versions, or overwrite an older installation in place.
5. Inspect **Help > About** for version/source identity, then follow the matching [Quick Start](QUICK_START.md).

The Windows x64 package includes Python and required Python/Qt libraries. Binary users do not need Python, Conda, a compiler, WIEN2k, or a pre-existing project JSON. Use writable project directories and sufficient RAM/disk for your configuration; inspect the resource estimate rather than assuming a universal hardware minimum.

The application is unsigned. Verify download origin and follow organizational policy. Native verification is not code signing or SmartScreen certification. Do not disable security protections to launch it.

Current development-package examples include `_internal/examples/Fe_BCC_a2.8665.cif`, `Ni_FCC_a3.52.cif`, their provenance/license information, and `synthetic_fe_atomic_parameters.json`. The atomic example is a **synthetic software demonstration**, not calibrated Fe spectroscopy. The application also selects its bundled five-column Ni XMCD source. These example paths are not a claim that every historical binary has identical contents.

## Create, save, and reopen a project

No project JSON is required at startup. Open a CIF or choose **File > New** for Ni, supply a valid MDFF, choose a small calculation profile, and run. **File > Save Project** asks for a parent directory and new project folder name. The application writes metadata and arrays, including its own project JSON. Reopen the complete folder with **File > Open Project...**; choose **Use These Settings** before rerunning.

Saving a completed numerical result is different from exporting a figure or retaining an uncalculated draft. Keep all project JSON/CIF/NPZ files together. Preserve external XMCD inputs: saved arrays may remain viewable without them, but rerunning requires the matching source. Editor-generated inputs have their implemented portable attachments; arbitrary external files are not universally embedded.

## Source installation

Source use is separate from installing a portable binary. The package requires **Python >=3.10**; the established Windows build uses Python **3.11**. With Git and Python 3.11 available, use PowerShell in a directory appropriate for a new clone:

```powershell
git clone https://github.com/dingpengem/EMCD-Sim.git
Set-Location EMCD-Sim
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[gui]"
.\.venv\Scripts\python.exe -m emcd_sim.gui
```

If `py` is unavailable, use your chosen interpreter's explicit path. Calling the venv interpreter avoids shell activation or execution-policy changes. The installed GUI entry point is also `emcd-gui`.

[pyproject.toml](../pyproject.toml) declares NumPy/Matplotlib and the PySide6/ASE `gui` extra, with their transitive requirements. Developers can install `.[dev,gui]` for tests. [packaging/requirements-windows.txt](../packaging/requirements-windows.txt) pins the established Windows **build** environment, including PyInstaller and `six`; binary users do not install it. The [build procedure](../packaging/README.md) preserves mandatory content/license inventories. Source installation neither certifies another platform nor resolves binary redistribution requirements.

## Platform and verification status

Windows x64 is the tested packaged platform. The `aaa69a1` EXE passed native ambiguity handling, Fe 710/723 eV preview/calculation, application-created saving, restart, reopening, and recalculation on the development host. The rebuilt beta.2 EXE (`88dc9ec`, `0.8.1b2`) also passed the affected native workflow: ambiguous/L3-only rejection, explicit Fe 710/723 eV preview and calculation, normal application-created save, process restart/reopen, restored preview and recalculation. Its Microsoft runtime DLLs loaded from System32 with no dependency-environment paths. Independent clean-PC/VM installation remains **unverified**. Linux/macOS are not supplied or certified; recorded interpreter-shutdown and Qt-modal CI problems remain limitations.

**Current beta.2 validation:** Release source `88dc9ec` passed 21 focused packaging/safeguard checks, and the actual packaged Windows EXE passed the native workflow described above. The earlier XMCD ambiguity failure was corrected in `4f15a4d`, with four focused regression cases passing. A complete full-suite rerun was not performed on the final release. Historical results and the prerelease-specific validation exception are recorded in the [release notes](RELEASE_NOTES_0_8_1_BETA_2.md#validation-evidence-and-scoped-exception).

## Troubleshooting and data locations

| Symptom | Action |
| --- | --- |
| Startup failure or missing DLL/Python/Qt files | Verify and freshly extract the complete ZIP. Check quarantine under local policy; do not mix package versions. |
| Run disabled or preview unavailable | Read the inline reason. Validate source/declarations; ambiguous L2,3 XMCD requires both explicit energies. Check structure/site and geometry eligibility. |
| Stale preview | Update MDFF preview after changing inputs. Elastic **Preview diffraction** is separate. Old curves are snapshots, not permission to execute old input. |
| Source/project verification failure | Preserve original data and locate the matching source. Do not alter metadata to bypass verification. |
| Memory rejection | Inspect requested/effective settings and available RAM. Free memory or explicitly choose a smaller supported configuration; raising a budget does not create RAM. |
| Cramped controls/plots | Resize, scroll, collapse advanced sections, use viewer maximize/restore, or **View > Restore Default Layout**. MDFF configuration scrolls separately. |
| Save failure | Choose a writable directory outside installation and retain the complete project, not only its figure. |

Default application data are in `%LOCALAPPDATA%\EMCD-Sim`: workspace files include `results_index.json` and `ui.ini`, and rotated logs are in `logs\runtime.log`. `EMCD_GUI_WORKSPACE` redirects the workspace, not the application-data log directory. Report exact source/binary identity, settings, relevant input/error, and avoid sharing unrelated private data.

Update into a new directory and retain older projects until compatibility is checked. Earlier v0.6.1 magnetic results used a superseded convention; opening their arrays does not upgrade or revalidate their physics.
