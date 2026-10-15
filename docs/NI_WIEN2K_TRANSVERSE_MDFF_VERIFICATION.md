# Ni WIEN2k transverse MDFF verification (2026-10-13)

## Result

The uploaded `Ni_fm_EMCD_DFT_inputs.tar.gz` contains a native five-column `Ni_fm.xmcd` (energy, RP, LP, XMCD, XAS). Repository `xmcd-effective` already imports **both** the average transverse XAS and magnetic XMCD spectrum; a new XAS parser is unnecessary.

Independent verification against the uploaded source:
- SHA256 of `Ni_fm.xmcd`: `a0e28ea6423b6c7832bb3cce6d69d71aa59336a221baeee3d2556b49ba501283`
- 4,329 energy values spanning **823.625–882.521 eV**
- Max absolute residual `(RP+LP)-XAS`: **5.0e-9** in source units
- Max absolute residual `(RP-LP)-XMCD`: **1.0e-9** in source units
- `max_E |M(E)|/N(E)`: **0.3098419501**, with `N=(RP+LP)/2` and `M=(RP-LP)/2`
- `max |T - T†|`: **0**; minimum eigenvalue **1.23057e-6** in *unscaled* source units for `eta=beta=1`

## Model being validated

```text
T_xx = T_yy = N(E) ; T_zz = beta*N(E)
T_xy = +i*eta*M(E) ; T_yx = -i*eta*M(E)
```

The importer in `src/emcd_sim/wien2k_xmcd.py` already checks the five-column sum/difference identities. `src/emcd_sim/xmcd_effective_mdff.py` already constructs a Hermitian positive-semidefinite effective dipole tensor, checks `|eta*M|<=N`, and normalizes by peak `N` for **relative** maps. The current CLI route uses entrance-only single-channeling.

## Unresolved physics assumptions

1. `eta=1` is **not** independent calibration of circular-polarization handedness relative to the electron-scattering MDFF sign or absolute strength.
2. `beta=1` assumes a longitudinal absorption `T_zz=N` that the XMCD left/right circular-polarization pair does not independently determine. Obtain linearly polarized XAS or full Cartesian dipole amplitudes to constrain it.
3. The spectral tensor remains an **axisymmetric dipole proxy**, not finite-q/full-transition MDFF, and does not include outgoing dynamical channeling.
4. Positive semidefiniteness and sum/difference consistency validate internal physical consistency, **not** Ni EMCD cross-section accuracy.

## Next step

Use existing `xmcd-effective` CLI with `eta=1, beta=1` as baseline, then sweep `eta` and `beta` while holding diffraction condition, sample thickness, energy windows and solver settings constant. Treat the resulting map changes as model sensitivities. Compare to the Gaussian pathway separately; do not describe differences caused by changed spectrum normalization as newly predicted diffraction physics.

No changes to the existing importer or tensor kernel are needed for these checks.

## Current committed source provenance (2026-10-15)

The independent archive hash above does **not** identify the current committed
`data/wien2k_ni/Ni_fm.xmcd`. Its Git blob SHA256 is
`4fd517af3e54db94588a76b7a6ed9c2f9a1b745cd8fe52b9fca0f87fc4938db3`,
also recorded by the published near-2BC example. Windows CRLF checkout bytes
have a further distinct hash. See the [reversal diagnostic provenance investigation](XMCD_MAGNETIC_REVERSAL_DIAGNOSTICS.md#source-provenance).
The earlier archive is unavailable for comparison here; the independent
verification above applies to that earlier dataset and does not establish
byte or numerical identity with the current committed file.
