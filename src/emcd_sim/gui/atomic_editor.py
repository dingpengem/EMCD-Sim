"""A source-backed atomic input editor, not an additional atomic physics model."""
from pathlib import Path
import copy
import hashlib
import json
import numpy as np
from ase.data import chemical_symbols, atomic_numbers, atomic_names
from PySide6 import QtCore, QtGui, QtWidgets
from .responsive import CollapsibleSection
from .atomic_editor_help import VISIBLE_LABELS,PLAIN_LANGUAGE,DETAILS,ORIGIN_LABELS
from .atomic_editor_model import (CAPABILITY, EDITOR_TAG, MAX_SAMPLES, ORBITALS,
    capability_reason, crystal_elements, edge_references, explicit_grid,
    validate_document, persist_document, read_document, reconcile_edge_origins)


# The same definitions feed tooltips, expanded help, and developer documentation.
FIELDS = {
    'l3': ('L3 reference energy', 'E_L3', 'eV', '0 < E_L3 < E_L2', '2p3/2 reference excitation, not necessarily a fitted peak maximum. The generator adds cubic and exchange shifts.'),
    'l2': ('L2 reference energy', 'E_L2', 'eV', 'E_L2 > E_L3', '2p1/2 reference excitation. Delta_SO = E_L2 - E_L3 is derived, not another fitted input.'),
    'cf': ('Cubic splitting', '10Dq', 'eV', 'finite, >= 0', 'eg shift +0.6*10Dq; t2g shift -0.4*10Dq about the weighted orbital centroid. Cubic symmetry only.'),
    'exchange': ('Effective exchange splitting', 'Delta_ex', 'eV', 'finite, >= 0', 'Shift = -spin_sign*magnetization_sign*Delta_ex/2. Not total exchange energy, a magnetic moment, or a many-body multiplet Hamiltonian.'),
    'radial': ('Radial dipole integral', 'D', 'Angstrom', 'finite, > 0', 'D = integral R_2p(r) R_3d(r) r^3 dr for full radial functions normalized with r^2 dr. Multiplies amplitudes; intensity scales quadratically. Declare calculation, effective fit, or synthetic origin.'),
    'holes': ('Orbital/spin holes', 'h(m,spin)', 'dimensionless', '[0,1], not all zero', 'Unoccupied final-state weights; electron occupation = 1-h within this independent-electron model. No normalization or magnetic-moment inference. Rows follow the generator exactly.'),
    'frame': ('Frame to crystal', 'R', 'dimensionless', 'R.T R=I, det R=+1 (tolerance 1e-12)', 'Columns are local axes in crystal Cartesian coordinates. Local M=(0,0,1); crystal M=R@(0,0,1). Rotate the entire cubic orbital/spin model; no independent noncollinear spin rotation or silent orthogonalization.'),
    'emin': ('Minimum energy loss', 'E_min', 'eV', '0 < E_min < E_max', 'First actual tensor sample, not an inferred threshold. Must cover the declared edges together with E_max. No automatic extension/extrapolation.'),
    'emax': ('Maximum energy loss', 'E_max', 'eV', 'E_max > E_min', 'Last actual tensor sample. Range and sampling are numerical choices, not physical convergence certification.'),
    'samples': ('Energy sample count', 'N_E', 'samples', f'integer 2..{MAX_SAMPLES}', 'Inclusive uniform linspace for a newly entered grid. Imported explicit grids are preserved exactly until the grid controls are edited. GUI allocation bound, not generator accuracy.'),
    'sigma': ('Gaussian standard deviation', 'sigma', 'eV', 'finite, > 0', 'FWHM = 2*sqrt(2*ln(2))*sigma. This is sigma, not FWHM; the accepted Gaussian broadening implementation is reused.'),
    'source': ('Parameter source', 'source', 'text/citation', 'nonempty', 'Give the origin of every material parameter, including manually overridden edge energies. CIF composition does not establish oxidation, magnetic order, or these electronic constants.'),
    'radial_source': ('Radial integral source', 'source_D', 'text/citation', 'nonempty', 'Identify a radial calculation, effective fit, or synthetic choice. No Ni or element-dependent value is automatically copied.'),
    'assumptions': ('Material/model assumptions', 'assumptions', 'text', 'nonempty', 'Declare physical interpretation and how the cubic independent-electron model approximates this material. The CIF alone is insufficient.'),
    'validity': ('Physical validity and limits', 'validity', 'text', 'nonempty', 'State missing physics and limits. Mathematical Hermiticity/PSD does not establish material-specific or experimental accuracy.'),
    'status': ('Scientific status', 'status', 'category', 'synthetic or physical_source_unvalidated', 'No quantitatively validated choice is provided. Synthetic inputs are software demonstrations only.'),
    'element': ('Active preparation element', 'Z, symbol', 'periodic-table identity', 'Z=1..118; generator Sc-Zn only', 'Presence in a CIF, atomic-model applicability, and executable single-element/equivalent-site eligibility are different questions. Multiple preparation selections are never summed.'),
    'edge': ('Core-loss transition', '2p -> 3d', 'edge family', 'L2,3 only for this generator', 'XMCD-constrained and imported tensor providers remain separate pathways with their own supported edge declarations.'),
    'normalization': ('Intensity normalization', 'T per atom', 'Angstrom^2/eV, relative', 'per_atom_relative (fixed)', 'No absolute cross-section calibration. Independently prepared tensors for different elements are not certified absolute comparisons.'),
}


def explanation(key):
    name, symbol, units, allowed, definition = FIELDS[key]
    return f'{name} ({symbol})\nUnits: {units}. Allowed: {allowed}.\n{definition}\nFrame: local real cubic orbital/spin frame unless specified; energies are scalar.\nProvenance: explicitly cite parameter/radial source and assumptions; editable does not mean calibrated.'


def tooltip(key):
    name,symbol,units,allowed,definition=FIELDS[key]
    return f'{name} ({symbol}). Units: {units}. Allowed: {allowed}.\n{definition.split(". ")[0]}\nProvenance: explicit source required. Expand Physical definitions for frame, relationships and limitations.'


class InputProblem(ValueError):
    def __init__(self,key,message):
        super().__init__(message);self.key=key


class AtomicParameterEditor(QtWidgets.QWidget):
    sourceReady = QtCore.Signal(str)
    invalidated = QtCore.Signal()

    def __init__(self, workspace, parent=None):
        super().__init__(parent)
        self.workspace = workspace
        self.owner=parent;self.historical_config=None
        self._loading = True
        self._states = {}
        self._element = ''
        self._context = None
        self._explicit_energy = None
        self.origins = {}
        self.parameter_origins = {}
        self.origin_labels = {}
        self.error_labels = {}
        self.info_buttons = {}
        self.reference_problem = ''
        self.validated_path = None
        self.validated_sha256 = None
        self._source_mode = False
        self.external_source_pending=False
        self._context_sync = False
        self.fields = {}
        self.sections = {}
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.use_editor = QtWidgets.QCheckBox('Use generalized manual atomic parameters (source-backed)')
        self.layout.addWidget(self.use_editor)
        f = self.section('A. Element and Core-loss Transition', ('element', 'edge'), True)
        self.crystal_box = QtWidgets.QGroupBox('Elements Available in Current Crystal')
        self.crystal_layout = QtWidgets.QVBoxLayout(self.crystal_box)
        f.addRow(self.crystal_box)
        self.element_boxes = {}
        self.element = QtWidgets.QComboBox()
        self.element.addItem('Select an element', '')
        for z, symbol in enumerate(chemical_symbols[1:], 1):
            self.element.addItem(f'{symbol} - {atomic_names[z]} (Z={z})', symbol)
        self.element.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.element.setMinimumContentsLength(14)
        self.element.setToolTip(tooltip('element'))
        f.addRow('One active ionizing/preparation element', self.element)
        self.add_explanation(f,'element')
        self.edge = QtWidgets.QComboBox(); self.edge.addItem('L2,3: electric-dipole 2p -> 3d', 'L2,3')
        self.edge.setToolTip(tooltip('edge')); f.addRow('Implemented transition', self.edge)
        self.add_explanation(f,'edge')
        self.capability = QtWidgets.QLabel(); self.capability.setWordWrap(True); f.addRow(self.capability)
        f = self.section('B. Core-level Energies', ('l3', 'l2'), True)
        self.field(f, 'l3'); self.field(f, 'l2')
        self.edge_status = QtWidgets.QLabel(); self.edge_status.setWordWrap(True)
        self.edge_status.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse); f.addRow(self.edge_status)
        self.button(f, 'Apply tabulated elemental references...', self.apply_references)
        self.button(f, 'Initialize numerical/frame starting choices...', self.initialize_defaults)
        self.derived_edges = QtWidgets.QLabel(); f.addRow(self.derived_edges)
        f = self.section('C. Crystal Field and Exchange', ('cf', 'exchange'))
        self.field(f, 'cf'); self.field(f, 'exchange')
        f = self.section('D. Orbital-resolved Hole Occupations', ('holes',))
        self.holes = self.table(5, 2, ['Up holes', 'Down holes'], ['d(z2)', 'd(x2-y2)', 'd(xy)', 'd(xz)', 'd(yz)'], 'holes')
        f.addRow(QtWidgets.QLabel('Spin-Resolved 3d Hole Occupations')); f.addRow(self.holes); self.add_explanation(f,'holes'); self.hole_totals = QtWidgets.QLabel(); f.addRow(self.hole_totals)
        f = self.section('E. Radial Dipole Matrix Element', ('radial', 'radial_source'))
        self.field(f, 'radial'); self.field(f, 'radial_source', numeric=False)
        f = self.section('F. Magnetization and Tensor Coordinate Frame', ('frame',))
        f.addRow(QtWidgets.QLabel('Magnetization Direction and Local Spin Axis: local M = (0,0,1), fixed by this model.'))
        self.frame_mode = QtWidgets.QComboBox(); self.frame_mode.addItems(['Select a frame', 'Identity frame (explicit choice)', 'Advanced proper rotation'])
        self.frame_mode.setToolTip(tooltip('frame')); f.addRow('Rigid orbital/spin frame', self.frame_mode)
        self.frame = self.table(3, 3, ['Local x', 'Local y', 'Local z'], ['Crystal x', 'Crystal y', 'Crystal z'], 'frame')
        f.addRow(QtWidgets.QLabel('Tensor Coordinate Frame - Local to Crystal')); f.addRow(self.frame); self.add_explanation(f,'frame'); self.derived_axis = QtWidgets.QLabel(); f.addRow(self.derived_axis)
        f = self.section('G. Spectral Energy Grid and Broadening', ('emin', 'emax', 'samples', 'sigma'))
        for key in ('emin', 'emax', 'samples', 'sigma'): self.field(f, key)
        self.button(f, 'Suggest starting grid from declared edges...', self.suggest_grid)
        self.grid_status = QtWidgets.QLabel(); self.grid_status.setWordWrap(True); f.addRow(self.grid_status)
        self.gaussian_status = QtWidgets.QLabel(); f.addRow(self.gaussian_status)
        f = self.section('H. Scientific Provenance and Validity', ('source', 'assumptions', 'validity', 'status', 'normalization'))
        for key in ('source', 'assumptions', 'validity'): self.field(f, key, numeric=False)
        self.scientific_status = QtWidgets.QComboBox(); self.scientific_status.addItems(['physical_source_unvalidated', 'synthetic'])
        self.scientific_status.setToolTip(tooltip('status')); f.addRow('Scientific status', self.scientific_status)
        norm = QtWidgets.QLabel('per_atom_relative; Angstrom^2/eV; no absolute cross-section calibration')
        norm.setWordWrap(True); norm.setToolTip(tooltip('normalization')); f.addRow(norm)
        f = self.section('I. Validation, Preview, Import and Export', (), True)
        self.validity_banner = QtWidgets.QLabel(); self.validity_banner.setWordWrap(True); f.addRow(self.validity_banner)
        self.status = QtWidgets.QLabel('Draft inputs; no generated source validated.'); self.status.setWordWrap(True); f.addRow(self.status)
        self.source_location = QtWidgets.QLineEdit(); self.source_location.setReadOnly(True); f.addRow('Managed immutable source (SHA256 filename)', self.source_location)
        self.preview_button = self.button(f, 'Preview MDFF Tensor Spectrum', self.preview)
        self.generate_button = self.button(f, 'Validate complete atomic source', self.generate)
        self.button(f, 'How Is the MDFF Tensor T(E) Constructed?', self.show_construction)
        self.button(f, 'Import parameter JSON...', self.import_dialog)
        self.button(f, 'Save parameter JSON...', self.export_dialog)
        self.button(f, 'Load Synthetic Fe Demonstration', self.load_demo)
        self.element.currentIndexChanged.connect(self.change_element)
        self.frame_mode.currentIndexChanged.connect(self.change_frame)
        self.scientific_status.currentIndexChanged.connect(self.edited)
        self.use_editor.toggled.connect(lambda _: self.edited(activate=False))
        self._loading = False
        from .mdff_usability import compact_atomic
        compact_atomic(self)

    @property
    def active(self):
        return self.historical_config is None and self.use_editor.isChecked()

    def clear_historical(self):
        if self.historical_config is None:return
        self.historical_config=None
        from .saved_atomic_ui import set_read_only
        set_read_only(self,False)

    def section(self, title, keys, expanded=False):
        s = CollapsibleSection(title, expanded=expanded); self.sections[title[0]] = s; self.layout.addWidget(s)
        form = QtWidgets.QFormLayout(s.body); form.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapLongRows)
        error=QtWidgets.QLabel();error.setWordWrap(True);error.setStyleSheet('color: #9b1c1c');form.addRow(error);self.error_labels[title[0]]=error
        if keys:
            help_box = CollapsibleSection('Physical definitions, units and limitations', expanded=False)
            layout = QtWidgets.QVBoxLayout(help_box.body)
            label = QtWidgets.QLabel('\n\n'.join(explanation(k) for k in keys)); label.setWordWrap(True); label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(label); form.addRow(help_box)
        return form

    def field(self, form, key, numeric=True):
        field = QtWidgets.QLineEdit(); field.setPlaceholderText('Required explicit input')
        if numeric:
            validator = QtGui.QIntValidator(2, MAX_SAMPLES, field) if key == 'samples' else QtGui.QDoubleValidator(field)
            validator.setLocale(QtCore.QLocale.c()); field.setValidator(validator)
        field.setToolTip(tooltip(key)); self.fields[key] = field
        title, symbol, units, _, _ = FIELDS[key]; form.addRow(VISIBLE_LABELS.get(key,f'{title}, {symbol} ({units})'), field)
        self.add_explanation(form,key)
        field.textChanged.connect(lambda _, k=key: self.field_changed(k))

    def table(self, rows, cols, headings, rownames, key):
        table = QtWidgets.QTableWidget(rows, cols); table.setHorizontalHeaderLabels(headings); table.setVerticalHeaderLabels(rownames)
        table.setToolTip(tooltip(key)); table.setMaximumHeight(240 if rows == 5 else 160)
        for i in range(rows):
            for j in range(cols):
                edit = QtWidgets.QLineEdit(); edit.setValidator(QtGui.QDoubleValidator(edit)); edit.validator().setLocale(QtCore.QLocale.c())
                edit.setToolTip(tooltip(key) + f'\nRow {rownames[i]}, column {headings[j]}.')
                edit.textChanged.connect(lambda _,k=key,r=i,c=j:self.table_changed(k,r,c)); table.setCellWidget(i, j, edit)
        return table

    def button(self, form, title, callback):
        button = QtWidgets.QPushButton(title); button.clicked.connect(lambda checked=False: callback()); form.addRow(button); return button

    def add_explanation(self,form,key):
        pane=QtWidgets.QWidget();layout=QtWidgets.QVBoxLayout(pane);layout.setContentsMargins(0,0,0,3)
        row=QtWidgets.QHBoxLayout();line=QtWidgets.QLabel(PLAIN_LANGUAGE[key]);line.setWordWrap(True);row.addWidget(line,1)
        button=QtWidgets.QToolButton();button.setText('i');button.setAccessibleName('Physical details: '+FIELDS[key][0]);button.clicked.connect(lambda checked=False,k=key:self.show_field_details(k));row.addWidget(button);layout.addLayout(row);self.info_buttons[key]=button
        origin=QtWidgets.QLabel();origin.setWordWrap(True);origin.setStyleSheet('color: #555');layout.addWidget(origin);self.origin_labels[key]=origin;form.addRow(pane)

    def show_field_details(self,key):
        d=QtWidgets.QDialog(self);d.setWindowTitle(FIELDS[key][0]+' - definition and provenance');d.resize(760,560)
        current='\n\n'+self.origin_labels[key].text() if key in ('l3','l2') else ''
        layout=QtWidgets.QVBoxLayout(d);text=QtWidgets.QPlainTextEdit(explanation(key)+'\n\n'+DETAILS.get(key,FIELDS[key][4])+current);text.setReadOnly(True);layout.addWidget(text)
        layout.addWidget(QtWidgets.QLabel('Optional parameter-specific citation / source note (overall provenance remains required)'))
        citation=QtWidgets.QLineEdit(self.parameter_origins.get(key,{}).get('citation',''));layout.addWidget(citation);citation.textChanged.connect(lambda value,k=key:self.set_parameter_citation(k,value));d.show();self.field_detail_dialog=d

    def set_parameter_citation(self,key,value):
        info=dict(self.parameter_origins.get(key,dict(origin='user_entered')));info['citation']=value;self.parameter_origins[key]=info;self.edited()

    def refresh_origin_labels(self):
        for key,label in self.origin_labels.items():
            info=self.parameter_origins.get(key,{})
            label.setText('Origin: '+ORIGIN_LABELS.get(info.get('origin'),info.get('origin','Explicit input required'))+(' | '+info['citation'] if info.get('citation') else ''))
            if key in ('l3','l2'):self.fields[key].setToolTip(tooltip(key)+'\n'+label.text())
        for i in range(5):
            for j in range(2):
                info=self.parameter_origins.get(f'holes.{i}.{j}',self.parameter_origins.get('holes',{}))
                self.holes.cellWidget(i,j).setToolTip(tooltip('holes')+'\nOrigin: '+ORIGIN_LABELS.get(info.get('origin'),info.get('origin','Explicit input required')))

    def table_changed(self,key,row,column):
        if self._loading:return
        self.external_source_pending=False
        self.parameter_origins[key]=dict(origin='user_entered')
        if key=='holes':self.parameter_origins[f'holes.{row}.{column}']=dict(origin='user_entered')
        self.edited()

    @staticmethod
    def initial_draft():
        fields=dict(sigma='1.0',cf='0',exchange='0.5',radial='1',
            source='Generic synthetic electronic starting choices; elemental tabulated edge references where available',
            radial_source='Synthetic unit radial integral, 1 Angstrom; not a calculated material radial function',
            assumptions='Cubic independent-electron example; uniform ferromagnetic spin weights, not inferred from CIF',
            validity='Synthetic example; no material calibration, bands, multiplets or quantitative spectroscopy')
        origins={key:dict(origin='synthetic_demonstration',citation='Generic editor default; not measured or material-specific') for key in FIELDS}
        origins['sigma']=dict(origin='numerical_starting',citation='Generic numerical sigma=1 eV; not experimental resolution')
        origins['frame']=dict(origin='coordinate_starting',citation='Identity frame; crystal Cartesian coordinates')
        return dict(fields=fields,holes=[[.2,.4] for _ in range(5)],frame=np.eye(3,dtype=int).tolist(),frame_mode=1,status='synthetic',parameter_origins=origins)

    def reset_defaults(self):
        self.clear_historical()
        with QtCore.QSignalBlocker(self.use_editor):self.use_editor.setChecked(True)
        self.restore_draft(self.initial_draft())
        if self._element and not capability_reason(self._element):self.apply_references(confirm=False)
        self.edited()

    def initialize_grid_if_empty(self):
        if any(self.fields[k].text() for k in ('emin','emax','samples')):return
        lo=float(self.fields['l3'].text());hi=float(self.fields['l2'].text())
        if not 0<lo<hi:return
        for key,value in (('emin',max(np.nextafter(0.,1.),lo-10)),('emax',hi+10),('samples',201)):
            self.fields[key].setText(str(value));self.parameter_origins[key]=dict(origin='numerical_starting',citation='Explicitly labeled starting grid: 10 eV margins and201 samples, not converged spectroscopy')
        self.grid_status.setText('Numerical starting grid: 10 eV margins,201 samples. Editable; not a physical range or convergence certificate.')

    def initialize_defaults(self):
        if QtWidgets.QMessageBox.question(self,'Replace numerical/frame choices?','Reset only Gaussian sigma, coordinate frame and grid to labeled numerical starting choices? No material electronic parameters will be supplied.')!=QtWidgets.QMessageBox.StandardButton.Yes:return
        self._loading=True
        self.fields['sigma'].setText('1.0');self.frame_mode.setCurrentIndex(1)
        for i in range(3):
            for j in range(3):self.frame.cellWidget(i,j).setText(str(int(i==j)))
        for key in ('emin','emax','samples'):self.fields[key].clear()
        self.parameter_origins.update(self.initial_draft()['parameter_origins'])
        try:self.initialize_grid_if_empty()
        except ValueError:self.grid_status.setText('Enter both edge references before initializing a grid.')
        self._loading=False;self.frame.setEnabled(False);self.edited()

    def show_problem(self,exc,prefix):
        key=getattr(exc,'key','');text=str(exc)
        if not key:
            key='holes' if 'hole' in text.lower() else 'frame' if 'frame' in text.lower() else 'energy_grid' if 'grid' in text.lower() else 'radial' if 'radial' in text.lower() else 'source'
        group='A' if key in ('element','edge') else 'B' if key in ('l3','l2') else 'C' if key in ('cf','exchange') else 'D' if key=='holes' else 'E' if key in ('radial','radial_source') else 'F' if key=='frame' else 'G' if key in ('emin','emax','samples','sigma','energy_grid') else 'H'
        self.sections[group].setChecked(True);self.error_labels[group].setText(text);self.status.setText(prefix+': '+text)
        if hasattr(self,'main_error'):
            self.main_error.setText(prefix+': '+text)
            self.preview_state.setText(prefix+': '+text+'; numerical spectrum remains stale.')
            if group in ('C','D','E','F','G','H'):self.advanced_parameters.setChecked(True)
        if key in self.fields:self.fields[key].setFocus()

    def field_changed(self, key):
        if self._loading: return
        self.external_source_pending=False
        self.parameter_origins[key]=dict(origin='user_entered',citation=self.parameter_origins.get(key,{}).get('citation',''))
        if key in ('l3', 'l2'):
            self.origins[key] = dict(origin='manual', previous_reference=self.origins.get(key, {}).get('url', ''))
        if key in ('emin', 'emax', 'samples'): self._explicit_energy = None
        self.edited()

    def edited(self, *_, activate=True):
        if self._loading: return
        if self.historical_config is not None:return
        if activate and not self._context_sync:
            with QtCore.QSignalBlocker(self.use_editor): self.use_editor.setChecked(True)
        self.validated_path = self.validated_sha256 = None
        for label in self.error_labels.values():label.clear()
        self.invalidate_preview('Physical inputs, source or crystal changed')
        if hasattr(self,"preview_state"):self.preview_state.setText("STALE numerical spectrum - update preview for current draft.")
        self.status.setText('UNVALIDATED EDITS - previous tensor/acknowledgement invalidated. Approximate atomic model; no physical calibration.')
        self.invalidated.emit(); self.update_derived()

    def update_derived(self):
        if hasattr(self,"schematic"):
            self.schematic.draw()
            try:self.direction.setText(" ".join(self.frame.cellWidget(i,2).text() for i in range(3)))
            except ValueError:pass
        if hasattr(self,'main_error'):self.main_error.setText(capability_reason(self.element.currentData()) or self.reference_problem)
        scientific_status=self.scientific_status.currentText()
        banner=('SYNTHETIC SOFTWARE TEST - NOT PHYSICALLY VALIDATED '+str(self.element.currentData())+' SPECTROSCOPY'
            if scientific_status=='synthetic' else 'APPROXIMATE ATOMIC MODEL - PHYSICALLY UNVALIDATED MATERIAL PARAMETERS')
        if any(x.get('origin')=='synthetic_demonstration' for x in self.parameter_origins.values()):banner+='; contains explicitly synthetic demonstration values'
        self.validity_banner.setText(banner+'\nParameter source: '+(self.fields['source'].text() or 'required')+
            '\nValidity: '+(self.fields['validity'].text() or 'required')+'\nRelative per-atom tensor, not absolute inter-element cross sections.')
        try:
            sigma=float(self.fields['sigma'].text())
            if not np.isfinite(sigma) or sigma<=0:raise ValueError('sigma')
            self.gaussian_status.setText(f'Derived Gaussian FWHM = {2*np.sqrt(2*np.log(2))*sigma:g} eV; sigma = {sigma:g} eV')
        except ValueError:self.gaussian_status.setText('A positive Gaussian sigma is required; FWHM is derived.')
        try:
            l3, l2 = (float(self.fields[k].text()) for k in ('l3', 'l2'))
            self.derived_edges.setText(f'Derived Delta_SO = {l2-l3:g} eV (not an independent fit)')
        except ValueError: self.derived_edges.setText('Delta_SO requires both explicit edge references.')
        try:
            h = np.array(self.table_values(self.holes), float)
            if hasattr(self,'hole_figure') and self.table_values(self.holes)!=getattr(self,'_hole_fingerprint',None):
                self._hole_fingerprint=self.table_values(self.holes)
                self.hole_figure.clear();ax=self.hole_figure.subplots()
                ax.imshow(h.T,vmin=0,vmax=1,cmap='Blues',aspect='auto')
                ax.set(xticks=range(5),xticklabels=['z^2','x^2-y^2','xy','xz','yz'],yticks=[0,1],yticklabels=['up holes','down holes'],title='Schematic hole weights (0-1)',xlabel='Orbital weights; not electron density')
                self.hole_canvas.draw_idle()
            self.hole_totals.setText(f'Up holes: {h[:,0].sum():g}; down holes: {h[:,1].sum():g}; total d holes: {h.sum():g}. Not normalized.')
        except ValueError: self.hole_totals.setText('Enter all five orbital/spin hole pairs explicitly.')
        try:
            frame = np.array(self.table_values(self.frame), float)
            valid = np.isfinite(frame).all() and np.allclose(frame.T @ frame, np.eye(3), atol=1e-12, rtol=0) and np.isclose(np.linalg.det(frame), 1, atol=1e-12, rtol=0)
            self.derived_axis.setText('Derived crystal M = '+str(frame[:,2].tolist()) if valid else 'Invalid proper frame; no silent repair.')
        except ValueError: self.derived_axis.setText('Select/enter a complete proper frame.')
        self.refresh_origin_labels()
        self.edge_status.setText('Edge input provenance - verify the current chemical environment; table references are not material predictions.\n'+
            (self.reference_problem+'\n' if self.reference_problem else '')+
            ('No bundled trustworthy reference; enter explicitly sourced energies.\n' if not self.origins else '')+
            '\n'.join(f'{k.upper()}: {v.get("origin", "imported")}; '+v.get('title', 'explicit source required')+'; '+v.get('reference_version','')+'\n'+v.get('url','') for k, v in self.origins.items())+
            '\nThreshold references are not peak maxima; CIF does not determine chemical shifts.')

    @staticmethod
    def table_values(table):
        return [[table.cellWidget(i,j).text() for j in range(table.columnCount())] for i in range(table.rowCount())]

    def draft(self):
        return dict(fields={k:w.text() for k,w in self.fields.items()}, holes=self.table_values(self.holes), frame=self.table_values(self.frame),
            frame_mode=self.frame_mode.currentIndex(), status=self.scientific_status.currentText(), origins=copy.deepcopy(self.origins), energy=copy.deepcopy(self._explicit_energy),reference_problem=self.reference_problem,parameter_origins=copy.deepcopy(self.parameter_origins))

    def restore_draft(self, draft):
        self._loading = True
        for key, widget in self.fields.items(): widget.setText(draft.get('fields', {}).get(key, ''))
        for table, key in ((self.holes, 'holes'), (self.frame, 'frame')):
            values = draft.get(key, [['']*table.columnCount() for _ in range(table.rowCount())])
            for i, row in enumerate(values):
                for j, value in enumerate(row): table.cellWidget(i,j).setText(str(value))
        self.frame_mode.setCurrentIndex(draft.get('frame_mode', 0)); self.frame.setEnabled(self.frame_mode.currentIndex() == 2)
        self.scientific_status.setCurrentText(draft.get('status', 'physical_source_unvalidated'))
        self.parameter_origins=copy.deepcopy(draft.get('parameter_origins',{}))
        self.origins = copy.deepcopy(draft.get('origins', {})); self._explicit_energy = copy.deepcopy(draft.get('energy'))
        self.reference_problem = draft.get('reference_problem','')
        self._loading = False

    def change_element(self, *_):
        if self._loading: return
        if self._element: self._states[self._element] = self.draft()
        self._element = self.element.currentData()
        self.restore_draft(self._states.get(self._element, self.initial_draft()))
        reason = capability_reason(self._element)
        self.capability.setText(reason or 'Atomic model: Sc-Zn / cubic 2p->3d L2,3. Preparation is separate from crystal/site execution eligibility.\n'+CAPABILITY['limitations'])
        self.generate_button.setEnabled(not reason)
        if self._element not in self._states and not reason: self.apply_references(confirm=False)
        self.edited()

    def set_crystal(self, structure, *, preserve_validation=False):
        atoms = structure.atoms
        key = (tuple(atoms.get_chemical_symbols()), atoms.cell.array.tobytes(), atoms.get_scaled_positions().tobytes(),
            repr(atoms.info.get('occupancy', {})), structure.source, structure.sha256)
        if key == self._context: return
        if self.historical_config is not None and not preserve_validation:
            self.clear_historical();self.restore_draft(self._states.get(self._element,self.initial_draft()))
            with QtCore.QSignalBlocker(self.use_editor):self.use_editor.setChecked(True)
        self._context = key
        self._context_sync = True
        while self.crystal_layout.count():
            item = self.crystal_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.element_boxes = {}
        descriptions = crystal_elements(atoms)
        for info in descriptions:
            box = QtWidgets.QCheckBox(f'{info["symbol"]} ({info["name"]}, Z={info["atomic_number"]}); {info["count"]} ASE sites; indices {info["site_indices"]}')
            box.setToolTip('Occupancy metadata: '+repr(info['occupancy'])+'\nWeights on ASE sites: '+repr(info['site_occupancy_weights'])+'\nPartial sites are not distinct fully occupied atoms. Composition does not determine oxidation, spin or magnetic structure.')
            box.setStyleSheet('font-weight: bold' if info['supported'] else '')
            box.toggled.connect(self.preparation_selection_changed); self.crystal_layout.addWidget(box); self.element_boxes[info['symbol']] = box
        notice = QtWidgets.QLabel('Preparation checkboxes do not select multiple execution groups. Multi-element/inequivalent-site EMCD remains unsupported.'); notice.setWordWrap(True); self.crystal_layout.addWidget(notice)
        if not preserve_validation:
            if len(descriptions) == 1:
                self.element.setCurrentIndex(self.element.findData(descriptions[0]['symbol']))
            self.edited(activate=False)
        if self._element in self.element_boxes:self.parameter_origins['element']=dict(origin='cif_derived',citation=str(structure.source)+'; SHA256 '+str(structure.sha256))
        self._context_sync = False
        self.update_derived()

    def preparation_selection_changed(self, *_):
        checked = [s for s,b in self.element_boxes.items() if b.isChecked()]
        if len(checked) == 1: self.element.setCurrentIndex(self.element.findData(checked[0]))
        self.edited()

    def apply_references(self, confirm=True):
        try: refs = edge_references(self._element)
        except (OSError, ValueError) as exc:
            self.estimated_edges(str(exc)); return
        if not refs:
            self.estimated_edges('No bundled trustworthy elemental edge reference.'); return
        if confirm and any(self.fields[k].text() for k in ('l3', 'l2')):
            if QtWidgets.QMessageBox.question(self, 'Replace edited edge references?', 'Replace current L3/L2 values with tabulated elemental references? Existing validation will be invalidated.') != QtWidgets.QMessageBox.StandardButton.Yes: return
        self._loading = True
        self.reference_problem=''
        for key, edge in (('l3', 'L3'), ('l2', 'L2')):
            self.fields[key].setText(str(refs[edge]['energy_ev'])); self.origins[key] = refs[edge]
            self.parameter_origins[key]=dict(origin='tabulated_reference',citation=refs[edge]['url'],library=refs[edge]['library'])
        self.initialize_grid_if_empty()
        self._loading = False; self.edited(activate=confirm)

    def estimated_edges(self, reason):
        # Explicitly synthetic scale for a usable draft, never a substituted element reference.
        z=atomic_numbers.get(self._element,0)
        lo=max(1.,.4*13.6*(z-10)**2);hi=lo+max(1.,.02*lo)
        self._loading=True
        self.fields['l3'].setText(str(lo));self.fields['l2'].setText(str(hi))
        for key in ('l3','l2'):
            self.parameter_origins[key]=dict(origin='synthetic_demonstration',citation='Synthetic hydrogenic energy scale only; not a reference or material prediction')
        self.reference_problem=reason+' Synthetic estimated energies supplied for demonstration only; replace with sourced values.'
        self.initialize_grid_if_empty();self._loading=False;self.edited()

    def change_frame(self, index):
        if self._loading: return
        if index == 1:
            self._loading = True
            for i in range(3):
                for j in range(3): self.frame.cellWidget(i,j).setText(str(int(i == j)))
            self._loading = False
        self.external_source_pending=False
        self.parameter_origins['frame']=dict(origin='user_entered',citation='Explicit rigid coordinate-frame choice')
        self.frame.setEnabled(index == 2); self.edited()

    def suggest_grid(self):
        try:
            lo, hi = (float(self.fields[k].text()) for k in ('l3', 'l2'))
            if not 0 < lo < hi: raise ValueError('Enter positive ascending edge references first')
            if any(self.fields[k].text() for k in ('emin', 'emax', 'samples')):
                if QtWidgets.QMessageBox.question(self, 'Replace explicit energy grid?', 'Use a numerical starting grid, not a physically established range or convergence certificate?') != QtWidgets.QMessageBox.StandardButton.Yes: return
            self.fields['emin'].setText(str(max(np.nextafter(0., 1.), lo-10)))
            self.fields['emax'].setText(str(hi+10)); self.fields['samples'].setText('201')
            self.grid_status.setText('Explicitly accepted numerical starting configuration: 10 eV margins, 201 samples. Review range and sampling; not converged material spectroscopy.')
            for key in ('emin','emax','samples'):self.parameter_origins[key]=dict(origin='numerical_starting',citation='Explicitly accepted numerical grid suggestion')
            self.update_derived()
        except ValueError as exc: self.status.setText(str(exc))

    def document(self):
        if self.historical_config is not None:raise ValueError('Saved model is retained read-only; Reset defaults starts a new editable source')
        reason = capability_reason(self.element.currentData(), self.edge.currentData())
        if reason: raise InputProblem('element',reason)
        for key, field in self.fields.items():
            if not field.text().strip(): raise InputProblem(key,'Required explicit input: '+FIELDS[key][0])
        if self.frame_mode.currentIndex() == 0: raise ValueError('Explicitly select the orbital/spin frame')
        def f(key):
            try:value=float(self.fields[key].text())
            except ValueError as exc:raise InputProblem(key,'Enter a real numeric '+FIELDS[key][0]) from exc
            if not np.isfinite(value):raise InputProblem(key,'Enter a finite '+FIELDS[key][0])
            return value
        for key in ('radial','sigma'):
            if f(key)<=0:raise InputProblem(key,FIELDS[key][0]+' must be positive')
        for key in ('cf','exchange'):
            if f(key)<0:raise InputProblem(key,FIELDS[key][0]+' must be nonnegative')
        if not 0<f('l3')<f('l2'):raise InputProblem('l3','Require 0 < E_L3 < E_L2')
        source = self.fields['source'].text().strip()
        trace = dict(edge_origins=self.origins, assumptions=self.fields['assumptions'].text().strip(),parameter_origins=self.parameter_origins,initialization_policy='synthetic-electronic-starting-v2; tabulated elemental edges where available; no material calibration')
        source += EDITOR_TAG + json.dumps(trace, sort_keys=True, allow_nan=False)
        try:hole_values=np.array(self.table_values(self.holes),float).tolist()
        except ValueError as exc:raise InputProblem('holes','Enter all ten real orbital/spin hole weights') from exc
        try:frame_values=np.array(self.table_values(self.frame),float).tolist()
        except ValueError as exc:raise InputProblem('frame','Enter all nine real proper-frame entries') from exc
        params = dict(element=self.element.currentData(), atomic_number=atomic_numbers[self.element.currentData()],
            edge_energies_ev=[f('l3'), f('l2')], radial_integral_angstrom=f('radial'), crystal_field_basis='real_cubic_eg_t2g',
            crystal_field_ev=f('cf'), exchange_ev=f('exchange'), spin_resolved_holes=hole_values,
            magnetization_local=[0,0,1], frame_to_crystal=frame_values,
            broadening_ev=f('sigma'), source=source, radial_source=self.fields['radial_source'].text().strip(),
            validity=self.fields['validity'].text().strip(), status=self.scientific_status.currentText())
        try:energy = self._explicit_energy if self._explicit_energy is not None else explicit_grid(f('emin'), f('emax'), f('samples'))
        except InputProblem:raise
        except ValueError as exc:raise InputProblem('samples' if 'integer' in str(exc) else 'emin',str(exc)) from exc
        doc = dict(schema=1, kind='atomic_2p3d', parameters=params, energy_ev=energy)
        validate_document(doc); return doc

    def load_document(self, path, *, validated=False):
        self.clear_historical()
        doc, digest = read_document(path); p = doc['parameters']; symbol = p['element']
        source, _, encoded = p['source'].partition(EDITOR_TAG)
        trace = json.loads(encoded) if encoded else {}
        origins=copy.deepcopy(trace.get('edge_origins', {k:dict(origin='imported', document_sha256=digest) for k in ('l3','l2')}))
        kind='imported_synthetic' if p['status']=='synthetic' else 'imported_physical_source'
        parameter_origins=trace.get('parameter_origins',{key:dict(origin=kind,citation='Imported document SHA256 '+digest) for key in FIELDS})
        origins,parameter_origins=reconcile_edge_origins(symbol,p['edge_energies_ev'],origins,parameter_origins,digest)
        fields = dict(l3=str(p['edge_energies_ev'][0]), l2=str(p['edge_energies_ev'][1]), cf=str(p['crystal_field_ev']),
            exchange=str(p['exchange_ev']), radial=str(p['radial_integral_angstrom']), sigma=str(p['broadening_ev']),
            emin=str(doc['energy_ev'][0]), emax=str(doc['energy_ev'][-1]), samples=str(len(doc['energy_ev'])), source=source,
            radial_source=p['radial_source'], validity=p['validity'], assumptions=trace.get('assumptions', 'Imported explicit cubic independent-electron 2p-to-3d parameter document; see original source/validity.'))
        draft = dict(fields=fields, holes=p['spin_resolved_holes'], frame=p['frame_to_crystal'],
            frame_mode=1 if np.array_equal(p['frame_to_crystal'], np.eye(3)) else 2, status=p['status'], energy=doc['energy_ev'],
            origins=origins)
        if self._element: self._states[self._element] = self.draft()
        self.external_source_pending=False
        self._loading = True; self.element.setCurrentIndex(self.element.findData(symbol)); self._element = symbol
        draft['parameter_origins']=parameter_origins
        self.restore_draft(draft); self._loading = True; self.use_editor.setChecked(True); self._loading = False
        self.grid_status.setText(f'Imported explicit grid: {len(doc["energy_ev"])} samples, preserved exactly until grid controls are edited. No extrapolation.')
        self.capability.setText(CAPABILITY['limitations']); self.generate_button.setEnabled(True)
        self.edited()
        if validated:
            self.validated_path = str(Path(path).resolve()); self.validated_sha256 = digest; self.source_location.setText(self.validated_path)
            self.status.setText('Validated source SHA256 '+digest+'\nAPPROXIMATE / '+p['status']+'; relative per-atom tensor, not detector spectra.')
        self.update_derived()

    def load_demo(self):
        if any(w.text() for k,w in self.fields.items() if k not in ('l3','l2')):
            if QtWidgets.QMessageBox.question(self, 'Replace current draft?', 'Load the explicitly synthetic Fe software demonstration into the editable fields?') != QtWidgets.QMessageBox.StandardButton.Yes: return
        from .runtime import resource_root
        root = resource_root(); path = root/'examples/synthetic_fe_atomic_parameters.json'
        if not path.exists(): path = root/'docs/examples/synthetic_fe_atomic_parameters.json'
        self.load_document(path)
        citation='Original reviewed synthetic Fe fixture; SHA256 '+hashlib.sha256(path.read_bytes()).hexdigest()
        self.parameter_origins={key:dict(origin='synthetic_demonstration',citation=citation) for key in FIELDS}
        for i in range(5):
            for j in range(2):self.parameter_origins[f'holes.{i}.{j}']=dict(origin='synthetic_demonstration',citation=citation)
        self.origins={k:dict(origin='synthetic_demonstration',title='Original reviewed synthetic Fe fixture',citation=citation) for k in ('l3','l2')}
        self.update_derived()
        self.status.setText('SYNTHETIC SOFTWARE TEST - NOT PHYSICALLY VALIDATED Fe SPECTROSCOPY. Fields are editable; validate a new managed source.')

    def generate(self):
        if self.historical_config is not None:
            self.status.setText('Retained saved model; use its preview or Reset defaults for a new source.');return
        self.invalidated.emit(); self.validated_path = self.validated_sha256 = None
        try:
            if self.external_source_pending:raise InputProblem('source','Import or validate the newly selected external JSON first; no old editor tensor will be substituted')
            doc = self.document(); path, digest = persist_document(self.workspace(), doc)
            # Existing provider performs transition generation, Hermiticity, PSD and provenance verification.
            from .generalized_forward import settings_for_provider
            settings_for_provider(path, 'atomic')
            self.validated_path = str(path); self.validated_sha256 = digest; self.source_location.setText(str(path))
            self._loading = True; self.use_editor.setChecked(True); self._loading = False
            self.sourceReady.emit(str(path))
            self.status.setText('Validated source SHA256 '+digest+'\nAPPROXIMATE / '+doc['parameters']['status']+'; relative per-atom units; material accuracy unvalidated.')
        except Exception as exc:self.show_problem(exc,'Generation blocked')

    def preview(self):
        if self.historical_config is not None:
            self.owner.preview_mdff();return
        try:
            if not self.validated_path:
                self.generate()  # Explicit Preview action; never regenerate per keystroke.
                if not self.validated_path:return
            _, digest = read_document(self.validated_path)
            if digest != self.validated_sha256: raise ValueError('Atomic source checksum changed')
            from .generalized_forward import settings_for_provider
            from ..mdff_providers import load_provider
            from .tensor_spectrum_preview import TensorSpectrumPreview
            source=load_provider(settings_for_provider(self.validated_path,'atomic'))
            old=getattr(self,'preview_dialog',None)
            if old is not None:old.close()
            self.preview_dialog=TensorSpectrumPreview(source,self)
            if hasattr(self,'spectrum_figure'):
                self.spectrum_figure.clear();ax=self.spectrum_figure.subplots()
                for label,tensor in (('+M',source.plus),('-M',source.minus),('Even',source.even)):
                    ax.plot(source.energy_ev,np.trace(tensor.tensor_angstrom2_per_ev,axis1=-2,axis2=-1).real/3,label=label)
                ax.set(xlabel='Energy loss (eV)',ylabel='Tr(T)/3');ax.legend(fontsize=8);self.spectrum_canvas.draw_idle()
                self.preview_state.setText('CURRENT numerical tensor spectrum; relative Angstrom^2/eV. Detailed components / odd response available below.')
            self.preview_dialog.show()
        except Exception as exc:
            self.edited();self.show_problem(exc,'Preview blocked')

    def invalidate_preview(self,reason):
        dialog=getattr(self,'preview_dialog',None)
        if dialog is not None and hasattr(dialog,'mark_stale'):dialog.mark_stale(reason)

    def show_construction(self):
        from .tensor_spectrum_preview import CONSTRUCTION
        d=QtWidgets.QDialog(self);d.setWindowTitle('How Is the MDFF Tensor T(E) Constructed?');d.resize(850,700)
        layout=QtWidgets.QVBoxLayout(d);text=QtWidgets.QPlainTextEdit(CONSTRUCTION);text.setReadOnly(True);layout.addWidget(text);d.show();self.construction_dialog=d

    def import_dialog(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Import complete atomic parameters', '', 'JSON (*.json)')
        if not path: return
        if self.active and QtWidgets.QMessageBox.question(self, 'Replace current draft?', 'Import this document into the editor? Current source validation will be invalidated.') != QtWidgets.QMessageBox.StandardButton.Yes: return
        try: self.load_document(path)
        except Exception as exc: self.edited(); self.status.setText('Import blocked: '+str(exc))

    def export_dialog(self):
        try:
            doc = self.document()
            path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save complete atomic parameter input', '', 'JSON (*.json)')
            if not path: return
            target = Path(path)
            if target.is_dir():raise ValueError('Choose a JSON filename, not a directory')
            managed=(Path(self.workspace()).resolve()/'atomic_inputs')
            if target.resolve().is_relative_to(managed):raise ValueError('Managed atomic sources are immutable; export to a different user filename outside atomic_inputs')
            if target.exists():
                if QtWidgets.QMessageBox.question(self, 'Overwrite parameter file?', 'Replace this existing user file? Managed validated sources are immutable.') != QtWidgets.QMessageBox.StandardButton.Yes: return
                if self.validated_path and target.resolve() == Path(self.validated_path).resolve(): raise ValueError('Choose a new file; managed validated source will not be overwritten')
                from tempfile import NamedTemporaryFile
                import os
                with NamedTemporaryFile(dir=target.parent, delete=False) as stream:
                    name = stream.name; stream.write((json.dumps(doc,indent=2,allow_nan=False)+'\n').encode())
                try: os.replace(name, target)
                finally:
                    if Path(name).exists(): Path(name).unlink()
            else:
                with target.open('x', encoding='utf-8') as stream: stream.write(json.dumps(doc,indent=2,allow_nan=False)+'\n')
            self.status.setText('Saved explicit parameter document: '+str(target)+'. Export does not validate edited values for execution.')
        except Exception as exc: self.status.setText('Save blocked: '+str(exc))
