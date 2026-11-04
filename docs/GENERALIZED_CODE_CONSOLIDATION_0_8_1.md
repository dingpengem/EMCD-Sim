# Unified MDFF consolidation, v0.8.1 Part 1B

Status: source acceptance passed; merged-source Windows candidate acceptance pending.

The immutable Part 1 scientific source is
`654ed042b1b9638a43112e215a129c1a8d1bf186`; its acceptance documentation is
`52b36ee41e20aed5a86fb37db56ca372fac936f8`. Its ZIP SHA256 is
`c485928a87a3c25aebf1fe749527ec8d3a2fdea7da6d1da648e4297d352d7e9e`.
Those source files, numerical controls, ZIP and acceptance evidence are retained.

## Architecture review before implementation

BW/MS propagation, ionization-site interference and `Re Tr(RT)` contraction
are element-independent. Eligibility belongs to the provider and crystal/site
validation. This iteration remains limited to fully occupied single-element
crystals with supported equivalent ionization sites and uniform magnetic states.

XMCD-constrained MDFF is an axisymmetric effective-tensor approximation using
declared XAS/XMCD data, native energy, axis, handedness, normalization and source
identity. It is not a full ab-initio MDFF. Imported tensors use the existing
complex 3x3 parser with explicit reversal states and no inferred missing state.
Neither provider is inherently limited to 3d elements or L2,3 edges. Atomic
Ionization alone is limited to the implemented 2p-to-cubic-3d L2,3 model with
explicit Sc–Zn parameters. Synthetic demonstrations are not physical validation.

## Initial function classification

The AST inventory script covers every function, including nested functions and
Qt callbacks, under `src/emcd_sim`; its JSON is review evidence, not a deletion
list. Classification: A physical inputs; B general algorithm with Ni hardcoding;
C duplicate generalized implementation; D compatibility interface;
E independent scientific reference; F obsolete.

The [complete function inventory](MDFF_FUNCTION_INVENTORY_0_8_1.csv) lists every
function with line/module and review disposition. `general` means no Ni-specific
implementation was identified; it is not a deletion category. The immutable
before-inventory is retained in `outputs/part1b/function-inventory-before.json`.
No function was classified F merely because a static scan found no callers.

| Function or group | Class | Intended disposition |
| --- | --- | --- |
| `NiLocalConfig`, Ni parameter validation | A, D | Preserve historical inputs/API |
| `core_spinor_amplitude`, `ni_2p_to_3d_dipole`, cubic orbitals and radial helpers | B, D | Preserve algebra and compatibility; generic production names |
| `ni_local_transitions` | C, D | Generalized adapter only after exact independent comparison |
| `fcc_site_phase_matrix` | B, D | Preserve phase formula and compatibility name |
| `ProjectedNiFFT` | D | Existing alias of `ProjectedFFT`; prefer generic name |
| BW/MS response and tensor contraction functions | B | Preserve kernels; provider-level eligibility |
| `gui.emcd_forward.calculate`, `_calculate` and generalized orchestration | C, D | One production orchestration, compatibility entry points |
| Ni source inspection and historical project adapters | A, D | Preserve source/energy identity |
| Ni benchmark, analytical geometries and standalone reference scripts | E | Retain independent scientific evidence |
| Qt virtual and signal callbacks | D | Retain; static reference count is insufficient |
| Genuinely obsolete functions | F | None established by initial audit |

## Acceptance gates

Passed: independent atomic transition/tensor equality; 1,080 protected arrays;
provider integrity and project round trips; synthetic edge/site checks; complete
Windows source suite on the exact clean commit below. Pending: local merge,
post-merge checks, fresh packaged EXE workflows, manifest and SHA256 verification.
Final source and ZIP hashes will be recorded only after those gates pass.
No publication is authorized.

## Implemented provider boundary

Both public forward entry points delegate to one `forward_pipeline` orchestration:
source/material preflight, shared resource guards, independent incoming BW/MS
propagation, the accepted Single/Double response kernels, common contraction and
result assembly. There is no element-specific replacement solver. The existing
`DipoleTensor` representation is common to all providers. Imported tensor parsing,
Hermiticity/PSD checks, convex energy interpolation and frame rotation are reused.

| Input/provider | Source boundary | Current transition scope |
| --- | --- | --- |
| Historical Ni XMCD/atomic settings | Original parameter/source interpretation and conventional-FCC gate | Original Ni compatibility domain |
| Declared XMCD file | Original five-column file, byte SHA256, element/edge/axis/handedness, scale and assumptions | Validated L2,3 and tested K dipole declarations; not a full DFT tensor |
| Declared atomic parameter JSON | Strict accepted `atomic_2p3d` input and original-byte SHA256 | Explicit Sc–Zn, 2p-to-cubic-3d L2,3 only |
| Imported complex tensor JSON | Existing parser; explicit nonmagnetic state or both magnetic states/shared even tensor | Validated L2,3 and tested K dipole declarations |

`mdff_edges` is a provider declaration boundary, not a kernel eligibility gate.
Other edge families remain explicitly rejected. K support was checked through
Single/Double BW/MS, actual Qt workers, selected/full spectral sampling, map labels,
source integrity, project reopening and figure/data exports. This is mathematical
and application validation using synthetic data, not physical K-edge accuracy.
L3/L2 peak normalization and the L3 white-line diagnostic remain restricted to
L2,3. Raw signals and pointwise asymmetry do not require those peak conventions.

The old `l3`/`l2` configuration envelope is retained for saved-project compatibility;
for K it carries first/last-selection aliases, not physical L-edge assignments.
The explicit `selected_edges` and provider provenance are authoritative.

Private, bounded cached conversions allow direct XMCD/atomic input without asking
the user to manage intermediate tensor JSON. Their saved source path/checksum refer
to the original input. Input bytes are rechecked before calculation and before
accepting the result. CLI-exported tensors remain ordinary self-contained imports.
Source SHA256 establishes identity, not scientific authorship or material accuracy.

Ambiguous XMCD features require explicit native-energy selections; the GUI never
inherits Ni edge values merely because they lie inside another source's range.
Revalidation clears acknowledgement, and reopening can restore it only when the
original source checksum verifies. Changed/missing inputs are also detected on Run
or Preview without requiring a prior GUI-change event. Typed imported settings
cannot be relabeled into the historical Ni path. These review corrections have
dedicated regression tests. Requested spectral sampling may interpolate within the
native range; its energy origin is never shifted and extrapolation is rejected.

## Mathematical and historical compatibility

No accepted BW/MS response kernel, phase sign, Born conjugation, `Re Tr(RT)`,
Coulomb factor, depth quadrature, elastic provider or unit conversion changed.
Core angular amplitudes, coherent cubic-orbital sums, spin-hole/exchange reversal,
unit-area Gaussian broadening and tensor outer products retain their operation order.
Ni compatibility maps its original parameters into the shared transition generator.
Independent archived-Part-1 comparisons cover energies, complex amplitudes, weights,
site/edge labels, source strings and broadened complete tensors for both signs.
The historical tiny-radial event-dropping implementation remains a reference and
compatibility fallback below 1e-12 Angstrom; the explicit atomic provider retains
its stricter accepted transition-amplitude validity checks.

The 1,080-array control NPZ is byte-identical to the immutable baseline (both
SHA256 `ea3a7b9f1d5f257bcf6efac46593f4e1222a2437ccdad309f35bf9def4d2d8e0`).
This includes original Ni XMCD/atomic Single/Double BW/MS and synthetic Fe controls.
It does not establish quantitative material physics. Existing site-order/origin,
equivalent-site and independent phase tests remain in the source suite.

Retained independent references include Ni benchmark geometries, projected-potential
references and historical project/array evidence. `fcc_site_phase_matrix` and the
Ni-only default domain of historical response APIs remain compatibility surfaces;
declared sources supply the accepted `IonizationSites` interface. New production
FFT adapters use `ProjectedFFT`; the `ProjectedNiFFT` alias remains available.
The duplicate imported orchestration was removed, and the old Ni orchestration body
was extracted into the common pipeline. No entire module or Qt callback was deleted.

## Limitations and redistribution

This is a single-element, full-occupancy, supported-equivalent-site research model.
No multi-element or inequivalent-site MDFF, complex magnetic structures, AFM/SDW,
arbitrary crystal-field symmetry, many-body multiplet solver or complete DFT MDFF
was added. The approximately 1.6% detector-refinement sensitivity remains relevant.
Archived synthetic Fe BW/MS differences of 0.06397% Single and 0.12816% Double are
bounded consistency controls, not general convergence or experimental validation.
Exact Ni regression means numerical compatibility, not quantitative metallic Ni.
Windows functionality and same-host packaging acceptance are separate from physics;
an independent clean PC/VM remains untested.

No new external scientific tables or physical material defaults are bundled.
The unlicensed legacy Z=1–98 table remains external. The existing Adaptive
Dirac–Padé coefficient subset, Apache-2.0 LICENSE/NOTICE and provenance remain
unchanged and separate from the MIT application. Historical outputs, figure assets,
Part 1 ZIP and unrelated root worktree files are protected. No remote publication,
tag, public-binary replacement or release workflow is part of this work.

## Recovery record

The initial complete 811-test invocation finished 766 passed, 39 skipped and six
failures. Four were legacy readout-envelope compatibility, one was validation
ordering, and one source-mutation test watched a replaced progress message. Those
causes were corrected; the targeted rerun passed 27 tests with one optional skip.
The subsequent complete-suite attempt was interrupted at partial progress: no
active Python process, final XML or exit-status record remained. All 171 recorded
source/test/packaging fingerprints matched its unchanged snapshot. It is retained
as interrupted evidence, not counted as a passing or failing complete invocation.
Further recovered review checks passed 48 tests with two optional skips. The final
committed-source regression and native acceptance are recorded below when complete.

## Final committed-source regression

Exact clean tested feature source: `1c77fb1227cae87bf417fffaeb321bfba59d116e`.
**818 collected: 779 passed, 39 skipped, 0 failed, 0 errors; process exit 0.**
Pytest wall time: 1181.69 s. All 171 canonical source/test/packaging Python/spec
fingerprints verified unchanged from start through completion. The earlier failed
and interrupted attempts remain preserved separately; they are not reported as
passing invocations. Logs, JUnit XML, exit status and exact skip messages are in
local `outputs/part1b/committed-full.*` and `source-acceptance.json`.

The 39 skips concern optional saved studies/projects, incomplete original benchmark
outputs, undistributed WIEN2k companions and unavailable pinned offline HDF5 inputs.
No fallback scientific calculation was launched to fill those references. The
genuine historical Ni project supplied through the explicit environment path was
checked independently, including its original Lobato elastic control.

Source GUI acceptance completed 12 workflows plus two supplemental full-spectrum
K workflows with clean shutdown. Comparing the original Part 1 EXE's eight projects
against current source GUI controls gave **1,080/1,080 strictly bitwise-equal arrays**
(dtype, shape and bytes, including NaNs/signed zeros), maximum absolute difference 0.
These controls are retained for the fresh extracted-EXE comparison.
