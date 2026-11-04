# Part 1C migration plan

Baseline: 133c3da6e69d633b0e1ea61a4de8005820885bbb; scientific source 98570c62.

1. Move unchanged 2p-to-3d angular/radial helpers to atomic_dipole; retain Ni public aliases.
2. Replace the reachable duplicate Ni transition loop with an explicit historical_drop policy
   in transitions_for_material; retain strict generalized validation and original Ni metadata.
3. Share Single phase arithmetic with historical eligibility wrappers intact. Keep Double phases unchanged.
4. Prepare every model through one provider interface. HistoricalNiProvider preserves direct requested-energy
   evaluation, legacy sampling, rotation, reversal validation and source identity; no interpolation migration.
5. Use one documented forward entry, retaining API wrappers required by existing projects/callers.
6. Check each change against immutable Git references, then full Windows source and extracted EXE acceptance.

Protected: numerical kernels, defaults, datasets, archived fixtures, Part 1B candidate. No publication.
