# EMCD-Sim v0.6.0 Beta - Double-Channeling EMCD Simulation

Windows x64 research **Pre-release**, tag `v0.6.0-beta.1`; application/package
version **0.6.0**. This is not a stable or quantitatively calibrated release.

[GitHub Pre-release](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.6.0-beta.1) -
[Windows ZIP](https://github.com/dingpengem/EMCD-Sim/releases/download/v0.6.0-beta.1/EMCD-Sim-0.6.0-Beta-Windows.zip) -
[SHA256SUMS.txt](https://github.com/dingpengem/EMCD-Sim/releases/download/v0.6.0-beta.1/SHA256SUMS.txt) -
[Build manifest](https://github.com/dingpengem/EMCD-Sim/releases/download/v0.6.0-beta.1/build_manifest.json) -
[Provenance](https://github.com/dingpengem/EMCD-Sim/releases/download/v0.6.0-beta.1/release_provenance.json).

## Install and learn

Download `EMCD-Sim-0.6.0-Beta-Windows.zip`, verify its SHA256 and **Extract All**.
Keep `EMCD-Sim.exe` beside `_internal`, then launch the EXE. No Python, Conda,
VS Code or WIEN2k runtime installation is required. Save projects in a separate
writable directory. The executable is **unsigned**; follow institutional
security policies. Independent clean-machine testing is **NOT TESTED**.

```text
6adda35a3b52ac35a06681a8cf5fca753aae2f03387feda57373c78ad8be2b5e
```

Build source: `c2caf4247a350e28a38b79cd402954d0c1ab2509`, clean isolated checkout.
Later release documentation/merge commits do not imply a different executable.
The exact size, source/frozen checks and provenance appear in the
[Windows acceptance report](WINDOWS_V060_BETA_ACCEPTANCE.md).

- [Windows installation](INSTALL_WINDOWS.md)
- [Quick Start](QUICK_START.md)
- [User Manual and signal definitions](USER_GUIDE.md#signal-definitions-in-060)
- [GUI reference](EMCD_GUI.md)
- [Changelog](CHANGELOG.md)

## Scientific milestone

Double Channeling was already included in **v0.4.5-beta.1**. Version 0.6.0
consolidates that framework and improves scientific visualization and
interpretation. It does not introduce Double Channeling for the first time.

Single Channeling retains entrance-only propagation. Genuine Double Channeling
integrates ionization through foil depth between incoming and reduced-energy
outgoing elastic propagation, retaining complex magnetic MDFF coherence.
Bloch-wave and independent FFT Multislice implementations support Single,
Double and Both comparisons with genuine energy-resolved Ni L3/L2 EELS.
Existing physical algorithms and numerical settings are preserved.

## Unified Raw / EMCD Asymmetry

Both primary EELS and angular views offer **Raw (a.u.)** (default) and
**EMCD Asymmetry (%)**. Raw retains original signed magnetic and nonmagnetic
components; total Asymmetry is the unchanged energy-local
`100*(I_A_plus-I_B_plus)/(I_A_plus+I_B_plus)` with no factor of two,
independent peak scaling or hidden post-edge correction. Total asymmetry can
include nonmagnetic diffraction imbalance and must not be called purely magnetic.
The original A/B spectra remain in a.u. above either lower-panel view.

Angular Raw uses magnetic/nonmagnetic differences between actual validated
(qx,qy)/(qx,-qy) samples. Angular Asymmetry uses their +M difference/sum.
Invalid/near-zero denominators remain NaN; signed scales and physical
000/ZA/hkl/target/Thales/aperture overlays remain. These are angular point-pair
quantities, not detector-integrated percentages. Integrate original aperture
intensities before taking the ratio, never average percentage pixels.

Advanced Diagnostics retains magnetic-only/even asymmetries on the common
N_A+N_B denominator, reversal spectra, intrinsic/local magnetic maps, raw total,
post-edge correction/residuals, legacy peak normalization, arbitrary-scale
detectability proxy and BW/MS diagnostics. Relative asymmetry alone does not
measure experimental detectability or SNR; arbitrary intensities are not counts.

Checksummed projects, Results Browser and PNG/SVG/CSV/NPZ exports remain.
Legacy PRB numerical fields and arrays are preserved; explicit new aliases
and denominator sidecars supplement them. Old Relative saved preferences open
explicit magnetic-only/even Advanced Diagnostics, never silently total Asymmetry.
Cooperative cancellation preserves completed results and supports restart;
a native numerical call must finish before acknowledging cancellation.

## Acceptance and limitations

Focused source tests, all six native worker dispatch cases, original-array
comparisons and extracted executable checks are recorded separately in the
[acceptance report](WINDOWS_V060_BETA_ACCEPTANCE.md). No full thickness or
voltage scans were rerun; acceptance does not establish global convergence.
The published 0.4.5 release/tag/assets remain unchanged.

Scientific limitations remain: XMCD-constrained approximate MDFF without a
complete DFT-derived transition tensor; projected elastic multislice potentials,
frozen longitudinal-transfer approximations, uncalibrated absolute EELS/counts,
native calculated energies without experimental calibration, limited tested
materials/geometries and representative parameter convergence only. No
experimental SNR calibration is supplied. Windows-only acceptance does not
certify Linux or macOS; their prior native-shutdown/RAM-adapter CI issues are
reported explicitly, not counted as passes.
