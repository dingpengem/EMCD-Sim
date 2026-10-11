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
