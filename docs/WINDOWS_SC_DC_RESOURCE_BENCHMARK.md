# Windows SC/DC resource benchmark — 11 November 2026

**PASS: all 16 complete, fresh-process calculations and their result round trips.**
For this representative Ni request, sampled Single Channeling (SC) memory was
lower than Double Channeling (DC). The previously higher SC *estimate* included
a full-map beam-pair workspace that the production adapter never allocates.
The correction changes admission accounting, not scientific sampling or physics.

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
Not in these sampled, matched Ni runs. SC required less incremental RSS; its
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
