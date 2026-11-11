# Install EMCD-Sim on Windows — beta.2 candidate and published beta.1

[Home](../README.md) · [Quick Start](QUICK_START.md) · [Tutorial](TUTORIAL.md) · [User Guide](USER_GUIDE.md)

## Ordinary packaged use

**Beta.2 is an unpublished candidate**, supplied separately as
`EMCD-Sim-v0.9.0-beta.2-Windows-RC1.zip` with its matching
`EMCD-Sim-v0.9.0-beta.2-RC1-Qt-sources.zip`. There is no beta.2 release/tag to
download yet. Extract the complete candidate into a new writable directory and
launch `EMCD-Sim.exe` beside `_internal`, as in steps 3–6 below. Candidate files
do not update an existing installation automatically. Offline guides are under
`_internal/documentation/docs/`; the source kit also contains them and their
illustrations. See [candidate status](RELEASE_NOTES_0_9_0_BETA_2.md).

For the **published** [v0.9.0-beta.1 Windows Research Beta](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.9.0-beta.1),
use the download steps below and its [tagged Quick Start](https://github.com/dingpengem/EMCD-Sim/blob/v0.9.0-beta.1/docs/QUICK_START.md).
Both are research software, not quantitatively calibrated stable releases.

1. Download **[EMCD-Sim-v0.9.0-beta.1-Windows.zip](https://github.com/dingpengem/EMCD-Sim/releases/download/v0.9.0-beta.1/EMCD-Sim-v0.9.0-beta.1-Windows.zip)** from that release's **Assets**. GitHub's automatic “Source code” archive and the Corresponding-Source ZIP are not the runnable application.
2. Download **[SHA256SUMS.txt](https://github.com/dingpengem/EMCD-Sim/releases/download/v0.9.0-beta.1/SHA256SUMS.txt)** from the same release. Optional PowerShell verification:
   ```powershell
   Get-FileHash -LiteralPath '.\EMCD-Sim-v0.9.0-beta.1-Windows.zip' -Algorithm SHA256
   Get-Content -LiteralPath '.\SHA256SUMS.txt'
   ```
   Compare the matching filename's entry. On mismatch, obtain a fresh copy from the intended release.
3. On Windows 10/11 x64, install or repair the **official Microsoft x64 Visual C++ v14 runtime, 14.44.35211 or newer** if needed: [Microsoft instructions](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist), [official x64 installer](https://aka.ms/vc14/vc_redist.x64.exe). The runtime/installer is external to this package. Do not obtain individual DLLs from download sites.
4. Right-click the Windows ZIP and choose **Extract All…** into a new writable folder. Extract the **complete folder**, preserving:
   ```text
   EMCD-Sim/
       EMCD-Sim.exe
       _internal/
       README.txt
       SHA256SUMS.txt
       ...other supplied files...
   ```
5. Open that extracted folder and double-click **EMCD-Sim.exe**. Keep `_internal` beside the EXE. Do not launch inside the ZIP, copy only the EXE, mix versions, or overwrite an older installation in place.
6. Check **Help → About**, then follow [Quick Start](QUICK_START.md) or the complete [Tutorial](TUTORIAL.md). Save projects in a writable directory outside the installation.

**Packaged users do not install Python, Conda, a compiler or WIEN2k, and do not set OpenBLAS/OMP variables.** The package includes its Python/Qt dependencies. The application manages supported BLAS runtimes during calculations and verifies its thread limits. Choose worker counts in the GUI and inspect its CPU/memory estimate.

The executable is unsigned; native acceptance is not code signing or SmartScreen certification. Follow organizational security policy rather than disabling protections. Independent clean-PC/VM acceptance remains unverified.

## Examples and matching sources

The complete Windows folder includes:

| Input | Path relative to the extracted EMCD-Sim folder |
| --- | --- |
| Verified illustrative FCC Ni, **3.520 Å**, four sites | `_internal/examples/Ni_FCC_a3.52.cif` |
| Five-column Ni source used by the representative tutorial | `_internal/data/wien2k_ni/Ni_fm.xmcd` |
| Synthetic BCC Fe and Atomic demonstration | `_internal/examples/Fe_BCC_a2.8665.cif`, `synthetic_fe_atomic_parameters.json` |
| Inverse-spinel Fe₃O₄ structure | `_internal/examples/Fe3O4_inverse_spinel.cif` |

These are software examples, not experimental material calibration. The built-in Ni default is **3.524 Å**; importing the tutorial's 3.520 Å CIF is intentional. Source-checkout links and the representative 243-energy/97×97 settings are in [Tutorial](TUTORIAL.md#1-import-the-verified-ni-input).

The published beta.1 **[Corresponding-Source ZIP](https://github.com/dingpengem/EMCD-Sim/releases/download/v0.9.0-beta.1/EMCD-Sim-v0.9.0-beta.1-Corresponding-Source.zip)** remains available unchanged. For the beta.2 candidate use its separately supplied matching source ZIP, not this older application snapshot. Each kit contains `EMCD-Sim-source.zip`, guides/illustrations and matching Qt/PySide/Shiboken sources. The unchanged Qt 6.12 [technical replacement guide](https://github.com/dingpengem/EMCD-Sim/blob/feat/windows-adaptive-compute/packaging/assets/qt-licenses/SOURCE_AND_REPLACEMENT.md) retains historical beta.1 names; the candidate kit's README identifies its actual package and source commit. Dependency licenses apply separately from the application MIT license. Unused Qt PDF/Virtual Keyboard components remain excluded. The existing manifest and `_internal/build_info.json` identify the exact source and dependencies. No independent clean-PC/VM validation is implied.

## Projects, updates and troubleshooting

Use **File → New Project**, **Open Project…**, **Save**, **Save As…**, and **Close Project**. No manually prepared JSON is required. **Save/Save As…** creates a complete project folder; **Open Project…** selects that folder. In the lower **Project Results** panel, select a run to **View Results** or **Restore Settings from Selected Run…**. Restoring settings is distinct from viewing an older result.

Retain every project file and required external source. Saved arrays remain viewable when a source is unavailable, but rerun requires a matching validated source. Editor-managed attachments are portable where implemented; arbitrary spectroscopy sources are not universally embedded. Update into a new application directory and preserve older projects.

| Symptom | Action |
| --- | --- |
| Missing `MSVCP140.dll` / `VCRUNTIME140*.dll` | Install/repair the official Microsoft runtime above. |
| Missing Python/Qt files or startup failure | Freshly extract the complete ZIP. Inspect quarantine under local policy; do not combine versions. |
| Run disabled | Read the complete inline reason. In the active Global/group context, validate source, conventions, frames and coverage; finish **Done → Apply and Close**. |
| “Inactive — Global mode” on a local row | That row is not used by Global mode. Check the accepted Global provider, not the inactive row. |
| Stale result notice | Distinguish changed working inputs from the displayed saved run. Missing/changed sources need resolution; do not bypass validation. |
| Memory admission rejected | Review effective beams, energies, angular support and workers. A larger budget does not create RAM. |
| Crowded view | Resize/scroll or use **Maximize / restore results**. Legends have separate rows. Figure export is in the Results details toolbar; its overflow menu remains available. |
| Save failed | Select a writable folder and retain the complete project. |

Default application data are under `%LOCALAPPDATA%\EMCD-Sim`; logs are in `logs\runtime.log`. `EMCD_GUI_WORKSPACE` redirects workspace files, not that log directory. Report version/source identity, settings and relevant errors without sharing private data.

## Source development — optional, separate from EXE use

For developers with Git and Python 3.11, use a new clone:

```powershell
git clone https://github.com/dingpengem/EMCD-Sim.git
Set-Location EMCD-Sim
git switch feat/windows-adaptive-compute
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[gui]"
.\.venv\Scripts\python.exe -m emcd_sim.gui
```

No Conda or shell activation is required. If `py` is unavailable, use an explicit compatible interpreter path. The project requires Python >=3.10; the Windows build uses Python 3.11. Developers may install `.[dev,gui]` for tests. [Windows build requirements](../packaging/requirements-windows.txt) and [packaging instructions](../packaging/README.md) are for maintainers, not EXE users.

Historical releases retain their own tagged instructions, including [v0.8.1-beta.2 installation](https://github.com/dingpengem/EMCD-Sim/blob/v0.8.1-beta.2/docs/INSTALL_WINDOWS.md). [Release evidence and limitations](RELEASE_NOTES_0_9_0_BETA_1.md) distinguish scoped native/focused checks from historical failed/incomplete broad verification and scientific convergence/calibration.
