# XMCD magnetic-reversal diagnostics (v0.4.6 milestone candidate)

This diagnostic separates magnetic-reversal-odd intensity from reversal-even
detector/diffraction asymmetry within the existing XMCD-constrained effective
model. It is relative intensity, entrance-only, and not an experimentally
validated quantitative Ni prediction or an experimental error bound.

For N=(RP+LP)/2 and M=(RP-LP)/2, the paired tensors have diagonal
(N,N,beta*N), Txy=+i*eta*M and Tyx=-i*eta*M for the plus state, and the
opposite off-diagonal signs for the minus state. Both use the same source peak
N normalization and energy grid. This is a controlled model-level reversal
of the antisymmetric response, not a separately calculated self-consistent
DFT magnetic state. Complex conjugation is not asserted to implement exact
magnetic reversal for arbitrary external DFT tensors.

The existing contraction Cgh=depth_average[psi_g conj(psi_h)] with
S(Qg,Qh,E)=Qg^T T(E) Qh is unchanged. Angular Q=2*pi*q is used internally;
map coordinates remain crystallographic cycles/angstrom. Coulomb factors
1/(|Qg|^2 |Qh|^2), the FCC site phases, thickness integration and the existing
longitudinal-transfer approximation are retained. Both forward calculations
use the same model object, elastic potential, beam basis and aperture geometry.

For each response, delta_plus=I_A_plus-I_B_plus and likewise delta_minus.
The saved quantities are:

- delta_odd=(delta_plus-delta_minus)/2, the reversal-sensitive contribution.
- delta_even=(delta_plus+delta_minus)/2, the reversal-insensitive difference.
- sigma_ref=[(I_A_plus+I_B_plus)+(I_A_minus+I_B_minus)]/2.
- A_odd=delta_odd/sigma_ref and A_even=delta_even/sigma_ref.
- A_raw_plus and A_raw_minus use their respective detector-sum denominators.

The odd part of separately normalized raw asymmetries generally differs from
A_odd because their denominators can differ. For each denominator, values at
or below 1e-12 times its peak magnitude are invalid: normalized outputs are
NaN and masks are saved (`valid`, `valid_raw_plus`, `valid_raw_minus`).
A wholly zero spectrum has no valid normalized points.

Raw A-B need not be purely magnetic: tilt, aperture geometry, finite beam
truncation and dynamical diffraction can generate reversal-even differences.
With eta=0 the odd components vanish but the even detector difference need
not vanish. Apertures come from the existing benchmark, including symmetric
3BC A=RU+LD and B=RD+LU.

At the sampled energies nearest the L3/L2 references, total maps are separated
as I_odd=(I_plus-I_minus)/2 and I_even=(I_plus+I_minus)/2. The actual selected
energies are recorded; these are not energy-integrated edge maps. L3 maps are
retained from the full spectral calculation; L2 maps use the same existing
solver on an adjacent two-sample tensor subset with the same normalization.

## Reproduce

From the repository root, install the package into your Python environment:

```text
python -m pip install -e ".[dev]"
```

The following single-line command works in Windows CMD, macOS and Linux
shells, without platform-specific line continuations:

```text
python -m emcd_sim.xmcd_reversal --xmcd-file data/wien2k_ni/Ni_fm.xmcd --condition near-2bc --eta 1 --beta 1 --thickness-nm 30 --grid 65 --steps 64 --output outputs/ni_xmcd_reversal
```

The default acceleration is 200 kV. `--condition` accepts `zone-axis`,
`two-beam`, `near-2bc`, `symmetric-3bc`, or `all`. Further controls include
`--acceleration-kv`, `--beam-order`, `--zone2d-max-g` (zone-axis only),
`--max-beams`, `--offzone-tilt-mrad`, `--tilt-x-mrad`, `--tilt-y-mrad`,
`--energy-points`, `--l3-energy-ev` and `--l2-energy-ev`. Tilt overrides are
absolute components in mrad, not additions to the preset. Grid/depth controls
are `--grid` and `--steps`; a very coarse grid may miss physical apertures and
is rejected by the existing solver. Defaults retain 185 samples over the
source intersection with 837-882 eV, 7 row beams, and 64 depth steps.

The Python interface is `run_xmcd_reversal(model, xmcd_file, energy_ev, ...)`.
It returns `ReversalResult` containing spectra, maps and tensor sources;
`parity_spectra` performs the detector aggregation and parity arithmetic.
`plot_summary` is separate from the physics calculation.

Each condition directory contains `magnetic_parity_spectra.npz`,
`magnetic_parity_L3_map.npz`, `magnetic_parity_L2_map.npz`,
`magnetic_parity_summary.png`, and `metadata.json`. NPZ keys use the ASCII
names defined above, plus energy and reciprocal coordinates. Map files also
retain I_plus and I_minus. Metadata records the exact input-byte hash,
parameters, beam basis, apertures/groups, sampling, selected energies and Git
commit when available. A commit identifies the checkout base during an
uncommitted development run. The console reports L3 A_raw_plus, A_odd and
A_even; undefined quantities print as JSON null.

## Source provenance

Before generating this example, the exact committed blob at baseline
`beca6adfda621098f10796a6435306d67f5345df` was hashed using `git show` bytes:

```text
4fd517af3e54db94588a76b7a6ed9c2f9a1b745cd8fe52b9fca0f87fc4938db3
```

It contains 372375 bytes and matches the existing committed near-2BC example
metadata. In this Windows checkout the working file contains 376704 bytes,
with CRLF line endings, and hashes to:

```text
bb9bdd478d54cc8de60403409f4d90e63deb11a64891bbac6754f867be14deda
```

Replacing CRLF with LF in memory reproduces the committed bytes exactly.
The new metadata deliberately records the exact working-file hash, as does
the unchanged importer. No source data were rewritten.

The earlier independent verification in
[NI_WIEN2K_TRANSVERSE_MDFF_VERIFICATION.md](NI_WIEN2K_TRANSVERSE_MDFF_VERIFICATION.md)
records `a0e28ea6423b6c7832bb3cce6d69d71aa59336a221baeee3d2556b49ba501283`
for an uploaded archive dataset. That hash is not the current committed file
and is not explained by this checkout's CRLF/LF difference. The source file
history contains the import commit `29ae655`; the earlier archive is not
available here for byte or numerical comparison. Its independent verification
must not be transferred to the current file on the basis of a matching name
or sample count. Their equivalence remains unresolved.

## Physical limits and verification

The calculation retains finite elastic bases, perfect-crystal parallel-beam
entrance channeling, an axisymmetric dipole proxy, an assumed beta, uncalibrated
eta handedness and relative normalization. It omits outgoing channeling,
finite-q/full DFT-MDFF information and detector/cross-section calibration.
It does not determine magnetic moments. Parity separates terms within this
model; it does not establish quantitative accuracy or convergence.

Focused checks use synthetic spectra and small grids:

```text
python -m pytest -q tests/test_xmcd_reversal.py tests/test_xmcd_effective_mdff.py tests/test_single_channeling_tensor.py tests/test_diffraction.py
```

No production four-condition sweep is required. Existing commands, published
scientific examples and the physical elastic backend are unchanged. Version
0.4.6 remains a review milestone candidate; this patch does not tag a release.

## Executed reference check

The command above completed on this Windows checkout at 200 kV, 30 nm,
eta=beta=1 with 65x65 reciprocal samples and 64 depth steps:

| Selected sample | Energy (eV) | A_raw_plus | A_odd | A_even |
| --- | ---: | ---: | ---: | ---: |
| L3 | 852.6521739130435 | 0.001680629197418126 | 0.001680629197418126 | 0 |
| L2 | 870.0163043478261 | 0.0004095760700967556 | 0.00040957607009678855 | -3.30e-17 |

All 185 reference denominators were valid and both selected total maps were
nonnegative. The near-zero even response is specific to this preset and
sampling; it is not a general statement about detector/diffraction asymmetry.
The synthetic asymmetric-aperture test explicitly retains nonzero even
response at eta=0. Results are under `outputs/ni_xmcd_reversal/near-2bc/`
(ignored generated artifacts); published examples were not regenerated.

The focused command passed **19 tests** using Python 3.10.9. Python 3.11 was
not available in the environment for a direct runtime check; the new code
uses syntax and standard-library interfaces supported by Python 3.11.
