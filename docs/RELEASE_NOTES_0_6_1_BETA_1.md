# EMCD-Sim v0.6.1-beta.1 — Windows Beta

- **Full-field EMCD Angular Maps:** display all valid calculated reciprocal-space samples with physical mirrored-point pairing, detector overlays, crystallographic markers and nearest-sample rendering. Raw magnetic/reversal-even differences remain distinct from total angular asymmetry and detector-integrated EELS.
- **97 x 97 default angular resolution:** Preview 33, Standard 97, High 193 and supported odd Custom grids. Actual saved map dimensions and q spacing are displayed. FFT sampling and aperture subpixels remain independent; angular sampling and EELS detector quadrature remain shared.
- **2048 MiB default RAM budget:** configurable 512–8192 MiB budgets, available-memory checks and preserved explicit saved settings. Numerical settings are not reduced automatically.
- **BW/MS Single and Double Channeling:** Bloch-wave and FFT multislice calculations, virtual-detector EELS, signed raw EMCD, percentage diagnostics, project save/open and figure/data export.
- **Complete 200 kV Ni thickness validation:** BW/MS, Single/Double, L3/L2 and 0–100 nm in 2 nm steps, for [017] full finite ZOLZ and [001] restricted systematic-row reference. All 204 production checkpoints are unchanged. Maximum BW/MS discrepancy is 0.009656 pp; maximum relative raw-intensity error is 0.015097%, within unchanged 0.01 pp / 0.1% gates. All 426 regression tests passed.

**Scientific limitations:** solver agreement certifies the tested matched profiles, not globally converged physics or experimental validation. The MDFF remains XMCD-constrained rather than a complete DFT-derived transition tensor; projected IAM and existing longitudinal-transfer approximations remain. Absolute energy/intensity calibration is not established. Sampled thickness extrema are not global optima, and [001] is a restricted-row comparison. Post-edge correction is not intrinsically magnetic; arbitrary-unit signals are not calibrated electron counts or experimental SNR. Representative angular convergence covers Ni [017], 8 nm, L3 Double only.

Extract the complete ZIP and keep `_internal` beside `EMCD-Sim.exe`. The Windows package is unsigned. Production datasets and licensed WIEN2k companion files are not bundled. See [release acceptance](https://github.com/dingpengem/EMCD-Sim/blob/v0.6.1-beta.1/docs/V061_BETA_ACCEPTANCE.md) for the installation environment, provenance and detailed validation.

ZIP SHA256: `9fd5e71437d2c26d4595abb7adde9436e4c333ce18f3a57cf381b0c541bfd94f`.

**Windows validation:** local Windows 11 acceptance passed; independent clean-machine installation remains **NOT TESTED**. The package is a research prerelease, not a stable/Latest release.

**Binary provenance:** the unchanged ZIP was built from validated runtime source revision `e66c97923bd4838188ed03c424dc9973ada55c25`. Subsequent release commits modify documentation and acceptance metadata only; every packaged runtime source hash matches the accepted runtime. The RC filename and original build label are retained intentionally. The tag identifies the final main commit including documentation, not a rebuild.
