# Documentation review: public Windows v0.7.0-beta.1

Review date: **2026-11-03**. This is a documentation-only overhaul, not a version, release, scientific-model or binary update. Source/release baseline was local and remote main `08d04fc35fca2071cc7e73af0aaa1de45e49a3f4`.

## Identities and preservation

- Public prerelease: [v0.7.0-beta.1](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.7.0-beta.1), verified public, not draft, with the portable Windows ZIP and SHA256SUMS.txt.
- Fixed annotated tag target: `481fed14b78f5439bb417bdc53d38d845a6b2592`.
- Released binary source: `97b2220e5329dad6f98eedec61f58a6cf07d9da8`; validated Actions run **41516996056**.
- ZIP SHA256: `8d157d8b62fb6570d201360cdae85f44aa4cea2c1478f1949eb4336a135e17bc`.
- Convention: **forward_born_dagger_g_minus_h_v1**. Later documentation does not change this EXE's provenance.
- Production source between the binary source and the review baseline is unchanged. Original worktrees, two untracked acceptance reports, scientific outputs and checkpoints remain preserved. No physics/GUI/default/test/workflow changes, calculations, build, version bump or tag/release mutation are part of this task.

## What was reorganized

README → Installation → small Quick Start → nine-part Tutorial → 23-section User Manual → current Physics/GUI technical references. The new index distinguishes released functions, current source, bounded validation, historical records and planned architecture. Historical acceptance reports, release notes, source audit and earlier scientific records are unchanged. Physical-unit definitions are retained; its final paragraph now names the 200/300 kV datasets explicitly instead of ambiguously calling one "the new study". Replaced append-only manual/physics/GUI text remains accessible at immutable revision `08d04fc3`.

## Implementation checks and resolved documentation discrepancies

|Topic|Verified source / documentation action|
|---|---|
|Geometry preset|`gui/app.py: reset_reference` restores [017]/(200), zero Y, full basis and apertures; it is not generic Bragg alignment. Corrected tutorial instructions.|
|Tilt step|`app.py: step_changed` changes spin-box increments only, not a scan or physical tilt by itself.|
|Circle definitions / dragging|`app.py` uses ZA = −k_perp, Laue center/radius and distinct styles; native before/after exports show current versus stale intensities. No new calculation performed.|
|Numerical profile|`stage_b.py`, `numerical_settings.py`, `propagation.py`: 300 kV starting voltage, 3.2/2.5 Å⁻¹ cutoffs, 97 grid, 2048 MiB budget, editable 2 nm max step. Effective values can differ; no universal convergence claim.|
|Controls / modes|Main display is Raw / conventional Asymmetry; additional relative diagnostics are advanced. No invented fixed-detector Flip-M/four-curve GUI mode or automatic survey button.|
|Denominators|`component_display.py`, `prb_benchmark.py`: conventional uses raw +M sum; GUI advanced components use even N_A+N_B. Tutorial common-conventional-denominator components are separately derived from raw exports.|
|Masking|`signal_normalization.py`: released P95-based support/floors distinguished from case-study maximum-based 1e−12 policy.|
|Energy sampling|`emcd_forward.py: energy_grid`: requested full-range samples plus selected energies, not automatically every source sample or spectra synthesized from two edge points.|
|Project/export behavior|`project_io.py`, `results_browser.py`, `emcd_forward.py`, `normalization_export.py`: completed results, method-prefixed raw arrays, separate input restoration, checksum-dependent reruns, CSV/NPZ and figure sidecars.|
|Physics|Current trace, L* and site phase mapped to unchanged kernels; old pre-correction source audit remains explicitly historical.|

## Existing visual/data evidence

Eight existing native/study images are copied or image-only downsampled, with original and preview hashes in [provenance](images/v070b1/provenance.json). No scientific arrays are resampled and no curves are regenerated. The GUI/map captures are explicitly coarse acceptance cases. The 9/30 nm spectra and selected table were checked against actual CSV/NPZ and configuration. Only compact previews and a four-row selected-value CSV are included, not full spectra/checkpoints. Original sources remain untouched.

The native SVG documentation copy has trailing whitespace removed, with normalized XML geometry/style tokens verified unchanged. CSV/SVG provenance explicitly distinguishes original/local text bytes from Git's LF text blobs so Windows checkout normalization does not masquerade as a changed scientific value. No production hash guard is relaxed or modified.

## Validation scope

Validation checks current-document local links/anchors/table structure and Python example syntax, incoming historical links to rewritten guides, public download URLs, version/source/hash consistency, PowerShell syntax without execution, existing-array normalization/decomposition, image/source hashes and unchanged non-document files. Focused existing source-identity/unit/version guards are used where appropriate; there is no broad regression or simulation rerun. Detailed receipts remain local under `outputs/documentation_overhaul_20261103/`.

Completed focused results:

- **176** current-document local path/anchor checks passed, including compatibility of incoming historical links; **24** tables have consistent columns.
- **Three** PowerShell blocks parsed without running their commands. The host blocks direct `.ps1` execution, so syntax was checked through the already-running PowerShell parser; no execution policy was changed.
- The tutorial's Python snippet passed syntax checks and ran successfully against an existing saved packaged scientific reference. This was read-only array post-processing, not propagation.
- The documented 27-beam, 17×17, 33-node Single/BW Quick Start profile passed configuration-only offscreen Qt preflight with preview/calculation-worker starts mocked and verified absent. This is not new native EXE acceptance or a convergence claim.
- **Eight existing focused tests passed, zero skips/failures**: physics source guards, current-guide unit checks, historical Windows identity and version metadata.
- Integrity checks verified **255 non-document tracked files**, **156 unaffected historical documents**, all **23 worktree identities** (with the active worktree's intended docs edits), original user-file hashes and **323 protected files including 204 production checkpoints**. The original spectral arrays/figures and accepted ZIP hash remain unchanged.
- A temporary local example harness initially asserted a Boolean return from the GUI's side-effect-only source-validation callback. It was corrected to inspect validated state; the original and passing logs remain local. No production callback or test assertion was changed.

## Remaining limitations

No new software defect or scientific convergence problem is fixed by documentation. Five native orientations and other bounded acceptance checks do not certify arbitrary settings. Independent clean-machine installation remains untested; Linux CI issues and uncertified macOS status remain. Full complex DFT MDFF, atomic-3D/HOLZ/TDS/absorption completeness, experimental handedness/energy/count calibration and global numerical convergence remain outside the validated model. A prescribed crystal magnetic vector does not determine physical surface/equilibrium magnetization.

Public prerelease assets/tag remain fixed. Any normal push of this documentation commit may start the unfiltered Python test workflow; the Windows build workflow excludes documentation-only paths and is not changed to suppress CI.
