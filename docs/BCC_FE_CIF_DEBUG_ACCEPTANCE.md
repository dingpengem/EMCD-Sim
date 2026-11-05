# BCC Fe GUI bugfix ? final acceptance review

## Candidate and execution boundary

- Worktree: `C:\Users\peng863\EMCD-Sim\build\v081-bcc-fe-cif-debug`.
- Branch: `fix/v081-bcc-fe-cif-preview`; base HEAD `b449edff0959058dc70b270e5fdf0f99fd485590`.
- Scientific baseline / accepted EXE source: `cdd5dc3efa43e4f3874e011aa1cfc98f80cf46dd`.
- Uncommitted candidate. No merge, push, tag, release, Windows build or v0.9.0 development.
- Only production file changed: `src/emcd_sim/gui/app.py`, methods `MainWindow.refresh` and `MainWindow.start_preview`.
- Original main, user files, historical worktrees, scientific references and published EXE/ZIP are preserved.

## Exact CIF and independently verified structure

Input: `C:\Users\peng863\Downloads\alpha_Fe_bcc_Im-3m.cif`.
SHA256: `e841d08df6ba5a2860385397a85da36856568d19e72250e1bebaa37885f595df`.
The original was read without modification. The new portable test fixture is a byte-for-byte copy, not an ASE-generated replacement.

ASE imports conventional BCC Fe with a=b=c=2.8665 angstrom, 90-degree angles, two Fe atoms at (0,0,0) and (1/2,1/2,1/2), space group 229, and no import warnings. All 96 supplied symmetry operations match the complete Im-3m set. The formula `Fe2` with formula-units Z=2 is inconsistent chemical bookkeeping for a two-atom cell; it does not change the imported positions or cause the GUI failures. The file was not corrected or normalized.

## Confirmed independent causes

### Beam-limit failure

On unchanged v0.8.1 source, launch default Ni, import the original CIF, and change **only** the zone to [001]. Target remains (200); beam/potential cutoffs remain 3.2/2.5 inverse angstrom, voltage 300 kV, thickness 30 nm and inherited tilt unchanged.

`geometry()` at `gui/geometry.py:120` raises:

```text
ValueError: 137 beams exceed the interactive limit 121. Lower the radial cutoff; no beams were silently dropped.
```

The full original configuration and traceback are in `outputs/bcc-fe-cif-debug/exact-zone-only-reproduction.json`.
This is the source of the reported zone-only `Invalid configuration ? no current plot` error. A separately observed [017]/(110) zone-law rejection is not substituted as the cause of this workflow.

Independent enumeration uses l=0, h+k even, and sqrt(h*h+k*k)/2.8665 <= cutoff. Counts include (000), matching the production limit:

| Cutoff (inverse angstrom) | Allowed beams | Result |
|---|---:|---|
| 1.05 | 13 | Within limit |
| 2.5 | 81 | Within limit |
| 3.0 | 113 | Within limit |
| 3.2 | 137 | Exceeds unchanged limit 121 |

### MDFF Automatic guard incorrectly coupled to elastic Preview

The original `start_preview()` rejected `_numerical_error` from MDFF-dependent Automatic preset preparation before checking elastic settings:

```text
Declared MDFF providers require explicit Manual numerical settings; Ni presets are not transferred
```

With Adaptive selected and valid [017] geometry, this blocked a valid Fe elastic preview even though factors and beam selection were supported.

The candidate retains the unchanged Automatic policy call (preserving existing Ni behavior), but validates elastic provider, actual displayed Settings, geometry, target and finite basis independently. It no longer treats an MDFF policy failure as an elastic eligibility failure. The existing `_numerical_error` guard in Stage B still blocks Run EMCD / EELS, together with unchanged material, source, frame, site and numerical checks.

No Fe automatic parameters are selected, invented or convergence-certified. The GUI explicitly says that displayed inherited values are used unchanged and are not independently convergence-validated for this material. Users must select Manual to edit disabled Automatic cutoff controls. A 137-beam geometry still fails; it is never silently coarsened.

### Geometric (100) point with unsupported Ni Lobato provider

Both an open (100) point and unavailable Preview were reproduced under [017] when **Ni Lobato** was selected for Fe. The exact provider reason is:

```text
Reciprocal geometry only: Ni Lobato provider supports only Ni; select Dirac-Pade for other neutral atoms
```

Without supported factors, existing geometry-only behavior displays unfiltered reciprocal-lattice points. These are not intensity-calculated reflections. The candidate labels the title, legend and information panel accordingly; it does not alter extinction filtering.

With **Adaptive Dirac?Pade** selected, (100) is absent and (200) allowed in [017] and [001]. Real calculated previews retain those absences. Unsupported providers remain selected and rejected; there is no automatic fallback or provider migration.

## Implementation review

Production diff: one file, 25 inserted / 8 removed lines. Authorized changes:

1. Preserve the existing beam-limit exception and show 137/121 plus explicit Manual/cutoff guidance in the plot and detailed diagnostic.
2. Explain unfiltered geometry-only markers when the chosen elastic provider is unsupported.
3. Report unsupported elastic providers directly from Preview.
4. Remove only the MDFF-policy eligibility gate from elastic Preview; retain independent elastic geometry/target/provider checks.
5. Explain unchanged inherited, unvalidated material settings without changing any values.

No BW/MS, potential, provider, MDFF, Born/conjugation, tensor contraction, extinction, integer indexing, numerical default, Automatic policy resolver, Stage B, project format or packaging code changed.

`git diff --check` passes. The separate candidate-attestation test verifies every part of the module AST outside the two authorized method bodies matches the accepted baseline. No historical source guard or manifest is changed.

Added files: this report; `docs/acceptance/bcc-fe-gui-reviewed-diff.json`; `tests/test_bcc_fe_cif_gui.py`; `tests/fixtures/alpha_Fe_bcc_Im-3m.cif`.

## Focused verification

**20 passed, zero failed/errors/skipped** in `final-decoupled-focused.xml`.

Coverage includes exact CIF checksum/cell/symmetry expansion, independent counts at four cutoffs, original Ni Automatic diffraction, real Fe [017]/[001] previews, 13/113 beams, (100) absent and (200) allowed, all three unsupported MDFF choices leaving elastic Preview available while EMCD stays disabled, unsupported elastic provider labeling/rejection, explicit provider switching, invalid zone/target/cutoff/beam-limit rejection, stale versus completed maps, no preset/settings mutation, and separate candidate diff attestation.

Actual Qt MainWindow/import handlers and PreviewWorker were used; automated file-dialog selection returned the original path. Qt used offscreen rendering. This is source-GUI testing, not a new packaged-EXE acceptance claim.

Original-path evidence: `final-exact-workflow.json` records explicit Manual recovery and successful 13/113-beam previews without changes to inherited voltage, thickness, tilt or potential cutoff. `final-provider-geometry-validation.json` records Adaptive and Ni Lobato, Automatic and Manual, exact reasons, completed/geometry-only state and unchanged original CIF hash.

## Source-hash checks: baseline integrity versus candidate acceptance

The first full candidate run returned **806 passed, 54 skipped, 2 failed** (862 cases; source/test files unchanged during that run). Failures:

- `tests/test_unit_labels.py::test_current_sources_match_separately_reviewed_scope`
- `tests/test_unit_labels.py::test_historical_and_current_guards_work_without_git`

Their purpose is strict accepted-source identity, including GUI text and execution, against immutable reviewed manifests. The second also checks historical unit-only evidence and verifies guards operate without Git/process access. Both reject the intentionally changed `gui/app.py`; neither reported a numerical discrepancy. They are not generic tests of future candidate behavior.

Both unchanged checks pass on original accepted main (**2 passed**, `baseline-identity-control.xml`). They are **not** labeled passing on the modified candidate. They have not been deleted, marked expected-fail, deselected, relaxed, or extended with an allowlist.

A separate reviewed-diff attestation records accepted baseline and candidate SHA256 values plus the exact two authorized methods. It is not inserted into the historical source registry. A future version-specific/current-candidate source manifest needs independent review and explicit authorization if a new source identity is to be accepted; existing v0.8.1 evidence must remain immutable. This task does not perform that policy change.

## First-run skip difference: 54 versus accepted 39

All accepted baseline cases remained collected; nine initial new GUI cases explain 853 -> 862 collection. The following 15 additional skips account exactly for 54 -> 39. Missing references are not scientific passes.

- `tests/test_legacy_atomic_factors.py::test_reviewed_file_hash_required` ? Set EMCD_SIM_LEGACY_ATOMIC_TABLE to the reviewed external table
- `tests/test_legacy_atomic_factors.py::test_all_elements_nodes_limits_and_both_scaling_branches` ? Set EMCD_SIM_LEGACY_ATOMIC_TABLE to the reviewed external table
- `tests/test_legacy_atomic_factors.py::test_no_reinterpolation_or_marker_replacement` ? Set EMCD_SIM_LEGACY_ATOMIC_TABLE to the reviewed external table
- `tests/test_legacy_atomic_factors.py::test_ni_provider_comparison_is_not_an_equivalence_claim` ? Set EMCD_SIM_LEGACY_ATOMIC_TABLE to the reviewed external table
- `tests/test_legacy_atomic_factors.py::test_all_44_mott_rows_reject_unreliable_positive_values_and_preserve_origin` ? Set EMCD_SIM_LEGACY_ATOMIC_TABLE to the reviewed external table
- `tests/test_legacy_atomic_factors.py::test_large_mott_supercell_nonzero_vectors_are_not_replaced_by_origin` ? Set EMCD_SIM_LEGACY_ATOMIC_TABLE to the reviewed external table
- `tests/test_legacy_atomic_factors.py::test_independent_all_mott_interval_audit` ? Set EMCD_SIM_LEGACY_ATOMIC_TABLE to the reviewed external table
- `tests/test_legacy_atomic_factors.py::test_real_cscl_diffraction_and_fcc_extinctions` ? Set EMCD_SIM_LEGACY_ATOMIC_TABLE to the reviewed external table
- `tests/test_legacy_atomic_factors.py::test_real_table_bloch_multislice_matched_potential[symbols0-positions0-4.1-target0-0.55]` ? Set EMCD_SIM_LEGACY_ATOMIC_TABLE to the reviewed external table
- `tests/test_legacy_atomic_factors.py::test_real_table_bloch_multislice_matched_potential[symbols1-positions1-3.615-target1-0.85]` ? Set EMCD_SIM_LEGACY_ATOMIC_TABLE to the reviewed external table
- `tests/test_legacy_atomic_factors.py::test_real_table_bloch_multislice_matched_potential[symbols2-positions2-3.147-target2-0.85]` ? Set EMCD_SIM_LEGACY_ATOMIC_TABLE to the reviewed external table
- `tests/test_legacy_atomic_factors.py::test_gui_elastic_cif_and_inelastic_restrictions_remain_separate` ? Set EMCD_SIM_LEGACY_ATOMIC_TABLE to the reviewed external table
- `tests/test_legacy_atomic_factors.py::test_configured_desktop_elastic_button_and_missing_file_gate` ? Set EMCD_SIM_LEGACY_ATOMIC_TABLE to the reviewed external table
- `tests/test_single_element_ni_compatibility.py::test_genuine_historical_ni_project_remains_read_only_lobato` ? Optional genuine historical Ni project unavailable
- `tests/test_unit_labels.py::test_unit_changes_give_identical_bw_ms_single_double_numerical_arrays` ? Optional external 160-array evidence unavailable; set EMCD_UNIT_IDENTITY_DIRECTORY

For the final run, existing local references are explicitly configured read-only:

- `EMCD_SIM_LEGACY_ATOMIC_TABLE=C:\Users\peng863\Downloads\scattering.py`, SHA256 `1a93fe5b5fa86ea968049d8f4daee99a00981f225b3e8b8d0d9417460443535a`, matching the adapter's pinned source. Unlicensed data remain external and are not copied into Git.
- `EMCD_HISTORICAL_NI_PROJECT=C:\Users\peng863\EMCD-Sim\outputs\v060_release\source_native\single_both_project`. Its unchanged existing exact/tolerance requirements passed in a separate read-only check.
- `EMCD_UNIT_IDENTITY_DIRECTORY=C:\Users\peng863\EMCD-Sim\build\v070b1-unit-standardization\outputs\unit_labels`, containing the original baseline/standardized archives. No golden arrays regenerated.

## Final complete Windows regression

Final observed result: **832 passed, 39 skipped, 2 failed, zero errors; 873 collected; exit 1** in 1,563.00 seconds (26 minutes 3 seconds). The complete suite had no deselection, expected-failure relabeling or source-hash bypass. Source and test hashes remained unchanged throughout the run.

All 853 original baseline cases remain collected, with exactly 20 new GUI/candidate-attestation cases. The final 39 skipped identities exactly match the accepted baseline: no additional skips and no former skips relabeled as passes. Configuring existing references restored the 15 first-run extra skips. The net pass change is 814 + 20 new cases - 2 unchanged source-identity failures = 832. The two failures are exactly the baseline-identity checks named above; no other test failed.

Detailed comparison: `outputs/bcc-fe-cif-debug/final-regression-comparison.json`; full XML/log: `full-final.xml` and `full-final.log`.

Command and environment are recorded in `outputs/bcc-fe-cif-debug/full-final-run.json`: existing Windows Python 3.11.17 environment, NumPy 2.4.6, ASE 3.29.0, PySide6 6.12.0; Qt offscreen; OPENBLAS_NUM_THREADS=OMP_NUM_THREADS=1.

```powershell
& C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe -B outputs/bcc-fe-cif-debug/run_full_acceptance.py full-final
```

The runner invokes `python -B -m pytest tests -q -ra -p no:cacheprovider`, an isolated basetemp, JUnit XML and durations; it records command, timestamps, exit code, per-source/test hashes and post-run identity comparison. The exact collection and skip reconciliation is recorded in `final-regression-comparison.json`. The test suite is not reported as all-green.

## Scientific protection and actual bitwise comparisons

All **99 protected baseline files**, including **70 runtime Python modules** outside the GUI edit, match the accepted integration worktree byte-for-byte. All 70 runtime hashes also match the accepted EXE's build manifest directly. `protected-integrity.json` records old/current SHA256 values. A separate canonical Git-blob comparison handles checkout CRLF without modifying files. No accepted numerical reference or historical manifest is edited.

Existing exact scientific comparisons retain original assertions and tolerances: historical Ni transitions, angular amplitudes, site phases, provider energy grids and direct tensors; Born/MDFF, BW/MS and Ni references are included in the full run.

An additional read-only archival check found **808 serialized NPZ array pairs** identical against original Part 1 and **1,326** against Part 1B, including dtype, shape and bytes. These stored-array counts are distinct from historical 1,080/1,758 result-level comparisons and exclude reconstructed aliases. They verify archived output preservation, not new simulations through the candidate. Historical 9/30 nm studies were not rerun or relabeled.

The published EXE/ZIP remain unchanged. No new binary is claimed to contain this patch.

## Recommendation

**INCOMPLETE for merge acceptance.** The GUI-only fix has passed its 20 focused cases, and the full run found no additional functional or scientific failures. However, the complete suite still exits 1 because two strict v0.8.1 source-identity checks deliberately reject the changed GUI file. Those failures remain visible and unchanged.

A separately reviewed version-specific/current-candidate identity policy is required before claiming an all-green merge gate. The explicit candidate attestation provides the concrete diff/hashes for that review; it does not waive the existing assertions. No merge is recommended automatically, and no merge, push, tag, EXE rebuild or release was performed.

Final preservation check: all 99 protected files remain byte-identical; all 70 runtime hashes match the accepted EXE manifest. Original CIF remains unchanged. The accepted EXE SHA256 remains `69c0869379c590839909275876de9df9bba6ee761a88171bfa16abe63e266886`, and published ZIP remains `6f43834b138089cbade14c39374da5b38b128c95ad075ba2d732d1f1cf23de23`. Original root remains on main with its 18 unrelated untracked paths preserved.

Candidate canonical GUI SHA256: `9f42e1e3c4aad3a0f20c136335cf5c1b64fce85949fb6b49415113ccf555ae90`; baseline canonical GUI SHA256: `b5783a8014864a44705f1d8c0173ec34ce18171e78406617112d6bbada41d68f`. Raw checkout/accepted-build hashes are separately recorded in the attestation so CRLF differences are not confused with code changes.
