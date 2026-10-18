# Ni [001]/[017]: actual Bragg geometry and full-ZOLZ elastic comparison

The completed full-spectrum study is preserved under
`outputs/ni_double_channeling_full_spectra/`. Its genuine energy-resolved
BW/MS validation is described in [the spectral report](DOUBLE_CHANNELING_FULL_SPECTRA.md).
This additional study changes no EMCD calculation. It uses elastic BW
propagation only at 8, 12 and 30 nm, with the existing projected Ni IAM,
200 kV, beam cutoff 4.6 Angstrom^-1 and potential Fourier cutoff
6.2 Angstrom^-1. No full energy scan, voltage scan, FFT convergence study,
atomic-3D implementation or GUI module is added.

## Audit of the saved reference

The saved [001] EMCD reference is **class C: [001]-derived,
exact-(200)-Bragg geometry with a systematic-row-restricted basis**.
It is not exact [001] incidence or a full-ZOLZ calculation.

| Quantity | Saved [001] row reference | Saved [017] reference |
| --- | --- | --- |
| Nominal crystal zone axis | [001], a major zone | [017], a minor zone |
| Absolute local tilt, also relative to nominal ZA (mrad) | (-7.11672544, +35.0) | (-7.11672544, 0) |
| Target | (200) | (200) |
| s200 (cycles/Angstrom) | 0 within implemented paraxial convention | 0 within implemented paraxial convention |
| Basis condition | k=l=0, FCC allowed | k+7l=0, FCC allowed |
| Saved basis | 17 beams, off-row excluded | 59 beams, full finite 2D ZOLZ disk |
| Beam / potential cutoffs (Angstrom^-1) | 4.6 / 6.2 | 4.6 / 6.2 |
| Projected ZA / Laue-circle center (cycles/Angstrom) | (+0.283768445, -1.395570991) | (+0.283768445, 0) |

The accelerating voltage is 200 kV and the existing relativistic wavelength
is 0.0250793404505 Angstrom. The transmitted beam is (0,0).
The Laue-circle center is -k_incident,perp, equal to the projected nominal
zone-axis direction in these transmitted-beam-centered coordinates; its
radius is |k_incident,perp|. No detector or tilt coordinate is hard-coded in
the analysis. Complete vectors and all hkl/g coordinates are in
`geometry_audit.json` and the NPZ files.

The normalized paraxial actual incident directions in cubic coordinates are:

- [001]: (-0.0071121906, +0.0349776975, +0.9993627857).
- [017]: (-0.0071165452, +0.1414177750, +0.9899244252).

For [001], the local frame is cubic x/y/z. For [017], its rows are
x=[100], y=[0,7,-1]/sqrt(50), z=[0,1,7]/sqrt(50). Thus crystal [001]
magnetization is local (0,-1/sqrt(50),7/sqrt(50)), not local [001]. The
unchanged spectral tensor uses this rotation; elastic diffraction is
independent of magnetization.

[001] is a major zone because the cubic fourfold projection contains several
short allowed reciprocal rows, including (200) and (020). The horizontal
-7.1167 mrad tilt enforces s200=0; it does not remove the other rows. Even the
saved additional 35 mrad vertical tilt does not establish two-beam isolation.
The new [001] full calculation retains **the identical incident direction**
and expands only the basis to the complete **213-beam** FCC-allowed ZOLZ disk.
It is class B, a new [001]-derived exact-(200)-Bragg full-ZOLZ calculation.
The original row spectra are never relabelled as this new model.

The script enumerates the complete finite disk directly from the actual
crystal. The GUI's 121-beam interactive preview cap is not changed; this
elastic-only script uses existing process-memory admission and does not
truncate the 213-beam basis to that cap. The [017] source basis is unchanged.

## Two-beam, off-row and other-row populations

Each percentage is relative to the total represented elastic intensity.
The table's two-beam group is 000 plus **positive (200)**; other row beams
include (-200), (+/-400), etc. Off-row means k or l nonzero. These three
disjoint groups sum to 100%, without an arbitrary ideal-two-beam threshold.

| Geometry | t (nm) | Exit 000+200 (%) | Exit off-row (%) | Exit other row (%) | Depth 000+200 (%) | Depth off-row (%) | Depth other row (%) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| [001] full | 8 | 76.753684 | 18.754429 | 4.491887 | 83.946411 | 10.973592 | 5.079997 |
| [001] full | 12 | 84.817194 | 14.180696 | 1.002110 | 83.016714 | 12.792151 | 4.191135 |
| [001] full | 30 | 54.975338 | 42.283285 | 2.741377 | 73.028155 | 23.568372 | 3.403473 |
| [017] full | 8 | 94.583692 | 0.022585 | 5.393723 | 93.360085 | 0.051384 | 6.588531 |
| [017] full | 12 | 96.962126 | 0.015654 | 3.022221 | 94.748634 | 0.047767 | 5.203599 |
| [017] full | 30 | 99.326257 | 0.018730 | 0.655013 | 94.344760 | 0.048613 | 5.606627 |

Total represented intensity is incident-normalized and equals one to a maximum
absolute normalization error **1.44e-15** across all nine elastic cases.
CSV/NPZ retain both absolute incident-normalized intensities and fractions of
the represented intensity, rather than reporting percentages alone. Unitary
normalization of a finite Hamiltonian does **not** demonstrate that omitted
beams have physically zero intensity or that the basis is complete.

Depth averages are evaluated analytically from the same finite BW eigenmodes:
<exp(i Delta*z)> = exp(i Delta*t/2)*sinc(Delta*t/(2*pi)). The full complex
coherence matrix is saved. This removes depth quadrature error from this
elastic comparison; it does not change the 257-node EMCD depth integration.
Focused tests compare the analytic average with fine direct depth propagation,
including complex Hermitian eigenmodes. Exit amplitudes for the unchanged row
and [017] bases reproduce the saved 8 nm incoming fields within 1e-12.

At 8 nm [017] reduces the exit off-row fraction by approximately
830-fold, and
the depth-averaged off-row fraction by approximately
214-fold,
relative to this specific 35 mrad-off-zone [001] geometry. It is substantially
cleaner at all three tested thicknesses. This is not a universal comparison
against all possible [001]-derived tilts.

[017] still has several percent in other systematic-row beams. At 30 nm its
exit 000+200 fraction is 99.326%, but its depth-averaged fraction is only
94.345%. A nearly two-beam exit pattern does not establish a strictly two-beam
wavefield throughout the specimen. The useful (200) intensity is explicitly
retained in the beam tables below; dominance is not obtained just by
suppressing every diffracted beam.

## Indexed reflections at 8 nm

These are absolute incident-normalized intensities. Excitation error s uses
cycles/Angstrom; coupling is |H_000,g| in nm^-1. All 213 or 59 represented
reflections and all three thicknesses are in `beam_populations.csv`; none of
the omitted reflections is assigned a physical zero.

### Full [001]

| hkl | g magnitude (Angstrom^-1) | s (Angstrom^-1) | Coupling (nm^-1) | Exit I | Depth-average I |
| --- | ---: | ---: | ---: | ---: | ---: |
| (0 0 0) | 0 | 0 | 0 | 0.4469878 | 0.7276934 |
| (2 0 0) | 0.5675369 | 0 | 0.08358753 | 0.320549 | 0.1117707 |
| (-2 0 0) | 0.5675369 | 0.008078008 | 0.08358753 | 0.03779233 | 0.04066463 |
| (4 0 0) | 1.135074 | 0.008078008 | 0.03908487 | 0.005708116 | 0.007727085 |
| (-4 0 0) | 1.135074 | 0.02423403 | 0.03908487 | 0.001059798 | 0.001621513 |
| (0 2 0) | 0.5675369 | 0.0239028 | 0.08358753 | 0.001663695 | 0.005801481 |
| (0 -2 0) | 0.5675369 | -0.01582479 | 0.08358753 | 0.007256063 | 0.00923616 |
| (2 2 0) | 0.8026184 | 0.0239028 | 0.05948 | 0.001177446 | 0.003527204 |
| (2 -2 0) | 0.8026184 | -0.01582479 | 0.05948 | 0.006179227 | 0.004984288 |
| (-2 2 0) | 0.8026184 | 0.0319808 | 0.05948 | 0.002012707 | 0.001555188 |
| (-2 -2 0) | 0.8026184 | -0.007746778 | 0.05948 | 0.05565707 | 0.02985527 |
| (4 -2 0) | 1.269051 | -0.007746778 | 0.03340435 | 0.03074273 | 0.01144072 |
| (-4 -4 0) | 1.605237 | 0.0006624599 | 0.02323702 | 0.02513122 | 0.009025967 |
| (6 -4 0) | 2.046283 | 0.0006624599 | 0.01543555 | 0.01195869 | 0.003803447 |

The strongest off-row population is not restricted to the lowest-index (020)
beam. The full calculation automatically identifies (-2,-2,0), (4,-2,0),
(-4,-4,0) and (6,-4,0) among the largest off-row contributors at 8 nm.
Nearly resonant higher reflections and dynamical transfer must be evaluated,
not discarded on the basis of the target's exact Bragg alignment.

### Full [017]

| hkl | g magnitude (Angstrom^-1) | s (Angstrom^-1) | Coupling (nm^-1) | Exit I | Depth-average I |
| --- | ---: | ---: | ---: | ---: | ---: |
| (0 0 0) | 0 | 0 | 0 | 0.4596964 | 0.7667759 |
| (2 0 0) | 0.5675369 | 0 | 0.08358753 | 0.4861405 | 0.166825 |
| (-2 0 0) | 0.5675369 | 0.008078008 | 0.08358753 | 0.04335999 | 0.05152785 |
| (4 0 0) | 1.135074 | 0.008078008 | 0.03908487 | 0.01012025 | 0.01173876 |
| (-4 0 0) | 1.135074 | 0.02423403 | 0.03908487 | 0.0001049171 | 0.001774422 |
| (1 7 -1) | 2.026512 | 0.0494778 | 0.01569743 | 1.037819e-05 | 8.863054e-05 |
| (-1 7 -1) | 2.026512 | 0.05351681 | 0.01569743 | 2.145296e-05 | 5.049392e-05 |
| (1 -7 1) | 2.026512 | 0.0494778 | 0.01569743 | 1.037819e-05 | 8.863054e-05 |
| (-1 -7 1) | 2.026512 | 0.05351681 | 0.01569743 | 2.145296e-05 | 5.049392e-05 |

For this orientation, k+7l=0 and FCC reflection indices must be all even or all
odd. Consequently (1,7,-1) is allowed, whereas (0,7,-1) is forbidden.
The nearest off-row allowed beams have g magnitude about 2.0265 Angstrom^-1,
with substantial excitation errors. This combination of larger reciprocal
row spacing and excitation error suppresses their populations; it is not a
numerical two-beam restriction. The full crystal structure factors and
couplings, including weak beams, are retained in the NPZ/CSV outputs.

## Isolating the systematic-row restriction

The tilt, IAM factors, beam radial cutoff and Fourier cutoff are identical
in the restricted/full [001] comparison. Only exclusion of off-row beams
changes. Exit-plane 000 and 200 populations demonstrate its material effect:

| t (nm) | Model | I000 | I200 | 000+200 (%) | Off-row (%) |
| --- | --- | ---: | ---: | ---: | ---: |
| 8 | 001_row | 0.46928901 | 0.47724558 | 94.653459 | 0.000000 |
| 8 | 001_full | 0.44698783 | 0.32054901 | 76.753684 | 18.754429 |
| 12 | 001_row | 0.17799609 | 0.79299538 | 97.099147 | 0.000000 |
| 12 | 001_full | 0.28118161 | 0.56699033 | 84.817194 | 14.180696 |

Zero off-row population in the restricted model denotes **excluded support**,
not a prediction of physically absent scattering. The restriction inflates
its two-beam fraction and changes the remaining row amplitudes and coherences.
`row_restriction_effect.csv` saves individual row changes and complex
000/g depth coherences at 8 and 12 nm.

The row approximation is not quantitatively faithful to the tested full-[001]
elastic wavefield. The original row EMCD results remain validated for their
explicit model; they are not full-ZOLZ [001] predictions. The cleaner [017]
elastic wavefield supports using it as the more two-beam-dominated reference
among these tested geometries, while retaining its full finite basis.
Weak elastic off-row populations may still affect EMCD through complex
interference terms involving amplitudes, Coulomb weights and the MDFF;
small beam intensity alone is not a bound on magnetic error.

No full-ZOLZ [001] inelastic correction is inferred from elastic populations.
The optional fixed-energy Double BW comparison was omitted: the existing
solver's conservative dense-kernel admission estimate at 213 beams is
157039 MiB (153.4 GiB), exceeding all supported budgets and available RAM.
This is the current estimator's limit, not a claim that every alternative
numerical formulation must allocate that amount. The estimator was not
relaxed and the beam basis was not reduced. No extra perpendicular-mistilt
optimization was needed to establish the substantially cleaner [017] result.

## Figures, data and reproduction

Outputs: `outputs/ni_two_beam_geometry_comparison/`.

- `indexed_diffraction.png/.svg`: full [001]/[017] 8 nm patterns, identical
  incident-intensity logarithmic color scale and reciprocal extents; labels
  include 000, 200 and strong off-row reflections. The visual 1e-9 color floor
  does not zero or threshold the numerical data.
- `beam_groups_8nm.png/.svg`: incident-normalized 000, 200, other-row and
  off-row populations, for exit and depth average.
- `two_beam_fractions.png/.svg`: 8/12/30 nm exit and depth-average fractions.
- `exit_vs_depth_average.png/.svg`: distinct exit/depth comparison.
- `beam_populations.csv`, `population_summary.csv`,
  `row_restriction_effect.csv`, and `001_row.npz`, `001_full.npz`,
  `017_full.npz`: full-precision numerical results, complex amplitudes and
  coherences, hkl/g, excitation errors, and structure-factor-related coupling.
- `geometry_audit.json` and per-geometry metadata: applied/cubic directions,
  frame, wavelength, actual Bragg error, Laue center, cutoffs, memory admission,
  software milestone, implementation hashes and original project provenance.
- `preservation.json`: source and all existing full-spectrum NPZ hashes
  before/after the elastic study; they remain unchanged.

```powershell
python scripts/ni_two_beam_geometry_comparison.py
```

This script requires the full-spectrum acceptance checkpoint first. Existing
elastic NPZ files are reused only with matching provenance. The comparison
uses low-level existing elastic routines; it does not add a new solver.

## Validation scope and remaining limitations

Seventy-one focused tests pass across the full-spectrum and geometry work.
They cover frame/tilt signs, Bragg alignment, FCC selection and complete finite
disk enumeration, partition/normalization, exit propagation, analytic complex
depth averages, unchanged raw/relative displays, cancellation/resume, legacy
Single/two-sample projects, and existing memory limits. The saved incoming
row/[017] amplitudes and all protected spectral NPZ files are unchanged.

This comparison establishes deterministic fractions for these three thicknesses
and finite numerical profiles, with normalization errors near machine
precision. It does not supply an experimental uncertainty interval or an
independent beam/potential-cutoff convergence study for full [001]. Finite
ZOLZ support, omitted HOLZ, projected rather than atomic-3D IAM, no absorption
or thermal diffuse scattering, and finite Fourier/beam cutoffs remain.
EMCD additionally retains the approximate XMCD-constrained MDFF and the
energy-dependent but branch-frozen longitudinal transfer. Absolute native
energy calibration is unverified. Neither numerical BW/MS agreement nor a
large two-beam fraction establishes full experimental agreement or complete
three-dimensional diffraction.
