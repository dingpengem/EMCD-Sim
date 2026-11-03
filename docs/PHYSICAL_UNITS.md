# Physical units and numerical conventions

[Documentation index](INDEX.md) · [Physics](PHYSICS.md) · [User Manual](USER_GUIDE.md)

The unit labels below apply to the active application, new exports and current
guides. Label changes do not rescale any value or change a numerical default.

|Quantity|Displayed unit|
|---|---|
|Accelerating voltage|kV|
|Energy loss|eV|
|Specimen thickness, maximum slice step, extinction distance|nm|
|Beam tilt|mrad|
|Crystal lattice parameter, electron wavelength|Å|
|Crystallographic reciprocal vectors, beam and potential cutoffs|Å⁻¹|
|Detector coordinates and aperture radius, excitation error|Å⁻¹|
|Angular momentum-transfer vector Q|Å⁻¹|
|Bloch propagation eigenvalues|nm⁻¹|
|EMCD asymmetry|%|
|Raw intensity and signed intensity differences|a.u.|
|Memory budget and estimates|MiB|

Crystallographic reciprocal vectors obey **|g_hkl| = 1/d_hkl**. Detector
coordinates are transverse crystallographic reciprocal coordinates relative
to transmitted (000), in the same convention. Angular momentum transfer is
**Q = 2πg** (or Q = 2πq for a momentum-transfer difference q). Both have
inverse-length dimensions, but their numerical values differ by 2π.
Plane-wave factors use exp(i Q·r), equivalently exp(2πi g·r).
The dipole/Coulomb kernels already perform this conversion where required.
**Changing a displayed unit label never adds another conversion.**

Bloch propagation eigenvalues use a separate longitudinal convention:
exp(i γz), with γ in nm⁻¹ and depth z in nm. Excitation error s_g is a
crystallographic inverse length in Å⁻¹; it is not γ. An aperture's integrated
area has units Å⁻². An accurate aperture area alone does not certify
integration of a spatially varying scattering field.

Existing project keys and APIs with legacy reciprocal naming remain valid
for compatibility. Their stored numbers are unchanged. Loading older
projects does not rewrite saved metadata or scientific arrays. Historical
research records, accepted package reports and previously generated figures
are preserved with their original labels.

Study voltages remain dataset-specific: the corrected **200 kV thickness
study** uses 200 kV; the corrected Stage 4.2 survey and earlier corrected
thickness study use **300 kV**. The separate **9/30 nm Ni [017], Y = +15 mrad
spectral case study** also uses **300 kV**. Unit-label standardization changes
none of those calculations or convergence flags. A study's saved configuration
takes precedence over GUI defaults; "new study" is not a voltage definition.
