# FCC Ni incoming Bloch-wave: basis convergence diagnostic (v0.3.5)

## Goal

A finite number of elastic Bloch-wave diffraction channels can strongly change the incoming electron amplitudes, the diffraction pattern and the entrance-only EMCD signal. This diagnostic systematically expands the **2D zero-order Laue-zone (ZOLZ)** basis at a *fixed incident tilt, thickness, Ni potential and detector geometry* to quantify sensitivity. No outgoing channeling, DFT MDFF, or true quantitative Ni core-loss calculation is included.

This patch is **P1 diagnostic work**, not completion of the planned independent elastic validation milestone.

## Basic run (Windows, macOS, Linux)

```bash
python -m emcd_sim.convergence --output outputs/ni_convergence
```

With Python 3.11, the same run works through `emcd-convergence`. The defaults are FCC Ni [001], 200 kV, nominal 852.7 eV Ni L3, thicknesses 10/30/50 nm, and 2D ZOLZ cutoffs 0.75/1.2/1.4/1.8 cycles/Angstrom, which select 5/13/21/37 beams. Both `zone-axis` (0,0 mrad) and `symmetric-3bc` (0,+25 mrad preset) use **2D** bases throughout. `symmetric-3bc` denotes the tilt/aperture geometry only, not a fixed 7-beam row. The nominal 25 mrad off-row tilt is illustrative, not an experimentally validated three-beam alignment.

To include both 2BC and 3BC *incident-tilt geometries* while growing the same 2D basis:

```bash
python -m emcd_sim.convergence --conditions two-beam near-2bc symmetric-3bc zone-axis --g-cutoffs 0.75 1.2 1.4 1.8 --thickness-nm 10 30 50 --output outputs/ni_all_geometries
```

**Important:** `two-beam` in this tool means the 2BC incident tilt and its apertures with a **growing 2D ZOLZ** basis. The regular `emcd-ni --diffraction-condition two-beam` still deliberately retains only 000 and +200. This naming difference prevents comparing two distinct beam bases while incorrectly calling both calculations exact 2BC.

Other options: `--max-beams`, `--grid`, `--steps`, `--energy-ev`, `--acceleration-kv`, `--b-factor`, `--offzone-tilt-mrad`, `--output`. Use larger grids and depth steps for a serious numerical study. A low reciprocal grid can discretize the circular virtual apertures severely.

## Results and interpretation

- `basis_convergence.png`: 000 transmitted intensity, **illustrative** L3 integrated EMCD asymmetry, and elastic total variation versus beam count for each thickness and geometry.
- `convergence_results.csv`: row per `(condition, cutoff, thickness)`, with beam count, incident tilt, I(000), I(±200), total elastic intensity, EMCD difference/asymmetry and discrepancies relative to the largest finite basis.
- `convergence_results.npz`: numerical data with axes `(condition, cutoff, thickness)`, numeric arrays and text condition names. No Python pickle is required.
- `convergence_metadata.json`: beam hkl sets for each cutoff, tilt/aperture semantics, cutoffs, grid parameters and approximation flags.

Elastic total-variation distance is `1/2 Σ_hkl |I_hkl(small) - I_hkl(reference)|`, taking omitted reflections as zero. This compares **distributions** of diffracted intensity, not just 000. The largest included cutoff has discrepancy zero by definition, **not because it has been shown to converge**. A comparison of successive larger sets, independent elastic software, additional HOLZ/absorption where appropriate, and experimental geometries is required before certifying convergence.

Near-zero zone-axis double-difference EMCD is possible for mirror-symmetric detectors. Do not interpret it as zero local magnetism or rely solely on a relative percentage when its numerator is symmetry-suppressed.

## Physics and next gates

1. Expand the Ni beam cutoff until differences stabilize for **the observable and geometry of interest**; add kinematic/slice and Debye–Waller sensitivity. Demonstrate mathematical 2BC/3BC limits and independently cross-check diffraction versus a separate Bloch-wave/multislice implementation using matched potential and tilt.
2. Validate the source-to-detector convention and sample tilt using actual diffraction settings rather than a fixed 25 mrad off-row preset.
3. Implement physically sourced, complex Ni 2p→unoccupied-state dipole MDFF and independent spectral checks **only after** the elastic baseline is appropriately controlled.
4. Quantify the remaining entrance-only assumption later; double channeling is a deferred milestone.

For the project sequence see [ROADMAP.md](ROADMAP.md) and [SINGLE_CHANNELING_QUANTITATIVE.md](SINGLE_CHANNELING_QUANTITATIVE.md).
