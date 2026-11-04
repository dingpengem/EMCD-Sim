# Generalized atomic ionization — Iteration C

Status: source-only research feature, not a new release. Historical Ni regressions
validate compatibility, not quantitative metallic-Ni spectroscopy. Non-Ni material
parameters are physically unvalidated. No physical Fe EMCD prediction is supplied.

## Model and compatibility

`emcd_sim.atomic_ionization` separates explicitly supplied material parameters from
shared 2p spin-orbit/Clebsch–Gordan/complex dipole mathematics. The shared functions
alias the historical angular helpers in `ni_local_mdff.py`. Part 1B routes the Ni
compatibility API through the shared generator where exact equality is established;
its tiny-radial event-dropping reference path is retained separately. Ni defaults,
elastic providers/defaults and propagation kernels remain unchanged. No Ni electronic
parameters are inferred for another element. Historical project interpretation is
preserved while production orchestration is shared across providers.

For each core `(j,mj)`, final cubic orbital and spin, the complex amplitude is the
coherent sum over its spherical `l=2,m` components. Distinct initial/final events add
incoherently, with the declared hole occupation as weight. Dipoles are
`d=<core|r|final>` in Angstrom, and `T(E)=sum w d d† Gaussian(E-E_transition,sigma)`
in Angstrom²/eV. The Gaussian has unit integrated area; finite sampled coverage need
not capture all area. `I=ReTr(RT)` and angular `Q=2*pi*g` are unchanged. PSD follows
from nonnegative weights and outer products; no eigenvalue clipping occurs.

Local cubic energies are `+0.6*10Dq` for eg and `-0.4*10Dq` for t2g, relative to
a zero centroid, with exchange `-spin_sign*M_sign*exchange/2`. Reversal explicitly
swaps spin holes and reverses exchange in the same core-SOC basis. Both tensor states
are generated, stored and checked; no general conjugation-only reversal is imposed.

## Required declarations

The strict input JSON has exactly `schema: 1`, `kind: "atomic_2p3d"`, `parameters`
and an explicit ascending positive `energy_ev` grid. Every parameter below is
required; there is no element-specific default or preset.

|Parameter|Meaning and units|
|---|---|
|`element`, `atomic_number`|Matching symbol/Z from ASE; Sc–Zn 3d series only. Mathematical support does not establish material eligibility/accuracy.|
|`edge_energies_ev`|Positive ascending `[L3,L2]` core-edge reference energies, eV. Crystal/exchange shifts are added; selected energies are references, not fitted maxima.|
|`radial_integral_angstrom`|Positive effective 2p–3d radial dipole integral, Angstrom, common to this model's transitions.|
|`radial_source`|Nonempty provenance for that integral; no automatic atomic calculation or Z-based guess.|
|`crystal_field_basis`|Only `real_cubic_eg_t2g`. Orbital order is **z2, x2_y2, xy, xz, yz**.|
|`crystal_field_ev`|Nonnegative cubic `10Dq`, eV. Other symmetries, negative/inverted splitting and arbitrary crystal-field matrices are unsupported.|
|`exchange_ev`|Nonnegative spin splitting, eV.|
|`spin_resolved_holes`|Five `[up,down]` pairs in orbital order, each in [0,1], not all zero. These are holes per orbital/spin state, not total d-hole numbers.|
|`magnetization_local`|Exactly `[0,0,1]`. Reversal is generated internally.|
|`frame_to_crystal`|Explicit proper orthonormal 3x3 rotation from the local orbital/spin frame to crystal Cartesian. It rotates the **whole** model.|
|`broadening_ev`|Positive Gaussian standard deviation sigma in eV, not FWHM.|
|`source`, `validity`|Nonempty provenance and explicit validity/assumptions for all supplied material inputs.|
|`status`|`synthetic` or `physical_source_unvalidated`; never a declaration of quantitative validation.|

A radial integral may be evaluated separately with the existing normalized
`hydrogenic_radial_dipole_angstrom(z2p,z3d)` or `radial_dipole_from_table(r,R2p,R3d)`
helpers. Effective charges/functions, length units, normalization, calculation method,
source and limitations must be recorded in `radial_source`. Tables use full R(r),
not reduced u(r). This iteration takes the resulting integral as its explicit input;
it does not import undocumented radial tables or ship any new external atomic data.

Noncollinear spin relative to a fixed anisotropic crystal field is **not implemented**.
To orient this aligned model, rotate its entire frame explicitly; the tensor's crystal
magnetic axis is frame times local z. A different axis requested at run time is rejected.
This is not an arbitrary spin-rotation solver or material-specific magnetocrystalline
anisotropy model. Vanishing numerical transition scales below the historical
1e-14 Angstrom amplitude threshold are rejected, rather than silently discarded.

## Generation, GUI and project workflow

The [synthetic Fe parameter document](examples/synthetic_fe_atomic_parameters.json)
is an original software fixture. Its energy labels, radial integral, splittings,
holes and broadening are deliberately chosen test numbers, **not Fe measurements,
DFT, fitted constants or transplanted Ni inputs**. The BCC geometry in tests is used
only to exercise indexing and propagation. Do not compare its spectra to physical Fe.

```powershell
$env:PYTHONPATH='src'
python -m emcd_sim.atomic_ionization docs/examples/synthetic_fe_atomic_parameters.json outputs/synthetic_fe_atomic_tensor.json
```

Create `outputs` first for the CLI export. Existing outputs are never overwritten.
In the Part 1B GUI select **Atomic Ionization MDFF**, browse the complete atomic
parameter JSON, validate it, review the source/frame/checksum and acknowledge its
approximate status. Use Manual numerics. No intermediate tensor file is required.
The original Ni controls remain a historical compatibility option when no explicit
parameter file is selected; they cannot supply another element. No Fe/Co/Cr
quantitative presets are added. Imported CIF/site eligibility
remains a single element with full occupancy and certified translation-equivalent
ionization sites; a supplied atomic model does not bypass these checks.

The output contains original parameter UTF-8 bytes, SHA256, parsed declarations,
model identifier and both tensor states. Loading verifies the embedded checksum and
regenerates the tensors to check the model/parameters/frame/edge declarations. Projects
retain the generated-source checksum and complete atomic provenance. Altering that
source blocks rerun; missing sources leave saved results viewable. The original
parameter file is no longer needed for the CLI-exported imported tensor, since its
exact content is embedded. The direct atomic-provider GUI workflow instead binds
the original parameter JSON checksum and requires it for rerunning. Updating parameters requires a new source and explicit
revalidation. External imported tensor conventions remain strict and unchanged.
The `atomic_` metadata namespace is reserved: a partial declaration (including a
removed model tag) or unknown atomic field is rejected. A source with no atomic
declarations is an ordinary imported tensor, not a verified generated model; its
different checksum cannot replace a saved project's source silently. Checksums
bind bytes and declarations, not scientific truth or authorship.

Generated sources use the existing `ImportedSettings` serialization and generalized
Single/Double Channeling BW/FFT Multislice route, not a new contraction kernel. The
configuration's legacy Ni fields remain unused; the generated atomic input parameters
are retained separately in `metadata.imported_mdff.atomic_parameters`.

## Validation boundaries and missing physics

The exact Ni event/tensor regressions, independent sphere-quadrature dipoles, independent
L.S eigensystem, strength closure, Gaussian-area consistency, reversal, Hermiticity,
PSD, source integrity, project roundtrip and GUI worker tests are software validation.
The bounded thin synthetic Fe BW/MS comparison is a consistency check at its stated
basis/depth/detector/FFT settings. It does not establish global convergence or physical
accuracy. Energy sampling/coverage, broadening, detector/subpixel/depth/basis/cutoff and
slice/FFT refinement remain the researcher's responsibility. The preceding A+B review's
approximately **1.6% detector-refinement sensitivity** remains a limitation; no broad
convergence claim follows from Iteration C.

This is an approximate independent-electron, electric-dipole, rigid cubic-field model.
Missing physics include 2p–3d Coulomb/exchange multiplets, core-hole interactions,
charge transfer, material-specific radial potentials, final-state SOC/band dispersion,
self-consistent occupations, finite-q non-dipole response, absolute cross sections,
experimental magnetic-handedness calibration, AFM/ferrimagnetic/SDW order and
multi-element/site-resolved ionization. A scalar exchange shift is not a substitute
for these. No experimental accuracy or quantitative Fe/Co/Cr EMCD is established.
