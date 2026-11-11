# v0.9.0-beta.1 — Windows Research Beta release notes

**Prerelease / Windows Research Beta, not a stable or quantitatively calibrated release.** Python version `0.9.0b1`, display `v0.9.0-beta.1`, Windows numeric version `0.9.0.1`. The release tag must identify the exact source embedded in `_internal/build_info.json`, the existing build manifest and the matching corresponding-source archive. Final user-guide/packaged-README changes follow verified RC2 without changing its numerical implementation; matching packages are built from that final documentation commit.

## User-visible scope

- General ASE/CIF viewer, structural orbit suggestions with original indices/Wyckoff/provenance, manual magnetic subgroups, normalized direction arrows and explicit ionization participation. Ordinary CIFs do not infer magnetism, moments or MDFF.
- Material-owned transactional Global/Local M. Local mode locks Global M; the shared XMCD/Atomic/Manual workspace shows inherited target M read-only. Validate/acknowledge, Done, then outer Apply and Close. Compatible physical reversal pairs are preserved through Apply, Save/Open and recalculation. Unsupported fixed-source rotations stay rejected.
- Multi-element/site BW/MS Single and Double Channeling, independent modeled energy windows and source amplitudes, incoherent localized-event sums with coherent elastic paths. Fixed per-selected-ionizing-atom normalization; excluded oxygen remains elastic.
- Uniform spectral sampling by default, plus exact selected energies. Selected-map/detector-only angular evaluation is independent; explicit all-energy full-field remains available. Internal FFT support is separate from requested detector coordinates.
- Normal-startup automatic verified thread control for both OpenBLAS runtimes, outer detector workers under existing admission, truthful response/depth progress and cooperative cancellation.
- Shared Global/Local Results with distinct Total/Element/Group Mean/additive Contribution/Comparison views, energy-aware Total deduplication, responsive layout, correct effective preset captions, scientific CSV/figure export and multi-calculation project management/restoration. Missing sources may block rerun without hiding saved arrays. Insufficient historical freshness evidence remains unavailable.

## Scoped evidence reused

RC2 addresses the outstanding comparison-legend crowding in the shared EELS rendering path. Legend rows use actual font/DPI measurements, wrap full labels and grow the scrollable canvas rather than overlap curves or axis decorations. A minimum-aware EELS canvas policy keeps the final legend rows reachable at high DPI. Both primary EELS/component panels and signal-only views retain clickable complete curves across separate modeled windows; the same legend artists remain in figure exports. This is a presentation correction, with no propagation, normalization or saved-array changes. Existing broad verification and scientific limitations below remain unchanged.

| Evidence | Meaning and limit |
| --- | --- |
| Legacy Ni, synthetic AFM Cr, inverse-spinel Fe₃O₄ and ordered NiFe₂O₄ validation | Existing scientific/numerical fixtures and native workflows; synthetic/effective MDFF is not calibrated material spectroscopy. See the corresponding `tests/test_multisite_scientific_validation.py`, `test_magnetite_site_benchmark.py`, and `test_nickel_ferrite_site_benchmark.py`. |
| Full NiFe₂O₄ BW Double | Completed original/optimized saved cases recorded **24.88× overall improvement**. It is case-specific, not a universal speedup claim; original and optimized numerical evidence is retained locally. |
| Bounded four-worker BW/MS Double, `62cb49a` | Actual concurrent work, verified NumPy/SciPy BLAS limits, progress, cancellation and subsequent success. Four workers are not universally faster. |
| Local MS selected scheduling, `daa5089` | **13 distinct focused cases passed**, covering the two repaired current-source test failures and relevant scheduling/numerical/window/cancellation behavior. A packaged 59-beam Fe₃O₄ MS Double case completed with 11 energies, 9×9 maps and **180** actual energy-pixel queries; Save/Open passed. |
| Original Fe₃O₄ MS request | Logged 243 energies, 97×97, selected-map policy and 160 detector-support pixels. Corrected planned work is **57,378**, versus the old route's 2,286,387. This is a query-work reduction, **not a measured full-size runtime improvement**. Original-size MS completion remains **unverified**. |
| Generic freshness | Existing focused round-trip/edit/revert and Cr evidence retained. Packaged `daa5089` restored preserved Global Ni and Local NiFe₂O₄ copies with matching inputs; real thickness edits (10→11 and 20→21 nm) marked them stale, and exact reverts restored matching status. No calculations were run. |

The latest two focused failures were reproduced and repaired as current-source expectations: the resource test now checks a real one-worker-fit/four-worker-rejection boundary under the approved live-allocation estimator; the GUI test uses approved defaults and the current MDFF acceptance workflow. Historical numerical references, safeguards and tolerances were not weakened. [Sampling detail](ENERGY_ANGULAR_SAMPLING_PERFORMANCE.md) explains detector support versus FFT support.

## Historical verification stays separate

- Source `49064fd`: historical Windows application regression **1,448 passed, 0 failed, 0 errors, 62 skipped, exit 0**; four separately validated scientific modules excluded. This is not a regression of the current RC.
- Later source `f769e05`: recorded application regression **1,300 passed, 40 failed, 126 setup errors, 62 skipped, exit 1**. Subsequent focused corrections do not turn that run into PASS. Broad application-regression/source-guard coverage remains incomplete.
- Focused inventories overlap. Counts are not summed into an invented comprehensive total. No new broad regression, guard/mutation campaign or scientific benchmark is claimed for this documentation/RC preparation.

The existing project format, safe loading, source identity and historical Global interpretation remain. Saved numerical arrays can be viewed without regeneration; missing/changed required sources block recalculation. Older convention metadata remains historical/unknown, not silently corrected.

## Scientific and software limitations

General beam-basis convergence is incomplete. Finite ZOLZ, projected IAM and continuous-depth localized ionization remain approximations; BW/MS convergence for some complex diffraction conditions is incomplete. Synthetic/effective MDFF lacks quantitative Fe₃O₄/NiFe₂O₄ spectral or magnetic-moment calibration and absolute cross-element scaling. No automatic magnetic-order inference, magCIF or general anisotropic tensor rotation is implemented. Direction alone is not a full tensor frame.

Independent clean-PC/VM Windows acceptance is unverified; Linux/macOS packages are not certified. Candidate packaging/native inspection is separate from numerical validation and does not complete the historical broad coverage. Source freeze/publication remains a subsequent explicit decision.

## Local package and proposed publication assets

- `EMCD-Sim-v0.9.0-beta.1-Windows.zip` — complete portable folder, EXE and `_internal`. Local RC1/RC2 artifacts remain preserved separately.
- `EMCD-Sim-v0.9.0-beta.1-Corresponding-Source.zip` — exact committed application source (including installation, Quick Start, Tutorial and illustrations) plus matching Qt/PySide/Shiboken sources and build/replacement instructions.
- Existing manifest/checksums and dependency licenses are retained. Qt PDF/Virtual Keyboard stay excluded; the required external Microsoft runtime is not bundled. spglib and Adaptive factor licensing/provenance remain included. Dependencies are not upgraded.

RC1/RC2 preparation was local and did not itself publish. Publication must integrate the intended source without discarding the original main worktree's unrelated work; its local branch need not be synchronized. Exact main/tag/build identities are recorded in the GitHub prerelease and packaged metadata. See [installation](INSTALL_WINDOWS.md), [Quick Start](QUICK_START.md), [Tutorial](TUTORIAL.md), [User Guide](USER_GUIDE.md) and [changelog](CHANGELOG.md).
