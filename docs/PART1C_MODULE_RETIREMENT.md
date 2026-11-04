# Part 1C module retirement and compatibility boundary

Baseline: accepted main 133c3da6; scientific source 98570c62.

| Module | Disposition | Concrete reason |
| --- | --- | --- |
| ni_local_mdff.py | Removed | Maintained callers/tests migrated; supported console entry retargeted to historical_ni.main |
| gui/legacy_ni_provider.py | Removed | Its compatibility configuration, direct-evaluation provider and CLI now have one documented home in historical_ni.py |
| historical_ni.py | Explicit historical-input/provider adapter | Ni defaults and metadata must remain separate from explicit generalized material parameters; direct evaluation cannot be replaced by imported-grid interpolation |
| atomic_dipole.py | Shared numerical implementation | One 2p-to-3d angular/radial implementation, with historical aliases in the explicit historical-input adapter |
| atomic_ionization.py | Shared transition generator | One event enumeration; explicit strict/historical_drop amplitude policy |
| mdff_orientation.py | Shared axis-frame implementation | Declared XMCD no longer imports a generic rotation through a Ni compatibility GUI wrapper |
| gui/emcd_forward.py | Retained common settings/resource/result/export API | Existing project and public callers, plus admission/cancellation hooks; four historical functions are now aliases rather than wrapper implementations |
| gui/generalized_forward.py | Retained declared settings/source validation and provider API | Used by project restore, GUI source controls and external callers; calculate is an alias, not a second orchestrator |
| gui/forward_pipeline.py | Single production pipeline | Common provider preparation and site interface; shared BW/MS Single/Double contractions |
| benchmark.py, study_geometry.py, multislice_reference.py | Retained scientific benchmark/reference utilities | Independent validation and historical study callers; not obsolete copies to remove |
| scattering.py | Retained original Lobato compatibility provider | Protected historical Ni elastic results; elastic providers are outside this refactor |
| ni_017_geometry.py, ni_117_geometry.py | Already absent from production baseline | Independent archived geometry tests remain outside production; no new deletion claim |

## Dependency verification

Searched source, scripts, tests, pyproject entry points and packaging for direct imports,
importlib/import_module/__import__ usage and historical module names. There are no
production imports of ni_local_mdff after migration: GUI configuration/project loading
uses historical_ni, and numerical providers use atomic_dipole/atomic_ionization. The documented
CLI entry point now targets historical_ni.main directly. Setuptools package
module discovery includes the new modules; PyInstaller follows the static imports from
GUI/provider dispatch. Extracted-EXE acceptance must verify actual inclusion.

Removal does not mean hiding an implementation behind a module-name alias in sys.modules.
No duplicate numerical loop remains for historical naming. The obsolete ProjectedNiFFT alias was removed; maintained callers use ProjectedFFT.
Archived reference modules keep their original API names, with test-only bindings.

## Validation strategy

Immutable Part 1B references check event ordering, complex amplitudes, weights, source
strings, both magnetization signs, normal and tiny radial values, original requested-energy
grids and directly evaluated tensors. Archived solver tests adapt only the newly explicit
historical-site argument, first asserting those positions exactly match the old input.
Zero-signal injection targets the provider interface; scientific expected arrays are not
changed. A structural test rejects reintroduction of the retired module or a production import into it.

All original scientific limitations, numerical defaults, source checksums, historical
project semantics, corrected Born convention and release boundaries remain unchanged.


## Intentionally discontinued API

`import emcd_sim.ni_local_mdff` and `python -m emcd_sim.ni_local_mdff` are discontinued.
Use historical_ni for historical inputs/CLI and atomic_dipole/atomic_ionization for
shared algebra and declared models. The documented `emcd-ni-local-mdff` console command
remains supported with the same arguments and scientific output; its entry point was
retargeted. Existing saved projects use JSON parameters, not Python pickle/module paths,
so project compatibility does not require retaining the obsolete module.

Earlier acceptance/design documents and archived research verification scripts describe
their pinned historical revisions. Their old source inventories are historical evidence,
not current API promises; original snapshots and scientific reference inputs remain intact.


## Complete Ni/nickel/FCC symbol audit under src

| Symbol | Final disposition and evidence |
| --- | --- |
| ProjectedNiFFT | Removed alias; ProjectedFFT is the sole production class/API. Maintained scripts/tests migrated; archived modules retain their own original names. |
| fcc_site_phase_matrix | Removed misleading name. Shared arithmetic is single_site_phase_matrix; the standalone Ni eligibility wrapper is historical_ni_site_phase_matrix. This preserves its Ni-only guard, not a new material restriction on shared contraction. |
| ni_2p_to_3d_dipole | Removed alias; shared API is atomic_dipole.dipole_2p_to_3d. No second angular implementation. |
| historical_ni module, NiLocalConfig, ni_local_transitions, _ni_transition_source | Retained: original Ni input defaults, compatibility mapping, event/source labels and provenance. Enumeration delegates to the generalized generator. |
| HistoricalNiProvider, HistoricalNiSites, historical_ni_site_phase_matrix | Retained: explicit historical eligibility, raw site coordinates, direct energy evaluation and sampling. None duplicates the shared contraction/phase arithmetic. |
| benchmark.nickel_apertures, nickel_physical_benchmark | Retained: actual Ni benchmark geometry/data, not generic propagation APIs. |
| crystal.fcc_nickel, Structure.nickel | Retained: factories construct an actual conventional FCC Ni crystal. |
| scattering.nickel_lobato_factor, _NI_A, _NI_B | Retained unchanged: actual Ni Lobato coefficients and compatibility provider. |
| multislice_reference._projected_ni_potential, fft_multislice_ni | Retained unchanged: independent Ni IAM/reference implementation, used to validate production; not an obsolete generalized production solver. |

The audit includes module names, function/class definitions, imports with aliases and
module-level assignments; generic propagation uses ProjectedFFT and explicit site
interfaces. Local variables such as ni/no in Double Channeling count incoming/outgoing
beams; they are not nickel API names. Genuine Ni source strings, datasets, figure labels,
benchmark outputs and saved project fields were not renamed.

The old ProjectedNiFFT, fcc_site_phase_matrix and ni_2p_to_3d_dipole import aliases are
intentionally discontinued. Archived reference source/fixtures remain byte-for-byte intact;
only import bindings in maintained reference loaders are adapted, preserving original
numerical statements and exact-array assertions. Original physics-source hash guards
reconstruct only the explicitly reviewed identifier/alias moves and phase-helper extraction.
