"""MDFF, propagation controls and worker lifecycle; calculations live in emcd_forward."""
from dataclasses import asdict
from pathlib import Path
import datetime,json,logging
import threading,time
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
        self.cancellation_event=threading.Event();self.cancellation_times={}
    def requestInterruption(self):
        # Called directly from the GUI, never queued into this busy thread.
        self.cancellation_times.setdefault('requested',time.perf_counter())
        self.cancellation_event.set();super().requestInterruption()
    def isInterruptionRequested(self):
        return self.cancellation_event.is_set() or super().isInterruptionRequested()
    def cancelled(self):
        requested=self.isInterruptionRequested()
        if requested:self.cancellation_times.setdefault('acknowledged',time.perf_counter())
        return requested
    def run(self):
        try:
            logging.getLogger('emcd_sim.gui').info('Calculate method=%s model=%s source=%s sha256=%s', self.config.propagation, self.config.model, self.config.source, self.config.source_sha256)
            r=calculate(self.structure,self.settings,self.config,self.stage.emit,self.cancelled)
            if not self.cancelled():self.result.emit(r)
        except Cancelled:pass
        except Exception as exc:
            logging.getLogger('emcd_sim.gui').exception('Calculation failed')
            if not self.isInterruptionRequested():self.failed.emit(str(exc))
        finally:
            self.cancellation_times['stopped']=time.perf_counter()


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
        self.channeling_box=QtWidgets.QComboBox();self.channeling_box.addItems(['Single Channeling','Double Channeling']);self.form.addRow('Channeling Model',self.channeling_box)
        self.channeling_box.setToolTip('Single: entrance-only. Double: incoming and post-energy-loss outgoing elastic propagation; actual independent BW/MS engines.')
        self.channeling_box.currentIndexChanged.connect(self.emcd_stale)
        self.propagation_box=QtWidgets.QComboBox();self.propagation_box.addItems(['Bloch-wave','FFT Multislice','Both (BW / MS comparison)']);self.form.addRow('Propagation Method',self.propagation_box)
        self.propagation_box.currentIndexChanged.connect(self.emcd_stale)
        group=QtWidgets.QGroupBox('Multislice numerical settings');group.setCheckable(True);group.setChecked(False)
        body=QtWidgets.QWidget();outer=QtWidgets.QVBoxLayout(group);outer.addWidget(body);self.form.addRow(group);body.setVisible(False);group.toggled.connect(body.setVisible)
        saved=self.form;self.form=QtWidgets.QFormLayout(body)
        box=QtWidgets.QSpinBox();box.setRange(12,128);box.setSingleStep(2);box.setValue(32);self.spin['fft_grid']=box;self.form.addRow('FFT grid (even)',box);box.valueChanged.connect(self.emcd_stale)
        self.number('slice_step','Max slice step (nm)',.04,.001,1,self.emcd_stale)
        label=QtWidgets.QLabel('Verified FFT: Ni [017], or explicit [001] (200) systematic row. Incoming/outgoing beam support is matched in Double Channeling.');label.setWordWrap(True);self.form.addRow(label);self.form=saved
        self.row_projection=QtWidgets.QCheckBox('Explicit [001] (200) systematic-row approximation');self.form.addRow(self.row_projection)
        self.row_projection.setToolTip('Only for [001]. Excludes off-row ZOLZ beams and changes the projected elastic model. Exact (200) Bragg alignment does not establish physical two-beam isolation. [017] retains its full finite 2D ZOLZ basis.')
        self.row_projection.toggled.connect(self.refresh)

    def numerical_controls(self):
        for key,title,value,lo,hi in [('energy','Energy sampling points',241,9,501),('grid','Detector grid points',33,9,193),('depth','Depth integration nodes',64,2,1025),('subpixels','Aperture subpixels',64,4,256)]:
            box=QtWidgets.QSpinBox();box.setRange(lo,hi);box.setValue(value);self.spin[key]=box;self.form.addRow(title,box);box.valueChanged.connect(self.emcd_stale)
        self.number('halfwidth','Map halfwidth (Å⁻¹)',1,.1,10,self.emcd_stale)
        self.energy_scope=QtWidgets.QComboBox();self.energy_scope.addItems(['Full native energy-resolved spectrum','Selected L3/L2 samples only (not full EELS)']);self.form.addRow('Spectral coverage',self.energy_scope);self.energy_scope.currentIndexChanged.connect(self.emcd_stale)
        self.energy_scope.setToolTip('Full spectra evaluate every displayed energy. Double Channeling angular maps can be expensive. Selected samples are displayed as points, never a fabricated white-line shape. Settings are not reduced automatically.')
        self.angular_maps=QtWidgets.QCheckBox('Calculate angular maps');self.angular_maps.setChecked(True);self.form.addRow(self.angular_maps);self.angular_maps.toggled.connect(self.emcd_stale)
        self.angular_maps.setToolTip('When off, evaluate only nonzero fractional-detector support on the unchanged reciprocal grid. No grid, precision or physical parameter is reduced.')
        saved_form=self.form;group=QtWidgets.QGroupBox('Advanced post-edge diagnostics');group.setCheckable(True);group.setChecked(False);body=QtWidgets.QWidget();outer=QtWidgets.QVBoxLayout(group);outer.addWidget(body);self.form.addRow(group);body.hide();group.toggled.connect(body.setVisible);self.form=QtWidgets.QFormLayout(body)
        self.correction=QtWidgets.QCheckBox('Enable post-edge A/B correction');self.correction.setChecked(True);self.form.addRow(self.correction);self.correction.toggled.connect(self.emcd_stale)
        self.number('window_lo','Window start (eV)',878,1,10000,self.emcd_stale);self.number('window_hi','Window end (eV)',882,1,10000,self.emcd_stale)
        self.form=saved_form
        from .memory_budget import BUDGETS_MIB,DEFAULT_BUDGET_MIB
        self.memory_budget=QtWidgets.QComboBox()
        for budget in BUDGETS_MIB:self.memory_budget.addItem(f'{budget} MiB',budget)
        self.memory_budget.setCurrentIndex(BUDGETS_MIB.index(DEFAULT_BUDGET_MIB));self.memory_budget.currentIndexChanged.connect(self.emcd_stale)
        self.form.addRow('Estimated process memory budget',self.memory_budget)
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
        return ForwardSettings(channeling_model=('single','double')[self.channeling_box.currentIndex()],energy_scope=('full','edges')[self.energy_scope.currentIndex()],angular_maps=self.angular_maps.isChecked(),systematic_row=self.row_projection.isChecked(),memory_budget_mib=self.memory_budget.currentData(),propagation=['bloch','fft-multislice','both'][self.propagation_box.currentIndex()],fft_grid=self.spin['fft_grid'].value(),slice_step=self.spin['slice_step'].value(),model=mode,source=self.source_path.text(),source_sha256=self.source_info['sha256'] if self.source_info else '',axis_declared=self.declaration.isChecked(),magnetization=axis,
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
            self.memory_label.setText(f"{info['bw_beams']} common BW beams; {info['fft_harmonics']} FFT harmonics. Dense kernel {info['dense_working_estimate_mib']:.1f} MiB; estimated arrays {info['estimated_working_mib']:.1f} MiB.\nEstimated process peak {info['estimated_process_peak_mib']:.1f} / {cfg.memory_budget_mib} MiB; available RAM {info['available_ram_mib']:.1f} MiB (50% allowed). Includes RSS, allocation margin and active calculations; not a guaranteed peak.")
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
        except Exception as exc:reason=reason or str(exc);fresh=False;self.memory_label.setText('Calculation unavailable: '+str(exc))
        self.emcd_button.setEnabled(not reason and not self.busy);self.emcd_button.setToolTip(reason or 'Run the selected incoming-wave propagation and shared EMCD/EELS contraction')
        if self.emcd_result:
            text=self.emcd_result['config'].channeling_model.title()+' Channeling | '+('Completed-run geometry and spectra; inputs match.' if fresh else 'STALE RESULT — current inputs differ; showing saved geometry and spectra.')
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
        self.worker=EMCDWorker(structure,s,cfg);self.worker.stage.connect(self.emcd_stage);self.worker.result.connect(self.emcd_completed);self.worker.failed.connect(self.emcd_failed);self.worker.finished.connect(self.emcd_finished);self.worker.start()
    def emcd_stage(self,message):
        # Queued progress from before Cancel must not hide the pending request.
        if not self.worker.isInterruptionRequested():self.statusBar().showMessage(message)
    def emcd_failed(self,message):
        if not self.worker.isInterruptionRequested():self.preview_failed(message)
    def emcd_completed(self,result):
        if self.worker.isInterruptionRequested():return
        self.emcd_result=result;self.run_outcome='completed'
        self.register_completed(result)
        for i,view in ((1,self.maps_view),(2,self.eels_view)):
            self.tabs.setTabEnabled(i,i!=1 or bool(result['maps']));view.set_result(result)
        for i,view in ((5,self.diffraction_view),(6,self.overview_view)):
            self.tabs.setTabEnabled(i,i==5 or len(result.get('methods',{}))==2);view.set_result(result)
        self.tabs.setTabEnabled(3,True);self.comparison.setPlainText(comparison_text(result));self.tabs.setCurrentIndex(2);self.emcd_stale();self.emcd_ready.emit()
    def emcd_finished(self):
        self.finished();self.emcd_stale()
        if self.worker.isInterruptionRequested():
            self.run_outcome='cancelled';self.worker.cancellation_times['idle']=time.perf_counter()
            self.statusBar().showMessage('Calculation cancelled.')
        else:self.statusBar().showMessage('EMCD '+('completed.' if self.run_outcome=='completed' else 'failed; no new result registered.'))
    def save_emcd(self):
        if self.emcd_result is None:self.error('Run EMCD/EELS successfully first.');return
        path=QtWidgets.QFileDialog.getExistingDirectory(self,'Export completed EMCD result (new subfolder)')
        if not path:return
        try:
            root=Path(path)/('emcd_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));export_result(self.emcd_result,root,component_mode=self.eels_view.component_mode.currentData(),map_signal_mode=self.maps_view.component_mode.currentData());self.statusBar().showMessage('Exported completed run: '+str(root))
        except Exception as exc:self.error(str(exc))
