"""Relocate dependencies of identified archived GUI references, not their math.

The energy-schedule, pre-feature Ni, Part 1C and released-controls tests execute
recorded Git source. Removed production import names must not force us to keep
obsolete APIs. Bind the old names only inside those reference namespaces; keep
all numerical statements and immutable source evidence unchanged.
"""
import ast


def relocate_reference_imports(source):
    routes={
        'ForwardSettings':('emcd_sim.forward_settings','NiForwardSettings'),
        'DEFAULT_SOURCE':('emcd_sim.forward_settings','DEFAULT_NI_SOURCE'),
        'inspect_source':('emcd_sim.xmcd_source','inspect_xmcd_source'),
        'calculate':('emcd_sim.forward_pipeline','calculate'),
        'metrics':('emcd_sim.forward_results','selected_edge_metrics'),
        'export_result':('emcd_sim.gui.result_export','export_result'),
        'Cancelled':('emcd_sim.cancellation','Cancelled'),
        'material_reason':('emcd_sim.historical_ni','material_reason'),
        'tensors':('emcd_sim.historical_ni','tensors'),
        'energy_grid':('emcd_sim.historical_ni','energy_grid'),
        'axis_rotation':('emcd_sim.mdff_orientation','axis_rotation'),
    }
    source=source.decode('utf-8-sig') if isinstance(source,bytes) else source
    positions=[0]
    for line in source.splitlines(keepends=True):positions.append(positions[-1]+len(line))
    edits=[]
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node,ast.ImportFrom):continue
        groups={};changed=False
        for item in node.names:
            target=None;name=item.name
            if node.module in ('multislice_double_channeling','emcd_sim.multislice_double_channeling') and item.name=='ProjectedNiFFT':
                target,name='emcd_sim.multislice_double_channeling','ProjectedFFT';changed=True
            elif node.module in ('single_channeling_tensor','emcd_sim.single_channeling_tensor') and item.name=='fcc_site_phase_matrix':
                target,name='emcd_sim.single_channeling_tensor','historical_ni_site_phase_matrix';changed=True
            elif node.module in ('ni_017_geometry','emcd_sim.ni_017_geometry') and item.name=='Ni017Geometry':
                target='legacy_geometry';changed=True
            elif node.module in ('emcd_forward','emcd_sim.gui.emcd_forward'):
                target,name=routes[item.name];changed=True
            elif node.module in ('generalized_forward','emcd_sim.gui.generalized_forward',
                                 'material_inputs','emcd_sim.gui.material_inputs'):
                target=('emcd_sim.material_inputs' if item.name in ('ImportedSettings','ProviderSettings')
                        else 'emcd_sim.mdff_providers');changed=True
            elif node.module in ('provider_preparation','emcd_sim.gui.provider_preparation',
                                 'provider_direction','emcd_sim.gui.provider_direction'):
                target='emcd_sim.mdff_providers';changed=True
            elif node.module in ('project_io','emcd_sim.gui.project_io') and item.name in (
                    'structure_snapshot','restore_structure','structures_match'):
                target='emcd_sim.structure_geometry';changed=True
            elif node.module in ('forward_results','emcd_sim.gui.forward_results') and item.name in ('export_result','export_method_result'):
                target='emcd_sim.gui.result_export';changed=True
            elif node.module in ('results','emcd_sim.gui.results') and item.name=='method_result':
                target='emcd_sim.forward_results';changed=True
            elif node.module in ('results','emcd_sim.gui.results') and item.name in (
                    'mdff_label','geometry_description','spectral_coverage_label','draw_maps',
                    '_draw_eels_diagnostics','draw_eels','draw_component_maps','draw_diffraction',
                    'draw_comparison','_single_comparison_text','comparison_text'):
                target='emcd_sim.gui.result_presentation';changed=True
            elif node.module in ('multisite_export','emcd_sim.gui.multisite_export'):
                target='emcd_sim.gui.multisite_results' if item.name=='DEFINITIONS' else 'emcd_sim.gui.result_export';changed=True
            elif node.module in ('multisite_results_controls','emcd_sim.gui.multisite_results_controls'):
                target='emcd_sim.gui.result_presentation';changed=True
            elif node.module in ('multisite_results','emcd_sim.gui.multisite_results') and item.name=='draw_totals':
                target,name='emcd_sim.gui.result_presentation','draw_multisite_panel';changed=True
            elif node.module in ('propagation','emcd_sim.gui.propagation') and item.name=='export_comparison':
                target='emcd_sim.gui.result_export';changed=True
            elif node.module in ('forward_results','emcd_sim.gui.forward_results') and item.name in ('assemble_forward_result','selected_edge_metrics','method_result'):
                target='emcd_sim.forward_results';changed=True
            elif node.module in ('xmcd_source','emcd_sim.gui.xmcd_source') and item.name=='inspect_xmcd_source':
                target='emcd_sim.xmcd_source';changed=True
            elif node.module in ('runtime','emcd_sim.gui.runtime') and item.name in ('LABEL','PHYSICS_CONVENTION','result_convention_status','resource_root','reference_source','build_info'):
                target='emcd_sim.provenance';changed=True
            elif node.module in ('prb_benchmark','emcd_sim.gui.prb_benchmark') and item.name in ('DEFINITION','relative_dichroism_percent','benchmark_spectra'):
                target='emcd_sim.detector_signals';changed=True
            elif node.module in ('signal_normalization','emcd_sim.gui.signal_normalization') and item.name in ('POLICY','EELS_FLOOR','scale95','divide_percent'):
                target='emcd_sim.detector_signals';changed=True
            elif node.module in ('forward_settings','emcd_sim.gui.forward_settings'):
                target='emcd_sim.forward_settings';changed=True
            elif node.module in ('parallel_resources','emcd_sim.gui.parallel_resources') and item.name!='preview_text':
                target='emcd_sim.parallel_resources';changed=True
            elif node.module in ('hardware_resources','emcd_sim.gui.hardware_resources'):
                target='emcd_sim.hardware_resources';changed=True
            elif node.module in ('memory_budget','emcd_sim.gui.memory_budget','gui.memory_budget'):
                target='emcd_sim.memory_budget';changed=True
            elif node.module=='forward_pipeline' and item.name=='calculate_prepared':
                target,name='emcd_sim.forward_pipeline','_calculate_uniform_prepared';changed=True
            elif node.module=='channeling' and item.name=='contract':
                target,name='emcd_sim.channeling','calculate_detector_signals';changed=True
            elif node.module in ('geometry','emcd_sim.gui.geometry') and item.name in ('Structure','Settings','orientation','geometry','elastic_model','excitation','za_from_tilt','tilt_from_za','align_bragg','structure_snapshot','restore_structure','structures_match','projected_geometry_from_oriented_crystal'):
                target='emcd_sim.structure_geometry';changed=True
            elif node.module in ('propagation','emcd_sim.gui.propagation') and item.name in ('projected_geometry_for','projected_geometry_from_oriented_crystal'):
                target,name='emcd_sim.structure_geometry','projected_geometry_from_oriented_crystal';changed=True
            elif node.module in ('propagation','emcd_sim.gui.propagation') and item.name=='propagate':
                target='emcd_sim.channeling';changed=True
            elif node.module in ('propagation','emcd_sim.gui.propagation'):
                target='emcd_sim.propagation';changed=True
            elif node.module in ('channeling','emcd_sim.gui.channeling'):
                target='emcd_sim.channeling';changed=True
            elif node.module in ('multisite_integration','emcd_sim.gui.multisite_integration'):
                target='emcd_sim.multisite_integration';changed=True
            elif node.module in ('forward_pipeline','emcd_sim.gui.forward_pipeline'):
                target='emcd_sim.forward_pipeline';changed=True
            elif (node.module in ('emcd_sim.gui','gui') or (node.module is None and node.level==1)) and item.name in ('propagation','channeling','multisite_integration','forward_pipeline'):
                target='emcd_sim';changed=True
            if target is None:target='.'*node.level+(node.module or '')
            binding=item.asname or item.name
            groups.setdefault(target,[]).append(name+(' as '+binding if name!=binding else ''))
        if changed:
            indent=' '*node.col_offset
            value=('\n'+indent).join('from '+module+' import '+', '.join(names) for module,names in groups.items())
            edits.append((positions[node.lineno-1]+node.col_offset,positions[node.end_lineno-1]+node.end_col_offset,value))
    for begin,end,value in sorted(edits,reverse=True):source=source[:begin]+value+source[end:]
    return source
