# Stage G — final acceptance and release readiness

**Status: suitable for reviewed research-preview integration; public release
remains blocked pending distribution validation, artifact provision and explicit
approval.** Software acceptance is not quantitative scientific validation.
No merge, version change, tag or GitHub release was performed.

## Reviewed source and candidate

| Item | Reviewed value |
| --- | --- |
| Branch | `feat/emcd-desktop-gui` |
| Application/documentation starting commit | `249ccaa9ee9fb16f2369f2cadd8704417558b3a2` |
| Frozen application build commit | `618789717303cbea246cdb0fbccfe6a44040ecb7` |
| Build UTC | 2026-10-16T17:03:47.009801+00:00 |
| Build identifier | EMCD-Sim GUI Stage F RC (unreleased) |
| Package metadata | 0.4.5, unchanged |
| Reviewed archive | `build/windows-stage-f/EMCD-Sim-Stage-F-Windows-RC.zip` |
| ZIP SHA256 | `523cc3a087a92b4dc7aa790daeefca3399dbe35d0974ad78c7cbb4913cda9ca8` |
| Archive / extracted size | 108,541,536 / 261,851,292 bytes; 608 application files |

Stage G changes documentation and adds a focused acceptance script. It does
not change GUI runtime code, scientific algorithms or project schema, so it
**reuses the accepted Stage F candidate without rebuilding**. The Stage G
documentation/tooling commit is the commit containing this report; use
`git rev-parse HEAD` to identify the exact checkout. Frozen build metadata
continues to identify the application build above, not the later docs commit.

The build reports a dirty workspace because of pre-existing user-owned inputs
and scripts. Every recorded GUI source hash matches the reviewed application
source. Only the committed five-column Ni example was bundled, not the local
modified header or original companion calculation. Its SHA256 is
`4fd517af3e54db94588a76b7a6ed9c2f9a1b745cd8fe52b9fca0f87fc4938db3`.
No WIEN2k source, binaries or full DFT environment are distributed.

## Acceptance status

| Area | Status | Evidence and scope |
| --- | --- | --- |
| Source GUI A–F tests | PASS | 70 tests, 115.14 s; compact real numerical fixtures, geometry/events, model gates, workers, cancellation, persistence, comparison, resources and percentages. |
| Existing atomic-model compatibility | PASS | Eight `test_ni_local_mdff.py` tests, 5.07 s. The branch's existing optional reversal extension retains the historical default; Stage G adds no engine changes. |
| Fresh source reference workflow | PASS | Actual native Qt preview, bundled-source validation/preview, default Ni [017] BW worker, Save Project As and threaded Open. All 107 NPZ entries equal Stage C's matched BW baseline. |
| Six saved model/method baselines | PASS | XMCD and atomic × BW/MS/Both reopened. All 702 NPZ entries, including labels, equal their existing Stage C counterparts; Stage E's separate report identifies 682 numerical arrays. This is baseline revalidation, not six new full simulations. |
| Reversal parity and signed observables | PASS | A–F tests plus saved-data review; magnetic-odd, even imbalance, raw and corrected quantities remain distinct. |
| Fresh portable extraction and launch | PASS | The reviewed ZIP extracted to `C:/EMCD-Sim-RC-Test/stage-g-20261016/`; launched from System32 with Python/Conda PATH entries and environment variables removed. Same Windows installation as development. |
| Frozen save/reopen, compare and exports | PASS | Existing opt-in reopen acceptance loads saved arrays without a propagation worker, compares reference/+1 mrad X, and exports PNG/SVG/numerical data. Save/load logic also exercised by source GUI and automated tests. |
| Frozen Stage F displays | PASS | All spectral modes/zooms, BW/MS overlay, local/paired angular percentages, saved comparison, PNG/SVG/CSV/NPZ. Nine guarded forward entry points recorded zero calls; original arrays/project files unchanged. |
| Missing original XMCD | PASS | Isolated project provenance points to a nonexistent XMCD, with the built-in structure intact. Source percentages and frozen viewing/export work; Use These Settings disables rerun. No original input was renamed/deleted. |
| Legacy B/C and Stage D compatibility | PASS | Included GUI persistence/normalization tests, using existing saved results read-only; schema remains 1. |
| Docs and screenshots | PASS | Control names and actions reviewed against implementation and exercised workflows; actual A–F captures reused with milestone captions, one native source-preview capture added. Relative links/images checked. |
| Existing Conda source environment | PASS | Python 3.11.17 environment reused for source GUI, tests and native reference workflow. |
| New source-install environment | NOT TESTED | Clean venv recipe follows `pyproject.toml`; no claim of a freshly provisioned environment or newly tested package installation. |
| Independent Windows VM / second computer | NOT TESTED | **NOT TESTED — independent clean-machine validation pending.** Clearing PATH on the development host is not an independent-machine test. |
| Other Windows versions / ARM / 32-bit | NOT TESTED | Candidate is x64, exercised on Windows 11 Enterprise build 26200.9457 only. |
| Native 100% / 125% display scaling | NOT TESTED | Native acceptance used 150%. Scrollable canvases/maximize controls mitigate clipping but do not substitute for these tests. |
| Startup variability and unsigned binary | WARNING | Measured overhead varies; no digital signature or SmartScreen trust is asserted. Do not disable security protections. |
| Public binary acquisition | BLOCKED | Candidate remains local. No GitHub release asset or public download URL exists; a trusted artifact location and explicit publication approval are needed. |
| Merge/tag/version/release actions | BLOCKED | Intentionally require separate explicit approval. This milestone does not perform them. |

The 70-test run emitted 31 existing Qt high-DPI deprecation / small-canvas
Matplotlib layout warnings. No test failed. Native images and exported figures
were inspected for readable axes and labels. A full 43-orientation study was
not run. Together with the eight atomic-model checks, **78 automated tests
passed**. All 77 relative documentation/image/anchor targets checked in the
README and current guides resolved. A final hash audit found all 827 previously
fingerprinted artifacts and both accepted E/F archives unchanged; current GUI
runtime source hashes still match the frozen candidate.

### Native source acceptance details

The documented reference is FCC Ni a=3.524 Å, [017], (200), 200 kV, 30 nm,
absolute tilt `(−7.11672544, 0)` mrad. Measured s200 was
`−1.4610787197e-14 Å⁻¹`, consistent with zero. The full finite 2D basis was
preserved. Native selected magnetic features remain 831.271/848.698 eV;
atomic-model defaults remain separate at 852.7/870 eV.

Source preview took 2.38 s and the matched BW calculation/display workflow
48.80 s on this host; these GUI timings include completion/display handling.
The bundled five-column file has no companion audit, so the workflow
explicitly declares source conventions and enables post-edge correction when
matching the corrected baseline. An initial acceptance-tool setup omitted that
checkbox; the resulting field-set mismatch was corrected in the tool, not by
changing physics. Another tool check initially changed only a top-level config
when constructing a missing-source fixture; saved method provenance correctly
retained the original source. The final tool constructs consistent isolated
top-level/method provenance, and tests the XMCD-only missing condition. It
resumes from the already verified reference project to avoid another solver run.

Reproduce on the existing GUI Python environment, with fresh output folders:

```powershell
python -m pytest tests/test_gui_stage_a.py tests/test_gui_stage_b.py tests/test_gui_stage_c.py tests/test_gui_stage_d.py tests/test_gui_stage_e.py tests/test_gui_stage_f.py -q
python -m pytest tests/test_ni_local_mdff.py -q
```

`scripts/gui_stage_g_validation.py` supplies the actual native source workflow;
`--output`, `--source`, `--baseline` and `--saved-root` are explicit local paths.
It performs one BW reference calculation, writes only to a new output/workspace,
and only reads existing baseline projects. `--resume-project` rechecks a newly
generated reference's project/source handling without another calculation.
The saved Stage C/E validation projects are required local evidence, not
bundled examples. Source-install recipes are separately labeled by verification
status in [INSTALL_WINDOWS](INSTALL_WINDOWS.md).

### Frozen acceptance and performance

Stage G repeated the accepted candidate's opt-in `--rc-reopen` workflow and
`--stage-f-acceptance` display workflow, using copied projects. A further reopen
used a consistently saved XMCD-only missing fixture, so that a missing CIF
could not accidentally satisfy the rerun-block check instead.

| Measured Stage G workflow | First window | Peak working set | Whole workflow |
| --- | --- | --- | --- |
| Frozen reopen/comparison/export | 28.11 s | 270.03 MiB | 229.71 s |
| Frozen percentage display/export | 42.71 s | 273.36 MiB | 116.49 s |
| Frozen explicit missing-XMCD reopen | Not separately timed | 269.81 MiB | See local reopen report |

Whole-workflow times include figure rendering, exports and verification; they
are not propagation times. Earlier Stage E measured default XMCD BW/MS/Both
workers around 49–119 s and peak process memory near 297 MiB. No minimum RAM
or guaranteed runtime is inferred. Native tests used an Intel Core i7-1365U,
31.58 GiB host RAM and 150% display scaling. A separate clean machine and
human layout review at other scaling settings remain necessary.

Local evidence (ignored generated data):

- `outputs/gui_stage_g/native_source_final/reference_export/` and its saved
  project: the new matched source BW result; its original tool report retains
  timings and the successful 107-entry comparison before the fixture check.
- `outputs/gui_stage_g/native_source_verified/acceptance.json`: final source
  saved-project, XMCD-only missing-source and six-case baseline checks.
- `C:/EMCD-Sim-RC-Test/stage-g-20261016/reopen/reopen.json`,
  `visualization/acceptance.json`, `process_reopen.json`,
  `process_visualization.json`, `missing_xmcd_reopen/reopen.json`.
- Existing [Stage E](EMCD_WINDOWS_RC_ACCEPTANCE.md) and
  [Stage F](EMCD_GUI_STAGE_F_ACCEPTANCE.md) numerical/build evidence.

## User documentation verification

- [Installation guide](INSTALL_WINDOWS.md): real portable-folder structure,
  correct current ZIP/hash, no invented MSI/download, measured host scope,
  workspace/log resolution, unsigned-app precautions, source-install status
  and practical troubleshooting.
- [Quick Start](QUICK_START.md): extract → geometry → source validation and
  declaration → explicit BW run → L3/L2/peak display → Save As/Open.
- [User Manual](USER_GUIDE.md): crystal/tilt/ZA distinctions, CIF gates, both
  MDFF models, depth-integrated propagation, signed decomposition, post-edge
  alpha versus peak normalization, missing sources, saved comparisons and exports.
- README presents one current desktop application and links these documents;
  the CLI/research documentation remains accessible. The technical GUI guide
  now labels older sections as milestone history rather than current product variants.

Every major guide retains projected-IAM/entrance-only assumptions and cautions
against interpreting corrected contrast or numerical BW/MS agreement as
experimental validation. Stage F's shared BW peak values remain approximately
−0.37556%/−0.37570% (BW/MS, L3) and +0.61516%/+0.61538% (L2). These are
simulated relative contrasts. The manual explains the different energy-dependent
asymmetry denominator and fixed full-spectrum reference.

## Git and distribution audit

`git fetch origin` was performed at review start. `origin/main...HEAD` showed
**0 commits behind, 11 ahead**, confirming the prompt's starting relation.
That comparison contained 48 files: GUI source/tests, docs/screenshots, build
scripts, GUI packaging metadata and the existing optional atomic reversal
extension. The core Bloch/FFT/tensor/contraction engines were not rewritten.
Stage G adds documentation, one actual screenshot and a validation script;
recheck counts after the Stage G commit and again before integration.

Review found no tracked generated output/build folders, Conda/venv trees,
executables, DLLs, ZIPs or proprietary WIEN2k wavefunction/code archives.
No added GUI-branch file exceeded 1 MB. The tracked five-column example is
unchanged against main. `.gitignore` excludes outputs, build/dist, environments,
caches and logs. Existing local WIEN2k companions, the modified example header
and unrelated raw-tilt scripts/tests remain unstaged and untouched. Guide paths
are labeled examples/local evidence; runtime resources resolve dynamically,
not from a developer's hard-coded home directory.

The ZIP's 608 application files contain the EXE, `_internal`, Qt/platform
plugins, Python/NumPy/SciPy runtime libraries, Matplotlib fonts/Agg/QtAgg/SVG,
ASE CIF support/space-group data, dependency licenses, build metadata and the
tracked Ni spectrum. They exclude user results and original WIEN2k companions.
The Stage E/F archives and earlier numerical artifacts are retained unchanged.

## Scientific-model readiness — separate from software distribution

**WARNING — research-stage model.** Projected independent-atom elastic
potential; entrance-only depth-integrated ionization; no outgoing channeling,
full double-channeling EMCD or atom-layer-resolved 3D multislice. XMCD constrains
an effective tensor rather than a complete complex DFT MDFF. Atomic ionization
is non-DFT. No absolute experimental cross-section calibration is provided;
the native WIEN2k energy axis is not experimentally calibrated. GUI FFT support
is verified only for conventional FCC Ni [017]; arbitrary CIF import does not
imply magnetic-ionization support. Physical Fourier-potential-cutoff convergence
remains unresolved. Good BW/MS agreement establishes neither that convergence
nor experimentally quantitative Ni EMCD.

## Proposed integration and version plan — no action taken

1. Review the Stage G docs/tooling commit and the complete GUI diff against
   freshly fetched main. Resolve any future divergence on the feature branch
   and rerun affected checks; do not force-push or delete research branches.
2. Obtain explicit approval for a normal reviewed integration into main.
   The exercised code is suitable for research-preview merge review with the
   pending tests clearly stated. No known failing exercised GUI/scientific
   regression remains. Public release readiness is a separate decision.
3. On an independent clean x64 Windows installation, verify extraction,
   launch, CIF import, the bundled-source default calculation, source-missing
   viewing, Save/Open, BW/MS/atomic saved data and exports without any developer
   paths. Test 100%/125% layout and review startup variability. Record OS,
   artifact checksum and outcomes; investigate DLL/plugin failures if any.
4. Choose an approved trusted artifact channel. If a future build is needed,
   use a fresh output/build identifier, reaccept it and record its own checksum;
   never relabel the current archive as a new binary. Keep accepted E/F artifacts.
5. **Proposed version**, only after approval: `0.5.0rc1` for the integrated
   GUI research preview, followed by `0.5.0` after distribution acceptance.
   Keep CLI and GUI under one package version; milestone letters are development
   history and RC build identifiers record commit/time. Do not imply v1.0 or
   quantitative scientific maturity. Metadata remains 0.4.5 in this milestone.
6. Obtain separate approval for any version commit, tag and public release;
   publish only accepted artifacts and their checksums/licenses/known limits.

Independent clean-machine validation and a real artifact acquisition channel
are the main public-distribution blockers. Signing/SmartScreen reputation,
additional OS/DPI coverage and performance profiling remain warnings/review
items. They do not negate the measured developer-host acceptance, and the
measured acceptance does not mark them passed. Stop here for review.
