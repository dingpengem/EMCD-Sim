# MS Double buffer and temporary-array optimization

Focused CPU patch based on `39aafb6701f7cf84643c10366afac59401e8d91e` and the
[profiling findings](MS_DOUBLE_PERFORMANCE_PROFILE.md). The
[energy-dependent angular schedule](ENERGY_ANGULAR_SAMPLING_PERFORMANCE.md)
is retained. No solver backend, physical parameter, precision or model changed.

## Exact matched cases and workload

The saved 300 kV benchmark supplies conventional FCC Ni [017], full finite 2D
ZOLZ, exact (200) Bragg, tilt (-5.586688140406262,0) mrad, beam cutoff 3.2 Å⁻¹
(27 incoming/outgoing beams), potential cutoff 2.2 Å⁻¹, B=0, FFT32, maximum
step 0.5 nm, depth64, angular grid97, extent ±1 Å⁻¹ and aperture subpixels64.
Thales A/B centers are (0.2837684449489217,±0.2837684449489217) Å⁻¹, radius
0.0908059024 Å⁻¹. The resource budget is 2048 MiB; outgoing workers remain four,
with OpenBLAS/OMP threads=1. Both cases use the same XMCD-effective tensor,
crystal [001] magnetization, eta=beta=1, native L3 831.271 eV and source hash
`a0e28ea6423b6c7832bb3cce6d69d71aa59336a221baeee3d2556b49ba501283`.
Only thickness changes between the 8 and 30 nm cases. There is no energy shift.

| Quantity | 30 nm | 8 nm |
| --- | ---: | ---: |
| Depth nodes / intervals | 64 / 63 | 64 / 63 |
| Substeps per interval | 1 | 1 |
| Actual step magnitude (nm) | 0.47619047619047616 | 0.12698412698412698 |
| Incoming split steps | 63 | 63 |
| Unique outgoing directions / batches | 7,857 / 246 | 7,857 / 246 |
| Outgoing batched split steps | 15,498 | 15,498 |
| Outgoing individual direction steps | 494,991 | 494,991 |
| Outgoing 2D FFT / inverse FFT calls | 15,498 each | 15,498 each |

All 9,409 map pixels are reconstructed with the existing exact mirror mapping.
The two cases have the same workload counts, because both depth spacings are
below 0.5 nm. Runtime must not be extrapolated linearly with thickness here.
Every depth node, norm check and excluded-basis population remains evaluated.

## Implementation

- `FFTSplitStep.advance` no longer copies its input before a positive number of
  steps: the first FFT already creates private output storage. Zero steps still
  return an independent copy. Scaling and transmission multiplication reuse
  private FFT outputs in place, preserving the original multiplication/division
  order. Input arrays, including read-only/strided arrays, remain untouched.
- Incoming squared magnitudes are formed once for incoming norm and leakage.
  Each outgoing batch has a reusable float64 magnitude buffer; absolute value
  and power are evaluated once per depth and reused for total/excluded sums.
  No diagnostic is removed or sampled less often.
- Retained incoming vectors are gathered once into contiguous storage; the
  outgoing conjugated gather is reused across site classes at each depth.
  Small weighted-amplitude and event buffers replace per-event temporaries.
  The exact existing einsum expression/path policy, complex128 tensor response,
  site weights and sequential independent-depth accumulation are retained.
- An unused local reciprocal-index-difference array was removed. Existing
  kinetic/transmission caches and detector-specific outgoing plans are retained.

NumPy 2.4.6 supports FFT `out=`, but this patch deliberately uses no new FFT API
or backend dependency. In-place ufuncs act only on new FFT outputs or local
buffers. There is no shared mutable work array between detector workers.
Negative propagation, reverse slice order and actual post-loss energy remain
unchanged. Configuration defaults, GUI controls and saved project formats are
unchanged; BW code is untouched and MS Single incoming fields remain exact.

## Measured full-field performance

Original source is loaded from the pinned Git commit into a separate module.
One baseline per thickness was saved before comparison. The same optional
worker/FFT instrumentation is used before and after; no full spectrum or
thickness scan was performed. Original arrays are preserved, never replaced.

| Thickness | Baseline outgoing field (s) | Optimized (s) | Speedup | Time saved |
| --- | ---: | ---: | ---: | ---: |
| **30 nm (primary)** | **41.5762** | **37.9134** | **1.097×** | **3.6627 s (8.81%)** |
| 8 nm | 40.6054 | 36.6112 | 1.109× | 3.9942 s (9.84%) |

The sum of separately measured serial numerical stages (FFT geometry,
incoming fields, outgoing field and result assembly) is **41.6243→37.9738 s**
at 30 nm and **40.6388→36.6514 s** at 8 nm. These exclude source import/setup,
GUI rendering and NPZ export, and are not whole-application launch timings.
The primary field timer covers the complete outgoing pool and deterministic
response assembly. Earlier profiling's 44.78 s at 8 nm is contextual; the fresh
matched baseline above is used for this comparison.

### Component timings

These are **summed worker elapsed seconds**, not disjoint fractions of main
wall time. Parallel worker totals cannot be added to the field's wall time.

| Component | 30 nm baseline→optimized | 8 nm baseline→optimized |
| --- | ---: | ---: |
| Outgoing advance, including FFTs | 74.5292→68.7914 (1.083×) | 72.7037→66.6267 (1.091×) |
| Depth contraction body | 51.6674→46.8441 (1.103×) | 51.1188→45.6896 (1.119×) |
| Norm/leakage diagnostics | 32.4201→25.5764 (1.268×) | 31.8193→24.5707 (1.295×) |
| Other response/setup | 3.7033→6.0022 | 3.5492→5.8177 |

The other bucket **increases**, partly because retained-vector preparation is
hoisted outside the timed contraction body. Combining contraction and other
response work yields the more conservative **1.048× / 1.061×** improvement.
Do not attribute the whole body-timer decrease to faster einsum arithmetic.
The 30 nm result-assembly timer also rose from 0.0041 to 0.0157 s; this small
single-observation variation is included in serial-stage totals.

Actual FFT-call elapsed time is nearly unchanged: approximately
40.5139→40.0583 worker seconds at 30 nm and 39.9030→39.1040 at 8 nm.
The useful outgoing gain is mainly non-FFT copy/product/temporary work. Process
CPU for the field changed **109.4688→97.6094 s** at 30 nm and
**105.7031→94.5156 s** at 8 nm.

Full fields are single matched measurements, not confidence intervals. Timing
contexts themselves have overhead, and the optimized diagnostics have more
explicit timed operations. To check without instrumentation, three alternating
baseline/optimized trials used the same 256 actual L3 directions (eight batches,
four workers), without repeating any full-field baseline:

| Thickness | Baseline batch median (s) | Optimized batch median (s) | Measured subset speedup |
| --- | ---: | ---: | ---: |
| 30 nm | 1.2677 | 1.0609 | 1.195× |
| 8 nm | 1.2573 | 1.0650 | 1.181× |

These batch measurements are not predictions of full-field speedup. There is
visible run variance (one optimized 8 nm batch trial took 1.3160 s). No worker
count or numerical setting was changed to obtain the improvement.

## Numerical equivalence and checks

At **both full fields**, comparisons are bitwise equal for:

- All 7,857 complex Cartesian 3×3 response matrices.
- Complete plus/minus, magnetic/nonmagnetic and paired raw-difference maps.
- All four raw A/B reversal states, raw components and EMCD percentages,
  including identical NaN masks.
- Every batch's incoming/outgoing norm errors and excluded populations, as
  well as their final maxima. Diagnostic distributions are compared because
  worker completion order can differ.

Maximum numerical discrepancy is **zero**. No BW/MS cross-solver tolerance is
used to excuse implementation drift. Incoming field arrays also match the
original kernel bitwise in focused 8/30 nm tests. Independent dense/adjoint,
vacuum, outgoing-energy, site-average, parity/mirror, memory rejection and
cancellation tests remain passing. Zero-step ownership, noncontiguous/read-only
inputs, changed-sign cached steps and concurrent calls have explicit coverage.

**121 focused tests passed** (0 failures/skips, 90.36 s): new buffer tests,
existing MS Double and cancellation validation, energy-dependent scheduling,
profiling hooks, memory budgets and Automatic/Manual GUI configuration. The
426-test release suite was not run; the 204 production checkpoints were not
recomputed. BW propagation, numerical settings and source/tensor conventions
remain unchanged.

## Memory, instrumentation and limitations

Sampled maximum RSS (50 ms) changed **118.50→115.54 MiB** at 30 nm and
**122.90→114.79 MiB** at 8 nm. These are observations, not guaranteed peaks or
an allocation requirement; allocator history and process order differ.
The existing conservative memory estimator/admission remains unchanged. Its
depth/FFT working allowances cover the local buffers; no retained spectrum or
full outgoing depth stack is added.

At this configuration, local incoming power is about 512 KiB, retained incoming
vectors 27 KiB, outgoing magnitude 256 KiB per active 32-direction batch and
event buffers 6 KiB. Their lifetimes replace several repeated temporaries;
FFT outputs are private and reused without persistent per-plan scratch.

The first optimized 8 nm attempt stopped on an existing Windows ctypes probe
race between optional RSS sampling and memory admission. The profiler sampler
now acquires the same admission lock while reading RAM; checks are not disabled
and production memory code is unchanged. The completed 30 nm result was reused,
and only unfinished 8 nm was resumed. A focused test covers sampler locking.

Contraction and actual FFT transforms remain the principal costs. This patch
does not claim a universal speedup, convergence at 30 nm, improved MDFF validity
or experimental calibration. Potential future work is layout-aware contraction
and FFT scratch handling, with equally strict raw-response validation.

## Reproduction and saved artifacts

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
python scripts/benchmark_ms_double_buffers.py --policy baseline
python scripts/benchmark_ms_double_buffers.py --policy optimized --compare
python scripts/benchmark_ms_double_buffers.py --microbench
python scripts/benchmark_ms_double_buffers.py --compare  # saved data only
```

Under `outputs/ms_double_buffer_optimization/`: immutable original kernel
snapshot, original/optimized NPZ responses/maps at both thicknesses, configuration
and implementation hashes, stage/worker timings and diagnostics, comparison JSON,
compact `summary.csv`/`summary.npz`, uninstrumented batch measurements and focused
test XML/logs. Completed cases require matching signatures and array SHA256
before reuse. No large generated dataset is committed.

Published release/version/ZIP, previous validation data and all 204 production
checkpoint hashes remain unchanged. There is no Windows build, push, main merge
or additional scientific scan in this task.
