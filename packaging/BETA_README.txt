EMCD-Sim v0.9.0-beta.2 — Windows Research Beta RC1 (UNPUBLISHED CANDIDATE)
Exact committed source, dependencies and build time are in
_internal/build_info.json and the existing build manifest. Prior development
candidates remain separate; this is not independent clean-PC/VM acceptance.

START HERE
Use the separately supplied EMCD-Sim-v0.9.0-beta.2-Windows-RC1.zip.
There is no beta.2 published release/tag yet. The previous beta.1 release remains
unchanged at https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.9.0-beta.1 .
Use Extract All, keep the complete EMCD-Sim folder, and double-click
EMCD-Sim.exe beside _internal. Do not run inside the ZIP or copy only the EXE.
Install the official Microsoft runtime below if needed. Python/Conda and
manual OpenBLAS/OMP environment settings are NOT required for ordinary use.
Installation:
https://github.com/dingpengem/EMCD-Sim/blob/feat/windows-adaptive-compute/docs/INSTALL_WINDOWS.md
Quick Start:
https://github.com/dingpengem/EMCD-Sim/blob/feat/windows-adaptive-compute/docs/QUICK_START.md
Tutorial (with bundled-input paths and native illustrations):
https://github.com/dingpengem/EMCD-Sim/blob/feat/windows-adaptive-compute/docs/TUTORIAL.md
Offline copies and illustrations: _internal/documentation/docs/ .
The independent macOS release/installation remain unchanged:
https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.9.0-beta.1-macos-arm64.1
https://github.com/dingpengem/EMCD-Sim/blob/main/docs/INSTALL_MACOS.md

INSTALLATION AND REDISTRIBUTION
Extract the complete EMCD-Sim folder; keep _internal beside EMCD-Sim.exe.
Windows 10/11 x64. Python, Conda and WIEN2k are not required at runtime.
Install Microsoft's official x64 Visual C++ v14 runtime (14.44.35211 or newer):
https://aka.ms/vc14/vc_redist.x64.exe . The runtime/installer is not bundled.
Use a writable project/export folder and retain the supplied SHA256SUMS.txt.
The matching Corresponding-Source ZIP contains EMCD-Sim-source.zip plus
matching Qt/PySide/Shiboken dependency sources and replacement instructions.
Use EMCD-Sim-v0.9.0-beta.2-RC1-Qt-sources.zip for this candidate. Its README
identifies the current commit; the unchanged Qt technical guide keeps its
historical beta.1 names. Those are not the current application source/package.
See _internal/licenses/qt/SOURCE_AND_REPLACEMENT.md and component licenses.
Unused Qt PDF and Virtual Keyboard components are excluded. ASE, spglib and
other dependencies retain applicable license/provenance files. Adaptive neutral
Z=1-118 factors retain their Apache-2.0 LICENSE/NOTICE; Ni Lobato remains a
historical compatibility choice. The legacy unlicensed table is not bundled.

MATERIAL, MAGNETIZATION AND MDFF
Use Material > Open CIF, then 3D Structure Viewer > Site groups.
Crystallographic orbit suggestions retain original ASE indices and provenance;
ordinary CIFs assign neither magnetic order nor MDFF. Create magnetic subgroups
manually when crystallographic equivalence does not imply magnetic equivalence.
Choose Global Magnetization Mode or Local Site Magnetization Mode. Local mode
locks Global M. Excluded oxygen stays in the elastic crystal, outside the
selected-ionizing-atom normalization denominator.
Configure MDFF in the explicit Global/group context: XMCD-constrained MDFF,
Atomic Ionization MDFF, or Manual tensor. Target M is inherited read-only from
Material; complete source-axis/frame declarations are separate. Validate sources,
complete required acknowledgements, choose Done, then outer Apply and Close.
Failed Apply preserves accepted settings and the draft; Cancel discards edits.
Explicit validated reversal pairs are supported. Unsupported fixed-source Z-to-X
changes are rejected; arbitrary tensor rotation and magCIF are not implemented.
Never use metallic Ni spectra as calibrated Fe/oxide spectroscopy.

SAMPLING, PROPAGATION AND RESOURCES
BW and FFT Multislice support Single and Double Channeling; Double includes
outgoing propagation at incident energy minus each actual energy loss.
Default spectral sampling requests 241 uniform points per modeled source window
and inserts exact selected energies. Native and selected-only modes are separate.
Full angular maps at selected energies uses detector support elsewhere; Full
angular field at every energy (advanced) is a distinct opt-in. Both MS Single
and Double honor this policy. The detector grid is not the internal FFT mesh;
depth nodes and aperture subpixels control different integrations.
Automatic/Manual outer workers respect existing CPU/memory admission. Supported
NumPy/SciPy OpenBLAS runtimes are limited and verified during calculation, then
restored. No BLAS environment-variable workaround is needed for normal startup.
Four workers are not universally faster. Progress counts actual completed work;
Cancel stops cooperatively and joins owned workers before another calculation.

COMPUTE RESOURCES AND REPRESENTATIVE NI
Shared Calculation Settings > Compute Resources replaces Resource Estimate.
CPU Workers and Memory Budget have independent Auto/Manual modes; remembered
Manual values are retained. The budget is an admission ceiling, the estimated
peak includes reserves, and measured process memory is a different quantity.
SC has one outer worker. Default Auto is conservative, not a speedup guarantee.
The Quick Start uses 200 kV/10 nm, actual 3.520 A Ni [017]/(200), 241 uniform
points plus exact selected features = 243 energies, and two 97x97 selected maps.
Spectra at other energies use the fractional detector support. No numerical
convergence or quantitative material calibration is implied.

EVIDENCE STATUS
The prior Windows 16-run benchmark is retained; its scientific arrays and
sources are unchanged. BW-SC cross-platform evidence passes. Direct Mac BW-DC,
MS-SC and MS-DC numerical comparisons remain INCOMPLETE until authentic retained
exports are transferred. See _internal/documentation/docs/WINDOWS_MACOS_NUMERICAL_EQUIVALENCE.md.
Publication is NO-GO pending those comparisons and final candidate acceptance.

RESULTS AND PROJECTS
The familiar Settings / Diffraction / Results / lower Project Results layout
is retained. Total, Element, Group Contribution, Group Mean and comparisons use
saved arrays without recalculation. Additive contributions use Total's fixed
selected-atom denominator; group means and percentages are not additive.
Raw +M/-M, reversal-even/odd and conventional A-B are distinct quantities.
Shared EELS legends wrap in measured rows below the curves, remain clickable,
and retain complete curve identification in figure exports. Scroll the Results
panel when needed; RC1 packages remain a separate unpublished candidate.
Independent windows/gaps describe a modeled partial core-edge spectrum.
File > New Project / Open Project / Save / Save As / Close Project manages a
complete multi-calculation project. Keep a new calculation rather than replacing
an original. Restore settings, deletion and two-run comparison are in Project
Results; figure/data exports and detailed metadata are near the Results plots.
Missing/changed external sources may block rerun while saved arrays remain
viewable. Unsupported freshness comparison remains unavailable, not falsely
matching. Read-only viewing does not change recorded numerical provenance.

RESEARCH LIMITATIONS AND EVIDENCE
Synthetic/effective providers are not absolute calibrated material spectra or
magnetic moments. Finite ZOLZ, projected IAM, continuous-depth localized events,
incomplete basis/FFT/depth/detector convergence and some complex BW/MS conditions
remain limitations. No quantitative Fe3O4/NiFe2O4 spectroscopy is established.
Bounded four-worker BW/MS execution and MS selected-map scheduling were checked.
The original-size Fe3O4 MS workload has NOT completed verification. The reported
angular-query reduction is not a measured full-size runtime speedup.
Historical failed/incomplete broad regression and source-guard coverage is not
superseded by focused passes. No new complete regression is claimed for this RC.
See docs/RELEASE_NOTES_0_9_0_BETA_1.md in the matching application-source archive.
Earlier magnetic-sign conventions and unknown provenance remain historical;
loading a project does not silently update its physics. Application source is
MIT licensed; dependency licenses apply separately.
