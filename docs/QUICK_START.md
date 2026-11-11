# Quick Start — v0.9.0-beta.2 Windows Research Beta candidate

[Home](../README.md) · [Install](INSTALL_WINDOWS.md) · [Complete Tutorial](TUTORIAL.md) · [User Guide](USER_GUIDE.md)

This guide describes the **unpublished beta.2 candidate**. The published beta.1
package remains available with its [tagged guide](https://github.com/dingpengem/EMCD-Sim/blob/v0.9.0-beta.1/docs/QUICK_START.md).
Use the complete extracted Windows package. Python, Conda and manual BLAS
environment variables are unnecessary. The representative Global Ni BW Single
request below has already completed in the adaptive-compute development EXE;
it is a functional example, not a convergence or calibration recipe.

1. Launch **EMCD-Sim.exe**; choose **File → New Project**.
2. In **Material**, click **Open CIF…** and select `_internal/examples/Ni_FCC_a3.52.cif`. **Inspect structure…** should show four Ni sites in a cubic **3.520 Å** cell, not the built-in 3.524 Å default.
3. Open **3D Structure Viewer… → Site groups**. Select **Global Magnetization Mode** and set **Global Material M (x y z)** to `0 0 1`.
4. Click **Configure MDFF…**. In **Global Material configuration**, choose **XMCD-constrained MDFF**. Browse `_internal/data/wien2k_ni/Ni_fm.xmcd`; browsing validates it, and **Recheck source (optional)** repeats that check. Use **831.271 / 848.698 eV** as its L3/L2 selections. These are this file's native features, not generic tabulated Ni energies.
5. Complete the visible convention acknowledgement and source declarations: Ni, L2,3, eta=beta=1, relative reference 1, `physical_source_unvalidated`, truthful source/provenance and effective-XMCD limitations. [Tutorial](TUTORIAL.md#2-set-material-global-m-and-accept-its-mdff) supplies the exact diagnostic declarations. Target M is read-only in MDFF Configuration. Choose **Done**, then the Viewer's **Apply and Close**. Preview alone does not accept the configuration. Inactive local rows may remain unconfigured.
6. Set the following in the existing Settings panel:

| Section / control | Value |
| --- | --- |
| Microscope & Sample | **200 kV**, **10 nm** |
| Orientation / ZA options | `0 1 7`, target `2 0 0`, **Full finite ZOLZ**, **Apply orientation / target** |
| Tilt X / Y | **−7.124812628 / 0 mrad**, for this actual 3.520 Å cell |
| Channeling Model / Propagation Method | **Single Channeling / Bloch-wave** |
| Numerical settings mode | **General settings (editable)** |
| Beam / MDFF cutoff; potential cutoff | **2.5 / 2.0 Å⁻¹**; effective **21 beams** |
| Debye–Waller B (A²); systematic-row approximation | **0; off** |
| Angular grid; depth nodes; aperture subpixels | **Standard - 97x97; 64; 64** |
| Map halfwidth | **1 Å⁻¹** |
| Energy sampling | **Entire energy range — uniform sampling**, **241** requested points |
| Angular evaluation | **Full angular maps at selected energies** on; advanced all-energy field off |
| Compute Resources | CPU Workers **Auto (recommended)**; Memory Budget **Auto (recommended)** |
| Virtual detectors | **Restore Thales A/B**, radius **0.09 Å⁻¹** |

Thales centers are approximately `(0.2840909091, ±0.2840909091) Å⁻¹`.
Review the effective request: **21 beams and 243 actual energies** over
823.625–882.521 eV. The 241 uniform points and two distinct exact selections
produce 243 samples. The two selected maps each contain **97×97 calculated
momentum samples**; other energies calculate the detector-support responses.
No spectral tails or full intermediate maps are invented.

Use **Shared Calculation Settings → Compute Resources** for independent CPU and
memory modes. The panel shows detected
hardware, effective allocation, estimated process peak and admission separately.
Auto retains your Manual values and never reduces scientific sampling. Older
projects with a saved fixed memory budget retain Manual memory. Run refreshes
available resources and submits its displayed allocation; admission may change
as other applications consume RAM. These controls are development-source changes,
not an update to the published v0.9.0-beta.1 Windows package. The memory budget
is an admission ceiling; the estimated process peak is not measured consumption.
SC uses one outer worker. DC includes post-loss outgoing propagation and has a
different memory/work schedule; more workers are not guaranteed to be faster.

7. Click **Run EMCD / EELS** after admission is **Ready**. **Preview diffraction** is a separate optional calculation. After completion, inspect **Virtual Detector EELS** across all 243 energies and select L3/L2 in **EMCD Angular Maps**. Raw ±M, reversal-even/odd and conventional A−B have different definitions.
8. Choose **File → Save As…** to retain a separate project folder. **Close Project → Open Project…** restores saved data without recalculation. Keep new runs rather than replacing an original. Export numerical data from **Results → Export Results…** or the selected-spectra CSV button. Use **Display details / diagnostics / export → toolbar → Export Figure…** for a figure; open the toolbar overflow if needed.

For **Local Site Magnetization Mode**, configure each participating group explicitly. Use original ASE indices; split crystallographic groups manually if magnetic sublattices differ. Uncheck **Ionize / Group ID** for oxygen or other non-ionizing groups, keeping those atoms elastic. Local mode locks Global M; no implicit Global MDFF or magnetic order is supplied. [Tutorial](TUTORIAL.md#4-local-site-groups-and-non-ionizing-atoms) explains group creation, accepted/draft directions and validated reversal pairs.

The full [Tutorial](TUTORIAL.md) includes illustrations, normal Save/Open/export steps, diagnostics and scientific limitations. Historical v0.8 menu instructions belong to their [tagged guide](https://github.com/dingpengem/EMCD-Sim/blob/v0.8.1-beta.2/docs/QUICK_START.md).

New single-element result metadata distinguishes the
requested `requested_uniform_energy_points` from `evaluated_energy_samples`.
`numerics.energy_samples` now reports the evaluated count. For example, 241
uniform points plus two distinct exact selected energies produce 243 samples.
The saved sampling controls remain unchanged. Older results may contain only
the historical `energy_samples` diagnostic; their actual energy array remains
authoritative, and opening them does not rewrite their metadata.

The 2.0 Å⁻¹ potential cutoff retains no off-row potential harmonics (first near
2.029 Å⁻¹). This example does not establish full 2D potential, beam-basis or
experimental spectral convergence. [Numerical evidence and missing Mac datasets](WINDOWS_MACOS_NUMERICAL_EQUIVALENCE.md)
separate known agreement from incomplete comparisons.
