"""Active-project actions; existing browser, editors and project IO remain owners."""
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path
from datetime import datetime, timezone
import json
import numpy as np
from PySide6 import QtCore, QtWidgets

from . import project_io as io
from .project_collection import save_collection, load_collection


def capture_configuration(w):
    viewer=getattr(w,'structure_viewer',None)
    global_editor=getattr(w,'mdff_dialog',None)
    if w.magnetization_mode=='global' and global_editor is not None and global_editor.has_unapplied_edits():
        raise ValueError('Apply or Cancel the Global MDFF draft before saving')
    if viewer is not None and viewer.pending_global_direction:
        raise ValueError('Apply or Cancel pending Global Material M edits before saving; accepted settings are unchanged')
    if (w.magnetization_mode=='local' and viewer is not None
            and viewer.editor.accepted_site_groups is not None
            and (viewer.editor.rows()!=viewer.editor._accepted_rows
                 or viewer.editor.reverse_magnetization!=viewer.editor._accepted_reversal
                 or viewer.editor.excluded_groups!=viewer.editor._accepted_excluded
                 or viewer.editor.magnetization_mode!=viewer.editor._accepted_mode)):
        raise ValueError('Apply or Cancel pending Site Group direction/provider edits before saving or recalculating; accepted settings are unchanged')
    from .emcd_forward import ForwardSettings
    from .forward_pipeline import MultiSiteForwardSettings
    common=dict(propagation=('bloch','fft-multislice','both')[w.propagation_box.currentIndex()],
        channeling_model=('single','double')[w.channeling_box.currentIndex()],energy_scope=('full','edges')[w.energy_scope.currentIndex()],
        centers=tuple(tuple(p) for p in w.detectors),angular_maps=w.angular_maps.isChecked(),systematic_row=w.row_projection.isChecked(),
        correction=w.correction.isChecked(),memory_budget_mib=w.memory_budget.currentData(),
        worker_mode=('automatic','manual')[w.worker_mode.currentIndex()],parallel_workers=w.worker_count.value(),fft_generators=w.saved_fft_generators())
    for key in ('grid','depth','subpixels','halfwidth','radius','fft_grid','slice_step'):common[key]=w.spin[key].value()
    if w.magnetization_mode=='local':cfg=MultiSiteForwardSettings(**common)
    else:
        try:cfg=w.forward_settings(prepare=False)
        except ValueError:
            saved=getattr(w,'_loaded_configuration_config',None)
            mode=('xmcd','atomic','imported')[w.model_box.currentIndex()]
            if getattr(saved,'model',None)!=mode and getattr(getattr(w,'_saved_global_config',None),'model',None)==mode:saved=w._saved_global_config
            path=w.imported_path.text() if mode=='imported' else w.atomic_parameter_path.text() if mode=='atomic' else w.source_path.text()
            cfg=ForwardSettings(**common,model=('xmcd','atomic','imported')[w.model_box.currentIndex()],
                source=w.source_path.text(),source_sha256=(w.source_info or {}).get('sha256',''),axis_declared=False,
                magnetization=w.material_magnetization,eta=w.spin['eta'].value(),beta=w.spin['beta'].value(),
                l3=w.spin['xl3'].value(),l2=w.spin['xl2'].value())
            from .generalized_forward import ImportedSettings,ProviderSettings
            effective=getattr(w,'_configuration_sources',{}).get('config')
            if isinstance(saved,ImportedSettings) and saved.model==mode and path in (saved.source,effective):
                cfg=replace(saved,**common,magnetization=cfg.magnetization,axis_declared=False)
            elif cfg.model=='atomic' and (w.atomic_editor.active or w.atomic_parameter_path.text().strip()):
                cfg=ProviderSettings(**dict(asdict(cfg),atomic=cfg.atomic,source=path,source_sha256='',
                    ionizing_element=w.atomic_editor.element.currentData(),magnetic_state=''))
            elif cfg.model=='imported':
                cfg=ImportedSettings(**dict(asdict(cfg),atomic=cfg.atomic,source=w.imported_path.text(),
                    ionizing_element=w.ionizing_element.text(),core_edge=w.imported_edge.text(),magnetic_state=w.imported_state.currentText()))
    state=dict(structure=w.structure,settings=w.settings(),config=cfg,magnetization_mode=w.magnetization_mode,
        source_overrides=dict(getattr(w,'_configuration_sources',{})),metadata=deepcopy(getattr(w,'_configuration_metadata',{})))
    viewer=getattr(w,'structure_viewer',None)
    if viewer is not None:
        editor=viewer.editor;rows=editor.rows()
        state['group_records']=[dict(group_id=r[0],label=r[0],element=r[1],indices=r[2],magnetization=r[3],
            mdff_reference=r[4],multiplicity=len(r[2]),normalization='mean_per_selected_atom',enabled=r[0] not in editor.excluded_groups) for r in rows]
        state['reverse_magnetization']=editor.reverse_magnetization
        omitted=getattr(editor,'omitted_site_groups',set())
        state['energy_windows']={k:v for k,v in editor.energy_windows.items() if k not in omitted} or None
        state['energy_ev']=getattr(editor,'requested_energy_ev',None)
        if omitted and state['energy_windows'] is None:state['energy_windows']={}
        state['editor_drafts']={name:d.snapshot() for name,d in editor.mdff_dialogs.items()}
        state['metadata']['group_applied_snapshots']={name:d._applied_snapshot for name,d in editor.mdff_dialogs.items() if d.has_unapplied_edits()}
        state['metadata']['viewer_display']=dict(colors=viewer.color_mode.currentIndex(),arrows=viewer.magnetic_arrows.isChecked())
        state['metadata']['crystallographic_sites']=deepcopy(editor.crystallographic_provenance)
    raw=w._capture_manual_state();raw['source']=None
    state['metadata']['gui_drafts']=dict(manual=raw,manual_key=w._manual_key,
        spectral=w.manual_spectral.draft(),atomic=w.atomic_editor.draft(),global_axis=w.axis.text())
    state['metadata']['numerical_selection']=w.numerical_selection_snapshot()
    if w.magnetization_mode=='local':state['global_config']=getattr(w,'_saved_global_config',None)
    declared={'config':cfg.source_sha256,'global_config':getattr(state.get('global_config'),'source_sha256','')}
    declared.update({'group:'+r['group_id']:getattr(r['mdff_reference'],'source_sha256','') for r in state.get('group_records',[])})
    pins=getattr(w,'_configuration_source_pins',{})
    state['source_overrides']={key:path for key,path in state['source_overrides'].items() if key not in pins or pins[key]==declared.get(key)}
    return deepcopy(state)


def restore_configuration(w,state):
    """Restore editable inputs, never results, and never infer a tensor frame."""
    from .geometry import orientation
    from .site_group_editor import validate_site_rows
    s=state['settings'];c=state['config'];w._session_restoring=True
    try:
        if state['magnetization_mode']=='local' and state.get('global_config') is None:w._accepted_global_mdff=None
        if state['magnetization_mode']=='local' and state.get('global_config') is not None:
            global_state=dict(state,magnetization_mode='global',config=state['global_config'],global_config=None,group_records=[],site_groups=None,
                metadata={},source_overrides={'config':state.get('source_overrides',{}).get('global_config',state['global_config'].source)})
            restore_configuration(w,global_state);w._session_restoring=True
        w._configuration_sources=dict(state.get('source_overrides',{}))
        w._loaded_configuration_config=c;w._configuration_metadata=deepcopy(state.get('metadata',{}))
        w._configuration_source_pins={'config':c.source_sha256}
        w._configuration_source_pins.update({'group:'+r['group_id']:getattr(r['mdff_reference'],'source_sha256','') for r in state.get('group_records',[])})
        if state['magnetization_mode']=='global':
            previous=w.emcd_result;busy=w.busy
            try:
                w.busy=False;w.set_magnetization_mode('global')
                snapshot=io.structure_snapshot(state['structure'])
                meta=dict(state.get('metadata',{}),frame=orientation(state['structure'].atoms.cell.array,s.zone,s.target).tolist())
                override=state.get('source_overrides',{}).get('config')
                w.emcd_result=dict(settings=s,config=c,structure_snapshot=snapshot,metadata=meta,
                    source_overrides={} if not override else {'xmcd':override,'mdff':override})
                w._restore_single_settings()
                w._restored_source_block=any(not value['verified'] for key,value in io.source_status(w.emcd_result).items() if key!='cif')
            finally:w.emcd_result=previous;w.busy=busy
        else:
            w.structure=deepcopy(state['structure'])
            for widget,text in ((w.zone,' '.join(map(str,s.zone))),(w.target,' '.join(map(str,s.target)))):
                with QtCore.QSignalBlocker(widget):widget.setText(text)
            for widget,value in ((w.propagation_box,('bloch','fft-multislice','both').index(c.propagation)),
                (w.channeling_box,('single','double').index(c.channeling_model)),(w.energy_scope,('full','edges').index(c.energy_scope)),
                (w.elastic_provider_box,w.elastic_provider_box.findData(s.elastic_provider)),(w.basis_mode,w.basis_mode.findData(s.basis_mode)),
                (w.memory_budget,w.memory_budget.findData(c.memory_budget_mib)),(w.worker_mode,0 if c.worker_mode=='automatic' else 1)):
                if value<0:raise ValueError('Saved numerical/provider setting is unavailable')
                with QtCore.QSignalBlocker(widget):widget.setCurrentIndex(value)
            values=dict(kv=s.voltage,thickness=s.thickness,beam=s.beam_cutoff,potential=s.potential_cutoff,b=s.b_factor,tx=s.tilt[0],ty=s.tilt[1])
            values.update({key:getattr(c,key) for key in ('grid','depth','subpixels','halfwidth','radius','fft_grid','slice_step')})
            w.set_values(values);w.detectors=np.asarray(c.centers);w.sync_detectors();w.sync_za()
            for widget,value in ((w.angular_maps,c.angular_maps),(w.row_projection,c.systematic_row),(w.correction,c.correction)):
                with QtCore.QSignalBlocker(widget):widget.setChecked(value)
            w.worker_count.setValue(c.parallel_workers);w._saved_global_config=state.get('global_config')
        drafts=state.get('metadata',{}).get('gui_drafts')
        if drafts:
            w.set_material_magnetization(tuple(float(v) for v in drafts['global_axis'].replace(',',' ').split()))
            w.atomic_editor.restore_draft(drafts['atomic'])
            source=w.imported_info;raw=deepcopy(drafts['manual']);raw['source']=source
            w._manual_bindings[drafts['manual_key']]=raw;w._activate_manual_state(drafts['manual_key'],remember=False)
            w.manual_spectral.restore_draft(drafts['spectral'])
        w.show_structure_viewer();viewer=w.structure_viewer;editor=viewer.editor
        editor.load_groups(None)
        rows=[]
        for r in state.get('group_records',[]):
            ref=r['mdff_reference'];path=state.get('source_overrides',{}).get('group:'+r['group_id'])
            if ref is not None and path:ref=replace(ref,source=path)
            rows.append((r['group_id'],r['element'],tuple(r['indices']),None if r['magnetization'] is None else tuple(r['magnetization']),ref))
        if not rows and state.get('site_groups') is not None:
            rows=[(g.group_id,g.element,g.indices,g.magnetization,g.mdff_reference) for g in state['site_groups'].groups]
        editor.excluded_groups={r['group_id'] for r in state.get('group_records',[]) if not r.get('enabled',True)}
        editor._accepted_excluded=set(editor.excluded_groups)
        model=editor.check_rows(rows)
        editor.crystallographic_provenance=deepcopy(state.get('metadata',{}).get('crystallographic_sites',{}))
        editor.restore_rows(rows)
        editor.energy_windows=dict(state.get('energy_windows') or {})
        editor.omitted_site_groups=({r[0] for r in rows}-set(editor.energy_windows)) if state.get('energy_windows') is not None else set()
        editor.requested_energy_ev=state.get('energy_ev');editor._restored_energy_scope=c.energy_scope
        editor.reverse_magnetization=editor._accepted_reversal=state.get('reverse_magnetization',False)
        editor.preview_site_groups=editor.accepted_site_groups=model;editor._accepted_rows=tuple(rows)
        editor.mode.setCurrentIndex(1 if state['magnetization_mode']=='local' else 0)
        editor._accepted_mode=state['magnetization_mode'];editor.dirty=False
        for name,snapshot in state.get('editor_drafts',{}).items():
            row=next((r for r in rows if r[0]==name),None)
            if row is None:continue
            from .group_mdff import GroupMDFFDialog
            dialog=GroupMDFFDialog(row,w.workspace,viewer);dialog.restore_snapshot(snapshot)
            dialog.reference=row[4];dialog.window=editor.energy_windows.get(name);dialog._applied_snapshot=dialog.snapshot()
            pending=state.get('metadata',{}).get('group_applied_snapshots',{})
            if name in pending:dialog._applied_snapshot=pending[name]
            dialog.commit=lambda cfg,window,d=dialog:editor.accept_mdff(d,cfg,window)
            dialog.draftChanged.connect(editor.pendingChanged)
            editor.mdff_dialogs[name]=dialog
        editor.recheck_mdff_sources()
        editor._accepted_mdff=(dict(editor.mdff_dialogs),dict(editor.energy_windows),dict(editor._mdff_status),
            {name:d._applied_snapshot if d._applied_snapshot is not None else d.snapshot() for name,d in editor.mdff_dialogs.items()})
        display=state.get('metadata',{}).get('viewer_display',{})
        viewer.color_mode.setCurrentIndex(display.get('colors',0));viewer.magnetic_arrows.setChecked(display.get('arrows',False))
        viewer._site_groups=model;viewer.rebuild();viewer.hide();w.set_magnetization_mode(state['magnetization_mode'])
        w.material_site_groups=model
        w._loaded_fft_recipe=(w.fft_cell_key(),c.fft_generators) if c.fft_generators is not None else None
        w.restore_numerical_selection(state.get('metadata',{}))
        w.refresh();w.sync_magnetization_mode()
        if state['magnetization_mode']=='global':w.mdff_dialog._entry=w.mdff_dialog.snapshot()
    finally:w._session_restoring=False
    w.emcd_stale()


class ProjectSession:
    def setup_project_session(self):
        self.active_project_path=None;self.project_dirty=False;self._session_restoring=False
        self._after_project_save=None;self._saving_project=False;self._configuration_sources={}
        self._configuration_source_pins={};self._configuration_metadata={};self._loaded_configuration_config=None
        self.project_status=QtWidgets.QLabel();self.statusBar().addPermanentWidget(self.project_status)
        self._legacy_record_index={r['path']:dict(r) for r in self.browser.registry.records if r.get('path')}
        self.browser.registry.records=[];self.browser.refresh()
        for root in (self.inputs,self.mdff_dialog):
            for widget in root.findChildren(QtWidgets.QWidget):
                if isinstance(widget,QtWidgets.QLineEdit):widget.textEdited.connect(self.mark_project_dirty)
                elif isinstance(widget,(QtWidgets.QDoubleSpinBox,QtWidgets.QSpinBox)):widget.valueChanged.connect(self.mark_project_dirty)
                elif isinstance(widget,QtWidgets.QComboBox):widget.currentIndexChanged.connect(self.mark_project_dirty)
                elif isinstance(widget,QtWidgets.QCheckBox):widget.toggled.connect(self.mark_project_dirty)
                elif isinstance(widget,QtWidgets.QTableWidget):widget.itemChanged.connect(self.mark_project_dirty)
        self.set_project_status('Unsaved Project')

    def mark_project_dirty(self,*_):
        if not hasattr(self,'project_status') or self._session_restoring or self._restoring:return
        self.project_dirty=True;self.set_project_status('Unsaved Changes' if self.active_project_path else 'Unsaved Project')

    def set_project_status(self,status):
        self.project_save_status=status;name=Path(self.active_project_path).name if self.active_project_path else 'Untitled'
        self.project_status.setText(name+' · '+status)
        self.project_status.setToolTip(str(self.active_project_path or 'Not saved')+'\n'+getattr(self,'last_project_save',''))
        from .runtime import LABEL
        self.setWindowTitle(name+' · '+status+' — '+LABEL)

    def confirm_project_changes(self,continuation):
        if not self.project_dirty:return True
        b=QtWidgets.QMessageBox.StandardButton
        answer=QtWidgets.QMessageBox.warning(self,'Unsaved Changes','Save changes to the current project?',b.Save|b.Discard|b.Cancel,b.Save)
        if answer==b.Discard:return True
        if answer==b.Save:self._after_project_save=continuation;self.save_project_action()
        return False

    def save_project_action(self,save_as=False):
        if self.busy:return
        path=None if save_as else self.active_project_path
        if path is None:
            path,_=QtWidgets.QFileDialog.getSaveFileName(self,'Save Project As — choose a project folder name',str(self.workspace/'Untitled'))
            if not path:self._after_project_save=None;return
        existing=Path(path).exists()
        if save_as and self.active_project_path and Path(path).resolve()==Path(self.active_project_path).resolve():
            self._after_project_save=None;self.error('Choose a different project location for Save As.');return
        if existing and str(Path(path).resolve())!=str(self.active_project_path):
            if QtWidgets.QMessageBox.question(self,'Replace Project?','Replace only this existing EMCD project after a successful safe save?')!=QtWidgets.QMessageBox.StandardButton.Yes:
                self._after_project_save=None;return
        self.save_to_path(path,existing)

    def save_to_path(self,path,replace_existing=False):
        if self.busy:return
        try:
            state=capture_configuration(self)
            runs=[(dict(r,pending=False),self.browser.cache[r['id']]) for r in self.browser.registry.records]
            # Retained legacy results keep the display preferences that the
            # original single-result Save workflow captured, without touching
            # any calculated arrays or the settings of other history entries.
            current=self.emcd_result
            retained=self.browser.cache.get(self.selected_record['id']) if self.selected_record else None
            if (retained is not None and current is not None and retained['spectra'] is current['spectra']
                    and current['config'].model!='multisite'):
                view=self.eels_view;prb=view.prb_benchmark
                retained['display_state']=dict(current.get('display_state',{}),signal_display_schema=2,
                    component_mode=view.component_mode.currentData(),map_signal_mode=self.maps_view.component_mode.currentData(),
                    method=view.method.currentData(),zoom=view.choice.currentText(),selection=prb.selection.currentData(),
                    energy_ev=prb.energy.value(),locked=prb.fixed.isChecked(),advanced=view.advanced.isChecked(),
                    component_diagnostic=view.component_diagnostic.currentData())
        except Exception as exc:self.set_project_status('Save Failed');self._after_project_save=None;self.error(str(exc));return
        self.set_project_status('Saving…');self._saving_project=True
        def saved(root):
            self.active_project_path=str(root);self.project_dirty=False
            self.last_project_save=QtCore.QDateTime.currentDateTimeUtc().toTimeZone(QtCore.QTimeZone(b'America/Los_Angeles')).toString('yyyy-MM-dd HH:mm:ss')+' America/Los_Angeles'
            manifest=json.loads((root/'project.json').read_text(encoding='utf-8'))
            for key,entry in manifest.get('configuration_sources',{}).items():
                self._configuration_source_pins[key]=entry['sha256']
                self._configuration_sources[key]=str(root/entry['attachment']) if entry.get('attachment') else entry['resolved_path']
            editor=getattr(getattr(self,'structure_viewer',None),'editor',None)
            if editor is not None:
                editor.portable_references={key[6:]:(self._configuration_source_pins[key],path)
                    for key,path in self._configuration_sources.items() if key.startswith('group:') and key in self._configuration_source_pins}
            for r in self.browser.registry.records:
                folder=root/'calculations'/r['id'];r['path']=str(folder);r['pending']=False
                result=self.browser.cache[r['id']];result['project_path']=str(folder)
                child=json.loads((folder/'project.json').read_text(encoding='utf-8'))
                overrides=result.setdefault('source_overrides',{})
                for gid,entry in child.get('multisite_sources',{}).items():overrides['group:'+gid]=str(folder/entry['path'])
                for field,key in (('manual_tensor_source','mdff'),('atomic_parameter_source','mdff')):
                    if field in child:overrides[key]=str(folder/child[field]['path'])
                if result.get('configuration'):result['configuration']['source_overrides']=overrides
            self.browser.refresh();self.set_project_status('Saved')
        self.io_operation(lambda cancel,progress:save_collection(state,runs,path,replace_existing=replace_existing,cancelled=cancel,progress=progress),saved)

    def open_project_path(self,path,*,legacy=False,record=None,relocated=False):
        if record is not None or legacy:return self._open_single_result_path(path,legacy=legacy,record=record,relocated=relocated)
        if self.busy:return
        if not self.confirm_project_changes(lambda:self.open_project_path(path)):return
        def loaded(payload):
            restore_configuration(self,payload['state'])
            self.browser.selection_timer.stop();self.browser.cache={};self.browser.registry.records=[]
            for record,result in payload['runs']:
                if record is None:
                    record=self.browser.registry.register(result,str(payload['path']))
                    known=self._legacy_record_index.get(str(payload['path']))
                    if known:record.update(id=known['id'],name=known['name'],custom_name=known.get('custom_name',False))
                    self._legacy_record_index[str(payload['path'])]=dict(record)
                else:record=dict(record,path=str(payload['path']/record['path']));self.browser.registry.records.append(record)
                self.browser.cache[record['id']]=result
            self.browser.refresh();self.active_project_path=str(payload['path']);self.project_dirty=False
            if payload['runs']:
                r=self.browser.registry.records[-1];self.browser.select_id(r['id']);self.display_saved_result(self.browser.cache[r['id']],r)
            else:self.clear_selected()
            self.project_dirty=False;self.set_project_status('Saved')
        self.io_operation(lambda cancel,progress:load_collection(path,cancelled=cancel,progress=progress),loaded)

    def new_project(self):
        if self.busy or not self.confirm_project_changes(self.new_project):return
        self._session_restoring=True
        try:
            self._reset_project_inputs();self.set_magnetization_mode('global')
            if getattr(self,'structure_viewer',None):self.structure_viewer.editor.load_groups(None)
            self.browser.registry.records=[];self.browser.cache={};self.browser.refresh()
            self.active_project_path=None;self.project_dirty=False;self._configuration_sources={}
            self._restored_source_block=False;self._saved_global_config=None
            self._loaded_configuration_config=None;self._configuration_metadata={};self._configuration_source_pins={}
            self.set_project_status('Unsaved Project')
        finally:self._session_restoring=False

    def close_project(self):self.new_project()

    def delete_selected_calculation(self):
        rows=self.browser.selected()
        if self.busy or len(rows)!=1:return
        row=rows[0]
        if QtWidgets.QMessageBox.question(self,'Delete Selected Calculation?',row['name']+'\nRun '+row['id']+'\nRemove this calculation only? Disk changes take effect on Save.')!=QtWidgets.QMessageBox.StandardButton.Yes:return
        self.browser.registry.records=[r for r in self.browser.registry.records if r['id']!=row['id']]
        self.close_run_comparisons(row['id'])
        self.browser.cache.pop(row['id'],None);self.browser.refresh()
        if self.selected_record and self.selected_record['id']==row['id']:self.clear_selected()
        self.mark_project_dirty()

    def use_result_settings(self):
        rows=self.browser.selected()
        if len(rows)>1:self.error('Select exactly one calculation to restore its settings.');return
        r=self.browser.cache.get(rows[0]['id']) if rows else self.emcd_result
        if self.busy or r is None:return
        if not self.confirm_project_changes(self.use_result_settings):return
        if r['config'].model=='multisite':
            if not r.get('configuration'):self.error('This older run lacks full provider declarations; no settings were substituted.');return
            state=deepcopy(r['configuration']);state['source_overrides']=r.get('source_overrides',{})
            if 'numerical_selection' in r['metadata']:state.setdefault('metadata',{})['numerical_selection']=r['metadata']['numerical_selection']
            restore_configuration(self,state)
        else:
            self.set_magnetization_mode('global');self._restore_single_settings()
        self.mark_project_dirty()

    def register_completed(self,result):
        rows=self.browser.selected();replace_row=None
        if len(rows)==1:
            dialog=QtWidgets.QMessageBox(self);dialog.setWindowTitle('Retain Calculation')
            dialog.setText('Keep this completed calculation as a new record, or replace '+rows[0]['name']+' ['+rows[0]['id'][:8]+']?')
            new=dialog.addButton('Keep as New Calculation',QtWidgets.QMessageBox.ButtonRole.AcceptRole)
            replace_button=dialog.addButton('Replace Selected Calculation',QtWidgets.QMessageBox.ButtonRole.DestructiveRole)
            dialog.setDefaultButton(new);dialog.exec()
            if dialog.clickedButton() is replace_button:replace_row=rows[0]
        result['metadata'].setdefault('calculation_utc',datetime.now(timezone.utc).isoformat())
        if replace_row:
            self.close_run_comparisons(replace_row['id'])
            s=result['settings'];c=result['config']
            from .multisite_results import material
            element=material(result) if c.model=='multisite' else getattr(c,'ionizing_element','Ni')
            replace_row.update(thickness=s.thickness,zone=list(s.zone),target=list(s.target),tx=s.tilt[0],ty=s.tilt[1],
                material=element,model=c.model,channeling_model=c.channeling_model,propagation=c.propagation,
                created_utc=result['metadata']['calculation_utc'],legacy=False,pending=True)
            if not replace_row.get('custom_name'):replace_row['name']=f'{element} [{" ".join(map(str,s.zone))}] | {s.thickness:g} nm | {c.model} | {c.propagation}'
            self.browser.cache[replace_row['id']]=result;self.selected_record=replace_row;self.browser.refresh()
        else:self.selected_record=self.browser.register(result)
        self.project_dirty=True;self.set_project_status('Unsaved Changes' if self.active_project_path else 'Unsaved Project')

    def close_run_comparisons(self,identity):
        from .calculation_comparison import CalculationComparison
        for dialog in list(self.dialogs):
            if isinstance(dialog,CalculationComparison) and any(record['id']==identity for record,_ in dialog.runs):
                dialog.close();dialog.deleteLater();self.dialogs.remove(dialog)

    def restored_source_reason(self):
        if not getattr(self,'_restored_source_block',False) or self.magnetization_mode=='local':return ''
        i=self.model_box.currentIndex()
        valid=((bool(self.source_info) and self.declaration.isChecked()) if i==0 else
               (bool(self.atomic_provider_info) and self.atomic_declaration.isChecked()) if i==1 else
               (bool(self.imported_info) and self.imported_declaration.isChecked()))
        if valid:self._restored_source_block=False;return ''
        return 'Saved external MDFF source is unavailable or changed. Explicitly validate and apply a source before recalculating.'

    def compare_selected(self):
        from .calculation_comparison import CalculationComparison
        if len(self.browser.registry.records)<2:self.error('Retain at least two calculations in this project.');return
        dialog=CalculationComparison(self);self.dialogs.append(dialog);dialog.show()
