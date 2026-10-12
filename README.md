# EMCD-Sim

Independent, modular **electron magnetic circular dichroism (EMCD)** simulation project, initially benchmarked on ferromagnetic **FCC Ni**.

> **Research status: v0.3.3.** The default elastic channel now uses a **real Ni scattering-factor-derived, multi-beam Bloch-wave propagator**. The **inelastic Ni L₂,₃ spectra and outgoing channeling are still qualitative/incomplete**; do not interpret this as a quantitatively validated EMCD calculation. See [physical elastic derivation](docs/PHYSICAL_ELASTIC.md) and [physics limitations](docs/PHYSICS.md).

## What works

- FCC Ni (`a=3.524 Å`), structure-factor extinction checks, reciprocal lattice without 2π.
- 200-kV relativistic electron wavevector and Ni [001] `(000),(200),(-200)` systematic-row geometry.
- **Physical multi-beam elastic Ni scattering:** Lobato–Van Dyck atomic electron factors, FCC electron structure factors, occupancy and optional Debye–Waller B, relativistically corrected diffraction coupling, seven-beam [001] baseline (or auto-generated 2D ZOLZ set).
- Hermitian Bloch-wave elastic propagation and depth-averaged coherence (incident wave); optional original surrogate backend for comparison.
- Cubic dipole-MDFF geometry `N(E) q·q′ + i M(E) m·(q×q′)` and energy-resolved diffraction map.
- 2BC Thales-circle A/B apertures and 3BC four-quadrant double-difference chiral grouping. EELS maps and indexed diffraction use the same 000-centered coordinates.
- **Pluggable core-loss line-shapes** (`LEdgeSpectrum` or `TabulatedEdgeSpectrum` using measured/DFT arrays).
- **Pluggable sample-bias-to-moment models**: constant (default) or user-supplied `V,µB` table; fictional demo data clearly marked.
- Lightweight numerical tests and reproducible PNG / NPZ / JSON output.

## Cross-platform setup (Windows, macOS, Linux)

EMCD-Sim is a Python 3.11 research package designed for Windows, macOS and Linux. The portable command `python -m emcd_sim` runs without a Unix shell. Windows PowerShell/Conda/VS Code setup is in [the cross-platform guide](docs/CROSS_PLATFORM.md). GitHub Actions runs tests on all three platforms; these tests do not establish quantitative EMCD accuracy.

## Install and run (macOS/Linux; Windows commands in platform guide)

```bash
cd ~/EM_code/EMCD-Sim
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -q
emcd-ni --output outputs/ni_baseline
```

Outputs now also include `diffraction_pattern.png/.npz` and `diffraction_spots.csv`, with indexed `(h,k,l)` Bragg spots and nominal `[001]` zone-axis labels.

The **default** command uses Ni physical elastic scattering (seven selected beams). Switch options:

```bash
# Physical 7-beam Ni systematic row (default)
emcd-ni --elastic-backend physical --beam-order 3 --output outputs/ni_physical
# Physical [001] ZOLZ 2D set
emcd-ni --zone2d-max-g 1.0 --max-beams 13 --output outputs/ni_zolz
# Optional measured/reference isotropic B; never silently assumed
emcd-ni --b-factor 0.4 --tilt-x-mrad -7 --output outputs/ni_tilted
# Former empirical model remains available for comparison
emcd-ni --elastic-backend surrogate --xi-nm 55 --output outputs/ni_surrogate
# Elastic-only sensitivity to number of diffracted beams
python examples/ni_elastic_convergence.py --max-order 6
```

`--xi-nm` affects only the `surrogate` backend; physical `ξ₂₀₀` is computed from Ni scattering factors. `--voltage-v` is **sample bias**, not microscope accelerating voltage (`--acceleration-kv`). The elastic backend is physical but the EMCD MDFF remains illustrative, and no outgoing channeling has been added.

For an **illustrative** voltage workflow (the CSV values are invented, not measured and must not be interpreted as Ni data):

```bash
emcd-ni --voltage-table examples/ni_voltage_example.csv --voltage-v 2 \
    --output outputs/ni_bias_demo
python examples/compare_voltage.py
```

For real voltage-dependent studies, replace the example CSV with measured or independently simulated magnetic moments before comparing against data. A pure Ni slab under arbitrary applied bias does not imply a predictable change in magnetization.

## Project structure

```text
src/emcd_sim/
  crystal.py       FCC structural model, reciprocal lattice, extinction
  geometry.py      electron optics, qz, reciprocal detectors
  scattering.py    Ni Lobato elastic factors and F_G, Debye-Waller, occupancies
  physical_elastic.py  physical finite-basis Bloch-wave propagation
  elastic.py       legacy surrogate, beam selection and coherence integration
  inelastic.py     cubic dipole MDFF & illustrative Ni edge model
  voltage.py       voltage-to-moment interface and tabulated values
  simulation.py    depth coherence, diffraction map, detector integration
  benchmark.py     FCC Ni [001] reference setup
  cli.py           reproducible command-line benchmark
examples/           illustrative sample-bias control
scripts/            local GitHub publishing workflow
tests/              focused validation tests
docs/               physics assumptions and upgrade roadmap
```

## Indexed diffraction geometries (v0.3.0)

The FCC Ni elastic Bloch-wave solver now supports nominal [001] `zone-axis`, idealized `two-beam`, `near-2bc` and `symmetric-3bc` conditions. Run the quick diffraction-only mode (no illustrative MDFF/EELS):

```bash
emcd-ni --diffraction-condition zone-axis --max-beams 13 --diffraction-only --output outputs/ni_zone_axis
emcd-ni --diffraction-condition near-2bc --diffraction-only --output outputs/ni_near_2bc
emcd-ni --diffraction-condition symmetric-3bc --diffraction-only --output outputs/ni_3bc
emcd-ni --diffraction-condition two-beam --diffraction-only --output outputs/ni_two_beam
```

See [diffraction conditions and limitations](docs/DIFFRACTION_CONDITIONS.md). The Bragg spot widths in PNGs are **visual only**, not CBED disks; systematic-row 2BC/3BC modes omit off-row beams. The default behavior of the old CLI remains unchanged.


## Tilt × thickness scans (v0.3.3)

Use `python -m emcd_sim.scan` or `emcd-scan` to compare a seven-beam systematic row and a finite 2D ZOLZ basis under identical tilts. The command saves 3D `(tilt_x, tilt_y, thickness)` L3 difference/asymmetry arrays, fixed-color-scale reciprocal maps, beam metadata and CSV outputs. See [the scan guide](docs/TILT_THICKNESS_SCAN.md). MDFF remains **illustrative**, not quantitative Ni.

## What is deliberately not claimed

V0.3 **does** use tabulated neutral-Ni scattering factors to derive a real, nonabsorptive independent-atom potential. However it is **not parameter-free** in the ab-initio electronic-structure sense. It does **not** include calibrated Ni EMCD matrix elements, ab-initio ELNES/MDFF, outgoing dynamical propagation, absolute cross sections, quantitative sum rules, experimental validation or voltage-driven magnetic theory. [Details](docs/PHYSICAL_ELASTIC.md).

## GitHub / Mac deployment

The initial project can be unpacked at `~/EM_code/EMCD-Sim`. From inside the folder, run `bash scripts/publish_on_mac.sh` (requires `gh` and GitHub authentication). It creates the **separate public** `dingpengem/EMCD-Sim` repository on GitHub and publishes the local commit. Environments, caches, generated outputs, local editor settings, and secrets are excluded by `.gitignore`.

## Detector geometry correction (v0.3.1)

2BC: A/B at (g/2, +/-g/2), g=|g_200|. Symmetric 3BC: physical apertures RU, RD, LU, LD at (+/-g/2,+/-g/2), with chiral difference (RU+LD)-(RD+LU). The previous v0.3.0 coordinates erroneously re-subtracted incident tilt from 000-centered reciprocal maps. These are geometric, not SNR-optimized apertures. See [diffraction and detector geometry](docs/DIFFRACTION_CONDITIONS.md).
