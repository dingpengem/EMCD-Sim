# BCC Fe GUI source-identity acceptance — bcc-fe-gui-v1

## Scope and approved identities

Implementation is test infrastructure only. The already reviewed production GUI is unchanged: `src/emcd_sim/gui/app.py`, methods `MainWindow.refresh` and `MainWindow.start_preview`, 25 insertions / 8 deletions from accepted main.

- Branch: `fix/v081-bcc-fe-cif-preview`.
- Worktree: `C:\Users\peng863\EMCD-Sim\build\v081-bcc-fe-cif-debug`.
- Base HEAD: `b449edff0959058dc70b270e5fdf0f99fd485590`.
- Accepted scientific/EXE source: `cdd5dc3efa43e4f3874e011aa1cfc98f80cf46dd`.
- Baseline GUI canonical SHA256: `b5783a8014864a44705f1d8c0173ec34ce18171e78406617112d6bbada41d68f`.
- Candidate GUI canonical SHA256: `9f42e1e3c4aad3a0f20c136335cf5c1b64fce85949fb6b49415113ccf555ae90`.
- New scope manifest canonical SHA256: `a3a23ce6c92cbb52c4b6a019f406b36d38a30ac329a68e2cd8c4ded8463d9d32`.

The GUI baseline and candidate identities were checked before implementation. The baseline snapshot was obtained with `git show cdd5dc3efa43e4f3874e011aa1cfc98f80cf46dd:src/emcd_sim/gui/app.py`, verified against the approved canonical hash, and written as the exact 39,750 Git-blob bytes. It was not reconstructed from the candidate. The snapshot is source evidence only, read as bytes or parsed as AST; it is never imported or executed.

`bcc-fe-gui-v1` versions the reviewed source scope. It does not change application version metadata, the published tag, executable or ZIP.

## Why the two checks failed before this implementation

`test_current_sources_match_separately_reviewed_scope` required the existing effective current-source registry, which still pinned the accepted GUI baseline. `test_historical_and_current_guards_work_without_git` checked both immutable historical evidence and the same current checkout. Its historical portion passed; the current-GUI comparison failed.

The pre-scope run was 832 passed / 39 skipped / 2 failed. Both failures rejected the intentional GUI hash difference. They were not numerical failures and were not waived, expected-fail marked or reported as passes. The original checks also passed on original accepted main as a separate baseline control. The prior audit and attestation remain unchanged records of that stage.

## Enforcement design

`tests/unit_source_snapshots.py` now separates three operations:

1. `reviewed_baseline_sources()` loads and verifies all original source manifests, snapshot archives and reviewed extensions using the original rules. It returns the unchanged effective baseline map.
2. `load_gui_scope()` independently verifies a fixed manifest checksum, its complete closed schema, the exact baseline commit/hash, fixed snapshot name, fixed GUI path, candidate hash, authorized methods and physics convention. It separately hashes the trusted baseline snapshot.
3. `assert_reviewed_current_sources()` verifies the GUI scope parent matches the baseline map, copies that map, and replaces only the expected GUI digest for the explicitly selected `bcc-fe-gui-v1` candidate. It then compares source content with fixed expected identities as before.

The baseline map is not mutated or overwritten. A baseline GUI substituted for the candidate is rejected. The approved hash is never derived from the working tree. There is no branch/environment detection, permissive old-or-new hash set, network lookup, subprocess, or automatic hash refresh.

The original `scope_bytes` injection and historical checksum checks remain intact. `tests/test_unit_labels.py`, `tests/single_element_source_guard.py`, historical manifests, source archives and scientific golden arrays are unchanged. The existing physics-kernel registry receives no GUI override.

The two original tests retain their original assertions. Their current-checkout portion now checks the explicitly reviewed candidate scope; their historical evidence checks still validate the immutable historical records. Passing the current check does not assert that the candidate has the baseline hash.

## Files and reasons

| File | Change and reason |
|---|---|
| `tests/fixtures/bcc_fe_gui_scope_v1.json` | New fixed versioned scope, single GUI path only |
| `tests/fixtures/bcc_fe_gui_baseline_v1.py.txt` | New trusted baseline source evidence, allowing Git-free verification |
| `tests/unit_source_snapshots.py` | Factor the original baseline map and add the strictly constrained current-GUI scope |
| `tests/test_bcc_fe_gui_source_scope.py` | New positive, negative, historical-preservation and no-Git/network/execution tests |
| `tests/test_bcc_fe_cif_gui.py` | Only its baseline-attestation test now reads the pinned snapshot instead of invoking Git; all functional test bodies remain unchanged |
| This document | New implementation/acceptance record; prior reports are retained |

## Negative checks

Tests reject unauthorized candidate edits inside and outside the reviewed methods, rollback to baseline, manifest whitespace/content edits, altered candidate/parent hashes or commit, extra paths, kernel authorization, unsupported/boolean schema, wrong scope ID, traversal/backslash/case/ambiguous paths, wrong snapshot paths, additional method authorization, changed convention, changed baseline snapshot, unrelated numerical-source changes and historical extension-manifest edits.

The no-Git check blocks `subprocess.Popen`, network connection creation and `builtins.exec` while checking current source, baseline evidence and physics extensions. The baseline snapshot is not executable input.

The strict checksum is the first manifest defense. Tests separately exercise the closed semantic validator, so confinement to the GUI path does not depend solely on checksum rejection. Original numerical mutation tests are retained.

SHA256 enforcement relies on reviewed test code and fixed pins, as did the existing architecture. It is integrity enforcement, not a cryptographic signature against an actor who can rewrite both tests and manifests. Canonicalization remains the existing UTF-8/BOM and CRLF-to-LF comparison only; it does not normalize executable statements, numeric constants, phase signs or tensor conventions.

## Validation

The initial identity group passed **34 tests**. The combined GUI, source-identity and unit-label focused run passed **68 tests**.

The completed recovery Windows regression collected **899 cases: 860 passed, 39 skipped, 0 failed and 0 errors; exit code 0**, in 1,141.17 seconds (19 minutes 1 second). Both previously failing, unchanged source-identity tests passed:

- `tests/test_unit_labels.py::test_current_sources_match_separately_reviewed_scope`
- `tests/test_unit_labels.py::test_historical_and_current_guards_work_without_git`

All **26 new source-scope cases passed**. No previously collected tests were removed: all 853 accepted baseline cases remain, with 20 GUI cases and 26 source-scope cases added. All 39 skipped test identities match the accepted baseline; skipped comparisons are not counted as successful scientific validation.

The complete suite ran without deselection, skipped-to-pass relabeling, changed tolerances or regenerated arrays. The existing pinned external table, historical Ni project and 160-array references were supplied read-only using the environment recorded in the runner report. The original unlicensed table remains outside the repository.

### Completed regression evidence

Paths below are relative to this candidate worktree:

- Final pytest log: `outputs/bcc-fe-cif-debug/source-scope-recovery-full.log`
- Final JUnit XML: `outputs/bcc-fe-cif-debug/source-scope-recovery-full.xml`
- Final command, environment, source identities and exit status: `outputs/bcc-fe-cif-debug/source-scope-recovery-full-run.json`
- Combined focused JUnit XML: `outputs/bcc-fe-cif-debug/source-scope-gui-focused.xml`
- Protected baseline identities: `outputs/bcc-fe-cif-debug/protected-integrity.json`
- Source-scope integrity check: `outputs/bcc-fe-cif-debug/source-scope-integrity.json`

The earlier `source-scope-full` regression was interrupted. Its partial log and initial runner record have no final JUnit XML or exit status and are **not** counted as a completed run. Those records and their `.interrupted-backup` copies remain preserved. The separately named `source-scope-recovery-full` run completed successfully with exit code 0; its runner record confirms source identities were unchanged during testing.

### Scientific integrity and scope

Independent final review verified all **99 protected scientific/baseline files unchanged** against accepted source `cdd5dc3efa43e4f3874e011aa1cfc98f80cf46dd`, using the documented canonical text comparison and exact binary comparison. They also remain byte-identical to the accepted integration worktree. The earlier protection record additionally verifies 70 runtime hashes outside the GUI edit against the accepted EXE manifest.

The reviewed GUI canonical SHA256 remains `9f42e1e3c4aad3a0f20c136335cf5c1b64fce85949fb6b49415113ccf555ae90`; the independently pinned accepted baseline remains `b5783a8014864a44705f1d8c0173ec34ce18171e78406617112d6bbada41d68f`. The production diff remains restricted to `MainWindow.refresh` and `MainWindow.start_preview`, 25 insertions / 8 deletions. No BW/MS, elastic-potential, MDFF, phase-convention or Single/Double Channeling kernel changed.

Elastic Preview eligibility is separate from MDFF/EELS/EMCD eligibility. A successful Fe elastic preview does not authorize unsupported MDFF calculations or establish convergence of inherited numerical settings. This work does not claim quantitatively validated BCC Fe EMCD. The dynamical forbidden-reflection beam-basis issue remains outside this GUI bugfix. The 121-beam interactive limit and physical numerical settings are unchanged.

Existing exact-comparison tests retained their original requirements. Previously recorded archival bitwise comparisons concern preserved outputs, not newly rerun historical studies. No golden arrays or large historical scientific calculations were regenerated. Validation concerns the source GUI; the published Windows EXE was neither rebuilt nor validated as containing this patch.

## Acceptance history and final recommendation

The earlier report `docs/BCC_FE_CIF_DEBUG_ACCEPTANCE.md` and attestation `docs/acceptance/bcc-fe-gui-reviewed-diff.json` describe the pre-source-scope stage and remain unchanged historical evidence. Their INCOMPLETE assessment was issued before the additive `bcc-fe-gui-v1` mechanism was implemented, when two intentional current-GUI identity mismatches remained. This document supersedes that assessment for the explicitly pinned candidate; it does not rewrite the original evidence or imply the candidate has the baseline identity.

The independent final review found no functional, numerical or scientific blocker. Its sole remaining administrative blocker was this document's pending-validation wording. Recording the completed evidence here resolves that documentation blocker.

**GO for local commit and merge acceptance**, subject to separate explicit authorization to perform those Git actions and a final source/status check. This is not release or publication acceptance. No commit, merge, push, tag, release, Windows build or v0.9.0 development was performed during documentation completion.
