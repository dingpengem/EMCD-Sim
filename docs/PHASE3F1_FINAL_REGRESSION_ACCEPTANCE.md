# Phase 3F-1: final source audit and regression acceptance

## A. Executive summary

**Conditional integration handoff to Phase 3F-2 native development validation.**
Clean full-regression GO and release GO are **not established**.

| Identity | Value |
|---|---|
| Starting HEAD and clean full-run candidate | `faee4861819c86aea45b6c00c34f7e04a98a6b1d` |
| Verified Phase 3E-2 application implementation | `20009f4ac138731e04b1a479acc6b76ce5a5717b` |
| Corrected candidate | `ce7677ed9cec6ba9e53b24fe6c592aafe64bf004` |
| Branch | `refactor/physics-readability` |
| Absolute working directory and worktree root | `C:/Users/peng863/EMCD-Sim/.worktrees/windows-adaptive-compute` |

The complete intended inventory ran **once**: 1,821 cases, **1,757 passed,
two failed, zero errors, 62 skipped**, in 12,873.90 pytest seconds (3h 34m).
Both failures were stale fixture inputs after neutral settings stopped
inheriting Ni detector defaults. Both reproduced fresh before correction.
Their original detector centers/radius were made explicit, with every assertion
preserved. No production implementation, scientific setting in production,
kernel, reference array, tolerance, resource policy or GUI workflow was changed.

Targeted recovery passed 40 cases; seven existing registration controls also
passed. Reconciliation covers **1,759 distinct passes and 62 existing skips**
across the same 1,821 cases. Neither failed node was omitted or skipped.
All application/build/script source objects are identical between the full-run
and corrected candidates. No scientific or application defect remains
demonstrated by this evidence. The corrected tests have not passed a new single
complete invocation; none was launched.

The remaining acceptance boundaries are strict clean-full-suite acceptance,
unavailable optional evidence, and native/frozen Windows validation. Phase 3F-2
is not performed here.

## B. Final source audit

The current ownership maps, Phase 3C/3D/3E reports, regression recovery report,
numerical-contract investigation and approved corrections were reviewed with
the actual source. Historical reports describe their recorded revisions;
the current source is authoritative.

* `emcd_sim.forward_pipeline.calculate` is the sole production forward entry.
  `emcd_sim.gui.forward_pipeline.calculate` directly re-exports the identical
  callable/signature. Uniform and grouped schedules remain distinct internal
  operations; BW/FFT and Single/Double retain their different numerical methods.
  Independent historical/reference calculations remain validation oracles.
* `ForwardSettings` is the neutral base of general imported/provider/multisite
  records. `NiForwardSettings` is an explicit preset. Arbitrary structures keep
  neutral provenance; missing sources, sites and detector inputs do not select
  Ni assumptions. Historical Ni interpretation remains in explicit presets and
  the existing loading/schema layer. Negative input and old-project tests pass.
* The engine's literal dependency closure reaches only the state-free
  `gui.memory_budget` adapter within the GUI namespace. Its four authenticated
  numerical consumers import the same root `reserve_memory` function. The eight
  strict-headless children also verify actual execution without presentation
  imports. No protected kernel import was edited to remove this exception.
* `memory_budget` owns one reservation dictionary and its reentrant lock.
  `parallel_resources` owns the separate BLAS control lock and worker policy.
  Admission, reservation release, cancellation and serial/parallel consistency
  checks pass; no second resource manager exists.
* Existing current/historical source authentication, runtime implementation
  inventories, offline/no-process safeguards and original kernel/data pins pass.
  The 173-entry current registry retains its original membership. Only the two
  already-protected test identities and required loader checksum were updated.
  Historical archives and `production_source` remain unchanged; the latter
  still identifies application implementation `20009f4...`.

No package reorganization, facade, alias, new registration framework, scientific
fallback or additional physical capability was introduced. The supported
provider helper calls remain unchanged. Full collection, console/public-import
tests and packaging hidden-import checks establish maintained import coverage.

The established AST/token audit ran once in `source-audit`. After recovery,
Git tree-object equality verifies that `src`, `packaging` and `scripts` remain
identical to the audited full-run candidate. Consequently its production
measurements also describe the corrected candidate without repeating the audit.

| Metric | Phase 3E-2 | Final candidate | Change |
|---|---:|---:|---:|
| Production Python files | 111 | 111 | 0 / 0.00% |
| GUI Python files | 53 | 53 | 0 / 0.00% |
| Non-GUI Python files | 58 | 58 | 0 / 0.00% |
| Physical production lines | 19,600 | 19,600 | 0 / 0.00% |
| Nonblank/noncomment lines including docstrings | 17,505 | 17,505 | 0 / 0.00% |
| Production source LOC excluding docstrings | 16,538 | 16,538 | 0 / 0.00% |
| GUI source LOC | 10,708 | 10,708 | 0 / 0.00% |
| Internal import edges | 497 | 497 | 0 / 0.00% |
| Cyclic dependency groups | 4 | 4 | 0 / 0.00% |
| Modules in cycles | 13 | 13 | 0 / 0.00% |
| Largest SCC | 5 | 5 | 0 / 0.00% |
| Non-GUI to GUI edges | 5 | 5 | 0 / 0.00% |

The existing app/acceptance, provider, project-I/O and elastic-provider cycles
remain (sizes 5, 3, 3 and 2). The five reverse edges are the application launcher
and four authenticated memory-adapter imports. No new cycle is introduced and
no further architectural simplification is claimed.

## C. Regression results and intended inventory

The clean candidate was frozen after 50 preflight passes and the exact
scientific comparison. `candidate.json` records HEAD/tree, 428 existing Git
file-object identities, clean status, versions, BLAS details, environment,
inventory, skip policy and execution-deadline rationale.

Environment: established Windows Python 3.11.17; NumPy 2.4.6; SciPy 1.17.1;
PySide6/Qt 6.12.0; `PYTHONHASHSEED=0`; `OPENBLAS_NUM_THREADS=1`;
`OMP_NUM_THREADS=1`; `QT_QPA_PLATFORM=offscreen`; source/test `PYTHONPATH`.
The recorded NumPy runtime is OpenBLAS 0.3.31.188.0, ILP64/Haswell configuration,
with one observed thread; complete build/runtime details are in `candidate.json`.
`PYTEST_ADDOPTS` was explicitly empty, and no native opt-in environment was set.
Temporary roots use the short unique `f1-<8 hex>` basename under
`C:/Users/peng863/EMCD-Sim/build/nc-tmp`.

Collection: **1,821 cases**, no collection errors, 70.54 pytest seconds.
Full-run options were `-v --tb=long -ra --durations=30
-o faulthandler_timeout=600`, plus the recorded short basetemp, existing
no-cache setting and JUnit output. No selection, `-x`, maximum-failure option,
new skip/xfail or reduced numerical dimensions were used. The eight-hour
execution bound exceeds historical complete-run times of 4,311.19, 10,985.88
and 19,907.56 seconds. The run completed normally inside that bound.

| Outcome | Complete run | Targeted corrective verification | Final combined distinct coverage |
|---|---:|---:|---:|
| Collected/represented | 1,821 | 47 | 1,821 |
| Passed | 1,757 | 47 | 1,759 |
| Failed | 2 | 0 | 0 |
| Errors | 0 | 0 | 0 |
| Skipped | 62 | 0 | 62 |
| Pytest duration | 12,873.90 s | 122.14 s | Multiple invocations |

Corrective verification is 40 affected/relevant cases (13.06 s) plus seven
registration controls (109.08 s). Every selected identity already belongs to
the full inventory. Their 45 previously passing cases are not added again.
Preflight, the two-case failing reproduction and script-based mutation probes
are separate evidence, not extra distinct passes. Full launcher duration is
12,887.766 s; recovery and registration launcher durations are 15.344 and
112.125 s. The 1,179 full-run warnings remain in the raw log: Qt/dependency
deprecations, offscreen constrained-layout warnings and an overflow warning
from the intentional extreme-value rejection test are observed examples.

Full XML identities equal the collected inventory, and the recorded execution
order matches collection. All 62 skipped node IDs equal the earlier 1,768-case
inventory's skipped set; no skip condition was added or changed.

| Existing skipped evidence | Cases |
|---|---:|
| Explicit native Windows workflows | 8 |
| Reviewed external legacy atomic table unavailable | 13 |
| Undistributed local WIEN2k audit companions | 2 |
| Pinned offline HDF5 input unavailable | 1 |
| Optional external 160-array unit evidence unavailable | 1 |
| Other optional stored/local GUI, project, angular, benchmark and opt-in evidence | 37 |
| Total | 62 |

Each exact node/reason is retained in `skip-inventory.json`. Missing stored
fixtures were not regenerated or replaced by fallback simulations. These
cases were not executed and are not represented as passing native or
independent historical evidence.

Changes since the original 1,768-case inventory are **60 new node IDs and seven
retired IDs**, net **+53 (+3.00%)**. All seven retired IDs have exact current
counterparts after source-owner path changes; no logical scientific case was
deleted. The complete IDs and seven mappings are recorded in
`inventory-delta.json` and `coverage-summary.json`.

| Test module | New IDs | Retired IDs | Net |
|---|---:|---:|---:|
| `test_calculation_api` | 1 | 0 | +1 |
| `test_headless_calculation` | 8 | 0 | +8 |
| `test_headless_settings_resources` | 3 | 0 | +3 |
| `test_material_independent_inputs` | 11 | 0 | +11 |
| `test_mdff_usability_source_scope` | 18 | 3 | +15 |
| `test_multisite_configuration` | 4 | 0 | +4 |
| `test_multisite_result_persistence` | 7 | 0 | +7 |
| `test_unified_mdff_providers` | 4 | 0 | +4 |
| `test_unit_labels` | 4 | 4 | 0 |
| Total | 60 | 7 | +53 |

Phase 3F-1 itself adds/removes no test identity. Its only test changes are the
explicit fixture inputs described below.

## D. Failure investigation and correction

Both original failures are **category A: historical fixture expectations**,
with one common root cause. They fail independently in a fresh two-case run
(two failures, 6.39 pytest seconds / 8.390 owned seconds); neither is a cascade.
Categories B through F have zero demonstrated root causes in this run.

| Original failed node | First meaningful failure | Correction and verification |
|---|---|---|
| `tests/test_part1c_provider_interface.py::test_declared_xmcd_uses_same_preparation_interface` | `provider.energy_grid()` reaches `mdff_providers.py:253`, raising `ValueError: Invalid detector/grid controls` | Declare the prior detector centers/radius in this provider fixture; whole module and exact tensor/grid/checksum assertions pass. |
| `tests/test_single_element_contracts.py::test_element_edge_checksum_and_no_ni_energy_inheritance` | `energy_grid(cfg)` reaches the same validation before its 243-point assertion | Declare the same prior inputs; whole module passes, including source-only energy calibration, checksum, rotation and malformed-input assertions. |

Actual pre-neutral-settings source
`2c78b40d78e65787876a58c32f11e6178e182e46` shows
`ImportedSettings(NiForwardSettings)` and `ProviderSettings(ImportedSettings)`.
Both fixtures therefore previously inherited centers
`((0.2837684449489217, 0.2837684449489217),
(0.2837684449489217, -0.2837684449489217))`, radius `0.0908059024`, and
halfwidth `1.0`, in cycles/angstrom. The neutral hierarchy intentionally has
empty centers and radius zero. The existing energy-planning contract validates
detector controls and correctly rejects those unconfigured requests.

Only the original centers and radius were made explicit at the two test
construction sites; halfwidth is already unchanged. These values come from
actual historical inputs, not trial-and-error replacements. AST review verifies
that removing those two added kwargs reproduces each entire original test
module AST. All 22 `assert` statements, NumPy comparisons, exception checks,
decorators and other statements remain unchanged. The common tensor helper is
still supported and requires no migration or compatibility wrapper.

Production validation was preserved. No generic Ni default, radius relaxation,
energy-planning redesign or production fix was needed. The six relevant
neutral/missing-input cases also pass. Existing reviewed identities for the two
protected tests and the loader checksum were updated; both guards reject
virtual mutations of either test, with real current/historical positives
passing before and after (38.406 s). No original archive or immutable pin changed.

`failure-inventory.json` retains every original node, source, message and full
traceback. Original full-run and reproduction XML/logs are preserved separately
from successful recovery. No second complete regression was launched.

## E. Scientific verification

| Required evidence | Result |
|---|---|
| Eight real strict-headless Ni/Cr, BW/FFT, Single/Double calculations | All pass in preflight and in the complete invocation; no Qt/presentation execution, with source/result identity and cleanup checks. |
| Six corrected numerical contracts | All pass in preflight and the complete invocation, with the existing tolerances and cancellation-sensitive Cr comparison unchanged. |
| Independent controls | Full-run event/quadrature, reversal, PSD/Hermiticity, geometry, multisite weighting/split-merge, Parseval and serial/parallel checks pass. |
| Unchanged exact comparison | 22 cases / 2,294 arrays exactly equal against `cdb8836388c5ccc5ae7a614b47894c0ab158a824`; physical metadata and edge metrics also equal; 26.469 s. |

The six contracts are numerical BW depth cancellation, Bloch/Both full-spectrum
compatibility, unequal-MDFF Cr Double Bloch symmetry, and Ni Double XMCD/Atomic
array compatibility. Original lossless serialization and persistence checks
remain exact. The unchanged exact driver separately reports its documented
older-reference Ni residuals; these are not differences against the required
pre-refactor source.

Preflight totals 50 passes (162.27 pytest seconds / 165.781 owned seconds).
The exact comparison precedes the full run and remains applicable to the final
application: every production source/data Git object is unchanged. Recovery
also executes the affected modules' historical Ni tensor, declared tensor,
interpolation, energy-calibration and source-authentication assertions.
No scientific reference, equation, evaluation order, setting in production,
roundoff allowance or test assertion was weakened or regenerated.

Unavailable optional external/unit, HDF5, benchmark and genuine private-project
evidence remains explicitly skipped. The existing physical-model limitations
remain those documented in the physics map; no new physical capability or
quantitative material validation is claimed.

## F. Memory, worker and Qt verification

| Measured pytest payload | Peak RSS MiB | Peak commit MiB |
|---|---:|---:|
| Scientific/source/resource preflight | 150.402 | 157.480 |
| Complete regression (PID 12068) | 840.055 | 1,033.371 |
| Affected/relevant recovery | 99.684 | 109.898 |

These are actual payload measurements, not the approximately 4 MiB Windows
venv launcher. Aggregate peak memory across all child processes was not
measured. Commands/probes and observations are retained in run records/logs.

No unintended admission cascade, reservation-release failure, worker-count
defect or cancellation failure was observed. Full resource, execution-control,
memory-budget and serial/parallel tests pass. Budgets, thresholds, scheduling
and cancellation code are unchanged. Strict-headless children check restored
thread/child state and empty reservations; the existing GUI teardown safeguard
rejects destruction of a test-owned window with an active calculation.

The full lifecycle log contains 1,801 current-format records, all reporting zero
remaining MainWindows and top-level widgets. Five supplemental older-format
records also report zero MainWindows but do not record all top-level widgets;
that missing observation is not treated as a zero. The final current-format
record reports zero for both. Records are observations, not additional distinct
test cases. Completed full-run launcher/payload and recovery process IDs were
checked absent; no unrelated process was terminated.

## G. GUI and project integration

| Supported workflow exercised | Passing evidence |
|---|---|
| Startup, CIF/structure, Material, Numerical Settings | Application-stage, Fe CIF, crystallography, material and solver-settings tests |
| Compute Resources, submission, worker status/cancel | Compute-resource/execution, parallel-policy, cancellation-profile and GUI run tests |
| Global Apply/Cancel; Local Done/Apply; Manual/Atomic/XMCD; site groups | Material/local workflows, Atomic editor, group-direction/control and unified-provider GUI tests |
| New/Save/Open/Save As; historical and portable sources; drafts; original/effective paths | Project workflow, run-selection restoration, multisite configuration/persistence and source-tamper tests |
| BW/FFT Single/Double; Ni and explicit non-Ni/multisite inputs | Headless, generalized orientation, AFM GUI/API, declared-source and scientific invariant tests |
| Raw/relative and magnetic/nonmagnetic views; energy/maps; exact arrays; selection/export | Component display, multisite/total selection, presentation, responsive and export tests |

These results are source/offscreen integration evidence. The exact optional
native/private-fixture cases in `skip-inventory.json` were not executed.
Native menus/dialogs, DPI/desktop appearance and the frozen application's
startup/export behavior remain Phase 3F-2 work. Offscreen layout warnings do not
certify native visual correctness. Current GUI defaults and native QA commands
were preserved; no profile mismatch was hidden by changing defaults.

## H. Git identity and retained evidence

Correction commit: `ce7677ed9cec6ba9e53b24fe6c592aafe64bf004`, containing two
fixture-input corrections and their existing registration updates. No
application implementation commit is required. A documentation-only successor
adds this report; it changes no tested application/test/build file. The final
worktree is checked clean on the original branch, without a reset or new
worktree. Nothing is pushed, merged, tagged, published, version-bumped, built
into an EXE or installed over the Research Beta.

The full result belongs to clean `faee486...`; recovery used the reviewed
working bytes subsequently committed as `ce7677e...`, with exact dirty paths
recorded. The original candidate was not modified during the full invocation.
The corrected candidate has combined coverage, not a clean full invocation.

Evidence is under `build/phase3f1/`:

* `candidate.json`, `collection-nodes.txt`, `inventory-delta.json`, `after.json`
  and `source-audit.log`: frozen identities, versions, inventory and audit.
* `preflight.*`, `exact.*`, `collection.*`, `full-regression.*` and their
  `-run.json` files: exact emitted argv, environments, source/status, owned PID,
  timing, complete logs and XML where applicable.
* `failure-inventory.json`, `failures-reproduced.*`, `targeted-recovery.*`,
  `registration-controls.*`, `reviewed-test-mutations.*`: original failures,
  fresh reproduction and successful corrective verification.
* `skip-inventory.json`, `coverage-summary.json` and lifecycle JSONL: all skip
  reasons, distinct-case reconciliation, source-tree equality and cleanup.

Existing source authentication is preserved; these task records do not create
a new runtime hash layer, frozen scientific baseline or acceptance framework.

## I. Phase 3F-2 handoff

The exact corrected source candidate is
**`ce7677ed9cec6ba9e53b24fe6c592aafe64bf004`**. Its application, packaging and
script trees are identical to the full-run candidate; only the reviewed tests
and required current registration differ. Preserve the documentation-only
successor, and record the actual commit used for any future build.

There are no unresolved reproduced scientific, application, memory, cancellation
or authentication defects. Conditional handoff supports **native development
validation**. Strict clean-full-regression acceptance remains unestablished:
a separately authorized complete run of the corrected candidate would be
needed to establish that result. It was not automatically repeated here.

Phase 3F-2 must independently verify a clean Windows build and frozen
package/source identity; startup and exact CLI/QA dispatch; native menus and
dialogs; DPI/responsive layout and wheel behavior; explicit Ni/non-Ni,
Global/Local MDFF and multisite calculations; Save/Open/restoration and original
source identity; result selection and CSV/NPZ/figure export; Compute Resources,
admission and cancellation; and actual packaged source/Qt licenses and release
inventories. Recheck current QA fixture/profile assumptions explicitly. Supply
real missing optional evidence if its claims are required; do not fabricate it.

No packaged/native acceptance campaign or Windows EXE build is started in
Phase 3F-1. This conditional handoff is not release GO.
