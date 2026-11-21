# Phase 3 final regression, main integration and scientific baseline

Date: 2026-11-21, America/Los_Angeles.

## A. Executive decision

| Acceptance | Decision | Evidence / boundary |
|---|---|---|
| Full Regression | **GO** | One uninterrupted invocation: **1,762 passed, 62 skipped, 0 failed, 0 errors**, all 1,824 collected nodes accounted for |
| Phase 3 Local Merge | **GO** | Normal history-preserving merge `46136856f9c8af56502a7dcc752bde2b6cd943ed`; entire merged Git tree equals the tested Phase 3 candidate; 14 post-merge tests passed |
| Next-Gen A Integration | **GO** | Separate merge `ff64d739375dfdbcb903105c365f9b0f1ca393ae`; exactly four reports/two benchmark scripts; 3 post-merge tests and tooling/link checks passed |
| Native Development | **Existing Conditional Native GO retained** | Application, packaging, test, data and original build-script objects match frozen Phase 3F-2 source; no EXE rebuild or new native run |
| Public Release | **Not granted** | Clean-machine installation and applicable release/security/publishing acceptance remain separate |

The final full-regression candidate is
`a97ccf14e890b9e52fc57d47261117717825f5ba`, on
`refactor/physics-readability`. It was clean and committed before testing and
remained unchanged throughout the complete invocation. The earlier Phase 3F-1
combined result is historical evidence; it is not substituted for this clean
run and is not retroactively attributed to the Phase 3F-2 implementation.

The application/design integration tip is
`ff64d739375dfdbcb903105c365f9b0f1ca393ae`. Final local `main` is its
documentation-only successor containing this report. Its exact commit is
recorded in `final-state.json` and the final handoff. It can be identified
without a self-referential hash in this file:

```powershell
git log -1 --format=%H -- docs/PHASE3_FINAL_REGRESSION_AND_MAIN_INTEGRATION.md
```

No unresolved regression, scientific-equivalence or integration blocker remains.
No scientific/application/test correction was made during this task. An extra
raw source-inventory probe found LF/CRLF checkout differences; section E records
their exact classification without modifying source or historical provenance.

## B. Git provenance and frozen source

| Identity | Exact commit |
|---|---|
| Original independent pre-refactor source | `cdb8836388c5ccc5ae7a614b47894c0ab158a824` |
| Starting local `main` | `28db1839417a6bdd9731c1368f8943ae3ef1d5d8` |
| Phase 3F-2 implementation / registered production source | `41e376c3b891df2ef225c43a5db0e1f6bc1794b8` |
| Phase 3F-2 frozen Windows build/source | `473ac666592e11fc962ecb64d27354ccb18d4ba0` |
| Final full-regression candidate | `a97ccf14e890b9e52fc57d47261117717825f5ba` |
| Phase 3 branch HEAD, before and after integration | `a97ccf14e890b9e52fc57d47261117717825f5ba` |
| Next-Gen A measured-tooling commit | `70af53cd763b64fe67af11a9d551b7ad6aa59755` |
| Next-Gen A branch HEAD, before and after integration | `eb67c17c18cd171262a9d552cb0dcf24119ea6b5` |
| Phase 3 merge commit | `46136856f9c8af56502a7dcc752bde2b6cd943ed` |
| Separate Next-Gen A merge / integrated baseline tip | `ff64d739375dfdbcb903105c365f9b0f1ca393ae` |
| Final local main, including this report | Commit containing this report; exact ID in `final-state.json` and the Git command above |

Relevant worktrees:

* Main: `C:/Users/peng863/EMCD-Sim`.
* Phase 3 / regression working directory:
  `C:/Users/peng863/EMCD-Sim/.worktrees/windows-adaptive-compute`.
* Next-Gen A: `C:/Users/peng863/EMCD-Sim/.worktrees/nextgen-a`.

The merge base of starting main and Phase 3 was starting main itself: divergence
0/141 commits. The merge base of Phase 3 and Next-Gen A was `a97ccf1`:
divergence 0/4 commits. Next-Gen A is therefore a verified descendant, not a
parallel experimental-science branch. The Phase 3 difference from frozen source
`473ac66` is only `docs/PHASE3F2_WINDOWS_NATIVE_ACCEPTANCE.md`.

The tested candidate's root Git tree is
`e62b3e5f351370bf3e6f9b7b9cbd277ac24076bf`. Git objects, rather than path-name
similarity, establish the implementation identity:

| Committed tree | Exact object | Candidate = native source = integrated main |
|---|---|---|
| `src` | `5e0a6ab123639d2d7191f8de98aea19a655c42da` | Yes |
| `packaging` | `25d5733d09db5353fc92e83e1a8b2f71e834e7e1` | Yes |
| `tests` | `294e512802833f96f07ef8fc5dac26923adcec13` | Yes |
| `data` | `8572e80da155df33ca0f8705fa1db99e8e868cb1` | Yes |
| Original `scripts` | `a89065cb026c6a4595ceaa85c02fe929a4940681` | Candidate/native/Phase 3 merge equal; Next-Gen A adds exactly two scripts |
| Integrated `scripts` | `b93ecefafe18e350555934646c20c1e20eb9cf83` | Exactly the reviewed Next-Gen A delta |

`pyproject.toml` also matches frozen source exactly. Existing scientific
references, schemas, dependency definitions and source-registration data are
unchanged. The current registration contains 173 file entries and still points
to reviewed production source `41e376c...`; merge/documentation commit identities
are not written back into historical scientific provenance.

## C. One clean complete regression

| Outcome | Result |
|---|---:|
| Collected | **1,824** |
| Passed | **1,762** |
| Failed | **0** |
| Errors | **0** |
| Skipped | **62** |
| Console pytest duration | **11,960.87 s (3:19:20.87)** |
| JUnit suite duration | 11,960.785 s |
| Owned launcher wall duration | 11,974.801 s |
| Warnings | 1,179, retained in the full log |
| Actual pytest payload PID | 31396 |
| Payload peak RSS | **928.578125 MiB** |
| Payload peak process commit | **1,020.58984375 MiB** |

The 1,824 XML identities exactly equal the collected nodes, in the same order.
There were no collection failures, new exclusions, xfails, added skips, relaxed
comparisons, reduced dimensions or regenerated references. The full run did not
use `-x` or `--maxfail`. It completed normally within the existing reviewed
eight-hour bound, chosen to accommodate historical 4,311–19,908-second full
runs and the earlier 12,874-second Phase 3F-1 invocation.

The previous 1,821-node inventory changed only by these three reviewed Phase
3F-2 tests, all passing in this run:

* `tests/test_project_workflow.py::test_collection_resave_replaces_run_inputs_and_preserves_attachments`
* `tests/test_multisite_result_selection.py::test_switching_disjoint_groups_clears_comparison_without_callback_errors[False]`
* `tests/test_multisite_result_selection.py::test_switching_disjoint_groups_clears_comparison_without_callback_errors[True]`

No node was removed or renamed. The net change is +3 (+0.165%).

### Environment and command

Python 3.11.17, established interpreter
`C:/Users/peng863/EMCD-Sim/build/windows-rc/venv/Scripts/python.exe`;
NumPy 2.4.6; SciPy 1.17.1; PySide6/Qt 6.12.0; pytest 9.1.1;
Matplotlib 3.11.2; ASE 3.29.0; spglib 2.7.0. The recorded native configuration
is OpenBLAS 0.3.31.188.0, one observed NumPy thread, with the existing
NumPy/SciPy runtime-control tests passing.

`PYTHONHASHSEED=0`, `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`,
`MKL_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`,
`QT_QPA_PLATFORM=offscreen`, `PYTHONDONTWRITEBYTECODE=1` and empty
`PYTEST_ADDOPTS`. `PYTHONPATH` contains the candidate worktree's `src` and
`tests`. The exact short unique basetemp is included in the command below,
under `C:/Users/peng863/EMCD-Sim/build/nc-tmp/`.

The reviewed Phase 3F-1 pytest payload/argument sequence was replayed from
`build/phase3f1/full-regression-run.json`, changing evidence and temporary paths.
Its unchanged `-c` bootstrap invokes `pytest.main` and reports Windows payload
peak memory at exit. It does not select or replace tests. A task-level Windows
kill-on-close job owned the launcher and all descendants, with no CPU/memory
quota. Final owned-process queries found no remaining processes and no forced
cleanup was necessary. Memory is the actual pytest process lifetime peak,
not the small venv launcher or a claimed aggregate of every child.

Exact executable and argv, recorded as JSON (escaped newlines belong to the
original Python `-c` payload):

```json
[
  "C:\\Users\\peng863\\EMCD-Sim\\build\\windows-rc\\venv\\Scripts\\python.exe",
  "-u",
  "-B",
  "-c",
  "import atexit,ctypes,json,os,sys\ndef report_peak():\n    class Counters(ctypes.Structure):\n        _fields_=[('cb',ctypes.c_ulong),('faults',ctypes.c_ulong)]+[(name,ctypes.c_size_t) for name in ('peak_ws','ws','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile','private')]\n    kernel=ctypes.WinDLL('kernel32',use_last_error=True)\n    kernel.GetCurrentProcess.restype=ctypes.c_void_p\n    get_memory=ctypes.WinDLL('psapi',use_last_error=True).GetProcessMemoryInfo\n    get_memory.argtypes=[ctypes.c_void_p,ctypes.POINTER(Counters),ctypes.c_ulong]\n    value=Counters();value.cb=ctypes.sizeof(value)\n    if not get_memory(kernel.GetCurrentProcess(),ctypes.byref(value),value.cb):\n        raise OSError(ctypes.get_last_error(),'Cannot measure pytest payload peak')\n    print('PHASE2_PAYLOAD_MEMORY '+json.dumps(dict(pid=os.getpid(),peak_rss_mib=value.peak_ws/2**20,peak_commit_mib=value.peak_pagefile/2**20)),flush=True)\nif os.name=='nt':atexit.register(report_peak)\nimport pytest\nraise SystemExit(pytest.main(sys.argv[1:]))\n",
  "-v",
  "--tb=long",
  "-ra",
  "--durations=30",
  "-o",
  "faulthandler_timeout=600",
  "--basetemp=C:\\Users\\peng863\\EMCD-Sim\\build\\nc-tmp\\fm-42bb9b0e",
  "-p",
  "no:cacheprovider",
  "--junitxml=C:\\Users\\peng863\\EMCD-Sim\\.worktrees\\windows-adaptive-compute\\build\\phase3-final-merge\\full-regression.xml"
]
```

The complete environment, timestamps, ownership, command origin and candidate
identity are also retained in `full-regression-run.json`; `candidate.json`
records the Git file objects, versions, native runtime and source registration.

### Existing skip reasons

The **exact 62 node IDs and their exact reason strings match the prior Phase
3F-1 skip inventory**. No changed reason was accepted by count alone. The full
node list is `skip-inventory.json`; all reason counts are listed here:

| Existing reason | Cases |
|---|---:|
| Optional stored GUI reference | 1 |
| Saved project fixture unavailable | 3 |
| Full benchmark outputs are not complete | 3 |
| Optional saved angular references unavailable | 6 |
| Full checkpointed thickness calculation still incomplete | 3 |
| Explicit native Windows check | 2 |
| Local legacy reference project unavailable | 1 |
| Saved BW/MS fixture not available; never run a fallback simulation | 1 |
| Optional GUI and existing real Stage D results required | 8 |
| Set EMCD_SIM_LEGACY_ATOMIC_TABLE to the reviewed external table | 13 |
| Optional saved benchmark unavailable | 1 |
| Explicit native Windows GUI check | 3 |
| Explicit native Windows selection/export check | 1 |
| Explicit native Windows result selection check | 1 |
| Requires original local WIEN2k audit companions; not distributed | 1 |
| Optional local WIEN2k companion audit; original files are not distributed with the package | 1 |
| Local four-point benchmark not generated | 2 |
| Local MS validation outputs not generated | 3 |
| Optional saved result fixture unavailable | 1 |
| Optional real saved Ni project unavailable | 1 |
| Explicit native Windows project workflow | 1 |
| Optional genuine historical Ni project unavailable | 1 |
| Optional saved GUI reference unavailable | 1 |
| Pinned offline HDF5 inputs unavailable | 1 |
| Optional external 160-array evidence unavailable; set EMCD_UNIT_IDENTITY_DIRECTORY | 1 |
| Optional historical saved project is unavailable | 1 |

These unavailable optional/native/external cases are not represented as
passing. Native workflows retain their separate Phase 3F-2 evidence.
Warnings remain visible in the full log; observed categories include Qt and
dependency deprecations, offscreen layout warnings, and the intentional
extreme-value rejection test. No warning filter was added for this task.

## D. Scientific preservation and native applicability

Before the full run, **61/61 preflight tests passed in 312.27 s**, including:
canonical GUI/root callable identity; all eight strict-headless Ni/Cr × BW/FFT
× Single/Double calculations; the six corrected numerical comparisons;
material-independent input/resource controls; cancellation and BLAS restoration;
current/historical source guards; scientific invariants; and the affected
persistence/result-control cases. This preflight is distinct from the clean
full result and is not added to its pass count.

The unchanged existing independent-source comparison passed in 36.089 owned
seconds: **22 cases / 2,294 arrays exactly equal**, including physical metadata
and edge metrics, against `cdb8836388c5ccc5ae7a614b47894c0ab158a824`.
It was not replaced by a new baseline or regenerated candidate expectation.

All six numerical-contract cases passed both preflight and the full run:

| Original contract | Full result |
|---|---|
| `test_bw_unchanged_and_depth_cancel[numerical]` | Pass |
| `test_full_spectrum_unchanged[bloch]` | Pass |
| `test_full_spectrum_unchanged[both]` | Pass |
| `test_bcc_cr_independent_events_and_symmetry[unequal-mdff-double-bloch]` | Pass |
| `test_original_ni_all_numeric_arrays_exact[double-xmcd]` | Pass |
| `test_original_ni_all_numeric_arrays_exact[double-atomic]` | Pass |

The parent-scale floating-point allowances and cancellation-sensitive Cr
comparisons remain exactly as previously reviewed. Exact comparisons for
serialization, shapes/dtypes, NaN masks and unchanged incoming/FFT values remain
in place. Full-run negative controls also passed. No kernel, equation, scientific
setting, tolerance, fixture source or reference array changed.

The full inventory and targeted checks preserve one authoritative
`emcd_sim.forward_pipeline.calculate` engine, explicit generic settings and
historical Ni inputs, BW/FFT Single/Double behavior, multi-site execution,
declared MDFF providers, detector integration, resources/cancellation, source
authentication and historical project interpretation.

The native application/packaging/data/source objects match frozen build source
`473ac666592e11fc962ecb64d27354ccb18d4ba0`; the existing Conditional Native GO
therefore applies to this scientific implementation. Existing native evidence
remains **19 projects / 57 NPZ files / 1,763 exact arrays**, including 448 arrays
containing NaNs, against independent Phase 2 frozen source
`6d98694b2367fdb9586f33287f9a09c159c7ef27`.

The historical raw comparison conservatively flagged inactive atomic metadata
and two path-only source-provenance differences. Its preserved
`native-reference-review.json` records the narrowly justified final PASS:
all arrays and effective physical inputs match; no numerical mismatch or
tolerance was excluded. The native package-verification record is complete.
These are existing native results, not new executions attributed to a later
merge hash. No new EXE was built or run for this task.

Physical limits remain unchanged: projected-potential/ZOLZ and declared
inelastic-response assumptions, finite numerical support and relative signal
normalization. Synthetic Cr/Fe3O4 fixtures establish software/scientific
consistency, not calibrated experimental spectra. Arbitrary depth-localized 3D
events, coherent probes, real-space STEM scans and GPU remain future work.

## E. Phase 3 integration and runtime identity

Starting `main` was an ancestor of Phase 3, so no divergent development commit
needed resolution. It did contain six modified documentation/packaging files
and 20 untracked files, including local `AGENTS.md`/`.ignore`, 14 Ni research
companions, three research scripts and one test. They were preserved in the
verified local stash:

* Object: `9191d6439615675124d944533ceb21e66c72fda3`.
* Message: `preserve/main-user-work-before-phase3-final-integration-20261121`.
* Parent: original main `28db1839417a6bdd9731c1368f8943ae3ef1d5d8`.
* All six tracked and 20 untracked paths were reconciled with the stash trees.

The stash remains available and unapplied. These unrelated files were not
silently merged into the accepted implementation or discarded. Exact path
lists and preservation checks are in `main-user-work-preserved.json`.

After strict Full Regression GO, a normal `git merge --no-ff` preserved the
entire Phase 3 history. Commit `4613685...` has original main and `a97ccf1...`
as parents; its whole tree equals the tested candidate's tree. There were no
conflicts, automatic side-selection or manual resolutions.

On merged main, **14/14 targeted tests passed in 171.36 s**: canonical API,
strict-headless Ni/Cr calculations, four foundation invariants, project history
and resave, both disjoint-group callback cases, GUI result switching, and the
existing current/historical/kernel guards. Package discovery found precisely
`emcd_sim` and `emcd_sim.gui`; all three console targets imported as callables.
The source is loaded from main's `src`, not accidentally from another worktree.
Accepted version remains `0.9.0b2` (display `v0.9.0-beta.2`).

The stale starting local main carried `0.8.1b2`; integrating the already
committed Phase 3 history brings its existing `0.9.0b2` metadata into local
main. The unchanged existing `origin/main` reference already carries
`0.9.0b2`. This task authored no further version bump, changed no remote
reference and did not replace the installed Research Beta.

An additional task-level exact *raw* runtime-hash comparison initially failed
for six files. Investigation established only LF/CRLF checkout differences in
`forward_pipeline.py`, `gui/geometry.py`, `propagation.py`, `channeling.py`,
`gui/result_export.py` and `multisite_integration.py`. Each extra byte corresponds
to a CR before LF; canonical text equals both the tested worktree and committed
Git blob. `structure_geometry.py` was already CRLF in both worktrees.

`checkout-line-ending-review.json` retains the original comparison outcome,
raw sizes/CRLF counts and exact canonical comparison. The existing source
guards already use this documented UTF-8/BOM/CRLF convention and passed on
main. No existing safeguard was relaxed, no source was rewritten to force
matching hashes, and raw runtime stamps were not falsely reported as equal.
The new runtime Git commit, existing canonical implementation identity and
raw checkout inventory are recorded separately in `post-phase3-interfaces.json`.

The complete regression was not repeated: committed application/test/packaging/
data trees did not change, and the root checkout's canonical sources and
required post-merge behavior checks passed. Future builds from the same Git
source still identify their actual build commit and inventory; historical
build provenance remains `473ac66`, not the merge or report commit.

## F. Separate Next-Gen A integration

The audited delta from `a97ccf1` to `eb67c17` contains only:

* `docs/NEXTGEN_A_ARCHITECTURE_READINESS.md`
* `docs/NEXTGEN_A_DEPTH_STEM_PHYSICS_DESIGN.md`
* `docs/NEXTGEN_A_PERFORMANCE_BASELINE.md`
* `docs/NEXTGEN_A_IMPLEMENTATION_ROADMAP.md`
* `scripts/benchmark_nextgen_readiness.py`
* `scripts/summarize_nextgen_readiness.py`

A separate normal `--no-ff` merge produced `ff64d739...`, preserving all four
Next-Gen A commits. Its whole tree equals the reviewed Next-Gen A branch tree;
application/test/packaging/data/dependency objects remain the Phase 3 candidate's.

After integration, **3/3 canonical API and source-authentication tests passed in
30.28 s**. Both benchmark scripts passed syntax and import checks, all 29 case
definitions and 18 arithmetic memory scenarios checked, and all 14 local
Markdown links resolved. The benchmark driver's Git object equals measured
tooling `70af53c`; the summary script equals the reviewed `eb67c17` object.

The original 29-case measurements, exact input/environment records, repeated
output fingerprints, CSV/JSON and plots remain under
`C:/Users/peng863/EMCD-Sim/.worktrees/nextgen-a/build/nextgen-a/measured/`.
They were inspected without rerunning calculations or regenerating performance
evidence. Their output fingerprints remain performance observations, not new
scientific reference arrays. No Next-Gen B1 implementation was integrated.

## G. Evidence and remaining boundaries

Acceptance evidence root:

`C:/Users/peng863/EMCD-Sim/.worktrees/windows-adaptive-compute/build/phase3-final-merge/`

| Evidence | Purpose |
|---|---|
| `git-audit.json`, `candidate.json` | Starting graph, clean test candidate, tree/file objects, source registration, versions and native configuration |
| `collection-nodes.txt`, `inventory-delta.json` | Complete inventory and exact three-node addition |
| `preflight.log/.xml`, `preflight-run.json` | 61 essential controls and owned process record |
| `exact.log`, `exact-run.json` | Existing 22-case / 2,294-array exact comparison |
| `full-regression.log/.xml`, `full-regression-run.json`, `full-regression-lifecycle.jsonl` | Complete run, exact argv/environment, memory, lifecycle and cleanup |
| `regression-summary.json`, `skip-inventory.json` | XML/order reconciliation, six contracts, added cases and exact 62-node/reason match |
| `main-user-work-preserved.json` | Named-stash identity and preserved paths |
| `phase3-integration.json`, `nextgen-integration.json` | Both merge commits and exact tree comparisons |
| `post-phase3.log/.xml`, `post-nextgen.log/.xml`, corresponding `-run.json` | 14 + 3 passing post-merge controls |
| `checkout-line-ending-review.json`, `post-phase3-interfaces.json` | Raw/canonical runtime identity distinction, imports, packages and version |
| `final-verification.json`, `final-state.json` | Tool/link checks, final main commit, source-tree identity and clean relevant worktrees |

Native evidence remains under the sibling
`build/phase3f2/candidate-473ac66/`: `candidate.json`,
`native-reference-review.json`, `package-verification.json` and the preserved
native artifacts/workflows described in
[Phase 3F-2](PHASE3F2_WINDOWS_NATIVE_ACCEPTANCE.md).

This task grants local scientific-development acceptance. Clean-machine
installation, unrestricted native combinations, absolute experimental
calibration, optional unavailable evidence, security/release review and public
publishing remain separate. The installed Research Beta and release artifacts
were not replaced. No public release is authorized or implied.

## H. Final baseline and Git state

The report commit's exact main HEAD, integration commits and tree objects are
recorded after commit in `final-state.json`. The final Git check verifies:
main clean; Phase 3 still `a97ccf1` and clean; Next-Gen A still `eb67c17` and
clean; preserved stash retained; remote-tracking references unchanged. Other
historical worktrees were not modified or subjected to cleanup.

No Git history was rewritten; no force-update, reset, squash, push, tag,
publication, new version bump, EXE rebuild or Next-Gen B1 implementation occurred.
The only new tracked content authored during this acceptance task is this
report; prior Phase 3 and Next-Gen A commits were integrated intact.

Future B1 development can branch from the exact final main commit recorded in
the handoff. Treat this committed version and the existing scientific safeguards
as the reference. New physical models require explicit identifiers and
independent validation; they must not silently alter current BW/FFT,
Single/Double, explicit Ni, multisite, provenance or historical project contracts.
Numerical equality with an older approximation is required only for genuinely
matched limiting cases. No new blanket hash layer or replacement numerical
baseline is introduced by this freeze.
