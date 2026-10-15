# Independent multislice reference for entrance-channeling EMCD

This workflow compares independently computed Bloch-wave and real-space FFT
incident waves, then applies the **same** XMCD-constrained effective dipole
MDFF contraction to both. It tests numerical incident propagation and
coherence within a controlled projected-potential model. It is entrance-only,
relative intensity, and **not quantitatively validated Ni EMCD**.

## Matched propagation and Fourier conventions

The existing periodic FCC Ni [001] FFT reference propagates a transverse
periodic envelope through a real, projected, z-independent independent-atom
potential. It is not an atom-layer-resolved 3D multislice calculation.
`FourierCutoffPotential` applies the same explicit Fourier harmonic cutoff to
the Bloch Hamiltonian. Both methods use the same Ni scattering factors,
Debye-Waller B, voltage, tilt, thickness and omitted U000 mean phase.

The conventions are unchanged:

```text
psi(r,z) = sum_g a_g(z) exp(+2*pi*i*g.r)
a = fft2(psi)/N^2
FFT harmonics (m,n) -> hkl=(2m,2n,0), g=(2m/a,2n/a)
D_g = -10*pi*lambda*(|g+k_perp|^2-|k_perp|^2)  [nm^-1]
U_G = 10*gamma*lambda*F_G/Omega, U_000=0
```

FFT array axes follow the existing `ij` ordering (first m, then n), while
detector images use `xy` grids. Integer hkl lookup, rather than an image-axis
assumption, maps coefficients between methods. The independent controlled
potential test verifies the positive potential-transmission sign through
`d a_g/dz = +i H_g0` at the entrance, as well as agreement of complex
amplitudes for both untilted and tilted propagation. No conjugation, Fourier
sign reversal or fitted correction is used to obtain agreement.

FFT propagation retains the existing Strang split
`exp(iD dz/2) exp(iU dz) exp(iD dz/2)`.
Each requested-depth interval is divided into `ceil(delta_z/slice_step_nm)`
equal steps. The configured slice step is an upper bound, not necessarily
the actual step for every interval. This subdivision can change when depth
sampling changes; both controls are separately recorded.

`fft_multislice_ni(..., return_amplitudes=True)` optionally retains raw
complex coefficients at every requested depth in `ElasticFFTResult.amplitudes`.
Depths, FFT-ordered hkl, reciprocal coordinates, intensities, FFT grid and
potential/slice settings remain available on the existing result. With the
flag omitted, amplitudes are None and historical intensities and propagation
are unchanged. The focused test checks bitwise equality of intensities with
and without export.

## Projection, phase and coherence

The FFT contains many more channels than the finite Bloch basis. Its
amplitudes are selected onto the **same ordered hkl** used for Bloch
propagation and for both inelastic contractions. They are not renormalized.
The full FFT elastic norm and intensity outside this basis are recorded at
every depth. The projected norm can be below one; treating it as one would
hide truncation. Common beams and potential harmonics are required to lie
safely below the FFT Nyquist boundary, and pair clipping by max_beams is
rejected.

Raw complex amplitudes are saved. For an additional physically meaningful
amplitude diagnostic, at each depth the overlap `sum(conj(a_BW)*a_MS)`
defines a global phase. Multiplication by its opposite phase aligns MS only
for reporting the amplitude residual. Vanishing overlap is marked invalid.
This operation never changes the propagated data or the coherence used for
EMCD. Relative beam phases remain essential and are not adjusted.

For both methods the exact same depth nodes and quadrature are used:

```text
z = linspace(0,t,depth_steps)
C_gh = trapezoid[a_g(z)*conj(a_h(z)), z] / t
```

A depth-dependent common phase cancels at each node. Coherence Hermiticity,
eigenvalues, trace/norm, raw and phase-aligned amplitude residuals, and full
elastic intensity total variation are reported. At a given depth, the full
elastic TV is one half the sum of the absolute common-beam intensity
differences plus the excluded FFT intensity. No projected-flux correction
is applied. Positive semidefiniteness is checked within floating-point
tolerance, including for the projected FFT coherence.

## Shared entrance-only inelastic contraction

`run_tensor_with_coherence(model, tensor, coherence, ...)` extracts the
existing inelastic integration from `single_channeling_tensor.py`. The model
carries ordered beam hkl, reciprocal vectors, voltage, FCC site positions,
detector positions/radii and chiral groups. The helper constructs the same
coordinates, hard masks and dq^2 weights as before and retains:

```text
S(Q_g,Q_h,E) = Q_g^T T(E) Q_h, Q=2*pi*q
I(q,E) = t * Re sum_gh [C_gh P_gh S(Q_g,Q_h,E) / (|Q_g|^2 |Q_h|^2)]
```

The site-phase matrix P, angular-wavevector conversion, external Coulomb
factors, longitudinal-transfer approximation, and numerical nonnegativity
tolerance are unchanged. `run_tensor_single_channeling` preserves its public
interface and obtains the existing Bloch coherence before calling the shared
helper. Tests check its output against the supplied-coherence path and verify
that halving a coherence halves intensity, without trace renormalization.
Existing tensor contraction and elastic-reference tests also pass.

Both methods use the same eta/-eta effective tensors, common source peak N
normalization, and actual selected source sample. The tensor factory uses
two source samples as required by its existing interface, then the selected
single sample is passed as a `DipoleTensor` to the contraction. No full energy
spectrum is needed, and no independent normalization is introduced.

The existing `parity_spectra` gives Delta_mag=(Delta_plus-Delta_minus)/2,
Delta_nonmag=(Delta_plus+Delta_minus)/2 and their common-Sigma_ref normalized
asymmetries A_mag/A_nonmag. Paired raw asymmetries retain their separate
sums and all inherited NaN/validity masks. The existing magnetic contribution
index f_mag is also retained. See the [geometry decomposition guide](XMCD_GEOMETRY_MAGNETIC_DECOMPOSITION.md)
for the precise definitions and metric floors. Reversal-even intensity maps
are not the same quantity as reversal-even detector differences.

Scalar discrepancies include absolute differences and symmetric relative
errors `abs(BW-MS)/max(abs(BW),abs(MS))`. Relative asymmetry/index errors are
undefined below 1e-8; unnormalized differences and Sigma_ref use a floor of
1e-10 times the larger detector normalization. Floor-aware signs are stored
alongside them. Near-zero components must be judged using absolute errors,
not a ratio of numerical roundoff. Maps retain both total states and their
odd/even components, maximum absolute error, absolute L2 error and relative
L2 error (undefined at norm <=1e-14).

## Reproduce the small benchmark

From the repository root in the existing environment, these single-line
commands work on Windows CMD, macOS and Linux:

```text
python -m pip install -e ".[dev]"
python -m emcd_sim.multislice_emcd_reference --xmcd-file data/wien2k_ni/Ni_fm.xmcd --check-propagation-controls --output outputs/ni_multislice_emcd_reference
```

Defaults select zone-axis and near-2BC, 10 and 30 nm, 200 kV, eta=beta=1,
L3 reference 852.7 eV, B=0, and these **distinct controls**:

| Control | Default | Meaning |
| --- | ---: | --- |
| `--potential-cutoff` | 0.75 cycles/angstrom | Shared potential harmonics (four nonzero axial harmonics here) |
| `--beam-cutoff` | 2.2 cycles/angstrom | Common finite Bloch/inelastic basis (45 beams) |
| `--fft-grid` | 32 | 32x32 periodic FFT envelope channels |
| `--slice-step-nm` | 0.04 nm | Maximum FFT propagation substep |
| `--depth-steps` | 64 | Common coherence integration samples, including both endpoints |
| `--detector-grid` | 33 | Common legacy hard-mask detector integration grid |

Potential cutoff is not beam cutoff. A larger beam basis permits repeated
scattering through channels above the potential harmonic cutoff.
`--conditions` also permits nominal symmetric-3BC. CLI controls include
`--thickness-nm`, `--acceleration-kv`, `--b-factor-angstrom2`,
`--offzone-tilt-mrad`, `--eta`, `--beta`, `--energy-ev`, and `--max-beams`.
All selected conditions use finite common 2D bases, not an exact two-beam
truncation. Symmetric-3BC remains an illustrative nominal geometry.

Before any MDFF contraction, the code estimates pair-array working memory
as `64*detector_grid^2*common_beam_count^2` bytes (about **134.6 MiB** at these
defaults). This is an allocation estimate, not a measured process-memory bound.
`--max-kernel-mib` rejects oversized requests (default 512 MiB). The full
32x32 FFT basis is never passed into a dense all-pairs inelastic kernel.

No fractional-aperture patch exists here: both methods deliberately use
identical legacy hard masks with unchanged radii. At 33x33 the zone-axis
apertures each contain **7 pixels**, and near-2BC each **4 pixels**. This is
a small controlled method comparison with unresolved aperture integration,
not a reliable cross-geometry intensity ranking. Aperture pixel counts are
recorded. Increasing detector resolution may require more kernel memory;
no adaptive integration or aperture algorithm is added.

The optional `--check-propagation-controls` performs only two extra wave-only
checks on the **last case**: halve the FFT slice step, and propagate Bloch
waves with cutoff increased by 0.4 cycles/angstrom. The larger Bloch waves
are projected back onto the original common channels without renormalization.
No larger all-pairs MDFF calculation is performed. This diagnoses the residual
without a full convergence campaign; it does not establish convergence.
For the defaults the target is near-2BC at 30 nm, with 69 Bloch beams.

The reusable API separates calculation and output:

```python
from emcd_sim.multislice_emcd_reference import (
    MultisliceEMCDConfig, run_multislice_emcd_reference,
    check_propagation_controls, save_multislice_emcd_reference,
    plot_multislice_emcd_reference,
)
result = run_multislice_emcd_reference("data/wien2k_ni/Ni_fm.xmcd", MultisliceEMCDConfig())
result.metadata["targeted_propagation_check"] = check_propagation_controls(result)
save_multislice_emcd_reference(result, "outputs/ni_multislice_emcd_reference")
plot_multislice_emcd_reference(result, "outputs/ni_multislice_emcd_reference")
```

## Outputs and executed comparison

The output directory contains:

- `elastic_complex_comparison.npz`: common hkl/g, depths, raw complex BW/MS
  amplitudes, global-phase diagnostics, projected-basis leakage and full
  norms at every depth, full FFT hkl and exit elastic intensities.
- `coherence_comparison.npz`: ordered BW/MS complex coherence matrices.
- `emcd_method_comparison.csv/.npz`: all paired detector/parity quantities,
  normalization, validity and contribution metrics. NPZ additionally stores
  odd/even and paired total maps with their shared reciprocal-coordinate grid.
- `comparison_metadata.json`: numerical controls, geometry/apertures, exact
  XMCD source SHA256, source normalization, software commit/dirty status,
  Python version, all discrepancy metrics and approximation flags.
- `bloch_multislice_emcd_comparison.png`: one six-panel elastic, complex/
  coherence, odd/even asymmetry, map-error and leakage comparison.
- `targeted_propagation_check.json`: only when the optional check is requested;
  its contents are also recorded in the metadata.

Cases are ordered by condition then thickness, and each case has Bloch then
FFT method records. NPZ numeric arrays require no pickle. Coordinates are
cycles/angstrom externally. The actual selected energy in the executed
benchmark was **852.698 eV**. The exact input-byte hash was
`bb9bdd478d54cc8de60403409f4d90e63deb11a64891bbac6754f867be14deda`
(the existing Windows CRLF checkout; source data were not changed).

| Geometry / thickness | A_mag BW | A_mag FFT | A_nonmag BW | A_nonmag FFT |
| --- | ---: | ---: | ---: | ---: |
| Zone-axis / 10 nm | 0.0009053348 | 0.0009053388 | ~0 | ~0 |
| Zone-axis / 30 nm | 0.0002906143 | 0.0002906160 | ~0 | ~0 |
| Near-2BC / 10 nm | 0.04173789 | 0.04173719 | -0.06455121 | -0.06458029 |
| Near-2BC / 30 nm | 0.01135648 | 0.01135599 | -0.06687730 | -0.06678893 |

Across the four baseline comparisons:

- Maximum absolute A_mag discrepancy: **6.92e-7**.
- Maximum absolute A_nonmag discrepancy: **8.84e-5**; zone-axis even
  differences are roundoff, so relative errors there are undefined.
- Maximum full elastic TV over depth: **2.29e-4**.
- Maximum phase-aligned component amplitude residual: **2.49e-3**.
- Largest absolute coherence Frobenius discrepancy: **6.09e-4**; relative
  coherence discrepancy **8.74e-4**.
- Largest magnetic-map relative L2 discrepancy: **7.45e-4**; even-map
  relative L2 discrepancy **6.30e-5**.
- Maximum excluded FFT intensity: **1.11e-5**; this is below the configured
  leakage warning of 1e-3, which is a diagnostic threshold, not an error bound.
- Maximum elastic norm error: **2.34e-14**. Coherences are Hermitian and PSD
  within floating-point tolerance, and total inelastic maps are nonnegative
  within the existing solver tolerance.

The targeted near-2BC/30-nm check gives a more specific diagnosis:

| Comparison of coherences on original 45 channels | Frobenius difference |
| --- | ---: |
| FFT step 0.04 vs 45-beam BW | 6.08821e-4 |
| FFT step 0.02 vs 45-beam BW | 6.08828e-4 |
| FFT step 0.04 vs FFT step 0.02 | 6.00385e-6 |
| FFT step 0.02 vs projected 69-beam BW | 3.37627e-6 |

This supports finite Bloch-basis truncation as the dominant residual in this
case, not an MDFF mismatch or a Fourier-sign correction. Small excluded
intensity does not guarantee negligible relative-phase error: omitted
channels can feed back into retained waves. Slice-step refinement alone
does not remove that truncation effect. The 69-beam check is wave-only;
no improved EMCD result or infinite-basis convergence is claimed from it.

These are numerical method-consistency results at a deliberately small,
matched truncated potential. They are not reference values for physical Ni
and must not be compared directly with previous larger-potential examples
as if only the propagation method had changed.

## Focused verification and physical limits

```text
python -m pytest -q tests/test_multislice_emcd_reference.py tests/test_elastic_reference.py tests/test_single_channeling_tensor.py
```

**18 focused tests passed** on **Python 3.10.9**. The seven new test cases
cover Fourier hkl/sign mapping, z=0 amplitudes, elastic norm, tilted and
untilted complex-wave matching, global phases, coherence Hermiticity/PSD,
eta=0 and reversal parity, nonnegative totals, unnormalized projection,
unchanged legacy outputs, supplied-coherence integration, memory/control
guards, targeted wave-only checks and saved outputs. Existing elastic and
tensor compatibility checks pass. The final full focused set, including the
targeted control checks, passed in 51.37 seconds.
Python 3.11 was unavailable for direct testing. No broad regression suite,
large parameter campaign or existing published example regeneration ran.

The comparison separates measured method discrepancies from explicitly
reported finite-basis leakage and controlled basis/slice effects. Potential,
FFT resolution, integration-depth, aperture and remaining beam convergence
are **unverified**. Both methods share the projected z-independent potential,
paraxial approximation, perfect-crystal/nonabsorbing independent-atom model,
axisymmetric effective tensor, assumed beta and eta handedness, site phases
and the entire inelastic contraction. There is no independent magnetic
DFT/MDFF validation, atom-layer-resolved 3D treatment, outgoing channeling,
absolute cross section, calibrated count rate or quantitative experimental
Ni prediction. No full double channeling or transition-potential solver was
added. This patch stops at the incident-propagation milestone.
