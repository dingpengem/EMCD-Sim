# CIF-aware atomic MDFF parameter editor

Development feature, isolated from the accepted BCC-Fe Windows candidate. The application version is unchanged. No new atomic physics, propagation or contraction implementation is introduced.

## Model applicability

The common BW/MS Single/Double framework remains element-independent when valid sources and sites exist. This editor prepares only the existing independent-electron, electric-dipole **Sc-Zn 2p-to-3d L2,3** atomic model. XMCD-constrained and imported complex tensors retain their own separate applicability. The periodic-table selector is not an all-element atomic-generator claim.

The editor has nine collapsible sections: element/transition, core references, cubic field/exchange, five orbital holes, radial dipole, rigid frame, explicit energy grid/broadening, provenance/validity, and validation/import/export/preview. Expanded definitions and tooltips are attached to the controls.

## Manual workflow

1. Import a CIF. Elements, atomic numbers, ASE site indices/counts and occupancy annotations come from the actual imported structure. The CIF does not establish oxidation state, electronic occupations or magnetic order.
2. Select preparation checkboxes and one active element. Multiple preparation selections are not multiple execution groups. A multi-element/partial-occupancy/inequivalent-site crystal remains subject to the existing solver eligibility restrictions.
3. Supported elements receive traceable elemental L3/L2 references, an editable 201-point grid extending 10 eV on either side, identity coordinate frame, fixed local +z axis and generic Gaussian sigma=1 eV. The grid and sigma are numerical starting choices, not measured resolution or convergence certification; identity is a coordinate choice, not inferred magnetism. Cubic/exchange splittings, all ten holes, radial integral/source and physical provenance remain explicit required inputs. No material electronic defaults are supplied. Resetting numerical/frame choices requires confirmation.
4. Click **Preview MDFF Tensor Spectrum** to validate and generate from the editable fields, or explicitly validate the complete atomic source. A complete strict schema1 atomic_2p3d document is stored visibly under the writable workspace's atomic_inputs directory, named by SHA256. The existing provider generates/validates explicit magnetic tensors. Then explicitly acknowledge source/frame/relative-unit assumptions for EELS/EMCD. Automatic Ni numerical presets remain unavailable for Fe.
5. Inspect the actual declared grid through the interactive tensor views, or export parameter JSON through Save As. Import saved inputs into the editable controls. Changing input, active element, source or CIF invalidates acknowledgement and the prior current tensor. Element-specific drafts remain separate; returning to a draft does not restore validation.

Use the explicit **Load Synthetic Fe Demonstration** action only as a software example. Its original710/723eV energies and electronic parameters are not an elemental edge table, material defaults, or quantitative Fe spectroscopy. Synthetic/source/validity notices remain visible next to generation controls.

## Fields and scientific definitions

### L3 reference energy

L3 reference energy (E_L3)
Units: eV. Allowed: 0 < E_L3 < E_L2.
2p3/2 reference excitation, not necessarily a fitted peak maximum. The generator adds cubic and exchange shifts.
Frame: local real cubic orbital/spin frame unless specified; energies are scalar.
Provenance: explicitly cite parameter/radial source and assumptions; editable does not mean calibrated.

### L2 reference energy

L2 reference energy (E_L2)
Units: eV. Allowed: E_L2 > E_L3.
2p1/2 reference excitation. Delta_SO = E_L2 - E_L3 is derived, not another fitted input.
Frame: local real cubic orbital/spin frame unless specified; energies are scalar.
Provenance: explicitly cite parameter/radial source and assumptions; editable does not mean calibrated.

### Cubic splitting

Cubic splitting (10Dq)
Units: eV. Allowed: finite, >= 0.
eg shift +0.6*10Dq; t2g shift -0.4*10Dq about the weighted orbital centroid. Cubic symmetry only.
Frame: local real cubic orbital/spin frame unless specified; energies are scalar.
Provenance: explicitly cite parameter/radial source and assumptions; editable does not mean calibrated.

### Effective exchange splitting

Effective exchange splitting (Delta_ex)
Units: eV. Allowed: finite, >= 0.
Shift = -spin_sign*magnetization_sign*Delta_ex/2. Not total exchange energy, a magnetic moment, or a many-body multiplet Hamiltonian.
Frame: local real cubic orbital/spin frame unless specified; energies are scalar.
Provenance: explicitly cite parameter/radial source and assumptions; editable does not mean calibrated.

### Radial dipole integral

Radial dipole integral (D)
Units: Angstrom. Allowed: finite, > 0.
D = integral R_2p(r) R_3d(r) r^3 dr for full radial functions normalized with r^2 dr. Multiplies amplitudes; intensity scales quadratically. Declare calculation, effective fit, or synthetic origin.
Frame: local real cubic orbital/spin frame unless specified; energies are scalar.
Provenance: explicitly cite parameter/radial source and assumptions; editable does not mean calibrated.

### Orbital/spin holes

Orbital/spin holes (h(m,spin))
Units: dimensionless. Allowed: [0,1], not all zero.
Unoccupied final-state weights; electron occupation = 1-h within this independent-electron model. No normalization or magnetic-moment inference. Rows follow the generator exactly.
Frame: local real cubic orbital/spin frame unless specified; energies are scalar.
Provenance: explicitly cite parameter/radial source and assumptions; editable does not mean calibrated.

### Frame to crystal

Frame to crystal (R)
Units: dimensionless. Allowed: R.T R=I, det R=+1 (tolerance 1e-12).
Columns are local axes in crystal Cartesian coordinates. Local M=(0,0,1); crystal M=R@(0,0,1). Rotate the entire cubic orbital/spin model; no independent noncollinear spin rotation or silent orthogonalization.
Frame: local real cubic orbital/spin frame unless specified; energies are scalar.
Provenance: explicitly cite parameter/radial source and assumptions; editable does not mean calibrated.

### Minimum energy loss

Minimum energy loss (E_min)
Units: eV. Allowed: 0 < E_min < E_max.
First actual tensor sample, not an inferred threshold. Must cover the declared edges together with E_max. No automatic extension/extrapolation.
Frame: local real cubic orbital/spin frame unless specified; energies are scalar.
Provenance: explicitly cite parameter/radial source and assumptions; editable does not mean calibrated.

### Maximum energy loss

Maximum energy loss (E_max)
Units: eV. Allowed: E_max > E_min.
Last actual tensor sample. Range and sampling are numerical choices, not physical convergence certification.
Frame: local real cubic orbital/spin frame unless specified; energies are scalar.
Provenance: explicitly cite parameter/radial source and assumptions; editable does not mean calibrated.

### Energy sample count

Energy sample count (N_E)
Units: samples. Allowed: integer 2..4096.
Inclusive uniform linspace for a newly entered grid. Imported explicit grids are preserved exactly until the grid controls are edited. GUI allocation bound, not generator accuracy.
Frame: local real cubic orbital/spin frame unless specified; energies are scalar.
Provenance: explicitly cite parameter/radial source and assumptions; editable does not mean calibrated.

### Gaussian standard deviation

Gaussian standard deviation (sigma)
Units: eV. Allowed: finite, > 0.
FWHM = 2*sqrt(2*ln(2))*sigma. This is sigma, not FWHM; the accepted Gaussian broadening implementation is reused.
Frame: local real cubic orbital/spin frame unless specified; energies are scalar.
Provenance: explicitly cite parameter/radial source and assumptions; editable does not mean calibrated.

### Parameter source

Parameter source (source)
Units: text/citation. Allowed: nonempty.
Give the origin of every material parameter, including manually overridden edge energies. CIF composition does not establish oxidation, magnetic order, or these electronic constants.
Frame: local real cubic orbital/spin frame unless specified; energies are scalar.
Provenance: explicitly cite parameter/radial source and assumptions; editable does not mean calibrated.

### Radial integral source

Radial integral source (source_D)
Units: text/citation. Allowed: nonempty.
Identify a radial calculation, effective fit, or synthetic choice. No Ni or element-dependent value is automatically copied.
Frame: local real cubic orbital/spin frame unless specified; energies are scalar.
Provenance: explicitly cite parameter/radial source and assumptions; editable does not mean calibrated.

### Material/model assumptions

Material/model assumptions (assumptions)
Units: text. Allowed: nonempty.
Declare physical interpretation and how the cubic independent-electron model approximates this material. The CIF alone is insufficient.
Frame: local real cubic orbital/spin frame unless specified; energies are scalar.
Provenance: explicitly cite parameter/radial source and assumptions; editable does not mean calibrated.

### Physical validity and limits

Physical validity and limits (validity)
Units: text. Allowed: nonempty.
State missing physics and limits. Mathematical Hermiticity/PSD does not establish material-specific or experimental accuracy.
Frame: local real cubic orbital/spin frame unless specified; energies are scalar.
Provenance: explicitly cite parameter/radial source and assumptions; editable does not mean calibrated.

### Scientific status

Scientific status (status)
Units: category. Allowed: synthetic or physical_source_unvalidated.
No quantitatively validated choice is provided. Synthetic inputs are software demonstrations only.
Frame: local real cubic orbital/spin frame unless specified; energies are scalar.
Provenance: explicitly cite parameter/radial source and assumptions; editable does not mean calibrated.

### Active preparation element

Active preparation element (Z, symbol)
Units: periodic-table identity. Allowed: Z=1..118; generator Sc-Zn only.
Presence in a CIF, atomic-model applicability, and executable single-element/equivalent-site eligibility are different questions. Multiple preparation selections are never summed.
Frame: local real cubic orbital/spin frame unless specified; energies are scalar.
Provenance: explicitly cite parameter/radial source and assumptions; editable does not mean calibrated.

### Core-loss transition

Core-loss transition (2p -> 3d)
Units: edge family. Allowed: L2,3 only for this generator.
XMCD-constrained and imported tensor providers remain separate pathways with their own supported edge declarations.
Frame: local real cubic orbital/spin frame unless specified; energies are scalar.
Provenance: explicitly cite parameter/radial source and assumptions; editable does not mean calibrated.

### Intensity normalization

Intensity normalization (T per atom)
Units: Angstrom^2/eV, relative. Allowed: per_atom_relative (fixed).
No absolute cross-section calibration. Independently prepared tensors for different elements are not certified absolute comparisons.
Frame: local real cubic orbital/spin frame unless specified; energies are scalar.
Provenance: explicitly cite parameter/radial source and assumptions; editable does not mean calibrated.

## Offline elemental edge references and redistribution

The library is a20-row L3/L2 subset for Sc-Zn from **xraylib4.2.1**, upstream commit `f7a4a5cd8eb6d48bb5f496553ac479c2dd42674f`, not Gatan data. [Original table](https://github.com/tschoonj/xraylib/blob/f7a4a5cd8eb6d48bb5f496553ac479c2dd42674f/data/edges.dat), [project-wide license](https://github.com/tschoonj/xraylib/blob/f7a4a5cd8eb6d48bb5f496553ac479c2dd42674f/license_all.txt), [data documentation](https://github.com/tschoonj/xraylib/blob/f7a4a5cd8eb6d48bb5f496553ac479c2dd42674f/data/README), [API definition](https://github.com/tschoonj/xraylib/wiki/The-xraylib-API-list-of-all-functions#absorption-edge-energies).

The upstream project-wide BSD-3-Clause notice expressly permits source/binary redistribution. It is retained verbatim with the subset; no data-specific restriction was identified in the tagged data documentation. Permission is based on that license, not scientific publication or Python translation. The subset preserves raw `edges.dat` eV values and documents the exact transformation and source hashes. xraylib's API returns keV, but these raw table entries are already in eV: **Fe L3=708.1eV,L2=721.1eV**. No API conversion is applied to raw rows. No uncertainty is invented.

The definition is elemental absorption-edge reference energy, not a fitted EELS peak or chemical-environment prediction. Bonding/oxidation/crystal field/exchange can alter observed structure. No chemical shift is inferred from the CIF. Both the subset and provenance are checksum-pinned; missing or corrupt data request explicit user input and never supply fabricated numbers. Runtime is offline, with no xraylib package/network dependency. Package-data and PyInstaller recipes include the edge table, provenance and license.

Each energy is tracked as tabulated,manual,imported or unverified imported override. Imported claims that no longer match the pinned row cannot retain the trusted-tabulated label. Replacement of existing edited references or an existing grid requires confirmation. Sources and origin metadata travel in the existing free-text `parameters.source` field as an `EMCD_EDITOR_REFERENCE_V1` annotation; the top-level strict schema remains unchanged. This is source metadata, not an extension of the tensor conventions.

## Persistence and project compatibility

Managed JSON files are immutable, content-addressed and outside packaged resources. Existing names with different bytes are rejected. Export cannot overwrite any managed atomic source, even one previously validated. Replacing a separate user file requires explicit confirmation. Empty paths,directories,missing inputs and unwritable workspaces give diagnostics instead of attempting to write `.` or `_internal`.

New editor-managed atomic project saves include a short `atomic_input.json` attachment (Windows path-length safe), whose bytes must match the config's source SHA256 and the project file manifest. Load selects that verified project-local copy; it does not reinterpret tensors or silently replace a source identity. Source-backed atomic files selected through the old external-JSON controls retain their historical source requirements. Old project schemas and historical Ni projects are not migrated. Conflicting user attachment names require Save As and are not overwritten.

Historical Ni controls remain intact in the collapsed **Legacy Ni Parameters - Historical Compatibility Only** section. Default historical Ni routing is unchanged. Editing the generalized Ni panel selects a source-backed workflow; unvalidated edits cannot fall back silently to Ni defaults. Non-Ni materials never use historical Ni electronic controls.

## Scope and limitations

Local M=(0,0,1) is fixed. Only proper rigid orbital/spin-frame rotations are supported; there is no arbitrary noncollinear magnetism or general crystal-field Hamiltonian. All holes are independent [0,1] final-state weights; no averaging/normalization is applied. The basic preview shows ReTr(T)/3, ReTzz, ImTxy and edge references on the declared grid; the additional modes inspect explicit reversal, even/odd responses and all nine complex components. These are relative per-atom tensor components,not final A/B detector spectra; ImTxy alone does not determine the measured EMCD sign.

The GUI bounds explicit grids to2..4096 samples and input JSON to8MiB before generation. These are allocation guards,not convergence claims or changes to standalone physics. Imported nonuniform grids remain exact until grid controls are explicitly edited. Grid suggestions are explicit numerical starting configurations; no range is silently extended.

No quantitative material validation,absolute inter-element cross-section calibration,multi-element site-resolved MDFF,AFM/SDW or new spectroscopy is supplied. Existing mathematical Hermiticity/PSD and checksum verification are necessary but do not establish physical accuracy. No release candidate, published EXE or historical reference array is changed by this feature.

## Validation and review boundaries

Focused GUI tests and native Windows **source-GUI** acceptance exercise the real controls and existing workers. They must be distinguished from packaged-EXE acceptance: no EXE is rebuilt in this task. Full Windows results,source hashes,exact comparisons and the proposed diff are recorded under this feature worktree's `outputs/editor-validation`.

Historical source manifests/archives and identity tests are not modified to accept this unreviewed feature. GUI/project-I/O changes can therefore produce expected current-source identity failures until a separate concrete diff/scope review. Such failures remain failures,not scientific passes or waived assertions. The accepted BCC GUI app.py hash itself remains unchanged.

## Interactive tensor views and parameter provenance

Each physical control has a plain-language description and an information button with its definition, equations, effects and limitations. The information dialog allows an optional parameter-specific citation. Origins distinguish CIF identity, tabulated energies, user values, imported physical or synthetic sources, explicit synthetic demonstrations, coordinate choices and numerical starting choices. Origins are recorded with the strict parameter source; they do not independently certify imported claims.

The preview reuses existing atomic generation and finite/Hermitian/PSD validation for both physical magnetic states. Its four modes show basic components, explicit +M/-M reversal, even/odd combinations and all nine complex components with real/imaginary selection. Pan/zoom and image export use the standard Matplotlib toolbar. Curves retain the declared local frame, per-atom relative Angstrom^2/eV units, source identity and physical-validity label.

For generated dipoles d and nonnegative hole weights h, T_ab(E)=sum h*d_a*conjugate(d_b)*G_sigma(E-E_n), using the existing normalized Gaussian. Even=(T_plus+T_minus)/2 and odd=(T_plus-T_minus)/2 use the separately generated magnetic states. The odd response is signed and need not be PSD. Detector contraction remains Re Tr(RT)=Re sum R_ab*T_ba, without additional conjugation. The construction panel explains each step. Tensor curves are not detector spectra or absolute cross sections.

Editing parameters, changing CIF/element or changing external-source identity invalidates acknowledgement and marks an open preview STALE. Generation happens only on explicit Preview/Validate actions. A newly selected external JSON must be imported or validated before old editor fields can generate another source. A successful preview does not authorize EELS/EMCD, certify equivalent sites or establish numerical convergence.

## Corrected source restoration and edge-origin reconciliation

Loader-verified project attachments take precedence over browser source locations, including empty, missing and wrong-content locations after project relocation. The GUI rechecks the loader source identity before installing it; a mismatch fails opening rather than substituting a scientific input. Historical projects without portable attachments retain their browser/external-source behavior.

Imported L3/L2 table claims must match the pinned element, edge, exact energy and complete reference identity. Both edge and parameter origins are reconciled before restoring editable fields. An unverifiable claim keeps its energy but receives an imported-override label in the inline text, tooltip and detail panel, and in subsequent JSON exports. A matching numerical value alone does not confer trusted-table provenance. Manual overrides remain user-entered.
