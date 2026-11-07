"""Per-group MDFF configuration, reusing the existing editors and validators.

No propagation, tensor-frame inference or cross-source amplitude scaling.
"""
from copy import deepcopy
from pathlib import Path
import json

import numpy as np
from PySide6 import QtCore, QtWidgets

from ..imported_mdff import CONVENTION
from ..mdff_providers import load_site_group_provider
from ..multisite import IonizationSiteGroup
from ..multisite_spectrum import ModeledEdgeWindow
from .generalized_forward import ImportedSettings, settings_for_provider, settings_for_source
from .provider_ui import ProviderUI


def validate_group_reference(row, reference=None, window=None):
    name, element, indices, direction, current = row
    cfg = current if reference is None else reference
    group = IonizationSiteGroup(name,element,indices,cfg,direction,len(indices))
    source = load_site_group_provider(group)
    bounds = source.energy_ev[[0,-1]] if window is None else np.asarray(window.bounds_ev)
    if bounds[0] < source.energy_ev[0] or bounds[-1] > source.energy_ev[-1]:
        raise ValueError('Missing MDFF coverage within required modeled window')
    energy = np.unique(bounds if window is None or window.energy_ev is None else
                       np.r_[bounds,window.energy_ev])
    source.tensors(energy,np.eye(3),group.magnetization)
    return source


class GroupMDFFDialog(ProviderUI, QtWidgets.QDialog):
    """Each instance owns its GUI drafts; applied references remain immutable."""
    configured = QtCore.Signal(object, object)  # Existing settings, ModeledEdgeWindow.

    def __init__(self, row, workspace, parent=None):
        super().__init__(parent)
        self.row = row; self.workspace = Path(workspace)
        self.reference = row[4] if isinstance(row[4],ImportedSettings) else None
        self.commit = None;self.provenance = None
        self.window = None; self.source_info = None; self._reviewed_sha = None
        self._inputs = {}; self.spin = {}; self._loading = True
        self.setWindowTitle('Configure MDFF for Group')
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.WindowMinMaxButtonsHint)
        self.resize(1150,850)
        layout = QtWidgets.QVBoxLayout(self)
        self.context = QtWidgets.QLabel(); self.context.setWordWrap(True); layout.addWidget(self.context)
        self.model = QtWidgets.QComboBox(); self.model.addItems(['XMCD-constrained MDFF','Atomic Ionization MDFF','Manual tensor / imported source'])
        layout.addWidget(self.model)
        scroll = QtWidgets.QScrollArea(); scroll.setWidgetResizable(True); layout.addWidget(scroll,1)
        self.pages = QtWidgets.QStackedWidget(); scroll.setWidget(self.pages)
        self.declaration = QtWidgets.QCheckBox('I acknowledge this source, its full tensor frame, physical reversal declarations, relative per-atom units and validity limits.')
        self.build_xmcd()
        self.build_atomic()
        self.build_manual()
        form = QtWidgets.QFormLayout(); layout.addLayout(form)
        self.bounds = self.field('window','',form,'Modeled window bounds (eV; optional)')
        self.samples = self.field('samples','',form,'Independent samples (eV; optional)')
        note = QtWidgets.QLabel('Blank window uses full validated source coverage/native samples. No extrapolation or invented tails. '
            'Intensities retain declared relative per-atom amplitudes; cross-element absolute calibration is not implied. '
            'Local M is not a complete anisotropic tensor frame.')
        note.setWordWrap(True); layout.addWidget(note); layout.addWidget(self.declaration)
        self.status = QtWidgets.QLabel('Incomplete — select a model and explicitly configure its source.');self.status.setWordWrap(True)
        self.status.setMinimumHeight(130)
        self.status.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,QtWidgets.QSizePolicy.Policy.Minimum)
        self.status.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.status)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Apply |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel | QtWidgets.QDialogButtonBox.StandardButton.Close)
        layout.addWidget(buttons);self.buttons = buttons
        buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Apply).setText('Validate and Apply')
        buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply_configuration)
        buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.reject)
        buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Close).setText('Keep Draft / Close')
        buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Close).clicked.connect(self.close)
        self.model.currentIndexChanged.connect(self.model_changed)
        self.set_context(row)
        if self.reference is not None:self.restore_reference(self.reference)
        else:self.model.setCurrentIndex(-1);self.pages.setEnabled(False)
        self._loading = False
        self._entry = self.snapshot()

    def field(self, key, text, form, label):
        widget = QtWidgets.QLineEdit(text); self._inputs[key] = widget
        form.addRow(label,widget); widget.textChanged.connect(self.emcd_stale)
        return widget

    def browse_row(self, field, form, title):
        button = QtWidgets.QPushButton('Browse…');form.addRow(button)
        def browse():
            path,_ = QtWidgets.QFileDialog.getOpenFileName(self,title,'','Source files (*)')
            if path:field.setText(path)
        button.clicked.connect(browse)
        return button

    def build_xmcd(self):
        page = QtWidgets.QWidget();self.pages.addWidget(page);self.form = QtWidgets.QFormLayout(page)
        self.source_path = self.field('xmcd_path','',self.form,'Original five-column source')
        self.browse_row(self.source_path,self.form,'Select original XMCD spectrum')
        for key,label in [('xl3','Explicit L3 selection (eV)'),('xl2','Explicit L2 selection (eV)')]:
            box = QtWidgets.QDoubleSpinBox();box.setRange(.001,1e6);box.setDecimals(6)
            self.spin[key] = box;self.form.addRow(label,box)
        self.xmcd_declaration_controls()  # The same declarations as the legacy dialog.
        self.explicit_xmcd.setChecked(True);self.explicit_xmcd.hide()
        self.xmcd_element.setText(self.row[1]);self.xmcd_element.setReadOnly(True)
        for name in ('xmcd_element','xmcd_edge','xmcd_selected','xmcd_provenance','xmcd_validity','xmcd_scale'):
            self._inputs[name] = getattr(self,name)
        self.eta = self.field('eta','',self.form,'Explicit XMCD eta')
        self.beta = self.field('beta','',self.form,'Explicit XMCD beta')
        text = QtWidgets.QLabel('Existing axisymmetric XMCD-odd/shared-XAS model only. Source-maximum normalization and the explicitly declared reference amplitude are retained. This is not a full anisotropic DFT MDFF.')
        text.setWordWrap(True);self.form.addRow(text)

    def build_atomic(self):
        from .atomic_editor import AtomicParameterEditor
        page = QtWidgets.QWidget();self.pages.addWidget(page);form = QtWidgets.QFormLayout(page)
        self.atomic_form = form
        self.atomic_mode = QtWidgets.QComboBox();self.atomic_mode.addItems(['Existing parameter source','Edit atomic parameters'])
        form.addRow('Atomic input',self.atomic_mode)
        self.atomic_path = self.field('atomic_path','',form,'Original atomic parameter JSON')
        self.atomic_browse = self.browse_row(self.atomic_path,form,'Select existing atomic parameters')
        load = QtWidgets.QPushButton('Load parameters into existing editor');form.addRow(load)
        self.atomic_load = load
        self.atomic = AtomicParameterEditor(lambda:self.workspace,self)
        self.atomic.element.setCurrentIndex(self.atomic.element.findData(self.row[1]))
        self.atomic.element.setEnabled(False);self.atomic.crystal_box.hide()
        # An explicit full frame is required; group M is never used to build it.
        self.atomic.direction.setEnabled(False);self.atomic.apply_direction.setEnabled(False)
        self.atomic.invalidated.connect(self.emcd_stale);form.addRow(self.atomic)
        load.clicked.connect(self.load_atomic)
        self.atomic_mode.currentIndexChanged.connect(self.atomic_mode_changed)
        self.atomic_mode.setCurrentIndex(1)

    def atomic_mode_changed(self, *_):
        editing = self.atomic_mode.currentIndex() == 1
        self.atomic.setVisible(editing)
        for widget in (self.atomic_path,self.atomic_browse,self.atomic_load):widget.setVisible(not editing)
        self.atomic_form.labelForField(self.atomic_path).setVisible(not editing)
        self.emcd_stale()

    def build_manual(self):
        from .mdff_usability import ManualTensorEditor
        page = QtWidgets.QWidget();self.pages.addWidget(page);form = QtWidgets.QFormLayout(page)
        self.manual_form = form
        self.manual_mode = QtWidgets.QComboBox();self.manual_mode.addItems(['Imported tensor source','Explicit constant +M / −M pair'])
        form.addRow('Manual input',self.manual_mode)
        self.import_path = self.field('import_path','',form,'Original tensor JSON')
        self.import_browse = self.browse_row(self.import_path,form,'Select original tensor source')
        self.manual_edge = self.field('manual_edge','L2,3',form,'Explicit core edge')
        self.manual_energy = self.field('manual_energy','',form,'Constant-pair energy grid (eV)')
        self.manual_selected = self.field('manual_selected','',form,'Selected edges JSON')
        self.manual_frame = self.field('manual_frame','',form,'Full frame_to_crystal (3×3 JSON)')
        self.manual_source = self.field('manual_source','',form,'Source provenance')
        self.manual_validity = self.field('manual_validity','',form,'Physical validity / limitations')
        self.pair_widget = QtWidgets.QWidget();pair_layout = QtWidgets.QHBoxLayout(self.pair_widget)
        self.pair = []
        for label in ('Explicit +M tensor','Explicit −M tensor'):
            box = QtWidgets.QGroupBox(label);box_layout = QtWidgets.QVBoxLayout(box)
            tensor = ManualTensorEditor(box)
            # Reuse coefficient editing, not its legacy conjugation ansatz.
            tensor.note.setText('Explicit Hermitian PSD state in the declared tensor frame. No other magnetic state is manufactured. Relative Å²/eV.')
            tensor.changed.connect(self.emcd_stale);box_layout.addWidget(tensor)
            pair_layout.addWidget(box);self.pair.append(tensor)
        form.addRow(self.pair_widget)
        self.manual_mode.currentIndexChanged.connect(self.manual_mode_changed)
        self.manual_mode_changed()

    def manual_mode_changed(self, *_):
        explicit = self.manual_mode.currentIndex() == 1
        self.pair_widget.setVisible(explicit)
        for key in ('manual_energy','manual_selected','manual_frame','manual_source','manual_validity'):
            self._inputs[key].setEnabled(explicit)
            self._inputs[key].setVisible(explicit)
            self.manual_form.labelForField(self._inputs[key]).setVisible(explicit)
        self.import_path.setVisible(not explicit);self.import_browse.setVisible(not explicit)
        self.manual_form.labelForField(self.import_path).setVisible(not explicit)
        self.emcd_stale()

    def model_changed(self, index):
        self.pages.setEnabled(index >= 0)
        if index >= 0:self.pages.setCurrentIndex(index)
        self.emcd_stale()

    def emcd_stale(self, *_):
        if not self._loading and hasattr(self,'status'):
            self.declaration.setChecked(False)
            self.status.setText('Incomplete / unapplied draft. Validate and Apply before using this configuration.')

    def set_context(self, row):
        changed = self.row[1:4] != row[1:4]
        self.row = row
        if changed:self.emcd_stale()
        self.context.setText(f'Group {row[0]} · {row[1]} · ASE indices {row[2]}\n'
            f'Declared local M (crystal Cartesian): {row[3]}. Legacy Global M is not used.')

    def load_atomic(self):
        try:
            from .atomic_editor_model import read_document
            document,_ = read_document(self.atomic_path.text())
            if document['parameters']['element'] != self.row[1]:raise ValueError('Atomic source element differs from site-group element')
            self.atomic.load_document(self.atomic_path.text(),validated=False)
            if self.atomic.element.currentData() != self.row[1]:raise ValueError('Atomic source element differs from site-group element')
            self.atomic_mode.setCurrentIndex(1);self.emcd_stale()
        except Exception as exc:self.status.setText('Invalid: '+str(exc))

    @staticmethod
    def numbers(text):
        return tuple(float(v) for v in text.replace(',',' ').split())

    def candidate(self):
        if self.model.currentIndex() == 0:
            from ..wien2k_xmcd import load_wien2k_xmcd
            path = self.source_path.text().strip();source = load_wien2k_xmcd(path)
            selected = (dict(L3=self.spin['xl3'].value(),L2=self.spin['xl2'].value())
                        if self.xmcd_edge.text().strip() == 'L2,3' else json.loads(self.xmcd_selected.text()))
            declaration = dict(element=self.row[1],edge=self.xmcd_edge.text().strip(),selected_ev=selected,
                magnetization_crystal=list(self.row[3]),handedness='RP_minus_LP_in_declared_axis',
                eta=float(self.eta.text()),beta=float(self.beta.text()),normalization='source_max_nonmagnetic',
                convention=CONVENTION,source=self.xmcd_provenance.text().strip(),validity=self.xmcd_validity.text().strip(),
                status=self.xmcd_status.currentText(),source_sha256=source.source_sha256,
                reference_tensor_scale_angstrom2_per_ev=float(self.xmcd_scale.text()),
                magnetic_state='uniform_fm',reversal_assumption='axisymmetric_XMCD_odd_shared_XAS')
            return settings_for_provider(path,'xmcd',declaration)
        if self.model.currentIndex() == 1:
            if self.atomic_mode.currentIndex() == 0:
                if not self.atomic_path.text().strip():raise ValueError('Select an original atomic parameter source')
                return settings_for_provider(self.atomic_path.text().strip(),'atomic')
            from .atomic_editor_model import persist_document
            path,_ = persist_document(self.workspace,self.atomic.document())
            return settings_for_provider(path,'atomic')
        if self.model.currentIndex() == 2:
            if self.manual_mode.currentIndex() == 0:
                cfg = settings_for_source(self.import_path.text().strip())
                if self.manual_edge.text().strip() != cfg.core_edge:raise ValueError('Selected core edge differs from imported source')
                return cfg
            energy = self.numbers(self.manual_energy.text())
            a,b = [editor.matrix() for editor in self.pair]
            pack = lambda tensor:dict(real=np.repeat(tensor[None],len(energy),axis=0).real.tolist(),
                                     imag=np.repeat(tensor[None],len(energy),axis=0).imag.tolist())
            document = dict(schema=1,element=self.row[1],edge=self.manual_edge.text().strip(),energy_ev=energy,
                selected_ev=json.loads(self.manual_selected.text()),units='angstrom^2/eV',normalization='per_atom_relative',
                basis='declared_local',frame_to_crystal=json.loads(self.manual_frame.text()),
                magnetic_state='uniform_fm',magnetization_crystal=list(self.row[3]),reversal='explicit_pair_shared_even',
                source=self.manual_source.text().strip(),validity=self.manual_validity.text().strip(),status='synthetic',
                convention=CONVENTION,T_plus=pack(a),T_minus=pack(b),T_even=pack((a+b)/2))
            source = self.pair[0].persist(self.workspace,document)
            return settings_for_source(source.path)
        raise ValueError('Select and configure an MDFF model')

    def validate_configuration(self):
        if not self.declaration.isChecked():raise ValueError('Acknowledge source, tensor frame, reversal and units first')
        cfg = self.candidate()
        if (self.reference is not None and cfg.source == self.reference.source
                and cfg.source_sha256 != self.reference.source_sha256 and self._reviewed_sha != cfg.source_sha256):
            self._reviewed_sha = cfg.source_sha256;self.declaration.setChecked(False)
            raise ValueError('Source identity changed; review, acknowledge and validate the new source again')
        source = validate_group_reference(self.row,cfg)
        bounds = self.numbers(self.bounds.text()) if self.bounds.text().strip() else tuple(source.energy_ev[[0,-1]])
        samples = self.numbers(self.samples.text()) if self.samples.text().strip() else tuple(np.unique(np.r_[bounds,source.energy_ev[(source.energy_ev>=bounds[0]) & (source.energy_ev<=bounds[-1])]]))
        window = ModeledEdgeWindow(bounds,samples)
        validate_group_reference(self.row,cfg,window)
        return cfg,window,source

    def apply_configuration(self):
        try:
            cfg,window,source = self.validate_configuration()
            if self.commit is not None:self.commit(cfg,window)
            self.configured.emit(cfg,window)
            self.reference = cfg;self.window = window
            self.provenance = source.provenance()
            d = source.metadata
            self.status.setText(f'Configured and valid (declarations; physical calibration not established).\n'
                f'{d["element"]} {d["edge"]}; {d["units"]}; {d["normalization"]}; source coverage {source.energy_ev[0]:g}–{source.energy_ev[-1]:g} eV\n'
                f'Frame to crystal: {d["frame_to_crystal"]}; reversal: {d["reversal"]}\n'
                f'Source: {d["source"][:250]}\nLimits: {d["validity"][:250]}')
            self._entry = self.snapshot()
            return cfg
        except Exception as exc:
            self.status.setText('Invalid / incomplete: '+str(exc));return None

    def restore_reference(self, cfg):
        self.reference = cfg
        if cfg.model == 'atomic':
            self.model.setCurrentIndex(1);self.atomic_mode.setCurrentIndex(0);self.atomic_path.setText(cfg.source)
        elif cfg.model == 'xmcd':
            self.model.setCurrentIndex(0);self.source_path.setText(cfg.source)
            d = cfg.provider_declaration or {}
            for name,key in [('xmcd_edge','edge'),('xmcd_provenance','source'),('xmcd_validity','validity'),('xmcd_scale','reference_tensor_scale_angstrom2_per_ev'),('eta','eta'),('beta','beta')]:
                getattr(self,name).setText(str(d.get(key,'')))
            self.xmcd_selected.setText(json.dumps(d.get('selected_ev',{})))
            for edge,key in [('L3','xl3'),('L2','xl2')]:self.spin[key].setValue(d.get('selected_ev',{}).get(edge,.001))
        else:
            self.model.setCurrentIndex(2);self.manual_mode.setCurrentIndex(0)
            self.import_path.setText(cfg.source);self.manual_edge.setText(cfg.core_edge)
        self.pages.setEnabled(True);self.pages.setCurrentIndex(self.model.currentIndex())
        self.declaration.setChecked(cfg.axis_declared)

    def snapshot(self):
        return dict(fields={key:w.text() for key,w in self._inputs.items()},model=self.model.currentIndex(),
            manual=self.manual_mode.currentIndex(),atomic=deepcopy(self.atomic.draft()),
            atomic_mode=self.atomic_mode.currentIndex(),
            pair=[[[e.cells.item(i,j).text() for j in range(3)] for i in range(3)] for e in self.pair],
            selections=[self.spin[k].value() for k in ('xl3','xl2')],
            status=self.xmcd_status.currentIndex(),ack=self.declaration.isChecked())

    def restore_snapshot(self, state):
        self._loading = True
        for key,text in state['fields'].items():self._inputs[key].setText(text)
        self.atomic.restore_draft(deepcopy(state['atomic']))
        self.atomic_mode.setCurrentIndex(state['atomic_mode'])
        for editor,values in zip(self.pair,state['pair']):
            with QtCore.QSignalBlocker(editor.cells):
                for i in range(3):
                    for j in range(3):editor.cells.item(i,j).setText(values[i][j])
            editor.edited()
        self.model.setCurrentIndex(state['model']);self.manual_mode.setCurrentIndex(state['manual'])
        for key,value in zip(('xl3','xl2'),state['selections']):self.spin[key].setValue(value)
        self.xmcd_status.setCurrentIndex(state['status']);self.declaration.setChecked(state['ack'])
        self._loading = False
        self.provenance = None
        self.status.setText('Restored draft. Validate and Apply to confirm source identity, frame and coverage.')

    def open_draft(self, row):
        self.set_context(row);self._entry = self.snapshot()
        self.show();self.raise_();self.activateWindow()

    def closeEvent(self, event):
        event.accept()  # Keep incomplete drafts; explicit Cancel restores entry state.

    def reject(self):
        self.restore_snapshot(self._entry)
        super().reject()
