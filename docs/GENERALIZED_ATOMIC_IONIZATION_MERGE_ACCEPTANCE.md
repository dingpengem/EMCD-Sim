# Independent final merge acceptance - generalized atomic ionization

Date: **2026-11-04**. **GO for local research-source integration after the correction
below.** The supplied original feature tip was NO-GO for an import-provenance bypass;
the issue was reproduced and corrected on the feature branch before acceptance.
The corrected feature is now merged into **local main only**. This is not quantitative
Fe EMCD, broad convergence, packaged-Windows acceptance or release approval.

## Exact identities and worktrees

|Identity|Commit|
|---|---|
|Verified original local/remote main baseline|`237944148151d784b6b2e3597e853dbc32779bd0`|
|Supplied feature tip independently reviewed (all 13 files)|`b0b719b1bf5f1c64b09426520db82664e749393b`|
|Original feature's full-suite scientific source, evidence verified|`d754756423e0e907b6d3e194e0d77f99ea44ab1a`|
|Corrected, actually merged feature tip|`10ec5192dfab70d621abedbc557c4d828636a78f`|
|Exact tested no-ff merge commit|**`7b0244d0108a6f0af57ee10554dcd5ed302c1d0f`**|
|Exact merge tree|`df68ff61ebacf02127e290aa0d08dc68ffec2211`|

The merge has exactly two parents: the verified main baseline and the corrected
feature tip. Its tree exactly matches the corrected feature, with no conflicts or
extra scientific changes. It was created by `git merge --no-ff` on the isolated
`integration/atomic-ionization-main-reviewed` branch. Main remained unchanged while
that exact clean merge passed the complete Windows suite. Main then advanced by
`--ff-only` to the same tested merge; its history retains that normal two-parent merge.
No reset, rebase, squash, forced branch update or replacement merge was used.

Local main now occupies `build/atomic-ionization-main-integration`. Its previous
worktree `build/single-element-main-integration` is preserved at the baseline on
`preserve/main-before-atomic-ionization-20261104`. The original feature worktree and
branch remain intact, with the supplied tip retained in their ancestry. Remote main
was fetched and checked before review, before preparing the merge and again before
advancing local main; it remained at the expected baseline. **Nothing was pushed.**

This report and the README source-status clarification are a subsequent documentation
commit. The final main HEAD is that documentation commit; its scientific source/tests
are exactly those of the tested merge recorded above.

## Complete review and original evidence

All 13 changed files, their complete contents and the supplied proposed patch were
reviewed. The patch exactly matched `git diff <baseline> <supplied-tip> --binary`:
SHA256 **`913745b773485b722b662355e2fccb42fd968a3f7393cc3efdf3eaaffe67ac5c`**.
An original-file SHA256 inventory and reproduction logs remain in the feature
worktree's ignored `outputs/merge-review/` directory. The supplied patch was preserved.

The original 747-pass/39-skip JUnit evidence and 70-pass focused evidence were read,
not inferred from this report. The full-run source marker is `d754756...`; comparison
with supplied `b0b719b...` shows only its subsequent validation-document addition.
Thus the original results do correspond to the accepted feature's scientific source.
The synthetic Fe metrics in the focused log were reproduced without altering the
fixture, material inputs, physical conventions or historical references.

## Corrected blocker: partial atomic provenance

At the supplied tip, generated-source regeneration ran only if `atomic_model` was
present. Deleting that tag and scaling both tensors/shared-even by two preserved
Hermiticity/PSD while bypassing regeneration; the import still retained atomic
parameter provenance. This was an import-boundary defect, not a scientific fit issue.

The feature-branch correction reserves the complete `atomic_` namespace. Any atomic
declaration now requires the six supported provenance fields, and unknown atomic
fields are rejected. Only then is the existing embedded-document/hash and tensor
regeneration validation called. Seven new regressions cover each deleted field and
an unknown atomic field. Original-source reproduction gave three failures/four passes:
missing-model and unknown-field cases were accepted; the missing-path case rejected
altered tensors but did not give the required incomplete-provenance diagnostic.
All seven corrected cases pass. No transition algorithm, parameter or contraction
kernel changed. The source-scope manifest was reviewed and updated only for the
import-boundary change; earlier immutable manifests were preserved.

A completely declaration-free file may still be explicitly imported as an ordinary
MDFF. It carries no verified atomic-model provenance and has different bytes/SHA;
it cannot replace an existing project's source under its saved checksum. This is
not cryptographic authorship or scientific-truth authentication. An unchanged original
generated source loads with its original SHA
`ee49ec9c228caf4eca27ab84e835872c4be42a8fd6bc7eb1763504a61eba9e98`.
Two exports of identical inputs/source path produced byte-identical output in the
independent reproducibility check.

## Scientific and compatibility findings

- Universal 2p core SOC states and CG/dipole functions are shared aliases of the
  unchanged historical Ni implementation. Direct spherical-harmonic integration of
  60 dipoles and an independent L.S eigensystem check support the angular algebra.
  The complex convention is `d=<core|r|final>`, with the required conjugation.
- Cubic-orbital amplitudes sum coherently within an event. Different core/final
  events sum incoherently as `T(E)=sum w*d*d_dagger*Gaussian(E-E_t,sigma)`.
  Nonnegative hole weights and positive Gaussian sigma yield Hermitian PSD tensors;
  no clipping, absolute-value repair or fitted rescaling is introduced.
- Radial dipoles are in Angstrom, tensor spectra in Angstrom^2/eV, broadening is
  Gaussian sigma in eV. The full-hole strength is `4*r^2`; an independent branch
  check gives `(8/3)*r^2` for L3 and `(4/3)*r^2` for L2. Integrated trace and radial
  scaling tests pass. The analytic full-hole test is not a changed material fixture.
- Material fields are mandatory and validated; no Ni electronic defaults are copied
  to Fe, Co or Cr. Opposite states explicitly swap holes and exchange shifts.
  Local +z, proper rigid orbital/spin-frame rotations, cubic basis and relative
  intensity conventions are enforced; unsupported axes/frames/parameters fail.
- Generated sources use the accepted imported-MDFF orchestration, localization/site
  phases, BW/FFT Multislice and Single/Double Channeling. Born `I=ReTr(RT)`, angular
  `Q=2*pi*g`, event normalization and outgoing-energy conventions are unchanged.
- Failed generation invalidates prior GUI validation/acknowledgement. Save/open,
  missing-source read-only use, replaced-source rejection, parameter provenance,
  source convention and native energy-range checks pass. Legacy Ni routes retain
  their conservative eligibility rules and do not migrate into the new provider.
- Ni event/tensor arrays remain exact for default/nondefault atomic configurations
  and both signs. Historical Ni XMCD/atomic x Single/Double, each BW/MS, numerical
  arrays remain identical. The protected 160-array archive passes. The genuine
  archived project retains Lobato and its elastic controls within the existing
  2e-12 criterion, with its manifest unchanged.

Git-blob comparisons against the baseline confirm unchanged Ni MDFF/forward providers,
shared tensor algebra, propagation kernels, project I/O, generalized orchestration,
elastic providers/defaults/coefficient data, version/packaging files, historical data,
figure assets and original physics/unit/source fixtures. The synthetic parameter
fixture is unchanged. No unlicensed legacy table, scientific outputs or binaries
were added. Existing licensing/Apache notices remain unchanged.

## Exact Windows acceptance

|Run|Passed|Skipped|Failures/errors|Duration|
|---|---:|---:|---:|---:|
|Corrected feature targeted independent suite|116|0|0 / 0|71.32 s|
|Complete exact-merge Windows suite (793 tests)|754|39|0 / 0|1410.01 s|
|Post-merge focused suite on actual local main|77|0|0 / 0|27.67 s|

All completed runs exited 0. Full-suite warnings: **909**, primarily existing Qt
and offscreen-layout diagnostics, plus deliberate invalid-input checks. Post-merge
warnings: one deliberate overflow-norm rejection diagnostic. The longer full-run
wall time is recorded, not treated as a physical or performance benchmark.
No running, skipped, interrupted or original negative-reproduction case is labeled
as a passing acceptance check.

Environment: native Windows build 26200, Python 3.11.17 via the existing Windows
venv; `PYTHONPATH=src`, offscreen Qt, OpenBLAS/OMP thread limits 1, no pytest cache,
and a 180-second faulthandler diagnostic for the full run. External legacy-table,
protected-array and genuine-project paths were provided read-only. This is source
acceptance; no EXE was built or tested. No expensive historical EMCD study was rerun,
and no missing reference was replaced by a fallback simulation.

Exact full/post-main SHA markers, logs, JUnit XML, reproducibility outputs and the
unrelated-root-file preservation inventory remain under this integration worktree's
ignored `outputs/atomic-merge-review/` directory.

### Synthetic Fe numerical consistency

The unchanged synthetic fixture uses explicitly declared illustrative inputs, not
physical Fe spectroscopy or Ni parameters relabeled as Fe. The finite thin-case
`I_A_plus` two-energy BW/MS relative L2 differences remain:

|Channeling|Relative difference|
|---|---:|
|Single|0.0006396961091371369 = 0.06397%|
|Double|0.0012815790733429451 = 0.12816%|

These are consistency results at the documented finite basis/depth/detector/FFT
settings, not material accuracy or general convergence. The previously documented
approximately **1.6% detector-refinement sensitivity** remains a limitation.

### Skips, not passes

|Count|Reason|
|---:|---|
|3|Full benchmark outputs are not complete|
|3|Full checkpointed thickness calculation still incomplete|
|3|Local MS validation outputs not generated|
|2|Local four-point benchmark not generated|
|1|Local legacy reference project unavailable|
|8|Optional GUI and existing real Stage D results required|
|1|Optional historical saved project is unavailable|
|1|Optional local WIEN2k companion audit; original files are not distributed with the package|
|1|Optional real saved Ni project unavailable|
|1|Optional saved GUI reference unavailable|
|6|Optional saved angular references unavailable|
|1|Optional saved benchmark unavailable|
|1|Optional saved result fixture unavailable|
|1|Optional stored GUI reference|
|1|Pinned offline HDF5 inputs unavailable|
|1|Requires original local WIEN2k audit companions; not distributed|
|1|Saved BW/MS fixture not available; never run a fallback simulation|
|3|Saved project fixture unavailable|

All 39 skips concern optional stored/benchmark/WIEN2k/offline-HDF5 evidence. Required
atomic/provenance/GUI checks and supplied historical Ni/array controls actually ran.

## Remaining scientific limitations and final disposition

**No essential software/scientific-convention merge blocker remains in the declared
approximate scope.** This is an independent-electron 2p-to-3d model with a declared
cubic field, explicit spin holes/radial inputs, aligned local magnetic axis, rigid
frame rotations and relative EELS/EMCD intensities. Material-specific inputs remain
physically unvalidated unless separately established by independent sources.

There is no quantitative Fe EMCD, general crystal-field solver, full DFT-derived
MDFF, many-body multiplet/core-hole/charge-transfer accuracy, absolute cross-section
or experimental-handedness calibration, validated AFM/SDW physics, arbitrary spin
rotation relative to a fixed anisotropic field, or multi-element site-resolved MDFF.
The distinction between a valid mathematical synthetic model and physical material
validation remains explicit in GUI/results, source metadata and documentation.

The merge is local only. No push, public version change, EXE build, tag, release,
Multi-element EMCD development or Linux/macOS CI investigation occurred. Historical
worktrees/outputs and unrelated files remain preserved. A future public release
needs its own packaging/native-application acceptance and physical claims review.

## Reviewed files

- `README.md`
- `docs/GENERALIZED_ATOMIC_IONIZATION.md`
- `docs/GENERALIZED_ATOMIC_IONIZATION_MERGE_ACCEPTANCE.md`
- `docs/GENERALIZED_ATOMIC_IONIZATION_VALIDATION.md`
- `docs/GENERALIZED_SINGLE_ELEMENT_EMCD_DESIGN.md`
- `docs/examples/synthetic_fe_atomic_parameters.json`
- `src/emcd_sim/atomic_ionization.py`
- `src/emcd_sim/gui/imported_tensor_ui.py`
- `src/emcd_sim/gui/results.py`
- `src/emcd_sim/imported_mdff.py`
- `tests/fixtures/atomic_ionization_scope_v1.json`
- `tests/single_element_source_guard.py`
- `tests/test_atomic_ionization.py`
- `tests/test_generalized_xmcd_atomic.py`
