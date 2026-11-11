"""Qt result views and reusable plotting of completed immutable run geometry."""
import numpy as np
from matplotlib.figure import Figure
from matplotlib import colormaps
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from .responsive import ResponsiveCanvas as FigureCanvasQTAgg
from PySide6 import QtWidgets,QtCore
from ..emcd_angular_plots import decorate_reciprocal_map
from .emcd_forward import metrics
from .signal_normalization import DisplaySettings, normalized_spectra, angular_display, percentage_metrics
from .normalization_controls import NormalizationControls
from ..mdff_edges import selected_samples


def mdff_label(result):
    if result['config'].model=='multisite':
        from .multisite_results import description
        return description(result)
    if result['config'].model=='imported' or hasattr(result['config'],'provider_schema'):
        if result['metadata'].get('imported_mdff',{}).get('atomic_model'):
            return result['metadata'].get('scientific_status','RESEARCH / APPROXIMATE')+'; approximate atomic '+result['config'].ionizing_element+' 2p-3d model; physically unvalidated parameters'
        kind='XMCD-effective approximation' if result['config'].model=='xmcd' else 'imported dipole tensor'
        return result['metadata'].get('scientific_status','RESEARCH / APPROXIMATE')+'; '+result['config'].ionizing_element+' '+result['config'].core_edge+' '+kind
    return 'XMCD-effective, native axis' if result['config'].model=='xmcd' else 'Atomic 2p-3d approximation, non-DFT, not quantitatively calibrated'


def geometry_description(result):
    """Describe the saved basis explicitly; Bragg alignment is not isolation."""
    settings=result['settings'];cfg=result['config']
    support=('explicit ideal 000 + target two-beam basis' if settings.basis_mode=='two-beam' else
        'systematic-row-restricted basis' if cfg.systematic_row else 'full finite ZOLZ basis')
    return (f'Nominal ZA {list(settings.zone)}; tilt ({settings.tilt[0]:.4f}, '
            f'{settings.tilt[1]:.4f}) mrad; {support}')


def spectral_coverage_label(result):
    if result['config'].model=='multisite':return 'Modeled partial core-edge spectrum'
    e=result['spectra']['energy_ev']
    if result['config'].energy_scope=='edges':return 'Selected '+ '/'.join(k for k,_ in selected_samples(result['config']))+' samples'
    audit=result['metadata'].get('source_audit') or {}
    bounds=audit.get('bounds')
    if result['config'].model=='imported':bounds=result['metadata'].get('imported_mdff',{}).get('energy_bounds_ev')
    if bounds is not None and not np.allclose(e[[0,-1]],bounds,rtol=0,atol=1e-9):return 'Calculated energy subset'
    return 'Full spectrum'


def draw_maps(fig,result,edge,method=None,field=None,display=None,*,signal_mode='raw',group_id=None,normalization='weighted'):
    if display is None and field is None:return draw_component_maps(fig,result,edge,method,signal_mode,group_id,normalization)
    display=display or DisplaySettings()
    original=result
    all_results=list(result.get('methods',{}).values()) or [result]
    method=method or result.get('method','bloch')
    result=method_result(result,method)
    fig.clear();maps=result['maps'][edge];cfg=result['config'];settings=result['settings']
    keys=('I_mag','I_nonmag','I_plus','D_raw','D_corrected','D_nonmag_residual')
    titles=('Magnetic odd intensity','Reversal-even intensity','Total +M intensity','Raw paired A-B','Post-edge corrected A-B','Residual even contrast')
    dq=result['qx'][0,1]-result['qx'][0,0];h=cfg.halfwidth+dq/2;extent=(-h,h,-h,h)
    # Shared absolute signed scales across both edges for each comparable field.
    if field is not None:
        title=dict(zip(keys,titles)).get(field,field);keys=(field,);titles=(title,)
    if display.map_mode=='local' and field is None:keys=('I_mag',);titles=('Local magnetic fraction',)
    elif display.map_mode=='paired' and field is None:
        keys=('D_mag','D_nonmag','D_raw','D_corrected','D_mag_processed','D_nonmag_residual');titles=('Magnetic-only paired asymmetry','Nonmagnetic paired asymmetry','Raw paired asymmetry','Corrected paired asymmetry','Processed magnetic asymmetry','Residual even asymmetry')
    axes=np.asarray(fig.subplots(2,3) if len(keys)>1 else [fig.subplots()])
    display_meta=[]
    for ax,key,title in zip(axes.flat,keys,titles):
        if key not in maps:
            ax.text(.5,.5,'Unavailable\n'+(result['metadata']['pair_reason'] if key=='D_raw' or 'Mirrored maps disabled' in result['metadata']['pair_reason'] else result['metadata']['correction_reason']),ha='center',va='center',wrap=True,transform=ax.transAxes,fontsize=8)
            ax.set_title(title,fontsize=9);ax.set_axis_off();continue
        try:
            def transformed(r):return angular_display(r,edge,key,display.map_mode)
            if method=='difference':
                bv,bmeta=transformed(original['methods']['bloch']);mv,_=transformed(original['methods']['fft-multislice']);value=bv-mv;meta=dict(bmeta,difference='BW-MS of displayed quantities; raw solver diagnostics unchanged')
            else:value,meta=transformed(result)
            pools=[transformed(r)[0] for r in (all_results if display.shared_scale and method!='difference' else [result])] if method!='difference' else [value]
            finite=np.concatenate([abs(v[np.isfinite(v)]) for v in pools]);vmax=max(float(finite.max()) if finite.size else 0.,1e-30)
        except ValueError as exc:
            ax.text(.5,.5,str(exc),ha='center',va='center',wrap=True,transform=ax.transAxes,fontsize=8);ax.set_axis_off();continue
        signed=display.map_mode!='raw' or method=='difference' or key not in ('I_nonmag','I_plus')
        cmap=colormaps['RdBu_r' if signed else 'viridis'].with_extremes(bad='#c8c8c8')
        im=ax.imshow(value,origin='lower',extent=extent,cmap=cmap,vmin=-vmax if signed else 0,vmax=vmax)
        display_meta.append(dict(field=key,**meta))
        if not np.isfinite(value).any():ax.text(.5,.5,'All pixels undefined / masked',ha='center',transform=ax.transAxes,fontsize=8)
        decorate_reciprocal_map(ax,result['model'],extent,target_hkl=settings.target,zone_axis=settings.zone)
        target=result['model'].elastic.crystal.g_vector(settings.target)[:2]
        ax.plot(*target,'s',mfc='none',mec='crimson',ms=8,mew=1)
        ax.set_title(title,fontsize=9);bar=fig.colorbar(im,ax=ax,shrink=.7,pad=.02);bar.set_label(meta['units'],fontsize=7);bar.ax.tick_params(labelsize=7)
    e=dict(selected_samples(cfg))[edge]
    solver_label='BW-MS numerical solver difference' if method=='difference' else method+' '+cfg.channeling_model.title()+' Channeling'
    fig.suptitle(f'{edge}: {e:.3f} eV | {solver_label} | '+('Relative intensity (a.u.)' if display.map_mode=='raw' else ('Local magnetic fraction (%)' if display.map_mode=='local' else 'Paired angular asymmetry (%)'))+f'\n'+mdff_label(result),fontsize=11)

    fig._emcd_display_metadata=dict(kind='angular',map_mode=display.map_mode,fields=display_meta,shared_color_scale=display.shared_scale,masked_color='#c8c8c8',note='No integrated-peak scaling of angular densities.')


def method_result(result,method):
    methods=result.get('methods',{result.get('method','bloch'):result})
    if method!='difference':return methods[method]
    b,m=[methods[k] for k in ('bloch','fft-multislice')]
    maps={edge:{k:b['maps'][edge][k]-m['maps'][edge][k] for k in b['maps'][edge] if k in m['maps'][edge]} for edge in b['maps'] if edge in m['maps']}
    metadata=dict(b['metadata'],pair_reason='BW-MS paired maps require validated physical pairing in both methods.',
        correction_reason='BW-MS corrected maps require valid correction in both methods. '+b['metadata']['correction_reason']+' / '+m['metadata']['correction_reason'])
    return dict(b,maps=maps,method='difference',metadata=metadata)


def _draw_eels_diagnostics(fig,result,zoom='Full spectrum',method=None,display=None,zoom_energy=None):
    display=display or DisplaySettings()
    fig.clear();cfg=result['config'];axes=fig.subplots(3,1,sharex=True)
    methods=result.get('methods',{result.get('method','bloch'):result});method=method or result.get('method','bloch')
    chosen=methods if method=='overlay' else {method:methods[method]}
    entries=[(name,methods[name],name) for name in sorted(methods,key=lambda n:n!='bloch')]
    normalized=normalized_spectra(entries,display,zoom);lookup={name:item for (name,_,_),item in zip(entries,normalized)}
    units=next(iter(lookup.values()))[1]['units']
    panels=[(('I_A_plus','A +M'),('I_B_plus','B +M'),('I_A_minus','A -M'),('I_B_minus','B -M'),('Sigma_ref','Even N_A+N_B reference')),
            (('D_mag','Magnetic odd A-B'),('D_nonmag','Reversal-even A-B')),
            (('D_raw','Raw A-B'),('D_corrected','Corrected A-B'),('D_mag','Intrinsic magnetic'),('D_nonmag_residual_obs','Residual even'),('magnetic_bias','Correction magnetic bias'),('D_mag_processed_obs','Processed magnetic'))]
    legends=[]
    for ax,curves in zip(axes,panels):
        lines=[]
        for name,r in chosen.items():
            s,meta=lookup[name];e=r['spectra']['energy_ev']
            for i,(key,label) in enumerate(curves):
                if key in s:lines.extend(ax.plot(e,s[key],label=name+': '+label,lw=1.1,ls='None' if len(e)==2 else ('--' if name=='fft-multislice' else '-'),marker='o' if len(e)==2 else None,color='C'+str(i)))
        for energy in dict.fromkeys(value for _,value in selected_samples(cfg) if np.isfinite(value)):ax.axvline(energy,color='.5',ls=':',lw=.7)
        if any(r['metadata']['alpha'] is not None for r in chosen.values()):ax.axvspan(*cfg.window,color='gold',alpha=.2)
        ax.axhline(0,color='.7',lw=.5);ax.set_ylabel(units,fontsize=8);ax.grid(alpha=.15)
        if ax is not axes[0]:
            limits=ax.get_ylim();limit=max(abs(limits[0]),abs(limits[1]));ax.set_ylim(-limit,limit)
        legend=ax.legend(fontsize=7,ncols=2,loc='upper right')
        for proxy,line in zip(legend.get_lines(),lines):proxy.set_picker(5);legends.append((proxy,line))
    axes[-1].set_xlabel('Declared imported energy loss (eV)' if cfg.model=='imported' else ('Native energy loss (eV)' if cfg.model=='xmcd' else 'Atomic model energy loss (eV)'))
    selected=zoom_energy if zoom_energy is not None else dict(selected_samples(cfg)).get(zoom.removesuffix(' zoom')) if zoom.endswith(' zoom') else None
    axes[-1].set_xlim((e[0],e[-1]) if selected is None else (selected-5,selected+5))
    factors=', '.join(name+' alpha='+('%.9g'%r['metadata']['alpha'] if r['metadata']['alpha'] is not None else 'disabled') for name,r in chosen.items())
    note='; '.join(dict.fromkeys(meta.get('warning','') for _,meta in normalized if meta.get('warning')))
    fig.suptitle(cfg.channeling_model.title()+' Channeling | '+units+' | '+factors+'\n'+('Selected declared samples only; full EELS not calculated.' if cfg.energy_scope=='edges' else (note or 'Common reference; corrected = processed magnetic + residual even; solid BW / dashed MS')),fontsize=10)
    if cfg.model=='imported':fig.suptitle(fig._suptitle.get_text()+'\n'+mdff_label(result),fontsize=10)
    fig._emcd_display_metadata=dict(kind='spectra',normalization=[meta for _,meta in normalized],zoom=zoom)
    return legends


def draw_eels(fig,result,zoom='Full spectrum',method=None,display=None,*,component_mode='raw',diagnostics=False,selection=('total',None),normalization='weighted',compared=(),quantity=0,include_total=False,zoom_energy=None):
    """Two primary panels; legacy normalization is an explicit diagnostic."""
    if diagnostics or display is not None:return _draw_eels_diagnostics(fig,result,zoom,method,display,zoom_energy)
    from .component_display import components,readouts
    cfg=result['config'];multisite=cfg.model=='multisite'
    from .multisite_results import spectral_series,covered_segments,QUANTITIES,selection_description
    fields=QUANTITIES[quantity][1] if multisite and quantity else None
    fig.clear();axes=np.atleast_1d(fig.subplots(1 if fields else 2,1,sharex=True));legends=[];records=[];targets={}
    methods=result.get('methods',{result.get('method','bloch'):result});method=method or result.get('method','bloch')
    chosen=methods if method=='overlay' else {method:methods[method]}
    for name,r in chosen.items():
        s=r['spectra'];e=s['energy_ev'];points=cfg.energy_scope=='edges' or len(e)<=2
        style=dict(ls='None' if points else ('--' if name=='fft-multislice' else '-'),marker='o' if points else None,lw=1.3)
        series=spectral_series(r,selection,normalization,compared,include_total) if multisite else [dict(spectra=s,label='',groups=())]
        for index,item in enumerate(series):
            s=item['spectra'];prefix=(name+': ' if len(chosen)>1 else '')+(item['label']+' | ' if len(series)>1 else '')
            segments=covered_segments(r,e,item['groups']) if multisite else [np.ones(len(e),bool)]
            def plot(ax,value,label,color,linestyle='-'):
                drawn=False;segments_drawn=[]
                for mask in segments:
                    if not np.any(mask):continue
                    line_style=dict(style)
                    if len(series)>1:line_style.update(ls='None' if points else linestyle)
                    segments_drawn.extend(ax.plot(e[mask],np.asarray(value)[mask],label=prefix+label if not drawn else None,color=color,**line_style));drawn=True
                if segments_drawn:targets.setdefault(ax,[]).append(tuple(segments_drawn))
            for i,(key,label) in enumerate(fields or [('I_A_plus','Detector A'),('I_B_plus','Detector B')]):
                plot(axes[0],s[key],label,'C'+str(index%10) if len(series)>1 else 'C'+str(i),('-','--',':','-.')[i%4])
            curves,meta=components(s,component_mode)
            if not fields:
                for i,(label,v) in enumerate(curves.items()):
                    color='C'+str(index%10) if len(series)>1 else {'Magnetic':'C3','Nonmagnetic':'C0','EMCD Asymmetry':'C2'}[label]
                    shown=({'Magnetic':'Magnetic-only Asymmetry','Nonmagnetic':'Nonmagnetic Asymmetry'}[label] if component_mode=='relative' else label)
                    plot(axes[1],v,shown,color,('-','--')[i%2])
        rows=[] if multisite else readouts(r)[0]
        records.append(dict(method=name,channeling_model=cfg.channeling_model,**(meta if series else {}),prb_readouts=rows))
    axes[0].set_ylabel('EELS intensity (a.u.)' if not fields else 'Intensity (a.u.)')
    if not fields:axes[1].set_ylabel('Intensity difference (a.u.)' if component_mode=='raw' else 'EMCD Asymmetry (%)' if component_mode=='asymmetry' else 'Magnetic-only / Nonmagnetic Asymmetry (%)');axes[1].axhline(0,color='.45',lw=.7)
    axes[-1].set_xlabel('Energy loss (eV)')
    samples=[(label,float(value)) for label,value in selected_samples(cfg) if np.isfinite(value)]
    for ax in axes:
        ax.grid(alpha=.15)
        if ax.get_legend_handles_labels()[0]:
            legend=ax.legend(fontsize=8,loc='upper right')
            for proxy,text,lines in zip(legend.get_lines(),legend.get_texts(),targets[ax]):
                proxy.set_picker(5);text.set_picker(True)
                legends.extend(((proxy,lines),(text,lines)))
        else:ax.text(.5,.5,'No modeled samples for this selection; excluded/unmodeled is not physical zero.',ha='center',va='center',wrap=True,transform=ax.transAxes,fontsize=8)
        if not fields:
            for v in dict.fromkeys(v for _,v in samples):ax.axvline(v,color='.6',ls=':',lw=.6)
    selected=zoom_energy if zoom_energy is not None else dict(samples).get(zoom.removesuffix(' zoom')) if zoom.endswith(' zoom') else None
    limits=(selected-5,selected+5) if selected is not None else (float(e[0]),float(e[-1]))
    if len(e)==1:limits=result['metadata'].get('imported_mdff',{}).get('energy_bounds_ev',(float(e[0])-1,float(e[0])+1))
    axes[-1].set_xlim(limits)
    from .component_display import MODES
    from .multisite_results import ionizing_label
    element=ionizing_label(result)
    title=f'{MODES.get(component_mode, "Magnetic-only / Nonmagnetic Asymmetry diagnostics")} | {cfg.channeling_model.title()} Channeling | {method} | {element} {list(result["settings"].zone)}, {result["settings"].thickness:g} nm'
    if cfg.energy_scope=='edges':title+='\nSelected native '+ '/'.join(k for k,_ in selected_samples(cfg))+' samples only; full EELS spectrum not calculated'
    elif spectral_coverage_label(result)=='Calculated energy subset':title+='\nCalculated energy subset; full native range not covered'
    title+='\n'+geometry_description(result)
    title+='\n'+zoom+'; actual calculated energy samples'
    if multisite:title+='\n'+selection_description(result,spectral_series(result,selection,normalization,compared,include_total))
    if cfg.model=='imported' or hasattr(cfg,'provider_schema'):title+='\n'+mdff_label(result)
    fig.suptitle(title,fontsize=11)
    fig._emcd_display_metadata=dict(kind='primary spectra',component_mode=component_mode,records=records,
        eels='Original +M detector A/B intensities, shared arbitrary-unit scale; no background or peak scaling',
        spectral_coverage='selected samples only' if points else spectral_coverage_label(result),
        geometry=geometry_description(result),
        prb='Separate raw +M difference/sum scalar benchmark; not the magnetic-only percentage')
    if multisite:fig._emcd_display_metadata.update(selection=selection,quantity=QUANTITIES[quantity][0],normalization=normalization,selected_atom_count=result['metadata']['multisite']['selected_atom_count'])
    return legends


def draw_component_maps(fig,result,edge,method=None,signal_mode='raw',group_id=None,normalization='weighted'):
    from .component_display import primary_angular,MODES
    fig.clear();method=method or result.get('method','bloch')
    originals=result.get('methods',{result.get('method','bloch'):result})
    try:
        from .multisite_results import angular_group_view
        methods={name:angular_group_view(value,group_id,normalization) if group_id is not None else value for name,value in originals.items()}
        r=methods.get(method,next(iter(methods.values())))
        values,meta=primary_angular(r,edge,signal_mode)
        if method=='difference':
            bv,_=primary_angular(methods['bloch'],edge,signal_mode);mv,_=primary_angular(methods['fft-multislice'],edge,signal_mode)
            values={k:bv[k]-mv[k] for k in bv};meta=dict(meta,units='BW-MS difference ('+('a.u.' if signal_mode=='raw' else 'percentage points')+')')
        scale_views=list(methods.values())
        if group_id is not None:
            scale_views=[]
            for original in originals.values():
                for gid in original['groups']:
                    try:scale_views.append(angular_group_view(original,gid,normalization))
                    except ValueError:continue
        pools=[v for m in scale_views for ed in m['maps'] for v in primary_angular(m,ed,signal_mode)[0].values()]
        if method=='difference':pools=list(values.values())
    except (ValueError,KeyError) as exc:
        fig.subplots().text(.05,.5,'Paired angular display unavailable: '+str(exc),wrap=True)
        fig._emcd_display_metadata=dict(unavailable=str(exc),derived_visualization_only=True)
        return
    limit=max([float(abs(v[np.isfinite(v)]).max()) for v in pools if np.isfinite(v).any()]+[1e-30])
    axes=np.atleast_1d(fig.subplots(1,len(values)));qx,qy=r['qx'],r['qy']
    dx=qx[0,1]-qx[0,0];dy=qy[1,0]-qy[0,0]
    extent=(qx[0,0]-dx/2,qx[0,-1]+dx/2,qy[0,0]-dy/2,qy[-1,0]+dy/2)
    for ax,(label,v) in zip(axes,values.items()):
        im=ax.imshow(v,origin='lower',extent=extent,interpolation='nearest',aspect='equal',cmap=colormaps['RdBu_r'].with_extremes(bad='#c8c8c8'),vmin=-limit,vmax=limit)
        decorate_reciprocal_map(ax,r['model'],extent,target_hkl=r['settings'].target,zone_axis=r['settings'].zone)
        beam_labels={str(hkl) for hkl in getattr(getattr(r['model'].elastic,'beams',None),'hkl',())}
        for text in ax.texts:
            if text.get_text() in beam_labels:text.set_gid('beam-index-label')
        ax.plot(*r['model'].elastic.crystal.g_vector(r['settings'].target)[:2],'s',mfc='none',mec='crimson',ms=8)
        ax.set_title(label,fontsize=10)
        units='a.u.' if signal_mode=='raw' and method!='difference' else meta['units']
        fig.colorbar(im,ax=ax,shrink=.7).set_label(units)
        if not np.isfinite(v).any():ax.text(.1,.5,'All pixels undefined / masked',transform=ax.transAxes)
    from .multisite_results import energy_sample_index,total_energy_samples
    sample_index=energy_sample_index(r,dict(selected_samples(r['config']))[edge]);e=float(r['spectra']['energy_ev'][sample_index])
    sample=next(item for item in total_energy_samples(r) if item['index']==sample_index)
    sampling=f'Angular Grid: {qx.shape[1]} x {qx.shape[0]}; q spacing: {dx:.6g}, {dy:.6g} Å⁻¹'
    scope=('Group Mean: ' if normalization=='mean' else 'Group Contribution: ')+group_id if group_id is not None else ('Total Results' if r['config'].model=='multisite' else '')
    energy_label=sample['label'] if group_id is None else f'{edge} {e:.4f} eV'
    fig.suptitle(f'{MODES[signal_mode]} | {r["config"].channeling_model.title()} Channeling | {method} | '+(scope+' | ' if scope else '')+energy_label+'\n'+geometry_description(r)+'\nFull-field mirrored-point EMCD; not detector-integrated asymmetry\n'+sampling,fontsize=10)
    if r['config'].model=='imported':fig.suptitle(fig._suptitle.get_text()+'\n'+mdff_label(r),fontsize=10)
    fig._emcd_display_metadata=dict(kind='primary angular components',edge=edge,method=method,**meta,shared_color_scale=True,
        angular_grid_shape=list(qx.shape),q_spacing_inv_angstrom=[float(dx),float(dy)],display_interpolation='nearest',
        energy_ev=e,sample_index=sample_index,sample_aliases=sample['keys'])
    if r['config'].model=='multisite':fig._emcd_display_metadata.update(scope=scope,energy_ev=e,
        group_id=group_id,normalization=normalization if group_id is not None else 'total_mean_per_selected_atom',
        selected_atom_count=r['metadata']['multisite']['selected_atom_count'],
        group=r.get('angular_selection'),global_reversal=r['metadata']['multisite']['global_reversal'])


def draw_diffraction(fig,result,method=None,depth_average=False):
    fig.clear();method=method or result.get('method','bloch');methods=result.get('methods',{result.get('method','bloch'):result})
    intensity=lambda r:np.diag(r['coherence']).real if depth_average else abs(r['amplitudes'][-1])**2
    value=intensity(methods['bloch'])-intensity(methods['fft-multislice']) if method=='difference' else intensity(methods[method])
    ax=fig.subplots();g=np.asarray(result['metadata']['g']);cfg=result['config'];limit=result['settings'].beam_cutoff+.2
    vmax=max(float(max(intensity(r))) for r in methods.values());signed=method=='difference'
    if signed:vmax=max(float(abs(value).max()),1e-30)
    scatter=ax.scatter(g[:,0],g[:,1],s=25+500*abs(value)/max(float(abs(value).max()),1e-30),c=value,cmap='RdBu_r' if signed else 'viridis',vmin=-vmax if signed else 0,vmax=vmax)
    decorate_reciprocal_map(ax,result['model'],(-limit,limit,-limit,limit),target_hkl=result['settings'].target,zone_axis=result['settings'].zone)
    ax.plot(*result['model'].elastic.crystal.g_vector(result['settings'].target)[:2],'s',mfc='none',mec='crimson',ms=8)
    ax.set_title(result['config'].channeling_model.title()+' Channeling | '+method+' | incoming '+('depth average diag(C)' if depth_average else 'exit elastic intensity')+'\nExact common hkl basis; excluded FFT intensity reported separately; spot area is visualization only')
    fig.colorbar(scatter,ax=ax,shrink=.8)


def draw_comparison(fig,result,display=None):
    if not result['maps']:
        draw_eels(fig,result,method='overlay')
        fig.suptitle(fig._suptitle.get_text()+'\nBW/MS spectra; incoming coherence diagnostics are reported separately',fontsize=10)
        return
    display=display or DisplaySettings()
    fig.clear()
    if fig.get_layout_engine() is None:fig.set_layout_engine('constrained')
    fig.get_layout_engine().set(w_pad=.06,h_pad=.08,hspace=.14,wspace=.06)
    methods=result.get('methods',{});axes=fig.subplots(2,3)
    if len(methods)!=2:
        for ax in axes.flat:ax.set_axis_off()
        axes[0,0].text(0,0,'Select Both to compare independent propagators');return
    b,m=[methods[k] for k in ('bloch','fft-multislice')];cfg=result['config'];h=cfg.halfwidth;extent=(-h,h,-h,h)
    map_mode=display.map_mode
    if map_mode=='paired':raise ValueError('Overview shows intrinsic I_mag. Use Angular Maps for paired detector percentages.')
    edge=next(iter(b['maps']))
    values=[angular_display(r,edge,'I_mag',map_mode)[0] for r in (b,m)]
    finite_limit=lambda v:max(float(np.max(abs(v[np.isfinite(v)]))) if np.isfinite(v).any() else 0.,1e-30)
    scale=max(finite_limit(v) for v in values)
    normalized=normalized_spectra([(name,r,name) for name,r in methods.items()],display);lookup={name:item for name,item in zip(methods,normalized)}
    for ax,v,title in zip(axes[0],values+[values[0]-values[1]],['BW '+edge+' magnetic odd','FFT MS '+edge+' magnetic odd','BW-MS numerical solver difference']):
        limit=finite_limit(v) if 'difference' in title else scale
        im=ax.imshow(v,origin='lower',extent=extent,cmap=colormaps['RdBu_r'].with_extremes(bad='#c8c8c8'),vmin=-limit,vmax=limit)
        decorate_reciprocal_map(ax,result['model'],extent,target_hkl=result['settings'].target,zone_axis=result['settings'].zone)
        ax.plot(*result['model'].elastic.crystal.g_vector(result['settings'].target)[:2],'s',mfc='none',mec='crimson',ms=8)
        ax.set_title(title+' | '+('a.u.' if map_mode=='raw' else 'local %'),fontsize=9);fig.colorbar(im,ax=ax,shrink=.65).set_label('Relative intensity (a.u.)' if map_mode=='raw' else 'Local magnetic fraction (%)',fontsize=7)
    for ax,key,title in zip(axes[1],('I_A_plus','D_mag','D_raw'),('Full detector A +M EELS','Intrinsic magnetic A-B','Raw / corrected A-B')):
        for name,r in methods.items():
            s,meta=lookup[name];points=len(r['spectra']['energy_ev'])==2
            ax.plot(r['spectra']['energy_ev'],s[key],ls='None' if points else ('-' if name=='bloch' else '--'),marker='o' if points else None,label=name,lw=1.1)
            if key=='D_raw' and 'D_corrected' in s:ax.plot(r['spectra']['energy_ev'],s['D_corrected'],ls='None' if points else (':' if name=='bloch' else '-.'),marker='x' if points else None,label=name+' corrected',lw=1)
        ax.set(title=title,xlabel='Energy loss (eV)',ylabel=next(iter(lookup.values()))[1]['units']);ax.legend(fontsize=7);ax.grid(alpha=.15)
    fig._emcd_display_metadata=dict(kind='BW/MS comparison',spectra=[meta for _,meta in normalized],map_mode=map_mode,solver_errors='Original raw arrays; never independently peak-normalized')
    diag=result['comparison'];fig.suptitle('Independent BW / FFT MS | '+cfg.model+' | '+str(result['settings'].zone)+', '+str(result['settings'].thickness)+' nm\nCoherence relative error %.3g; FFT norm error %.3g. Fixed potential cutoff: agreement is not physical convergence.'%(diag['coherence']['l2_relative'],diag['fft']['norm_error']),fontsize=11)
    fig.suptitle(cfg.channeling_model.title()+' Channeling | '+fig._suptitle.get_text()+'\n'+normalized[0][1]['units']+' | reference '+normalized[0][1]['reference_run']+' '+normalized[0][1]['reference_method'],fontsize=10)
    if cfg.model=='imported':fig.suptitle(fig._suptitle.get_text()+'\n'+mdff_label(result),fontsize=10)


from .responsive import FlowLayout, CollapsibleSection, FigurePresentation


class ResultsView(QtWidgets.QWidget):
    def __init__(self,parent,kind):
        super().__init__();self.owner=parent;self.kind=kind;self.result=None;self.proxies=[]
        outer=QtWidgets.QVBoxLayout(self);outer.setContentsMargins(0,0,0,0)
        self.scroll=QtWidgets.QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        content=QtWidgets.QWidget();self.scroll.setWidget(content);outer.addWidget(self.scroll)
        layout=QtWidgets.QVBoxLayout(content);self.label=QtWidgets.QLabel('No completed EMCD calculation.');self.label.setWordWrap(True);layout.addWidget(self.label)
        row=FlowLayout();layout.addLayout(row)
        if kind=='maps':
            self.map_scope=QtWidgets.QComboBox();self.map_scope.setAccessibleName('Angular result scope')
            for title,key in [('Total Results','total'),('Group Contribution (n/N)','weighted'),('Group Mean (per atom)','mean')]:self.map_scope.addItem(title,key)
            self.map_scope.hide();row.addWidget(self.map_scope);self.map_scope.currentIndexChanged.connect(self.update_map_choices)
        self.choice=QtWidgets.QComboBox();self.choice.addItems([] if kind=='maps' else (['Exit intensity','Depth average'] if kind=='diffraction' else ['Full spectrum']));row.addWidget(self.choice)
        if kind=='maps':
            self.choice.setAccessibleName('Angular group / energy')
            for box in (self.map_scope,self.choice):
                box.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);box.setMinimumContentsLength(16)
        self.method=QtWidgets.QComboBox();row.addWidget(self.method);self.method.currentIndexChanged.connect(self.update_map_choices if kind=='maps' else self.redraw)
        self.choice.setVisible(kind!='comparison');self.method.setVisible(kind!='comparison')
        self.field=QtWidgets.QComboBox();self.field.addItem('All six fields',None)
        for title,key in [('Magnetic odd','I_mag'),('Magnetic paired','D_mag'),('Nonmagnetic paired','D_nonmag'),('Nonmagnetic even','I_nonmag'),('Total +M','I_plus'),('Raw paired A-B','D_raw'),('Corrected paired A-B','D_corrected'),('Residual even','D_nonmag_residual')]:self.field.addItem(title,key)
        self.field.setVisible(kind=='maps');self.field.currentTextChanged.connect(self.redraw)
        self.component_mode=QtWidgets.QComboBox()
        from .component_display import MODES
        for key,title in MODES.items():self.component_mode.addItem(title,key)
        self.signal_label=QtWidgets.QLabel('Signal Display');self.signal_label.setVisible(kind in ('eels','maps'));row.addWidget(self.signal_label)
        self.component_mode.setVisible(kind in ('eels','maps'));row.addWidget(self.component_mode);self.component_mode.currentIndexChanged.connect(self.redraw)
        maximize=QtWidgets.QPushButton('Maximize / restore results');row.addWidget(maximize);maximize.clicked.connect(self.maximize)
        if kind=='eels':
            from .multisite_results_controls import MultisiteSpectraControls
            self.multisite_controls=MultisiteSpectraControls();self.multisite_controls.hide()
            layout.addWidget(self.multisite_controls);self.multisite_controls.changed.connect(self.redraw)
        self.advanced=QtWidgets.QGroupBox('Advanced Diagnostics — legacy displays');self.advanced.setCheckable(True);self.advanced.setChecked(False);layout.addWidget(self.advanced)
        self.advanced_body=QtWidgets.QWidget();outer=QtWidgets.QVBoxLayout(self.advanced);outer.addWidget(self.advanced_body);self.advanced_body.hide();advanced_layout=QtWidgets.QVBoxLayout(self.advanced_body)
        self.advanced.toggled.connect(self.advanced_body.setVisible);self.advanced.toggled.connect(self.redraw);self.advanced.setVisible(kind!='diffraction')
        self.normalization=NormalizationControls(self,maps=kind=='maps');self.normalization.setVisible(kind!='diffraction');advanced_layout.addWidget(self.normalization);self.normalization.changed.connect(self.redraw)
        advanced_layout.addWidget(self.field)
        self.component_diagnostic=QtWidgets.QComboBox();self.component_diagnostic.addItem('Legacy diagnostics','legacy');self.component_diagnostic.addItem('Magnetic-only / Nonmagnetic Asymmetry (%)','relative');self.component_diagnostic.setToolTip('Magnetic-reversal-odd detector difference, normalized by reversal-even intensity.');self.component_diagnostic.setVisible(kind=='eels');advanced_layout.addWidget(self.component_diagnostic);self.component_diagnostic.currentIndexChanged.connect(self.redraw)
        self.display_note=QtWidgets.QLabel();self.display_note.setWordWrap(True);layout.addWidget(self.display_note)
        if kind=='eels':
            from .prb_controls import PRBBenchmarkControls
            self.prb_benchmark=PRBBenchmarkControls(self);self.benchmark_section=CollapsibleSection('PRB benchmark controls',self.prb_benchmark,expanded=False);self.benchmark_section.setObjectName('benchmark_panel');layout.addWidget(self.benchmark_section)
            self.prb_readout=self.prb_benchmark.summary
            self.prb_benchmark.changed.connect(self.update_prb_metadata)
        export=QtWidgets.QPushButton('Export derived NPZ/CSV + metadata');export.setVisible(kind!='diffraction');layout.addWidget(export);export.clicked.connect(self.export_derived)
        self.export_button=export
        self.figure=Figure(layout='constrained');self.canvas=FigureCanvasQTAgg(self.figure)
        self.navigation=NavigationToolbar2QT(self.canvas,self)
        self.canvas.setMinimumSize(280,160)
        self.canvas.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,QtWidgets.QSizePolicy.Policy.Ignored)
        self.multisite_banner=QtWidgets.QLabel();self.multisite_banner.setWordWrap(True);self.multisite_banner.hide()
        layout.addWidget(self.multisite_banner);layout.addWidget(self.canvas,1)
        self.details_section=CollapsibleSection('Display details / diagnostics / export',expanded=False);self.details_section.setObjectName('results_details_'+kind);self.details_toggle=self.details_section.header;self.details_body=self.details_section.body;details=QtWidgets.QVBoxLayout(self.details_body);details.setContentsMargins(0,0,0,0)
        for widget in (self.label,self.advanced,self.display_note,export):
            layout.removeWidget(widget);details.addWidget(widget)
        if kind=='eels':
            self.multisite_controls.layout().removeWidget(self.multisite_controls.sources)
            details.addWidget(self.multisite_controls.sources)
        self.full_caption=QtWidgets.QLabel();self.full_caption.setWordWrap(True);self.full_caption.setTextFormat(QtCore.Qt.TextFormat.PlainText);details.addWidget(self.full_caption)
        details.addWidget(self.navigation)
        self.navigation.setMinimumWidth(0)
        self.navigation.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
        self.presentation=FigurePresentation(self.canvas,kind,self.full_caption)
        layout.insertWidget(1,self.details_section)
        self.choice.currentTextChanged.connect(self.redraw);self.canvas.mpl_connect('pick_event',self.pick)
    def set_compact(self,compact):
        focused=getattr(self,'_focused',False)
        self.details_section.setVisible(True)
        if hasattr(self,'prb_benchmark'):
            self.prb_benchmark.set_compact(compact)
            self.benchmark_section.setVisible(not focused and (self.result is None or self.result['config'].model!='multisite'))
    def maximize(self):
        w=self.owner
        w.responsive.show_panel(2);self._focused=not getattr(self,'_focused',False);self.set_compact(w.responsive.compact);w.responsive.focus_plot('results')
    def set_result(self,result):
        fresh=result is not self.result
        self.result=result
        # The application supplies its metadata-aware figure export action.
        # Keep the standard Matplotlib action only in standalone views.
        if any(action.text()=='Export Figure…' for action in self.navigation.actions()):
            standard=getattr(self.navigation,'_actions',{}).get('save_figure')
            if standard is not None:self.navigation.removeAction(standard)
        multisite=result['config'].model=='multisite'
        if self.kind=='eels':
            self.multisite_controls.setVisible(multisite);self.choice.setVisible(True)
            self.signal_label.setVisible(True)
            self.multisite_controls.sources.setVisible(multisite)
            if multisite:self.multisite_controls.set_result(result)
            else:self.multisite_controls.result=None
        self.multisite_banner.setVisible(multisite)
        if multisite:
            sites=result['metadata']['multisite']
            self.multisite_banner.setText('Complete-crystal incoming elastic intensity; per incident electron.' if self.kind=='diffraction' else
                f'Modeled partial core-edge · mean per selected ionizing atom (N={sites["selected_atom_count"]}).')
        self.advanced.setVisible(not multisite);self.component_mode.setVisible(self.kind in ('eels','maps'))
        self.field.setVisible(self.kind=='maps' and not multisite)
        self.export_button.setEnabled(True)
        self.export_button.setText(('Export selected spectra CSV + metadata' if self.kind=='eels' else 'Export saved arrays + metadata') if multisite else 'Export derived NPZ/CSV + metadata')
        self.export_button.setToolTip(('All spectral components for the selected series; unsupported samples are blank and labeled. Metadata is written automatically.' if self.kind=='eels' else 'Original saved total/group arrays, coverage, normalization and source metadata; no recalculation.') if multisite else '')
        if self.kind=='eels':self.benchmark_section.setVisible(not multisite)
        if self.kind=='maps':
            self.map_scope.setVisible(multisite)
            if multisite:
                from .multisite_results import angular_choices
                available=bool(angular_choices(result,True))
                for i in (1,2):self.map_scope.model().item(i).setEnabled(available)
                if fresh or not available:
                    with QtCore.QSignalBlocker(self.map_scope):self.map_scope.setCurrentIndex(0)
            else:
                with QtCore.QSignalBlocker(self.map_scope):self.map_scope.setCurrentIndex(0)
        elif self.kind=='eels':
            from .multisite_results import total_energy_samples
            energies=total_energy_samples(result,maps_only=False)
            with QtCore.QSignalBlocker(self.choice):
                self.choice.clear();self.choice.addItem(spectral_coverage_label(result))
                for sample in energies:
                    unique=sum(s['edge_label']==sample['edge_label'] for s in energies)==1
                    self.choice.addItem((sample['edge_label'] if unique else sample['label'])+' zoom',sample['energy_ev'])
        if not multisite:self.normalization.set_result(result)
        from .propagation import METHOD_NAMES
        options=list(result.get('methods',{result.get('method','bloch'):result}))
        if len(options)==2 and not multisite:options.append('difference' if self.kind in ('maps','diffraction') else 'overlay')
        self.method.blockSignals(True);self.method.clear()
        for key in options:self.method.addItem(METHOD_NAMES.get(key,'BW / MS overlay'),key)
        if self.kind=='eels':self.choice.setItemText(0,spectral_coverage_label(result))
        self.method.blockSignals(False)
        if self.kind=='maps':self.update_map_choices(redraw=False,preserve=not fresh)
        self.redraw()
    def map_result(self):
        return self.result.get('methods',{}).get(self.method.currentData(),self.result)
    def update_map_choices(self,*_,redraw=True,preserve=True):
        if self.result is None:return
        from .multisite_results import angular_choices,energy_sample_index
        current=self.map_result();previous=self.map_options() if preserve else {}
        with QtCore.QSignalBlocker(self.choice):
            self.choice.clear()
            samples=dict(selected_samples(current['config']))
            for label,data in angular_choices(current,self.map_scope.currentData()!='total' and current['config'].model=='multisite'):
                self.choice.addItem(label,data)
                energy=float(current['spectra']['energy_ev'][energy_sample_index(current,samples[data[1]])])
                self.choice.setItemData(self.choice.count()-1,energy,QtCore.Qt.ItemDataRole.UserRole+1)
                aliases=[key for key,value in samples.items() if value==energy]
                self.choice.setItemData(self.choice.count()-1,'Saved energy: '+repr(energy)+' eV\nSample aliases: '+', '.join(aliases),QtCore.Qt.ItemDataRole.ToolTipRole)
            # Changing scope preserves the energy, but never merges different groups.
            target_gid=previous.get('group_id') if self.map_scope.currentData()!='total' else None
            index=next((i for i in range(self.choice.count()) if self.choice.itemData(i)[0]==target_gid and self.choice.itemData(i,QtCore.Qt.ItemDataRole.UserRole+1)==previous.get('energy_ev')),-1)
            if index<0 and target_gid is None and previous.get('energy_ev') is not None:
                index=next((i for i in range(self.choice.count()) if self.choice.itemData(i,QtCore.Qt.ItemDataRole.UserRole+1)==previous['energy_ev']),-1)
            if index>=0 or previous.get('energy_ev') is not None:self.choice.setCurrentIndex(index)
        self.choice.setToolTip('Select the actual saved group and energy. Total Results uses total maps; the spectra selector is independent. Only modeled, saved group maps are listed.')
        if redraw:self.redraw()
    def map_options(self):
        selection=self.choice.currentData() or (None,None)
        return dict(scope=self.map_scope.currentData(),group_id=selection[0],edge=selection[1],
            energy_ev=self.choice.currentData(QtCore.Qt.ItemDataRole.UserRole+1),method=self.method.currentData())
    def restore_map_options(self,options):
        if not options:return
        from .multisite_results import energy_sample_index
        method=options.get('method',self.method.currentData());mi=self.method.findData(method)
        if mi>=0:
            with QtCore.QSignalBlocker(self.method):self.method.setCurrentIndex(mi)
        index=self.map_scope.findData(options.get('scope','total'))
        available=index>=0 and self.map_scope.model().item(index).isEnabled() and mi>=0
        with QtCore.QSignalBlocker(self.map_scope):self.map_scope.setCurrentIndex(index if available else 0)
        self.update_map_choices(redraw=False)
        current=self.map_result();energy=options.get('energy_ev')
        if energy is None:energy=dict(selected_samples(current['config'])).get(options.get('edge'))
        try:energy=float(current['spectra']['energy_ev'][energy_sample_index(current,energy)]) if energy is not None else None
        except ValueError:energy=None
        index=next((i for i in range(self.choice.count()) if self.choice.itemData(i)[0]==options.get('group_id') and self.choice.itemData(i,QtCore.Qt.ItemDataRole.UserRole+1)==energy),-1) if available and energy is not None else -1
        self.choice.setCurrentIndex(index)
        self.redraw()
        if index<0:self.display_note.setText('Saved angular scope/energy is unavailable. Choose an available selection explicitly; no substitute was selected.')
    def restore_zoom(self,label,energy=None):
        from .multisite_results import energy_sample_index
        if energy is None and label and label.endswith(' zoom'):
            energy=dict(selected_samples(self.result['config'])).get(label.removesuffix(' zoom'))
        if energy is not None:
            try:energy=float(self.result['spectra']['energy_ev'][energy_sample_index(self.result,energy)])
            except ValueError:energy=None
            index=self.choice.findData(energy) if energy is not None else -1
        else:index=self.choice.findText(label or '')
        with QtCore.QSignalBlocker(self.choice):self.choice.setCurrentIndex(max(0,index))
        return 'Saved spectral zoom unavailable; showing the actual calculated range.' if index<0 and label and label.endswith(' zoom') else ''
    def redraw(self,*_):
        if self.result is None:return
        method=self.method.currentData() or self.result.get('method','bloch')
        if self.result['config'].model=='multisite' and self.kind in ('eels','comparison'):
            from .multisite_results import draw_totals,description
            options=self.multisite_controls.options() if self.kind=='eels' else {}
            self.proxies=(draw_eels(self.figure,self.result,self.choice.currentText(),method,component_mode=self.component_mode.currentData(),zoom_energy=self.choice.currentData(),**options)
                if self.kind=='eels' else draw_totals(self.figure,self.result,method,self.kind,self.choice.currentText(),**options))
            if self.kind=='eels':
                from .multisite_results import spectral_series,selection_description
                current=self.result.get('methods',{}).get(method,self.result)
                series=spectral_series(current,options['selection'],options['normalization'],options['compared'],options['include_total'])
                sites=current['metadata']['multisite']
                self.multisite_banner.setText(self.multisite_controls.normalization_note(current,series))
                self.multisite_banner.setToolTip(selection_description(current,series)+'\n'+description(current))
                self.display_note.setText(selection_description(current,series)+'\n'+description(current))
                self.component_mode.setEnabled(options['quantity']==0)
            else:self.display_note.setText(description(self.result))
            if self.figure._suptitle is not None:self.figure._suptitle.set_wrap(True)
            self.presentation.capture();self.canvas.draw_idle();return
        display=self.normalization.settings()
        advanced=self.advanced.isChecked() and self.result['config'].model!='multisite'
        self.component_mode.setEnabled(not advanced)
        try:
            if self.kind=='maps':
                local=self.result['config'].model=='multisite'
                option=self.map_options()
                if option['edge'] is None:raise ValueError('No saved angular energy is selected')
                if local and option['scope']!='total' and option['group_id'] is None:raise ValueError('No modeled group angular maps were saved')
                draw_maps(self.figure,self.result,option['edge'],method,self.field.currentData() if advanced else None,display if advanced else None,
                    signal_mode=self.component_mode.currentData(),group_id=option['group_id'],normalization=option['scope'])
                if local:
                    gid=option['group_id'];n=self.result['metadata']['multisite']['selected_atom_count']
                    note=(f'Total Results: mean per selected ionizing atom (N={n}).' if gid is None else
                        f'{gid}: '+('Group Mean per atom (nonadditive).' if option['scope']=='mean' else f'Group Contribution: n/N × group mean (fixed N={n}).'))
                    self.multisite_banner.setText(note)
                    state='reversed configuration' if self.result['metadata']['multisite']['global_reversal'] else 'declared configuration'
                    self.multisite_banner.setToolTip(note+' '+state+(f'; crystal M={self.result["groups"][gid]["metadata"]["magnetization_crystal"]}' if gid is not None else '')+'; minus exchanges all provider pairs.')
            elif self.kind=='diffraction':draw_diffraction(self.figure,self.result,method,self.choice.currentIndex()==1)
            elif self.kind=='comparison':draw_comparison(self.figure,self.result,display)
            else:
                relative=advanced and self.component_diagnostic.currentData()=='relative'
                self.proxies=draw_eels(self.figure,self.result,self.choice.currentText(),method,display if advanced and not relative else None,component_mode='relative' if relative else self.component_mode.currentData(),diagnostics=advanced and not relative,zoom_energy=self.choice.currentData())
            from .component_display import TOOLTIPS
            self.component_mode.setToolTip(TOOLTIPS[self.component_mode.currentData()])
            self.display_note.setText('Display only; simulation arrays unchanged. '+('Explicit advanced diagnostics.' if advanced else TOOLTIPS[self.component_mode.currentData()]))
            if self.kind=='maps' and not advanced:
                note='Full-field mirrored-point EMCD; actual saved qy-reflected samples, independent of detector outlines. Includes possible nonmagnetic diffraction asymmetry.'
                self.component_mode.setToolTip(note);self.display_note.setText(note)
        except (ValueError,KeyError) as exc:
            self.figure.clear();self.figure.subplots().text(.05,.6,'Normalization unavailable: '+str(exc),wrap=True);self.display_note.setText(str(exc));self.figure._emcd_display_metadata=dict(unavailable=str(exc),derived_visualization_only=True)
        if self.kind=='eels' and hasattr(self.owner,'comparison'):self.owner.comparison.setPlainText(comparison_text(self.result,display.windows))
        if self.kind=='eels':
            selected=self.choice.currentData()
            if selected is None:selected=next((value for _,value in selected_samples(self.result['config']) if np.isfinite(value)),float(self.result['spectra']['energy_ev'][0]))
            self.prb_benchmark.set_context(self.result,method,display.windows,selected)
        if self.figure._suptitle is not None:self.figure._suptitle.set_wrap(True)
        self.presentation.capture()
        self.canvas.draw_idle()
    def update_prb_metadata(self):
        metadata=getattr(self.figure,'_emcd_display_metadata',{})
        metadata['prb_2007_benchmark']=dict(values=self.prb_benchmark.records,undefined=self.prb_benchmark.errors)
        self.figure._emcd_display_metadata=metadata
        records=self.prb_benchmark.records
        text='PRB benchmarks / controls'
        if len(records)==1:
            value=records[0]['prb_relative_dichroism_percent'];energy=records[0]['evaluation_energy_ev']
            if value is not None and energy is not None:text=f'PRB {value:+.4f}% at {energy:.4f} eV'
        self.benchmark_section.header.setText(text);self.benchmark_section.header.setToolTip(self.prb_benchmark.compact_summary.text())
    def export_derived(self):
        from .normalization_export import export_derived
        from pathlib import Path
        from datetime import datetime
        multisite=self.result is not None and self.result['config'].model=='multisite'
        parent=QtWidgets.QFileDialog.getExistingDirectory(self,'Spectra export parent (new folder)' if multisite else 'Derived visualization export parent (new folder)')
        if parent and self.result is not None:
            try:
                if multisite:
                    if self.kind!='eels':
                        from .project_io import save_project
                        state=dict(self.result.get('display_state',{}),angular_selection=self.map_options(),map_signal_mode=self.component_mode.currentData())
                        save_project(dict(self.result,display_state=state),Path(parent)/datetime.now().strftime('multisite_%Y%m%d_%H%M%S_%f'))
                        return
                    from .multisite_export import export_multisite_spectra
                    export_multisite_spectra(self.result,Path(parent)/datetime.now().strftime('multisite_%Y%m%d_%H%M%S_%f'),
                        method=self.method.currentData() or self.result.get('method','bloch'),**self.multisite_controls.options())
                    return
                if not self.advanced.isChecked() or (self.kind=='eels' and self.component_diagnostic.currentData()=='relative'):
                    from .emcd_forward import export_result
                    export_result(self.result,Path(parent)/datetime.now().strftime('emcd_%Y%m%d_%H%M%S_%f'),component_mode='relative' if self.advanced.isChecked() and self.kind=='eels' else self.owner.eels_view.component_mode.currentData(),map_signal_mode=self.owner.maps_view.component_mode.currentData())
                    return
                from .prb_benchmark import data_origin
                entries=[(name,dict(r,prb_data_origin=data_origin(self.result),prb_project_path=self.result.get('project_path')),name) for name,r in self.result.get('methods',{self.result.get('method','bloch'):self.result}).items()]
                options=self.prb_benchmark.options() if self.kind=='eels' else None
                export_derived(entries,Path(parent)/datetime.now().strftime('derived_%Y%m%d_%H%M%S_%f'),self.normalization.settings(),self.choice.currentText(),prb_options=options)
            except (ValueError,OSError) as exc:self.owner.error(str(exc))
    def pick(self,event):
        for proxy,target in self.proxies:
            if event.artist is proxy:
                lines=target if isinstance(target,tuple) else (target,)
                visible=not any(line.get_visible() for line in lines)
                for line in lines:line.set_visible(visible)
                for artist,other in self.proxies:
                    if other is target:artist.set_alpha(1 if visible else .2)
                self.canvas.draw_idle();return


def _single_comparison_text(result,windows=None,reference=None):
    rows=metrics(result)
    try:
        for edge,extra in percentage_metrics(result,windows,reference).items():rows[edge].update(extra)
    except ValueError:pass
    lines=['Signed edge metrics; Sigma_ref = N_A + N_B.','Even intensity differs from even A/B imbalance.','Corrected contrast is not a pure magnetic signal.','']
    for edge,row in rows.items():
        lines.append(edge)
        lines.extend(f'  {key}: '+('undefined' if value is None else (f'{value:+.10g}' if isinstance(value,(float,int)) else str(value))) for key,value in row.items())
        lines.append('')
    lines.extend([result['metadata']['pair_reason'],result['metadata']['correction_reason'],result['metadata']['limitations']])
    return '\n'.join(lines)


def comparison_text(result,windows=None):
    if result['config'].model=='multisite':
        from .multisite_results import comparison_text as multisite_text
        return multisite_text(result)
    import json
    methods=result.get('methods',{result.get('method','bloch'):result})
    text='\n\n'.join(name+'\n'+_single_comparison_text(r,windows,methods.get('bloch',next(iter(methods.values())))) for name,r in methods.items())
    return text+'\n\nNumerical comparison diagnostics (null = undefined):\n'+json.dumps(result.get('comparison',{}),indent=2)+'\nNumerical agreement at fixed potential cutoff does not establish physical convergence.'
