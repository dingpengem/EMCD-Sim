# Spatial post-edge EMCD comparison: matched Bloch and FFT multislice

The workflow compares paired detector-difference maps before/after constant
post-edge normalization, with independently propagated incident waves and the
existing shared XMCD-effective tensor contraction. No scattering, propagation,
coherence, normalization or historical integration implementation is modified.

```bash
python -m emcd_sim.postedge_emcd_maps --xmcd-file data/wien2k_ni/Ni_fm.xmcd \
  --conditions near-2bc symmetric-3bc --postedge-start 878 --postedge-end 882 \
  --integration-mode fractional --output outputs/ni_postedge_emcd_map_comparison
```

Defaults: FCC Ni [001], 200 kV, 30 nm, eta=beta=1; Fourier potential cutoff
0.75 cycles/A; common ZOLZ beam cutoff 2.2 cycles/A; FFT 32 square, maximum
Strang slice step 0.04 nm; 64 depth samples; detector grid 33 square;
fractional circular integration with 64 boundary subpixels. The matched
independent-atom potential has B=0 and U000=0. The existing memory guard,
beam-cap check and FFT Nyquist checks run before the spectral calculation.
Coherences are calculated once per method/geometry, reused over energies,
and never renormalized after FFT projection. See the existing
[multislice reference](MULTISLICE_EMCD_REFERENCE.md) for conventions.

The detector spectra sample 185 evenly spaced energies from 837 eV through
the actual source end (882.521 eV). Normalization uses exact interpolated
window endpoints and identical trapezoidal quadrature. Magnetic source tails
are neither removed nor extrapolated. L3/L2 maps use actual source samples
nearest 852.7/870 eV, independently of the interpolated spectral grid. Only
these selected maps are retained; no full energy-map cube is saved.

## Definitions and pairing

`I_mag=(I_plus-I_minus)/2` and `I_nonmag=(I_plus+I_minus)/2` are full-grid,
unprocessed intrinsic parity intensities. They are distinct from detector
contrasts. The reflection `R(qx,qy)=(qx,-qy)` pairs A with B in near-2BC and
RU with RD, LD with LU in 3BC. The original 3BC grouping is preserved:
A=RU+LD, B=RD+LU. The workflow checks the physical aperture centers/radii,
bijective mapping, full coverage and reflected integration weights before
forming paired fields. Mismatched geometry or weights are rejected.

Paired fields exist only on the weighted A-side support; all other pixels are
NaN. Their spatial integral uses the original A fractional weights times dq^2.
The paired B field then exactly recovers the original B spectrum, including
both physical apertures in the 3BC group. The full-grid intrinsic intensity
fields remain finite outside the apertures.

Each method uses its own `alpha_obs`, obtained solely from its integrated
plus-state A/B spectra in 878-882 eV. `alpha_nonmag` is an even-oracle diagnostic
only. No pixelwise factor, fitted BW/MS gain or energy-dependent correction is
used. A secondary stored MS map applies the independently obtained BW factor
to isolate scale-factor differences.

```
D_raw = I_plus(q) - I_plus(Rq) = D_mag + D_nonmag
D_corrected = I_plus(q) - alpha_obs*I_plus(Rq)
            = D_mag_processed + D_nonmag_residual
D_mag_processed = M(q) - alpha_obs*M(Rq)
D_nonmag_residual = N(q) - alpha_obs*N(Rq)
```

Both identities and all four selected A/B reversal-state integrals are checked
against the existing detector contraction. Post-edge normalization changes
processed contrast, not the intrinsic magnetic scattering intensity. Magnetic
norm changes compare different normalization conventions and do not represent
a calibrated magnetic-moment loss.

## Outputs and error conventions

The ignored output folder contains `map_comparison.npz`,
`method_comparison.csv`, `comparison_metadata.json`, and four figure types for
each geometry (the three map types are produced separately at L3 and L2):

- `*_raw_corrected.png`: BW/MS rows, raw/corrected columns, one common zero-centered scale.
- `*_decomposition.png`: original magnetic/even differences and processed magnetic/even residuals, BW/MS rows and a common scale.
- `*_method_errors.png`: MS minus BW raw, corrected, intrinsic magnetic and even-residual errors, with absolute/relative L2 values.
- `*_detector_spectra.png`: A/B spectra, raw/corrected differences, magnetic reference and even residual, with the normalization window shaded.

Solid aperture outlines indicate A; dashed outlines indicate B. White outside
paired supports means invalid, not zero EMCD. The intrinsic magnetic error
uses the full reciprocal grid; other error metrics use A-side fractional area
weights. Relative L2 uses the larger compared norm and is undefined below
1e-10 times the corresponding intensity norm. Absolute errors remain available
when the reference cancels. Spatial suppression uses a weighted norm before
integration; spectral suppression uses the norm of the detector-integrated
spectrum, so the two can differ through cancellation.

NPZ map axes are condition, method, selected energy (L3/L2), qy, qx. Intrinsic
maps and paired fields are separately named. Group weights, every physical
aperture weight, validity masks, detector spectra, observed/oracle factors,
shared-factor corrected fields, coherences and depth-resolved FFT leakage are
saved without pickle. Spectral arrays have the `spectra__` prefix. The CSV
separates selected-energy detector/spatial metrics, full/L3/L2 spectral
recovery metrics, and MS-BW discrepancies by method/scope/quantity. NaN marks
undefined metrics. JSON includes the source hash, actual energies, physical
geometry, effective aperture areas, every numerical control, leakage,
coherence errors, normalization diagnostics and software provenance.

To regenerate figures without running physics, use the same command with
`--plot-only`; this reads the saved output and ignores numerical CLI settings.
The Python `load_comparison` and `plot_comparison` functions also support this.

## Limitations

This is a small matched-potential comparison, not convergence testing. It
cannot validate the separate full-potential 13/21/37-beam results, which use a
different elastic potential. No optional full-potential run was added.
Finite common-basis projection, FFT resolution/slice step, depth quadrature,
coarse detector grid, spatially varying aperture intensity and spectral
sampling remain possible numerical errors. Both methods model entrance-only
channeling with a shared effective MDFF; agreement does not independently
validate the MDFF or outgoing inelastic diffraction. No quantitative Ni
magnetic moment, optimal experimental geometry or convergence is claimed.

## Focused matched example

Python 3.10.9; 45 common beams; estimated pair arrays 134.60 MiB. Actual
selected source samples are L3=852.698 eV and L2=870.004 eV. The table below
uses the L3 detector-integrated values (asymmetries are dimensionless).
A_raw uses the plus-state detector sum; A_mag and A_nonmag use the common
reversal-even Sigma_ref, following the existing parity convention:

| Geometry / method | alpha observed | alpha oracle | A_raw | A_mag | A_nonmag | Sigma_ref |
|---|---:|---:|---:|---:|---:|---:|
| near-2BC / BW | 0.872717573 | 0.871601051 | -0.05816859 | 0.01109846 | -0.06922328 | 0.04119459 |
| near-2BC / MS | 0.872872214 | 0.871755570 | -0.05808093 | 0.01109793 | -0.06913502 | 0.04119305 |
| symmetric-3BC / BW | 1.000434689 | 1.000000000 | 0.00377814 | 0.00377814 | -3.96e-16 | 0.07875788 |
| symmetric-3BC / MS | 1.000434834 | 1.000000000 | 0.00377939 | 0.00377939 | 3.08e-16 | 0.07875355 |

The full-range detector-spectral even-norm suppression is 98.1194% (BW) and
98.1170% (MS) in near-2BC, with processed magnetic norm changes -6.7954% and
-6.7885%, and corrected/reference errors 11.2496% and 11.2437%. For 3BC the
original integrated even spectrum is negligible, making suppression undefined;
magnetic norm changes are +0.02173/0.02174%, and corrected/reference errors
are 2.87262/2.87263%. These values belong to the matched truncated potential;
they do not reproduce or replace the separate full-potential post-edge study.

### Local contrast versus integrated cancellation

Near-2BC L3 spatial even-norm suppression is only 84.2208% (BW) and 84.2122%
(MS), despite approximately 98.12% spectral suppression. L2 spatial suppression
is 84.2896/84.2811%. Local residual structure therefore persists after constant
scaling. The L3 spatial magnetic norm changes are -6.8326/-6.8258%; intrinsic
I_mag remains unchanged. The corrected field's spatial error relative to the
unscaled magnetic difference is 100.21/100.15% at L3 and 401.32/401.06% at L2:
local residuals can be comparable to or larger than the magnetic contrast even
when the integrated spectrum appears much cleaner.

For symmetric-3BC, substantial local even differences have opposite signs
across RU and LD and cancel in the grouped spectrum. Integrated purity is
therefore not pointwise purity. Post-edge scaling slightly increases the
spatial even norm by 0.02182% at L3 instead of removing it. The local magnetic
norm grows approximately 0.02173%; the corrected spatial field remains
dominated by the original canceling even contrast. Its L3 corrected/reference
spatial error is about 42.7 times the magnetic reference norm, already large
before correction. This is not a new physical magnetic amplification or loss.

### Method discrepancies

Area-weighted map errors, with each method using its own observed factor:

| Geometry / edge | Raw abs L2 | Raw rel (%) | Corrected abs L2 | Corrected rel (%) | Intrinsic I_mag full-grid rel (%) | Even residual rel (%) |
|---|---:|---:|---:|---:|---:|---:|
| near-2BC / L3 | 2.318e-5 | 0.15137 | 4.048e-6 | 0.10734 | 0.07449 | 0.14503 |
| near-2BC / L2 | 1.018e-6 | 0.13473 | 1.797e-7 | 0.14310 | 0.07469 | 0.14643 |
| symmetric-3BC / L3 | 8.185e-5 | 0.14170 | 8.187e-5 | 0.14170 | 0.43592 | 0.14173 |
| symmetric-3BC / L2 | 3.567e-6 | 0.14225 | 3.567e-6 | 0.14224 | 0.43838 | 0.14225 |

Near-2BC normalization reduces absolute method differences, but does not
uniformly reduce relative errors: the smaller corrected L2 norm produces a
slightly larger relative discrepancy. With the shared BW factor, near-2BC
corrected relative errors are 0.55646% (L3) and 0.73709% (L2), compared with
0.10734/0.14310% for independently derived factors. The corresponding absolute
errors are 2.105e-5 and 9.262e-7. Agreement of the complete independently
normalized workflow partly reflects the different detector-integrated factors;
it does not prove identical propagation. Shared-factor 3BC errors are almost
unchanged (0.14171/0.14225%). No factor was fitted to force agreement.

L3 absolute BW/MS differences in A_raw, A_mag and A_nonmag are respectively
8.77e-5, 5.24e-7 and 8.83e-5 for near-2BC; 1.25e-6, 1.25e-6 and 7.05e-16
for 3BC. Sigma_ref differs by 1.54e-6 and 4.33e-6. Relative errors for the
negligible integrated 3BC even difference are deliberately undefined.

Maximum projected FFT leakage is 1.11085e-5 (near-2BC) and 1.10123e-5 (3BC).
Coherence Frobenius differences are 6.08821e-4 and 8.81779e-4; relative values
are 0.08744% and 0.10291%. FFT norm errors are below 2.34e-14. Selected
paired-field detector reconstruction differs by at most 6.94e-18.

Validation: 24 focused tests passed across map, post-edge normalization and
multislice reference modules, including synthetic grouping/weight checks,
pointwise decomposition, reversal parity, a real-source eta=0 check,
plus-only observed scaling, matched source conventions, binary masks and
pickle-free output/reload. No broad regression suite or parameter sweep ran.
Fourteen figures were generated: four types per geometry, with separate L3/L2
versions of the three map types. Raw and processed data remain separate.
