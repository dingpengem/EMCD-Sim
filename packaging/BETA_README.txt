EMCD-Sim v0.8.1-beta.1 - Windows-only Research Beta
Windows x64 portable research prerelease; unsigned. Python package 0.8.1b1.
Windows numeric file/product version 0.8.1.1.
Physics convention: forward_born_dagger_g_minus_h_v1.
The release tag targets the exact accepted build source in About/build_info.json.
New GUI calculations default to bundled Adaptive Dirac-Pade neutral Z=1-118
elastic factors. Ni Lobato remains the historical compatibility provider; old
projects without provider settings restore Lobato. Provider identity and
coefficient digests are saved with new projects. Ordered multi-element CIFs
support elastic diffraction, including non-FCC indexing. Original Ni providers keep their Ni eligibility gate. Opt-in declared imported
tensors and approximate cubic 2p-to-3d atomic sources support eligible equivalent-site
single-element research calculations. They do not provide universal quantitative EMCD.
The Apache-2.0 coefficient subset has separate LICENSE/NOTICE/provenance.
No upstream HDF5 archive or h5py is needed by the bundled JSON evaluator.
The unlicensed legacy Z=1-98 table is NOT bundled; its optional adapter
requires external data and enforces the documented low-g reliability guard.
Linux/macOS are not certified or packaged in this Windows-only release.
Linux retains a bool_dealloc shutdown abort; macOS retains a Qt modal-test
stall. These known CI issues have not been suppressed.

CRITICAL SCIENTIFIC COMPATIBILITY NOTICE
Legacy Windows packages before v0.7.0-beta.1 used a superseded Born/MDFF
convention affecting magnetic-odd EMCD signs. Revalidate or recalculate
historical signed L3/L2 spectra before corrected interpretation. Do not
silently flip/relabel old arrays. Preserve original arrays/source/version
and convention provenance; missing convention is unknown/legacy-unverified.
This does not imply that all historical nonmagnetic EELS, diffraction or
thickness trends are wrong. Corrected source 4f578156 still used the old
version label, so exact source/convention metadata is authoritative.
Absolute experimental magnetic handedness remains uncalibrated.

Extract the complete folder. Run EMCD-Sim.exe; keep _internal beside it.
Python, Conda and WIEN2k are not required to run this application.
Use your own writable folder for saved projects and exports.
SHA256SUMS.txt lists the application files. The archive checksum is supplied
separately. This package is tested on the development Windows host;
independent clean-machine acceptance has not been performed.

The bundled five-column Ni spectrum is the repository-tracked example only.
It does not include WIEN2k code, executables, licensed source or private
calculation companions. To use another spectrum, browse to a five-column
WIEN2k XMCD file, validate it, then explicitly declare magnetization axis,
RP/LP convention and L3/L2 assignment. Missing data blocks calculation;
saved projects remain viewable without recalculating missing spectra.
Native calculated energies are not an experimental energy calibration.
The production reference selections 831.4778/848.698 eV differ from the
source-audit L3 magnetic extremum 831.271 eV. Record the actual selection.

Single Channeling is entrance-only. Double Channeling includes incoming,
localized ionization and reduced-energy outgoing elastic propagation.
BW, Multislice and Both use the selected actual model. The GUI uses
projected IAM potentials, not an atomic-3D electrostatic multislice model.
Exact (200) Bragg alignment does not establish physical two-beam isolation.
The explicit [001] row restriction excludes off-row beams; [017] retains
its full finite ZOLZ basis. The separate 213-beam [001] elastic audit is
not the source of the restricted-row EELS reference.

Upper spectral panel: raw detector A/B EELS on a common arbitrary-unit scale.
Signal Display: Raw (a.u.) / EMCD Asymmetry (%), default Raw.
Raw lower panel: signed magnetic and nonmagnetic differences.
Asymmetry lower panel: one total 100*(A_plus-B_plus)/(A_plus+B_plus) curve.
The total can include nonmagnetic diffraction asymmetry. Advanced magnetic-only
and nonmagnetic percentages share N_A+N_B. Display switching preserves physics.
Maps use actual mirrored points, not detector-integrated percentages.
Old Relative preferences migrate to explicitly labeled advanced components.
Post-edge correction is an advanced diagnostic, not intrinsic magnetic EMCD.
Two-energy saved results remain discrete samples, not fabricated spectra.
CSV/NPZ exports retain raw and percentage values in either display mode.
Projects preserve their inputs, results and spectral display/energy selection.

Memory budgets: 512/1024/2048(default)/4096/8192 MiB. Jobs are rejected when
the estimated process peak exceeds the budget or 50% of available RAM.
Settings are never silently reduced. Reference Ni settings, not mandatory
defaults: beam 4.6 A^-1, Fourier potential 6.2 A^-1, FFT 48, depth 257,
maximum MS step 0.04 nm, float64/complex128; crystallographic g=1/d.

Research limitations: XMCD-constrained approximate MDFF, no full DFT-derived
MDFF, branch-frozen longitudinal transfer, finite projected ZOLZ and cutoffs,
no calibrated absolute EELS cross section or electron-count SNR. Agreement at
representative settings does not establish convergence for every geometry,
thickness or energy. No claim of quantitative experimental predictivity.

Responsive UI: Settings and Diffraction remain side by side. Drag the
three-column splitters; click chevron headers to collapse optional controls
or Project Results. Very narrow windows offer a one-click Results strip.
Layout preferences are independent of scientific project settings.

GENERALIZED ATOMIC / IMPORTED SOURCES
Use the imported tensor panel and explicit parameter JSON. The original synthetic
Fe example is at _internal/examples/synthetic_fe_atomic_parameters.json. Every
material-dependent input must be declared. Generated tensors retain parameter bytes,
SHA256 and explicit reversal states. The local spin axis is +z; only rigid frame
rotations of the cubic model are supported. Intensities are relative.
Synthetic Fe calculations are software tests only, not quantitatively validated Fe
EMCD. No validated Co/Cr parameters, full DFT MDFF, many-body multiplets, AFM/SDW,
general crystal-field symmetry or multi-element site-resolved MDFF is provided.
Finite-case BW/MS agreement does not establish broad convergence or experimental
accuracy; detector refinement sensitivity remains. Historical Ni figures retain
their original Lobato/provider provenance and were not regenerated for this release.
