"""MDFF, propagation controls and worker lifecycle; calculations live in emcd_forward."""
from dataclasses import asdict
from pathlib import Path
import datetime,json
import numpy as np
from PySide6 import QtCore,QtWidgets
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg,NavigationToolbar2QT
from .geometry import Structure
from .emcd_forward import (ForwardSettings,DEFAULT_SOURCE,inspect_source,material_reason,energy_grid,tensors,calculate,Cancelled,export_result)
from ..ni_local_mdff import NiLocalConfig
from ..wien2k_xmcd import load_wien2k_xmcd
from .results import ResultsView,comparison_text


class EMCDWorker(QtCore.QThread):
    result=QtCore.Signal(object);failed=QtCore.Signal(str);stage=QtCore.Signal(str)
    def __init__(self,structure,settings,config):
        super().__init__();self.structure=structure;self.settings=settings;self.config=config
    def run(self):
        try:
            r=calculate(self.structure,self.settings,self.config,self.stage.emit,self.isInterruptionRequested)
            if not self.isInterruptionRequested():self.result.emit(r)
        except Cancelled:pass
        except Exception as exc:
            if not self.isInterruptionRequested():self.failed.emit(str(exc))


class StageB:
    emcd_ready=QtCore.Signal()
    def mdff_controls(self):
        self.emcd_result=None;self.source_info=None;self.validated_path=None
        self.model_box=QtWidgets.QComboBox();self.model_box.addItems(['XMCD-constrained (WIEN2k)','Atomic ionization (Ni 2p -> 3d)']);self.form.addRow(self.model_box)
        self.axis=QtWidgets.QLineEdit('0 0 1');self.form.addRow('Crystal Cartesian M axis',self.axis)
        self.mdff_stack=QtWidgets.QStackedWidget();self.form.addRow(self.mdff_stack)
        xm=QtWidgets.QWidget();xf=QtWidgets.QFormLayout(xm);self.mdff_stack.addWidget(xm);saved=self.form;self.form=xf
        self.source_path=QtWidgets.QLineEdit(str(DEFAULT_SOURCE) if DEFAULT_SOURCE.exists() else '');self.form.addRow('Five-column XMCD',self.source_path)
        self.button('Browse XMCD...',self.browse_xmcd);self.button('Validate source / native features',self.validate_xmcd)
        self.number('eta','eta',1,-5,5,self.emcd_stale);self.number('beta','beta',1,0,10,self.emcd_stale)
        self.number('xl3','L3 native feature (eV)',831.271,1,10000,self.emcd_stale);self.number('xl2','L2 native feature (eV)',848.698,1,10000,self.emcd_stale)
        self.declaration=QtWidgets.QCheckBox('I declare M axis, RP/LP convention and edge assignments');self.declaration.setToolTip('Tensor Txy=+i eta (RP-LP)/2; source convention must be checked.');self.form.addRow(self.declaration)
        self.source_status=QtWidgets.QLabel('Validate source before calculation.');self.source_status.setWordWrap(True);self.form.addRow(self.source_status)
        at=QtWidgets.QWidget();self.form=QtWidgets.QFormLayout(at);self.mdff_stack.addWidget(at)
        label=QtWidgets.QLabel('Atomic 2p-3d approximation, non-DFT, not quantitative metallic Ni. Crystal [001] magnetization only.');label.setWordWrap(True);self.form.addRow(label)
        cfg=NiLocalConfig()
        for key,title,lo,hi in [('l3_ev','L3 (eV)',1,10000),('l2_ev','L2 (eV)',1,10000),('crystal_field_10dq_ev','10Dq (eV)',0,5),('exchange_split_ev','Exchange (eV)',0,5),('eg_up_holes','eg up holes',0,1),('eg_down_holes','eg down holes',0,1),('t2g_up_holes','t2g up holes',0,1),('t2g_down_holes','t2g down holes',0,1)]:
            self.number('atomic_'+key,title,getattr(cfg,key),lo,hi,self.emcd_stale)
        self.number('sigma','Gaussian sigma (eV)',.8,.05,5,self.emcd_stale)
        advanced=QtWidgets.QGroupBox('Advanced atomic radial controls');advanced.setCheckable(True);advanced.setChecked(False);body=QtWidgets.QWidget();outer=QtWidgets.QVBoxLayout(advanced);outer.addWidget(body);self.form.addRow(advanced);body.setVisible(False);advanced.toggled.connect(body.setVisible);self.form=QtWidgets.QFormLayout(body)
        self.number('atomic_zeff_2p','Zeff 2p',25,1,40,self.emcd_stale);self.number('atomic_zeff_3d','Zeff 3d',9,1,40,self.emcd_stale)
        self.radial_override=QtWidgets.QCheckBox('Use explicit radial dipole (Angstrom)');self.form.addRow(self.radial_override);self.number('radial','Radial dipole',.05,.00001,10,self.emcd_stale)
        self.form=saved;self.button('Preview source / tensor spectrum...',self.preview_mdff)
        self.model_box.currentIndexChanged.connect(self.model_changed)
        self.axis.textChanged.connect(self.emcd_stale);self.declaration.toggled.connect(self.emcd_stale);self.source_path.textChanged.connect(self.source_changed);self.radial_override.toggled.connect(self.emcd_stale)

    def propagation_controls(self):
        self.propagation_box=QtWidgets.QComboBox();self.propagation_box.addItems(['Bloch-wave','FFT Multislice','Both (BW / MS comparison)']);self.form.addRow('Propagation Method',self.propagation_box)
        self.propagation_box.currentIndexChanged.connect(self.emcd_stale)
        group=QtWidgets.QGroupBox('Multislice numerical settings');group.setCheckable(True);group.setChecked(False)
        body=QtWidgets.QWidget();outer=QtWidgets.QVBoxLayout(group);outer.addWidget(body);self.form.addRow(group);body.setVisible(False);group.toggled.connect(body.setVisible)
        saved=self.form;self.form=QtWidgets.QFormLayout(body)
        box=QtWidgets.QSpinBox();box.setRange(12,128);box.setSingleStep(2);box.setValue(32);self.spin['fft_grid']=box;self.form.addRow('FFT grid (even)',box);box.valueChanged.connect(self.emcd_stale)
        self.number('slice_step','Max slice step (nm)',.04,.001,1,self.emcd_stale)
        label=QtWidgets.QLabel('Verified FFT orientation: Ni [017] only. Shared depth nodes, beam and potential cutoffs below. No outgoing channeling.');label.setWordWrap(True);self.form.addRow(label);self.form=saved

    def numerical_controls(self):
        for key,title,value,lo,hi in [('energy','Energy sampling points',241,9,501),('grid','Detector grid points',33,9,97),('depth','Depth integration nodes',64,2,256),('subpixels','Aperture subpixels',64,4,256)]:
            box=QtWidgets.QSpinBox();box.setRange(lo,hi);box.setValue(value);self.spin[key]=box;self.form.addRow(title,box);box.valueChanged.connect(self.emcd_stale)
        self.number('halfwidth','Map halfwidth (cycles/A)',1,.1,10,self.emcd_stale)
        self.correction=QtWidgets.QCheckBox('Enable post-edge A/B correction');self.correction.setChecked(True);self.form.addRow(self.correction);self.correction.toggled.connect(self.emcd_stale)
        self.number('window_lo','Window start (eV)',878,1,10000,self.emcd_stale);self.number('window_hi','Window end (eV)',882,1,10000,self.emcd_stale)
        self.memory_label=QtWidgets.QLabel();self.memory_label.setWordWrap(True);self.form.addRow(self.memory_label)

    def setup_stage_b(self):
        self.setWindowTitle('EMCD-Sim Desktop — Stage C: BW / FFT multislice EMCD / EELS')
        self.emcd_button=QtWidgets.QPushButton('Run EMCD / EELS');self.emcd_button.clicked.connect(self.start_emcd)
        self.zone.textChanged.connect(self.emcd_stale);self.target.textChanged.connect(self.emcd_stale)
        self.run_button.parentWidget().layout().itemAt(1).layout().insertWidget(1,self.emcd_button)
        self.maps_view=ResultsView(self,'maps');self.eels_view=ResultsView(self,'eels');self.comparison=QtWidgets.QPlainTextEdit();self.comparison.setReadOnly(True)
        for i,widget,title in ((1,self.maps_view,'EMCD Angular Maps'),(2,self.eels_view,'Virtual Detector EELS'),(3,self.comparison,'Magnetic / Nonmagnetic')):
            old=self.tabs.widget(i);self.tabs.removeTab(i);old.deleteLater();self.tabs.insertTab(i,widget,title);self.tabs.setTabEnabled(i,False)
        self.diffraction_view=ResultsView(self,'diffraction');self.overview_view=ResultsView(self,'comparison')
        self.tabs.addTab(self.diffraction_view,'BW/MS Diffraction');self.tabs.addTab(self.overview_view,'BW/MS Overview')
        self.tabs.setTabEnabled(5,False);self.tabs.setTabEnabled(6,False)
        if DEFAULT_SOURCE.exists():self.validate_xmcd(show_error=False)
        self.emcd_stale()

    def model_changed(self,index):
        self.mdff_stack.setCurrentIndex(index)
        if hasattr(self,'correction'):
            self.correction.setChecked(index==0 and bool(self.source_info and self.source_info['audit']))
        self.emcd_stale()
    def source_changed(self,*_):
        self.source_info=None;self.validated_path=None;self.declaration.setChecked(False);self.source_status.setText('Source changed; validate and declare conventions.');self.emcd_stale()
    def browse_xmcd(self):
        path,_=QtWidgets.QFileDialog.getOpenFileName(self,'Import five-column WIEN2k XMCD','','XMCD / text (*.xmcd *.txt *.dat);;All files (*)')
        if path:self.source_path.setText(path);self.validate_xmcd()
    def validate_xmcd(self,show_error=True):
        try:
            info=inspect_source(self.source_path.text());self.source_info=info;self.validated_path=self.source_path.text()
            if info['selected']:self.set_values({'xl3':info['selected']['L3'],'xl2':info['selected']['L2']})
            self.declaration.setChecked(bool(info['audit']));self.source_status.setText(info['provenance']+'\nNative range: %.3f–%.3f eV; no energy shift.'%tuple(info['bounds']))
            if hasattr(self,'correction'):self.correction.setChecked(bool(info['audit']))
        except Exception as exc:
            self.source_info=None;self.validated_path=None;self.source_status.setText(str(exc))
            if show_error:self.error(str(exc))
        self.emcd_stale()

    def forward_settings(self):
        atomic=NiLocalConfig(**{k:self.spin['atomic_'+k].value() for k in asdict(NiLocalConfig())})
        mode='xmcd' if self.model_box.currentIndex()==0 else 'atomic';axis=tuple(float(v) for v in self.axis.text().replace(',',' ').split())
        if len(axis)!=3:raise ValueError('Magnetization needs three Cartesian components')
        if mode=='xmcd' and (not self.source_info or self.validated_path!=self.source_path.text()):raise ValueError('Validate the current XMCD source first')
        return ForwardSettings(propagation=['bloch','fft-multislice','both'][self.propagation_box.currentIndex()],fft_grid=self.spin['fft_grid'].value(),slice_step=self.spin['slice_step'].value(),model=mode,source=self.source_path.text(),source_sha256=self.source_info['sha256'] if self.source_info else '',axis_declared=self.declaration.isChecked(),magnetization=axis,
            eta=self.spin['eta'].value(),beta=self.spin['beta'].value(),l3=self.spin['xl3'].value() if mode=='xmcd' else atomic.l3_ev,l2=self.spin['xl2'].value() if mode=='xmcd' else atomic.l2_ev,
            atomic=atomic,sigma=self.spin['sigma'].value(),radial=self.spin['radial'].value() if self.radial_override.isChecked() else None,
            energy_points=self.spin['energy'].value(),grid=self.spin['grid'].value(),depth=self.spin['depth'].value(),subpixels=self.spin['subpixels'].value(),halfwidth=self.spin['halfwidth'].value(),
            centers=tuple(tuple(p) for p in self.detectors),radius=self.spin['radius'].value(),correction=self.correction.isChecked(),window=(self.spin['window_lo'].value(),self.spin['window_hi'].value()))

    def emcd_stale(self,*_):
        if not hasattr(self,'emcd_button') or getattr(self,'_restoring',False):return
        reason=material_reason(self.structure);cfg=None;info=None
        try:
            cfg=self.forward_settings();s=self.settings();energy_grid(cfg)
            if cfg.model=='xmcd' and not cfg.axis_declared:raise ValueError('Declare XMCD conventions before Run EMCD')
            if cfg.model=='atomic' and not np.allclose(cfg.magnetization,(0,0,1)):raise ValueError('Atomic model supports crystal [001] M only')
            from .propagation import numerical_info
            info=numerical_info(self.structure,s,cfg)
            self.memory_label.setText(f"{info['bw_beams']} common BW beams; {info['fft_harmonics']} FFT harmonics ({info['potential_nonzero_harmonics']} nonzero potential).\nSingle pair {info['single_complex_pair_mib']:.1f} MiB; dense working {info['dense_working_estimate_mib']:.1f} / 512 MiB; estimated arrays {info['estimated_working_mib']:.1f} MiB. Not total peak process memory.")
            if s.target not in self.current[2] or s.target==(0,0,0):reason='Select a valid target reflection.'
            structure_matches=self.emcd_result is not None and self.emcd_result['metadata']['structure']==self.structure.description()
            if self.emcd_result and self.emcd_result.get('structure_snapshot'):
                from .project_io import structures_match
                structure_matches=structures_match(self.emcd_result['structure_snapshot'],self.structure)
            config_matches=self.emcd_result is not None and self.emcd_result['config']==cfg
            if self.emcd_result and cfg.model==self.emcd_result['config'].model=='atomic':
                old=asdict(self.emcd_result['config']);new=asdict(cfg)
                for key in ('source','source_sha256'):old.pop(key);new.pop(key)
                config_matches=old==new
            fresh=self.emcd_result is not None and self.emcd_result['settings']==s and config_matches and structure_matches
            reason=reason or self.input_source_reason()
        except Exception as exc:reason=reason or str(exc);fresh=False
        self.emcd_button.setEnabled(not reason and not self.busy);self.emcd_button.setToolTip(reason or 'Run the selected incoming-wave propagation and shared EMCD/EELS contraction')
        if self.emcd_result:
            text='Completed-run geometry and spectra; inputs match.' if fresh else 'STALE RESULT — Viewing saved result — current inputs differ. Showing completed-run geometry and spectra.'
            for view in (self.maps_view,self.eels_view,self.diffraction_view,self.overview_view):view.label.setText(text)
        current_marker='\n\nCurrent EMCD propagation:';saved_marker='\n\nCompleted EMCD run (snapshot):'
        base=self.info.toPlainText().split(current_marker)[0].split(saved_marker)[0]
        if cfg is not None:
            base+=current_marker+'\n'+json.dumps(dict(requested=cfg.propagation,fft_grid=cfg.fft_grid,max_slice_step_nm=cfg.slice_step,depth_nodes=cfg.depth,numerics=info,unavailable_reason=reason or None),indent=2)
        if self.emcd_result:
            r=self.emcd_result
            base+=saved_marker+'\n'+json.dumps(dict(methods=list(r.get('methods',{'bloch':0})),settings=r['metadata']['settings'],numerics=r['metadata'].get('numerics',{}),comparison=r.get('comparison',{})),indent=2)
        self.info.setPlainText(base)

    def preview_mdff(self):
        try:
            cfg=self.forward_settings();e=energy_grid(cfg)
            if cfg.model=='xmcd':
                source=load_wien2k_xmcd(cfg.source);e=source.energy_ev;curves=[(source.right+source.left,'XAS = RP + LP'),(source.right-source.left,'XMCD = RP - LP')]
            else:
                t=tensors(cfg,e,np.eye(3))[0].tensor_angstrom2_per_ev;curves=[(np.trace(t,axis1=-2,axis2=-1).real/3,'Re Tr(T)/3'),(t[:,0,1].imag,'Im Txy (magnetic)'),(t[:,2,2].real,'Re Tzz')]
            dialog=QtWidgets.QDialog(self);dialog.setWindowTitle('Native XMCD source' if cfg.model=='xmcd' else 'Atomic 2p-3d approximation, non-DFT, not quantitative metallic Ni');dialog.resize(900,600);layout=QtWidgets.QVBoxLayout(dialog)
            fig=Figure(layout='constrained');canvas=FigureCanvasQTAgg(fig);layout.addWidget(NavigationToolbar2QT(canvas,dialog));choice=QtWidgets.QComboBox();choice.addItems(['Full spectrum','L3 zoom','L2 zoom']);layout.addWidget(choice);layout.addWidget(canvas);ax=fig.subplots()
            def draw(*_):
                ax.clear()
                for y,label in curves:ax.plot(e,y,label=label)
                for v in (cfg.l3,cfg.l2):ax.axvline(v,ls=':',color='.5')
                ax.set(xlabel='Unshifted source / model energy (eV)',ylabel='Source spectral units' if cfg.model=='xmcd' else 'Tensor (A²/eV)',xlim=(e[0],e[-1]) if choice.currentIndex()==0 else ((cfg.l3-5,cfg.l3+5) if choice.currentIndex()==1 else (cfg.l2-5,cfg.l2+5)))
                ax.legend();canvas.draw_idle()
            choice.currentTextChanged.connect(draw);draw();dialog.show();self.dialogs.append(dialog)
        except Exception as exc:self.error(str(exc))

    def start_emcd(self):
        if self.busy:return
        try:
            cfg=self.forward_settings();s=self.settings();energy_grid(cfg)
            reason=material_reason(self.structure)
            reason=reason or self.input_source_reason()
            if reason:raise ValueError(reason)
            from .propagation import numerical_info
            numerical_info(self.structure,s,cfg)
            structure=Structure(self.structure.atoms.copy(),self.structure.source,self.structure.sha256,self.structure.import_warnings)
        except Exception as exc:self.error(str(exc));return
        self.busy=True;self.run_outcome='running';self.inputs.setEnabled(False);self.run_button.setEnabled(False);self.emcd_button.setEnabled(False);self.cancel_button.setEnabled(True);self.progress.setRange(0,0)
        self.worker=EMCDWorker(structure,s,cfg);self.worker.stage.connect(self.statusBar().showMessage);self.worker.result.connect(self.emcd_completed);self.worker.failed.connect(self.preview_failed);self.worker.finished.connect(self.emcd_finished);self.worker.start()
    def emcd_completed(self,result):
        if self.worker.isInterruptionRequested():return
        self.emcd_result=result;self.run_outcome='completed'
        self.register_completed(result)
        for i,view in ((1,self.maps_view),(2,self.eels_view)):
            self.tabs.setTabEnabled(i,True);view.set_result(result)
        for i,view in ((5,self.diffraction_view),(6,self.overview_view)):
            self.tabs.setTabEnabled(i,i==5 or len(result.get('methods',{}))==2);view.set_result(result)
        self.tabs.setTabEnabled(3,True);self.comparison.setPlainText(comparison_text(result));self.tabs.setCurrentIndex(2);self.emcd_stale();self.emcd_ready.emit()
    def emcd_finished(self):
        self.finished();self.emcd_stale()
        self.statusBar().showMessage('EMCD '+('cancelled; no cancelled result registered.' if self.worker.isInterruptionRequested() else ('completed.' if self.run_outcome=='completed' else 'failed; no new result registered.')))
    def save_emcd(self):
        if self.emcd_result is None:self.error('Run EMCD/EELS successfully first.');return
        path=QtWidgets.QFileDialog.getExistingDirectory(self,'Export completed EMCD result (new subfolder)')
        if not path:return
        try:
            root=Path(path)/('emcd_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));export_result(self.emcd_result,root);self.statusBar().showMessage('Exported completed run: '+str(root))
        except Exception as exc:self.error(str(exc))
