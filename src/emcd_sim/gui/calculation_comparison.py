"""Native-grid overlays of retained calculations; separate from group comparison."""
import csv
import json
from pathlib import Path
from datetime import datetime
from PySide6 import QtCore, QtWidgets
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
import numpy as np
from .multisite_results import QUANTITIES, spectral_series, covered_segments
from .normalization_export import save_figure


class CalculationComparison(QtWidgets.QDialog):
    def __init__(self,owner):
        super().__init__(owner);self.setWindowTitle('Compare Calculations');self.resize(1050,760)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowMaximizeButtonHint,True)
        self.owner=owner;self.runs=[(r,owner.browser.cache[r['id']]) for r in owner.browser.registry.records]
        layout=QtWidgets.QVBoxLayout(self);choices=QtWidgets.QHBoxLayout();layout.addLayout(choices)
        self.first=QtWidgets.QComboBox();self.second=QtWidgets.QComboBox()
        selected={r['id'] for r in owner.browser.selected()}
        for label,box in [('Calculation A',self.first),('Calculation B',self.second)]:
            choices.addWidget(QtWidgets.QLabel(label));choices.addWidget(box,1)
            box.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);box.setMinimumContentsLength(14)
            for record,r in self.runs:
                text='['+record['id'][:8]+'] '+record['name']+f' | {r["settings"].thickness:g} nm | {r["config"].channeling_model}'
                box.addItem(text,record['id']);box.setItemData(box.count()-1,text,QtCore.Qt.ItemDataRole.ToolTipRole)
        indices=[i for i,(record,_) in enumerate(self.runs) if record['id'] in selected]
        self.first.setCurrentIndex(indices[0] if indices else 0)
        self.second.setCurrentIndex(indices[1] if len(indices)>1 else (1 if self.first.currentIndex()!=1 else 0))
        row=QtWidgets.QHBoxLayout();layout.addLayout(row)
        self.scope=QtWidgets.QComboBox();self.scope.addItem('Total',('total',None));row.addWidget(self.scope)
        elements=set();groups=set()
        for _,r in self.runs:
            for gid,g in r.get('groups',{}).items():elements.add(g['metadata']['element']);groups.add(gid)
        for element in sorted(elements):self.scope.addItem('Element '+element,('element',element))
        for gid in sorted(groups):self.scope.addItem('Group '+gid,('group',gid))
        self.signal=QtWidgets.QComboBox();row.addWidget(self.signal)
        for i,(label,fields) in enumerate(QUANTITIES[1:],1):self.signal.addItem(label,i)
        self.mean=QtWidgets.QCheckBox('Group means (nonadditive)');row.addWidget(self.mean)
        self.note=QtWidgets.QLabel();self.note.setWordWrap(True);layout.addWidget(self.note)
        self.figure=Figure(layout='constrained');self.canvas=FigureCanvasQTAgg(self.figure)
        toolbar=NavigationToolbar2QT(self.canvas,self);toolbar.addAction('Export Figure…',self.export_figure)
        toolbar.addAction('Export Comparison CSV…',self.export_data);layout.addWidget(toolbar);layout.addWidget(self.canvas,1)
        self.advanced=toolbar.addAction('Legacy maps / metrics…',self.legacy_views)
        self.advanced.setToolTip('Existing legacy map/metric comparison. Multi-site calculation comparison currently supports spectra only.')
        for box in (self.scope,self.signal):box.currentIndexChanged.connect(self.redraw)
        self.mean.toggled.connect(self.redraw)
        self.first.currentIndexChanged.connect(self.redraw);self.second.currentIndexChanged.connect(self.redraw);self.redraw()

    def redraw(self,*_):
        self.figure.clear();ax=self.figure.subplots();self.rows=[];notes=[];count=0
        scope=tuple(self.scope.currentData());fields=QUANTITIES[self.signal.currentData()][1]
        self.mean.setEnabled(scope[0]=='group')
        chosen=(self.first.currentData(),self.second.currentData())
        self.figure._emcd_display_metadata=dict(kind='calculation_comparison',run_ids=chosen,scope=scope,
            signal=self.signal.currentText(),units='Original relative provider intensity scale',group_means=self.mean.isChecked() and scope[0]=='group')
        self.advanced.setEnabled(chosen[0]!=chosen[1] and all(r['config'].model!='multisite' for record,r in self.runs if record['id'] in chosen))
        if self.first.currentData()==self.second.currentData():
            self.note.setText('Choose exactly two distinct calculations from the active project.');self.canvas.draw_idle();return
        for i,(record,root) in enumerate(self.runs):
            if record['id'] not in (self.first.currentData(),self.second.currentData()):continue
            count+=1
            for method,r in root.get('methods',{root.get('method','bloch'):root}).items():
                if r['config'].model=='multisite':
                    try:series=spectral_series(r,scope,'mean' if self.mean.isChecked() else 'weighted')[0]
                    except ValueError as exc:notes.append(record['name']+': '+str(exc));continue
                    masks=covered_segments(r,r['spectra']['energy_ev'],series['groups']);spectra=series['spectra']
                    convention={'mean':'group_mean_per_atom_nonadditive','weighted':'additive_contribution_n_over_N',
                                'total':'total_mean_per_selected_ionizing_atom'}[series['normalization']]
                    denominator=r['metadata']['multisite']['selected_atom_count']
                else:
                    if scope[0]!='total':notes.append(record['name']+': legacy result has no site/element decomposition');continue
                    spectra=r['spectra'];masks=[np.ones(len(spectra['energy_ev']),bool)];convention='legacy_source_scale';denominator=''
                for key,label in fields:
                    if key not in spectra:notes.append(record['name']+': '+key+' unavailable');continue
                    name=f'[{record["id"][:8]}] {record["name"][:28]} | {method} {r["config"].channeling_model} | {r["settings"].thickness:g} nm | {label}'
                    color=None
                    segments=np.full(len(spectra['energy_ev']),-1,int)
                    for mi,mask in enumerate(masks):
                        if not mask.any():continue
                        segments[mask]=mi
                        line,=ax.plot(spectra['energy_ev'][mask],spectra[key][mask],label=name if mi==0 else None,
                            color=color,marker='o',ls='none' if r['config'].energy_scope=='edges' else '-')
                        color=line.get_color()
                    self.rows.extend((record['id'],record['name'],method,scope[0],scope[1] or '',key,float(e),
                        float(v) if segment>=0 else '',int(segment),'modeled' if segment>=0 else 'unmodeled',
                        convention,denominator,'points' if r['config'].energy_scope=='edges' else 'segments')
                        for e,v,segment in zip(spectra['energy_ev'],spectra[key],segments))
        ax.set(xlabel='Native energy loss (eV)',ylabel='Original relative intensity');ax.grid(alpha=.15)
        if ax.lines:ax.legend(fontsize=6)
        text='Calculation comparison: original amplitudes and native grids; no peak scaling, interpolation or extrapolation. Model/source intensity scales may differ; overlays are qualitative, not calibrated ratios.'
        if scope[0]!='total':text+=' Additive curves retain each run’s own selected-atom denominator.'
        if scope[0]=='group' and self.mean.isChecked():text+=' Group means are nonadditive.'
        if count<2:text+=' Select at least two calculations.'
        counts=[]
        for record,r in self.runs:
            if record['id'] not in chosen:continue
            norm='legacy source normalization'
            if r['config'].model=='multisite':
                norm=('per-group-atom mean (nonadditive)' if scope[0]=='group' and self.mean.isChecked() else
                      'additive contribution' if scope[0]!='total' else 'total mean per selected atom')
                norm+=', selected N='+str(r['metadata']['multisite']['selected_atom_count'])
                norm+='; active provider '+('−M' if r['metadata']['multisite']['global_reversal'] else '+M')
            counts.append('['+record['id'][:8]+']: '+norm)
        self.note.setText(text+' '+'; '.join(counts+notes))
        self.figure._emcd_display_metadata['note']=self.note.text();self.canvas.draw_idle()

    def export_figure(self):
        path,_=QtWidgets.QFileDialog.getSaveFileName(self,'Export displayed calculation comparison','','PNG (*.png);;SVG (*.svg)')
        if path:save_figure(self.figure,path)

    def legacy_views(self):
        if self.first.currentData()==self.second.currentData():return
        from .compare_results import CompareResults
        selected=[(record['name']+' ['+record['id'][:8]+']',r) for record,r in self.runs
                  if record['id'] in (self.first.currentData(),self.second.currentData())]
        dialog=QtWidgets.QDialog(self);dialog.setWindowTitle('Legacy Calculation Maps / Metrics');dialog.resize(1150,850)
        dialog.setWindowFlag(QtCore.Qt.WindowType.WindowMaximizeButtonHint,True)
        layout=QtWidgets.QVBoxLayout(dialog);layout.addWidget(CompareResults(self.owner,selected))
        self.owner.dialogs.append(dialog);dialog.show()

    def export_data(self):
        if not self.rows:return
        path,_=QtWidgets.QFileDialog.getSaveFileName(self,'Export displayed comparison CSV','','CSV (*.csv)')
        if not path:return
        with Path(path).open('w',encoding='utf-8',newline='') as stream:
            writer=csv.writer(stream);writer.writerow(['run_id','run_name','solver','scope','scope_id','signal','energy_ev','relative_intensity',
                'segment','coverage_state','normalization','selected_atom_count','plot_style']);writer.writerows(self.rows)
        from .multisite_export import DEFINITIONS
        Path(str(path)+'.json').write_text(json.dumps(dict(note=self.note.text(),signal_definitions=DEFINITIONS,
            units={'energy_ev':'eV','relative_intensity':'Original provider scale; no cross-element calibration'},
            coverage='Blank is unmodeled, not physical zero. Do not connect different segment numbers or interpolate between points.'),indent=2)+'\n',encoding='utf-8')
