# EMCD-Sim Windows Quick Start

This is a short reading guide, not a promise of total calculation time.
For installation details see [Install on Windows](INSTALL_WINDOWS.md); for
interpretation and other workflows see the [User Manual](USER_GUIDE.md).
The application is an unreleased research candidate.

## 1. Extract and open

Obtain the reviewed `EMCD-Sim-Stage-F-Windows-RC.zip` from the maintainer;
there is currently **no published binary download**. Verify the checksum in
the installation guide and **Extract All**. In the extracted `EMCD-Sim`
folder, double-click `EMCD-Sim.exe`. Keep `_internal` beside it. No Python,
Conda, VS Code or WIEN2k installation is required. Initialization can take
tens of seconds. Do not run inside the ZIP.

## 2. Preview the default Ni reference

1. Choose **File → New**, then **View → Restore Default Layout** if an old
   layout or selection is restored. **FCC Ni default** selects the built-in
   conventional Ni cell, a=3.524 Å.
2. Confirm **Nominal zone [uvw]** `0 1 7`, **Target (hkl)** `2 0 0`,
   **Voltage (kV)** `200`, **Thickness (nm)** `30`. Use **Reset to reference
   geometry** if needed: Tilt X is approximately `-7.11672544` mrad and Y is zero.
3. Click **Preview diffraction**. The initial geometry drawing is replaced
   by calculated elastic intensities. In **Select reflection** click (200),
   then **Align to selected Bragg**. Check `s≈0` below the plot.
4. The cross is transmitted (000); the star is projected **ZA [017]**.
   They differ at this exact-Bragg tilt. The Thales circle has (000)–(200)
   as its diameter. Use **Restore Thales A/B** for the physical apertures.

![Default Ni diffraction and controls](images/gui/stage_e_main.png)

Actual accepted Windows capture, reused from Stage E; the current candidate
retains these controls and geometry. Labels in **Calculation Information**
distinguish current inputs from the completed-run snapshot.

## 3. Select the bundled spectrum and run BW

1. Expand **D. MDFF Model** and choose **XMCD-constrained (WIEN2k)**.
2. The source normally points to the bundled five-column example. If empty,
   **Browse XMCD...** to `EMCD-Sim\_internal\data\wien2k_ni\Ni_fm.xmcd`.
3. Click **Validate source / native features**. Check L3 `831.271` and L2
   `848.698` eV and **Crystal Cartesian M axis** `0 0 1`. These are native
   calculated features, not calibrated experimental edge energies.
4. For the supplied example, retain eta=beta=1 and check **I declare M axis,
   RP/LP convention and edge assignments**. Bundled numerical data have no
   companion audit; the declaration is deliberately not automatic.
5. Choose **Propagation Method → Bloch-wave**. Leave the default numerical
   settings. For corrected curves, explicitly check **Enable post-edge A/B
   correction** and retain its separate `878–882 eV` window. Validation of an
   unaudited source can leave correction off; do not mistake that for failure.
6. Click **Run EMCD / EELS** once. Wait for completion; **Cancel** is available.
   Changing display options later does not rerun the solver.

## 4. Read maps and EELS

- In **EMCD Angular Maps**, choose **L3** or **L2**. **Magnetic odd** is the
  reversal-odd signal; **Nonmagnetic even** is reversal-even intensity.
  Raw and corrected paired A−B maps are different observables.
- In **Virtual Detector EELS**, inspect the A/B, +M/−M spectra, magnetic and
  even differences. Choose **L3 zoom** or **L2 zoom** to inspect an edge.
- Set **Intensity Display → EELS Peak (%)**. **Auto** uses a fixed L3 peak
  for Full spectrum/L3 zoom and a fixed L2 peak for L2 zoom. The denominator
  is the maximum of the summed even A+B EELS in that window, not each curve's
  own maximum. Explicit L3/L2 choices override Auto.
- The saved reference gives BW magnetic peak contrasts about **−0.37556% at
  L3** and **+0.61516% at L2**, each using its own edge reference. These are
  simulated relative contrasts, not measurements. Full spectrum with the
  L3 reference uses that same L3 denominator for its L2 feature.

![Saved Ni percentage displays](images/gui/stage_f_emcd_percentage.png)

Actual native Stage F acceptance capture combining saved paired magnetic/even
maps and BW/MS EELS with a fixed L3 peak. Grey pixels are undefined/outside A
support. The normal map and EELS tabs provide the display selectors.
Post-edge-corrected A−B is **not automatically intrinsic magnetic EMCD**.

## 5. Save and reopen

1. **File → Save Project As...**: choose a writable research folder outside
   the application, then a new name such as `Ni017_BW_reference`.
2. Keep the entire resulting folder, including `project.json` and NPZ/JSON
   companions. **Save Project** updates the selected saved project; use
   **Save Project As...** to preserve a new condition separately.
3. **Open Project** and select that complete folder, or select it in the
   **Results Browser** and use **View Selected**. Maps and spectra reopen
   without a calculation.
4. **Use These Settings** restores inputs separately. Rerunning needs the
   original matching source; viewing saved data does not. A stale-result
   banner means current inputs differ from the completed result, not that
   its arrays have changed.

Next: use the [manual's mistilt comparison](USER_GUIDE.md#compare-two-conditions)
and export tutorials. Check [release readiness](STAGE_G_RELEASE_READINESS.md)
for the candidate's acceptance and pending checks.

## Limits to keep with your figures

Projected IAM; entrance-only depth-integrated ionization; no outgoing or
full double channeling; no atom-layer-resolved 3D multislice. The XMCD-effective
tensor is not a full complex DFT MDFF; the atomic model is non-DFT. There is no
absolute experimental cross-section or native-energy calibration. GUI FFT is
verified only for FCC Ni [017], not arbitrary CIFs. Physical Fourier-potential
cutoff convergence remains unresolved; good BW/MS agreement does not resolve it.
