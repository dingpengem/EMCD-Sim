# Ni [017] minor-zone EMCD with crystal-[001] magnetization

This is a separate development from the [710] calculation. New data are saved
under `outputs/ni_017_minorzone_mistilt/`; the 115 existing [710] output files
were hashed before this work and are never output targets.

## True orientation and magnetic convention

The proper cubic-to-local matrix has rows

```
x = [100]
y = [0,7,-1]/sqrt(50)
z = [0,1,7]/sqrt(50)
```

Its determinant is +1 and x cross y = z. The actual cubic Ni cell is rotated;
the ZOLZ condition is `k+7l=0`, with FCC h,k,l all even or all odd. FFT index
`(m,n)` maps to real cubic `(m,7n,-n)`, local reciprocal coordinates
`(m/a,sqrt(50)*n/a)`. The projected rectangular repeat lengths are `a` and
`a/sqrt(50)`, including the FCC parity constraint. The target is genuinely
(200), not a relabeled [710] (002) wave. The oriented potential is passed to
the existing FFT algorithm and the same IAM coefficients enter BW.

The original `Ni_fm.inso` specifies `0 0 1`; `Ni_fm.outputopup` also prints
`s-o calc. M|| 0.00 0.00 1.00`. The tensor starts in **cubic crystal axes**:
Txx=Tyy=N, Tzz=beta*N, Txy=i*eta*D, Tyx=-i*eta*D, with D=(RP-LP)/2.
Each reversal state is formed in those axes before applying `R T R^T`.
The local magnetic direction is consequently
`(0,-1/sqrt(50),7/sqrt(50)) = (0,-0.1414213562,0.9899494937)`.
It is not replaced by local z. Both the tilted magnetic component and its
associated complex tensor cross terms are retained. Tests check Hermiticity,
positive semidefiniteness, eigenvalues and odd/even reversal at several beta
values. No longitudinal/transverse beta or eta convention is changed.

For beta=1 the even tensor is isotropic. For other beta values rotation can
generate real yz cross terms; the cancellation observed for beta=1 should not
be generalized to an anisotropic even tensor.

## Native energy audit before the sweep

The original five-column source covers **823.625–882.521 eV**. No energy shift
or experimental calibration is applied. The selected map energies are the
signed magnetic extrema around the two strong absorption features:

| Edge | Native XAS maximum (eV) | Selected magnetic feature (eV) | Source D sign |
|---|---:|---:|---|
| L3 | 831.421 | **831.271** | negative |
| L2 | 848.752 | **848.698** | positive |

The L3/L2 assignments are corroborated by `inop` selecting L23, the 2p1/2 and
2p3/2 core configuration in `inc`, the two `injoint` core energies
(-60.534300889, -61.819104105 Ry), their **17.48063828 eV** separation, and
the raw/broadened individual edges. Both unbroadened raw1/raw2 magnetic peaks
are at relative 0.10451 eV. Broad1 has its signed magnetic extremum at relative
0.24057 eV; broad2 at 0.18614 eV. Broad1 matches the early combined source
magnetic spectrum to 1e-9 in printed source units. Mapping its extremum to
831.271 eV and applying the core splitting predicts the upper magnetic feature
at 848.697208 eV, agreeing with the printed 848.698 eV sample within 0.001 eV.
The lower-energy edge is L3 (2p3/2), the higher L2 (2p1/2).

The older 852.7/870 eV map selections were external nominal reference energies,
not the magnetic peaks on this raw calculated axis. Old results are preserved
with their original labels/provenance, not silently shifted. The new full
spectrum combines 241 uniform native-axis samples with the two actual selected
samples, giving 243 energies. Edge analysis and zoom windows are centered on
the verified features (±5 eV); post-edge normalization retains 878–882 eV.
`energy_alignment.json` records the audit, correspondence tests, magnetization
axes and SHA256 of all original inputs used. It is an assignment audit, not
an experimental energy calibration or a new DFT calculation.

## Reference and numerical settings

At 200 kV, exact paraxial (200) Bragg alignment is local
`(-7.116725439974256,0) mrad`, with s200=0. Nine offsets from -2 to +2 mrad in
0.5 mrad increments vary x only. Every case records absolute tilt, offset,
s200, all indexed competing excitation errors, and the projected ZA position
`q_ZA=-k_incident,perp`. Zero local tilt is [017] zone-axis incidence; exact
Bragg incidence is a distinct slightly tilted direction.

Transmitted (000), true (200), ZA [017], the fixed Thales circle and physical
A/B detectors are overlaid on all angular panels. The circle has diameter
(000)–(200), and A/B are its upper/lower Thales positions with the existing
fractional apertures. Neither detectors nor circle follow the moving ZA.

Production settings match the earlier elastic comparison: FCC Ni a=3.524 Å,
30 nm, 200 kV, potential cutoff2.2 cycles/Å, beam cutoff3.2 (27 full beams),
FFT32, maximum step0.04 nm, depth64, detector33, fractional64, eta=beta=1.
The dense-kernel estimate is 48.45 MiB, below 512 MiB. Each entrance coherence
is calculated once and reused for selected maps and full EELS. No projected
FFT amplitude renormalization is applied and no energy-resolved map cube is made.

The full two-dimensional basis is retained. At the reference, 000/200 carries
about 99.43% exit intensity and 94.50% depth-average intensity, with up to
10.57% outside the pair at saved depths. Thus the declared strict 5%-maximum
other-mode criterion fails, despite a two-beam-dominated exit pattern. The
strongest competitors are (-200) and (400); all reflections are saved in
`reference_competing_reflections.csv`. No reflections are suppressed to improve
the criterion. An ideal strict 000/200 result is separately labeled.

Limited independent controls reproduce the established study: BW cutoffs
2.2/3.2/4.5 (15/27/57 beams), FFT16/32/64 at fixed physical cutoff2.2, potential
cutoffs0.75/2.2/3.2 at fixed57 beams, and step0.04/0.02. Control detector grid17
is fixed across comparisons; production uses33. Increasing mesh does not change
potential cutoff. The physical-potential sensitivity remains large: magnetic
signals are not globally or potential-cutoff-converged. The potential0.75
control is effectively one-dimensional because off-row harmonics start near
2.027 cycles/Å; production2.2 includes those actual oriented harmonics.

## Explicit comparison with [710]

`scripts/research/ni_017_comparison.py` reads the untouched [710] checkpoints and verifies matched
elastic/detector settings. The equal-local-transverse-coordinate index map is
`(h,k,l)_710 -> (l,-k,-h)_017`. The FCC selection and IAM coefficients are
preserved, and reordered Hamiltonians, complex BW/FFT amplitudes, exit
populations and coherences are compared at each mistilt.

The simple cubic x/z permutation maps the nominal axes but reverses local y.
The equal-local-xy mapping additionally reverses the longitudinal direction;
this is harmless for this centrosymmetric z-independent elastic projection.
It must **not** be used as an unqualified axial-magnetization rotation. Each
physical magnetic tensor instead uses its own proper orientation matrix.

Historical [710] used M along local z, which corresponds to cubic [710], not
cubic [001]. A corrected [710] comparison therefore uses its actual R and
crystal M=[001], yielding local M=(1,0,0), at the **same verified native
831.271/848.698 eV samples**. The new [017] result is compared with this
corrected reference. At exact Bragg, a separate historical local-z calculation
at the new energies isolates the old magnetic convention, while an additional
identical-local-tensor control isolates the elastic/indexing equivalence.
No original [710] spectra or figures are overwritten by these reanalyses.

Outputs: `elastic_710_017_comparison.csv`, `magnetic_710_017_comparison.csv`,
and `orientation_comparison.json`. Magnetic changes cannot be attributed to
crystallographic labels alone: they combine the explicitly recorded magnetic
direction, native-energy selection and the matched elastic scattering.

## Running and saved outputs

```powershell
$env:PYTHONPATH='src'
python -m emcd_sim.ni_017_mistilt --controls-only
python -m emcd_sim.ni_017_mistilt
python -m emcd_sim.ni_017_mistilt --plot-only
python scripts/research/ni_017_comparison.py
```

The scan supports offset range/step, output directory and numerical controls.
Source provenance, code hashes and completed-checkpoint checksums are validated
before reuse. Plot-only regenerates figures from saved selected maps and full
spectra without propagation. Old versioned [710] results remain protected by
their recorded hashes; source-provenance guards may require their original code
revision for rerunning the historical workflow.

Each of nine `case_*` folders contains selected L3/L2 angular arrays and figures,
full BW/MS A/B EELS for both reversal states, raw/odd/even/corrected/residual
spectra, alpha and validity masks, a propagation checkpoint and metadata.
`mistilt_maps.npz` uses `[mistilt,method,edge,qy,qx]`; spectral arrays in
`mistilt_eels.npz` use `[mistilt,method,energy]`. Scalar alpha/masks have
`[mistilt,method]`. All NPZ files load without pickle. Undefined relative
metrics remain NaN/null. Intrinsic odd/even maps are not post-edge-scaled.

Main figures include shared-scale L3/L2 magnetic, even, total and corrected
mosaics for BW and MS, individual raw/corrected maps, individual complete EELS,
combined edge spectra, raw/corrected EELS, and mistilt metric/error trends.
Alpha is observed independently from each case/method's +M spectra over
878–882 eV. There is no per-case peak normalization or fit to another mistilt.

The model remains a z-independent projected IAM, entrance-only, with an
XMCD-constrained effective dipole tensor. It does not provide atom-layer 3D
multislice, HOLZ, outgoing channeling, absorption/TDS or a genuine directional
complex DFT MDFF. Absolute sign/scale retains the original eta/RP-LP conventions.
Matching BW and FFT does not resolve these limitations or the measured
physical-potential-cutoff sensitivity.

## Completed default run

Nine offsets were completed for both methods with 243 native-axis energy
samples (241 uniform samples plus the two exact magnetic features). The
reference tilt is (-7.11672544, 0) mrad and s200 is zero to floating-point
precision. At offsets -2/+2 mrad, s200 is respectively
-0.00113507378/+0.00113507378 inverse angstrom. The full 27-beam finite 2D
basis was retained for every propagation.

Selected BW magnetic asymmetries, defined as magnetic-odd A-minus-B divided
by the reversal-averaged A-plus-B reference, are:

| Horizontal Bragg offset (mrad) | L3, 831.271 eV | L2, 848.698 eV |
|---:|---:|---:|
| -2 | +0.036459% | -0.058865% |
| 0 | -0.379660% | +0.615155% |
| +2 | +0.158651% | -0.256892% |

Across all nine cases, the largest relative BW/MS magnetic-map L2-norm
difference is 0.04141%; the largest relative coherence difference is
0.003198%. Map-to-EELS reconstruction differs by at most 3.39e-17 absolute.
The paired-detector nonmagnetic-even difference is at roundoff (maximum
1.53e-16) for this beta=1 mirror-symmetric configuration; no numerical
suppression claim is made for an already-zero intrinsic even difference.
Observed post-edge alpha ranges from 0.99992642 to 1.00017648. A finite
magnetic post-edge tail means observed scaling can introduce a small even
residual, which is exported separately.

The postprocessing comparison command also writes
`postedge_normalized_eels.npz` at the root and in every case: A is unchanged,
B is multiplied by the observed alpha, and their difference is checked
against the saved corrected spectrum. Raw spectra remain separately saved.

All 18 matched method/case elastic comparisons with [710] give maximum
complex-amplitude error 1.40e-14 and coherence error 3.85e-15 after hkl
reindexing. At exact Bragg, the L3 magnetic difference is -9.42203e-4 for
[017]/crystal-[001], +1.47197e-7 for [710]/crystal-[001], and -9.51769e-4
for the historical [710]/local-z convention evaluated at the same native
energy. The matched-local-tensor control reproduces [017] to roundoff.
These are orientation/convention effects within the effective-tensor model,
not a failure of elastic cubic equivalence.

The reference wavefield has 99.4307% exit intensity in 000/200 but only
94.5007% depth-averaged pair intensity; competing beams reach 10.5726% at
sampled depths. It fails the strict 5%-outside-pair criterion. At fixed
potential cutoff 2.2 inverse angstrom, increasing BW cutoff 3.2 to 4.5
(27 to 57 beams) changes the selected magnetic difference by about 0.002%.
FFT meshes 32/64 agree to 8.65e-9 in common amplitudes. Halving the FFT
step 0.04 to 0.02 nm reduces the absolute BW coherence discrepancy from
2.12e-5 to 9.85e-6. Increasing the physical potential cutoff 2.2 to 3.2
at 57 beams changes the magnetic difference by about 21.8%; this physical
potential convergence remains unresolved. Controls use a smaller detector
grid of 17 and must be compared within each control, not directly with
the production grid of 33.

Fifteen focused tests passed, including tensor PSD/Hermiticity/reversal,
native edge assignment, oriented BW/FFT equivalence, plot overlay/data
preservation, and unchanged shared [710]/mistilt defaults. The 115 original
[710] files were verified against `previous_710_sha256.json` without changes.
The initial numerical provenance is retained separately from a plot-only
correction of a copied zone-axis label; coordinates and physical arrays were
unchanged. No numerical rerun was needed for that correction.
