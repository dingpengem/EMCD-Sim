# Ni [001] EMCD and extinction distance at 100/200/300 kV

Complete results are under `outputs/ni_voltage_dependence_100_200_300kv/`.
Each voltage has 51 thickness points, 0-100 nm in 2 nm increments, with
Bloch-wave and projected-2D FFT multislice. The original 200 kV study and
XMCD source remain unchanged. This task changes scripts/documentation only;
no solver, GUI, MDFF or package version is changed and no atomic-3D method
is used.

## Configuration and 200 kV reuse

This uses the previously validated **explicit (200) systematic-row
approximation**, not the full-[001]-ZOLZ control or an isolated two-beam
propagation. There are 11 row beams (-10,0,0) through (10,0,0) in increments
of 2, with beam/potential cutoffs 3.2/2.2 cycles/Angstrom, FCC Ni a=3.524
Angstrom and B=0. FFT is 32x32 with maximum physical step 0.04 nm. Every
positive thickness has 64 equally spaced trapezoidal depth nodes. The FFT
subdivides intervals to reach the requested depth exactly; actual thickness
equals requested thickness. Calculations are sequential and checkpoints
contain compact detector states/populations, not full-series wavefields.

The source SHA256 is unchanged:
`a0e28ea6423b6c7832bb3cce6d69d71aa59336a221baeee3d2556b49ba501283`.
XMCD-constrained eta=beta=1, crystal magnetization [001] and the proper [001]
frame are fixed. Reversal tensors are identical across voltages. Evaluation
energies are fixed at **831.4778 eV (L3)** and **848.698 eV (L2)** on the native
axis; no voltage/thickness-specific energy optimization or energy shift is used.

Detectors are independently derived as G/2 +/- perpendicular(G)/2, giving
A=(0.283768444948922,+0.283768444948922),
B=(0.283768444948922,-0.283768444948922) cycles/Angstrom. Radius is fixed at
0.0908059024 cycles/Angstrom for all voltages. Fractional integration uses
64 subpixels and a **193x193** grid over [-0.5,0.5] cycles/Angstrom. Both
apertures are fully supported. Float64/complex128 precision and the existing
2048 MiB memory admission checks are retained; supported pixels are evaluated
through the existing tensor kernel in batches of 64. No settings are reduced
to satisfy memory limits.

Before new propagation, the prior 200 kV configuration, source/code hashes,
basis, frames, detectors, energies and slicing were inspected. The physical
settings match, but its complete thickness curve used a coarse 33x33 grid over
[-1,1]. Prior validation found a 0.078074 pp L3 change at 12 nm upon finer
integration. Therefore the primary voltage comparison uses the validated fine
grid consistently, rather than accepting coarse intensity-field quadrature.

The five compatible fine-grid 200 kV points at 10/12/20/30/50 nm are **reused**.
Only missing fine-grid points are calculated; zero thickness is defined
analytically. The old 51-point coarse curve is retained/exported as a reference,
not recalculated. One matched coarse-grid 12 nm check reproduces the original
four detector-state intensities **exactly for both solvers**, including the
old BW L3 -11.77570914%. The new fine-grid BW maximum is -11.85378347% at
12 nm. This difference is detector integration, not a changed physical model.
The existing 200 kV 385-grid control is also reused.

## Relativistic quantities and exact Bragg alignment

The existing relativistic wavelength and velocity functions are used. Absolute
x tilt is recalculated at each voltage so that k_incident,x=-Gx/2; the same
off-row y tilt of +35 mrad is retained. All three target excitation errors
are zero to numerical precision. The full excitation-error vector and
Hamiltonian/eigenvectors are exported, not inferred from the 200 kV solution.

| Voltage (kV) | Wavelength (Angstrom) | Velocity (m/s) | Interaction constant (rad / V / nm) | xi_200 (nm) |
| ---: | ---: | ---: | ---: | ---: |
| 100 | 0.03701436614 | 164352479.7 | 0.00924395817 | 29.63348170 |
| 200 | 0.02507934045 | 208450034.4 | 0.00728840104 | 37.58446657 |
| 300 | 0.01968748901 | 232796486.3 | 0.00652616142 | 41.97423992 |

| Voltage (kV) | Bragg x tilt (mrad) | Fixed reciprocal aperture's semiangle (mrad) |
| ---: | ---: | ---: |
| 100 | -10.50350912 | 3.36112292 |
| 200 | -7.11672544 | 2.27735214 |
| 300 | -5.58668814 | 1.78774021 |

These are fixed reciprocal-space acceptance comparisons, not fixed-mrad
collection-angle comparisons. The latter optional study was not added.
Transmitted-centered coordinates and projected ZA positions are recorded in
configuration metadata. No detector or magnetic-response optimization occurs.

The solver's convention is `xi_200 = pi / abs(H_000,200)` with H in inverse nm.
Its IAM (200) potential coefficient is 11.4685686982 V at every voltage.
Interaction constant is recovered directly from `abs(H_000,200)/(10*abs(V200))`
in rad/(V Angstrom), also reported times 10 in rad/(V nm). An independent SI
check `e/(hbar*v)` with the appropriate length conversion agrees. Mean inner
potential is a discarded common phase, as in the unchanged solver.

For fixed potential, the extinction ratios are:

- xi_200(100 kV) / xi_200(200 kV) = **0.7884502403**.
- xi_200(300 kV) / xi_200(200 kV) = **1.1167975430**.

They agree with the independently calculated velocity ratios and the expected
approximately 0.79/1.12 sanity checks; neither ratio is imposed or fitted.
The subscript 200 denotes the **reflection**, not the accelerating voltage.

## EMCD magnitudes and peak thicknesses

Primary signed percentage is `100*(A_plus-B_plus)/(A_plus+B_plus)`, without a
factor two, peak scaling or post-edge correction. Magnetic-only and even
diagnostics retain their reversal-even denominator `N_A+N_B`. Even imbalance
is numerical zero for this symmetric row model, so primary and magnetic-only
percentages coincide to roundoff. Raw A/B states and both denominators remain
separately exported. At zero thickness all inelastic intensities are zero and
relative percentages are NaN, not zero.

| Voltage (kV) | BW maximum signed L3 (%) | MS maximum signed L3 (%) | Thickness (nm) | BW L2 at that thickness (%) |
| ---: | ---: | ---: | ---: | ---: |
| 100 | -11.54244896 | -11.54246348 | 10 | +19.55399569 |
| 200 | -11.85378347 | -11.85378188 | 12 | +20.10740700 |
| 300 | -11.89414343 | -11.89414664 | 14 | +20.18495419 |

For both solvers, the sampled maximum absolute L2 also occurs at the listed
thickness. `summary.csv` includes both edges' maxima and magnetic-only values.
These are sampled extrema on a 2 nm grid, not fitted sub-grid optima. No
additional 1 nm thickness refinement is performed. The strongest EMCD shifts
earlier at lower voltage. From 100 to 300 kV, maximum L3 magnitude increases
by about 3.05% relative (0.35169 percentage points), a modest amplitude change
compared with the shift in thickness scale.

Both solvers and both edges give these sampled sign-change brackets (nm):

| Voltage (kV) | Brackets |
| ---: | --- |
| 100 | 24-26, 26-28, 50-52, 52-54 |
| 200 | 30-32, 34-36, 64-66, 66-68 |
| 300 | 34-36, 36-38, 70-72, 72-74 |

Brackets are not exact zero locations. All positive-thickness percentages are
finite; no relative error or normalization is divided by the magnetic zero.

## Extinction scaling and elastic oscillations

For an **ideal two-beam Bragg** model, the unchanged solver independently
confirms `I200=sin^2(pi*t/xi_200)`. The eigenvalue-gap population period is
exactly xi_200; propagation gives I200=1 at xi/2 and I200=0 at xi. This is an
intensity-period convention, not an assertion of an amplitude period xi.
Ideal diagnostic populations use the same 2 nm output sampling; the two
isolated xi/2 and xi checks are identity checks, not a refined thickness scan.

The multibeam row calculation retains other reflections and has different
effective periods. Direct sampled (200) population maxima give:

| Voltage (kV) | Row (200) peak positions (nm), BW | Successive spacings (nm) | Spacing / ideal xi |
| ---: | --- | --- | --- |
| 100 | 14, 40, 66, 92 | 26, 26, 26 | 0.87739 |
| 200 | 18, 50, 82 | 32, 32 | 0.85142 |
| 300 | 18, 54, 90 | 36, 36 | 0.85767 |

These discrete multibeam spacings are not new definitions of extinction
distance. All target populations are selected by **hkl=(200)**; the first
nonzero row-basis entry is (-200), which must not be substituted for (200).
EMCD depends on accumulated depth coherence, so its strongest signal need not
occur at an exit-beam population maximum.

Plotting against each voltage's own `t/xi_200(V)` aligns the broad EMCD lobes
much better than physical thickness alone. Sampled strongest-L3 positions are
0.33746, 0.31928 and 0.33354. Their spread is 0.01818, compared with 0.10643
when all physical peak positions are divided by the fixed 200 kV xi. This is
a landmark comparison, not a curve fit or proof of exact collapse. Comparisons
of peak locations remain limited by normalized sampling steps of 0.048-0.067,
larger than that sampled peak spread. All three complete normalized curves
share a domain only up to approximately
2.38; the lower-voltage curve extends farther in normalized thickness.

Exact collapse is not expected. Higher-row detunings in H scale with wavelength
while off-diagonal couplings scale with gamma*wavelength. Thus `H*xi` retains
voltage-dependent diagonal entries, even though its off-diagonal entries scale
together. Longitudinal loss momentum also changes: L3 qz magnitudes are
0.122329/0.096450/0.086363 cycles/Angstrom at 100/200/300 kV; the existing
kernel uses their negative sign. These change the angular MDFF/Coulomb
contraction without changing the source tensor or eta/beta. Voltage therefore
affects both period and amplitude through distinct mechanisms.

## Numerical checks and limits

Maximum absolute BW-MS raw PRB discrepancies over 0-100 nm, in percentage points:

| Voltage (kV) | L3 | L2 |
| ---: | ---: | ---: |
| 100 | 0.000305080 | 0.000516961 |
| 200 | 0.000151988 | 0.000257936 |
| 300 | 0.000090109 | 0.000152958 |

Maximum FFT norm error is below 1.5e-13 and maximum population excluded from
the common row basis is below 9.6e-8 of incident intensity. No projection
renormalization is applied. Individual beam populations and their excitation
errors are exported for all retained beams and every thickness.

At 12 nm, 193-to-385 detector-grid checks for both edges/solvers and all
voltages change dichroism by less than **0.000556 pp**. A/B intensity changes
are also exported. At 100 nm, an analytic depth integral of the same finite BW
Hamiltonian checks the 64-node result: maximum absolute errors across both
edges are 0.004760/0.001372/0.006527 pp at 100/200/300 kV. These meet the
previously stated local 0.01 pp trend criterion, but are much larger than
some solver discrepancies and can matter near a crossing. They do not establish
global depth, potential-cutoff or basis convergence. Use finer quadrature for
precision zero-crossing work; this scan retains 64 nodes consistently and
does not claim sub-grid crossing locations. The control CSV keeps absolute
magnetic differences and masks relative magnetic errors below an explicit
5%-of-peak signal floor.

Seven focused tests cover relativistic quantities/units, velocity-extinction
scaling, fresh Bragg tilts and fixed acceptance, unchanged source tensors,
nonuniform Hamiltonian scaling, reference reuse, complete thickness/edge/method
sequences, zero handling, PRB/reversal identities, correct beam indexing,
BW-MS consistency, preservation and all seven figure exports. No broad suite
or executable build is run.

## Interpretation relative to the PRB benchmark

Lower voltage does shorten extinction distance and move the strongest EMCD
toward thinner specimens in this model. This could contribute to a difference
in a benchmark's favorable **thickness**, but the tested voltage range changes
the L3 maximum only modestly and does not bring it to the reference's approximate
15-20% magnitude. L2 values near 20% must not be substituted for an L3 comparison.
**The accelerating voltage of PRB 2007 Figure 5 remains unidentified.** This
study neither verifies nor infers a particular published voltage.

The XMCD-effective tensor is not a full transition-derived DFT MDFF, and only
entrance channeling is included. Outgoing channeling, absolute energy/source
conventions, finite collection acceptance and potential/basis approximations
remain material differences. Raw intensities are relative model units, not
voltage-calibrated absolute experimental cross sections. No empirical magnetic
scaling, forced period collapse or fitting is used.

## Files and reproduction

From the repository root in the existing `emcd-python` environment:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
python scripts/ni_voltage_dependence.py
python -m pytest tests/test_ni_voltage_dependence.py -q
```

`--memory-budget-mib` retains the existing selectable budgets, default 2048;
`--output` selects another local directory. Matching checkpoints resume without
rerunning scattering; completed-point CSVs are regenerated without duplicates.

- `results.csv/npz`: all 612 voltage/thickness/edge/method records, physical
  quantities and units, tilts, detectors, source model, raw reversals, N/M,
  denominators, percentages, t/xi and compact elastic exit populations.
- `voltage_physics.csv`, `dynamical_coefficients.npz`: wavelength, velocity,
  interaction constant, xi, potential coefficient, Hamiltonian, eigenvalues,
  eigenvectors, entrance coefficients, full hkl/g/s and ideal populations.
- `summary.csv/json`, `elastic_periods.json`, `sign_change_brackets.csv`.
- `elastic_populations.csv`, `bw_ms_differences.csv`, `propagation_diagnostics.json`.
- `numerical_controls.csv`, `numerical_control_errors.csv`: grid and analytic
  depth checks, with absolute errors and explicitly gated relative errors.
- `data_origins.csv`, `reference_200kv_coarse33.csv`, `reference_reproduction.json`,
  configuration/provenance and preservation hashes.
- Seven PNG/SVG figures: L3, L2, magnetic-only, t/xi, elastic populations,
  BW-MS differences, and xi versus voltage/velocity scaling. Colors are
  consistent (100 blue, 200 orange, 300 green); solid BW/dashed MS. Curves
  connect original samples without smoothing or fitting.

Only scripts, focused tests and documentation are committed. Generated numerical
data and figures remain local; no push, package build or release is performed.
