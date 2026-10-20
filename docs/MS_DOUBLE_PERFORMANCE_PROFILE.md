# FFT Multislice Double: remaining performance profile

Profiling-only milestone based on `c15581a934c858e77c5104bfbc623dba70ca32a5`.
**No production solver, settings, numerical model or algorithm was modified.**
One optimized L3 full field and small outgoing-batch checks were measured;
there was no energy scan, thickness scan or repeat of the original baseline.

## Reference and measurement method

Inputs are loaded verbatim from the previous benchmark's saved optimized MS
project, not reconstructed from GUI defaults:
`outputs/energy_angular_sampling/benchmark/fft-multislice_optimized/project/`.

| Setting | Actual value |
| --- | --- |
| Crystal/frame | Conventional FCC Ni, a=3.524 Å; full finite 2D [017] ZOLZ |
| Voltage / thickness | 300 kV / 8 nm |
| Absolute local tilt | (-5.586688140406262, 0) mrad; exact (200) Bragg |
| Beam / potential cutoffs, B | 3.2 / 2.2 Å⁻¹; B=0; 27 incoming and outgoing MDFF beams |
| FFT / maximum slice step | 32×32 / 0.5 nm |
| Depth nodes / intervals | 64 / 63 |
| Actual substeps / interval | 1 |
| Actual signed outgoing step | -0.12698412698412698 nm |
| Angular grid / extent | 97×97; ±1 Å⁻¹ on each axis |
| Apertures | A=(0.2837684449489217,+0.2837684449489217), B=(0.2837684449489217,-0.2837684449489217) Å⁻¹; radius 0.0908059024 Å⁻¹; fractional, 64 subpixels |
| MDFF | Saved XMCD-effective source, crystal [001] magnetization; eta=beta=1 |
| Source SHA256 | `a0e28ea6423b6c7832bb3cce6d69d71aa59336a221baeee3d2556b49ba501283` |
| Profiled outgoing loss | Native L3, 831.271 eV; no energy shift |
| Resources / precision | 2048 MiB admission budget; float64/complex128 |
| Host | Windows build 26200, Intel family 6/model 186; 12 logical processors |
| Software | Python 3.11.17, NumPy 2.4.6; OpenBLAS/OMP threads=1 |

The saved spectral axis is reused for tensor import (which requires at least
two samples), but only the L3 tensor/response is evaluated for this profile.
Actual source/configuration, production source hashes and environment are in
`outputs/ms_double_performance_profile/audit.json`.

The tool times an **in-memory copy** of the original response function, adding
contexts around unchanged AST statements. Production files remain untouched.
Process-local FFT hooks exist only inside the explicit profiling context.
Counters/timers are thread-local and merged after workers finish. Separate
worker cProfiles use `time.thread_time`, so worker execution is not missed by
a main-thread-only profile. No per-iteration logging is used.

## Main finding and timing breakdown

The instrumented L3 response took **44.7775 s wall / 118.0938 s process CPU**,
averaging **2.64 active CPU-core equivalents** with four workers. Its full maps
were **bitwise identical** to saved L3 plus/minus maps (maximum difference 0).
The previous saved uninstrumented L3 outgoing-response interval was 41.0690 s;
that comparison is contextual, not a new paired overhead experiment.

Percentages below partition **summed worker response elapsed time** (178.4720 s),
not main-thread wall time. Parallel elapsed times cannot be added to the
44.7775 s wall total. Worker CPU totals were 117.6250 s; CPU fractions are
shown separately. Very small CPU timers on this Windows host were quantized,
so sub-percent CPU values should not be interpreted precisely.

| Component | Worker elapsed (s) | Worker elapsed (%) | Worker CPU (s) | Worker CPU (%) |
| --- | ---: | ---: | ---: | ---: |
| Outgoing FFT transforms | 43.0897 | 24.14 | 29.1719 | 24.80 |
| Other work inside outgoing advance | 35.6800 | 19.99 | 20.3125 | 17.27 |
| Depth/site Cartesian contraction and response accumulation | 58.7598 | 32.92 | 43.4063 | 36.90 |
| Norm/leakage diagnostics | 33.9465 | 19.02 | 21.0781 | 17.92 |
| Dipole kernel | 1.0480 | 0.59 | 0.6875 | 0.58 |
| Transfer allocation/fill | 0.4769 | 0.27 | 0.2031 | 0.17 |
| Equivalent-site phases | 1.2388 | 0.69 | 1.0781 | 0.92 |
| Outgoing plan construction | 0.4544 | 0.25 | 0.1406 | 0.12 |
| Other response work | 3.7780 | 2.12 | 1.5469 | 1.32 |

Outgoing advance therefore accounts for **44.14%** in aggregate, but only
24.14% is inside NumPy FFT calls. Cartesian contraction is the largest single
leaf component. Norm/leakage work is also substantial. Kernel/phase/plan
caching alone cannot remove most of this runtime.

Main-thread geometry/potential construction took **0.0284 s**, incoming fields
**0.0118 s**, and both magnetic-state contractions plus map assembly/equality
check **0.0047 s**. These separate main-thread timings are not included in the
worker percentages. Export was not repeated: this tool saves small profiling
metadata, not a new scientific project or map dataset.

## Actual propagation and reuse counts

| Operation | Measured count |
| --- | ---: |
| Full-field samples | 9,409 |
| Unique evaluated outgoing q directions | 7,857 |
| Outgoing response batches / plans | 246 / 246 (245×32, final 17 directions) |
| Incoming plan / forward advance calls | 1 / 63 |
| Outgoing advance calls / batched split steps | 15,498 / 15,498 |
| Outgoing individual direction split steps | 494,991 |
| Outgoing 2D FFT calls | 15,498 forward + 15,498 inverse |
| Outgoing individual 2D transforms | 494,991 forward + 494,991 inverse |
| Including incoming: batched 2D calls | 15,561 forward + 15,561 inverse |
| Including incoming: individual 2D transforms | 495,054 forward + 495,054 inverse |
| Depth contraction calls | 15,744 = 246×64×1 unique site-phase group |
| Dipole-kernel / site-phase preparations | 246 / 246 |

Counts distinguish vectorized 2D calls from individual direction transforms;
each 2D FFT internally uses two 1D-axis passes. The worker sample confirms this
dispatch. The 0.5 nm maximum step does **not** make this a 16-step propagation:
depth quadrature forces 63 intervals in each incoming/outgoing field.
Potential construction separately contains one `ifft2` call (source inspection);
the table's propagation counters exclude that potential-construction transform.

The physical cell has four Ni sites, grouped by the existing exact phase
equivalence into one phase class with the original multiplicity/averaging.
Incoming fields and FFT potential are built once and shared read-only across
all batches. Each outgoing adjoint field is reused across site phases and both
magnetization tensors. Kernel and plan are already built once per batch, not
once per depth. Existing mirror reuse and exact q coordinates are preserved.

Kinetic/transmission factors are already cached within each outgoing plan:
**246 misses and 15,252 hits**, plus one miss/62 hits for the incoming plan.
Blindly proposing a new per-step exponential cache would duplicate existing
behavior. Full kinetic factors depend on q and energy; sharing them without
those keys would be wrong. Potential/transmission invariants are more reusable,
but measured plan construction is small.

## Inner-loop and allocation observations

At each independent depth/site event the code contracts
`g,bh,bgha,gh->ba`, then adds `w_z * site_weight * v v†`. The response is an
incoherent sum of independent depth/site events. **Do not sum v over depths
before squaring.** Complex phase, conjugation and averaging must be retained.

Incoming retained-beam gathers, outgoing conjugated gathers, response outer
products and diagnostic arrays are rebuilt at every depth. `advance` validates,
reshapes/copies coefficients and creates FFT/product temporaries for each depth
interval. Diagnostics independently form `abs(reciprocal)**2` for norm and for
the excluded-index population; advance also checks finite coefficients. The
same mathematical magnitude information is used repeatedly.
Prepared-input shape/depth validation, incoming norm/leakage calculation and
ordered FFT-index lookup are also repeated per batch. An unused local `delta`
array is built before equivalent-site preparation recomputes its own delta;
this is small and is not the main bottleneck.

The 256-direction worker CPU profile contains 512 depth contractions, 1,536
NumPy `bmm_einsum` calls and 5,144 ndarray reshapes. Internal BMM work accounts
for about 0.891 worker CPU seconds, reshapes 0.375 s, and raw FFTs 1.063 s in
that profiled sample. `einsum_path`/greedy selection was called 512 times but
only about 0.016 s cumulatively: path selection is **not the main bottleneck**
on this NumPy build. NumPy already caches parts of its equation-to-BMM layout
logic. Older builds or different basis sizes may behave differently.

These measurements identify real arithmetic and array-layout/allocation work,
but do not establish a strict memory-bandwidth-versus-compute classification.
No hardware cache/bandwidth or direct GIL-blocking counters were collected.
CPU/wall gaps may reflect GIL, scheduling and memory contention; they do not
prove one particular cause.

## Threading and overhead

The same 256 actual L3 directions, eight fixed batches, were measured without
instrumentation at 1/2/4 workers. Three additional runs per count rotated the
order to reduce warm-up/order bias; no full angular field was repeated.

| Workers | Median wall (s) | Range (s) | Median process CPU (s) | Median active cores | Speedup over 1 | Efficiency |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| 1 | 2.4193 | 2.3475–2.7670 | 2.3594 | 0.98 | 1.00× | 100% |
| 2 | 1.4471 | 1.3827–1.5176 | 2.5625 | 1.73 | 1.67× | 83.6% |
| 4 | 1.2697 | 1.1968–1.4430 | 3.6563 | 2.88 | 1.91× | 47.6% |

Four workers are beneficial here, but the marginal gain over two is modest
and CPU work increases. The initial single measurement had 2 workers beating
4 (1.4271 vs 1.6338 s), illustrating why that observation alone cannot justify
changing the default. These batch medians are not full-field scaling results.

Full-L3 load balance was good: workers completed 61–62 batches each, 1,952–1,984
directions and approximately 44.51–44.76 s active elapsed time each. The
executor/batch envelope gap was only **0.0017 s**; submit time was **0.0361 s**
and overlapped running work. Main-thread submit/wait overhead is not the main
problem. The CPU cost of concurrent temporary-array handling remains distinct
from executor submission overhead.

On the initial matched 4-worker batch sample, timing hooks took 1.8070 s versus
1.6338 s uninstrumented (about 10.6% overhead in that pair). cProfile timings
have their own overhead and run variance; use them for attribution, not a new
production speed claim. No worker-count or BLAS setting was changed in the GUI.

## Memory and scaling

Sampled maximum RSS during the full L3 profile was **116.39 MiB**, at 50 ms
sampling; this is not a process peak guarantee or budget requirement. A separate
single 32-direction call had **4.94 MiB peak traced Python/NumPy allocations**;
that excludes some native FFT workspace and is not total process peak RAM.
Existing memory admission remained active.

For this 27×27-beam batch, transfer and real kernel arrays are each about
0.534 MiB; a complex phase-weighted kernel would be about 1.068 MiB. The shared
64×1024 incoming field is 1 MiB. FFT input counters total about 7.55 GiB for
each forward/inverse family across L3 (including incoming). These are cumulative
input bytes, not simultaneous allocations or measured hardware memory traffic.

Approximate structural scaling under fixed settings:

- Outgoing work grows with actual unique q directions and number of batches.
- FFT arithmetic grows roughly with `q × actual_steps × N² log(N²)` for 2D N;
  diagnostics and several temporaries grow with `q × depth_nodes × N²`.
- Contraction grows with depth/site groups and incoming×outgoing MDFF beams;
  it need not scale like the FFT mesh. The present 27-beam result does not
  predict the component balance for a 59-beam basis.
- Step count is `(depth_nodes-1) × ceil(depth_spacing/max_slice_step)`.
  Making max_slice_step larger than depth_spacing has no further effect here.
- Equivalent sites cost distinct phase classes, with multiplicities retained,
  rather than necessarily four repeated contractions in this FCC case.

These are algorithmic dependencies, not a fitted universal runtime model.

## Ranked next opportunities (not implemented)

| Priority / target | Measured opportunity and expected scope | Complexity / numerical risk | Memory / compatibility |
| --- | --- | --- | --- |
| 1. Reuse outgoing/depth-loop work buffers and squared magnitudes | Non-FFT advance ~20% plus diagnostics ~19% of worker elapsed; reduce redundant copies/products/gathers without dropping any check/event. Actual gain unmeasured; removing these entire categories would be an unrealistic ~1.64× ceiling. | Medium; low-to-medium risk from aliasing, stale buffers, adjoint signs and zero-step ownership semantics. | Bounded per-worker scratch buffers; keep current array precision and admission accounting. |
| 2. Improve contraction operand layout and batch-local invariant reuse | Depth contraction ~33%; target repeated BMM reshapes, index gathers and reusable phase/kernel layout. Exact path caching alone has little measured value. Entire-category removal ceiling ~1.49×, not an expected speedup. | Medium; changed reduction order needs strict old/new raw/map tests. | A complex phase-weighted kernel costs ~1.07 MiB per active batch here; avoid caching whole spectra/full fields. |
| 3. Improve FFT batching/layout with reusable storage | Actual FFT transforms ~24%; shape/stride/buffer work is worth a focused microbenchmark. Backend replacement is a separate later experiment. | Medium-to-high; normalization, negative-dz adjoint and backend rounding must be checked. | Check supported NumPy API versions; no new FFT dependency is introduced here. |
| 4. Tune CPU concurrency using evidence | 4-worker efficiency ~48%; 2 workers use less CPU with near-comparable latency. Do not infer a universal best count from eight batches. | Low implementation cost, workload-dependent benefit; preserve cancellation/admission and both engines. | Worker count changes concurrent memory demand; revalidate estimator if changed. |
| 5. Cache phases/plans/transverse geometric terms | Phase+plan+dipole preparation totals ~1.5%; straightforward invariants are small, not the main acceleration. Full energy-dependent kernels cannot be reused blindly across losses. | Low-to-medium; keys must include geometry, q, energy where relevant, depth/slice layout and potential. | Small immutable contexts; reuse existing prepared-grid/incoming guarantees. |

The illustrative ceilings use `1/(1-f)` on measured worker fractions solely
to prioritize work. They are not predictions or bounds on parallel end-to-end
speedup: waiting/overlap and allocation behavior can change with implementation.

Recommended first focused patch: **reuse bounded outgoing/depth-loop buffers,
especially one squared-magnitude field per depth for both norm and leakage,
while retaining every depth event, diagnostic and finite-value check.** Measure
each subchange under identical settings; preserve original sum order where
possible and keep a generic fallback. This has a better supported near-term
benefit/risk balance than more kernel caching or merely forcing a worker count.
Follow with contraction-layout changes if that first patch's measured gain is
insufficient. No numerical parameters should be reduced to obtain speed.

## Reproduction, outputs and validation

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
python scripts/profile_ms_double.py --run          # one new L3 profile, explicit opt-in
python scripts/profile_ms_double.py --batch-checks # small batches only
python scripts/profile_ms_double.py --summarize    # reads saved measurements only
```

Importing the tool installs no hooks. Normal application execution is unchanged.
Four focused tests check import safety, bitwise equality of the instrumented
response/diagnostics and exact FFT counts, restoration after exceptions, and
saved-reference setup without propagation. No broad regression suite was run.

Artifacts under `outputs/ms_double_performance_profile/`: exact audit,
`full_L3.json`, per-worker events/times, `components.csv`, `summary.json`, thread
trials and CSV summary, sampled/traced memory notes, worker `workers.pstats` and
machine-readable `worker_cprofile.json`, plus focused-test XML/logs. No large
scientific array dataset was generated. Profiling does not establish physical
convergence, absolute MDFF validity or experimental agreement. The 204 production
checkpoints, preceding BW/MS benchmark data, scheduling/GUI behavior, published
release and validated Windows ZIP remain unchanged.
