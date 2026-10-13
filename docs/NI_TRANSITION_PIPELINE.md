# P2 Ni L2,3 transition matrix-element pipeline (v0.4.1)

## Status and scientific scope

This patch adds **computed 2p core spin-orbit angular momentum coupling** and
**2p -> 3d electric-dipole selection rules**, plus a portable adapter accepting
*already-calculated* complex transition dipoles. It is **not yet Ni DFT** and
**does not change the default EMCD maps**. The existing v0.4.0 tensor engine is
still independent of the entrance-only Bloch-wave simulator.

The new atomic-angular reference calculates angular transition matrix elements
but deliberately keeps these inputs illustrative:

- The unoccupied Ni 3d states are ideal spherical `|l=2,m,spin>` orbitals rather
  than spin-polarized DFT Bloch eigenstates.
- Final 3d crystal-field, exchange-band dispersion and spin-orbit mixing are
  **not** calculated. The two spin-hole weights are manually provided.
- The Ni L3/L2 reference energy losses are supplied (852.7/870.0 eV by default),
  not predicted by a core-level electronic-structure calculation.
- The common 2p-3d *radial* length-gauge dipole integral is an arbitrary
  input (1 Å by default), so **absolute intensity and magnetic response are
  uncalibrated**. No core hole, lifetime broadening beyond the specified
  Gaussian, or many-body multiplet structure is included.

This replaces *arbitrarily specified circular dipoles* in the toy dataset
with physically derived **angular** dipole matrix elements. It does **not**
replace the Gaussian `magnetic_fraction=0.12` in the existing `emcd-ni` CLI.

## Analytic 2p spinor basis and 2p -> 3d transition operator

Core SOC spinors `|l=1,s=1/2;j,mj>` use Condon-Shortley Clebsch-Gordan
coefficients. The initial 2p3/2 manifold (4 mj) corresponds to L3; 2p1/2
(2 mj) corresponds to L2. The final reference orbitals are pure 3d states,
`|l=2,m,ms>`; the electric dipole operator conserves spin.

For spherical unit-vector components `n_q` and a common radial integral `R`:

`<2,mf|r_q|1,mi> = R * sqrt(2/5) * C(1,mi;1,q|2,mf)`

with `q=mf-mi`, `q in {-1,0,1}`. Convert
`r_(+1)=-(x+i*y)/sqrt(2)`, `r_(-1)=(x-i*y)/sqrt(2)`, `r_0=z`
to Cartesian amplitudes. The `TransitionDataset` convention is
`d=<core|r|final>`, the conjugate of `<final|r|core>`.

The tensor built from these dipoles is a spectral Gram matrix:

`T_ab(E) = sum_n weight_n * d_n,a * conj(d_n,b) * G_sigma(E - E_n)`.

Spin-dependent empty-state weights change the antisymmetric imaginary tensor;
swapping spin-up and spin-down weights reverses the chiral response while
preserving the nonmagnetic response in this spherical reference. Unpolarized
weights yield a purely real tensor. In this restricted atomic reference the
L3 and L2 chiral signs are opposite and the unpolarized nonmagnetic L3/L2
integrated branching ratio is 2:1 (state-counting result, not a Ni DFT result).

## Run on native Windows, macOS or Linux

From the existing `emcd-python` Python environment:

```bash
python -m emcd_sim.ni_atomic_reference --output outputs/ni_atomic_reference
```

Outputs are `ni_atomic_transitions.npz`, `ni_atomic_tensor.npz`,
`ni_atomic_tensor.png`, `metadata.json`. Parameters include
`--spin-up-holes`, `--spin-down-holes`, `--radial-dipole-angstrom`,
`--l3-ev`, `--l2-ev`, `--sigma-ev`.

Changing these parameters is a **sensitivity calculation**, not a fitted Ni
magnetic moment. Physical Ni orbital/spin magnetization is not inferred from
these hole weights without a properly normalized band/electronic structure.

## External DFT core-to-band transition adapter: CSV -> NPZ

The CSV adapter is not tied to an operating system or DFT binary. It needs the
following UTF-8 columns:

```text
energy_ev,dx_re,dx_im,dy_re,dy_im,dz_re,dz_im,weight,edge,site
```

Each row represents one **coherent complex** 2p-core -> final-band transition;
`dx`, `dy`, `dz` are **length-gauge dipoles in Å**, **not intensities**, and
`weight` is nonnegative and already includes relevant core initial occupancy,
final empty-state weight and k-point weight. Preserve `L3` / `L2` core
identity, SOC, crystal/magnetization axes, k weights, site and wavefunction
normalization in the export provenance. Real and imaginary columns must be
retained; never replace amplitudes by `abs(d)**2` or DOS. The importer rejects
missing columns and invalid amplitudes/weights.

```bash
python -m emcd_sim.transition_csv --input complex_dipoles.csv \
  --source "Ni SOC-DFT: specify actual code/version, functional, k mesh, core states and normalization" \
  --output outputs/ni_from_external/transitions.npz
python -m emcd_sim.mdff_reference \
  --transitions outputs/ni_from_external/transitions.npz \
  --output outputs/ni_from_external/mdff
```

For Windows PowerShell, run each command on one line or use PowerShell's
backtick continuation instead of Bash backslashes. `--amplitude-order
final_bra` converts externally supplied `<final|r|core>` to the required
`<core|r|final>` by complex conjugation. **Only use that option when the input
really is a Cartesian length-gauge dipole.** Raw finite-q
`<final|exp(i Q.r)|core>` matrix elements are a different representation and
must not be fed to this converter as if they were dipoles.

The importer does not verify DFT physics and never marks data as validated
purely on the basis of the provided source string.

## Elk implementation reference and limitations

The open-source Elk `elnes.f90` source computes complex
`<i,k+q|exp(iq.r)|j,k>` elements through `genexpmat`, but its displayed ELNES
cross-section uses the **squared magnitude** and does not retain a complete
complex core-to-band transition dataset:

- https://elk.sourceforge.io/doxygen/html/elnes_8f90_source.html
- https://elk.sourceforge.io/doxygen/html/elk_8f90_source.html

A valid Ni converter requires **independent verification** of whether the
relevant relativistic 2p core spinors are included and how to isolate the
Ni core-to-unoccupied-band channels in the chosen Elk version. The native
Elk output `ELNES.OUT` alone is insufficient for a full MDFF: it contains
intensity, not complex off-diagonal matrix elements. A future Elk-specific
exporter should reconstruct/compute and export **complex x/y/z Cartesian
core dipoles** (or documented multi-q finite-momentum amplitudes), preserve
SOC and phase conventions, k integration and energies, and only then use the
portable CSV/NPZ bridge.

Elk source is GPL; EMCD-Sim is MIT. The current Python implementations are
original, do not vendor Elk's source code, and only exchange numerical data.

## P2 next acceptance gate

1. Produce a genuine converged **spin-polarized SOC-DFT FCC Ni** electronic
   structure, with fully characterized 2p core states and unoccupied bands.
2. Verify the core-to-band exporter yields *complex*, properly normalized,
   phase-consistent transition amplitudes (not ELNES intensity or PDOS).
3. Check real and magnetic Ni L2/L3 ELNES shape/branching versus independent
   reference spectroscopy, including broadening and possible core-hole effects.
4. Only then connect the resulting site-aware physical MDFF to incoming
   Bloch-wave scattering for quantitative **within-model** Single Channeling.

Double channeling stays deferred. `magnetic_fraction=0.12` remains an
**illustrative legacy parameter**, not a physically calculated Ni quantity.
