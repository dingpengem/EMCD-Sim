"""File and image exports of completed single-provider and multi-site results."""
import csv
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path

import numpy as np

from .. import __version__
from ..multislice_reference import complex_wave_diagnostics
from .forward_results import selected_edge_metrics
from .multisite_results import SPECTRAL_KEYS, QUANTITIES, material, spectral_series, selection_description, DEFINITIONS


def _json_value(value):
    """Keep metadata JSON portable; unset numerical settings become null."""
    if is_dataclass(value):return _json_value(asdict(value))
    if isinstance(value, dict):return {str(k):_json_value(v) for k,v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):return [_json_value(v) for v in value]
    if isinstance(value, np.generic):return _json_value(value.item())
    if isinstance(value, float) and not np.isfinite(value):return None
    if isinstance(value, Path):return str(value)
    return value


def export_multisite_spectra(result, path, *, method=None, selection=('total',None),
                            normalization='weighted', compared=(), quantity=0, include_total=False):
    """Write the selected stored curves and all their linear signal components.

    One CSV row per series and original energy sample. Unsupported intensities
    are blank, never a fabricated zero. Active calculated zeros remain numeric.
    csv.writer's float representation round-trips binary64 values without a
    display-precision limit. No calculation, resampling or source IO occurs.
    """
    method = method or result.get('method','bloch')
    r = result.get('methods',{}).get(method,result)
    series = spectral_series(r,selection,normalization,compared,include_total)
    if not series:raise ValueError('Select at least one comparison group or include the total before exporting.')
    channels = r['metadata']['multisite']['channels']
    denominator = r['metadata']['multisite']['selected_atom_count']
    energy = r['spectra']['energy_ev']
    records = []
    for index,item in enumerate(series):
        kind = 'total' if item['normalization']=='total' else 'element' if selection[0]=='element' else 'group'
        identity = 'Total' if kind=='total' else selection[1] if kind=='element' else item['groups'][0]
        convention = {'total':'total_mean_per_selected_ionizing_atom', 'weighted':'additive_contribution_n_over_N',
                      'mean':'group_mean_per_atom_nonadditive'}[item['normalization']]
        records.append(dict(series_index=index,series_kind=kind,series_id=identity,label=item['label'],
            group_ids=item['groups'],normalization=convention,applied_scale=item['scale'],
            global_denominator=denominator,
            multiplicities={gid:r['groups'][gid]['metadata']['multiplicity'] for gid in item['groups']},
            declared_source_units={gid:r['groups'][gid]['metadata']['source'].get('units','undeclared') for gid in item['groups']}))

    crystal = r['model'].elastic.crystal
    metadata = dict(
        kind='Multi-site numerical spectra export (not a saved project)',
        spectrum_kind='modeled_partial_core_edge_spectrum',material=material(r),
        structure=dict(species=crystal.species,lattice_angstrom=crystal.lattice_angstrom,
                       fractional_positions=crystal.fractional_positions),
        method=method,settings=r['settings'],calculation_config=r['config'],
        software_version=r['metadata'].get('software_version',__version__),
        calculation_metadata=r['metadata'],groups={gid:g['metadata'] for gid,g in r['groups'].items()},
        selection=dict(mode=selection,compared=compared,include_total=include_total,
                       displayed_quantity=QUANTITIES[quantity][0]),
        series=records,normalization_description=selection_description(r,series),
        signal_definitions=DEFINITIONS,
        state_definition='plus is the active declared configuration; minus reverses every physical provider pair together. '
                         'If global_reversal is true, plus uses the declared -M states. No conjugation inference.',
        units=dict(energy_ev='eV',intensities='Relative provider intensity scale; declared source units recorded per group; no unit conversion or cross-element calibration.'),
        coverage=dict(modeled='At least one selected channel active; inactive channels listed separately.',
                      excluded='Every selected channel explicitly excluded by request.',
                      unmodeled='No selected channel modeled at this energy; intensities blank.',
                      note='No interpolation or extrapolation. Blank is not physical zero. Numeric zero is a calculated active value. '
                           'Load the long-form CSV by series_index and use coverage_state to break lines across unsupported gaps.'),
        limitations='Partial core-edge spectrum, not complete EELS. Provider amplitudes retained; no automatic peak/area scaling or absolute cross-element calibration.',
        metadata_note='JSON is written automatically for provenance; no JSON input is required. Unset/nonfinite metadata settings are null.')
    encoded = json.dumps(_json_value(metadata),indent=2,allow_nan=False)+'\n'
    root = Path(path);root.mkdir(parents=True,exist_ok=False)
    fields = ['solver','channeling_model','series_index','series_kind','series_id','label','normalization',
              'global_denominator','intensity_units','energy_ev','coverage_state',
              'active_group_ids','excluded_group_ids','unmodeled_group_ids',*SPECTRAL_KEYS]
    with (root/'spectra.csv').open('w',encoding='utf-8',newline='') as stream:
        writer = csv.DictWriter(stream,fields);writer.writeheader()
        for item,record in zip(series,records):
            for ie,loss in enumerate(energy):
                active = [];excluded = [];unmodeled = []
                for gid in item['groups']:
                    channel = channels[gid]
                    if channel['omitted_by_request']:excluded.append(gid)
                    elif channel['active_energy_mask'][ie]:active.append(gid)
                    else:unmodeled.append(gid)
                state = 'modeled' if active else 'excluded' if len(excluded)==len(item['groups']) else 'unmodeled'
                row = {key:record[key] for key in ('series_index','series_kind','series_id','label','normalization','global_denominator')}
                row.update(solver=method,channeling_model=r['config'].channeling_model,
                    intensity_units='relative_provider_scale',energy_ev=float(loss),coverage_state=state,
                    active_group_ids=json.dumps(active),excluded_group_ids=json.dumps(excluded),unmodeled_group_ids=json.dumps(unmodeled))
                row.update({key:float(item['spectra'][key][ie]) if active else '' for key in SPECTRAL_KEYS})
                writer.writerow(row)
    (root/'metadata.json').write_text(encoded,encoding='utf-8')
    return root


def export_method_result(result,path):
    """Export one completed solver result to a new directory, without rerunning."""
    from matplotlib.figure import Figure
    from emcd_sim.gui.result_presentation import draw_maps, draw_eels
    root=Path(path);root.mkdir(parents=True,exist_ok=False)
    meta=dict(result['metadata'],edge_metrics=selected_edge_metrics(result))
    for name,value in (('input_parameters',dict(settings=meta['settings'],mdff=meta['mdff'],structure=meta['structure'])),('metadata',meta)):
        (root/(name+'.json')).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    np.savez_compressed(root/'virtual_detector_eels.npz',**result['spectra'])
    arrays=dict(qx=result['qx'],qy=result['qy'],coherence=result['coherence'],depth_nm=result['depth_nm'],amplitudes=result['amplitudes'])
    for edge,m in result['maps'].items():
        arrays.update({edge+'_'+k:v for k,v in m.items()})
        fig=Figure(figsize=(15,9),layout='constrained');draw_maps(fig,result,edge);fig.savefig(root/(edge+'_angular_maps.png'),dpi=145)
    arrays.update({'weight_'+k:v for k,v in result['weights'].items()});np.savez_compressed(root/'angular_maps.npz',**arrays)
    fig=Figure(figsize=(11,9),layout='constrained');draw_eels(fig,result);fig.savefig(root/'virtual_detector_eels.png',dpi=150)


def export_result(result,path,*,component_mode='raw',advanced=False,map_signal_mode=None):
    """One numerical bundle; raw and percentage spectra survive every display."""
    if advanced:
        export_method_result(result,path)
        export_comparison(result,Path(path),export_method_result)
        return
    import csv
    from matplotlib.figure import Figure
    from .project_io import save_project
    from emcd_sim.gui.result_presentation import draw_eels, draw_maps
    from .prb_benchmark import benchmark_spectra
    from .component_display import MODES,DEFINITIONS,exported_spectra,exported_angular
    if component_mode not in (*MODES,'relative'):raise ValueError('Unknown EMCD display mode')
    map_signal_mode=map_signal_mode or (component_mode if component_mode in MODES else 'raw')
    if map_signal_mode not in MODES:raise ValueError('Unknown angular signal display')
    root=save_project(result,path)
    derived={};unavailable={}
    methods=result.get('methods',{result.get('method','bloch'):result})
    for name,r in methods.items():
        spectra=dict(r['spectra'],**benchmark_spectra(r['spectra'])[0]);keys=list(spectra)
        with (root/(name+'_spectra.csv')).open('w',newline='',encoding='utf-8') as f:
            writer=csv.writer(f);writer.writerow(['solver','channeling_model']+keys)
            writer.writerows((name,r['config'].channeling_model,*values) for values in zip(*(spectra[k] for k in keys)))
        explicit=exported_spectra(r['spectra']);derived.update({name+'__'+k:v for k,v in explicit.items()})
        with (root/(name+'_signal_display.csv')).open('w',newline='',encoding='utf-8') as f:
            writer=csv.writer(f);writer.writerow(list(explicit));writer.writerows(zip(*explicit.values()))
        prefix='' if name==result.get('method','bloch') else name+'_'
        fig=Figure(figsize=(10,7),layout='constrained');draw_eels(fig,r,component_mode=component_mode)
        for ext in ('png','svg'):fig.savefig(root/(prefix+'virtual_detector_eels.'+ext),dpi=170)
        for edge in r['maps']:
            fig=Figure(figsize=(11,5),layout='constrained');draw_maps(fig,r,edge,signal_mode=map_signal_mode)
            try:derived.update({name+'__'+edge+'__'+k:v for k,v in exported_angular(r,edge).items()})
            except (ValueError,KeyError) as exc:unavailable[name+'__'+edge]=str(exc)
            for ext in ('png','svg'):fig.savefig(root/(prefix+edge+'_angular_maps.'+ext),dpi=170)
    derived['definitions_json']=np.array(json.dumps(DEFINITIONS))
    np.savez_compressed(root/'signal_display.npz',**derived)
    (root/'figure_display.json').write_text(json.dumps(dict(component_mode=component_mode,map_signal_mode=map_signal_mode,definitions=DEFINITIONS,unavailable_paired_maps=unavailable,
        note='Display only. CSV/NPZ retain signed raw components, both relative percentages, raw reversal spectra and denominators.',
        prb='Separate raw +M difference/sum; no factor two or post-edge correction'),indent=2)+'\n',encoding='utf-8')


def export_comparison(result,root,export_single):
    methods=result.get('methods',{result.get('method','bloch'):result});labels=list(methods)
    # Preserve all historical primary arrays. Additional fields have explicit
    # method prefixes; no hidden axis changes for Stage B consumers.
    for filename,kind in (('angular_maps','maps'),('virtual_detector_eels','spectra')):
        with np.load(root/(filename+'.npz'),allow_pickle=False) as saved:arrays={k:saved[k] for k in saved.files}
        arrays['method_labels']=np.asarray(labels)
        for name,r in methods.items():
            if kind=='spectra':arrays.update({name+'__'+k:v for k,v in r['spectra'].items()})
            else:
                arrays.update({name+'__'+edge+'__'+key:v for edge,fields in r['maps'].items() for key,v in fields.items()})
                arrays[name+'__coherence']=r['coherence']
        np.savez_compressed(root/(filename+'.npz'),**arrays)
    arrays=dict(method_labels=np.asarray(labels),beam_hkl=np.asarray(result['metadata']['beam_hkl']),g=np.asarray(result['metadata']['g']),depth_nm=result['depth_nm'])
    for name,r in methods.items():
        arrays.update({name+'__amplitudes':r['amplitudes'],name+'__exit_intensity':abs(r['amplitudes'][-1])**2,name+'__depth_average_intensity':np.diag(r['coherence']).real})
    fft=result.get('fft',{})
    for key in ('beam_hkl','reciprocal_gxy','exit_intensity','total_norm','excluded_intensity','full_amplitudes','generators'):
        if key in fft:arrays['fft_full__'+key]=fft[key]
    if len(methods)==2:
        diag=complex_wave_diagnostics(methods['bloch']['amplitudes'],methods['fft-multislice']['amplitudes']);arrays.update(diag)
    np.savez_compressed(root/'diffraction_pattern.npz',**arrays)
    from .forward_results import selected_edge_metrics
    meta=dict(method_labels=labels,methods={name:dict(r['metadata'],edge_metrics=selected_edge_metrics(r)) for name,r in methods.items()},
        diagnostics=result.get('comparison',{}),array_schema='Unprefixed arrays: primary method. method__field and method__edge__field: explicit arrays; maps (qy,qx), spectra (energy), amplitudes (depth,beam). No implicit method dimension.',primary_method=result.get('method','bloch'))
    (root/'comparison_metadata.json').write_text(json.dumps(meta,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    if len(methods)>1:
        from matplotlib.figure import Figure
        from emcd_sim.gui.result_presentation import draw_comparison, draw_eels, draw_maps
        for name,r in methods.items():
            export_single(r,root/name)
            for edge in r['maps']:
                fig=Figure(figsize=(15,9),layout='constrained');draw_maps(fig,result,edge,method=name);fig.savefig(root/name/(edge+'_angular_maps.png'),dpi=145)
        fig=Figure(figsize=(15,10),layout='constrained');draw_comparison(fig,result);fig.savefig(root/'bw_ms_comparison.png',dpi=145)
        fig=Figure(figsize=(12,9),layout='constrained');draw_eels(fig,result,method='overlay');fig.savefig(root/'virtual_detector_eels.png',dpi=145)
        for edge in result['maps']:
            fig=Figure(figsize=(15,9),layout='constrained');draw_maps(fig,result,edge,method='difference');fig.savefig(root/(edge+'_bw_minus_ms.png'),dpi=145)
