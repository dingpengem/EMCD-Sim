# v0.9.0-beta.2 Windows Research Beta — candidate notes

**Unpublished RC1. No release tag or GitHub Release has been created.**
The published Windows beta.1 and macOS ARM64 beta.1 remain unchanged.

## Changes from published Windows beta.1

- One unified Compute Resources panel replaces Resource Estimate and duplicate
  worker/budget controls. It shows actual detected CPU/RAM, effective allocation,
  estimated process peak and admission status.
- Independent Auto/Manual worker and memory modes retain Manual values and old
  projects' explicit settings. Auto considers topology, useful work, current
  memory/commit/address-space headroom and existing safety reserves. It never
  reduces scientific sampling. SC uses one outer worker; DC is admitted with
  bounded concurrency and verified/restored BLAS limits. No four-worker cap is
  imposed, and more workers need not be faster.
- SC admission now accounts for the actual unchanged 64-pixel contraction batch,
  not a hypothetical full-map beam-pair allocation. Existing full results,
  FFT/depth buffers, worker scratch and safety margins remain included.
- New single-element results distinguish requested uniform points and evaluated
  samples. Old results are not silently rewritten. The representative Ni recipe
  requests 241 uniform points plus two exact features, yielding 243 energies
  and two 97×97 maps; other energies use detector support.
- Existing multi-site providers, Global/Local M, grouping/viewer, BW/MS SC/DC,
  explicit reversal, Results, exports and project persistence are retained.
  Scientific kernels, MDFF conventions and historical numerical references
  were not modified by this candidate preparation.
- Offline Windows installation, Quick Start, Tutorial and required illustrations
  accompany the candidate. Public macOS installation/documentation links remain
  independent. Python/Conda and manual BLAS variables are unnecessary for EXE use.

## Existing evidence and candidate acceptance boundary

The [Windows resource benchmark](WINDOWS_SC_DC_RESOURCE_BENCHMARK.md) records 16
completed full requests across four backends, worker scaling and separate Auto
cases. The focused SC correction passed four directly affected checks. Original
and later serial timings are both retained; these are observations on a shared
hybrid laptop, not universal speedup or RAM guarantees.

The final RC1 EXE requires its own focused native check. Earlier evidence is
not relabeled as fresh candidate execution: dev5 `ed03f7b` passed resource-panel
Save/Open/export and a small Ni run; dev6 `527a290` passed the complete raw-GUI
243-energy Ni BW-SC Quick Start. Earlier dev3 `190cb3a` exercised small Cr
BW/MS SC/DC, cancellation/restart and Auto/Manual resources; later source/API
benchmarks exercised all four full Ni requests at `527a290` and `9d6b7fb`.
The existing scientific/propagation code is unchanged, but those are distinct
source/build and dependency records, not final-RC packaged evidence.

## Numerical and release status

[Per-array numerical evidence and transfer inventory](WINDOWS_MACOS_NUMERICAL_EQUIVALENCE.md)
preserve the completed BW-SC comparison. Direct authentic Mac BW-DC, MS-SC and
MS-DC raw arrays are unavailable locally. Their cross-platform comparisons
remain **INCOMPLETE**; matching settings or timing summaries do not prove them.
No calculation was rerun to replace missing exports.

**NO-GO for publication/release acceptance** until those exports and comparisons
are available and final candidate evidence is reviewed. Internal candidate
building/testing may proceed with that gap explicit. No full regression or
broad source-guard campaign is authorized here; prior incomplete coverage stays
incomplete. Independent clean-PC/VM, code signing and repeatable performance
certification are not claimed.

## Packaging and scientific limitations

The candidate uses a separate Windows ZIP and matching corresponding-source
ZIP, with exact committed identity in `_internal/build_info.json` and the
existing manifest. Qt/PySide/Shiboken 6.12 sources and applicable notices are
retained; unused Qt PDF/Virtual Keyboard remain excluded. The official x64
Microsoft VC++ v14 runtime remains an external prerequisite. See
[installation](INSTALL_WINDOWS.md); existing packages are not overwritten.

Signals retain relative source amplitudes, not absolute cross sections,
quantitative material spectra or calibrated moments. General beam/FFT/depth
convergence remains unestablished. The Ni 2.0 Å⁻¹ potential cutoff misses the
first off-row harmonic near 2.029 Å⁻¹. The benchmark MS actual step 10/63 nm is
above the advisory 0.04 nm reference. Cross-platform agreement cannot establish
convergence, model accuracy or experimental calibration.
