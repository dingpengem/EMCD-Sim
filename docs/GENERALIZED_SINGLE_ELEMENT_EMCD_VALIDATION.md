# Generalized single-element EELS/EMCD: local validation

The imported-tensor **software** milestone is implemented and locally validated within the cases below. **Quantitatively or experimentally validated Fe EMCD is not delivered.** No trustworthy, basis/units/reversal-complete Fe-specific tensor dataset was supplied or obtained; the Fe demonstration is **SYNTHETIC TEST ONLY**. Physical Fe validation and broad numerical convergence remain blockers to stronger claims.

## Source identity and scope

- Feature branch: `feat/generalized-single-element-emcd`.
- Verified starting main/origin: `2f9c130099dce5df4e4609b521c42f53c5385518`.
- Implementation commit: `76deb6526fdd6e23f01e65a2d8f2436d6439113b`.
- Final scientific source, including inequivalent magnetic/charge-site guards: **`7c1d4a356e05f69cb0f4bfcf19905fbf35c0b27b`**; all final acceptance artifacts record this clean source (`dirty=false`).
- This later report commit does not change scientific source. The final feature tip is available from `git log -1` and the delivery message.
- Worktree: `build/generalized-single-element-emcd`. Main, the v0.8.0 release/tag, binaries and historical working trees are untouched. No merge, push, tag, package, EXE build or release occurred. Version identifiers remain at the released baseline; v0.8.1 is a development target, not a published package.
- [Architecture audit, import schema and contracts](GENERALIZED_SINGLE_ELEMENT_EMCD_DESIGN.md).

## Mandatory Windows source regression

Complete Windows source suite: **701 passed, 39 skipped, 0 failed, 0 errors**, 740 collected, **1504.11 seconds**. The log retains **907 warnings**, including Qt deprecation and Matplotlib collapsed-layout warnings. Run from the clean final source using the existing Python 3.11 Windows build environment, `QT_QPA_PLATFORM=offscreen`, `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, and `pytest tests -q -p no:cacheprovider -o faulthandler_timeout=180`.

The real external legacy scattering table was configured by path for its optional tests; it was not copied or committed. The existing protected 160-array evidence and the genuine historical Ni project were supplied read-only by `EMCD_UNIT_IDENTITY_DIRECTORY` and `EMCD_HISTORICAL_NI_PROJECT`. No expensive missing benchmark was regenerated as a fallback. Skips:

- 3: Full benchmark outputs are not complete
- 3: Full checkpointed thickness calculation still incomplete
- 3: Local MS validation outputs not generated
- 2: Local four-point benchmark not generated
- 1: Local legacy reference project unavailable
- 8: Optional GUI and existing real Stage D results required
- 1: Optional historical saved project is unavailable
- 1: Optional local WIEN2k companion audit; original files are not distributed with the package
- 1: Optional real saved Ni project unavailable
- 1: Optional saved GUI reference unavailable
- 6: Optional saved angular references unavailable
- 1: Optional saved benchmark unavailable
- 1: Optional saved result fixture unavailable
- 1: Optional stored GUI reference
- 1: Pinned offline HDF5 inputs unavailable
- 1: Requires original local WIEN2k audit companions; not distributed
- 1: Saved BW/MS fixture not available; never run a fallback simulation
- 3: Saved project fixture unavailable

Only the completed final-source suite is acceptance evidence. Preliminary/interrupted runs are retained separately and are not counted as passes. Logs retain deprecation/layout warnings; warnings are not presented as failures or silently removed.

## Retained physics and site normalization

The corrected contract remains `I(E)=Re sum_ab R_ab(E) T_ba(E)`, `T=L L†`, with conjugated forward transition modes and `Q=2*pi*g`. Incoming/outgoing propagation, actual post-loss energy, Coulomb denominators, coherent paths within one event, depth quadrature, cancellation/resource admission and independent-event intensity sums are retained.

For selected equivalent atoms, Single uses `P_ij=(1/N) sum_s exp(+2*pi*i*(g_i-g_j).u_s)`. Double multiplies each same-event kernel by `exp(+2*pi*i*(g-h).u_s)` and averages its response/intensity, never site amplitudes. Normalization is explicitly **mean per selected equivalent atom**, matching historical Ni; no hidden per-cell density or multiplicity is introduced. The complete crystal remains in the elastic potential.

Actual CIF/ASE fractional coordinates are used. Translation equivalence of the entire single-element cell is certified; rotation-related sites needing different tensor frames are rejected. Mixed/partial occupancy, inequivalent magnetic/charge sites and unsupported AFM/SDW are rejected even if the user selects only one atom. Available vector moments must agree with the declared +M axis; nonmagnetic tensors conflicting with nonzero moments are rejected. Magnetic state/axis and any ASE starting moment/charge annotations are recorded, not used as fabricated transition strengths.

The original Single kernel, Ni forward adapter, `mdff_tensor.py`, `ni_local_mdff.py`, `xmcd_effective_mdff.py`, IAM providers, coefficients and numerical defaults remain byte-for-byte unchanged. Double BW/MS files gain only optional validated site selection. Removing exactly that reviewed plumbing reconstructs the original default kernel source exactly. Immutable earlier source/physics fixtures are preserved; a separately pinned single-element extension guards all changed/new source files without requiring Git/network in ordinary source guards.

## Ni compatibility

- Four actual numerical comparisons against immutable pre-feature source passed: XMCD and Ni atomic models, each Single/Double with **both** BW and FFT MS. Every compared spectrum, map, coherence and amplitude array was exactly equal (at least 50 array comparisons per configuration).
- The existing protected 160-array unit-change evidence remained exactly equal.
- A genuine historical saved Ni project without a provider field restored **Ni Lobato**; its archived elastic amplitudes matched with the existing absolute tolerance `2e-12`. Its original manifest/checksummed arrays were not modified. Unknown/legacy sign-convention metadata remains unknown; no historical arrays were relabeled.
- Original `NiLocalConfig` defaults, source spectra, magnetic sign convention and project loading remain intact. Legacy XMCD/atomic providers continue to reject non-Ni material. The new non-Ni route is explicitly selected and independently gated.

## Imported MDFF and independent mathematical checks

The JSON interface validates element/edge, positive ascending native energy coverage, real/imag `(n,3,3)` arrays, finite values, scale-relative Hermiticity, PSD, proper Cartesian/local frame, declared per-atom units, provenance, validity assumptions and exact file checksum. Convex piecewise-linear interpolation preserves PSD without extrapolation or repair. Source `status` cannot self-declare scientific VALIDATED.

Nonmagnetic sources provide one real time-reversal-even tensor. Uniform-FM sources provide both explicit states and a shared-even tensor checked against their mean. Tests include a pair with a real magnetic-odd component for which `T_minus != conj(T_plus)`; no Ni conjugation-only reversal is imposed. Both states are individually validated. The element-specific XMCD exporter is a separate declared axisymmetric approximation; its pair is model-derived under the explicitly acknowledged reversal assumption, not two independent DFT calculations. Both matrices must still be present in the imported file.

Passed independent checks include direct small-beam Single event sums, direct matrix-exponential Double event/depth integrals, analytic/numerical depth agreement, site permutations, translations, consistent unit-cell-origin transformations, primitive/conventional BCC descriptions under the same periodic projected conditions, and the Double outgoing-potential-off reduction to entrance-only. Proper source-local/crystal/microscope rotations and nonnegative EELS were checked. Invalid/missing states, PSD/Hermiticity, units/provenance, edges, frames, extrapolation, changed checksums, unsupported state and site configurations were rejected.

An additional fixed-detector state-swap calculation passed **4/4** combinations (Single/Double × BW/MS): explicitly supplied +M/−M tensors were exchanged with the declared axis reversed. Raw spectra swapped **exactly**, `D_mag` reversed **exactly**, `D_nonmag` was **exactly unchanged**, and the Flip-M A signal was nonzero. No tensor was manufactured by conjugation.

## BCC Fe synthetic demonstration

The original synthetic PSD fixture has nine declared energy samples over 704–730 eV, with illustrative labels L3=710 eV and L2=723 eV. These are software-fixture choices, **not an Fe energy calibration, DFT result or experimental dataset**. Source SHA256: `bc7e671be41893bac5dba36c1ec3d943ca6b755c8bf97230f375d91203c3561a`.

Baseline: conventional BCC a=2.866 Å, [001], target (110), 200 kV, 0.4 nm, tilt (-5,7) mrad, beam cutoff 0.6 Å⁻¹, Fourier potential cutoff 1.2 Å⁻¹, angular grid17, depth17, boundary subpixels16, FFT24, maximum slice step0.005 nm; fixed detectors centered (0.2,±0.2) Å⁻¹, radius0.12 Å⁻¹. Fe (100) is extinct, Fe (110) retained; independently constructed reciprocal vectors/frame/indexing match. Both solvers use the same declared potential cutoff; full FFT propagation retains harmonics outside the finite BW/MDFF support and reports leakage without renormalizing.

All requested software outputs exist under ignored `outputs/fe-synthetic-acceptance-7c1d4a3/`: source JSON/CIF, nine-sample EELS, selected L3/L2 angular maps, virtual-detector raw spectra/decomposition, Flip-M A, Single/Double and BW/MS comparisons, saved projects and PNG/SVG/CSV/NPZ exports. Plot captions explicitly identify **Fe / SYNTHETIC TEST ONLY**. Required output data and checksums were verified; generated artifacts were not committed as scientific reference data.

Selected **BW synthetic** raw values (a.u.; no absolute cross-section calibration):

|Case|A+|B+|D_mag|D_nonmag|Flip-M A|
|---|---:|---:|---:|---:|---:|
|single L3|0.00583600603|0.00675290389|9.91254732e-06|-0.000926810415|-9.60908287e-08|
|single L2|0.00324633242|0.00376638781|-6.00488547e-06|-0.000514050503|5.75748384e-08|
|double L3|0.00582368378|0.00673205701|9.89799706e-06|-0.000918271229|-4.93510513e-08|
|double L2|0.00323945613|0.00375476695|-5.99604863e-06|-0.000509314779|2.94409668e-08|

Baseline whole-grid detector A+ BW/MS relative L2 difference: **0.236394% Single**, **0.474516% Double**. These finite-basis comparisons establish bounded software consistency, not physical accuracy or universal solver convergence.

## Bounded numerical sensitivity

All **24 cases** completed: twelve variations for each channeling model, both solvers, two selected energies. The table gives percent relative L2 changes in A+ versus the baseline. Thickness rows change the physical specimen, rather than representing numerical error. JSON evidence retains magnetic/nonmagnetic components, full method comparisons, norm/leakage diagnostics and exact controls.

|Variation|Single BW %|Single MS %|Double BW %|Double MS %|
|---|---:|---:|---:|---:|
|beam_cutoff|0.128925|0.0135672|0.27066|0.0396223|
|potential_cutoff|0|0.0363668|0|0.0729937|
|thickness_thin|49.941|49.8522|49.8615|49.6824|
|thickness_thicker|99.061|97.6747|97.8041|95.0205|
|depth_coarser|0.0009179|0.00228356|0.000473441|0.0022842|
|depth_finer|0.000229473|0.000570824|0.000118357|0.000570917|
|detector_coarser|9.2562|9.26664|9.24545|9.26648|
|detector_finer|1.61508|1.61806|1.61416|1.62016|
|fft_coarser|0|1.33722e-12|0|2.54702e-12|
|fft_finer|0|1.28735e-12|0|2.38644e-12|
|slice_coarser|0|9.65587e-07|0|1.90794e-06|
|slice_finer|0|1.37942e-07|0|2.72565e-07|

Beam cutoff increased to0.85 Å⁻¹; potential to1.5 Å⁻¹; thickness0.2/0.8 nm; depth9/33; detector grid9/25 with subpixels8/32; FFT16/32; slice maximum0.02/0.0025 nm. Detector refinement changes intensities by about1.6%, so this profile is **not declared numerically converged**. A potential-only increase cannot establish complete convergence in a fixed BW basis, even if its BW result is unchanged. Small FFT/slice changes do not certify beam, detector, thickness or physical-potential convergence. Post-loss propagation and its outgoing-off limit were independently checked; Double is not a scaled Single approximation.

## GUI and project acceptance

Offscreen GUI regression and an additional **native Windows source-GUI** run passed. The native run used Qt `windows`, real visible widgets/workers and a separate application-data/workspace directory. Three scenarios passed: Single with both solvers and GUI project restoration; Double with both solvers and restoration; missing source leaves saved arrays viewable and rerun blocked. The actual Python process returned0, no recorded errors, all workers stopped. **No packaged EXE was built or tested in this milestone.** Responsive mode may shorten the displayed title; the full scientific caption and exported figure retain element/status/context.

The third provider panel includes source validation, ionizing element, edge, uniform-FM/nonmagnetic state, crystal Cartesian axis, equivalent-site selection and acknowledgement. Manual numerical settings avoid transferring Ni automatic presets. Projects record source/checksum, magnetic state/axis, elastic provider, site selection/normalization, physics convention and exact commit. Missing/changed source disables rerunning, not read-only saved viewing. Old projects never migrate automatically.

## Configuration status and remaining blockers

|Configuration|Classification|Scope|
|---|---|---|
|Historical FCC Ni numerical/project compatibility|VALIDATED|Within protected fixtures and bounded source comparisons; not a new experimental-accuracy claim|
|Ni XMCD-effective / Ni atomic scientific model|RESEARCH / APPROXIMATE|Existing limits/defaults preserved|
|BCC Fe elastic coordinates, selection rules, indexing and phase contracts|VALIDATED|The tested periodic projected cases|
|BCC Fe synthetic tensor Single/Double EELS/EMCD|SYNTHETIC TEST ONLY|All software paths above; no physical Fe prediction|
|User-supplied physically sourced single-element tensor|RESEARCH / APPROXIMATE|File/software validation alone does not validate its Fe/material physics|
|Quantitatively validated Fe EMCD|UNSUPPORTED|Trustworthy Fe-specific data and independent quantitative references still required|
|Co/Cr validated material-specific spectroscopy or realistic Cr magnetism|UNSUPPORTED|No validated material tensor/configuration supplied; no FM Cr claim|
|Generalized non-Ni atomic spectra|UNSUPPORTED|Shared algebra/interface only; execution disabled|
|AFM/ferrimagnetic/SDW, inequivalent or multi-element site-resolved MDFF|UNSUPPORTED|Explicit rejection, not site averaging|

Approximations: dipole-only response; projected neutral IAM; finite ZOLZ/cutoffs; branch-frozen longitudinal transfer; continuous uniform-depth event density instead of discrete atomic layers/surface terminations; relative per-atom intensity; no calibrated experimental cross section, dose or absolute magnetic handedness. No complete DFT MDFF is supplied. Imported arbitrary-crystal XMCD remains an axisymmetric approximation and may omit anisotropy.

Recommended next step: obtain a provenance/rights/units/frame-complete **FM BCC Fe** L2,3 tensor dataset with explicit states, verify its normalization and reversal assumptions, then compare against independent analytical/published/numerical reference geometries. Refine detector and joint beam/potential support before any quantitative convergence claim. Rotation-related/HCP and site-resolved magnetic structures need separate tensor-frame/material work. Do not enable Co/Cr atomic or AFM/SDW physics by removing gates.

## Local evidence and complete changed-file list

All final scientific evidence records source `7c1d4a356e05f69cb0f4bfcf19905fbf35c0b27b`. Generated outputs remain local and checksummed; no historical figure/data was overwritten. Linux/macOS CI was not investigated. The existing v0.8.0 release and its assets remain unchanged.

|Evidence, relative to `outputs/`|SHA256|
|---|---|
|`final-full-windows-tests.xml`|`4f389dea15dd8c253de07a065ec192029534c8e10fd3207b02c54ba41de97a4d`|
|`fe-synthetic-acceptance-7c1d4a3/validation.json`|`f1014634b14509d082c6aad457d5f42431d9d2477eb7ddea09e697b73d26d8c8`|
|`fe-synthetic-acceptance-7c1d4a3/SHA256_manifest.json`|`dc0674e3b0993c75d7011913e62872af864908ca295fe820fb9d858e3baf8447`|
|`native-single-element-7c1d4a3-pass2/acceptance.json`|`f932e11ad84f7990ede3e6b1446b3978947cf7ce109afb2f381900718910ed3b`|
|`explicit-fe-state-swap-7c1d4a3/validation.json`|`2539bc5a586e86a6bda6aaecc8b13618176c91e4468e4cb328d94fb4c54187cf`|

Complete proposed change versus the verified starting main (including this report):

- `docs/GENERALIZED_SINGLE_ELEMENT_EMCD_DESIGN.md`
- `docs/GENERALIZED_SINGLE_ELEMENT_EMCD_VALIDATION.md`
- `docs/ROADMAP.md`
- `scripts/research/validate_single_element_emcd.py`
- `src/emcd_sim/atomic_ionization.py`
- `src/emcd_sim/double_channeling.py`
- `src/emcd_sim/generalized_xmcd.py`
- `src/emcd_sim/gui/channeling.py`
- `src/emcd_sim/gui/generalized_forward.py`
- `src/emcd_sim/gui/imported_tensor_ui.py`
- `src/emcd_sim/gui/numerical_settings.py`
- `src/emcd_sim/gui/project_io.py`
- `src/emcd_sim/gui/propagation.py`
- `src/emcd_sim/gui/results.py`
- `src/emcd_sim/gui/results_browser.py`
- `src/emcd_sim/gui/stage_b.py`
- `src/emcd_sim/imported_mdff.py`
- `src/emcd_sim/ionization_sites.py`
- `src/emcd_sim/multislice_double_channeling.py`
- `tests/fixtures/single_element_scope_v1.json`
- `tests/physics_source_guard.py`
- `tests/single_element_helpers.py`
- `tests/single_element_source_guard.py`
- `tests/test_generalized_xmcd_atomic.py`
- `tests/test_single_element_contracts.py`
- `tests/test_single_element_forward.py`
- `tests/test_single_element_gui.py`
- `tests/test_single_element_invariance.py`
- `tests/test_single_element_ni_compatibility.py`
- `tests/test_unit_labels.py`
- `tests/unit_source_snapshots.py`
