# True Ni [710] projected minor-zone (002) benchmark

This branch implements an actual [710]-oriented, z-independent projected IAM
potential and uses the existing BW and FFT propagation algorithms. It does not
relabel [001] waves. The earlier [001] results remain historical results, not
[710] evidence. All new outputs are under `outputs/ni_710_minorzone_mistilt/`.

## Crystallography and Fourier representation

The matrix mapping cubic Cartesian components to local components has rows

```
x = (0, 0, 1)
y = (1,-7, 0) / sqrt(50)
z = (7, 1, 0) / sqrt(50)
```

It is orthonormal, determinant +1, with x cross y = z. The conventional cubic
Ni row-vector cell is rotated as `A_local = A_cubic @ R.T`; fractional atomic
positions and genuine cubic hkl remain unchanged. Existing physical BW code
already accepts this rotated cell when the selected beams have local gz=0.
The old hk0-only beam enumerator is not used for [710].

The [710] ZOLZ is `7h+k=0`. With FCC selection, all indices have equal parity.
(002) belongs to it; (200) does not. The complete transverse set is
`hkl=(n,-7n,m)`, with m and n of equal parity. Its local reciprocal coordinates
are `(m/a, sqrt(50)*n/a)`, in cycles/Å. Beam sets include every allowed vector
inside the requested radial cutoff; no arbitrary beam cap clips a mirror pair.

A rectangular projected supercell has lengths `Lx=a`, `Ly=a/sqrt(50)`.
Its reciprocal mesh has steps `1/a`, `sqrt(50)/a`; forbidden opposite-parity
harmonics have exactly zero potential. Equivalently, a primitive reciprocal
basis is (002), (1,-7,1); the rectangular cell has twice its area. FFT harmonics
are mapped to actual `(n,-7n,m)` labels, not `(2m,2n,0)`. The kinetic operator
uses the actual local reciprocal vectors. Physical cutoff coverage is checked
against every allowed oriented harmonic, excluding Nyquist boundaries.

Fourier coefficients retain the existing `10*gamma*lambda*F_hkl/Omega`
normalization, conventional-cell structure factors and removed mean potential.
The first off-row modes, (±1,∓7,±1), have length `sqrt(51)/a`, about
2.027 cycles/Å. A 0.75 cutoff would therefore be a genuinely one-dimensional
projected potential. It is retained only as a separately labeled cutoff control;
production uses **2.2 cycles/Å**, which includes off-row couplings.

The FFT extension is optional through `projected_geometry`; default [001]
indexing, potential construction and propagation remain unchanged. A saved
pre-change [001] complex-wave baseline is bitwise equal after this extension.
Scientific checkpoint hashes conservatively change when solver source changes;
historical [001] checkpoints should be read with their recorded code revision.

## Reference, axes and physical limits

At 200 kV, the existing wavelength is 0.02507934045046928 Å. The local (002)
Bragg reference is `theta_x=-7.116725439974256 mrad`, `theta_y=0`.
`s002 = lambda/2*(|g002+k_perp|²-|k_perp|²)` is zero to roundoff there.
Zero local incident tilt is instead exact [710] zone-axis incidence.
All nine offsets from -2 to +2 mrad in 0.5 mrad steps keep local y=0.
The transmitted spot is always (0,0), target (002) is `(2/a,0)`, and the
[710] marker is `-k_perp`, with qy=0 and qx moving through the scan.
At Bragg it lies at the Thales circle center, not at transmitted (000).

A/B detectors remain `(g002/2, ±g002/2)`, radius `0.16*g002`; the Thales circle
has diameter (000)–(002). All map panels use real hkl, the [710] star and (000)
cross. Detector/circle positions do not follow the moving ZA marker.

The source remains the existing WIEN2k XMCD-effective dipole proxy. The same
matrices are defined **in the local frame**, with magnetic axial response along
local z=[710], eta=beta=1. This is not a claim that a full cubic-axis DFT tensor
has been rotated or that orientation-dependent Ni XMCD has been validated.
The scalar source has no complete directional complex transition information.
The native source axis remains 823.625–882.521 eV; requested reference samples
are 852.698 and 870.004 eV, not inferred experimental peak alignment.

This is a z-independent projected IAM model, not atom-layer-resolved 3D
multislice. HOLZ, exit channeling, absorption/TDS and a genuine finite-q DFT MDFF
remain absent. Agreement of the two solvers does not validate quantitative Ni.

## Limited convergence controls and measured symmetry

Controls are one-dimensional comparisons, not a Cartesian parameter sweep:

- BW beam cutoffs 2.2, 3.2, 4.5 cycles/Å give 15, 27, 57 beams, at fixed
  physical potential cutoff 2.2. Complex amplitudes, phase-aligned errors and
  coherences are compared on the common inner 15 channels; selected EMCD
  observables use each **full** propagation basis.
- FFT meshes 16, 32, 64 keep the physical potential cutoff 2.2 and the same
  inner 15-channel inelastic comparison. Full FFT propagation is retained;
  raw projection leakage is recorded and never renormalized away.
- Potential cutoffs 0.75, 2.2, 3.2 are compared separately with the same
  57-beam BW basis. This changes the physical truncated potential.
- A targeted FFT step change 0.04 to 0.02 nm uses FFT32 and the production
  27-channel comparison. Selected control contractions use detector grid17,
  fractional64 and depth64 throughout; production maps/spectra use grid33.

For the fixed 2.2 potential, the 27-to-57 basis change gives common-coherence
absolute Frobenius error 5.28e-6 and maximum common-wave amplitude difference
5.97e-5. The selected L3 magnetic detector difference changes about 0.0020%.
The 15-to-27 change is larger, about 0.724% in that magnetic difference.
FFT32 versus FFT64 gives common-coherence absolute error 5.28e-10 and maximum
amplitude difference 8.65e-9; FFT16 is measurably less accurate despite covering
the physical potential coefficients. Mesh refinement is not cutoff refinement.
Step refinement reduces the BW/MS coherence error from 2.12e-5 to 9.85e-6.

The magnetic result is **not potential-cutoff-converged**: at fixed 57 beams,
the selected L3 detector difference is 5.1282e-4, 6.4945e-5 and 5.0781e-5 for
potential cutoffs 0.75, 2.2 and 3.2, respectively. The latter change is about
21.8%. Production at 2.2 is a controlled matched-potential comparison, not a
converged magnetic prediction. No monotonic decrease of contamination is assumed.

Intrinsic nonmagnetic A−B is measured from reversal-even spectra **before**
post-edge processing. In these controls it is zero or roundoff, around 1e-18
in model intensity units, for the full bases and the separate strict two-beam
reference. It is not forced to zero in the code.

There is a symmetry explanation within this model: y reflection maps
`(h,-7h,l)` to `(-h,7h,l)`, preserving FCC selection, radial cutoffs and the
projected IAM coefficients. At local y tilt=0, the kinetic operator and full
radial-cutoff basis preserve that reflection. The isotropic even tensor and
mirrored detector weights consequently preserve even A/B equality, also under
horizontal x mistilt. This does not assert a corresponding cancellation for
all 3D experimental scattering or for an unverified anisotropic DFT MDFF.
Finite resolution cannot be credited with restoring a symmetry already present.

## How two-beam-like is the exact Bragg candidate?

The declared strict criterion is no more than **5% of incident intensity outside
000/002 at every saved depth**. It fails: the production reference has pair exit
population 99.4307%, depth-average 94.5007%, and maximum sampled competing
population 10.5726%. It is strongly two-beam-dominated at exit but is not an
isolated two-beam wavefield throughout the specimen. No competitors are removed.

Strong competitors at the reference (BW percentages of incident intensity):

| Reflection | s_g (Å^-1) | Exit (%) | Depth average (%) | Sampled maximum (%) |
|---|---:|---:|---:|---:|
| (0,0,-2) | +0.008078008 | 0.028881 | 3.508172 | 8.324920 |
| (0,0,4) | +0.008078008 | 0.453317 | 1.744276 | 4.374058 |
| (0,0,-4) | +0.024234025 | 0.033169 | 0.117839 | 0.369441 |
| (1,-7,1) | +0.049477802 | 0.002364 | 0.008042 | 0.018662 |
| (-1,7,1) | +0.049477802 | 0.002364 | 0.008042 | 0.018662 |

The target (002) has exit population 5.9222% and depth-average 51.1873%;
000 has exit 93.5085% and depth-average 43.3134%. Thickness oscillations make
the exit pattern alone insufficient for entrance-channeling classification.
`reference_competing_reflections.csv` includes every production beam.
`ideal_two_beam_reference.csv` is explicitly the separate strict 000/002 basis.

## Reproduction and outputs

With the `emcd-python` environment, from the repository root:

```powershell
$env:PYTHONPATH='src'
python -m emcd_sim.ni_710_mistilt --controls-only
python -m emcd_sim.ni_710_mistilt
python -m emcd_sim.ni_710_mistilt --plot-only
```

CLI options include start/stop/step, thickness, basis/potential cutoffs, FFT mesh,
slice/depth/detector settings, energy points, source and output. Nonzero local y
is rejected for this horizontal scan. Per-case checkpoints verify complete
provenance and hashes; plot-only uses saved waves/spectra and selected maps.

Production settings: 200 kV, 30 nm, 27 full BW/common inelastic beams at cutoff
3.2, FFT32, potential2.2, maximum step0.04 nm, depth64, detector33, fractional64.
The inelastic dense-array estimate is about 48.5 MiB, below 512 MiB. Each
method propagates once per mistilt; its coherence is reused across 243 common
energies and both selected edge maps. No full energy-resolved map cube is made.

Main artifacts:

- `geometry_validation.json`: frame, indexing, physical settings, reference
  excitation errors, ZA and detector coordinates, projected-cell mapping.
- `basis_convergence.csv`, `fft_mesh_convergence.csv`,
  `potential_cutoff_convergence.csv`, `slice_step_convergence.csv` and figures.
- `reference_two_beam_quality.json`, `reference_competing_reflections.csv`,
  and the separately labeled `ideal_two_beam_reference.csv`.
- `mistilt_maps.npz` arrays `[mistilt, method, edge, qy, qx]` and
  `mistilt_eels.npz` arrays `[mistilt, method, energy]`, plus labels and grids.
- `mistilt_summary.csv` and `comparison_metadata.json` record signed magnetic
  and even signals, asymmetries, undefined ratios, normalization and BW/MS errors.
- Shared-scale 3×3 L3/L2 magnetic, nonmagnetic, total and corrected mosaics for
  both methods; `emcd_and_bw_ms_vs_mistilt.png` and combined EELS figures.
- Nine individual `case_*` directories: full two-method EELS with both reversal
  states, raw/odd/even/corrected/residual arrays, alpha and validity masks;
  selected angular arrays, full propagation checkpoint and metadata;
  `virtual_detector_eels.png`, `L3_angular_maps.png`, `L2_angular_maps.png`.

Post-edge alpha is observed independently from each case/method's own +M A/B
integrals over 878–882 eV, with the existing exact-endpoint interpolation.
Intrinsic odd/even maps are not scaled. Near-zero original even signals make
relative even suppression undefined; NaN/null is retained, not replaced by zero.
All NPZ files are numeric/Unicode/bool and load without pickle.

Focused tests check the frame and actual hkl, Bragg condition, fixed y, ZA and
Thales geometry, FFT Fourier-coefficient equality at fixed cutoff, short-wave
phase/sign and amplitudes, mirror symmetry and selected-map/EELS reconstruction.
Existing [001] driver/overlay/independent-wave checks are also run, without a
broad regression suite. Old output hashes and the exact [001] FFT baseline are
recorded under the new output directory for preservation validation.

## Completed production sweep

All nine offsets have selected L3/L2 maps, full 243-energy EELS for both
methods and both reversal states, individual figures, and validated checkpoints.
Here are the signed BW detector asymmetries (percent, not fractions):

| Delta x (mrad) | L3 magnetic (%) | L2 magnetic (%) |
|---:|---:|---:|
| -2.0 | -0.014773 | -0.003618 |
| -1.5 | +0.011560 | +0.002851 |
| -1.0 | +0.071537 | +0.017597 |
| -0.5 | +0.130539 | +0.032098 |
| 0.0 | +0.154509 | +0.037977 |
| +0.5 | +0.129114 | +0.031720 |
| +1.0 | +0.065622 | +0.016113 |
| +1.5 | -0.009387 | -0.002311 |
| +2.0 | -0.064514 | -0.015847 |

Magnetic response peaks at the sampled exact Bragg reference and changes sign
toward both scan extremes. Intrinsic nonmagnetic detector differences remain
within ±3.47e-18 across methods and selected energies; those tiny signed values
are roundoff, not a physical contamination trend. Complete mirror-symmetric
finite bases preserve the cancellation; the code does not impose it on results.

The largest full-grid BW/MS magnetic-map relative L2 difference is **0.04141%**;
coherence relative differences are at most **0.003198%**. Detector-map integration
reconstruction error is at most 5.01e-18. These compare the matched 2.2-cutoff
models and do not resolve the much larger physical-potential-cutoff sensitivity.

Observed alpha ranges from 0.99992568 to 1.00017828. Even with almost unit
scaling, the magnetic source tail in the normalization interval means alpha is
not exactly the even-only value 1. At Bragg, BW unprocessed/corrected differences
are 6.51047e-5 / 6.13559e-5 at L3 and 6.97773e-7 / 5.34116e-7 at L2. The corrected
values are 5.76% and 23.45% below the unprocessed magnetic references. The
processed magnetic component itself changes only about +0.00891%; the main
change is the induced even residual (−3.75460e-6 and −1.63720e-7). Thus a small
alpha departure can bias weak magnetic signals even where intrinsic even
asymmetry is absent. Relative suppression of an original zero even difference
is undefined and is retained as NaN/null.

Fourteen focused tests passed: four [710] geometry/physics checks, four existing
[001] mistilt-driver checks, three existing overlay checks, and three existing
independent-wave checks. The nine-case plot-only path was exercised with forward
calculation disabled; saved physical arrays were unchanged. All generated NPZ
files were loaded without pickle. The 122 earlier output files retained their
exact hashes, and the pre-extension [001] wave baseline remained bitwise equal.
`validation_summary.json` records these checks. No old [001] result is relabeled
or replaced, and no global convergence or isolated two-beam claim is made.

Raw/corrected contrast panels use the same color limits, including across
methods and mistilts. A final rendering-only revision made those limits shared
and clarified individual EELS energy/tilt labels. The execution source and JSON
metadata were retained in `render_revision_backup/`; `render_only_revision.json`
records an exact AST comparison proving all non-plotting code unchanged,
unchanged physical-NPZ hashes, and the corresponding provenance revision.
Figures were then regenerated with forward calculation disabled.
