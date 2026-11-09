"""Native Qt diffraction controls and Stage B Bloch-wave EMCD/EELS."""
from dataclasses import asdict
from pathlib import Path
import argparse,json,sys
import numpy as np
from PySide6 import QtCore,QtWidgets,QtGui
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from .responsive import ResponsiveCanvas as FigureCanvasQTAgg
from matplotlib.patches import Circle
from .geometry import (Structure,Settings,indices,geometry,preview,excitation,
                       align_bragg,za_from_tilt,tilt_from_za)


class PreviewWorker(QtCore.QThread):
    result=QtCore.Signal(object)
    failed=QtCore.Signal(str)
    def __init__(self,structure,settings,systematic_row=False):
        super().__init__();self.structure=structure;self.settings=settings;self.systematic_row=systematic_row
    def run(self):
        try:
            if self.isInterruptionRequested():return
            result=preview(self.structure,self.settings,systematic_row=self.systematic_row)
            if not self.isInterruptionRequested():self.result.emit(result)
        except Exception as exc:self.failed.emit(str(exc))


from .responsive import FlowLayout, ResponsiveLayout, CollapsibleSection
from .stage_b import StageB
from .results_browser import ProjectWorkspace


class MainWindow(ProjectWorkspace,StageB,QtWidgets.QMainWindow):
    preview_ready=QtCore.Signal()
    def __init__(self,workspace=None):
        super().__init__()
        from .runtime import LABEL
        self.setWindowTitle(LABEL)
        self.resize(1550,960);self.structure=Structure.nickel();self.last_result=None;self.worker=None;self.busy=False
        self.magnetization_mode='global'
        self.material_site_groups=None
        self.history=[];self.detectors=np.zeros((2,2));self.spin={};self.dialogs=[];self.run_outcome=None
        self.splitter=QtWidgets.QSplitter();self.setCentralWidget(self.splitter)
        self.inputs=QtWidgets.QWidget();self.form_layout=QtWidgets.QVBoxLayout(self.inputs)
        scroll=QtWidgets.QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(self.inputs);scroll.setMinimumWidth(320);self.splitter.addWidget(scroll)
        self.section('Material');self.button('Open CIF…',self.load_cif)
        self.structure_label=QtWidgets.QLabel();self.structure_label.setWordWrap(True);self.form.addRow(self.structure_label)
        self.button('Inspect structure…',self.inspect_structure)
        self.button('3D Structure Viewer…',self.show_structure_viewer)
        from ..elastic_providers import CHOICES
        self.elastic_provider_box=QtWidgets.QComboBox()
        for label,key in CHOICES:self.elastic_provider_box.addItem(label,key)
        self.form.addRow('Elastic scattering provider',self.elastic_provider_box)
        self.elastic_provider_box.currentIndexChanged.connect(self.refresh)
        self.section('Zone Axis & Diffraction',key='B. Zone Axis & Diffraction')
        geometry_form=self.form;self.geometry_options=CollapsibleSection('Orientation / ZA options',expanded=False);self.geometry_options.setObjectName('geometry_options');self.geometry_options.header.setToolTip('Crystal orientation, target hkl, projected ZA coordinates and Bragg alignment lock');geometry_form.addRow(self.geometry_options);self.form=QtWidgets.QFormLayout(self.geometry_options.body);self.form.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapLongRows)
        self.zone=QtWidgets.QLineEdit('0 1 7');self.zone.setToolTip('Direct-lattice [u v w]; changes the actual oriented cell.');self.form.addRow('Nominal zone [uvw]',self.zone)
        self.target=QtWidgets.QLineEdit('2 0 0');self.target.setToolTip('Target Miller indices; must belong to the oriented finite basis.');self.form.addRow('Target (hkl)',self.target)
        self.basis_mode=QtWidgets.QComboBox();self.basis_mode.addItem('Full finite ZOLZ','full');self.basis_mode.addItem('Ideal 000 + target','two-beam');self.form.addRow('Diffraction basis',self.basis_mode);self.basis_mode.currentIndexChanged.connect(self.refresh)
        self.button('Apply orientation / target',self.apply_orientation)
        self.mode=QtWidgets.QComboBox();self.mode.addItems(['Select reflection','Set projected ZA','Move detector A','Move detector B']);self.form.addRow('Click mode',self.mode)
        self.show_laue=QtWidgets.QCheckBox('Show ZOLZ Laue circle');self.show_laue.setChecked(True)
        self.show_laue.setToolTip('Zero-excitation-error circle centered on projected ZA; not a Thales circle or intensity contour.')
        self.show_laue.toggled.connect(self.refresh);self.form.addRow(self.show_laue)
        self.number('qx','ZA qx (Å⁻¹)',0,-20,20,self.za_changed)
        self.number('qy','ZA qy (Å⁻¹)',0,-20,20,self.za_changed)
        self.lock=QtWidgets.QComboBox();self.lock.addItems(['None','X','Y']);self.form.addRow('Lock for Bragg alignment',self.lock)
        self.form=geometry_form
        self.number('tx','Tilt X (mrad)',Settings().tilt[0],-100,100,self.tilt_changed)
        self.number('ty','Tilt Y (mrad)',0,-100,100,self.tilt_changed)
        self.step=QtWidgets.QComboBox();self.step.addItems(['0.01','0.1','1']);self.step.setCurrentText('0.1');self.step.currentTextChanged.connect(self.step_changed);self.form.addRow('Tilt step (mrad)',self.step)
        self.align_button=self.button('Align to selected Bragg',self.align)
        self.button('Reset to zone axis',lambda:self.set_tilt((0,0)))
        self.button('Reset to reference geometry',self.reset_reference)
        self.section('Microscope & Sample',key='C. Microscope & Sample')
        self.number('kv','Voltage (kV)',300,20,1000,self.tilt_changed)
        self.number('thickness','Thickness (nm)',30,.1,1000,self.refresh)
        settings_form=self.form
        self.mdff_host=QtWidgets.QWidget(self);self.form=QtWidgets.QFormLayout(self.mdff_host)
        self.mdff_controls()
        self.mdff_host.hide();self.form=settings_form
        self.section('Propagation Method',key='E. Propagation Method')
        self.propagation_controls()
        self.section('Shared Calculation Settings',key='F. Shared Calculation Settings')
        self.numerical_controls()
        self.section('Virtual Detectors',key='Virtual detectors')
        self.show_detectors=QtWidgets.QCheckBox('Show physical A/B apertures');self.show_detectors.setChecked(True);self.show_detectors.toggled.connect(self.refresh);self.form.addRow(self.show_detectors)
        for key,label,val in [('ax','A qx',0),('ay','A qy',0),('bx','B qx',0),('by','B qy',0)]:self.number(key,label+' (Å⁻¹)',val,-20,20,self.detectors_changed)
        self.number('radius','Radius (Å⁻¹)',.0908059024,.001,2,self.refresh)
        self.button('Restore Thales A/B',self.restore_detectors)
        self.pair_label=QtWidgets.QLabel();self.pair_label.setWordWrap(True);self.form.addRow(self.pair_label)
        self.section('Output Settings',False,key='G. Output Settings')
        self.button('Export current plot PNG / SVG…',self.export_plot)
        self.button('Save elastic preview…',self.save_preview)
        self.button('Export completed EMCD / EELS...',self.save_emcd)
        self.form_layout.addStretch()
        center=QtWidgets.QWidget();layout=QtWidgets.QVBoxLayout(center);self.figure=Figure(layout='constrained');self.canvas=FigureCanvasQTAgg(self.figure);self.ax=self.figure.add_subplot()
        self.toolbar=NavigationToolbar2QT(self.canvas,self);layout.addWidget(self.toolbar)
        actions=FlowLayout();layout.addLayout(actions)
        self.run_button=QtWidgets.QPushButton('Preview diffraction');self.run_button.clicked.connect(self.start_preview);actions.addWidget(self.run_button)
        self.cancel_button=QtWidgets.QPushButton('Cancel');self.cancel_button.clicked.connect(self.cancel);self.cancel_button.setEnabled(False);actions.addWidget(self.cancel_button)
        self._basis_view_limits=None;self._basis_view_geometry=None
        self.basis_view_button=QtWidgets.QPushButton('Show full basis');self.basis_view_button.clicked.connect(self.toggle_basis_view);actions.addWidget(self.basis_view_button)
        maximum=QtWidgets.QPushButton('Maximize / restore viewer');maximum.clicked.connect(self.maximize_view);actions.addWidget(maximum)
        layout.addWidget(self.canvas,1);self.selection=QtWidgets.QLabel();self.selection.setWordWrap(True);self.diffraction_details=CollapsibleSection('Diffraction details',self.selection,expanded=False);self.diffraction_details.setObjectName('diffraction_details');layout.addWidget(self.diffraction_details)
        self.progress=QtWidgets.QProgressBar();self.progress.setRange(0,1);self.progress.setValue(0);layout.addWidget(self.progress)
        self.splitter.addWidget(center);self.tabs=QtWidgets.QTabWidget();self.tabs.setMinimumWidth(300)
        self.table=QtWidgets.QTableWidget(0,5);self.table.setHorizontalHeaderLabels(['hkl','qx (Å⁻¹)','qy (Å⁻¹)','s_g (Å⁻¹)','Exit I (a.u., last preview)'])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers);self.tabs.addTab(self.table,'Diffraction')
        for title in ('EMCD Angular Maps','Virtual Detector EELS','Magnetic / Nonmagnetic'):
            index=self.tabs.addTab(QtWidgets.QLabel('Not calculated — later milestone.'),title);self.tabs.setTabEnabled(index,False)
        self.info=QtWidgets.QPlainTextEdit();self.info.setReadOnly(True);self.tabs.addTab(self.info,'Calculation Information')
        self.splitter.addWidget(self.tabs);self.splitter.setSizes([340,820,390]);self.saved_sizes=None
        self.canvas.mpl_connect('button_press_event',self.clicked)
        self._za_drag=False
        self.canvas.mpl_connect('motion_notify_event',self.drag_za)
        self.canvas.mpl_connect('button_release_event',self.release_za)
        self.zone.returnPressed.connect(self.apply_orientation);self.target.returnPressed.connect(self.apply_orientation)
        self.sync_za();self.restore_detectors();self.refresh();self.setup_stage_b();self.setup_stage_d(workspace)
        self.responsive=ResponsiveLayout(self)
        self.model_box.setCurrentIndex(1)
        from .mdff_usability import GlobalMDFFDialog
        self.mdff_dialog=GlobalMDFFDialog(self)
        self.structure_view_action=QtGui.QAction('View 3D Crystal Structure…',self)
        self.structure_view_action.triggered.connect(self.show_structure_viewer)
        self.setup_project_session()
        from .parameter_wheel import protect_parameter_wheels
        protect_parameter_wheels(self)

    def section(self,title,expanded=True,*,key=None):
        group=CollapsibleSection(title.replace('&','&&'),expanded=expanded)
        group.setObjectName('settings_'+''.join(c if c.isalnum() else '_' for c in (key or title)))
        group.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,QtWidgets.QSizePolicy.Policy.Maximum)
        self.form=QtWidgets.QFormLayout(group.body);self.form.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapLongRows);self.form_layout.addWidget(group)

    def number(self,key,label,value,lo,hi,callback):
        box=QtWidgets.QDoubleSpinBox();box.setRange(lo,hi);box.setDecimals(10);box.setValue(value);box.setSingleStep(.1);box.setKeyboardTracking(False)
        box.setToolTip(label+'; editing changes configuration only, not a simulation.');self.spin[key]=box;self.form.addRow(label,box);box.valueChanged.connect(callback)

    def button(self,title,callback):
        button=QtWidgets.QPushButton(title);button.clicked.connect(lambda checked=False:callback());self.form.addRow(button);return button

    def settings(self):
        return Settings(zone=indices(self.zone.text(),True),target=indices(self.target.text()),tilt=(self.spin['tx'].value(),self.spin['ty'].value()),voltage=self.spin['kv'].value(),
            thickness=self.spin['thickness'].value(),beam_cutoff=self.spin['beam'].value(),potential_cutoff=self.spin['potential'].value(),b_factor=self.spin['b'].value(),basis_mode=self.basis_mode.currentData(),elastic_provider=self.elastic_provider_box.currentData())

    def set_values(self,values):
        changed=any(self.spin[key].value()!=float(value) for key,value in values.items())
        for key,value in values.items():
            with QtCore.QSignalBlocker(self.spin[key]):self.spin[key].setValue(float(value))
        if changed:self.mark_project_dirty()

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

    def invalidate_basis_view(self):
        self._basis_view_limits=None
        self.basis_view_button.setText('Show full basis')

    def toggle_basis_view(self):
        """Change only the viewport; pan/zoom and plotting data stay untouched."""
        if self._basis_view_geometry is None:return
        if self._basis_view_limits is None:
            self._basis_view_limits=(self.ax.get_xlim(),self.ax.get_ylim())
            bound=self.drawn_settings.beam_cutoff+.2
            limits=((-bound,bound),)*2
            self.basis_view_button.setText('Restore previous view')
        else:
            limits=self._basis_view_limits
            self.invalidate_basis_view()
        self.ax.set(xlim=limits[0],ylim=limits[1],aspect='equal')
        self.canvas.draw_idle()

    def refresh(self,*_,fit=False):
        if not hasattr(self,'canvas'):return
        if getattr(self,'_project_structure',self.structure) is not self.structure:self.mark_project_dirty()
        self._project_structure=self.structure
        viewer=getattr(self,'structure_viewer',None)
        if viewer is not None:viewer.set_structure(self.structure)
        self._za_drag=False
        self.resolve_numerical_ui()
        try:
            s=self.settings();self.current=geometry(self.structure,s,systematic_row=self.row_projection.isChecked());self.drawn_settings=s;crystal,R,hkl,g,microscope=self.current
            # Include marker geometry as well as the reciprocal basis. Intensity-
            # only refreshes keep the saved viewport; incompatible geometry also
            # clears Matplotlib's navigation history to prevent stale Home/Back.
            view_geometry=(s.zone,s.target,s.tilt,s.voltage,s.beam_cutoff,s.basis_mode,self.row_projection.isChecked(),
                self.structure.atoms.cell.array.tobytes(),self.structure.atoms.get_scaled_positions().tobytes(),
                tuple(self.structure.atoms.get_chemical_symbols()),tuple(hkl),g.tobytes())
            if view_geometry!=self._basis_view_geometry:
                self.invalidate_basis_view();self.toolbar.update()
            self._basis_view_geometry=view_geometry;self.basis_view_button.setEnabled(True)
            from ..geometry import electron_wavelength_angstrom
            angle=1000*electron_wavelength_angstrom(s.voltage)*s.beam_cutoff
            self.spin['beam'].setToolTip(f'BW: limits diffraction beams retained in the Bloch-wave eigenproblem and MDFF response. MS: limits retained diffraction beams used for MDFF contraction. Additional FFT harmonics may participate in MS propagation. g=1/d, Å⁻¹; no 2π conversion. Approximate angular equivalent λ|g|max = {angle:.4f} mrad at {s.voltage:g} kV. Not the EELS detector collection limit.')
            target_valid=s.target in hkl and s.target!=(0,0,0)
            elastic_reason=self.structure.elastic_reason_for(s.elastic_provider)
            preview_reason=self.preview_blocking_reason(s,hkl)
            supported=not preview_reason
            numerical_reason=self._numerical_error or ''
            self.run_button.setEnabled(supported and not self.busy);self.align_button.setEnabled(target_valid and not self.busy)
            elastic_notice=('Elastic Preview uses the displayed settings unchanged; no automatic preset was applied for these inputs. Inherited values are not independently convergence-validated for this material. MDFF/EELS automatic settings remain unavailable: '+numerical_reason if numerical_reason else '')
            target_notice=('Selected target is absent from the retained basis; full-basis elastic preview remains available. Choose a retained reflection for Bragg alignment.' if not target_valid else '')
            self.run_button.setToolTip(preview_reason or target_notice or elastic_notice or 'Calculate elastic diffraction for the current structure and settings.')
            self.structure_label.setText(f'{self.structure.atoms.get_chemical_formula()} · {len(self.structure.atoms)} atoms\n'+(elastic_reason or 'IAM BW elastic preview supported; EMCD material eligibility is separate.'))
            old_limits=(self.ax.get_xlim(),self.ax.get_ylim()) if self.ax.has_data() else ((-1.3,1.3),(-1.3,1.3))
            self.ax.clear();fresh=self.preview_is_current(s)
            self._diffraction_spots=self.ax.scatter(g[:,0],g[:,1],s=28,facecolors='none',edgecolors='.5',zorder=3)
            if elastic_reason:self._diffraction_spots.set_label('Unfiltered reciprocal-lattice points; no intensities')
            self.update_preview_status(s)
            for h,(gx,gy) in zip(hkl,g):self.ax.annotate(str(h),(gx,gy),xytext=(4,5),textcoords='offset points',fontsize=7,zorder=4)
            self.ax.plot(0,0,'kx',ms=7,label='Transmitted (000)',zorder=4)
            za=za_from_tilt(s.tilt,s.voltage);zone_label='['+' '.join(map(str,s.zone))+']'
            self._za_artist,=self.ax.plot(*za,marker='*',color='gold',mec='black',ms=12,ls='',label=f'ZA {zone_label}',zorder=6)
            self._laue_circle=Circle(za,np.linalg.norm(za),fill=False,color='darkorange',ls='--',lw=1.8,alpha=.95,
                label='ZOLZ Laue circle (s_g = 0)',zorder=2)
            self._laue_circle.set_visible(self.show_laue.isChecked() and np.linalg.norm(za)>1e-12)
            self.ax.add_patch(self._laue_circle)
            if target_valid:
                gg=g[hkl.index(s.target)];self.ax.plot(*gg,'rs',mfc='none',ms=12,label=f'Target {s.target}',zorder=6)
                self.ax.add_patch(Circle(gg/2,np.linalg.norm(gg)/2,fill=False,color='teal',ls=':',lw=1.2,alpha=.75,
                    label='Thales circle (000–target)',zorder=1))
            self.update_diffraction_details(s,fresh=fresh)
            if self.show_detectors.isChecked():
                for name,p in zip(('A','B'),self.detectors):
                    self.ax.add_patch(Circle(p,self.spin['radius'].value(),fill=False,color='purple',ls='-' if name=='A' else '--',zorder=5));self.ax.annotate(name,p,xytext=(6,-10),textcoords='offset points',zorder=5)
            self.pair_label.setText('Exact y-mirrored A/B pair.' if np.allclose(self.detectors[0],[self.detectors[1,0],-self.detectors[1,1]],atol=1e-9,rtol=0) else 'Manual / non-y-mirrored A/B pair. Mirrored-map analysis will require validation.')
            limits=((-s.beam_cutoff-.2,s.beam_cutoff+.2),)*2 if fit else old_limits
            plot_title=('Reciprocal lattice only — elastic provider unavailable' if elastic_reason else 'Elastic diffraction — exit intensities' if fresh else 'Current reciprocal geometry — no current intensities')
            self.ax.set(xlim=limits[0],ylim=limits[1],aspect='equal',xlabel='qx (Å⁻¹)',ylabel='qy (Å⁻¹)',title=plot_title)
            self.update_diffraction_legend();self.canvas.draw_idle()
            support=('explicit ideal 000 + target two-beam basis' if s.basis_mode=='two-beam' else
                'explicit target systematic row' if self.row_projection.isChecked() else 'full radial ZOLZ cutoff')
            self.info.setPlainText(self.structure.description()+f'\n\nNominal zone: {s.zone}\nR crystal-to-local:\n{R}\nIncluded beams: {len(hkl)} ({support})\n'
                f'Current tilt: {s.tilt} mrad\nZA: {za} Å⁻¹\nSelected target: {s.target}\n'
                'Generalized projected ZOLZ IAM: BW / FFT Single or Double Channeling EMCD/EELS through Run EMCD / EELS.\nSingle includes incoming diffraction; Double also includes reduced-energy outgoing diffraction. No absorption/TDS, atomic 3D potential or physical CBED disks.\n'
                + ('Current inputs match last completed preview.' if fresh else 'Inputs differ from last preview, or no preview exists. Right diffraction table is the last completed result.')
                +f'\nCompleted previews this session: {len(self.history)}'
                + ('\n'+elastic_reason+'\nOpen markers are unfiltered reciprocal-lattice points, not intensity-calculated reflections; systematic absences are not filtered without supported elastic factors.' if elastic_reason else '\n'+elastic_notice if elastic_notice else ''))
            self.statusBar().showMessage(f'{len(hkl)} included reciprocal points. '+(elastic_reason or elastic_notice or ('Current preview.' if fresh else 'Geometry only; press Preview diffraction explicitly.')))
        except Exception as exc:
            message=str(exc)
            beam_limit=isinstance(exc,ValueError) and 'beams exceed the interactive limit' in message
            if beam_limit:
                message+='\nSelect Manual (Advanced) in Numerical Settings, then lower the Beam / MDFF cutoff for this structure and zone. Loading a CIF retains previous settings. No cutoff or beam limit was changed automatically.'
            elif self.numerical_mode.currentIndex()==0:
                message+='\nSelect Manual (Advanced) to edit elastic cutoffs, or correct the zone/target. No numerical settings were changed automatically.'
            self.invalidate_basis_view();self._basis_view_geometry=None;self.basis_view_button.setEnabled(False);self.toolbar.update()
            self.structure_label.setText(f'{self.structure.atoms.get_chemical_formula()} · {len(self.structure.atoms)} atoms\n'+(self.structure.elastic_reason or 'IAM elastic species supported; geometry needs correction.'))
            self.info.setPlainText(self.structure.description()+'\n\nNo valid current geometry: '+message)
            self.run_button.setEnabled(False);self.align_button.setEnabled(False);self.tabs.setTabText(0,'Diffraction (last preview)');self.ax.clear();self.ax.set_title('Beam limit exceeded — no current plot' if beam_limit else 'Invalid configuration — no current plot')
            self.run_button.setToolTip(message)
            if beam_limit:
                self.ax.text(.5,.5,str(exc).split('.')[0]+'.\nSelect Manual (Advanced),\nthen lower the Beam / MDFF cutoff.',transform=self.ax.transAxes,ha='center',va='center',wrap=True)
            self.canvas.draw_idle();self.selection.setText(message);self.statusBar().showMessage(message)

        self.emcd_stale()

    def preview_is_current(self,s):
        return self.last_result is not None and self.last_result['settings']==asdict(s) and self.last_result.get('systematic_row',False)==self.row_projection.isChecked() and self.last_result['source']==self.structure.source and self.last_result['source_sha256']==self.structure.sha256

    def update_preview_status(self,s):
        fresh=self.preview_is_current(s)
        self.tabs.setTabText(0,'Diffraction (current)' if fresh else 'Diffraction (last preview)')
        spots=self._diffraction_spots
        if fresh:
            intensity=self.last_result['intensity']
            spots.set_facecolor('C0');spots.set_array(intensity);spots.set_cmap('viridis');spots.set_clim(0,1)
            spots.set_sizes(20+550*intensity);spots.set_edgecolor('black');spots.set_linewidth(.5)
        else:
            spots.set_array(None);spots.set_sizes(np.full(len(self.current[2]),28))
            spots.set_facecolor('none');spots.set_edgecolor('.5')
        return fresh

    def update_diffraction_legend(self):
        handles,labels=self.ax.get_legend_handles_labels()
        visible=[(h,l) for h,l in zip(handles,labels) if h.get_visible()]
        if visible:self.ax.legend(*zip(*visible),fontsize=7,loc='upper right')

    def update_diffraction_details(self,s,*,fresh=False):
        hkl,g=self.current[2:4];za=za_from_tilt(s.tilt,s.voltage);radius=float(np.linalg.norm(za))
        if s.target in hkl and s.target!=(0,0,0):
            j=hkl.index(s.target);gg=g[j];error=float(excitation(gg,s.tilt,s.voltage))
            value=f'{self.last_result["intensity"][j]:.7g}' if fresh else 'not calculated for current inputs'
            text=f'Target {s.target}: q=({gg[0]:.6f}, {gg[1]:.6f}) Å⁻¹; |g|={np.linalg.norm(gg):.6f}\ns={error:+.9g} Å⁻¹; exit intensity={value} a.u.'
        else:text='Target is not a nonzero retained reflection. Choose a valid spot for alignment or target intensity; other retained reflections can still be previewed in the full basis.'
        text+=f'\nZA=({za[0]:.6f}, {za[1]:.6f}) Å⁻¹; tilt=({s.tilt[0]:.8f}, {s.tilt[1]:.8f}) mrad'
        text+=f'\nLaue center: ({za[0]:.6f}, {za[1]:.6f}) Å⁻¹; Laue radius: {radius:.6f} Å⁻¹'
        if radius<=1e-12:text+=' — On zone axis'
        self.selection.setText(text)

    def drag_za(self,event):
        if not self._za_drag:return
        if self.busy or self.toolbar.mode or self.mode.currentIndex()!=1:
            self.release_za(event);return
        if not self.apply_za_event(event):return
        s=self.settings();za=za_from_tilt(s.tilt,s.voltage)
        self._za_artist.set_data([za[0]],[za[1]])
        self._laue_circle.set_center(za);self._laue_circle.set_radius(np.linalg.norm(za))
        self._laue_circle.set_visible(self.show_laue.isChecked() and np.linalg.norm(za)>1e-12)
        fresh=self.update_preview_status(s)
        self.update_diffraction_details(s,fresh=fresh);self.update_diffraction_legend()
        self.ax.set_title('Elastic diffraction — exit intensities' if fresh else 'Projected ZA positioning — no current intensities')
        # Recheck dependent result labels on the first movement and when a
        # cached configuration is entered/left, not on every mouse event.
        signature=(fresh,self.emcd_result is not None and self.emcd_result['settings']==s)
        if signature!=self._za_drag_status:
            self.emcd_stale()
            # Automatic settings may require a normal geometry refresh once;
            # keep positioning active if that refresh produced a valid view.
            self._za_drag=self._basis_view_geometry is not None
            now=self.settings()
            self._za_drag_status=(self.preview_is_current(now),self.emcd_result is not None and self.emcd_result['settings']==now)
        text=self.info.toPlainText().splitlines()
        preview_text='Current inputs match last completed preview.' if fresh else 'Inputs differ from last preview, or no preview exists. Right diffraction table is the last completed result.'
        self.info.setPlainText('\n'.join(f'Current tilt: {s.tilt} mrad' if line.startswith('Current tilt:') else
            f'ZA: {za} Å⁻¹' if line.startswith('ZA:') else preview_text if line.startswith(('Current inputs match last completed preview.','Inputs differ from last preview,')) else line for line in text))
        self.statusBar().showMessage('Positioning ZA; release to apply geometry. No calculation started.')
        self.canvas.draw_idle()

    def apply_za_event(self,event):
        """Validate and apply one pointer position, without refreshing the plot."""
        if event.inaxes is not self.ax or event.xdata is None or event.ydata is None:return False
        point=np.array([event.xdata,event.ydata],float)
        if not np.isfinite(point).all():return False
        tilt=tilt_from_za(point,self.spin['kv'].value())
        if not np.isfinite(tilt).all() or max(abs(tilt))>100:
            self.statusBar().showMessage('ZA request exceeds ±100 mrad GUI range; unchanged.');return False
        before=(self.spin['tx'].value(),self.spin['ty'].value())
        self.set_values(dict(tx=tilt[0],ty=tilt[1]));self.sync_za()
        return before!=(self.spin['tx'].value(),self.spin['ty'].value())

    def release_za(self,event):
        if self._za_drag:
            self._za_drag=False
            if not self.busy and not self.toolbar.mode and self.mode.currentIndex()==1 and getattr(event,'button',None)==1:
                self.apply_za_event(event)
            if self.settings()!=self.drawn_settings:self.refresh()

    def clicked(self,event):
        if self.busy or event.inaxes is not self.ax or event.button!=1 or self.toolbar.mode:return
        if event.xdata is None or event.ydata is None:return
        try:
            if self.settings()!=getattr(self,'drawn_settings',None):
                self.refresh();self.statusBar().showMessage('Inputs changed: geometry refreshed. Click again in the updated view.');return
        except Exception as exc:self.error(str(exc));return
        point=np.array([event.xdata,event.ydata]);mode=self.mode.currentIndex()
        if not np.isfinite(point).all():return
        try:
            if mode==1:
                tilt=tilt_from_za(point,self.spin['kv'].value())
                if max(abs(tilt))>100:return
                self.set_tilt(tilt);self._za_drag=True;self._za_drag_status=None
            elif mode in (2,3):self.detectors[mode-2]=point;self.sync_detectors();self.refresh()
            else:
                hkl,g=self.current[2:4];delta=g-point;pixel_delta=self.ax.transData.transform(g)-self.ax.transData.transform(point)
                j=int(np.argmin(np.sum(pixel_delta**2,axis=1)))
                if np.linalg.norm(pixel_delta[j])>16 or hkl[j]==(0,0,0):return
                self.target.setText(' '.join(map(str,hkl[j])));self.restore_detectors()
        except Exception as exc:self.error(str(exc))

    def align(self):
        try:
            s=self.settings();_,_,hkl,g,_=geometry(self.structure,s,systematic_row=self.row_projection.isChecked());self.set_tilt(align_bragg(g[hkl.index(s.target)],s.tilt,s.voltage,self.lock.currentText()))
        except Exception as exc:self.error(str(exc))
    def reset_reference(self):
        self._loaded_fft_recipe=None
        with QtCore.QSignalBlocker(self.basis_mode):self.basis_mode.setCurrentIndex(0)
        with QtCore.QSignalBlocker(self.row_projection):self.row_projection.setChecked(False)
        self.zone.setText('0 1 7');self.target.setText('2 0 0');self.set_tilt((0,0));self.lock.setCurrentText('Y');self.align();self.restore_detectors()
    def sync_detectors(self):self.set_values(dict(ax=self.detectors[0,0],ay=self.detectors[0,1],bx=self.detectors[1,0],by=self.detectors[1,1]))
    def detectors_changed(self,*_):
        self.detectors=np.array([[self.spin['ax'].value(),self.spin['ay'].value()],[self.spin['bx'].value(),self.spin['by'].value()]]);self.refresh()
    def restore_detectors(self):
        try:
            s=self.settings();_,_,hkl,g,_=geometry(self.structure,s,systematic_row=self.row_projection.isChecked());gg=g[hkl.index(s.target)];perp=np.array([-gg[1],gg[0]])
            self.detectors=np.array([gg/2+perp/2,gg/2-perp/2]);self.sync_detectors();self.refresh()
        except Exception as exc:self.statusBar().showMessage(str(exc))

    def default_structure(self):self.structure=Structure.nickel();self.last_result=None;self.table.setRowCount(0);self.reset_reference()
    def load_cif(self):
        path,_=QtWidgets.QFileDialog.getOpenFileName(self,'Load crystal structure','','CIF files (*.cif)')
        if path:
            try:
                self.structure=Structure.from_cif(path)
                self.show_structure_viewer(show=False)
                self.last_result=None;self.table.setRowCount(0);self.refresh();self.inspect_structure()
            except Exception as exc:self.error(str(exc))
    def show_structure_viewer(self,*_,show=True):
        from .structure_viewer import CrystalStructureDialog
        if getattr(self,'structure_viewer',None) is None:
            self.structure_viewer=CrystalStructureDialog(self)
            self.structure_viewer.globalDirectionApplied.connect(self.set_material_magnetization)
            self.structure_viewer.editor.mdff_opener=self.open_mdff_context
            self.structure_viewer.magnetizationModeChanged.connect(self.set_magnetization_mode)
            self.structure_viewer.editor.changed.connect(self.emcd_stale)
            self.structure_viewer.editor.pendingChanged.connect(self.emcd_stale)
            self.structure_viewer.siteGroupsApplied.connect(lambda _:self.emcd_stale())
            self.structure_viewer.siteGroupsApplied.connect(lambda model:setattr(self,'material_site_groups',model))
            self.structure_viewer.editor.changed.connect(self.mark_project_dirty)
            self.structure_viewer.editor.pendingChanged.connect(self.mark_project_dirty)
            self.structure_viewer.set_magnetization_mode(self.magnetization_mode)
        self.structure_viewer.set_structure(self.structure,force=True)
        self.structure_viewer.set_global_direction(self.material_magnetization)
        self.material_site_groups=self.structure_viewer.accepted_site_groups
        if show:
            self.structure_viewer.show();self.structure_viewer.raise_();self.structure_viewer.activateWindow()

    def set_magnetization_mode(self,mode):
        if mode not in ('global','local'):raise ValueError('Expected global or local magnetization mode')
        changed=self.magnetization_mode!=mode
        if changed and mode=='local' and not getattr(self,'_session_restoring',False):
            try:self._saved_global_config=self.forward_settings(prepare=False)
            except ValueError:self._saved_global_config=None
        self.magnetization_mode=mode
        viewer=getattr(self,'structure_viewer',None)
        if viewer is not None and viewer.editor.magnetization_mode!=mode:viewer.set_magnetization_mode(mode)
        self.sync_magnetization_mode()
        if changed:self.emcd_stale()
        if changed:self.mark_project_dirty()

    def open_mdff_context(self,group_id=None):
        from .mdff_workspace import MDFFWorkspace
        for dialog in self.findChildren(MDFFWorkspace):
            if dialog.isVisible() and dialog._context_id!=group_id:
                if not dialog.confirm_context_exit():return None
                dialog.hide()
        if group_id is None:
            from .mdff_usability import configuration_dialog
            return configuration_dialog(self)
        editor=self.structure_viewer.editor
        item=next((editor.groups.topLevelItem(i) for i,r in enumerate(editor.rows()) if r[0]==group_id),None)
        if item is None:raise ValueError('Unknown MDFF editing context: '+group_id)
        editor.groups.setCurrentItem(item);dialog=editor.configure_mdff()
        dialog.set_context_choices(self,group_id);return dialog

    def sync_magnetization_mode(self):
        local=self.magnetization_mode=='local'
        self.axis.setEnabled(not local)
        if hasattr(self,'numerical_mode'):
            self.sync_sampling_controls()
        self.refresh_material_direction()
        if hasattr(self,'magnetization_mode_note'):
            self.magnetization_mode_note.setText('Global magnetization is locked while site-specific magnetization is enabled.'
                + ' Run uses applied group MDFFs and their energy grids.' if local else 'Global Magnetization Mode. Local directions are inactive; configure Global MDFF through the 3D viewer.')

    def set_material_magnetization(self,direction):
        vector=np.asarray(direction,float)
        if vector.shape!=(3,) or not np.isfinite(vector).all() or np.linalg.norm(vector)<1e-12:
            raise ValueError('Material M requires three finite nonzero crystal Cartesian components')
        changed=getattr(self,'material_magnetization',None)!=tuple(vector)
        self.material_magnetization=tuple(map(float,vector))
        with QtCore.QSignalBlocker(self.axis):self.axis.setText(' '.join(f'{v:.17g}' for v in vector))
        self.refresh_material_direction()
        if changed:
            viewer=getattr(self,'structure_viewer',None)
            if viewer is not None:viewer.set_global_direction(self.material_magnetization)
            if hasattr(self,'atomic_editor'):
                self.atomic_editor.invalidate_preview('Material magnetization changed')
                self.atomic_editor.preview_state.setText('STALE — Material magnetization changed; update preview.')
            self.emcd_stale();self.mark_project_dirty()

    def refresh_material_direction(self):
        try:text=' '.join(f'{v:.12g}' for v in self.material_direction())
        except ValueError:text='Invalid Material direction — correct Global Material M in the Viewer'
        for editor in (getattr(self,'atomic_editor',None),getattr(self,'manual_spectral',None)):
            if editor is not None and hasattr(editor,'direction'):
                with QtCore.QSignalBlocker(editor.direction):editor.direction.setText(text)
        if hasattr(self,'mdff_material_direction'):
            self.mdff_material_direction.setText('Global Material target M (crystal Cartesian, read-only): '+text+
                '. Set through Material → 3D Structure Viewer → Site Groups. '+
                ('Inactive for the current Local calculation.' if self.magnetization_mode=='local' else 'Global Magnetization Mode.'))

    def inspect_structure(self):
        dialog=QtWidgets.QDialog(self);dialog.setWindowTitle('Crystal structure — ASE import');dialog.resize(650,500);layout=QtWidgets.QVBoxLayout(dialog)
        text=QtWidgets.QPlainTextEdit(self.structure.description());text.setReadOnly(True);layout.addWidget(text);dialog.show();self.dialogs.append(dialog)
    def start_preview(self):
        if self.busy:return
        try:
            self.resolve_numerical_ui()
            # MDFF Automatic-policy failures do not invalidate displayed elastic
            # controls. Validate those controls and their provider independently;
            # Run EMCD / EELS retains its existing _numerical_error gate.
            s=self.settings();actual=geometry(self.structure,s,systematic_row=self.row_projection.isChecked())
            reason=self.preview_blocking_reason(s,actual[2])
            if reason:raise ValueError(reason)
        except Exception as exc:self.error(str(exc));return
        self.refresh()
        self.busy=True;self.run_outcome='running';self.inputs.setEnabled(False);self.run_button.setEnabled(False);self.cancel_button.setEnabled(True);self.progress.setRange(0,0);self.emcd_button.setEnabled(False)
        self.statusBar().showMessage('Preparing crystal / selecting basis / running Bloch-wave elastic preview…')
        self.worker=PreviewWorker(Structure(self.structure.atoms.copy(),self.structure.source,self.structure.sha256,self.structure.import_warnings),s,self.row_projection.isChecked())
        self.worker.result.connect(self.completed);self.worker.failed.connect(self.preview_failed);self.worker.finished.connect(self.finished);self.worker.start()

    def preview_blocking_reason(self,settings,hkl):
        reason=self.structure.elastic_reason_for(settings.elastic_provider)
        if reason:return reason
        if settings.basis_mode=='two-beam' and (settings.target not in hkl or settings.target==(0,0,0)):
            return 'Ideal two-beam preview requires a retained nonzero target; check its systematic absence and the beam cutoff.'
        return ''
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
        if self.busy and self.worker:
            self.worker.requestInterruption();self.statusBar().showMessage('Cancelling...')
    def closeEvent(self,event):
        if self.busy:self.cancel();event.ignore();return
        if not self.confirm_project_changes(self.close):event.ignore();return
        self.store_ui_preferences()
        super().closeEvent(event)
    def maximize_view(self):
        self.responsive.focus_plot('diffraction')
    def export_plot(self):
        path,_=QtWidgets.QFileDialog.getSaveFileName(self,'Export current diffraction viewer','','PNG (*.png);;SVG (*.svg)')
        if path:self.figure.savefig(path,dpi=160)
    def save_preview(self):
        if self.last_result is None:self.error('Calculate an elastic preview first.');return
        path=QtWidgets.QFileDialog.getExistingDirectory(self,'Save last completed elastic preview (new subfolder)')
        if not path:return
        try:
            import datetime
            root=Path(path)/('elastic_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
            from .project_io import save_elastic_project
            save_elastic_project(self.last_result,root)
            self.statusBar().showMessage('Saved last completed elastic preview: '+str(root))
        except Exception as exc:self.error(str(exc))
    def open_elastic_project_dialog(self):
        path=QtWidgets.QFileDialog.getExistingDirectory(self,'Open saved elastic-only project')
        if not path:return
        try:
            from .project_io import load_elastic_project
            result=load_elastic_project(path)
            dialog=QtWidgets.QDialog(self);dialog.setWindowTitle('Saved elastic diffraction (read-only)');dialog.resize(750,650)
            layout=QtWidgets.QVBoxLayout(dialog)
            layout.addWidget(QtWidgets.QLabel('Elastic only; current inputs unchanged. Provider: '+result['elastic_provider']['provider']))
            figure=Figure();canvas=FigureCanvasQTAgg(figure);layout.addWidget(canvas)
            ax=figure.add_subplot();g=result['g'];ax.scatter(g[:,0],g[:,1],c=result['intensity'],s=45)
            for h,(x,y) in zip(result['beam_hkl'],g):ax.annotate(str(tuple(int(v) for v in h)),(x,y),fontsize=7)
            ax.set(xlabel='qx (inverse angstrom)',ylabel='qy (inverse angstrom)',aspect='equal');canvas.draw()
            dialog.saved_elastic_result=result;dialog.show();self.dialogs.append(dialog)
        except Exception as exc:self.error(str(exc))
    def error(self,message):
        import logging
        logging.getLogger('emcd_sim.gui').warning('%s',message)
        QtWidgets.QMessageBox.warning(self,'EMCD-Sim',message)


def add_about_menu(window):
    from .runtime import LABEL, build_info
    action=window.menuBar().addMenu('Help').addAction('About / build')
    action.triggered.connect(lambda:QtWidgets.QMessageBox.information(window,LABEL,json.dumps(build_info(),indent=2)))
    return action


def main():
    parser=argparse.ArgumentParser(description='EMCD-Sim desktop diffraction and BW EMCD/EELS interface')
    parser.add_argument('--smoke-screenshot',type=Path,help='Run a real default elastic preview, save a Qt window screenshot and exit')
    parser.add_argument('--smoke-emcd-screenshot',type=Path,help='Compute and export real default BW EMCD, capture native Qt results')
    parser.add_argument('--smoke-atomic',action='store_true',help='Use the atomic model for EMCD acceptance run')
    parser.add_argument('--smoke-propagation',choices=['bloch','fft-multislice','both'],default='bloch')
    parser.add_argument('--cancellation-acceptance',type=Path,help='Run focused real-worker cancellation acceptance into a new directory')
    parser.add_argument('--cancellation-source',type=Path,help='Explicit external XMCD source for cancellation acceptance')
    parser.add_argument('--parallel-acceptance',type=Path,help='Opt-in resource-controls and bounded native BW Double acceptance')
    parser.add_argument('--parallel-project',type=Path,help='Optional checksummed saved case for diagnostic acceptance')
    parser.add_argument('--parallel-workers',type=int,help='Explicit supported detector-worker request for diagnostic acceptance')
    parser.add_argument('--desktop-acceptance',type=Path,help='Opt-in portable-build GUI and small BW/MS Single/Double acceptance')
    parser.add_argument('--desktop-orientation',choices=['001','017','117','111','710'],default='017',help='Orientation for the bounded desktop acceptance only')
    parser.add_argument('--scientific-acceptance',type=Path,help='Opt-in bounded matched Python/frozen Ni [017] raw-reversal reference')
    parser.add_argument('--unified-elastic-acceptance',type=Path,help='Opt-in bounded unified-provider native GUI acceptance in a new folder')
    parser.add_argument('--unified-historical-project',type=Path,help='Read-only historical Ni project for unified-provider acceptance')
    args=parser.parse_args()
    from .runtime import configure_logging, LABEL, build_info
    configure_logging()
    if args.unified_elastic_acceptance:
        from .unified_elastic_acceptance import run
        return run(args.unified_elastic_acceptance,args.unified_historical_project)
    if args.scientific_acceptance:
        from .scientific_acceptance import run
        return run(args.scientific_acceptance)
    if args.desktop_acceptance:
        from .desktop_acceptance import run
        return run(args.desktop_acceptance,args.desktop_orientation)
    if args.parallel_acceptance:
        from .parallel_acceptance import run
        return run(args.parallel_acceptance,args.parallel_project,args.parallel_workers)
    if args.cancellation_acceptance:
        if not args.cancellation_source:parser.error('Cancellation acceptance requires an explicit source')
        from .cancellation_acceptance import run
        return run(args.cancellation_acceptance,args.cancellation_source)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    if not QtGui.QFontDatabase.families():
        # Qt's offscreen Windows plugin may expose no system fonts. Use the
        # font already bundled with Matplotlib, rather than unreadable boxes.
        from matplotlib import get_data_path
        font_id=QtGui.QFontDatabase.addApplicationFont(str(Path(get_data_path())/'fonts/ttf/DejaVuSans.ttf'))
        families=QtGui.QFontDatabase.applicationFontFamilies(font_id)
        if families:app.setFont(QtGui.QFont(families[0],9))
    window=MainWindow();window.setWindowTitle(build_info()['label'])
    add_about_menu(window)
    window.show()
    if args.smoke_screenshot:
        def capture():
            if window.busy:QtCore.QTimer.singleShot(100,capture);return
            args.smoke_screenshot.parent.mkdir(parents=True,exist_ok=True);window.grab().save(str(args.smoke_screenshot));app.quit()
        window.preview_ready.connect(lambda:QtCore.QTimer.singleShot(300,capture));QtCore.QTimer.singleShot(200,window.start_preview)
        QtCore.QTimer.singleShot(30000,lambda:app.exit(2))
    if args.smoke_emcd_screenshot:
        window.propagation_box.setCurrentIndex(['bloch','fft-multislice','both'].index(args.smoke_propagation))
        if args.smoke_atomic:window.model_box.setCurrentIndex(1)
        def capture_emcd():
            if window.busy:QtCore.QTimer.singleShot(100,capture_emcd);return
            from .emcd_forward import export_result
            import datetime
            from .runtime import workspace
            root=(workspace()/'smoke_exports')/('atomic_' if args.smoke_atomic else 'xmcd_')
            root=root.parent/(root.name+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
            export_result(window.emcd_result,root)
            window.eels_view.maximize();window.tabs.setCurrentIndex(window.tabs.indexOf(window.overview_view) if args.smoke_propagation=='both' else 2)
            def grab():
                args.smoke_emcd_screenshot.parent.mkdir(parents=True,exist_ok=True)
                window.grab().save(str(args.smoke_emcd_screenshot));print('Completed EMCD export: '+str(root),flush=True);app.quit()
            QtCore.QTimer.singleShot(700,grab)
        window.emcd_ready.connect(lambda:QtCore.QTimer.singleShot(300,capture_emcd));QtCore.QTimer.singleShot(300,window.start_emcd)
        QtCore.QTimer.singleShot(240000,lambda:app.exit(2))
    return app.exec()
