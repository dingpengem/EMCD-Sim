# Post-edge normalization and magnetic EMCD recovery

This workflow tests whether constant post-edge scaling removes detector/
diffraction asymmetry while preserving magnetic contrast. It uses the
existing **XMCD-constrained effective MDFF, entrance-only, relative-intensity**
model. The reversal-odd spectrum is a simulation reference, not validated
experimental Ni truth. No new scattering physics or signal-shape fitting
is introduced.

## Exact decomposition and experimental versus oracle scaling

The unmodified spectra are retained for both effective magnetic responses.
For each physical detector group D:

```text
N_D = (I_D_plus + I_D_minus)/2
M_D = (I_D_plus - I_D_minus)/2
D_raw    = I_A_plus - I_B_plus
D_mag    = M_A - M_B
D_nonmag = N_A - N_B
```

For window W, the experimentally accessible constant scale is
`alpha_obs = integral_W I_A_plus / integral_W I_B_plus`. It uses **only the
plus-state spectra**. Neither the reversal reference nor an edge peak is
used to estimate it. The corrected spectrum is
`D_corrected = I_A_plus - alpha_obs*I_B_plus`.

The oracle scale `alpha_nonmag = integral_W N_A / integral_W N_B` uses only
reversal-even spectra. `D_oracle = I_A_plus-alpha_nonmag*I_B_plus` remains
an idealized simulation comparison, unavailable from one experimental
magnetic state. It is not obtained by fitting to the magnetic reference.

For either scalar alpha, the code checks and saves the exact identity:

```text
D_corrected(alpha) = D_nonmag_residual(alpha) + D_mag_processed(alpha)
D_nonmag_residual(alpha) = N_A - alpha*N_B
D_mag_processed(alpha)  = M_A - alpha*M_B
                       = D_mag - (alpha-1)*M_B
```

Thus suppressing the even difference does not imply an unbiased estimate
of the original magnetic difference. The processed magnetic term must be
compared with **unscaled D_mag**, not relabeled as that reference. Even the
oracle factor only cancels the nonmagnetic **window integral**, not its
value at every energy. Observed normalization cancels the total plus-state
window integral, potentially balancing a magnetic tail with an even residual.

The optional reversal consistency diagnostic is computed automatically:
`alpha_obs_minus = integral_W I_A_minus / integral_W I_B_minus`. It is saved
but is not substituted into the forward physics. If the two fitted factors
differ, independently processing the states mixes their parity. Algebraically,
the odd part of independently corrected states would contain

```text
M_A - [(alpha_plus+alpha_minus)/2]*M_B
    - [(alpha_plus-alpha_minus)/2]*N_B.
```

The final term is an even-spectrum contribution induced by the normalization
procedure itself, not a new physical magnetic effect.

## Window integration and recovery metrics

The default post-edge sensitivity windows are 878-882 eV (primary),
874-878 eV and 877-881 eV. A window must be finite/increasing, lie inside
both source/sampled coverage, and contain at least three original spectral
samples. Exact endpoints are inserted by linear interpolation, without
extrapolation; A and B are integrated with identical trapezoidal nodes.
Both positive post-edge integrals must exceed
`1e-12*max(max(abs(A)),max(abs(B)))*window_width`. Invalid or negligible
integrals are rejected. There is no independent peak normalization.

Metrics are computed for the full sampled range and two explicit,
configurable illustrative edge intervals: **L3=[844,862] eV** and
**L2=[864,874] eV**. These broad analysis intervals are declared choices,
not validated optimal integration limits or automatically identified edges.
The full-range interval is 837-882.521 eV in the executed reference.

The spectral norm is `||s||=sqrt(integral s(E)^2 dE)` on common quadrature
nodes. Reported quantities include:

- Raw and residual even norms and `nonmag_suppression=1-||residual||/||D_nonmag||`.
  This is a norm reduction, not a squared-norm reduction or electron fraction.
- `magnetic_amplitude_ratio=||processed||/||D_mag||`, its fractional change,
  and `magnetic_relative_error=||processed-D_mag||/||D_mag||`.
- `corrected_relative_error=||D_corrected-D_mag||/||D_mag||`, which includes
  both magnetic modification and remaining even contamination.
- Energy-weighted centered Pearson correlations of processed magnetic and
  corrected spectra with D_mag. High correlation tests shape, not amplitude.
- Signed magnetic reference/processed integrals and fractional integral
  changes for each explicit interval. Corrected integral changes relative
  to the same unscaled magnetic integral are also recorded.
- A signed projection gain, without using it to rescale any spectrum.

A norm reference must exceed 1e-10 times the detector-sum norm in that
interval; signed integrals use 1e-10 times the integral of abs(Sigma_ref).
Centered correlations require both centered norms above that norm floor.
A near-zero signal or cancellation makes the relative metric **undefined**,
not zero. NPZ/CSV use NaN; JSON uses null; machine-readable validity masks
and per-row reasons are saved. Absolute norms/integrals remain available.
An already negligible raw even difference has no meaningful suppression
percentage, even if scaling creates a finite new residual.

## Source limits and experimental relevance

The repository source ends at **882.521 eV**. It has no extended post-L2
continuum or complete experimental EELS background. No extrapolation,
artificially zeroed magnetic tail, manufactured continuum, power-law
background subtraction or energy-dependent normalization is performed.

Using native source sampling, the intensity-weighted source
`integral(abs(M))/integral(N)` is:

| Window (eV) | Source tail fraction |
| --- | ---: |
| 878-882 | 0.442732% |
| 874-878 | 0.947174% |
| 877-881 | 0.559657% |

These are source diagnostics before detector diffraction weighting and eta
scaling, not a claim that observed detector tails share those fractions.
The limited nonzero tail can bias alpha_obs even when the source contribution
looks small. These windows are sensitivity choices, not experimentally
validated optimal Ni normalization intervals.

Relevant primary processing literature motivates this caution:

- [Thersleff et al. (2019), Scientific Reports 9, 18170](https://doi.org/10.1038/s41598-019-53373-1)
  describes an Fe experiment where a constant integral scale was sensitive
  to window placement. The authors used a linear ratio correction fitted
  over 730-760 eV to address instrumental trends. This patch deliberately
  tests only a constant factor and does not implement that extra correction.
- [Ali et al. (2023), Ultramicroscopy 251, 113760](https://doi.org/10.1016/j.ultramic.2023.113760)
  applies post-edge scaling over 750-800 eV in Fe. Differing spectral slopes
  complicate single-difference alignment, while a four-aperture double
  difference improves it. The much longer Fe interval and experimental
  background treatment are not available in the present Ni source model.

These studies support evaluating normalization bias and window dependence;
they do not validate the present effective Ni tensor or transfer Fe settings
to this Ni calculation.

## Reproduce on Windows CMD, macOS and Linux

From the repository root in the existing environment (or after
`python -m pip install -e ".[dev]"`):

```text
python -m emcd_sim.xmcd_postedge_normalization --xmcd-file data/wien2k_ni/Ni_fm.xmcd --condition near-2bc --postedge-start 878 --postedge-end 882 --thickness-nm 30 --cutoff 1.4 --grid 65 --steps 64 --integration-mode fractional --output outputs/ni_postedge_normalization
```

The actual primary comparison used `--condition all`, which calculates
**near-2BC and nominal symmetric-3BC only**, at otherwise identical defaults.
`--condition zone-axis` is optional. Every case uses a common 2D ZOLZ selection
(cutoff 1.4 cycles/angstrom, 21 beams here), its existing physical tilt and
apertures, 200 kV, eta=beta=1, 30 nm and fractional integration with 64 boundary
subpixels per axis. Symmetric-3BC preserves A=RU+LD and B=RD+LU. No two-beam
truncation is presented as another geometry. The nominal 3BC geometry remains
an illustrative alignment, not an independently established experimental one.

`--energy-points` defaults to 185 over `--energy-start 837` through the actual
source maximum; `--energy-end` can restrict that interval. All windows must
remain covered and sufficiently sampled. Full spectra are generated once
per condition through the existing `run_xmcd_reversal`; window comparisons
reuse those arrays. Elastic propagation is not rerun per energy or window.
The existing solver calculates transient maps per energy as part of its
contraction and retains selected edge maps; this wrapper does not export a
full reciprocal-map cube. No physics kernel or existing API default changed.

`--l3-start`, `--l3-end`, `--l2-start`, `--l2-end` explicitly override the
edge integration intervals. `--comparison-window START END` can be repeated
to replace the default extra sensitivity windows; the primary start/end
window is always included first and duplicates are removed. The CLI also
exposes `--eta`, `--beta`, `--acceleration-kv`, `--offzone-tilt-mrad`,
`--max-beams`, `--aperture-subpixels`, and `--integration-mode binary`.
Only this new workflow defaults to fractional; historical defaults are unchanged.

The signal-processing API is independent of propagation:

```python
from emcd_sim.xmcd_postedge_normalization import (
    normalize_postedge, analyze_postedge_spectra, recovery_diagnostics,
    PostedgeConfig, run_postedge_simulation, save_postedge_result, plot_postedge_result,
)
# normalize_postedge(energy, A_plus, B_plus, window) uses this pair only.
result = run_postedge_simulation("data/wien2k_ni/Ni_fm.xmcd", PostedgeConfig())
save_postedge_result(result, "outputs/ni_postedge_normalization/near-2bc")
plot_postedge_result(result, "outputs/ni_postedge_normalization/near-2bc")
```

## Executed results

For the primary 878-882 eV window, full-spectrum diagnostics were:

| Geometry / normalization | alpha | Even norm suppression | Processed magnetic norm change | Corrected/reference norm error |
| --- | ---: | ---: | ---: | ---: |
| Near-2BC / observed | 0.758520168 | 98.6253% | -16.2671% | 18.1862% |
| Near-2BC / oracle | 0.755778410 | 99.7416% | -16.4518% | 16.7594% |
| Nominal symmetric-3BC / observed | 1.000694362 | Undefined | +0.0347181% | 2.87019% |
| Nominal symmetric-3BC / oracle | 1 | Undefined | 0% | 8.11e-15 (fractional) |

Near-2BC raw even norm was 0.0297125 in relative-intensity*sqrt(eV) units;
observed residual norm was 0.000408472 and oracle residual norm 0.0000767770.
The observed/oracle scale difference was 0.00274176, or **0.362773%** of the
oracle scale. Processed-magnetic correlation was nearly one, but that did
not prevent a 16.27% magnetic norm loss. The corrected/reference correlation
was 0.999769, illustrating why correlation alone is insufficient.

In nominal symmetric-3BC the original even norm was only 6.75e-17; observed
scaling creates an even residual norm of 0.000209904. Its suppression fraction
is therefore undefined. Oracle scaling preserves D_mag to roundoff.
The already symmetric signal does not benefit from blindly forcing a
magnetic post-edge tail to cancel.

Window sensitivity for observed normalization, evaluated on the full range:

| Window (eV) | Near-2BC alpha_obs | Near-2BC even suppression | Near-2BC magnetic norm change | Near-2BC corrected error | 3BC corrected error |
| --- | ---: | ---: | ---: | ---: | ---: |
| 878-882 | 0.758520 | 98.6253% | -16.2671% | 18.1862% | 2.87019% |
| 874-878 | 0.761583 | 97.3746% | -16.0608% | 19.9794% | 6.14680% |
| 877-881 | 0.759227 | 98.3366% | -16.2195% | 18.5834% | 3.62909% |

The primary observed processed-magnetic integral changes were **-16.2675%**
(L3) and **-16.2740%** (L2) for near-2BC. The corresponding corrected-spectrum
integral changes were **-20.3955%** and **-32.6922%**, since the latter also
include the even residual. For nominal symmetric-3BC, processed magnetic
integrals changed +0.0347181% on both edges, but corrected integrals changed
-4.07676% (L3) and -17.8556% (L2). The small signed L2 reference makes its
relative bias larger; all signed reference integrals and absolute residuals
are saved, rather than inferring moments from these percentages.

The plus/minus fitted primary scales differ: near-2BC 0.758520 versus
0.753049, and nominal 3BC 1.000694 versus 0.999306. Thus independently
normalizing magnetic states would mix parity. The exact residual identity
was satisfied at approximately 1e-17 absolute intensity in the primary runs.

These results answer the question conditionally: constant post-edge scaling
strongly cleans the near-2BC nonmagnetic difference, **while changing its
magnetic amplitude substantially**. In the nominal symmetric case, tail bias
can introduce contamination where little existed. Neither the largest
suppression nor the highest correlation alone identifies an unbiased or
optimal experimental recovery. No magnetic amplitude correction is fitted
or applied to the reported spectra.

## Outputs, verification and limits

Each selected condition writes its own directory under
`outputs/ni_postedge_normalization/` containing:

- `postedge_spectra.npz`: original A/B spectra for both states, N_D/M_D,
  raw magnetic/even references, all scale factors, corrected and oracle
  spectra, their exact residual/processed terms, scaled B spectra, window
  masks and validity arrays. All arrays load with `allow_pickle=False`.
- `postedge_window_comparison.csv`: rows by window, observed/oracle method,
  and full/L3/L2 analysis scope, with interval bounds and undefined reasons.
- `postedge_metrics.json`: the same rows, with undefined numerical values
  encoded as null. NPZ `metric_names/values/valid`, `metric_window_index`,
  `metric_normalization` and `metric_scope` map validity to these rows.
- `metadata.json`: configuration, physical tilts, hkl basis, actual aperture
  areas/weights, source coverage/hash, native tail diagnostics, tensor
  sources, quadrature policies, software commit/dirty status, Python version
  and approximation flags.
- Three requested figures: `postedge_normalization_comparison.png`,
  `magnetic_recovery_comparison.png`, `normalization_window_sensitivity.png`.
  Legends distinguish observed corrections from oracle/reference terms;
  undefined suppression panels are explicitly labeled.

The exact Windows CRLF source SHA256 remains
`bb9bdd478d54cc8de60403409f4d90e63deb11a64891bbac6754f867be14deda`.
Existing scientific examples, fractional integration, Bloch/FFT propagation,
MDFF and independent multislice validation were not modified.

```text
python -m pytest -q tests/test_xmcd_postedge_normalization.py
```

**11 focused tests passed**. They cover exact multiplicative imbalance removal, eta=0,
observed/oracle input independence, residual algebra and magnetic scaling,
post-edge tail bias, exact endpoints, bad/undersampled windows, negligible
integrals, cancellation/undefined metrics, and one small real-source 3BC
CLI smoke test with fractional integration and pickle-free outputs.
The primary study used both requested geometries and three postprocessing
windows without a convergence campaign. Python runtime was **3.10.9**;
Python 3.11 was unavailable for direct testing.

Finite beam, depth, spectral and spatial sampling remain unverified. The
model omits outgoing channeling, full complex DFT-MDFF, instrumental effects,
experimental background fitting and an extended continuum. No orbital/spin
moment ratios, count calibration, optimal experimental window or quantitative
Ni magnetization are claimed. This patch stops at the constant-factor
signal-processing milestone; no energy-dependent correction is implemented.
