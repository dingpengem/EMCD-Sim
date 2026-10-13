# P2: non-DFT atomic MDFF and physically sourced radial amplitudes (v0.4.2)

## What is actually calculated

`ni_local_mdff.py` is a **local, independent-electron, cubic crystal-field atomic reference**, not an all-electron DFT, Hartree-Fock self-consistent calculation, full multiplet solver, or quantitatively calibrated nickel spectrum. It preserves the phase-coherent *complex* 2p→3d electric-dipole amplitudes required to construct a positive-semidefinite 3×3 energy-resolved MDFF tensor.

Core initial 2p states are 2p₃/₂ and 2p₁/₂ spin-orbit angular spinors (`j,mj`), coupled by explicitly calculated Condon–Shortley coefficients. Final states are orthonormal *real cubic* 3d orbitals `(z², x²-y², xy, xz, yz)` with separately specified spin-dependent hole occupations. The final 3d energy model uses **adjustable illustrative** 10Dq and exchange splittings. L₂/L₃ reference threshold energies are **inputs**.

The optional *screened hydrogenic* radial orbitals are normalized:

- `R_21(r)=A_p r exp[-Zeff_2p r/(2 a0)]`, with `A_p=(Zeff_2p/a0)^(5/2)/sqrt(24)`;
- `R_32(r)=A_d r² exp[-Zeff_3d r/(3 a0)]`, with `A_d=(2 Zeff_3d/(3 a0))^(7/2)/sqrt(720)`.

They give the 2p→3d radial length-gauge dipole integral in Å:

`R = ∫_0^∞ R_21(r) R_32(r) r³ dr = 6! A_p A_d / [Zeff_2p/(2a0)+Zeff_3d/(3a0)]^7`.

**Both effective charges are empirical inputs** (defaults 25 and 9 purely to exercise the method); their output is not a first-principles Ni radial integral. The code allows externally supplied tabulated atomic Hartree-Fock orbitals from a separately validated source, with numerical radial normalization, to replace the hydrogenic model. This provides a genuinely **non-DFT wavefunction route**, although accurate angular/multiplet/local-state physics remains essential for Ni.

An external radial CSV must have fields `radius_angstrom,R_2p,R_3d`, where the two latter columns are **full radial functions R(r), not u(r)=rR(r)** on the same increasing Angstrom grid. The import normalizes each function using `∫ |R(r)|² r² dr`. It does not infer the atomic state, functional, spin-orbit Hamiltonian or source from the CSV. The sign of an overall radial integral depends on orbital phase and is not an observable; the code takes its magnitude for the transition set and retains its signed value inside `radial_dipole_from_table()`.

`TransitionDataset` and `DipoleTensor` retain coherent complex dipoles, the energy resolution and physically required `2π` conversion of reciprocal coordinates. This patch **does not yet couple the new tensors into entrance-only Bloch-wave EMCD**. The legacy `emcd-ni` is unchanged and still uses its illustrative Gaussian magnetic fraction of 0.12.

## Run (Windows / macOS / Linux; Python 3.11)

```bash
python -m emcd_sim.ni_local_mdff --output outputs/ni_local_non_dft
python -m emcd_sim.ni_local_mdff --ten-dq-ev 1.0 --exchange-ev 0.3 --output outputs/ni_local_sensitivity
python -m emcd_sim.ni_local_mdff --radial-table path/to/atomic_hf_radial.csv --output outputs/ni_local_hf_radial
```

Outputs: `transitions.npz`, `mdff_tensor.npz`, `mdff_tensor.png`, `metadata.json`. Results must be labeled `is_dft=false`, `is_atomic_multiplet=false`, `quantitative_Ni=false` and *never* used as measured or first-principles Ni EMCD.

## Better non-DFT options: atomic multiplets and ligand-field charge transfer

To predict **localized L₂/L₃ fine structure**, a stronger non-DFT route is configuration-interaction multiplet theory. Include 2p and 3d spin-orbit couplings, Slater–Condon integrals `F^k`, `G^k` (from independent Hartree-Fock or fitted spectra), crystal-field energies, 2p core-hole interaction, exchange field, thermal occupation and, for covalent systems, explicit ligand orbitals/hybridization.

For many-body ground states |i> and core-excited final states |f>, calculate the *complex* vector `d_{fi,a}=<i|D_a|f>` with the **same** phase convention as `TransitionDataset`, then contract `T_ab(E)=sum_i,f p_i d_a d_b* L(E-E_f+E_i)`. Do not try to recover off-diagonal tensor phases from independently exported isotropic XAS intensity, left/right spectra, or DOS. Magnetic reversal and tensor PSD/Hermiticity remain required consistency checks. A full density-matrix / spectroscopy tensor can serve as an alternative input only after proving its exact relation, units and polarization conventions to the absorptive dipole transition tensor.

The documented research code **Quanty** supports atomic and ligand-field multiplets, Ni 2p→3d XAS/XMCD and energy-dependent polarization tensors. It is a practical external provider for local magnetic oxides and a reference for non-DFT operator construction; do not assume the downloaded executable or core source is MIT/open-source compatible. Integration should exchange numeric tensors/transition data, not vendor its source code.

Relevant upstream documentation:
- https://www.quanty.org/documentation/tutorials/small_programs_a_quick_start/xas
- https://www.quanty.org/documentation/tutorials/nio_crystal_field/nixs_l23
- https://www.quanty.org/documentation/tutorials/start
- https://abtem.github.io/doc/user_guide/tutorials/core_loss.html (core-loss transition-potential workflow; internally GPAW for radial functions)

## For metallic FCC Ni versus NiO

The isolated localized reference provides angular rules but cannot predict metallic Ni's 3d band dispersion, Fermi occupations, or realistic L-edge broadening. In particular, tuning effective charges, 10Dq, exchange or hole counts to reproduce 1% EMCD asymmetry is **not** first-principles prediction. For bulk FCC Ni, calibrated atomic Hartree-Fock plus an explicitly supplied final-state DOS/mixing model or spin-polarized SOC-DFT is usually more defensible than isolated multiplets alone. For NiO/magnetic correlated oxides, multiplet/charge-transfer models can be essential.

## Next development gate

1. Import *documented* Hartree-Fock radial functions and/or a Quanty transition/dipole tensor (check amplitude phase and units).
2. Verify Ni L₂/L₃ magnetic and nonmagnetic line shapes, spectral integrals and sum-rule limits against independently measured data, with uncertainty in local model parameters.
3. Couple `DipoleTensor` consistently to Bloch-wave **single channeling**, with coherent atom/site phases and separate Coulomb factors; compare this atomic-input model to a separately sourced SOC-DFT Ni tensor.
4. Defer outgoing/double channeling as agreed.
