# Physics audit validation results

Date: 2026-11-01; source `a77f7455f5fe57dad6bae5d948477b2390433bb0`.
Production behavior is unchanged. **Physics acceptance is blocked** by the
two convention failures in [the audit](PHYSICS_MATRIX_IMPLEMENTATION_AUDIT.md).
The [source map](PHYSICS_CONVENTIONS_AND_SOURCE_MAP.md) distinguishes inspected
implementations from established theory and unverified literature details.

## Reproducible commands

Run from `C:/Users/peng863/EMCD-Sim/build/source-cleanup-integration`, with the
existing `emcd-python` environment (Python 3.11.17, NumPy 2.4.6, pytest).
PowerShell environment used:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH=(Join-Path (Get-Location) 'src')
$env:QT_QPA_PLATFORM='offscreen'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
python -B -m pytest tests/test_physics_matrix_audit.py -q -rx -p no:cacheprovider
python -B -m pytest tests/test_physics_matrix_audit.py -q --runxfail -k 'microscopic_born or nontrivial_site' -p no:cacheprovider
python -B scripts/physics_matrix_audit.py
python -B -m pytest tests -q -p no:cacheprovider --basetemp=build/physics-matrix-audit/pytest-baseline
```

The unmasked reproduction command is **supposed to fail** until an approved
physics correction is made. Strict expected failures are included only in
the new audit file; no existing tolerance or test was loosened. The final
regression status is recorded below after completion.

## Independent evidence and classification

New controls are in `tests/test_physics_matrix_audit.py`. They use closed Pauli
exponentials, explicit DFT matrices, nested transition sums and high-order
Gauss–Legendre quadrature, not two wrappers sharing one suspected kernel.

| Scope | Type | Result / tolerance |
|---|---|---|
| 2x2 complex Hermitian incoming/exit propagation, 0, 1e-7, .3, 17 nm | Solver implementation | Pass; response `rtol=2e-12`, `atol=2e-15` against independent depth quadrature |
| Direct `V=sum K*d` target-mode sum versus response tensor | Algebra, not Born validation | Pass `rtol=2e-13`; phase invariance passes; wrong trace deliberately distinguished |
| Forward Born excitation with declared `d=<i|r|f>` | Physics/convention | **FAIL / strict XFAIL**: production 0, microscopic reference 4; `atol=1e-14` |
| Nontrivial synthetic site, free outgoing reduction | Physics/convention | **FAIL / strict XFAIL**: pair-phase max difference 1.97730349; `atol=1e-14` |
| Nonmagnetic intensity consequence of the site mismatch | Diagnostic algebra | Single .8184010927362846 vs free-exit Double 1.8465989072637155; difference 1.0281978145274309 a.u. |
| Explicit weighted Gaussian dipole Gram sum | Algebra/units | Pass; Hermitian PSD and proper MDFF transfer-pair Hermiticity/nonnegative diagonal; `atol=1e-15` |
| `2*pi` and Coulomb factors | Units/algebra | Pass: proper MDFF scales as Q², kernel scales as 1/Q; denominators remain outside S |
| Independent 2x3 incoming/outgoing bases and boundary indices | Solver implementation | Pass against explicit propagation; `atol=3e-14` |
| Nearly degenerate modes, complex eigenvectors | Solver implementation | Pass; `atol=2e-15`; non-Hermitian complex-eigenvalue H explicitly rejected |
| Reversal, N/M, raw differences, common-denominator percentages | Algebra | Pass; fractional aperture integration precedes percentage formation |
| FFT elastic propagation versus independently built Hamiltonian | Solver / small-model convergence | Pass; halving slice step reduces error by >3.9; adjoint reconstruction `atol=2e-14` |
| FFT event-to-exit Double intensity | Solver / small-model convergence | Pass; separate depth and slice refinements; relative raw error <1e-4 at tested finest depth |
| Numerical depth quadrature against independent Gauss control | Convergence of tested model | Pass; node doubling reduces error by >3.9 |

Focused result: **13 passed, 2 strict expected failures**. Running those two
with `--runxfail` gives **2 failed, 13 deselected**. They are unresolved
failures, not physics acceptance passes.

For the 17 nm complex-H example, the analytic and independent response differ
by at most `1.2212454657744986e-15`; contracted intensities are
`1.0793878511140174` and `1.079387851114018`. Trapezoidal depth errors
(Frobenius norm) are:

| Nodes | Error |
|---|---:|
| 33 | 0.00034810873756975215 |
| 65 | 0.00008700209363364026 |
| 129 | 0.000021748956741739543 |

Evidence: `build/physics-matrix-audit/evidence.json`,
`small_model_evidence.npz`, `focused.log`, `focused.xml`, and
`independent_failures.log`. No result is a full Ni convergence certificate.
Existing physical mirror-parity controls are restricted to geometries and
magnetization for which the symmetry actually holds. No artificial mirrored
or antisymmetrized display was used as physical evidence.

## Preservation and changes

`baseline.json` was written before adding tests/docs. Rechecking its hashes
confirmed 123 existing source/test/config/user-guide files, all 323 protected
files (including 204 production checkpoints), and all 19 original user files
unchanged. Baseline reference-manifest mismatches were empty. The user's
`docs/USER_GUIDE.md` edit remains untouched. The four saved [017] rows used for
hypothetical sign predictions were read only, and their CSV hash is recorded.

Changed/added audit files only:

- `tests/test_physics_matrix_audit.py`: independent controls and explicit failures.
- `scripts/physics_matrix_audit.py`: small-model evidence and read-only fingerprint check.
- `docs/PHYSICS_MATRIX_IMPLEMENTATION_AUDIT.md`.
- `docs/PHYSICS_CONVENTIONS_AND_SOURCE_MAP.md`.
- `docs/PHYSICS_VALIDATION_RESULTS.md`.

Generated evidence is kept in the ignored `build/physics-matrix-audit/` folder.
No production Python, reference array, numerical default, GUI or package
version changed. No old-vs-new production numerical differences are claimed:
there is no production patch. The hypothetical Ni table explicitly describes
the observable changes a future approved tensor-conjugation correction would
produce, separately from unchanged current results.

## Existing practical regression suite

The complete **pre-existing** suite (collected before the new audit test file
was added) ran in 358.41 seconds: **558 passed, 15 failed, 2 skipped**.
This is not an all-green regression claim. `regression.log`, `regression.xml`
and `regression_summary.json` preserve the failures. The skips require optional
local WIEN2k companion audits not distributed in this worktree.

| Existing failure scope | Count | Inspected cause / disposition |
|---|---:|---|
| `test_double_channeling_full_outputs::test_orientation_source_reproduction_and_preservation` | 1 | Historical provenance expects original-checkout source hash `a0e28e...`; this worktree's existing source is `4fd517...`. Both hashes predate this audit. Parsed 4329×5 arrays are exactly equal, max absolute difference 0; byte provenance still fails and was not rewritten. |
| `test_multislice_slice_step_range::test_manual_gui_preserves_requested_maximum` | 9 | Full-suite RSS accumulation triggered the unchanged 2048 MiB resource gate (e.g. 2057.2 MiB estimated peak). UI test expects enabled Run regardless of current RSS. Separate fresh-process diagnostic recorded below; no admission rule bypassed. |
| `test_solver_settings_ui::test_released_configuration_exactly_preserved` | 2 | Old released control expects .04 nm default, current already-approved default is 2 nm. No default reverted. |
| `test_solver_settings_ui::test_solver_visibility_and_classification` | 3 | Old test expects slice-step widget inside the legacy MS settings group; current editable control has different ownership. No GUI/layout modification made. |

The independent new controls ran separately after the suite. No production
code or existing test was changed between baseline and audit runs. The
fresh-process GUI resource diagnostic completed: **12 passed, 20 deselected
in 159.23 seconds**. Command:

```powershell
python -B -m pytest tests/test_multislice_slice_step_range.py -k manual_gui -q -p no:cacheprovider --basetemp=build/physics-matrix-audit/pytest-isolated
```

`gui-isolated.log` and `gui-isolated.xml` preserve that result. No selected
budget, available-memory fraction or safety check was changed. It supports
the accumulated-process-memory diagnosis; it does not erase the original
full-suite failures or certify general Windows memory stability. The other
six existing failures remain unresolved in this scope. No full-suite rerun
was needed because production and existing test files remain byte-identical.

Final focused run after adding the explicit production reversal-decomposition
and mirrored-aperture controls: **13 passed, 2 xfailed in 1.12 seconds**.
Final read-only integrity recheck again reported zero mismatches for the
123 baseline files, 323 protected files, and 19 user files. Acceptance remains
NO-GO for the microscopic convention gate; the two strict XFAILs need an
approved physics correction and independent review, not a threshold change.

## Follow-up: complete regression diagnosis and finalized proposal

The [per-failure review](PHYSICS_REGRESSION_FAILURE_REVIEW.md) records every
test name and the exact original JUnit assertion message. None of the 15
fails at either disputed physics operation. The six non-resource cases were
rerun separately without source changes: **6 failed in 72.35 s**, confirming
the provenance mismatch, two stale-default assertions and three stale-layout
assertions. The nine resource failures remain documented despite the earlier
fresh-process 12-case pass. No full-suite failure or tolerance was suppressed.

Five new tests in `tests/test_physics_correction_proposal.py` evaluate the
proposed formulas without patching production. Independent direct-Born,
prospective Single and free-outgoing Double intensities are respectively
`0.9324430655720030`, `0.9324430655720032`, `0.9324430655720031` a.u.
The test-local phase-only and contraction-only alternatives disagree with
the reference, establishing that both changes are needed for this synthetic
case. Mode conjugation, complex-kernel forward exit propagation and site
origin covariance also pass. The result does not imply that current production
has been corrected.

```powershell
python -B -m pytest tests/test_physics_correction_proposal.py tests/test_physics_matrix_audit.py -q -rx -p no:cacheprovider
```

Combined result: **18 passed, 2 strict XFAILs in 3.46 s**. The two unresolved
production failures are the original reproductions. Source/kernel hashes
remain the acceptance baseline. No broad-suite repeat or research scan was
needed for this documentation/test-only follow-up.

The [minimal proposal](PHYSICS_MINIMAL_CORRECTION_PROPOSAL.md) contains exact
unapplied diffs, all affected contractions, native Ni [017] L3/L2 predictions,
and full regression acceptance gates. The proposed three-file patch passes
read-only `git apply --check`; it has not been applied. Follow-up raw
evidence and fingerprints are under `build/physics-matrix-audit/review/`.
