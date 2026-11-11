# Install EMCD-Sim v0.9.0-beta.2 on Windows

[Home](../README.md) · [Quick Start](QUICK_START.md) · [Tutorial](TUTORIAL.md) · [User Guide](USER_GUIDE.md)

## Ordinary packaged use

1. Open the [Windows Research Beta release](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.9.0-beta.2). Under **Assets**, download **EMCD-Sim-v0.9.0-beta.2-Windows.zip**. GitHub's automatic Source code ZIP is not the Windows application. Earlier releases remain unchanged.
2. Use Windows 11 x64 and install/repair the official [Microsoft Visual C++ v14 x64 Redistributable](https://aka.ms/vc14/vc_redist.x64.exe) if needed. The tested runtime is **14.44.35211**; use a compatible current v14 runtime. This remains an external dependency: Microsoft runtime DLLs are not bundled contrary to the established redistribution policy.
3. In File Explorer, right-click the downloaded ZIP and choose **Extract All…** into a new writable folder. Wait for extraction to finish. Keep the **complete EMCD-Sim folder** and all `_internal` contents together.
4. Open the extracted folder and double-click **EMCD-Sim.exe**, beside `_internal`. Do not run from inside the ZIP or copy the EXE alone. Follow local SmartScreen/security policy; the research binary is not code-signed. Do not disable antivirus as a workaround.
5. Check the displayed version and **Help → About** build identity. Start with the [Quick Start](QUICK_START.md), not a restored unknown configuration. The example CIF and XMCD file are under `_internal/examples/Ni_FCC_a3.52.cif` and `_internal/data/wien2k_ni/Ni_fm.xmcd`.
6. Save projects to a writable location. Updating means extracting a new complete package into a different directory; preserve previous projects and required source files.

**Python, Conda, WIEN2k and manual OpenBLAS/OMP environment variables are not required for packaged use.** The application supplies its Python/Qt and supported numerical libraries. Windows beta.2 is distinct from the unchanged macOS ARM64 release and has its own source revision.

## Compute Resources

In **Shared Calculation Settings → Compute Resources**, **CPU Workers** and **Memory Budget** each offer **Auto (recommended)** or **Manual**. Auto considers detected hardware, useful tasks and current memory/commit headroom; it never silently reduces beams, energy points, FFT/grid or depth sampling. SC has one outer worker; DC may use more. More workers are not necessarily faster.

The panel shows effective workers/budget, the current calculation estimate and admission status. A memory budget is a ceiling, not expected consumption; the estimate includes reserves and differs from measured RSS. Insufficient admission must be resolved before Run. Manual values are remembered when switching back to Auto and reopening projects. Run applies and verifies supported BLAS thread limits and restores them afterward; users need no shell-variable workaround.

## Projects and exports

Use **File → New Project**, **Open Project…**, **Save**, **Save As…**, and **Close Project**. Save creates a complete folder; Open Project selects that folder. Keep all its files. The lower **Project Results** panel retains separate calculations; **Restore Settings from Selected Run…** differs from merely viewing an old result. Compare exactly two selected runs in the separate comparison dialog.

In Results, inspect detector spectra and selected angular maps. **Results → Export Results…** writes CSV/NPZ and available figures; figure export also sits near its plot. Save/Open restores existing arrays without rerunning. External spectroscopy files are not all automatically embedded: retain required sources. Missing/changed sources may block rerun while saved arrays remain viewable. Never bypass scientific source/frame validation.

## Guides, sources and licenses

Offline guides, citation, scientific references and illustrations are in `_internal/documentation/`; online [Quick Start](QUICK_START.md) and [Tutorial](TUTORIAL.md) use current controls. The release's **EMCD-Sim-v0.9.0-beta.2-Corresponding-Source.zip** contains the exact application snapshot plus matching Qt/PySide/Shiboken 6.12 sources and replacement instructions. Do not substitute the older beta.1 application source.

The unchanged Qt 6.12 [technical replacement guide](../packaging/assets/qt-licenses/SOURCE_AND_REPLACEMENT.md) retains historical beta.1 example names; the source kit's outer README identifies the actual beta.2 package and commit. Applicable dependency licenses/notices accompany the binaries. Unused Qt PDF and Virtual Keyboard are excluded; required Qt plugins and spglib runtime/licenses are retained. The existing build manifest and `_internal/build_info.json` record dependencies and exact committed source. No independent clean-PC/VM validation is claimed.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Missing MSVCP140/VCRUNTIME140 DLL | Install/repair the official Microsoft x64 runtime above. |
| Missing Python/Qt file or startup failure | Freshly extract the complete ZIP; inspect quarantine under local policy, and do not combine versions. |
| Run disabled | Read the full reason; validate the active Global/group source, conventions, frame and coverage, then finish **Done → Apply and Close**. |
| Inactive — Global mode on a group | That Local row is not used by Global calculation; check the Global provider's actual readiness. |
| Stale result notice | Compare working inputs with the displayed saved run. Resolve genuinely missing/changed sources; do not blindly reapply or bypass validation. |
| Memory admission rejected | Review the effective settings and workers. Increasing a budget does not create RAM. |
| Crowded Results | Resize/scroll or use **Maximize / restore results**. Dedicated legends and toolbar overflow preserve access and figure identification. |
| Save failed | Select a writable location and retain the complete project folder. |

Default application data are under `%LOCALAPPDATA%\EMCD-Sim`; logs are in `logs\runtime.log`. `EMCD_GUI_WORKSPACE` redirects workspace files, not that log directory. Include build identity, relevant settings and a bounded error excerpt when reporting problems.

## Source development — optional and separate

Developers may clone the repository, check out the required version and install `.[gui]` in a Python >=3.10 virtual environment. The Windows package uses Python 3.11. See [build requirements](../packaging/requirements-windows.txt) and [packaging workflow](../packaging/README.md); these are maintainer instructions, not EXE prerequisites. No Conda installation or environment activation is required.

Research limitations, unchanged historical failed/incomplete broad checks and current focused acceptance are in the [release notes](RELEASE_NOTES_0_9_0_BETA_2.md). Finite-basis agreement is not convergence or quantitative material calibration.
