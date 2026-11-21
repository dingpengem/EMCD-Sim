# Phase 3 Windows Public Research Beta — Candidate Acceptance

**RELEASE CANDIDATE READY — AWAITING MANUAL GUI APPROVAL**

Automatic preparation and acceptance are complete for the exact candidate below.
Human GUI acceptance has not been provided. Public release GO remains pending:
no push, tag, draft release or publication has occurred. A clean-machine test
has not been performed.

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
| Documentation handoff main | The documentation-only commit containing this report; exact SHA is recorded after commit in release_provenance.json, candidate.json and the final handoff |
| Final public main | Pending manual acceptance, publication and the verified-link README update |
| Proposed annotated tag | v0.9.0-beta.3; verified unused; **not created** |
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

## D. Manual approval and GitHub publication

**Manual GUI approval: NOT RECEIVED. Publication: NOT PERFORMED.**

Extract the whole new Windows ZIP to a separate folder and manually verify:

1. Windows application startup.
2. Normal main-window appearance and navigation.
3. Ni BW/FFT calculation and result display.
4. Global/Local MDFF editing and Apply/Cancel.
5. Project Save/Open and restored results.
6. CSV/NPZ/figure exports.
7. Cancellation and subsequent restart.

Confirm the exact ZIP SHA-256 shown in section B. A clean Windows PC/VM is
recommended if available; it has not been tested. A different rebuilt ZIP
requires renewed acceptance. The gate comes from the supplied release request,
section 7; automated QA and historical approvals do not satisfy it.

| Publication item | Current state |
| --- | --- |
| Repository | dingpengem/EMCD-Sim; authenticated ownership/access verified |
| Refreshed origin/main | 8bd06771c60014f33175b0f4b96ca334fc17ffc6 |
| Proposed tag / required source | v0.9.0-beta.3 / f2965cbfbddb0b839c5eb4db8e1b50d2047fa4a6; tag absent |
| Release URL / verified public download | Pending manual acceptance and publication; no new public URL claimed |
| Public README download links | Unchanged until publication/download verification |
| Existing public releases/assets | 11 releases / 36 assets unchanged by ID, source target, size and digest at 2026-11-21T22:38:48.667Z |
| Existing Windows beta.2 / macOS | Untouched; macOS remains v0.9.0-beta.1-macos-arm64.1 from its separate source |

After explicit acceptance: revalidate source/artifact/remote identities, normally
push main, annotate/tag the **actual build source**, publish the prerelease and
all ZIPs/manifests/checksums, download and verify public assets, then update/push
README links. Later homepage/report commits must not be mistaken for the EXE
source. No unchanged EXE rebuild is needed for a homepage-only update.

## E. Git safety and local handoff

The checkout remained clean at f2965cb through all automatic checks. A fresh
fetch found main **67 ahead / 0 behind** origin/main before this report's
documentation commit. That documentation-only successor adds one local commit;
clean status is verified at handoff. Its exact SHA is recorded in local
release_provenance.json/candidate.json and the final response, and is resolvable
with `git log -1 --format=%H -- docs/PHASE3_WINDOWS_PUBLIC_RELEASE.md`.

Protected unapplied stash:
`9191d6439615675124d944533ceb21e66c72fda3`, unchanged.
No apply/pop/drop, checkout move, reset, remerge, force-push, history rewrite,
tag creation, push, release creation or publication occurred. Phase 3 and
Next-Gen A branch/worktree identities remain preserved. Source archives contain
only reviewed tracked inputs and exclude unrelated local research work.

Final evidence root:
`C:/Users/peng863/EMCD-Sim/build/phase3-windows-public-release/rebuilt-f2965cb`.
Each build/native/verification stem has exact argv/environment, source identity,
start/end, exit, PID ownership and source-cleanliness records and logs.
candidate-f2965cb contains package-verification.json, final-automatic-review.json,
raw/reviewed comparisons, saved projects and screenshots. Initial 27-check and
22-case evidence plus the superseded failure remain in the parent release
evidence directory.

## F. Future development baseline

Proposed accepted release source:
**f2965cbfbddb0b839c5eb4db8e1b50d2047fa4a6**, subject to manual acceptance
and publication. After those gates, create feature/nextgen-b1-depth-events from
then-current main containing this source and verified publication/README
documentation. Record the final public main SHA at that time. The source tag
continues to identify f2965cb.

No B1 branch, new physics, package restructuring, GPU/HPC implementation,
reference replacement or unrelated cleanup was performed in this release task.
