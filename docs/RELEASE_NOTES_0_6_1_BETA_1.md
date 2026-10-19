# v0.6.1-beta.1 — local Windows candidate

This candidate integrates the completed full-field angular-map behavior and the read-only scientific audit of the 200 kV Ni thickness study. It is not a public release. Python package metadata uses the equivalent PEP 440 version `0.6.1b1`.

Primary angular maps use the full valid calculated grid, independently of the A/B aperture overlays. Raw magnetic and reversal-even point-pair differences remain separate from total EMCD asymmetry. Missing full-field arrays produce an unavailable-data message; unsupported pixels are never synthesized. Historical diagnostics remain accessible in Advanced Diagnostics.

The scientific report distinguishes original +M detector asymmetry from the additive reversal-even-denominator decomposition. It also separates the sampled percentage maximum from the maximum raw magnetic intensity difference. See [scientific analysis](NI_EMCD_THICKNESS_SCIENTIFIC_ANALYSIS.md) and [acceptance record](V061_BETA_ACCEPTANCE.md).

BW/MS, Single/Double channeling, detector EELS, raw/percentage displays, cancellation, project save/open and export retain the existing solver implementations. No physics parameters, source spectra, propagation kernels or production checkpoints were changed for this candidate. The packaged Ni example remains the tracked repository example; it is not a replacement for the separately hashed study source. Production datasets are not bundled.

The distribution is unsigned. Extract the complete ZIP and keep `_internal` beside the executable. Existing v0.6.0-beta.1 releases and assets remain unchanged. No push, merge, release tag or publication is authorized by this task.
