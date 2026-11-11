# Changelog

## v0.9.0-beta.2 Windows candidate — unpublished

- Prepare version-consistent standalone RC1 packaging with the unified Compute
  Resources panel, preserved Auto/Manual settings and corrected bounded SC
  memory estimates. Keep physics, sources, references and published artifacts.
- Distinguish requested/evaluated energy counts; document the verified 243-energy,
  selected-97×97 Ni workflow with Auto CPU/memory and offline guides.
- Preserve BW-SC per-array cross-platform evidence; record the unavailable
  authentic Mac BW-DC/MS-SC/MS-DC exports and publication NO-GO explicitly.
- See [candidate notes](RELEASE_NOTES_0_9_0_BETA_2.md) and
  [numerical comparison inventory](WINDOWS_MACOS_NUMERICAL_EQUIVALENCE.md).

## v0.9.0-beta.1 — Windows Research Beta (prerelease)

- Finalize current installation, Quick Start and Tutorial with the verified small 3.520 Å Ni Global workflow, current Viewer/MDFF acceptance controls, Local magnetic-subgroup/exclusion guidance and retained native illustrations. Packaged use needs neither Conda nor manual BLAS variables. Rebuild matching source/packages after this documentation-only change; numerical RC2 evidence remains separate.
- RC2: reserve measured, wrapping legend rows in shared EELS views, including narrow/DPI-scaled comparisons. Keep full curve identification in figure exports and preserve legend hide/show state, including curves split across modeled energy windows. RC1 and RC2 remain separate local preparation records, not beta-version changes.
- Consolidate the multi-site BW/MS Single/Double, crystallographic grouping, Material-owned Global/Local M, native per-group MDFF, results, project/history and export workflows. Magnetic grouping, ionization participation and source/frame declarations remain explicit.
- Include normal-startup verified single-thread control for both OpenBLAS runtimes, bounded four-worker execution, response/depth progress and cooperative cancellation (`62cb49a`). Four workers are not universally faster.
- Honor selected-energy full maps and detector support elsewhere in Local MS Double; preserve explicit all-energy full-field evaluation and internal FFT support (`daa5089`). The original Fe₃O₄ query count changes from 2,286,387 planned to 57,378 expected, not a measured original-size runtime improvement.
- Resolve both focused current-source resource/default test failures, without changing memory policy or numerical tolerances. Thirteen distinct directly relevant cases passed; historical failed/incomplete broad regression and source-guard status remains unchanged.
- Include shared Results layout/selection fixes, effective sampling captions, persistence, and generic saved-input freshness comparisons. Consolidate current user instructions; retain version-specific historical records below. See [release-note draft and scoped evidence](RELEASE_NOTES_0_9_0_BETA_1.md).


## Unreleased development source — crystallographic groups and direction workflow

- Restore uniform source-range sampling (241 requested points plus exact selected energies) as the new-project default. Keep native and selected-only sampling explicit and independent of selected-energy angular maps. Single Channeling evaluates only nonzero detector support elsewhere, prepares group tensors/phases and reciprocal vectors once, and retains bounded blocks, source checks and the unchanged tensor kernel. Save/Open preserves explicit old native/full-field choices. These changes are development source, not updates to earlier candidates or published releases.

- Bound multi-site Single Channeling raw storage to 16-energy blocks, reducing each block immediately to the unchanged fractional detector spectra and selected maps. Retain every requested/native energy and angular pixel, provider amplitudes, and existing kernels. Include this storage in GUI/worker admission consistently; retain RAM/budget margins and show dominant contributors without contradictory execution-allowed wording after rejection.

- Correct Local group MDFF setup: reuse source-backed XMCD declarations, check selected files automatically, suggest source-covered edge selections, expose the required RP−LP confirmation, and generate optional source/limitation descriptions. New group eta/beta defaults are visibly 1; saved values remain unchanged. Preview no longer clears unchanged model confirmations. Clarify preview/draft/accepted states, report actual Local energy/pixel workload, and retain named frame/source errors. Missing directions remain unconfigured and safe to cancel. Remove reference-Ni choices from ordinary controls while retaining saved compatibility internally. No solver or scientific-reference changes.

- Simplify new Global XMCD setup: automatic source format/range checks, visible source-convention choice and relative reference default 1, generated provenance/limitations with optional overrides, and the generalized provider as the normal path. MDFF Done returns a validated Material draft; Viewer Apply and Close accepts it. Cancel rolls back pending MDFF/direction edits. New projects start with editable general numerical settings (2.5/2.0 Å⁻¹ cutoffs), explicitly without a convergence claim. Preserve saved historical Ni providers and presets as reference options. Replace empty-reference conversion errors with a named A²/eV input error. These are development-source changes, not changes to previously accepted EXEs.

- Clarify UI status scope: local groups show “Inactive — Global mode” while Global magnetization is active, with inactive local direction details. Local mode retains actual missing/invalid-provider requirements and elastic-only exclusions. The shared MDFF editor identifies Global versus group readiness without copying configurations or changing validation. This is a UI-status clarification, not acceptance of Site M calculations.

- Prepare local dev4: full-basis diffraction preview no longer requires an inherited target to survive systematic-absence filtering (Fe₃O₄ [017], cutoff 2: 59 beams, absent 200 target). Retain valid orientation, two-beam-target and 121-beam safeguards. Set ordinary fresh/reset/Automatic cutoffs to beam 2.5 and potential 2.0 Å⁻¹; retain explicit saved values and the matched historical reference preset.
- Retire optional post-edge A/B correction from the GUI and force it off in new requests. Convert enabled legacy flags only in working settings with a notice; retain original files until Save and preserve historical results. Keep required MDFF physics and source/frame validation.
- Prevent wheel edits to focused parameter spin boxes and closed selectors, forwarding page scrolling while preserving explicit edits, dropdown-list scrolling, 3D zoom and plot gestures. Give group MDFFs an explicit numerical-preview action, show validated XMCD input spectra when missing declarations block tensors, and bind reversed group previews through the existing physical-pair validator. No general tensor rotation, scattering-kernel or numerical-reference changes; dev1/dev2/dev3 remain unchanged.

- Prepare local dev3: one Viewer/Site Groups MDFF entry and a shared, explicit-context three-model workspace; remove the main MDFF section while retaining seven peer Settings sections. Accept Global MDFF as configuration data, preserve group draft/outer Cancel transactions and independent contexts, and guard pending context switches. Scroll scientific controls with fixed footer actions for smaller/DPI-scaled desktops.
- Add explicit ionization participation to existing structural groups and project persistence. Excluded oxygen remains in the full elastic structure but not the selected-Fe denominator; enabled missing sources block by group name. Nonmagnetic sources retain validated reference frames without assigning Material magnetic order. Keep energy-window exclusions separate. Report the actual elastic-preview geometry/beam-limit reason without adding an MDFF requirement. No propagation kernels or historical references changed; dev1/dev2 remain unchanged.

- Make Material authoritative for target M, with transactional Global editing in the existing Viewer/Site Groups workflow and read-only target/context displays in MDFF Configuration. Remove per-model target restoration and source-validation overrides; retain independent full frames, physical-pair validation and compatible preview/submission. Use consistent title-case Settings headings without peer prefixes. This source cleanup is not in the unchanged `windows-crystal-groups-dev1` candidate (`effb755`).
- Preserve the previous application regression at `f769e05`: **1,300 passed, 40 failed, 126 setup errors, 62 skipped, exit 1**, followed by 22 distinct focused passes at `effb755`. Broad regression/source-guard coverage remains incomplete; this cleanup does not rerun those suites, maintain pins or build another candidate.

- On `feat/v0.9.0-crystal-grouping`, add symmetry-orbit grouping with original ASE indices, Wyckoff/CIF provenance, explicit unconfigured structural drafts and project persistence (`f2a6e93`). Ordinary CIF import does not assign magnetic order or MDFF.
- Accept compatible group directions and explicitly validated physical reversal pairs through Apply, Save/Open and recalculation (`8b0c8e3`). Preserve source/frame identity and amplitudes; failed Apply retains accepted settings and drafts. Reject unsupported fixed-frame Z→X changes. magCIF and general tensor rotation remain future work.
- Improve the existing Site Group Editor with a scrollable panel, a readable/resizable group table, count and MDFF status columns, and explicit accepted/draft/input M summaries. Clarify individual atom picking versus whole-group editing and Apply/Cancel status.
- Document the development workflow and its limits. These additions are not in the accepted v0.9.0-beta.1 candidate at `6b917ed` or a published release. Scientific kernels, references and tensor validation are unchanged. Previous broad source-guard verification remains **incomplete**; this UI/documentation step does not run calculations, full regression, guard suites or builds.

## v0.8.1-beta.2 - Windows Research Beta (prerelease)

- Add the dedicated MDFF configuration interface and element-aware cubic Sc-Zn Atomic parameter editor, including explicit electronic/radial/frame inputs, reference starts, synthetic defaults, per-element drafts, and numerical previews.
- Add editable constant complex tensors and L2,3 Lorentzian spectra from independent integrated-strength tensors, with simple/full matrix views, heatmaps, and advanced imported exchange.
- Show actual XMCD source columns beside the provider tensor. One source selection supplies preview and calculation; stale snapshots remain identifiable.
- Require both explicit edge selections for ambiguous XMCD. Preserve Fe 710/723 eV selections after save/reopen and prevent stale JSON overriding later visible controls.
- Preserve historical saved Atomic settings, reject pending/failed external source validation, restore intended model/frame/inputs, and separate valid Fe elastic preview from MDFF eligibility.
- Update installation, first-calculation, model-construction, and project-creation documentation. No existing project JSON is required.
- Validation: release source `88dc9ec` passed **21 focused packaging/safeguard checks**, and the beta.2 EXE passed native ambiguity handling, explicit Fe 710/723 eV preview/calculation, and normal save/restart/reopen/recalculation. The earlier full-run XMCD ambiguity issue was fixed in `4f15a4d` and passed **four focused regression cases**. No complete full-suite rerun was performed on the final release; historical results and the authorized prerelease-specific exception remain in the [release notes](RELEASE_NOTES_0_8_1_BETA_2.md#validation-evidence-and-scoped-exception).
- Explicitly exclude unused Qt PDF/Virtual Keyboard and their dependency chain; provide matching Qt/PySide/Shiboken sources and replacement instructions. Omit Microsoft runtime copies and require the official user-installed x64 runtime. Set consistent beta.2 version metadata. See [release notes](RELEASE_NOTES_0_8_1_BETA_2.md).

## v0.8.1-beta.1 - Windows-only Research Beta

- Generalized single-element imported MDFF and explicit atomic 2p-to-3d research
  workflows, GUI generation, source provenance and unchanged Ni compatibility.
- Conservative cleanup: 64 modules retained with evidence; five unused imports
  removed; no scientific function or kernel/default changed.
- Fresh portable Windows build with extracted-EXE imported/atomic/project/export
  acceptance. Publication is gated by the separate versioned acceptance record.
- Synthetic Fe remains physically unvalidated; no multiplet/DFT, AFM/SDW or
  multi-element site-resolved MDFF is supplied. See [release notes](RELEASE_NOTES_0_8_1_BETA_1.md).

## v0.8.0-beta.1 — Windows-only Research Beta (2026-11-03)

- Fresh Windows portable build with consistent Python 0.8.0b1 / Windows 0.8.0.1 metadata; exact source is the release tag target.
- Windows source and extracted-EXE acceptance are recorded in the [release acceptance](https://github.com/dingpengem/EMCD-Sim/blob/main/docs/WINDOWS_0_8_0_BETA_1_ACCEPTANCE.md). Independent clean-machine installation and experimental quantitative accuracy remain unverified.
- Linux/macOS are not certified or packaged: unresolved Linux bool_dealloc shutdown abort and macOS Qt modal preflight stall remain visible.
- Preserve historical v0.7.0 assets and the recalculated 9/30 nm Ni Lobato case study, with raw a.u. primary and normalized percentages supplementary.

### Unified neutral-atom elastic factors

- Bundle pinned Apache-2.0 Adaptive Dirac–Padé 2026 Z=1–118 coefficient data with separate license, attribution and provenance. Use an independent NumPy evaluator over crystallographic g=0..36 inverse angstrom; no new runtime dependency or double potential scaling.
- Default new GUI/provider-factory calculations to Adaptive; retain named Ni Lobato, unchanged legacy Python constructor and explicit Lobato fallback for old saved settings. Record provider identity/digests in new projects.
- Preserve the external Z=1–98 adapter and strict all44 XF/Mott low-g guard. Its unlicensed table remains outside Git.
- Validate BCC Fe, CsCl, hexagonal ZnO and a monoclinic cell using independent reciprocal references, actual Qt indexing/click controls and bounded matched BW/MS checks. Add checksummed elastic-only save/read-only open.
- Preserve historical scientific outputs and Ni MDFF/EMCD kernels. This release changes packaging/version and provider availability, without rerunning historical studies. See the [acceptance reports](acceptance/unified-elastic-2026-11-03/FINAL_INTEGRATION_RECOMMENDATION.md) for numerical/physical limits.

## 2026-11-03: recalculated Ni documentation example

- Replaced current-facing Ni spectra with verified fresh `20261103T225908Z` results, twelve portrait previews and raw/percent 2x2 summaries.
- Clarified fixed-detector Flip-M magnetic `2*M_A`, exact ideal zero even residual, and distinct normalization denominators.
- Added independent four-spectrum validation, new selected-energy tables and hashed provenance. Historical figures/data are preserved; no kernels, GUI, defaults or release version changed.

## 2026-11-03: user documentation for the public Windows Research Beta

- Reorganized README, installation, small Quick Start and User Manual; added a complete scientific tutorial and documentation index for public v0.7.0-beta.1.
- Verified released controls/source, live Laue/Thales behavior, energy sampling, fixed-detector reversal, raw differences and distinct percentage denominators against implementation and existing data.
- Reused actual native EXE captures and completed 9/30 nm Ni spectra with compact preview/source hashes. No new simulations, binary build, physics/default/GUI changes, version, tag or release.
- Publication and compatibility status are in the [public release](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.7.0-beta.1), [current guides](INDEX.md) and [documentation review](DOCUMENTATION_REVIEW_0_7_0_BETA_1.md). Historical entries below retain their original milestone statements.

# v0.7.0-beta.1 - physics-corrected local Windows candidate

> **Critical scientific compatibility notice:** legacy Windows packages before
> **v0.7.0-beta.1** used a superseded Born/MDFF convention affecting calculated
> magnetic-odd EMCD signs. Historical signed L3/L2 magnetic spectra require
> revalidation or recalculation before interpretation under the corrected
> convention. This does not imply that all historical nonmagnetic EELS,
> diffraction intensities or thickness trends are wrong. Preserve original
> arrays, software/convention and source provenance; never silently flip or
> relabel legacy arrays. Intermediate corrected source commits, including
> `4f578156`, still used the old version label: exact commit/convention metadata
> takes precedence over version alone. Missing convention is unknown or
> legacy-unverified. Absolute experimental magnetic handedness is uncalibrated.

- First Windows candidate of the corrected forward-Born implementation:
  I=Re sum R_ab T_ba=Re Tr(RT), forward modes L* with T=L L-dagger,
  Double site phase exp(+2*pi*i*(g-h).u); Single site phase unchanged.
- Version/build/provenance metadata and legacy-result warnings; no solver,
  numerical-default, worker-policy, GUI-layout or project-schema changes.
- Historical releases and scientific arrays remain unchanged. See
  [release notes](RELEASE_NOTES_0_7_0_BETA_1.md) and
  [candidate acceptance](WINDOWS_0_7_0_BETA_1_ACCEPTANCE.md).

## Windows candidate from 97b2220e (same application version)

Native automated acceptance: **PASSED**. Independent clean-machine acceptance:
**NOT TESTED**. Official public v0.7.0 release: **NOT PUBLISHED**. Linux CI
line-ending/hash and interpreter-shutdown issues remain unresolved; macOS
validation remains pending. This remains a beta research candidate, without a
complete complex DFT-derived MDFF or universal numerical convergence.

- [Windows Actions run 41516996056](https://github.com/dingpengem/EMCD-Sim/actions/runs/41516996056) produced a development candidate containing standardized physical-unit labels and the reviewed live ZOLZ/ZA overlay and drag fixes. Thales remains teal dotted; Laue is darkorange dashed; stale intensities are invalidated during dragging.
- Five native orientation checks, eight exact scientific reference comparisons and two fresh-process nine-scenario cancellation/worker-safety runs passed. See [candidate acceptance](WINDOWS_ZOLZ_97B2220_CANDIDATE_ACCEPTANCE.md) for scope and limitations.
- Binary source remains `97b2220e5329dad6f98eedec61f58a6cf07d9da8`; portable ZIP SHA256 is `8d157d8b62fb6570d201360cdae85f44aa4cea2c1478f1949eb4336a135e17bc`. Documentation updates do not create a new binary or scientific candidate. No v0.7.0 Release or tag is published by this update.

## Historical development entries (preserved)

# Unreleased → generalized Multislice final scientific review

- Five targeted [111] detector-only controls identify potential/beam support as
  the dominant raw-intensity sensitivity; passing final MS increments do not
  erase the lower-profile failure or certify enlarged BW.
- Reject mismatched prepared FFT microscope/frame/reciprocal/depth contexts;
  make large-cell preview work checks overflow-safe.
- Expose [111] certification warnings and truthful ideal-basis preview labels;
  retain existing defaults, thresholds, MDFF and protected scientific outputs.
- [GO for bounded research merge](GENERALIZED_MULTISLICE_MERGE_READINESS.md),
  not unrestricted convergence. No merge, release, Atomic 3D or Windows rebuild.

# Unreleased → generalized EMCD end-to-end validation

- Normal source-GUI Single/Double BW/MS acceptance across [001], [017], [117],
  [111] and [710], including Bragg alignment, coherent EELS/maps and projects.
- General target/local-row selection replaces the remaining implicit (200) FFT
  row fallback; stale orientation/outgoing/basis descriptions and project naming fixed.
- Direct [117] raw-map equivalence and independent [111] quadrature/outgoing/joint
  controls; residual joint raw-intensity failure retained at unchanged thresholds.
- No solver-model/default/version change, Atomic 3D work, merge or Windows rebuild.
  See [validation and review disposition](GENERALIZED_MULTISLICE_EMCD_VALIDATION.md).

# Unreleased → generalized Projected ZOLZ development

- Shared crystallographic orientation, exact integer reciprocal basis and
  structure-derived IAM Fourier potential; no production [017]/[117] geometry imports.
- Legacy algorithms retained as frozen test fixtures; saved FFT-cell metadata
  and frame guards preserve viewing and prevent ambiguous reruns.
- Representative [001]/[017]/[117]/[111]/[710] BW/MS Single/Double checks.
  Independent [111] quadrature failures remain documented; no universal
  production convergence claim. Atomic 3D B1 is deferred pending review.
- No default/version change, Windows rebuild, merge or publication.
  See [Milestone A validation](GENERAL_ZOLZ_MULTISLICE_VALIDATION.md).

# Unreleased — Ni [117] research geometry

- Target-aligned FCC Ni [117] / (2,-2,0), full finite ZOLZ and explicit ideal
  incoming/outgoing two-beam support for BW/MS Single and Double Channeling.
- Raw mirror-parity diagnostics and reproducible bounded scientific validation;
  crystal-[001] magnetization remains fixed and rotates once into the local frame.
- Solver-independent warnings for absent off-row potential terms and coarse
  sampling; safe read-only viewing of older [117] projects with guarded input reuse.
- Existing [001]/[017] defaults, XMCD data, physical conventions, package version
  and Windows artifacts are unchanged. No universal convergence, genuine DFT
  MDFF or calibrated experimental accuracy is claimed. See [review](NI_117_MERGE_READINESS.md).

# v0.6.1-beta.3 - Windows Actions candidate

Package `0.6.1b3`; no release or tag. Responsive simultaneous scientific panels,
persistent splitter/chevron preferences, collapsible Project Results, compact
figure reflow and native standalone acceptance. Versioned EXE metadata and
ZIP/build provenance use the existing PyInstaller pipeline. Physics and
300 kV / 3.2 / 2.5 / 97 / 2048 defaults remain unchanged. See
[candidate scope and downloads](WINDOWS_BETA_3.md).

# v0.6.0-beta.1 - Double-Channeling EMCD Simulation

Windows research prerelease; application/package version **0.6.0**.
See [acceptance and provenance](WINDOWS_V060_BETA_ACCEPTANCE.md).
Double Channeling already shipped in 0.4.5-beta.1. This milestone consolidates
its incoming/depth-integrated/outgoing BW and FFT framework and full-energy
EELS/EMCD interpretation within the existing model and convergence limits.

- Unified primary Raw (a.u.) / EMCD Asymmetry (%) controls for spectra and maps.
- Preserved signed raw magnetic/nonmagnetic differences; total asymmetry is
  the unchanged +M difference/sum, not a magnetic-only quantity.
- Retained magnetic-only/even common-denominator components and other legacy
  diagnostics in Advanced Diagnostics; explicit saved Relative migration.
- Added descriptive CSV/NPZ sidecars while preserving original project arrays,
  PRB fields, provenance and original numerical definitions.
- Added a fresh Windows x64 standalone build with source/frozen acceptance,
  manifest, checksums and original-array comparison.
- Focused hand-reference, GUI, geometry, export and compatibility validation:
  see [validation report](EMCD_V060_VALIDATION.md).
- Physical solvers, MDFF, apertures, precision, memory and cancellation unchanged.
  Published 0.4.5-beta.1 remains intact. No global convergence or calibrated
  intensity/SNR claim is added.

---

# v0.4.5-beta.1 - Windows research Beta

Package version remains `0.4.5`; this is a GitHub Pre-release, not a stable release.
See [release notes and exact binary provenance](RELEASE_0_4_5_BETA.md).

- Added genuine BW and independent FFT Double Channeling with post-loss outgoing propagation and depth-distributed ionization.
- Added full-energy Ni L3/L2 EELS/EMCD, preserved four raw A/B reversal spectra, signed magnetic/nonmagnetic Raw and Relative displays, and separate PRB dichroism.
- Clarified crystallographic g=1/d beam/potential cutoffs, zone-axis versus tilt, physical detectors and restricted-row versus full finite ZOLZ geometry.
- Preserved checksummed projects, Results Browser and PNG/SVG/CSV/NPZ export, including raw/percentage data and saved display state.
- Added configurable 512/1024/2048/4096/8192 MiB process-memory budgets and cooperative cancellation through BW/MS kernels; Both stops before the second solver starts.
- Reused the accepted cancellation-fixed Windows ZIP without rebuilding. Main/tag documentation can be newer than its explicit build-source commit.
- Validation and limitations: earlier 115-test acceptance and 42 focused cancellation tests are separate, overlapping inventories. Native Windows 150% testing passed; independent clean-machine testing remains NOT TESTED. Approximate XMCD MDFF, projected potentials, frozen longitudinal transfer, uncalibrated counts/native energies and representative convergence scope remain.

---

## Historical post-v0.4.5 research record

The sections below retain the original milestone assumptions and numerical results.

# Unreleased research main — Ni [017] high-mistilt XY and native WIEN2k edge audit (post-v0.4.5)

**This records research work already merged into `main`; no new version tag, package-version bump, or experimental/quantitative accuracy claim is implied.** The package metadata is still `0.4.5`.

- Added real oriented projected FCC Ni **[710]** and **[017]** crystal geometries with genuine cubic hkl, matched physical Bloch-wave / FFT-multislice elastic potentials, indexed diffraction, and explicit ZA markers and Thales-circle apertures. Target **(200)** for [017]; `s200=0` defines the reference but the internal wavefield is not an isolated two-beam state.
- Added [017] cubic-[001]-magnetization **tensor rotation** (`T_local=R T_crystal R^T`) and native WIEN2k source-energy feature assignment. Native XAS maxima are **831.421/848.752 eV** (L3/L2); selected signed magnetic extrema are **831.271/848.698 eV**. The archived SOC core splitting ≈**17.48 eV** supports the relative assignment. The ~+21.25 eV discrepancy between native XAS maxima and older nominal 852.7/870 eV references **does not establish experimental absolute energy calibration**. Source spectrum is unchanged and unshifted.
- Completed **43 distinct X/Y mistilt orientations** around exact paraxial (200) Bragg with independently preserved native full BW/MS A/B EELS, plus/minus magnetization states, parity-odd/even contrast, raw and post-edge-corrected differences, selected L3/L2 angular maps, indexed diffraction and plot-only regeneration. Definitions: `theta_x=-7.11672544+delta_x`, `theta_y=delta_y` (mrad) in local [017] coordinates. Generated numerical/figure outputs remain local under `outputs/ni_017_high_mistilt_xy/` and are not necessarily Git tracked.
- Selected low-cutoff candidates: **(delta_x,delta_y)=(-6,0)** maximizes sampled absolute magnetic detector differences; **(0,-25)** maximizes sampled absolute magnetic asymmetry and relative ideal-counting proxy. Intrinsic even A–B follows the predicted Y-reflection relation in the present model; at nonzero Y, post-edge scaling often improves recovery but introduces an artificial even residual on the Y=0 symmetry plane.
- **Critical limitation:** physically changing Fourier potential cutoff 2.2→3.2 cycles/Å changes the exact-Bragg selected magnetic signal by about **21.8%** and reverses ranking of two absolute-signal candidate orientations. BW/FFT matched-model agreement (maximum magnetic-map relative discrepancy about **0.6025%** in the 43-case production survey) is *not* physical potential convergence. No full 3D ionization/outgoing channeling, complete DFT MDFF, experimental energy/dose calibration or validated quantitative Ni EMCD is provided.
- Added [Ni [017] case-study explanation and figure guide](NI_017_CASE_STUDY_GUIDE.md): separates computed spectral features from experimental absolute edge energies; explains why [017] and (200) were selected; documents all X/Y tilt conventions and special conditions; identifies exactly which saved plots show magnetic, even, raw/corrected and convergence effects. The guide also points to [high-mistilt technical data](NI_017_HIGH_MISTILT_XY.md) and [oriented [017] baseline](NI_017_MINORZONE.md).
- The recorded high-mistilt milestone passed **20 focused tests**, including magnetic parity, selected map/EELS integral reconstruction and byte-identical prior-output preservation. The documentation-only updates here do not alter the numerical engine or rerun the forward simulations.

---

# v0.4.4 — Metallic Ni transition-data provenance gate

- Audited public Ni L2/L3 datasets and distinguished phase-correct FCC Ni **complex transitions** from EELS/XAS/XMCD intensity datasets and NiO models. No suitable publicly downloadable complex FCC-Ni transition table was verified; no automatic physics replacement was performed.
- Added `ni_data_audit.py` to check NPZ dipoles, L2/L3 labels, core-SOC/spin/phase declarations, phase-specific source metadata and algebraic tensor consistency. Audit pass is **not** scientific validation.
- Added optional `--mdff-model ni-metal-external --mdff-provenance path.json`; it refuses missing/mismatched inputs and continues to report relative/nonquantitative units.
- Preserved all prior EMCD modes and Windows/macOS/Linux compatibility.

# v0.4.3 — Complex MDFF in entrance-only Ni EMCD

- Added a transition-derived complex tensor backend to the physical Bloch-wave single-channeling forward calculation, preserving the legacy Gaussian model as a selectable default.
- Coupled coherent incoming beam amplitudes to localized FCC Ni core-loss site phases; kept the **proper** dipole MDFF separate from fast-electron Coulomb denominators, with explicit cycles-to-angular-Q conversion.
- Added `--mdff-model {gaussian,ni-local,transitions}` and portable complex transition NPZ support; disabled unsupported tensor voltage-to-moment scaling.
- Added matched L₂/L₃ reciprocal component figures and data, source/approximation metadata and focused positive-intensity, phase, and chirality-reversal tests.
- No claim of Ni-specific quantitative MDFF, absolute cross sections, DFT, voltage response or double channeling.

# v0.4.2 — Non-DFT local atomic MDFF option (P2)

- Added independently written Ni core-SOC + cubic-orbital local dipole transitions with analytic normalized screened-hydrogenic 2p/3d radial integral.
- Added optional imported radial wavefunction CSV and normalized numerical radial dipole integral for external atomic Hartree-Fock data.
- Preserved complex amplitudes and transition-derived tensor; added cubic basis, radial quadrature, chirality and cross-platform CLI checks.
- Documented atomic multiplet/Quanty route and explicit non-DFT versus quantitative limitations. Existing Gaussian-MDFF `emcd-ni` is unchanged.

# v0.4.1 — Ni 2p core-SOC angular reference and portable transition data bridge

- Computed 2p3/2 and 2p1/2 core angular spinors and 2p->3d complex Cartesian
  dipole amplitudes using Clebsch-Gordan coefficients and spin selection.
- Illustrative Ni 3d spin-hole weights, L3/L2 onset energies and radial dipole
  integral remain explicitly user-specified. **Not** DFT or calibrated Ni MDFF.
- Added strict external complex dipole CSV -> TransitionDataset NPZ converter
  (with explicit input bra convention), platform-neutral command line and tests.
- Preserved legacy Gaussian EMCD CLI unchanged. Double channeling deferred.

# v0.4.0 — P2 complex MDFF tensor foundation

- Added `TransitionDataset` for externally supplied complex dipole matrix elements, energy losses, site/edge labels and transition weights. Portable NPZ with strict explicit conventions and provenance.
- Added spectrally broadened Hermitian dipole tensor `T_ab(E)` and full complex `S_dip(Q,Q',E)` contraction, separate from Coulomb factors.
- Added `emcd-mdff` / `python -m emcd_sim.mdff_reference` synthetic-only demonstration and basic physics tests.
- No real Ni DFT/SOC transitions provided; no claim of quantitative Ni EMCD and no changes to existing Gaussian EMCD results.

# v0.3.6 — Independent elastic Fourier multislice reference (P1)

- Added pure NumPy projected FCC Ni [001] periodic FFT split-step elastic propagation, independent of finite-beam eigendecomposition.
- Added matched Fourier-truncated IAM potentials for Bloch/FFT propagation, and cross-method comparisons under zone-axis and illustrative 3BC geometry, multiple cutoffs and thicknesses.
- Exported elastic intensity, full distribution total-variation discrepancy, source parameters and PNG/CSV/JSON reference; no EMCD or outgoing-wave changes.
- Added convergence-sensitive tests for Fourier potential normalization, unitary propagation, tilt response, matched Bloch/FFT diffraction and Windows-safe CLI.
- Documented residual physical potential/basis cutoff sensitivity and limitation of the 2D z-independent projected reference. No quantitative Ni EMCD claim.

# v0.3.5 — Entrance Bloch-wave 2D basis convergence diagnostic

- Added `python -m emcd_sim.convergence` / `emcd-convergence` to compare growing FCC Ni 2D ZOLZ bases under fixed 2BC/3BC/zone-axis incident geometry.
- Compare elastic 000/±200 intensities, norm, full beam-distribution total variation against largest *finite* basis, and illustrative L3 EMCD difference/asymmetry.
- Export CSV, NPZ, metadata and labeled PNG; shared detector and tilt within each condition, platform-neutral paths.
- No modifications to elastic Hamiltonian, scattering factors or Gaussian MDFF. **No convergence certificate or quantitative EMCD claim**.
- Added focused validations for reference alignment, normalization, CLI output and path portability.

# v0.3.4 — EMCD reciprocal maps by diffraction condition

- Added portable `emcd-compare` / `python -m emcd_sim.compare_conditions` to generate a side-by-side FCC Ni L3 reciprocal-map comparison for 2BC, near-2BC, symmetric-3BC and zone-axis.
- Shared q axes and color limits across conditions; indexed diffracted beams, condition-specific apertures/tilts, illustrative local magnetic/nonmagnetic ratio, integrated A−B metadata and machine-readable NPZ.
- Reproducible example and deliberately non-quantitative provenance; no changes to Bloch-wave or MDFF physics.

# v0.3.3 — Tilt and thickness EMCD diagnostic

- Added `python -m emcd_sim.scan` / `emcd-scan`: 3D tilt-x × tilt-y × thickness scans at Ni L3 using existing entrance-only illustrative MDFF.
- CSV and NPZ numerical results, fixed color scales for comparison heatmaps and magnetic/nonmagnetic reciprocal maps.
- Explicitly demonstrate that systematic-row Y tilt insensitivity is a basis truncation artifact, while finite 2D ZOLZ can vary with Y tilt.
- Portable Windows/macOS/Linux CLI, focused symmetry/data-shape regression tests; no changes to existing Bloch-wave, MDFF or EELS equations.

# v0.3.2 — Windows/macOS/Linux portability

- Added an OS-neutral entry point: `python -m emcd_sim`.
- Added PowerShell/Conda/VS Code setup instructions for Windows and portable commands for macOS/Linux.
- Added GitHub Actions Python 3.11 test matrix for Windows, macOS and Linux and a CLI smoke test.
- Added regression coverage for paths with spaces and version consistency.
- No changes to electron diffraction physics or MDFF; quantitative limitations remain unchanged.

# v0.3.1 — Chiral aperture geometry fix

- Corrected 000-centered transverse momentum coordinate for tilted 2BC/3BC EMCD maps (removed erroneous extra incident-tilt subtraction).
- Exact transverse Thales-circle detector centers for 2BC/near-2BC; four physical 3BC apertures and symmetry-correct double difference.
- Added detector overlays and standalone `aperture_geometry.png`, per-aperture spectra, group metadata and focused regression tests.
- Still illustrative: truncated systematic rows, simplified MDFF, no outgoing channeling or SNR optimization.

# Changelog

## 0.2.0 — Ni physical elastic Bloch-wave solver

- Added a neutral-Ni (Z=28) Lobato–Van Dyck 2014 elastic electron scattering-factor implementation.
- Added general independent-atom periodic crystal Fourier factors with optional per-site Debye–Waller B and occupancy, and a physical Fourier-potential adapter.
- Added finite-basis relativistic Bloch-wave elastic propagation with derived beam couplings and ξ200 (no fitted extinction distance in this backend).
- Added systematic-row and Friedel-paired in-plane ZOLZ beam generation; seven-beam Ni systematic row is the default physical reference.
- Switched `emcd-ni` CLI default to `--elastic-backend physical`. Original `--elastic-backend surrogate` is retained for comparison, with `--xi-nm` applying only to the surrogate.
- Added plots and NPZ for each elastic beam's thickness-dependent intensity and a row-order convergence diagnostic.
- Added five physical tests (12 tests total) for form factor, FCC extinctions, DW, Hermiticity/unitarity, ξ200 and exact two-beam Bragg Pendellösung.
- Documented units, modeling assumptions, citations, and remaining outgoing-channeling/MDFF limitations.

This version **does not** validate quantitative EMCD: magnetic L-edge MDFF remains illustrative and the electron does not undergo outgoing channeling after its core-loss event.

## 0.1.0 — Initial proof of concept

- Phenomenological entrance-channeling elastic coupling; illustrative magnetic core-loss MDFF; Ni 3-beam virtual-aperture workflow; bias-to-moment data interface.

## 0.3.0 — Indexed diffraction geometry and patterns

- Added `--diffraction-condition {systematic-row,zone-axis,two-beam,near-2bc,symmetric-3bc}`.
- Added `--diffraction-only` for elastic diffraction without costly illustrative MDFF/EELS integration.
- Added reproducible indexed reciprocal-space diffraction PNG, NPZ and CSV with `(h,k,l)`, nominal `[001]` zone axis, tilt and signed excitation errors.
- Preserved the v0.2 default systematic row, physical Ni elastic solver and existing EELS API.
- The 2BC/3BC presets explicitly state their finite-basis/systematic-row assumptions; diffraction spot broadening is graphical only.
- Added focused tests of s_g, Bragg condition, ±200 symmetry, ZOLZ indexing and elastic conservation.
