# v0.3.3 — Tilt and thickness EMCD diagnostic

- Added `python -m emcd_sim.scan` / `emcd-scan`: 3D tilt-x × tilt-y × thickness scans at Ni L3 using the existing entrance-only illustrative MDFF.
- CSV and NPZ numerical results, fixed color scales for comparison heatmaps and magnetic/nonmagnetic reciprocal maps.
- Demonstrated that systematic-row Y tilt insensitivity is a basis-truncation artifact; finite 2D ZOLZ can vary with Y tilt.
- Portable Windows/macOS/Linux CLI, focused symmetry/data-shape regression tests; no changes to Bloch-wave, MDFF or EELS equations.

# v0.3.2 — Windows/macOS/Linux portability

- Added `python -m emcd_sim` as a shell-independent entry point (the original `emcd-ni` remains supported).
- Documented native Windows PowerShell, Conda and VS Code setup; added cross-platform development conventions.
- Added a GitHub Actions matrix for Windows, macOS and Linux (Python 3.11), including an output-path CLI smoke test.
- Added regression testing for paths with spaces and synchronized the package version.
- No changes to Bloch-wave diffraction or the illustrative MDFF.

# v0.3.1 — Chiral aperture geometry fix

- Corrected 000-centered transverse momentum coordinate for tilted 2BC/3BC EMCD maps (removed erroneous extra incident-tilt subtraction).
- Exact transverse Thales-circle detector centers for 2BC/near-2BC; four physical 3BC apertures and symmetry-correct double difference.
- Added detector overlays and standalone `aperture_geometry.png`, per-aperture spectra, group metadata and focused regression tests.
- Still illustrative: truncated systematic rows, simplified MDFF, no outgoing channeling or SNR optimization.

# Changelog

## 0.2.0 — Ni physical elastic Bloch-wave solver

- Added a neutral-Ni (Z=28) Lobato–Van Dyck 2014 elastic electron scattering-factor implementation.
- Added general independent-atom periodic crystal Fourier factors with optional per-site Debye–Waller B and occupancy, and a physical Fourier-potential adapter.
- Added finite-basis relativistic Bloch-wave elastic propagation with derived beam couplings and ξ200 (no fitted extinction distance in this backend).
- Added systematic-row and Friedel-paired in-plane ZOLZ beam generation; seven-beam Ni systematic row is the default physical reference.
- Switched `emcd-ni` CLI default to `--elastic-backend physical`. Original `--elastic-backend surrogate` is retained for comparison, with `--xi-nm` applying only to the surrogate.
- Added plots and NPZ for each elastic beam's thickness-dependent intensity and a row-order convergence diagnostic.
- Added five physical tests (12 tests total) for form factor, FCC extinctions, DW, Hermiticity/unitarity, ξ200 and exact two-beam Bragg Pendellösung.
- Documented units, modeling assumptions, citations, and remaining outgoing-channeling/MDFF limitations.

This version **does not** validate quantitative EMCD: magnetic L-edge MDFF remains illustrative and the electron does not undergo outgoing channeling after its core-loss event.

## 0.1.0 — Initial proof of concept

- Phenomenological entrance-channeling elastic coupling; illustrative magnetic core-loss MDFF; Ni 3-beam virtual-aperture workflow; bias-to-moment data interface.

## 0.3.0 — Indexed diffraction geometry and patterns

- Added `--diffraction-condition {systematic-row,zone-axis,two-beam,near-2bc,symmetric-3bc}`.
- Added `--diffraction-only` for elastic diffraction without costly illustrative MDFF/EELS integration.
- Added reproducible indexed reciprocal-space diffraction PNG, NPZ and CSV with `(h,k,l)`, nominal `[001]` zone axis, tilt and signed excitation errors.
- Preserved the v0.2 default systematic row, physical Ni elastic solver and existing EELS API.
- The 2BC/3BC presets explicitly state their finite-basis/systematic-row assumptions; diffraction spot broadening is graphical only.
- Added focused tests of s_g, Bragg condition, ±200 symmetry, ZOLZ indexing and elastic conservation.
