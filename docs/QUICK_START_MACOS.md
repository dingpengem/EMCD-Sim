# macOS ARM64 Quick Start — Ni EMCD spectrum and momentum-space maps

[Home](../README.md) · [macOS Installation](INSTALL_MACOS.md) · [macOS Research Beta](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.9.0-beta.1-macos-arm64.1) · [Windows Quick Start](QUICK_START.md) · [MDFF Workflows](MDFF_WORKFLOWS.md)

This walkthrough uses a **normal-size, illustrative FCC Ni Bloch-wave Single Channeling request**, with **a sampled L₂,₃ spectrum and 97×97 momentum-space maps at the selected L₃/L₂ energies**. It is a more representative introduction than the earlier 2-energy, 9×9 packaged smoke test.

**Evidence boundary:** The source, physical geometry and sampling approach are based on documented EMCD-Sim Ni workflows; the *combined* 241-uniform-plus-selected / 97×97 configuration below has **not yet been independently executed and accepted as a packaged macOS Quick Start run**. The earlier 2-energy, 9×9 packaged Ni diagnostic *was* tested and remains in the [Installation Guide](INSTALL_MACOS.md#5-optional-minimal-packaged-ni-diagnostic). Do not mistake these validation scopes. Neither recipe establishes physical convergence, experimental calibration or quantitative magnetic moments.

You need an Apple Silicon Mac with macOS 15+ and the [standalone ARM64 Research Beta](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.9.0-beta.1-macos-arm64.1). [Install it with Finder](INSTALL_MACOS.md#2-download-and-install-using-finder). No Python, Conda, Terminal or developer tools are required. The package is ad-hoc signed, not Apple notarized; see the [first-launch guidance](INSTALL_MACOS.md#3-first-launch-and-troubleshooting).

## 1. Copy the bundled input files

Create **Documents → EMCD-Sim Examples** in Finder. In Applications, Control-click **EMCD-Sim** → **Show Package Contents**, and **copy** (do not move or edit) these files into that folder:

- `Contents/Resources/examples/Ni_FCC_a3.52.cif` — four FCC Ni atoms, `a=3.520 Å`.
- `Contents/Resources/data/wien2k_ni/Ni_fm.xmcd` — example five-column Ni XMCD source.

Keep the original files in the app. Save simulation projects separately in Documents.

## 2. Import Ni and accept its MDFF

1. Open **File → New Project**. Under **Material → Open CIF…**, select your `Ni_FCC_a3.52.cif` copy. **Inspect structure…** should show four Ni atoms and a 3.520 Å cubic cell (not the built-in 3.524 Å reference).
2. Open **3D Structure Viewer… → Site groups**, select **Global Magnetization Mode**, and set **Global Material M (x y z) = 0 0 1**.
3. Choose **Configure MDFF…** and check that the context is **Global Material configuration**. Select **XMCD-constrained MDFF** and browse to your `Ni_fm.xmcd` copy.
4. Choose **Validate source / native features**. Use the actual selected features **L₃ = 831.271 eV** and **L₂ = 848.698 eV**; set **eta = beta = 1**. These are source-specific features, not universally tabulated Ni edges.
5. Complete the visible declarations truthfully:

| MDFF field | Value for this example |
| --- | --- |
| Declared element / core-loss edge | `Ni` / `L2,3` |
| Source / provenance | `Ni_fm.xmcd; supplied five-column Ni source` |
| Physical assumptions / limits | `Effective axisymmetric XMCD-derived Ni diagnostic; not quantitatively calibrated for this CIF` |
| Relative tensor reference | `1` (relative, not an absolute cross section) |
| Scientific status | `physical_source_unvalidated` |
| Convention acknowledgement | Review M axis, RP/LP convention and L₂/L₃ assignments, then check the corresponding declaration |

6. Click **Done** to return to the 3D Viewer. Then click **Apply and Close** in the Viewer. Both are required to accept the configuration; preview alone does not make it active.

## 3. Set a representative Ni calculation

Select **General settings (editable)** where necessary. Use the following case; it retains the documented 3.520 Å Ni [017]/(200) geometry, rather than the deliberately unphysical 0.1 nm thickness and ideal 2-beam-only basis used by the old smoke test.

| GUI section / control | Input |
| --- | --- |
| Material → elastic scattering provider | **Adaptive Dirac–Padé 2026** (default) |
| Material → Debye–Waller B | **0** |
| Microscope & Sample | **200 kV**, **10 nm** thickness |
| Zone Axis & Diffraction → orientation | **[0 1 7]**, target **(2 0 0)**, **Full finite ZOLZ**; click **Apply orientation / target** |
| Zone Axis & Diffraction → tilt | **X = −7.124812628 mrad**, **Y = 0 mrad** for the actual 3.520 Å CIF at 200 kV |
| Propagation Method | **Bloch-wave**, **Single Channeling** |
| Propagation Method → explicit target systematic-row approximation | **Off** |
| Shared Calculation Settings → numerical settings | **General settings (editable)** |
| Elastic Potential and Beam Support | **Beam / MDFF cutoff 2.5 Å⁻¹**, **potential Fourier cutoff 2.0 Å⁻¹** (approximately 21 effective beams for this case) |
| Inelastic and Angular Sampling → depth | **64 integration nodes** |
| Inelastic and Angular Sampling → aperture boundary | **64 subpixels per direction at boundary** |
| Inelastic and Angular Sampling → map halfwidth | **1.0 Å⁻¹** |
| Inelastic and Angular Sampling → Angular Map Resolution | **Standard – 97×97** (or set angular/detector grid points to **97**) |
| Inelastic and Angular Sampling → Energy sampling | **Entire energy range → uniform sampling** |
| Inelastic and Angular Sampling → energy points | **241 points per modeled source window**, with exact selected L₃/L₂ energies included |
| Inelastic and Angular Sampling → angular evaluation | **Full angular maps at selected energies: ON**; **Full angular field at every energy (advanced): OFF** |
| Compute Resources | **CPU workers: Auto**; **Memory budget: Auto** |
| Virtual Detectors | **Restore Thales A/B** for this geometry; **radius = 0.09 Å⁻¹** |

For this Ni source, the two exact selected energies normally add to the 241-point uniform grid, yielding **243 distinct energies**, provided neither selected value happens to coincide with a uniform sample. Confirm the **actual effective energy count** displayed by the application. The source covers approximately **823.625–882.521 eV**; do not shift its energy scale without evidence.

Use the **97×97 physical momentum-space grid** for angular maps. At a map halfwidth of 1.0 Å⁻¹, the nominal spacing is approximately **0.0208 Å⁻¹** between adjacent samples along each axis. These q-space coordinates are **not** the multislice FFT mesh or a real-space 4D-STEM scan grid. Aperture boundary subpixels refine integration weights, not the underlying 97×97 map.

Only the **two selected L₃/L₂ energies** request full 97×97 maps. The other spectral energies evaluate the detector-support coordinates needed for the A/B EELS/EMCD spectra. Leave **Full angular field at every energy (advanced)** **off**; it would request much more work without supplying more displayed selected-energy maps. Do not confuse the **number of spectral samples** with the **number of q pixels**.

After selecting Standard 97×97, inspect the effective grid and **map halfwidth**; changing presets can update more than one control. Do not choose another preset merely to alter a caption.

## 4. Run and inspect both kinds of result

1. Review **Compute Resources**: effective Auto workers, effective memory budget, predicted peak and **Admission**. Auto selections depend on the actual Mac and workload; no single worker count or budget applies to every machine. **Ready** means resource admission, not scientific convergence.
2. Click **Preview diffraction** if you want to inspect the retained full finite ZOLZ beam basis and [017]/(200) alignment; this is a separate elastic preview. Then select **Run EMCD / EELS**.
3. Inspect **Virtual Detector EELS** to see the sampled energy dependence across the modeled Ni L₂,₃ range. Inspect the two detector signals and the chosen magnetic/nonmagnetic or reversal-derived observables using their actual definitions. An extended simulated spectrum is not experimental energy resolution or a calibrated cross section.
4. Inspect **EMCD Angular Maps** at **831.271 eV** and **848.698 eV**. These should be **97×97 q-space maps**. Raw difference/asymmetry views and the fixed A/B aperture overlays are different quantities; a high-resolution display zoom does not create additional computed samples.
5. Export both the **spectral data** and **angular maps**, using **Results → Export Results…** and the relevant **Export Figure…** toolbar actions.
6. Use **File → Save As…** for a new project folder, then **Close Project → Open Project…** to check that accepted settings, the spectra and maps restore without recalculation.

If Run is unavailable, check the **Done → Apply and Close** acceptance transaction, selected source-energy coverage, diffraction settings and the complete resource-admission reason. Do not change beam, energy, momentum grid or physics values silently just to obtain a pass.

## 5. Understand the two independent sampling dimensions

| Sampling dimension | What is calculated | Why it matters |
| --- | --- | --- |
| **Energy: 241 uniform + selected L₃/L₂** | Detector-integrated values as a function of energy | Provides a model EELS/EMCD spectrum rather than only two isolated edge samples |
| **Momentum: 97×97** | Two physical qx–qy intensity maps at selected energies | Reveals angular dependence, detector positions and magnetic/nonmagnetic contrast |
| **Other energies: detector-only q support** | A/B detector spectra without a whole angular image at every energy | Controls cost without fabricating the spectral values by interpolating final detector signals |

Both dimensions are real numerical sampling choices, but they address different questions. Increasing energy points does not improve q-space resolution, and increasing q-grid points does not improve energy sampling.

**Scope:** This is a **normal illustrative starting workflow**, not an experimentally converged Ni simulation or a newly verified macOS packaged benchmark. The earlier [minimal tested diagnostic](INSTALL_MACOS.md#5-optional-minimal-packaged-ni-diagnostic) is retained separately for troubleshooting. A future native packaged run with these *exact combined settings* is needed before marking this Quick Start end-to-end validated.
