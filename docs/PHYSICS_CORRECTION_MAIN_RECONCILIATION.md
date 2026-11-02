# Physics correction: main-worktree reconciliation

**NO-GO for advancing actual main.** Documentation reconciliation is prepared,
but two substantive audit-test collisions require explicit disposition and a
fresh-checkout input-provenance defect remains unresolved. Nothing has been
committed, staged, merged into main, pushed, tagged, released or packaged here.
No research simulation or Stage4.2 rerun was performed; focused tests executed
only their existing bounded mathematical/solver controls.

## 1. State and preserved worktrees

- Correction commit: `5347f4473dc6057dadb97e102aa26aca7ba7214e`.
- Previously validated preview: `dabf61886e4432afa8e5692097b9d8903879b1fe`.
- Reconciliation branch: `reconciliation/forward-born-user-work`, at the same
  preview commit, in `build/physics-correction-main-reconciliation`.
- Actual main: `a77f7455f5fe57dad6bae5d948477b2390433bb0`, still checked out dirty in
  `build/source-cleanup-integration`; its original file bytes/status are unchanged.
- Local `origin/main` remains at the previously fetched baseline. No remote
  mutation or fetch was performed during this reconciliation task.

All 13 worktrees and all branches were inspected. The 12 pre-existing worktrees'
HEADs, status records and modified/untracked file hashes remain unchanged.
Complete evidence is in `outputs/physics_main_reconciliation/worktree_baseline.json`,
`branches_before.txt` and `preservation.json`. Only the new worktree has proposed
documentation edits. The earlier [integration report](../../physics-correction-main-preview/docs/PHYSICS_CORRECTION_MAIN_INTEGRATION.md)
is preserved in its original preview worktree.

## 2. Exact USER_GUIDE changes and proposed combination

The preview's committed guide is identical to main's committed guide, so there
is no overlap with the user's changes. The user's four diff hunks update the
policy from v3 to v5, change documented .04 nm defaults to 2 nm, describe the
editable .001-10 nm range/coarse-step advisory, and explain preservation of
explicit overrides across Automatic/Manual and BW/MS switching. These agree
with the unchanged production policy `automatic-starting-v5`.

Exact original user diff relative to main:

```diff
diff --git a/docs/USER_GUIDE.md b/docs/USER_GUIDE.md
index 9399fc3..b7c320f 100644
--- a/docs/USER_GUIDE.md
+++ b/docs/USER_GUIDE.md
@@ -407,9 +407,9 @@ Memory estimates and admission failures remain visible. Automatic selection
 does not propagate waves, evaluate MDFF, run trial calculations or establish
 convergence. Pressing Run starts only the requested calculation.
 
-The deterministic `automatic-starting-v3` policy normally uses the development
+The deterministic `automatic-starting-v5` policy normally uses the development
 starting values: beam 3.2 Å⁻¹, potential 2.5 Å⁻¹, depth 64, maximum MS step
-0.04 nm, angular grid 97, 64 aperture subpixels, halfwidth 1 Å⁻¹, 241 energy
+2 nm, angular grid 97, 64 aperture subpixels, halfwidth 1 Å⁻¹, 241 energy
 samples and 2048 MiB budget. It retains the selected physical geometry, B,
 systematic-row approximation, source, magnetization and detector positions.
 These settings are labeled **Automatic starting settings — convergence not
@@ -472,7 +472,7 @@ Panel F groups Manual controls into **Elastic Potential and Beam Support**, **In
 | Estimated process memory budget | Shared execution/admission resource, **not a physical-model parameter or required allocation**; stored unchanged and checked against current available RAM. |
 | Memory estimate and solver explanation | Diagnostics-only presentation; estimates reflect the currently selected engines, basis/sampling, retained allocations and RAM. |
 
-The physical-model and angular/integration categories affect both engines; memory admission and worker scheduling are separate resources rather than scattering parameters. Only FFT mesh and maximum slice step are MS-only. New development-project defaults are **300 kV**, beam **3.2 cycles/Å**, potential **2.5 cycles/Å**, B = 0, 64 depth nodes, FFT 32, maximum step 0.04 nm, energy count 241, halfwidth 1 cycle/Å, aperture subpixels 64, angular grid **97** and budget **2048 MiB**. New-project reference alignment follows the selected voltage; loading a saved project preserves its explicit voltage, tilt, cutoffs and sampling. Production reference settings are not substituted as ordinary defaults.
+The physical-model and angular/integration categories affect both engines; memory admission and worker scheduling are separate resources rather than scattering parameters. Only FFT mesh and maximum slice step are MS-only. New development-project defaults are **300 kV**, beam **3.2 cycles/Å**, potential **2.5 cycles/Å**, B = 0, 64 depth nodes, FFT 32, maximum step 2 nm, energy count 241, halfwidth 1 cycle/Å, aperture subpixels 64, angular grid **97** and budget **2048 MiB**. New-project reference alignment follows the selected voltage; loading a saved project preserves its explicit voltage, tilt, cutoffs and sampling. Production reference settings are not substituted as ordinary defaults.
 
 ### Parallel Workers and pre-Run risk
 
@@ -531,7 +531,7 @@ ZOLZ disk. Exact Bragg alignment does not establish physical two-beam isolation.
 | Potential cutoff (cycles/A) | Fourier harmonics of the elastic projected IAM potential. It is a separate physical/numerical convergence question. |
 | Debye–Waller B (A²) | The existing potential damping parameter; record any change. |
 | Multislice numerical settings → FFT grid (even) | Real/reciprocal sampling mesh, default 32. Must include the exact common hkl basis; even 12–128 is the supported control range. |
-| Max slice step (nm) | Maximum propagation substep, default 0.04 nm; distinct from the ionization depth nodes. |
+| Max slice step (nm) | Maximum propagation substep, default 2 nm, editable range 0.001?10 nm in both Automatic and Manual modes; distinct from the ionization depth nodes. The actual substep can be smaller. Requests above 0.04 nm show a nonblocking accuracy advisory, not a universal convergence threshold; check smaller steps for EMCD convergence. |
 | Depth integration nodes | Ionization/coherence depth sampling, default 64. |
 | Angular Map Resolution / Angular / detector grid points (odd) / Map halfwidth | Actual reciprocal sampling and field of view: Quick Preview 33, Standard 97 (default), High 193, or odd Custom 9–193; halfwidth defaults to 1 cycle/Å. Shared with detector-EELS quadrature. |
 | Aperture boundary subpixels | Boundary sampling for fractional circular area weights, default 64. It does not refine a spatially varying intensity field itself. |
@@ -945,3 +945,5 @@ explicitly. Cached low-level MS fields must match microscope, frame, reciprocal
 support and physical depth quadrature; mismatches fail instead of silently
 mixing contexts. Very large cells are rejected before overflowing a search-size
 calculation. These checks do not change solver physics, defaults or saved arrays.
+
+Max Slice Step remains visible and independently editable when FFT Multislice or Both is selected, including Automatic numerical mode. Explicit edits survive refreshes, mode changes and BW/MS switching. Other numerical controls retain their Automatic/Manual rules. New projects start at 2 nm; saved projects and frozen reference profiles preserve their explicit steps. Coarse settings require convergence checks against smaller steps; elastic-intensity accuracy alone does not certify EMCD accuracy.
```

The isolated combined file starts with **every original user byte verbatim**,
then adds a small forward-Born correction / historical-output note and an
unambiguous range statement. The existing literal `0.001?10` typography is
retained from the user's original line; the added note says `0.001 to 10 nm`.
No original guide file was edited, reformatted or replaced.

- Original user guide SHA256: `179e54badf9ca9442a90ea982deddb021156a32730c4038308f8c54a0fa136fb`.
- Original preview guide SHA256: `ef25cb4c88a922a1bbbe7e19fdabd1457789ac0556c3e94541baf09aa676498d`.
- Proposed combined guide SHA256: `20ff9153db25408294a11d6e0ebee8a6a577f3cce1dd88a9a50a519908fea4a0`.

Complete proposed guide diff relative to the validated preview:

```diff
--- validated_preview/docs/USER_GUIDE.md
+++ proposed/docs/USER_GUIDE.md
@@ -407,9 +407,9 @@
 does not propagate waves, evaluate MDFF, run trial calculations or establish
 convergence. Pressing Run starts only the requested calculation.
 
-The deterministic `automatic-starting-v3` policy normally uses the development
+The deterministic `automatic-starting-v5` policy normally uses the development
 starting values: beam 3.2 Å⁻¹, potential 2.5 Å⁻¹, depth 64, maximum MS step
-0.04 nm, angular grid 97, 64 aperture subpixels, halfwidth 1 Å⁻¹, 241 energy
+2 nm, angular grid 97, 64 aperture subpixels, halfwidth 1 Å⁻¹, 241 energy
 samples and 2048 MiB budget. It retains the selected physical geometry, B,
 systematic-row approximation, source, magnetization and detector positions.
 These settings are labeled **Automatic starting settings — convergence not
@@ -472,7 +472,7 @@
 | Estimated process memory budget | Shared execution/admission resource, **not a physical-model parameter or required allocation**; stored unchanged and checked against current available RAM. |
 | Memory estimate and solver explanation | Diagnostics-only presentation; estimates reflect the currently selected engines, basis/sampling, retained allocations and RAM. |
 
-The physical-model and angular/integration categories affect both engines; memory admission and worker scheduling are separate resources rather than scattering parameters. Only FFT mesh and maximum slice step are MS-only. New development-project defaults are **300 kV**, beam **3.2 cycles/Å**, potential **2.5 cycles/Å**, B = 0, 64 depth nodes, FFT 32, maximum step 0.04 nm, energy count 241, halfwidth 1 cycle/Å, aperture subpixels 64, angular grid **97** and budget **2048 MiB**. New-project reference alignment follows the selected voltage; loading a saved project preserves its explicit voltage, tilt, cutoffs and sampling. Production reference settings are not substituted as ordinary defaults.
+The physical-model and angular/integration categories affect both engines; memory admission and worker scheduling are separate resources rather than scattering parameters. Only FFT mesh and maximum slice step are MS-only. New development-project defaults are **300 kV**, beam **3.2 cycles/Å**, potential **2.5 cycles/Å**, B = 0, 64 depth nodes, FFT 32, maximum step 2 nm, energy count 241, halfwidth 1 cycle/Å, aperture subpixels 64, angular grid **97** and budget **2048 MiB**. New-project reference alignment follows the selected voltage; loading a saved project preserves its explicit voltage, tilt, cutoffs and sampling. Production reference settings are not substituted as ordinary defaults.
 
 ### Parallel Workers and pre-Run risk
 
@@ -531,7 +531,7 @@
 | Potential cutoff (cycles/A) | Fourier harmonics of the elastic projected IAM potential. It is a separate physical/numerical convergence question. |
 | Debye–Waller B (A²) | The existing potential damping parameter; record any change. |
 | Multislice numerical settings → FFT grid (even) | Real/reciprocal sampling mesh, default 32. Must include the exact common hkl basis; even 12–128 is the supported control range. |
-| Max slice step (nm) | Maximum propagation substep, default 0.04 nm; distinct from the ionization depth nodes. |
+| Max slice step (nm) | Maximum propagation substep, default 2 nm, editable range 0.001?10 nm in both Automatic and Manual modes; distinct from the ionization depth nodes. The actual substep can be smaller. Requests above 0.04 nm show a nonblocking accuracy advisory, not a universal convergence threshold; check smaller steps for EMCD convergence. |
 | Depth integration nodes | Ionization/coherence depth sampling, default 64. |
 | Angular Map Resolution / Angular / detector grid points (odd) / Map halfwidth | Actual reciprocal sampling and field of view: Quick Preview 33, Standard 97 (default), High 193, or odd Custom 9–193; halfwidth defaults to 1 cycle/Å. Shared with detector-EELS quadrature. |
 | Aperture boundary subpixels | Boundary sampling for fractional circular area weights, default 64. It does not refine a spatially varying intensity field itself. |
@@ -945,3 +945,25 @@
 support and physical depth quadrature; mismatches fail instead of silently
 mixing contexts. Very large cells are rejected before overflowing a search-size
 calculation. These checks do not change solver physics, defaults or saved arrays.
+
+Max Slice Step remains visible and independently editable when FFT Multislice or Both is selected, including Automatic numerical mode. Explicit edits survive refreshes, mode changes and BW/MS switching. Other numerical controls retain their Automatic/Manual rules. New projects start at 2 nm; saved projects and frozen reference profiles preserve their explicit steps. Coarse settings require convergence checks against smaller steps; elastic-intensity accuracy alone does not certify EMCD accuracy.
+
+
+## Forward-Born convention correction and historical results
+
+The corrected source uses d=<i|r|f>, Q=k_out-k_in and
+T_ab=sum_n w_n d_na conj(d_nb). With R_ab=v_a conj(v_b), forward intensity
+is Re sum_ab R_ab T_ba. The factorization remains T=L L^dagger; forward transition
+amplitudes use L*. Double Channeling uses the localized site phase
+exp(+2*pi*i*(g-h).u), consistent with the Single Channeling convention.
+See [physics correction acceptance](PHYSICS_CORRECTION_FINAL_INTEGRATION.md)
+for independent controls, sign changes and numerical limitations. Historical
+scientific outputs and previously built Windows executables were not regenerated
+by this source correction; do not relabel their raw spectra or signed figures
+as corrected calculations. Corrected contrast remains distinct from intrinsic
+magnetic intensity.
+
+The editable maximum split-step range is 0.001 to 10 nm, with a 2 nm
+new-project default. This default is not a convergence certification. Explicit
+fine-step settings in saved/reference projects remain unchanged; verify EMCD
+convergence against smaller steps independently of elastic-intensity accuracy.
```

## 3. All seven collision identities and classifications

All five documents below are historical audit artifacts, not numerical results.
The two Python files are historical audit tests, not production kernels or
scientific output arrays. `content-equivalent` means exact Unicode text after
UTF-8 BOM removal and CRLF-to-LF conversion only; no other normalization.

| Path | Classification | Original user SHA256 | Validated preview SHA256 |
|---|---|---|---|
| `docs/PHYSICS_CONVENTIONS_AND_SOURCE_MAP.md` | content-equivalent | `db1a55e95398132764ca4a8b55c93b692e810b1236420fa3f879a76a948e79cf` | `8667e93782a43779f31ba0d4ce8020259cadaec85582ca43b6390eae97d1ecd7` |
| `docs/PHYSICS_MATRIX_IMPLEMENTATION_AUDIT.md` | content-equivalent | `44e8655ce05c5240b6fabf8d9a80bbc921eb5245fb25dc8cf7d24de2c01fb733` | `1dcfd6cad299ae7548dbeea16148c9f5b608796acb337221ee9f2240b6ac5c2c` |
| `docs/PHYSICS_MINIMAL_CORRECTION_PROPOSAL.md` | byte-identical | `cbf0935570ea2550db9f4715097dd53b314c8949cafe2a903f345e948905f59d` | `cbf0935570ea2550db9f4715097dd53b314c8949cafe2a903f345e948905f59d` |
| `docs/PHYSICS_REGRESSION_FAILURE_REVIEW.md` | byte-identical | `f3e636c4e674a24eb0a0f597a11308b1b3e447688020040ed6e010602107a4c5` | `f3e636c4e674a24eb0a0f597a11308b1b3e447688020040ed6e010602107a4c5` |
| `docs/PHYSICS_VALIDATION_RESULTS.md` | content-equivalent | `e983001806007447f5a16f1c420b0b0912cb19d640b5ccb6b1d569ddfc50cb61` | `e781fb740ad5797589f2ff8840f36167a97b9cde2b282028aba910fb7c41e61e` |
| `tests/test_physics_correction_proposal.py` | different | `38dc34a7f89586981039a1b0a88c050ea8654a462f03c00bffb93d4fdbd6d401` | `2e6a92e24b23000c8bf22e90292a5c4b484ed42b5dc90622fd5fdf84121330b7` |
| `tests/test_physics_matrix_audit.py` | different | `99f18b043a4e0345f0b58731dc012832578a7bb9730b3aa9f3045df4fba6ecb7` | `2da72a956a1a9246bc33940cc017d4d39714492f0fe0f9e119fd8cd05e11395b` |

Both raw versions are preserved under
`outputs/physics_main_reconciliation/snapshots/user/` and
`snapshots/validated_preview/`, with a comparison patch for each path under
`comparisons/`. Byte-identical files have no differences; the three equivalent
documents differ only in line endings. Their original bytes remain untouched.
No choice or overwrite was made to resolve either substantive test collision.
The new branch inherits the validated tests from its base; that fact does not
constitute approval to replace the user's older files in their original worktree.

### Substantive differences requiring review

1. `tests/test_physics_correction_proposal.py`: the historical version compensates
   for old kernels with transposed tensors/conjugated inputs. The validated
   version invokes corrected Single contraction and forward modes with the
   original tensor, uses the real `intensities_from_response`, and keeps an
   explicit old-phase comparator. These are changes of convention expectations,
   not just formatting. Full diff:
   [proposal comparison](../outputs/physics_main_reconciliation/comparisons/tests/test_physics_correction_proposal.py.patch).
2. `tests/test_physics_matrix_audit.py`: the old file has two strict XFAIL markers,
   same-index/direct-dipole references and opposite site-phase expectations.
   The validated file removes those XFAILs, uses conjugated physical dipoles,
   and tests the corrected site-phase equality. The two original independent
   Born/site-phase reproduction bodies are AST-identical across versions;
   decorators and other convention-dependent references differ. Full diff:
   [audit comparison](../outputs/physics_main_reconciliation/comparisons/tests/test_physics_matrix_audit.py.patch).

**Proposed, not applied:** keep the corrected tests as active tests and preserve
the original audit versions as historical snapshots outside test discovery.
This requires explicit review; neither historical file was overwritten or
added as a duplicate active test. No automatic version selection was performed.

The eighth untracked file, `scripts/physics_matrix_audit.py`, is a noncolliding
personal audit tool, absent from the preview. Its SHA256 is
`2979b209422ebd8d7b5a36255fd1da83a41921fe72c112ecfcd656f4e62c4a1c`.
It remains unchanged in place and has an ignored preservation snapshot. It is
not proposed for Git inclusion. No collision is a scientific result.

## 4. Fresh-checkout provenance failure: additional blocker

The focused tests found a reproducible committed-provenance mismatch, separate
from the two collisions and from physics-kernel behavior:

```text
tests/test_physics_source_guard.py::test_historical_and_current_ni_inputs_have_distinct_exact_provenance
assert actual package SHA256 == manifest canonical_package.sha256
actual:   4fd517af3e54db94588a76b7a6ed9c2f9a1b745cd8fe52b9fca0f87fc4938db3
expected: bb9bdd478d54cc8de60403409f4d90e63deb11a64891bbac6754f867be14deda
```

The Git blob of `data/wien2k_ni/Ni_fm.xmcd` contains LF bytes (actual hash above).
The existing correction/preview worktrees retain CRLF bytes (expected hash).
The committed `.gitattributes` sets this file to `-text`, so a fresh checkout
keeps the LF Git blob. The committed `ni_xmcd_provenance_v1.json` expects only
the old CRLF worktree hash. A clean checkout therefore fails the exact-byte
guard even though the older worktrees passed. Direct byte comparison after
CRLF-to-LF conversion is identical, and NumPy arrays compare exactly equal.
This is **not** a physical-data difference or a reason to replace provenance
checks with numerical equality.

The original historical source hash remains
`a0e28ea6423b6c7832bb3cce6d69d71aa59336a221baeee3d2556b49ba501283`.
No data, attribute, fixture manifest, source guard or test was changed to hide
the failure. Detailed evidence is in `fresh_checkout_provenance_failure.json`.
The previous 600-pass preview evidence remains valid for its CRLF worktree;
it does **not** establish fresh-checkout exact-byte provenance acceptance.

**Proposed review only:** register the shipped LF Git-blob identity in a
reviewed/versioned provenance repair while retaining the CRLF validated-worktree
identity and all historical hashes. Decide the exact package representation
contract explicitly, then verify clean and existing worktrees. Do not merely
accept arbitrary normalized content, rewrite an old hash silently, or mutate
scientific archives. This repair is not applied. If tests/fixtures change in a
subsequent approved repair, rerun the full practical suite as well as focused
provenance checks before declaring integration ready.

## 5. Validation and unchanged physics

| Check in reconciliation worktree | Result |
|---|---|
| Focused physics and source/input guards | **58 passed, 1 failed**: exact input provenance above |
| Original Born and nontrivial site reproductions | pass, no XFAIL in active tests |
| Three kernel guards and mutation rejection | pass |
| Documentation/reconciliation artifact checks | **8 passed** |
| Production source files | all 53 byte hashes unchanged |
| Active test files and versioned source guard | unchanged from validated preview |
| Protected files / production checkpoints | 323 / 204 unchanged |
| Historical research files | 9756 unchanged |
| Original scientific files | 19 unchanged |
| Original user guide, eight untracked files, other worktrees | unchanged |

The first documentation-check run caught an encoding error in the newly appended
note (`L?` instead of dagger notation). Only the new isolated note/helper check
was repaired to ASCII `L^dagger`; the original user bytes were preserved.
Initial logs (7 pass / 1 fail) remain alongside the final 8-pass logs. The
focused provenance failure is retained as a failure; it was not suppressed,
XFAILed or rerun with altered data.

No full pytest suite was repeated because no integrated source, active test,
fixture, numerical setting or input file changed from the preview. The original
600 pass / 2 skip full-suite and 32/32 BW/MS evidence are previous results, not
new runs. The current fresh-checkout failure blocks acceptance despite that
earlier green status. No new research calculation was run.

Active physics convention: `forward_born_dagger_g_minus_h_v1`. Kernel canonical SHA256:

| File | Canonical SHA256 |
|---|---|
| `src/emcd_sim/single_channeling_tensor.py` | `ac8a150fd370615b74886aeb81564a2fdd6b15e3d5da94e58ea1982afba8610d` |
| `src/emcd_sim/double_channeling.py` | `5b641bc918250b6402f4bcf6c31c1f3fec1425714098a1c99ed04e321b7ef06b` |
| `src/emcd_sim/multislice_double_channeling.py` | `f7cc80b8de0898123813d6f1a284519df3790516ffa5660634bfccc838c437c5` |

The versioned source guard and its manifest are byte-identical to the validated
preview. Their raw SHA256 identities are recorded in the reconciliation manifest.
No Hamiltonian, propagation, MDFF, site phase, contraction, default, worker policy,
GUI layout or result was edited. Existing [111] and Stage4.2 detector-grid
convergence limits and absolute XMCD/MDFF convention limitations remain.

## 6. Reconciliation manifest and exact change boundary

The complete machine-readable [manifest](../outputs/physics_main_reconciliation/reconciliation_manifest.json)
contains all seven classifications and both hashes, the eighth personal tool,
guide identities, snapshot/patch paths, unresolved paths and provenance evidence.
Worktree baseline, preservation proof and exact commands/logs are beside it.
Only `docs/USER_GUIDE.md` differs among tracked files; this report is a new
untracked review document. All evidence/snapshots/helpers are ignored outputs.
Nothing is staged or committed, and no unrelated artifact is proposed for Git.

Reproducible focused command (emcd-python environment, PYTHONPATH=src,
PYTHONDONTWRITEBYTECODE=1, QT_QPA_PLATFORM=offscreen, BLAS/OMP threads=1):

```powershell
python -B -m pytest tests/test_physics_matrix_audit.py tests/test_physics_correction_proposal.py tests/test_physics_correction_engines.py tests/test_double_channeling_foundation.py tests/test_multislice_double_channeling.py tests/test_double_channeling_bw.py tests/test_double_channeling_full_benchmark.py tests/test_single_channeling_tensor.py tests/test_physics_source_guard.py -q -p no:cacheprovider
python -B -m pytest outputs/physics_main_reconciliation/test_reconciliation_documents.py -q -p no:cacheprovider
python -B outputs/physics_main_reconciliation/verify_preservation.py
```

## 7. Main readiness and safe next commands

**Actual main must not advance now.** Required review decisions:

1. Approve a disposition for both substantive historical-vs-corrected test files,
   including retention of the original audit snapshots outside active discovery.
2. Approve a minimal input-provenance repair and its exact-byte representation
   contract, then validate it in a fresh checkout. This is now a separate blocker.
3. Review the combined guide diff and proposed documentation-only commit.

A separate documentation reconciliation commit will be needed after approval
to retain the combined guide and this report. No additional commit of the
personal audit tool or unrelated research data is required or proposed. The
provenance repair may need its own narrowly reviewed fixture/test commit and
full regression acceptance. No such commits were made here.

Safe inspection commands now (all read-only; these do not clean or move main):

```powershell
git -C C:/Users/peng863/EMCD-Sim/build/source-cleanup-integration status --short
git -C C:/Users/peng863/EMCD-Sim/build/source-cleanup-integration diff -- docs/USER_GUIDE.md
git -C C:/Users/peng863/EMCD-Sim/build/physics-correction-main-reconciliation diff -- docs/USER_GUIDE.md
git -C C:/Users/peng863/EMCD-Sim/build/physics-correction-main-reconciliation diff --exit-code dabf618 -- src tests data pyproject.toml
git -C C:/Users/peng863/EMCD-Sim/build/physics-correction-main-reconciliation show dabf618:tests/fixtures/ni_xmcd_provenance_v1.json
```

An executable main-advancement command sequence is deliberately **not finalized**
while collision decisions and a failing provenance guard are unresolved.
Running `git merge` in the dirty main worktree now is not safe.

After explicit review, the file-preserving integration strategy can be to
switch that worktree to a new preservation branch **at its same current commit**,
verify unchanged hashes/status, and leave all its dirty files in place. Main
would then be free for checkout in a different clean worktree, where a normal
non-fast-forward merge of the approved reconciliation branch can occur.
Git must refuse if main is still checked out elsewhere; no force option or
checked-out-ref update is appropriate. Recheck remote divergence and all guards
before any later main merge. This strategy has not been executed or approved
as a substitute for resolving the current review decisions.

No reset, forced checkout, stash, file removal, GitHub push, tag, release,
version bump, Windows build or Stage4.2 execution was performed.
