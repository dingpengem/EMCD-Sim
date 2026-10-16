"""Qt result views and reusable plotting of completed immutable run geometry."""
import numpy as np
from matplotlib.figure import Figure
from matplotlib import colormaps
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg,NavigationToolbar2QT
from PySide6 import QtWidgets
from ..emcd_angular_plots import decorate_reciprocal_map
from .emcd_forward import metrics
from .signal_normalization import DisplaySettings, normalized_spectra, angular_display, percentage_metrics
from .normalization_controls import NormalizationControls


def draw_maps(fig,result,edge,method=None,field=None,display=None):
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
        keys=('D_mag','D_nonmag','D_raw','D_corrected','D_mag_processed','D_nonmag_residual');titles=('Magnetic paired asymmetry','Nonmagnetic paired asymmetry','Raw paired asymmetry','Corrected paired asymmetry','Processed magnetic asymmetry','Residual even asymmetry')
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
    e=cfg.l3 if edge=='L3' else cfg.l2
    solver_label='BW-MS numerical solver difference' if method=='difference' else method+' entrance channeling'
    fig.suptitle(f'{edge}: {e:.3f} eV | {solver_label} | '+('Relative intensity (a.u.)' if display.map_mode=='raw' else ('Local magnetic fraction (%)' if display.map_mode=='local' else 'Paired angular asymmetry (%)'))+f'\n'+('XMCD-effective, native axis' if cfg.model=='xmcd' else 'Atomic 2p-3d approximation, non-DFT, not quantitative metallic Ni'),fontsize=11)

    fig._emcd_display_metadata=dict(kind='angular',map_mode=display.map_mode,fields=display_meta,shared_color_scale=display.shared_scale,masked_color='#c8c8c8',note='No integrated-peak scaling of angular densities.')


def method_result(result,method):
    methods=result.get('methods',{result.get('method','bloch'):result})
    if method!='difference':return methods[method]
    b,m=[methods[k] for k in ('bloch','fft-multislice')]
    maps={edge:{k:b['maps'][edge][k]-m['maps'][edge][k] for k in b['maps'][edge] if k in m['maps'][edge]} for edge in ('L3','L2')}
    metadata=dict(b['metadata'],pair_reason='BW-MS paired maps require validated physical pairing in both methods.',
        correction_reason='BW-MS corrected maps require valid correction in both methods. '+b['metadata']['correction_reason']+' / '+m['metadata']['correction_reason'])
    return dict(b,maps=maps,method='difference',metadata=metadata)


def draw_eels(fig,result,zoom='Full spectrum',method=None,display=None):
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
                if key in s:lines.extend(ax.plot(e,s[key],label=name+': '+label,lw=1.1,ls='--' if name=='fft-multislice' else '-',color='C'+str(i)))
        for energy in (cfg.l3,cfg.l2):ax.axvline(energy,color='.5',ls=':',lw=.7)
        if any(r['metadata']['alpha'] is not None for r in chosen.values()):ax.axvspan(*cfg.window,color='gold',alpha=.2)
        ax.axhline(0,color='.7',lw=.5);ax.set_ylabel(units,fontsize=8);ax.grid(alpha=.15)
        if ax is not axes[0]:
            limits=ax.get_ylim();limit=max(abs(limits[0]),abs(limits[1]));ax.set_ylim(-limit,limit)
        legend=ax.legend(fontsize=7,ncols=2,loc='upper right')
        for proxy,line in zip(legend.get_lines(),lines):proxy.set_picker(5);legends.append((proxy,line))
    axes[-1].set_xlabel('Native energy loss (eV)' if cfg.model=='xmcd' else 'Atomic model energy loss (eV)')
    axes[-1].set_xlim((e[0],e[-1]) if zoom=='Full spectrum' else ((cfg.l3-5,cfg.l3+5) if zoom=='L3 zoom' else (cfg.l2-5,cfg.l2+5)))
    factors=', '.join(name+' alpha='+('%.9g'%r['metadata']['alpha'] if r['metadata']['alpha'] is not None else 'disabled') for name,r in chosen.items())
    note='; '.join(dict.fromkeys(meta.get('warning','') for _,meta in normalized if meta.get('warning')))
    fig.suptitle(units+' | '+factors+'\n'+(note or 'Common reference; corrected = processed magnetic + residual even; solid BW / dashed MS'),fontsize=10)
    fig._emcd_display_metadata=dict(kind='spectra',normalization=[meta for _,meta in normalized],zoom=zoom)
    return legends


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
    ax.set_title(method+' | '+('depth average diag(C)' if depth_average else 'exit elastic intensity')+'\nExact common hkl basis; excluded FFT intensity reported separately; spot area is visualization only')
    fig.colorbar(scatter,ax=ax,shrink=.8)


def draw_comparison(fig,result,display=None):
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
    values=[angular_display(r,'L3','I_mag',map_mode)[0] for r in (b,m)]
    finite_limit=lambda v:max(float(np.max(abs(v[np.isfinite(v)]))) if np.isfinite(v).any() else 0.,1e-30)
    scale=max(finite_limit(v) for v in values)
    normalized=normalized_spectra([(name,r,name) for name,r in methods.items()],display);lookup={name:item for name,item in zip(methods,normalized)}
    for ax,v,title in zip(axes[0],values+[values[0]-values[1]],['BW L3 magnetic odd','FFT MS L3 magnetic odd','BW-MS numerical solver difference']):
        limit=finite_limit(v) if 'difference' in title else scale
        im=ax.imshow(v,origin='lower',extent=extent,cmap=colormaps['RdBu_r'].with_extremes(bad='#c8c8c8'),vmin=-limit,vmax=limit)
        decorate_reciprocal_map(ax,result['model'],extent,target_hkl=result['settings'].target,zone_axis=result['settings'].zone)
        ax.plot(*result['model'].elastic.crystal.g_vector(result['settings'].target)[:2],'s',mfc='none',mec='crimson',ms=8)
        ax.set_title(title+' | '+('a.u.' if map_mode=='raw' else 'local %'),fontsize=9);fig.colorbar(im,ax=ax,shrink=.65).set_label('Relative intensity (a.u.)' if map_mode=='raw' else 'Local magnetic fraction (%)',fontsize=7)
    for ax,key,title in zip(axes[1],('I_A_plus','D_mag','D_raw'),('Full detector A +M EELS','Intrinsic magnetic A-B','Raw / corrected A-B')):
        for name,r in methods.items():
            s,meta=lookup[name];ax.plot(r['spectra']['energy_ev'],s[key],ls='-' if name=='bloch' else '--',label=name,lw=1.1)
            if key=='D_raw' and 'D_corrected' in s:ax.plot(r['spectra']['energy_ev'],s['D_corrected'],ls=':' if name=='bloch' else '-.',label=name+' corrected',lw=1)
        ax.set(title=title,xlabel='Energy loss (eV)',ylabel=next(iter(lookup.values()))[1]['units']);ax.legend(fontsize=7);ax.grid(alpha=.15)
    fig._emcd_display_metadata=dict(kind='BW/MS comparison',spectra=[meta for _,meta in normalized],map_mode=map_mode,solver_errors='Original raw arrays; never independently peak-normalized')
    diag=result['comparison'];fig.suptitle('Independent BW / FFT MS | '+cfg.model+' | '+str(result['settings'].zone)+', '+str(result['settings'].thickness)+' nm\nCoherence relative error %.3g; FFT norm error %.3g. Fixed potential cutoff: agreement is not physical convergence.'%(diag['coherence']['l2_relative'],diag['fft']['norm_error']),fontsize=11)
    fig.suptitle(fig._suptitle.get_text()+'\n'+normalized[0][1]['units']+' | reference '+normalized[0][1]['reference_run']+' '+normalized[0][1]['reference_method'],fontsize=10)


class ResultsView(QtWidgets.QWidget):
    def __init__(self,parent,kind):
        super().__init__();self.owner=parent;self.kind=kind;self.result=None;self.proxies=[]
        layout=QtWidgets.QVBoxLayout(self);self.label=QtWidgets.QLabel('No completed EMCD calculation.');self.label.setWordWrap(True);layout.addWidget(self.label)
        row=QtWidgets.QHBoxLayout();layout.addLayout(row);self.choice=QtWidgets.QComboBox();self.choice.addItems(['L3','L2'] if kind=='maps' else (['Exit intensity','Depth average'] if kind=='diffraction' else ['Full spectrum','L3 zoom','L2 zoom']));row.addWidget(self.choice)
        self.method=QtWidgets.QComboBox();row.addWidget(self.method);self.method.currentIndexChanged.connect(self.redraw)
        self.choice.setVisible(kind!='comparison');self.method.setVisible(kind!='comparison')
        self.field=QtWidgets.QComboBox();self.field.addItem('All six fields',None)
        for title,key in [('Magnetic odd','I_mag'),('Magnetic paired','D_mag'),('Nonmagnetic paired','D_nonmag'),('Nonmagnetic even','I_nonmag'),('Total +M','I_plus'),('Raw paired A-B','D_raw'),('Corrected paired A-B','D_corrected'),('Residual even','D_nonmag_residual')]:self.field.addItem(title,key)
        self.field.setVisible(kind=='maps');row.addWidget(self.field);self.field.currentTextChanged.connect(self.redraw)
        maximize=QtWidgets.QPushButton('Maximize / restore results');row.addWidget(maximize);maximize.clicked.connect(self.maximize)
        self.normalization=NormalizationControls(self,maps=kind=='maps');self.normalization.setVisible(kind!='diffraction');layout.addWidget(self.normalization);self.normalization.changed.connect(self.redraw)
        self.display_note=QtWidgets.QLabel();self.display_note.setWordWrap(True);layout.addWidget(self.display_note)
        export=QtWidgets.QPushButton('Export derived NPZ/CSV + metadata');export.setVisible(kind!='diffraction');layout.addWidget(export);export.clicked.connect(self.export_derived)
        self.figure=Figure(layout='constrained');self.canvas=FigureCanvasQTAgg(self.figure)
        layout.addWidget(NavigationToolbar2QT(self.canvas,self))
        # Keep scientific axes readable in a narrow splitter. Maximizing gives
        # the full figure; scrolling avoids collapsed axes at smaller sizes.
        self.canvas.setMinimumSize(900 if kind in ('maps','comparison') else 650,650 if kind=='maps' else 580)
        scroll=QtWidgets.QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(self.canvas);layout.addWidget(scroll,1)
        self.choice.currentTextChanged.connect(self.redraw);self.canvas.mpl_connect('pick_event',self.pick)
    def maximize(self):
        w=self.owner
        if getattr(w,'result_sizes',None) is None:w.result_sizes=w.splitter.sizes();w.splitter.setSizes([0,0,sum(w.result_sizes)])
        else:w.splitter.setSizes(w.result_sizes);w.result_sizes=None
    def set_result(self,result):
        self.result=result
        self.normalization.set_result(result)
        from .propagation import METHOD_NAMES
        options=list(result.get('methods',{result.get('method','bloch'):result}))
        if len(options)==2:options.append('difference' if self.kind in ('maps','diffraction') else 'overlay')
        self.method.blockSignals(True);self.method.clear()
        for key in options:self.method.addItem(METHOD_NAMES.get(key,'BW / MS overlay'),key)
        if self.kind=='eels' and len(options)>1:self.method.setCurrentIndex(len(options)-1)
        self.method.blockSignals(False);self.redraw()
    def redraw(self,*_):
        if self.result is None:return
        method=self.method.currentData() or self.result.get('method','bloch')
        display=self.normalization.settings()
        try:
            if self.kind=='maps':draw_maps(self.figure,self.result,self.choice.currentText(),method,self.field.currentData(),display)
            elif self.kind=='diffraction':draw_diffraction(self.figure,self.result,method,self.choice.currentIndex()==1)
            elif self.kind=='comparison':draw_comparison(self.figure,self.result,display)
            else:self.proxies=draw_eels(self.figure,self.result,self.choice.currentText(),method,display)
            self.display_note.setText('Display-only derived quantities. '+('Raw solver discrepancies remain unchanged.' if display.mode!='raw' or display.map_mode!='raw' else 'Raw (a.u.); no rescaling.'))
        except (ValueError,KeyError) as exc:
            self.figure.clear();self.figure.subplots().text(.05,.6,'Normalization unavailable: '+str(exc),wrap=True);self.display_note.setText(str(exc));self.figure._emcd_display_metadata=dict(unavailable=str(exc),derived_visualization_only=True)
        if self.kind=='eels' and hasattr(self.owner,'comparison'):self.owner.comparison.setPlainText(comparison_text(self.result,display.windows))
        self.canvas.draw_idle()
    def export_derived(self):
        from .normalization_export import export_derived
        from pathlib import Path
        from datetime import datetime
        parent=QtWidgets.QFileDialog.getExistingDirectory(self,'Derived visualization export parent (new folder)')
        if parent and self.result is not None:
            try:
                entries=[(name,r,name) for name,r in self.result.get('methods',{self.result.get('method','bloch'):self.result}).items()]
                export_derived(entries,Path(parent)/datetime.now().strftime('derived_%Y%m%d_%H%M%S_%f'),self.normalization.settings(),self.choice.currentText())
            except ValueError as exc:self.owner.error(str(exc))
    def pick(self,event):
        for proxy,line in self.proxies:
            if event.artist is proxy:line.set_visible(not line.get_visible());proxy.set_alpha(1 if line.get_visible() else .2);self.canvas.draw_idle()


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
    import json
    methods=result.get('methods',{result.get('method','bloch'):result})
    text='\n\n'.join(name+'\n'+_single_comparison_text(r,windows,methods.get('bloch',next(iter(methods.values())))) for name,r in methods.items())
    return text+'\n\nNumerical comparison diagnostics (null = undefined):\n'+json.dumps(result.get('comparison',{}),indent=2)+'\nNumerical agreement at fixed potential cutoff does not establish physical convergence.'
