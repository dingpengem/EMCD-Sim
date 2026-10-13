# WIEN2k XMCD → effective MDFF → EMCD: research pathway

**Status:** XMCD-constrained effective dipole model; **not** full first-principles MDFF, not quantitative Ni EMCD.

## Current data

Input: spin-polarized/SOC WIEN2k `Ni_fm.xmcd` (energy, RIGHT_POL, LEFT_POL, XMCD = RP-LP, XAS = RP+LP). Preserve unmodified source, record its SHA256, and verify both difference/sum columns. Example local data location: `data/wien2k_ni/Ni_fm.xmcd`. Other WIEN2k provenance files and symmat are optional archival files, not input to this approximation.

## Mathematical assumption

For collinear magnetization along z and an axisymmetric dipole response:

```
N(E) = [RP(E)+LP(E)]/2
D(E) = [RP(E)-LP(E)]/2
T(E) = [[N, i eta D, 0],
        [-i eta D, N, 0],
        [0, 0, beta N]]
```

eta defaults to 1 and beta to 1 as illustrative assumptions; eta's sign is convention-dependent. Enforce beta>=0 and |eta*D|<=N so T is Hermitian and positive semidefinite. Normalize to peak N for relative maps only. XMCD supplies one transverse antisymmetric response and the transverse sum, **not** full complex phase-resolved amplitudes, longitudinal absorption, finite-q multipoles or an absolute electron-scattering cross section. The model must NOT pass the `ni-metal-external` first-principles provenance audit.

## Present computational path

1. Import/check `Ni_fm.xmcd` and save source hash.
2. Build effective Hermitian spectral DipoleTensor using `effective_tensor_from_xmcd`.
3. Feed this into the **existing** `run_tensor_single_channeling` for L2/L3 reciprocal maps and virtual apertures, using only energies within the input range.
4. Sweep `eta` and `beta` and compare 2BC/3BC, thickness, and mistilt; distinguish model sensitivity from robust trends.
5. Later add outgoing-channeling / double-channeling, inelastic damping and controlled comparisons to experimental Ni EMCD; do not claim absolute EMCD from current entrance-only model.

An in-repo integration can call:
```python
from emcd_sim.xmcd_effective_mdff import effective_tensor_from_xmcd
tensor = effective_tensor_from_xmcd("data/wien2k_ni/Ni_fm.xmcd", energy_ev=energies,
                                    eta=1.0, beta=1.0)
# result = run_tensor_single_channeling(sim, tensor, thickness_nm=...,
#                                      grid_size=..., depth_steps=...)
```
Existing `cli.py` has **not yet gained a --mdff-model xmcd-effective switch**; this document intentionally describes the callable interface without claiming end-to-end CLI integration.

## Future full WIEN2k-derived MDFF, unchanged solver interface

Keep `DipoleTensor` as the interchange. Future exporter should retain spin/SOC-resolved core initial states, unoccupied band energies/occupations, k weights, three **complex** Cartesian 2p→band dipoles, consistent gauge/phase conventions, units and transition weights. Then use existing `TransitionDataset` → `dipole_tensor_from_transitions` → `run_tensor_single_channeling` (and later double-channeling). `ni-metal-external` audits declared metallic-Ni complex data and must remain fail-closed. Full q-dependent, non-dipole MDFF would require separate momentum-dependent matrix elements and a generalized kernel.

## Verification boundaries

Synthetic checks: sum/difference, Hermiticity, positive semidefiniteness, no energy extrapolation, eta=0 yields zero antisymmetric tensor, reversing eta reverses magnetic tensor, and consistency of magnetization/handedness conventions. Independent Ni XMCD spectral agreement alone is not validation of absolute EMCD.
