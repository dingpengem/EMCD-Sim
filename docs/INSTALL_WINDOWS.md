# Windows installation and source setup

[Home](../README.md) | [Quick Start](QUICK_START.md) | [MDFF workflows](MDFF_WORKFLOWS.md) | [User manual](USER_GUIDE.md)

## Choose the correct version

The latest published Windows Research Beta is [v0.8.1-beta.1](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.8.1-beta.1). The current-main MDFF redesign is prepared for **v0.8.1-beta.2**, which is **unpublished** while its [redistribution review remains open](RELEASE_NOTES_0_8_1_BETA_2.md#publication-status). The tested local development package is `0.8.1b1`, source `aaa69a1`; renaming it does not make it beta.2.

Use documentation matching your binary. The [published beta.1 installation guide](https://github.com/dingpengem/EMCD-Sim/blob/v0.8.1-beta.1/docs/INSTALL_WINDOWS.md) describes its older interface. New-editor instructions require the local development build or current-main source until a new binary is published.

## Windows binary installation

1. Open the intended version's release page and download its **complete Windows ZIP**. GitHub's automatic source archive and an outer Actions artifact wrapper are not the portable application. Published beta.1 supplies `EMCD-Sim-v0.8.1-beta.1-Windows.zip`.
2. Download the checksum file from that same release and compare the matching ZIP entry:

   ```powershell
   Get-FileHash -LiteralPath '.\EMCD-Sim-v0.8.1-beta.1-Windows.zip' -Algorithm SHA256
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

Windows x64 is the tested packaged platform. The `aaa69a1` EXE passed native ambiguity handling, Fe 710/723 eV preview/calculation, application-created saving, restart, reopening, and recalculation on the development host. Independent clean-PC/VM installation remains **unverified**. Linux/macOS are not supplied or certified; recorded interpreter-shutdown and Qt-modal CI problems remain limitations.

The full `7730e38` run remains **FAILED: 1,191 passed, 1 failed, 54 skipped**. The repair passed four focused cases. The user's prerelease-specific exception permits using this evidence without another complete regression; it does not waive scientific, security, redistribution, or formal publishing requirements. See [draft release notes](RELEASE_NOTES_0_8_1_BETA_2.md).

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
