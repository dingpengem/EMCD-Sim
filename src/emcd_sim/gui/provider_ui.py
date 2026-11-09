"""Declarations for source-backed providers; no material parameters inferred."""
from dataclasses import asdict,replace
from pathlib import Path
import json
from PySide6 import QtCore,QtWidgets
from .generalized_forward import ProviderSettings,settings_for_provider,source_for
from .emcd_forward import DEFAULT_SOURCE
from ..imported_mdff import CONVENTION


class ProviderUI:
    def material_direction(self):
        if hasattr(self,'row'):return self.row[3]
        viewer=getattr(self,'structure_viewer',None)
        return viewer.draft_global_direction() if viewer is not None and viewer.editor.magnetization_mode=='global' else self.material_magnetization

    def bind_material_reference(self,cfg):
        """Reuse the existing physical-pair validator for the Material target."""
        from .group_mdff import bind_group_direction
        if hasattr(self,'row'):row=self.row[:4]+(cfg,)
        else:
            indices=tuple(i for i,atom in enumerate(self.structure.atoms) if atom.symbol==cfg.ionizing_element)
            if not indices:raise ValueError('MDFF source element is absent from the Material structure')
            row=('Global Material M',cfg.ionizing_element,indices,self.material_direction(),cfg)
        return bind_group_direction(row)

    def xmcd_declaration_controls(self):
        self.explicit_xmcd=QtWidgets.QCheckBox('Use explicit material declarations',self)
        self.explicit_xmcd.setChecked(True)
        self.explicit_xmcd.hide()  # Retained for saved historical settings.
        self.reference_ni=QtWidgets.QCheckBox('Historical reference Ni adapter (a=3.524 Å; v0.8 behavior)')
        self.form.addRow(self.reference_ni)
        self.reference_ni.toggled.connect(lambda checked:self.explicit_xmcd.setChecked(not checked))
        self.explicit_xmcd.toggled.connect(self.sync_xmcd_route)
        self.xmcd_element=QtWidgets.QLineEdit('Ni');self.form.addRow('Declared source element',self.xmcd_element)
        self.xmcd_edge=QtWidgets.QLineEdit('L2,3');self.form.addRow('Declared core-loss edge',self.xmcd_edge)
        self.xmcd_l23_controls=tuple(widget for key in ('xl3','xl2') for widget in (self.spin[key],self.form.labelForField(self.spin[key])))
        self.xmcd_selected=QtWidgets.QLineEdit();self.xmcd_selected.setPlaceholderText('Optional JSON, e.g. {"K": 530}; L2,3 uses fields above')
        self.form.addRow('Explicit native selections',self.xmcd_selected)
        self.xmcd_selected.setEnabled(False)  # L2,3 uses the visible energy controls.
        self.xmcd_provenance=QtWidgets.QLineEdit();self.form.addRow('Source / provenance',self.xmcd_provenance)
        self.xmcd_validity=QtWidgets.QLineEdit();self.form.addRow('Physical assumptions / limits',self.xmcd_validity)
        self.xmcd_scale=QtWidgets.QLineEdit('1');self.form.addRow('Relative tensor reference (A^2/eV)',self.xmcd_scale)
        self.xmcd_scale.setToolTip('Default 1: one relative reference unit after source-max normalization. This is not an absolute cross-section calibration.')
        note=QtWidgets.QLabel('Element/edge are editing-context declarations, not five-column file metadata. Native peak selections are suggestions: confirm their L3/L2 assignment. Relative reference defaults to 1; no absolute calibration is implied.')
        note.setWordWrap(True);self.form.addRow(note)
        self.xmcd_status=QtWidgets.QComboBox();self.xmcd_status.addItems(['physical_source_unvalidated','synthetic']);self.form.addRow('Scientific status',self.xmcd_status)
        for widget in (self.xmcd_element,self.xmcd_edge,self.xmcd_provenance,self.xmcd_validity,self.xmcd_scale):
            widget.textChanged.connect(self.xmcd_declaration_changed)
        self.xmcd_selected.textChanged.connect(self.xmcd_selections_changed)
        for key,edge in (('xl3','L3'),('xl2','L2')):
            self.spin[key].valueChanged.connect(lambda value,edge=edge:self.xmcd_energy_selected(edge,value))
        self.explicit_xmcd.toggled.connect(self.xmcd_declaration_changed)
        self.xmcd_status.currentIndexChanged.connect(self.xmcd_declaration_changed)

    def xmcd_declaration_changed(self,*_):
        for widget in self.xmcd_l23_controls:widget.setVisible(self.xmcd_edge.text().strip()=='L2,3')
        self.xmcd_selected.setEnabled(self.xmcd_edge.text().strip()!='L2,3' or not (self.source_info or {}).get('selected'))
        if self.sender() in (self.xmcd_element,self.xmcd_edge):self.declaration.setChecked(False)
        self.emcd_stale()

    def sync_xmcd_route(self,*_):
        with QtCore.QSignalBlocker(self.reference_ni):self.reference_ni.setChecked(not self.explicit_xmcd.isChecked())
        for widget in (self.xmcd_element,self.xmcd_edge,self.xmcd_selected,self.xmcd_provenance,self.xmcd_validity,self.xmcd_scale,self.xmcd_status):
            widget.setEnabled(self.explicit_xmcd.isChecked())

    def xmcd_descriptions(self):
        path=Path(self.source_path.text())
        return (f'{path.name}; five-column XAS/XMCD input; identity checked, material calibration not established',
                'Effective axisymmetric XMCD model; uniform selected magnetic state; shared XAS and reversal-odd XMCD; no full ab-initio MDFF or absolute material calibration')

    def xmcd_energy_selected(self,edge,value):
        if self.source_info is not None and self.validated_path==self.source_path.text():
            self.source_info.setdefault('explicit_selected',{})[edge]=value
            self.emcd_stale()

    def xmcd_selections_changed(self):
        if self.xmcd_edge.text().strip()=='L2,3' and self.source_info is not None and self.validated_path==self.source_path.text():
            self.source_info['explicit_selected']={}
            try:
                from ..mdff_edges import validate_selected
                selected=dict(validate_selected(self.xmcd_element.text().strip(),'L2,3',json.loads(self.xmcd_selected.text()),self.source_info['bounds']))
                self.set_values(dict(xl3=selected['L3'],xl2=selected['L2']))
                self.source_info['explicit_selected']=selected
            except (ValueError,TypeError):pass  # Invalid drafts cannot authorize inherited controls.
        self.xmcd_declaration_changed()

    def atomic_parameter_controls(self):
        self.atomic_provider_info=None
        from .atomic_editor import AtomicParameterEditor
        from .runtime import workspace
        self.atomic_editor=AtomicParameterEditor(lambda:getattr(self,'workspace',None) or workspace(),self)
        self.form.addRow(self.atomic_editor)
        self.atomic_editor.invalidated.connect(self.atomic_parameters_changed)
        self.atomic_editor.sourceReady.connect(self.atomic_editor_source_ready)
        from .responsive import CollapsibleSection
        exchange=CollapsibleSection('Optional parameter-file exchange',expanded=False)
        self.atomic_editor.advanced_parameters.body.layout().addWidget(exchange)
        normal_form=self.form;self.form=QtWidgets.QFormLayout(exchange.body)
        self.atomic_parameter_path=QtWidgets.QLineEdit();self.form.addRow('Parameter source',self.atomic_parameter_path)
        button=QtWidgets.QPushButton('Browse atomic parameters…');button.clicked.connect(self.browse_atomic_parameters);self.form.addRow(button)
        button=QtWidgets.QPushButton('Validate atomic parameters');button.clicked.connect(self.validate_atomic_parameters);self.form.addRow(button)
        self.atomic_declaration=QtWidgets.QCheckBox('I acknowledge approximate 2p-to-3d cubic model, source, frame and relative units')
        self.form.addRow(self.atomic_declaration)
        self.atomic_provider_status=QtWidgets.QLabel('Edit parameters and preview; sources are authenticated automatically.')
        self.atomic_provider_status.setWordWrap(True);self.form.addRow(self.atomic_provider_status)
        self.atomic_parameter_path.textChanged.connect(self.atomic_parameters_changed)
        self.atomic_declaration.toggled.connect(self.emcd_stale)
        self.form=normal_form

    def atomic_parameters_changed(self,*_):
        if _ and isinstance(_[0],str):self.atomic_editor.external_source_pending=bool(_[0].strip())
        self.atomic_editor.validated_path=None;self.atomic_editor.validated_sha256=None
        self.atomic_editor.invalidate_preview('Atomic source or parameter identity changed')
        self.atomic_editor.status.setText('UNVALIDATED input/source change; generate or validate the current parameters again. No stale tensor may execute.')
        self.atomic_provider_info=None;self.atomic_declaration.setChecked(False)
        self.atomic_provider_status.setText('Atomic input changed; validate its checksum and parameters again.')
        self.emcd_stale()

    def browse_atomic_parameters(self):
        path,_=QtWidgets.QFileDialog.getOpenFileName(self,'Explicit approximate atomic parameters','','JSON (*.json)')
        if path:self.atomic_parameter_path.setText(path);self.validate_atomic_parameters()

    def atomic_editor_source_ready(self,path):
        with QtCore.QSignalBlocker(self.atomic_parameter_path):self.atomic_parameter_path.setText(path)
        self.atomic_editor.external_source_pending=False
        self.validate_atomic_parameters()

    def sync_atomic_editor_structure(self):
        if hasattr(self,'atomic_editor') and not getattr(self,'_restoring',False):
            self.atomic_editor.set_crystal(self.structure)

    def validate_atomic_parameters(self,*_,expected_sha256=None):
        self.atomic_provider_info=None;self.atomic_declaration.setChecked(False)
        try:
            path=self.atomic_parameter_path.text().strip()
            if not path:raise ValueError('Select or create explicit atomic parameters; the source path is empty')
            from .atomic_editor_model import read_document
            _,digest=read_document(path)  # Check bounds and retain the parsed identity.
            cfg=settings_for_provider(path,'atomic')
            if cfg.source_sha256!=digest:raise ValueError('Atomic source changed during validation; validate again')
            if expected_sha256 and cfg.source_sha256!=expected_sha256:raise ValueError('Atomic parameter checksum changed; acknowledgement invalidated')
            if (self.atomic_editor.validated_path,self.atomic_editor.validated_sha256)!=(str(Path(path).resolve()),digest):
                self.atomic_editor.load_document(path,validated=True)
            if self.atomic_editor.validated_sha256!=digest:raise ValueError('Atomic source changed while loading the editor; validate again')
            self.atomic_provider_info=cfg
            self.atomic_provider_status.setText(cfg.ionizing_element+'; APPROXIMATE / physically unvalidated\nSHA256 '+cfg.source_sha256)
        except Exception as exc:
            self.atomic_editor.external_source_pending=True
            self.atomic_editor.validated_path=self.atomic_editor.validated_sha256=None
            self.atomic_editor.invalidate_preview('Atomic source validation failed or its identity changed')
            self.atomic_editor.preview_state.setText('STALE numerical spectrum - Atomic source validation failed.')
            self.atomic_provider_status.setText('Atomic generation failed: '+str(exc))
        self.emcd_stale()

    def declared_provider_settings(self,base,prepare=True):
        symbols=set(self.structure.atoms.get_chemical_symbols())
        if base.model=='atomic':
            if self.atomic_editor.active and self.atomic_editor.external_source_pending:
                raise ValueError('Validate the selected external Atomic source before preview or calculation')
            if self.atomic_editor.active and not self.atomic_editor.validated_path:
                if not prepare:
                    self.atomic_editor.document()
                    raise ValueError('Atomic draft ready for explicit preview or calculation')
                self.atomic_editor.generate()
            path=self.atomic_parameter_path.text().strip()
            if not path:
                if self.atomic_editor.active:raise ValueError('Generalized atomic editor has unvalidated edits; generate the current source first')
                if symbols!={'Ni'}:raise ValueError('Atomic Ionization requires explicit element-specific parameters; Ni defaults are not transferred')
                return base
            cfg=self.atomic_provider_info
            if cfg is None or cfg.source!=str(Path(path).resolve()):raise ValueError('Validate the current atomic parameter source first')
            acknowledged=self.atomic_declaration.isChecked() or (self.atomic_editor.active and not self.atomic_editor.external_source_pending)
        elif base.model=='xmcd':
            if not self.explicit_xmcd.isChecked() and symbols=={'Ni'}:return base
            if Path(base.source).resolve()==DEFAULT_SOURCE.resolve() and symbols!={'Ni'}:
                raise ValueError('Bundled Ni XMCD cannot be used for another element; select its declared source')
            if self.xmcd_edge.text().strip()=='L2,3':
                selected=dict(L3=base.l3,L2=base.l2)
                info=self.source_info or {}
                if not info.get('selected') and info.get('explicit_selected')!=selected:
                    raise ValueError('Explicit native edge selections required: select both L3/L2 energies or enter their JSON')
            else:
                if not self.xmcd_selected.text().strip():
                    raise ValueError('Explicit native edge selections JSON required for this edge')
                selected=json.loads(self.xmcd_selected.text())
            raw=self.xmcd_scale.text().strip()
            try:scale=float(raw)
            except ValueError:raise ValueError('Relative tensor reference (A^2/eV): enter a positive finite number; the relative-model default is 1 (not absolute calibration)') from None
            import math
            if not math.isfinite(scale) or scale<=0:raise ValueError('Relative tensor reference (A^2/eV): enter a positive finite number')
            provenance,limits=self.xmcd_descriptions()
            declaration=dict(element=self.xmcd_element.text().strip(),edge=self.xmcd_edge.text().strip(),selected_ev=selected,
                magnetization_crystal=list(base.magnetization),handedness='RP_minus_LP_in_declared_axis',eta=base.eta,beta=base.beta,
                normalization='source_max_nonmagnetic',convention=CONVENTION,source=self.xmcd_provenance.text().strip() or provenance,
                validity=self.xmcd_validity.text().strip() or limits,status=self.xmcd_status.currentText(),source_sha256=base.source_sha256,
                reference_tensor_scale_angstrom2_per_ev=scale,
                magnetic_state='uniform_fm',reversal_assumption='axisymmetric_XMCD_odd_shared_XAS')
            cfg=settings_for_provider(base.source,'xmcd',declaration)
            acknowledged=base.axis_declared
        else:return base
        fields=asdict(base);fields['atomic']=base.atomic
        for key in ('model','source','source_sha256','l3','l2','magnetization','axis_declared'):fields.pop(key,None)
        cfg=replace(cfg,**fields,magnetization=base.magnetization,axis_declared=acknowledged)
        return self.bind_material_reference(cfg)

    def restore_provider_settings(self,cfg,path=None):
        if cfg.model=='atomic':
            self.atomic_editor.set_crystal(self.structure,preserve_validation=True)
            with QtCore.QSignalBlocker(self.atomic_parameter_path):self.atomic_parameter_path.setText(path or cfg.source)
            self.validate_atomic_parameters(expected_sha256=cfg.source_sha256)
            with QtCore.QSignalBlocker(self.atomic_declaration):self.atomic_declaration.setChecked(bool(self.atomic_provider_info and cfg.axis_declared))
        elif cfg.model=='xmcd':
            d=cfg.provider_declaration
            values=((self.xmcd_element,d['element']),(self.xmcd_edge,d['edge']),
                (self.xmcd_selected,'' if d['edge']=='L2,3' else json.dumps(d['selected_ev'])),(self.xmcd_provenance,d['source']),
                (self.xmcd_validity,d['validity']),(self.xmcd_scale,str(d['reference_tensor_scale_angstrom2_per_ev'])))
            for widget,value in values:
                with QtCore.QSignalBlocker(widget):widget.setText(value)
            with QtCore.QSignalBlocker(self.xmcd_status):self.xmcd_status.setCurrentText(d['status'])
            with QtCore.QSignalBlocker(self.explicit_xmcd):self.explicit_xmcd.setChecked(True)
            self.sync_xmcd_route()
            if d['edge']=='L2,3':
                for key,edge in (('xl3','L3'),('xl2','L2')):
                    with QtCore.QSignalBlocker(self.spin[key]):self.spin[key].setValue(d['selected_ev'][edge])
                if self.source_info and self.source_info['sha256']==cfg.source_sha256 and self.validated_path==self.source_path.text():
                    self.source_info['explicit_selected']=dict(d['selected_ev'])
            for widget in self.xmcd_l23_controls:widget.setVisible(cfg.core_edge=='L2,3')
            self.xmcd_selected.setEnabled(cfg.core_edge!='L2,3')

    def invalidate_provider_acknowledgement(self):
        index=self.model_box.currentIndex()
        checkbox=(self.declaration,self.atomic_declaration,self.imported_declaration)[index]
        with QtCore.QSignalBlocker(checkbox):checkbox.setChecked(False)
        if index==0:self.source_info=None;self.validated_path=None
        elif index==1:self.atomic_provider_info=None
        else:self.imported_info=None

    def invalidate_on_source_error(self,exc):
        message=str(exc).lower()
        changed=isinstance(exc,(FileNotFoundError,PermissionError)) or any(word in message for word in
            ('checksum changed','checksum mismatch','missing/unreadable','no such file'))
        if changed:self.invalidate_provider_acknowledgement()
        return changed
