# First calculation with the current MDFF interface

[Home](../README.md) | [Installation](INSTALL_WINDOWS.md) | [MDFF workflows](MDFF_WORKFLOWS.md) | [Tutorial](TUTORIAL.md)

This is a small functional demonstration for the published [v0.8.1-beta.2 Windows Research Beta](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.8.1-beta.2). It is not a convergence result or timing guarantee. Install the [required Microsoft runtime and complete application ZIP](INSTALL_WINDOWS.md) first. For the older beta.1 binary, use its [version-specific Quick Start](https://github.com/dingpengem/EMCD-Sim/blob/v0.8.1-beta.1/docs/QUICK_START.md).

## 1. Start with the existing Ni example

Launch the application and choose **File > New** to restore the Ni structure. No project JSON is needed. Set nominal zone **0 0 1**, target **2 0 0**, then **Apply orientation / target**. Set **200 kV**, **0.2 nm** thickness, and tilt **-5, +7 mrad**. Use **Restore Thales A/B** after setting the geometry. Leave the current elastic provider explicit in your recorded settings; choose Ni Lobato only when reproducing an example that used it.

Under **Model**, open **Configure MDFF...** and choose **XMCD-constrained MDFF**. Select and validate the bundled Ni five-column source. In the beta.2 Windows package it is `_internal/data/wien2k_ni/Ni_fm.xmcd`; in source it is `data/wien2k_ni/Ni_fm.xmcd`. Do not retain a different material's file from an earlier session.

Use the native features actually returned by validation, crystal Cartesian M **0 0 1**, **eta = 1**, and **beta = 1**. Review and acknowledge the documented source magnetic axis, RP/LP convention, and edge assignment. The native calculated energies are not an experimental Ni edge calibration. For ambiguous input, both selections must be explicit; existing numbers are insufficient.

Click **Update preview**. Confirm the current source and provider tensor; this is not detector EELS. **Done** returns to the main calculation controls.

## 2. Choose a small manual calculation

Choose **Single Channeling**, **Bloch-wave**, and **Numerical Settings > Manual (Advanced)** before entering these values. Automatic mode chooses its own numerical starting configuration.

| Control | Coarse demonstration value |
| --- | ---: |
| Beam / MDFF basis cutoff | 0.6 inverse Angstrom |
| Potential Fourier cutoff | 1.2 inverse Angstrom |
| Explicit target systematic-row approximation | Off |
| Angular / detector grid points (odd) | 9 |
| Depth integration nodes | 5 |
| Aperture boundary subpixels | 4 |
| Map halfwidth | 0.7 inverse Angstrom |
| Spectral coverage | Selected declared edge samples only |
| Calculate angular maps | On |
| Parallel workers | Manual, requested workers 1 |
| Post-edge A/B correction | Off |

Support controls are in **Elastic Potential and Beam Support**; grid/depth controls are in **Inelastic and Angular Sampling**; worker controls are in **Computational Resources**. Read the resource estimate and any admission message. Do not silently coarsen a research calculation to make it run.

## 3. Run and inspect

Optionally calculate **Preview diffraction** to inspect elastic intensities. **Run EMCD / EELS** performs the inelastic calculation. Wait for completion; **Cancel** requests cooperative stopping, and the interface must return idle before another calculation.

Inspect **EMCD Angular Maps**, **Virtual Detector EELS**, and calculation information. Selected-edge mode evaluates only the declared samples: two plotted points are **not a resolved white-line spectrum**. Start with raw intensities; normalization percentages have different denominator assumptions and are supplementary. BW/MS comparisons, Double Channeling, full spectra, and refined sampling are separate calculations requiring their own convergence/resource review.

## 4. Create and reopen a project

Use **File > Save Project**, choose a writable parent folder, and provide a new project name. The application creates the JSON/CIF/NPZ project files from the completed result. Do not handcraft a project JSON. Keep the whole folder and original external sources.

Close and relaunch the application, select **File > Open Project...**, and choose that project folder. **Use These Settings** restores its verified model and configuration. Update the MDFF preview and rerun the small case if desired. Reopening saved arrays alone does not recalculate, convert a historical convention, or validate a missing source.

For the new Atomic editor and explicit Fe **710/723 eV** example, follow [Synthetic Fe from existing inputs](MDFF_WORKFLOWS.md#worked-example-synthetic-fe-from-existing-inputs). That example uses the supplied complete parameter input and is a software demonstration, not calibrated Fe spectroscopy. See [the user manual](USER_GUIDE.md) for detector definitions, normalization, and scientific limits.
