# Numerical regression contract corrections

Date: 2026-11-19 (America/Los_Angeles).

This follows the completed
[Phase 2.1 investigation](SCIENTIFIC_NUMERICAL_CONTRACT_REVIEW.md). Its original
failures, raw arrays and scientific interpretation remain historical evidence.
This correction changes only test comparisons and the demonstrated stale
cancellation hook. Application source, equations, kernels, physical settings,
reference source/arrays, serialization and the native Windows EXE are preserved.

Starting commit: `88fd29625797f946ce38df7fd5c61ab5df38574c`.
Working directory and Git worktree root:
`C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute`.
Branch: `refactor/physics-readability`.

## Scope and comparison decisions

The six failures originate at the earlier batching/outgoing-preparation
optimization `ef54a53`, not the readability refactor. The investigation showed
mathematically equivalent expressions with differing binary64 rounding,
including a cancellation-sensitive weak Cr signal. The original archived
sources remain the expected results; no expected value is regenerated or
replaced by the current implementation.

| Test | Correction | Exact/independent checks retained |
| --- | --- | --- |
| `test_bw_unchanged_and_depth_cancel[numerical]` | Compare historical Cartesian response within the fixture's rounding envelope; trigger cancellation in the executed `_numerical_site_responses` path | Exact current no-callback/false-callback equality; analytic historical comparison; required `Cancelled` exception |
| `test_full_spectrum_unchanged[bloch]` | Compare optimized historical Bloch raw, linear and normalized observables using propagated parent scales | Reference identity, energy grid, shapes, dtypes, undefined-value locations and every map field |
| Same function `[both]` | Same correction, confined to its Bloch results | All FFT result comparisons stay exact |
| `test_bcc_cr_independent_events_and_symmetry[unequal-mdff-double-bloch]` | Parent-scale allowance for group/total `M_A`, `M_B`, `D_mag` reduction commutation | Raw independent localized-event checks, nonmagnetic comparisons, input/site/multiplicity/tensor assertions, reversal and parity checks; all other configurations' tolerances |
| `test_original_ni_all_numeric_arrays_exact[double-xmcd]` | Compare only optimized Double/Bloch observables with propagated rounding allowance | Incoming amplitudes, coherence, depth, q grids, all FFT values, original source and settings; count of compared arrays |
| Same function `[double-atomic]` | Same model-independent comparison using the explicit atomic intensity/energy scales | Atomic settings, incoming/FFT exact checks and original archived calculations; no XMCD absolute floor |

The historical pytest node names are retained to correlate these results with
the original six failures. Their docstrings now describe the refined contract.
No serialization or other genuinely lossless comparison is relaxed.

## Numerical allowances and their limits

The test-local `tests/numerical_roundoff.py` supplies the shared comparison
logic. It does not change production numerical evaluation or provide a second
calculation engine. All checks require the same shape and dtype. NaN/Inf values
and their locations remain exact, including the paired angular maps' support.
Unknown observable names raise an error instead of receiving a generic fallback.

Let `u=eps(float64)/2=2^-53`, `gamma(m)=m*u/(1-m*u)`.
For the fixed small-basis historical Bloch fixtures, use the operation budget

```
amplitude = 4*n*n + 8 + 2*(4*n + 8)
m = 2*(2*amplitude + depth_nodes + detector_pixels + 8)
relative_budget = gamma(m)
```

The beam-pair expanded-real contraction has a `4*n*n+8` accumulation budget;
each of the two complex field formations contributes `4*n+8`. The quadratic
response doubles the amplitude contribution. Include depth and detector
reduction counts and final scalar arithmetic, then count both evaluation
routes. The independent Decimal and matrix-exponential checks in Phase 2.1
support this conservative envelope for these finite, well-conditioned,
three-beam fixtures. It is a regression roundoff model, not a universal
eigensolver certificate, discretization bound or experimental uncertainty.

| Comparison | Inputs to operation model | Resulting relative budget |
| --- | --- | ---: |
| a1 numerical response | n=3, 9 depths, no detector reduction; m=370 | approximately 4.11e-14 |
| Historical Bloch spectra/maps | n=3, 9 depths, grid 9²; m=532 | approximately 5.91e-14 |
| Cr linear group reduction | 8 nonzero supported pixels, 2 groups; m=30 | approximately 3.33e-15 of parent intensity |

These counts are chosen from the operations and the investigation's validated
numerical model, not from the observed maximum failing residual. The historical
raw map discrepancies were below 2e-15 relative. The allowance is conservative
for reassociation and propagation, remains on a double-precision rounding
scale, and is narrower than the independent scientific checks' existing
3e-13/3e-12 relative tolerances. Those independent tolerances were not changed.

Raw intensities use their own magnitude as scale. Linear combinations use the
absolute weighted sum of their raw parents: e.g. `M_A` uses
`(|I_A_plus|+|I_A_minus|)/2`, and `D_mag` includes both detectors. Angular
spatial differences include both mirrored parents. The complex response
comparison uses the maximum component magnitude of each reference response
matrix; its nearly zero imaginary components do not set the absolute scale.
No fixed material-dependent absolute floor is introduced.

For percentages, propagate numerator/denominator error separately. With ratio
`r=x/y`, and bounds `E_x`, `E_y`, use

```
100*(E_x + abs(r)*E_y)/(abs(y)-E_y)
```

plus division/percentage rounding, requiring the finite denominator to exceed
its error interval. PRB normalization uses `I_A_plus+I_B_plus`; magnetic and
nonmagnetic diagnostics use `Sigma_ref`. Undefined-value masks stay exact.
This avoids giving a near-zero derived percentage an arbitrary relative floor.

### Cancellation-sensitive Cr signal

The two equivalent routes average/integrate/derive parity in different orders.
At the failing energy, parent `N_A≈0.00659748`, whereas `M_A≈-1.24825e-8`.
The condition factor is approximately 528,539. The observed absolute difference
1.0842e-18 is rounding-scale relative to its parent, despite the 8.69e-11
relative error in `M_A` itself.

Use the investigation's positive-reduction model
`gamma(2*N+2*G+10)*parent_scale`, retaining the existing `rtol=3e-13` and
minimum `atol=1e-18`. Count N=8 nonzero supported pixels rather than all 81
grid entries: adding/multiplying exact zero-weight terms introduces no error.
This tightens the report's full-grid conservative bound by approximately 5.87.
For the first-energy `M_A`, the new parent contribution is about 2.20e-17,
compared with 1.29e-16 for the earlier full-grid model. The criterion is confined
to this unequal-MDFF Double/Bloch group-reduction comparison.

No weak signal is replaced with zero. Its sign and nonzero magnitude remain
scientifically testable. Eight negative/identity tests reject 1% raw/percentage
changes, zeroed or reversed weak magnetic signal, a spurious near-zero even
percentage, erased paired odd maps, changed paired-map validity, dtype or shape.
These are ordinary behavioral tests of the numerical comparisons; they add no
reference snapshot, hash pin or release gate.

## Validation and source identity

Use the established Phase 2 Python environment, NumPy 2.4.6, SciPy 1.17.1,
the recorded OpenBLAS runtimes, one native thread, `PYTHONHASHSEED=0`, and
offscreen Qt. Each operation runs sequentially with its own log, XML where
applicable, source identity, environment, timeout and owned PID. Evidence lives
under `build/numerical-contract-correction/`. Original investigation and
recovery evidence is preserved.

- First focused run: **31 passed, four helper coverage failures, one optional
  historical-project skip**, 96.17 s. Independent event/quadrature/symmetry
  checks and the corrected Cr/cancellation cases passed. The four failures
  identified omitted paired map fields, not numerical tolerance failures.
- After adding those fields: **all six affected cases and eight negative/
  identity checks passed (14 passed)**, 24.91 s. No tolerance was increased to
  correct the helper omission.
- Existing exact 22-case / 2,294-array source equivalence: **passed unchanged**,
  including physical metadata and selected-edge metrics, 44.718 s launcher
  duration. Evidence: `exact-22-case-equivalence.log` and `-run.json`.
- Complete regression ran **once**, at clean test-correction commit
  `7fd38620a7619362a0568d0414d58679d34a875e`: **1,473 passed, 98 failed,
  135 setup errors, 62 skipped**, 1,768 collected, 10,985.88 pytest seconds
  (3h 03m). All six corrected cases and eight comparison negative/identity
  cases passed within this run. Evidence: `complete-regression-7fd3862.log`,
  `.xml`, `-run.json`, and the existing test-lifecycle log.

### Required registration integration and temporary-path correction

The full run exposed two validation-integration issues. They were not additional
numerical tolerance failures in the six corrected cases:

- The existing reviewed-current-source map pins
  `tests/test_double_cancellation.py` and
  `tests/test_single_element_ni_compatibility.py`. Their authorized comparison
  changes require reviewed current identities. Stale registrations caused all
  135 source-scope setup errors and direct guard failures; they must be updated
  explicitly, rather than bypassing the checks.
- I used a longer pytest temporary root inside the worktree than the established
  Phase 2 main-repository build temporary root. All **26 direct file-not-found
  failures have 260-265-character paths**. Transactional save/bundle nesting hit
  the Windows path boundary; GUI source generation also produced subsequent
  missing-source/state failures. The affected recheck uses
  `C:\Users\peng863\EMCD-Sim\build\nc-tmp` and a short unique pytest basename,
  while keeping the same checkout, interpreter, physical inputs and code.

The registration-only correction changes the two existing **current test-file**
digests, registers their new shared `tests/numerical_roundoff.py` dependency,
and updates the existing current-manifest pin and exact path allowlist in
`tests/mdff_usability_source_scope.py`. All other current entries, the
`production_source` identity, historical maps, compressed prior sources,
archives, kernel identities and reference-data pins remain unchanged.

Registering the helper preserves an existing scientific-check boundary: these
two already-pinned tests now delegate comparison decisions to it. Leaving that
dependency unprotected would allow an unreviewed helper edit to loosen the
checks while both callers still matched their pins. Git records the change but
does not replace the existing runtime override/mutation checks. No new guard or
general hash layer is introduced. A direct controlled helper mutation
(`return 1.` instead of the rounding factor) was rejected by the existing
physics/source guard; the unchanged current kernel identities also authenticated.
Evidence: `reviewed-registration-guard.log` and `-run.json`.

The original complete-run failures/errors remain in their logs/XML. Only the
failed/error nodes and affected source-guard/comparison checks are being rerun;
no second complete regression is launched. Final recheck results and GO/NO-GO
will be recorded below.

Application source has not changed, so no Windows EXE rebuild is required or
performed. Final GO/NO-GO and local commit identities will be recorded after
the required checks finish.
