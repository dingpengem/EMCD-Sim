"""Native Qt diffraction controls and Stage B Bloch-wave EMCD/EELS."""
from dataclasses import asdict
from pathlib import Path
import argparse,json,sys
import numpy as np
from PySide6 import QtCore,QtWidgets,QtGui
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg,NavigationToolbar2QT
from matplotlib.patches import Circle
from .geometry import (Structure,Settings,indices,geometry,preview,excitation,
                       align_bragg,za_from_tilt,tilt_from_za)


class PreviewWorker(QtCore.QThread):
    result=QtCore.Signal(object)
    failed=QtCore.Signal(str)
    def __init__(self,structure,settings):
        super().__init__();self.structure=structure;self.settings=settings
    def run(self):
        try:
            if self.isInterruptionRequested():return
            result=preview(self.structure,self.settings)
            if not self.isInterruptionRequested():self.result.emit(result)
        except Exception as exc:self.failed.emit(str(exc))


from .stage_b import StageB


class MainWindow(StageB,QtWidgets.QMainWindow):
    preview_ready=QtCore.Signal()
    def __init__(self):
        super().__init__();self.setWindowTitle('EMCD-Sim Desktop — Stage A: diffraction geometry')
        self.resize(1550,960);self.structure=Structure.nickel();self.last_result=None;self.worker=None;self.busy=False
        self.history=[];self.detectors=np.zeros((2,2));self.spin={};self.dialogs=[];self.run_outcome=None
        self.splitter=QtWidgets.QSplitter();self.setCentralWidget(self.splitter)
        self.inputs=QtWidgets.QWidget();self.form_layout=QtWidgets.QVBoxLayout(self.inputs)
        scroll=QtWidgets.QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(self.inputs);scroll.setMinimumWidth(320);self.splitter.addWidget(scroll)
        self.section('A. Crystal Structure');self.button('FCC Ni default',self.default_structure);self.button('Load CIF…',self.load_cif)
        self.structure_label=QtWidgets.QLabel();self.structure_label.setWordWrap(True);self.form.addRow(self.structure_label)
        self.button('Inspect structure…',self.inspect_structure)
        self.section('B. Zone Axis & Diffraction')
        self.zone=QtWidgets.QLineEdit('0 1 7');self.zone.setToolTip('Direct-lattice [u v w]; changes the actual oriented cell.');self.form.addRow('Nominal zone [uvw]',self.zone)
        self.target=QtWidgets.QLineEdit('2 0 0');self.target.setToolTip('Target Miller indices; must belong to the oriented finite basis.');self.form.addRow('Target (hkl)',self.target)
        self.button('Apply orientation / target',self.apply_orientation)
        self.mode=QtWidgets.QComboBox();self.mode.addItems(['Select reflection','Set projected ZA','Move detector A','Move detector B']);self.form.addRow('Click mode',self.mode)
        self.number('tx','Tilt X (mrad)',-7.116725439974256,-100,100,self.tilt_changed)
        self.number('ty','Tilt Y (mrad)',0,-100,100,self.tilt_changed)
        self.number('qx','ZA qx (cycles/A)',0,-20,20,self.za_changed)
        self.number('qy','ZA qy (cycles/A)',0,-20,20,self.za_changed)
        self.step=QtWidgets.QComboBox();self.step.addItems(['0.01','0.1','1']);self.step.setCurrentText('0.1');self.step.currentTextChanged.connect(self.step_changed);self.form.addRow('Tilt step (mrad)',self.step)
        self.lock=QtWidgets.QComboBox();self.lock.addItems(['None','X','Y']);self.form.addRow('Lock for Bragg alignment',self.lock)
        self.align_button=self.button('Align to selected Bragg',self.align)
        self.button('Reset to zone axis',lambda:self.set_tilt((0,0)))
        self.button('Reset to reference geometry',self.reset_reference)
        self.section('C. Microscope & Sample')
        self.number('kv','Voltage (kV)',200,20,1000,self.tilt_changed)
        self.number('thickness','Thickness (nm)',30,.1,1000,self.refresh)
        self.section('D. MDFF Model',False)
        self.mdff_controls()
        self.section('E. Propagation Method')
        method=QtWidgets.QLabel('Bloch-wave entrance channeling\nMultislice: disabled until Stage C');method.setWordWrap(True);self.form.addRow(method)
        self.section('F. Calculation Settings')
        self.number('beam','Beam cutoff (cycles/A)',3.2,.2,6.5,self.refresh)
        self.number('potential','Potential cutoff (cycles/A)',2.2,.1,6.5,self.refresh)
        self.number('b','Debye–Waller B (A²)',0,0,10,self.refresh)
        self.numerical_controls()
        self.section('Virtual detectors')
        self.show_detectors=QtWidgets.QCheckBox('Show physical A/B apertures');self.show_detectors.setChecked(True);self.show_detectors.toggled.connect(self.refresh);self.form.addRow(self.show_detectors)
        for key,label,val in [('ax','A qx',0),('ay','A qy',0),('bx','B qx',0),('by','B qy',0)]:self.number(key,label+' (cycles/A)',val,-20,20,self.detectors_changed)
        self.number('radius','Radius (cycles/A)',.0908059024,.001,2,self.refresh)
        self.button('Restore Thales A/B',self.restore_detectors)
        self.pair_label=QtWidgets.QLabel();self.pair_label.setWordWrap(True);self.form.addRow(self.pair_label)
        self.section('G. Output Settings',False)
        self.button('Export current plot PNG / SVG…',self.export_plot)
        self.button('Save elastic preview…',self.save_preview)
        self.button('Export completed EMCD / EELS...',self.save_emcd)
        self.form_layout.addStretch()
        center=QtWidgets.QWidget();layout=QtWidgets.QVBoxLayout(center);self.figure=Figure(layout='constrained');self.canvas=FigureCanvasQTAgg(self.figure);self.ax=self.figure.add_subplot()
        self.toolbar=NavigationToolbar2QT(self.canvas,self);layout.addWidget(self.toolbar)
        actions=QtWidgets.QHBoxLayout();layout.addLayout(actions)
        self.run_button=QtWidgets.QPushButton('Preview diffraction');self.run_button.clicked.connect(self.start_preview);actions.addWidget(self.run_button)
        self.cancel_button=QtWidgets.QPushButton('Cancel');self.cancel_button.clicked.connect(self.cancel);self.cancel_button.setEnabled(False);actions.addWidget(self.cancel_button)
        fit=QtWidgets.QPushButton('Show full basis');fit.clicked.connect(lambda:self.refresh(fit=True));actions.addWidget(fit)
        maximum=QtWidgets.QPushButton('Maximize / restore viewer');maximum.clicked.connect(self.maximize_view);actions.addWidget(maximum)
        layout.addWidget(self.canvas,1);self.selection=QtWidgets.QLabel();self.selection.setWordWrap(True);layout.addWidget(self.selection)
        self.progress=QtWidgets.QProgressBar();self.progress.setRange(0,1);self.progress.setValue(0);layout.addWidget(self.progress)
        self.splitter.addWidget(center);self.tabs=QtWidgets.QTabWidget();self.tabs.setMinimumWidth(300)
        self.table=QtWidgets.QTableWidget(0,5);self.table.setHorizontalHeaderLabels(['hkl','qx','qy','s_g (1/A)','Exit I (last preview)'])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers);self.tabs.addTab(self.table,'Diffraction')
        for title in ('EMCD Angular Maps','Virtual Detector EELS','Magnetic / Nonmagnetic'):
            index=self.tabs.addTab(QtWidgets.QLabel('Not calculated — later milestone.'),title);self.tabs.setTabEnabled(index,False)
        self.info=QtWidgets.QPlainTextEdit();self.info.setReadOnly(True);self.tabs.addTab(self.info,'Calculation Information')
        self.splitter.addWidget(self.tabs);self.splitter.setSizes([340,820,390]);self.saved_sizes=None
        self.canvas.mpl_connect('button_press_event',self.clicked)
        self.zone.returnPressed.connect(self.apply_orientation);self.target.returnPressed.connect(self.apply_orientation)
        self.sync_za();self.restore_detectors();self.refresh();self.setup_stage_b()

    def section(self,title,expanded=True):
        group=QtWidgets.QGroupBox(title);group.setCheckable(True);group.setChecked(expanded);body=QtWidgets.QWidget();self.form=QtWidgets.QFormLayout(body)
        outer=QtWidgets.QVBoxLayout(group);outer.addWidget(body);body.setVisible(expanded);group.toggled.connect(body.setVisible);self.form_layout.addWidget(group)

    def number(self,key,label,value,lo,hi,callback):
        box=QtWidgets.QDoubleSpinBox();box.setRange(lo,hi);box.setDecimals(10);box.setValue(value);box.setSingleStep(.1);box.setKeyboardTracking(False)
        box.setToolTip(label+'; editing changes configuration only, not a simulation.');self.spin[key]=box;self.form.addRow(label,box);box.valueChanged.connect(callback)

    def button(self,title,callback):
        button=QtWidgets.QPushButton(title);button.clicked.connect(lambda checked=False:callback());self.form.addRow(button);return button

    def settings(self):
        return Settings(zone=indices(self.zone.text(),True),target=indices(self.target.text()),tilt=(self.spin['tx'].value(),self.spin['ty'].value()),voltage=self.spin['kv'].value(),
            thickness=self.spin['thickness'].value(),beam_cutoff=self.spin['beam'].value(),potential_cutoff=self.spin['potential'].value(),b_factor=self.spin['b'].value())

    def set_values(self,values):
        for key,value in values.items():
            with QtCore.QSignalBlocker(self.spin[key]):self.spin[key].setValue(float(value))

    def sync_za(self):
        q=za_from_tilt((self.spin['tx'].value(),self.spin['ty'].value()),self.spin['kv'].value());self.set_values(dict(qx=q[0],qy=q[1]))
    def tilt_changed(self,*_):self.sync_za();self.refresh()
    def za_changed(self,*_):
        tilt=tilt_from_za((self.spin['qx'].value(),self.spin['qy'].value()),self.spin['kv'].value())
        if max(abs(tilt))>100:self.statusBar().showMessage('ZA request exceeds ±100 mrad GUI range; unchanged.');self.sync_za();return
        self.set_tilt(tilt)
    def set_tilt(self,tilt):
        if max(abs(np.asarray(tilt)))>100:raise ValueError('Tilt exceeds ±100 mrad GUI range')
        self.set_values(dict(tx=tilt[0],ty=tilt[1]));self.sync_za();self.refresh()
    def step_changed(self,text):
        for k in ('tx','ty'):self.spin[k].setSingleStep(float(text))

    def apply_orientation(self):
        try:
            s=self.settings();self.zone.setText(' '.join(map(str,s.zone)));self.refresh()
            if s.target in self.current[2]:self.restore_detectors()
        except Exception as exc:self.error(str(exc))

    def refresh(self,*_,fit=False):
        if not hasattr(self,'canvas'):return
        try:
            s=self.settings();self.current=geometry(self.structure,s);self.drawn_settings=s;crystal,R,hkl,g,microscope=self.current
            target_valid=s.target in hkl and s.target!=(0,0,0)
            supported=not self.structure.elastic_reason and target_valid
            self.run_button.setEnabled(supported and not self.busy);self.align_button.setEnabled(target_valid and not self.busy)
            self.structure_label.setText(f'{self.structure.atoms.get_chemical_formula()} · {len(self.structure.atoms)} atoms\n'+(self.structure.elastic_reason or 'Ni IAM BW elastic preview supported.'))
            old_limits=(self.ax.get_xlim(),self.ax.get_ylim()) if self.ax.has_data() else ((-1.3,1.3),(-1.3,1.3))
            self.ax.clear();fresh=self.last_result is not None and self.last_result['settings']==asdict(s) and self.last_result['source']==self.structure.source and self.last_result['source_sha256']==self.structure.sha256
            self.tabs.setTabText(0,'Diffraction (current)' if fresh else 'Diffraction (last preview)')
            if fresh:
                intensity=self.last_result['intensity'];self.ax.scatter(g[:,0],g[:,1],s=20+550*intensity,c=intensity,cmap='viridis',vmin=0,vmax=1,edgecolors='black',linewidths=.5)
            else:self.ax.scatter(g[:,0],g[:,1],s=28,facecolors='none',edgecolors='.5')
            for h,(gx,gy) in zip(hkl,g):self.ax.annotate(str(h),(gx,gy),xytext=(4,5),textcoords='offset points',fontsize=7)
            self.ax.plot(0,0,'kx',ms=7,label='Transmitted (000)')
            za=za_from_tilt(s.tilt,s.voltage);zone_label='['+' '.join(map(str,s.zone))+']'
            self.ax.plot(*za,marker='*',color='gold',mec='black',ms=12,ls='',label=f'ZA {zone_label}')
            if target_valid:
                gg=g[hkl.index(s.target)];self.ax.plot(*gg,'rs',mfc='none',ms=12,label=f'Target {s.target}')
                self.ax.add_patch(Circle(gg/2,np.linalg.norm(gg)/2,fill=False,color='teal',ls=':',label='Thales (000)—target'))
                error=float(excitation(gg,s.tilt,s.voltage));j=hkl.index(s.target)
                value=f'{self.last_result["intensity"][j]:.7g}' if fresh else 'not calculated for current inputs'
                self.selection.setText(f'Target {s.target}: q=({gg[0]:.6f}, {gg[1]:.6f}) cycles/A; |g|={np.linalg.norm(gg):.6f}\ns={error:+.9g} 1/A; exit intensity={value}\nZA=({za[0]:.6f}, {za[1]:.6f}) cycles/A; tilt=({s.tilt[0]:.8f}, {s.tilt[1]:.8f}) mrad')
            else:self.selection.setText('Target is not a nonzero reflection in this oriented basis. Click a valid spot or enter its hkl; no intensity is calculated.')
            if self.show_detectors.isChecked():
                for name,p in zip(('A','B'),self.detectors):
                    self.ax.add_patch(Circle(p,self.spin['radius'].value(),fill=False,color='purple',ls='-' if name=='A' else '--'));self.ax.annotate(name,p,xytext=(6,-10),textcoords='offset points')
            self.pair_label.setText('Exact y-mirrored A/B pair.' if np.allclose(self.detectors[0],[self.detectors[1,0],-self.detectors[1,1]],atol=1e-9,rtol=0) else 'Manual / non-y-mirrored A/B pair. Mirrored-map analysis will require validation.')
            limits=((-s.beam_cutoff-.2,s.beam_cutoff+.2),)*2 if fit else old_limits
            self.ax.set(xlim=limits[0],ylim=limits[1],aspect='equal',xlabel='qx (cycles/A)',ylabel='qy (cycles/A)',title='Elastic diffraction — exit intensities' if fresh else 'Current reciprocal geometry — no current intensities')
            self.ax.legend(fontsize=7,loc='upper right');self.canvas.draw_idle()
            self.info.setPlainText(self.structure.description()+f'\n\nNominal zone: {s.zone}\nR crystal-to-local:\n{R}\nIncluded beams: {len(hkl)} (full radial cutoff)\n'
                f'Current tilt: {s.tilt} mrad\nZA: {za} cycles/A\nSelected target: {s.target}\n'
                'Stage B: BW entrance-channeling MDFF and EELS available through explicit Run EMCD / EELS.\nNi projected ZOLZ IAM; no outgoing channeling, absorption/TDS or physical CBED disks.\n'
                + ('Current inputs match last completed preview.' if fresh else 'Inputs differ from last preview, or no preview exists. Right diffraction table is the last completed result.')
                +f'\nCompleted previews this session: {len(self.history)}')
            self.statusBar().showMessage(f'{len(hkl)} included reciprocal points. '+('Current preview.' if fresh else 'Geometry only; press Preview diffraction explicitly.'))
        except Exception as exc:
            self.structure_label.setText(f'{self.structure.atoms.get_chemical_formula()} · {len(self.structure.atoms)} atoms\n'+(self.structure.elastic_reason or 'Ni IAM species supported; geometry needs correction.'))
            self.info.setPlainText(self.structure.description()+'\n\nNo valid current geometry: '+str(exc))
            self.run_button.setEnabled(False);self.align_button.setEnabled(False);self.tabs.setTabText(0,'Diffraction (last preview)');self.ax.clear();self.ax.set_title('Invalid configuration — no current plot');self.canvas.draw_idle();self.selection.setText(str(exc));self.statusBar().showMessage(str(exc))

        self.emcd_stale()

    def clicked(self,event):
        if self.busy or event.inaxes is not self.ax or event.button!=1 or self.toolbar.mode:return
        if event.xdata is None or event.ydata is None:return
        try:
            if self.settings()!=getattr(self,'drawn_settings',None):
                self.refresh();self.statusBar().showMessage('Inputs changed: geometry refreshed. Click again in the updated view.');return
        except Exception as exc:self.error(str(exc));return
        point=np.array([event.xdata,event.ydata]);mode=self.mode.currentIndex()
        try:
            if mode==1:self.set_tilt(tilt_from_za(point,self.spin['kv'].value()))
            elif mode in (2,3):self.detectors[mode-2]=point;self.sync_detectors();self.refresh()
            else:
                hkl,g=self.current[2:4];delta=g-point;pixel_delta=self.ax.transData.transform(g)-self.ax.transData.transform(point)
                j=int(np.argmin(np.sum(pixel_delta**2,axis=1)))
                if np.linalg.norm(pixel_delta[j])>16 or hkl[j]==(0,0,0):return
                self.target.setText(' '.join(map(str,hkl[j])));self.restore_detectors()
        except Exception as exc:self.error(str(exc))

    def align(self):
        try:
            s=self.settings();_,_,hkl,g,_=geometry(self.structure,s);self.set_tilt(align_bragg(g[hkl.index(s.target)],s.tilt,s.voltage,self.lock.currentText()))
        except Exception as exc:self.error(str(exc))
    def reset_reference(self):
        self.zone.setText('0 1 7');self.target.setText('2 0 0');self.set_tilt((0,0));self.lock.setCurrentText('Y');self.align();self.restore_detectors()
    def sync_detectors(self):self.set_values(dict(ax=self.detectors[0,0],ay=self.detectors[0,1],bx=self.detectors[1,0],by=self.detectors[1,1]))
    def detectors_changed(self,*_):
        self.detectors=np.array([[self.spin['ax'].value(),self.spin['ay'].value()],[self.spin['bx'].value(),self.spin['by'].value()]]);self.refresh()
    def restore_detectors(self):
        try:
            s=self.settings();_,_,hkl,g,_=geometry(self.structure,s);gg=g[hkl.index(s.target)];perp=np.array([-gg[1],gg[0]])
            self.detectors=np.array([gg/2+perp/2,gg/2-perp/2]);self.sync_detectors();self.refresh()
        except Exception as exc:self.statusBar().showMessage(str(exc))

    def default_structure(self):self.structure=Structure.nickel();self.last_result=None;self.table.setRowCount(0);self.reset_reference()
    def load_cif(self):
        path,_=QtWidgets.QFileDialog.getOpenFileName(self,'Load crystal structure','','CIF files (*.cif)')
        if path:
            try:self.structure=Structure.from_cif(path);self.last_result=None;self.table.setRowCount(0);self.refresh();self.inspect_structure()
            except Exception as exc:self.error(str(exc))
    def inspect_structure(self):
        dialog=QtWidgets.QDialog(self);dialog.setWindowTitle('Crystal structure — ASE import');dialog.resize(650,500);layout=QtWidgets.QVBoxLayout(dialog)
        text=QtWidgets.QPlainTextEdit(self.structure.description());text.setReadOnly(True);layout.addWidget(text);dialog.show();self.dialogs.append(dialog)
    def start_preview(self):
        if self.busy:return
        try:s=self.settings();actual=geometry(self.structure,s)
        except Exception as exc:self.error(str(exc));return
        if self.structure.elastic_reason:self.error(self.structure.elastic_reason);return
        if s.target not in actual[2] or s.target==(0,0,0):self.error('Select a valid nonzero target');return
        self.refresh()
        self.busy=True;self.run_outcome='running';self.inputs.setEnabled(False);self.run_button.setEnabled(False);self.cancel_button.setEnabled(True);self.progress.setRange(0,0);self.emcd_button.setEnabled(False)
        self.statusBar().showMessage('Preparing crystal / selecting basis / running Bloch-wave elastic preview…')
        self.worker=PreviewWorker(Structure(self.structure.atoms.copy(),self.structure.source,self.structure.sha256,self.structure.import_warnings),s)
        self.worker.result.connect(self.completed);self.worker.failed.connect(self.preview_failed);self.worker.finished.connect(self.finished);self.worker.start()
    def completed(self,result):
        if self.worker.isInterruptionRequested():return
        self.run_outcome='completed'
        self.last_result=result;self.history.append(result);self.table.setRowCount(len(result['beam_hkl']))
        for row,(h,g,s,i) in enumerate(zip(result['beam_hkl'],result['g'],result['s'],result['intensity'])):
            for col,value in enumerate((str(tuple(int(v) for v in h)),f'{g[0]:.6f}',f'{g[1]:.6f}',f'{s:+.8g}',f'{i:.7g}')):self.table.setItem(row,col,QtWidgets.QTableWidgetItem(value))
        self.table.resizeColumnsToContents();self.refresh();self.preview_ready.emit()
    def finished(self):
        cancelled=self.worker.isInterruptionRequested();self.busy=False;self.inputs.setEnabled(True);self.progress.setRange(0,1);self.progress.setValue(int(not cancelled and self.run_outcome=='completed'))
        self.cancel_button.setEnabled(False);self.refresh()
        if cancelled:self.statusBar().showMessage('Preview cancelled; no cancelled result was registered.')
        elif self.run_outcome=='failed':self.statusBar().showMessage('Preview failed; no new result was registered.')
    def preview_failed(self,message):self.run_outcome='failed';self.error(message)
    def cancel(self):
        if self.worker:self.worker.requestInterruption();self.statusBar().showMessage('Cancellation requested; waiting for the current numerical stage to finish…')
    def closeEvent(self,event):
        if self.busy:self.cancel();event.ignore();return
        super().closeEvent(event)
    def maximize_view(self):
        if self.saved_sizes is None:self.saved_sizes=self.splitter.sizes();self.splitter.setSizes([0,sum(self.saved_sizes),0])
        else:self.splitter.setSizes(self.saved_sizes);self.saved_sizes=None
    def export_plot(self):
        path,_=QtWidgets.QFileDialog.getSaveFileName(self,'Export current diffraction viewer','','PNG (*.png);;SVG (*.svg)')
        if path:self.figure.savefig(path,dpi=160)
    def save_preview(self):
        if self.last_result is None:self.error('Calculate an elastic preview first.');return
        path=QtWidgets.QFileDialog.getExistingDirectory(self,'Save last completed elastic preview (new subfolder)')
        if not path:return
        try:
            import datetime
            root=Path(path)/('elastic_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'));root.mkdir()
            r=self.last_result;np.savez_compressed(root/'diffraction_pattern.npz',**{k:r[k] for k in ('beam_hkl','g','s','depth_nm','amplitudes','intensity','frame')})
            metadata={k:r[k] for k in ('settings','source','source_sha256','structure_description','model')};(root/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
            self.statusBar().showMessage('Saved last completed elastic preview: '+str(root))
        except Exception as exc:self.error(str(exc))
    def error(self,message):QtWidgets.QMessageBox.warning(self,'EMCD-Sim',message)


def main():
    parser=argparse.ArgumentParser(description='EMCD-Sim desktop diffraction and BW EMCD/EELS interface')
    parser.add_argument('--smoke-screenshot',type=Path,help='Run a real default elastic preview, save a Qt window screenshot and exit')
    parser.add_argument('--smoke-emcd-screenshot',type=Path,help='Compute and export real default BW EMCD, capture native Qt results')
    parser.add_argument('--smoke-atomic',action='store_true',help='Use the atomic model for EMCD acceptance run')
    args=parser.parse_args();app=QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    if not QtGui.QFontDatabase.families():
        # Qt's offscreen Windows plugin may expose no system fonts. Use the
        # font already bundled with Matplotlib, rather than unreadable boxes.
        from matplotlib import get_data_path
        font_id=QtGui.QFontDatabase.addApplicationFont(str(Path(get_data_path())/'fonts/ttf/DejaVuSans.ttf'))
        families=QtGui.QFontDatabase.applicationFontFamilies(font_id)
        if families:app.setFont(QtGui.QFont(families[0],9))
    window=MainWindow();window.show()
    if args.smoke_screenshot:
        def capture():
            if window.busy:QtCore.QTimer.singleShot(100,capture);return
            args.smoke_screenshot.parent.mkdir(parents=True,exist_ok=True);window.grab().save(str(args.smoke_screenshot));app.quit()
        window.preview_ready.connect(lambda:QtCore.QTimer.singleShot(300,capture));QtCore.QTimer.singleShot(200,window.start_preview)
        QtCore.QTimer.singleShot(30000,lambda:app.exit(2))
    if args.smoke_emcd_screenshot:
        if args.smoke_atomic:window.model_box.setCurrentIndex(1)
        def capture_emcd():
            if window.busy:QtCore.QTimer.singleShot(100,capture_emcd);return
            from .emcd_forward import export_result
            import datetime
            root=Path('outputs/gui_stage_b')/('atomic_' if args.smoke_atomic else 'xmcd_')
            root=root.parent/(root.name+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
            export_result(window.emcd_result,root)
            window.eels_view.maximize();window.tabs.setCurrentIndex(2)
            def grab():
                args.smoke_emcd_screenshot.parent.mkdir(parents=True,exist_ok=True)
                window.grab().save(str(args.smoke_emcd_screenshot));print('Completed EMCD export: '+str(root),flush=True);app.quit()
            QtCore.QTimer.singleShot(700,grab)
        window.emcd_ready.connect(lambda:QtCore.QTimer.singleShot(300,capture_emcd));QtCore.QTimer.singleShot(300,window.start_emcd)
        QtCore.QTimer.singleShot(240000,lambda:app.exit(2))
    return app.exec()
