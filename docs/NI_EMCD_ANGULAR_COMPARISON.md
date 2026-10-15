# Ni L3/L2 angular maps and virtual-detector EELS

This presentation mode extends the matched post-edge map workflow with indexed
intrinsic angular maps, total intensity, full-source virtual-detector EELS and
explicit BW/MS discrepancies. It reuses all existing propagation, tensor,
magnetic reversal, fractional detector integration and constant normalization.
The small `emcd_angular_plots.py` module performs visualization/export and
comparison metrics only. Historical CLI defaults and published examples are
unchanged.

```bash
python -m emcd_sim.postedge_emcd_maps \
  --xmcd-file data/wien2k_ni/Ni_fm.xmcd \
  --conditions near-2bc symmetric-3bc \
  --angular-output --full-source-range --energy-points 241 \
  --output outputs/ni_emcd_angular_comparison
```

The calculation uses FCC Ni [001], 200 kV, 30 nm, eta=1, beta=1. Its Fourier
potential cutoff is 0.75 cycles/A; the independent common-beam cutoff is
2.2 cycles/A (45 ZOLZ beams). FFT sampling is 32 square, maximum Strang step
0.04 nm, with 64 common depth points and a 33 square detector map.
Fractional apertures use 64 boundary subpixels. The same Fourier-truncated
independent-atom potential (B=0), tilt, tensor, energy grid and detectors are
used by both methods. FFT amplitudes are projected without renormalization;
the resulting coherences are reused over energy. Existing memory, beam-cap and
FFT guards remain active (estimated pair-array memory 134.60 MiB).

`--full-source-range` chooses the source minimum rather than the historical
837 eV start. For the supplied source, the retained interval is
823.625-882.521 eV, sampled with 241 evenly spaced points (about 0.2454 eV).
This spans the source but does not assert spectral-sampling convergence.
Only L3/L2 maps are retained, at the actual source samples nearest 852.7 and
870 eV: **852.698 and 870.004 eV**. These requested reference energies are
not assumed to be peak positions. The effective tensor always normalizes to
the same original source XAS peak; no separate geometric-kernel rescaling is
applied. The nonzero magnetic post-edge tail is retained without extrapolation.

## Definitions and outputs

Magnetic angular intensity is `(I_plus-I_minus)/2`; nonmagnetic angular intensity
is `(I_plus+I_minus)/2`. The total displayed intensity is `I_plus`. These
full-grid fields come directly from the spectral-weighted tensor contraction.
Post-edge normalization leaves them unchanged. Its observed factor is obtained
only from plus-state detector spectra in 878-882 eV and affects paired detector
contrasts. The oracle even factor is diagnostic only. No pixelwise factor or
fitted method-agreement gain is used.

Near-2BC pairs the upper A aperture with lower B by `(qx,qy)->(qx,-qy)`.
Symmetric-3BC preserves A=RU+LD and B=RD+LU. Physical aperture mapping and
fractional weights are verified by the existing workflow. Paired fields are
NaN outside the weighted A support. The identities
`D_raw=D_mag+D_nonmag` and
`D_corrected=D_mag_processed+D_nonmag_residual` hold pointwise, and weighted
paired fields reproduce original selected-energy detector intensities.

Each geometry has its own folder with:

- `L3_angular_maps.png`, `L2_angular_maps.png`: BW/MS rows and magnetic, even and total columns, indexed hkl, detector outlines, shared axes and method-matched scales. Magnetic scales are symmetric about zero; positive intensities use sequential scales.
- `virtual_detector_eels.png`: A/B EELS, raw/odd/even differences, corrected contrast and residual; selected L3/L2 energies and post-edge window are marked.
- `raw_corrected_emcd_maps.png`: L3 BW/MS by raw/corrected four-panel comparison on one symmetric scale. `L2_raw_corrected_emcd_maps.png` provides the same L2 comparison.
- `bloch_multislice_difference.png`: full-grid magnetic/even MS-minus-BW residuals at both energies, absolute and relative L2 errors; each residual panel has an explicitly labeled symmetric scale.
- `angular_maps.npz`: coordinates, common hkl/gxy, physical/group weights, validity, intrinsic plus/minus/odd/even and paired maps, method labels, selected energies, both coherences, depth points and actual FFT projection leakage. Map axes: method, L3/L2, qy, qx.
- `virtual_detector_spectra.npz`: all original/processed detector spectra, parity references, normalization factors, metric validity and bias diagnostics; method is the first axis.
- `comparison_metadata.json`: geometry, configuration, selected energies, source hash, differences and link to the complete parent metadata.

The root retains the canonical `map_comparison.npz`, `method_comparison.csv`
and complete `comparison_metadata.json` from the existing workflow. All NPZs
load with `allow_pickle=False`. Both propagation results are retained as
coherences and resulting method-specific intensities; no full energy-map cube
is stored. Full-grid map L2 norms include dq^2. Spectral L2 norms use identical
energy trapezoids. Relative discrepancies divide by the larger compared norm,
with a floor of 1e-10 times the relevant intensity norm; absolute errors remain
available for negligible or canceled signals.

Replot all six figure files per geometry from the canonical saved NPZ:

```bash
python -m emcd_sim.postedge_emcd_maps \
  --xmcd-file data/wien2k_ni/Ni_fm.xmcd \
  --angular-output --plot-only --output outputs/ni_emcd_angular_comparison
```

Plot-only reads saved arrays and settings without source loading, propagation,
tensor contraction or normalization. The source argument is retained for CLI
compatibility. Numerical CLI settings are ignored in this mode.

## Scope

These are matched truncated-potential entrance-only relative intensities,
not absolute cross sections or a full DFT-MDFF calculation. The earlier
full-potential 21/37-beam results are a different configuration and are not
validated by this comparison. Neither method models outgoing inelastic
channeling. FFT step/resolution, finite common basis, projection leakage,
depth quadrature, coarse reciprocal sampling, fractional-boundary accuracy
and spectral sampling remain convergence limitations. Scaling changes the
processed magnetic normalization convention; its norm change alone is not a
calibrated magnetic-moment loss. No optimal geometry or quantitative Ni
accuracy is claimed.

## Numerical example

Both geometries were run at the settings above on Python 3.10.9. Full-grid
angular-map differences are symmetric relative L2 differences, without any
normalization fitted to method agreement:

| Geometry / edge | Magnetic abs L2 | Magnetic rel (%) | Even abs L2 | Even rel (%) |
|---|---:|---:|---:|---:|
| near-2BC / L3 | 6.0764e-6 | 0.074493 | 1.0698e-4 | 0.006295 |
| near-2BC / L2 | 6.5021e-8 | 0.074690 | 4.6363e-6 | 0.006349 |
| symmetric-3BC / L3 | 1.6569e-5 | 0.435917 | 2.6321e-4 | 0.013823 |
| symmetric-3BC / L2 | 1.7758e-7 | 0.438380 | 1.1442e-5 | 0.013973 |

Raw/corrected paired-map relative discrepancies are respectively 0.15137% /
0.10734% (near-2BC L3), 0.13473% / 0.14310% (near-2BC L2), 0.14170% /
0.14170% (3BC L3) and 0.14225% / 0.14224% (3BC L2). Near-2BC absolute map
errors fall from 2.318e-5 to 4.048e-6 at L3 and 1.018e-6 to 1.797e-7 at L2.
A lower absolute discrepancy need not imply a lower relative discrepancy,
because correction also reduces the reference norm.

| Geometry / method | alpha observed | alpha oracle | Full-range even suppression (%) | Magnetic norm change (%) | Corrected/reference spectral error (%) |
|---|---:|---:|---:|---:|---:|
| near-2BC / BW | 0.872717641 | 0.871601051 | 97.86233 | -6.79479 | 7.47226 |
| near-2BC / MS | 0.872872282 | 0.871755570 | 97.85957 | -6.78791 | 7.46866 |
| symmetric-3BC / BW | 1.000434716 | 1.000000000 | undefined | +0.021736 | 2.89254 |
| symmetric-3BC / MS | 1.000434861 | 1.000000000 | undefined | +0.021743 | 2.89255 |

Full-range detector A/B spectral BW/MS relative errors are 0.006032% /
0.011839% for near-2BC and 0.005607% / 0.005459% for 3BC. The corresponding
absolute spectral L2 differences are 1.4864e-5 / 3.3980e-5 and 2.8485e-5 /
2.7857e-5. Raw/corrected detector-difference spectral discrepancies are
0.115686% / 0.001129% for near-2BC and 0.027380% / 0.027388% for 3BC.
The tiny integrated even spectrum in 3BC makes its relative method error
undefined (absolute spectral difference 2.63e-16).

These full-range norms include 823.625-837 eV, which was excluded from the
previous post-edge map report. They must not be compared as if they used the
same interval. The selected intrinsic plus/minus/magnetic/even maps and all
detector weights are bitwise unchanged from that matched example; only
spectral sampling/coverage and presentation differ. The post-edge factors
change by less than 7e-8 as a result of the new spectral grid.

Near-2BC correction reduces integrated even contrast strongly but leaves local
structure: L3 spatial even-norm suppression is approximately 84.22%, with a
roughly -6.83% processed magnetic spatial norm change. Intrinsic angular maps
remain unchanged. In 3BC, large opposite-sign local even contrasts cancel in
the grouped spectrum; negligible integrated even intensity does not mean local
purity. Constant normalization slightly increases the spatial even norm.
This distinction remains visible in the raw/corrected paired maps.

Maximum FFT projection leakage is 1.11085e-5 / 1.10123e-5 (near-2BC / 3BC).
Coherence Frobenius differences are 6.08821e-4 / 8.81779e-4, or 0.08744% /
0.10291% relative. These diagnostics quantify residual numerical differences;
they are not convergence bounds.

Seven focused tests passed: the existing six map tests plus one small
full-source real-source test. The new test independently compares angular
terms against the shared contraction at actual source energies, verifies
selected detector integrals and full energy coverage, checks pickle-free
exports, and regenerates all figures with forward contraction disabled.
Existing tests cover reversal parity, exact raw/corrected decompositions,
matched source/detector conventions and legacy binary weights. No broad
regression suite, packaging validation or parameter sweep was performed.
