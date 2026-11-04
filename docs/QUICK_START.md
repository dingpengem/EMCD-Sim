# Quick Start: a small FCC Ni calculation

[Home](../README.md) · [Installation](INSTALL_WINDOWS.md) · [Tutorial](TUTORIAL.md) · [User Manual](USER_GUIDE.md)

This 5–10 minute walkthrough targets the **released v0.8.1-beta.1 Windows Research Beta**. Setup and runtime depend on the machine. It is a deliberately small functional demonstration—not a quantitatively converged Ni result or the advanced 9/30 nm spectral study.

New calculations use the bundled Adaptive Dirac–Padé neutral Z=1–118 provider. Select Ni Lobato explicitly for the historical 9/30 nm examples; old saved projects without provider metadata restore Lobato. This is a Windows-only Research Beta; Linux/macOS are not certified.

## 1. Extract and open

Install the verified [public Windows ZIP](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.8.1-beta.1) using the [Installation Guide](INSTALL_WINDOWS.md). Launch the extracted `EMCD-Sim.exe` with `_internal` beside it. Confirm version/convention in **Help → About**. No Python installation is needed.

If necessary, select **View → Restore Default Layout**. Settings scroll vertically; use the blue section headers/chevrons to expand controls. These instructions name the controls in the released EXE.

## 2. Set the crystal and diffraction geometry

1. Choose **File → New**, then **A. Crystal Structure → FCC Ni default**. This is the conventional four-atom FCC Ni cell, a = 3.524 Å. **Load CIF…** is available, but arbitrary CIFs do not acquire a validated Ni inelastic model.
2. Expand **B. Zone Axis & Diffraction → Orientation / ZA options**. Enter **Nominal zone [uvw]** `0 1 7` and **Target (hkl)** `2 0 0`; click **Apply orientation / target**.
3. Leave **Diffraction basis** at **Full finite ZOLZ**. This is not an artificial two-beam truncation.
4. Under **C. Microscope & Sample**, explicitly set **Voltage (kV)** = **300** and **Thickness (nm)** = **1**.
5. Click **Reset to reference geometry**. The exact (200) Bragg reference is approximately **Tilt X = −5.5866881404 mrad**, **Tilt Y = 0** at 300 kV. Zero tilt is zone-axis incidence, a different condition. To align another selected beam, use **Align to selected Bragg** and inspect its excitation error.
6. Click **Virtual detectors → Restore Thales A/B**. Keep radius **0.0908059024 Å⁻¹**. For this target, centers are approximately **(0.283768445, ±0.283768445) Å⁻¹**.

The transmitted (000) cross and yellow projected-ZA star generally differ under tilt. The teal dotted circle is Thales; the darkorange dashed circle is the ZOLZ Laue locus. **Set projected ZA** click mode allows live dragging, which makes old diffraction intensities stale. It does not start a calculation or move detectors.

## 3. Select and validate the inelastic model

Expand **D. MDFF Model**:

1. Select **XMCD-constrained (WIEN2k)** and retain the bundled **Five-column XMCD** source.
2. Click **Validate source / native features**. The bundled source's selected magnetic energies are **L3 = 831.271 eV** and **L2 = 848.698 eV**.
3. Keep **Crystal Cartesian M axis** `0 0 1`, **eta = 1**, **beta = 1**. Check **I declare M axis, RP/LP convention and edge assignments** for this documented reference. Do not use that declaration as a substitute for checking a new source.

These are native model energies, not experimentally calibrated Ni edge positions. The model is an effective tensor constrained by XMCD, not full complex DFT transition data. Each calculation evaluates both reversal states at fixed A/B detectors; no second manual detector move is needed.

## 4. Choose a small numerical profile

Under **E. Propagation Method**, choose **Single Channeling** and **Bloch-wave**. Single omits outgoing elastic channeling. After this first run, **Double Channeling**, **FFT Multislice** or **Both (BW / MS comparison)** can be explored as separate saved runs; they need different resource and convergence checks.

Under **F. Shared Calculation Settings**, choose **Numerical Settings → Manual (Advanced)** **before** entering the following values. Automatic would select its own starting configuration.

|Control|Demonstration value|
|---|---:|
|Beam / MDFF basis cutoff (Å⁻¹)|3.2|
|Potential Fourier cutoff (Å⁻¹)|3.8|
|Explicit target systematic-row approximation|Off|
|Angular Map Resolution|Custom; set grid below|
|Angular / detector grid points (odd)|17|
|Map halfwidth (Å⁻¹)|0.5|
|Depth integration nodes|33|
|Aperture boundary subpixels|32|
|Spectral coverage|Selected L3/L2 samples only (not full EELS)|
|Calculate angular maps|On|
|Estimated process memory budget|2048 MiB|
|Parallel Workers|Manual; Requested workers = 1|
|Enable post-edge A/B correction|Off, under Advanced post-edge diagnostics|

The sampling controls are in **Inelastic and Angular Sampling**; support/cutoffs are in **Elastic Potential and Beam Support**. Resource controls are separate. This [017] profile retains 27 beams. **Max slice step** and FFT mesh do not affect this BW run. Inspect **Resource estimate** before Run; admission may reject a job on a RAM-constrained machine rather than silently coarsening it.

For research, refine one source of numerical error at a time. These coarse settings are not a certification, and BW/MS agreement alone would not make them converged.

## 5. Calculate and inspect

1. Click **Preview diffraction**. Inspect the indexed spots, **Diffraction details** and the **Diffraction** table, including `s_g` for the target. Preview is elastic, not EELS.
2. Click **Run EMCD / EELS**. **Cancel** requests cooperative shutdown; wait until the interface returns idle before another run.
3. Open **Virtual Detector EELS**. Two selected samples are displayed as points; they are **not a full white-line spectrum**.
4. **Signal Display → Raw (a.u.)** shows original magnetic/nonmagnetic A/B differences. **EMCD Asymmetry (%)** shows conventional +M A/B difference divided by its sum; nonmagnetic imbalance can contribute.
5. Open **EMCD Angular Maps** and select L3 or L2. Maps use the actual calculated 17×17 samples. Zooming does not add numerical resolution. A map pixel percentage is not a detector-integrated percentage.
6. Read **Calculation Information** and the numerical warnings. A warning is not a convergence certificate or necessarily a fatal error.

For a complete spectrum later, choose **Full native energy-resolved spectrum** and set **Energy sampling points**. The existing model is evaluated independently at every requested energy; this is not interpolation of the two calculated edge points. It can be much slower. See [energy sampling](USER_GUIDE.md#energy-sampling).

## 6. Save, reopen and export

Choose **File → Save Project As...**, select a writable parent folder and a new name. Preserve the **whole** project folder. Then **File → Open Project...** and select that folder: reopening saved arrays does not run the solver.

Current Inputs and saved results are separate. Use **Use These Settings** explicitly if you want to restore the saved controls; changing inputs alone does not rewrite existing results. Unsaved in-memory runs are not a backup.

- **Export current plot PNG / SVG…** or **Results → Export Current Figure** saves a figure.
- **Export completed EMCD / EELS...** saves a numerical/figure bundle.
- **Export derived NPZ/CSV + metadata** saves derived views alongside preserved raw data.

Keep denominators and source/convention metadata with figures. The GUI's advanced magnetic/nonmagnetic percentages use `N_A+N_B`; the tutorial separately explains the common conventional denominator needed to reconstruct total A/B percentages. See [exports](USER_GUIDE.md#export-figures-and-data).

## Troubleshooting

If Run is disabled, inspect source validation/declaration, material, geometry and resource status. If only gray spots are shown, request a fresh diffraction preview. If controls are hidden, expand the section and confirm Manual mode; use **View → Restore Default Layout** if needed. A source, memory or FFT-support error is not permission to silently change scientific settings. See [installation troubleshooting](INSTALL_WINDOWS.md#i-troubleshooting).

**Next:** [Complete Tutorial](TUTORIAL.md). It explains the measurements and shows a verified advanced 9/30 nm case without requiring a long spectral run.
