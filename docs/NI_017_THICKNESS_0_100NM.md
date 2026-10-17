# Ni [017] exact-(200)-Bragg thickness study

Completed 51 requested thicknesses, 0 through 100 nm in 2 nm steps, with
Bloch-wave and FFT multislice entrance channeling. Results are in
`outputs/ni_017_thickness_0_100nm/` (generated data are kept locally).
MDFF and propagation physics, package version and executable remain unchanged.
The accompanying minimal GUI change adds a selectable memory budget and
available-RAM admission checks; it does not change simulation parameters.

## Configuration and definitions

The starting saved project is
`outputs/gui_stage_d/windows_20261016/reference_project`, calculated at 30 nm.
Its active XMCD source SHA256 is
`a0e28ea6423b6c7832bb3cce6d69d71aa59336a221baeee3d2556b49ba501283`.
The study preserves eta=beta=1, cubic magnetization [001], rotation into the
right-handed [017] local frame, 200 kV and absolute tilt
(-7.11672544, 0) mrad. This is the saved **projected 2D IAM** configuration,
not the newer atomic-3D potential implementation on the development branch.

The full oriented FCC ZOLZ basis has 27 beams, beam cutoff 3.2 cycles/Angstrom,
potential cutoff 2.2 cycles/Angstrom and B=0. FFT uses a 32x32 mesh and a
maximum split step of 0.04 nm. Both methods use 64 equally spaced depth nodes
per positive thickness and the same 33x33 reciprocal detector grid spanning
[-1,1] cycles/Angstrom in each direction. No projected FFT population is
renormalized. Thickness-independent geometry and the two reversal tensors
are prepared once; the existing contraction and propagation functions are used.
Each completed thickness flushes compact detector data and elastic populations
to disk; wavefields, coherences and full FFT intermediates are then released
before starting the next point. Arithmetic remains float64/complex128.

The GUI and scan driver use a configurable process-memory budget, default
2048 MiB, with options 512/1024/2048/4096/8192 MiB. The driver accepts
`--memory-budget-mib`. Fresh available-RAM/RSS checks occur before calculations;
estimated process peak must fit the budget and 50% of available physical RAM.
The estimate includes important non-kernel arrays, concurrent in-process
calculation reservations, a 25% allocation margin and 128 MiB reserve. These
are admission estimates, not guaranteed process peaks. No basis, cutoff, grid,
energy resolution, depth count or precision is reduced to fit memory.

Fixed physical detector centres are
A=(0.28376844494892167, +0.28376844494892167) and
B=(0.28376844494892167, -0.28376844494892167) cycles/Angstrom. They are the
opposite top/bottom Thales-circle positions for (200); aperture radius is
0.0908059024 cycles/Angstrom. Fractional integration uses 64 subpixels.
The sampled effective area is 0.025895118713378906 inverse-Angstrom squared
for each detector, with exactly mirrored A/B weights. Detectors never move.

Fixed evaluation energies are **831.4778 eV (L3)** and **848.698 eV (L2)**,
both present on the saved GUI energy grid. The former is the saved 30 nm
summed +M white-line peak; the latter is the saved native L2 magnetic feature.
Only these two energies are contracted in this study. The existing tensor
builder interpolates the unchanged native WIEN2k source at those energies;
no experimental energy shift or thickness-dependent peak selection is used.

The signed primary metric is `100*(A_plus-B_plus)/(A_plus+B_plus)`.
Reversal diagnostics use `N=(I_plus+I_minus)/2`, `M=(I_plus-I_minus)/2`:
magnetic-only is `100*(M_A-M_B)/(N_A+N_B)` and even imbalance is
`100*(N_A-N_B)/(N_A+N_B)`. No post-edge correction is applied.
The +M denominator generally differs from the reversal-even denominator,
even when the even A/B difference vanishes. At 0 nm all raw inelastic
intensities and denominators are exactly zero; all three percentages are NaN
(undefined), not zero. Actual thickness equals requested thickness everywhere:
the projected FFT solver subdivides each interval and reaches its endpoint
exactly; it does not round to unit cells.

## Numerical findings

L3 fixed-energy results, in signed percent:

| Thickness (nm) | BW raw PRB | MS raw PRB | BW magnetic-only | MS magnetic-only |
| ---: | ---: | ---: | ---: | ---: |
| 10 | -11.22445738 | -11.22441194 | -11.28972894 | -11.28968315 |
| 20 | -7.46796621 | -7.46820817 | -7.49680483 | -7.49704874 |
| 30 | -0.36256678 | -0.36269676 | -0.36263454 | -0.36276457 |
| 50 | -3.34777967 | -3.34786812 | -3.35356198 | -3.35365075 |
| 100 | -0.05327667 | -0.05318675 | -0.05327813 | -0.05318820 |

The largest sampled absolute L3 PRB dichroism occurs at **12 nm**:
BW -11.58068666%, MS -11.58068777%. Corresponding magnetic-only diagnostics
are -11.65020785% and -11.65020915%. This is a sampled maximum; no fitting,
smoothing or optimization between 2 nm samples was performed.

Both methods change L3 sign in the sampled brackets (30,32), (34,36),
(62,64), (66,68), (96,98), (98,100) nm. These bracket crossings rather than
locating exact zeros. Even imbalance remains numerical zero: maximum absolute
value across both edges is 4.61e-14% (BW) and 3.61e-14% (MS).
The numerical-noise scale in Figure 3 must not be interpreted as a physical
even signal.

| Thickness (nm) | BW L2 raw PRB (%) | MS L2 raw PRB (%) |
| ---: | ---: | ---: |
| 10 | +19.34590805 | +19.34582951 |
| 20 | +12.80265464 | +12.80307431 |
| 30 | +0.61535450 | +0.61557526 |
| 50 | +5.70584363 | +5.70599523 |
| 100 | +0.09047907 | +0.09032653 |

Maximum absolute BW-minus-MS differences are 0.000273911 percentage points
for L3 raw PRB and 0.000472280 for L2 raw PRB. The magnetic-only differences
are 0.000275522 and 0.000467490 percentage points. At 30 nm the original
four detector-state intensities at both fixed energies reproduce the saved
project **exactly**, including both previously reported L3 percentages.
Maximum FFT norm error is 1.61e-13; maximum population excluded from the common
27-beam projection is 1.63e-7 of incident intensity.

## Competing diffraction beams

The calculated signed `s_200 = -1.46108e-14` inverse Angstrom verifies exact
Bragg alignment to numerical precision. Other reflections are retained in
propagation. Relative intensities below are fractions of incident intensity,
without any per-beam normalization:

| Reflection | Excitation error (inverse Angstrom) | Largest BW exit population in scan | Thickness (nm) |
| --- | ---: | ---: | ---: |
| (200) | -1.46108e-14 | 98.5454% | 82 |
| (-200) | +0.008078008445 | 8.28270% | 36 |
| (400) | +0.008078008445 | 6.11808% | 88 |
| (1,7,-1) | +0.049477801725 | 0.012458% | 94 |
| (-1,7,-1) | +0.053516805948 | 0.006563% | 98 |

At 30 nm, BW exit populations are 93.5085% for 000, 5.92223% for 200,
0.453317% for 400 and 0.028881% for -200. Depth-averaged populations of
-200 and 400 are larger: 3.50817% and 1.74428% respectively. Across the scan,
the minimum 000+200 exit population is 89.3899% (BW), 89.3895% (MS); the
minimum depth-averaged pair population is 93.5433% and 93.5432%. These values
show substantial two-beam dominance with measurable multibeam contributions;
the configuration is **exact (200) Bragg**, not a strict isolated two-beam
wavefield. `elastic_beams.csv` records every common beam at every thickness.

## Focused validation and limitations

Representative 10, 30 and 100 nm cases were checked before the remaining
sequence. Focused study checks cover sequence, fixed energies/detectors,
percentage definitions, zero-thickness handling, reversal parity, saved-source
configuration and reference reproduction, together with the existing PRB
readout tests. Additional memory checks cover all five budgets, available-RAM
rejection, GUI controls, concurrent admission, cancellation/error cleanup,
512 MiB support, and weak-reference verification that compact checkpoints
retain no wavefields or coherences. Original project files and XMCD source
remain unchanged. The streaming scan is compared against the original
completed scan at every detector state, energy and thickness: 43 shared
numerical arrays and both methods' elastic populations are identical.
The final memory-managed run admits 51 sequential points at a 2048 MiB
budget. Dense working storage is estimated at 48.455 MiB and total calculation
arrays at 54.030 MiB; process-peak admission estimates range from 301.5 to
303.1 MiB with current RSS included. These are estimates, not measured peaks.
Fifteen memory/study tests pass; the pre-existing targeted 512 MiB rejection
check is also retained with an explicit 512 MiB selection.

A separate 100 nm quadrature control uses 128 and 256 depth nodes with the
same engines and physical settings. BW L3 PRB values for 64/128/256 nodes
are -0.05327667/-0.05338931/-0.05321999%; MS values are
-0.05318675/-0.05330394/-0.05313600%. This nonmonotonic spread is up to
0.000170 percentage points. L2 spread is up to 0.000288 percentage points.
Production curves retain 64 nodes for consistency with the saved reference;
the control does **not** establish depth convergence or replace those curves.
Close BW/MS agreement alone cannot establish convergence.

The finite basis, FFT sampling, detector-grid integration and potential cutoff
are held fixed, not newly converged here. This is an entrance-only model with
approximate XMCD-constrained MDFF, no outgoing channeling and no full
DFT-derived transition tensor. Native energies are not absolutely calibrated;
intensities are relative units, not experimental cross sections. The geometry
is [017], not the PRB reference [001] systematic-row vicinity. No eta/beta or
other scale was fitted to literature.

## Files and reproduction

Run from the repository root in the existing `emcd-python` environment:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
python scripts/ni_017_thickness_scan.py
```

The output directory must not exist; `--output` selects a fresh directory.
The original saved project and matching source must be available. No GUI is
launched, and no standalone executable is rebuilt. Focused checks:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest tests/test_memory_budget.py tests/test_ni_017_thickness_scan.py -q
```

Generated files include five figures in both PNG and SVG, long-form
`thickness_series.csv` (requested/actual thickness, solver, edge, energies,
all four detector intensities, N/M components, percentages and denominators),
`bw_ms_comparison.csv`, `elastic_beams.csv`, `depth_quadrature_control.csv`,
`configuration.json`, `summary.json` and `thickness_series.npz`. The NPZ embeds
configuration/provenance and includes compact common-beam exit/depth-average
populations, weights and hkl coordinates. Per-thickness checkpoints preserve
full-precision detector states and elastic populations (plus full-FFT exit
populations), with no wavefield/coherence stack. `completed_points.csv` is
flushed after each point. Figure 1 is L3 raw PRB; Figure 2 magnetic-only;
Figure 3 even imbalance; Figure 4 L2 raw PRB; Figure 5 BW-MS differences.
Axes preserve signs, use a common 0-100 nm thickness range and include zero
references. Lines join the calculated points without smoothing or fitting.
