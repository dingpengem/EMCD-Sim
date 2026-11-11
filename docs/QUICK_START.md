# Quick Start — v0.9.0-beta.1 Windows Research Beta

[Home](../README.md) · [Install](INSTALL_WINDOWS.md) · [Complete Tutorial](TUTORIAL.md) · [User Guide](USER_GUIDE.md)

Use the complete extracted Windows package. Python, Conda and manual BLAS environment variables are unnecessary. This is the already verified **small Global Ni BW Single** workflow, not a convergence or calibration recipe.

1. Launch **EMCD-Sim.exe**; choose **File → New Project**.
2. In **Material**, click **Open CIF…** and select `_internal/examples/Ni_FCC_a3.52.cif`. **Inspect structure…** should show four Ni sites in a cubic **3.520 Å** cell, not the built-in 3.524 Å default.
3. Open **3D Structure Viewer… → Site groups**. Select **Global Magnetization Mode** and set **Global Material M (x y z)** to `0 0 1`.
4. Click **Configure MDFF…**. In **Global Material configuration**, choose **XMCD-constrained MDFF**. Browse `_internal/data/wien2k_ni/Ni_fm.xmcd`, click **Validate source / native features**, and use **831.271 / 848.698 eV** as its L3/L2 selections. These are this file's native features, not generic tabulated Ni energies.
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
| Angular grid; depth nodes; aperture subpixels | **9×9; 64; 64** |
| Map halfwidth | **1 Å⁻¹** |
| Energy sampling | **Selected energies only**, two actual samples |
| Angular evaluation | **Full angular maps at selected energies** on; advanced all-energy field off |
| Workers / budget | **Manual, 1 worker; 2048 MiB** |
| Virtual detectors | **Restore Thales A/B**, radius **0.09 Å⁻¹** |

Thales centers are approximately `(0.2840909091, ±0.2840909091) Å⁻¹`. Review the effective request. Do not apply another sampling preset afterward; **Custom – 9×9** is the correct caption for these settings.

7. Click **Run EMCD / EELS**. **Preview diffraction** is a separate optional calculation. After completion, inspect **EMCD Angular Maps** and **Virtual Detector EELS**. Two energy samples do not form a resolved spectrum. Raw ±M, reversal-even/odd and conventional A−B have different definitions.
8. Choose **File → Save As…** to retain a separate project folder. **Close Project → Open Project…** restores saved data without recalculation. Keep new runs rather than replacing an original. Export numerical data from **Results → Export Results…** or the selected-spectra CSV button. Use **Display details / diagnostics / export → toolbar → Export Figure…** for a figure; open the toolbar overflow if needed.

For **Local Site Magnetization Mode**, configure each participating group explicitly. Use original ASE indices; split crystallographic groups manually if magnetic sublattices differ. Uncheck **Ionize / Group ID** for oxygen or other non-ionizing groups, keeping those atoms elastic. Local mode locks Global M; no implicit Global MDFF or magnetic order is supplied. [Tutorial](TUTORIAL.md#4-local-site-groups-and-non-ionizing-atoms) explains group creation, accepted/draft directions and validated reversal pairs.

The full [Tutorial](TUTORIAL.md) includes illustrations, normal Save/Open/export steps, diagnostics and scientific limitations. Historical v0.8 menu instructions belong to their [tagged guide](https://github.com/dingpengem/EMCD-Sim/blob/v0.8.1-beta.2/docs/QUICK_START.md).
