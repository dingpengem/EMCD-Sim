EMCD-Sim v0.9.0-beta.3 ? Windows Research Beta

STARTUP AND DISTRIBUTION
Extract the complete EMCD-Sim-v0.9.0-beta.3-Windows.zip. Keep EMCD-Sim.exe
beside its _internal folder and launch the EXE. Do not distribute the EXE alone.
Python/Conda and manual BLAS environment settings are not required for packaged use.
The documented Microsoft x64 VC++ v14 runtime is an external prerequisite:
https://aka.ms/vc14/vc_redist.x64.exe . The installer is not bundled.
This Research Beta is unsigned. Follow institutional security policies; do not
disable Windows security protections. Use a writable project/export folder.

Release information, after publication:
https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.9.0-beta.3
The public beta.2 and macOS ARM64 packages remain unchanged. macOS still uses
v0.9.0-beta.1-macos-arm64.1 and a different source revision; this is Windows-only.
The bundled homepage can describe the preceding published download because
public links are updated only after approval/publication. Use this bundle's
version and build_info.json for its actual source identity.

SOURCE AND LICENSES
EMCD-Sim-v0.9.0-beta.3-Corresponding-Source.zip is the exact application Git
snapshot. EMCD-Sim-v0.9.0-beta.3-Qt-Sources.zip supplies reviewed matching
Qt/PySide/Shiboken sources, replacement guidance and another copy of that snapshot.
The kit README records the actual build commit; historical beta.1 names in the
unchanged Qt technical guide do not identify this application build.
Check SHA256SUMS.txt and build/release manifests. Application source is MIT;
dependency licenses apply separately. See _internal/licenses/qt and the source
kit's replacement instructions. Reviewed dependency versions are unchanged.
Adaptive neutral Z=1-118 factors retain Apache-2.0 LICENSE/NOTICE; Ni Lobato is
an explicit historical choice. The unlicensed legacy atomic table is not bundled.

MATERIAL AND MDFF
Use Material > Open CIF and the 3D Structure Viewer > Site groups. CIF import
supplies geometry, not magnetic order or material spectra. Define Global/Local
magnetic states and groups explicitly. Excluded oxygen stays in the elastic
structure without entering selected-ionizing-site normalization.
Configure Global/group MDFF in its explicit context: declared XMCD-constrained,
Atomic Ionization or Manual tensors. Validate source, frames and energy coverage;
complete Done, then outer Apply and Close. Cancel preserves accepted inputs.
Magnetic directions alone do not define arbitrary anisotropic tensor rotations.
Unsupported source/material/model combinations must fail explicitly; metallic
Ni examples are not calibrated Fe/oxide data. magCIF is not implemented.

CALCULATION, RESOURCES AND RESULTS
The shared headless engine preserves BW and FFT Multislice Single/Double
Channeling. Double includes outgoing propagation at incident energy minus
actual energy loss. Depth nodes, FFT mesh, detector grid and fractional-aperture
subpixels are different controls. Generic production inputs do not assume Ni.
Compute Resources keeps CPU Workers and Memory Budget Auto/Manual independent.
A memory budget is an admission ceiling, not observed consumption. Existing
native-thread limits are verified and restored. More workers are not always
faster. Cancellation joins owned workers before restart.
Save/Open the complete project folder. Earlier runs, source declarations,
recorded input settings and raw arrays are retained. Missing/changed external
sources may block rerun while stored views remain available. Selecting Total,
Element, Group Contribution/Mean or comparisons does not recalculate results.
Percentages and group means are not additive; fixed-denominator contributions
and raw +M/-M, reversal-even/odd and conventional A-B have distinct meanings.

VERIFICATION
The Phase 3 scientific baseline passed one complete 1824-case invocation:
1762 passed, 62 existing skips, zero failures/errors. The independent source
comparison is 22 cases / 2294 exact arrays. Existing Phase 3F-2 frozen evidence
is a different 19-project / 1763-array exact comparison; it does not certify
this new binary automatically. Native/manual acceptance of this exact ZIP and
its source/checksums are recorded separately in the release report/page.
No clean-machine installation is claimed by package creation or same-host QA.

LIMITATIONS AND FUTURE WORK
Projected IAM/ZOLZ, finite numerical support and independent local dipole-event
assumptions remain. Signals are relative/a.u.; absolute dose, cross sections,
magnetic moments, experimental noise and SNR are uncalibrated. Synthetic Cr,
Fe3O4/nickel-ferrite fixtures are consistency checks, not measured spectra.
The original-size Fe3O4 MS workload remains unverified. Direct Mac BW-Double,
MS-Single and MS-Double array comparisons remain INCOMPLETE; Windows checks do
not replace missing authentic cross-platform exports.
Arbitrary atom-depth events, convergent probes, STEM scans, GPU/HPC acceleration
and new thermal/nonlocal/absorptive physics are future work, not beta.3 features.
Loading historical data preserves its convention and provenance; it does not
silently update physics. Keep original projects and historical packages.
See _internal/documentation/docs/RELEASE_NOTES_0_9_0_BETA_3.md, the Phase 3
acceptance reports, Next-Gen A roadmap and SCIENTIFIC_REFERENCES.md / CITATION.md.
