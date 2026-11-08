"""Per-group MDFF configuration, reusing the existing editors and validators.

No propagation, tensor-frame inference or cross-source amplitude scaling.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json

import numpy as np
from PySide6 import QtCore, QtWidgets

from ..imported_mdff import CONVENTION
from ..mdff_providers import load_site_group_provider
from ..multisite import IonizationSiteGroup
from ..multisite_spectrum import ModeledEdgeWindow
from .generalized_forward import ImportedSettings, settings_for_provider, settings_for_source
from .provider_ui import ProviderUI
from .group_mdff_controls import EdgeSelections, EnergySelection, energy_box


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


def bind_group_direction(row, window=None):
    """Prepare an acknowledged provider binding without changing any live row."""
    from dataclasses import replace
    name,element,indices,direction,current = row
    if current is None:return current
    if not isinstance(current,ImportedSettings):
        raise ValueError(f'Group {name}: configure an acknowledged MDFF provider first')
    for reversed_pair in (False,True):
        candidate=replace(current,magnetization=direction,pair_reversed=reversed_pair)
        try:
            validate_group_reference(row,candidate,window)
            return current if candidate==current else candidate
        except (ValueError,OSError) as exc:
            if not reversed_pair:first_error=exc
    try:
        from ..mdff_providers import load_provider
        d=load_provider(current).metadata
        detail=f"source axis {d['magnetization_crystal']}, frame_to_crystal={d['frame_to_crystal']}"
    except (ValueError,OSError):detail='source axis/frame unavailable because source validation failed'
    raise ValueError(f'Group {name}: requested crystal Cartesian direction {direction} is incompatible with '
        f'{detail} or its physical reversal pair. {first_error}. '
        'Open this group\'s MDFF Editor or supply a compatible validated source; accepted settings are unchanged.')


class GroupMDFFDialog(ProviderUI, QtWidgets.QDialog):
    """Each instance owns its GUI drafts; applied references remain immutable."""
    configured = QtCore.Signal(object, object)  # Existing settings, ModeledEdgeWindow.
    draftChanged = QtCore.Signal()

    def __init__(self, row, workspace, parent=None):
        super().__init__(parent)
        self.row = row; self.workspace = Path(workspace)
        from ase import Atoms
        self.structure = SimpleNamespace(atoms=getattr(parent,'atoms',None) if getattr(parent,'atoms',None) is not None else Atoms(row[1]))
        self.reference = row[4] if isinstance(row[4],ImportedSettings) else None
        self.commit = None;self.provenance = None
        self.window = None; self.source_info = None; self.validated_path = None;self._reviewed_sha = None
        self._inputs = {}; self.spin = {}; self._loading = True
        self.setWindowTitle('Configure MDFF for Group')
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.WindowMinMaxButtonsHint)
        self.resize(1150,850)
        layout = QtWidgets.QVBoxLayout(self)
        self.context = QtWidgets.QLabel(); self.context.setWordWrap(True); layout.addWidget(self.context)
        self.model = QtWidgets.QComboBox(); self.model.addItems(['XMCD-constrained MDFF','Atomic Ionization MDFF','Manual Tensor'])
        self.model_box = self.model
        self.axis = QtWidgets.QLineEdit(' '.join(map(str,row[3])));self.axis.setReadOnly(True);self.axis.hide()
        layout.addWidget(self.model)
        scroll = QtWidgets.QScrollArea(); scroll.setWidgetResizable(True); layout.addWidget(scroll,1)
        self.pages = QtWidgets.QStackedWidget(); scroll.setWidget(self.pages)
        self.declaration = QtWidgets.QCheckBox('I acknowledge this source, its full tensor frame, physical reversal declarations, relative per-atom units and validity limits.')
        self.build_xmcd()
        self.build_atomic()
        self.build_manual()
        from .responsive import CollapsibleSection
        energy_section = CollapsibleSection('Modeled energy window and independent sampling',expanded=False)
        energy_layout = QtWidgets.QVBoxLayout(energy_section.body)
        self.energy_window = EnergySelection(native=True);energy_layout.addWidget(self.energy_window)
        self.energy_window.changed.connect(self.emcd_stale);layout.addWidget(energy_section)
        note = QtWidgets.QLabel('Default: full validated source coverage/native samples. No extrapolation or invented tails. '
            'Intensities retain declared relative per-atom amplitudes; cross-element absolute calibration is not implied. '
            'Local M is not a complete anisotropic tensor frame.')
        note.setWordWrap(True); layout.addWidget(note); layout.addWidget(self.declaration)
        self.status = QtWidgets.QLabel('Incomplete — select a model and explicitly configure its source.');self.status.setWordWrap(True)
        self.status.setMinimumHeight(48);self.status.setMaximumHeight(76)
        self.status.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,QtWidgets.QSizePolicy.Policy.Minimum)
        self.status.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.status)
        self.details = CollapsibleSection('Validated source details',expanded=False)
        details_layout = QtWidgets.QVBoxLayout(self.details.body)
        self.detail_text = QtWidgets.QPlainTextEdit();self.detail_text.setReadOnly(True);self.detail_text.setMaximumHeight(130)
        details_layout.addWidget(self.detail_text);layout.addWidget(self.details)
        export = QtWidgets.QPushButton('Export original applied source…');details_layout.addWidget(export)
        export.clicked.connect(lambda:self.export_applied_source())
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
        self._applied_snapshot = deepcopy(self._entry) if self.reference is not None else None

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
        page = QtWidgets.QWidget();self.pages.addWidget(page);columns = QtWidgets.QHBoxLayout(page)
        inputs = QtWidgets.QWidget();self.form = QtWidgets.QFormLayout(inputs);columns.addWidget(inputs,1)
        self.form.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.source_path = self.field('xmcd_path','',self.form,'Original five-column source')
        self.browse_row(self.source_path,self.form,'Select original XMCD spectrum')
        for key,label in [('xl3','Explicit L3 selection (eV)'),('xl2','Explicit L2 selection (eV)')]:
            box = QtWidgets.QDoubleSpinBox();box.setRange(.001,1e6);box.setDecimals(6)
            self.spin[key] = box;self.form.addRow(label,box)
        self.xmcd_declaration_controls()  # The same declarations as the legacy dialog.
        self.xmcd_selected.hide();self.form.labelForField(self.xmcd_selected).hide()
        self.xmcd_edges = EdgeSelections();self.form.addRow('Selected core edges',self.xmcd_edges)
        self.xmcd_edges.changed.connect(self.sync_xmcd_edges)
        self.xmcd_edge.textChanged.connect(self.show_xmcd_edges);self.show_xmcd_edges()
        self.explicit_xmcd.setChecked(True);self.explicit_xmcd.hide()
        self.xmcd_element.setText(self.row[1]);self.xmcd_element.setReadOnly(True)
        for name in ('xmcd_element','xmcd_edge','xmcd_selected','xmcd_provenance','xmcd_validity','xmcd_scale'):
            self._inputs[name] = getattr(self,name)
        self.eta = QtWidgets.QDoubleSpinBox();self.eta.setRange(-1e6,1e6);self.eta.setValue(1.)
        self.beta = QtWidgets.QDoubleSpinBox();self.beta.setRange(-1e6,1e6)
        for key,box in [('eta',self.eta),('beta',self.beta)]:
            box.setDecimals(6);self.spin[key] = box;self.form.addRow(key,box);box.valueChanged.connect(self.emcd_stale)
        validate = QtWidgets.QPushButton('Validate spectral data');self.form.addRow(validate)
        validate.clicked.connect(self.validate_xmcd_source)
        text = QtWidgets.QLabel('Existing axisymmetric XMCD-odd/shared-XAS model only. Source-maximum normalization and the explicitly declared reference amplitude are retained. This is not a full anisotropic DFT MDFF.')
        text.setWordWrap(True);self.form.addRow(text)
        from .xmcd_preview import XMCDPreview
        self.xmcd_preview = XMCDPreview(self);columns.addWidget(self.xmcd_preview,1)

    def sync_xmcd_edges(self):
        self.xmcd_selected.setText(json.dumps(dict(self.xmcd_edges.rows())))

    def show_xmcd_edges(self):
        if hasattr(self,'xmcd_edges'):
            visible = self.xmcd_edge.text().strip() != 'L2,3'
            self.xmcd_edges.setVisible(visible);self.form.labelForField(self.xmcd_edges).setVisible(visible)

    def validate_xmcd_source(self):
        try:
            from ..wien2k_xmcd import load_wien2k_xmcd
            source = load_wien2k_xmcd(self.source_path.text())
            self.source_info = dict(sha256=source.source_sha256,bounds=source.energy_ev[[0,-1]].tolist(),
                selected=None,explicit_selected=dict(L3=self.spin['xl3'].value(),L2=self.spin['xl2'].value()))
            self.validated_path = self.source_path.text();self.declaration.setChecked(False)
            self.status.setText('Spectral data validated. Select native energies and acknowledge declarations before tensor preview or Apply.')
        except Exception as exc:self.status.setText('Invalid spectral data: '+str(exc))

    def declared_provider_settings(self, base, prepare=True):
        # The unchanged XMCD preview requests the same declared group candidate.
        return self.candidate()

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
        self.atomic_editor = self.atomic
        self.atomic.element.setCurrentIndex(self.atomic.element.findData(self.row[1]))
        self.atomic.element.setEnabled(False);self.atomic.crystal_box.hide()
        # An explicit full frame is required; group M is never used to build it.
        self.atomic.direction.setReadOnly(True)
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
        self.manual_mode = QtWidgets.QComboBox();self.manual_mode.addItems(['Constant tensor (existing synthetic model)',
            'L2,3 Lorentzian tensor spectrum','Explicit constant +M / −M pair','Advanced / Import Existing Source'])
        form.addRow('Manual input',self.manual_mode)
        self.import_path = self.field('import_path','',form,'Original tensor JSON')
        self.import_browse = self.browse_row(self.import_path,form,'Select original tensor source')
        self.manual_edge = self.field('manual_edge','L2,3',form,'Explicit core edge')
        self.constant = QtWidgets.QWidget();constant_layout = QtWidgets.QHBoxLayout(self.constant);constant_layout.setContentsMargins(0,0,0,0)
        parameters = QtWidgets.QWidget();parameter_layout = QtWidgets.QVBoxLayout(parameters);parameter_layout.setContentsMargins(0,0,0,0)
        parameter_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.manual_edges = EdgeSelections();parameter_layout.addWidget(self.manual_edges)
        self.constant_energy = EnergySelection();parameter_layout.addWidget(self.constant_energy)
        constant_form = QtWidgets.QFormLayout();constant_form.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapAllRows)
        parameter_layout.addLayout(constant_form)
        self.manual_frame = QtWidgets.QTableWidget(3,3)
        self.manual_frame.setHorizontalHeaderLabels(['model x','model y','model z']);self.manual_frame.setVerticalHeaderLabels(['crystal x','crystal y','crystal z'])
        self.manual_frame.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch);self.manual_frame.setFixedHeight(125)
        for i in range(3):
            for j in range(3):self.manual_frame.setItem(i,j,QtWidgets.QTableWidgetItem(str(int(i==j))))
        constant_form.addRow('Full frame to crystal',self.manual_frame)
        self.manual_source = self.field('manual_source','Manual tensor editor; explicitly synthetic example',constant_form,'Source provenance')
        self.manual_validity = self.field('manual_validity','Synthetic constant within declared interval only; no material calibration',constant_form,'Validity / limitations')
        self.pair_widget = QtWidgets.QWidget();pair_layout = QtWidgets.QHBoxLayout(self.pair_widget)
        self.pair = []
        for label in ('Explicit +M tensor','Explicit −M tensor'):
            box = QtWidgets.QGroupBox(label);box_layout = QtWidgets.QVBoxLayout(box)
            box_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
            tensor = ManualTensorEditor(box)
            tensor.layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
            tensor.changed.connect(self.emcd_stale);box_layout.addWidget(tensor)
            pair_layout.addWidget(box);self.pair.append(tensor)
        self.manual_tensor = self.pair[0]
        constant_layout.addWidget(self.pair_widget,2);constant_layout.addWidget(parameters,1);form.addRow(self.constant)
        from .manual_l23_editor import ManualL23Editor
        class GroupL23Editor(ManualL23Editor):
            def reset_defaults(self):
                super().reset_defaults()
                self.frame_mode.setCurrentIndex(1);self.frame_mode.setEnabled(False)
        self.manual_spectral = GroupL23Editor(self)
        self.manual_spectral.element.setCurrentText(self.row[1]);self.manual_spectral.element.setEnabled(False)
        # Retain a complete explicit frame; never initialize anisotropy from local M.
        self.manual_spectral.frame_mode.setCurrentIndex(1);self.manual_spectral.frame_mode.setEnabled(False)
        self.manual_spectral.invalidated.connect(self.emcd_stale);form.addRow(self.manual_spectral)
        selected = [(key,float(self.manual_spectral.fields[key,'energy'].text())) for key in ('L3','L2')]
        self.manual_edges.set_rows(selected)
        self.constant_energy.low.setValue(max(.001,selected[0][1]-10));self.constant_energy.high.setValue(selected[1][1]+10)
        self.manual_edges.changed.connect(self.emcd_stale);self.constant_energy.changed.connect(self.emcd_stale)
        self.manual_frame.itemChanged.connect(self.emcd_stale)
        preview = QtWidgets.QPushButton('Update numerical tensor preview');form.addRow(preview)
        preview.clicked.connect(self.preview_tensor)
        self.manual_mode.currentIndexChanged.connect(self.manual_mode_changed)
        self.manual_mode_changed()

    def manual_mode_changed(self, *_):
        mode = self.manual_mode.currentIndex();explicit = mode == 2;imported = mode == 3
        self.constant.setVisible(mode in (0,2));self.manual_spectral.setVisible(mode == 1)
        self.pair[1].parentWidget().setVisible(explicit)
        for number,tensor in enumerate(self.pair):
            tensor.note.setText('Explicit independent Hermitian PSD state; no other state is manufactured.' if explicit else
                'Existing constant synthetic model: −M = conjugate(+M). This is a declared model assumption, not a physical reversal rule for arbitrary imported tensors.')
        self.import_path.setVisible(imported);self.import_browse.setVisible(imported)
        self.manual_form.labelForField(self.import_path).setVisible(imported)
        self.manual_edge.setVisible(mode != 1);self.manual_form.labelForField(self.manual_edge).setVisible(mode != 1)
        self.emcd_stale()

    def preview_tensor(self):
        try:
            cfg = self.bind_material_reference(self.candidate());source = validate_group_reference(self.row,cfg)
            if self.manual_mode.currentIndex() == 1 and self.model.currentIndex() == 2:
                self.manual_spectral.update_preview(source);return
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            if getattr(self,'tensor_preview',None) is not None:self.tensor_preview.close();self.tensor_preview.deleteLater()
            dialog = QtWidgets.QDialog(self);dialog.setWindowTitle('Provider-evaluated tensor preview');dialog.resize(900,600)
            layout = QtWidgets.QVBoxLayout(dialog);figure = Figure(layout='constrained');canvas = FigureCanvasQTAgg(figure);layout.addWidget(canvas)
            plus,minus = [t.tensor_angstrom2_per_ev for t in source.tensors(source.energy_ev,np.eye(3),self.row[3])]
            self.preview_states = dict(plus=plus,minus=minus,even=(plus+minus)/2,odd=(plus-minus)/2)
            for ax,part in zip(figure.subplots(2,1),('real','imag')):
                for label,value in self.preview_states.items():
                    ax.plot(source.energy_ev,getattr(value[:,0,1],part),label=label+' Txy')
                    ax.plot(source.energy_ev,getattr(np.trace(value,axis1=1,axis2=2)/3,part),ls='--',label=label+' Tr(T)/3')
                ax.set(xlabel='Energy loss (eV)',ylabel=part+' Å²/eV');ax.legend(ncol=4,fontsize=8)
            self.tensor_preview = dialog;canvas.draw_idle();dialog.show()
        except Exception as exc:self.status.setText('Preview unavailable: '+str(exc))

    def set_values(self, values):
        for key,value in values.items():
            with QtCore.QSignalBlocker(self.spin[key]):self.spin[key].setValue(value)

    def model_changed(self, index):
        self.pages.setEnabled(index >= 0)
        if index >= 0:self.pages.setCurrentIndex(index)
        self.emcd_stale()

    def emcd_stale(self, *_):
        if not self._loading and hasattr(self,'status'):
            self.declaration.setChecked(False)
            self.status.setText('Incomplete / unapplied draft. Validate and Apply before using this configuration.')
            self.draftChanged.emit()

    def set_context(self, row):
        changed = self.row[1:3] != row[1:3]
        direction_changed=self.row[3]!=row[3]
        self.row = row
        if hasattr(self,'axis'):
            self.axis.setText(' '.join(map(str,row[3])))
        for editor in (getattr(self,'atomic',None),getattr(self,'manual_spectral',None)):
            if editor is not None:
                with QtCore.QSignalBlocker(editor.direction):editor.direction.setText(' '.join(map(str,row[3])))
        if changed:self.emcd_stale()
        if direction_changed:
            self.atomic.invalidate_preview('Material group direction changed')
            self.atomic.preview_state.setText('STALE — Material group direction changed; update preview.')
            self.manual_spectral.is_stale=True
            self.manual_spectral.status.setText('STALE — Material group direction changed; update preview.')
        self.atomic.schematic.draw();self.manual_spectral.frame_diagram.update()
        self.context.setText(f'Group {row[0]} · {row[1]} · ASE indices {row[2]}\n'
            f'Material group draft M (crystal Cartesian, read-only): {row[3]}. Set through Material → 3D Structure Viewer → Site Groups. Legacy Global M is not used. '
            + ('Physical source −M pair member selected.' if getattr(row[4],'pair_reversed',False) else 'Physical source +M pair member selected.'))

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
                        if self.xmcd_edge.text().strip() == 'L2,3' else self.xmcd_edges.selected())
            declaration = dict(element=self.row[1],edge=self.xmcd_edge.text().strip(),selected_ev=selected,
                magnetization_crystal=list(self.row[3]),handedness='RP_minus_LP_in_declared_axis',
                eta=float(self.eta.text()),beta=float(self.beta.text()),normalization='source_max_nonmagnetic',
                convention=CONVENTION,source=self.xmcd_provenance.text().strip(),validity=self.xmcd_validity.text().strip(),
                status=self.xmcd_status.currentText(),source_sha256=source.source_sha256,
                reference_tensor_scale_angstrom2_per_ev=float(self.xmcd_scale.text()),
                magnetic_state='uniform_fm',reversal_assumption='axisymmetric_XMCD_odd_shared_XAS')
            if (self.reference is not None and self.reference.model=='xmcd' and self.reference.pair_reversed
                    and str(path)==self.reference.source and tuple(self.row[3])==self.reference.magnetization):
                declaration['magnetization_crystal']=self.reference.provider_declaration['magnetization_crystal']
            return settings_for_provider(path,'xmcd',declaration)
        if self.model.currentIndex() == 1:
            if self.atomic_mode.currentIndex() == 0:
                if not self.atomic_path.text().strip():raise ValueError('Select an original atomic parameter source')
                return settings_for_provider(self.atomic_path.text().strip(),'atomic')
            from .atomic_editor_model import persist_document
            path,_ = persist_document(self.workspace,self.atomic.document())
            return settings_for_provider(path,'atomic')
        if self.model.currentIndex() == 2:
            if self.manual_mode.currentIndex() == 3:
                cfg = settings_for_source(self.import_path.text().strip())
                if self.manual_edge.text().strip() != cfg.core_edge:raise ValueError('Selected core edge differs from imported source')
                return cfg
            if self.manual_mode.currentIndex() == 1:
                source = self.manual_tensor.persist(self.workspace,self.manual_spectral.document())
                return settings_for_source(source.path)
            bounds,energy = self.constant_energy.values()
            ModeledEdgeWindow(bounds,energy)
            selected = self.manual_edges.selected()
            a = self.pair[0].matrix()
            legacy = None
            if self.manual_mode.currentIndex() == 0:
                # Reuse the original editor's declared synthetic model exactly.
                legacy = self.manual_tensor.document(self.row[1],self.manual_edge.text().strip(),bounds,self.row[3])
                b = np.asarray(legacy['T_minus']['real'][0])+1j*np.asarray(legacy['T_minus']['imag'][0])
            else:b = self.pair[1].matrix()
            pack = lambda tensor:dict(real=np.repeat(tensor[None],len(energy),axis=0).real.tolist(),
                                     imag=np.repeat(tensor[None],len(energy),axis=0).imag.tolist())
            document = dict(schema=1,element=self.row[1],edge=self.manual_edge.text().strip(),energy_ev=energy,
                selected_ev=selected,units='angstrom^2/eV',normalization='per_atom_relative',
                basis='declared_local',frame_to_crystal=[[float(self.manual_frame.item(i,j).text()) for j in range(3)] for i in range(3)],
                magnetic_state='uniform_fm',magnetization_crystal=list(self.row[3]),reversal='explicit_pair_shared_even',
                source=self.manual_source.text().strip(),validity=self.manual_validity.text().strip(),status='synthetic',
                convention=CONVENTION,T_plus=pack(a),T_minus=pack(b),T_even=pack((a+b)/2))
            document['manual_constant_editor' if self.manual_mode.currentIndex() == 0 else 'manual_constant_pair_editor'] = 1
            if legacy is not None:document['validity'] += '; '+legacy['validity']
            source = self.pair[0].persist(self.workspace,document)
            return settings_for_source(source.path)
        raise ValueError('Select and configure an MDFF model')

    def validate_configuration(self):
        if not self.declaration.isChecked():raise ValueError('Acknowledge source, tensor frame, reversal and units first')
        unchanged = False
        if self.reference is not None and not self.has_unapplied_edits():
            from ..mdff_providers import load_provider
            try:
                load_provider(self.reference)
                unchanged=(self.reference.model!='xmcd' or tuple(self.row[3])==self.reference.magnetization)
            except (ValueError,OSError):pass  # Retain the existing explicit source-change review workflow.
        cfg = self.reference if unchanged else self.candidate()
        if (self.reference is not None and cfg.source == self.reference.source
                and cfg.source_sha256 != self.reference.source_sha256 and self._reviewed_sha != cfg.source_sha256):
            self._reviewed_sha = cfg.source_sha256;self.declaration.setChecked(False)
            raise ValueError('Source identity changed; review, acknowledge and validate the new source again')
        cfg = bind_group_direction(self.row[:4]+(cfg,))
        source = validate_group_reference(self.row,cfg)
        bounds,samples = self.energy_window.values(source.energy_ev)
        window = ModeledEdgeWindow(bounds,samples)
        validate_group_reference(self.row,cfg,window)
        return cfg,window,source

    def apply_configuration(self):
        try:
            cfg,window,source = self.validate_configuration()
            selection_changed = (self.reference is not None and cfg.source==self.reference.source
                                 and cfg.pair_reversed!=self.reference.pair_reversed)
            if self.commit is not None:self.commit(cfg,window)
            self.configured.emit(cfg,window)
            if selection_changed:
                loading=self._loading;self._loading=True
                try:self.restore_reference(cfg)
                finally:self._loading=loading
            self.reference = cfg;self.window = window
            self.provenance = source.provenance()
            d = source.metadata
            self.status.setText(f'Configured and valid: {d["element"]} {d["edge"]}, {source.energy_ev[0]:g}–{source.energy_ev[-1]:g} eV. '
                'Relative per-atom units; physical calibration not established.')
            self.detail_text.setPlainText(json.dumps(self.provenance,indent=2,ensure_ascii=False))
            self._entry = self.snapshot()
            self._applied_snapshot = deepcopy(self._entry)
            return cfg
        except Exception as exc:
            self.status.setText('Invalid / incomplete: '+str(exc));return None

    def export_applied_source(self, path=None):
        """Expert exchange of the original input; no project serialization."""
        try:
            if self.reference is None:raise ValueError('Apply a valid source before exporting')
            validate_group_reference(self.row,self.reference,self.window)
            if path is None:
                path,_ = QtWidgets.QFileDialog.getSaveFileName(self,'Export original applied source (new file)',
                    Path(self.reference.source).name,'Original source files (*)')
            if not path:return None
            raw = Path(self.reference.source).read_bytes()
            # Preserve the already-established scientific source identity.
            import hashlib
            if hashlib.sha256(raw).hexdigest() != self.reference.source_sha256:
                raise ValueError('Source identity changed; validate again before export')
            with Path(path).open('xb') as stream:stream.write(raw)
            return Path(path)
        except Exception as exc:self.status.setText('Export unavailable: '+str(exc));return None

    def restore_reference(self, cfg):
        self.reference = cfg
        if cfg.model == 'atomic':
            self.model.setCurrentIndex(1);self.atomic_mode.setCurrentIndex(0);self.atomic_path.setText(cfg.source)
        elif cfg.model == 'xmcd':
            self.model.setCurrentIndex(0);self.source_path.setText(cfg.source)
            d = cfg.provider_declaration or {}
            for name,key in [('xmcd_edge','edge'),('xmcd_provenance','source'),('xmcd_validity','validity'),('xmcd_scale','reference_tensor_scale_angstrom2_per_ev')]:
                getattr(self,name).setText(str(d.get(key,'')))
            self.xmcd_selected.setText(json.dumps(d.get('selected_ev',{})))
            self.xmcd_edges.set_rows(list(d.get('selected_ev',{}).items()))
            for key in ('eta','beta'):self.spin[key].setValue(d.get(key,0.))
            for edge,key in [('L3','xl3'),('L2','xl2')]:self.spin[key].setValue(d.get('selected_ev',{}).get(edge,.001))
        else:
            self.model.setCurrentIndex(2);self.manual_mode.setCurrentIndex(3)
            self.import_path.setText(cfg.source);self.manual_edge.setText(cfg.core_edge)
            try:
                from .generalized_forward import source_for
                source = source_for(cfg);d = source.metadata
                if 'manual_l23_model' in d and not cfg.pair_reversed:
                    self.manual_spectral.load_source(source);self.manual_spectral.frame_mode.setCurrentIndex(1)
                    self.manual_mode.setCurrentIndex(1)
                elif d.get('manual_constant_editor') or d.get('manual_constant_pair_editor'):
                    a,b = [t.tensor_angstrom2_per_ev for t in (source.plus,source.minus)]
                    if np.all(a == a[0]) and np.all(b == b[0]) and (not d.get('manual_constant_editor') or np.allclose(b,a.conj(),rtol=0,atol=1e-12)):
                        for editor,tensor in zip(self.pair,(a[0],b[0])):
                            with QtCore.QSignalBlocker(editor.cells):
                                for i in range(3):
                                    for j in range(3):editor.cells.item(i,j).setText(str(tensor[i,j]).strip('()'))
                            editor.edited()
                        self.manual_edges.set_rows(list(d['selected_ev'].items()))
                        self.constant_energy.low.setValue(source.energy_ev[0]);self.constant_energy.high.setValue(source.energy_ev[-1])
                        self.constant_energy.kind.setCurrentText('Selected energies')
                        self.constant_energy.table.setRowCount(0)
                        for energy in source.energy_ev:self.constant_energy.add_energy(energy)
                        for i in range(3):
                            for j in range(3):self.manual_frame.item(i,j).setText(str(d['frame_to_crystal'][i][j]))
                        self.manual_source.setText(d['source']);self.manual_validity.setText(d['validity'])
                        self.manual_mode.setCurrentIndex(0 if d.get('manual_constant_editor') else 2)
            except (ValueError,OSError):pass  # Stale original remains an Advanced source; never substitute a default.
        self.pages.setEnabled(True);self.pages.setCurrentIndex(self.model.currentIndex())
        self.declaration.setChecked(cfg.axis_declared)

    def snapshot(self):
        # Selected edges are stored by their native controls below. The hidden
        # legacy adapter is derived text, not an independently editable draft.
        return dict(fields={key:w.text() for key,w in self._inputs.items() if key != 'xmcd_selected'},model=self.model.currentIndex(),
            source_info=deepcopy(self.source_info),validated_path=self.validated_path,reviewed_sha=self._reviewed_sha,
            manual=self.manual_mode.currentIndex(),atomic=deepcopy(self.atomic.draft()),
            atomic_mode=self.atomic_mode.currentIndex(),
            energy_window=self.energy_window.state(),constant_energy=self.constant_energy.state(),
            manual_edges=self.manual_edges.rows(),xmcd_edges=self.xmcd_edges.rows(),
            frame=[[self.manual_frame.item(i,j).text() for j in range(3)] for i in range(3)],
            spectral=deepcopy(self.manual_spectral.draft()),eta=self.eta.value(),beta=self.beta.value(),
            pair=[[[e.cells.item(i,j).text() for j in range(3)] for i in range(3)] for e in self.pair],
            selections=[self.spin[k].value() for k in ('xl3','xl2')],
            status=self.xmcd_status.currentIndex(),ack=self.declaration.isChecked())

    def restore_snapshot(self, state):
        self._loading = True
        self.source_info = None
        for key,text in state['fields'].items():self._inputs[key].setText(text)
        self.atomic.restore_draft(deepcopy(state['atomic']))
        self.atomic_mode.setCurrentIndex(state['atomic_mode'])
        self.energy_window.restore(state['energy_window']);self.constant_energy.restore(state['constant_energy'])
        self.manual_edges.set_rows(state['manual_edges']);self.xmcd_edges.set_rows(state['xmcd_edges'])
        for i in range(3):
            for j in range(3):self.manual_frame.item(i,j).setText(state['frame'][i][j])
        self.manual_spectral.restore_draft(deepcopy(state['spectral']))
        self.eta.setValue(state['eta']);self.beta.setValue(state['beta'])
        for editor,values in zip(self.pair,state['pair']):
            with QtCore.QSignalBlocker(editor.cells):
                for i in range(3):
                    for j in range(3):editor.cells.item(i,j).setText(values[i][j])
            editor.edited()
        self.model.setCurrentIndex(state['model']);self.manual_mode.setCurrentIndex(state['manual'])
        for key,value in zip(('xl3','xl2'),state['selections']):self.spin[key].setValue(value)
        self.xmcd_status.setCurrentIndex(state['status']);self.declaration.setChecked(state['ack'])
        self.source_info = deepcopy(state['source_info']);self.validated_path = state['validated_path'];self._reviewed_sha = state['reviewed_sha']
        self._loading = False
        self.provenance = None
        self.detail_text.clear()
        self.status.setText('Restored draft. Validate and Apply to confirm source identity, frame and coverage.')

    def open_draft(self, row):
        self.set_context(row);self._entry = self.snapshot()
        self.show();self.raise_();self.activateWindow()

    def has_unapplied_edits(self):
        if self._applied_snapshot is None:return False
        current=self.snapshot();accepted=deepcopy(self._applied_snapshot)
        # Material's read-only direction mirror is not an MDFF parameter edit.
        for state in (current,accepted):state['spectral'].pop('direction',None)
        return current!=accepted

    def closeEvent(self, event):
        event.accept()  # Keep incomplete drafts; explicit Cancel restores entry state.

    def reject(self):
        self.restore_snapshot(self._applied_snapshot or self._entry)
        self.draftChanged.emit()
        super().reject()
