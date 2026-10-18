# EMCD-Sim 0.4.5 Windows research Beta

Release tag: **v0.4.5-beta.1**. Package metadata remains **0.4.5**.
This is a research **Pre-release**, not a stable production release.

**Publication succeeded:** [GitHub Windows Beta Pre-release](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.4.5-beta.1).

[Download the Windows ZIP](https://github.com/dingpengem/EMCD-Sim/releases/download/v0.4.5-beta.1/EMCD-Sim-0.4.5-Beta-RC-Cancellation-Fix-Windows.zip) -
[SHA256SUMS.txt](https://github.com/dingpengem/EMCD-Sim/releases/download/v0.4.5-beta.1/SHA256SUMS.txt) -
[Build manifest](https://github.com/dingpengem/EMCD-Sim/releases/download/v0.4.5-beta.1/build_manifest.json) -
[Publication provenance](https://github.com/dingpengem/EMCD-Sim/releases/download/v0.4.5-beta.1/release_provenance.json).

## Install and learn

Download `EMCD-Sim-0.4.5-Beta-RC-Cancellation-Fix-Windows.zip`, verify SHA256,
extract the complete directory and launch `EMCD-Sim.exe`. Keep `_internal`
beside the executable. No separate Python or Conda installation is required.
The EXE is unsigned; follow institutional security policies.

- [Windows installation](INSTALL_WINDOWS.md)
- [Quick Start](QUICK_START.md)
- [Complete User Manual](USER_GUIDE.md)
- [GUI technical reference](EMCD_GUI.md)
- [Current scientific limitations](USER_GUIDE.md#scientific-limitations-and-responsible-interpretation)
- [Changelog](CHANGELOG.md)

## What's new

Genuine Single/Double Channeling with independent BW and FFT multislice;
full-energy Ni L3/L2 EELS and magnetic/nonmagnetic decomposition; original raw
A/B intensities; signed Raw EMCD and common-denominator Relative EMCD; separate
PRB benchmark; indexed diffraction, zone-axis/Bragg geometry and physical
Thales apertures; saved projects, Results Browser and PNG/SVG/CSV/NPZ exports;
configurable process-memory budgets and responsive cooperative cancellation.

Double Channeling integrates localized ionization through specimen depth
between incoming and post-loss outgoing elastic propagation, retaining complex
MDFF interference. It is not a fitted scale factor. The GUI permits individual
thickness/mistilt conditions and comparisons; dedicated scripts retain the
existing research scan workflows.

## Exact binary provenance

| Item | Value |
| --- | --- |
| Main publication merge / annotated tag commit | `4185080dfb76c5dcce051b43511969caf9181548` |
| Validated development merge input | `71b068d8eedfc566ad626fe2634ae8d7c61527ac` |
| Accepted binary build source | `9937d3b820e4225fdf06b7f3ed33c7083d0f35ea` |
| Scientific/full-spectrum acceptance milestone | `7dd90fcac948fe0b8922e7b7d3571261631c4672` |
| Final cancellation acceptance documentation | `6f6362d7da544324159942ecf1808be88a195dac` |
| ZIP | `EMCD-Sim-0.4.5-Beta-RC-Cancellation-Fix-Windows.zip` |
| ZIP size | **108,689,021 bytes (103.65 MiB)** |
| EXE SHA256 | `812e010974e22a2ca541198d64ff174a21627d749d313e2915bac9f27bcef693` |

ZIP SHA256:

```text
309438c4a049773a6e99948477c8d52051cd8f1de632a762c795656e6c5a2216
```

The exact accepted ZIP is reused, without rebuilding or repacking. All **80
packaged runtime-source hashes** were independently checked. Changes after
the build are documentation, acceptance verification tooling and CI setup;
the release/tag source includes later documentation and merge history.
The binary corresponds to the build-source commit above, not a claim that
every later Git commit was compiled. The release attaches the build manifest,
checksum text and a separate publication-provenance record.

Only the tracked, distributable five-column Ni example is included; no WIEN2k
code, companion calculation archive, credentials or private user projects.
The bundled source hash is
`4fd517af3e54db94588a76b7a6ed9c2f9a1b745cd8fe52b9fca0f87fc4938db3`.
The external accepted production-reference source hash is
`a0e28ea6423b6c7832bb3cce6d69d71aa59336a221baeee3d2556b49ba501283`;
these are distinct inputs. Import and validate matching external data before
attempting a numerical reference reproduction.

## Validation scope

- Earlier Beta acceptance: **115 passed after targeted rechecks**, with no
  unresolved failures; not a single newly rerun 115-test suite.
- Cancellation fix: **42 focused tests passed**. Counts overlap the earlier
  milestone and must not be added into a purported unique suite count.
- Real source and frozen Single/Double × BW/MS/Both routes were exercised.
  Matched completed arrays were verified **bitwise identical**.
- Final cancellation run: worst request-to-idle **0.607 s source**, **0.337 s
  frozen**. Worst across source iterations: 0.744 s. Tests include controlled
  work blocks and uninstrumented cases, late/repeated Cancel, queued completion,
  Both before MS starts, restart, prior-result integrity and resource cleanup.
  Individual native calls are not interruptible mid-call; no universal latency
  guarantee follows from these measured profiles.
- Native Windows 11 x64 development host, **150% scaling**. Fresh extraction
  outside the repository with development Python/Conda removed from PATH.
  **Independent clean-machine validation: NOT TESTED.**
- Saved scientific references and 1,692 protected files were preserved.
  The saved production maximum BW/MS PRB discrepancy is 0.001678 pp, within the
  unchanged 0.01 pp tolerance. No expensive thickness/voltage scan was rerun.

See [original acceptance](WINDOWS_BETA_RELEASE_ACCEPTANCE.md),
[cancellation acceptance](DOUBLE_CHANNELING_CANCELLATION.md),
[full-spectrum validation](DOUBLE_CHANNELING_FULL_SPECTRA.md) and
[geometry validation](NI_TWO_BEAM_GEOMETRY_COMPARISON.md).

## Scientific limitations

The Ni magnetic MDFF is XMCD-constrained and approximate, not a complete
DFT transition-wavefunction MDFF. Intensities are arbitrary units, without
absolute cross-section/electron-count or experimental SNR calibration.
Native WIEN2k energies are unshifted calculated energies, not experimental
absolute calibration. GUI multislice uses projected IAM potentials, not genuine
atomic-3D slice-dependent electrostatics; branch-frozen longitudinal-transfer
approximations remain. Representative convergence does not certify every
material, geometry, energy or thickness.

Ni [017] is a minor-zone, exact-(200)-Bragg, full finite ZOLZ example; the
separate [001] reference is explicitly systematic-row restricted. Strong
two-beam dominance is not strict physical isolation. Approximate 8 nm L3 PRB
values -13.0601% / -13.2278% are calculated model references at 831.4778 eV,
not measurements or universal optimum thicknesses. Arbitrary CIF loading does
not establish magnetic EELS support for arbitrary materials. Raw, intrinsic
magnetic, reversal-even, post-edge-corrected and percentage contrasts remain
distinct observables.

## Publication verification

**PASS:** merged main and development commits were pushed without force;
`v0.4.5-beta.1` is an annotated tag on the publication merge above. The public
GitHub release is `prerelease=true`, `draft=false`, and was created with
`make_latest=false`. Its four release assets are uploaded. A fresh public
unauthenticated ZIP download is exactly **108,689,021 bytes**, with SHA256
matching the accepted local archive. ZIP CRC, complete folder structure and
all extracted-manifest file hashes pass. The README download link resolves to
that actual release; installation, quick start and manual remain linked on main.

The tag is preserved on the exact publication merge. Subsequent main commits
record verified public URLs and repair CI/test-only portability issues; they
do not alter runtime, resources, package version or binary bytes. Existing
main history and the old `v0.4.5` tag were retained. Local user-owned modified
source data and untracked research scripts were excluded from commits.

The existing Ni map-generation workflow skipped the main publication merge
and tag, so release publication did not regenerate main's scientific examples.
A normal development-branch push triggered its preexisting branch workflow,
creating example-only commit `096f87aabda947d9c185819654359cf5eef113e5` after the
validated development merge input. That automated example commit was not
merged into the Beta tag; it was retained on the remote development branch.

Initial automatic cross-platform CI exposed unavailable local-only reference
projects/WIEN2k audit companions, stale version/PRB/GUI fixtures and missing
Linux EGL libraries. Repairs are confined to tests and CI: explicit skips
for absent local inputs, current fixture fields and explicit convention
handling, isolated test workspaces, and Linux Qt runtime libraries. Numerical
thresholds and physical algorithms were not changed. Focused affected checks
are recorded locally in `outputs/beta_release_publish/`; this is not a new
production physics validation or a combined replacement test count.

Automatic CI on post-publication test/documentation commit
`bc05316b180599c89410423d6574fdede24c5f77`:

| Platform | Outcome | Evidence |
| --- | --- | --- |
| Windows source tests and CLI smoke | PASS | 341 passed, 49 skipped; job completed successfully |
| Linux source suite | FAIL | 341 passed, 49 skipped, then native-extension `bool_dealloc` abort during interpreter finalization (exit 134) |
| macOS guarded channeling workflows | FAIL | Available-RAM adapter attempts `/proc/meminfo`, unavailable on macOS; calculations fail closed |

[Automatic CI run](https://github.com/dingpengem/EMCD-Sim/actions/runs/39159953271).
Windows source CI is additional evidence, not an independent clean-machine
frozen-EXE test. Linux/macOS source portability is unresolved; this release
ships a tested **Windows x64** binary only. No non-Windows success is claimed,
no failed check was hidden or threshold relaxed, and no new runtime adapter
or GUI change was introduced to force a green matrix. These remaining issues
require separate platform-focused work. Publication/download verification is
complete; full cross-platform source CI is not green.

The final main documentation update records these results and public links;
it contains no runtime/resource changes and does not move the release tag.
