# macOS ARM64 beta.3 — Public Research Beta Acceptance

**Approved candidate: automatic focused checks and user manual GUI acceptance PASSED.** The user accepted the exact RC5 below, including real mouse interaction with MDFF Done and the originating 3D Viewer, and authorized publication. The official release is [EMCD-Sim v0.9.0-beta.3 — macOS ARM64 Research Beta](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.9.0-beta.3-macos-arm64.1).

**Publication verification:** **PASS, 21 November 2026 (America/Los_Angeles).** All four assets were downloaded without authentication and verified. The downloaded app passed extraction, signature, version, native startup and normal shutdown checks.

## Exact source and release identities

| Identity | Value |
| --- | --- |
| Embedded version | `0.9.0b3` / `v0.9.0-beta.3`; bundle build `0.9.0.3` |
| Actual approved clean app and corresponding source | `05eb7b372003f177e03e65846e720260b7d3ad9c`, dirty=false |
| Separate annotated macOS tag | `v0.9.0-beta.3-macos-arm64.1` |
| Annotated tag object | `d6eac77eb84df7f1a920b1380da8217a589c4a0e` |
| Remote tag peeled source | `05eb7b372003f177e03e65846e720260b7d3ad9c` — verified on GitHub |
| Direct parent / earlier RC4 | `947e9fe12e9c851ca2ec9163451117b8914a4bec` |
| Original Phase 3 Windows baseline | `f2965cbfbddb0b839c5eb4db8e1b50d2047fa4a6` |
| Main integration merge | `87103a560928a7986c3da47c23325b40fa0a3b42` |
| Final matching local/remote main | The post-publication documentation commit containing this report; the final immutable SHA is recorded in the publication handoff. |
| README documentation commit | The same post-publication documentation commit; see this file’s Git history. |
| Scientific convention | `forward_born_dagger_g_minus_h_v1` |

The annotated macOS tag identifies the approved build-source commit, not the later integration, README or report commit. The existing Windows `v0.9.0-beta.3` tag remains unchanged. Source integration retains the approved app's source and packaging bytes; it does not rebuild or silently change the accepted app.

The internal `RC5` designation records the fifth local candidate, and the app's internal macOS `rc.1` identifier records its historical unpublished build label. These strings and the source kit's build-time documentation remain preserved. The official publication identity is the separate macOS tag above. Public renaming changes archive filenames only; app and source ZIP bytes are unchanged.

## Public assets

| Asset | Bytes | Approved SHA-256 |
| --- | ---: | --- |
| [EMCD-Sim-v0.9.0-beta.3-macos-arm64.zip](https://github.com/dingpengem/EMCD-Sim/releases/download/v0.9.0-beta.3-macos-arm64.1/EMCD-Sim-v0.9.0-beta.3-macos-arm64.zip) | 85,541,802 | `f5f752a16e524a0baf1684d0141dbd38e7772e2cf389f2111a72fc5e1da98180` |
| [EMCD-Sim-v0.9.0-beta.3-macos-arm64-Corresponding-Source.zip](https://github.com/dingpengem/EMCD-Sim/releases/download/v0.9.0-beta.3-macos-arm64.1/EMCD-Sim-v0.9.0-beta.3-macos-arm64-Corresponding-Source.zip) | 193,693,394 | `e6a8bfee304262d17833e1abf90c48d27e4c0f8d32295cf7c781296dc06fb867` |
| [BUILD_MANIFEST-macos-arm64.json](https://github.com/dingpengem/EMCD-Sim/releases/download/v0.9.0-beta.3-macos-arm64.1/BUILD_MANIFEST-macos-arm64.json) | 17,451 | `06ce2446c004806c49208f2c98c1b68499f766c222b654a5872de1b5d18cefff` |
| [SHA256SUMS.txt](https://github.com/dingpengem/EMCD-Sim/releases/download/v0.9.0-beta.3-macos-arm64.1/SHA256SUMS.txt) | 329 | `5c8883ede407fef7c332877797ad531213742e36e0a47f170fecf0e32831967c` |

The public checksum file names the actual uploaded app/source/manifest filenames. Public app/source copies were required to match the approved local archives byte-for-byte. The matching corresponding-source kit contains the application's git archive at the exact approved commit, dependency inventory, matching reviewed dependency sources, license notices and replacement instructions. The source/dependency audit found no unrelated temporary projects or research files. No existing published asset was overwritten.

## Implemented scope and focused correction

The package brings the Phase 3 headless, material-independent forward engine to Apple Silicon. Explicit structure, material/provider and geometry inputs retain BW and FFT MS, Single/Double Channeling, explicit site/group magnetic configuration, Global/Local MDFF workflows, historical Ni presets and project compatibility. The Phase 3 refactor adds no new physical model. The macOS source also retains the reviewed native resource measurements, resource admission and cooperative cancellation changes from RC4.

The reported MDFF issue was investigated through shared workspace, Global/Local editor, group editor, Viewer and main-window context paths. Native source tests on unchanged RC4 reproduced **loss of Viewer activation** after a Qt mouse press/release on Done followed by event-loop processing. The Viewer remained alive and Qt-visible; no Viewer close, reject, accept, hide, destruction or Material commit was observed in that interval. Actual closure/destruction was not demonstrated. A packaged RC4 in-process AppKit sequence returned activation successfully, so it did not establish the exact reported disappearance.

The focused RC5 correction queues a guarded raise/activation of the **existing** originating Viewer after valid Done or MDFF Cancel. It runs after the editor hides and the queued mouse-release work completes. It does not show a cancelled Viewer or steal focus from another visible MDFF context. It neither recreates the Viewer nor reloads the structure. Valid Done still stages an MDFF draft; selected group, magnetization and other Viewer edits remain intact. Complete Material acceptance still requires **Apply and Close**. Invalid Done remains in the editor with an actionable error; Cancel retains existing rollback semantics. No sleep, ownership change, always-on-top flag or automatic Material acceptance was introduced.

Only these files changed between RC4 and RC5:

- `src/emcd_sim/gui/mdff_workspace.py`: guarded queued focus handoff after valid Done.
- `src/emcd_sim/gui/mdff_usability.py`: focus handoff after Global Cancel rollback.
- `src/emcd_sim/gui/group_mdff.py`: focus handoff after Local Cancel rollback.
- `tests/test_mdff_window_lifecycle.py`: actual-button mouse regression coverage.

## RC5 validation

These results identify build source `05eb7b372003f177e03e65846e720260b7d3ad9c` and the approved candidate. They are distinct from earlier RC4 measurements.

| Check | Result / scope |
| --- | --- |
| Before-fix native regression | 3 failures against unchanged RC4 runtime source, all at original Viewer activation assertions |
| After-fix native Cocoa selection | 8 passed, including the same regression and native MDFF controls |
| Affected offscreen suite | 30 passed; 1 optional saved-result fixture skipped |
| Packaged RC5 lifecycle | 42 checks passed; 84 native AppKit mouse press/release events routed through actual Cocoa buttons |
| Lifecycle coverage | Global/Local valid Done, original Viewer alive/visible, no unintended accept/reject/close or Material commit, preserved drafts/group/M, prepared draft reopening, invalid Done, Cancel rollback, outer Apply/Cancel and ten alternating Local group edit/Done cycles |
| Native activation and stacking | Original Viewer becomes Cocoa key window and precedes main window in CoreGraphics stacking order at normal window level 0 |
| Packaged Ni smoke | BW/MS Single/Double, displayed arrays, Save/Open and CSV/NPZ/figure exports passed |
| Architecture | All 231 bundled Mach-O files support ARM64; no x86_64-only or Windows runtime binaries found |
| Packaging integrity | Fresh RC5 provenance embeds exact source, dirty=false; frozen changed-module bytecode matches committed source; ditto extraction preserves file bytes, executable modes and framework symlinks; deep/strict ad-hoc signature verifies |
| Dialog/process cleanup | Repeated edit cycles did not accumulate dialogs; all seven tracked packaged PIDs exited; app copies, RC4 bundle and RC4 archive remained unchanged |
| User manual GUI acceptance | PASSED on this exact RC5, including real mouse MDFF Done / 3D Viewer workflow |

The native packaged lifecycle automation posts in-process AppKit mouse events; it does not call `finish_edit()` or `apply_configuration()` in place of clicking Done. Offscreen tests alone do not establish native stacking. The user's completed real mouse acceptance supplies the practical user workflow verification. No unperformed external automated OS-mouse comparison is claimed.

Native environment: Apple M2 Pro, 16 GiB RAM, macOS 26.3.1; Python 3.11.16 ARM64, NumPy 2.4.6, SciPy 1.17.1/Apple Accelerate, PySide/Qt 6.12.0 and PyInstaller 6.22.3. Existing isolated dependencies were reused without package changes.

## Earlier RC4 evidence, retained with its original provenance

The source/frozen Ni [017] comparison at **RC4 `947e9fe`** found **114 arrays exactly equal (106 numeric)**, including shape/dtype, finite/NaN/Inf masks, real/imaginary components and labels. Maximum finite component error was zero. This is a matched final-RC4-source/frozen check, not the Windows saved-output comparison.

RC4's native acceptance covered help/version, memory, desktop, grouping, provider/release, multisite, cancellation and scientific profiles, plus extracted-archive LaunchServices opening and a genuine historical Ni saved project. Its bounded memory matrix exercised Auto and safely admitted Manual one/two workers, repeated result replacement, cancellation/restart and native RSS/footprint observations. It does not certify arbitrary workloads, four-worker manual calculations, general convergence or calibrated spectra.

Those earlier numerical/memory results were not rerun or relabeled as RC5 results. RC5 changes no scientific kernel, numerical tolerance, memory admission, cancellation or project-format contract. The complete regression and broad memory audit were not repeated. The Windows **1,763-array comparison was not run on this Mac** because the approved Windows reference artifacts were not available. No unmatched Windows/macOS measurements are used to claim improved performance or memory efficiency.

## Public download and homepage verification

All four assets returned HTTP 200 without authentication. Their downloaded sizes and SHA-256 values match the table above, GitHub's asset digests, the staged public copies and, for the app/source ZIPs, the approved RC5 archives. Every entry in the public checksum file passed.

The downloaded source/dependency kit identifies the approved commit in its inner git archive comment. All **832 application-source files** exactly match that commit's git blobs, with no extra application files; all 19 source-kit checksum entries passed. The kit contains reviewed matching Qt/PySide, ASE and GCC/libquadmath sources, dependency inventory, notices and replacement instructions.

The downloaded app was extracted with `ditto`. Its **1,091 file/symlink inventory entries** exactly match the approved RC5 inventory, including file bytes, executable modes and framework symlink targets. All **231 Mach-O files support ARM64**. `codesign --verify --deep --strict` passed. Running the downloaded executable from `/private/tmp` returned the approved version/source and dirty=false. A separate normal GUI launch with isolated QA user data displayed the native EMCD-Sim main window. A normal application termination request completed with exit 0, leaving no process for that copy.

The source integration merge is `87103a560928a7986c3da47c23325b40fa0a3b42`, with the approved build source as its second parent. Runtime and packaging files are identical to the approved source. Focused integration checks passed **41 tests, with 2 expected skips** (a native Windows-only check and an optional saved-result fixture). No rebuild was performed.

Before marking publication complete, verify every release asset in a separate download directory against its approved size and SHA-256, verify the remote tag peel and source-package identity, and extract the publicly downloaded app with ditto. Confirm bundle structure, executable permissions, symlink targets, deep/strict signature integrity, embedded version/source and minimal startup. Record actual results here or in the public build manifest, distinguishing download integrity from clean-machine/quarantined installation.

The homepage update follows successful public download verification. It points macOS users to this beta.3 release, describes the Viewer correction and links this report. Existing Windows downloads, earlier macOS releases and historical version/context labels for benchmarks remain intact.

The homepage, installation and Quick Start changes are separate documentation updates after successful public-download verification. They link this release, its direct app download and this acceptance report. Their commit does not identify a different application build; the exact application source remains the annotated tag above. Final post-push rendered-homepage verification is recorded in the publication handoff.

## Installation and scientific limitations

The app is **ad-hoc signed, not Developer ID signed or notarized**. Clean-machine/quarantined-download installation remains untested. A verified public download and successful startup on the development Mac do not establish Gatekeeper acceptance on another machine. See [macOS installation](INSTALL_MACOS.md) and [macOS Quick Start](QUICK_START_MACOS.md); retain the full application bundle.

This is a Research Beta, not calibrated quantitative spectroscopy. Projected IAM/ZOLZ, finite beam/FFT/depth/detector support, localized independent ionization and the documented transfer assumptions remain. General convergence is unestablished. Synthetic/effective MDFF fixtures do not validate absolute cross sections, calibrated Fe₃O₄/NiFe₂O₄ spectra or magnetic moments. CIF import does not infer magnetic order. Existing small-window plot-title clipping, elided tabs and Matplotlib layout warnings remain; enlarge Viewer/results as needed.

Next-Gen depth events, convergent probes, scanned STEM-EMCD, general tensor rotation/magCIF and GPU execution remain future work. Publication did not begin Next-Gen B1. See the [scientific limitations](../README.md#scientific-limitations) and [Next-Gen design documentation](NEXTGEN_A_IMPLEMENTATION_ROADMAP.md).

No scientific kernel, tolerance or reference-array change, app rebuild, force-push, history rewrite, earlier tag movement, Apple credential request, notarization upload or system-security change was part of this publication. Previous Windows/macOS releases, RC4/RC5 evidence, projects, stashes and unrelated local work were preserved. All 12 earlier GitHub releases and their assets were compared before/after publication and remained unchanged; every pre-existing remote tag was unchanged. The 76 files in the user’s untracked `test/` directory and four unrelated unstaged test-file deletions were preserved. A recovery stash for those deletion intents was retained. No installed application was replaced.
