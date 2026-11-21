# macOS representative Ni Quick Start acceptance — 11 November 2026

**PASS: exact requested combined workload in the published native application.** [User walkthrough and genuine figures](QUICK_START_MACOS.md). This is automated native Qt acceptance, not direct human acceptance.

## Application identity and method

- Published tag: `v0.9.0-beta.1-macos-arm64.1`.
- Embedded source and result metadata: `03dc8f8d1f0374984c9fc81866eaa32ce48008d0`, clean build, ARM64, Qt Cocoa.
- [Published ZIP](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.9.0-beta.1-macos-arm64.1): 68,956,384 bytes; SHA256 `1d791f8c2bdce2abee5456f91ffad08013b9dbb847b9ef4a5279ae5d336ac6bc`. Testing used a fresh extraction of that exact archive.
- An external launch-time ARM64 controller scheduled native Qt interaction inside the frozen application. It used the app's own packaged Python/modules and normal widget callbacks, Qt mouse events and File actions. File-dialog return paths were supplied automatically. This instrumentation did not edit the bundle, replace scientific modules, inject an already accepted MDFF, change source paths for imports, or substitute a development application. Personal UI preference writes were suppressed.
- A failed LLDB attach preceded this method; no calculation ran in that process. Two initial controller attempts stopped on button-label lookups before Run. The successful third attempt performed the complete workflow without reducing or changing any requested scientific setting.
- Local evidence root: `outputs/macos-quick-start-20261111/attempt-3/`, containing `report.json`, `native-qt-controller.py`, `bootstrap.py`, `bootstrap.c`, native screenshots, normal exports and a new saved project. Historical candidates/projects remain intact.

## Acceptance matrix

| Case | Status | Evidence |
| --- | --- | --- |
| New project, raw bundled Ni CIF | PASS | Four Ni atoms; 3.520 Å cubic cell; native Viewer capture |
| Global M = (0,0,1), raw XMCD declarations | PASS | Source checked through MDFF dialog; eta/beta 1; relative reference 1; status `physical_source_unvalidated` |
| Done → Viewer → Apply and Close | PASS | Mouse-click Done kept Viewer open and state unaccepted; Apply and Close accepted it |
| Exact geometry / propagation / cutoffs | PASS | 200 kV, 10 nm, [017]/(200), full finite ZOLZ, tilt (−7.124812628,0) mrad; BW Single; systematic-row off; Adaptive Dirac–Padé 2026; cutoffs 2.5/2.0 Å⁻¹; B=0; 21 beams |
| Requested numerical settings | PASS | 64 depth nodes / 64 boundary subpixels / halfwidth 1.0 Å⁻¹ / grid 97 / uniform points 241; selected maps on, every-energy full fields off |
| Auto admission and execution | PASS | CPU/memory Auto; Ready; actual BW 1 worker / 729 MiB |
| Energy calculation | PASS | 243 unique increasing energies; exactly uniform 241 plus selected 831.271 / 848.698 eV; interval 823.625–882.521 eV |
| Genuine response at every energy | PASS | 243 ordered diagnostics, all evaluated pixels >0, none checkpoint-reused; 2 full fields ×9,409 pixels, 241 detector-support responses ×162 pixels |
| Actual angular coordinates/maps | PASS | qx/qy and both selected full intensity maps 97×97; −1…+1 Å⁻¹; spacing 1/48 Å⁻¹; no coarse-map enlargement |
| Signal definitions / selectors | PASS | Native magnetic/nonmagnetic selectors exercised; reversal/parity identities checked without changing convention |
| Export | PASS | Normal Results export plus figure export; CSV, spectrum NPZ and both selected map fields/figures |
| Save → Close → Open | PASS | Normal File actions; crystal, geometry/configuration, accepted MDFF declaration, Auto modes and numerical-result fingerprints preserved |
| Native layout | INCOMPLETE | Genuine captures reveal partly clipped energy-count text and result viewport; complete normal figure exports are provided. No claim of clipping-free layout |
| Human interaction | INCOMPLETE | File-picker selections automated; trackpad, Retina, focus/window management and ordinary quarantined first launch need direct user inspection |

## Numerical evidence

Every spectrum array has shape `(243,)` and finite values. The final detector spectra were calculated at each energy, not interpolated from two selected detector intensities. Interpolation of the source MDFF onto requested energies is a separate, expected operation.

Both L3/L2 `I_plus`, `I_minus`, `I_mag` and `I_nonmag` fields have shape `(97,97)` and are finite. A-supported paired contrasts deliberately mask values outside their aperture support with NaN, as defined by the released `paired_maps`; those masks are not failed calculations. The exported coherence matrix is `(21,21)`. Detector A/B centres are `(0.2840909090909091, ±0.2840909090909091)` Å⁻¹, radius 0.09 Å⁻¹, with 64-subpixel boundary weights.

Reversal checks included `N_A=(I_A_plus+I_A_minus)/2`, `M_A=(I_A_plus−I_A_minus)/2` at relative tolerance 1e−12 / absolute tolerance 1e−14 times the maximum detector signal; `D_raw=D_mag+D_nonmag` at 1e−10 / 1e−13 respectively. These are internal identity checks, not a platform comparison.

| Relative detector quantity | Minimum | Maximum |
| --- | ---: | ---: |
| I_A(+M) | 6.899160629e−5 | 0.04586464795 |
| I_B(+M) | 7.122068049e−5 | 0.03647209887 |
| D_mag | −0.01055924498 | 0.009727368427 |
| D_nonmag | 0 | 2.081668171e−17 |

The EELS source features and sign-changing magnetic detector difference are numerically interpretable within the declared relative, axisymmetric source model. No quantitative magnetic moment, absolute cross section, experimental energy resolution or convergence certification follows.

**Numerical support limitation retained:** at the requested potential cutoff 2.0 Å⁻¹, the app warns that the first off-row ZOLZ potential harmonic is about 2.029 Å⁻¹, so no off-row potential harmonics are retained. Full finite ZOLZ is the selected basis mode, but this requested potential is not a full 2D potential. The setting was retained exactly; this run does not establish off-row convergence.

## Timing and memory

M2 Pro (Mac14,9), ARM64, 10 logical cores (6P/4E), 16 GiB, macOS 26.3.1. Published NumPy 2.4.6 / SciPy 1.17.1, Accelerate; fixed native BLAS limits are handled by the unchanged application.

| Measurement | Value |
| --- | --- |
| Requested modes | CPU Auto / Memory Auto |
| Preview | BW 1, budget 723 MiB, estimated process peak 424.3 MiB |
| Final Run allocation | BW 1, budget 729 MiB, estimated process peak 396.6 MiB |
| Process RSS at run-sampling baseline | 261.4 MiB |
| Sampled Run/display RSS peak | 299.6 MiB (1,939 readings, 20 ms target interval, nonuniform actual scheduling) |
| Native lifetime RSS high-water mark | 401.9 MiB, includes startup/configuration |
| Calculation wall time | 93.4034 s |
| Run through display | 94.3842 s |

The machine already had Warning memory pressure and about 4.6 GiB swap in use; admission remained Ready. A sampled peak can miss short transients. The lifetime peak and conservative Run estimate cover different scopes. The completed-resource screenshot also shows a refreshed prospective estimate (777 MiB budget / 422.5 MiB peak); it is not the finalized allocation. This single instrumented run does not predict performance on other machines.

## Artifacts and remaining scope

Public unchanged exports: [CSV](examples/macos-ni-quickstart/bloch_spectra.csv), [spectra NPZ](examples/macos-ni-quickstart/virtual_detector_eels.npz), [maps NPZ](examples/macos-ni-quickstart/angular_maps.npz). Complete figures and genuine native captures are embedded in the [Quick Start](QUICK_START_MACOS.md#6-verified-run-and-genuine-figures).

Local saved project: `outputs/macos-quick-start-20261111/attempt-3/Ni-QuickStart-project/`. Full export folder: `outputs/macos-quick-start-20261111/attempt-3/exports/emcd_20261111_002652_878206/`. Reopening preserved every fingerprinted numerical array without recalculation.

**INCOMPLETE:** direct human native acceptance and authentic matched Windows numerical comparison. This work does not extend acceptance to other propagation/channeling modes or prove quantitative Ni calibration. The app remains ad-hoc signed and not notarized. No scientific source, released application, release tag or release asset was changed. Only documentation and genuine reference figures/data are published by this update.
