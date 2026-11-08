EMCD-Sim v0.9.0-beta.1 - Windows Research Beta prerelease
Windows x64 research software; unsigned. Python package 0.9.0b1.
Windows numeric version 0.9.0.1; ProductVersion v0.9.0-beta.1.
Physics convention: forward_born_dagger_g_minus_h_v1.
Exact build source, version and coefficient identity are in About/build_info.json.
Local development candidate only; not published. Scientific source validated at 49064fd.

Extract the complete folder. Run EMCD-Sim.exe; keep _internal beside it.
Python, Conda and WIEN2k are not required. Use a writable project/export folder.
Verify the candidate ZIP against the accompanying SHA256SUMS.txt.
Acceptance is on the development Windows host, not an independent clean PC/VM.
Linux/macOS applications are not certified or packaged by this candidate.

ELASTIC SCATTERING
New GUI calculations default to bundled Adaptive Dirac-Pade neutral Z=1-118
elastic factors. Ni Lobato remains selectable for historical compatibility;
old projects without a provider restore Lobato. Provider identity and coefficient
digests are saved. Ordered fully occupied multi-element CIFs support elastic
diffraction and non-FCC indexing. This does not supply multi-element MDFF.
The coefficient subset retains separate Apache-2.0 LICENSE/NOTICE/provenance.
No upstream HDF5 archive or h5py is required by its bundled JSON evaluator.
The unlicensed legacy Z=1-98 table is NOT bundled. Its optional external adapter
retains its documented reciprocal-space validity and low-g reliability guards.

THREE MDFF CHOICES, ONE PROPAGATION FRAMEWORK
The same choices are visible for every crystal:
1. XMCD-constrained MDFF
2. Atomic Ionization MDFF
3. Manual tensor (including advanced imported tensor exchange)
Run eligibility depends on valid source/model inputs and supported equivalent
sites in a fully occupied single-element crystal, not menu visibility.
Shared BW/MS Single/Double propagation and tensor contraction are independent of
the element. No multi-element, inequivalent-site, AFM/SDW or complex magnetic
structure model is added.

XMCD-constrained: browse a compatible five-column XAS/XMCD file, validate its
native unshifted energy range and checksum, and acknowledge magnetic axis,
RP-minus-LP handedness and edge assignments. The original Ni source/workflow is
preserved. Other elements require their own declared source, provenance,
assumptions and relative reference scale; Ni data/energies are never substituted.
Ambiguous features require explicit native-energy selections. No separate tensor
JSON, DFT wavefunctions, or WIEN2k installation is required. The axisymmetric
effective tensor is approximate, not a complete ab-initio complex MDFF.

Atomic Ionization: use Model > Configure MDFF... and the element-aware editor
for the cubic independent-electron Sc-Zn 2p-to-3d L2,3 model. Inspect reference
energies, Gaussian width, magnetization/frame, crystal-field and exchange
splitting, spin-resolved holes, radial input, and per-element drafts. Generic
electronic defaults are explicitly synthetic, not measured material properties.
Complete parameter JSON can also be imported/exported. The supplied example is
_internal/examples/synthetic_fe_atomic_parameters.json; it is a software test,
not fitted or quantitatively validated Fe spectroscopy. Historical saved Ni
settings retain their original interpretation. This is not a full multiplet,
band-structure, or arbitrary-edge model.

Manual tensor: edit a constant complex Hermitian PSD 3x3 tensor, or independent
integrated L3/L2 strength tensors broadened by Lorentzian profiles. Finite-window
tail loss is displayed without automatic renormalization. Advanced imported
exchange accepts the declared complex 3x3 dipole tensor JSON, units,
normalization, frame, element/edge, magnetic state, provenance and checksum.
Nonmagnetic input supplies an explicit even state. Magnetic input supplies both
states and their shared even tensor. A missing general magnetic state is never
manufactured by conjugation. Hermiticity, PSD, finite values, source identity,
energy coverage and conventions are checked without clipping or extrapolation.

Declared sources use explicit Manual numerics. Source adapters validate the L2,3
contract and have bounded synthetic K-edge workflow tests. Other edge families
remain rejected; a synthetic K test is not physical arbitrary-edge validation.
Atomic Ionization does not provide K transitions. L3/L2 peak normalization and
L3 white-line diagnostics remain limited to L2,3. Raw and pointwise asymmetry
signals retain their actual declared edge labels. Requested sampling may
interpolate within the native range; no energy-axis shift is applied.

SOURCE AND PROJECT INTEGRITY
Provider identity, original input bytes/checksum, conventions, frame and model
provenance are retained. Missing/changed data blocks rerun and clears previous
acknowledgement. Revalidation is explicit; no provider substitution occurs.
Saved arrays remain viewable when an external source is unavailable. Failed atomic
generation does not replace an existing successful result with stale source state.
SHA256 establishes file identity, not scientific authenticity or physical accuracy.

MULTI-SITE RESEARCH LIMITS
Independent local MDFF reversal pairs and selected-ionizing-atom normalization
are supported. Fe3O4/NiFe2O4 benchmarks use synthetic site tensors, not calibrated
material spectra or magnetic moments. Finite ZOLZ and continuous-depth events
remain approximations; general beam-basis and BW/MS convergence is incomplete.

SIGNALS AND NUMERICAL LIMITATIONS
Single Channeling is entrance-only; Double includes localized ionization and
reduced-energy outgoing elastic propagation. BW and FFT MS use the selected
actual model. The potential is projected IAM, not an atomic-3D electrostatic model.
Crystallographic g=1/d; angular Q=2*pi*g. Intensity uses Re Tr(RT).
Exact target Bragg alignment does not establish physical two-beam isolation.

EELS retains original detector A/B signals on a shared arbitrary-unit scale.
Raw lower signals are signed magnetic/nonmagnetic differences. Conventional
asymmetry uses 100*(A_plus-B_plus)/(A_plus+B_plus) and can include even imbalance.
Maps use actual mirrored points, not detector-integrated percentages. Post-edge
correction is an optional diagnostic, not intrinsic magnetic EMCD. Sparse selected
energies are points, not fabricated spectra. CSV/NPZ retain original signed values.

Exact Ni regression means compatibility, not quantitatively accurate metallic Ni.
Synthetic Fe and K cases are software/math tests. No calibrated absolute cross
section, electron-count SNR, full DFT MDFF, or experimental accuracy is established.
Approximately 1.6% detector-refinement sensitivity remains a limitation in reviewed
finite cases. BW/MS agreement is neither general convergence nor material accuracy.
Check beam/potential support, FFT mesh, depth/step and detector sampling separately.
Memory guards reject unsupported requests; scientific settings are not reduced
silently to fit resources.

HISTORICAL COMPATIBILITY
Earlier pre-v0.7 Windows packages used a superseded magnetic Born/MDFF convention.
Preserve their arrays and provenance; revalidate signed results before corrected
interpretation. Missing convention metadata remains unknown/legacy-unverified,
not silently corrected. Absolute experimental magnetic handedness is uncalibrated.
Historical Ni examples retain their original Lobato/provider provenance; 9/30 nm
figures and raw scientific data were not regenerated or relabeled by consolidation.
Packaged structure examples: _internal/examples/Fe_BCC_a2.8665.cif and
_internal/examples/Ni_FCC_a3.52.cif. Select these files in the CIF open dialog.
Their provenance and MIT redistribution terms are in _internal/examples/README.txt
and LICENSE.txt. The Ni example uses a=3.52 angstrom; built-in Ni uses 3.524.
Qt component licenses, notices and provenance: _internal/licenses/qt/README.txt.
Qt PDF and Virtual Keyboard are excluded from this candidate. Retained components have
separate license terms; see the component inventory and accompanying source kit.

DISTRIBUTION PREREQUISITES AND SOURCE
Install Microsoft's official x64 Visual C++ v14 runtime (14.44.35211 or newer)
directly from https://aka.ms/vc14/vc_redist.x64.exe . Windows 10/11 x64 required.
No Microsoft runtime DLL copies or installer are included in this package.
Qt PDF and Virtual Keyboard are unused and excluded, with their dependency chain.
Use the accompanying EMCD-Sim-v0.9.0-beta.1-Qt-sources.zip for
matching LGPL component sources and build/replacement instructions. Also see
_internal/licenses/qt/SOURCE_AND_REPLACEMENT.md and the included license texts.
EMCD-Sim remains MIT licensed; dependency licenses apply separately.
