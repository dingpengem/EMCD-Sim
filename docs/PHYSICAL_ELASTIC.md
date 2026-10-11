# V0.2 — Physical elastic Bloch-wave backend

## Scope and status

This patch replaces the adjustable extinction-distance **surrogate** with a real (nonabsorptive) independent-atom elastic potential for **neutral FCC nickel**, propagated using a finite-basis Bloch-wave/Darwin–Howie–Whelan formulation. It remains **entrance-channeling only** for EMCD: the core-loss `DipoleMDFF`, sample-bias magnetic response, and outgoing inelastic electron trajectories are **not** quantitatively calculated.

The original `ElasticModel` survives solely as the explicitly selectable **surrogate** backend, allowing reproducible comparisons.

## Units and structure-factor convention

- Direct lattice `A` (Å, row vectors), reciprocal basis `A^{-T}` (cycles/Å, no `2π`).
- Elastic scattering factor `f_e(g)` (Å), with `g=|h b1 + k b2 + l b3|` in Å⁻¹.
- FCC Ni (neutral atoms, `a=3.524 Å`, four Ni sites per conventional unit cell).
- Isotropic thermal motion optional; its `B` in Å² is **not assumed**: default `B=0`. Choose a measured/reference value if comparing to experiment.

For atomic sites j, the independent-atom electron structure factor is

`F_G = Σ_j occupancy_j f_j(|G|) exp(-2πi G·r_j) exp(-B_j |G|²/4)`.

Its units are Å, with `G·r_j` dimensionless. The thermal factor follows the usual crystallographic isotropic Debye–Waller convention `B=8π² ⟨u²⟩`.

For Ni, the scattering factor is from **Lobato & Van Dyck (2014), Table 1, Z=28**:

`f_Ni(g) = Σ_{i=1..5} a_i (2 + b_i g²) / (1 + b_i g²)²`.

The 10 numbers are directly included in `src/emcd_sim/scattering.py`, with exact provenance. The parameters describe *neutral isolated Ni atoms* and do not represent a spin-polarized/charge-self-consistent DFT crystal potential. Other species can be supplied through the `IndependentAtomPotential.atomic_factors` mapping; **only Ni coefficients are bundled so far**.

## Dynamical equations

For electron wavelength `λ` (Å) at accelerating voltage `E_k`, relativistic `γ = 1 + E_k/(m_e c²)`, and cell volume `Ω` (Å³):

`dψ(z)/dz = i H ψ(z)`, `ψ(z) = exp(i H z) ψ(0)`.

For `z` in nm and transverse reciprocal g in cycles/Å,

`H_gg = -10 π λ (|k_perp+g|² - |k_perp|²)` nm⁻¹,

`H_gh = 10 γ λ F_(g-h)/Ω` nm⁻¹ (g ≠ h).

The factor `10` converts Å⁻¹ to nm⁻¹. The potential convention is electron-positive electrostatic potential; `H_gh = 10 σ V_(g-h)` with interaction constant `σ = γ m0 e λ/(2π ħ²)` [radians/(V Å)] and `V_G = [2π ħ²/(m0 e)] F_G/Ω` [V]. The `F_G` coefficients are **nonrelativistic** Born elastic factors, hence the explicit `γ` multiplying the coupling. `V_0` gives only a common phase and is not included in H.

This choice of diagonal sign comes from the same paraxial propagation equation as the positive elastic potential term. It is physically different from the sign convention used in the original surrogate, which remains unchanged for backwards compatibility.

For a two-beam systematic reflection, the conventional extinction distance is `ξ_G = π / |H_0G|` (nm). It is **computed**, not fitted, in the physical backend.

For 200 kV Ni, `a=3.524 Å`, **B=0** and this tabulation, `f_Ni(g_200) ≈ 2.62074 Å`, `ξ_200 ≈ 37.58 nm` (two-beam definition). These numbers are values of this independent-atom approximation, **not a validated experimental Ni extinction distance**. Finite-basis simulations redistribute intensities among beams and depend on tilt and beam cutoff.

## Beam selection

- Default: seven-beam `[001]` systematic row: `000, ±200, ±400, ±600`, generated with `BeamSet.systematic_row(order=3)`.
- Optional: centered in-plane `[001]` ZOLZ set selected by |g| cutoff with Friedel pairs preserved: `BeamSet.zolz(crystal, max_g_angstrom_inv, max_beams)`.
- Explicit beam lists are supported by `BeamSet`. Reflections structurally extinct in the crystal are rejected; missing off-axis beams constitute basis truncation, not forbidden coupling.
- The zone is currently represented by the **oriented crystal coordinate frame** (`g_z=0`). Arbitrary crystal rotations, HOLZ and convergent probe illumination are later work.

## Validation and reproducibility

Focused tests in `tests/test_physical_elastic.py` cover Lobato Ni values, FCC extinctions and Friedel conjugation, Debye–Waller reduction, Hermitian multi-beam Hamiltonian, elastic probability conservation, normalized positive-semidefinite entrance coherence, **exact two-beam Bragg Pendellösung** (the intensity transfers fully at `ξ/2`), and [001] ZOLZ pair selection.

Run:

```bash
python -m pip install -e '.[dev]'
pytest -q
emcd-ni --elastic-backend physical --beam-order 3 --output outputs/ni_physical
emcd-ni --elastic-backend physical --zone2d-max-g 1.0 --max-beams 13 --output outputs/ni_zolz
emcd-ni --elastic-backend surrogate --xi-nm 55 --output outputs/ni_surrogate
python examples/ni_elastic_convergence.py --max-order 6
```

Outputs include `ni_elastic_diffraction.png` (individual elastic Bragg intensities vs thickness), `ni_elastic_diffraction.npz` (depth, beam hkl, intensity, H), and illustrative `ni_emcd.*` and `metadata.json` (which records backend, beam count, Ni ξ200, B factor and limitations).

## What this **does not** solve

1. **Double channeling:** the scattered EELS electron must propagate from each inelastic event to the exit surface, ideally using a reciprocity-based exit-channel basis; entrance-only EMCD can be qualitatively misleading.
2. **Quantitative Ni MDFF:** the Ni `L₂,₃` edge is still an illustrative Gaussian model; requires spin-orbit/core-level matrix elements, actual electronic structure, edge-resolved spectra and correct site/transition formalism.
3. **Crystal potential limitations:** neutral independent-atom scattering omits bonding/charge-density deviations, absorption/inelastic TDS, validated thermal motion, magnetic contributions to elastic scattering and sample strain. The elastic solver is physical but not yet independently cross-benchmarked to Ni CBED or abTEM multislice.
4. **Convergence:** seven selected beams are **not proof of a converged Ni diffraction simulation**. For quantitative work compare larger row and 2D cutoffs, realistic orientation/tilt and absorption.
5. **Voltage response:** no predictive `V→μ`, domain motion, or electronic response; requires material/device-specific inputs.

## References

- I. Lobato & D. Van Dyck, *Acta Crystallographica A* **70**, 636–649 (2014), DOI: https://doi.org/10.1107/S205327331401643X — neutral-atom electron factors, Table 1.
- C. Ophus et al. / abTEM team, *The abTEM code: transmission electron microscopy from first principles*, https://pmc.ncbi.nlm.nih.gov/articles/PMC10446032/ — IAM potential parameterizations.
- abTEM, *Bloch-wave simulations*, https://abtem.github.io/doc/user_guide/tutorials/blochwave.html — Bloch scattering matrix and F_G convention, relevant for independent cross-validation.
- *A physical optics formulation of Bloch waves and its application to 4D STEM, 3D ED and inelastic scattering simulations*, *Acta Crystallographica A* (2025): https://journals.iucr.org/a/issues/2025/02/00/tw5012/ — high-energy paraxial elastic propagator and structure matrix.
