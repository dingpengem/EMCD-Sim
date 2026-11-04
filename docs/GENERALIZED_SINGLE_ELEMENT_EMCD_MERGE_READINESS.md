# Generalized single-element EELS/EMCD — independent merge readiness

Review date: **2026-11-04** (America/Los_Angeles). **GO for local research/software integration**, after correcting the findings below. This is not approval of quantitatively validated Fe EMCD, broad convergence, a binary package or a public release.

## Exact sources and local integration

|Identity|Commit|
|---|---|
|Starting local main|`2f9c130099dce5df4e4609b521c42f53c5385518`|
|Original feature tip reviewed|`1aa1efb5fa2f8d9ac4e6bfdba5ef18d7bced0221`|
|Earlier validated scientific source, retained as historical evidence|`7c1d4a356e05f69cb0f4bfcf19905fbf35c0b27b`|
|Source/shape review fix|`f8a1a65c219e57a3d9ca42d518fa3c1e0e0d4bb5`|
|Final corrected feature tip|`bde4b30e287f08ab25652fb22b0e4f978cd2952b`|
|Accepted/tested **no-ff merge commit**|**`ff894941be0cf790f5644137d6355bfc767f86c8`**|
|Exact tested tree|`1669220e6083ea45efa5b55768f3f84e5891eac0`|

The merge has exactly two parents: starting main and the corrected feature tip. It was prepared with normal `git merge --no-ff` on `integration/single-element-main-reviewed` in the isolated `build/single-element-main-integration` worktree. Main remained unchanged while that exact clean commit passed the complete Windows suite. After GO, local main advanced by fast-forward to this tested two-parent merge; there was no reset, squash, rebase or replacement of the tested source.

The original feature branch remains `feat/generalized-single-element-emcd` at the corrected tip; the supplied original tip and earlier scientific source remain in its ancestry. The previous main worktree remains intact on `preserve/main-before-single-element-20261104` at its original source. The superseded candidate/reproduction evidence is retained, but its interrupted suite is not acceptance evidence. This report is a subsequent documentation-only commit; it does not alter the merge's tested scientific source.

## Review scope and corrected blockers

All **31 original changed files** and the supplied `proposed.patch` were reviewed. The supplied patch matched the exact original feature diff, SHA256 `754be1bfd2aaa4166c57e7775fbeda961a8bc46750da1220b89d1cd264f25acb`. The per-file original/current fingerprints are recorded in the local review inventory. New fixes were made on the feature branch before preparing the accepted merge.

The original tip was **NO-GO** for these boundary/provenance issues:

1. **Silent tensor broadcasting:** scalar or missing-energy-axis real/imaginary components could expand into apparently valid tensors. Both components now require their exact `(n_energy,3,3)` shapes. Three regression cases reproduced the original acceptance and now reject it.
2. **Mutable XMCD conversion source/provenance:** the converter validated one read but evaluated the two states through later reads of the mutable original path. It now reads/hashes once and evaluates both states from a private byte-identical snapshot using the unchanged Ni evaluator. A mutation regression flips the original source's dichroism after validation and verifies that both converted tensors still exactly equal the declared snapshot's baseline. Empty original source/validity declarations are rejected before explanatory text is appended.
3. **Axis normalization overflow:** finite components with an infinite norm could normalize to zero and bypass orientation matching. Such axes now fail explicitly in imported MDFF loading/evaluation and declared XMCD conversion; no clipping or guessed direction is used.
4. **Single-channeling loss domain:** an imported loss at/above incident energy could reach the entrance-only calculation. A shared pre-propagation guard now enforces loss below incident energy for Single and Double. Double already rejected impossible outgoing energies; the new common guard makes the eligibility domain explicit and consistent. Tests cover above-boundary and exact-boundary losses.

Additional tests verify convention rejection and replacement of an external MDFF during an actual calculation: results are discarded on the final digest check. Original reproductions failed as expected before correction; those failures are not described as passing acceptance. The last focused source/physics/Ni gate run before candidate preparation passed 67 tests; the final boundary additions are included in the full and post-merge suites below.

No new Atomic Ionization or Multi-element work was started. The original disabled atomic-interface scaffold was inspected but unchanged by this review.

## Physics, project and preservation findings

- **Localized events:** `P_ij=mean_s exp(+2*pi*i*(g_i-g_j).u_s)` for Single; `exp(+2*pi*i*(g-h).u_s)` inside each Double event. Same-event elastic paths interfere coherently; different localized events are averaged in intensity/response, preserving historical **per-selected-equivalent-atom** normalization. Actual imported coordinates and the complete crystal elastic potential are retained.
- **Contraction:** `I=Re sum_ab R_ab T_ba`, `T=L L†`, conjugated forward transition modes, angular `Q=2*pi*g`, Coulomb denominators, actual post-loss outgoing energy and depth quadrature are unchanged. Direct event sums/matrix exponentials, origin/site-order invariance, primitive/conventional descriptions and the outgoing-potential-off Single limit independently test the site plumbing.
- **Magnetic data:** both explicit uniform-FM tensors and the shared-even component are validated; the importer does not manufacture a missing state by conjugation. Tests include a non-conjugate pair with a real odd component. Source-local/crystal/microscope frames require proper rotations. Nonmagnetic, uniform-FM and site-equivalence gates remain explicit; AFM/SDW, partial occupancy and inequivalent sites are rejected.
- **Source interpretation:** units, basis, frame, element, L2,3 declarations and native energy selections are checked. Extrapolation and convention changes are rejected. SHA256 binds the exact tensor file before calculation and after completion; source relinking requires matching bytes. Checksum integrity is not authentication of scientific truth or source authorship. A file cannot self-declare a physically VALIDATED result.
- **Projects:** checksummed saved arrays remain viewable without their external tensor. Missing/replaced sources block reruns rather than migrating providers. Legacy Ni project defaults and Lobato recovery are preserved. Source identity, state/axis, site selection, elastic provider and exact source commit are recorded.
- **Protected source/data:** Ni forward/MDFF providers, original Single kernel, IAM implementations/coefficient data/defaults, version/packaging files, historical input/reference fixtures and figure assets have no diff from starting main. Independently removing only the reviewed optional site interface reconstructs the complete original default Single/Double kernel source exactly, without using the feature's guard helper. Double's explicit site argument is an intended interface addition, not a Born/conjugation change.
- **Historical Ni:** four XMCD/atomic × Single/Double comparisons, each with both BW and MS, pass exact equality for all compared numerical arrays. Protected 160-array archive evidence passes. A genuine historical project still restores Lobato and matches archived elastic amplitudes within `2e-12`; its original manifest is unchanged.

## Exact Windows results

|Run at merge `ff894941be0cf790f5644137d6355bfc767f86c8`|Passed|Skipped|Failed/errors|Duration|
|---|---:|---:|---:|---:|
|Complete Windows source suite (751 tests)|712|39|0 / 0|621.40 s|
|Targeted **post-merge** suite on local main|74|0|0 / 0|35.35 s|

The full run retained 1037 warnings; post-merge retained two expected overflow warnings from rejection tests. No running/interrupted run is counted as passed. The tests use the existing Python 3.11 Windows environment, offscreen Qt, `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, no pytest cache, and a 180-second faulthandler diagnostic. Real external legacy-table, protected 160-array and genuine historical Ni paths were supplied read-only. No missing expensive reference study was regenerated.

Post-merge coverage includes source replacement/convention/shape/domain regressions, independent Single/Double phase references, BW/FFT comparisons, explicit reversal states, GUI/project restoration, original Ni numerical comparisons, the historical Lobato project and immutable-source guards. Full-suite skips are unavailable optional stored/benchmark/WIEN2k/offline-HDF5 evidence, not passes:

- 3: Full benchmark outputs are not complete
- 3: Full checkpointed thickness calculation still incomplete
- 3: Local MS validation outputs not generated
- 2: Local four-point benchmark not generated
- 1: Local legacy reference project unavailable
- 8: Optional GUI and existing real Stage D results required
- 1: Optional historical saved project is unavailable
- 1: Optional local WIEN2k companion audit; original files are not distributed with the package
- 1: Optional real saved Ni project unavailable
- 1: Optional saved GUI reference unavailable
- 6: Optional saved angular references unavailable
- 1: Optional saved benchmark unavailable
- 1: Optional saved result fixture unavailable
- 1: Optional stored GUI reference
- 1: Pinned offline HDF5 inputs unavailable
- 1: Requires original local WIEN2k audit companions; not distributed
- 1: Saved BW/MS fixture not available; never run a fallback simulation
- 3: Saved project fixture unavailable

## Reproduced Fe results and scientific limits

The candidate completed all **24 bounded synthetic Fe sensitivity cases** and produced the spectra/maps/projects/CSV/NPZ/PNG/SVG evidence under the local review directory. All **59** generated files matched their manifest. Across **eight NPZ files, 348 arrays** are exactly equal to the earlier scientific-source evidence. The import/domain corrections do not alter these valid-input numerical results.

The Fe source is explicitly **SYNTHETIC TEST ONLY**; illustrative L3/L2 labels are not a physical energy calibration. GUI/result labels and documentation do not call it physically validated Fe EMCD. Physically sourced imports remain **RESEARCH / APPROXIMATE** until independently validated.

Baseline detector A+ BW/MS relative differences remain **0.236394% Single / 0.474516% Double**. Detector refinement changes A+ by approximately **1.6%**, magnetic differences by roughly **1.9%** and nonmagnetic differences by up to about **2.8%** in the tested profile. This is not a converged quantitative profile. Small FFT/slice changes do not certify detector, beam, potential or specimen-thickness convergence; a fixed BW basis can hide sensitivity to added potential harmonics. Thickness rows change the physical specimen, not merely numerical error.

Remaining approximations: electric-dipole tensors; projected neutral IAM/finite ZOLZ; finite beam/potential/detector/depth sampling; branch-frozen longitudinal transfer; continuous uniform event-depth density rather than discrete atomic layers/surface termination; per-atom relative intensity; no calibrated cross section, experimental handedness or complete supplied DFT MDFF. Rotation-related/HCP and inequivalent/multi-element site MDFF, AFM/ferrimagnetic/SDW and validated Co/Cr or generalized atomic spectra remain outside the accepted scope. No packaged-EXE or cross-platform acceptance is claimed here.

**Outstanding local merge blockers: none after the fixes and completed acceptance.** Trustworthy Fe-specific tensors, independent physical references and further numerical convergence remain blockers to quantitative Fe/general-material claims, not grounds for relabeling the synthetic results.

## Local evidence

Evidence is retained under ignored `outputs/merge-readiness-20261104/` in the isolated main integration worktree. No generated scientific outputs were added as new reference fixtures. The earlier [implementation validation](GENERALIZED_SINGLE_ELEMENT_EMCD_VALIDATION.md) remains a historical record; this review supersedes its source-acceptance decision for the corrected merge.

|Evidence path relative to the review directory|SHA256|
|---|---|
|`review-inventory-final.json`|`4b872cd239207eb4d5d5e44444ba10d243ca3d9e513f8c5b382a617a6f976ed1`|
|`final-full-windows.xml`|`fd151de23ed6895b4cadd6ad1fc5f11a9d194837705390eeea67f72425a87bb9`|
|`post-merge.xml`|`c4954bb6f134b52018fd9e7ba91c486a772b08d3115c7eb99768ba0786e6c093`|
|`fe-reproduction.json`|`6252ac9c1993720262f7ab6bd300de6780be61146acd925c48dcd7a658b8af1a`|
|`final-fe-synthetic/validation.json`|`f5756c6993e8bad17d3595950bc4d7d0689d9b2d0c16082bac5919e6f4c2578d`|
|`final-fe-synthetic/SHA256_manifest.json`|`9d9fa2204d89fc49551517581920a3e449d6bd45ae720c1270f63e4196a75a91`|

Original 31-file review inventory:

- `docs/GENERALIZED_SINGLE_ELEMENT_EMCD_DESIGN.md`
- `docs/GENERALIZED_SINGLE_ELEMENT_EMCD_VALIDATION.md`
- `docs/ROADMAP.md`
- `scripts/research/validate_single_element_emcd.py`
- `src/emcd_sim/atomic_ionization.py`
- `src/emcd_sim/double_channeling.py`
- `src/emcd_sim/generalized_xmcd.py`
- `src/emcd_sim/gui/channeling.py`
- `src/emcd_sim/gui/generalized_forward.py`
- `src/emcd_sim/gui/imported_tensor_ui.py`
- `src/emcd_sim/gui/numerical_settings.py`
- `src/emcd_sim/gui/project_io.py`
- `src/emcd_sim/gui/propagation.py`
- `src/emcd_sim/gui/results.py`
- `src/emcd_sim/gui/results_browser.py`
- `src/emcd_sim/gui/stage_b.py`
- `src/emcd_sim/imported_mdff.py`
- `src/emcd_sim/ionization_sites.py`
- `src/emcd_sim/multislice_double_channeling.py`
- `tests/fixtures/single_element_scope_v1.json`
- `tests/physics_source_guard.py`
- `tests/single_element_helpers.py`
- `tests/single_element_source_guard.py`
- `tests/test_generalized_xmcd_atomic.py`
- `tests/test_single_element_contracts.py`
- `tests/test_single_element_forward.py`
- `tests/test_single_element_gui.py`
- `tests/test_single_element_invariance.py`
- `tests/test_single_element_ni_compatibility.py`
- `tests/test_unit_labels.py`
- `tests/unit_source_snapshots.py`

Local main was clean at the accepted merge and post-merge checks; the only subsequent change is this committed report. The feature and historical worktrees are preserved. No GitHub push, EXE build, public-version change, tag or release was performed. Linux/macOS CI debugging was not undertaken.
