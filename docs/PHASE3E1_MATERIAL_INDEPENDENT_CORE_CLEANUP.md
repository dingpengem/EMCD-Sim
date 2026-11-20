# Phase 3E-1: material-independent core cleanup and historical Ni isolation

## A. Scope and decision

Starting HEAD: `2c78b40d78e65787876a58c32f11e6178e182e46`, clean on
`refactor/physics-readability`, containing Phase 3D-2B-2 implementation
`55a1aa941f53f9cf1efe7d3cf505bf94a5af53bf`. Working directory/worktree root:
`C:/Users/peng863/EMCD-Sim/.worktrees/windows-adaptive-compute`.
All 171 current registrations and independent historical controls passed before
editing. No checkout move/reset or prior-evidence replacement occurs.

Implementation commit: `8be3b5e6eda9a019ba4406aa0fe7ddd4ae86e8a6`. **Focused GO**: the neutral input
contract, supported historical models and required scientific equivalence pass.
This is not full regression, native desktop or release acceptance.

## B. Authoritative material-specific inventory

This inventory was completed before application changes. The complete raw
matches, direct production/test/tool consumers, protocol-method annotations,
saved-data requirements, authentication boundaries and decisions are retained
in `build/phase3e1/material-inventory-before.json`. It covers all 111 production
Python files, 111 grouped findings / 223 matched lines, and the material-indexed
coefficient data. Each table row groups occurrences at one symbol; names in
comments/docstrings are distinguished from behavior. Generic +Z local axes and
3d-element support bounds are physical model conventions, not Ni fallbacks.

A = general science; B = explicit preset/example; C = supported compatibility;
D = unnecessary implicit specialization; E = obsolete production convenience;
F = independent reference/QA. Static aliases are supplemented by provider/site
protocol consumers and the declared `emcd-ni-local-mdff` console entry point.
The four final columns record the pre-edit inventory: production-path use,
implicit material behavior, saved-data requirements and the existing identity
boundary. A preset/reference marked No in the production-path column still
has its concrete preset, CLI or reference consumers; it is not dead code.

| Module / symbol | Class | Actual purpose / consumer | Decision and reason | Production path | Implicit before | Saved requirement | Authentication before |
|---|---|---|---|---|---|---|---|
| `__init__.py:@module` | A | Local/protocol, explicit API/preset or validation; see full inventory | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | reviewed current source |
| `atomic_dipole.py:@module` | A | Local/protocol, explicit API/preset or validation; see full inventory | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | ordinary current source; no new pin proposed |
| `atomic_dipole.py:hydrogenic_radial_dipole_angstrom` | A | gui/saved_atomic_ui.py, historical_ni.py | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | ordinary current source; no new pin proposed |
| `atomic_ionization.py:@module` | A | Local/protocol, explicit API/preset or validation; see full inventory | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | ordinary current source; no new pin proposed |
| `atomic_ionization.py:AtomicMaterialParameters.validate` | A | Local/protocol, explicit API/preset or validation; see full inventory | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | ordinary current source; no new pin proposed |
| `atomic_ionization.py:transitions_for_material` | A | atomic_ionization.py, historical_ni.py | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | ordinary current source; no new pin proposed |
| `benchmark.py:@module` | B | Local/protocol, explicit API/preset or validation; see full inventory | Keep explicit named preset. Parameters supply shared implementations, not a separate engine | No | No | No | ordinary current source; no new pin proposed |
| `benchmark.py:nickel_apertures` | B | benchmark.py | Keep explicit named preset. Parameters supply shared implementations, not a separate engine | No | No | No | ordinary current source; no new pin proposed |
| `benchmark.py:nickel_physical_benchmark` | B | study_presets.py | Keep explicit named preset. Parameters supply shared implementations, not a separate engine | No | No | No | ordinary current source; no new pin proposed |
| `channeling.py:@module` | D | gui/cancellation_acceptance.py | Remove the now-unused historical phase import. Explicit providers already supply sites | Yes | Yes | No | reviewed current source |
| `channeling.py:calculate_detector_signals` | D | forward_pipeline.py | Require explicit sites before numerical work. The shared scheduler must not activate a Ni-only phase model when sites are omitted | Yes | Yes | No | reviewed current source |
| `crystal.py:fcc_nickel` | B | benchmark.py, multislice_reference.py, study_presets.py | Keep explicit named preset. Parameters supply shared implementations, not a separate engine | No | No | No | ordinary current source; no new pin proposed |
| `double_channeling.py:double_channeling_response` | C | channeling.py, double_channeling.py | Preserve immutable kernel and legacy domain; use explicit inputs in canonical callers. Whole-file pins and supported standalone Ni references; no repinning permitted | Yes | No | Yes | immutable current kernel |
| `double_channeling.py:_run_tensor_double_channeling` | C | double_channeling.py | Preserve immutable kernel and legacy domain; use explicit inputs in canonical callers. Whole-file pins and supported standalone Ni references; no repinning permitted | Yes | No | Yes | immutable current kernel |
| `double_channeling.py:run_tensor_double_channeling` | C | Local/protocol, explicit API/preset or validation; see full inventory | Preserve immutable kernel and legacy domain; use explicit inputs in canonical callers. Whole-file pins and supported standalone Ni references; no repinning permitted | Yes | No | Yes | immutable current kernel |
| `elastic.py:BeamSet.zolz` | A | benchmark.py | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | ordinary current source; no new pin proposed |
| `elastic_providers.py:@module` | C | Local/protocol, explicit API/preset or validation; see full inventory | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | ordinary current source; no new pin proposed |
| `elastic_providers.py:resolved_provider` | C | elastic_providers.py | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | ordinary current source; no new pin proposed |
| `elastic_providers.py:factors_for_provider` | C | scattering.py, structure_geometry.py | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | ordinary current source; no new pin proposed |
| `elastic_providers.py:provider_provenance` | C | forward_results.py, gui/geometry.py, gui/project_io.py | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | ordinary current source; no new pin proposed |
| `emcd_angular_plots.py:decorate_reciprocal_map` | A | gui/compare_results.py, gui/result_presentation.py | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | ordinary current source; no new pin proposed |
| `forward_results.py:assemble_forward_result` | A | forward_pipeline.py | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | reviewed current source |
| `forward_settings.py:@module` | A | Local/protocol, explicit API/preset or validation; see full inventory | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | reviewed current source |
| `forward_settings.py:NiForwardSettings` | B | forward_settings.py, gui/app.py, gui/calculation_controls.py, gui/group_mdff.py, gui/project_io.py, gui/project_session.py, gui/results_browser.py, gui/scientific_acceptance.py, gui/xmcd_preview.py, material_inputs.py, mdff_providers.py | Keep supported class/defaults; separate common representation from this preset. Explicit historical input model remains supported | No | No | Yes | reviewed current source |
| `forward_settings.py:MultiSiteForwardSettings` | D | forward_pipeline.py, gui/multisite_run.py, gui/project_io.py, gui/project_session.py | Derive from neutral common settings, preserve field order and saved values. Unnecessary Ni inheritance and atomic factory | Yes | Yes | No | reviewed current source |
| `generalized_xmcd.py:export_declared_xmcd` | A | mdff_providers.py | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | ordinary current source; no new pin proposed |
| `gui/app.py:MainWindow.__init__` | B | Local/protocol, explicit API/preset or validation; see full inventory | Retain explicitly identified Ni example / historical controls. Named preset/reference UI; generic execution is reviewed separately | No | No | No | reviewed current source |
| `gui/app.py:MainWindow.default_structure` | B | Local/protocol, explicit API/preset or validation; see full inventory | Retain explicitly identified Ni example / historical controls. Named preset/reference UI; generic execution is reviewed separately | No | No | No | reviewed current source |
| `gui/app.py:main` | B | gui/__init__.py | Retain explicitly identified Ni example / historical controls. Named preset/reference UI; generic execution is reviewed separately | No | No | No | reviewed current source |
| `gui/atomic_editor.py:@module` | C | Local/protocol, explicit API/preset or validation; see full inventory | Retain accepted-state/project/source compatibility. Editing/display/loading responsibility, not a material solver | No | No | Yes | reviewed current source |
| `gui/atomic_editor.py:AtomicParameterEditor.__init__` | C | Local/protocol, explicit API/preset or validation; see full inventory | Retain accepted-state/project/source compatibility. Editing/display/loading responsibility, not a material solver | No | No | Yes | reviewed current source |
| `gui/atomic_editor_help.py:@module` | C | Local/protocol, explicit API/preset or validation; see full inventory | Retain accepted-state/project/source compatibility. Editing/display/loading responsibility, not a material solver | No | No | Yes | ordinary current source; no new pin proposed |
| `gui/atomic_editor_model.py:@module` | C | Local/protocol, explicit API/preset or validation; see full inventory | Retain accepted-state/project/source compatibility. Editing/display/loading responsibility, not a material solver | No | No | Yes | ordinary current source; no new pin proposed |
| `gui/calculation_controls.py:@module` | C | Local/protocol, explicit API/preset or validation; see full inventory | Retain accepted-state/project/source compatibility. Editing/display/loading responsibility, not a material solver | No | No | Yes | reviewed current source |
| `gui/calculation_controls.py:CalculationControls.mdff_controls` | B | Local/protocol, explicit API/preset or validation; see full inventory | Retain explicitly identified Ni example / historical controls. Named preset/reference UI; generic execution is reviewed separately | No | No | No | reviewed current source |
| `gui/calculation_controls.py:CalculationControls.global_mdff_draft_settings` | D | Local/protocol, explicit API/preset or validation; see full inventory | Construct general drafts without Ni factories; select Ni only for explicit reference/saved historical inputs. Declared-source preparation currently constructs unused Ni parameters | No | Yes | No | reviewed current source |
| `gui/calculation_controls.py:CalculationControls.emcd_stale` | C | Local/protocol, explicit API/preset or validation; see full inventory | Retain accepted-state/project/source compatibility. Editing/display/loading responsibility, not a material solver | No | No | Yes | reviewed current source |
| `gui/cancellation_acceptance.py:run` | F | gui/app.py | Retain bounded opt-in QA/reference. Independent acceptance evidence is not obsolete production science | No | No | No | reviewed current source |
| `gui/desktop_acceptance.py:run.boot` | F | Local/protocol, explicit API/preset or validation; see full inventory | Retain bounded opt-in QA/reference. Independent acceptance evidence is not obsolete production science | No | No | No | reviewed current source |
| `gui/group_mdff.py:GroupMDFFDialog.candidate` | D | Local/protocol, explicit API/preset or validation; see full inventory | Use common declared-source input record. Temporary generic source construction should not seed Ni values | No | Yes | No | ordinary current source; no new pin proposed |
| `gui/imported_tensor_ui.py:ImportedTensorUI.generate_atomic_tensor` | C | Local/protocol, explicit API/preset or validation; see full inventory | Retain accepted-state/project/source compatibility. Editing/display/loading responsibility, not a material solver | No | No | Yes | reviewed current source |
| `gui/numerical_settings.py:@module` | C | Local/protocol, explicit API/preset or validation; see full inventory | Retain accepted-state/project/source compatibility. Editing/display/loading responsibility, not a material solver | No | No | Yes | reviewed current source |
| `gui/numerical_settings.py:resolve_parameters` | C | gui/numerical_settings.py | Retain accepted-state/project/source compatibility. Editing/display/loading responsibility, not a material solver | No | No | Yes | reviewed current source |
| `gui/numerical_settings.py:NumericalSettingsUI.resolve_numerical_ui` | C | Local/protocol, explicit API/preset or validation; see full inventory | Retain accepted-state/project/source compatibility. Editing/display/loading responsibility, not a material solver | No | No | Yes | reviewed current source |
| `gui/parallel_acceptance.py:run` | F | Local/protocol, explicit API/preset or validation; see full inventory | Retain bounded opt-in QA/reference. Independent acceptance evidence is not obsolete production science | No | No | No | reviewed current source |
| `gui/prb_benchmark.py:@module` | B | Local/protocol, explicit API/preset or validation; see full inventory | Retain explicitly identified Ni example / historical controls. Named preset/reference UI; generic execution is reviewed separately | No | No | No | reviewed current source |
| `gui/prb_benchmark.py:benchmark_readout` | B | gui/component_display.py, gui/normalization_export.py, gui/prb_controls.py | Retain explicitly identified Ni example / historical controls. Named preset/reference UI; generic execution is reviewed separately | No | No | No | reviewed current source |
| `gui/project_io.py:@module` | C | gui/multisite_project.py, gui/project_collection.py, gui/project_configuration.py, gui/project_session.py | Retain accepted-state/project/source compatibility. Editing/display/loading responsibility, not a material solver | No | No | Yes | reviewed current source |
| `gui/project_io.py:settings_from_dict` | C | gui/project_configuration.py, gui/project_io.py | Make old Ni reconstruction explicit and scope current general loading by configuration type. Known missing historical fields require old numerical values | No | No | Yes | reviewed current source |
| `gui/project_io.py:config_from_dict` | C | gui/project_configuration.py, gui/project_io.py | Decode stored atomic values explicitly; reject untyped/missing declarations; preserve recognized historical schemas. Saved old Ni dictionaries retain their meaning without a generic Ni fallback | No | No | Yes | reviewed current source |
| `gui/project_session.py:capture_configuration` | C | gui/calculation_controls.py, gui/project_session.py | Retain accepted-state/project/source compatibility. Editing/display/loading responsibility, not a material solver | No | No | Yes | ordinary current source; no new pin proposed |
| `gui/project_session.py:ProjectSession.new_project` | C | Local/protocol, explicit API/preset or validation; see full inventory | Retain accepted-state/project/source compatibility. Editing/display/loading responsibility, not a material solver | No | No | Yes | ordinary current source; no new pin proposed |
| `gui/provider_ui.py:ProviderUI.xmcd_declaration_controls` | C | Local/protocol, explicit API/preset or validation; see full inventory | Retain accepted-state/project/source compatibility. Editing/display/loading responsibility, not a material solver | No | No | Yes | reviewed current source |
| `gui/provider_ui.py:ProviderUI.declared_provider_settings` | D | Local/protocol, explicit API/preset or validation; see full inventory | Require explicit source or retained historical Atomic configuration; preserve explicit Ni reference selection. A missing source must not select Ni merely because the structure contains Ni | No | Yes | No | reviewed current source |
| `gui/results_browser.py:ProjectWorkspace._reset_project_inputs` | C | Local/protocol, explicit API/preset or validation; see full inventory | Retain accepted-state/project/source compatibility. Editing/display/loading responsibility, not a material solver | No | No | Yes | reviewed current source |
| `gui/results_browser.py:ProjectWorkspace._restore_single_settings` | C | Local/protocol, explicit API/preset or validation; see full inventory | Retain accepted-state/project/source compatibility. Editing/display/loading responsibility, not a material solver | No | No | Yes | reviewed current source |
| `gui/saved_atomic_ui.py:restore` | C | gui/app.py, gui/mdff_usability.py, gui/results_browser.py | Retain accepted-state/project/source compatibility. Editing/display/loading responsibility, not a material solver | No | No | Yes | reviewed current source |
| `gui/scientific_acceptance.py:@module` | F | Local/protocol, explicit API/preset or validation; see full inventory | Retain bounded opt-in QA/reference. Independent acceptance evidence is not obsolete production science | No | No | No | reviewed current source |
| `gui/scientific_acceptance.py:run` | F | Local/protocol, explicit API/preset or validation; see full inventory | Retain bounded opt-in QA/reference. Independent acceptance evidence is not obsolete production science | No | No | No | reviewed current source |
| `gui/unified_elastic_acceptance.py:run` | F | Local/protocol, explicit API/preset or validation; see full inventory | Retain bounded opt-in QA/reference. Independent acceptance evidence is not obsolete production science | No | No | No | reviewed current source |
| `gui/xmcd_preview.py:XMCDPreview.update_preview` | C | Local/protocol, explicit API/preset or validation; see full inventory | Retain accepted-state/project/source compatibility. Editing/display/loading responsibility, not a material solver | No | No | Yes | reviewed current source |
| `historical_ni.py:@module` | C | Local/protocol, explicit API/preset or validation; see full inventory | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | reviewed current source |
| `historical_ni.py:NiLocalConfig` | C | forward_settings.py, gui/calculation_controls.py, gui/project_io.py, historical_ni.py | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | reviewed current source |
| `historical_ni.py:ni_local_transitions` | C | historical_ni.py | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | reviewed current source |
| `historical_ni.py:_ni_transition_source` | C | historical_ni.py | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | reviewed current source |
| `historical_ni.py:main` | C | historical_ni.py | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | reviewed current source |
| `historical_ni.py:material_reason` | C | gui/numerical_settings.py, gui/unified_elastic_acceptance.py, historical_ni.py | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | reviewed current source |
| `historical_ni.py:tensors` | C | historical_ni.py | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | reviewed current source |
| `historical_ni.py:HistoricalNiSites` | C | historical_ni.py | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | reviewed current source |
| `historical_ni.py:HistoricalNiSites.positions_for` | C | Local/protocol, explicit API/preset or validation; see full inventory | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | reviewed current source |
| `historical_ni.py:HistoricalNiProvider` | C | mdff_providers.py | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | reviewed current source |
| `historical_ni.py:HistoricalNiProvider.sites` | C | Local/protocol, explicit API/preset or validation; see full inventory | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | reviewed current source |
| `legacy_atomic_factors.py:@module` | C | Local/protocol, explicit API/preset or validation; see full inventory | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | ordinary current source; no new pin proposed |
| `legacy_atomic_factors.py:LegacyNeutralAtomFactors.from_file` | C | legacy_atomic_factors.py | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | ordinary current source; no new pin proposed |
| `legacy_atomic_factors.py:configured_legacy_factors` | C | elastic_providers.py, legacy_atomic_factors.py | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | ordinary current source; no new pin proposed |
| `legacy_atomic_factors.py:factors_for_elastic_species` | E | Local/protocol, explicit API/preset or validation; see full inventory | Remove wrapper; migrate its four maintained test uses to explicit canonical providers. No production/script consumer; duplicates canonical provider selection, not an independent numerical reference | No | No | No | ordinary current source; no new pin proposed |
| `material_inputs.py:@module` | A | Local/protocol, explicit API/preset or validation; see full inventory | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | reviewed current source |
| `material_inputs.py:ImportedSettings` | D | gui/calculation_controls.py, gui/group_mdff.py, gui/project_configuration.py, gui/project_io.py, gui/project_session.py, gui/site_group_editor.py, material_inputs.py, mdff_providers.py | Derive from neutral common settings, preserve declarations and saved fields. General source records must not construct Ni physical inputs | Yes | Yes | No | reviewed current source |
| `material_inputs.py:ProviderSettings` | A | gui/calculation_controls.py, gui/project_io.py, gui/project_session.py, mdff_providers.py | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | reviewed current source |
| `mdff_providers.py:@module` | A | Local/protocol, explicit API/preset or validation; see full inventory | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | reviewed current source |
| `mdff_providers.py:prepare_provider` | A | forward_pipeline.py, gui/xmcd_preview.py, mdff_providers.py | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | reviewed current source |
| `mdff_providers.py:source_for` | A | forward_pipeline.py, gui/atomic_editor.py, gui/calculation_controls.py, gui/group_mdff.py, gui/imported_tensor_ui.py, gui/project_configuration.py, mdff_providers.py, multisite_double_channeling.py, multisite_single_channeling.py | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | reviewed current source |
| `mdff_tensor.py:@module` | A | Local/protocol, explicit API/preset or validation; see full inventory | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | ordinary current source; no new pin proposed |
| `multisite_spectrum.py:@module` | A | Local/protocol, explicit API/preset or validation; see full inventory | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | ordinary current source; no new pin proposed |
| `multislice_double_channeling.py:run_tensor_multislice_double_channeling` | C | Local/protocol, explicit API/preset or validation; see full inventory | Preserve immutable kernel and legacy domain; use explicit inputs in canonical callers. Whole-file pins and supported standalone Ni references; no repinning permitted | Yes | No | Yes | immutable current kernel |
| `multislice_reference.py:@module` | F | Local/protocol, explicit API/preset or validation; see full inventory | Retain independent reference and explicit Ni convenience. Reference/benchmark implementation, not redundant forward orchestration | No | No | No | ordinary current source; no new pin proposed |
| `multislice_reference.py:_projected_ni_potential` | F | multislice_reference.py | Retain independent reference and explicit Ni convenience. Reference/benchmark implementation, not redundant forward orchestration | No | No | No | ordinary current source; no new pin proposed |
| `parallel_resources.py:worker_plan` | A | propagation.py | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | reviewed current source |
| `propagation.py:numerical_info` | A | forward_pipeline.py, gui/calculation_controls.py, gui/numerical_settings.py | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | reviewed current source |
| `provenance.py:reference_source` | A | forward_settings.py, gui/unified_elastic_acceptance.py, xmcd_source.py | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | reviewed current source |
| `scattering.py:@module` | C | Local/protocol, explicit API/preset or validation; see full inventory | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | ordinary current source; no new pin proposed |
| `scattering.py:nickel_lobato_factor` | C | elastic_providers.py, legacy_atomic_factors.py, scattering.py | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | ordinary current source; no new pin proposed |
| `scattering.py:IndependentAtomPotential` | C | benchmark.py, multislice_reference.py, physical_elastic.py, projected_potential.py, scattering.py, structure_geometry.py, study_presets.py | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | ordinary current source; no new pin proposed |
| `scattering.py:FourierCutoffPotential` | C | scattering.py, structure_geometry.py, study_presets.py | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | ordinary current source; no new pin proposed |
| `scattering.py:elastic_reflection_allowed` | C | elastic.py, physical_elastic.py, structure_geometry.py | Retain explicit/legacy model and versioned provider interfaces. Supported historical Ni/data-provider consumers; current engine uses explicit provider identities | Yes | No | Yes | ordinary current source; no new pin proposed |
| `simulation.py:SimulationResult.at_edge` | E | Local/protocol, explicit API/preset or validation; see full inventory | Remove unused Ni-energy shortcut. No production, test, script or documentation consumer | No | No | No | ordinary current source; no new pin proposed |
| `single_channeling_tensor.py:@module` | C | Local/protocol, explicit API/preset or validation; see full inventory | Preserve immutable kernel and legacy domain; use explicit inputs in canonical callers. Whole-file pins and supported standalone Ni references; no repinning permitted | Yes | No | Yes | immutable current kernel |
| `single_channeling_tensor.py:historical_ni_site_phase_matrix` | C | channeling.py, single_channeling_tensor.py | Preserve immutable kernel and legacy domain; use explicit inputs in canonical callers. Whole-file pins and supported standalone Ni references; no repinning permitted | Yes | No | Yes | immutable current kernel |
| `single_channeling_tensor.py:run_tensor_single_channeling` | C | Local/protocol, explicit API/preset or validation; see full inventory | Preserve immutable kernel and legacy domain; use explicit inputs in canonical callers. Whole-file pins and supported standalone Ni references; no repinning permitted | Yes | No | Yes | immutable current kernel |
| `single_channeling_tensor.py:run_tensor_with_coherence` | C | single_channeling_tensor.py | Preserve immutable kernel and legacy domain; use explicit inputs in canonical callers. Whole-file pins and supported standalone Ni references; no repinning permitted | Yes | No | Yes | immutable current kernel |
| `structure_geometry.py:@module` | A | gui/multisite_project.py, gui/project_collection.py, gui/project_configuration.py, gui/project_io.py, gui/project_session.py | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | reviewed current source |
| `structure_geometry.py:Structure` | D | gui/app.py, gui/calculation_controls.py, gui/scientific_acceptance.py, gui/unified_elastic_acceptance.py, structure_geometry.py | Use neutral identity for new arbitrary structures; keep explicit/saved Ni labels. Incorrect material provenance can be attached without a material request | Yes | Yes | No | reviewed current source |
| `structure_geometry.py:Structure.nickel` | B | gui/app.py, gui/scientific_acceptance.py, gui/unified_elastic_acceptance.py | Keep; make its source label explicit. Intentionally requested built-in Ni example | No | No | No | reviewed current source |
| `structure_geometry.py:Settings` | D | gui/app.py, gui/project_io.py, gui/scientific_acceptance.py | Replace Ni-derived constructor geometry with neutral inputs; add explicit Ni preset and scoped legacy loading. New general input must not derive tilt from a Ni lattice | Yes | Yes | Yes | reviewed current source |
| `study_presets.py:@module` | B | Local/protocol, explicit API/preset or validation; see full inventory | Keep explicit named preset. Parameters supply shared implementations, not a separate engine | No | No | No | reviewed current source |
| `study_presets.py:NickelStudyGeometry` | B | Local/protocol, explicit API/preset or validation; see full inventory | Keep explicit named preset. Parameters supply shared implementations, not a separate engine | No | No | No | reviewed current source |
| `study_presets.py:NickelStudyGeometry.geometry` | B | Local/protocol, explicit API/preset or validation; see full inventory | Keep explicit named preset. Parameters supply shared implementations, not a separate engine | No | No | No | reviewed current source |
| `study_presets.py:NickelStudyGeometry.model` | B | Local/protocol, explicit API/preset or validation; see full inventory | Keep explicit named preset. Parameters supply shared implementations, not a separate engine | No | No | No | reviewed current source |
| `wien2k_source_audit.py:energy_audit` | A | xmcd_source.py | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | ordinary current source; no new pin proposed |
| `xmcd_source.py:@module` | A | Local/protocol, explicit API/preset or validation; see full inventory | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | reviewed current source |
| `xmcd_source.py:inspect_xmcd_source` | A | forward_results.py, gui/calculation_controls.py, gui/group_mdff.py, gui/results_browser.py | Keep general scientific functionality / truthful documentation. No independent material-specific solver is selected | Yes | No | No | reviewed current source |

## C. General scientific configuration

The generic hierarchy is now `ForwardSettings -> MultiSiteForwardSettings` and
`ForwardSettings -> ImportedSettings -> ProviderSettings`. The explicit
`NiForwardSettings` preset also derives from the common base. General records
construct no `NiLocalConfig`, select no source or Ni peaks, and supply no
Ni-derived aperture coordinates or post-edge window. Redundant subclass
overrides of already-neutral fields were removed. Numerical/resource field
names, ordering, class paths and supported source-backed declarations survive;
this is one execution representation, not a second engine or schema.

| Input | Previous implicit value | New general construction | Explicit/historical route |
|---|---|---|---|
| Arbitrary ASE structure source | Built-in FCC Ni, a=3.524 Å | In-memory ASE structure | `Structure.nickel()` supplies the original label; stored labels are never relabeled |
| Zone / target | [017] / (200) | [001] / (200) | `nickel_geometry_settings()` returns the common record with old [017] inputs |
| Tilt | 300 kV / 3.524 Å Ni-derived Bragg value | (0,0) mrad | Explicit preset retains (-5.5866881404,0); caller overrides keep old constructor semantics |
| Elastic provider | Adaptive in modern records; Lobato when missing in old projects | Adaptive unchanged | Historical Ni loading explicitly reconstructs missing Lobato identity |
| Source / atomic model | Ni source/factory inherited into general records | Empty source / `atomic=None` | Explicit `NiForwardSettings` retains original source/factory |
| Peaks / apertures / correction | General classes inherited Ni detector/window values | Unset peaks; empty centers, radius 0; empty window, correction off | Caller/source supplies peaks and aperture geometry; Ni preset keeps all previous values |
| Scheduler sites | Omission invoked historical Ni phases | Missing sites raise `ValueError` before numerical work | Canonical provider always supplies explicit sites, including explicit historical Ni sites |

Radius zero denotes an unconfigured aperture and is rejected before uniform
resource admission; the existing multisite validator also rejects it. It is a
finite, portable saved input, not a NaN that needs a new persistence rule. Edge
NaNs retain the existing null encoding in editable configuration files.

Maintained scripts and scientific fixtures retain their prior numerical inputs
explicitly: 115 formerly underspecified `Settings` calls in 48 files were
migrated. Calls missing the zone select the named historical geometry preset;
cases already selecting another zone record their prior tilt explicitly.
No array, equation, tolerance or physical setting was changed to obtain a pass.
The existing archived-source import translator binds historical `Settings`
imports to that preset in test namespaces only; archived bytes and the unchanged
22-case driver remain intact.

`config_from_dict` creates historical atomic parameters only for a recognized
old Ni record, or decodes an explicitly saved atomic dictionary. Declared and
multisite records without one retain `None`. Missing provider schema alongside
declared fields is an error. New incomplete generic drafts remain non-executable
generic records. Loading fully specified old values preserves them, including
unused historical fields. `settings_from_dict(..., historical_ni=True)` is the
identified old-project/script adapter; current declared/multisite readers
explicitly use the neutral context. Sparse historical Ni records keep their
old interpretation. No speculative external API aliases were added.

GUI draft construction and common sampling/resource resets use neutral records.
Only the explicit Ni reference choice or retained historical Atomic project
constructs the Ni preset. Selecting Ni atoms alone is insufficient to activate
an undeclared Atomic source. Restoration tolerates absent atomic/window inputs
and confines Ni-specific restoration to the explicit historical preset.

## D. Historical Ni responsibilities

All nine top-level historical symbols have concrete supported consumers. The
CLI, explicit Ni provider, legacy site protocol and original input values are
not obsolete merely because their names contain Ni. Nested validation/provider
methods are included in the machine-readable inventory.

| Symbol | Concrete consumer/purpose | Decision |
|---|---|---|
| `NiLocalConfig` | forward_settings.py, gui/calculation_controls.py, gui/project_io.py, historical_ni.py | Keep supported historical model / source identity |
| `ni_local_transitions` | historical_ni.py | Keep supported historical model / source identity |
| `_ni_transition_source` | historical_ni.py | Keep supported historical model / source identity |
| `main` | historical_ni.py | Keep supported historical model / source identity |
| `material_reason` | gui/numerical_settings.py, gui/unified_elastic_acceptance.py, historical_ni.py | Keep supported historical model / source identity |
| `tensors` | historical_ni.py | Keep supported historical model / source identity |
| `energy_grid` | historical_ni.py | Keep supported historical model / source identity |
| `HistoricalNiSites` | historical_ni.py | Keep supported historical model / source identity |
| `HistoricalNiProvider` | mdff_providers.py | Keep supported historical model / source identity |


| Retained historical method | Concrete consumer / responsibility |
|---|---|
| `NiLocalConfig.validate` | historical provider / canonical provider or site protocol; Retained historical model/configuration/site/provider protocol |
| `HistoricalNiSites.positions_for` | historical provider / canonical provider or site protocol; Retained historical model/configuration/site/provider protocol |
| `HistoricalNiSites.single_phase` | historical provider / canonical provider or site protocol; Retained historical model/configuration/site/provider protocol |
| `HistoricalNiProvider.__init__` | historical provider / canonical provider or site protocol; Retained historical model/configuration/site/provider protocol |
| `HistoricalNiProvider.material_reason` | historical provider / canonical provider or site protocol; Retained historical model/configuration/site/provider protocol |
| `HistoricalNiProvider.energy_grid` | historical provider / canonical provider or site protocol; Retained historical model/configuration/site/provider protocol |
| `HistoricalNiProvider.tensors` | historical provider / canonical provider or site protocol; Retained historical model/configuration/site/provider protocol |
| `HistoricalNiProvider.sites` | historical provider / canonical provider or site protocol; Retained historical model/configuration/site/provider protocol |
| `HistoricalNiProvider.revalidate_source` | historical provider / canonical provider or site protocol; Retained historical model/configuration/site/provider protocol |

No historical scientific function was deleted or reimplemented. All nine
symbols above and their nested validation/provider/site methods remain for the
same concrete consumers. `NiLocalConfig` field defaults, `ni_local_transitions`
event policy, source identity, energy-grid ordering, tensor generation, site
phases and the CLI are unchanged. `HistoricalNiProvider` is selected by the
existing exact `NiForwardSettings` type/model dispatch; generic records cannot
reach it by omission. It feeds the shared propagation/contraction schedules.

| Removed interface | Identified consumers and disposition | Reason |
|---|---|---|
| `legacy_atomic_factors.factors_for_elastic_species` | Four tests now select explicit LOBATO or LEGACY via `factors_for_provider`; zero production/script consumers | Redundant material-dependent dispatch; external-table parser, integrity checks and factor equations retained |
| `SimulationResult.at_edge(edge_ev=852.7)` | No source, maintained script, test or documentation caller | Unused Ni-energy convenience; generic result spectra/contrast methods retained |
| Scheduler's omitted-site fallback | Canonical forward caller already provides provider sites | Missing input must not select a material; historical phase helper remains authenticated in standalone/reference consumers |

Remaining compatibility is deliberate, not complete elimination of every Ni
name or dependency. `ForwardSettings.atomic` retains a nullable historical type
and serialized slot, and Ni/generic definitions share their existing module.
Old explicitly stored unused fields survive loading. The protected standalone
Single/BW/FFT kernels retain Ni-bounded omitted-site/852.7 eV conveniences for
identified historical references; the canonical engine always supplies actual
sites and energy. `IndependentAtomPotential` retains its old Ni-only unversioned
constructor default; `.from_provider` and the production structure engine use
explicit provider factors, and unsupported species without them fail.
Elastic utility `auto` selection still chooses the old Ni Lobato model for Ni;
the production engine passes `settings.elastic_provider` explicitly. Direct
utility defaults remain a future API cleanup, not a silently selected MDFF in
the canonical engine. Source-specific Ni audits, Ni117 convergence advisories
and the Windows Ni017 evidence/scheduling guard are preserved safeguards.

Retained explicit presets include `Structure.nickel`, `crystal.fcc_nickel`,
`NiForwardSettings`, `NiLocalConfig`, `NickelStudyGeometry`, Ni benchmark
apertures and the new `nickel_geometry_settings`. Ni reference conveniences in
`multislice_reference` remain independent scientific validation, not alternate
production forward orchestration. No material-specific production module was
removed; deleting `historical_ni.py` would remove supported science and the CLI.
No independent Cr or Fe3O4 production solver was found.

Scientific limitations remain unchanged: projected neutral IAM/finite ZOLZ,
dipole tensors, localized ionization, source-declared magnetic axes and modeled
energy coverage, with explicit errors outside supported conditions. Synthetic
BCC Cr is an ordered software fixture, not bulk Cr SDW physics; Fe3O4 fixtures
do not establish a new quantitative material model. Missing band, multiplet,
charge-transfer, calibrated moment/absolute-MDFF, full momentum or 3D/TDS physics
requires future scientific development, separate from the remaining software
compatibility cleanup.

## E. Focused verification

Evidence is under `build/phase3e1/`: every owned run has a log and a
`*-run.json` containing argv, cwd, starting HEAD/status, environment, Python,
PID, bound, duration and exit status; pytest continuations also have JUnit XML.
The Python 3.11.17 validation environment, fixed hash seed, one-thread native
libraries, offscreen Qt and short `build/nc-tmp` paths were reused. No completed
baseline was restarted for a clarification. Failures were retained separately;
continuations deselected completed nodes. The owned workflow tree was explicitly
stopped after observed failures; timeout handlers killed only their owned trees.

| Focused evidence | Outcome | Meaning |
|---|---|---|
| `science-headless` | 70 passed | Eight strict headless calculations, all six numerical contracts, independent Ni/Cr events/reversal, tensor and source invariants |
| `roundtrip-corrected` | 17 passed | Three failed generalized/local round trips, neutral input contracts and three fresh-process settings/resource checks |
| Broad affected workflow selection, completed across `workflows*` continuations | 223 passed, 5 skipped | All 228 existing selected cases completed; no full regression claim |
| `final-headless` | 9 passed | Eight strict Ni/Cr calculations repeated after final input validation, plus the new non-Ni negative case |
| Authentication prefix in `authentication-corrected.log` plus `authentication-remainder.xml` | 18 completed passes + 24 passed / 1 skipped | All 43 selected source/history/offline/runtime cases completed; prefix/continuation are counted once |
| Existing legacy-table tests in `neutral-inputs-corrected.xml` | 5 passed, 13 skipped | Explicit provider choice, missing-source diagnostics and identity gate preserved; external table unavailable |
| Current protected changed-file mutations | 13 rejected (5 prefix + 8 continuation); real controls pass afterward | Existing in-memory byte overrides only; three ordinary GUI controllers retain behavioral coverage |
| `exact-final` | 22 cases / 2,294 arrays exactly equal | Original source `cdb8836388c5ccc5ae7a614b47894c0ab158a824`, unchanged driver; physical metadata and edge metrics also equal |

**Distinct test coverage: 343 passed, 19 skipped**, after deduplicating named
cases across these artifacts and retaining the 12 completed statuses/lifecycle
records in the deliberately stopped first workflow run. This is combined
focused coverage, not a complete regression result. The implementation is committed separately from its registration/report
successor. Subsequent registration-only checks repeat existing nodes and do not
increase this count. Source-mutation
virtual cases and the 22-case array comparison are reported separately.

The six required contracts passed without changing any assertions/tolerances:
`test_bw_unchanged_and_depth_cancel[numerical]`,
`test_full_spectrum_unchanged[bloch]`, `[both]`,
`test_bcc_cr_independent_events_and_symmetry[unequal-mdff-double-bloch]`, and
`test_original_ni_all_numeric_arrays_exact[double-xmcd]` / `[double-atomic]`.
The cancellation-sensitive Cr contract remains its established roundoff bound;
serialization, array persistence, source bytes and lossless operations retain
exact comparisons.

All eight real headless cases use the root calculation with strict GUI/Qt import
rejection, existing source/model identity and mask/array checks, explicit sites,
resource reservations, worker/child/thread cleanup and Windows BW/BLAS locks.
The new non-Ni negative first validates a complete synthetic Cr uniform request,
then removes its source or element and proves that neither historical Ni
construction nor propagation occurs. It separately rejects missing apertures.
The four established Cr AFM cases retain their original opposite-site inputs;
the new negative does not change those fixtures or assert real Cr ground-state
physics. Source-backed and historical Ni project tests exercise old loading,
missing/tampered/relocated sources, original snapshots and selected-run restoration.

Three optional native GUI profiles, the optional saved-GUI reference, optional
pinned upstream HDF5 data, the external 160-array unit-label evidence and 13
external legacy-table cases account for the 19 skips. None of the required
eight calculations, six contracts or 22-case exact comparison is skipped.
No missing reference was regenerated or substituted.

Unsuccessful evidence is intentionally retained. `neutral-inputs` was a test
path typo with no executed cases. `neutral-inputs-valid` caught an inadvertently
removed shared wavelength import plus two overstrict new test assertions;
the import was restored and new structure checks use the existing identity
tolerance rather than claiming lossless ASE coordinate reconstruction.
`neutral-inputs-corrected` retained the remaining new-coordinate failure before
that fix. No original scientific comparison was relaxed.

The first workflow run exposed restoration's unconditional Ni atomic access.
Subsequent continuations found synthetic stored/run/provider fixtures relying
on inherited aperture defaults. Restoration now handles optional fields; those
fixtures record their original aperture values explicitly. Source constructors
remain neutral. All failed cases completed successfully later. A new negative
test initially hit unrelated AFM eligibility; its setup now explicitly selects
the source's uniform branch, validates the complete request first, and scopes
negative spies before GUI cleanup.

The first authentication run reported 41 passes/1 skip before timeout and had no
finalized XML; it is not presented as a clean run or added to totals. A bounded
GUI reproduction produced a native Matplotlib constrained-layout access
violation in the hidden units-only test. That test now suppresses queued canvas
painting while preserving every widget-label and no-worker assertion; normal
rendering/export workflows remain separately tested. A later stack also showed
slow authenticated filesystem reads, so painting is not asserted to be the
sole cause of the first timeout. The corrected run completed 18 named cases
before its bound; only its 25 unfinished nodes were continued, completing with
24 passes/1 skip and finalized XML. No source guard was disabled. The final registration-pointer check then
completed with **2 passed** in `final-registration.xml`; these repeat existing
nodes and are not added to the distinct count.

The changed-file mutation script first assumed all GUI controllers were pinned;
after five valid rejections it found three intentionally unregistered ordinary
GUI controllers. The existing policy is preserved: `group_mdff`,
`project_configuration` and `project_session` use behavioral tests, not new
identity gates. Their actual consumers and source-authentication classification
are in the initial inventory. The remaining eight protected-file checks passed in
`changed-source-mutations-remainder`, with real-disk positive controls afterward. This is not an unauthorized-source acceptance or a scientific
kernel repin.


Use `build/phase3e1/` for logs/XML/argv/environment/source identities, the
existing Python 3.11 environment and short temporary paths. No full regression,
EXE build/replacement, version bump, push, merge, tag or publication is performed.

## F. Complexity and generality

Same established AST/token methodology as the starting report, applied to
tracked current production Python under `src/`. GUI is a subset; non-GUI is
the difference, never an added overlapping total. Physical lines include every
line. Nonblank/noncomment includes docstrings; source LOC also excludes
module/class/function docstrings. Literal internal imports include deferred
imports, with one edge per module pair; dynamic dispatch and third-party edges
are not counted. SCCs contain more than one module. Artifacts:
`build/phase3e1/before.json`, `after.json`, and the reused `measure.py`.

| Metric | Before | After | Absolute / percentage change |
|---|---:|---:|---:|
| Production Python files | 111 | 111 | +0 / +0.00% |
| GUI Python files | 53 | 53 | +0 / +0.00% |
| Non-GUI Python files | 58 | 58 | +0 / +0.00% |
| Physical Python lines | 19,571 | 19,602 | +31 / +0.16% |
| Nonblank, noncomment lines (including docstrings) | 17,481 | 17,512 | +31 / +0.18% |
| Source LOC (excluding docstrings) | 16,519 | 16,547 | +28 / +0.17% |
| Internal import edges | 495 | 498 | +3 / +0.61% |
| Cyclic dependency groups | 4 | 4 | +0 / +0.00% |
| Modules in cycles | 14 | 13 | -1 / -7.14% |
| Largest SCC | 5 | 5 | +0 / +0.00% |
| Non-GUI → GUI edges | 5 | 5 | +0 / +0.00% |

No production module was created, moved, renamed or deleted. No competing
material kernel was consolidated because no separate Ni/Cr/Fe3O4 production
solver was found: the baseline already had one forward engine. This phase
preserves that centralization and improves its input contract. Two unused
interfaces and the generic missing-site branch were removed; generic records
no longer inherit the Ni preset. These are behavioral and dependency changes,
not cosmetic relocation.

Source LOC increases by 28 and import edges by three: explicit preset/loading
and input validation add small, reviewable responsibilities. The external
legacy-table parser no longer imports scattering through the deleted dispatch
wrapper, reducing its old three-member cycle to the two-member
`elastic_providers`/`scattering` cycle. Four SCCs remain; this is a reduction in
one cycle's membership, not removal of all coupling. The other groups are the
five-module GUI app/acceptance family, the three-module atomic/imported/manual
provider family, and the three-module GUI project configuration/I/O family.

All five reverse edges remain: `__main__ -> gui` and the reviewed
`gui.memory_budget` imports from `double_channeling`,
`multislice_double_channeling`, `multislice_reference` and `projected_potential`.
No new GUI import enters the scientific engine. Retained material-specific
modules are `historical_ni`, `study_presets` and the explicit Ni benchmark;
material-specific module deletions: **0**. Independent reference implementations
and genuinely different physical/numerical methods remain separate.

The gain is less hidden material coupling in constructors and execution, not
a smaller module graph. This phase does not establish wholesale architectural
simplification, complete utility-default neutrality or new scientific capability.


## G. Phase 3E-2 handoff

Future focused cleanup should separate widget collection/transactions,
restoration, rendering and file compatibility at existing owners. Do not move
numerical equations into another GUI facade or merge different scientific
models to reduce file count.

| GUI module | Physical lines | Source LOC |
|---|---:|---:|
| `src/emcd_sim/gui/app.py` | 676 | 620 |
| `src/emcd_sim/gui/atomic_editor.py` | 627 | 574 |
| `src/emcd_sim/gui/group_mdff.py` | 599 | 547 |
| `src/emcd_sim/gui/responsive.py` | 614 | 531 |
| `src/emcd_sim/gui/calculation_controls.py` | 570 | 529 |
| `src/emcd_sim/gui/project_io.py` | 584 | 493 |
| `src/emcd_sim/gui/site_group_editor.py` | 529 | 461 |
| `src/emcd_sim/gui/project_session.py` | 500 | 461 |

`app` still coordinates substantial state, callbacks and preview actions;
`calculation_controls` mixes input translation, validation, worker actions and
preview presentation. `results_browser` couples display with detailed input
restoration; `project_session` combines capture, selected-run restoration and
project actions. `project_io` retains required saved-array reconstruction,
source integrity and schema compatibility, not a second solver. Group/Atomic
editors retain accepted/draft transactions and source/model-specific controls.
`responsive` has large but independent layout responsibilities; size alone
is not evidence of duplicated physics.

GUI elastic preview orchestration and MDFF preview reductions still merit
future owner review. The engine, source services and resource model remain
authoritative; maintain visible Apply/Cancel, original atom indices, source
acknowledgement, old project interpretation and saved-array identity when
extracting additional GUI responsibilities. Source-backed energy planning also
still validates numerical/detector controls; changing that API belongs in a
separate focused contract review. No such future cleanup is performed here.



Apart from this report, the source-registration/report successor updates only the existing
`production_source` pointer and its required loader checksum; application source,
reference arrays, original archive identities and scientific kernel pins remain
those of the implementation commit. No full regression, EXE build/replacement,
version bump, installed-beta change, merge, tag, push or publication was performed.


Current reviewed overrides number 173, versus 171 initially. The two additional
current entries are `legacy_atomic_factors.py` and `simulation.py`: both were
already protected by historical source identities. Their unmodified preimages
were retained in the existing `previous_sources` layer to support the reviewed
removal of their unused interfaces. Original archive/kernel identities are not
repinned, and no identity requirement is added to ordinary GUI controllers.
