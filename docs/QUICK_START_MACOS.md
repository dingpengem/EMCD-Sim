# macOS ARM64 Quick Start — first EMCD calculation

[Home](../README.md) · [macOS Installation](INSTALL_MACOS.md) · [macOS Research Beta](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.9.0-beta.1-macos-arm64.1) · [Windows Quick Start](QUICK_START.md)

This standalone Quick Start uses the **verified packaged macOS Ni Global XMCD / Bloch-wave Single Channeling example**. First [download and install EMCD-Sim.app](INSTALL_MACOS.md#2-download-and-install-using-finder) on an Apple Silicon Mac running macOS 15 or later. No Python, Conda or Terminal is required. The app is ad-hoc signed and not notarized; consult the [first-launch guidance](INSTALL_MACOS.md#3-first-launch-and-troubleshooting) if blocked.

The example is deliberately small and **not** a calibrated or converged experimental EMCD calculation. It uses 2 energy samples rather than a resolved spectrum.

## 1. Copy the two example files with Finder

The current bundle stores examples inside the app. **Copy** them to Documents without changing the application:

1. In Finder, open **Documents**. Choose **File → New Folder** and name it **EMCD-Sim Examples**.
2. Return to **Applications**. Control-click **EMCD-Sim** and choose **Show Package Contents**. This is a Finder viewing action, not a security override.
3. Open **Contents → Resources → examples**.
4. Select **Ni_FCC_a3.52.cif**. Choose **Edit → Copy**, return to **Documents → EMCD-Sim Examples**, and choose **Edit → Paste Item**.
5. Return to the app's **Contents → Resources**, then open **data → wien2k_ni**. Copy **Ni_fm.xmcd** into the same Documents folder using **Copy** and **Paste Item**.
6. Close the package-contents window. Leave the original files inside the app untouched. Use your Documents copies below.

The CIF file describes the crystal's atoms and cell. The XMCD file supplies the example magnetic spectroscopy input.

## 2. Run the verified small nickel calculation

This recipe matches **Ni_global_BW_single**, which passed native packaged-app acceptance, including result export. It deliberately uses a small calculation to check the workflow. The data and model are research approximations.

### Open the crystal

1. Open EMCD-Sim and choose **File → New Project**. Save any existing unsaved work first.
2. Expand **Material** in Settings. Click **Open CIF…**, browse to **Documents → EMCD-Sim Examples**, select **Ni_FCC_a3.52.cif**, then click **Open**.
3. Click **Inspect structure…**. Check for **four Ni atoms** and a cubic cell of **3.520 Å**. Close the information window.
4. Click **3D Structure Viewer…**. The four green atoms should resemble this captured Mac example:

![Native Mac Viewer showing the four nickel atoms before MDFF configuration](https://raw.githubusercontent.com/dingpengem/EMCD-Sim/v0.9.0-beta.1-macos-arm64.1/docs/images/macos/ni-structure-viewer.png)

The screenshot shows the initial unconfigured state. **Site groups** is the tab at the upper right.

### Set the magnetic model

1. In the Viewer, select **Site groups**, then **Global Magnetization Mode**.
2. Enter `0 0 1` in **Global Material M (x y z)**: three numbers separated by spaces.
3. Click **Configure MDFF…**. MDFF is the model used for the inelastic scattering calculation. Check that the context says **Global Material configuration**.
4. Choose **XMCD-constrained MDFF**. Click **Browse XMCD…** and open your Documents copy of **Ni_fm.xmcd**.
5. Click **Validate source / native features**. Confirm **L3 = 831.271 eV**, **L2 = 848.698 eV**, **eta = 1** and **beta = 1**. These selections belong to this particular file.
6. Complete the example declarations below. Review them before checking the convention acknowledgement.

| Field | Example value |
|---|---|
| Declared source element | `Ni` |
| Declared core-loss edge | `L2,3` |
| Source / provenance | `Ni_fm.xmcd; supplied five-column Ni source` |
| Physical assumptions / limits | `Effective axisymmetric XMCD-derived Ni diagnostic; not quantitatively calibrated` |
| Relative tensor reference | `1` |
| Scientific status | `physical_source_unvalidated` |
| Convention acknowledgement | Check **I declare M axis, RP/LP convention and edge assignments** for this supplied example. |

7. Click **Done**. You should return to the 3D Viewer. Then click the Viewer's **Apply and Close** to accept the complete configuration. Closing only the MDFF window does not complete this step.

### Enter the small calculation settings

Expand the named Settings sections. Click inside a number field to replace its value. Keep these settings together; choosing a sampling preset afterward can change them.

| Section | Setting | Value |
|---|---|---|
| Material | Elastic scattering provider | **Adaptive Dirac-Pade 2026 (default; neutral Z=1-118)** |
| Material | Debye–Waller B | `0` |
| Microscope & Sample | Voltage; thickness | `200` kV; `0.1` nm |
| Zone Axis & Diffraction → Orientation / ZA options | Nominal zone; target reflection | `0 0 1`; `2 0 0` |
| Same orientation controls | Diffraction basis | **Ideal 000 + target**, then **Apply orientation / target** |
| Zone Axis & Diffraction | Tilt X; Tilt Y | `−5`; `7` mrad |
| Propagation Method | Channeling; propagation | **Single Channeling**; **Bloch-wave** |
| Propagation Method | Explicit target systematic-row approximation | Unchecked |
| Shared Calculation Settings | Numerical Settings | **General settings (editable)** |
| Elastic Potential and Beam Support | Beam / MDFF cutoff; potential cutoff | `0.6`; `1.2` Å⁻¹ |
| Inelastic and Angular Sampling | Angular / detector grid points; depth nodes | `9`; `3` |
| Same sampling section | Aperture boundary subpixels; map halfwidth | `4`; `0.7` Å⁻¹ |
| Same sampling section | Energy sampling | **Selected energies only** |
| Same sampling section | Full angular maps at selected energies | Checked; leave the all-energy advanced field off |
| Compute Resources | CPU workers | **Manual**, requested workers `1` |
| Compute Resources | Memory budget | **Manual**, requested budget `2048` MiB |
| Virtual Detectors | A qx; A qy; B qx; B qy | `0.2`; `0.2`; `0.2`; `−0.2` Å⁻¹ |
| Virtual Detectors | Radius | `0.12` Å⁻¹ |

Leave post-edge correction off. FFT-specific settings do not affect this Bloch-wave example. A **Custom – 9×9** caption is expected. Do not click **Restore Thales A/B** for this recipe: it would change the detector positions above.

### Run and recognize success

1. Check **Compute Resources → Admission**. It should say **Ready**. If resources are insufficient, close other large applications and read the explanation; do not increase the budget just to dismiss the warning.
2. Click **Run EMCD / EELS**. **Preview diffraction** is a separate, optional calculation.
3. Wait for completion, then open **EMCD Angular Maps** and **Virtual Detector EELS** in Results. Expand a collapsed view or enlarge the window if needed.
4. Expect two selected energy samples near **831.271** and **848.698 eV**, rather than a continuous spectrum. This is intentional. The exported example below shows the verified result; display options can change its appearance.

![Verified Mac nickel Bloch-wave Single result with two selected energy samples](https://raw.githubusercontent.com/dingpengem/EMCD-Sim/v0.9.0-beta.1-macos-arm64.1/docs/images/macos/ni-quick-start-result.png)

If Run is unavailable, check that you used both **Done** and **Apply and Close**, and read the admission or MDFF explanation. Do not substitute another spectroscopy file to clear a validation message.

## 3. Save, reopen and export

1. Choose **File → Save As…**. Select **Documents**, name the project **My First Ni Calculation**, then save. Projects are folders: keep each entire project folder together.
2. Choose **File → Close Project**, then **File → Open Project…** and select the saved project folder. Saved results should return without another calculation.
3. For numerical files, use **Results → Export Results…** or **Output Settings → Export completed EMCD / EELS…** and choose a new folder in Documents.
4. For a picture, open the result view's **Display details / diagnostics / export** section and its **Export Figure…** action. Check the toolbar's **»** overflow if hidden. Choose PNG for an ordinary image or SVG for a vector figure.
5. If a later run triggers a retention prompt, choose **Keep as New Calculation** to preserve the earlier calculation.

## 4. Auto CPU and memory for later work

For everyday use, **Compute Resources → CPU workers → Auto** and **Memory budget → Auto** let the app choose resources for your request. The detected chip, core counts and RAM come from your Mac. Auto values can change with the calculation and available memory.

**Effective budget** is the allowed process memory; **Estimated peak memory** predicts the current request's use. **Pending** means configuration needs more information: read the reason. **Insufficient resources** means the request cannot currently be admitted.

At Run, memory is checked again and changes from the preview are reported. Manual values are retained when switching to Auto. The Quick Start uses Manual 1 / 2048 MiB to match its recorded case; try Auto afterward as a separate run.

To stop a calculation, click **Cancel** and wait for stopping to finish before starting another. Earlier completed results should remain available.

