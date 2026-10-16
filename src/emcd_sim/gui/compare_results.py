"""Scientific comparison of immutable completed results; no forward solver."""
import csv,json
from pathlib import Path
import numpy as np
from PySide6 import QtWidgets
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg,NavigationToolbar2QT
from ..emcd_angular_plots import decorate_reciprocal_map
from .emcd_forward import metrics

FIELDS={'Magnetic odd':'I_mag','Nonmagnetic even':'I_nonmag','Total +M':'I_plus','Raw paired EMCD':'D_raw','Corrected paired EMCD':'D_corrected'}


def identity(label,r,method):
    s=r['settings'];return f'{label} | {s.thickness:g} nm | tilt ({s.tilt[0]:+.4f},{s.tilt[1]:+.4f}) mrad | {r["config"].model} | {method}'


def map_compatibility(a,b,edge,field):
    reasons=[];ac,bc=a['config'],b['config']
    for key in ('qx','qy'):
        if a[key].shape!=b[key].shape or not np.allclose(a[key],b[key],rtol=0,atol=1e-13):reasons.append('Reciprocal coordinate grids differ; no interpolation.')
    ea,eb=(ac.l3,bc.l3) if edge=='L3' else (ac.l2,bc.l2)
    if abs(ea-eb)>1e-8:reasons.append('Selected native energies differ; no energy shift/alignment.')
    if not np.allclose(a['metadata']['frame'],b['metadata']['frame'],atol=1e-12,rtol=0):reasons.append('Local Cartesian crystal frames differ.')
    if ac.model!=bc.model:reasons.append('Different MDFF models/intensity normalizations: qualitative overlay only, no absolute difference or ratio.')
    elif ac.model=='xmcd':
        digest=lambda r:r['config'].source_sha256 or (r['metadata'].get('source_audit') or {}).get('sha256')
        if not digest(a) or digest(a)!=digest(b):reasons.append('XMCD source-maximum normalization is not shared (source hashes differ or missing).')
    ua=a['metadata'].get('intensity_convention');ub=b['metadata'].get('intensity_convention')
    if ua and ub and ua!=ub:reasons.append('Intensity unit/normalization conventions differ.')
    ma=np.asarray(ac.magnetization,float);mb=np.asarray(bc.magnetization,float)
    if not np.allclose(ma/np.linalg.norm(ma),mb/np.linalg.norm(mb),rtol=0,atol=1e-12) or a['metadata'].get('reversal')!=b['metadata'].get('reversal'):
        reasons.append('Magnetization axis or reversal convention differs; no sign adjustment.')
    if field=='I_mag' or field.startswith('D_'):
        if np.sign(ac.eta)!=np.sign(bc.eta) and ac.model=='xmcd':reasons.append('XMCD eta magnetic-sign convention differs.')
    if field.startswith('D_'):
        if ac.centers!=bc.centers or ac.radius!=bc.radius or ac.subpixels!=bc.subpixels:reasons.append('Paired detector supports/integration differ; intrinsic intensity maps may still be compared.')
    if field=='D_corrected' and ac.window!=bc.window:reasons.append('Post-edge window definitions differ.')
    if field not in a['maps'][edge] or field not in b['maps'][edge]:reasons.append('Requested map is unavailable for one result.')
    return not reasons,list(dict.fromkeys(reasons))


def scalar_rows(entries):
    rows=[]
    for label,r,name in entries:
        for edge,row in metrics(r).items():
            e=r['spectra']['energy_ev'];i=int(np.argmin(abs(e-row['energy_ev'])));s=r['spectra'];sigma=row['Sigma_ref'];floor=1e-10*max(float(s['Sigma_ref'].max()),1e-30)
            denominator=float(s['I_A_plus'][i]+s['I_B_plus'][i])
            row=dict(row,run=identity(label,r,name),edge=edge,A_raw_plus_sum=row['D_raw']/denominator if denominator>floor else None,
                A_corrected_sigma=row['D_corrected']/sigma if row['D_corrected'] is not None and sigma>floor else None,
                relative_detectability_proxy=abs(row['D_mag'])/np.sqrt(sigma) if sigma>floor else None,
                proxy_definition='|D_mag|/sqrt(Sigma_ref), relative units, not calibrated SNR or cross-model ratio',
                bw_ms_coherence_relative=r.get('comparison',{}).get('coherence',{}).get('l2_relative'))
            rows.append(row)
    return rows


def draw_saved_comparison(fig,entries,edge='L3',field='I_mag',spectral='D_mag',zoom='Full spectrum'):
    fig.clear();fig.set_layout_engine('constrained');fig.get_layout_engine().set(hspace=.12,wspace=.06,h_pad=.08)
    grid=fig.add_gridspec(2,3);axes=[fig.add_subplot(grid[0,i]) for i in range(3)];ax=fig.add_subplot(grid[1,:]);reasons=[]
    first=entries[:2];compatible=False
    if len(first)==2:compatible,reasons=map_compatibility(first[0][1],first[1][1],edge,field)
    vals=[r['maps'][edge].get(field) for _,r,_ in first]
    # Compatible fields share their absolute physical/relative scale. For
    # incompatible models label separate units instead of implying calibration.
    shared=max([float(np.nanmax(abs(v))) for v in vals if v is not None]+[1e-30])
    for index,(panel,(label,r,name),v) in enumerate(zip(axes,first,vals)):
        if v is None:panel.text(.5,.5,'Requested map unavailable',ha='center',transform=panel.transAxes);panel.set_axis_off();continue
        scale=shared;signed=field not in ('I_nonmag','I_plus')
        qx,qy=r['qx'],r['qy'];dx=float(qx[0,1]-qx[0,0])/2;dy=float(qy[1,0]-qy[0,0])/2
        extent=(qx.min()-dx,qx.max()+dx,qy.min()-dy,qy.max()+dy)
        image=panel.imshow(v,origin='lower',extent=extent,cmap='RdBu_r' if signed else 'viridis',vmin=-scale if signed else 0,vmax=scale)
        decorate_reciprocal_map(panel,r['model'],extent,target_hkl=r['settings'].target,zone_axis=r['settings'].zone)
        panel.set_title(f'Result {index+1} | {name} | {r["settings"].thickness:g} nm\n'+f'tilt ({r["settings"].tilt[0]:+.3f},{r["settings"].tilt[1]:+.3f}) mrad; {r["config"].model}',fontsize=8)
        fig.colorbar(image,ax=panel,shrink=.7)
    if compatible:
        v=vals[0]-vals[1];scale=max(float(np.nanmax(abs(v))),1e-30);r=first[0][1]
        image=axes[2].imshow(v,origin='lower',extent=extent,cmap='RdBu_r',vmin=-scale,vmax=scale);fig.colorbar(image,ax=axes[2],shrink=.7)
        decorate_reciprocal_map(axes[2],r['model'],extent,target_hkl=r['settings'].target,zone_axis=r['settings'].zone)
        second_za=-first[1][1]['model'].elastic.microscope.incident_k_xy
        if extent[0]<=second_za[0]<=extent[1] and extent[2]<=second_za[1]<=extent[3]:
            axes[2].plot(*second_za,marker='*',ms=9,mfc='none',mec='crimson',ls='',label='ZA result 2');axes[2].legend(fontsize=6)
        else:axes[2].text(.02,.1,'Result 2 ZA outside: '+str(second_za),transform=axes[2].transAxes,fontsize=7)
        # Difference has common reciprocal coordinates. Both run-specific ZA
        # markers remain explicit in their own side-by-side physical panels.
        axes[2].set(xlabel='qx (cycles/A)',ylabel='qy (cycles/A)',aspect='equal',title='Result 1 - Result 2\nActual units; no matching factor')
    else:
        axes[2].text(.02,.9,'Direct subtraction disabled\n'+'\n'.join(reasons or ['Select two results']),va='top',wrap=True,fontsize=9,transform=axes[2].transAxes);axes[2].set_axis_off()
    for index,(label,r,name) in enumerate(entries):
        s=r['spectra'];keys=('I_A_plus','I_B_plus') if spectral=='A/B +M' else (spectral,)
        for j,key in enumerate(keys):
            if key in s:ax.plot(s['energy_ev'],s[key],color='C'+str(j if len(keys)>1 else 0),ls=('-','--','-.',':')[index%4],label=identity(label,r,name)+' | '+key,lw=1.1)
        for e in (r['config'].l3,r['config'].l2):ax.axvline(e,color='.5',ls=':',lw=.6)
        if r['metadata']['alpha'] is not None:ax.axvspan(*r['config'].window,color='gold',alpha=.08)
    if zoom!='Full spectrum' and entries:
        c=entries[0][1]['config'];center=c.l3 if zoom=='L3 zoom' else c.l2;ax.set_xlim(center-5,center+5)
    ax.set(xlabel='Native energy loss (eV); no shifts or interpolation',ylabel='Original relative intensity');ax.legend(fontsize=7,ncols=1);ax.grid(alpha=.15)
    mixed=len({r['config'].model for _,r,_ in entries})>1 or any('normalization' in reason or 'Intensity unit' in reason for reason in reasons)
    warning='QUALITATIVE overlay: native model/normalization scales differ; no absolute intensity ratio.' if mixed else 'Original values; separate run-specific geometry; no peak normalization.'
    fig.suptitle(edge+' | '+field+' | Saved-result comparison\n'+warning,fontsize=10)
    return compatible,reasons


def export_comparison_data(entries,path):
    root=Path(path);root.mkdir(parents=True,exist_ok=False);arrays={};records=[]
    for i,(label,r,name) in enumerate(entries):
        arrays.update({f'run{i}__'+k:v for k,v in r['spectra'].items()});arrays[f'run{i}__qx']=r['qx'];arrays[f'run{i}__qy']=r['qy']
        for edge,m in r['maps'].items():arrays.update({f'run{i}__{edge}__'+k:v for k,v in m.items()})
        records.append(dict(label=label,method=name,metadata=r['metadata']))
        with (root/f'run{i}_spectra.csv').open('w',newline='',encoding='utf-8') as f:
            keys=[k for k,v in r['spectra'].items() if np.ndim(v)==1 and len(v)==len(r['spectra']['energy_ev'])]
            writer=csv.writer(f);writer.writerow(keys);writer.writerows(zip(*(r['spectra'][k] for k in keys)))
    np.savez_compressed(root/'comparison_data.npz',**arrays)
    rows=scalar_rows(entries)
    with (root/'scalar_metrics.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (root/'comparison_metadata.json').write_text(json.dumps(records,indent=2,allow_nan=False)+'\n',encoding='utf-8')


class CompareResults(QtWidgets.QWidget):
    def __init__(self,owner,selected):
        super().__init__();self.owner=owner;self.selected=selected;self.methods=[];layout=QtWidgets.QVBoxLayout(self)
        self.note=QtWidgets.QLabel('Maps show the first two results. Spectra and signed metrics include all selections.');self.note.setWordWrap(True);layout.addWidget(self.note)
        row=QtWidgets.QHBoxLayout();layout.addLayout(row)
        for label,r in selected:
            choice=QtWidgets.QComboBox()
            for name in r.get('methods',{r.get('method','bloch'):r}):choice.addItem(label+' | '+name,name)
            self.methods.append(choice);row.addWidget(choice);choice.currentIndexChanged.connect(self.redraw)
        self.edge=QtWidgets.QComboBox();self.edge.addItems(['L3','L2']);row.addWidget(self.edge)
        self.field=QtWidgets.QComboBox();self.field.addItems(list(FIELDS));row.addWidget(self.field)
        self.spectrum=QtWidgets.QComboBox();self.spectrum.addItems(['D_mag','A/B +M','D_nonmag','D_raw','D_corrected']);row.addWidget(self.spectrum)
        self.zoom=QtWidgets.QComboBox();self.zoom.addItems(['Full spectrum','L3 zoom','L2 zoom']);row.addWidget(self.zoom)
        for c in (self.edge,self.field,self.spectrum,self.zoom):c.currentIndexChanged.connect(self.redraw)
        actions=QtWidgets.QHBoxLayout();layout.addLayout(actions)
        for title,callback in [('Export figure PNG/SVG',self.export_figure),('Export NPZ/CSV',self.export_data),('Maximize / restore',self.maximize)]:
            b=QtWidgets.QPushButton(title);b.clicked.connect(callback);actions.addWidget(b)
        self.tabs=QtWidgets.QTabWidget();layout.addWidget(self.tabs,1);plot=QtWidgets.QWidget();pl=QtWidgets.QVBoxLayout(plot)
        self.figure=Figure(figsize=(14,9),layout='constrained');self.canvas=FigureCanvasQTAgg(self.figure);pl.addWidget(NavigationToolbar2QT(self.canvas,self));self.canvas.setMinimumSize(950,650)
        scroll=QtWidgets.QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(self.canvas);pl.addWidget(scroll);self.tabs.addTab(plot,'Maps and EELS')
        self.table=QtWidgets.QTableWidget();self.tabs.addTab(self.table,'Signed scalar metrics');self.redraw()
    def entries(self):
        return [(label,dict(r.get('methods',{r.get('method','bloch'):r})[choice.currentData()],comparison=r.get('comparison',{})),choice.currentData()) for (label,r),choice in zip(self.selected,self.methods)]
    def redraw(self,*_):
        if not hasattr(self,'canvas'):return
        entries=self.entries();valid,reasons=draw_saved_comparison(self.figure,entries,self.edge.currentText(),FIELDS[self.field.currentText()],self.spectrum.currentText(),self.zoom.currentText())
        self.note.setText(('Direct map difference compatible.' if valid else 'Side-by-side only: '+' '.join(reasons))+' Maps: first two; spectra/metrics: all selected. Scientific convergence is not implied.')
        rows=scalar_rows(entries);keys=list(rows[0]);self.table.setColumnCount(len(keys));self.table.setRowCount(len(rows));self.table.setHorizontalHeaderLabels(keys)
        for i,r in enumerate(rows):
            for j,k in enumerate(keys):self.table.setItem(i,j,QtWidgets.QTableWidgetItem('undefined' if r[k] is None else str(r[k])))
        self.table.resizeColumnsToContents();self.canvas.draw_idle()
    def maximize(self):
        if getattr(self.owner,'result_sizes',None) is None:self.owner.result_sizes=self.owner.splitter.sizes();self.owner.splitter.setSizes([0,0,sum(self.owner.result_sizes)])
        else:self.owner.splitter.setSizes(self.owner.result_sizes);self.owner.result_sizes=None
    def export_figure(self):
        path,_=QtWidgets.QFileDialog.getSaveFileName(self,'Export displayed scientific comparison','','PNG (*.png);;SVG (*.svg)')
        if path:self.figure.savefig(path,dpi=300)
    def export_data(self):
        path=QtWidgets.QFileDialog.getExistingDirectory(self,'Comparison export parent (new subfolder)')
        if path:
            from datetime import datetime,timezone
            try:export_comparison_data(self.entries(),Path(path)/datetime.now(timezone.utc).strftime('comparison_%Y%m%d_%H%M%S_%fZ'))
            except Exception as exc:self.owner.error(str(exc))
