# EMCD-Sim v0.9.0-beta.3 — Windows Research Beta

**Windows x64 release candidate. Publication and manual GUI approval are pending.**
This source snapshot describes the release scope and established baseline.
The new build's measured acceptance, exact source commit and asset checksums
are recorded in `docs/PHASE3_WINDOWS_PUBLIC_RELEASE.md` after the build,
and in the GitHub release when publication is authorized.

## What's changed

Beta.3 packages the completed Phase 3 architecture and application stabilization:

* One canonical, headless forward-calculation entry point with explicit
  structure, material/provider and geometry inputs. Generic calculations do
  not silently inherit a Ni material or detector configuration.
* Shared provider and multi-site integration, with explicit source frames,
  magnetic configurations, selection weights and source validation.
* Preserved Bloch-wave and FFT multislice Single/Double Channeling. These are
  existing scientific capabilities; this release refactors their ownership
  and verifies preservation rather than claiming to introduce the theories.
* Clearer neutral settings, scientific data/geometry ownership and separation
  from GUI presentation. The familiar Global/Local MDFF workflows remain.
* Stabilized project persistence, recorded run inputs, selected-run restoration
  and result switching, including disjoint magnetic groups.
* Preserved Compute Resources admission, automatic/manual allocation,
  native-thread control, cancellation, cleanup and restart workflows.

No new calculation kernel, magnetic model or physical approximation is added
for beta.3. Release-specific changes are version/configuration, documentation
and the existing source-registration bookkeeping. The Windows workflow now
supplies its mandatory reviewed Qt-source inputs; dependency versions are
unchanged.

The packaged multisite acceptance profile checks its recorded version against
the authoritative package version, replacing an obsolete beta.2 literal. This
release-tooling correction changes no scientific assertion or calculation.

## Verification and provenance

The completed Phase 3 application source
`a97ccf14e890b9e52fc57d47261117717825f5ba` passed one uninterrupted full
regression: **1,824 collected, 1,762 passed, 62 existing skips, zero failures
and zero errors**. The exact skip nodes/reasons match the prior inventory.
This is the [Phase 3 baseline](PHASE3_FINAL_REGRESSION_AND_MAIN_INTEGRATION.md),
not a claim that an earlier invocation tested later release bookkeeping.
Scientific calculation source and scientific test assertions are preserved;
affected version, authentication and packaging checks are run for this candidate.

Two different numerical comparisons retain their original provenance:

* **22 cases / 2,294 arrays exactly equal** against independent pre-refactor
  source `cdb8836388c5ccc5ae7a614b47894c0ab158a824`.
* Existing Phase 3F-2 frozen Windows evidence: **19 projects / 57 NPZ files /
  1,763 arrays exactly equal**, including 448 NaN-bearing arrays, against
  independently validated earlier frozen outputs. This is
  [beta.2 development-source evidence](PHASE3F2_WINDOWS_NATIVE_ACCEPTANCE.md),
  not native acceptance of the newly rebuilt beta.3 binary.

The rebuilt beta.3 EXE from
`f2965cbfbddb0b839c5eb4db8e1b50d2047fa4a6` passed **all 11 native packaged
profiles**, package/source/license verification and its own independent
**19-project / 57-NPZ / 1,763-exact-array** comparison, including 448 NaN-bearing
arrays. No scientific tolerance or reference changed. The initial candidate
was superseded after an obsolete beta.2 version assertion in acceptance tooling
was corrected; every final native profile ran on the replacement binary.

The release preflight passed 27 checks; three affected registration checks
passed after that QA-only correction. All final src bytes are identical to
the release source used for the new **22-case / 2,294-exact-array** comparison.
The complete regression retains its original tested-source identity and was
not restarted for release bookkeeping.

**Manual GUI approval and publication remain pending.** The exact Windows ZIP
SHA-256 is `da12fff50ec062f9c1054c40cf34b0435924d3091dfd99f31e44fe6ea4c1089e`.
See the [measured release report](PHASE3_WINDOWS_PUBLIC_RELEASE.md) for artifact
identities, native outcomes, retained limitations and the manual checklist.
A later documentation-only
commit may contain that report without changing the tagged build source or
the accepted binary. No full-suite, native or clean-machine claim is inferred
from a version string.

## Windows package and corresponding sources

Extract the complete `EMCD-Sim-v0.9.0-beta.3-Windows.zip`, retaining
`EMCD-Sim.exe` and its adjacent `_internal` directory. The EXE is not a
self-contained download. No Python/Conda installation is required for packaged
use. The documented Microsoft x64 VC++ runtime remains an external prerequisite.
The Research Beta is unsigned; follow institutional security policies.

The application corresponding-source ZIP identifies the exact committed
repository snapshot. The separate Qt source kit contains the matching reviewed
Qt/PySide/Shiboken sources, replacement instructions and a copy of that exact
application snapshot. Dependency licenses and notices remain in the Windows
bundle. Verify filenames, sizes and SHA-256 against the supplied checksums and
manifests. A release tag must identify the actual build-source commit.

The public Windows beta.2 and macOS ARM64 assets are preserved. This is a
**Windows-only** update: the macOS application remains
`v0.9.0-beta.1-macos-arm64.1`, from its own source revision. It has not received
the Windows Phase 3 refactor. Windows and macOS download versions and source
revisions can differ. The public homepage is updated only after the new
Windows artifacts are approved, published and verified.

## Next-generation development

Next-Gen A supplies an audited architecture, bounded CPU measurements and a
design/validation roadmap:

* [Architecture readiness](NEXTGEN_A_ARCHITECTURE_READINESS.md)
* [Depth and STEM physics design](NEXTGEN_A_DEPTH_STEM_PHYSICS_DESIGN.md)
* [Measured performance baseline](NEXTGEN_A_PERFORMANCE_BASELINE.md)
* [Implementation roadmap](NEXTGEN_A_IMPLEMENTATION_ROADMAP.md)

Depth-localized inelastic multislice with explicit 3D specimen events,
convergent-beam EMCD, real-space STEM-EMCD scans, scalable high-dimensional
storage and GPU/HPC acceleration are **future development goals**. They are
not implemented release features. No Next-Gen B1 implementation is included.

## Known scientific and validation limits

* Projected IAM/ZOLZ, dipole/local independent-event and documented longitudinal
  transfer assumptions remain. Depth integration and incoming/outgoing
  propagation are not an arbitrary atom-resolved 3D specimen/event interface.
* Beam, FFT, depth and detector support are finite. Representative controls and
  passing fixtures do not certify arbitrary geometry, thickness or convergence.
* Signals remain relatively normalized/arbitrary units, without absolute
  electron-count/cross-section, magnetic-moment, experimental noise or SNR calibration.
* Declared, effective and synthetic MDFFs retain their source/model limitations.
  Synthetic Cr, Fe3O4 and nickel-ferrite fixtures are not quantitative
  experimental material spectra. CIF import does not infer magnetic order.
* Arbitrary magnetic-tensor rotation, magCIF, nonlocal/coherent intersite
  excitations, thermal/absorptive models and new non-dipole physics are not
  implied by the refactor.
* The original-size Fe3O4 multislice workload remains unverified. Bounded motif
  and grouping cases do not close that gap or establish full-size speedups.
* Historical direct macOS BW-Double, MS-Single and MS-Double raw-array
  comparisons remain **INCOMPLETE**. New Windows/source comparisons do not
  replace missing authentic cross-platform exports.
* Native same-host acceptance is separate from clean-machine installation and
  unrestricted runtime certification. Manual GUI acceptance and publication
  status must be stated explicitly for the exact candidate.

Existing projects retain their saved arrays and original physics/source
provenance. Loading old data does not silently recalculate or relabel its
scientific convention. Keep original projects and historical releases.
