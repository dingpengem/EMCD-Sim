# Full Ni double-channeling thickness benchmark

This study keeps numerical solver validation separate from convergence of the
truncated physical model. Additional voltage scans and GUI activation are
conditional on the 200 kV convergence gate; their status is reported explicitly
below. No uncalculated curves are supplied.

## Configuration and workflow

The starting commit is `be8c3c34477f2a197646bf07f01a64d38fde1b33` on
`feat/atomic-3d-multislice`. The primary geometry is the established FCC Ni [001]
(200) systematic-row projected potential. The secondary geometry is genuine
Ni [017], with full finite 2D ZOLZ diffraction and k+7l=0. It is not a two-beam
restriction or a rotated [001] potential.

Both use 200 kV, a=3.524 angstrom, B=0, beam cutoff 3.2 cycles/angstrom,
potential cutoff 2.2 cycles/angstrom, native L3=831.4778 eV and L2=848.698 eV,
and the unchanged XMCD-constrained tensor with eta=beta=1. [001] has 11 h00
beams and incident tilt (-7.116725439974256,+35) mrad. [017] has 27 allowed
beams and exact-Bragg tilt (-7.116725439974256,0) mrad. Excitation errors and
the full ordered hkl basis are recorded; s200 is zero to numerical precision.

Magnetization is crystal [001]. The existing proper orientation matrix rotates
the tensor into each local frame, after reversal in the cubic frame. For [017],
local magnetization is (0,-1/sqrt(50),7/sqrt(50)); it is not aligned with the
local beam axis. Hermitian complex magnetic terms and Coulomb factors are
preserved. Both solvers use the same frozen longitudinal transfer
qz=-E_loss/(h*v_in), while outgoing elastic propagation uses E0-E_loss and its
corresponding relativistic wavelength and interaction constant.

A/B Thales apertures remain fixed in reciprocal units: centers
(0.283768444948922,+/-0.283768444948922) cycles/angstrom and radius
0.0908059024. The detector grid is 193x193 over [-0.5,0.5] in each coordinate,
with fractional circular boundaries and 64 subpixels per boundary axis. These
weights are shared by methods, edges and reversal states. The primary FFT mesh
is 32x32; [001]'s explicit row potential permits the independently verified
invariant-sector 1D reduction. [017] retains the complete oriented 2D FFT mesh.

All four methods are saved: BW entrance-only, BW double-channeling, MS
entrance-only, MS double-channeling. Thickness is exactly 0-100 nm in 2 nm
steps. No unit-cell rounding or 1 nm refinement is performed. Raw intensities
are integrated over depth and detector first; percentages are calculated only
from those integrals. At t=0 the raw yield is zero and relative percentages
are NaN, not zero.

MS uses 257 trapezoid nodes including half-weighted endpoints and maximum
split step 0.04 nm. Actual equal steps land exactly on each ionization node.
BW entrance-only and [001] double-channeling use analytical depth integrals.
For the larger 27-beam [017] double-channel contraction, the existing numerical
BW depth reference is used at the same 257 nodes as MS, avoiding the large
mode-pair analytical contraction. A focused comparison against the analytical
27-beam response at 12 and 100 nm validates this choice; further depth controls
remain part of the gate. This numerical choice is explicit and does not reduce
the beam basis, tensor complexity, precision or potential support.

## Reproduction, safe reuse and minimal solver extension

Before either full scan, all four previous [001] points (10,12,20,30 nm) are
re-executed. Every raw A/B(+/-M) state at both energies is compared with the
recorded BW/MS results. The largest reproduced raw discrepancy is below
5.6e-17 and the largest percentage discrepancy below 3.2e-14 percentage points.
They are then reused in the full scan. Previous 64-node entrance-only voltage
curves and the coarser [017] detector study have different numerical metadata,
so they are preserved rather than silently substituted for the new quadrature.

Two small reusable extensions support the study:

- Exact periodic equivalent-site phase groups retain their multiplicities,
  averaging independent site intensities once per distinct phase field. For
  allowed FCC paths the four sites have exactly the same phase. No physical
  event, interference term or per-atom normalization is dropped. Tests include
  inequivalent complex site phases, and the four-point absolute-intensity
  reproduction checks the complete calculation after this change.
- The existing [017] projected geometry supplies actual oriented harmonics,
  Fourier coefficients and FCC extinctions to the FFT double-channel solver.
  It is checked against the established [017] entrance FFT amplitudes and
  reciprocal coordinates. No atomic-3D potential is introduced.

Both geometries have a y-mirror symmetric elastic problem at their chosen
incidence (the [001] potential is explicitly y-invariant). The study evaluates
q_y>=0 response matrices and obtains negative-y responses by S R S with
S=diag(1,-1,1). The tensor is **not** reflected, so all components of the fixed
crystal magnetization, including [017]'s local y component, remain intact.
Coordinates are not interpolated or rounded; full detector weights still
integrate every original pixel. Independent direct +/-qy tests verify the
complex-response symmetry for BW and MS before the full calculations.

Checkpoints contain only compact raw integrals, elastic exit populations,
settings and diagnostics. Each completed thickness is saved atomically. Resume
requires exact source, tensor, physical/numerical settings and implementation
hashes; mismatches raise rather than silently reuse results. No complete series
of wavefields is retained. Float64/complex128 and the existing 2048 MiB memory
admission checks are preserved. The checkpoint round-trip/provenance test also
checks that resumption does not invoke the producer a second time.

## Numerical results

Both 51-point scans are complete. The table gives signed raw PRB contrast at
each method's sampled maximum absolute L3 signal; L2 is evaluated at the same
thickness. These are model predictions at the fixed primary settings, subject
to the convergence checks below.

| Geometry | Method | Peak thickness (nm) | L3 (%) | L2 (%) |
|---|---|---:|---:|---:|
| [001] row | BW entrance | 12 | -11.854907 | +20.109313 |
| [001] row | MS entrance | 12 | -11.854842 | +20.109202 |
| [001] row | BW double | 8 | -13.186492 | +22.345617 |
| [001] row | MS double | 8 | -13.186474 | +22.345587 |
| [017] | BW entrance | 12 | -11.658619 | +20.102848 |
| [017] | MS entrance | 12 | -11.658559 | +20.102745 |
| [017] | BW double | 8 | -12.995977 | +22.430920 |
| [017] | MS double | 8 | -12.996003 | +22.430966 |

Outgoing channeling moves the strongest sampled L3 signal from 12 to 8 nm in
both geometries. The BW maximum magnitude increases by 1.331585 percentage
points (11.23%) for [001], and 1.337359 points (11.47%) for [017]. The peak
positions are resolved only on the requested 2 nm grid.

It also changes the oscillation pattern: [001] entrance-only absolute maxima
occur at 12,48,82 nm, whereas both double-channel curves have local absolute
maxima at 8,28,50,74,88 nm. The latter spacings are 20,22,24,14 nm; a single
oscillation period would conceal the interference structure. [017] entrance
maxima are at 12,48,80 nm and its double maxima are at the same sampled
thicknesses as [001]. Incoming elastic (200) population maxima are at 18,50,82
nm in both geometries and methods, with sampled spacing 32 nm. The two-beam
extinction-distance estimate is xi_200=37.58446657 nm. Neither that estimate
nor the elastic population spacing alone determines the EMCD extrema.

The [001] entrance curves reverse sign in the sampled brackets 30-32,34-36,
64-66 and 66-68 nm. All actual brackets for both geometries and edges are in
`sign_reversal_brackets.csv`. Neither double-channel curve has a sampled
sign-change bracket through 100 nm. This does not exclude a crossing between
samples. At 100 nm, MS double L3/L2 are -0.482981/+0.817759% for [001] and
-0.483302/+0.818894% for [017].

BW/MS double-channel contrasts differ by at most 0.000423382 percentage
points over the complete two-geometry, two-edge series. The [001] maximum is
0.000381001 points, with maximum raw relative difference 0.00119161%.
Long-thickness agreement is therefore strong at matched settings; it does not
establish convergence of the finite basis or potential cutoff.

| Geometry/mode | Maximum BW-MS contrast difference (pp) | Maximum raw relative difference (%) |
|---|---:|---:|
| [001] entrance | 0.00105119 | 0.00119971 |
| [001] double | 0.00038100 | 0.00119161 |
| [017] entrance | 0.00107138 | 0.00140978 |
| [017] double | 0.00042338 | 0.00129159 |

These maxima include both edges and every positive thickness. The complete
per-thickness differences are in `bw_ms_discrepancies.csv`.

Reversal-even A/B imbalance is roundoff-sized for these symmetric elastic
geometries. However, for [017] a common magnetic contribution to A and B
changes the +M sum: at 8 nm, MS L3 raw contrast is -12.996003%, while the
magnetic-only percentage is -13.083422%. The full rotated tensor is retained;
the two percentages are not conflated.

The shift to an 8 nm sampled optimum is qualitatively closer to the thin-sample
optimum discussed with PRB Figure 5(c). It is not a quantitative reproduction
of its amplitude, period or accelerating-voltage dependence. No spectral or
magnetic parameters were fitted. Voltage dependence remains conditional on
the convergence gate, and cannot be inferred from the 200 kV curves alone.

## Convergence gate and conditional work

The screening tolerances were declared before examining the full convergence
results: maximum 0.01 percentage points in paired PRB contrast and 0.1% in each
raw detector state. They are local research criteria chosen to resolve effects
smaller than the previously observed 0.09086-point potential-cutoff sensitivity,
not a universal accuracy standard or a fit to the publication.

The primary scan settings remain fixed. Controls assess potential cutoff,
incoming/outgoing basis, FFT mesh, split step, depth integration, and detector
sampling near a sampled maximum and a sign reversal, plus additional depth and
step checks at 80 and 100 nm. If a double-channel curve has no sign reversal,
the first entrance-only crossing is used and labeled explicitly. No crossing
is invented. All controls report raw intensities and signed percentage-point
changes. Potential-cutoff sensitivity is evaluated separately from BW/MS error.

**Gate failed.** The maximum contrast change is 0.142819146 percentage points
and maximum raw relative change is 0.706599748%, both from the [017] 30 nm
MS-double L2 potential-cutoff control (2.2 to 3.0 cycles/angstrom). The limits
are 0.01 points and 0.1%, respectively. The largest [001] cutoff change is
0.103096902 points. These differences are much larger than matched BW/MS error.

Maximum absolute change over all checked thicknesses, methods and edges:

| Control | [001] contrast (pp) | [017] contrast (pp) | [001] raw (%) | [017] raw (%) |
|---|---:|---:|---:|---:|
| Depth nodes 257 to 513 | 0.00074764 | 0.00074793 | 0.00091465 | 0.00097120 |
| Maximum step .04 to .02 nm | 0.00009446 | 0.00017126 | 0.00031777 | 0.00063727 |
| Potential cutoff 2.2 to 2.6 | 0.08323318 | 0.10610154 | 0.27134365 | 0.49334362 |
| Potential cutoff 2.2 to 3.0 | 0.10309690 | 0.14281915 | 0.34956234 | 0.70659975 |
| Beam cutoff 3.2 to 3.8 | 0.00026559 | 0.00065710 | 0.00176026 | 0.00381658 |
| FFT 32 to 48 | 5.91e-13 | 1.71e-8 | 1.26e-11 | 1.37e-7 |
| Detector grid 193 to 385 | 0.00057882 | 0.00057559 | 0.00293073 | 0.00293232 |

Raw changes use the larger absolute intensity of the control and reference as
denominator for each individual A/B(+/-M) state. These controls include 8 and
30 nm for all settings, and 80/100 nm for depth and step. The double-channel
curves have no sampled crossing, so 30 nm is explicitly the left endpoint of
the first **entrance-only** crossing bracket. The complete 288-row control
table preserves signed contrast changes and raw/magnetic/even differences.

The larger [001] row contains 13 beams rather than 11; [017] retains its full
oriented finite basis at both cutoffs. The script constructs the larger row
directly to avoid the unrelated GUI limit on its unfiltered 2D parent basis.
No beams are discarded to satisfy that interactive limit.

The tested depth, propagation, FFT, detector and basis controls pass the local
criteria. The physical potential support does not. Increasing the cutoff to
3.0 is a sensitivity probe, not proof that 3.0 itself is converged, and the
primary production scan remains at 2.2. There is no inferred error cancellation
or claim of a strict physical convergence plateau.

Consequently, the 100 and 300 kV double-channel scans are **not run**. Voltage
dependence of this double-channel thickness series and cross-voltage t/xi
collapse remain undetermined. Figure 7 contains only the calculated 200 kV
normalization; Figure 6 is replaced by an explicit NOT_RUN status file.
Existing entrance-only voltage results are preserved and are not substituted
for missing double-channel calculations. Checkpoint C is **not activated**:
GUI, project schema, package version and executable are unchanged. A future
study should establish adequate potential-cutoff convergence before expanding
the voltage comparison or enabling the GUI mode.

## Relation to PRB 2007 Figure 5(c)

The original source is Rusz, Rubino and Schattschneider,
[Physical Review B 75, 214425 (2007)](https://doi.org/10.1103/PhysRevB.75.214425),
checked in the [original author manuscript](https://arxiv.org/pdf/0704.1407).
Figure 5(c) concerns fcc Ni, G=(200), opposite Thales detector positions, and
an L3 signal. Its relative dichroism is the detector difference divided by the
sum. Here the same definition is expressed as a signed percentage:
100*(I_A(+M)-I_B(+M))/(I_A(+M)+I_B(+M)). There is no extra factor two.

Absolute raw difference, magnetic-odd difference, reversal-even difference and
magnetic-only percentage are exported separately. The magnetic-only denominator
uses the reversal-even sum. It must not automatically be equated to the raw
+M denominator, particularly with a rotated magnetization. No average of
pointwise depth percentages, peak renormalization or post-edge correction is
used in this benchmark.

The reference calculation's accelerating voltage has not been conclusively
established. Neither a presumed 200 kV value nor a digitized curve fitted by
adjusting eta/beta is used. The source is an XMCD-constrained effective tensor,
not the paper's full DFT-derived MDFF. Projected IAM potential, cutoff, finite
ZOLZ basis, frozen qz, continuous ionization-depth density and uncalibrated
absolute cross-section prefactors have not been fully matched to the reference.
Both this model and the published Figure 5 calculation omit absorption, as the
paper states explicitly. Absorption is therefore a limitation for comparison
with experiment, not an explanation of disagreement with that particular
calculated figure. TDS and HOLZ are also absent from the present model.
The native calculated energy axis is unchanged; agreement in curve shape does
not calibrate absolute experimental energies or magnetic amplitudes.

## Deliverables and reproducibility

Local output directory: `outputs/ni_double_channeling_full_benchmark/`.
The runner is `scripts/ni_double_channeling_full_benchmark.py`; the analysis and
figures use `scripts/ni_double_channeling_full_report.py`. Run checkpoint A,
then B, using `--stage a` and `--stage b` respectively. Check the saved gate
before considering any additional voltage or GUI work. Exact-provenance cached
points resume without propagation. Figure regeneration reads calculated arrays.

Each geometry has its own `configuration.json`, `results.csv`, `results.npz`
and compact `checkpoints/`. Common exports include reference reproduction,
summary extrema, sign-reversal brackets, BW/MS discrepancies, elastic sampled
peak positions and convergence controls. The figures distinguish entrance and
double channeling, signed L3/L2 contrast, raw reversal components, absolute
method differences, incoming elastic populations and normalized thickness.
No smoothing or fitted oscillation period replaces the original samples.
Representative angular figures retain 000, (200), ZA, Thales and physical
aperture overlays. Unrun voltage comparisons are labeled as not run; no
synthetic 100/300 kV double-channel curves are generated.

Previous simulation outputs and the Ni source are hash-checked unchanged.
Existing GUI source, project schema and published results are not modified
unless checkpoint C is explicitly reached and passed. No executable rebuild,
release tag, package or push is part of this task.

## Focused validation

**34 focused tests passed** (4.87 s), covering the two new benchmark test
modules and existing multislice, BW and double-channel foundation tests.
No broad regression suite was run. The JUnit record is
`outputs/ni_double_channeling_full_benchmark/focused_tests.xml`.

The checks cover complex equivalent-site intensity averages, actual oriented
[017] FFT amplitudes, magnetic-frame-preserving mirror response, numerical BW
depth integration against the analytical response at 12 and 100 nm, exact
checkpoint resumption and mismatch rejection, serial/eight-worker equivalence,
larger-row construction, all 102 completed thickness checkpoints, raw-state
CSV/NPZ equality, zero-thickness NaNs, ratios of integrated intensities,
magnetization/ZA metadata, four-point reproduction, unchanged old output/source
hashes and honest reporting of the failed gate. Existing tests additionally
exercise independent forward/adjoint propagation, elastic conventions,
magnetic parity and analytical/numerical double-channel contractions.

The final development commit and software/file hashes are recorded locally in
`delivery_provenance.json`. Large generated arrays and figures remain local;
only the minimal implementation, scripts, focused tests and this report are
committed. No push, executable build, package, version change or tag was made.
