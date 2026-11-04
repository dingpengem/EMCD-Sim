# Verified v0.7.0-beta.1 documentation figures

The spectral figures here preserve the historical `20261102T232115Z` study and its original provenance. The current tutorial uses the [fresh recalculated Ni example](../ni017_flipm_recomputed/README.md). Native GUI captures in this directory remain current documentation references.

[Tutorial](../../TUTORIAL.md) · [User Manual](../../USER_GUIDE.md) · [Machine-readable provenance](provenance.json)

These are previews of **existing actual outputs**, not fabricated GUI controls or new scattering calculations. Originals, full-resolution PNG/SVG, numerical arrays and checkpoints remain unchanged in their original local directories. Preview downsampling is image-only; it does not increase or alter the calculated angular grid.

|Figure|Origin and interpretation|
|---|---|
|[gui_overview.png](gui_overview.png)|Accepted native EXE, source `97b2220e`, orientation [017], 1 nm selected-energy coarse acceptance case. Two energy points are not a full EELS spectrum.|
|[diffraction_preview.svg](diffraction_preview.svg)|Current-intensity preview exported by that actual EXE before dragging; documentation-copy whitespace cleanup only, with unchanged XML geometry/styles.|
|[laue_drag.png](laue_drag.png)|Native export after ZA drag; distinct circles, fixed A/B; gray geometry deliberately marks stale intensities.|
|[angular_smoke.png](angular_smoke.png)|Actual 9×9 mirrored-point angular components from native acceptance; functional presentation, not convergence evidence.|
|[ni017_raw.png](ni017_raw.png)|Existing 9/30 nm BW Double full spectra: conventional, magnetic, nonmagnetic and full fixed-A Flip-M raw differences.|
|[ni017_asymmetry.png](ni017_asymmetry.png)|Same actual study; A/B components share the +M sum, Flip-M uses its own reversal sum.|
|[ni017_contamination.png](ni017_contamination.png)|Same study; sampled nonmagnetic dominance and opposite-sign regions highlighted.|
|[ni017_eels.png](ni017_eels.png)|Same study; all four fixed A/B reversal spectra.|

The spectral study used source `08d04fc35fca2071cc7e73af0aaa1de45e49a3f4` (production code unchanged from released source), 300 kV, full 71-beam Ni [017]/(200), exact Bragg X, Y=+15 mrad, 9 and 30 nm. It evaluated 243 full-range energies, not merely two selected points and not all 4,329 original source samples. Native energies are unshifted/un-calibrated experimentally. See the [tutorial configuration and scope](../../TUTORIAL.md#part-vii-practical-ni-017-case-study).

The [selected-value CSV](ni017_selected_values.csv) copies the four source rows for checking the tutorial table, **not the full spectral dataset**. Its original local Windows-byte hash and Git/public LF-byte hash are recorded separately; Git text line-ending normalization does not change the values. SVG provenance likewise records the Git-blob hash in addition to local/source hashes; PNGs retain their byte identities. Original spectra/acceptance checksums, configuration, figure hashes and preview processing are in `provenance.json`. The study's eight selected-energy depth/grid checks do not establish global spectral/basis/potential or experimental convergence. None of these files is a replacement release binary or a new acceptance run.
