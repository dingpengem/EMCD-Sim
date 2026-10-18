EMCD-Sim 0.6.0 Beta - Double-Channeling EMCD Simulation (unpublished)
Prepared documentation only; no 0.6.0 executable has been built.
Double Channeling already existed in published 0.4.5-beta.1.

Extract the complete folder. Run EMCD-Sim.exe; keep _internal beside it.
Python, Conda and WIEN2k are not required to run this application.
Use your own writable folder for saved projects and exports.
SHA256SUMS.txt lists the application files. The archive checksum is supplied
separately. This candidate is tested on the development Windows host;
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
