# Phase 3 Windows Public Research Beta — Candidate Acceptance

**PUBLISHED — AUTOMATIC AND MANUAL ACCEPTANCE PASSED**

The user explicitly confirmed PASSED manual GUI acceptance of the exact
candidate below and authorized publication without another confirmation.
The prerelease is published. All five public assets were downloaded without
authentication and verified against approved sizes and SHA-256 values.
A clean-machine test has not been performed. Homepage verification and the
final documentation commit identity are recorded at handoff.

## A. Release and source identity

| Identity | Exact value / state |
| --- | --- |
| Version / platform | v0.9.0-beta.3 / 0.9.0b3 / Windows x64 |
| Absolute working directory and Git worktree root | C:/Users/peng863/EMCD-Sim |
| Branch | main |
| Accepted integration before release preparation | 53637717c13f96718fca188138d3541ac0d5fc5f |
| Phase 3 / Next-Gen A merges retained | 46136856f9c8af56502a7dcc752bde2b6cd943ed / ff64d739375dfdbcb903105c365f9b0f1ca393ae |
| Accepted complete-regression source | a97ccf14e890b9e52fc57d47261117717825f5ba |
| Release metadata implementation | e21dd81eaefde7072fd90cb59e276c27b367fce5 |
| Native-QA version correction implementation | cc79262f50a9a17c541cea5af219beb255f0c058 |
| **Actual clean EXE / source archive / required tag source** | **f2965cbfbddb0b839c5eb4db8e1b50d2047fa4a6** |
| Local main during build and automatic QA | f2965cbfbddb0b839c5eb4db8e1b50d2047fa4a6 |
| Prepublication documentation main | 3091cd6eb0b72b9dc56aaafed14d07b027fd6d39 |
| Final public main / README commit | This post-publication documentation update; exact matching local/remote SHA recorded after push in release_provenance.json and the final response |
| Published annotated tag | v0.9.0-beta.3; object **9abfa61af50959df3b7b84b892cee1f3bbe3dc3c** |
| Scientific convention | forward_born_dagger_g_minus_h_v1 |
| Final stabilized Phase 3 implementation | 41e376c3b891df2ef225c43a5db0e1f6bc1794b8; calculation source preserved |

Git confirms every file under src is identical to the first release candidate
24dcb536a46c77a84eee4ebfca29d06caad2d0c2. Relative to accepted integration
5363771, only two version strings in src/emcd_sim/__init__.py changed under src.
Scientific equations, kernels, settings, arrays and tolerances were not changed.
The existing kernel/reference pins and historical registration bytes remain intact.

Release work changes necessary package/PE/CI metadata, documentation, two
metadata-test functions and existing registration bookkeeping. The Windows
workflow now supplies its previously missing mandatory CorrespondingSourceRoot
from the unchanged verified Qt sources and creates application source from the
actual build commit. The later embedded QA-only correction is described below.
No new hash framework or scientific reference baseline was introduced.

### Clean build and environment

The existing packaging/build_windows.ps1 completed in **938.784 seconds**,
exit 0. Build UTC: **2026-11-21T21:47:37.529396+00:00**. It used a fresh
committed Git archive snapshot, fresh PyInstaller work/dist directories and an
isolated alternate index. The checkout, branch and ordinary index were not moved.

Python 3.11.17, NumPy 2.4.6, SciPy 1.17.1, Matplotlib 3.11.2, PySide6/Qt
6.12.0, PyInstaller 6.22.3, ASE 3.29.0 and spglib 2.7.0 were unchanged.
Interpreter: C:/Users/peng863/EMCD-Sim/build/windows-rc/venv/Scripts/python.exe.
Recorded host: Windows-10-10.0.26200-SP0. These are traceable clean build inputs;
byte-identical reproducibility of repeated builds was not separately certified.

Only **817 tracked files** entered the source archive. Its Git commit comment
and all source bytes match the snapshot. Package audit verified 111 runtime
source identities, 107 embedded source origins, 108 embedded application/QA
modules, eight scientific data files and ZIP integrity. Checked source origins
belong to the new snapshot. Tracked-path and credential-pattern review found no
private release input; unrelated stash/untracked research/HPC files were excluded.

## B. Exact local artifacts

Artifact directory: `C:/Users/peng863/EMCD-Sim/build/rb3-f2965cb`.

| Artifact | Exact filename | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Windows ZIP | EMCD-Sim-v0.9.0-beta.3-Windows.zip | 106,110,039 | `da12fff50ec062f9c1054c40cf34b0435924d3091dfd99f31e44fe6ea4c1089e` |
| Application corresponding source | EMCD-Sim-v0.9.0-beta.3-Corresponding-Source.zip | 27,169,928 | `46f63c5d5b1efd64dd34576a8d50912b7e4ec6c21cdbdf850925e0db64aafe96` |
| Qt corresponding-source kit | EMCD-Sim-v0.9.0-beta.3-Qt-Sources.zip | 102,753,129 | `b8691e67a8b0938e64151cc898ac2188ce4c6a9a897c5e90fecc004e5af4aba6` |
| Build manifest | build_manifest.json | 219,024 | `974958b82ae3b02a9a2781bb3825a9046cd3c3d32f4f72c309a87c568169a1aa` |
| Checksums | SHA256SUMS.txt | 409 | `4f5e0e6c97f54bc8f42213f3652fa7e005ab11cc8f494dc1fe04fe945031dcb6` |

Manual-test EXE:
`C:/Users/peng863/EMCD-Sim/build/rb3-extracted-f2965cb/EMCD-Sim/EMCD-Sim.exe`.
Bytes: **14,833,682**. SHA-256:
`3a7aae3322e3c5752fdc87f6c58b99a187328289aa95fdafdad99d5aa4fc3f8b`.
PE FileVersion/ProductVersion: **0.9.0.3 / v0.9.0-beta.3**.

The Windows ZIP is an onedir distribution: extract the complete EMCD-Sim folder,
retaining its adjacent _internal directory. Do not distribute the EXE alone.
The application source ZIP is a byte-exact public-name copy of the builder's
corresponding-source/EMCD-Sim-source.zip. The Qt kit contains that same
application snapshot and five pinned matching Qt/PySide/Shiboken source archives.
Licenses, notices, source inventories and replacement instructions were verified,
covering 34 Qt binary components, 99 translation catalogs and 41 required assets.

All 653 inventoried distribution files plus the distribution SHA256SUMS.txt
verified in the fresh extraction. After native execution, all 653 files and
artifact identities remained unchanged, with no extra distribution files.

The public SHA256SUMS.txt covers the three ZIPs and frozen build_manifest.json.
The separate release_provenance.json records post-build status and the later
documentation commit. This keeps the EXE source distinct from its report.
Packaged notes describe their build-time state; this report and the updated
repository release notes are documentation-only successors.

## C. Acceptance and numerical evidence

| Evidence | Actual tested source / independent provenance | Result |
| --- | --- | --- |
| Existing uninterrupted complete regression | a97ccf14e890b9e52fc57d47261117717825f5ba, integrated into accepted main | 1,824 collected; 1,762 passed; 62 exact existing skips; zero failures/errors |
| New release preflight | 24dcb536a46c77a84eee4ebfca29d06caad2d0c2 | 27 passed: metadata/packaging/source guards, kernel identities, canonical/headless interfaces and six corrected numerical contracts |
| Affected QA-registration checks | f2965cbfbddb0b839c5eb4db8e1b50d2047fa4a6 | 3 passed in 94.68 pytest seconds: current/historical positive, manifest mutation negative and historical-identity preservation |
| New pre-refactor source comparison | Release source 24dcb536 vs cdb8836388c5ccc5ae7a614b47894c0ab158a824 | **22 cases / 2,294 arrays exactly equal** |
| New final EXE saved-output comparison | Actual f2965cb EXE vs independent Phase 2 frozen source 6d98694b2367fdb9586f33287f9a09c159c7ef27 | **19 projects / 57 NPZ / 1,763 arrays exactly equal**, including 448 NaN-bearing arrays |

These are separate invocations with separate provenance. The complete regression
was not restarted for release metadata or the QA-only assertion correction.
The 22-case driver's bootstrap root was relocated in memory to the current
checkout, with actual imports/version verified; no historical driver on disk,
settings or references changed. Final Git review proves all src bytes identical
between that release comparison and the final candidate.

The new frozen comparison uses independent earlier saved outputs, not expected
arrays generated by this EXE. Both project manifests validate and both project
generations load without recalculation. Shapes, dtypes, decoded values, finite
and NaN masks and real/imaginary components compare exactly.

The preserved raw comparison flags 14 inactive inherited atomic-dict to None
metadata differences and two Fe imported-source checksum differences.
native-reference-review.json checks the exact previously reviewed 14-case set,
proves current src identical to reviewed Phase 3F-2 source except the two version
strings, and verifies that the two tensor JSON files differ only in
atomic_parameter_path while original parameter files are byte-identical.
Seventeen source hashes match directly. All effective physical inputs and all
1,763 arrays match. No numerical assertion, tolerance or reference was weakened.

### Actual final native execution

Every profile ran the freshly extracted final EXE on native Windows Qt with
empty PYTHONPATH, PATH restricted to the bundle/Windows directories and isolated
workspace/user/cache directories. All frozen reports identify f2965cb / 0.9.0b3.
File-picker choices are automated; these runs do not constitute human approval.

| Profile | Launch-to-exit seconds | Observed final result |
| --- | ---: | --- |
| native-help | 6.073 | CLI help and clean exit |
| native-release-help | 5.600 | Release-acceptance CLI help and clean exit |
| native-startup | 11.100 | Main window, default diffraction preview and clean shutdown |
| native-desktop | 73.686 | Ni [017] BW/FFT Single/Double, About/version, numerical controls, Save/Open and exports |
| native-providers | 435.869 | 14 Ni/Fe/O provider/full-edge + 2 manual-spectral cases; source preview, restoration/recalculation, tamper rejection and exports |
| native-grouping | 118.600 | 56-atom Fe3O4 structural grouping/persistence; Cr reversal, MDFF Apply/Cancel, invalid-axis rejection and Global-M lock |
| native-multisite | 607.514 | 10 Ni/Cr/synthetic Fe3O4-motif calculations; normalization, CSV, history, comparison, delete, Save As and reopen |
| native-resources | 22.136 | Actual four-worker calculation, memory admission, exact saved arrays and restored resource settings |
| native-cancellation | 38.145 | All nine cases, queued completion, immediate restart and saved-result integrity |
| native-scientific | 10.095 | Explicit Ni [017] raw/reversal Single/Double x BW/FFT, canonical callable and decomposition checks |
| native-desktop-dpi100 | 69.216 | Desktop workflow with process-only Qt scale 2/3, effective DPR 1.0 |

Every applicable completion/closed-window assertion passed. Cancellation uses
its own outcome/restart/integrity PASS fields and nine individual case outcomes.
Final native logs contain no exception traces. No final profile timed out or
required forced termination: Windows jobs recorded no remaining owned
descendants before cleanup. A final path-filtered query found no candidate GUI
process.

The resource profile requested/used four BW workers, retained the original
2,048 MiB memory request/allocation, restored settings and preserved arrays
after deliberate unexecuted edits. Both NumPy/SciPy runtimes used one BLAS
thread. Existing conservative risk/admission messages remain: a bounded passing
case does not certify every resource/geometry combination.

Final-candidate screenshots actually opened include startup, desktop double_maps
export, Global Fe MDFF preview, full Fe3O4 structural groups, Local Cr manual
pair, Fe3O4-motif results, resource controls, cancellation restart and the
effective-DPR-1.0 Double result. Populated results, physical units, source context
and available controls render. Existing narrow-panel clipping and scrolling
limitations remain; standalone map exports render complete titles/axes/legends.

### Superseded first candidate and smallest correction

The initial 24dcb536 source/artifacts remain preserved under build/rb3-24dcb53
and the initial release evidence root. It is **not accepted** and must not be
used for manual approval/publication. Its multisite profile stopped before any
calculation because packaging/native_acceptance.py compared the recorded
version with the obsolete literal 0.9.0b2.

The correction imports authoritative package __version__ in that profile and
retains strict exact version equality. It changes no scientific assertion.
Existing source-registration entry/pin and committed production pointer were
updated, preserving all historical bytes and kernel/reference identities.
A fresh committed snapshot/build followed. All 11 final native profiles,
package/source audits and independent frozen comparison above ran against
the replacement binary; no earlier native pass substituted for them.

### Known scientific, visual and host limitations

* Projected IAM/ZOLZ, dipole/local independent-event and documented longitudinal
  transfer assumptions remain; no arbitrary atom-resolved 3D inelastic event
  model is implied.
* Beam/FFT/depth/detector supports are finite. Bounded fixtures do not certify
  arbitrary material, geometry, thickness or convergence.
* Signals remain relative/arbitrary units, without absolute cross-section,
  electron-count, magnetic-moment, experimental noise or SNR calibration.
* Synthetic Cr/Fe3O4 fixtures validate software/scientific consistency, not
  experimental spectra. CIF import does not infer magnetic order.
* The full 56-atom Fe3O4 check is structural/grouping validation. The original-size
  Fe3O4 multislice workload remains unverified.
* Arbitrary tensor rotation, magCIF, coherent/nonlocal intersite excitations,
  thermal/absorptive and new non-dipole models remain outside supported scope.
* Authentic direct macOS BW-Double/MS-Single/MS-Double raw-array comparisons
  remain **INCOMPLETE**; macOS beta.1 source/assets are unchanged.
* Native QA was on the recorded development host. A clean Windows PC/VM and
  multi-monitor testing were not performed. The documented external Microsoft
  x64 VC++ runtime prerequisite and unsigned Research Beta status remain.
* Existing narrow-panel geometry-title clipping, elided text and tall-plot
  scrolling remain. Matplotlib layout warnings are recorded.
* Depth-localized events, convergent-beam/real-space STEM-EMCD, scalable storage
  and GPU/HPC implementation are future Next-Gen work, not beta.3 capabilities.

Old projects retain their arrays and original physics/source provenance;
loading does not silently recalculate or relabel conventions.

## D. Manual acceptance and GitHub publication

**Manual GUI approval: PASSED. Publication: COMPLETE. Public assets: VERIFIED.**

The user explicitly confirmed acceptance of the exact candidate in publication
request a04ee861-63d2-4888-9a8b-3803c27a5cbc, covering startup/navigation, Ni
BW/FFT results, Global/Local MDFF Apply/Cancel, Save/Open/restoration, exports,
and cancellation/restart. The approved ZIP and EXE have not been rebuilt or
replaced. A clean Windows PC/VM remains recommended and untested.

| Publication item | Verified identity / state |
| --- | --- |
| Repository | dingpengem/EMCD-Sim; authenticated dingpengem owner/push access |
| Initial normal main push | 8bd06771c60014f33175b0f4b96ca334fc17ffc6 → 3091cd6eb0b72b9dc56aaafed14d07b027fd6d39 |
| Annotated tag | v0.9.0-beta.3; object **9abfa61af50959df3b7b84b892cee1f3bbe3dc3c** |
| Remote peeled source | **f2965cbfbddb0b839c5eb4db8e1b50d2047fa4a6** |
| Prerelease | [v0.9.0-beta.3](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.9.0-beta.3), ID 454159968 |
| Direct Windows download | [Approved Windows ZIP](https://github.com/dingpengem/EMCD-Sim/releases/download/v0.9.0-beta.3/EMCD-Sim-v0.9.0-beta.3-Windows.zip) |
| Published UTC | 2026-11-22T03:12:23Z |
| Public downloads | All five assets downloaded without authentication; exact bytes/SHA-256 match section B |
| Existing releases/assets | 11 releases / 36 assets preserved by ID, target, size and digest after publication at 2026-11-22T03:15:32.270Z |
| Existing Windows beta.2 / macOS | Untouched; macOS remains v0.9.0-beta.1-macos-arm64.1 from its separate source |

Five assets were uploaded to a prerelease draft and all server digests matched
the approved local files before publication. After publication, every asset
was downloaded into the separate publication/public-downloads directory.
All four downloaded checksum entries passed. The downloaded manifest and
application source archive identify f2965cb. The EXE inside the downloaded
Windows ZIP matches the approved EXE SHA-256.

Only after public-download verification were README's primary Windows link,
Phase 3 validation summary, release/report links and four Next-Gen A links
updated. The macOS download, benchmark evidence and scientific limitations are
preserved. The README's existing current-source registration entry and required
bootstrap pin are maintained through the existing mechanism, preserving all
historical bytes and scientific pins.

The rendered homepage is checked after this documentation update's normal push.
The exact final README/local/remote main SHA and served-homepage verification
result are recorded after push in release_provenance.json, local publication
evidence and the final response. The annotated source tag remains f2965cb;
the homepage/report commit does not identify a different EXE.

## E. Git safety and local handoff

The checkout remained clean at f2965cb throughout automatic acceptance.
At the candidate gate it was 67 ahead / 0 behind origin/main before the
prepublication report commit, which produced 3091cd6. Publication fetched again,
confirmed no divergence and normally pushed main. The final documentation-only
README/report successor is also pushed normally, with exact matching local and
remote identities recorded at handoff.

Protected unapplied stash:
`9191d6439615675124d944533ceb21e66c72fda3`, unchanged.
No apply/pop/drop, checkout move, reset, remerge, force-push or history rewrite
occurred. Only authorized main and the beta.3 tag were pushed. Phase 3 and
Next-Gen A branch/worktree identities are preserved. No unrelated research
files were staged or included in source archives.

Final evidence root:
`C:/Users/peng863/EMCD-Sim/build/phase3-windows-public-release/rebuilt-f2965cb`.
The candidate directory retains package-verification.json,
final-automatic-review.json, raw/reviewed independent comparisons, saved
projects and screenshots. The publication subdirectory records approved input
verification, draft/uploads, public downloads, tag identity, old-release
preservation and homepage verification. Initial 27-check/22-case evidence and
the superseded failure remain in the parent release evidence directory.

Existing main-push CI workflows are automatic. No additional workflow was
dispatched, no new full-suite acceptance is claimed, and no CI-produced artifact
replaced the approved release. Only the affected documentation registration
checks are run locally for the README update.

Post-publication documentation checks passed: two existing registration tests
in 74.50 pytest seconds, plus successful in-memory README mutation rejection by
both existing source guards. Historical registration bytes and scientific pins
are unchanged; only the current README digest and its required bootstrap pin
were updated. No test assertion or scientific setting changed.

## F. Future development baseline

Accepted published scientific source:
**f2965cbfbddb0b839c5eb4db8e1b50d2047fa4a6**.

Future feature/nextgen-b1-depth-events work should start from current main
containing this source and the verified publication/README documentation.
The exact final main/README SHA is recorded in the handoff and
release_provenance.json. The source tag continues to identify f2965cb.

No B1 branch, new physics, package restructuring, GPU/HPC implementation,
reference replacement or unrelated cleanup was performed.
