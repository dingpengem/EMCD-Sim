"""Small opt-in controls for the declared imported-MDFF route."""
from dataclasses import asdict
from pathlib import Path
from PySide6 import QtWidgets,QtCore
from ..imported_mdff import ImportedMDFF


class ImportedTensorUI:
    def imported_mdff_controls(self):
        panel=QtWidgets.QWidget();form=QtWidgets.QFormLayout(panel);self.mdff_stack.addWidget(panel)
        self.imported_info=None;self.imported_path=QtWidgets.QLineEdit();form.addRow('Imported MDFF JSON',self.imported_path)
        browse=QtWidgets.QPushButton('Browse tensor…');browse.clicked.connect(self.browse_imported_mdff);form.addRow(browse)
        validate=QtWidgets.QPushButton('Validate tensor / provenance');validate.clicked.connect(self.validate_imported_mdff);form.addRow(validate)
        atomic=QtWidgets.QPushButton('Generate approximate atomic tensor from declared parameters…')
        atomic.clicked.connect(self.generate_atomic_tensor);form.addRow(atomic)
        self.ionizing_element=QtWidgets.QLineEdit();form.addRow('Ionizing element',self.ionizing_element)
        self.imported_edge=QtWidgets.QLineEdit('L2,3');form.addRow('Core-loss edge',self.imported_edge)
        self.imported_state=QtWidgets.QComboBox();self.imported_state.addItems(['uniform_fm','nonmagnetic']);form.addRow('Magnetic state',self.imported_state)
        self.ionization_selection=QtWidgets.QLineEdit('all');form.addRow('Equivalent site indices (0-based)',self.ionization_selection)
        self.imported_declaration=QtWidgets.QCheckBox('I acknowledge source frame, crystal M axis,\nexplicit reversal and relative per-atom units');form.addRow(self.imported_declaration)
        self.imported_status=QtWidgets.QLabel('No imported tensor validated. Synthetic data are software tests only.');self.imported_status.setWordWrap(True);form.addRow(self.imported_status)
        self.imported_path.textChanged.connect(self.imported_source_changed)
        for widget in (self.ionizing_element,self.imported_edge,self.ionization_selection):widget.textChanged.connect(self.emcd_stale)
        self.imported_state.currentIndexChanged.connect(self.emcd_stale);self.imported_declaration.toggled.connect(self.emcd_stale)

    def imported_source_changed(self,*_):
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
            self.imported_status.setText('Atomic model rejected: '+str(exc))

    def validate_imported_mdff(self,*_,expected_sha256=None):
        try:
            source=ImportedMDFF.load(self.imported_path.text(),expected_sha256 or '')
            self.imported_info=source;d=source.metadata
            for widget,text in ((self.ionizing_element,d['element']),(self.imported_edge,d['edge'])):
                with QtCore.QSignalBlocker(widget):widget.setText(text)
            with QtCore.QSignalBlocker(self.imported_state):self.imported_state.setCurrentText(d['magnetic_state'])
            with QtCore.QSignalBlocker(self.axis):self.axis.setText(' '.join(map(str,d['magnetization_crystal'])))
            self.imported_status.setText(('SYNTHETIC TEST ONLY' if d['status']=='synthetic' else 'RESEARCH / APPROXIMATE: imported physical source is not independently validated')+
                '\n'+d['source']+'\nSHA256: '+source.sha256+'\nL3/L2: '+str(d['selected_ev'])+'; no extrapolation.\n'+d['validity'])
        except Exception as exc:
            self.imported_info=None;self.imported_status.setText(str(exc))
        self.emcd_stale()

    def imported_forward_settings(self,base):
        from .generalized_forward import ImportedSettings
        source=self.imported_info
        if source is None or source.path!=str(Path(self.imported_path.text()).resolve()):raise ValueError('Validate the current imported MDFF source first')
        indices=self.ionization_selection.text().strip()
        selected=None if indices=='all' else tuple(int(v) for v in indices.replace(',',' ').split())
        fields=asdict(base);fields['atomic']=base.atomic
        fields.update(source=self.imported_path.text(),source_sha256=source.sha256,
            ionizing_element=self.ionizing_element.text().strip(),core_edge=self.imported_edge.text().strip(),
            magnetic_state=self.imported_state.currentText(),site_indices=selected,axis_declared=self.imported_declaration.isChecked(),
            l3=source.metadata['selected_ev']['L3'],l2=source.metadata['selected_ev']['L2'])
        return ImportedSettings(**fields)

    def restore_imported_settings(self,cfg,path=None):
        with QtCore.QSignalBlocker(self.imported_path):self.imported_path.setText(path or cfg.source)
        self.validate_imported_mdff(expected_sha256=cfg.source_sha256)
        for widget,text in ((self.ionizing_element,cfg.ionizing_element),(self.imported_edge,cfg.core_edge),
                (self.ionization_selection,'all' if cfg.site_indices is None else ' '.join(map(str,cfg.site_indices))),
                (self.axis,' '.join(map(str,cfg.magnetization)))):
            with QtCore.QSignalBlocker(widget):widget.setText(text)
        with QtCore.QSignalBlocker(self.imported_state):self.imported_state.setCurrentText(cfg.magnetic_state)
        with QtCore.QSignalBlocker(self.imported_declaration):self.imported_declaration.setChecked(cfg.axis_declared)
