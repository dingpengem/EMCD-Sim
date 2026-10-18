# Final 200 kV Ni channeling benchmark

The final benchmark is saved separately in
`outputs/ni_double_channeling_final_200kv/`. The production BW curve samples
0–100 nm every 2 nm. MS controls sample 8, 12, 20, 30, 50, 80 and 100 nm.
Sampled extrema are not continuous global extrema, and numerical controls at
representative thicknesses do not certify the entire curve as converged.

## Physical and numerical configuration

Both calculations retain the existing projected Ni IAM and XMCD-constrained
Hermitian dipole tensor, with eta = beta = 1. Single Channeling includes the
incoming elastic wave and localized ionization. Double Channeling additionally
propagates the outgoing electron at its post-loss energy. Neither model supplies
a complete complex DFT-derived MDFF, an absolute cross section, or a new
atomic-3D potential.

The geometries are the explicit [001] (200) systematic-row approximation and
the genuine full-2D [017] projected crystal at exact (200) Bragg alignment.
The latter is not an artificially isolated two-beam wavefield. Magnetization is
crystal [001], rotated into each local frame before contraction.

The fixed native evaluation energies are **831.4778 eV (L3)** and
**848.698 eV (L2)**. The active source's automatically selected L3 magnetic
extremum is 831.271 eV; the benchmark preserves its previously validated
evaluation energy rather than retuning it with thickness. No experimental
energy shift is applied. These two samples alone are not a full EELS spectrum.

The numerical profile uses potential Fourier cutoff 6.2 Å⁻¹, matched incoming
and outgoing beam cutoff 4.6 Å⁻¹, FFT mesh 48, 257 depth nodes, maximum MS step
0.04 nm, and float64/complex128 precision. The detector grid has 193 × 193
samples over ±0.5 Å⁻¹, with fractional circular-aperture weights using 64
boundary subpixels per dimension. Detectors have centres
(0.283768444948922, ±0.283768444948922) Å⁻¹ and radius 0.0908059024 Å⁻¹.

Crystallographic reciprocal coordinates use **g = 1/d**, in Å⁻¹. Values formerly
labelled cycles/Å are numerically identical; there is no extra 2π conversion.
The beam cutoff selects the maximum elastic beam radius. Its approximate
angular equivalent is λ|g|max, not the detector collection angle. The potential
Fourier cutoff selects elastic couplings with |g−g′| below the cutoff; it is
neither an ionization momentum-transfer limit nor an excitation-error threshold.

## Raw, relative and PRB quantities

For detector J, N_J = (I_J(+M)+I_J(−M))/2 and
M_J = (I_J(+M)−I_J(−M))/2. The signed raw differences are
**D_mag = M_A−M_B** and **D_nonmag = N_A−N_B** in arbitrary units.
Their sum equals the raw +M detector difference.

Relative magnetic and nonmagnetic components are respectively
100 D_mag/(N_A+N_B) and 100 D_nonmag/(N_A+N_B). They share one denominator;
neither curve is independently peak scaled. The separate PRB benchmark is
100 [I_A(+M)−I_B(+M)]/[I_A(+M)+I_B(+M)]. It is not the magnetic-only percentage.
All ratios follow depth and detector integration. At zero thickness, raw
inelastic intensities are zero and percentages are undefined (NaN).

The GUI's primary spectral view preserves raw detector A/B EELS, a single
Raw EMCD (a.u.) / Relative EMCD (%) switch for the two components, and a
separate PRB readout at a recorded energy. Plot selection must not change
simulation arrays. CSV/NPZ retain both raw and percentage quantities regardless
of the displayed mode. Advanced post-edge correction remains a diagnostic:
corrected contrast is not intrinsically magnetic EMCD.

Raw intensity and percentage convey different information. A large percentage
alone does not establish detectability. The optional comparison diagnostic
|D_mag|/sqrt(N_A+N_B) is an **arbitrary-scale detectability proxy, not experimental
SNR**; compare it only at consistent intensity scale and sampling. Arbitrary
intensity is not electron count. Physical SNR needs dose, efficiency, energy-bin
width, background and other noise calibration. For four independent reversal
measurements, the magnetic-odd estimator has variance
(Var A+ + Var B+ + Var A− + Var B−)/4; the two-spectrum difference variance is
not interchangeable with this estimator.

## Reproduction and convergence scope

The completed BW sampling gives these strongest absolute values. Signs refer
to the retained detector order and magnetization convention.

| Geometry | Model | Thickness (nm) | L3 PRB (%) | L2 PRB (%) |
|---|---|---:|---:|---:|
| [001] row | Single | 12 | −11.85726490 | +20.11327018 |
| [001] row | Double | 8 | −13.22777304 | +22.41544106 |
| [017] full 2D | Single | 12 | −11.65564115 | +20.09789902 |
| [017] full 2D | Double | 8 | −13.06008297 | +22.54492355 |

These are extrema of the actual sampled curves, not imposed fit parameters.
The outgoing-channeling model changes both the thickness dependence and the
sampled strongest L3 magnitude. It cannot be represented by a constant empirical
multiplier applied to the Single curve.
These percentage extrema do not establish an experimentally optimal thickness
or a maximum in raw magnetic intensity or shot-noise SNR.

Run `python scripts/ni_double_channeling_final_200kv.py --run` to resume only
missing cases with matching provenance, then
`python scripts/ni_double_channeling_final_report.py` to generate the report.
Completed compatible checkpoints are reused without overwriting earlier
studies. The output provenance records source SHA256, calculation commit,
physical configuration, numerical profile, areas and implementation hashes.

Checkpoint A passed all 118 engine/geometry/thickness cases, including exact
zero-thickness boundaries and compatible reused checkpoints. The maximum
matched BW/MS discrepancy over the seven nonzero MS controls is **0.00777326
percentage points**, with maximum raw-state relative error **0.01302088%**.
Both pass the unchanged limits. L3/L2 signs oppose each other at every nonzero
BW thickness sampled here. The full raw curves and actual zero-crossing
brackets remain available; no continuous oscillation period or global optimum
is inferred from the discrete samples.

The acceptance limits remain 0.01 percentage points for dichroism and 0.1%
relative raw intensity. Potential, basis, FFT, slice and depth sensitivity are
distinct from BW/MS agreement and from physical-model accuracy. Earlier
potential/FFT controls used beam cutoff 3.8 Å⁻¹; independent 3.8→4.6 Å⁻¹ basis
controls cover 8/12/30/100 nm. They are not a joint convergence proof at every
enlarged-basis thickness. Older 2.2 Å⁻¹ production curves remain preserved and
are not substituted for this profile.

The machine-readable acceptance outcome and actual sampled extrema are in
`checkpoint_A.json` and `sampled_extrema.csv`; signed oscillation extrema and
zero-crossing brackets are saved separately. PNG/SVG figures distinguish BW
curves sampled every 2 nm from discrete MS controls. Raw reversal intensities,
component differences and denominators are retained in CSV/NPZ.

## GUI validation and saved figures

Checkpoint B passed **48 actual GUI/CLI comparisons**: [001]/[017],
8/12/30 nm, Single/Double, BW/MS, and both native edge energies. Maximum
GUI/CLI difference is **0.00011724 pp**, and maximum relative raw-state error
is **0.00013769%**. Double results reproduce the CLI to floating-point precision.
The preserved legacy Single BW numerical quadrature differs slightly from the
CLI analytic coherence, within the unchanged limits. Maximum GUI BW/MS gap at
these three thicknesses is **0.00503654 pp**. Results are saved under
`gui_validation/`, including separate reference and BW/MS comparison CSVs.

The **76 focused tests** cover the actual six dispatch routes, raw detector
references/provenance, reversal parity, map integrals, legacy Single contraction,
old project loading, model persistence, memory admission/concurrent cleanup,
normalization, display immutability and exports. The source physics modules
remain unchanged. No broad regression suite or application packaging was run.

The default figures are `L3_thickness`, `L2_thickness`, `BW_MS_comparison` and
`convergence_summary`, each as PNG/SVG. `representative_eels.png/.svg` shows
genuine Single BW [017], 8 nm EELS with 242 calculated native-energy samples;
its full raw/relative spectra are in `representative_eels.csv` and the original
NPZ in `gui_validation/native_eels_017_single_bw/`. This full-spectrum example
is explicitly Single Channeling. Production Double results here contain the
two selected native energies; full Double spectra are supported by the GUI but
were only exercised in the small focused energy-grid test, not calculated at
the production profile for every thickness.

`gui_primary_spectra.png` is a source-GUI preview from saved numerical data.
It does not imply a rebuilt Windows executable. The GUI's Raw/Relative switch
preserves both components and the underlying numerical arrays; advanced legacy
diagnostics remain available. See [GUI usage](EMCD_GUI.md) for units,
normalization, angular point-pair definitions and export details.
