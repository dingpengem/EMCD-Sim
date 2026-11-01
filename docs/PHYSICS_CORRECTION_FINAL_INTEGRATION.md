# Physics correction final integration assessment

**Recommendation: GO for controlled, reviewed source integration into main.**
This is approval preparation only. No commit, merge, push, tag, release or
Windows executable build was performed. Full test green status below is scoped
to the practical suite and named optional skips; it does not establish full
physical convergence or quantitative Ni accuracy.

## 1. State and scope

Worktree: `C:/Users/peng863/EMCD-Sim/build/physics-correction-validation`,
detached at `a77f7455f5fe57dad6bae5d948477b2390433bb0` plus uncommitted
reviewed corrections. `start_state.json` records the incoming status and
hashes of 313 source/test/doc/tool files and 182 earlier acceptance artifacts.
All incoming final source hashes matched. Original checkout/worktrees and
user edits remain untouched. No assumption of live GitHub main equality was
made; future integration must fetch and inspect divergence normally.

The three production kernels were corrected in the preceding approved phase.
**This finalization changed no production Python whatsoever**: all `src/`
hashes match the incoming approved state, including GUI, numerical defaults,
worker policies and memory safety. Current GUI default remains 2 nm, range
0.001–10 nm; fine-step validation inputs remain explicit .04/.005 nm settings.
The public version remains 0.6.1b3.

## 2. Physical conventions and functions

| Item | Historical `legacy_same_index_h_minus_g` | Active `forward_born_dagger_g_minus_h_v1` |
|---|---|---|
| Imported target dipole | d=<i|r|f> | unchanged |
| Tensor | T_ab=sum_n w_n d_na conj(d_nb) | unchanged |
| Forward target excitation | used d | d* from <f|exp(-i Q.x)|i> |
| Intensity, R_ab=v_a conj(v_b) | Re sum R_ab T_ab = Re Tr(R T^T) | Re sum R_ab T_ba = Re Tr(R T) |
| Factorization | T=L L^dagger | unchanged; excite with L* |
| Double localized site phase | exp(+2*pi*i*(h-g).u) | exp(+2*pi*i*(g-h).u) |
| Single pair phase | exp(+2*pi*i*(g-g').u) | unchanged |
| Momentum / elastic propagation | Q=2*pi*(q_detector+h-g,q_z), independent entrance/exit | unchanged |

Carried approved functions: `_tensor_angular_maps` in
`single_channeling_tensor.py`; `contract_cartesian`, `equivalent_site_phases`,
`intensities_from_response`, and map components of `_run_tensor_double_channeling`
in `double_channeling.py`; `forward_event_amplitudes` and map components of
`run_tensor_multislice_double_channeling` in `multislice_double_channeling.py`.
Single BW/MS and Double BW/MS share these consistent contractions. No new
MDFF, material/orientation support, propagation scheme or numerical threshold.

## 3. Regression repairs and demonstrated causes

### Qt ownership and process RSS

The baseline failures were legitimate resource rejections, not a defective
budget comparison. A controlled probe showed four closed windows remained
alive after GC, retaining eight figures; RSS rose from 177.1 to 199.9 MiB.
Four subsequent deferred-deletion iterations added no live windows/figures;
RSS plateaued near 206 MiB. Native allocations need not return every byte
immediately; this evidence identifies retained test GUI ownership, not an
unproven production allocator leak. Normal desktop application exit is not
the repeated-window lifecycle used in a long pytest process.

`tests/conftest.py::release_test_owned_gui_resources` now destroys only
test-created MainWindows after fixture teardown, drains Qt deferred deletions,
closes only newly created pyplot figures, and collects Python cycles. Windows
owned by an earlier module/class scope are preserved. A remaining active GUI
calculation raises a teardown failure; it is never destroyed silently.
Optional JSONL telemetry reads actual RSS/RAM. No fake snapshot, allocation
trim, higher budget, disabled admission, source sampling reduction or weakened
resource assertion was introduced. Dedicated low-memory rejection tests pass.

Observed complete-suite lifecycle summaries:

```json
[
  {
    "round": 1,
    "logged_tests": 601,
    "destroyed_windows": 105,
    "max_remaining_mainwindows": 0,
    "max_post_teardown_rss_mib": 313.77734375
  },
  {
    "round": 2,
    "logged_tests": 601,
    "destroyed_windows": 105,
    "max_remaining_mainwindows": 0,
    "max_post_teardown_rss_mib": 314.30859375
  }
]
```

These are **post-teardown RSS samples**, not claimed whole-process peak-memory
measurements. Independent clean processes are enforced by
`scripts/run_final_physics_regressions.py`, which fingerprints source/tests,
records exact commands and refuses to count a source-mutated run as accepted.

### Exact historical input identity

The historical full-benchmark provenance asserts byte identity of the input
that produced that checkpoint. It is not a contract that every future package
copy has those same bytes. The immutable historical SHA256 remains
`a0e28ea6423b6c7832bb3cce6d69d71aa59336a221baeee3d2556b49ba501283`.
The later canonical package input remains
`4fd517af3e54db94588a76b7a6ed9c2f9a1b745cd8fe52b9fca0f87fc4938db3`.
The exact original was copied into
`tests/fixtures/Ni_fm_historical_full_benchmark.xmcd`. The benchmark test now
checks that historical artifact against the **unchanged** historical manifest.
A separate guard verifies both registered byte hashes; exact numerical equality
is supplementary, never substituted for provenance. `.gitattributes` prevents
Git EOL conversion of these two byte-identified input files. Neither input was
numerically edited, and no old provenance file was updated.

The first clean subset exposed 197 missing transitive historical fixture files
(first error: the voltage-study comparison CSV). All were restored as independent
copies after verifying their recorded hashes; no solver ran. The initial
48-pass/1-fixture-failure log is retained, and the repaired subset was rerun
cleanly. The complete suites used the restored dependencies.

### Approved defaults and present layout

`test_released_configuration_exactly_preserved` now compares **matched explicit**
legacy slice-step values instead of requiring the approved new-project default
to revert from 2 nm to .04 nm. The existing default=2 nm and editable-range
tests remain. `test_solver_visibility_and_classification` checks the current
separate editable slice control and collapsible FFT group, with correct BW/MS
visibility and enabled states. No GUI redesign, tabs or production edit.

### Versioned source identity, not a disabled guard

`tests/fixtures/physics_source_manifest_v1.json` preserves old Git blob hashes,
old reviewed worktree byte hashes, old convention identifier, approved patch
and acceptance provenance, and corrected source hashes. Canonical code hashes
normalize only UTF-8 BOM / CRLF, making the same source portable across OSs.
The active identifier is pinned by `tests/physics_source_guard.py`; the fixture
does not regenerate itself during tests. The former source-identity test keeps
its unchanged GUI/propagation AST guards and now checks the entire three-file
corrected source registration instead of insisting the repaired code is byte
identical to an older release. Mutation tests prove restoration of same-index
contraction, wrong site phase or unconjugated modes is rejected. The original
independent 0-versus-4 Born and nontrivial-site reproductions still pass without
XFAIL and would independently catch those errors even apart from file hashing.

### Three apparent intermittent failures

They were two old-convention reference expressions collected before their
required updates and one incomplete frozen-fixture set, not evidence of a
random solver defect. Forward order, reverse order and 3 repetitions in one
process all pass with explicit logs. The exact historical provenance case was
included in those sequences as an additional check. Numerical tolerances are
unchanged; no original failure was XFAILed, removed or relabeled as a pass.

## 4. Final test acceptance

| Scope | Passed | Failed/errors | Skipped |
|---|---:|---:|---:|
| Focused physics/guards | 59 | 0 | 0 |
| Clean-process GUI/regression repair subset | 49 | 0 | 0 |
| Repeated forward order | 4 | 0 | 0 |
| Repeated reverse order | 4 | 0 | 0 |
| Repeated in one process | 4 | 0 | 0 |
| Complete suite 1 | 600 | 0 | 2 |
| Complete suite 2 | 600 | 0 | 2 |

Counts overlap and are not summed. Complete rounds have identical immutable
source/test fingerprints: `f6ddbfa07de366a11c14f9b7e6b02ba4590a17d813330c742f79888fe8bb9797`.
Their elapsed times were 954.82 and
975.38 seconds. Exact commands, exit codes, warnings,
JSONL lifecycle samples and JUnit cases are retained under
`outputs/physics_correction_final_integration/acceptance_v1_run1/` and `run2/`.
No native standalone EXE acceptance is claimed from offscreen Qt tests.

The complete logs retain 902/894 warnings respectively: Qt/Matplotlib high-DPI
API deprecations and constrained-layout warnings from small/offscreen GUI
windows. They were not filtered or treated as proof of native display quality;
neither run reported a physics assertion or resource-admission failure.

Remaining optional skips (identical in both complete runs):

- `tests.test_ni_017.Ni017Tests::test_verified_native_edges`: Requires original local WIEN2k audit companions; not distributed
- `tests.test_ni_117_final_symmetry::test_wien2k_axis_is_independent_of_gui_default`: Optional local WIEN2k companion audit; original files are not distributed with the package

All former baseline failure classifications are preserved in the earlier
review. They are resolved by the documented contract/isolation repairs,
not erased from the old 576/18/3 evidence. Current pass/skip status is the
new evidence. If either complete round has any failure, integration is
**not fully accepted** regardless of isolated retries.

Reproducible commands (existing emcd-python environment; PYTHONPATH=src,
PYTHONDONTWRITEBYTECODE=1, QT_QPA_PLATFORM=offscreen, native BLAS/OMP=1):

```powershell
python -B scripts/run_final_physics_regressions.py --rounds 2 --tag acceptance_v1
python -B -m pytest tests/test_physics_matrix_audit.py tests/test_physics_correction_proposal.py tests/test_physics_correction_engines.py tests/test_double_channeling_foundation.py tests/test_multislice_double_channeling.py tests/test_double_channeling_bw.py tests/test_double_channeling_full_benchmark.py tests/test_single_channeling_tensor.py tests/test_physics_source_guard.py -q -p no:cacheprovider
python -B scripts/revalidate_final_physics.py --preservation
python -B scripts/finalize_physics_integration_report.py
```

The full runner safely reuses a completed passing tag only if the fingerprint
matches; failed/incomplete logs are preserved and require an explicit new tag.
The three-case order commands are recorded verbatim in `repeated_checks.json`.
No additional pytest isolation plugin or other dependency was introduced.

## 5. Scientific and protected-result integrity

All production hashes still match the previously approved correction. Existing
corrected/original Ni checkpoints were read only; stored kernel identities and
result digests match. Reversal-even quantities, reversed odd signs, Flip-M,
conventional A/B differences and percentages were recomputed from the four
raw intensities, not rerun or renormalized. All **32** old/new representative
BW/MS comparisons still pass raw-relative <=0.001 and PRB <=0.01 pp. Maximum
raw discrepancy remains **0.01749585%**, PRB **0.005387449 pp**.
At Ni [017], 30 nm/+15 mrad, corrected L3 magnetic-only asymmetry is +1.7099%
while conventional A/B is -2.9371%, due to strong nonmagnetic imbalance.
L3/L2 odd signs are corrected, even intensities and absolute |M| are unchanged
for the conventional FCC phases. The original Stage4.2 signed false-sign
locations require revision even where counts coincide; old plots/data remain
unaltered. These findings are neither a new full tilt scan nor a new proof of
quantitative Ni accuracy. See the unchanged detailed correction acceptance.

Hash checks passed for all **323 protected files / 204 production checkpoints**,
**9756 historical Stage1–4.2 files**, **19 original user files**, **182 previous
acceptance artifacts**, and the original worktree's audit/user edits, including
USER_GUIDE. Evidence: `preservation.json`, `revalidation.log`,
`scientific_revalidation.json`, `start_state.json`. No Ni research calculation
was rerun for checkpoint revalidation; regression tests still executed their
existing bounded solver controls. Existing current-facing physics notes now
state the corrected formulas; obsolete formulas are explicitly folded/marked
as superseded historical context. Historical audit/research reports are not
rewritten.

## 6. Source hashes and exact changed-file boundary

Canonical source SHA256 (full raw/Git/worktree identities and approval chain
are retained in the versioned JSON):

| Kernel | Legacy canonical SHA256 | Corrected canonical SHA256 |
|---|---|---|
| `src/emcd_sim/single_channeling_tensor.py` | `6dc8ca4a88d417196bd2b379da26ce1dbb97b1a3e24584a8c1dfc26a18d0553a` | `ac8a150fd370615b74886aeb81564a2fdd6b15e3d5da94e58ea1982afba8610d` |
| `src/emcd_sim/double_channeling.py` | `87bbadae896092f4e91c5a54a4ecc32df1a933e7bf8d79ddd9a5a7eadef7ba65` | `5b641bc918250b6402f4bcf6c31c1f3fec1425714098a1c99ed04e321b7ef06b` |
| `src/emcd_sim/multislice_double_channeling.py` | `bf256520126a9cf6e4e8bd1af15b1ca0352e7f2c1a1148f8a293ff289ae31df6` | `f7cc80b8de0898123813d6f1a284519df3790516ffa5660634bfccc838c437c5` |

Tracked changes relative to a77f745 (includes the carried approved correction):

```text
docs/DOUBLE_CHANNELING_BW.md
docs/DOUBLE_CHANNELING_MS.md
docs/MDFF_TENSOR.md
docs/PHYSICS.md
docs/SINGLE_CHANNELING_TENSOR.md
src/emcd_sim/double_channeling.py
src/emcd_sim/multislice_double_channeling.py
src/emcd_sim/single_channeling_tensor.py
tests/test_double_channeling_foundation.py
tests/test_double_channeling_full_benchmark.py
tests/test_double_channeling_full_outputs.py
tests/test_multislice_double_channeling.py
tests/test_single_channeling_tensor.py
tests/test_solver_settings_ui.py
```

Untracked source/test/docs to review (generated outputs intentionally excluded):

```text
.gitattributes
docs/PHYSICS_CONVENTIONS_AND_SOURCE_MAP.md
docs/PHYSICS_CORRECTION_ACCEPTANCE.md
docs/PHYSICS_CORRECTION_FINAL_INTEGRATION.md
docs/PHYSICS_MATRIX_IMPLEMENTATION_AUDIT.md
docs/PHYSICS_MINIMAL_CORRECTION_PROPOSAL.md
docs/PHYSICS_REGRESSION_FAILURE_REVIEW.md
docs/PHYSICS_VALIDATION_RESULTS.md
scripts/analyze_physics_correction.py
scripts/check_physics_correction_integrity.py
scripts/finalize_physics_integration_report.py
scripts/report_physics_correction.py
scripts/revalidate_final_physics.py
scripts/run_final_physics_regressions.py
scripts/validate_physics_correction_ni017.py
tests/conftest.py
tests/fixtures/Ni_fm_historical_full_benchmark.xmcd
tests/fixtures/ni_xmcd_provenance_v1.json
tests/fixtures/physics_source_manifest_v1.json
tests/physics_source_guard.py
tests/test_physics_correction_engines.py
tests/test_physics_correction_proposal.py
tests/test_physics_matrix_audit.py
tests/test_physics_source_guard.py
```

The incoming untracked audit/proposal documents and scientific tools were
already present before this finalization and are preserved. Do not use a blind
`git add .`: review the source/test/provenance/docs set, retaining the historical
audit context, and exclude build/output directories. The original main worktree
also has unrelated edits and untracked audit documents; integration must compare
and preserve those files rather than overwriting them.

## 7. Remaining limitations

No new physical convergence certification: [111] support sensitivity and the
Stage4.2 30 nm/offset -5 mrad/Y=+15 mrad/L2 detector-grid failure remain documented.
BW/MS agreement alone is not independent basis/potential/depth/FFT convergence.
XMCD-effective is not a genuine complex-transition DFT MDFF; RP/LP-to-absolute
magnetization handedness and absolute energy calibration remain unverified.
Frozen characteristic q_z, projected IAM, finite ZOLZ/path support and continuous
site/depth averaging remain; no outgoing change beyond the existing Double
model, atomic 3D/HOLZ, absorption/TDS, double ionization or electron-count/SNR
calibration was added. Accurate elastic intensities do not certify EMCD.
These existing limitations must remain visible after integration.

## 8. Controlled integration and rollback

GO applies only to reviewed source integration of the bounded research model.
Stop here for user review. After separate authorization, create a focused branch
from this isolated tree, stage only reviewed files, commit normally, fetch
main and inspect divergence, then use a normal non-destructive merge preserving
the feature history. Resolve no scientific/protected-data conflict by guessing.
If existing untracked files collide, stop and preserve/compare their hashes;
do not force checkout, reset, overwrite the user guide, or stash unrelated
science silently. Do not combine this with packaging, a version bump or release.

Recommended exact commit message:

```text
fix(physics): finalize forward-Born conventions and regression acceptance
```

Rollback is a separate clean worktree at a77f745 or a reviewed revert commit
of the coordinated code/tests/manifest together, never a reset of the user's
working tree. Preserve corrected artifacts as a separate convention/version;
never present old raw arrays under the corrected identity. Original kernels
and the approved diff remain in the earlier acceptance `before/` and patch
artifacts. A rollback must also restore the appropriate convention guard and
explicitly identify its old magnetic signs.

## 9. Future Stage4.2 corrected rerun plan — not executed

1. Use a new directory such as
   `outputs/ni017_stage42_corrected_forward_born_v1/<fingerprint>/`; retain every
   old Stage1–4.2 artifact. Case identity must include active convention ID,
   kernel hashes, eventual commit/dirty state, source SHA and complete settings.
2. Retain both equally important t=10/30 nm primary grids: offsets X=-8…+8
   mrad at 1 mrad, absolute Y=-15…+15 mrad at 2.5 mrad, both native L3/L2
   energies. Derive exact Bragg X via the current geometry; do not hard-code
   a shifted zone axis or change detectors with tilt. Same full finite Ni [017]
   basis (b=5/p=6.2), grid65, depth129, fractional boundary128, source eta/beta,
   fixed crystal magnetization and q apertures. No ideal two-beam truncation.
3. First profile a few missing corrected points using the saved runtime evidence.
   Reuse only validated thickness-independent elastic caches with matching input
   hashes; never reuse old raw intensity or old-convention response just by
   filename. Recompute actual corrected contractions/phase handling and save
   each completed condition immediately. Respect actual RAM admission and
   selected workers; do not silently reduce precision or sampling.
4. Execute the 884 primary conditions, then only justified local adaptive
   refinement (the previous cap was 24) and representative independent beam,
   potential, detector-grid, depth/slice controls. At the inherited failed
   grid65 point explicitly compare97/129 and further refinement if needed;
   preserve a failed baseline and use unchanged 0.01 pp/0.1% thresholds.
   Report convergence only for tested settings, never infer it from method
   agreement or a phase/sign identity.
5. Reuse the present bounded BW/MS control settings as checks, not a full MS
   tilt survey. Independently evaluate both reversal states with identical
   geometry; integrate raw apertures before percentages. Retain raw even/odd,
   Flip-M, conventional A/B, common denominators, uncertainty masks and PRB.
   Do not manufacture antisymmetry or separately normalize curve magnitudes.
6. Regenerate signed figures in the new directory with absolute tilt axes,
   derived Bragg/ZA markers and clear corrected-convention captions. Recompute
   false-sign spatial assignments, not just counts. Compare thin/thick
   |D_nonmag/D_mag| and zero crossings with explicit unresolved points. The
   prior algebraic state swap is a useful check, not the executed rerun.
7. Scientific review of the new convergence/status tables precedes any main
   publication, quantitative claim or later DFT-complex-transition work.
   No such rerun, DFT calculation, merge or Windows build was started here.
