# Entrance-only EMCD tilt × thickness scans (v0.3.3)

## Purpose and physical scope

The FCC Ni systematic-row model propagates only (000), ±(200), ±(400), ±(600). Every retained reciprocal vector has g_y = 0, so the elastic Hamiltonian is independent of Y tilt. In the current **000-centered** momentum-transfer convention, the simplified EMCD model is also Y-tilt independent. This is a **beam-basis truncation issue**, not the consequence of fixed magnetic_fraction = 0.12.

A finite 2D ZOLZ basis includes reflections with g_y != 0, and can display Y tilt and thickness dependence. **A 13-beam result is not a converged quantitative prediction.**

## Installation and default run

With the independent emcd-python Conda environment active, run from repository root on Windows/macOS/Linux:

```bash
python -m emcd_sim.scan --output outputs/ni_tilt_thickness_scan
```

The default scan compares **systematic-row (7 beams)** and **zone-axis (13-beam 2D ZOLZ)** on the same **absolute** incidence angles: X tilt = 0 mrad, Y tilt = -10, -5, 0, +5, +10 mrad; thickness = 10, 20, 30, 40, 50 nm; Ni L3 energy = 852.7 eV; 33x33 reciprocal grid; 32 integration steps. The outputs use the same 000-centered coordinates and condition-appropriate virtual apertures.

### Full X/Y/tilt array

```bash
python -m emcd_sim.scan --conditions systematic-row zone-axis --tilt-x-mrad -4 0 4 --tilt-y-mrad -8 0 8 --thickness-nm 10 30 50 --max-beams 13 --output outputs/ni_tilt_3d
```

All flags shown on a single line for Windows PowerShell compatibility.

### Nominal near-2BC scan

```bash
python -m emcd_sim.scan --conditions near-2bc --tilt-x-mrad -8 -7.12 -6 --tilt-y-mrad 20 25 30 --thickness-nm 10 30 50 --output outputs/ni_near_2bc_scan
```

**Absolute tilt values override diffraction-preset defaults.** The two-beam, near-2BC, symmetric-3BC row bases omit all off-row beams, so Y tilt insensitivity there must not be interpreted as a physical property of experimental EMCD. Select sufficiently large 2D beam bases and test cutoff/convergence before drawing quantitative conclusions.

## Files

- `scan_results.csv`: rows for condition, X tilt, Y tilt, thickness, A/B signals, difference and asymmetry.
- `scan_{condition}.npz`: full 3D `difference` and `asymmetry` datasets and `A`, `B` arrays; array shape **(tilt_x, tilt_y, thickness)** with axis coordinates included.
- `heatmaps_{condition}_xXX.png`: L3 Y-tilt versus thickness difference and normalized asymmetry at each scanned X tilt, with one common color scale across all scan conditions.
- `comparison_y_tilt.png`: difference and asymmetry profiles at the midpoint thickness and the X tilt closest to zero.
- `comparison_reciprocal_maps.png`: nonmagnetic and magnetic *additive model terms* at the same representative (X tilt, Y tilt, thickness), using identical reciprocal axes and global color limits.
- `reciprocal_map_{condition}.npz`: numerical nonmagnetic and magnetic maps plus reciprocal coordinates and selected diffraction indices at the representative parameters.
- `scan_metadata.json`: approximation labels, beam sets, axes, shared color limits and reference indices.

The pixelwise magnetic term is **not** the measured aperture difference and is **not** a pixelwise EMCD asymmetry. The output difference A-B is in arbitrary units; normalized (A-B)/(A+B) cancels an explicit common thickness multiplier, but retains thickness dependence through depth-averaged Bloch-wave coherence.

**Scientific limits:** Ni MDFF is an illustrative Gaussian model, no DFT-derived matrix elements, no outgoing channeling, no absorption/TDS, no finite probe, and no calibrated cross-section units. The 2D example diagnoses truncation sensitivity, not theoretical accuracy.
