# P2 v0.4.3 — Complex MDFF tensor in entrance-only EMCD

**Research status:** a real complex transition-tensor contraction is implemented, not a quantitatively calibrated Ni MDFF or absolute cross section. The previous Gaussian `magnetic_fraction=0.12` mode remains the default for compatibility.

## Portable examples (Windows / macOS / Linux)

```bash
python -m emcd_sim --mdff-model ni-local --diffraction-condition near-2bc --output outputs/ni_local_emcd
python -m emcd_sim --mdff-model transitions --mdff-transitions path/to/transitions.npz --diffraction-condition symmetric-3bc --output outputs/from_transitions
python -m emcd_sim --mdff-model gaussian --output outputs/legacy
```

`ni-local` generates non-DFT cubic 2p/3d transition dipoles, with uncalibrated effective charges, exchange, crystal fields and empty-state weights. It is **not** an atomic multiplet calculation. `transitions` reads the [complex transition NPZ schema](MDFF_TENSOR.md) from an external source. `--mdff-sigma-ev` and `--mdff-radial-table` (for ni-local only) control linewidth or imported atomic radial functions. Multi-site datasets require `--mdff-site LABEL`; inequivalent-site spatial registration has **not** been implemented.

## Momentum, complex phases, and cross section

The transition convention is `d_a=<core|r_a|final>` in Å, `T_ab(E)=Σ_n w_n d_na conj(d_nb) L(E-E_n)`, with `S_dip(Q_g,Q_h,E) = Q_g^T T(E) Q_h`. This is the *proper* dipole MDFF without Coulomb denominators.

Transverse diffraction coordinates are 000-centered `q_g = q_detector - g` in cycles/Å; `q_z=-E/(h v)`. Convert all components to **angular** `Q_g=2πq_g` in rad/Å before tensor contraction or Coulomb normalization. The incoming coherence is `C_gh(t)=1/t∫ψ_g(z)conj(ψ_h(z))dz`.

For **equivalent localized FCC Ni core-loss sites**, `P_gh=mean_a exp[2πi(hkl_g-hkl_h)·fractional_site_a]`. The relative intensity kernel is

```
I_rel(q,E) = t Re Σ_gh C_gh P_gh S_dip(Q_g,Q_h,E) / (|Q_g|² |Q_h|²)
```

Equivalent core-loss sites are summed **incoherently**, but incident Bragg channels at each site interfere coherently. The site *mean* fixes only a relative per-atom scale. No fast-electron absolute cross-section prefactor, atomic density, detector solid-angle correction, absorption, thermal diffuse scattering, or outgoing propagation is present. The implementation rejects significantly negative total intensity.

The plotted `nonchiral`/ `chiral` terms are respectively from the real/imaginary portions of the complex Hermitian tensor. Imaginary components may have nonmagnetic origins in more general materials; magnetic interpretation requires magnetization-reversal checks, not simply a nonzero `Im(Txy)`.

## Results and limitations

- `ni_emcd.png`, `ni_emcd.npz`: original L3 map and aperture-resolved L2/L3 spectra.
- `ni_mdff_reciprocal.png`: common-scale 2×2 nonchiral/chiral L3 and L2 maps with (hkl) and aperture markers.
- `ni_l2_reciprocal.npz`: L2 map arrays; `input_mdff_tensor.npz`: actual complex input tensor.
- `metadata.json`: explicit tensor source, `magnetic_fraction_applied=false`, `mdff_quantitative_Ni=false`, `outgoing_channeling=false`, `cross_section_units=relative_only_missing_fast_electron_prefactors`.
- `muB_per_atom=null` in tensor-mode CLI output is deliberate. A physical magnetic moment is **not inferred** from uncalibrated orbital/spin weights.

A spin-degenerate test requires **both** equal spin hole occupations **and** zero exchange splitting. Only using equal hole weights leaves spin-dependent spectral shifts.

Legacy `--voltage-v`/ `--voltage-table` scaling is intentionally rejected for tensor modes. To study bias, supply a new physically calculated transition data state for each bias instead. Future work: real Ni SOC-DFT/atomic multiplet complex transition datasets, inequivalent sites, reference spectroscopy, calibrated absolute units, then outgoing double channeling.
