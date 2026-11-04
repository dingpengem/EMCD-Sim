# v0.8.1-beta.1 Part 1 - local Windows acceptance

Date: **2026-11-04**, America/Los_Angeles.

**LOCAL ACCEPTANCE: GO.** All required local gates passed on the exact versioned
candidate below. This is **not publication approval**: no push, tag, release,
GitHub workflow dispatch or release CI was performed. Publication awaits the user's
separate instruction. Part 1B code consolidation has not started.

## Source, branches and artifact identity

|Item|Identity|
|---|---|
|Original accepted scientific main|`82bd58098cf5722b342c2d92b2395c223faa4cde`|
|Tested conservative cleanup source|`e601e04540a06ed490466680bc4fa151146c1eaa`|
|Cleanup acceptance-document commit|`7feba3ebc54911353f4e29a803e4a4f69446a7bb`|
|Local main after accepted cleanup merge|`0f981bf4864cbb84ccc496fa32900ee7919b95e6`|
|**Exact built and tested release source**|**`654ed042b1b9638a43112e215a129c1a8d1bf186`**|
|Candidate branch/worktree|`release/v0.8.1-beta.1`, `build/v081-release-source`|
|Package/display/Windows numeric version|`0.8.1b1` / `v0.8.1-beta.1` / `0.8.1.1`|
|Physics convention|`forward_born_dagger_g_minus_h_v1` - unchanged|
|Last fetched remote main|`237944148151d784b6b2e3597e853dbc32779bd0` - not pushed|

The candidate source worktree was clean when built and tested; the embedded build
manifest records the exact source and `dirty=false`. The native Windows executable
ProductVersion resource independently reports `v0.8.1-beta.1`, and newly saved
projects report compiled software version `0.8.1b1`.

This report is a subsequent documentation-only commit on the candidate branch.
It does not alter the executable/test source or the accepted ZIP. Local main remains
at the cleanup merge; version preparation is preserved on the isolated release
branch for review. The future tag, if separately authorized, must identify the actual
accepted build source above rather than silently relabeling a different binary.

|Local artifact|Value|
|---|---|
|ZIP|`build/windows-v081b1-release/EMCD-Sim-v0.8.1-beta.1-Windows.zip`|
|ZIP bytes|**108709102**|
|ZIP SHA256|**`c485928a87a3c25aebf1fe749527ec8d3a2fdea7da6d1da648e4297d352d7e9e`**|
|Checksum file|`build/windows-v081b1-release/SHA256SUMS.txt`|
|Build manifest|`build/windows-v081b1-release/build_manifest.json`|
|Actual tested EXE|`build/windows-v081b1-release/extracted/EMCD-Sim/EMCD-Sim.exe`|

Paths are relative to the candidate worktree. The ZIP, extracted app and all
intermediate artifacts remain local and preserved; older packages were not replaced.

## Recovery of the original run

The model capacity interruption was **not a software/test failure**. Recovery found
the original Python processes still active (original start 08:48:27 local time) and
the original execution session `30690` intact. Its existing log advanced from 72%
to completion. No completed build or scientific test was restarted or duplicated.
The same run produced final JUnit XML and the original shell returned exit 0.
`source-tests-source.txt` binds that run to the exact source above; the recovered
exit status is retained separately in `source-exit-status.json`.

Previously completed native, startup, numerical, manifest and checksum evidence was
reused and checked against the unchanged candidate. Hash/file verification during
recovery did not rerun the numerical calculations. No new consolidation or scientific
feature work was performed during recovery.

## Local gates and exact results

|Gate|Result|
|---|---|
|Complete Windows source regression|**793 collected: 754 passed, 39 skipped, 0 failed, 0 errors**|
|Original source-process exit|**0**, completed normally; no restart|
|Source regression wall time|**1503.03 s (25m 03s)**|
|Warnings|**885**, retained; existing Qt deprecations/layout diagnostics and deliberate invalid-input checks|
|Skip comparison|Same 39 test identities/reasons as accepted cleanup baseline; no new skips|
|Extracted-EXE GUI worker matrix|**8/8 cases**, frozen=true, Qt platform=windows, exit 0, clean shutdown|
|Source-control vs versioned-EXE numerical comparison|**1080/1080 arrays bitwise equal**, maximum absolute difference **0**|
|Compiled project version|`0.8.1b1` in all eight newly saved case projects|
|Normal application entry|Default elastic preview, native screenshot and normal exit **0**|
|Package manifest|**614** listed files independently checked for exact byte size and SHA256|
|Checksums|ZIP matches external SHA256SUMS; all **614** internal checksum entries match the verified manifest|
|Documentation|No new or pre-existing local link/image-reference failures in the reviewed current documents|
|Preservation|All **19** pre-existing unrelated root files/statuses remain byte-identical; protected data/figures/fixtures unchanged|

No skipped, pending or interrupted work is described as passed. The complete source
run used native Windows Python 3.11.17, offscreen Qt, one OpenBLAS/OMP thread, disabled
pytest cache and the existing Windows venv. Real protected-array, historical-project
and external legacy-table paths were supplied read-only. Missing optional historical
studies were not regenerated or replaced by fallback simulations.

### Actual extracted-EXE coverage

The ZIP was freshly extracted and verified before launch. Runtime PATH was limited
to Windows system locations, Python/Conda environment paths were removed, and a
separate writable profile/workspace was used. This is same-host native acceptance,
not certification on a separate clean PC or VM. The application remains unsigned.

The actual EXE exercised:

- Real GUI startup, CIF import, elastic preview and clean process shutdown.
- Original Ni XMCD and original Ni atomic providers; Single/Double Channeling;
  both BW and FFT Multislice in every case.
- Declared imported complex tensor validation, element/edge matching, explicit
  magnetic states and nonmagnetic-source validation.
- Complete parameter JSON input through the GUI generation action, tensor generation,
  embedded source checksums/provenance, and GUI project save/open.
- Invalid parameters, replaced-source checksum rejection and partial atomic
  provenance rejection; failed generation clears stale validation/acknowledgement.
- Synthetic BCC Fe selected L2,3 EELS, angular maps, virtual detector spectra,
  BW/MS comparison and explicit synthetic/physically-unvalidated labels.
- Scientific PNG/SVG/CSV export from the completed generalized result.
- Read-only genuine historical Ni project loading, explicit Lobato recovery and
  archived elastic controls within the existing `2e-12` criterion.

|Native case|Channeling|BW/MS `I_A_plus` relative L2 norm difference|
|---|---|---:|
|`Ni_xmcd_single`|Single|0.00032945034278085|
|`Ni_xmcd_double`|Double|0.0006593227630042392|
|`Ni_ni-atomic_single`|Single|0.0003302171062392723|
|`Ni_ni-atomic_double`|Double|0.0006617875268144831|
|`Fe_imported_single`|Single|0.0006396961091371369|
|`Fe_imported_double`|Double|0.001281579073342945|
|`Fe_atomic_single`|Single|0.0006396961091371369|
|`Fe_atomic_double`|Double|0.001281579073342945|

These are finite-case numerical consistency checks, not general convergence or
quantitative material accuracy. Synthetic Fe Single/Double differences are
approximately **0.064% / 0.128%**. The previously documented approximately **1.6%
detector-refinement sensitivity** remains a limitation.

## Compatibility, cleanup and redistribution

The [cleanup report](SOURCE_CODE_CLEANUP_0_8_1.md) and
[64-module inventory](SOURCE_CODE_CLEANUP_0_8_1_INVENTORY.csv) are preserved. No whole
source module, scientific function, independent benchmark or compatibility path
was deleted. Five unused imports in three diagnostic/runtime files were removed;
public re-exports and Qt virtual callbacks were retained. The earlier 1080-array
accepted-main/cleanup comparison was also exact. This does not initiate Part 1B.

Compared with accepted main, src changes are limited to package version metadata
and the three already validated unused-import cleanups. AST checks confirm unchanged
non-import bodies/defaults there and unchanged public package exports apart from
version strings. Born/MDFF kernels, generalized tensor/atomic mathematics, core SOC,
CG coefficients, complex-dipole conjugation, IAM providers/defaults and historical
reference fixtures remain unchanged. Historical Ni numerical source regressions and
the protected 160-array comparison pass. The genuine archived project's successful
elastic control does not retroactively certify legacy magnetic-sign conventions.

The raw-a.u. 9/30 nm Ni [017] A/B and Flip-M figures, source/provider metadata and
historical research outputs were neither regenerated nor relabeled with the new
elastic provider. Raw a.u. remains primary and normalized percentages supplementary.

The package includes the existing MIT and dependency notices, unchanged Apache-2.0
Adaptive coefficient LICENSE/NOTICE/provenance, CIF space-group data and the original
synthetic parameter example. The sample and coefficient files match source bytes.
No upstream HDF5 archive or unlicensed external Z=1-98 table is bundled. No broad
hidden-import workaround was introduced; the required DLL/module paths worked in
the tested extracted runtime. Optional-platform warnings are not proof of arbitrary
optional dependency or hardware coverage.

## Scientific boundaries

- The generalized atomic model is approximate independent-electron **2p-to-3d**,
  with a declared **cubic** crystal field, explicit radial inputs, spin-resolved
  holes, exchange/broadening, local +z magnetization and proper rigid frame rotations.
- Synthetic Fe is a mathematical/software demonstration, **not quantitative Fe EMCD**.
  There is no supplied validated Co/Cr material model, general crystal-field solver,
  full DFT-derived MDFF, many-body multiplet/core-hole/charge-transfer accuracy,
  validated AFM/SDW or multi-element site-resolved MDFF.
- EELS/EMCD intensities remain relative, not calibrated electron counts, experimental
  detectability or absolute cross section/handedness. BW/MS agreement is distinct
  from basis/FFT/depth/energy/detector convergence and physical accuracy.
- Existing Ni-specific providers retain their original eligibility gates. Generalized
  sources require explicit element, edge, frame/state, checksum and eligible
  single-element full-occupancy translation-equivalent ionization sites.

## Skips - not passes

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

Required supplied historical Ni/array controls and all new model/source workflows
ran. The skips concern unavailable optional stored studies, benchmarks, GUI projects,
WIEN2k companions or offline HDF5 evidence, with no new skip reason introduced.

## Evidence inventory and execution boundary

Evidence remains under ignored `outputs/v081-release/`. Exact evidence digests are
in `part1-evidence-sha256.json`; the table below records the principal artifacts.

|Evidence|SHA256|
|---|---|
|`source-tests.xml`|`4ace1e09fcbf1a43c176e8f3f4b39aead477a6833dcf9982de144974788210b6`|
|`source-tests.log`|`7589f3d0b58a583e76bc2383d4a067fe241b3aedd8e1a60a9154b347ede9c1b3`|
|`source-tests-source.txt`|`e85b8f5dad4ecf93c89e9b728637e373718b3d64a2675b8ad58d2d5febfa4cb8`|
|`source-exit-status.json`|`40927bc1e5e9e4f7640fc1a2a5525261ab864c9030cc1e54d421afb495cc24fb`|
|`exe-native/acceptance.json`|`bd57c354dc8512b04246122aa0abf7ce0f65ef76923a32e9f5ba3f3070b95322`|
|`native-exit.txt`|`13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354`|
|`native-numerical-comparison.json`|`fae5cc12a84803a4bb23ff88d5d6e09d7d5e1356c045c5f7754312559eb28c98`|
|`normal-startup.json`|`e176deeea68dbc5d37cdf8328d91b7a4b41498bb9ed1d33c872d7562a7e479ad`|
|`normal-startup.png`|`828e0d76c158bae150781b833682003935fef02d10c9d9c10fc47589149af10a`|
|`package-verification.json`|`731a9cebebe31f337b9540581c2d8e0dc78ae357081240fb2ff0d0a75e0f71ea`|
|`documentation-audit.json`|`8ad106047a3a5e4e9b056c880806e3591480d1fe166f6d42fcbec8cf5c5e8b38`|
|`preservation-verification.json`|`422dda735e2d1e52c3227f173d93d160a2d0a1bf7077f3345a86c27a95e20950`|
|`part1-recovery-verification.json`|`33fbf401a3dc6538eac0fa56af3a01d2755fd8a826a3914a77848f068f969462`|

**STOP after Part 1.** No GitHub push, tag, workflow dispatch, release creation,
asset upload, publication or Part 1B consolidation was performed. Release CI is
**NOT RUN - intentionally deferred**, not passed. Linux/macOS CI was neither
investigated nor suppressed; this report certifies only the stated local Windows
checks. Staged download/tag/documentation URLs are future publication links and
must not be represented as live released assets.

There is no essential local Windows blocker in the tested scope. Separate publication
authorization, fresh remote-divergence checks and any requested release-CI/public
asset verification remain outside this completed Part 1 boundary. All worktrees,
old releases, build intermediates, logs, exported projects and artifacts are retained.
