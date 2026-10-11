# Magnetic EMCD project roadmap

This project **must remain independent from the QCBED repository and its magnetic-QCBED workstream**. Physics interfaces may be compared conceptually, but code, Git history and deployment remain separate unless explicitly requested later.

## V0 — demonstrator (implemented)

- FCC Ni [001], ±(200) three-beam diffraction, simple finite-beam Hermitian channeling.
- Core-loss L2/L3 phenomenological nonmagnetic/chiral MDFF and reciprocal map.
- Finite virtual detector integration: A/B spectra, Δ, asymmetry; voltage data law interface.
- Command-line output and lightweight invariance tests.

## V0.2 — physical elastic entrance propagation (implemented, not yet validated to experiment)

- Ni Z=28 Lobato–Van Dyck elastic factors and complex FCC Fourier coefficients, isotropic DW B and occupancy inputs.
- Relativistic, nonabsorptive finite-basis Bloch-wave propagation (default 7-beam Ni row; optional symmetric [001] ZOLZ set).
- Source-controlled elastic intensity/thickness curves and a two-beam Bragg Pendellösung numerical check; original surrogate retained as explicit option.
- Still **not** quantitative EMCD: outgoing channeling, magnetic MDFF and experimental convergence remain V1–V2 work.

## V1 — quantitative elastic geometry

- Crystal orientations incl. arbitrary zone and detector projection; extend tabulated electron scattering factors beyond Ni and independently validate Ni IAM potentials.
- Compare current finite-beam physical Bloch-wave solver to an independent multislice/reference implementation and measured Ni CBED; convergence versus beam count, thickness, tilt.
- Source/aperture coherence and calibrated illuminated volume.

## V2 — proper EMCD double channeling

- Excitation-position-resolved incoming and outgoing channeling, exit-wave reciprocity and full MDFF convolution.
- Elastic absorption/thermal diffuse scattering, energy-dependence and transition operator; validated sign conventions.
- Ni L2,3 radial and spin-orbit matrix elements from DFT or calibrated XAS/ELNES; quantitatively meaningful spectral units.

## V3 — experiments and inferred moments

- Reader for measured EELS/4D-STEM datasets; dark-current/gain/background, PSF, drift correction.
- Map virtual aperture geometries; optimize thickness, tilt, field and momentum acceptance by predicted EMCD SNR.
- Ni benchmark measured vs predicted: contrast, edge integrals and spin/orbital sum-rule estimators; uncertainty estimates.

## V4 — electrically tunable EMCD (research target)

- Device-agnostic `MagneticState(V, B, T, z)` provider with spin/orbital magnetic moments, orientation, domain populations.
- Separate `ElectronicResponse(E,V)` for bias-dependent nonmagnetic and magnetic white lines.
- Couple to first-principles calculations, micromagnetics or *measured* voltage curves; track hysteresis, sweep direction and dynamics.
- Distinguish true magnetic EMCD from thickness/strain drift, bias-dependent ELNES/oxidation and microscope deflection.

**Validation gate:** do not interpret numerical V0 amplitude changes as proof of voltage-controlled magnetism or absolute magnetic moment.
