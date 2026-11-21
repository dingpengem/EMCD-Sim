# Windows SC/DC resource benchmark — 11 November 2026

**PASS: all 16 complete, fresh-process calculations and their result round trips.**
For this representative Windows source/API Ni request, sampled Single Channeling (SC) memory was
lower than Double Channeling (DC). The previously higher SC *estimate* included
a full-map beam-pair workspace that the production adapter never allocates.
The correction changes admission accounting, not scientific sampling or physics.

See the [matched Windows/macOS comparison](#matched-windowsmacos-full-workload-comparison)
for the separate analysis of the completed published-app macOS dataset.

This is a Windows source/API benchmark using the production calculation entry
point and existing Windows build environment. It is not a new packaged-GUI,
clean-PC, full-regression, convergence or release-acceptance campaign. The
complete specified 243-energy workload ran; no smaller substitute was used.

## Revisions and environment

- Original accepted/benchmark source: `527a29063c0f2d76c67fba7117303bcd7f16e7f4`.
- Corrected calculation source: `9d6b7fbb6f824e275cf3c266c0ab22f562ee72af`.
  Subsequent report-only commits do not change that implementation.
- Branch: `feat/windows-adaptive-compute`. Public releases and existing Windows
  and macOS binaries were not changed or rebuilt.
- Windows 11 x64, build 26200; Python reports
  `Windows-10-10.0.26200-SP0`. Python 3.11.17, NumPy 2.4.6, SciPy 1.17.1.
- Intel Core i7-1365U: 10 physical cores, 12 available logical processors;
  hybrid topology detected, no process-affinity restriction. Cores were not
  pinned and other user applications were left running.
- 32,768 MiB installed RAM, 32,336 MiB usable. Available RAM at the recorded
  initial snapshots ranged from 15,442 to 16,114 MiB.
- NumPy OpenBLAS 0.3.31.188.0, ILP64; SciPy OpenBLAS 0.3.30. Both loaded
  runtimes reported 12 threads before and after each calculation, and **1
  during every calculation** through the existing scoped guard. No BLAS
  environment-variable workaround was used.

## Exact scientific request

Configuration was loaded, without result arrays, from the separate project
created through the accepted Windows Ni Quick Start GUI. Each new process
changed only propagation/channeling and resource controls.

| Input | Value |
| --- | --- |
| Structure | FCC Ni, a=3.520 Å; four original atoms at (0,0,0), (0,½,½), (½,0,½), (½,½,0); full occupancy |
| Magnetic configuration | Global M=(0,0,+1); local groups inactive |
| MDFF | Declared XMCD-constrained `Ni_fm.xmcd`; eta=beta=1; relative reference 1; existing source-max nonmagnetic normalization and explicit axisymmetric reversal assumption |
| Scientific status | `physical_source_unvalidated`; effective model, not calibrated Ni spectroscopy |
| Source/features | Unmodified bundled five-column source; L3=831.271 eV, L2=848.698 eV |
| Microscope/sample | 200 kV; 10 nm; B=0; Adaptive Dirac–Padé 2026 elastic provider |
| Geometry | [017]/(200), full finite ZOLZ, tilt (−7.124812628,0) mrad; systematic-row approximation off |
| Reciprocal support | Beam/MDFF cutoff 2.5 Å⁻¹; potential cutoff 2.0 Å⁻¹; 21 incident beams |
| Energies | 241 uniform points over 823.625–882.521 eV plus exact L3/L2: **243 actual samples** |
| Angular evaluation | Two full 97×97 maps at L3/L2; 162 fractional-detector-support pixels at each of the other 241 energies |
| Momentum grid | Halfwidth 1 Å⁻¹; qx/qy spacing 1/48 Å⁻¹ |
| Depth/apertures | 64 depth nodes; 64 boundary subpixels per direction |
| Detectors | Thales A=(0.2840909090909091,+0.2840909090909091), B=(0.2840909090909091,−0.2840909090909091) Å⁻¹; radius 0.09 Å⁻¹ |
| MS settings | Supported 32×32 FFT grid; requested maximum step 2 nm, retained from the saved configuration; effective step 10/63=0.1587301587 nm, one substep per depth interval, 63 incoming propagation steps |
| DC outgoing energy | 200000−E_loss eV at every actual energy; no frozen-energy or SC fallback |

MS uses the existing 64-node quadrature and outgoing backward propagation;
the full-thickness traversal also spans 63 intervals. These FFT/slice settings
are a functional benchmark, not evidence of convergence. The existing warning
about a requested step above the 0.04 nm advisory reference remains applicable.
The 2.0 Å⁻¹ potential cutoff retains no off-row potential harmonics (first
approximately 2.029 Å⁻¹). Full finite ZOLZ is still the selected basis mode.

## Measurement boundaries and limitations

Each case used a new Python process. Source/provider loading and the initial
resource preview preceded the calculation. The timed interval includes final
Run admission, scoped BLAS control, validation, propagation, contractions and
result construction. It excludes process startup, GUI rendering, saving and
reloading. No Qt canvases were created, so these RSS figures are **not total
packaged-GUI RAM requirements**.

A task-local thread called Windows `GetProcessMemoryInfo`, including native
NumPy/SciPy allocations, with a 20 ms target interval. Runs collected 50–10,161
readings; the largest observed interval was 74.2 ms. Sampling can miss shorter
peaks. The sampler stopped and joined before Save/Open. Reported incremental
RSS is sampled calculation peak minus the immediate pre-calculation RSS.
Lifetime working-set high-water marks were read before and after calculation;
they may include a larger *earlier import/preflight* peak and cannot be called
the calculation's peak. No working-set trimming or artificial baseline padding
was performed.

For MS DC with four workers, the counter advanced to 156.38 MiB, establishing
a slightly higher interval peak than the 156.17 MiB sampled maximum. Auto MS
DC advanced to 162.26 MiB. For the other runs the earlier import/preflight HWM
remained larger, so the native cumulative counter cannot isolate their exact
calculation peak.

The Manual comparisons all used **8192 MiB**, never automatically raised.
Memory budget is an admission ceiling, not consumption. SC supports one outer
worker; Manual 2/4 is not a supported SC executor configuration and was not
misrepresented as parallel work. DC was measured at Manual 1/2/4. Optional
6/8-worker sweeps were omitted after four workers failed to improve on two.
Auto was measured separately for all four backends.

**Estimate scope matters:** the legacy DC `metadata.memory_admission` records
the retained-result reservation; worker scratch has separate concurrent
reservations. It is not the whole-calculation estimate. SC reserves its whole
working bound, so its field has a different scope. The Run† entries below
reconstruct the DC whole-process estimate using the saved full working bound
and actual RSS at the immediately following retained-array reservation:

`RSS_at_reservation + 128 MiB + 1.25 × whole_calculation_working_bound`.

These are explicitly reconstructed estimates, not directly captured earlier
planner-time RSS snapshots. The Preview values were recorded directly. The
reservation-only DC figures, around 252 MiB for BW and 270 MiB for MS, must not
be substituted for the whole-process estimate. Exact planner-time DC snapshot
capture remains **INCOMPLETE**; no expensive calculation was repeated merely
to relabel this existing evidence.

## Complete run inventory

All memory values are MiB; times are seconds. `I` means initial source,
`C` corrected SC, `R` fresh serial control, `W` worker scaling, `A` Auto.
Initial runs used 527a290; all remaining rows used 9d6b7fb. Run† has the scope
described above. All rows include a completed Save/Open check.

| Backend / case | Workers | Budget | Preview → Run estimate | Sampled peak RSS | Calculation time | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BW SC / I | 1 | 8192 | 586.54 → 587.00 | 121.02 | 6.238 | PASS |
| BW DC / I | 1 | 8192 | 265.34 → 265.77† | 124.28 | 76.523 | PASS |
| MS SC / I | 1 | 8192 | 588.85 → 589.62 | 122.08 | 4.386 | PASS |
| MS DC / I | 1 | 8192 | 295.96 → 296.41† | 141.99 | 332.937 | PASS |
| BW SC / C | 1 | 8192 | 249.88 → 250.08 | 121.15 | 1.724 | PASS |
| MS SC / C | 1 | 8192 | 251.51 → 252.27 | 121.66 | 1.580 | PASS |
| BW DC / W | 2 | 8192 | 278.86 → 279.26† | 125.37 | 24.916 | PASS |
| BW DC / W | 4 | 8192 | 306.63 → 306.92† | 130.52 | 34.095 | PASS |
| BW DC / R | 1 | 8192 | 265.43 → 265.93† | 123.44 | 25.131 | PASS |
| MS DC / W | 2 | 8192 | 320.36 → 320.68† | 145.97 | 136.062 | PASS |
| MS DC / W | 4 | 8192 | 369.05 → 369.65† | 156.17 | 140.395 | PASS |
| MS DC / R | 1 | 8192 | 296.10 → 296.78† | 142.14 | 252.754 | PASS |
| BW SC / A | 1 | 6871 | 249.95 → 250.14 | 120.74 | 2.395 | PASS |
| MS SC / A | 1 | 6858 | 251.96 → 252.66 | 121.67 | 2.104 | PASS |
| BW DC / A | 5 | 6870 | 319.80 → 320.35† | 132.74 | 35.398 | PASS |
| MS DC / A | 5 | 6813 | 393.00 → 393.84† | 162.26 | 152.668 | PASS |

### RSS baseline, increment and lifetime high-water mark

| Case | RSS before | Sampled peak | Increment | Lifetime HWM before → after |
| --- | ---: | ---: | ---: | ---: |
| BW SC / I | 116.97 | 121.02 | 4.05 | 148.04 → 148.04 |
| BW DC / I | 117.18 | 124.28 | 7.11 | 147.97 → 147.97 |
| MS SC / I | 117.29 | 122.08 | 4.79 | 148.38 → 148.38 |
| MS DC / I | 117.25 | 141.99 | 24.73 | 149.70 → 149.70 |
| BW SC / C | 117.19 | 121.15 | 3.96 | 148.84 → 148.84 |
| MS SC / C | 117.12 | 121.66 | 4.54 | 147.85 → 147.85 |
| BW DC / W2 | 117.03 | 125.37 | 8.34 | 147.84 → 147.84 |
| BW DC / W4 | 117.47 | 130.52 | 13.05 | 147.57 → 147.57 |
| BW DC / R | 117.26 | 123.44 | 6.18 | 149.69 → 149.69 |
| MS DC / W2 | 117.33 | 145.97 | 28.64 | 147.54 → 147.54 |
| MS DC / W4 | 117.85 | 156.17 | 38.32 | 148.22 → 156.38 |
| MS DC / R | 117.69 | 142.14 | 24.45 | 147.79 → 147.79 |
| BW SC / A | 117.26 | 120.74 | 3.48 | 147.63 → 147.63 |
| MS SC / A | 117.44 | 121.67 | 4.23 | 149.68 → 149.68 |
| BW DC / A | 116.98 | 132.74 | 15.76 | 149.85 → 149.85 |
| MS DC / A | 117.42 | 162.26 | 44.84 | 148.99 → 162.26 |

Using corrected SC and the fresh one-worker DC controls, SC/DC sampled total
RSS ratios are **0.981 BW** and **0.856 MS**. Incremental ratios are **0.642 BW**
and **0.186 MS**. Full-process estimates exceed sampled peaks by about 129,
142, 131 and 155 MiB respectively for BW SC, BW DC, MS SC and MS DC. The
128 MiB reserve explains most of this difference; allocation bounds and the
25% margin add further conservatism. Estimates are not precise RSS forecasts.
Unchanged earlier lifetime HWMs bound possible missed peaks but do not prove
a strict ordering of instantaneous peaks between modes.

## Allocation audit and correction

The [shared planner](../src/emcd_sim/gui/propagation.py) and
[production adapter](../src/emcd_sim/gui/channeling.py) were compared with the
existing SC, BW DC and MS DC allocation schedules.

- **BW SC:** incoming beam/depth amplitudes and coherence are shared. Source
  tensors cover all energies, but tensor contraction scratch covers only 64
  query pixels at once. The old bound charged four complex full-map P×N×N
  buffers and full-map P×N coordinate scratch. At P=9409 and N=21, the dense
  term was 253.257 MiB, although the live batch bound is 1.723 MiB. The
  corresponding coordinate allowance also needed the batch size. Selected
  fields, detector weights/coordinates and spectra remain charged separately.
- **MS SC:** the same bounded contraction follows incoming FFT propagation;
  retained incoming FFT/depth fields and propagation buffers are additional.
  The correction does not remove these or alter the FFT mesh/steps.
- **BW DC:** complete-crystal incoming preparation is shared, outgoing
  preparation is reused within each energy, and bounded numerical site/depth
  contractions feed per-pixel Cartesian responses. Worker scratch scales with
  actual worker count. The active numerical path does not allocate an analytic
  N⁴ mode-integral array. The existing solver-specific bound was preserved.
- **MS DC:** the complete potential/grid/incoming fields are shared; detector
  batches have at most 32 pixels and reuse incoming preparation. Outgoing FFT
  fields, Cartesian kernels and depth accumulation are worker-local. Returned
  responses are retained for the current query; full fields are retained only
  at the two selections, not at all 243 energies. The existing conservative
  MS buffer/result allowances were retained; they are not an exact live-array
  census and may overestimate, including the generic P×N retention allowance.

The focused fix shares the unchanged **64-pixel SC constant** between planner
and Global adapter, replacing the erroneous full-map scratch charge. It does
not change batching, result retention, tensor equations, contraction order,
normalization, source amplitude, propagation, tolerances or reference arrays.
No estimator was forced to report DC>SC. No scheduler defect was established
merely because additional threads were slower.

Four directly affected checks pass: BW/MS representative SC admission, a
genuine large-basis low-budget rejection, and GUI preview/Run allocation
binding. The large-basis resource test now rejects a genuinely insufficient
224 MiB budget instead of relying on the obsolete full-map scratch assumption;
legacy 512 MiB support remains. The initial targeted run had two new-test
KeyErrors from treating the optional success-path `rejected` flag as required;
those two assertions were corrected and only those checks repeated. No
scientific assertion, numerical reference, source pin or skip was changed.

## CPU scaling and timing interpretation

Two additional serial controls were justified because the initial BW ratio
appeared superlinear and serial timing varied substantially. Initial results
remain in the inventory. The corrected SC timings are **not** evidence of an
algorithmic speed improvement: only accounting and a constant alias changed.

| Solver, DC | Workers | Time | Ratio vs fresh serial control | Maximum overlapping tasks | Process CPU seconds / wall seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| BW | 1 | 25.131 | 1.00× | 1 | 0.98 |
| BW | 2 | 24.916 | 1.01× | 2 | 1.36 |
| BW | 4 | 34.095 | 0.74× | 4 | 1.61 |
| BW Auto | 5 | 35.398 | 0.71× | 5 | 1.55 |
| MS | 1 | 252.754 | 1.00× | 1 | 0.98 |
| MS | 2 | 136.062 | 1.86× | 2 | 1.60 |
| MS | 4 | 140.395 | 1.80× | 4 | 2.31 |
| MS Auto | 5 | 152.668 | 1.66× | 5 | 2.79 |

CPU/wall is an average number of busy cores, not total-machine Task Manager
percentage. More overlap or CPU consumption did not imply lower elapsed time.
The initial BW/DC serial time was 76.523 s versus 25.131 s in its control;
MS/DC was 332.937 versus 252.754 s. These are observations on an unpinned,
hybrid, shared-use laptop, not statistical confidence intervals or portable
speedup guarantees. No unsupported cause was assigned to that variability.

Auto selected a CPU limit of five from the detected topology/workload. Memory
admission allowed it. It remained safe here but was not the fastest choice:
Manual 1/2 BW were effectively tied, and Manual 2 MS was the lowest observed
time. This is a limitation of an admission/workload heuristic, not proof of
optimal scheduling or justification for a Ni-specific rule.

Existing timing boundaries in the fresh serial controls show where time went:

| Backend | Incoming + extra incoming preparation | Outgoing response stage | SC contraction / DC final tensor contraction |
| --- | ---: | ---: | ---: |
| BW SC, corrected | 0.007 | not applicable | 1.173 |
| MS SC, corrected | 0.158 | not applicable | 1.119 |
| BW DC, serial control | 0.017 | 24.667 | 0.069 |
| MS DC, serial control | 0.558 | 251.629 | 0.065 |

DC response time includes worker propagation, Coulomb/site kernels and depth
contractions; MS also includes outgoing FFT work. It is not an isolated FFT
timer. Energy-specific preparation outside that stage, admission, validation,
result accumulation and diagnostics occupy the residual. BW had 243/486/972
tasks at 1/2/4 workers; MS had 2036 bounded tasks at each count. Executors are
created per energy. Existing summed queue-wait and task-busy times overlap and
must not be added to wall time. The data locate DC cost in outgoing response,
but do not independently prove GIL, bandwidth or thread-start overhead as the
unique bottleneck. No speculative solver/pool optimization was implemented.

## Numerical validation, evidence and conclusion

All 16 runs retained exactly 243 energies, two 97×97 selected fields and the
unchanged fractional detector support. Raw spectra/full intensity maps were
finite, nonnegative within tolerance and nonzero where supported. Both
detectors' reversal identities, magnetic/nonmagnetic detector differences,
selected-map fractional integrals and actual outgoing energies were checked.
Intentional paired-map NaN masks were preserved.

Save/Open preserved spectra and selected maps in every case. Cross-worker,
Auto and SC-before/after comparisons covered **696 nonreference saved-array
comparisons**, all exactly equal to their corresponding one-worker reference
(928 checks including the four reference sets). Tolerances
allowed ordinary rounding (3e−13 relative plus source-scale absolute tolerance,
with separate coordinate/percentage handling); bitwise equality was observed,
not imposed as a cross-platform requirement. All executor diagnostics reported
zero active tasks after join; both BLAS runtimes restored their prior limits.
No task-owned benchmark process remained running.

Corrected BW SC also passed comparison of 43 numerical arrays with the genuine
[published macOS exports](https://github.com/dingpengem/EMCD-Sim/tree/32c30a5dfac52b6f100f8a2127ed99b270d36d0b/docs/examples/macos-ni-quickstart)
using their matched scientific recipe, units, source and masks. Those exports
came from macOS application source `03dc8f8d1f0374984c9fc81866eaa32ce48008d0`;
no new macOS run or artifact change was made. BW and MS, or SC and DC, were not
required to agree with one another under different numerical/physical models.

Task-local evidence is retained under
`build/windows-resource-benchmark-527a290/<case>/`: each `measurement.json`
contains settings-derived bounds, hardware/thread evidence and timing/RSS
measurements; each `project/` contains the normal saved numerical results.
The original Quick Start project, accepted packages and macOS reference files
remain intact. Temporary payloads, raw arrays, projects and build outputs are
not staged or committed; this report and the focused source/tests are the
Git deliverables.

**Does Single Channeling actually use more memory than Double Channeling?**
Not in these sampled, matched Windows Ni runs. SC required less incremental RSS; its
former larger estimate was caused by charging a hypothetical full-map scratch
workspace despite bounded contraction. This does not establish a universal
SC<DC theorem: result retention, basis size, FFT/depth settings, groups, worker
count, allocator behavior and missed short peaks can change comparisons.

**Remaining limitations:** sampled rather than exact interval RSS maxima;
reconstructed DC Run-total estimates; substantial laptop timing variability;
no 6/8-worker scaling claim; no general BW/MS/beam/slice convergence; effective
uncalibrated XMCD tensors; loose conservative DC bounds. Full regression,
previously incomplete source-guard coverage and new packaged acceptance are
**INCOMPLETE / not run**. This source correction is not contained in the
preserved dev6 binary. No new release or general performance guarantee follows
from this benchmark.

## Matched Windows/macOS full-workload comparison

This comparison was added **after all 16 Windows measurements completed**.
No existing run was interrupted, restarted, reconfigured or invalidated; no
EMCD calculation was added to fill a comparison gap. This section changes
documentation only, not either platform's kernels or resource policy.

The complete macOS [report](https://github.com/dingpengem/EMCD-Sim/blob/6475afed8d133fe39773c08701b216312cd455d5/docs/MACOS_SC_DC_RESOURCE_BENCHMARK.md)
and [structured results](https://github.com/dingpengem/EMCD-Sim/blob/6475afed8d133fe39773c08701b216312cd455d5/docs/benchmarks/macos-sc-dc-20261111/benchmark_results.json)
are pinned to benchmark-branch commit
`6475afed8d133fe39773c08701b216312cd455d5` on
`feat/macos-sc-dc-resource-benchmark`. Its 15 records contain **14 completed
full workloads and one incomplete attempt**, not 15 completed runs. The tested
macOS application remains published source
`03dc8f8d1f0374984c9fc81866eaa32ce48008d0`.
The macOS report's unavailable-Windows paragraph predates the Windows branch
push; the comparison below now uses the genuine retained Windows evidence.

### Matching and exclusions

All 16 Windows saved projects were checked against the macOS common
configuration, active provider declaration and per-run execution fields:

- Registered CIF SHA256:
  `ad8372ef427a95957a6182d5a7b7f5aaea5899e1464eb0afa8e540ff2f47d67d`.
  Registered XMCD SHA256:
  `bb9bdd478d54cc8de60403409f4d90e63deb11a64891bbac6754f867be14deda`.
  These are existing source identities, not new hash gates.
- Four occupied Ni sites, a=3.520 Å; Global +z; identical acknowledged XMCD
  element/edge, handedness, tensor convention, relative reference, eta/beta,
  selected features, normalization and reversal assumptions.
- Identical 200 kV/10 nm, [017]/(200), full finite ZOLZ, exact tilt and
  2.5/2.0 Å⁻¹ cutoffs; 21 common beams; B=0 and the same elastic model.
- All **243 actual energies**, two **97×97** full selected fields, 64 depth
  nodes, 64 boundary subpixels, exact Thales apertures and 57,860 evaluated
  pixels per calculation (2×9409 + 241×162). No checkpoints were reused.
- MS mesh **32×32**, projected generators (200)/(1,7,−1), maximum step 2 nm,
  actual step 10/63 nm and 63 intervals. Saved Windows depths agree with
  z_i=10i/63 nm; the existing trapezoid/reverse propagation schedule matches
  the documented macOS schedule. Propagation/channeling modes are matched
  individually, never SC against DC or BW against MS.

Inactive atomic-model parameters, sigma/radial controls and the disabled
post-edge window do not define this XMCD calculation. They were not used to
reject an otherwise scientifically identical pair. Resource controls and
platform-local source paths are experimental/context differences, not changes
to the source bytes or scientific request.

The Windows primary selections remain those already used above: corrected
SC rows `C` and fresh DC serial controls `R`. They are not newly selected by
their cross-platform ratios. `bw-sc/bw-dc/ms-sc-manual-1-v2` and
`ms-dc-manual-1-v3` are the corresponding macOS baselines. Windows `W2/W4`
match the same backend's `manual-2-v2/manual-4-v2`; Windows `A` matches that
backend's `auto-v2`, with different effective DC workers explicitly retained.

| Comparison/evidence | Classification |
| --- | --- |
| Four primary baselines and four DC Manual 2/4 pairs | MATCHED full scientific inputs and equal requested/effective workers |
| Four Auto pairs | MATCHED full scientific inputs and Auto mode; DC workers differ, so not equal-worker comparisons |
| Four earlier Windows `I` duplicates | Also full-workload matches to the same macOS one-worker baselines; retained, not substituted for the primary Windows controls |
| macOS BW Manual 6/8 | Completed but UNMATCHED: Windows did not run these counts; no new run or ratio invented |
| `ms-dc-manual-1-v2` | INCOMPLETE cancelled attempt; excluded, with successful `v3` used instead |
| Old macOS 93.4 s Quick Start and 98.548 s qWait trial | INVALID scientific-performance references due to the external controller; neither is used below |
| Reduced diagnostics or SC requests blocked above one worker | Not completed full workloads; excluded from performance pairing |

For traceability, the earlier Windows `I` timings BW SC/DC and MS SC/DC were
6.238/76.523/4.386/332.937 s. Matching them to the same complete macOS baselines
would give T_Mac/T_Windows=0.219/0.196/0.292/0.406. Those observations remain
in the inventory; the narrower primary ratios below must not erase this
substantial Windows run-to-run variation. Initial SC memory estimates also
belong to the obsolete Windows estimator, not the corrected model.

### Equal-worker timing and memory

All primary rows requested and executed **Manual 1 worker on both platforms**.
Windows used 8192 MiB and macOS 1024 MiB Manual caps. Both admitted the full
request without sampling changes; these caps are not allocations. Thus workers
and science match, but budgets, execution environments and hardware are not
a controlled hardware-only experiment.

T_Mac/T_Windows below 1 means the recorded Mac case took less reported time;
it is not an architecture or BLAS speedup attribution.

| Matched full backend | Windows seconds | macOS seconds | T_Mac / T_Windows |
| --- | ---: | ---: | ---: |
| BW SC | 1.724 | **1.365** | 0.792 |
| BW DC | 25.131 | 14.970 | 0.596 |
| MS SC | 1.580 | 1.279 | 0.810 |
| MS DC | 252.754 | 135.037 | 0.534 |

All memory below is MiB. Windows DC Run† retains the reconstruction scope
explained earlier; macOS final totals are the captured finalized admission
estimates. Baselines are each harness's recorded initial RSS, not a common
admission-time timestamp. Sampled peaks cover the calculation window, not GUI
rendering. Every row used verified single-thread calculation BLAS.

| Backend / platform | Estimated working arrays | Estimated process peak | Initial RSS | Sampled calculation peak | Increment | Budget |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BW SC / Windows | 3.786 | 250.08 | 117.19 | 121.15 | 3.96 | 8192 |
| BW SC / macOS | 5.185 | 423.92 | 301.09 | 311.22 | 10.13 | 1024 |
| BW DC / Windows | 16.187 | 265.93† | 117.26 | 123.44 | 6.18 | 8192 |
| BW DC / macOS | 16.185 | 401.64 | 253.70 | 275.25 | 21.55 | 1024 |
| MS SC / Windows | 5.442 | 252.27 | 117.12 | 121.66 | 4.54 | 8192 |
| MS SC / macOS | 6.842 | 408.32 | 271.83 | 287.25 | 15.42 | 1024 |
| MS DC / Windows | 40.664 | 296.78† | 117.69 | 142.14 | 24.45 | 8192 |
| MS DC / macOS | 23.360 | 432.87 | 278.38 | 288.00 | 9.63 | 1024 |

Equal-worker DC scaling is separate from Auto. Requested=effective on both
platforms at each listed count; the same respective 8192/1024 MiB Manual caps
and one-thread BLAS apply.

| Backend / workers on each platform | Windows seconds | macOS seconds | T_Mac / T_Windows | Within-platform speedup W / Mac vs its primary Manual 1 |
| --- | ---: | ---: | ---: | ---: |
| BW DC / 2 | 24.916 | 14.576 | 0.585 | 1.01× / 1.03× |
| BW DC / 4 | 34.095 | 20.775 | 0.609 | 0.74× / 0.72× |
| MS DC / 2 | 136.062 | 92.910 | 0.683 | 1.86× / 1.45× |
| MS DC / 4 | 140.395 | 78.065 | 0.556 | 1.80× / 1.73× |

For these scaling rows, each paired memory cell is **Windows / macOS**:

| Backend / workers | Working bound | Process estimate | Initial RSS | Calculation peak RSS | Incremental RSS |
| --- | ---: | ---: | ---: | ---: | ---: |
| BW DC / 2 | 27.117 / 27.116 | 279.26† / 476.75 | 117.03 / 316.17 | 125.37 / 315.52 | 8.34 / −0.66 |
| BW DC / 4 | 48.979 / 48.977 | 306.92† / 426.22 | 117.47 / 240.53 | 130.52 / 270.89 | 13.05 / 30.36 |
| MS DC / 2 | 60.073 / 39.810 | 320.68† / 446.42 | 117.33 / 268.27 | 145.97 / 290.50 | 28.64 / 22.23 |
| MS DC / 4 | 98.889 / 72.709 | 369.65† / 488.23 | 117.85 / 270.22 | 156.17 / 307.75 | 38.32 / 37.53 |

The negative macOS BW-2 increment is retained: calculation-window residency
fell below its earlier initial RSS. It is not a negative allocation or a value
to clamp to zero. The Mac-only 6/8 BW cases took 19.145/20.155 s and add no
equal-worker Windows ratio.

### Auto default-experience comparison

Both platforms requested **Auto CPU and Auto memory** in these rows. These
ratios describe the measured defaults, not equal-worker scaling. SC still
executes one outer worker; Auto DC chooses different counts.

| Full backend | Effective workers W / Mac | Seconds W / Mac | T_Mac / T_Windows | Budget MiB W / Mac |
| --- | ---: | ---: | ---: | ---: |
| BW SC | 1 / 1 | 2.395 / 1.219 | 0.509 | 6871 / 699 |
| BW DC | 5 / 4 | 35.398 / 17.176 | 0.485 | 6870 / 793 |
| MS SC | 1 / 1 | 2.104 / 1.242 | 0.590 | 6858 / 699 |
| MS DC | 5 / 6 | 152.668 / 79.339 | 0.520 | 6813 / 765 |

The complete paired Auto memory scopes, again **Windows / macOS**, are:

| Backend | Working bound | Process estimate | Initial RSS | Calculation peak RSS | Incremental RSS |
| --- | ---: | ---: | ---: | ---: | ---: |
| BW SC | 3.786 / 5.185 | 250.14 / 405.31 | 117.26 / 270.94 | 120.74 / 297.34 | 3.48 / 26.41 |
| BW DC | 59.909 / 48.977 | 320.35† / 493.27 | 116.98 / 305.20 | 132.74 / 318.19 | 15.76 / 12.98 |
| MS SC | 5.442 / 6.842 | 252.66 / 445.33 | 117.44 / 308.59 | 121.67 / 341.20 | 4.23 / 32.61 |
| MS DC | 118.298 / 105.608 | 393.84† / 536.38 | 117.42 / 278.08 | 162.26 / 315.28 | 44.84 / 37.20 |

Neither scheduler selected the fastest observed DC setting on its machine.
Windows BW favored Manual 1/2, and Mac BW favored Manual 1/2; Windows MS's
lowest observed time was Manual 2, Mac MS's Manual 4. This is evidence about
these observations, not a reason to install material-specific rules or retune
either policy to make platform ratios agree.

### What memory and timing differences do—and do not—show

The Mac is an Apple M2 Pro, **6P+4E / 16 GiB**; Windows is an i7-1365U,
hybrid 10 physical/12 logical / 32 GiB. macOS 26.3.1 uses packaged Python
3.11.16, NumPy 2.4.6/SciPy 1.17.1 with **Apple Accelerate**. Windows uses
Python 3.11.17 and the NumPy/SciPy **OpenBLAS** runtimes recorded earlier.
Both verified single-thread calculation/detector BLAS. Mac GUI default mode
is Automatic, whereas Windows restores numerical runtimes to 12 threads;
neither default is the calculation's BLAS thread count.

Windows timed the production source/API call including scoped BLAS entry/exit
and final admission, without Qt canvases. Mac timed the frozen GUI app's
scientific worker inside its existing BLAS guard, excluding display/save;
that same process still contained the GUI/restored-state/probe footprint.
The timing boundaries are close but not identical. No hardware-only or
library-only causal ranking follows from those totals. Existing phase timers
also warn against such attribution: primary BW-SC tensor contraction was
1.173 s Windows versus 1.220 s Mac despite the lower Mac total time.

The corrected Mac harness uses a normal native Qt event loop. The earlier
**93.4-second Quick Start is not used as scientific timing**, and the 98.548 s
qWait trial is also invalid for that purpose. The application kernel was not
accelerated by that harness correction. Windows calls `calculate` directly;
its progress callback does not wait, and only the separate RSS thread calls
`Event.wait(.02)`. It has no `QtTest.qWait`, GUI controller sleep or analogous
worker-blocking wait loop. A separate, non-scientific 0.5 s CPU-loop check
observed 0.484 s thread CPU without the sampler and 0.500 s with it; the sampler
made 12 readings. This supports absence of comparable starvation, **not** a
precise zero-overhead claim. No EMCD workload was rerun for that check.

Windows working set and Mac `proc_pid_rusage` resident RSS have OS-specific
sharing, residency and compression behavior. Mac physical footprint is a
different metric and is not substituted for RSS or Windows commit. The Mac
reported Warning pressure, roughly 3 GiB available RAM and about 4 GiB of
pre-existing swap during primary baselines; Windows had about 15 GiB available
RAM. Those conditions and different process contents prevent interpreting the
higher Mac total RSS as a kernel allocation, leak or architecture effect.
Both 20 ms-target samplers can miss brief peaks; Mac's native pthread sampler
is GIL-independent, while Windows' small sampling loop is a Python thread.

SC/DC conclusions must retain the memory definition:

- **BW:** Windows sampled SC/DC total RSS=0.981 and incremental=0.642. Mac
  total RSS=1.131, although its SC increment was only 10.125 MiB versus DC's
  21.547 MiB. Mac SC began about 47.4 MiB higher. Its larger SC total does not
  establish intrinsically larger SC calculation storage.
- **MS:** Windows sampled total ratio=0.856 and incremental=0.186. Mac total
  ratio=0.997, with increments 15.422 MiB SC and 9.625 MiB DC. Incremental RSS
  is a change in process residency, not a complete allocation ledger, so it
  cannot establish the opposite intrinsic ordering either.
- Working-array bounds put SC below DC on both platforms, but the bounds are
  not identical models. The published Mac SC planner includes additional
  coherence temporaries and site-phase allowance; Windows' corrected planner
  retains a smaller coherence allowance. Mac's Global MS-DC planner uses
  explicit response/result terms and preparation-stage lifetime accounting;
  Windows retains the looser legacy Global MS allowances described above.
  Some Mac energy-dependent retention terms use requested 241 while Windows
  plans actual 243; that explains the small BW-DC bound difference (~0.0016
  MiB), not a different calculated energy grid. These are accounting
  differences, not measured architectural memory efficiencies. No policy was
  changed to force equality.

The final process estimates exceed primary sampled calculation RSS by about
129–155 MiB Windows and 113–145 MiB Mac. The shared 128 MiB reserve, 25% margin,
different admission RSS timestamps and conservative array terms explain much
of that gap. They do not prove precise allocation accounting or general peak
safety. Exact allocation-stack attribution remains INCOMPLETE.

### Numerical status and targeted follow-ups

The existing scale-aware comparison of **43 numerical BW-SC arrays** with
authentic published macOS Quick Start exports remains valid: full 243-energy
spectra, selected full maps and intentional masks match within the recorded
tolerances. The new Mac benchmark report independently states its corrected
BW-SC baseline is bit-for-bit equal to those Quick Start arrays. Thus there is
authentic matched BW-SC numerical evidence, not an inference from timings.
That comparison allowed rtol 1e−9 with raw-scale absolute tolerances and separate
energy/percentage handling; it did not require cross-platform bitwise equality.

For **BW DC, MS SC and MS DC**, the Mac branch publishes compact within-platform
comparison results, not the raw spectra/maps. Those checks and Windows' own
worker comparisons pass, but **direct cross-platform numerical equivalence is
INCOMPLETE** for those three backends. Requesting their authentic Manual-1 NPZ
or CSV exports is the smallest next step; it requires no new calculation.

Other targeted follow-ups, if separately authorized, are matching frozen-app
measurement contexts/timer boundaries, directly recording the complete Windows
Run admission snapshot, and allocation-lifetime attribution for differing
coherence/MS bounds. Statistical/power/thermal repeatability and instrumentation
overhead have not been isolated. No expensive run or missing worker count was
silently repeated here. The four primary science/worker matches and separate
Auto comparisons are available; universal platform superiority, unmeasured
numerical equivalence, convergence and quantitative Ni calibration are not.
