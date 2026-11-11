# EMCD-Sim v0.9.0-beta.1 — macOS ARM64 Research Beta

First standalone native Apple Silicon application. Download the macOS ARM64 ZIP,
extract it in Finder and copy the complete EMCD-Sim.app to Applications. No
Python, Conda or developer tools are needed. See [the installation guide](https://github.com/dingpengem/EMCD-Sim/blob/v0.9.0-beta.1-macos-arm64.1/docs/INSTALL_MACOS.md)
for illustrated first steps and the verified small Ni example.

**Ad-hoc signed; not Apple notarized.** No Developer ID signing is claimed.
Downloaded copies may be blocked by macOS. The guide describes alerts and how to
report them; disabling protections is not an installation step.

## Included

- Native Qt GUI, CIF import and 3D Structure Viewer.
- Global/Local magnetization, site groups, XMCD, Atomic and Manual MDFF workflows.
- Bloch-wave and FFT multislice, Single and Double Channeling.
- Spectra, angular maps, group/element/total results, numerical and figure export.
- Projects, cancellation/restart, and adaptive Auto/Manual CPU and memory controls.

This is the existing scientific application with macOS portability/resource
changes and release packaging. No new scientific model or physics convention is
introduced. Application version is 0.9.0b1; macOS bundle build is 0.9.0.2. The
distinct tag is v0.9.0-beta.1-macos-arm64.1. The packaged build_info.json and
matching source tag identify the exact source commit. Windows v0.9.0-beta.1 was
built from ef81576e2692c2c826bfbe2b89f21e00b05936e4 and remains unchanged; the two
binaries do not claim the same source revision.

## Validation and limits

Native testing is on M2 Pro / 10 logical cores / 16 GiB / macOS 26.3.1. macOS 15+
and Apple Silicon ARM64 are required; Intel Macs are not supported. General
hardware detection and conservative fallbacks are implemented, but other physical
Apple Silicon configurations and macOS versions are not all tested.

Earlier evidence includes 111 focused resource tests and 96 simulated allocation
decisions, plus eight packaged resource runs across BW/MS Single/Double. The
resource GUI update separately passed 16 focused tests and eight packaged runs,
with 1328 arrays matching the previous Mac baseline. These overlapping evidence
sets are not added into a new total. Simulation is policy testing, not native
testing on 96 machines. Final focused packaged acceptance is supplied as the
release acceptance report, including relocated/extracted launch and numerical
comparison evidence.

Human GUI/trackpad acceptance and authentic matched Windows numerical comparisons
remain incomplete. Known issues include clipped diffraction titles in compact
windows and two baseline Cocoa result-pane sizing test failures. Four historical
legacy failures remain classified: one native modal retention automation timeout,
two tests omitting the required Global Material/MDFF acceptance transaction, and
one obsolete post-edge-correction expectation. They are not silently counted as
passing. Local MDFF Done/focus return has native mouse-click evidence.

Research/approximate models and synthetic examples are not scientific
certification or quantitative material calibration. Selected-edge Quick Start
points are not a resolved spectrum; convergence must be established for each
research request. No Windows equivalence is claimed without an authentic matched
reference.

## Sources and notices

The accompanying macOS Corresponding-Source ZIP supplies the matching application,
Qt/PySide/Shiboken, ASE and GCC runtime source/build materials. The retained
libquadmath was traced from the exact SciPy wheel to the historical Homebrew GCC
13.4.0 ARM64 bottle, with matching source and Apple Silicon patch; its working
numerical implementation was not replaced. Full notices and source/replacement
instructions are included in the application and source ZIP. The separate
SHA256SUMS.txt identifies the downloadable archives.
