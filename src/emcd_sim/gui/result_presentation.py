"""Plotting and controls over completed scientific data; no calculation."""
from pathlib import Path
from PySide6 import QtCore, QtWidgets
from .multisite_results import QUANTITIES
from .responsive import FlowLayout
import numpy as np
from matplotlib import colormaps
from ..emcd_angular_plots import decorate_reciprocal_map
from .forward_results import selected_edge_metrics
from .signal_normalization import DisplaySettings, normalized_spectra, angular_display, percentage_metrics
from ..mdff_edges import selected_samples
from .forward_results import method_result
from .multisite_results import comparison_text as _multisite_comparison_text


class MultisiteSpectraControls(QtWidgets.QWidget):
    changed = QtCore.Signal()

    def __init__(self):
        super().__init__();self.result = None
        layout = QtWidgets.QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(3)
        row = FlowLayout();layout.addLayout(row)
        self.selection = QtWidgets.QComboBox();row.addWidget(self.selection)
        self.normalization = QtWidgets.QComboBox();self.normalization.addItems(['Group Contribution (n/N, additive)','Group Mean (per atom, nonadditive)'])
        layout.addWidget(self.normalization)
        self.normalization.setToolTip('Weighted group/element curves use the total selected-atom denominator. Group means are diagnostic and not additive.')
        self.quantity = QtWidgets.QComboBox()
        for label,_ in QUANTITIES:self.quantity.addItem(label)
        from emcd_sim.gui.multisite_results import DEFINITIONS
        from .multisite_results import PANELS
        for i,(_,fields) in enumerate(QUANTITIES):
            fields=fields or [field for _,panel in PANELS for field in panel]
            text='\n'.join(key+': '+DEFINITIONS[key] for key,_ in fields)
            self.quantity.setItemData(i,text+'\nThe active ±M configuration and its simultaneous global reversal are complete provider states.',QtCore.Qt.ItemDataRole.ToolTipRole)
        row.addWidget(self.quantity)
        self.groups = QtWidgets.QListWidget();self.groups.setMaximumHeight(78);layout.addWidget(self.groups)
        self.include_total = QtWidgets.QCheckBox('Include total spectrum');layout.addWidget(self.include_total)
        self.include_total.setToolTip('Overlay the normalized total. Group means remain nonadditive; weighted groups use the total denominator.')
        self.include_total.toggled.connect(self.updated)
        self.sources = QtWidgets.QLabel();self.sources.setWordWrap(True)
        self.sources.setTextFormat(QtCore.Qt.TextFormat.PlainText);layout.addWidget(self.sources)
        for box in (self.selection,self.normalization,self.quantity):
            box.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            box.setMinimumContentsLength(12)
            box.currentIndexChanged.connect(self.updated)
        self.groups.itemChanged.connect(self.updated)

    def set_result(self, result):
        fresh=result is not self.result
        self.result = result;previous = None if fresh else self.selection.currentData()
        checked = {self.groups.item(i).data(QtCore.Qt.ItemDataRole.UserRole) for i in range(self.groups.count())
                   if self.groups.item(i).checkState() == QtCore.Qt.CheckState.Checked}
        with QtCore.QSignalBlocker(self),QtCore.QSignalBlocker(self.selection),QtCore.QSignalBlocker(self.groups):
            if fresh:
                self.normalization.setCurrentIndex(0);self.include_total.setChecked(False);checked=set()
            self.selection.clear();self.selection.addItem('Total Results',('total',None))
            for element in dict.fromkeys(g['metadata']['element'] for g in result['groups'].values()):
                self.selection.addItem('Element: '+element+' (all groups)',('element',element))
            self.groups.clear()
            for gid,entry in result['groups'].items():
                meta = entry['metadata'];source = meta['source'];label = f'{gid} · {meta["element"]} {source["edge"]}'
                excluded = result['metadata']['multisite']['channels'][gid]['omitted_by_request']
                if excluded:label += ' (excluded)'
                self.selection.addItem('Group: '+label,('group',gid))
                tooltip = f'{label}\nMDFF: {source.get("provider_identity","imported tensor")}\n{source["path"]}\n{source["source"]}'
                self.selection.setItemData(self.selection.count()-1,tooltip,QtCore.Qt.ItemDataRole.ToolTipRole)
                item = QtWidgets.QListWidgetItem(label);item.setData(QtCore.Qt.ItemDataRole.UserRole,gid)
                item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(QtCore.Qt.CheckState.Checked if not checked or gid in checked else QtCore.Qt.CheckState.Unchecked)
                item.setToolTip(tooltip);self.groups.addItem(item)
            self.selection.addItem('Group Comparison',('compare',None))
            height=max(self.groups.sizeHintForRow(0),self.groups.fontMetrics().height()+4)
            self.groups.setFixedHeight(min(78,self.groups.count()*height+2*self.groups.frameWidth()))
            index = next((i for i in range(self.selection.count()) if previous is not None
                          and tuple(self.selection.itemData(i)) == tuple(previous)),0)
            self.selection.setCurrentIndex(index)
            self.updated()

    def options(self):
        selection = self.selection.currentData() or ('total',None)
        compared = tuple(self.groups.item(i).data(QtCore.Qt.ItemDataRole.UserRole) for i in range(self.groups.count())
                         if self.groups.item(i).checkState() == QtCore.Qt.CheckState.Checked)
        normalization = 'mean' if self.normalization.currentIndex() == 1 and selection[0] in ('group','compare') else 'weighted'
        return dict(selection=selection,normalization=normalization,compared=compared,quantity=self.quantity.currentIndex(),
                    include_total=self.include_total.isChecked() and selection[0]=='compare')

    def restore_options(self, options):
        """Restore display preferences against available saved group identities."""
        selection=tuple(options.get('selection',('total',None)))
        index=next((i for i in range(self.selection.count()) if tuple(self.selection.itemData(i))==selection),0)
        self.selection.setCurrentIndex(index)
        self.normalization.setCurrentIndex(1 if options.get('normalization')=='mean' else 0)
        self.quantity.setCurrentIndex(max(0,min(len(QUANTITIES)-1,int(options.get('quantity',0)))))
        for i in range(self.groups.count()):
            item=self.groups.item(i)
            item.setCheckState(QtCore.Qt.CheckState.Checked if item.data(QtCore.Qt.ItemDataRole.UserRole) in options.get('compared',()) else QtCore.Qt.CheckState.Unchecked)
        self.include_total.setChecked(bool(options.get('include_total',False)))
        self.updated()

    def updated(self, *_):
        mode,value = self.selection.currentData() or ('total',None)
        self.groups.setVisible(mode == 'compare');self.normalization.setVisible(mode in ('group','compare'))
        self.include_total.setVisible(mode == 'compare')
        self.normalization.setEnabled(mode in ('group','compare'))
        self.selection.setToolTip(self.selection.currentData(QtCore.Qt.ItemDataRole.ToolTipRole) or self.selection.currentText())
        self.quantity.setToolTip(self.quantity.currentData(QtCore.Qt.ItemDataRole.ToolTipRole) or '')
        if self.result is not None:
            options = self.options()
            ids = ([value] if mode == 'group' else list(options['compared']) if mode == 'compare' else
                   [gid for gid,g in self.result['groups'].items() if mode == 'total' or g['metadata']['element'] == value])
            if options['include_total']:ids = list(self.result['groups'])
            descriptions = [];full = []
            for gid in ids:
                d = self.result['groups'][gid]['metadata'];source = d['source']
                channel = self.result['metadata']['multisite']['channels'][gid]
                status = 'excluded by request' if channel['omitted_by_request'] else 'modeled '+str(channel['modeled_window_ev'])+' eV'
                name = Path(source['path']).name
                if len(name)>24:name = name[:16]+'…'+Path(name).suffix
                descriptions.append(f'{gid}: {d["element"]} {source["edge"]} · MDFF {name}'+(' · EXCLUDED' if channel['omitted_by_request'] else ''))
                full.append(f'{gid} · n={d["multiplicity"]} · {source["path"]}\n{source["source"]}\n{status}')
            structural = set(self.result['model'].elastic.crystal.species)
            ionizing = {g['metadata']['element'] for g in self.result['groups'].values()}
            if structural-ionizing:descriptions.append('No ionizing channel modeled for '+', '.join(sorted(structural-ionizing))+' (elastic structure only).')
            self.sources.setText('; '.join(descriptions));self.sources.setToolTip('\n\n'.join(full))
            self.selection.setToolTip(self.sources.text()+'\n\n'+self.sources.toolTip())
        self.changed.emit()

    def normalization_note(self, result, series):
        """Compact visible caption; full definitions remain in Details/exports."""
        from .multisite_results import selection_description
        mode=self.options()['selection'][0];n=result['metadata']['multisite']['selected_atom_count']
        if mode=='total' or not series:return selection_description(result,series)
        if self.options()['normalization']=='mean':note='Group Mean: per atom within each group (not additive).'
        else:note=('Element Contribution: Σ n × group mean / N' if mode=='element' else 'Group Contribution: n × group mean / N')+f' (fixed N={n}).'
        if self.options()['include_total']:note+=f' Total normalized intensity: mean per selected atom (N={n}).'
        return note


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


def _single_comparison_text(result,windows=None,reference=None):
    rows=selected_edge_metrics(result)
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


def draw_multisite_panel(figure, result, method, kind, choice, *, selection=('total',None),normalization='weighted',compared=(),quantity=0,include_total=False):
    """Render a stored multi-site panel through the shared presentation functions."""
    if kind == 'eels':
        return draw_eels(figure,result,choice,method,selection=selection,normalization=normalization,
                         compared=compared,quantity=quantity,include_total=include_total)
    if kind == 'maps':return draw_maps(figure,result,choice,method)
    if kind == 'diffraction':return draw_diffraction(figure,result,method,choice=='Depth average')
    figure.clear();ax=figure.subplots();ax.axis('off')
    ax.text(.01,.98,_multisite_comparison_text(result),va='top',fontsize=8,wrap=True)
    figure._emcd_display_metadata=dict(kind='multisite details',method=method)
    return []
