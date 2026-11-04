# v0.8.0-beta.1 Windows-only Research Beta acceptance

All essential local Windows release gates passed. This report describes the extracted standalone application and the Windows source suite. It does not certify Linux/macOS, independent clean-machine installation or quantitative experimental accuracy.

## Source and build identity

- Exact accepted EXE source and intended `v0.8.0-beta.1` tag target: **`bc22a4b04c828efad027140e94039464fed06641`**.
- Baseline main: `87e95f69bf19977d5eec5e0f193e781b1daba898`; fresh fetch matched before preparation.
- Version: Python `0.8.0b1`, display `v0.8.0-beta.1`, Windows numeric `0.8.0.1`. Clean committed source: embedded `dirty=false`.
- The tag targets the build source above, not this later reporting commit. No binary was reused from v0.7.0; a new isolated PyInstaller build and new archive were created.
- Runtime Python: `3.11.17`. Build UTC: `2026-11-04T05:40:37.143288+00:00`.
- Source changes under `src/emcd_sim` versus baseline are only version metadata and the opt-in native acceptance harness. **No Ni MDFF/EMCD/event kernels, elastic computation, physics conventions, provider coefficients or numerical defaults changed.**

|Build dependency|Version|
|---|---|
|numpy|2.4.6|
|scipy|1.17.1|
|matplotlib|3.11.2|
|ase|3.29.0|
|PySide6|6.12.0|
|pyinstaller|6.22.3|

## Windows source regression

Complete `python -m pytest tests -q -p no:cacheprovider -o faulthandler_timeout=180` using the Python 3.11 Windows build environment and offscreen Qt: **664 passed, 40 skipped, 0 failed, 0 errors** (704 collected, 919.30 seconds). The log retains 891 warnings, including Matplotlib collapsed-layout and Qt deprecation warnings. The optional external legacy table was configured outside the checkout; it was never copied into the repository or package. Source contents match the accepted commit. The preliminary source-native run also passed 12/12 checks before the clean build.

The suite includes provider units/Fourier scaling, all-element coverage, original Lobato constructor and historical references, full XF/Mott low-g guard, external missing-table diagnostics, weighted extinctions/CsCl (100), non-FCC indexing, bounded BW/MS cases, Hermitian potentials, provider persistence and Ni-only eligibility. Skips are reported rather than counted as passes:

- 3: Full benchmark outputs are not complete
- 3: Full checkpointed thickness calculation still incomplete
- 3: Local MS validation outputs not generated
- 2: Local four-point benchmark not generated
- 1: Local legacy reference project unavailable
- 8: Optional GUI and existing real Stage D results required
- 1: Optional external 160-array evidence unavailable; set EMCD_UNIT_IDENTITY_DIRECTORY
- 1: Optional historical saved project is unavailable
- 1: Optional local WIEN2k companion audit; original files are not distributed with the package
- 1: Optional real saved Ni project unavailable
- 1: Optional saved GUI reference unavailable
- 6: Optional saved angular references unavailable
- 1: Optional saved benchmark unavailable
- 1: Optional saved result fixture unavailable
- 1: Optional stored GUI reference
- 1: Pinned offline HDF5 inputs unavailable
- 1: Requires original local WIEN2k audit companions; not distributed
- 1: Saved BW/MS fixture not available; never run a fallback simulation
- 3: Saved project fixture unavailable

## Actual extracted-EXE native acceptance

Extracted the newly built ZIP, then launched that extracted `EMCD-Sim.exe` with `QT_QPA_PLATFORM=windows`, PATH restricted to Windows/System32 and Windows, and Python/Conda/plugin-path variables removed. The real Qt window, application workers, CIF dialogs, save/open controls and click handlers ran. **12/12 checks passed; actual process exit code 0; all workers stopped; no recorded application/native crash.** Native run completed `2026-11-04T05:48:22.6732711Z`.

|Native check|Result|
|---|---|
|application_version|PASS|
|bundled_all118_and_notices|PASS|
|default_ni_worker_preview|PASS|
|native_save_reopen_elastic|PASS|
|genuine_historical_project|PASS|
|bcc_fe|PASS|
|cscl|PASS|
|hex_zno|PASS|
|monoclinic|PASS|
|missing_external_provider_diagnostic|PASS|
|ni_native_mdff_and_full_project_roundtrip_single|PASS|
|ni_native_mdff_and_full_project_roundtrip_double|PASS|

Rendered/clicked indices were compared to independently constructed reciprocal coordinates for BCC Fe, CsCl, hexagonal ZnO and monoclinic Si/O. Fe (100) remained extinct; CsCl (100) survived. Each non-Ni CIF ran an elastic worker and retained a disabled Ni-specific EMCD button. Default Ni elastic diffraction and elastic project save/read-only reopen passed.

The genuine historical Ni project had no provider field. It restored **Ni Lobato**, matched archived beam ordering and elastic amplitudes with maximum absolute error **0.0**, preserved saved array fingerprints and original project-manifest SHA256 `57c81a23675aa14268a44441fda0ff3909602432cab7345c554f2423ccd5e80d`, and saved/reopened a separate copy. Missing old convention metadata remains explicitly legacy-unverified; no arrays were relabeled or silently migrated.

- Single Channeling: two native Ni energy samples, nonzero magnetization-odd signal, all four raw detector spectra finite, magnetic/even decomposition checked independently from those arrays, exact saved-array fingerprints preserved. Flip-M A values: `[7.630053039029208e-05, -8.214200755131407e-05]`.
- Double Channeling: two native Ni energy samples, nonzero magnetization-odd signal, all four raw detector spectra finite, magnetic/even decomposition checked independently from those arrays, exact saved-array fingerprints preserved. Flip-M A values: `[0.00014899607814099214, -0.0001604007598047033]`.

These are bounded two-energy, 1 nm functional smoke calculations, not regenerated full-spectrum studies or a convergence campaign. Single and Double numerical regression coverage comes from the source suite; the native checks additionally exercise the real packaged application.

## Packaging, licenses and archive

All **613 manifest file sizes and SHA256 digests** matched after extraction and again after native acceptance. The additional internal SHA256SUMS file matched its expected records. The native application verified the bundled factor at g=0, very small positive g and supported upper limit for every Z=1–118. No missing coefficient data, Python modules, DLLs or runtime data errors occurred in these tests.

|Artifact|Bytes|SHA256|
|---|---:|---|
|`EMCD-Sim-v0.8.0-beta.1-Windows.zip`|108652577|`eec12e9ed4d102cb4ae3ff46871f53e199bd9a63d7a9f4dd233eccb4eafc023f`|
|`EMCD-Sim.exe`|14169875|`0800be09ae2bebed6873a0b106f79b6bd5b1db6578c69758f0fb9ca19c46bb91`|
|`build_manifest.json`|182676|`ae8f4f6049214edda8c82c7b29e6102c597dcb3918663d35dba61549e4bb02ba`|

The build manifest records the exact source, clean state, dependencies, source hashes, coefficient provenance and every packaged file. ZIP/SHA256SUMS are the version-specific release assets; the manifest is supplied as an additional provenance asset.

The ASE CIF imports and space-group database are included. The Adaptive runtime uses the extracted JSON coefficient subset and requires **no h5py dependency or upstream HDF5 archive**; therefore there is no missing runtime HDF5 dependency. Offline upstream HDF5 extraction comparisons are separate validation, not application requirements.

EMCD-Sim code remains MIT. The coefficient subset is Apache-2.0 with the complete pinned upstream LICENSE, copyright/attribution NOTICE, modification statement and provenance. Upstream commit: `1667babb2c5bdb44a0535438b846eb1bbfbc03ac`; bundled coefficients SHA256 `a67788f59b426c07cf27913e023ed08e3a748fdb6b634d0bb5eed6b4ecf77b5c`. The upstream license was checked again during release preparation. License metadata preflight covered all 17 required distributions. The unlicensed legacy Z=1–98 table is absent from Git and the package; the external adapter is optional and its absence does not break either bundled provider. Its original redistribution permission remains unestablished.

## Documentation and preserved results

README, installation, Quick Start, Tutorial, User Guide, Changelog, physics/provider documentation, packaging guidance and new release notes describe the Windows release and Adaptive default. Historical screenshots are explicitly labeled. **Raw EMCD a.u. remains the primary README example; normalized asymmetry is supplementary.** The existing recalculated 9/30 nm Ni arrays, figures and provenance are unchanged and remain identified with original Lobato. No historical outputs/checkpoints were overwritten and no large study was rerun.

The prepublication audit checked 122 tracked Markdown files and 508 references: no new missing local target/anchor. Five pre-existing links in historical physics acceptance reports remain unresolved; a literature publisher returned HTTP 403. The new release page, two download links and this main-branch acceptance URL were intentionally pending publication and must be verified after push/publication. Existing main README rendering retained raw-before-percent, historical Lobato and Adaptive coverage text. Final public-link and asset verification is recorded separately after publication.

## Limits and platform status

- **Numerical compatibility:** unchanged original Lobato implementation and historical project controls passed. New GUI/provider-factory calculations default to Adaptive; select Lobato explicitly for historical reproduction. The unversioned Python constructor remains Lobato.
- **BW/MS convergence:** only selected matched finite-basis elastic cases are covered; no broad convergence claim.
- **Quantitative physical accuracy:** neutral IAM omits bonding/ionic charge transfer; projected finite-ZOLZ and approximate Ni MDFF retain their limits. Experimental quantitative accuracy and absolute magnetic handedness remain unverified.
- **Windows functionality:** tested on the development Windows host with a cleaned runtime environment. Independent clean-machine installation, signing and arbitrary hardware/configuration coverage remain unverified.
- **Linux:** unresolved Python interpreter-shutdown `bool_dealloc` abort. **macOS:** Qt modal preflight dialog stalls the runner. Existing CI failures were not suppressed or debugged for this task. No Linux/macOS package or cross-platform certification is claimed; these failures are not Windows-only release gates.

## Local evidence inventory

Evidence remains in the isolated release worktree under ignored `outputs/v080b1-release/`; the public report records their digests rather than committing generated scientific or binary outputs.

|Evidence (relative to that directory)|SHA256|
|---|---|
|`source-tests.xml`|`7ebc62346d2f9134c5570ca5badbb44d1302162fcf02e8231c29af75bdc962b4`|
|`exe-native/acceptance.json`|`55e1512df731b1c940a399516e44ec863bf2e23882ceff51b537ca9a2a112dca`|
|`native-launch.json`|`8a227fca7b41b3a598b06ed1215cfb0cc3cd332ba56401ec8269b848531ad7f3`|
|`package-verification.json`|`62197ba874b1e0c34779aaac1edb82ad1df827105535fc3f1f3b6c733078c6fb`|
|`push-verification/markdown_link_audit.json`|`57110ab7fd817835669f8c245d4addd6b1ab303a838fac9b0aa52f6964cc7646`|

The previous v0.7.0-beta.1 release is preserved. Publication is authorized only as a GitHub **prerelease** after all Windows gates above; normal pushes and a new exact-source tag are used. No old asset is replaced and no stable/latest release is requested.

## Publication and independent public-download verification

Published [v0.8.0-beta.1](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.8.0-beta.1) as a public GitHub **prerelease**, release ID `433562665`. The lightweight tag resolves to exact accepted EXE source `bc22a4b04c828efad027140e94039464fed06641`. Main was normally pushed and verified synchronized at `ee16c2ea107ddea4d50afad77359962ed59297b2` before publication; this later reporting update does not change the tagged build.

|Public asset|Bytes|GitHub and independently downloaded SHA256|
|---|---:|---|
|[Windows ZIP](https://github.com/dingpengem/EMCD-Sim/releases/download/v0.8.0-beta.1/EMCD-Sim-v0.8.0-beta.1-Windows.zip)|108652577|`eec12e9ed4d102cb4ae3ff46871f53e199bd9a63d7a9f4dd233eccb4eafc023f`|
|[SHA256SUMS.txt](https://github.com/dingpengem/EMCD-Sim/releases/download/v0.8.0-beta.1/SHA256SUMS.txt)|102|`4038bf087e3e08feae881d16863dc53d99598695d70acf81eebe225eca1099b2`|
|[build_manifest.json](https://github.com/dingpengem/EMCD-Sim/releases/download/v0.8.0-beta.1/build_manifest.json)|182676|`ae8f4f6049214edda8c82c7b29e6102c597dcb3918663d35dba61549e4bb02ba`|

All three public assets were downloaded afresh and their byte counts/digests matched both the local accepted artifacts and GitHub's server-side digests. The downloaded checksum file identifies this ZIP exactly. GitHub's release API confirms `draft=false`, `prerelease=true` and the expected source. No release asset was overwritten.

The previous release remains ID `432071673`, with ZIP asset `703513772` and checksum asset `703513771`: both original names, sizes, SHA256 digests and update timestamps remain unchanged. The original ZIP is still 113643171 bytes with SHA256 `8d157d8b62fb6570d201360cdae85f44aa4cea2c1478f1949eb4336a135e17bc`.

Public README source matched the pushed commit exactly, and GitHub rendering displayed v0.8.0-beta.1, Adaptive Z=1–118, raw-before-percent figures and historical Lobato provenance. The postpublication link audit found all release/download/acceptance links reachable. Five historical local-reference issues and one publisher HTTP 403 remain as described above; no new release-documentation link failure was introduced. Local public-download evidence is `outputs/v080b1-release/public-download-verification.json`.

New Actions runs are [Windows Beta candidate](https://github.com/dingpengem/EMCD-Sim/actions/runs/41782257949) and [cross-platform source tests](https://github.com/dingpengem/EMCD-Sim/actions/runs/41782257941). At publication these were **in progress**, not reported as passed. Local Windows gates were complete before publication; known Linux/macOS failures remain separate and are not release gates.
