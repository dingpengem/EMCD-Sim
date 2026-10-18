# 0.6.0 development validation — Double-Channeling EMCD Simulation

Date: 2026-10-18. Branch: `feat/emcd-v060-double-channeling`.
Baseline: `7bc78e5905f82d533abf931967eacb1f8ac3a452`.
Application/package metadata: **0.6.0**. Planned prerelease:
`v0.6.0-beta.1`, **unpublished**. No executable, tag or release was created.
Double Channeling already shipped in 0.4.5; this milestone consolidates its
framework and scientific presentation without changing the physical model.

## Scientific definitions

Both primary selectors offer **Raw (a.u.)** (initial default) and
**EMCD Asymmetry (%)**. EELS keeps original +M A/B spectra above two signed
raw component curves or one total asymmetry curve. Angular Raw keeps two
paired component maps; angular Asymmetry keeps one total point-pair map.

The independent hand reference `(A+, B+, A−, B−)=(0.65,0.45,0.55,0.55)` gives:

| Quantity | Expected |
| --- | ---: |
| Magnetic difference | 0.10 a.u. |
| Nonmagnetic difference | 0.10 a.u. |
| Total raw difference | 0.20 a.u. |
| Total EMCD Asymmetry, `100*(A+−B+)/(A++B+)` | 18.181818…% |
| Magnetic-only Asymmetry, `100*D_mag/(N_A+N_B)` | 9.090909…% |

An additional independent example has zero even difference but nonzero
`M_A+M_B`, checking that the two denominators still differ. Signed values,
reversal parity, zero/near-zero validity and NaN retention are tested.
There is no factor of two, separate curve normalization or implicit correction.

Angular helpers validate actual saved regular coordinates, qy mirror mapping,
physical mirrored A/B apertures, nonoverlap and fractional-weight matching.
They derive from original plus/minus intensity maps without interpolation.
Raw panels use a common signed zero-centered scale. The inherited angular
relative denominator floor is `1e-6`; invalid pixels remain NaN. The legacy
EELS difference/sum implementation and its validity policy are unchanged.
Integrated detector asymmetry is formed after integrating intensities, never
by averaging percentage pixels. Unavailable mirror geometry is explained.

## Focused acceptance

| Check | Result |
| --- | --- |
| Signal, plot/widget, export, saved-state and historical benchmark tests | 34 passed |
| Source version consistency and existing focused cancellation tests | 9 passed |
| Native Windows saved Single/Double × BW/MS/Both presentation | 6 cases passed |
| Forward calculation calls while switching saved displays | 0 |
| Original spectra, maps, coherences and amplitude fingerprints after switching | Identical |
| Native Windows cancellation cases | 9 passed |
| Cancellation preservation, queued completion, restart and save/open checks | Passed |
| Longest cancellation request-to-idle in this controlled small profile | 0.301385 s |
| Windows screen scaling | Native Qt Windows, DPR 1.5 (150%) |
| PowerShell build configuration syntax | Parsed without errors; not executed |

The 34-test command covers `test_v060_signals.py`,
`test_v060_presentation.py`, `test_gui_component_display.py` and
`test_prb_benchmark.py`. The separate 9-test command covers only
`test_portability.py::test_version_matches_source_metadata` and
`test_double_cancellation.py`. Historical numerical assertions remain;
obsolete primary-label/default expectations were updated. Two-energy results
remain discrete points in both modes. A two-point peak-search failure no
longer hides otherwise valid saved L3/L2 scalar readouts.

The GUI checks load existing accepted projects under
`outputs/windows_beta_acceptance/source_native/`. The reproducible opt-in
script is `scripts/validate_v060_presentation.py`; it rejects calculation calls
and writes fingerprints and PNG/SVG figures. Native cancellation acceptance
uses the unchanged existing harness with small actual jobs and controlled
180 ms work blocks. These are responsiveness checks, not production timing
or scientific convergence measurements. No production scans were rerun.

Local evidence is in `outputs/v060_validation/`:

- `checkpoint4_final.xml`: 34 passing tests.
- `version_cancellation_tests.xml`: 9 passing tests.
- `native_presentation_v2/acceptance.json`: six cases, fingerprints and zero calls.
- `native_presentation_v2/`: native captures and exported PNG/SVG in both modes.
- `cancellation_native/acceptance.json`: case timing and preserved-result hashes.
- `preservation_audit.json`: baseline source and published artifact checks.

Earlier exploratory logs are retained there, including obsolete-label failures
and sandbox temporary-directory ACL failures. The final focused test run used
normal host permissions to resolve those Windows pytest directory restrictions.

Offscreen/narrow panes can produce Matplotlib constrained-layout warnings.
The existing **Maximize / restore results** control makes labels readable at
150%; scrollbars preserve the minimum plotting size when the complete plot
does not fit vertically. The default narrow split pane remains cramped.
Actual exported figures were inspected; current examples are embedded in the
[manual](USER_GUIDE.md#read-angular-maps). They use the small saved dispatch
profile, not a new production convergence result.

## Numerical and project preservation

The original solver, MDFF, detector weights, beam/cutoff/depth settings,
precision, memory admission and cancellation implementations are unchanged.
Baseline comparison confirms unchanged BW/MS Double and Single tensor sources,
GUI propagation/channeling/memory helpers, cancellation, `project_io.py`,
`prb_benchmark.py` and `signal_normalization.py`. Within `emcd_forward.py`, only
`export_result` changed; all calculation functions are unchanged. Within
`stage_b.py`, only `StageB.save_emcd` changed; `EMCDWorker` is unchanged.

Old project arrays and key sets stay in their original checksummed containers.
Legacy PRB fields and original per-method CSV columns remain. Supplemental
`signal_display.npz` and `*_signal_display.csv` add explicit derived aliases and
denominators; `figure_display.json` records definitions and view settings.
Tests check exact CSV/NPZ agreement, legacy spectral values, project reopen,
separate PNG/SVG modes and source-array immutability.

Old saved `relative` preferences mean magnetic-only/even common-denominator
components. They open that explicit advanced view with a migration notice and
Raw primary selection, never silently becoming total asymmetry. Schema 2 saves
separate EELS/map display modes, diagnostic selection and energy locking.
Advanced reversal, correction/residual, local/intrinsic, paired magnetic/even,
legacy peak, arbitrary detectability-proxy and BW/MS diagnostics remain.

## Version and publication boundary

`pyproject.toml` and the package declaration agree on **0.6.0**; GUI title/About
and future build metadata use the source package version. Build label, manifest
and archive defaults derive from it. This avoids stale installed distribution
metadata when preparing a later build. Build scripts were only inspected and
syntax-checked. README, Quick Start, User Manual, GUI reference, changelog and
future packaging notes identify the unpublished development status.

The existing `v0.4.5-beta.1` tag still resolves to
`4185080dfb76c5dcce051b43511969caf9181548`. Its locally retained published ZIP
still has SHA256:

```text
309438c4a049773a6e99948477c8d52051cd8f1de632a762c795656e6c5a2216
```

No push, merge, packaging, tag or publication was performed. User-owned Ni
source changes and companion files are excluded from the development commit.

## Remaining scope

The XMCD-constrained MDFF remains approximate, without a complete DFT-derived
transition tensor. Elastic potentials are projected; longitudinal transfer
uses the existing frozen approximation. Native source energies are not an
experimental calibration. Absolute EELS units and the detectability proxy are
not calibrated electron counts or experimental SNR. Only representative
numerical configurations/materials/geometries have been validated; no global
convergence or new scientific optimum is certified here.

Standalone Windows acceptance, source/frozen comparison for 0.6.0,
independent clean-machine testing and release preparation remain a separate
milestone. The 0.4.5 executable and its existing limitations remain intact.
