# Ni EMCD thickness scientific analysis - 200 kV

The read-only production audit passes the unchanged numerical comparison gates. All 204 joint checkpoints (both channeling models per solver/geometry/thickness), 816 edge/model records, and 51 actual 0:2:100 nm points per series are present. No propagation, interpolation, peak fitting, independent curve normalization or replacement of production data is used. Original checkpoint bytes are checked unchanged.

## Setup and geometry

Fixed native energies: L3 831.4778 eV and L2 848.698 eV; no absolute experimental calibration. Ni FCC, 200 kV, eta=beta=1; crystal [001] magnetization rotated into the local frame. Potential cutoff 6.2 cycles/Angstrom; incoming/outgoing beam cutoff 4.6 cycles/Angstrom; FFT 48; 257 depth nodes ([001] BW uses analytic depth integration; [017] BW uses numerical depth integration); MS maximum step 0.04 nm; float64/complex128. Fractional circular detectors: grid 193, 64 subpixels, radius 0.0908059024 cycles/Angstrom, centers (0.28376844495, +/-0.28376844495) cycles/Angstrom. Configuration/source hashes, actual weights/areas and basis lists remain in production metadata.

[017] is the main physical reference: full finite ZOLZ, local x tilt -7.11672544 mrad, y=0, exact (200) Bragg condition. [001] uses the same x tilt and y=+35 mrad (about 2.05 degree inclination) with an explicitly restricted (200) systematic row. It is a theoretical comparison, not a validated full-ZOLZ two-beam-dominated case; previous elastic audits found substantial off-row scattering. Neither exact Bragg alignment nor a finite basis proves an isolated two-beam wavefield.

## Definitions and audit

For each detector J, N_J=(I_J(+M)+I_J(-M))/2 and M_J=(I_J(+M)-I_J(-M))/2. D_mag=M_A-M_B; D_nonmag=N_A-N_B; D_raw=I_A(+M)-I_B(+M)=D_mag+D_nonmag. These are original signed arbitrary intensities. Detector intensities are integrated before ratios are formed; no pixelwise percentage averaging is used.

The task supplied two definitions under A_raw. Both are retained explicitly: **A_raw_plus=100 D_raw/(I_A(+M)+I_B(+M))** preserves the original benchmark and figures; **A_raw_even=100 D_raw/(N_A+N_B)** supports the additive decomposition A_raw_even=A_mag+A_nonmag. A_mag=100 D_mag/(N_A+N_B); A_nonmag=100 D_nonmag/(N_A+N_B). These denominators must not be silently interchanged. R_contam=abs(D_nonmag)/abs(D_mag). Undefined or numerically tiny denominators yield NaN, using a documented 32-epsilon relative series floor. No ratios are capped. Zero thickness has exactly zero raw intensities and undefined percentages.

## Complete BW/MS comparison

worst_asymmetry: [017] single L2, 22 nm. Signed BW 9.13233768616%, MS 9.12268166935%; MS-BW -0.00965601680493 pp; maximum relative raw-state difference 0.0103855190824%.
States in order A+, B+, A-, B-: BW `[0.06610964817950736, 0.05504536339850317, 0.05562218087125759, 0.06668646565226179]`; MS `[0.06610364026344012, 0.055051080738998365, 0.05562729164343182, 0.06667985116787356]`.

worst_raw: [017] double L2, 18 nm. Signed BW 5.37493823455%, MS 5.3664819205%; MS-BW -0.00845631405063 pp; maximum relative raw-state difference 0.015097376485%.
States in order A+, B+, A-, B-: BW `[0.05625280667761409, 0.05051414876752374, 0.05080661823552568, 0.05654527614561602]`; MS `[0.05624475820952014, 0.05051548885264397, 0.05080746993551572, 0.05653673929239185]`.

Maximum asymmetry difference 0.00965601680493 pp is below 0.01 pp, with only 0.00034398319507 pp margin. Maximum relative raw error 0.015097376485% is below 0.1%. Worst cases are [017] L2 at 22 nm Single and 18 nm Double, not the L3 peak points. Raw-state reconstruction and complete comparison pass without threshold changes. Existing representative cutoff/basis/FFT/slice/depth evidence is retained; no new control is necessary to make a passing gate pass. Agreement is not proof of complete physical or parameter convergence.

## Distinct sampled optimization targets

| Zone | Solver | Model | Edge | Observable | Thickness nm | Signed value |
|---|---|---|---|---|---:|---:|
| 017 | bw | single | L3 | A_raw_plus | 12 | -11.65564115 |
| 017 | bw | single | L3 | A_mag | 12 | -11.72545502 |
| 017 | bw | single | L3 | D_mag | 48 | -0.01403130042 |
| 017 | bw | single | L3 | R_contam | 16 | 0 |
| 017 | bw | single | L2 | A_raw_plus | 12 | 20.09789902 |
| 017 | bw | single | L2 | A_mag | 12 | 19.88949433 |
| 017 | bw | single | L2 | D_mag | 48 | 0.01577380189 |
| 017 | bw | single | L2 | R_contam | 2 | 0 |
| 017 | bw | double | L3 | A_raw_plus | 8 | -13.06008297 |
| 017 | bw | double | L3 | A_mag | 8 | -13.14878246 |
| 017 | bw | double | L3 | D_mag | 12 | -0.01070617755 |
| 017 | bw | double | L3 | R_contam | 56 | 0 |
| 017 | bw | double | L2 | A_raw_plus | 8 | 22.54492355 |
| 017 | bw | double | L2 | A_mag | 8 | 22.28011963 |
| 017 | bw | double | L2 | D_mag | 12 | 0.01204178646 |
| 017 | bw | double | L2 | R_contam | 18 | 1.209149249e-15 |
| 017 | ms | single | L3 | A_raw_plus | 12 | -11.65543241 |
| 017 | ms | single | L3 | A_mag | 12 | -11.72524431 |
| 017 | ms | single | L3 | D_mag | 48 | -0.01402773029 |
| 017 | ms | single | L3 | R_contam | 2 | 0 |
| 017 | ms | single | L2 | A_raw_plus | 12 | 20.09753696 |
| 017 | ms | single | L2 | A_mag | 12 | 19.88913816 |
| 017 | ms | single | L2 | D_mag | 48 | 0.0157697896 |
| 017 | ms | single | L2 | R_contam | 2 | 0 |
| 017 | ms | double | L3 | A_raw_plus | 8 | -13.06103222 |
| 017 | ms | double | L3 | A_mag | 8 | -13.14974733 |
| 017 | ms | double | L3 | D_mag | 12 | -0.01070248305 |
| 017 | ms | double | L3 | R_contam | 36 | 0 |
| 017 | ms | double | L2 | A_raw_plus | 8 | 22.54660178 |
| 017 | ms | double | L2 | A_mag | 8 | 22.2817508 |
| 017 | ms | double | L2 | D_mag | 12 | 0.01203763754 |
| 017 | ms | double | L2 | R_contam | 4 | 0 |
| 001 | bw | single | L3 | A_raw_plus | 12 | -11.8572649 |
| 001 | bw | single | L3 | A_mag | 12 | -11.8572649 |
| 001 | bw | single | L3 | D_mag | 50 | -0.01426162845 |
| 001 | bw | single | L3 | R_contam | 18 | 0 |
| 001 | bw | single | L2 | A_raw_plus | 12 | 20.11327018 |
| 001 | bw | single | L2 | A_mag | 12 | 20.11327018 |
| 001 | bw | single | L2 | D_mag | 50 | 0.01603300528 |
| 001 | bw | single | L2 | R_contam | 4 | 0 |
| 001 | bw | double | L3 | A_raw_plus | 8 | -13.22777304 |
| 001 | bw | double | L3 | A_mag | 8 | -13.22777304 |
| 001 | bw | double | L3 | D_mag | 12 | -0.01101710634 |
| 001 | bw | double | L3 | R_contam | 30 | 0 |
| 001 | bw | double | L2 | A_raw_plus | 8 | 22.41544106 |
| 001 | bw | double | L2 | A_mag | 8 | 22.41544106 |
| 001 | bw | double | L2 | D_mag | 12 | 0.01239132991 |
| 001 | bw | double | L2 | R_contam | 12 | 0 |
| 001 | ms | single | L3 | A_raw_plus | 12 | -11.85719451 |
| 001 | ms | single | L3 | A_mag | 12 | -11.85719451 |
| 001 | ms | single | L3 | D_mag | 50 | -0.01426000453 |
| 001 | ms | single | L3 | R_contam | 4 | 0 |
| 001 | ms | single | L2 | A_raw_plus | 12 | 20.113151 |
| 001 | ms | single | L2 | A_mag | 12 | 20.113151 |
| 001 | ms | single | L2 | D_mag | 50 | 0.0160311797 |
| 001 | ms | single | L2 | R_contam | 6 | 0 |
| 001 | ms | double | L3 | A_raw_plus | 8 | -13.22778653 |
| 001 | ms | double | L3 | A_mag | 8 | -13.22778653 |
| 001 | ms | double | L3 | D_mag | 12 | -0.01101693392 |
| 001 | ms | double | L3 | R_contam | 20 | 0 |
| 001 | ms | double | L2 | A_raw_plus | 8 | 22.41546383 |
| 001 | ms | double | L2 | A_mag | 8 | 22.41546383 |
| 001 | ms | double | L2 | D_mag | 12 | 0.01239113641 |
| 001 | ms | double | L2 | R_contam | 20 | 0 |

In the main [017] BW reference, the largest sampled L3 magnetic-only percentage shifts from 12 nm (Single, -11.7254550%) to 8 nm (Double, -13.1487825%), matching the raw-asymmetry ordering. The maximum raw magnetic difference instead occurs at 48 nm for Single and 12 nm for Double, at both edges. Percentage peaks and absolute magnetic signal therefore select different thicknesses. These are sampled extrema, not continuous/global maxima or experimental optima. MS and the restricted [001] results are independently listed above.

## Contamination and signs

| Zone | Solver | Model | Edge | Largest R_contam | Opposite-sign points | D_nonmag-dominated points |
|---|---|---|---|---:|---:|---:|
| 017 | bw | single | L3 | 1.07722111e-11 | 23 | 0 |
| 017 | bw | single | L2 | 3.49951341e-13 | 11 | 0 |
| 017 | bw | double | L3 | 1.85634676e-13 | 23 | 0 |
| 017 | bw | double | L2 | 7.84795655e-14 | 23 | 0 |
| 017 | ms | single | L3 | 1.81602564e-11 | 33 | 0 |
| 017 | ms | single | L2 | 1.41225585e-11 | 1 | 0 |
| 017 | ms | double | L3 | 9.99752507e-14 | 26 | 0 |
| 017 | ms | double | L2 | 8.90124614e-14 | 21 | 0 |
| 001 | bw | single | L3 | 1.09815791e-11 | 34 | 0 |
| 001 | bw | single | L2 | 5.07921778e-12 | 5 | 0 |
| 001 | bw | double | L3 | 1.38798157e-13 | 24 | 0 |
| 001 | bw | double | L2 | 1.20987048e-13 | 20 | 0 |
| 001 | ms | single | L3 | 1.60973221e-11 | 38 | 0 |
| 001 | ms | single | L2 | 3.49374167e-12 | 3 | 0 |
| 001 | ms | double | L3 | 1.34777907e-13 | 32 | 0 |
| 001 | ms | double | L2 | 6.30410032e-14 | 21 | 0 |

Full signed component arrays and every zero-crossing bracket are in components.csv/npz and audit.json. Opposite signs close to roundoff in an almost symmetric reversal-even component are not physically resolved sign reversals. Exact zero contamination at isolated points reflects model symmetry/floating-point cancellation, not a guaranteed experimental background-free optimum. Strong total raw asymmetry alone does not establish a strong magnetic count signal; inspect D_mag, D_nonmag and their common-denominator percentages separately. Post-edge correction, where used in saved spectral diagnostics, is not an intrinsic magnetic estimator.

## Figures and GUI

The original twelve PNG/SVG figures remain unchanged in outputs/ni_emcd_asymmetry_thickness_200kv/figures/. Eight additional figures, each PNG/SVG, are in outputs/ni_emcd_thickness_scientific_audit/figures/: components panels show raw magnetic/nonmagnetic differences, magnetic-only percentage and uncapped contamination; asymmetries panels show the additive common-denominator components alongside the original +M ratio. Each curve uses 51 actual saved points; undefined zero-thickness percentages are gaps.

The primary GUI maps use actual calculated (qx,qy)/(qx,-qy) samples over the full valid stored grid. Raw Magnetic and Raw Nonmagnetic are point-pair differences; total asymmetry includes nonmagnetic diffraction. Physical detector apertures are overlays, independent of map support and allowed to be nonmirrored. Missing/unsupported arrays produce unavailable-data messages; invalid denominators remain NaN. Historical restricted diagnostics remain in Advanced Diagnostics. Detector EELS integrates before taking ratios and is scientifically distinct from these point-pair maps. Existing project registration/open/export is retained; the thickness CSV is an offline study, not a fabricated spectrum project. No production checkpoints are bundled.

## Experimental and numerical limits

Approximate XMCD-constrained MDFF; no complete DFT transition tensor; projected IAM potential; existing longitudinal-transfer model; limited convergence assessment; uncalibrated absolute intensity. No physical electron counts, dose optimization or experimental SNR prediction follows. Outgoing channeling changes sampled percentage peaks and raw magnetic buildup independently. Model-specific thickness extrema are not universal experimental optima. The 2 nm scan does not establish sub-step peak locations.

Release acceptance is documented separately in docs/V061_BETA_ACCEPTANCE.md.

## Sign stability and interpretation of cancellation

[017] single L3: magnetic sign brackets BW [[30, 32], [32, 34], [62, 64], [64, 66]], MS [[30, 32], [32, 34], [62, 64], [64, 66]]; identical.
[017] single L2: magnetic sign brackets BW [[30, 32], [32, 34], [62, 64], [64, 66]], MS [[30, 32], [32, 34], [62, 64], [64, 66]]; identical.
[017] double L3: magnetic sign brackets BW [], MS []; identical.
[017] double L2: magnetic sign brackets BW [], MS []; identical.
[001] single L3: magnetic sign brackets BW [[30, 32], [34, 36], [62, 64], [66, 68], [96, 98], [98, 100]], MS [[30, 32], [34, 36], [62, 64], [66, 68], [96, 98], [98, 100]]; identical.
[001] single L2: magnetic sign brackets BW [[30, 32], [34, 36], [62, 64], [66, 68], [96, 98], [98, 100]], MS [[30, 32], [34, 36], [62, 64], [66, 68], [96, 98], [98, 100]]; identical.
[001] double L3: magnetic sign brackets BW [], MS []; identical.
[001] double L2: magnetic sign brackets BW [], MS []; identical.

All contamination ratios in these saved symmetric paired-detector results are below 2e-11. No sampled percentage peak is reversal-even dominated. Reversal-even opposite-sign counts in the table describe tiny floating-point residuals, not resolved physical cancellation intervals. In particular A_mag and A_raw_plus can still differ visibly even when D_nonmag approximately zero: their denominators differ because M_A+M_B need not vanish. This is why both definitions must be exported explicitly. These observations do not imply that general mistilt/aperture geometries have negligible nonmagnetic asymmetry.

Study source SHA256: `a0e28ea6423b6c7832bb3cce6d69d71aa59336a221baeee3d2556b49ba501283`. Incoming/outgoing bases contain 17 beams for [001] and 59 for [017]. Local magnetization in [017] is [0, -1/sqrt(50), 7/sqrt(50)], obtained from cubic [001]; no magnetic amplitude refitting is used.
