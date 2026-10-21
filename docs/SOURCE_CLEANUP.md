# Source-package cleanup

Branch: `cleanup/source-package`. Baseline: local main
`f427992cf0523423fbeb794e0a22a82480a2be07`, which includes the previously validated
3.2/2.5 cutoff-default update on top of latest remote main `8b0c496`.
No unrelated working data or untracked user scripts are included in this cleanup.

## Inventory and decisions

The original `src/` contains **83 Python files**, all under `src/emcd_sim/`.
After relocation it contains **78**. The [complete module inventory](SOURCE_MODULE_INVENTORY.csv)
classifies every original file, records internal imports/callers and textual
references, and explains its disposition. Categories: **69 core/API modules
retained; 14 active research modules, of which five moved and nine retained**.
There are no proven-obsolete deletions and no modules classified solely by a lack
of static callers. No compatibility wrappers or placeholder production modules
were introduced.

The audit parsed every Python module, including function-local imports, checked
the transitive closure from the public package, all GUI modules and all 12
declared console entry points, and searched source, tests, scripts, examples,
documentation, pyproject, packaging and workflows. Dynamic-import scanning found
the research driver's `__import__('platform')`, an external standard-library
import, not a hidden internal module. Existing importlib/spec-loading uses in
tests and scripts and the PyInstaller hidden-import list were inspected separately.
`gui/__main__.py` intentionally launches the application on import; it was checked
statically rather than imported as an ordinary library. Historical data metadata
and old release records are provenance, not instructions to regenerate results.

## Relocated drivers

| Original module under `src/emcd_sim/` | New location | Reason |
| --- | --- | --- |
| `atomic_slicing_diagnostics.py` | `scripts/research/atomic_slicing_diagnostics.py` | Standalone P1 geometry exporter; only its direct diagnostic test and documented command depend on it. Reusable atomic geometry remains in the package. |
| `fractional_aperture_validation.py` | `scripts/research/fractional_aperture_validation.py` | Focused study frontend; no production/API callers. Shared aperture integration and BW/MS engines remain in the package. |
| `ni_017_comparison.py` | `scripts/research/ni_017_comparison.py` | Repository-checkpoint comparison frontend with no incoming production dependency. Shared orientation, tensor and mistilt helpers remain. |
| `plot_wien2k_xmcd.py` | `scripts/research/plot_wien2k_xmcd.py` | Standalone spectrum plotting command, not an exported API or installed console script. |
| `plot_wien2k_xmcd_suite.py` | `scripts/research/plot_wien2k_xmcd_suite.py` | Standalone figure generator. The existing conditional/manual workflow now invokes its repository path. |

Use `python scripts/research/<name>.py` from the repository root after installing
the package. The old `python -m emcd_sim.<name>` commands for these five drivers
are replaced, without shims. [Research-driver instructions](../scripts/research/README.md)
give supported help commands; the [017]/[710] comparison has no help parser and
executing it runs the original calculation. The atomic diagnostic test loads the
script explicitly by file path; no runtime search-path manipulation is needed.

Only imports, invocation documentation and the dependent test/workflow paths
changed. AST comparisons confirm that all **17 top-level function/class bodies** in the
five relocated drivers are unchanged, including signatures. Their relative
package imports became absolute `emcd_sim` imports. The P1 exporter's repository
root calculation still uses the same `parents[2]` depth after relocation; future
exports naturally record the relocated driver's own new source hash.

## Files deliberately retained

All 69 core/API files remain byte-for-byte unchanged in Git, including the BW
Hamiltonian, FFT propagators, single/double-channeling contractions, MDFF and
XMCD sources, detector/integration code, cancellation, worker-safety policies and
all GUI code. Public `__init__` exports, pyproject entry points and the PyInstaller
specification are unchanged. `atomic_multislice_geometry.py` remains a reusable,
tested scientific API rather than moving with its diagnostic exporter.

The nine retained research modules are `ni_017_high_mistilt_xy`,
`ni_017_high_mistilt_analysis`, `ni_017_high_mistilt_convergence`,
`ni_017_high_mistilt_plots`, `ni_017_mistilt`, `ni_710_mistilt`,
`ni_mistilt_diffraction`, `ni_mistilt_eels` and `ni_mistilt_series`.
They share configuration, numerical/postprocessing helpers and checkpoint
conventions across active tested workflows, including delayed/circular imports.
Moving their whole dependency chain would exceed this minimal leaf cleanup.
Likewise `multislice_emcd_reference` provides coherence/projection diagnostics
used by the GUI, and other apparently research-named modules are dependencies of
declared CLI/API paths. They are retained, not treated as dead code.

No module was uncertain enough to require category D after inspection. This is
not a claim that external downstream callers can be exhaustively discovered;
the five repository-only invocation changes are explicitly documented above.

## Validation

- 25 focused relocation/atomic-geometry tests passed.
- 77 ordinary package modules imported; the intentional GUI launcher was checked
  statically. GUI initialization passed with eigensolves forbidden.
- All 12 pyproject entry-point targets and all five PyInstaller hidden imports
  resolved; all 12 installed CLI help commands passed. No original internal
  import points to a removed module.
- All 559 tests collected successfully. The full Windows suite finished with
  **558 passed, one pre-existing failure, 32 warnings**, in 617.11 seconds.
- All 204 production checkpoint hashes matched both before and after testing.
  The Beta 1, Beta 2 and local 3.2/2.5-default ZIP hashes are also unchanged, as
  is the user's existing source dataset.

### Existing unrelated validation failure

`tests/test_ni_voltage_dependence.py::test_reference_gate_and_fine_point_reuse`
fails in `scripts/ni_voltage_dependence.py:78`: its archived implementation-hash
gate rejects `gui/memory_budget.py`. Neither that file, the voltage script nor
the voltage test is changed by this cleanup. Running the same test with the
clean pre-cleanup `f427992` runtime reproduces the same failure (9.03 seconds).
The archived digest begins `ec4c15e742bf`; the baseline Git blob begins
`ee0446189528`, so even the pre-cleanup source does not match the archive.
This is an existing provenance/reuse-gate failure, not a numerical difference
introduced by relocation. The guard, archived metadata and reference results
are deliberately unchanged; no production recalculation was used to bypass it.
The complete full-suite result is therefore reported as not wholly green.

Local evidence includes `before.json`, `validation.json`, `cli_help.json`,
`focused.xml`, `full.xml`, `baseline_failure.log`, `unrelated_failure.json` and
`after_integrity.json` under the audit output directory.

No production simulations, reference regeneration, GUI behavior changes, version
change, EXE build, release/tag modification or remote push is part of this task.
Local audit details and test reports are under `outputs/source_cleanup_audit/`.
