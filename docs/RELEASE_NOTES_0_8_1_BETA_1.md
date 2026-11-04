# v0.8.1-beta.1 - Windows-only Research Beta

Python package: **0.8.1b1**. Windows numeric version: **0.8.1.1**.
Physics convention remains `forward_born_dagger_g_minus_h_v1`.

This release adds the accepted generalized single-element tensor framework and
explicitly parameterized approximate atomic ionization to the portable Windows GUI.
Publication requires the separate full source, native extracted-EXE, manifest and
checksum gates; the [public acceptance report](https://github.com/dingpengem/EMCD-Sim/blob/main/docs/WINDOWS_0_8_1_BETA_1_ACCEPTANCE.md)
records the final accepted source and artifacts. The public prerelease entry is
authoritative for publication state; source preparation is not a passed release gate.

## Included

- Declared complex Hermitian PSD 3x3 dipole tensor sources, explicit magnetic states,
  core-edge/element/frame matching and localized equivalent-site phases.
- Generalized BW and FFT Multislice Single/Double Channeling, using unchanged kernels.
- Approximate independent-electron 2p-to-3d cubic atomic generator: every material
  input is explicit, with radial provenance, spin-resolved holes, splittings,
  Gaussian broadening and the local magnetic-axis/rigid-frame convention.
- GUI generation from complete parameter JSON, embedded source bytes/SHA256,
  regeneration checks and source replacement/missing-source safeguards. Partial
  atomic provenance is rejected. Failed generation invalidates stale GUI state.
- Checksummed project save/open, plots and data export; old Ni providers/projects
  remain on their historical routes. Old Lobato projects do not migrate providers.
- Source Python API for declared XMCD-effective conversion; the portable GUI imports
  the generated JSON rather than supplying an automatic material-specific XMCD model.
- The original synthetic Fe parameter example is bundled under
  `_internal/examples/synthetic_fe_atomic_parameters.json`.

[Source cleanup](SOURCE_CODE_CLEANUP_0_8_1.md) audited all 64 modules: no unsafe file
removal was justified. Five unused diagnostic/runtime imports were removed. No
scientific function, independent reference, compatibility provider or test was deleted.
Version and release preparation were committed separately from cleanup.

## Scientific scope

Synthetic Fe outputs are **software tests only**, not physically validated Fe EMCD.
The atomic model is approximate and cubic. No quantitative Co/Cr model, general
crystal-field symmetry, complete DFT-derived MDFF, many-body multiplet/core-hole/
charge-transfer accuracy, validated AFM/SDW or multi-element site-resolved MDFF is
provided. Inputs and their sources must be declared, not borrowed from Ni defaults.
Intensities remain relative, not calibrated electron counts or experimental SNR.

The finite-case synthetic Fe Single/Double BW/MS differences (~0.064%/~0.128%) are
consistency tests only. Approximately 1.6% detector-refinement sensitivity remains
a documented limitation. No broad convergence, experimental accuracy or absolute
magnetic handedness is established by GUI/package acceptance.

The neutral elastic Adaptive Dirac-Pade Z=1-118 default and Apache-2.0 notices are
unchanged; Ni Lobato remains historical compatibility. The unlicensed legacy Z=1-98
table is external and not bundled. Historical raw-a.u. Ni [017] A/B and Flip-M
9/30 nm figures, provider metadata and saved scientific outputs are unchanged.
No historical study was regenerated or relabeled using a new provider.

## Windows distribution

Extract the complete unsigned portable ZIP; keep `_internal` with `EMCD-Sim.exe`.
No installed Python/Conda/WIEN2k is required. Native same-host testing is not an
independent clean-machine/VM certification. Linux/macOS packages are not offered;
existing Linux shutdown and macOS modal-test CI issues are neither suppressed nor
certified by this Windows-only release. Their status is reported separately from
Windows acceptance. v0.8.0-beta.1 and all older releases/assets are preserved.
