"""Relocate dependencies of identified archived GUI references, not their math.

The energy-schedule, pre-feature Ni, Part 1C and released-controls tests execute
recorded Git source. Removed production import names must not force us to keep
obsolete APIs. Bind the old names only inside those reference namespaces; keep
all numerical statements and immutable source evidence unchanged.
"""
import ast


def relocate_reference_imports(source):
    routes={
        'ForwardSettings':('emcd_sim.gui.forward_settings','NiForwardSettings'),
        'DEFAULT_SOURCE':('emcd_sim.gui.forward_settings','DEFAULT_NI_SOURCE'),
        'inspect_source':('emcd_sim.gui.xmcd_source','inspect_xmcd_source'),
        'calculate':('emcd_sim.gui.forward_pipeline','calculate'),
        'metrics':('emcd_sim.gui.forward_results','selected_edge_metrics'),
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
            if node.module in ('emcd_forward','emcd_sim.gui.emcd_forward'):
                target,name=routes[item.name];changed=True
            elif node.module in ('generalized_forward','emcd_sim.gui.generalized_forward',
                                 'material_inputs','emcd_sim.gui.material_inputs'):
                target=('emcd_sim.gui.material_inputs' if item.name in ('ImportedSettings','ProviderSettings')
                        else 'emcd_sim.mdff_providers');changed=True
            elif node.module in ('provider_preparation','emcd_sim.gui.provider_preparation',
                                 'provider_direction','emcd_sim.gui.provider_direction'):
                target='emcd_sim.mdff_providers';changed=True
            elif node.module in ('project_io','emcd_sim.gui.project_io') and item.name in (
                    'structure_snapshot','restore_structure','structures_match'):
                target='emcd_sim.gui.geometry';changed=True
            elif node.module in ('forward_results','emcd_sim.gui.forward_results') and item.name in ('export_result','export_method_result'):
                target='emcd_sim.gui.result_export';changed=True
            elif node.module in ('results','emcd_sim.gui.results') and item.name=='method_result':
                target='emcd_sim.gui.forward_results';changed=True
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
            elif node.module=='forward_pipeline' and item.name=='calculate_prepared':
                target,name='emcd_sim.gui.forward_pipeline','_calculate_uniform_prepared';changed=True
            elif node.module=='channeling' and item.name=='contract':
                target,name='emcd_sim.gui.channeling','calculate_detector_signals';changed=True
            elif node.module=='propagation' and item.name=='projected_geometry_for':
                target,name='emcd_sim.gui.propagation','projected_geometry_from_oriented_crystal';changed=True
            if target is None:target='.'*node.level+(node.module or '')
            binding=item.asname or item.name
            groups.setdefault(target,[]).append(name+(' as '+binding if name!=binding else ''))
        if changed:
            indent=' '*node.col_offset
            value=('\n'+indent).join('from '+module+' import '+', '.join(names) for module,names in groups.items())
            edits.append((positions[node.lineno-1]+node.col_offset,positions[node.end_lineno-1]+node.end_col_offset,value))
    for begin,end,value in sorted(edits,reverse=True):source=source[:begin]+value+source[end:]
    return source
