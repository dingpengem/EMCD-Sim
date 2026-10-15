# WIEN2k Ni complex-transition audit (Phase 1)

Audit date: 2026-10-15. **Final classification: INTENSITY_ONLY.**

**No: the existing local outputs do not demonstrate enough information to
build a general genuinely DFT-derived Ni L3/L2 Cartesian dipole tensor.**
They preserve two circular projected intensities per k-point/band, with core
magnetic substates summed, not complex Cartesian amplitudes or all Hermitian
products. Their sum/difference constrains transverse response but does not
supply longitudinal or general off-diagonal components. No phases were
invented, no transitions imported, and no dataset labeled `ni-metal-external`.

This is a data/feasibility audit only. No WIEN2k, Bloch, multislice or EMCD
calculation was run; no original calculation file was modified. Existing
user-added files and the modified tracked Ni_fm.xmcd were preserved. The
requested branch starts at 7135964fe061f09e0d331a8cddab0f0016a893a7;
the later plotting-marker commit is outside this explicitly requested base.

## Inventory and evidence scope

Primary root: `C:/Users/peng863/EMCD-Sim/data/wien2k_ni`.
Every file under this root was enumerated recursively, streamed for SHA256,
format-identified and read. There are 15 files, all directly readable ASCII
text; no subdirectories or archives occur in this root. The exact absolute
path for each entry is the primary root plus the filename below. Sizes are
bytes; hashes refer to the actual local bytes, not Git blobs or old examples.

| Filename | Bytes | SHA256 |
|---|---:|---|
| Ni_fm.broad1 | 372294 | `b51823b6a73df4533fee3382bccae2b3496e7aaf86d6b315976921cea5d38e2f` |
| Ni_fm.broad2 | 372294 | `9594428e7f15adc15fe8a50b0e3f705e75c68a8ab10466555452f26697ac6559` |
| Ni_fm.in2c | 381 | `4bacaeee0cda7c85831551d3642b670e2b8a57333ed25f037bf7da88fa826096` |
| Ni_fm.inc | 241 | `9d2ce38113cfe8f924ed5e15e9f331511d4455f5736b0b32e0f9e9cb81436d4b` |
| Ni_fm.injoint | 98 | `11333c6dcc3d9e564ac8aeaf39299d4f0aa19fce03d6265f8a69acafddfb42d9` |
| Ni_fm.inop | 439 | `675bc2cc16d372f5ee2cefe65e0da4d090a244202e2bedb27adfdfe3d6574eb9` |
| Ni_fm.inso | 250 | `1031918977eab5ab8abbc7da42b3629fb9e38e3969449a8ae3d3e3aad38f0d5b` |
| Ni_fm.outputopup | 818507 | `a792df2eb595efc9df927093b0f5ee33229a370ec5f8fd7d5f36f5fe4fc0f37b` |
| Ni_fm.raw1 | 372294 | `d4cfb643ffa797701ef1b443d592d9b09112298e624db11c87690d208b0822f1` |
| Ni_fm.raw2 | 372294 | `b6c8e90f737b221e0228b4b38b17d2215ccb179bd0de42dc74dff2980fd5dd97` |
| Ni_fm.rawxmcd | 372294 | `2f25f2dd5bc32745a7c213df889f9f75debc3dc4cc3bc4fc7ba335d3de343cd9` |
| Ni_fm.struct | 1844 | `a8f3028871c426556c007b590bb27cb31baf71a868a4548c00650f93f1927a00` |
| Ni_fm.symmat1up | 2496498 | `09e2b730822c3b9e9abe349cd10587003293ac9ca3529ca28de971a6da3037af` |
| Ni_fm.symmat2up | 2496498 | `8010bc6353bd52435c3cccf6c3bf85ee08c0d91daf653b2ac7689f3b6a6ddae6` |
| Ni_fm.xmcd | 372376 | `a0e28ea6423b6c7832bb3cce6d69d71aa59336a221baeee3d2556b49ba501283` |

Compact machine-readable inventory, format/count checks, archive member lists
and spectral discrepancies are in the ignored
`outputs/ni_wien2k_transition_audit/audit_diagnostics.json`. The utility verifies
that the complete primary inventory is unchanged after its read-only pass.

An external **distribution**, not a Ni calculation backup, was found at
`C:\Users\peng863\Downloads\WIEN2k_18.2.tar` (126371840 bytes), SHA256
`4d048ef228a342dd456074b4a910a87b01673a51a0e2d569d50faed338ada152`. Its 75 top-level members were listed, and selected nested
OPTIC, JOINT and user-guide files were inspected directly in memory without
extraction. No licensed source text is included in this repository or report.
Relevant inspected members and hashes:

| Archive / member | SHA256 |
|---|---|
| SRC_optic.tar.gz / SRC_optic/opmain.f | `bc2f8f81636843e39ff1994a646d3a4581cf0e28e6d4079f43a7cf9fa0fdecb8` |
| SRC_optic.tar.gz / SRC_optic/outmatABZ.f | `251d58860919c55c0b0079eb72db94a4b4da84bf1410aa88310802f5f642604a` |
| SRC_optic.tar.gz / SRC_optic/sph-UPcor.frc | `788e93940f00d2c4b3e32fc984a0b34b5b2e9a72c7c0d382b4d09b71e96fbbb6` |
| SRC_optic.tar.gz / SRC_optic/mmatcv.f | `624999908ebf8e4923b465ec877003e04c358ef5a6e3bf092c71c36c4e339c8f` |
| SRC_joint.tar.gz / SRC_joint/readopx.f | `20dc0ca862917fe24c2bc2d1d15f85a82d877d497bf37f88047cbc0fdf713446` |
| SRC_joint.tar.gz / SRC_joint/dich2.f | `b6014b8d672723cca2ac3e34eb3a231bdf2cf73c665b34bab617764866b6e878` |
| SRC_joint.tar.gz / SRC_joint/joint.f | `c7882e0a749ae528bcc159e510f99cc9785d6b354b270abb37851cfd531affd6` |
| SRC_usersguide_html.tar.gz / SRC_usersguide_html/8Analysis_Properties.html | `31398a1d6b36b14d78a43e7e01d6e00dce8c324c58510f641f058557e1909a53` |

The archive is labeled WIEN2k 18.2; it is not proof of the version or patches
used to generate the calculation. No WIENROOT environment, executable version
banner, build manifest or installed source tree was established in the
inspected Windows locations. The archive behavior is verified for those exact
member hashes; correspondence to the generating binary is inferred from
matching records and spectral checks, not asserted as a version identification.
No WSL retrieval was needed or attempted. The local Downloads directory was
also checked for WIEN2k/case archives; the distribution above is the available
source reference, not a backup of missing Ni wavefunctions.

Missing from the complete primary inventory: `corewfup`, `corewfdn`,
`upoptic.def`, vector/vectorso spinor files, energy/energyso files, klist,
weight and tetrahedron integration files, SCF/Fermi-level and LCORE output,
JOINT execution log, and a unit-4 unsquared matrix-element export. No Ni
calculation archive was present in the primary tree. These absences limit both
independent integration and claims about upstream-state reuse.

## Actual symmat records

Both files start with `T L23 LEFT RIGHT ALL`. T is the SOC flag, L23 the edge
family, LEFT/RIGHT the two polarization labels, and ALL the atom-selection
mode; **ALL is not a third numerical tensor column**. A following block header
reports KP, NEMIN/NEMAX, the calculation window dE=-5.00..3.00 and a K label.
The dE fields are absolute matrix-element window limits in Ry, not a
per-transition energy. The files contain 2,744 sequential k-point blocks each,
60,858 band records each, and 18-24 bands per k-point. Every block contains
exactly the declared consecutive band indices. All two-column values are
finite, real and nonnegative.

Representative actual records (not amplitudes):

```text
symmat1up: 2p   7  0.139227E-01  0.464089E-02
symmat2up: 2ps  7  0.686190E-33  0.915723E-02
```

The minimum/maximum intensities are 2.60779e-32 / 0.639838 for symmat1up,
and 6.8619e-34 / 0.445337 for symmat2up. There is no dx/dy/dz, real/imaginary
pairing, transition energy, occupation, integration weight, explicit spinor
index or core m_j index in a record. Up is not evidence of spin-independent
transitions: the execution log explicitly states spin polarization and SOC.
The 2,744 count is compatible with 14^3 but does not by itself establish
integration weights, BZ topology or convergence. Outputopup prints k-point
coordinates and band ranges throughout; its detailed band-energy diagnostic
is confined to initial records and cannot replace complete energy/weight files.

## Verified source behavior versus literature

The following are read-only observations of the local source archive, with
file line references so a licensed owner can check them:

- `opmain.f:256-260,472-477` associates the first L23 core with 2p and the
  second with 2ps. `sph-UPcor.frc:273-286` selects 2ps with twice-j=1 and
  2p with twice-j=3. Thus symmat1up is L3 (2p3/2) and symmat2up L2
  (2p1/2), consistent with the actual file labels and core inputs.
- `mmatcv.f` accumulates complex core-bra gradient matrix elements from radial
  integrals and LAPW coefficients, with SOC angular coupling. In
  `sph-UPcor.frc:694-721`, the spinor contributions are combined into complex
  Cartesian DOPMATX/Y/Z for each band and m_j, including the momentum -i
  factor, before OUTMATABZ is called.
- `outmatABZ.f:57-88` receives those complex values. A unit-4 path at
  lines 69-73 can write unsquared Cartesian complex quantities when the
  supplied output mode is ON. The audited inop says OFF, and this export is
  absent. Its unit/file mapping requires the missing definition file.
- `outmatABZ.f:155-189` forms O_x+i O_y and O_x-i O_y, takes squared
  magnitudes, sums over m_j and writes two real numbers per band. The explicit
  symmetry-loop normalization does not preserve m_j-resolved phases; its
  transverse operation is not an export of nine Cartesian tensor products.
- `opmain.f:324-337` reads the requested columns but forces two columns with
  indices 1 and 2 for XMCD. Thus the generic Re xx/Re zz comments and nine
  possible optical columns listed in inop do **not** establish Cartesian
  product availability in these XMCD files. Recommending nine generic optical
  columns as an automatic solution would be unsupported.
- `readopx.f:39-52` reads two real band values into JOINT. `joint.f:420-464`
  separately requires eigenvalues and weights, including Fermi information.
  `dich2.f` combines the two core edges, applies broadening and writes the
  raw/broadened intensity observables. This is where further k/band integration
  occurs; unlike the final spectra, symmat still distinguishes k and band.

The local bundled user guide's OPTIC/JOINT sections corroborate squared
matrix output and separate L3/L2 edge handling. The historical method is
also described by [Pardini et al., CPC 183 (2012), 628-636,
DOI 10.1016/j.cpc.2011.12.010](https://doi.org/10.1016/j.cpc.2011.12.010)
and its [author preprint](https://arxiv.org/abs/1104.1558). The requested page
range 628-635 differs from the publisher's 628-636. These sources provide
historical context, not proof of the generating executable's version.

There is a handedness-label warning: the symmat header calls its first column
LEFT, while archived JOINT dich2 writes the first combined column as RIGHT.
No handedness swap should be silently introduced based on names. A Phase 2
export must establish operator order, circular convention and physical
magnetization sign with a controlled polarization check.

## What is and is not reconstructible

Define P_ab=sum_m O_a conj(O_b) for the archived momentum convention.
For its unnormalized circular combinations,
C_plus=Pxx+Pyy+2 Im(Pxy), C_minus=Pxx+Pyy-2 Im(Pxy).
Thus (C_plus+C_minus)/2 gives the transverse trace, and
(C_plus-C_minus)/4 gives an antisymmetric transverse product in that specified
operator convention. Individual phases do not follow from these identities.
Circular normalization, momentum-to-length conversion and the LEFT/RIGHT
label issue must be resolved before identifying these with EMCD-Sim T_ab.

| Target Cartesian length-gauge component | Classification from these files |
|---|---|
| Txx | Reconstructible only under explicit axial symmetry, with operator/scale conversion; only transverse trace is measured |
| Tyy | Same; equality to Txx is not independently measured |
| Tzz | Unavailable; no longitudinal response exported |
| Re(Txy) | Only symmetry-assumed zero for a suitable axial ensemble; unavailable generally |
| Im(Txy) | Reconstructible from circular intensity difference as a momentum-product combination; length-gauge magnitude/sign require verified conversion/convention |
| Re(Txz), Im(Txz) | Only symmetry-assumed zero for axial ensemble; unavailable generally |
| Re(Tyz), Im(Tyz) | Only symmetry-assumed zero for axial ensemble; unavailable generally |

Even an exact axial-symmetry reduction leaves independent Tzz unknown.
A finite per-k transition need not obey the energy-integrated ensemble's
axial tensor form. Setting beta=1 remains a model assumption, and arbitrarily
assigning dx,dy,dz phases from intensities would create fake transitions.
Complete Hermitian transition products would be sufficient for an
energy-resolved full dipole tensor without recovering individual amplitudes;
these two projections are not such a complete product set. Classification
INTENSITY_ONLY refers to the stored category-C circular projected intensities
(and final category-D spectra), despite the genuine partial transverse
information they encode; it is not FULL_COMPLEX_AVAILABLE or a validated
Cartesian PARTIAL_TENSOR_ONLY dataset.

## Core, energy, spin and broadening metadata

Struct identifies relativistic FCC Ni, atom 1 at the origin, lattice parameter
6.651839 bohr, local rotation identity. Inso gives magnetization [001], with
no atoms excluded from SOC; outputopup explicitly confirms spin-polarized SOC.
Inc lists n=2,kappa=+1,occupation=2 and n=2,kappa=-2,occupation=4, identifying
2p1/2 and 2p3/2, respectively. These are shell occupancies, not complete
transition weights or individual m_j factors.

Injoint supplies core energies -60.534300889 Ry (L3) and -61.819104105 Ry
(L2); these are actual saved input values, not independently checked LCORE
energies. The splitting is 17.48064455 eV using the archive's
13.605698 eV/Ry. A 0.001 Ry integration step and 0..2 Ry integration window
are supplied, with eV output, XMCD mode, switch 4 and two columns. In2c
requests FERMI and TETRA but contains no numerical EF or complete weights.

Dich2 combines edges using an integer displacement of 1,284 samples:
17.46971623 eV, rather than the exact core splitting. The remaining fraction
changes the rounded axis offset at the join. Edge raw/broad energies span
-7.40584..51.4796 eV relative to the JOINT Fermi reference; the combined
axis is 823.625..882.521 eV. Its offset varies 831.03034..831.04230 eV.
Inverting the archived axis rule only suggests EF near 0.544-0.545 Ry;
it is not an independently known EF and must not be used to fabricate
transition energies. The familiar requested map references 852.7/870 eV
are not substitutes for actual core-to-band excitation energies.

Injoint declares lifetime parameters 0.6 and 1.0 eV and spectrometer 0.1 eV.
The audited dich2 implementation uses the second lifetime for the first
(2p/L3) spectrum and the first for 2ps/L2. Its Gaussian sigma is
0.1/2.35 eV; the arctangent-bin Lorentz prescription uses 1.0 and 0.6 eV
as its width parameters. This parameter ordering is a source observation,
not an assumed physical assignment or a fitted width. No ad hoc rescaling
or energy shift was used to improve agreement.

## Limited intensity reconstruction and checks

All six five-column spectra contain 4,329 records. At printed precision their
XMCD and XAS columns equal the first polarization minus/plus the second;
maximum residuals are at most 1e-8 / 5e-8 for raw and 1e-9 / 5e-9 for
broadened outputs. The combined xmcd header itself identifies RP then LP.

Using the saved core splitting and integration step, independent addition
of edge 2 shifted by exactly 1,284 samples to edge 1 gives:

| Compared output / observable | Max absolute discrepancy | Relative Euclidean L2 discrepancy |
|---|---:|---:|
| rawxmcd RP | 8.10e-9 | 9.70e-7 |
| rawxmcd LP | 8.20e-9 | 4.76e-7 |
| rawxmcd XMCD | 1.00e-8 | 3.24e-6 |
| rawxmcd XAS | 5.00e-8 | 1.59e-6 |
| xmcd RP | 1.00e-9 | 1.15e-6 |
| xmcd LP | 1.00e-9 | 1.05e-6 |
| xmcd XMCD | 1.30e-9 | 4.84e-6 |
| xmcd XAS | 5.00e-9 | 1.58e-6 |

The independently evaluated finite-grid Lorentz-bin plus Gaussian broadening
of already saved raw edge intensities reproduces broad1/broad2 with maximum
absolute errors 1.56e-8 / 1.12e-8 and relative L2 errors 4.45e-6 / 4.98e-6.
These comparisons use the archived settings and no fitted gain. Differences
are consistent with rounded input/output and energy-grid representation.
They are consistency checks of integrated intensities and archived behavior,
not independent reconstruction of JOINT BZ integration from symmat. Missing
weights, complete band energies and EF prevent that stage; it is stopped here.
Neither agreement nor successful parsing proves complex MDFF availability.

## EMCD-Sim compatibility and minimum Phase 2

`TransitionDataset` and `transition_csv.py` require positive transition energy,
complex Cartesian length-gauge dx/dy/dz in angstrom, nonnegative weight,
edge, site and provenance, with d=<core|r|final>. From existing files only
edge labels and atom-1/site context can be populated directly; band/k indices
identify records but not complete physical weights. Energy, dipoles and full
weights cannot be populated without additional data. `ni_data_audit.py`
requires code version, SOC/core definitions, phase preservation and weight
provenance; this archive cannot pass by relabeling intensity data. The
existing `xmcd_effective_mdff.py` remains explicitly approximate.

The archived intermediate is a core-bra momentum/gradient quantity, not
angstrom length dipoles. For a local nonrelativistic Hamiltonian, in atomic
units p_if=-i*(E_f-E_i)*r_if, so r_if=i*p_if/DeltaE_Hartree; length products
require the squared energy conversion and bohr-to-angstrom factor.
That commutator conversion is conditional: relativistic/SOC, basis and operator
approximations must be checked for the actual implementation. A final-bra
export additionally needs the documented Cartesian conjugation. No conversion
is performed in this audit.

The smallest valid next phase is:

1. Identify the generating WIEN2k version/build and recover the complete Ni
   case: SOC vector files, potentials/radial/core states, band energies,
   Fermi level, k mesh and integration weights/geometry. Existing convergence
   and completeness are not established by the present output log.
2. Inspect/test that version's existing ON/unit-4 unsquared output path.
   The inspected 18.2 source already offers complex Cartesian output before
   projection. Therefore a new proprietary-source patch may be unnecessary.
   Verify actual definition-file destination, units, bra/ket order and implied
   m_j loop ordering; do not assume an ordinary ON file is self-documenting.
3. If reusable converged SOC wavefunctions and core/radial data exist, rerun
   only the required OPTIC export (and recover integration metadata); no SCF
   rerun is intrinsically required merely to change the export. The files
   currently inventoried are insufficient to do even that. If the state is
   lost or mismatched, upstream LAPW/SOC/LCORE work may be required; do not
   promise OPTIC-only reuse or launch it automatically.
4. Minimum export row: site, core n/kappa/j/m_j (or explicit core-summed
   product tag), k ID and coordinates, SOC band ID, E_core and E_band plus
   reference/units, occupation and unoccupied-final factors, BZ quadrature
   weights/normalization, and complex px/py/pz (or validated length dipoles).
   Preserve coherent spinor contributions before squaring. Record rotations,
   magnetization, symmetry treatment, build/source hashes and operator order.
5. An alternative minimal product export is all nine real independent
   components of the Hermitian Cartesian product, resolved by site, edge,
   k and band (m_j summed is allowed for a full-shell tensor). This avoids
   unnecessary individual phase recovery but must preserve off-diagonal
   products and correct energy/weight association. Do not manufacture
   TransitionDataset rows by arbitrary factorization of these products.
6. After a documented momentum/length conversion, true complex amplitudes
   can enter the existing transition CSV/NPZ bridge with full provenance.
   Complete product matrices instead need a separately reviewed direct-tensor
   import route. Validate polarization sums, Hermiticity, PSD, L3/L2 indexing,
   energy alignment and intensity normalization before any DFT-MDFF claim.

Recommendation: Phase 2 should first recover the generating case and verify
the existing unsquared export, not implement a new MDFF or reconstruct phases
from the two circular columns. **Stop at Phase 1:** no exporter, source change,
DFT rerun or DFT-derived EMCD calculation has been implemented here.

## Reproduction

Use the existing environment directly (no installation changes):

```powershell
& 'C:/Users/peng863/AppData/Local/miniconda3/envs/emcd-python/python.exe' `
  scripts/wien2k_transition_audit.py `
  --archive 'C:/Users/peng863/Downloads/WIEN2k_18.2.tar'
```

The audit used emcd-python, Python 3.11.17. The utility is limited to the
observed two-column symmat format and saved Ni broadening settings; it is not
a general WIEN2k transition parser or physics validator. It rejects malformed
blocks/intensities instead of inventing missing amplitudes. Licensed source
was read only from nested archives and only member names/hashes are recorded.

Focused validation used two stdlib unittest tests (including four malformed
record subcases): intensity-versus-complex schema, band-count consistency,
extra/missing columns, negative/nonfinite intensity rejection, read-only bytes
and inventory hashes. Both passed in emcd-python. Pytest is not installed in
that environment, so the checks use unittest without environment changes.
Run them with the same Python executable and `-m unittest discover -s tests
-p test_wien2k_transition_audit.py`. No broad suite was run.
