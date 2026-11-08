"""Small opt-in controls for the declared imported-MDFF route."""
from dataclasses import asdict
from pathlib import Path
from PySide6 import QtWidgets,QtCore
from ..imported_mdff import ImportedMDFF
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg


class ImportedTensorUI:
    def imported_mdff_controls(self):
        panel=QtWidgets.QWidget();form=QtWidgets.QFormLayout(panel);self.mdff_stack.addWidget(panel)
        from .mdff_usability import ManualTensorEditor
        from .responsive import CollapsibleSection
        self.manual_tensor=ManualTensorEditor(panel);form.addRow(self.manual_tensor)
        self.manual_l3=QtWidgets.QLineEdit('708.1');self.manual_l2=QtWidgets.QLineEdit('721.1')
        form.addRow('L3 selection (eV)',self.manual_l3);form.addRow('L2 selection (eV)',self.manual_l2)
        self.manual_bounds=QtWidgets.QLabel('Constant over [L3 - 10, L2 + 10] eV. Selections locate evaluation energies, not peaks. Default Fe selections are an example; edit for your element.')
        self.manual_bounds.setWordWrap(True);form.addRow(self.manual_bounds)
        self.manual_tensor.changed.connect(self.manual_tensor_changed)
        for field in (self.manual_l3,self.manual_l2):field.textChanged.connect(self.manual_tensor_changed)
        exchange=CollapsibleSection('Advanced source exchange / declarations',expanded=False);form.addRow(exchange)
        normal_form=form;form=QtWidgets.QFormLayout(exchange.body)
        self.imported_info=None;self.imported_path=QtWidgets.QLineEdit();form.addRow('Imported MDFF JSON',self.imported_path)
        browse=QtWidgets.QPushButton('Browse tensor…');browse.clicked.connect(self.browse_imported_mdff);form.addRow(browse)
        validate=QtWidgets.QPushButton('Validate tensor / provenance');validate.clicked.connect(self.validate_imported_mdff);form.addRow(validate)
        self.ionizing_element=QtWidgets.QLineEdit('Fe');normal_form.addRow('Element',self.ionizing_element)
        self.imported_edge=QtWidgets.QLineEdit('L2,3');form.addRow('Core-loss edge',self.imported_edge)
        self.imported_state=QtWidgets.QComboBox();self.imported_state.addItems(['uniform_fm','nonmagnetic']);form.addRow('Magnetic state',self.imported_state)
        self.ionization_selection=QtWidgets.QLineEdit('all');form.addRow('Equivalent site indices (0-based)',self.ionization_selection)
        self.imported_declaration=QtWidgets.QCheckBox('I acknowledge source frame, crystal M axis,\nexplicit reversal and relative per-atom units');form.addRow(self.imported_declaration)
        self.imported_status=QtWidgets.QLabel('No imported tensor validated. Synthetic data are software tests only.');self.imported_status.setWordWrap(True);form.addRow(self.imported_status)
        self.imported_path.textChanged.connect(self.imported_source_changed)
        for widget in (self.ionizing_element,self.imported_edge,self.ionization_selection):widget.textChanged.connect(self.emcd_stale)
        self.imported_state.currentIndexChanged.connect(self.emcd_stale);self.imported_declaration.toggled.connect(self.emcd_stale)
        self.manual_preview=QtWidgets.QPushButton('Update numerical preview');normal_form.addRow(self.manual_preview);self.manual_preview.clicked.connect(self.preview_mdff)
        self.manual_preview_state=QtWidgets.QLabel('Numerical preview not calculated.');self.manual_preview_state.setWordWrap(True);normal_form.addRow(self.manual_preview_state)
        self.manual_figure=Figure(layout='constrained');self.manual_canvas=FigureCanvasQTAgg(self.manual_figure);self.manual_canvas.setFixedHeight(180);normal_form.addRow(self.manual_canvas)
        columns=QtWidgets.QWidget();columns_layout=QtWidgets.QHBoxLayout(columns)
        columns_layout.setContentsMargins(0,0,0,0);columns_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        left=QtWidgets.QGroupBox('Main parameters');left_layout=QtWidgets.QVBoxLayout(left);left_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        normal_form.takeRow(self.manual_tensor);left_layout.addWidget(self.manual_tensor)
        right=QtWidgets.QGroupBox('Preview and energy interval');right_layout=QtWidgets.QFormLayout(right)
        right_layout.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapLongRows)
        right_layout.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        for widget,label in ((self.ionizing_element,'Element'),(self.manual_l3,'L3 selection (eV)'),(self.manual_l2,'L2 selection (eV)'),
                (self.manual_bounds,''),(self.manual_preview,''),(self.manual_preview_state,''),(self.manual_canvas,''),(exchange,'')):
            taken=normal_form.takeRow(widget)
            if taken.labelItem and taken.labelItem.widget():taken.labelItem.widget().hide()
            if label:right_layout.addRow(label,widget)
            else:right_layout.addRow(widget)
        columns_layout.addWidget(left,3);columns_layout.addWidget(right,2);normal_form.addRow(columns)
        normal_form.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.manual_preview_state.setMinimumHeight(54)
        self.manual_bounds.setMinimumHeight(54)
        self.manual_energy_labels=tuple(right_layout.labelForField(w) for w in (self.manual_l3,self.manual_l2))
        self.constant_input_mode=QtWidgets.QComboBox();self.constant_input_mode.addItems(['Manual constant matrix','Imported tensor source'])
        normal_form.insertRow(0,'Tensor input',self.constant_input_mode)
        self.imported_summary=QtWidgets.QLabel();self.imported_summary.setWordWrap(True);left_layout.addWidget(self.imported_summary);self.imported_summary.hide()
        # Distinct models share the existing imported-provider boundary, not data.
        constant=QtWidgets.QWidget();constant.setLayout(normal_form)
        outer=QtWidgets.QVBoxLayout(panel)
        self.manual_model=QtWidgets.QComboBox();self.manual_model.addItems(['Constant tensor (original semantics)','L2,3 Lorentzian tensor spectrum'])
        outer.addWidget(self.manual_model)
        self.manual_models=QtWidgets.QStackedWidget();outer.addWidget(self.manual_models);self.manual_models.addWidget(constant)
        from .manual_l23_editor import ManualL23Editor
        self.manual_spectral=ManualL23Editor(self);self.manual_models.addWidget(self.manual_spectral)
        self.manual_spectral.invalidated.connect(self.emcd_stale)
        self._manual_loading=False;self._manual_key='constant'
        initial=self._capture_manual_state()
        self._manual_bindings={'constant':initial,'spectral':dict(initial),'imported':dict(initial)}
        self._manual_bindings['spectral']['source']=None
        self._manual_bindings['imported']['source']=None
        self.manual_model.currentIndexChanged.connect(self.manual_model_changed)
        self.constant_input_mode.currentIndexChanged.connect(self.manual_model_changed)
        self.manual_model.setCurrentIndex(1)

    @staticmethod
    def manual_source_kind(source):
        if 'manual_l23_model' in source.metadata:return 'spectral'
        return 'constant' if source.metadata.get('manual_constant_editor')==1 else 'imported'

    def _capture_manual_state(self):
        fields={name:getattr(self,name).text() for name in ('imported_path','ionizing_element','imported_edge','ionization_selection','manual_l3','manual_l2')}
        return dict(fields=fields,source=self.imported_info,declared=self.imported_declaration.isChecked(),state=self.imported_state.currentIndex(),
            cells=[[self.manual_tensor.cells.item(i,j).text() for j in range(3)] for i in range(3)],bounds=self.manual_bounds.text(),status=self.imported_status.text())

    def _remember_manual_state(self):
        if hasattr(self,'_manual_key') and not self._manual_loading:
            self._manual_bindings[self._manual_key]=self._capture_manual_state()

    def _activate_manual_state(self,key,*,remember=True):
        if remember and not getattr(self,'_restoring',False):self._remember_manual_state()
        self._manual_loading=True;self._manual_key=key
        state=self._manual_bindings[key]
        with QtCore.QSignalBlocker(self.manual_model):self.manual_model.setCurrentIndex(1 if key=='spectral' else 0)
        if key!='spectral':
            with QtCore.QSignalBlocker(self.constant_input_mode):self.constant_input_mode.setCurrentIndex(1 if key=='imported' else 0)
        self.manual_models.setCurrentIndex(self.manual_model.currentIndex())
        for name,text in state['fields'].items():
            if name=='axis':continue  # Old per-model drafts never override Material M.
            widget=getattr(self,name)
            with QtCore.QSignalBlocker(widget):widget.setText(text)
        with QtCore.QSignalBlocker(self.imported_state):self.imported_state.setCurrentIndex(state['state'])
        with QtCore.QSignalBlocker(self.imported_declaration):self.imported_declaration.setChecked(state['declared'])
        self.imported_info=state['source']
        if key=='constant':
            with QtCore.QSignalBlocker(self.manual_tensor.cells):
                for i in range(3):
                    for j in range(3):self.manual_tensor.cells.item(i,j).setText(state['cells'][i][j])
            self.manual_tensor.edited()
        self.manual_tensor.external=key=='imported'
        self.manual_tensor.setVisible(key!='imported');self.imported_summary.setVisible(key=='imported')
        for widget in (self.ionizing_element,self.manual_l3,self.manual_l2):widget.setReadOnly(key=='imported')
        for widget in (self.manual_l3,self.manual_l2,*self.manual_energy_labels):widget.setVisible(key!='imported')
        self.manual_bounds.setText(state['bounds']);self.imported_status.setText(state['status'])
        self.manual_model.setItemText(0,'Imported tensor (saved source)' if self.constant_input_mode.currentIndex()==1 else 'Constant tensor (original semantics)')
        self.imported_summary.setText(self.imported_source_summary())
        self.manual_preview_state.setText('STALE numerical preview - update for the restored model binding.')
        self._manual_loading=False
        # Presentation must also update when selector signals were blocked.
        if hasattr(self,'mdff_refresh_model'):self.mdff_refresh_model(self.model_box.currentIndex())

    def manual_model_changed(self,*_):
        if self._manual_loading:return
        key='spectral' if self.manual_model.currentIndex()==1 else 'imported' if self.constant_input_mode.currentIndex()==1 else 'constant'
        self._activate_manual_state(key);self.emcd_stale()

    def imported_source_summary(self):
        if self.imported_info is None:return 'Select and validate the original imported tensor source. Its frame, energy dependence and reversal declarations are retained; it is not a constant-matrix draft.'
        source=self.imported_info;d=source.metadata
        return f"Authenticated imported tensor: {d['element']} {d['edge']}\n{d['basis']}; source frame to crystal = {d['frame_to_crystal']}\nDeclared source magnetic axis (not target M) = {d['magnetization_crystal']}\n{d['normalization']}; {d['units']}\nSelections (eV): {d['selected_ev']}\nEnergy samples: {len(source.energy_ev)}; no extrapolation.\n{d['source']}\nSHA256 {source.sha256}"

    def manual_tensor_changed(self,*_):
        if not hasattr(self,'manual_preview_state') or getattr(self,'_manual_loading',False):return
        self.manual_tensor.external=False
        self.manual_preview_state.setText('STALE numerical preview - update for current draft.')
        self.emcd_stale()

    def prepare_manual_tensor(self):
        if self.manual_model.currentIndex()==1:
            from .runtime import workspace
            doc=self.manual_spectral.document()
            source=self.manual_tensor.persist(getattr(self,'workspace',None) or workspace(),doc)
            with QtCore.QSignalBlocker(self.imported_path):self.imported_path.setText(source.path)
            with QtCore.QSignalBlocker(self.imported_declaration):self.imported_declaration.setChecked(True)
            self.imported_info=source
            self._remember_manual_state()
            return
        if self._manual_key=='imported':return
        from .runtime import workspace
        try:
            doc=self.manual_tensor.document(self.ionizing_element.text().strip(),self.imported_edge.text().strip(),
                (float(self.manual_l3.text()),float(self.manual_l2.text())),tuple(float(v) for v in self.axis.text().split()))
            source=self.manual_tensor.persist(getattr(self,'workspace',None) or workspace(),doc)
            with QtCore.QSignalBlocker(self.imported_path):self.imported_path.setText(source.path)
            self.imported_info=source
            with QtCore.QSignalBlocker(self.imported_declaration):self.imported_declaration.setChecked(True)
            self.imported_status.setText('Authenticated manual constant source SHA256 '+source.sha256)
            self._remember_manual_state()
        except Exception as exc:
            self.manual_tensor.error.setText(str(exc));raise

    def draw_manual_preview(self,cfg=None):
        from .generalized_forward import source_for
        if cfg is None:cfg=self.forward_settings()
        source=source_for(cfg)
        if self.manual_model.currentIndex()==1:
            self.manual_spectral.update_preview(source);return
        plus,minus=[t.tensor_angstrom2_per_ev for t in source.tensors(source.energy_ev,np.eye(3),cfg.magnetization if cfg else source.metadata['magnetization_crystal'])]
        self.manual_preview_pair=(plus.copy(),minus.copy())
        self.manual_figure.clear();ax=self.manual_figure.subplots()
        for name,t in (('+M',plus),('-M',minus),('Even',(plus+minus)/2),('Odd',(plus-minus)/2)):
            ax.plot(source.energy_ev,np.trace(t,axis1=-2,axis2=-1).real/3,label=name)
        ax.set(xlabel='Energy loss (eV)',ylabel='Tr(T)/3');ax.legend(fontsize=8);self.manual_canvas.draw_idle()
        self.manual_preview_state.setText('CURRENT authenticated '+('constant density' if self._manual_key=='constant' else 'imported spectrum')+'; crystal Cartesian Tr(T)/3. Odd trace may vanish with nonzero odd off-diagonal components.')


    def imported_source_changed(self,*_):
        if getattr(self,'_manual_loading',False):return
        if hasattr(self,'_manual_key') and self._manual_key!='imported':
            selected=self.imported_path.text();state=self._capture_manual_state()
            state['fields']['imported_path']=state['source'].path if state['source'] is not None else self._manual_bindings[self._manual_key]['fields']['imported_path']
            self._manual_bindings[self._manual_key]=state
            self._activate_manual_state('imported',remember=False)
            with QtCore.QSignalBlocker(self.imported_path):self.imported_path.setText(selected)
        self.manual_tensor.external=True
        self.imported_info=None;self.imported_declaration.setChecked(False)
        self.imported_status.setText('Imported source changed; validate checksum and declarations again.');self.emcd_stale()

    def browse_imported_mdff(self):
        path,_=QtWidgets.QFileDialog.getOpenFileName(self,'Import declared dipole MDFF','','Tensor JSON (*.json)')
        if path:self.imported_path.setText(path);self.validate_imported_mdff()

    def generate_atomic_tensor(self):
        """Opt-in declared configuration, not migration of the legacy Ni panel."""
        from ..atomic_ionization import export_atomic_parameters
        parameters,_=QtWidgets.QFileDialog.getOpenFileName(self,'Fully declared atomic research parameters','','Atomic parameter JSON (*.json)')
        if not parameters:return
        output,_=QtWidgets.QFileDialog.getSaveFileName(self,'New approximate atomic tensor (existing files preserved)','','Tensor JSON (*.json)')
        if not output:return
        try:
            source=export_atomic_parameters(parameters,output)
            self.imported_path.setText(source.path);self.validate_imported_mdff(expected_sha256=source.sha256)
        except Exception as exc:
            self.imported_info=None;self.imported_declaration.setChecked(False)
            self.imported_status.setText('Atomic model rejected: '+str(exc))
            self.emcd_stale()

    def validate_imported_mdff(self,*_,expected_sha256=None):
        try:
            source=ImportedMDFF.load(self.imported_path.text(),expected_sha256 or '')
            d=source.metadata;key=self.manual_source_kind(source)
            self._activate_manual_state(key)
            self._manual_loading=True;self.imported_info=source
            with QtCore.QSignalBlocker(self.imported_path):self.imported_path.setText(source.path)
            if key=='spectral':
                self.manual_spectral.load_source(source)
                self.imported_status.setText('Authenticated phenomenological L2,3 source SHA256 '+source.sha256)
            if key=='constant':
                with QtCore.QSignalBlocker(self.manual_tensor.cells):
                    a=source.plus.tensor_angstrom2_per_ev[0]
                    for i in range(3):
                        for j in range(3):self.manual_tensor.cells.item(i,j).setText(str(a[i,j]).strip('()'))
                for widget,key in ((self.manual_l3,'L3'),(self.manual_l2,'L2')):
                    with QtCore.QSignalBlocker(widget):widget.setText(str(d['selected_ev'][key]))
                self.manual_tensor.edited()
                self.manual_tensor.external=False
            self.manual_tensor.external=key=='imported'
            for widget,text in ((self.ionizing_element,d['element']),(self.imported_edge,d['edge'])):
                with QtCore.QSignalBlocker(widget):widget.setText(text)
            with QtCore.QSignalBlocker(self.imported_state):self.imported_state.setCurrentText(d['magnetic_state'])
            with QtCore.QSignalBlocker(self.imported_declaration):self.imported_declaration.setChecked(False)
            if key=='imported':
                self.manual_bounds.setText(f"Original source density over {source.energy_ev[0]:g} to {source.energy_ev[-1]:g} eV; {len(source.energy_ev)} samples. No constant substitution or extrapolation.")
                self.imported_summary.setText(self.imported_source_summary())
            self.imported_status.setText(('SYNTHETIC TEST ONLY' if d['status']=='synthetic' else 'RESEARCH / APPROXIMATE: imported physical source is not independently validated')+
                '\n'+d['source']+'\nSHA256: '+source.sha256+'\nNative selections: '+str(d['selected_ev'])+'; no extrapolation.\n'+d['validity'])
        except Exception as exc:
            self.imported_info=None;self.imported_declaration.setChecked(False);self.imported_status.setText(str(exc))
        finally:self._manual_loading=False
        self._remember_manual_state()
        self.emcd_stale()

    def imported_forward_settings(self,base,prepare=True):
        if self.manual_model.currentIndex()==1 and not prepare:
            self.manual_spectral.inputs()
            raise ValueError('Manual draft ready for explicit preview or calculation')
        if not prepare and not self.manual_tensor.external:
            self.manual_tensor.document(self.ionizing_element.text().strip(),self.imported_edge.text().strip(),
                (float(self.manual_l3.text()),float(self.manual_l2.text())),tuple(float(v) for v in self.axis.text().split()))
            raise ValueError('Manual draft ready for explicit preview or calculation')
        self.prepare_manual_tensor()
        from .generalized_forward import ImportedSettings
        from ..mdff_edges import validate_selected
        source=self.imported_info
        if source is None or source.path!=str(Path(self.imported_path.text()).resolve()):raise ValueError('Validate the current imported MDFF source first')
        if self.manual_source_kind(source)!=self._manual_key:raise ValueError('Selected manual model differs from its authenticated provider; restore or validate its own source')
        indices=self.ionization_selection.text().strip()
        selected=None if indices=='all' else tuple(int(v) for v in indices.replace(',',' ').split())
        fields=asdict(base);fields['atomic']=base.atomic
        selections=validate_selected(source.metadata['element'],source.metadata['edge'],source.metadata['selected_ev'],source.energy_ev[[0,-1]])
        fields.update(source=self.imported_path.text(),source_sha256=source.sha256,
            ionizing_element=source.metadata['element'] if self.manual_model.currentIndex()==1 else self.ionizing_element.text().strip(),core_edge=source.metadata['edge'] if self.manual_model.currentIndex()==1 else self.imported_edge.text().strip(),
            magnetic_state=source.metadata['magnetic_state'] if self.manual_model.currentIndex()==1 else self.imported_state.currentText(),site_indices=selected,axis_declared=self.imported_declaration.isChecked(),
            selected_edges=() if source.metadata['edge']=='L2,3' else selections,
            l3=selections[0][1],l2=selections[-1][1])
        return self.bind_material_reference(ImportedSettings(**fields))

    def restore_imported_settings(self,cfg,path=None):
        with QtCore.QSignalBlocker(self.imported_path):self.imported_path.setText(path or cfg.source)
        self.validate_imported_mdff(expected_sha256=cfg.source_sha256)
        for widget,text in ((self.ionizing_element,cfg.ionizing_element),(self.imported_edge,cfg.core_edge),
                (self.ionization_selection,'all' if cfg.site_indices is None else ' '.join(map(str,cfg.site_indices)))):
            with QtCore.QSignalBlocker(widget):widget.setText(text)
        with QtCore.QSignalBlocker(self.imported_state):self.imported_state.setCurrentText(cfg.magnetic_state)
        self.set_material_magnetization(cfg.magnetization)
        verified=self.imported_info is not None and self.imported_info.sha256==cfg.source_sha256
        with QtCore.QSignalBlocker(self.imported_declaration):self.imported_declaration.setChecked(bool(verified and cfg.axis_declared))
        self._remember_manual_state()
