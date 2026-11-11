# Native macOS ARM64 local development candidate

Date: 2026-11-10, America/Los_Angeles. This is a local research candidate, not a
published, notarized, certified, or quantitatively calibrated release.

## Source and environment

Baseline: `ef81576e2692c2c826bfbe2b89f21e00b05936e4`, v0.9.0-beta.1.
Branch: `feat/macos-arm64-gui`. The original `main` checkout at
`1c5a01109e781c8accd458e2f5ebb60afdda144d` and its scientific outputs were preserved.
The isolated worktree is `outputs/macos-arm64-development-20261110` under the
original checkout. `/private/tmp/EMCD-Sim-macos-arm64` remains a symlink to it,
preserving earlier development-environment and evidence paths.

| Component | Observed version |
|---|---|
| macOS / hardware | 26.3.1 (25D2128), ARM64, 10 logical CPUs |
| Dedicated venv Python | CPython 3.11.16, ARM64 |
| NumPy / SciPy | 2.4.6 / 1.17.1 |
| PySide6 / Qt | 6.12.0 / 6.12.0 |
| Matplotlib / ASE / spglib | 3.11.2 / 3.29.0 / 2.7.0 |
| PyInstaller / hooks | 6.22.3 / 2026.10 |
| Xcode / Apple clang | 16.4 (16F6) / 17.0.0 |
| BLAS/LAPACK | Apple Accelerate, from these platform wheels |

All primary dependency pins match `packaging/requirements-windows.txt`.
The Windows wheels use a different native BLAS backend; equal Python package
versions do not imply identical operating-system numerical libraries. Full
installed dependencies pass `pip check`; the build stores a dependency freeze.
Early checks used these same official ARM64/universal2 wheels in an isolated
preflight import directory while the large optional Qt components downloaded.
Final source/build checks use the fully installed dedicated `.venv-macos`.

## Compatibility corrections

- macOS writable data, preferences, default workspace and logs use
  `~/Library/Application Support/EMCD-Sim`. Windows retains LOCALAPPDATA.
- Memory admission uses current Mach VM pages and libproc current RSS on macOS,
  retaining the existing budget, margins and rejection policy. Available RAM is
  conservatively free plus inactive pages; speculative pages are not counted twice.
- Accelerate BLAS/LAPACK is limited and restored through Apple's macOS 15+
  thread-local API in both calculation and detector executor threads. Native
  success, exceptions and concurrent eigensolver dispatch were checked. macOS
  OpenBLAS dylib discovery was added but is NOT TESTED with an OpenBLAS Mac build.
- A separate macOS PyInstaller spec and launcher reuse the shared Qt application,
  workers, kernels, resources and project schemas. No Windows packaging changed.

No physics formula, MDFF convention, source-frame/reversal validation, production
sampling default, beam count, worker request or project schema was changed.
Apple's threading API is documented at
[BLASSetThreading](https://developer.apple.com/documentation/accelerate/blassetthreading(_:)).
This candidate requires macOS 15 or newer; this host is macOS 26.3.1.

## Observed native acceptance

PASS means an observed workflow completed; INCOMPLETE / NOT TESTED means it has
no corresponding completed evidence. Tests use explicit bounded diagnostic
settings, not original-size workload benchmarks. Ni uses the bundled 3.520 Å CIF
and repository XMCD. Fe3O4 uses the actual 56-atom inverse-spinel fixture. Ordered
56-atom NiFe2O4 is generated with the existing benchmark's B-site ordering and
round-tripped through CIF; it is not the seven-atom catalogue fixture. Cr is the
existing idealized two-site BCC construction. Cr atomic and ferrite/magnetite
manual tensors are software examples, not experimental spectroscopy validation.

| Workflow | Final installed source | Relocated delivery .app |
|---|---|---|
| Native Cocoa GUI, seven settings sections, menus and resizing | PASS | PASS |
| CIF import, original membership, crystallographic grouping and 3D viewer | PASS | PASS |
| Ni Global XMCD, BW Single, selected energies, maps/spectra/export | PASS | PASS |
| Ni Local XMCD, site-group binding and calculation | PASS | PASS |
| Two-run comparison, save/reopen and equivalent recalculation | PASS | PASS |
| Fe3O4 8a/16d/32e groups, Fe(A)/Fe(B), oxygen elastic-only | PASS | PASS |
| Fe3O4 bounded synthetic Local calculation and group results | PASS | PASS |
| Cr manual magnetic subgroups, opposite directions, Local Atomic | PASS | PASS |
| Cr BW/MS Single and Double, two BW detector threads, reversal identities | PASS | PASS |
| NiFe2O4 full ordered membership, independent Fe/Ni windows and providers | PASS | PASS |
| Total/element/group contribution/group mean/group comparison rendering | PASS | PASS |
| PNG/SVG and numerical exports, source validation after reopening | PASS | PASS |
| Multiple calculations/project, stale thickness edit and exact revert | PASS | PASS |
| Uninstrumented real Double worker cancellation, prior arrays/history retained | PASS | PASS |
| Ni BW/MS combined comparison and completed detector-only spectrum | PASS | PASS |

The two-worker Cr run records two distinct thread IDs, maximum concurrency two,
and verified single-thread Accelerate inside execution. Cancellation was requested
after 100 ms during real Double work; prior saved arrays/history remained intact.

Evidence is in `build/macos-validation` in the worktree:
`source-final/acceptance.json` (12 cases, including cancellation),
`source-05/acceptance.json`, `bundle-preflight/acceptance.json`,
`bundle-final-relocated/acceptance.json` (12 cases),
`final-source-frozen-comparison.json`, `reversal-group-checks.json`,
`cancellation-source/acceptance.json`, screenshots,
NPZ/CSV exports and fresh per-material projects. Earlier `source-01` through
`source-04` preserve partial diagnostics: a native retention-sheet wait and an
invalid magnetite 200/two-beam diagnostic. The corrected profile uses 400, as the
existing benchmark does. These were diagnostic setup failures, not kernel fixes.
Native file-dialog paths are injected; calculations and numerical arrays are real.
The final driver deselects history before starting each new run, using the normal
GUI workflow that retains a new calculation without a replacement prompt.

## Numerical comparison

PASS: 1,588 numeric arrays across all twelve final installed-source/relocated-app cases
were compared, including diffraction amplitudes, selected spectra, angular maps,
even/odd and group-resolved data. All were identical on this host (maximum
absolute difference zero). The acceptance criterion was rtol `2e-10`, with an
absolute floor `2e-12` times the archive's raw-intensity scale for cancellation-
sensitive signals; non-intensity archives use their numeric scale. Save/reopen
also preserves numerical fingerprints exactly. Ni recalculation and reversal
identities passed separately. Nonzero Cr group-odd signals (about `6.84e-8`)
reverse individually while even signals persist and the opposite AFM groups cancel
in the total; both source and relocated app passed these nontrivial group checks.

INCOMPLETE: matching Windows v0.9.0-beta.1 arrays/projects were not supplied.
Historical repository diffraction evidence predates the exact release and is
not relabeled as current cross-platform EMCD validation. No Windows/macOS
scientific-equivalence certification or bitwise cross-platform expectation is
claimed. No discrepancy was observed in the completed source/frozen comparisons.

## Focused tests and unresolved test contracts

- PASS: initial resource group, 40 passed / 1 Windows-specific skip.
- PASS: 31 native crystallography/MDFF transaction/GUI worker checks completed in
  the focused batch before its modal wait; these include four AFM BW/MS
  Single/Double comparisons with the production programmatic API.
- FAIL: a follow-up legacy eight-case batch had 3 passed, 4 failed, 1 Windows-only
  skip (four already-completed AFM parameterizations deselected). Two tests omit
  required Global MDFF acceptance; one expects an older unsupported post-edge
  gate; one timed out around a native retention prompt. These assumptions concern
  unchanged release GUI code. The scientific validation was not relaxed and
  old tests/reference values were not rewritten to force a pass. The attempted
  test-specific retention workaround was removed from the delivered test file.
- The resource test now explicitly accepts its Material MDFF draft and cleans up
  its disposable project. Path tests explicitly distinguish Windows and macOS;
  native tests verify real memory APIs and Accelerate restoration.
- Final installed-environment resource group: PASS, 40 passed / 1 Windows-only skip.

No full regression was run. Manual trackpad/keyboard ergonomics, native file picker
interaction, retention/replacement sheets and exhaustive plot-legend interactions
remain INCOMPLETE / NOT TESTED by a human. Independent clean-Mac installation,
a genuine Windows-created project and Windows numerical comparison are NOT TESTED.
Qt/macOS IMK/TSM and Matplotlib constrained-layout diagnostics occurred during some
hidden/compact redraws; completed screenshots/exports and workers remained usable.
General convergence, finite-ZOLZ/projected-IAM/localized-ionization approximations,
uncalibrated synthetic Fe/Cr/ferrite spectra, no magnetic-order inference, and no
general unsupported tensor rotation remain the release's scientific limitations.

## Bundle and modified files

The preflight `.app` launched through `open` (LaunchServices), completed a native
diffraction preview and all ten scientific cases without source-path imports.
Its 245 Mach-O files support ARM64; no Windows DLLs/executables were found.
Python, Qt Cocoa, NumPy/SciPy, ASE/spglib, Matplotlib, scientific tables, edge data,
Ni XMCD, CIF examples and runtime license notices are collected. The final full-
environment bundle and moved-app launch also passed, as recorded below.
Signing is local ad-hoc only; TeamIdentifier is absent. No Developer ID,
notarization, publishing, pushing, tagging or Windows artifact modification.

Modified production files:
`src/emcd_sim/gui/{runtime,memory_budget,parallel_resources,channeling}.py`.
New packaging files: `packaging/{build_macos.sh,emcd_macos.spec,launcher_macos.py,
macos_acceptance.py,check_macos_bundle.py,requirements-macos.txt}`.
Focused tests: `tests/{test_gui_stage_e,test_memory_budget,test_parallel_resources,
test_macos_runtime}.py` (last is new). Also `.gitignore`, this report and
`docs/INSTALL_MACOS.md`.

## Final candidate

- PASS: application built from clean commit
  `a96f24203c3631761031cb072ff87b2a65b2fdee` on `feat/macos-arm64-gui`.
  The subsequent documentation-only commit records these final observations;
  it does not change application code or bundle contents.
- PASS: original final app launched graphically through LaunchServices and
  completed a real diffraction preview (`final-original-launch.png`).
- PASS: the entire app was copied with `ditto` to a different writable directory,
  then launched with `open -n -W` and completed all 12 native scientific cases,
  save/reopen/export, BW/MS comparison, detector-only spectra and cancellation.
- PASS: 246 Mach-O files contain ARM64; no Windows binaries; required resources
  and Python/PyInstaller/native-library license notices are present.
- PASS: deep/strict ad-hoc signature verification before and after execution.
- PASS: all 1,588 compared source/frozen arrays identical, maximum difference zero.
- Final app: `outputs/macos-arm64-candidate-20261110/EMCD-Sim.app` under the original
  checkout. Development build: `build/macos-arm64-final/dist/EMCD-Sim.app` in this
  worktree. All evidence lives in `build/macos-validation` in this worktree.
- Rebuild using a fresh destination:
  `bash packaging/build_macos.sh "$PWD/build/macos-arm64-rebuild"`.
  Actual resolved packages: `build/macos-arm64-final/dependencies.txt`.
- Functional acceptance is bounded and automated. Full human workflow parity,
  Windows numerical/project compatibility, independent clean-Mac installation,
  and the four legacy test failures described above remain INCOMPLETE / FAIL
  as specifically identified. No scientific parity certification is claimed.
