# Ni PRB 2007 geometry, aperture and depth validation

Results: `outputs/ni_prb2007_geometry_validation/`. The completed [017]
0-100 nm study is reused unchanged. New thickness curves retain 2 nm spacing.
All generated data remain local. There is no GUI redesign, MDFF rescaling,
1 nm refinement, executable rebuild or release.

**Atomic-3D scattering is unavailable on this branch.** Inspection found only
P1 atomic geometry and integration boundaries. Part D therefore supplies
structural checks and an exact interface-readiness report, not fabricated 3D
diffraction/EMCD numbers. No full atomic-3D scan or Figure 6 was generated.

## Reference and geometry choices

[Rusz, Rubino and Schattschneider, PRB 75, 214425 (2007), manuscript](https://arxiv.org/pdf/0704.1407),
DOI 10.1103/PhysRevB.75.214425: Section III and Figure 5(c) specify fcc Ni,
the [001] vicinity, a (200) systematic row, row-projected Laue center G/2,
opposite Thales positions and difference/sum normalization. The theory includes
incoming and outgoing Bloch waves; Figure 5 excludes absorption. Numerical
voltage, exact off-row tilt and precise Figure 5 evaluation energy were not
established from the inspected manuscript. Its favorable Ni thickness is about
6-10 nm; 15-20% is only an approximate literature magnitude, not a fitting target.

Study choices, explicitly distinguished from verified reference settings:

| Setting | This calculation |
| --- | --- |
| Voltage / wavelength | 200 kV / approximately 0.02507934 Angstrom |
| Material | FCC Ni, a=3.524 Angstrom, IAM, B=0 |
| Nominal frame [001] | x=[100], y=[010], z=[001] |
| Incident tilt | (-7.116725439974256, +35) mrad; y chosen approximately 2 degrees off row |
| Target excitation | s200=0 to numerical precision |
| Row Laue-center projection | (0.283768444948922, 0) cycles/Angstrom |
| Full Laue center / projected ZA | (0.283768444948922, -1.395570990757259) cycles/Angstrom |
| Transmitted beam | (0,0) in transmitted-centered coordinates |
| Detectors A/B | G/2 +/- perpendicular(G)/2, derived from each actual local G |
| A/B numerical centers | (0.283768444948922, +/-0.283768444948922) cycles/Angstrom |
| Reference aperture | radius 0.0908059024 cycles/Angstrom |
| Primary [001] approximation | 11 row beams, (-10,0,0) through (10,0,0) in steps of 2 |
| Explicit full-[001] control | 97 FCC ZOLZ beams, no row Fourier projection |
| [017] comparison | Original 27-beam, full oriented ZOLZ, local y tilt zero |
| Beam / potential cutoff | 3.2 / 2.2 cycles/Angstrom, unchanged |
| FFT | 32x32, maximum physical split step 0.04 nm |
| Source magnetization | Crystal [001], rotated by the actual orientation matrix |

The full Laue center is **not** silently identified with its row projection.
In the row approximation only the G direction is retained. The off-row tilt
and off-row degrees of freedom are deliberately distinguished. Detector
coordinates happen to equal those of [017] because both frames place (200)
along local x with the same lattice parameter; they were recomputed, not copied
as an assumption of equivalent crystal geometry. Neither orientation nor
magnetization is optimized to match a published percentage.

The narrowly scoped source addition is the optional
`fft_multislice_ni(..., systematic_row_hkl=(2,0,0))` argument. It projects the
**potential Fourier series** onto the row, keeping higher row harmonics. The
BW row basis makes the corresponding explicit approximation. This is neither
an FCC extinction rule nor a strict two-beam truncation. The default `None`
keeps the original full projected IAM potential and reproduces saved [017]
FFT amplitudes byte-for-byte. No Hamiltonian, FFT propagation step, MDFF,
Coulomb factor or published default result was changed.

## Fixed energies and normalization

Both orientations retain the active saved XMCD source SHA256
`a0e28ea6423b6c7832bb3cce6d69d71aa59336a221baeee3d2556b49ba501283`, eta=beta=1.
The fixed native energies are **831.4778 eV (L3)** and **848.698 eV (L2)**.
These are the previous study's energy definitions, not newly peak-tracked
samples or a claim of matched experimental calibration.

Primary signed percentage is `100*(A_plus-B_plus)/(A_plus+B_plus)`.
Diagnostics are `100*(M_A-M_B)/(N_A+N_B)` and
`100*(N_A-N_B)/(N_A+N_B)`, using original magnetization reversals.
No factor two, post-edge correction, independent scaling or fitting is applied.
At 0 nm raw intensity is zero and percentages are undefined. Raw paired
contrast can include reversal-even imbalance; a larger raw percentage need
not mean stronger magnetic EMCD.

## A. Thickness and geometry findings

At the matched coarse 33x33 integration grid, radius 0.0908059024, 64 depth
nodes, fixed L3 energy (signed percent):

| Thickness (nm) | [001] row BW | [001] row MS | Saved [017] BW |
| ---: | ---: | ---: | ---: |
| 10 | -11.38974542 | -11.38971729 | -11.22445738 |
| 12 | -11.77570914 | -11.77570759 | -11.58068666 |
| 30 | -0.41834078 | -0.41841564 | -0.36256678 |
| 50 | -3.42560100 | -3.42564290 | -3.34777967 |

Both geometries' sampled maxima occur at 12 nm, with similar magnitude
(approximately 1.68% difference between those BW peak magnitudes). The new
row result remains below the approximate reference magnitude and its peak
thickness differs. This is a geometry/normalization benchmark, not quantitative
reproduction of the paper's full theory. Maximum row BW-MS differences are
0.000150965 pp (L3) and 0.000256202 pp (L2). Row reversal-even imbalance is
numerical zero; raw and magnetic-only percentages coincide in this symmetric
row model. The rotated [017] tensor does not in general have the same +M and
even-sum denominators, so those two percentages remain distinct there.

Competing row reflections are measurable. Excitation errors of -200 and 400
are +0.008078008445 inverse Angstrom; their largest BW exit populations reach
8.2768% at 36 nm and 6.27795% at 88 nm. The minimum 000+200 exit fraction is
89.4774%, and minimum depth-average pair fraction is 93.6328%. This is not an
isolated two-beam wavefield. `elastic_001.csv` records all retained row beams.

The initially calculated **full-[001]-ZOLZ control** is separately retained
under `full_001_zolz_control/`, with all 97 beams and exactly the same tilt,
source and detectors. Its largest L3 raw BW value is -31.05201% at 16 nm,
but magnetic-only is -10.51137% and even imbalance is -21.59359% there.
Thus full off-row propagation is not equivalent to the paper's row
approximation; the large raw number is not an intrinsic magnetic enhancement.
This control was preserved rather than adjusted to resemble the reference.

## B. Aperture averaging and detector-grid convergence

Radii 0.03, 0.06, 0.0908059024 and 0.12 cycles/Angstrom correspond to
collection semiangles **0.752380, 1.504760, 2.277352 and 3.009521 mrad** at
200 kV. All are fully inside the detector grid. Centers are held fixed for
all thicknesses and radii. BW and MS are calculated at 10, 12, 20, 30, 50 nm;
no additional full aperture-thickness series was needed.

Main aperture calculations use 193x193 over [-0.5,0.5] cycles/Angstrom,
fractional weights with 64 subpixels. The smallest diameter spans 11.52
pixels, versus less than one pixel on the old 33x33 [-1,1] grid. Pixel batches
evaluate the existing tensor kernel directly, without intensity interpolation.

At 12 nm, BW results:

| Radius | [001] row L3 (%) | [017] L3 (%) | [001] row L2 (%) | [017] L2 (%) |
| ---: | ---: | ---: | ---: | ---: |
| 0.03 | -12.156596 | -11.955791 | +20.621529 | +20.610295 |
| 0.06 | -12.046891 | -11.847726 | +20.435236 | +20.425813 |
| 0.0908059024 | -11.853783 | -11.657545 | +20.107407 | +20.100965 |
| 0.12 | -11.589885 | -11.397719 | +19.659572 | +19.656818 |

Increasing radius from 0.03 to 0.12 reduces the 12 nm L3 magnitude by
4.66% ([001]) / 4.67% ([017]); L2 reductions are 4.66% / 4.63%.
The reference radius reduces magnitudes by about 2.5% relative to 0.03.
Integrated A/B intensities and magnetic-only percentages are exported for
every case, rather than equating intensity loss with contrast loss.

At 12 nm, independent grids 97/193/385 check all radii and both solvers.
193 versus 385 differs by at most **0.000612785 pp** in raw dichroism and
**0.006042%** in A/B intensity; maximum 193-grid circle-area error is
0.001372%. This supports the fine-grid aperture calculation at the tested
point; it is not proof of global physical convergence at every thickness.

Detector **area** accuracy alone does not establish intensity-field quadrature
accuracy. For example the reference-radius [001] L3 value at 12 nm changes
from -11.775709% on the old coarse grid to -11.853783% on the fine grid.
The main thickness curves deliberately retain the coarse matched setting to
compare directly with the preserved [017] series. Their peak values should
not be presented as fully detector-grid-converged numbers.

## C. Depth quadrature

The 64-node [017] states are reused from the original scan. New 128/256-node
checks cover 12, 30, 64 and 100 nm, for both solvers and both edges. A
diagnostic analytic integral of the **same finite BW Hamiltonian** supplies
an independent BW reference; it changes no propagation or physical model.
512-node checks are triggered at 12, 64 and 100 nm because the 256-node
PRB error exceeds 0.0001 pp or detector-intensity relative error exceeds
1e-6. The 30 nm point does not trigger that extension.

Maximum BW PRB error across these thicknesses and both edges:

| Nodes | Maximum absolute error (pp) | Maximum A/B intensity relative error |
| ---: | ---: | ---: |
| 64 | 0.003224626 | 0.004489% |
| 128 | 0.000765612 | 0.001510% |
| 256 | 0.000188743 | 0.000358% |
| 512 (three tested thicknesses) | 0.000046932 | 0.000089% |

The declared local trend criterion is 0.01 pp PRB, 0.1% detector intensity
and 0.1% magnetic-difference relative error where the reference magnetic
signal exceeds 5% of the tested peak. **64 nodes pass this trend criterion**;
the largest eligible magnetic-difference relative error is 0.03710%.
No complete [017] rerun is justified for these main trends.

Near crossings, use absolute errors. At 64 nm, BW L3 is +0.00171747% at
64 nodes versus the analytic +0.00361569%: the relative error is large even
though the absolute error is only 0.00189822 pp. Relative PRB and magnetic
errors are masked below explicit 5%-of-tested-peak signal floors in
`depth_convergence.csv`; undefined does not mean zero. That file also records
absolute magnetic differences and individual A/B intensity changes.

Recommend **256 nodes** for more accurate routine comparisons at the tested
thicknesses, and **512** for a BW depth-error target around 1e-4 pp at long
thickness. These are local numerical recommendations, not a new full-series
convergence claim. At 100 nm the 64-to-128 change is nonmonotonic; comparing
only adjacent coarse quadratures can therefore be misleading.

MS is compared against its own highest sampled node count in the CSV; that
reference is not asserted exact. Figure 4 additionally plots both methods
against analytic BW and labels the MS propagation-error contribution. Changing
observation nodes also changes the actual subdivisions below the 0.04 nm
maximum. A separate 100 nm, 512-node control reduces that maximum to 0.02 nm:
the L3 MS-BW difference falls from about 0.00008350 to 0.00001220 pp, and
the L2 difference from about 0.00014198 to 0.00002067 pp. Thus remaining
BW-MS discrepancies cannot all be assigned to depth quadrature. No error
floor was removed by fitting.
The nearly vanishing MS-minus-analytic BW L3 difference at the smaller step
is cancellation of finite-quadrature and propagation errors, not proof of
exact integration.

## D. Atomic-3D readiness instead of invented scattering

`atomic_multislice_geometry.py` explicitly implements P1 structure only;
`multislice_reference.py` builds a z-independent projected potential. There
is no finite-z atomic potential integrator, slice potential cache,
slice-dependent transmission or atomic-3D propagator to invoke.

The actual oriented [017] cell has 50 Ni atoms, 50 planes and a
12.459221484507 Angstrom repeat. Plane-aware slice geometry at 10/12/30/50 nm
covers each requested thickness exactly, with 402/482/1204/2007 slab atom
centers and 410/492/1229/2048 physical intervals. Atomic positions and
boundaries are exported. These checks establish structural geometry only:
periodic **potential** construction and total integrated electrostatic
potential remain unverified and explicitly undefined.

The inelastic interface already accepts a finite Hermitian coherence matrix
in the ordered common hkl basis. What is absent is an atomic-3D producer of
the potential, psi(z,g), validated 3D-to-ZOLZ harmonic mapping and C_gh.
Finite atomic tails, slab termination, potential/phase units, HOLZ leakage
and site/depth weighting must also be validated before claiming 3D EMCD.
Repeating the same projected potential per slice would not fill this gap.
Figure 5 therefore shows real atomic geometry and labeled existing projected
BW/MS points, with no 3D curve. The potential-model effect on thickness
dependence cannot yet be determined.

## Outputs, checks and reproduction

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
python scripts/ni_prb2007_geometry_validation.py --full-zolz-control
python -m pytest tests/test_ni_prb2007_validation.py -q
```

Default memory budget is 2048 MiB; `--memory-budget-mib` supports the existing
512/1024/2048/4096/8192 choices. Calculations are sequential, use existing
RAM/RSS admission checks and compact per-point NPZ checkpoints, then release
wavefields. Only supported detector pixels are evaluated in batches of 64;
no basis, cutoff, sampling or precision is reduced to fit memory. Weights
are prepared once per detector/grid and shared across energies/reversals.
All arithmetic remains float64/complex128. This batching agrees with the
existing public contraction to approximately 1e-17 intensity units.

The script resumes matching compact checkpoints. Use `--output` for a fresh
directory. `--full-zolz-control` includes the separate full-[001] control;
it does not replace the primary row approximation. Replotting/resummarizing
completed checkpoints requires no scattering rerun. Results include:

- `results.csv` / `results.npz`: fixed-energy raw states, N/M components,
  percentages, denominators and per-case settings.
- `configuration.json`: complete frames/hkl/g/excitation errors, tilts,
  Thales positions, ZA/Laue coordinates, detector geometry, source/code hashes,
  models, budget and scientific distinctions.
- `elastic_001.csv` and `full_001_zolz_control/`: row/full diffraction controls.
- `aperture_grid_convergence.csv`, `aperture_suppression.csv`,
  `depth_convergence.csv`, `fft_step_control.csv` and `summary.json`.
- `atomic_3d_readiness.csv/json`, `atomic_geometry_only.npz`: truthful P1
  capability/structural data, without 3D scattering intensities.
- Figures 1-5 as PNG and SVG: L3/L2 geometry curves, aperture dependence,
  quadrature and the unavailable-3D disclosure. No smoothing or fitting.
- `preservation.json`: hashes verifying the original [017] study is unchanged.

Seven focused tests pass: oriented Bragg/Thales geometry and tensor reversal,
batched/public kernel equivalence, analytic/dense quadrature agreement,
aperture support/area/weight bounds, row FFT/BW behavior and invalid inputs,
byte-identical legacy FFT amplitudes, and completed output/3D-status checks.
No broad regression suite, GUI packaging or full MDFF work was performed.

Approximate XMCD-derived MDFF, omitted outgoing channeling, native energy
calibration, finite IAM potential/basis/FFT cutoffs, finite collection apertures
and the explicit row approximation remain barriers to quantitative agreement
with the reference. Close BW-MS agreement checks the shared chosen model;
it does not remove these physical limitations.
