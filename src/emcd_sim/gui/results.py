"""Qt result views and reusable plotting of completed immutable run geometry."""
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg,NavigationToolbar2QT
from PySide6 import QtWidgets
from ..emcd_angular_plots import decorate_reciprocal_map
from .emcd_forward import metrics


def draw_maps(fig,result,edge):
    fig.clear();maps=result['maps'][edge];cfg=result['config'];settings=result['settings']
    keys=('I_mag','I_nonmag','I_plus','D_raw','D_corrected','D_nonmag_residual')
    titles=('Magnetic odd intensity','Reversal-even intensity','Total +M intensity','Raw paired A-B','Post-edge corrected A-B','Residual even contrast')
    dq=result['qx'][0,1]-result['qx'][0,0];h=cfg.halfwidth+dq/2;extent=(-h,h,-h,h)
    # Shared absolute signed scales across both edges for each comparable field.
    axes=fig.subplots(2,3)
    for ax,key,title in zip(axes.flat,keys,titles):
        if key not in maps:
            ax.text(.5,.5,'Unavailable\n'+(result['metadata']['pair_reason'] if key=='D_raw' or 'Mirrored maps disabled' in result['metadata']['pair_reason'] else result['metadata']['correction_reason']),ha='center',va='center',wrap=True,transform=ax.transAxes,fontsize=8)
            ax.set_title(title,fontsize=9);ax.set_axis_off();continue
        vmax=max(float(np.nanmax(abs(m[key]))) for m in result['maps'].values() if key in m)
        vmax=max(vmax,1e-30);signed=key not in ('I_nonmag','I_plus')
        im=ax.imshow(maps[key],origin='lower',extent=extent,cmap='RdBu_r' if signed else 'viridis',vmin=-vmax if signed else 0,vmax=vmax)
        decorate_reciprocal_map(ax,result['model'],extent,target_hkl=settings.target,zone_axis=settings.zone)
        target=result['model'].elastic.crystal.g_vector(settings.target)[:2]
        ax.plot(*target,'s',mfc='none',mec='crimson',ms=8,mew=1)
        ax.set_title(title,fontsize=9);fig.colorbar(im,ax=ax,shrink=.7,pad=.02).ax.tick_params(labelsize=7)
    e=cfg.l3 if edge=='L3' else cfg.l2
    fig.suptitle(f'{edge}: {e:.3f} eV | BW entrance channeling | relative intensity\n'+('XMCD-effective, native axis' if cfg.model=='xmcd' else 'Atomic 2p-3d approximation, non-DFT, not quantitative metallic Ni'),fontsize=11)


def draw_eels(fig,result,zoom='Full spectrum'):
    fig.clear();s=result['spectra'];e=s['energy_ev'];cfg=result['config'];axes=fig.subplots(3,1,sharex=True)
    panels=[(('I_A_plus','A +M'),('I_B_plus','B +M'),('I_A_minus','A -M'),('I_B_minus','B -M')),
            (('D_mag','Magnetic odd A-B'),('D_nonmag','Reversal-even A-B')),
            (('D_raw','Raw A-B'),('D_corrected','Corrected A-B'),('D_mag','Intrinsic magnetic'),('D_nonmag_residual_obs','Residual even'),('magnetic_bias','Correction magnetic bias'))]
    legends=[]
    for ax,curves in zip(axes,panels):
        lines=[]
        for key,label in curves:
            if key in s:lines.extend(ax.plot(e,s[key],label=label,lw=1.1))
        for energy in (cfg.l3,cfg.l2):ax.axvline(energy,color='.5',ls=':',lw=.7)
        if result['metadata']['alpha'] is not None:ax.axvspan(*cfg.window,color='gold',alpha=.2)
        ax.axhline(0,color='.7',lw=.5);ax.set_ylabel('Relative intensity');ax.grid(alpha=.15)
        legend=ax.legend(fontsize=8,ncols=2,loc='upper right')
        for proxy,line in zip(legend.get_lines(),lines):proxy.set_picker(5);legends.append((proxy,line))
    axes[-1].set_xlabel('Native energy loss (eV)' if cfg.model=='xmcd' else 'Atomic model energy loss (eV)')
    axes[-1].set_xlim((e[0],e[-1]) if zoom=='Full spectrum' else ((cfg.l3-5,cfg.l3+5) if zoom=='L3 zoom' else (cfg.l2-5,cfg.l2+5)))
    alpha=result['metadata']['alpha'];fig.suptitle('BW virtual-detector EELS | '+('alpha = %.9g'%alpha if alpha is not None else 'Post-edge correction unavailable / disabled')+'\nCorrected contrast = processed magnetic + residual even; click legend curves to toggle',fontsize=10)
    return legends


class ResultsView(QtWidgets.QWidget):
    def __init__(self,parent,kind):
        super().__init__();self.owner=parent;self.kind=kind;self.result=None;self.proxies=[]
        layout=QtWidgets.QVBoxLayout(self);self.label=QtWidgets.QLabel('No completed EMCD calculation.');self.label.setWordWrap(True);layout.addWidget(self.label)
        row=QtWidgets.QHBoxLayout();layout.addLayout(row);self.choice=QtWidgets.QComboBox();self.choice.addItems(['L3','L2'] if kind=='maps' else ['Full spectrum','L3 zoom','L2 zoom']);row.addWidget(self.choice)
        maximize=QtWidgets.QPushButton('Maximize / restore results');row.addWidget(maximize);maximize.clicked.connect(self.maximize)
        self.figure=Figure(layout='constrained');self.canvas=FigureCanvasQTAgg(self.figure)
        layout.addWidget(NavigationToolbar2QT(self.canvas,self))
        # Keep scientific axes readable in a narrow splitter. Maximizing gives
        # the full figure; scrolling avoids collapsed axes at smaller sizes.
        self.canvas.setMinimumSize(900 if kind=='maps' else 650,650 if kind=='maps' else 580)
        scroll=QtWidgets.QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(self.canvas);layout.addWidget(scroll,1)
        self.choice.currentTextChanged.connect(self.redraw);self.canvas.mpl_connect('pick_event',self.pick)
    def maximize(self):
        w=self.owner
        if getattr(w,'result_sizes',None) is None:w.result_sizes=w.splitter.sizes();w.splitter.setSizes([0,0,sum(w.result_sizes)])
        else:w.splitter.setSizes(w.result_sizes);w.result_sizes=None
    def redraw(self,*_):
        if self.result is None:return
        if self.kind=='maps':draw_maps(self.figure,self.result,self.choice.currentText())
        else:self.proxies=draw_eels(self.figure,self.result,self.choice.currentText())
        self.canvas.draw_idle()
    def pick(self,event):
        for proxy,line in self.proxies:
            if event.artist is proxy:line.set_visible(not line.get_visible());proxy.set_alpha(1 if line.get_visible() else .2);self.canvas.draw_idle()


def comparison_text(result):
    rows=metrics(result);lines=['Signed edge metrics; Sigma_ref = N_A + N_B.','Even intensity differs from even A/B imbalance.','Corrected contrast is not a pure magnetic signal.','']
    for edge,row in rows.items():
        lines.append(edge)
        lines.extend(f'  {key}: '+('undefined' if value is None else f'{value:+.10g}') for key,value in row.items())
        lines.append('')
    lines.extend([result['metadata']['pair_reason'],result['metadata']['correction_reason'],result['metadata']['limitations']])
    return '\n'.join(lines)
