# Scientific numerical contract review — Phase 2.1

Review date: **2026-11-19, America/Los_Angeles**. Evidence timestamps also include
UTC; records after 00:00 UTC on November 20 belong to this local review date.

## A. Executive summary

**Investigation GO; scientific regression acceptance remains NO-GO.** All six
original failures were reproduced individually in fresh processes, then
reproduced again with bitwise-identical observed results. All six original
assertions are unchanged. No production code, physical model, scientific
reference, numerical tolerance, project data or native application was changed.

The evidence classifies the six first-failing numerical comparisons as
**B: valid historical behavior with non-bitwise floating-point differences**.
The first divergence is the pre-refactor optimization
`ef54a53be4bb509feeae984de23de28c5166ecdc`, which batches independent-site
contractions and reuses outgoing Bloch preparation. The five Ni discrepancies
are absent in the preceding tested kernels. The Cr assertion passes at the
optimization's direct parent and fails at the optimization itself. Thus none
of these six discrepancies originated in the readability refactor or Phase 2.

This conclusion uses more than current-versus-pre-refactor agreement: actual
archived source, operand-level replay, independent 80-digit arithmetic,
conditioning analysis, existing independent localized-event assertions,
symmetry checks and a separate matrix-exponential evaluation were examined.
The two evaluation orders are not uniformly ranked by accuracy. The evidence
does not establish one historical bit pattern as the uniquely authoritative
scientific answer.

No new scientific implementation defect was demonstrated in these cases.
A **separate, concrete test-maintenance defect** was found: the numerical
cancellation test's later spy watches `depth_response`, which its batched
numerical path no longer calls. Current immediate and in-work cancellation
checks succeed. Fixing only that test's first exact comparison would expose
this stale hook; it must be addressed explicitly in a reviewed follow-up.

The proposed resolutions in section F are recommendations, **not implemented
acceptance changes**. In particular, classification B does not waive a required
assertion. The original scientific suite still has the six known failures in
the recorded baseline environment. Complete scientific acceptance requires
reviewing the proposed contracts and verifying the resulting changes.

| Identity | Verified value |
| --- | --- |
| Absolute working directory / Git worktree root | `C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute` |
| Branch | `refactor/physics-readability` |
| Starting / investigated HEAD | `cb180cd877dfc2b92b4fa9fc7945525a89862b56` |
| Actual pre-refactor source | `cdb8836388c5ccc5ae7a614b47894c0ab158a824` |
| Phase 1 final source | `6817d644d3e9dcc3f06d02d1ad733e36b331d0f2` |
| Phase 2 complete-regression source | `91aff158d7c6ec17a45196200830d3e1f7c178a3` |
| Phase 2 final application/build source | `6d98694b2367fdb9586f33287f9a09c159c7ef27` |
| Historical cancellation reference | `7bebdce4303bc7d517e826c9e0c91e8418f3f55b` |
| Historical Ni reference | `2f9c130099dce5df4e4609b521c42f53c5385518` |
| First divergent optimization | `ef54a53be4bb509feeae984de23de28c5166ecdc` |
| Optimization's direct parent | `35a8e811a98515337ee96c14868ed3bd1bb65e2b` |

Identities were resolved from Git, not inferred from report titles. Existing
context remains in [the recovery report](REGRESSION_RECOVERY_REPORT.md),
[physics map](PHYSICS_CODE_MAP.md), [name map](REFACTOR_NAME_MAP.md) and
[structural audit](REFACTOR_COMPLEXITY_AUDIT.md). This review does not revise
their recorded measurements.

The Phase 2 complete run remains **1,692 passed, six failed, zero errors,
62 skipped / 1,760 collected**, on **91aff15**, taking 4,311.19 pytest seconds.
The earlier 22-case / 2,294-array exact comparison against cdb8836 remains
unchanged evidence. Neither is represented as a new full run of 6d98694 or
cb180cd. No complete suite, GUI campaign, build or native acceptance campaign
was restarted for this review.

## B. Numerical failure matrix

Case IDs below are evidence labels only. All paths are under `tests/`.
The reported errors are for the **first original failing assertion**, not the
largest error among all returned arrays. Section D also reports other arrays.
For complex values ULPs are measured separately for real and imaginary binary64
components. Numerical equality and byte equality are recorded separately.

| ID / original test | Historical comparison | Current source | Max absolute error | Max relative error | ULP characteristics | Root cause | Class |
| --- | --- | --- | ---: | ---: | --- | --- | --- |
| a1: `test_double_cancellation.py::test_bw_unchanged_and_depth_cancel[numerical]` | 7bebdce kernel | cb180cd | 1.387808077191692e-17 | 1.848251729101348e-16 | Ordinary real differences: 1 ULP; tiny imaginary components: up to 5,895,890,062,035,818 ULP | Reassociated complex contraction, followed by the same outer product and trapezoid rule | B |
| a2: `test_double_cancellation.py::test_full_spectrum_unchanged[bloch]` | 7bebdce kernels through current orchestration | cb180cd | 6.938893903907228e-18 | 8.522751319434426e-16 | 1–6 ULP in first intensity array | Batched contraction and algebraically equivalent outgoing preparation | B |
| a3: `test_double_cancellation.py::test_full_spectrum_unchanged[both]` | Same archived kernels, both solvers | cb180cd | 6.938893903907228e-18 | 8.522751319434426e-16 | Same first Bloch array as a2 | Same Bloch path; the unchanged FFT branch is not a second cause | B |
| b1: `test_multisite_scientific_validation.py::test_bcc_cr_independent_events_and_symmetry[unequal-mdff-double-bloch]` | Weighted independent-group result within the same run; also actual pre-refactor source | cb180cd | 1.084202172485504e-18 | 8.685788417812607e-11 | 655,360 ULP in weak `M_A`; raw detector differences at most 2 ULP | Linear operations commute in exact arithmetic, but averaging/integration/subtraction order rounds differently; cancellation amplifies relative error | B |
| c1: `test_single_element_ni_compatibility.py::test_original_ni_all_numeric_arrays_exact[double-xmcd]` | 2f9c130 channeling + BW/MS kernels through current orchestration | cb180cd | 1.301042606982605e-18 | 5.051999600395727e-16 | 3 ULP | Same batched Bloch optimization, historical XMCD inputs preserved | B |
| c2: same function `[double-atomic]` | Same 2f9c130 source, atomic inputs | cb180cd | 2.646977960169689e-23 | 1.163688863869625e-16 | 1 ULP | Same shared Bloch kernel, different explicit MDFF model/energies | B |

| ID | First compared array / dtype / shape | Differing elements | Original failing elements | Maximum assertion residual |
| --- | --- | ---: | ---: | ---: |
| a1 | Cartesian response, complex128, `(2,3,3)` | 12/18 (66.67%) | 12 | +1.387808077191692e-17 |
| a2 | `I_A_plus`, float64, `(11,)` | 8/11 (72.73%) | 8 | +6.938893903907228e-18 |
| a3 | `I_A_plus`, float64, `(11,)` | 8/11 (72.73%) | 8 | +6.938893903907228e-18 |
| b1 | `M_A`, float64, `(2,)` | 2/2 (100%) | 1 | +8.045742720620870e-20 |
| c1 | `I_A_plus`, float64, `(2,)` | 1/2 (50%) | 1 | +1.301042606982605e-18 |
| c2 | `I_A_plus`, float64, `(2,)` | 1/2 (50%) | 1 | +2.646977960169689e-23 |

For a1/a2/a3/c1/c2, the original condition is `assert_array_equal`:
the diagnostic allowance is zero. For b1 the original allowance is
`1e-18 + 3e-13*abs(expected)`. Every element's actual allowance and residual
`abs(actual-expected) - allowance` is saved in `assertion_elements.csv`.
None of these first assertion arrays contains a nonfinite value or a differing
value whose whole real/complex reference is exactly zero. Near-zero individual
components and derived quantities still require separate interpretation.

## C. Historical source comparison

### Inputs and actual reference contracts

All runs use the installed Phase 2 dependency environment and the tests'
original explicit configurations. Forward-setting dataclasses, source paths,
site assignments and geometry are in the applicable `capture.json`; a1 records
the derived elastic input from its fixed original fixture. The adjacent NPZ holds
the compared arrays. The compact descriptions here do not replace those
complete input records.

| Cases | Physical/numerical inputs that matter |
| --- | --- |
| a1 | FCC Ni, zone `(0,1,7)`, 300 kV, 2 nm, beam/potential cutoffs 0.9/1.8 Å⁻¹; queries `(0.15,±0.2)` Å⁻¹; loss 831.4778 eV; 9 depth nodes; numerical Bloch Double Channeling |
| a2/a3 | Same structure/settings, historical Ni XMCD source, explicit declared axis, Double Channeling; Bloch or Both; 9 requested energy samples plus selected edges = 11 energies; grid 9, depth 9, FFT grid 24, detector subpixels 16, maps enabled, correction disabled |
| c1/c2 | FCC Ni, same orientation/voltage/cutoffs, 0.3 nm; Both solvers, Double Channeling, edge energies only; grid/depth 9, FFT grid 16, slice step 0.01 nm, detector subpixels 8, halfwidth 0.7 Å⁻¹, centers `(0.2,±0.2)`, radius 0.12 Å⁻¹, correction disabled, one explicit worker. XMCD edges 831.271/848.698 eV or atomic edges 852.7/870 eV |
| b1 | Synthetic BCC Cr, a=2.88 Å, two independent sites `(0,0,0)` and `(½,½,½)`; zone `(0,0,1)`, target `(1,1,0)`, tilt `(-5,7)`, 200 kV, 0.5 nm, cutoffs 0.55/0.8 Å⁻¹; grid 9, depth 17, subpixels 8, same small detectors as c1; loss labels 710/723 eV, one worker, no maps, no post-edge correction; separate declared MDFFs, antiparallel directions, second odd MDFF amplitude 0.6 |

The Cr energies are **illustrative synthetic labels, not measured Cr edges**.
The fixture is an ordered two-sublattice example, not a model of bulk Cr's
spin-density wave. Its elastic potential is the complete chemical crystal;
the magnetic site groups supply independent inelastic events. Default Ni
fields inherited by a settings container are not used as Cr spectroscopy:
the explicit group providers and explicit energy array own those inputs.

a1 is a pure archived-kernel comparison using the same current elastic input.
a2/a3 run archived BW/MS kernels through current forward orchestration. Their
adapter removes unsupported software parameters and certifies that the
explicit `HistoricalNiSites` positions equal the archived implicit FCC sites.
It does not substitute another element, magnetic frame or detector geometry.
The prepared-incoming software type is bound explicitly as in the original
test; the archive prepares its own outgoing basis.

c1/c2 execute the actual 2f9c130 channeling and BW/MS kernels via the original
`old_contract` fixture. The current forward pipeline surrounds that reference.
Its import/name relocation is in `tests/reference_imports.py` and the fixture;
the scientific numerical statements remain archived source. These are
**historical-kernel/channeling contracts under common current inputs**, not
independent reconstructions of every old package, default or installation.
They do not validate an entire original released program bit for bit.

The effective elastic provider in these current settings is
`adaptive-dirac-pade-2026`, in both sides of the comparisons. The comparisons
do not silently substitute the old Ni Lobato provider. Required saved-project
provider restoration and existing source/data identity pins remain unchanged.

### First divergence

`history-v2/kernel_history.json` records execution of actual Git kernels at
7bebdce, f030556, 5347f44, 2f9c130, 76deb65, a87f5df, ef54a53, e5b6e4a,
cdb8836, 91aff15 and 6d98694. The same five Ni configurations are used at
each revision, with the adapters above.

| Kernel revision / change | a1 differing elements | a2 differing array paths | a3 differing array paths | c1 differing array paths | c2 differing array paths |
| --- | ---: | ---: | ---: | ---: | ---: |
| 7bebdce through a87f5df, including cancellation and explicit-site additions | 0 | 0 | 0 | 0 | 0 |
| ef54a53: reuse outgoing preparation and batch site contractions | 12 | 68 | 68 | 66 | 56 |
| e5b6e4a, cdb8836, 91aff15, 6d98694 | 12 | 68 | 68 | 66 | 56 |

Array paths include some top-level/method aliases of the same data; these
counts are not counts of independent scientific observables. The kernel
history excludes top-level FFT diagnostic/cohort trees from its comparison.

Cr's original scientific-validation test was introduced at
`db9c2cdfd3596ea7482467e4fb63f92282e12f2f`. Earlier actual orchestration,
channeling and multisite BW sources were executed in private namespaces at
that commit, ef54a53's direct parent, and ef54a53 itself:

| Actual earlier source | `M_A` max absolute discrepancy | `M_A` residual | Original RAW/PARITY group assertions |
| --- | ---: | ---: | --- |
| db9c2cdfd3596ea7482467e4fb63f92282e12f2f | 4.336808689942018e-19 | -5.700638762848989e-19 | All 12 array comparisons pass |
| 35a8e811a98515337ee96c14868ed3bd1bb65e2b | 4.336808689942018e-19 | -5.700638762848989e-19 | All 12 array comparisons pass |
| ef54a53be4bb509feeae984de23de28c5166ecdc | 1.084202172485504e-18 | +8.045742720620870e-20 | Only first-energy `M_A` fails |

These older-source executions retain modern shared geometry/provider/resource
dependencies. Their software schema adapter supplies `memory_mode` and
`resource_allocation`; at db9c2cd it also carries `energy_sampling` and
`angular_evaluation`. The original energies are explicit and angular maps
are disabled. The adapter preserves all physical input values and survives
the archived pipeline's `dataclasses.replace`. The removed
`gui.generalized_forward.source_for` import is relocated to its current owner,
`gui.material_inputs.source_for`. No numerical statement is edited.
This isolates the source change without claiming a historical wheel environment.

Successful evidence: `resolution-v5/checks.json`, `observed_arrays.npz` and
`linear_assertions.json`. Attempts v1–v4 expose schema/import incompatibilities
and are retained as adapter-development evidence, not scientific outcomes.

### Pre-refactor and Phase 2 orchestration

Actual archived `channeling` and forward orchestration sources at cdb8836,
91aff15 and 6d98694 were also executed, with import/name relocation and common
explicit inputs. Their a2/a3/c1/c2 arrays are bitwise equal to the current
outputs on the compared paths: 90 paths for a2 and 135 for each Both case.
Their Cr `M_A` residual is the same positive 8.045742720620870e-20. The
independent kernel history separately establishes the same a1 response at
these revisions. Details are in `history-v2/frozen_sources.json`.

This is stronger than simply inspecting current code, but it is still a
controlled Git-source comparison with shared dependencies. It does not prove
all historical defaults, all materials or all numerical environments equivalent.

### What changed mathematically and computationally

For one site/component, both versions evaluate
`v[z,c] = Σ(g,h) a[z,g] b[z,h] K[g,h,c] phase[g,h]`, then form the Gram
response and apply the same uniform-depth trapezoid rule. Earlier code uses
`einsum('zg,zh,gha->za', ..., optimize=True)`. ef54a53 explicitly forms the
incoming/outgoing products and uses a batched matrix multiplication. The
independent events are still squared separately, then averaged by multiplicity.
There is no coherent sum across independent ionization events.

The cached outgoing Hamiltonian is the algebraic identity
`H_out(q) = H_out(0) - 20π λ_out diag(g·q)` for this finite, elastic,
absorption-free model. Its off-diagonal potential is reused by the ratio
`(γ_out λ_out)/(γ_in λ_in)`. Direct recomputation and factor/reuse have
different rounding paths. No outgoing loss, longitudinal transfer, potential
cutoff or declared reciprocal basis is removed.

The archived phase convention changed at 5347f44 for general sites. In these
FCC Ni cases the selected site phases are exactly one after periodic reduction;
the BCC fixture has even `h+k+l`, also giving equal site phases. Executing
5347f44 leaves the Ni results exact. It is not the cause of these six failures.
This does **not** establish that the pre-5347f44 convention is a valid generic
reference for arbitrary sites or geometries.

## D. Floating-point diagnostics

### Environment, repetition and error distribution

Recorded environment: Windows AMD64, Python 3.11.17, NumPy 2.4.6, SciPy 1.17.1,
float64/complex128. NumPy loads OpenBLAS **0.3.31.188.0**, while SciPy loads a
separate OpenBLAS **0.3.30**. The default observed core is Haswell.
`OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `PYTHONHASHSEED=0`, and offscreen
Qt were set before launch. The Python executable is the Phase 2 Windows venv
interpreter; the package paths actually resolve to the existing `emcd-python`
installation, as captured in backend metadata. CPU counts and each loaded
runtime's observed thread count/configuration are recorded.

Some original Ni full-spectrum configurations use the application's automatic
detector-worker policy, even with one native BLAS thread. Their original input
was preserved. The observer profiles both the main thread and worker threads.
Repeated results are deterministic under that policy; this is not a separate
claim of arbitrary serial-versus-parallel equivalence.

Each case has two completed fresh-process baseline observations. All saved
current, reference and first-assertion arrays are **byte-identical between
repetitions**, including dtype/shape. Determinism within this environment does
not imply historical bitwise equivalence or invariance across BLAS cores.

| Case | Compared numeric array paths | Paths with value differences | Repeated baseline byte equality |
| --- | ---: | ---: | --- |
| a1 | 1 | 1 | Yes |
| a2 | 90 | 68 | Yes |
| a3 | 141 | 68 | Yes |
| b1 | 12 | 11 | Yes |
| c1 | 141 | 66 | Yes |
| c2 | 141 | 56 | Yes |

These observation counts include top-level/method aliases and more diagnostic
paths than the filtered history comparison. They do not count independent
experiments. Differences extend beyond the first failing assertion:

- a2/a3: a nonmagnetic imbalance percentage differs by up to
  **2.014358288320208e-14 percentage points**, with relative error up to 3
  in that near-zero diagnostic. A large relative error there is not a 300%
  change in a large detector intensity.
- c1: the largest absolute returned-array difference is
  **8.548717289613705e-15 percentage points** in `magnetic_only_percent`;
  that array's maximum relative error is 1.512838248590230e-14 (77 ULP).
- c2: the largest absolute returned-array difference is
  **5.828670879282072e-15 percentage points** in
  `prb_relative_dichroism_percent`; maximum relative error in that array is
  3.780708922425767e-14 (210 ULP).

The complete per-array distributions and ULP histograms are in
`analysis/error_distributions.json` and `analysis/array_errors.csv`. They
preserve these less favorable derived-signal metrics instead of reporting
only the first raw intensity failure.

Representative first-assertion elements, with `actual - expected` sign:

| Case / index | Actual | Expected | Signed error |
| --- | --- | --- | --- |
| a1 `(0,2,2)` | `0.07508761146223673 - 1.468311893747363e-19j` | `0.07508761146223672 - 5.665650819108149e-20j` | `+1.387778780781446e-17 - 9.017468118365479e-20j` |
| a2/a3 `(1,)` | `0.009025792438312419` | `0.009025792438312412` | `+6.938893903907228e-18` |
| b1 `(0,)` | `-1.2482484263234839e-8` | `-1.2482484264319041e-8` | `+1.0842021724855044e-18` |
| c1 `(1,)` | `0.0025753022761139826` | `0.002575302276113984` | `-1.3010426069826053e-18` |
| c2 `(0,)` | `2.2746440585223682e-7` | `2.2746440585223684e-7` | `-2.6469779601696886e-23` |

Every first-assertion element, including matching entries, has decimal errors
and hexadecimal component values in the capture's CSV. Huge ULP distances in
tiny imaginary Gram-diagonal components or across the sign of a near-zero
derived value are not comparable to a few ULP in a normal positive intensity.
ULPs describe representation distance; they are not by themselves a physical
error criterion.

### Independent arithmetic and the first differing operations

The observer saved the actual complex operands, return values and array
strides. Replaying the old `einsum` and new batched expressions with restored
layouts reproduces **both captured response matrices bit for bit**. This
isolates evaluation order rather than introducing another expected-result
fixture.

For selected a1/a2/c1 queries, incoming fields and Coulomb kernels are exactly
equal across old/new paths. Outgoing fields are identical for the selected a1
query; their maximum differences are 2.267533093483919e-16 for a2 and
3.711951304433880e-33 for c1. Replaying with the same outgoing fields isolates
the contraction change. Replacing only the outgoing fields separately isolates
the cache/recomputation path. Both effects can occur; it would be inaccurate to
attribute every last bit solely to summation of detector pixels.

Windows `longdouble` here has only **53 significant binary bits**. The independent
arithmetic therefore uses `decimal.Decimal` with 80 decimal digits, explicitly
expanding complex products, sums, outer products and trapezoid integration from
the observed binary64 inputs. It is independent arithmetic on those operands,
not a higher-fidelity elastic or MDFF model.

Let `u=2^-53` and `γ_m=m*u/(1-m*u)`. For an amplitude component, let
`S=Σ(g,h) (|Re a|+|Im a|)(|Re b|+|Im b|)(|Re K|+|Im K|)`.
An expanded-real-operation bound uses `m=4*N_in*N_out+8`; each real/imaginary
component is bounded by `γ_m*S`, with complex modulus bounded by
`sqrt(2)*γ_m*S`. The count allows the expanded products and reassociated
reductions. Both old and batched amplitude errors satisfy this conservative
bound. Reported amplitude distances, like the response distances below, use
binary64 rounding of the independent Decimal output. The standard `γ_m` model
is a rounding-error bound, not an experimental
uncertainty model; see [Higham's primary analysis of floating-point
summation](https://nhigham.com/wp-content/uploads/2023/10/high93s.pdf).

| Selected case | Old max amplitude error | Batched max amplitude error, fixed old operands | Max per-component `γ_m*S` | Both within bound |
| --- | ---: | ---: | ---: | --- |
| a1 | 5.594315114139762e-17 | 1.112389315513593e-16 | 2.385318484105456e-15 | Yes |
| a2 | 1.112389315513593e-16 | 1.110223024625157e-16 | 1.848008655161747e-15 | Yes |
| c1 | 4.163336342344337e-17 | 2.775557561562891e-17 | 5.827007333562781e-16 | Yes |

Distances of the final response to the **rounded Decimal(80) result** are:

| Selected case | Old response | Batched response using the same old operands |
| --- | ---: | ---: |
| a1 | 5.551126123970261e-17 | 5.551125106525682e-17 |
| a2 | 5.551115123665375e-17 | 5.551116654484554e-17 |
| c1 | 4.336872162880708e-19 | 4.336814615762959e-19 |

Neither evaluation order is uniformly more accurate. The Decimal response
components are retained as 80-digit strings in
`analysis/contraction_precision.json`. The amplitude bound is not silently
promoted to an end-to-end tolerance for normalized spectra. Propagation,
quadratic contraction, detector integration and division require their own
error propagation, described in section F.

### Cr cancellation, normalization and the actual assertion excess

For detector A, `M_A=(I_A_plus-I_A_minus)/2`. At 710 eV,
`N_A=(I_A_plus+I_A_minus)/2 ≈ 6.597484951519288e-3`, while
`M_A ≈ -1.2482484264e-8`. The cancellation condition estimate
`κ=(|I_A_plus|+|I_A_minus|)/(2*|M_A|)` is about **528,539**; at 723 eV
it is **493,291**. Thus `κ*u` is already of order 5e-11. A raw-intensity
rounding difference on the scale of `u` can produce the reported 8.69e-11
relative difference in `M_A`.

This is a weak but nonzero signal. Unequal MDFFs intentionally leave a signal
of approximately 0.2 times the up-group `M_A`; the expected value must not be
replaced with zero because the directions sum to zero.

| 710 eV observable | Current value | Current vs weighted-group absolute difference | Parent intensity scale | Cancellation condition |
| --- | ---: | ---: | ---: | ---: |
| `N_A` | 6.597484951519289e-3 | 8.673617379884035e-19 | 6.597484951519288e-3 | 1 |
| `M_A` | -1.248248426323484e-8 | 1.084202172485504e-18 | 6.597484951519288e-3 | 528,539.4 |
| `M_B` | -2.205610783186963e-6 | 2.168404344971009e-19 | 7.771645097141408e-3 | 3,523.6 |
| `D_mag=M_A-M_B` | 2.193128298923729e-6 | 8.673617379884035e-19 | 1.436913004866070e-2 | 6,551.9 |
| `Sigma_ref=N_A+N_B` | 1.436913004866070e-2 | 1.734723475976807e-18 | 1.436913004866070e-2 | 1 |

The worst raw detector relative discrepancy is 2.629375846763534e-16,
at most 2 ULP. Well-conditioned nonmagnetic sums likewise differ at rounding
scale. The `M_A` discrepancy is only 1.6433568e-16 of its parent `N_A` scale.
At the failing element the actual allowance is **1.003744745279296e-18**;
the absolute discrepancy exceeds it by **8.045742720620870e-20**.
The second `M_A` element differs by 2.168404344971009e-19 and **passes**
the original allowance 1.002233465165222e-18.

There are two linear paths: average positive group pixel intensities and then
integrate/derive parity, or integrate/derive each group and then average.
Their exact arithmetic result is identical. Their binary64 reductions need
not be identical. The independent Decimal calculation multiplies the saved
per-group pixel intensities by the actual fractional detector weights and
pixel area, then performs the linear forms at 80 digits. It does not call the
production detector integration or parity helper for its reference value.

At the first energy, current `M_A` minus that independent pixel-reduction value
is **+4.996207579322052e-19**; the weighted-group path minus it is
**-5.845814145532992e-19**. Both bracket the more accurate arithmetic result.
For `M_B`, the weighted-group path happens to be closer. There is no consistent
winner. The diagnostic separates raw reduction error from parity postprocessing
in `analysis/cr_conditioning.json`.

The same file evaluates normalization against a **common independent
`Sigma_ref`**. At 710 eV, `M_A/Sigma_ref≈-8.687014607678558e-7`, whose
current-versus-independent numerator error becomes 3.477042494850086e-17
after normalization. `D_mag/Sigma_ref≈1.526277715837184e-4`, with error
2.070494975826540e-17. These isolate numerator rounding; they do not claim
that the independently rounded production denominator has zero error.
Ratios of group signals are nonlinear and must **not** be averaged as if they
were the raw intensities or linear parity forms.

For this specific commutation assertion, a conservative positive-reduction
bound is `B_key=γ_(2*N+2*G+10)*S_key`, with N=81 full-grid positions, G=2
groups, and `S_key` the sum of absolute parent detector terms with the same
linear-form coefficients. Eight grid positions have nonzero support. Captured
group pixel intensities are positive (minimum >0.02858), fractional weights
are nonnegative, and the group weights are positive.

The count covers the product and N-term integration on **both** routes,
group averaging, pixel-area multiplication and the final linear forms.
Each route is bounded by a `γ` factor times its absolute positive parent sum;
adding the two route bounds is conservatively covered by the combined count.
For `M_A`, `S_key=(|I_A_plus|+|I_A_minus|)/2`; for `D_mag` it includes both
detectors. This derives the scale from the operations, not from the observed
maximum residual. It assumes finite normal-range binary64 arithmetic and
does not cover discretization or upstream wavefield error.

The resulting bounds at 710 eV are **1.289143626811892e-16** for `M_A`,
**1.518573641386872e-16** for `M_B`, and **2.807717268198764e-16** for
`D_mag`. All 24 energy/key comparisons satisfy their bound. This conservative
model is a proposed comparison diagnostic, **not an adopted test tolerance**.
It would still reject setting this `M_A` to zero by roughly 97 million bound
units, reversing its sign by roughly 194 million units, or a 1% error by
roughly 968,000 units. These arithmetic ratios describe sensitivity; they
are not a substitute for independent physical checks.

### Environment sensitivity and FMA limits

Three representative original tests were rerun in fresh processes under each
of two requested environment controls, without changing the assertions:

| Environment | a1 | b1 | c1 | What was verified |
| --- | --- | --- | --- | --- |
| Baseline, native Haswell BLAS, one thread | Fails | Fails | Fails | Repeated baseline arrays identical |
| `NPY_DISABLE_CPU_FEATURES=AVX2,FMA3` | Fails, same first-pair metrics | Fails, same metrics | Fails, same metrics | Environment variable present; **feature disablement not established** |
| `OPENBLAS_CORETYPE=NEHALEM` | Fails, different last bits | **Entire original test passes** | Fails, different last bits | Both loaded BLAS runtime configurations report **Nehalem** |

The verified BLAS-path experiment demonstrates environment dependence of the
Cr pass/fail boundary. It does not establish that Nehalem is more physically
correct or recommend changing the application's default core selection.
No claim of cross-machine or all-thread reproducibility follows from it.

In the NumPy-control runs the captured CPU feature dictionary still reports
AVX2/FMA3 true. A direct interpreter probe with the requested variable likewise
reports those flags true and baseline `X86_V2`. Thus those runs cannot be used
as proof that all relevant fused/vector operations were disabled. NumPy
dispatch and OpenBLAS dispatch are separate mechanisms. Fused versus
non-fused evaluation remains a possible contributor to final-bit behavior;
this review does not isolate an individual FMA instruction as the cause.
The documented controls are described by
[NumPy](https://numpy.org/devdocs/user/troubleshooting-importerror.html) and
[OpenBLAS](https://github.com/OpenMathLib/OpenBLAS/blob/develop/docs/runtime_variables.md);
the conclusions here depend on the locally observed runtime metadata.

## E. Scientific validity and limits of independent evidence

| Cases | Check and result | What it establishes / does not establish |
| --- | --- | --- |
| a1 | Both old and current selected responses obey Hermiticity/PSD to rounding scale. For the selected query, Hermitian residuals are 1.734723475976807e-18 old and 3.344446255927791e-19 current, response norm ≈0.70256. The old minimum symmetrized eigenvalue is -6.10e-30; current ≈1.39e-17. | A finite positive-depth Gram integral is Hermitian PSD in exact arithmetic. The residuals fit rounding. This invariant cannot select a unique historical bit pattern. No clipping was applied. |
| a1 | Current `cancelled=None` versus `lambda:False` responses are byte-identical for analytic and numerical methods. Both methods raise `Cancelled` on immediate and in-work requests. | Cancellation plumbing does not change numerical results in this controlled comparison. The historical bitwise assertion is also testing a later optimization, beyond its original cancellation-only scope. |
| a2/a3 | Fixed-operand Decimal arithmetic and actual-operation replay explain the contraction difference. Direct and cached Hamiltonians differ by at most 2.22e-16 in selected matrix elements. Independently evaluated matrix exponentials agree with the Bloch wavefields at rounding scale. | Supports the shared physical/discrete model and the outgoing algebra. It does not prove angular/depth/basis convergence, or every material/geometry. The Both case's unchanged FFT arrays do not validate the differing Bloch last bits. |
| b1 | The original test reaches its group-parity assertion only after all independent localized-event raw-detector assertions pass. Recorded worst relative raw-event discrepancy is 4.017815604068825e-16, against unchanged `rtol=3e-12, atol=1e-17`. Fixture checks confirm finite Hermitian positive MDFF tensors and independent BCC groups. | Validates raw site-event contraction and detector integration for these inputs, beyond comparison with another production response array. The reference still shares elastic propagation and some low-level inputs; it is not an independent ab-initio Cr model. |
| b1 | All **66** saved-output decomposition and reversal comparisons pass at the original `rtol=3e-13, atol=1e-18`. They include total/up/down, both reversal states, linear identities, plus↔minus exchange, even invariance and odd sign reversal. | Completes checks that the failing original run could not reach. These are separately evaluated observations, not 66 newly passing original pytest cases. They do not distinguish the two legitimate reduction orders. |
| c1 | Selected response has Hermitian residual 4.69e-21 old / 1.36e-20 current, norm ≈0.0077069; both symmetrized spectra are PSD to rounding. Decimal fixed-operand evaluation supports the same Gram/trapezoid calculation. | Supports the XMCD fixture's shared numerical kernel. The physical accuracy of the supplied spectrum is outside this arithmetic comparison. |
| c2 | The source history isolates the same generic kernel change using the original explicit atomic MDFF/edge settings; the first raw difference is 1 ULP. FFT/incoming results remain available as exact comparisons. | Supports classification of this historical comparison. No independent atomic-physics ground truth was generated here; the selected Decimal response diagnostic was c1, not a new independent validation of the entire atomic model. |

For the independent matrix-exponential check, both direct and cached outgoing
Hamiltonians and the incoming Hamiltonian were evaluated with
`scipy.linalg.expm(1j*H*z) @ e0`, separately from `BlochStates.ket`'s eigenstate
construction. Across the nine selected state/configuration combinations:

- Maximum wavefield component difference: **6.661351400811327e-16**.
- Maximum `|Σ|ψ|²-1|`: **1.443289932012704e-15**.
- Maximum normalized eigenproblem residual: approximately **9.60e-16**.

Unit norm applies to this finite Hermitian, absorption-free elastic model.
It would not be the right conservation test for an absorptive or open-channel
extension. No such extension was introduced. Individual eigenvectors are
phase/degeneracy dependent; the diagnostic compares propagated states.
`expm` is an independent numerical evaluation of the same Hamiltonian, not
independent evidence for that Hamiltonian's physical scattering coefficients.

Existing Phase 2 XML was read, not rerun. At the exact full-run source 91aff15,
`test_ni_bounded_depth_quadrature_against_independent_gauss` passed, all eight
`test_historical_ni_matched_thicknesses` cases passed, and seven of eight BCC
Cr scientific-validation cases passed (the eighth is b1). The Gauss test checks
depth convergence at 2/10 nm, not all basis/angular convergence. These existing
results support the unchanged paths at their recorded inputs; they are not
new executions at cb180cd and do not select historical last bits.

No invariant here establishes experimental calibration, real bulk-Cr order,
absolute/cross-element intensity normalization, absorption, HOLZ, or a general
magnetic structure not already supported. The independent arithmetic is
conditional on supplied binary64 fields/tensors. Those genuine scientific
limitations cannot be removed by interface cleanup or tolerance changes.
The results support B for these six comparisons, with the acceptance decision
still requiring review; they do not confer generic scientific correctness
on every application output.

## F. Proposed resolution — review required, not implemented

### Decision for each original failure

| Case | Explicit recommended action | Scientific/software justification |
| --- | --- | --- |
| a1 | Separate cancellation neutrality from the older-kernel arithmetic comparison. Keep exact current no-callback/false-callback equality. Make the cancellation trigger observe the method actually executed: numerical site batching for `numerical`, `depth_response` for `analytic`, or a behavioral checkpoint independent of private helper names. Review a response-level propagated roundoff comparison for the old kernel. | Current cancellation neutrality is exact; the first mismatch comes from ef54a53. The later numerical spy provably receives zero calls, so changing only the first comparison is insufficient. |
| a2 | Preserve the 7bebdce reference and every scientific assertion category. Keep unchanged incoming/coherence/grid/depth values exact; review error propagation through only the changed Bloch result calculations. Compare raw, linear derived and normalized results separately. | A global scalar relaxation would conceal cancellation/normalization behavior. Algebra, replay, source history and independent arithmetic support the common intended model. |
| a3 | Apply the a2 Bloch contract within Both, retaining exact assertions on unchanged FFT paths and solver/result association. Preserve all maps and per-method results. | The first failure is the same Bloch calculation as a2. A Both-level blanket tolerance is unnecessarily broad. |
| b1 | Retain all independent raw-event, group-assignment and reversal assertions. For the internal linear group/total commutation assertion, review an operation-count/absolute-parent-scale criterion such as the derived `γ_(2*N+2*G+10)*S_key` model. Check all RAW/PARITY keys, not only `M_A`. | Decimal pixel reduction, positivity, parent-scale conditioning and verified BLAS dependence explain the existing boundary. The bound is independently derived and rejects loss/sign/percent-level changes of this nonzero signal. |
| c1 | Preserve the original 2f9c130 source reference and explicit XMCD inputs. Review a bounded Bloch response/intensity comparison with derived-signal propagation; retain all unchanged exact comparisons. | The historical compatibility requirement has mathematical equivalence and environment-dependent bit patterns as distinct questions. Existing source identity pins remain in place. |
| c2 | Use the same proposed error-propagation procedure with the explicit atomic model/tensor/energy inputs and their actual scales. Retain atomic-model assertions and unchanged exact comparisons. | A Ni-XMCD absolute floor is inappropriate for the much smaller atomic intensity. This is the same production numerical path with different inputs, not a separate material implementation. |

No scientific-kernel correction is justified by the evidence collected here.
Restoring an old operation order could restore particular historical bits in
a specified environment, but it would be a deliberate implementation/contract
decision with performance and validation consequences. This review recommends
retaining the common calculation engine and reviewing the comparison semantics.

### Concrete proposed numerical comparison procedure

The following is the implementation proposal for a subsequent reviewed step.
It is intentionally more precise than choosing a new `rtol` above today's
maximum discrepancy.

1. Keep source/data identity pins and fixed physical input assertions. Require
   matching shapes, finite values, provider identity, site assignment, geometry,
   energy grid and normalization convention before comparing numbers.
2. At the response primitive, calculate the componentwise expanded-product
   amplitude bound `E_v` from section D, using the complex-modulus bound for
   the subsequent outer product. Propagate input/field/phase error separately;
   do not treat an observed field discrepancy as evidence of zero upstream
   error. For the Hermitian propagation algebra, a perturbation satisfies
   `||exp(iHz)-exp(iH'z)||₂ <= |z|*||H-H'||₂`; solver backward/orthogonality
   errors must be included as well. This follows from the integral identity
   for two unitary propagators. Use independent high-precision/matrix-exponential
   evaluation on the bounded fixtures to verify the resulting estimator.
3. Propagate amplitude error through each outer-product component using
   `|δ(v_i conj(v_j))| <= E_i*|v_j| + |v_i|*E_j + E_i*E_j`, then include
   the complex-product rounding and the trapezoid's sum/product rounding.
   Contract with the tensor through an absolute sum of the same coefficients;
   integrate with the nonnegative detector weights/pixel area. Include both
   comparison paths' bounds. This yields a per-component/per-energy bound,
   not a universal absolute tolerance.
4. Propagate raw-intensity bounds through the actual linear coefficients of
   `N`, `M`, `D` and `Sigma_ref`. For b1's internal commutation comparison,
   the demonstrated positive-reduction bound is the narrower available model;
   it does not need a new uncertainty allowance for a shared upstream wavefield.
5. For a ratio `x/y`, require a denominator safely separated from its error
   interval. With `|δx|<=E_x`, `|δy|<=E_y`, and `|y|>E_y`, use a propagated
   bound such as `(E_x + |x/y|*E_y)/(|y|-E_y)`, plus division rounding and
   the other comparison path's bound. Apply the explicit factor 100 for
   percentages. A near-zero numerator must not set the absolute error scale.
6. Verify with deliberate negative controls: wrong site weights, zeroed/reversed
   odd signal, changed detector geometry, changed MDFF source and percent-level
   amplitude perturbations. Keep independent localized-event, parity, reversal,
   limiting-case and quadrature tests. Preserve exact equality for deterministic
   same-path invariants. No observed-array snapshot becomes a new golden array.

The current amplitude/Cr bounds are demonstrated for the recorded operations.
A complete end-to-end estimator for every normalized Ni map/spectrum has **not**
been implemented or accepted by this investigation. Its review and verification
are an explicit follow-up dependency. If the proposed propagation cannot be
justified for a required result, retain that result's unresolved assertion
rather than adopting an empirical universal tolerance.

The Cr bound above also depends on finite normal-range values, positive raw
terms and the stated operation counts. A future input/model violating those
assumptions needs an applicable error analysis, not silent reuse of this
fixture-specific derivation. This changes no supported physics.

### Follow-up verification and scientific acceptance

After a reviewed correction decision, rerun the six original configurations
and focused affected checks in the baseline environment, include a verified
second BLAS path, and ensure negative controls are rejected. Preserve the
original failing evidence and explicitly document any assertion replacement.
Preserve unaffected exact assertions and scientific checks. Do not relabel
this investigation as six passing tests.

If implementation changes, the required complete regression and affected
native validation must be performed against the new scientific source. A
test-only contract decision still needs the affected checks and applicable
project verification requirements. The present validated 6d98694 executable
continues to represent its original source and six-failure acceptance status.

## G. Impact on Phase 3

No Phase 3 cleanup was performed. The supported physical engine remains the
canonical `gui.forward_pipeline.calculate` route with explicit structure,
settings/model and optional site-group inputs. The diagnosis does not justify
material-specific replacement engines, a Ni fallback in generic paths, or
separate implementations to reproduce each old test's bits.

| Planned area | Risk / dependency before further restructuring |
| --- | --- |
| GUI/engine separation | Moving ownership can be behavior-preserving, but extracting functions that also change numeric batching or reductions requires an accepted comparison contract. Preserve the current canonical inputs, GUI workflows and result association. |
| BW service ownership | **Block arithmetic/batching/cache changes** in `double_channeling.py`, especially `_numerical_site_responses`, `prepare_outgoing_bloch`, and group response accumulation, until the affected historical-comparison contract is reviewed. All six first divergences trace to the earlier optimization in this path. |
| FFT multislice service ownership | Keep distinct physical/numerical methods distinct. Unchanged FFT results are useful exact controls. Do not merge FFT/BW methods merely because they share response/tensor interfaces. Ownership cleanup must preserve the independent validation path. |
| MDFF and multisite integration | **Block reordering** of event averaging, group multiplicities, detector integration, parity or normalization in `multisite_double_channeling.py`, `multisite_spectrum.py`, `gui.multisite_integration` and `detector_signals.py` until the linear/normalized contracts are reviewed. |
| Numerical accumulation order | Mathematical distributivity is insufficient for bitwise preservation. Retain independent-site squaring, full-crystal elastic preparation and explicit fractional detector weighting. Evaluate parent-scale error and cancellation before changing reductions. |
| Deterministic regression | Preserve same-environment repeated equality, source/provider identity and invariant tests. Historical bitwise equality across independent evaluation orders/BLAS paths requires an explicitly chosen requirement; it is not implied by scientific equivalence. |
| Cancellation tests | Repair the demonstrated method-specific hook in a reviewed test change before further internal helper movement. Keep behavioral cancellation and numerical neutrality as separate assertions. |

These are focused numerical-contract dependencies, not a proposal to freeze
all ordinary GUI code. The earlier structural audit's remaining large/coupled
modules are unchanged. Generality limitations requiring future physical models
remain separate scientific work, not Phase 3 interface tasks.

## H. Git state, evidence and reproducibility

Starting HEAD and all numerical observations in this investigation:
**`cb180cd877dfc2b92b4fa9fc7945525a89862b56`**, on
`refactor/physics-readability`, in
`C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute`.
The worktree was clean before the investigation. The checkout and branch were
not moved.

The local investigation commit adds only:

- `docs/SCIENTIFIC_NUMERICAL_CONTRACT_REVIEW.md` — this report.
- `scripts/scientific_contract_review/README.md` — reproduction instructions,
  dependency/adaptation limits and evidence naming.
- `scripts/scientific_contract_review/contract_capture.py` — observation plugin.
- `scripts/scientific_contract_review/history_sweep.py` — Git-source comparisons.
- `scripts/scientific_contract_review/analyze_observations.py` — arithmetic and
  full-array diagnostics.
- `scripts/scientific_contract_review/resolution_checks.py` — focused independent
  checks and earlier Cr comparisons.

These scripts are non-production investigation material. They do not enter
application packaging, register tests, replace assertions, introduce new
scientific baselines or write into reference-data directories. Their default
outputs remain ignored build evidence. The reviewed copies accept
`SCI_REVIEW_ROOT` so reproduction can use a fresh directory without overwriting
the original evidence. Syntax is checked without creating bytecode files.
No additional broad tests are required for these documentation/observer copies;
the actual diagnostic executions and their limits are recorded above.

Only this documentation/non-production material is committed locally. The
commit containing this report records that addition; its exact ID is supplied
in the completion response. The final ordinary Git status is checked after
commit. Final ordinary Git status is clean; ignored raw evidence remains in
place. No source, test, data, packaging or release-artifact change is included.
No push, merge, tag, publication or version change was performed.

### Raw evidence index

All paths below are relative to `build/scientific-contract-review/`:

| Evidence | Contents / status |
| --- | --- |
| `a1-r1`, `a2-r1`, `a3-r1`, `b1-r1-fixed`, `c1-r1`, `c2-r1` with `.log`, `.xml`, `-run.json` and `-capture/` | Six original individual failures, baseline environment |
| `a1-r2` through `c2-r2`, same suffixes | Six repeated original failures, identical compared arrays |
| `*-capture/capture.json` | Actual source, Python/packages/BLAS, inputs, assertion metrics, signed/max locations, component ULP histogram and operation layouts |
| `*-capture/observed_arrays.npz` | Observed current/reference/assertion arrays and selected intermediate operands; **not golden fixtures** |
| `*-capture/assertion_elements.csv` | Every original first-assertion element, exact component hex values, signed/absolute errors, allowance, residual and ULPs |
| `a2-trace`, `b1-trace`, `c1-trace` | Additional worker-thread observation during original tests |
| `a1-layout`, `a2-layout`, `c1-layout` | Operand strides and response intermediates for exact operation replay |
| `b1-pixel-reduction` | Original positive per-group pixels, fractional detector weights and independent reduction inputs |
| `history-v2/` | Successful kernel/orchestration history JSON and observed arrays; Git sources read directly by the driver |
| `analysis/error_distributions.json`, `array_errors.csv` | All comparable output paths, repeat equality, full error distributions |
| `analysis/contraction_precision.json` | Old/new replay, selected Decimal responses, amplitude bounds, Hermiticity and eigenvalues |
| `analysis/cr_conditioning.json` | Both energies, all 12 linear quantities, exact-pixel Decimal reductions, raw/postprocess split, normalization and propagated error bounds |
| `resolution-v1/checks.json` and NPZ | 66 saved-output Cr checks; cancellation neutrality/stale hook; direct/cached Hamiltonians and independent matrix exponentials |
| `resolution-v5/checks.json`, NPZ and `linear_assertions.json` | Successful original-introduction / direct-parent / optimization Cr history and all 12 original linear comparisons |
| `a1/b1/c1-numpy-sse*`, `a1/b1/c1-blas-nehalem*` | Environment experiments, requested variables and observed runtime configuration; names do not prove control success |

Historical evidence is preserved, including observer/schema/import failures:
the initial `b1-r1` observer attempt, the first history sweep's Windows decoding
error, and earlier Cr adapter attempts. They are excluded from scientific
outcome counts. All successful comparisons read Git blobs explicitly as UTF-8
where the diagnostic loader controls decoding. Existing original assertions
and archived numerical source statements were not rewritten.

Each launched diagnostic/test operation had its own command, PID, bounded
timeout and completion record. The launcher waits for its payload and stops
only its owned process tree on interruption/timeout. No unrelated process was
terminated. All investigation payloads completed; no background review job is
left running.

The Phase 2 native development executable remains at
`build/regression-recovery/native-candidate-6d98694/native-build/dist/EMCD-Sim/EMCD-Sim.exe`,
with its existing validated source identity. No rebuild or replacement was
performed. A preservation-only check matched its previously recorded SHA-256,
`cefb4b7880930dba38e966f9f437d6b2a4fc90af9ceb0814feccddcebcccaaaa`.
Existing strict kernel/reference-data pins, source/result
traceability and formal release inventories remain unchanged.

The investigation is complete as an evidence-and-recommendation task.
The scientific acceptance decision remains **NO-GO** until the required
comparison contracts are reviewed, changed explicitly where justified, and
verified without hiding the original failures.
