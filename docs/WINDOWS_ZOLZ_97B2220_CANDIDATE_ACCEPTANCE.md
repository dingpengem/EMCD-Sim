# Windows ZOLZ candidate acceptance — source 97b2220

**Windows Development Candidate ? Validated.**

|Acceptance scope|Status|
|---|---|
|Native automated Windows acceptance|PASSED|
|Independent clean-machine acceptance|NOT TESTED|
|Official public v0.7.0 release|NOT PUBLISHED|

This beta research candidate is accepted within the native Windows scope below.
Independent clean-machine testing is not required for the documentation-only
integration. Cross-platform issues remain separate limitations.

Local and remote main: `97b2220e5329dad6f98eedec61f58a6cf07d9da8`; ahead/behind 0/0, reverified after native acceptance. Ordinary non-force push from cf8fa647d1cbe7457362f54fbd4ecdce5c65cea5; no history rewrite or other branch modification. All four reviewed commits are present:

- `b3edf65e8f539b6f4e37e35b8b35144566b7838a`
- `e12f8acbfc929e1c8fadff840528da7dec1dcd99`
- `dfd60115e73cf0fcfc4c7d7c44432c667c771b34`
- `97b2220e5329dad6f98eedec61f58a6cf07d9da8`

[Windows build run 41516996056](https://github.com/dingpengem/EMCD-Sim/actions/runs/41516996056): **completed successfully**, including source checks, packaging and extracted standalone acceptance for all five orientations. Artifact ID 13176670856, name `EMCD-Sim-v0.7.0-beta.1-Windows`. The binary was built by the unchanged approved Actions workflow from the exact pushed commit; no local rebuild or version change.

## Candidate paths and integrity

- EXE: `C:\Users\peng863\EMCD-Sim\build\v070b1-unit-clean-main\build\windows-zolz-97b2220-actions41516996056\extracted\EMCD-Sim\EMCD-Sim.exe`
- Portable ZIP: `C:\Users\peng863\EMCD-Sim\build\v070b1-unit-clean-main\build\windows-zolz-97b2220-actions41516996056\artifact\EMCD-Sim-v0.7.0-beta.1-Windows.zip`
- EXE SHA256: `c73510032ad2dfc1320e550d79dc9da69613cc14b1b91c42816cc09e3b266110`
- Portable ZIP SHA256: `8d157d8b62fb6570d201360cdae85f44aa4cea2c1478f1949eb4336a135e17bc`
- Outer Actions artifact SHA256: `09bcef093a92dbcc3688631176f275835a0d15acc63f1bd2aa096dfc6e7abd9b`

GitHub supplied the outer artifact digest; the portable ZIP matches its included SHA256SUMS.txt. All 1215 packaged manifest files were rehashed before and after testing, and all 54 recorded Python source fingerprints match the intended Git tree (accounting explicitly for LF/CRLF checkout bytes). No missing module/DLL was observed. six license collection was verified. The source-only test fixture ZIP in the pushed history is reviewed source evidence, not a Windows artifact or scientific result.

## Build environment and dependencies

Build environment: `{"python_version": "3.11.9", "python_executable": "C:\\hostedtoolcache\\windows\\Python\\3.11.9\\x64\\python.exe", "python_prefix": "C:\\hostedtoolcache\\windows\\Python\\3.11.9\\x64", "platform": "Windows-10-10.0.26100-SP0"}`. Version remains package 0.7.0b1 / display v0.7.0-beta.1; native Windows EXE metadata was independently read as 0.7.0.1. Build UTC: `2026-11-02T20:13:49.766592+00:00`.

|Distribution|Verified version|
|---|---|
|numpy|2.4.6|
|scipy|1.17.1|
|matplotlib|3.11.2|
|ase|3.29.0|
|PySide6|6.12.0|
|pyinstaller|6.22.3|
|six|1.17.0|

six==1.17.0 is explicitly declared in the unchanged Windows requirements; the fresh CI install and metadata preflight logged that version, and the resulting portable package includes its license. All application dependencies came from the approved packaging workflow. Local pywinauto/comtypes/pywin32 tools were installed separately under native-tools only; they were not added to the application lock or ZIP.

## Native packaged-runtime outcomes

These checks launched the actual extracted EXE with QT_QPA_PLATFORM=windows, PATH restricted to Windows/System32 and Windows, and Python/Conda/Qt override paths removed. Tests used isolated application-data/workspace directories. This is same-host native Windows acceptance, not merely offscreen/source testing, and **not an independent clean-machine installation test**.

|Check|Result|
|---|---|
|Native launch, responsive window, About/version/convention, standard unit labels|PASS|
|Ni [017], [117], [001], [111], [710] smoke profiles|5/5 PASS|
|Single and Double Channeling, both BW and FFT MS, elastic preview and Bragg alignment|PASS in each orientation|
|Saved-project save/reopen, display switches, maps/EELS and scientific exports|PASS in ten orientation/channel workflows|
|Approved Ni [017] L3/L2 raw-reference comparison|8/8 PASS, exactly matching|
|Fresh-process cancellation/worker-safety scenarios|2 runs × 9 scenarios PASS|
|Normal-launch ZOLZ drag, current-to-stale status, neutral spot rendering, release and outside fallback|PASS|
|Native SVG/PNG styles, star shape, circle center/radius and visibility|PASS|
|Real toolbar-click pan/zoom priority; detector A movement, B/ZA preservation and restore|PASS|
|Application exit and no remaining owned calculation processes|PASS|

The cancellation protocol verified its effective Manual 3-beam/9×9 profile, active-worker cancellation/acknowledgement, restart and saved-result integrity. Worst reported cancel-to-idle: **0.481192 s** across both runs. The protocol rejects calculations that finish before cancellation as cancellation evidence.

The normal-launch native drag began at an exactly current cached preview, moved continuously through distinct positions, removed cached intensity fills and marked the tab/readout stale without a busy worker. A/B positions remained unchanged. Native readouts followed q_ZA=-theta/lambda and R=|q_ZA|. Release used its final real mouse location; outside release preserved the last valid position. SVG geometry independently confirms that the darkorange circle center equals the gold star, its radius matches |q_ZA|, and the star is a star-shaped marker. At the default exact-Bragg reference it coincides with Thales; off-row intersection versus complete overlap remains correctly distinguished.

Styles were read from the EXE-generated SVG: teal dotted width 1.2/alpha .75; darkorange dashed width 1.8/alpha .95. Native PNG was also exported. Hidden Laue exports retain the ZA star/Thales circle while omitting orange geometry and legend. Neutral stale diffraction uses gray unfilled paths. Source identity and native exports preserve the requested z order.

Native mouse checks have screen-pixel precision (the recorded coordinate resolution is in uia/interaction.json). The distinct-final-release-without-intermediate-motion edge case additionally passed the unchanged exact-coordinate source regression on the identical packaged app source. Nonfinite pointer values are source-level controls; an OS mouse cannot emit NaN. These distinctions are explicit rather than claiming native subpixel or impossible-input coverage.

External automation was corrected for pywinauto mouse.move arguments, native Windows filename syntax, asynchronous save completion and SVG inline-path encoding. UIA Toggle changes only QAction check state on this Qt provider, so navigation was verified with real mouse clicks. A long observer reached its own preset deadline and closed cleanly; a fresh instance independently completed detector/navigation checks. These were test-controller issues only: no application source/binary was patched or rebuilt and no completed scientific case was restarted. Logs preserve attempts and final passing evidence.

## Numerical reference scope

Approved reference reused without recomputation: `C:\Users\peng863\EMCD-Sim\build\v070b1-candidate-source\outputs\windows_v070b1_acceptance\native_clean_commit_rc1\python_reference\scientific_acceptance.json`, SHA256 `d5907e9263f753313f5b8c9e3bd91be3b8fda06bc6f6fbbe0c02448fdff7ebb9`, producer `f80a96f6e9f36c63dd6f673e70bc54ce4030963e`. The physics convention, Ni source checksum, complete geometry/settings, frame, beam indexing, energy grid and physical configuration match. This reuse is valid across the already verified unit-label-only changes; no MDFF or propagation change occurred.

The packaged selected-energy run uses Ni [017], 300 kV, 10 nm, exact (200) Bragg with 15 mrad off-row tilt, 17×17 angular grid, 33 depth nodes, 32×32 FFT and .04 nm maximum step. It is a bounded packaging reference, not either historical 200/300 kV study. Single/Double × BW/MS × L3/L2 yielded zero raw-intensity relative difference and zero magnetic/PRB percentage-point difference against all eight approved reference rows. Existing tolerances stayed at raw relative ≤0.001 (0.1%) and asymmetry difference ≤0.01 percentage points; no thresholds were relaxed.

The five-orientation tiny selected-energy smoke profiles test functional packaging and coordinate consistency. They do not certify quantitative beam/potential/depth/grid convergence. All documented [111], coarse-detector, effective-MDFF/IAM and experimental-handedness limitations remain.

## Source CI status and remaining issues

[Cross-platform tests run 41516996011](https://github.com/dingpengem/EMCD-Sim/actions/runs/41516996011):

- Windows: completed successfully, 618 passed / 39 skipped. The extra skip relative to local 619/38 is the external 160-array evidence, absent on CI; it passed locally.
- Ubuntu: failed, 617 passed / 39 skipped / 1 failed. test_approved_physics_kernel_bytes_unchanged expects raw Windows CRLF SHA256; Linux LF content has the confirmed canonical hash ac8a150fd370615b74886aeb81564a2fdd6b15e3d5da94e58ea1982afba8610d. This is a platform-dependent byte guard, not a changed physics source.
- Ubuntu also aborted at Python shutdown with bool_dealloc / C-extension refcount error (exit 134). The underlying extension/cause is unverified and remains unresolved.
- macOS: still in progress at the final status check; it is not reported passed. No unrelated run was cancelled or restarted.

Those cross-platform issues require a separate reviewed follow-up; the exact approved source was not changed to hide them. **Windows-only development-candidate testing is GO; a broader formal release is not accepted here.** Independent clean-machine installation and native user acceptance on another Windows host remain untested. No version tag or GitHub Release was authorized or created.

## Scientific and user-work preservation

The three approved physics-kernel raw hashes match both local main and the CI build manifest. All 323 protected files, including 204 production checkpoints, were rehashed again and match. Existing user worktree HEADs, statuses and dirty/untracked file hashes are unchanged; both uncommitted acceptance reports retain their pre-push hashes. The previously verified 9,756 historical files, corrected 200 kV thickness and 300 kV Stage 4.2 studies were never written or regenerated by this task. All generated candidate/test material is confined to the new candidate build/output directories and this new local report.

Raw evidence: `C:\Users\peng863\EMCD-Sim\build\v070b1-unit-clean-main\outputs\windows_zolz_candidate`; native reports and exports: `C:\Users\peng863\EMCD-Sim\build\v070b1-unit-clean-main\build\windows-zolz-97b2220-actions41516996056`. This report is included in the subsequent documentation-only integration. Source push and build were completed before this documentation update. The documentation commit does not change the accepted binary identity.


## Final documentation acceptance

Independent testing on a separate clean Windows PC or VM has **NOT BEEN
PERFORMED**. The user's earlier statement, "I manually test it," is not treated
as independent clean-machine evidence or as a verified per-function checklist.
No environment or manual test outcome is inferred from it. The native automated
acceptance above remains PASSED; it is not invalidated by this untested scope.

The installation documentation identifies the candidate that actually includes
standardized labels, corrected Born/MDFF conventions, live ZOLZ/ZA interaction,
correct drag-release positioning, stale-preview invalidation and existing
project save/open compatibility. Earlier released EXEs retain their original
features and scientific provenance. Full complex DFT-derived MDFF remains
unimplemented; approximate effective MDFF, projected IAM and configuration-
specific convergence limitations remain. This is beta research software, not
complete experimental validation.

Binary source remains `97b2220e5329dad6f98eedec61f58a6cf07d9da8`, with
portable ZIP SHA256
`8d157d8b62fb6570d201360cdae85f44aa4cea2c1478f1949eb4336a135e17bc`.
A documentation-only commit does not create a new scientific or binary candidate.
Version remains v0.7.0-beta.1 / 0.7.0b1. No rebuild, version tag or release is
part of this documentation integration.

### Documentation push and CI scope

The five reviewed documents are README.md, docs/USER_GUIDE.md,
docs/QUICK_START.md, docs/CHANGELOG.md and this report. Local Markdown file
links and candidate identity are checked before commit. No source, tests,
workflows, numerical defaults or scientific results are included.

The Windows build workflow runs on main pushes only when src/**, packaging/**,
pyproject.toml or its own workflow file changes. Therefore this documentation-
only push does **not** automatically build a new Windows candidate. The
cross-platform Python test workflow has no path filter and is expected to run.
The release-asset assembly workflow is manual; it is not invoked here.
The earlier cross-platform run still reports macOS in progress at this review;
it is not claimed passed. Linux's line-ending/hash failure and interpreter-
shutdown error remain unresolved, independently of the successful Windows
acceptance. Workflow definitions are unchanged.
