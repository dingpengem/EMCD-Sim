# Part 1C migration plan

Baseline: 133c3da6e69d633b0e1ea61a4de8005820885bbb; scientific source 98570c62.

1. Move unchanged 2p-to-3d angular/radial helpers to atomic_dipole; retain Ni public aliases.
2. Replace the reachable duplicate Ni transition loop with an explicit historical_drop policy
   in transitions_for_material; retain strict generalized validation and original Ni metadata.
3. Share Single phase arithmetic with historical eligibility wrappers intact. Keep Double phases unchanged.
4. Prepare every model through one provider interface. HistoricalNiProvider in historical_ni preserves direct requested-energy
   evaluation, legacy sampling, rotation, reversal validation and source identity; no interpolation migration.
5. Use one documented forward entry, retaining API wrappers required by existing projects/callers.
6. Check each change against immutable Git references, then full Windows source and extracted EXE acceptance.

Protected: numerical kernels, defaults, datasets, archived fixtures, Part 1B candidate. No publication.

## Implementation and call graphs

Before: StageB -> generalized_forward.calculate -> emcd_forward.calculate ->
_calculate -> forward_pipeline.calculate_prepared -> legacy/declared tensor dispatch ->
shared propagation/channeling. Historical tiny-radial Ni used its own enumeration loop.

After: StageB / generalized_forward / forward_pipeline expose the SAME calculate callable.
The resource admission envelope and retained _calculate compatibility hook invoke one
calculate_prepared implementation. prepare_provider selects HistoricalNiProvider or
DeclaredMDFFProvider; both expose material_reason, energy_grid, tensors, sites,
simulation_magnetization and revalidate_source. Both use identical BW/MS and Single/Double
response kernels. XMCD, atomic and imported source models remain physically distinct.

HistoricalNiProvider keeps the original material/grid/tensor functions verbatim. Its
HistoricalNiSites preserves unwrapped positions and the original per-atom mean; declared
IonizationSites retains strict equivalence/context checks. Both Single paths call
single_site_phase_matrix. Double equivalent_site_phases is unchanged.

Atomic angular/radial algebra now lives in atomic_dipole. historical_ni retains NiLocalConfig,
public aliases, metadata mapping and CLI support. transitions_for_material is the only
transition event loop; strict rejects tiny nonzero amplitudes, historical_drop omits them
exactly as the historical tiny-radial implementation did. No interpolation replaces direct
historical evaluation. Broadening, phases and event order are unchanged.

Compatibility retained: ni_2p_to_3d_dipole alias; fcc_site_phase_matrix eligibility wrapper;
ProjectedNiFFT class alias; old forward function imports; _calculate admission hook;
historical L2/L3 sampling/validation; Ni project/config interpretation. Deprecated names
remain only where public compatibility or independent references require them.

## Review limits

This is a refactor, not new physics. Element-independent propagation still requires a
validated single-element crystal, supported equivalent sites and valid tensor. Atomic
ionization remains the implemented cubic 2p-to-3d model. No multi-element/site-resolved,
AFM/SDW, multiplet or DFT capability is added. Synthetic Fe/O tests are mathematical
software demonstrations. Approximately 1.6% detector-refinement sensitivity and absence
of broad quantitative/experimental validation remain. Native acceptance is same-host,
not clean-PC certification. Historical manifests and scientific arrays are not rewritten;
Part 1C has an additive source-identity manifest and immutable-source equivalence tests.


## Additional module-retirement requirement

Production callers now bypass ni_local_mdff entirely, and that obsolete module is removed;
all input compatibility lives in historical_ni. The intermediate gui/legacy_ni_provider
module was removed, generic axis rotation moved to mdff_orientation, and four old GUI
wrappers became aliases. See PART1C_MODULE_RETIREMENT.md for dependency evidence and
retained modules. No accepted reference or previously completed test output was removed.
