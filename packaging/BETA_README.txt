EMCD-Sim v0.8.1-beta.1 - Part 1B LOCAL Windows Research Candidate
Windows x64 portable research software; unsigned. Python package 0.8.1b1.
Windows numeric file/product version 0.8.1.1 remains unchanged.
Physics convention: forward_born_dagger_g_minus_h_v1.
Exact build source, version and coefficient identity are in About/build_info.json.
This local build does not push, create a tag, or publish a release.

Extract the complete folder. Run EMCD-Sim.exe; keep _internal beside it.
Python, Conda and WIEN2k are not required. Use a writable project/export folder.
SHA256SUMS.txt lists the application files; the ZIP checksum is supplied separately.
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
3. Imported Complex MDFF Tensor
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

Atomic Ionization: select explicit parameter JSON directly in the Atomic panel,
validate it, and acknowledge the approximate model. The original synthetic Fe
example is _internal/examples/synthetic_fe_atomic_parameters.json. Its numbers
are software test inputs, not measured, fitted or quantitatively validated Fe.
Every material input must be declared. This provider is restricted to the accepted
Sc-Zn 2p-to-cubic-3d L2,3 model, local +z spin and proper rigid frame rotations.
It is not an arbitrary crystal-field, core-loss-edge or many-body multiplet model.
Without explicit JSON, the historical Ni controls retain their original Ni-only
interpretation; those electronic parameters are not transferred to other elements.

Imported Complex MDFF: supply the declared complex 3x3 dipole tensor JSON, units,
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
Virtual Keyboard has GPLv3/commercial terms; this internal candidate is not a
release-compliance certification. See the component-specific notice inventory.
