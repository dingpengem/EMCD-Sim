# Ni double-channeling potential-cutoff convergence

This follow-up starts at `f97e16c495097c27363c8b29938c254825ff7364` on
`feat/atomic-3d-multislice`. It changes no solver or physical model. The original
benchmark and its failed gate remain unchanged. New results are local under
`outputs/ni_double_channeling_cutoff_convergence/`.

**Uniform enlarged-basis follow-up:** the 4.6 cycles/angstrom profile passes
matched BW/MS agreement and independent 3.8-to-4.6 basis sensitivity at
8, 12, 30 and 100 nm, for both geometries and edges. See
[the enlarged-basis validation report](DOUBLE_CHANNELING_UNIFORM_BASIS.md)
for numerical tables, the tested production profile and scope limitations.
The complete 0-100 nm curve remains uncertified.

**Original cutoff-study outcome:** final potential-cutoff increments are below the unchanged
thresholds at the tested conditions, and the 12 nm entrance versus 8 nm double
ordering survives. The uniform 3.8 beam-cutoff profile still fails matched
BW/MS contrast at three [017] points. Enlarging the basis improves agreement
at 8/12 nm, but a uniform enlarged production profile had not yet been validated
at every representative thickness. That study's overall gate therefore remained failed;
the complete 0-100 nm curve is not certified as numerically converged.

## What failed

The old scan used potential cutoff 2.2 cycles/angstrom, beam cutoff 3.2,
FFT 32, 257 depth nodes and maximum propagation step .04 nm. Of its 288
control rows, 64 failed the unchanged screening criteria: .01 percentage
points in raw PRB contrast or .1% relative raw-detector change. These are the
2.6/3.0 potential-cutoff probes at 8 and 30 nm, for both geometries, both edges
and all four entrance/double BW/MS methods. Other independent controls passed.
The largest failure was [017], 30 nm, MS double, L2: +.1428191456 points and
.7065997483% maximum raw change for 2.2 to 3.0. Per-state values and all
individual failed rows are saved in `original_failed_states.csv`,
`original_failed_controls.csv` and `original_failure_audit.json`.

The original cutoff excludes (800), whose transverse magnitude is
2.2701475596 cycles/angstrom and IAM coupling coefficient is approximately
.0128726093 inverse nm. [017] also gains off-row terms such as (5,7,-1) at
2.4575068212 cycles/angstrom. These are actual Fourier components of the same
oriented IAM potential, not a change of potential model. Adding them changes
the elastic wave amplitudes and phases before and after ionization. Their
interference can change a detector difference even if their populations are
small. `fourier_shells.csv` records the actual admitted terms and coefficients;
population convergence is therefore checked alongside EMCD rather than used
as a substitute for it.

## Controlled study

The cutoff ladder is 2.2,3.0,3.8,4.6,5.4,6.2 cycles/angstrom. Both incident and
outgoing explicit bases initially use cutoff 3.8 (13 row beams for [001],
37 full-2D ZOLZ beams for [017]). The FFT is fixed at 48 throughout the ladder,
so changing potential support is not confounded with mesh size. The existing
oriented harmonic-support validation rejects an inadequate mesh; no Fourier
terms are silently dropped. The [001] invariant-row reduction is unchanged.

The completed BW ladder uses 8,12,20,30,50,80,100 nm. At the user's request to
test only a few thicknesses, remaining MS work was narrowed to the final three
cutoffs at 8/30 nm, the final two cutoffs at 100 nm, and the final cutoff at
12 nm. Available lower-cutoff results and already completed broader [001] MS
results are retained without restarting them. `scope_update.json`
records the change explicitly; absent cases are not interpolated or inferred.
All cases retain both native energies
831.4778/848.698 eV and all four raw A/B(+/-M) states. Geometry, exact (200)
Bragg tilt, crystal-[001] magnetization and tensor rotation, eta=beta=1,
193-square detector grid, 64-subpixel fractional apertures, Coulomb factors,
energy conventions and normalization are identical to the original study.
Intensities are integrated before percentages. No post-edge correction,
fitting, energy shift or amplitude rescaling is introduced.

At cutoff 6.2, independent controls enlarge incoming only, outgoing only and
both bases to 4.6 (17 row / 59 [017] beams): at 8 nm with MS and 30 nm with BW.
BW also checks both bases at 8/100 nm. Depth nodes double to 513 at 100 nm
with both methods, plus 8/30 nm with BW. A targeted both-bases check at 12 nm
with BW/MS investigates its larger matched-method residual. FFT increases to
64 and MS maximum
step halves to .02 nm at 8 nm. Matched BW/MS at 30/100 nm additionally
checks the combined long-thickness propagation/basis discrepancy. Analytical
row BW is depth-exact; [017] BW retains its existing
numerical quadrature and is checked at doubled depth. The existing conservative
BW memory estimator requires fewer simultaneous detector workers at 59 beams;
the 2048 MiB budget is retained. Thicknesses remain sequential, precision is
float64/complex128 and compact per-engine checkpoints are atomic/resumable.

The memory guard initially rejected four simultaneous mixed-basis BW workers
at an estimated process peak of 2129.1 MiB. The script reduces detector-worker
concurrency with headroom for the existing allocation margin, RSS and reserve;
it does not change any physical or numerical parameter. A strict source-hash
equivalence check permits existing checkpoints only when the sole calculation
function change is that worker allowance. All other parameters and core hashes
must still match exactly. Original checkpoints remain byte-for-byte unchanged;
their pre-change hashes are recorded separately and the no-rerun behavior is
tested with a forbidden propagation callback.

Extra BW 6,10,14 nm cases test the local peak competitors. BW cases at 32,34,36
nm, together with 30 nm, test the first entrance-only sign-change brackets. MS
directly compares 8 and 12 nm at the final cutoff. These
are additional points on the existing 2 nm grid, not a 1 nm refinement.

The criteria remain .01 percentage points and .1% per raw detector state.
Both final consecutive short-thickness ladder increments (4.6 to 5.4 and 5.4
to 6.2), the final long-thickness increment, independent controls and matched
BW/MS comparison must pass. Missing required calculations produce
an incomplete gate, never a pass. The original 2.2 production results are not
retroactively relabeled as converged. A representative-condition pass does not
establish numerical convergence of the complete 0-100 nm curve.

## Numerical findings

There are 182 distinct saved engine cases, including the already completed
broader BW and [001] MS work. Each contains both channeling modes, both native
energies and all four reversal detector states. All completed checkpoints were
preserved, including across the worker-admission adjustment.

Maximum absolute PRB change over available, matched conditions (both edges,
entrance/double and BW/MS); raw errors are relative changes of individual
detector states, expressed here as percentages:

| Potential increment | [001] contrast (pp) | [017] contrast (pp) | [001] raw (%) | [017] raw (%) |
|---|---:|---:|---:|---:|
| 2.2 to 3.0 | .29057219 | .42833951 | .47875379 | .95007550 |
| 3.0 to 3.8 | .01929088 | .06335817 | .03673422 | .15384739 |
| 3.8 to 4.6 | .00917067 | .01607051 | .01781936 | .04218217 |
| 4.6 to 5.4 | .00097076 | .00429651 | .00164298 | .01241811 |
| 5.4 to 6.2 | .00046899 | .00176018 | .00078090 | .00405047 |

The final two increments pass .01 pp and .1% raw without relaxing either
threshold. Lower-cutoff [017] entries use the completed BW ladder and available
MS cases; they do not imply absent MS calculations were performed. At fixed
3.8 beam cutoff, the BW 20 nm [017] double L2 signal changes from 4.237580%
at potential cutoff 2.2 to 3.727320% at 6.2, a .510260 pp difference. Thus the
old two-thickness sensitivity check did not bound the error throughout the
old curve, even though the main peak ordering is robust.

The factors must be distinguished:

| Check | Largest contrast change (pp) | Largest raw change (%) | Conclusion at tested conditions |
|---|---:|---:|---|
| Final potential increments | .00429651 | .01241811 | Pass at fixed explicit basis |
| Incoming/outgoing/both basis controls | .00901932 | .03956347 | Adjacent increments pass; not a uniform joint-limit proof |
| FFT/slice/depth controls | .00037344 | .00113724 | Pass at the specified representative points |
| BW-MS, uniform 3.8 beam cutoff | .01598292 | .03094605 | Contrast fails |
| BW-MS, common 4.6 beam cutoff, 8/12 nm | .00503654 | .00887358 | Pass for these matched conditions |

In particular, the [017] 8 nm FFT 48-to-64 change is at most .00001305 pp
over both modes/edges, slice halving changes at most .00037344 pp, and the
largest depth control is .00009661 pp. They are substantially smaller than
the residual uniform-basis method difference. The corresponding [001]
depth/slice maxima are .00015836/.00011133 pp, with FFT differences at roundoff.

The remaining uniform-profile failures all concern L2:

| [017] thickness/mode | MS minus BW at beam cutoff 3.8 (pp) |
|---|---:|
| 12 nm double | -.01598292 |
| 30 nm entrance | -.01053816 |
| 100 nm entrance | +.01265960 |

FFT propagation retains surrounding harmonics outside the explicit event
basis, whereas BW elastic propagation is confined to its finite beam set.
Increasing potential support can therefore reveal a basis error that was
small at the original cutoff. This is a truncation issue, not evidence that
the two engines implement different intended physical models. At [017] 12 nm,
enlarging both bases from 37 to 59 beams changes BW L2 from 16.657240% to
16.649624% and MS L2 from 16.641257% to 16.644587%. The matched discrepancy
falls to .00503654 pp. Independent incoming/outgoing controls and actual
populations support the same interpretation. This does not prove an infinite
beam-basis limit; the next 81-beam BW set exceeds the current conservative
2 GiB admission estimate, so it was not executed or silently substituted.

For the common enlarged basis (17 row / 59 [017] beams), L3 percentages are:

| Geometry/method | Entrance 8 nm | Entrance 12 nm | Double 8 nm | Double 12 nm |
|---|---:|---:|---:|---:|
| [001] BW | -10.274345 | -11.857265 | -13.227773 | -9.917033 |
| [001] MS | -10.274366 | -11.857195 | -13.227787 | -9.916869 |
| [017] BW | -10.178247 | -11.655641 | -13.060083 | -9.691791 |
| [017] MS | -10.179719 | -11.655432 | -13.061032 | -9.688894 |

**The 12-to-8 nm ordering is stable in both methods and geometries.** The
additional BW 6/10/14 nm samples also retain 8 nm as the strongest checked
double-channel point. This supports the main interpretation, not a claim of
global peak-location convergence for a newly computed full curve.

At fixed 3.8 basis and cutoff 6.2, BW [001] entrance first zero brackets stay
30-32 and 34-36 nm. For [017], they are 30-32 and 32-34 nm; the second was
34-36 nm in the original profile. That weak zero region is not location-stable
to the original-to-new settings. No interpolated zero or MS zero-location
convergence is claimed. No checked double-channel samples reverse sign.

`beam_populations.csv` provides incoming/outgoing depth means, exit/entrance
populations in checkpoint NPZs, and excluded fractions. BW's zero excluded
fraction is a consequence of its finite unitary basis, not proof of basis
convergence. Small excluded populations likewise do not bound a small
interference difference. Magnetic-only asymmetry changes are exported
separately; their largest final-cutoff change is .00429446 pp and largest
adjacent-basis change .00901713 pp. They are not equated to raw PRB contrast.

## Gate, production recommendation and remaining limits

`convergence_gate.json` is complete but **fails** for the uniform 6.2 potential /
3.8 beam / FFT48 / 257-depth / .04 nm profile. All required reduced comparisons
exist. Potential-tail, adjacent-basis and FFT/slice/depth checks separately
pass, but BW/MS contrast must also pass. The raw-state criterion passes even
where the contrast criterion fails. `factor_status.json` preserves those
separate outcomes and the enlarged-basis agreement; no failed row is hidden
by averaging or changing the threshold.

A sensible **candidate for further production validation** is potential
cutoff 6.2, incoming/outgoing beam cutoff 4.6, FFT48, 257 depth nodes and maximum
step .04 nm, retaining all original detector/MDFF settings. It has good common-
basis method agreement at 8/12 nm and smaller independent discretization
changes. It is not a certified uniform production profile: common-basis MS at
4.6 was intentionally not expanded to 30/100 nm, consistent with the reduced
scope, and a larger-basis plateau was not demonstrated beyond 59 beams.

Do not resume a full voltage sweep or activate GUI integration on the premise
that the old gate now passes. The next focused step is to validate the uniform
enlarged profile, including the remaining entrance-channel discrepancies,
before expansion. Voltage-specific convergence still needs checking at each
voltage. No such expansion, GUI modification or packaging was performed here.

Convergence here concerns the specified finite projected-IAM/dipole model at
the tested geometries and thicknesses. It does not validate an absolute
cross-section or replace a genuine DFT-derived MDFF. HOLZ, absorption, TDS,
atomic-3D potentials and different detector/voltage conditions remain outside
this study. Two small final cutoff increments alone are insufficient evidence
unless basis, FFT, depth and propagation controls also pass.

## Outputs and validation

The calculation script is `scripts/ni_double_channeling_cutoff_study.py` with
sequential stages `bw`, `ms`, `controls`, `locations`. The analysis script is
`scripts/ni_double_channeling_cutoff_report.py`. Exact provenance mismatch
rejects reuse. `observables.csv` preserves raw intensities, magnetic/even
differences, both edges' signed PRB and magnetic-only percentages.
`differences.csv` records signed percentage-point and relative raw changes;
`beam_populations.csv` and checkpoint NPZs retain incident and reciprocal
outgoing populations. Outgoing diagnostics use the actual post-loss energies
at both physical detector centers. Full FFT outgoing populations include
harmonics outside the explicit inelastic basis; excluded populations are
reported, not renormalized away. `compact_results.npz` collects raw states.

Figures are calculated-data-only PNG/SVG: cutoff ladders, independent controls,
beam-population changes and peak/crossing locations. No uncomputed curves,
smoothed curves, voltage scans, GUI changes or Windows builds are included.

**39 focused tests passed in 14.24 s.** The five new checks cover unchanged
geometry/tensors/detectors under basis enlargement, FFT support and rejection
of insufficient sampling, signed integrated-raw comparisons, saved-data
precision/parity/outgoing norms, and reuse of an original checkpoint with a
propagation callback that raises if called. The existing focused BW, MS,
foundation and full-benchmark tests cover solver physics and preserved data.
No broad regression suite was run. `focused_tests.xml` stores the JUnit result.

`validation.json` records original-output/source and pre-fix checkpoint hash
preservation, required-case completeness, artifacts and software versions.
`delivery_provenance.json` records the final local commit and file hashes.
Only scripts, this report and focused tests are committed. Generated data stay
local; no push, package, release, GUI change or numerical-physics change was made.
