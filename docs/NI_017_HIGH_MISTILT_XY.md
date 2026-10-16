# Ni [017] high-mistilt X/Y study

This study extends `ea3e42af600019be421379cd6922a9dc47b36658` on the
separate `feat/ni-017-high-mistilt-xy` branch. All numerical artifacts are
local under `outputs/ni_017_high_mistilt_xy/`; the historical [017]/[710]
directories are protected by a SHA256 manifest and are not rewritten.

## Physical model and coordinates

FCC Ni, a=3.524 angstrom, 200 kV, 30 nm. Rows of the proper rotation R are
[100], [0,7,-1]/sqrt(50), and [0,1,7]/sqrt(50). The actual rotated crystal
and projected IAM obey k+7l=0 with FCC parity, including odd off-row beams.
The projected rectangular FFT cell is a by a/sqrt(50); integer FFT modes
(m,n) correspond to cubic (m,7n,-n). The complete radial BW basis is used;
no propagation is restricted to an ideal two-beam subspace.

Magnetization is fixed at cubic [001], or local
(0,-0.1414213562,0.9899494937). The existing XMCD-effective Hermitian tensor
is reversed in the cubic frame before applying R T R^T. Eta=beta=1.
The core MDFF contraction, Coulomb factors, elastic Hamiltonian and FFT
propagator have not been changed by this study. The geometry API adds an
optional `y_offset=0` argument; old default calculations retain y=0.

At the (200) reference, theta_x=-7.116725439974256 mrad, theta_y=0.
The scan axes are offsets: theta_x=theta_Bragg200+delta_x and
theta_y=delta_y. In transmitted-beam-centered cycles/angstrom coordinates,
ZA=-k_incident,perp. The transmitted beam, (200) spot, physical A/B
apertures and (000)-(200) Thales circle stay fixed. Only the ZA marker
moves with tilt; out-of-frame coordinates are printed rather than moved.
Fixed Thales detectors need not be optimal at a different dominant reflection.

## Scan registry and provenance

The horizontal scan has 13 points: -10 to +10 mrad in steps of 2, plus
programmatically computed delta_x=theta_Bragg200 (exact paraxial 400 Bragg)
and delta_x=-theta_Bragg200 (zero absolute tilt, [017] incidence).
The vertical scan has 13 points, -30 to +30 mrad in steps of 5 at delta_x=0.
The 5x5 grid uses x=[-10,-5,0,5,10] and y=[-25,-10,0,10,25] mrad.
The union is 43 unique pairs; the registry references one canonical case
for every overlap. Special offsets remain separate from the regular grid.

Production starts with potential cutoff 2.2 cycles/angstrom, BW cutoff 3.2
(27 beams), FFT32, maximum step 0.04 nm, 64 depth nodes, detector grid33,
and fractional aperture resolution64. The estimated single dense pair
array is 48.45 MiB, below the 512 MiB guard. This is a per-array estimate,
not a total process-memory prediction. FFT amplitudes are never rescaled
after projection. The wave and coherence are calculated once per tilt and
method, then reused across energies and magnetization states.

The energy grid has 243 samples: 241 uniformly spaced points spanning the
unchanged source range 823.625-882.521 eV, plus exact native magnetic
features L3=831.271 and L2=848.698 eV. The established interpolation of the
source spectrum is retained. This preserves the native energy coordinate;
it does not claim experimental calibration or use all 4329 source samples.
No source shift or per-peak intensity scaling is applied. Post-edge
normalization uses only observed +M detector A/B integrals over 878-882 eV.
The source and raw-edge audit inputs are hashed in provenance.

Checkpoints include complex BW/MS amplitudes, coherences, both reversal
states, spectra, selected maps, weights and alpha. Source, numerical code,
configuration, X/Y coordinates and checkpoint checksum must agree before
reuse. Plotting code is outside the numerical signature so figure-only
changes do not invalidate physical data. Plot-only checks the numerical
signature, loads checkpoints, and never calls propagation or contraction.

## Definitions and output arrays

Intrinsic I_mag=(I_plus-I_minus)/2 and I_nonmag=(I_plus+I_minus)/2 are
separate from paired maps and spectra. D_mag=M_A-M_B, D_nonmag=N_A-N_B,
D_raw=D_mag+D_nonmag. The intrinsic even difference is not the scaled
even residual. With observed alpha, D_corrected=I_A_plus-alpha I_B_plus,
whose components are M_A-alpha M_B and N_A-alpha N_B. Both are saved.
Explicit normalized A and alpha*B spectra are also saved.
Paired-difference angular fields use the established A-supported,
y-reflected B pairing. White pixels outside that valid aperture support
are masked, not zero-valued contrast over the whole reciprocal plane.

Intrinsic and corrected asymmetries use Sigma_ref, the reversal-averaged
A+B intensity. `raw_asymmetry_sigma_ref` uses that common denominator;
the legacy `raw_asymmetry` retains +M A+B and is labeled separately.
Fractions are used unless a field explicitly ends in `_percent`.
Metrics below a relative intensity floor are undefined, not set to zero.

The relative ideal shot-noise proxy is abs(D_mag)/sqrt(Sigma_ref).
It uses the same per-atom intensity normalization at every tilt; it is not
an absolute SNR, dose requirement, or experimental detection limit.
Signed and absolute edge integrals use separate +/-5 eV windows around
the two native features, with exact linearly interpolated endpoints.
Opposite-sign L3/L2 contributions are never silently summed.

Every case contains `checkpoint.npz`, `angular_maps.npz`,
`virtual_detector_eels.npz`, full EELS figure, L3/L2 six-column angular
figures, a diffraction figure, and metadata. Angular figures contain
magnetic/even/total, raw/corrected paired contrast, and scaled even residual,
using common scales across the entire study. Individual EELS plots retain
raw units and distinguish intrinsic parity from normalization artifacts.

`aggregate/all_cases_maps.npz` and `all_cases_eels.npz` carry explicit
pair coordinates, including horizontal special points. Regular-grid
`aggregate/mistilt_maps.npz` axes are
[delta_y,delta_x,method,edge,qy,qx]; regular spectra axes are
[delta_y,delta_x,method,energy]. `xy_metrics.npz` uses
[delta_y,delta_x,method,edge]. Method order is BW then FFT multislice;
edge order is L3 then L2. Coordinate, label and scalar arrays have their
natural lower-dimensional axes. All NPZ files load without pickle.
Colored squares display values only at the 25 actual nonuniform X/Y-grid
coordinates. Other 1D cases remain separate; no interpolation is used.

## Focused validation and convergence policy

Preflight independently compares BW and FFT at short high-tilt trajectories,
checks the proper frame and fixed magnetization, derives excitation errors
from each actual microscope tilt, and verifies the y-reflected potential
and basis closure. Because g200,y=0, numerical s200 is independent of y;
off-row excitation errors vary. The nonmagnetic mirror relation compares
independent +y/-y results over the full energy grid, without imposing it.
The magnetic response is assessed separately because fixed M has local y.

Cheap BW27/BW57 preflight at all 43 orientations finds a worst common
coherence change of 0.218% near (5,+/-25) mrad. Representative selected-energy
controls therefore include those points in addition to the five requested
orientations and coarse-scan extrema. They compare potential cutoffs
2.2/3.2, BW27/57/81/121, FFT32/64 and a halved slice step at the larger cutoff.
All control contractions use detector grid17 consistently and are compared
within that grid, rather than directly against production grid33.
FFT64 is required for the BW81 propagation channels; FFT32 is compared
only on the common BW57 basis. Every matched BW/MS comparison uses the
same physical potential. No projected amplitude renormalization is used.

Excellent agreement between solvers establishes numerical agreement for
the matched discretized model; it does not establish physical-potential
convergence. Detector-grid, depth quadrature and global potential-cutoff
convergence are not exhaustively established by these limited controls.

## Reproduction

From the repository, use the established Python environment with numpy and
matplotlib, set PYTHONPATH=src, and limit BLAS/OpenMP threads to one for
these small dense contractions. No new dependencies are needed.
The local audited `Ni_fm.xmcd`, raw1/raw2, broad1/broad2, rawxmcd, inso,
injoint and inc inputs must be present in `data/wien2k_ni/`. Their hashes
are recorded; this patch does not commit or alter the user's local WIEN2k
inputs. A fresh clone requires those same audited source files.

```powershell
$env:PYTHONPATH='src'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
python -m emcd_sim.ni_017_high_mistilt_xy --scan all
python -m emcd_sim.ni_017_high_mistilt_xy --scan x --no-plots --skip-convergence
python -m emcd_sim.ni_017_high_mistilt_xy --scan y --no-plots --skip-convergence
python -m emcd_sim.ni_017_high_mistilt_xy --scan xy --no-plots --skip-convergence
python -m emcd_sim.ni_017_high_mistilt_xy --scan all --plot-only
```

Validated resume is always on (`--resume` is accepted explicitly).
Use `--x-list`/`--y-list` for custom scan lists. Physical/numerical options
include potential/beam cutoffs, FFT grid, maximum slice step, thickness,
depth steps, detector grid, energy-point count and output directory.
A changed physical/configuration signature requires a new output directory.

## Scope

These are model-level results for projected IAM elastic scattering,
entrance-only channeling and an XMCD-effective tensor. They omit outgoing
channeling, HOLZ, atom-layer 3D propagation, TDS/absorption, complete complex
DFT MDFF and absolute detector-dose calibration. High-tilt optima remain
conditional on the finite basis, fixed original detectors and unresolved
global physical-potential convergence. They are not quantitative
experimentally validated Ni EMCD predictions.

## Completed results

All 43 unique pairs completed with both methods, both reversal states, 243
spectral samples and both selected angular energies. The three scan lists
contain 13, 13 and 25 entries but share canonical cases. The following are
BW extrema over those 43 sampled orientations at production cutoff 2.2;
they are not continuous-orientation or globally converged optima. MS gives
the same extremum locations.

| Quantity | Offset (delta_x, delta_y), mrad | L3 | L2 |
|---|---|---:|---:|
| Largest absolute magnetic difference | (-6, 0) | 0.00594761 | 0.00646335 |
| Magnetic asymmetry at that location | (-6, 0) | -2.55335% | +4.14652% |
| Largest absolute magnetic asymmetry | (0, -25) | -2.72434% | +4.41607% |
| Largest relative shot-noise proxy | (0, -25) | 0.0125259 | 0.0166153 |
| Reference magnetic asymmetry | (0, 0) | -0.379660% | +0.615155% |

At (-6,0), Sigma_ref is 0.232933/0.155874 for L3/L2; at (0,-25), it is
0.211395/0.141562. This explains why maximizing absolute magnetic counts
and maximizing asymmetry or the ideal-counting proxy do not coincide.
The absolute incident tilts are (-13.116725,0) mrad at the first extremum,
and (-7.116725,-25) mrad at the second, whose total tilt is 25.993226 mrad.
The reference L3 proxy is 0.00189134, versus 0.0125259 at (0,-25); this
comparison remains relative to the model's fixed intensity normalization.

The minimum intrinsic nonmagnetic imbalance is a degenerate symmetry-plane
result across y=0, not a unique physical optimum identified from numerical
roundoff. The largest absolute nonmagnetic asymmetry is 4.94454% at
(5,-25), L3, BW. At (0,-25), the L3 magnetic/even differences are
-0.00575912/-0.00248965. The corresponding +25 even difference has the
opposite sign. Across all paired orientations and full spectra, the largest
even antisymmetry error is 1.03e-15; reflected even angular maps agree to
3.70e-13 absolute. The fixed-magnetization magnetic response is not exactly
even under y reversal: the largest full-spectral even-relation deviation
is 1.18e-5. No averaging or symmetry enforcement was applied.

Post-edge correction reduces the absolute discrepancy from the intrinsic
magnetic signal in all 112 nonzero-y method/edge comparisons. The corrected
error is a median 2.04% of the raw error, with a range 0.036%-20.36%.
This does not mean perfect recovery. At (0,-25), L3 error falls from
0.00248965 to 0.0000896306; at (0,+25), it falls to 0.000225333 instead.
On the symmetry plane, the raw even imbalance is already roundoff;
correction introduces an artifact in all 60 method/edge comparisons there.
At the reference the L3 corrected error is 2.20e-5, about 2.33% of the
intrinsic magnetic signal. Observed alpha spans 0.907050-1.104574.
A magnetic tail in the chosen post-edge window and energy-dependent
scattering prevent treating observed normalization as exact magnetic recovery.

### Diffraction regime

At the reference, the BW depth-averaged off-row population is 0.0351%.
It rises to 16.7437% at (0,+/-25), where (1,+/-7,-/+1) is strongly excited,
and to 27.0943% at (5,-25). The (1,7,-1) beam alone carries 17.7522% at
the latter orientation. These are full multibeam states even though s200
remains zero along the vertical x=0 series. At the horizontal signal maximum,
(400) is the strongest competitor outside the 000/200 pair, with 4.9361%
depth-averaged intensity; (200) still has the largest nontransmitted average.
For positive offsets beyond ZA incidence (x=8 or 10 on y=0, and x=10 on
the 2D rows), (-200) becomes the largest nontransmitted beam. Therefore
exact Bragg labels, the strongest competing beam, and the largest populated
nontransmitted beam must be distinguished. All are recoverable from the
saved excitation errors, populations and `diffraction_summary.csv`.

### Numerical and physical convergence

Eight representative orientations were checked with 240 selected-energy
method/edge records. The largest estimated dense control pair array is
258.25 MiB (121 beams, detector grid17), below the 512 MiB limit.
Production magnetic-map BW/MS discrepancies reach 0.6025% at (-10,-25).
On the selected-energy controls, increasing 27 to 81 beams changes the
magnetic signal by at most 0.654%, while 81 to 121 changes it by at most
0.000562% at potential2.2 and 0.003306% at potential3.2. Thus representative
finite-basis refinement supports the principal coarse trends.

At potential3.2, FFT32/64 magnetic differences on the common 57-beam basis
change by at most 0.00413%. Matched BW81/MS64 selected-energy differences
are at most 0.0877% at step0.04 nm, reduced to 0.0219% at step0.02 nm.
Those metrics are selected-detector spectral differences, not the whole-map
norm used for the production 0.6025% result.

The physical potential cutoff produces much larger changes. The table uses
121 BW beams and the same detector grid17 throughout; intensities should
not be directly substituted for production grid33 values.

| Orientation (mrad) | L3 D_mag, cutoff2.2 | L3 D_mag, cutoff3.2 |
|---|---:|---:|
| (0,0) | -0.000939916 | -0.000734921 |
| (-6,0) | -0.00588271 | -0.00585094 |
| (0,-25) | -0.00573792 | -0.00629930 |
| (5,-25) | -0.00405130 | -0.00409127 |
| (10,25) | +0.00106798 | +0.000741841 |
| (-10,-25) | -0.00102824 | -0.00134804 |

The reference magnitude decreases by 21.8%, whereas (0,-25) grows by
9.78% and (-6,0) changes by only -0.54%. Corner changes reach about 31%
relative to the lower-cutoff magnitude. Magnetic signs remain stable at
all 16 tested orientation/edge combinations. However, the nonmagnetic L3
difference at (-10,-25) changes sign, from +0.00171573 to -0.00115906.
The absolute-magnetic ranking of (-6,0) and (0,-25) also reverses when the
cutoff increases. Signal enhancement away from exact200 is supported at
these tested candidates, but a cutoff-independent global optimum, full
contamination pattern and quantitative recovery fidelity are unresolved.
Only eight orientations were checked at the larger cutoff.

Main entry figures are `aggregate/emcd_xy_heatmaps.png`,
`raw_corrected_xy.png`, `detectability_xy.png`, `bw_ms_xy.png`, and
`potential_cutoff_controls.png`. The separate x/y scan folders contain
full common-scale angular series and spectral overlays. Individual full
EELS and angular figures remain with their canonical cases.

Twenty focused tests passed. Full production parity and map/EELS identities
were checked, with selected map-to-spectrum reconstruction error at most
5.58e-17 absolute. The preservation manifest confirms all 232 historical
[017]/[710] output files remain unchanged. Plot-only regeneration additionally
checks that every saved physical NPZ stays byte-identical and blocks any
unexpected forward calculation.
