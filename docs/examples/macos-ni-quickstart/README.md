# Published macOS Ni Quick Start reference exports

These are unchanged files produced by the published macOS app's normal Results export on 11 November 2026. See the [recipe](../../QUICK_START_MACOS.md) and [acceptance record](../../MACOS_QUICK_START_ACCEPTANCE.md).

- `bloch_spectra.csv`: 243 energy-resolved rows, including detector/reversal/parity signals.
- `virtual_detector_eels.npz`: `bloch__energy_ev` and 15 corresponding 243-element signal arrays, plus method/channeling labels.
- `angular_maps.npz`: `qx`, `qy`, aperture weights, and L3/L2 97×97 fields. `I_plus`, `I_minus`, `I_mag`, `I_nonmag` are finite full fields. A-supported paired contrasts deliberately contain NaN outside positive `weight_A`, as defined by `paired_maps` in the released application. Includes the 21×21 coherence matrix.

Intensities are relative, with tensor reference 1 and scientific status `physical_source_unvalidated`. These files demonstrate execution and sampling, not experimental calibration or a converged reference standard. No Windows equivalence is asserted.
