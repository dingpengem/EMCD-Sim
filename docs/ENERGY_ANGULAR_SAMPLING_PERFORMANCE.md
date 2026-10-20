# Energy-dependent angular sampling: bounded performance comparison

This is a scheduling optimization, not a convergence study. The exact baseline
is commit `619a1969055ac6d717c092dcf663c3d58062b7e0`; the benchmark loads that
commit's `gui/emcd_forward.py` and `gui/channeling.py` from Git. The elastic,
MDFF, coherence, BW and MS double-channeling kernels are unchanged.

## Confirmed bottleneck and scheduling

Previously, enabling maps evaluated every q pixel at every energy, although
only selected L3/L2 maps survived. Single also ran separate full-grid reversal
contractions. The shared adapter now uses full support only at selected map
energies and the nonzero fractional A/B weight union elsewhere. Full-field
energies supply their own detector integrals without duplicate response work.
Weights are computed once; original coordinates, energy samples and reductions
are retained. Single evaluates both original reversal tensors, not a sign proxy.

## Matched configuration and scope

There were no saved physical input records in the current GUI workspace. The
benchmark explicitly uses its starting conventional FCC Ni [017], full finite
2D ZOLZ, (200) exact-Bragg geometry at **300 kV, 8 nm**; eta=beta=1, crystal
[001] magnetization, beam cutoff **3.2 Å⁻¹** (27 beams), potential **2.2 Å⁻¹**,
B=0, FFT **32**, maximum slice step **0.5 nm**, depth **64**, angular grid **97**,
halfwidth **1 Å⁻¹**, **64** aperture subpixels, **2048 MiB** budget, original
Thales A/B centers and radius. The selected current source energies are
**831.271 and 848.698 eV**, with one ordinary sample at **839.9845 eV**. No
experimental energy shift or change to the input source is applied. The source
SHA256, absolute tilt and complete configuration are saved in `audit.json`.

Both engines passed existing geometry/support and memory admission before the
probe. One 32-direction probe per engine preceded the bounded three-energy
Double-channeling calculation. Every original/optimized setting is identical;
there is no benchmark-specific coarsening. Windows/Python environment details
are recorded in the audit; OpenBLAS/OMP threads were limited to one and the
existing outgoing scheduler used four workers. Cases were run once and saved
immediately; completed cases are reused on a compatible rerun.

## Actual work counts

| Quantity | Original | Optimized |
| --- | ---: | ---: |
| Ordinary-energy evaluated pixels | 9,409 | 162 |
| Ordinary-energy outgoing directions after existing mirror reuse | 7,857 | 133 |
| Selected-energy evaluated pixels, each edge | 9,409 | 9,409 |
| Three-energy evaluated pixels | 28,227 | 18,980 |
| Three-energy outgoing directions | 23,571 | 15,847 |
| Requested full-spectrum energies | 243 | 243 |
| Full-spectrum evaluated pixels (count only) | 2,286,387 | 57,860 |
| Full-spectrum outgoing directions (count only) | 1,909,251 | 47,767 |

The 243 samples are the unchanged 241-point energy grid plus the two locked
native features. Unique direction counts are actual `np.unique` results under
the existing mirror gate and actual floating-point coordinates, not an assumed
perfect halving. There is no new rounding or symmetry approximation. With a
nonzero vertical [017] mistilt, existing mirror reuse remains disabled.

## Measured calculation wall time

| Engine | Original (s) | Optimized (s) | Measured speedup |
| --- | ---: | ---: | ---: |
| BW Double | 23.4068 | 15.3475 | 1.525× |
| MS Double | 134.2284 | 80.3245 | 1.671× |

These are actual three-energy calculations including incoming propagation,
source/tensor preparation, responses, integration and derived observables;
project saving and import time are excluded. They are single measurements, not
confidence intervals. Two of three energies still require full maps. The full
243-energy spectrum was **not rerun**: its work counts above are deterministic
scheduling counts, not measured full-spectrum timing or a claimed 40× speedup.

| Engine / policy | Incoming (s) | Outgoing response (s) | Final tensor contraction (s) | Response batches | Sampled max RSS (MiB) |
| --- | ---: | ---: | ---: | ---: | ---: |
| BW original | 0.0559 | 22.8828 | 0.002710 | 12 | 89.31 |
| BW optimized | 0.1004 | 14.8002 | 0.001904 | 12 | 91.72 |
| MS original | 0.0247 | 133.6238 | 0.003256 | 738 | 141.86 |
| MS optimized | 0.0225 | 79.5990 | 0.002825 | 497 | 152.77 |

Outgoing response timing is the union of concurrent worker intervals and
includes Cartesian event-kernel construction and depth integration; it is not
an isolated FFT/eigensolve timer. Final tensor contraction is timed separately.
RSS is sampled every 50 ms in the same process across cases, **not peak RAM**;
allocator retention and concurrent test activity affect timing and RSS. The
measured RSS does not establish a memory reduction. Response batches are calls
into the outgoing kernels, not individual FFT substeps.

## Numerical agreement and focused acceptance

For both measured engines, maximum differences are **zero** in all four raw
detector states, all compared derived spectra (including EMCD percentages),
and finite values of every saved L3/L2 map field. NaN masks also match. This
does not imply BW and MS are themselves identical or physically converged.

Focused tests compare the exact old and new adapters for BW/MS Single/Double,
Both, asymmetric detector pairs, nonzero vertical mistilt, actual atomic
reversal tensors, maps on/off, post-edge diagnostics and raw parity identities.
Zero-signal tests retain NaN denominator behavior. Callback tests cover complete
resume, legacy raw-only selected edges, malformed/incomplete maps, cancellation
and no checkpoint writes for partial energies. Saved projects/arrays round-trip
without changing their formats. Existing cooperative-kernel cancellation and
Automatic/Manual GUI tests also pass. Total: **95 focused tests passed** (92 in
the combined run, followed by 3 added edge-case tests); no broad release suite.

Configuration identity remains the checkpoint provider's responsibility. The
standalone full-spectrum driver's strict implementation-hash gate is retained,
so an old disk profile is not silently admitted merely because array shapes
match. Compatible callback raw-only entries reuse ordinary energies and
recompute a selected edge only if its required full arrays are absent.

## Reproduction and artifacts

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
python scripts/benchmark_energy_angular_sampling.py --probe
python scripts/benchmark_energy_angular_sampling.py --run
```

Local generated artifacts are separate under
`outputs/energy_angular_sampling/`: probe/configuration/count audit, the two test
XML/log sets, benchmark `comparison.json`, compact `summary.csv`/`summary.npz`
and original/optimized saved projects with their numerical arrays. Signatures
include exact settings, source hash, baseline commit and adapter hashes; a
mismatch rejects reuse rather than overwriting previous completed cases.

No production thickness checkpoint, numerical precision, physical parameter,
energy calibration, release asset, version or Windows build is changed. Existing
limitations of the projected potential and XMCD-effective/atomic MDFF remain.
This optimization provides no new numerical or experimental accuracy claim.
