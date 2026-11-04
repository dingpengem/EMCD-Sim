# Iteration C ? generalized atomic ionization validation

Date: **2026-11-04**, native Windows source environment.

**GO for review and future bounded research-source integration.** No essential software
merge blocker was found within the declared scope. **Iteration C is not merged or
pushed.** This is not approval of quantitative Fe/Co/Cr EMCD, general convergence,
a Windows package or a new public release.

## Source and accepted-main delivery

|Identity|SHA|
|---|---|
|Accepted A+B main, pushed normally and verified on GitHub|`237944148151d784b6b2e3597e853dbc32779bd0`|
|Accepted A+B no-ff merge retained|`ff894941be0cf790f5644137d6355bfc767f86c8`|
|Iteration C implementation commit|`d37ce887c038a60ca9e38004659a930d2cbad03d`|
|Corrected scientific source, exact complete-suite candidate|**`d754756423e0e907b6d3e194e0d77f99ea44ab1a`**|

Branch: `feat/generalized-atomic-ionization`. Isolated worktree:
`build/generalized-atomic-ionization`, based directly on accepted main.
This report is a subsequent documentation-only commit; the scientific source and
tests remain those of the exact tested commit above.

Before pushing main, its worktree was clean and the accepted scientific source and
merge-readiness report were intact. Fetch showed remote main at the expected ancestor
`2f9c130099dce5df4e4609b521c42f53c5385518`, with no unexpected divergence. A normal
`git push origin main` succeeded, followed by fetch/SHA comparison. A later live
`git ls-remote origin refs/heads/main` again returned exactly `2379441...`.
No force push, version change, tag or release occurred. The accepted main worktree,
previous feature branch and historical worktrees remain intact.

## Mathematical implementation and scope

See [model, parameters, units and workflow](GENERALIZED_ATOMIC_IONIZATION.md) and
the [fully declared synthetic Fe fixture](examples/synthetic_fe_atomic_parameters.json).

- Shared core 2p spin-orbit states, CG coefficients, complex Cartesian dipoles,
  cubic orbitals and radial helpers alias the historical implementation; its source
  remains unchanged. Material parameters are a separate mandatory dataclass/JSON schema.
- Each cubic final orbital coherently combines its spherical-d components. Distinct
  core/final events add incoherently as `T(E)=sum w d d? Gaussian(E-E_t,sigma)`.
  Dipoles are `<core|r|final>` in Angstrom; tensors are Angstrom?/eV. The positive
  hole weights construct Hermitian PSD tensors without clipping.
- Reversal swaps spin-resolved holes and reverses exchange shifts in the fixed
  core-SOC basis. Both states are independently generated and stored, with their
  shared even tensor. Born `I=ReTr(RT)`, angular `Q=2*pi*g`, ionization-site phases,
  depth normalization and Single/Double BW/MS kernels are unchanged.
- Required declarations include matching ASE symbol/Z (Sc?Zn), L3/L2 reference
  energies, effective radial integral and its source, cubic basis/10Dq, exchange,
  five up/down hole pairs, local axis, proper crystal frame, Gaussian sigma,
  provenance, validity and synthetic/unvalidated status. There are no material presets.
- Only the aligned local +z spin/cubic model and explicit proper rigid-frame rotations
  are supported. Arbitrary spin rotation relative to a fixed anisotropic field,
  other crystal-field parameterizations and multi-element/site-resolved ionization
  are explicitly outside this implementation.
- A strict parameter JSON generates an explicit imported-tensor source, through the
  existing GUI imported-source panel or CLI. Existing Ni panels/projects are not
  migrated. The existing generalized pipeline consumes the source, avoiding a second
  propagation/contraction implementation.

## Exact validation results

|Run|Passed|Skipped|Failures/errors|Time|
|---|---:|---:|---:|---:|
|Corrected focused atomic + GUI + Ni + source/reference suite|70|0|0 / 0|32.34 s|
|Complete Windows source suite, exact clean `d754756...` (786 tests)|747|39|0 / 0|651.13 s|

The full run exited 0 and retained **1069 warnings**, including Qt deprecations,
small offscreen-layout warnings and deliberate invalid-input overflow warnings.
Warnings were not suppressed or counted as scientific validation. The initial
`d37ce88...` full run was deliberately interrupted for the GUI state fix; it is
not acceptance evidence. The corrected run completed in full.

Windows environment: existing `build/windows-rc/venv/Scripts/python.exe`, Python 3.11,
NumPy/SciPy/ASE/PySide6; `PYTHONPATH=src`, `QT_QPA_PLATFORM=offscreen`,
`OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, pytest cache disabled and a 180 s
faulthandler diagnostic. Real external-table, protected 160-array and genuine
historical-project paths were supplied read-only. No missing historical study was
regenerated. This was native Windows Python/Qt source regression, **not an EXE build
or packaged-binary acceptance**. No Linux/macOS CI investigation was performed.

Local untracked evidence is retained under this worktree's ignored `outputs/`:

- `atomic-focus-corrected.log` / `.xml`
- `atomic-windows-corrected.log` / `.xml`
- `atomic-full-corrected-source.txt`
- `cli_synthetic_fe_atomic_tensor.json`
- `iteration-c-proposed.patch`

### Required scientific and workflow checks

|Requirement|Observed result|
|---|---|
|Historical Ni event/tensor regression|Exact array equality for default and nondefault Ni configurations, both reversal signs: energies, complex amplitudes, hole weights, edge labels and broadened tensors.|
|Historical Ni end-to-end compatibility|Original XMCD/atomic ? Single/Double, each BW and MS: exact numerical-array equality against immutable pre-feature source; protected 160-array archive passes.|
|Genuine historical project|Retains Lobato and archived elastic-control agreement within the existing 2e-12 criterion; source/data not migrated or regenerated.|
|Independent dipole algebra|60 core/spin/final-m combinations compared to direct spherical-harmonic sphere quadrature; independent L.S operator eigenstates, normalization and orthogonality pass.|
|Reversal and spin|Explicit opposite states, shared even response, conjugation relation for this real cubic model and spin-symmetric/zero-exchange nonmagnetic limit pass. No such conjugation assumption is imposed on general imported tensors.|
|Hermiticity/PSD/nonnegative EELS|Tensors pass Hermiticity/eigenvalue checks; all tested four-state detector EELS spectra are finite and nonnegative for both solvers and channeling modes.|
|Transition strength|Full-hole shell sum is 4*r?; sampled integrated trace agrees with weighted event strength to the test's 1e-12 relative tolerance. Doubling the radial integral doubles amplitudes.|
|Unsupported parameters|Missing declarations, mismatched element/Z, noninteger Z, invalid energies, nonnumeric/nonfinite/complex values, holes, basis, axis, improper frame, status/provenance and unsupported tiny radial scales are rejected.|
|Source integrity|Original UTF-8 input/hash is embedded; imports regenerate the atomic tensors and verify parameter/frame/edge/status consistency. Checksum, parameter, tensor, frame and model tampering is rejected.|
|GUI/projects|Generation, validation, actual worker calculation, save/open, embedded provenance, missing-source/read-only restoration and conservative Ni gates pass. Failed generation clears prior source validation/acknowledgement, rather than leaving an older tensor eligible.|
|CLI/documentation|Documented synthetic example generates and validates successfully. All local Markdown links in modified documentation resolve.|

### Synthetic Fe BW/MS checks

These are **original synthetic software-test numbers, not measured/fitted Fe
constants and not Ni electronic parameters assigned to Fe**. The committed fixture
fully declares them and their nonphysical provenance. The finite BCC geometry is
only a propagation/indexing test structure, not a physical comparison dataset.

Settings: BCC a=2.866 Angstrom, [001], target (110), tilts (-5,7) mrad, 200 kV,
0.2 nm; beam/potential cutoffs 0.6/1.2 Angstrom^-1, 9 depth points, 9x9 maps,
8 detector subpixels, 16x16 FFT mesh, 0.01 nm slice step; selected 710/723 eV.
The **I_A_plus two-energy spectrum L2 relative norm difference** is:

|Channeling model|BW/MS relative difference|
|---|---:|
|Single|0.0006396961091371369 = **0.06397%**|
|Double|0.0012815790733429451 = **0.12816%**|

These limited settings establish consistency only for the tested finite case.
There is no general detector/depth/beam/FFT convergence or physical accuracy claim.
The previous A+B approximately **1.6% detector-refinement sensitivity** remains a
known limitation; this milestone does not remove it.

### Full-suite skips (not passes)

|Count|Reason|
|---:|---|
|3|Full benchmark outputs are not complete|
|3|Full checkpointed thickness calculation still incomplete|
|3|Local MS validation outputs not generated|
|2|Local four-point benchmark not generated|
|1|Local legacy reference project unavailable|
|8|Optional GUI and existing real Stage D results required|
|1|Optional historical saved project is unavailable|
|1|Optional local WIEN2k companion audit; original files are not distributed with the package|
|1|Optional real saved Ni project unavailable|
|1|Optional saved GUI reference unavailable|
|6|Optional saved angular references unavailable|
|1|Optional saved benchmark unavailable|
|1|Optional saved result fixture unavailable|
|1|Optional stored GUI reference|
|1|Pinned offline HDF5 inputs unavailable|
|1|Requires original local WIEN2k audit companions; not distributed|
|1|Saved BW/MS fixture not available; never run a fallback simulation|
|3|Saved project fixture unavailable|

The 39 skips concern optional stored/benchmark/WIEN2k/offline-HDF5 evidence. Required
new atomic tests, real external-table workflow, protected-array and supplied genuine
historical-project checks ran. No fallback simulations replaced unavailable evidence.

## Compatibility, redistribution and remaining limitations

Canonical source comparison against accepted main confirms no changes to historical
`ni_local_mdff.py`, `gui/emcd_forward.py`, `mdff_tensor.py`, Single/Double channeling
kernels, elastic IAM providers/defaults, coefficients, version/packaging, historical
research data, figure assets or earlier immutable physics/unit/source manifests.
Iteration C has a separately pinned reviewed source-scope manifest; earlier evidence
was preserved rather than regenerated or silently whitelisted.

The original synthetic parameter fixture introduces no external material dataset.
No unlicensed legacy elastic table was added. Existing Apache-2.0 coefficient notices
and repository licensing remain unchanged. Source checksum integrity does not
authenticate material truth, authorship, experimental accuracy or redistribution
rights of any future user-supplied radial/MDFF dataset.

**No essential software merge blocker remains for this declared research scope.**
Before quantitative material EMCD, independent physical sources/validation are still
needed for radial functions/integrals, core energies, occupations, crystal/exchange
splittings, orientation assumptions and broadening. The independent-electron dipole
model omits multiplets, core-hole/charge-transfer effects, band/final-state SOC physics,
self-consistent material electronic structure, non-dipole response and absolute
cross-section/experimental handedness calibration. AFM/SDW, arbitrary spin-field
orientation, noncubic fields and multi-element/site-resolved ionization remain unsupported.
GUI configuration uses fully declared JSON, not automatic element presets.

No Iteration C merge/push, EXE publication, public version change, tag, release or
multi-element development was performed. The source is ready for review within these
bounds, and **not a quantitative Fe EMCD or public-binary acceptance**.

## Changed feature files

- `README.md`
- `docs/GENERALIZED_ATOMIC_IONIZATION.md`
- `docs/GENERALIZED_ATOMIC_IONIZATION_VALIDATION.md`
- `docs/GENERALIZED_SINGLE_ELEMENT_EMCD_DESIGN.md`
- `docs/examples/synthetic_fe_atomic_parameters.json`
- `src/emcd_sim/atomic_ionization.py`
- `src/emcd_sim/gui/imported_tensor_ui.py`
- `src/emcd_sim/gui/results.py`
- `src/emcd_sim/imported_mdff.py`
- `tests/fixtures/atomic_ionization_scope_v1.json`
- `tests/single_element_source_guard.py`
- `tests/test_atomic_ionization.py`
- `tests/test_generalized_xmcd_atomic.py`
