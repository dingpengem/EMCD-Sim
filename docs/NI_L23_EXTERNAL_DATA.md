# FCC metallic Ni L2,3: external transition-data sourcing (v0.4.4)

## Outcome of the literature/open-data audit (October 2026)

**No directly downloadable, phase-correct, core-SOC-resolved, complex Cartesian 2p-to-unoccupied-state transition amplitude dataset for ferromagnetic FCC Ni was verified during this audit.** Accordingly, v0.4.4 **does not replace** the default Gaussian model or the illustrative non-DFT Ni-local backend with any claimed first-principles Ni data. The `ni-metal-external` input mode remains deliberately *data-gated*. No invented matrix elements, fitted `magnetic_fraction`, or digitized spectrum are passed off as transition data.

This distinction is scientific, not cosmetic: a scalar EELS/XAS or XMCD spectrum does not reconstruct all off-diagonal complex phase relationships of the full momentum-dependent MDFF. A polarization-resolved absorption tensor could provide a **dipole-level** tensor after careful mapping, provided *all necessary components and calibration* are available; this is still not a table of microscopic transitions or full finite-q MDFF.

## Relevant sources and their actual limits

| Source | Useful verified information | Why it cannot be substituted for FCC-Ni complex transitions |
|---|---|---|
| Rusz, Rubino & Schattschneider, PRB 75, 214425 (2007), DOI:10.1103/PhysRevB.75.214425 | First-principles EMCD theory for 3d ferromagnets including Ni | Published theory/results, not a verified downloadable transition-amplitude table |
| Elk `elnes.f90` / `genexpmat`, https://elk.sourceforge.io/doxygen/html/elnes_8f90_source.html | Calculates electronic excitation matrix elements | Native ELNES output normally contains intensity; complex Ni 2p core-to-band amplitudes require a modified, tested export and actual Ni calculation |
| WIEN2k core/momentum matrix exporter (user discussion), https://www.mail-archive.com/wien@zeus.theochem.tuwien.ac.at/msg12128.html | Shows complex x/y/z components can be output | Example data are not a verified Ni-metal L2,3 dataset; length/velocity-gauge conventions and normalization need checking |
| Quanty NiO L2,3 conductivity-tensor tutorial, https://quanty.org/documentation/tutorials/nio_crystal_field/xas_l23_as_conductivity_tensor | Energy-dependent 3x3 polarized transition response for a NiO crystal-field model | **NiO is not ferromagnetic metallic FCC Ni**; one cannot relabel this data |
| Materials Project site-resolved L-edge XAS database, https://doi.org/10.1038/s41597-021-00936-5 | Downloadable computed L-edge XAS for some compounds, useful as spectral reference | Site XAS arrays are **real absorption intensities**, not magnetic complex MDFF amplitudes; dataset inclusion of the desired metal/sample must be confirmed |
| Gatan/EELS Atlas Ni page, https://www.eels.info/Resources/EELS-Atlas/Nickel | Reference EELS energies and downloaded spectra | Some linked specimen descriptions are **NiO**, and no complex magnetic transition phases are provided |
| Nickel-related XMCD open datasets (Zenodo, e.g. DOI:10.5281/zenodo.4831735) | Experimentally measured dichroic spectra useful for future *matching material* validation | Not guaranteed elemental FCC Ni and not transition amplitudes |

**DO NOT** silently relabel NiO, Ni(OH)2, NiFe2O4, ionic Ni(II), or doped compounds as ferromagnetic FCC Ni. Published Ni L2,3 peak energies are useful benchmarks, not proof of correct magnetic MDFF.

## Strict external data mode

A real external DFT/many-body exporter should produce a `TransitionDataset` NPZ (complex `d=<i|r|f>` in Angstroms, per-transition energies, final-state occupation and k-point weights, `L3`/`L2` IDs, site labels) plus an explicit JSON sidecar. The new audit checks **file structure and claimed provenance**; it cannot establish whether the vendor's DFT calculation is truly converged or whether its SOC, gauges, core level or absolute cross sections are physically correct.

Sidecar keys (all mandatory):

```json
{
  "material": "Ni",
  "phase": "fcc_metal",
  "absorber": "Ni",
  "edges": ["L3", "L2"],
  "method": "spin-polarized SOC electronic-structure method (actual name)",
  "code": "actual electronic-structure code",
  "code_version": "actual version",
  "core_spin_orbit": true,
  "spin_polarized": true,
  "data_type": "complex_length_gauge_dipoles",
  "dipole_convention": "<i|r|f>",
  "dipole_units": "angstrom",
  "complex_phase_preserved": true,
  "weights_definition": "actual k-weight and occupancy convention",
  "core_state_definition": "actual Ni 2p_j,mj states and normalization",
  "k_point_definition": "actual Brillouin zone mesh and weights",
  "reference_url": "actual data DOI/URL or repository",
  "citation": "actual author, year, paper/DOI",
  "input_description": "actual material geometry, magnetization, XC/SOC settings, core-hole/broadening, empty-band cutoffs"
}
```

Run on Windows/macOS/Linux:

```bash
python -m emcd_sim.ni_data_audit --transitions data/real_fcc_ni_transitions.npz --provenance data/real_fcc_ni_provenance.json
python -m emcd_sim --mdff-model ni-metal-external --mdff-transitions data/real_fcc_ni_transitions.npz --mdff-provenance data/real_fcc_ni_provenance.json --diffraction-condition near-2bc --output outputs/ni_external_mdff
```

An audit **pass is NOT a physics certificate**. Runtime output records `mdff_quantitative_Ni=false`, `calibrated=false`, and the metadata status `format_and_declared_provenance_passed_NOT_physics_validated`. Such results cannot be published as ab-initio quantitative EMCD until independently validated.

Legacy `--mdff-model transitions` remains a general research input accepting unverified transitions; `--mdff-model ni-local` is the explicitly non-DFT atomic demo; `--mdff-model gaussian` remains an illustrative model.

## Concrete next step to actually replace the default Ni model

1. Run a spin-polarized SOC **FCC Ni** all-electron calculation (e.g. Elk/WIEN2k) with *validated Ni 2p core-state spinors* and enough unoccupied bands.
2. Add/export complex x/y/z **2p-to-band** dipole amplitudes with appropriate k-point/site weights and phase conventions. Store wavefunction normalization, absolute scales and SOC/core-state IDs. Do not use a simple XAS intensity export.
3. Convert with `emcd_sim.transition_csv` or emit the NPZ schema directly; run the audit above.
4. Independently compare resulting nonmagnetic and magnetic Ni L2,3 tensor spectra with suitable **metallic Ni** spectroscopy, check chirality reversal, sum rules where applicable, k-point/empty-band/broadening convergence and site phases.
5. Only then make the real physical Ni tensor the **default** and retire `magnetic_fraction=0.12` from quantitative workflows.

**Cross-platform:** the DFT stage may run on Linux/HPC; the transition NPZ and MDFF calculation are portable to Windows/macOS/Linux without linking the DFT executable.
