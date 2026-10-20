# GUI and performance integration

This milestone integrates development source after the published v0.6.1-beta.1. The existing release, tag, version and ZIP remain unchanged. The new Windows package is a **local development build**, not a published release. Installation and project/export instructions are in [Windows installation](INSTALL_WINDOWS.md#local-windows-development-build) and the [User Manual](USER_GUIDE.md).

## Features and ancestry

Inspection after fetching main established a linear history, rather than assuming branch independence. `integration/gui-performance-update` was created from `origin/main` at `f1b025f9970af8aad13e04df0f4b2920192fc2c7` and fast-forwarded to the validated development tip. No cherry-picks or duplicate merges were necessary:

| Commit | Change |
| --- | --- |
| `f1b025f` | Shared versus solver-specific settings, already on main |
| `6145b2c` | Automatic / Manual settings and saved-setting provenance |
| `619a196` | Reversible diffraction full-basis view, with stale-geometry invalidation |
| `c15581a` | Energy-dependent exact angular support scheduling |
| `39aafb6` | Optional external MS Double profiling tools |
| `3a866ac` | Private MS Double FFT outputs and event-buffer reuse |

Automatic uses configuration checks without trial solves. Strict reference matching is distinguished from starting settings; neither guarantees universal convergence. Manual overrides and explicit legacy values are retained. New projects use 97 x 97 angular sampling and a 2048 MiB process budget. MS FFT/slice settings remain distinct from shared reciprocal support and potential cutoff. Both solvers retain the reciprocal-space MDFF formulation.

The scheduler evaluates complete selected L3/L2 fields and the exact nonzero A/B weight union elsewhere, retaining every requested energy without interpolation. All BW/MS Single/Double/Both paths, fractional integration, raw data, display modes, checkpointing and cancellation remain supported. MS optimization retains complex128/float64 arithmetic, adjoint propagation, outgoing energy, quadrature, site averaging and norm/leakage diagnostics. Working arrays belong to each call/batch, not shared global scratch.

## Numerical evidence and performance

The [scheduling study](ENERGY_ANGULAR_SAMPLING_PERFORMANCE.md) measured three-energy 300 kV, 8 nm Double times of BW 23.41→15.35 s and MS 134.23→80.32 s, with bitwise-identical saved observables. The [buffer study](MS_DOUBLE_BUFFER_OPTIMIZATION.md) measured MS outgoing-field time of 40.61→36.61 s at 8 nm and 41.58→37.91 s at 30 nm for the same 300 kV Ni [017], FFT 32, 64 depth nodes, maximum slice step 0.5 nm and 97 x 97 L3 field. Complete complex responses, raw states, maps, percentages and per-batch diagnostic distributions were bitwise identical. These are separate matched benchmarks, not guaranteed full-spectrum or total GUI speedups.

Integration exposed a checkpoint-audit assumption that all accepted MS implementations must have identical ASTs. Its narrowly pinned equivalence now accepts only the validated pre/post-buffer revisions after verifying the older default path. Unknown optimized-code changes still fail closed; physical parameter comparison and all numerical gates are unchanged. The audit records this distinction rather than claiming AST identity for the optimized implementation. No production scan was rerun.

Two older GUI regression cases now explicitly select Manual before overriding energy/grid parameters. Their numerical and admission assertions remain unchanged; dedicated Automatic tests cover the new default behavior separately.

## Validation and provenance

The integration checks use saved results whenever possible. The extended packaged acceptance harness checks Automatic/Manual controls, BW/MS/Both visibility, actual defaults, reversible view limits, raw/percentage modes, full-field rendering/overlays, numerical and figure exports, save/reopen and immutable arrays, with forward routines guarded against invocation. Reports record the executable path, PID, frozen status and embedded build identity to distinguish the tested process from older GUI instances.

Focused integration checks passed **156 tests**, followed by **19** legacy GUI tests after their explicit Manual setup was corrected. The fresh full available suite passed **527 tests, zero failures/errors/skips**, with 33 Matplotlib/Qt warnings, in **414.03 s**. This includes **525 tracked tests and two untouched, untracked local user tests**; those local files are not included in the integration commit. Logs and JUnit XML are under `outputs/gui_performance_integration/` (`focused_final`, `legacy_controls`, `full_final`). Saved BW/MS Single/Double source-GUI acceptance passed with zero forward calls and unchanged arrays. All **204 production checkpoints remain byte-identical**; the published ZIP retains SHA256 `9fd5e71437d2c26d4595abb7adde9436e4c333ce18f3a57cf381b0c541bfd94f`. Documentation checks cover 169 relative links including anchors.

Frozen acceptance and exact build identity are recorded below after packaging. Generated evidence and packages are excluded from Git. The package is built from a committed, clean isolated worktree, preserving unrelated modified Ni data and untracked experiments in the user's worktree. Its bundled spectrum is the repository-tracked example, not private WIEN2k companions.

## Build and scientific scope

The existing PyInstaller workflow produces `build/windows-main-dev/dist/EMCD-Sim/EMCD-Sim.exe` and `build/windows-main-dev/EMCD-Sim-main-dev-<source-short-SHA>-Windows.zip`. The complete archive contains the `EMCD-Sim/` directory and `_internal` runtime. `build_manifest.json`, external `SHA256SUMS.txt` and embedded `_internal/build_info.json` record commit, timestamp, Python/dependency versions and file/source hashes. The package version stays `0.6.1b1`; its development label and source commit distinguish it from the published Beta.

Acceptance is on the development Windows host, not an independent clean machine. The effective XMCD-constrained MDFF is incomplete as a DFT-derived description; elastic propagation uses projected IAM potentials. Convergence evidence is limited to tested configurations, and arbitrary-unit EELS lacks count/dose calibration or experimental SNR. Native calculated energies are not absolute experimental calibration. No voltage/thickness scans, model refits or GUI physics changes form part of this integration. The full-basis toggle is reversible; large fields can still require scrolling or viewer maximization. Unsigned Windows distribution and unsupported arbitrary-material FFT geometries remain limitations.
