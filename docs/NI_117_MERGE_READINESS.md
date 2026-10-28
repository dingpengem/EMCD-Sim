# Ni [117] merge-readiness review

Reviewed locally on 2026-10-27, branch `feat/ni-117-emcd`, based on main
`236893392838ab5bc17dcf1848fd127009f2f048`. This review does not merge, push,
tag, release or rebuild an executable. The subsequent generalized-multislice
milestone will use a separate branch from this reviewed baseline.

## Outcome and scope

**Ready for reviewed, opt-in research integration. No blocking issue remains
in the tested [117] scope.** This is not a claim of arbitrary-zone support,
global numerical convergence, genuine DFT MDFF or calibrated experimental
accuracy. The [scientific diagnosis](NI_117_EMCD_VALIDATION.md) and
[final validation](NI_117_FINAL_SYMMETRY_VALIDATION.md) remain authoritative
about the physical interpretation and representative numerical limits.

Supported combinations are Ni [117] / (2,-2,0), explicit ideal incoming/outgoing
000+target or full finite ZOLZ, BW/MS, Single/Double. Right-handed geometry,
signed indexing, target Bragg alignment and the actual projected IAM potential
are consistent. Crystal-frame [001] reversal and one tensor rotation preserve
the physically permitted mirror-even magnetic contribution. No MDFF,
Coulomb factor, outgoing-energy convention or Single/Double definition changed.

## Review findings and corrections

| Finding | Correction / disposition |
|---|---|
| Cutoff warning only visible for MS | Off-row support and coarse-sampling warnings now apply to BW, MS and Both. No numerical settings are changed. |
| Missing/invalid saved [117] frame could pass input-reuse guard | View remains available; missing, malformed, nonfinite or earlier frames block reuse of orientation-dependent inputs. [001]/[017] behavior is preserved. |
| Automatic unsupported-zone retry used an obsolete error substring | Fatal no-fallback errors now stop after one capability check rather than retrying all FFT sizes. |
| A provenance test depended on untracked WIEN2k companions | The actual-file audit runs locally and explicitly skips when original companions are unavailable. No licensed data or fabricated metadata is distributed. |
| Old whole-class AST assertion prohibited the intentional opt-in FFT extension | Unchanged MDFF/kinematic/persistence AST guards remain; default-path behavior is protected by strict archived-code array tests for [001] and [017]. |
| Redundant research-driver imports | Removed unused imports only; retained the bounded checkpoint/reproduction and analytical drivers. |
| Local-only figure embeds would break after source integration | Eight deliberately tracked compressed previews, about1.6 MB total, have original-image hashes. Large numerical outputs and originals remain excluded. |

The new two-beam kick is the FFT-sampled projected `exp(i dz PVP)`, not a
lossy crop of full propagation, BW eigenmode propagation, or a normalization
of truncated coefficients. The full FFT path retains its existing arithmetic.
The generic old [117] frame was proper but not target-aligned; it is not
retroactively labeled a physical defect. Old/new covariant calculations agree.
The exact historical figure remains unrecovered.

## Tests against reviewed code

| Check | Result |
|---|---|
| All tracked regression tests plus three new [117] test files | **472 passed**, 442.45 s |
| Final focused geometry, science, GUI, settings and project suite | **87 passed**, 33.25 s; includes final warning/frame/fail-fast corrections |
| Targeted revised AST guard and archived [001] default-FFT comparison | **2 passed** |
| Clean-source copy with tracked XMCD only, no private companions | **8 passed, 1 explicitly skipped** (optional WIEN2k audit) |
| Fresh reviewed-code [001]/[017], BW/MS, Single/Double small control | **344 arrays bit-for-bit identical** to archived reference |
| Protected source/results hash audit | **323 files unchanged**, including204 production checkpoints and50 original [117] NPZ/JSON pairs |
| Native Windows launcher `python -m emcd_sim.gui --help` | Passed |
| Python source compile and Windows `.spec` syntax check | Passed; no packaging executed |
| Dependencies, version, packaging changes | None |

The first focused pass exposed the obsolete AST assertion (85 passed, one
failure); it was corrected with explicit archived-code coverage, not by changing
physics or tolerances. Broader tests report dependency deprecation/headless
Matplotlib layout warnings; there were no numerical failures or native crashes.
The clean-copy test also reports an unwritable pytest-cache warning; test and
source functionality pass. These Windows checks are not a new clean-machine
installer or a cross-platform release acceptance.

Logs and fresh array/hash evidence are in `outputs/ni_117_merge_review/` and
`outputs/ni_117_final_symmetry_validation/review_regression_tests.log`.
The scientific baseline remains72 matched/joint checks and four finer-aperture
checks passing, with failed coarse-aperture checks explicitly retained.

The working Ni XMCD file has a **pre-existing trailing-newline/line-ending
difference** from Git. Its numeric table is bit-for-bit equal to the tracked
table. It and all private companion files are left untouched and unstaged.
Protected [117] and production results are not regenerated to pass tests.

## Files and integration boundary

- `ni_117_geometry.py`, `mirror_parity.py`: reusable Ni research geometry and
  raw-map diagnostics; no forced antisymmetry.
- `multislice_double_channeling.py`: opt-in closed two-beam FFT convolution;
  independent full-field propagation preserved.
- GUI geometry/propagation/channeling: consistent orientation, exact common
  hkl support, independent BW/MS and incoming/outgoing handling.
- GUI settings/project/browser: basis serialization, source-specific guard,
  no-fallback validation and solver-independent warnings.
- Tests: signed indices, metric/Bragg, tensor covariance, parity, projected
  support, resource/UI/project checks and frozen legacy arrays.
- Scientific drivers/reports: reproducibility and bounded numerical evidence;
  no production scan or runtime dependence on research scripts.
- README, user guide, architecture note, changelog and preview images: explain
  setup and limits without changing the package version or released artifacts.

Saved project schema1 remains readable by this implementation; old [117]
frames are not silently reinterpreted. Forward compatibility with older
executables that lack new settings is not promised. Published EXE/ZIP files
are unchanged. New runtime imports are static and use existing dependencies;
the existing PyInstaller analysis can discover them without new hidden imports.

## Remaining issues and recommendation

**Blocking:** none within the reviewed, opt-in Ni [117] scope.

**Non-blocking:** representative convergence is not uniform full-parameter
certification at12/30 nm or across a tilt/thickness surface. The default2.5
potential lacks off-row [117] terms. Coarse grids fail, including0.2296 pp at
30 nm for17 versus97. Warnings and documentation must accompany integration;
they are not replaced by global default increases. Local output archives are
not included in the source checkout; previews and reproducibility instructions
are included. The exact historical figure and complete original electronic
state/build provenance remain unavailable.

**Future work:** orientation-independent geometry/potential providers, atomic
3D propagation and independently validated site-aware coupling, broader
convergence, genuine complex DFT MDFF and experimental calibration. These are
not silently added to this review. The orientation-specific [017]/[117]
providers are acceptable here as validated references; the newly requested
generalized architecture must remove their production/GUI dependencies on its
own branch after numerical equivalence is demonstrated.

Recommend integration only after explicit review/approval of the tested
research scope. No main merge, push, release, tag or Windows rebuild is authorized
or performed by this record.
