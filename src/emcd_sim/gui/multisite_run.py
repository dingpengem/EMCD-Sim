"""GUI request preparation; all numerical work stays in forward_pipeline."""
from copy import deepcopy
from dataclasses import replace
import numpy as np

from ..multisite import MultiSiteIonization
from ..multisite_spectrum import ModeledEdgeWindow, prepare_multisite_spectrum
from .forward_pipeline import MultiSiteForwardSettings
from .propagation import resolve_fft_configuration


def configuration_equal(left,right,*,portable_source=False):
    """Use the existing persistence representation for unset values/containers."""
    import json
    from .project_configuration import _encode_config
    def value(cfg):
        data=_encode_config(cfg)
        data.pop('resource_allocation',None)  # A completed Run's allocation is not a scientific input change.
        # Called for already-validated group references. Moving a portable
        # attachment does not change its declared contents or parameters.
        if portable_source and data.get('source_sha256'):data['source']=''
        return json.loads(json.dumps(data,allow_nan=False))
    return value(left)==value(right)


def saved_inputs_match(result,signature):
    """Compare validated effective Local inputs; None means missing evidence."""
    from .project_configuration import _records
    state=result.get('configuration');previous=result.get('gui_multisite_input')
    if state is not None:
        old_groups=[(r['group_id'],r['element'],tuple(r['indices']),r['magnetization'],r['multiplicity'],r['mdff_reference'])
                    for r in _records(state) if r.get('enabled',True)]
    elif previous is not None:old_groups=previous[0]
    else:return None
    groups,windows,reverse,excluded,energy=signature
    old={row[0]:row for row in old_groups};new={row[0]:row for row in groups}
    if old.keys()!=new.keys():return False
    for gid,a in old.items():
        b=new[gid]
        if (a[1]!=b[1] or tuple(a[2])!=tuple(b[2]) or tuple(a[3])!=tuple(b[3]) or a[4]!=b[4]
                or not configuration_equal(a[5],b[5],portable_source=True)):return False
    meta=result['metadata'].get('multisite',{});channels=meta.get('channels')
    if channels is None or 'global_reversal' not in meta:return None
    if reverse!=meta['global_reversal']:return False
    if not np.array_equal(energy,result['spectra']['energy_ev']):return False
    current=dict(windows)
    for gid,channel in channels.items():
        if channel['omitted_by_request']!=(gid not in current):return False
        if gid in current:
            w=current[gid];e=np.asarray(energy)
            if tuple(channel['modeled_window_ev'])!=tuple(w.bounds_ev):return False
            if not np.array_equal(channel['active_energy_mask'],(e>=w.bounds_ev[0]) & (e<=w.bounds_ev[1])):return False
    participation=result['metadata'].get('ionization_participation')
    if participation is not None:
        old_excluded={(r['group_id'],r['element'],tuple(r['indices'])) for r in participation['excluded_structural_groups']}
        if old_excluded!={(gid,element,tuple(indices)) for gid,element,indices in excluded}:return False
    elif previous is not None and len(previous)>3:
        if set(previous[3])!=set(excluded):return False
    elif excluded:return None
    return True


def forward_settings(window):
    """Read shared numerical/detector controls, never the legacy MDFF or M."""
    if window.spin['grid'].value()%2 == 0:raise ValueError('Choose an odd angular / detector grid size')
    cfg = MultiSiteForwardSettings(
        fft_generators=window.saved_fft_generators(),**window.compute_resources.settings(),channeling_model=('single','double')[window.channeling_box.currentIndex()],
        **window.sampling_fields(),
        systematic_row=window.row_projection.isChecked(),
        propagation=('bloch','fft-multislice','both')[window.propagation_box.currentIndex()],
        fft_grid=window.spin['fft_grid'].value(),slice_step=window.spin['slice_step'].value(),
        grid=window.spin['grid'].value(),depth=window.spin['depth'].value(),subpixels=window.spin['subpixels'].value(),
        halfwidth=window.spin['halfwidth'].value(),centers=tuple(tuple(p) for p in window.detectors),
        radius=window.spin['radius'].value(),correction=False)
    if cfg.channeling_model == 'double' and cfg.propagation == 'both':
        raise ValueError('Multi-site Double Channeling requires a separate BW or FFT Multislice run; select one solver')
    return cfg


def applied_inputs(window, cfg):
    viewer = getattr(window,'structure_viewer',None)
    if viewer is None:raise ValueError('Open the 3D viewer and configure site groups before running Local mode')
    viewer.set_structure(window.structure)
    editor = viewer.editor
    if editor.dirty:raise ValueError('Apply or Cancel pending site-group/magnetization edits in the 3D viewer before Run')
    if not editor.rows():raise ValueError('Local mode has no applied site groups; configure groups and MDFF providers')
    for name,dialog in editor.mdff_dialogs.items():
        if name not in editor.excluded_groups and dialog.has_unapplied_edits():raise ValueError('Apply or Cancel pending MDFF edits for '+name+', then Apply site groups')
    sites = editor.validated_site_groups
    if sites is None:raise ValueError('Every ionizing group needs a configured and validated MDFF provider; no Global M fallback is used')
    sites.validate_structure(window.structure)
    # Work only on copied references: an open editor cannot alter the worker's inputs.
    sites = MultiSiteIonization(window.structure,[replace(g,mdff_reference=deepcopy(g.mdff_reference)) for g in sites.groups])
    from ..mdff_providers import load_site_group_provider
    windows = {};selections = []
    requested=getattr(editor,'requested_energy_ev',None)
    from .provider_preparation import sampling_mode
    mode=sampling_mode(cfg)
    if requested is not None and (getattr(editor,'_restored_energy_sampling',mode)!=mode or
            mode=='uniform' and getattr(editor,'_restored_uniform_points',cfg.energy_points)!=cfg.energy_points):requested=None
    for group in sites.groups:
        if group.group_id in getattr(editor,'omitted_site_groups',set()):continue
        source = load_site_group_provider(group)
        declared = editor.energy_windows.get(group.group_id)
        bounds = declared.bounds_ev if declared is not None else tuple(source.energy_ev[[0,-1]])
        selected = [(key,float(value)) for key,value in source.metadata['selected_ev'].items() if bounds[0]<=value<=bounds[1]]
        if requested is not None:selected=[(key,value) for key,value in selected if np.any(np.isclose(requested,value,rtol=0,atol=1e-9))]
        if mode == 'edges':
            if not selected:raise ValueError('No selected core-edge energies in the modeled window for '+group.group_id+'; use Full spectrum or edit its window')
            samples = [value for _,value in selected]
        elif requested is not None:
            samples=np.asarray(requested)[(np.asarray(requested)>=bounds[0])&(np.asarray(requested)<=bounds[1])]
        elif mode=='uniform':
            samples=np.linspace(*bounds,cfg.energy_points)
        elif mode=='native':
            samples = (declared.energy_ev if getattr(editor,'_restored_energy_sampling',None)=='native'
                       and not getattr(editor,'_sampling_user_override',False)
                       and declared is not None and declared.energy_ev is not None
                       else source.energy_ev[(source.energy_ev>=bounds[0]) & (source.energy_ev<=bounds[1])])
        else:raise ValueError('Unknown energy sampling')
        if mode!='edges':
            # Exact source selections are needed by the existing angular-map controls.
            samples = np.r_[samples,[value for _,value in selected]]
        samples = tuple(np.unique(samples))
        windows[group.group_id] = ModeledEdgeWindow(bounds,samples)
        selections.extend((group.group_id+':'+key,value) for key,value in selected)
    plan = prepare_multisite_spectrum(sites,energy_ev=requested,energy_windows=windows)
    if plan['energy_ev'][-1] >= 1000*window.settings().voltage:raise ValueError('Require energy losses below incident energy')
    if not selections:selections=[(f'E={loss:g}eV',float(loss)) for loss in np.unique(plan['energy_ev'][[0,-1]])]
    cfg = replace(cfg,energy_points=len(plan['energy_ev']),selected_edges=tuple(selections))
    cfg = resolve_fft_configuration(window.structure,window.settings(),cfg)
    signature = (tuple((g.group_id,g.element,g.indices,g.magnetization,g.multiplicity,g.mdff_reference) for g in sites.groups),
                 tuple(windows.items()),editor.reverse_magnetization,
                 tuple((r[0],r[1],r[2]) for r in editor.rows() if r[0] in editor.excluded_groups),tuple(plan['energy_ev']))
    return cfg,sites,windows,editor.reverse_magnetization,signature
