# EMCD-Sim

EMCD-Sim is a research simulation tool for **electron magnetic circular dichroism (EMCD)** using Bloch-wave (BW) and independent FFT multislice (MS) propagation. It combines dynamical electron diffraction, approximate core-loss scattering tensors and virtual-detector EELS/EMCD analysis, with fcc Ni as the principal validated material.

**Current source / Windows Actions candidate: v0.6.1-beta.3 (package 0.6.1b3).**
[Beta 3 build and installation](docs/WINDOWS_BETA_3.md) ? [Download from a successful Windows Actions run](https://github.com/dingpengem/EMCD-Sim/actions/workflows/windows-build.yml). The candidate ZIP is `EMCD-Sim-v0.6.1-beta.3-Windows.zip`; no Beta 3 release or tag is created.

**Latest published release: v0.6.1-beta.2 (preserved).**
[Release and download](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.6.1-beta.2) · [Windows installation](docs/INSTALL_WINDOWS.md) · [Quick Start](docs/QUICK_START.md) · [User Manual](docs/USER_GUIDE.md) · [Release notes and acceptance](docs/RELEASE_NOTES_0_6_1_BETA_2.md).

## Main capabilities

- Single Channeling (entrance-only) and Double Channeling (incoming diffraction, depth-distributed ionization and post-loss outgoing diffraction).
- Bloch-wave, FFT Multislice and matched **Both (BW / MS comparison)** calculations.
- Virtual Detector EELS, selected L3/L2 samples or full native energy-resolved spectra, and magnetization reversal.
- **Full-field EMCD Angular Maps** over actual calculated reciprocal-space samples, independently of detector-circle overlays.
- Signed magnetic/nonmagnetic decomposition, raw differences, total EMCD Asymmetry and Advanced Diagnostics.
- Checksummed projects, Results Browser, PNG/SVG figures and CSV/NPZ scientific exports.
- Configurable memory admission, cooperative cancellation and checksummed saved results.
- Beta 2 adds Automatic / Manual Numerical Settings, exact detector-support sampling away from selected map energies, and optimized MS Double buffers. Automatic performs configuration checks without trial simulations; convergence still requires numerical validation.

## Supported physical models

Elastic propagation uses an oriented **projected independent-atom-model (IAM) potential**. Single retains entrance channeling; Double also propagates the outgoing electron at its reduced post-loss energy. BW and MS are independent numerical implementations within matched physical approximations.

The principal Ni MDFF is an **XMCD-constrained effective Hermitian tensor**. An approximate atomic-ionization model is also available. A complete DFT-derived MDFF from complex core-to-band transition matrix elements is **not implemented**. CIF import supports structural inspection; it does not validate arbitrary materials for magnetic EELS. The separate generalized-multislice development branch uses one structure-derived Projected ZOLZ engine for bounded crystallographic directions, with [001]/[017]/[117]/[111]/[710] BW/MS Single/Double comparisons. Orientation-specific geometry modules are retained only as frozen test references. See the [architecture](docs/GENERALIZED_MULTISLICE_ARCHITECTURE.md), [validation and explicit convergence failures](docs/GENERAL_ZOLZ_MULTISLICE_VALIDATION.md), and [Atomic 3D integration plan](docs/ATOMIC_3D_MULTISLICE_DEVELOPMENT.md). Atomic 3D is not implemented by this milestone. These source additions are not in the preserved Windows packages.

For [117], crystal-[001] magnetization is rotated once into the target-aligned frame; raw magnetic intensity need not be mirror-antisymmetric. The default potential cutoff 2.5 cycles/Å has no off-row [117] harmonics. Use explicit research settings and resource checks; Automatic does not establish convergence. See the [configuration guide](docs/USER_GUIDE.md#research-ni-117--2-20), [scientific validation](docs/NI_117_FINAL_SYMMETRY_VALIDATION.md) and [merge-readiness review](docs/NI_117_MERGE_READINESS.md). Validation is representative, not a universal convergence or experimental-accuracy claim.

The generalized branch now has [normal-GUI end-to-end validation](docs/GENERALIZED_MULTISLICE_EMCD_VALIDATION.md)
for all five representative orientations in Single/Double BW/MS. The [111]
angular/aperture refinements pass at the tested 2 nm point, but a joint raw-intensity
check still fails; general production convergence remains uncertified. No Atomic
3D implementation, packaged EXE update or release is included.

The [final scientific merge review](docs/GENERALIZED_MULTISLICE_MERGE_READINESS.md)
recommends merging this bounded research implementation with explicit limits.
The [111] residual is dominated by potential/beam support; larger-MS increments
pass at the tested point, while the lower-support profile remains uncertified.
Main and existing Windows packages have not been updated by this review.

The subsequent [local main merge acceptance](docs/GENERALIZED_MULTISLICE_LOCAL_MERGE_ACCEPTANCE.md) records the authorized merge and post-merge checks. No GitHub push, Windows rebuild, version change or release was performed.

## Installation

### Beta 3 Windows candidate

Use the [Actions installation instructions](docs/WINDOWS_BETA_3.md#download-and-install). The three adjustable scientific panels keep Settings and Diffraction visible together; chevron sections and Project Results collapse to release plot space. Layout preferences persist independently of scientific projects. Defaults remain 300 kV, beam/potential cutoffs 3.2/2.5 cycles/Angstrom, 97x97 and 2048 MiB. No physics changes or new full-curve convergence claims are introduced.

### Historical published Beta 2 portable application

1. Open [v0.6.1-beta.2 Releases](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.6.1-beta.2).
2. Download [EMCD-Sim-0.6.1-beta.2-Windows.zip](https://github.com/dingpengem/EMCD-Sim/releases/download/v0.6.1-beta.2/EMCD-Sim-0.6.1-beta.2-Windows.zip) and `SHA256SUMS.txt`.
3. Verify SHA256, then **Extract All** into a normal writable folder.
4. Open the extracted **`EMCD-Sim/EMCD-Sim.exe`**. Keep `_internal` and all other application files beside it; do not run inside the ZIP or copy only the EXE.

```powershell
Get-FileHash "$HOME/Downloads/EMCD-Sim-0.6.1-beta.2-Windows.zip" -Algorithm SHA256
```

Require an exact match to the Beta 2 release's `SHA256SUMS.txt`. The Beta 1 archive and checksum remain preserved in its historical release.

The package bundles its Python runtime and is intended to run without a separate Python/Conda/WIEN2k installation. Same-host standalone testing passed; **independent clean-machine installation remains NOT TESTED**. This Windows x64 Beta is unsigned. See [installation and troubleshooting](docs/INSTALL_WINDOWS.md), including saved-project reopening. The historical Beta 1 ZIP is retained unchanged despite its `RC` filename.

### From Python source

The source package contains the current GUI, active BW/MS and tensor algorithms, persistence and safety code. Historical study drivers have been retired; see the [source audit and supported interfaces](docs/SOURCE_CLEANUP.md). The published Windows packages are unchanged by this source cleanup.

With a suitable Python environment (tested with Python 3.11), clone this repository, open its directory, then run:

```powershell
python -m pip install -e ".[gui]"
python -m emcd_sim.gui
```

Source installation is a separate workflow; the portable EXE does not require this step. Linux/macOS source support does not establish standalone binary acceptance on those platforms.

## Quick Start

Choose **File → New**, **FCC Ni default**, nominal zone `0 1 7` and target `2 0 0`. New projects start at 300 kV. For the historical 200 kV reference, explicitly set 200 kV and use **Reset to reference geometry** for Tilt X approximately -7.11672544 mrad and Tilt Y = 0. Click **Preview diffraction**; exact (200) Bragg alignment is not zero-tilt zone-axis incidence or an isolated two-beam wavefield.

Select and validate the bundled five-column XMCD source, inspect its native energy assignments and explicitly declare the magnetization/polarization convention. Choose **Channeling Model**, **Propagation Method** and **Spectral coverage**. For a faster selected-energy workflow choose **Selected L3/L2 samples only (not full EELS)**. Click **Run EMCD / EELS** once. **Cancel** cooperatively stops the worker while preserving the last completed result. Do not start duplicate jobs while initialization or cancellation is pending.

## GUI workflow

**Post-release source defaults:** new projects now use beam cutoff **3.2 Å⁻¹** and potential Fourier cutoff **2.5 Å⁻¹**. Automatic starting settings and New Project use these values; saved projects retain their explicit settings. The published Beta 2 Windows ZIP retains its original 3.0/2.0 defaults until a new build is validated and released.

**Beta 2 worker-safety update:** new projects start at **300 kV**, beam/MDFF cutoff **3.0 Å⁻¹**, potential cutoff **2.0 Å⁻¹**, angular grid **97×97** and **2048 MiB**. Panel F adds independent Automatic/Manual **Parallel Workers**, actual native BLAS threading and a pre-Run resource/risk preview. These are starting settings, not universal convergence or crash guarantees. The old Beta 1 and development ZIPs predate this fix; see the [validation report](docs/BW_PARALLEL_WORKER_SAFETY.md).

**Beta 2 numerical settings:** numerical settings default to Automatic, with a read-only parameter summary and full Manual overrides. Selection uses inexpensive configuration checks, without trial simulations or a guarantee of convergence. MS-only FFT/slice controls remain separate from shared support and sampling. See the [selection policy](docs/USER_GUIDE.md#automatic-and-manual-numerical-settings) and [parameter-role table](docs/USER_GUIDE.md#development-source-shared-and-solver-specific-settings). The historical v0.6.1-beta.1 binary is unchanged.



1. Set structure, zone/target, voltage, thickness, absolute incident tilt and diffraction settings.
2. Choose the MDFF and crystal-frame magnetization, then Single/Double and BW/MS/Both.
3. Use **Automatic** Numerical Settings, inspect **View Numerical Parameters**, and switch to **Manual (Advanced)** for explicit overrides. Set physical detectors separately. Automatic distinguishes matching reference settings from starting configurations.
4. View **BW/MS Diffraction**, **Virtual Detector EELS** and **EMCD Angular Maps**. **Signal Display** offers **Raw (a.u.)** or **EMCD Asymmetry (%)**; Advanced Diagnostics retains magnetic-only/even percentages and corrected contrasts.
5. Save with **File → Save Project As...**. Reopen the complete project folder with **Open Project** or **Results Browser → View Selected**; viewing does not rerun physics. **Use These Settings** restores inputs separately.

**Angular Map Resolution:** Quick Preview 33 x 33, Standard **97 x 97 (default)**, High 193 x 193, or supported odd Custom sizes. It adds actual reciprocal-space samples; it is separate from the FFT propagation mesh and aperture boundary subpixels. Angular maps and detector-EELS quadrature currently share the angular grid.

Full-field maps are evaluated at selected L3/L2 energies. Other requested spectral energies use the exact union of nonzero fractional A/B aperture weights, without interpolation or dropping energies. This applies to BW/MS Single/Double and Both. Private MS Double working buffers reduce allocations without changing precision, propagation or diagnostics. Measured three-energy BW/MS Double times were 23.41→15.35 s and 134.23→80.32 s; later outgoing-field buffer improvements were 40.61→36.61 s at 8 nm and 41.58→37.91 s at 30 nm. These matched 300 kV benchmarks are not full-spectrum or whole-GUI timing guarantees.

The historical **v0.6.1-beta.1 ZIP remains unchanged** and predates these improvements. The [integration report](docs/GUI_PERFORMANCE_INTEGRATION.md) and [development installation instructions](docs/INSTALL_WINDOWS.md#local-windows-development-build) retain the earlier local-build record; Beta 2 is the version-matched prerelease of these developments.

**Estimated process memory budget:** 512, 1024, **2048 (default)**, 4096 or 8192 MiB. This is a ceiling, not a reserved allocation. Available RAM and estimated process peak are checked; High does not necessarily fit 2048 MiB. Existing explicit saved settings are preserved; New Project resets angular grid/budget to 97/2048. See [sampling and memory](docs/ANGULAR_MAP_RESOLUTION.md).

## Example simulations

The preferred reference is **fcc Ni [017], exact (200) Bragg, 200 kV, 8 nm, Double Channeling, Bloch-wave**. Use Tilt X = -7.116725439974256 mrad, Tilt Y = 0, crystal magnetization [001], eta = beta = 1, and the physical Thales A/B apertures. The [reproducible GUI example](docs/USER_GUIDE.md#validated-ni-017-8-nm-double-example) gives source hashes, actual detector coordinates, energies and all numerical settings, using Standard 97 and a 2048 MiB budget. MS or full-energy spectra may take substantially longer; a selected L3/L2 calculation is not a fabricated full spectrum.

The completed **200 kV, 0–100 nm at 2 nm steps** study covers BW/MS, Single/Double, L3/L2 and [017] full finite ZOLZ / [001] restricted row: **204 checkpoints, 426 regression passes**. Maximum BW/MS detector asymmetry discrepancy is **0.009656 pp**; maximum relative raw-intensity error is **0.015097%**, within unchanged 0.01 pp / 0.1% gates. These certify the tested matched profile, not global physical convergence. See [scientific analysis](docs/NI_EMCD_THICKNESS_SCIENTIFIC_ANALYSIS.md) and [representative angular convergence](docs/ANGULAR_MAP_CONVERGENCE.md).

![Verified Ni [017] X/Y survey](docs/images/ni017/xy_overview.png)

Actual historical 200 kV, 30 nm BW/MS calculations; this existing survey image is not the new 8 nm/97-grid example. Its colorbar fractions are not percentages. The [case-study gallery](docs/NI_017_CASE_STUDY_GUIDE.md) retains angular/EELS plots and raw/corrected interpretation.

## Output formats and interpretation

Projects retain settings, native energies, source hashes and original arrays in JSON/CIF/NPZ files. CSV/NPZ exports retain raw magnetic and nonmagnetic differences and explicit percentage definitions; PNG/SVG exports include display metadata. Keep each project folder complete. The [User Manual](docs/USER_GUIDE.md#export-figures-and-data) explains original versus derived exports.

For detector J, `N_J=[I_J(+M)+I_J(-M)]/2` and `M_J=[I_J(+M)-I_J(-M)]/2`. Thus `D_mag=M_A-M_B`, `D_nonmag=N_A-N_B`, and `D_raw=D_mag+D_nonmag`. Raw detector EMCD Asymmetry is `100*[I_A(+M)-I_B(+M)]/[I_A(+M)+I_B(+M)]`; it can contain reversal-even diffraction contributions.

The angular Asymmetry uses actual `q=(qx,qy)` and `q'=(qx,-qy)` samples: `100*[I_plus(q)-I_plus(q')]/[I_plus(q)+I_plus(q')]`. Detector circles are overlays. Integrate **raw intensities before taking a detector ratio**; never average local percentages. Invalid/near-zero denominators remain NaN. Post-edge-corrected contrast is not intrinsic magnetic EMCD. See [signal definitions](docs/USER_GUIDE.md#signal-definitions-in-061).

<a id="known-limitations"></a>

## Scientific limitations

- XMCD-constrained approximate MDFF, not complete DFT transition matrix elements.
- Projected IAM elastic potential, not genuine atomic-3D electrostatic multislice; longitudinal transfer uses the documented approximation.
- BW/MS agreement is numerical cross-validation within shared approximations. Full physical-parameter convergence has not been demonstrated globally.
- Absolute EELS intensities, native calculated energy calibration and experimental counting statistics are uncalibrated. Arbitrary units and percentages are not electron counts or experimental SNR.
- Raw EMCD Asymmetry can contain nonmagnetic contributions. Sampled thickness maxima are not globally converged optima.
- [001] restricted systematic-row results are not validated full-ZOLZ exact two-beam geometry. [017] remains the preferred reference.
- Independent clean-machine Windows installation is **NOT TESTED**. The app is unsigned; local acceptance is not signing or SmartScreen certification.

## Documentation

[Windows installation](docs/INSTALL_WINDOWS.md) · [Quick Start](docs/QUICK_START.md) · [Complete User Manual](docs/USER_GUIDE.md) · [GUI technical/milestone reference](docs/EMCD_GUI.md) · [Ni [017] case study](docs/NI_017_CASE_STUDY_GUIDE.md) · [Scientific analysis](docs/NI_EMCD_THICKNESS_SCIENTIFIC_ANALYSIS.md) · [Angular resolution](docs/ANGULAR_MAP_RESOLUTION.md) · [Angular convergence](docs/ANGULAR_MAP_CONVERGENCE.md) · [Release notes](docs/RELEASE_NOTES_0_6_1_BETA_1.md) · [Acceptance/provenance](docs/V061_BETA_ACCEPTANCE.md) · [Changelog](docs/CHANGELOG.md).

## Citation and license

For reproducibility, cite the repository and exact release/commit, and report source hashes, geometry, MDFF, detectors, grid/basis/cutoff/depth settings and signal definitions. The theoretical normalization reference is Rusz et al., Physical Review B 75, 214425 (2007); normalization agreement alone is not complete physical equivalence. No software paper or DOI is claimed here. Code is distributed under the [MIT License](LICENSE); third-party runtime licenses remain with the Windows distribution.

Previous [v0.6.0-beta.1](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.6.0-beta.1) and [v0.4.5-beta.1](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.4.5-beta.1) releases/assets remain preserved. Their original documentation and source remain available in Git history.

## Historical studies and current source interfaces

The [source cleanup audit](docs/SOURCE_CLEANUP.md) identifies retired research
drivers and their replacements in the current runtime. Historical numerical
datasets, figures, published packages and scientific reports remain preserved;
old study commands require their original Git revision.

Current installed commands are `emcd-gui`, `emcd-import-transitions` and
`emcd-ni-local-mdff`. `python -m emcd_sim` also launches the desktop application.
The latter two commands prepare complex transition datasets and atomic-model
inputs; they do not run DFT or claim a complete DFT-derived Ni MDFF.
