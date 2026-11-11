"""Lightweight persistent project-path index and Stage D Qt workspace actions."""
from dataclasses import replace,asdict
from pathlib import Path
from datetime import datetime,timezone
import json,os,uuid,logging
import numpy as np
from PySide6 import QtCore,QtWidgets,QtGui
from .project_io import load_project,save_project,source_status,sha256,restore_structure,rerun_reason
from .emcd_forward import Cancelled,inspect_source
from .results import comparison_text
from .project_session import ProjectSession


def default_workspace():
    from .runtime import workspace
    return workspace()


class Registry:
    def __init__(self,path):
        self.path=Path(path);self.records=[]
        if self.path.exists():
            data=json.loads(self.path.read_text(encoding='utf-8'))
            if data.get('version')!=1:raise ValueError('Unsupported Results Browser index version')
            self.records=data['records']
    def persist(self):
        self.path.parent.mkdir(parents=True,exist_ok=True);temp=self.path.with_name(self.path.name+'.tmp')
        temp.write_text(json.dumps(dict(version=1,records=[r for r in self.records if r.get('path')]),indent=2)+'\n',encoding='utf-8');temp.replace(self.path)
    def register(self,result,path=None,name=None):
        resolved=str(Path(path).resolve()) if path else None
        existing=next((r for r in self.records if resolved and r.get('path')==resolved),None)
        if existing:
            existing.update(channeling_model=result['config'].channeling_model,propagation=result['config'].propagation)
            self.persist();return existing
        s=result['settings'];cfg=result['config'];stamp=result.get('metadata',{}).get('calculation_utc','')
        from .multisite_results import ionizing_label
        element=ionizing_label(result)
        if cfg.model=='multisite':
            from .multisite_results import material
            element=material(result)
        record=dict(id=uuid.uuid4().hex,path=resolved,name=name or f'{element} [{" ".join(map(str,s.zone))}] | {s.thickness:g} nm | X={s.tilt[0]:+.3f}, Y={s.tilt[1]:+.3f} | {cfg.model} | {cfg.propagation}',
            created_utc=stamp,material=element,zone=list(s.zone),target=list(s.target),tx=s.tilt[0],ty=s.tilt[1],thickness=s.thickness,model=cfg.model,channeling_model=cfg.channeling_model,propagation=cfg.propagation,legacy=result.get('read_only_legacy',False))
        self.records.append(record);self.persist();return record
    def remove(self,id):self.records=[r for r in self.records if r['id']!=id];self.persist()
    def rename(self,id,name):
        record=next(r for r in self.records if r['id']==id);record['name']=name;record['custom_name']=True;self.persist()


class IOWorker(QtCore.QThread):
    result=QtCore.Signal(object);failed=QtCore.Signal(str);stage=QtCore.Signal(str)
    def __init__(self,operation):super().__init__();self.operation=operation
    def run(self):
        try:
            value=self.operation(self.isInterruptionRequested,self.stage.emit)
            if not self.isInterruptionRequested():self.result.emit(value)
        except Cancelled:pass
        except Exception as exc:
            logging.getLogger('emcd_sim.gui').exception('Project operation failed')
            self.failed.emit(str(exc))


from .responsive import FlowLayout


class ResultsBrowser(QtWidgets.QWidget):
    def __init__(self,owner,index):
        super().__init__();self.owner=owner;self.registry=index;self.cache={};layout=QtWidgets.QVBoxLayout(self);row=QtWidgets.QHBoxLayout();layout.addLayout(row)
        self.filter=QtWidgets.QLineEdit();self.filter.setPlaceholderText('Filter material, zone, MDFF, method or name');row.addWidget(self.filter)
        self.action_buttons=[];self.more=QtWidgets.QToolButton();self.more.setText('More actions');self.more.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup);menu=QtWidgets.QMenu(self.more);self.more.setMenu(menu)
        for title,callback in [('View Results',self.view),('Restore Settings from Selected Run…',owner.use_result_settings),('Delete Selected Calculation…',owner.delete_selected_calculation)]:
            b=QtWidgets.QPushButton(title);b.clicked.connect(callback);row.addWidget(b);self.action_buttons.append(b)
        row.addWidget(self.more);self.more.hide()
        for title,callback in [('Import Existing Result…',owner.import_result_dialog),('Open Folder',self.open_folder),('Details',self.details),('Rename Run…',self.rename),('Locate Original Source…',owner.locate_source),('Clear Display',owner.clear_selected)]:
            menu.addAction(title,callback)
        self.table=QtWidgets.QTableWidget(0,11);self.table.setHorizontalHeaderLabels(['Run name','Date (Los Angeles)','Material','Zone','Target','Tilt X (mrad)','Tilt Y (mrad)','Thickness (nm)','MDFF','Method','Status'])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows);self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection);self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True);layout.addWidget(self.table);self.filter.textChanged.connect(self.refresh);self.table.cellDoubleClicked.connect(lambda *_:self.view());self.refresh()
        self.table.setMinimumHeight(96)
        self.selection_timer=QtCore.QTimer(self);self.selection_timer.setSingleShot(True);self.selection_timer.setInterval(250)
        self.table.itemSelectionChanged.connect(lambda:self.selection_timer.start());self.selection_timer.timeout.connect(self.auto_view)
    def set_compact(self,compact):
        for button in self.action_buttons:button.setVisible(True)
        self.more.setVisible(True)
        self.table.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,QtWidgets.QSizePolicy.Policy.Ignored if compact else QtWidgets.QSizePolicy.Policy.Expanding)
    def auto_view(self):
        rows=self.selected()
        if not self.owner.busy and len(rows)==1 and (not self.owner.selected_record or rows[0]['id']!=self.owner.selected_record['id']):self.view()
    def selected(self):
        ids=[self.table.item(i,0).data(QtCore.Qt.ItemDataRole.UserRole) for i in sorted({x.row() for x in self.table.selectedIndexes()})]
        return [r for identity in ids for r in self.registry.records if r['id']==identity]
    def refresh(self,*_):
        selected={r['id'] for r in self.selected()} if self.table.rowCount() else set();self.table.setSortingEnabled(False)
        rows=[r for r in self.registry.records if self.filter.text().lower() in json.dumps(r).lower()];self.table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            available=bool(r.get('path') and Path(r['path']).is_dir());status='Unsaved calculation' if r.get('pending') else 'Unsaved session' if not r.get('path') else (('Legacy (read-only)' if r.get('legacy') else 'Available') if available else 'Unavailable - locate folder')
            stamp=QtCore.QDateTime.fromString(r['created_utc'],QtCore.Qt.DateFormat.ISODateWithMs)
            if not stamp.isValid():stamp=QtCore.QDateTime.fromString(r['created_utc'],QtCore.Qt.DateFormat.ISODate)
            date=stamp.toTimeZone(QtCore.QTimeZone(b'America/Los_Angeles')).toString('yyyy-MM-dd HH:mm:ss')
            values=('['+r['id'][:8]+'] '+r['name'],date,r['material'],str(r['zone']),str(r['target']),r['tx'],r['ty'],r['thickness'],r['model'],r.get('channeling_model','single').title()+' Channeling / '+r['propagation'],status)
            for j,value in enumerate(values):
                item=QtWidgets.QTableWidgetItem();item.setData(QtCore.Qt.ItemDataRole.DisplayRole,value)
                if j==0:item.setData(QtCore.Qt.ItemDataRole.UserRole,r['id'])
                self.table.setItem(i,j,item)
            if r['id'] in selected:self.table.selectionModel().select(self.table.model().index(i,0),QtCore.QItemSelectionModel.SelectionFlag.Select|QtCore.QItemSelectionModel.SelectionFlag.Rows)
        self.table.setSortingEnabled(True);self.table.resizeColumnsToContents();self.table.setColumnWidth(0,380)
    def select_id(self,id):
        self.table.clearSelection()
        for i in range(self.table.rowCount()):
            if self.table.item(i,0).data(QtCore.Qt.ItemDataRole.UserRole)==id:self.table.selectRow(i);break
    def register(self,result,path=None,name=None):
        record=self.registry.register(result,path,name)
        self.cache[record['id']]=dict(result,project_path=record.get('path'),source_overrides=dict(record.get('source_overrides',{}),**result.get('source_overrides',{})))
        self.refresh();self.select_id(record['id']);return record
    def view(self):
        rows=self.selected()
        if not rows:return
        r=rows[0]
        if r['id'] in self.cache:self.owner.display_saved_result(self.cache[r['id']],r);return
        if r.get('path'):self.owner.open_project_path(r['path'],legacy=not (Path(r['path'])/'project.json').exists(),record=r)
    def open_folder(self):
        rows=self.selected()
        if rows and rows[0].get('path'):QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(rows[0]['path']))
    def rename(self):
        rows=self.selected()
        if not rows:return
        name,ok=QtWidgets.QInputDialog.getText(self,'Rename display name','Display name (scientific metadata unchanged)',text=rows[0]['name'])
        if ok and name.strip():self.registry.rename(rows[0]['id'],name.strip());self.refresh()
        if ok and name.strip():self.owner.mark_project_dirty()
    def remove(self):
        self.owner.delete_selected_calculation()
    def locate(self):
        rows=self.selected()
        if not rows:return
        path=QtWidgets.QFileDialog.getExistingDirectory(self,'Locate registered project folder')
        if path:self.owner.open_project_path(path,legacy=not (Path(path)/'project.json').exists(),record=rows[0],relocated=True)
    def details(self):
        rows=self.selected()
        if not rows:return
        r=rows[0];result=self.cache.get(r['id']);text=dict(registration=r)
        if result:text.update(metadata=result['metadata'],source_status=source_status(result),warnings=result.get('project_warnings',[]))
        dialog=QtWidgets.QDialog(self);dialog.setWindowTitle('Run details - immutable physical provenance');dialog.resize(850,650);layout=QtWidgets.QVBoxLayout(dialog);edit=QtWidgets.QPlainTextEdit(json.dumps(text,indent=2));edit.setReadOnly(True);layout.addWidget(edit);dialog.show();self.owner.dialogs.append(dialog)


class ProjectWorkspace(ProjectSession):
    project_ready=QtCore.Signal()
    def setup_stage_d(self,workspace=None):
        self.workspace=Path(workspace or default_workspace());self.workspace.mkdir(parents=True,exist_ok=True);self.selected_record=None;self._io_success=False;self._restoring=False;self.input_source_requirements=[]
        self.ui_settings=QtCore.QSettings(str(self.workspace/'ui.ini'),QtCore.QSettings.Format.IniFormat)
        try:index=Registry(self.workspace/'results_index.json')
        except Exception as exc:self.statusBar().showMessage('Results index could not be read: '+str(exc));index=Registry(self.workspace/('recovered_index_'+uuid.uuid4().hex+'.json'))
        self.browser=ResultsBrowser(self,index);self.browser_dock=QtWidgets.QDockWidget('Results Browser',self);self.browser_dock.setObjectName('resultsBrowser');self.browser_dock.setWidget(self.browser);self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea,self.browser_dock);self.resizeDocks([self.browser_dock],[190],QtCore.Qt.Orientation.Vertical)
        from .runtime import LABEL
        self.setWindowTitle(LABEL)
        file=self.menuBar().addMenu('File');results=self.menuBar().addMenu('Results')
        for title,callback,shortcut in [('New Project',self.new_project,'Ctrl+N'),('Open Project…',self.open_project_dialog,'Ctrl+O'),('Save',self.save_project_action,'Ctrl+S'),('Save As…',lambda:self.save_project_action(save_as=True),'Ctrl+Shift+S'),('Close Project',self.close_project,'')]:
            action=file.addAction(title);action.triggered.connect(lambda checked=False,f=callback:f());action.setShortcut(shortcut)
        self.toolbar.addAction('Open Elastic Project…',self.open_elastic_project_dialog);self.toolbar.addAction('Save Elastic Project…',self.save_preview)
        for title,callback in [('Compare Calculations…',self.compare_selected),('Export Results…',self.export_selected_data)]:
            action=results.addAction(title);action.triggered.connect(lambda checked=False,f=callback:f())
        self.browser.more.menu().addAction('Restore Default Layout',self.restore_layout)
        for widget in (self.eels_view,self.maps_view,self.diffraction_view,self.overview_view):
            widget.navigation.addAction('Export Figure…',lambda checked=False,v=widget:self.export_figure_for(v.figure))
        value=self.ui_settings.value('geometry')
        if isinstance(value,QtCore.QByteArray):self.restoreGeometry(value)
        value=self.ui_settings.value('state')
        if isinstance(value,QtCore.QByteArray):self.restoreState(value)
        # ResponsiveLayout validates and restores legacy or current proportions.
    def store_ui_preferences(self):
        if not hasattr(self,'ui_settings'):return
        self.ui_settings.setValue('geometry',self.saveGeometry());self.ui_settings.setValue('state',self.saveState())
        responsive=getattr(self,'responsive',None)
        if responsive is not None:responsive.save_preferences()
        self.ui_settings.setValue('splitter',responsive.saved_splitter_sizes() if responsive is not None else self.splitter.sizes());self.ui_settings.sync()
    def restore_layout(self):
        self.browser_dock.show()
        if hasattr(self,'responsive'):self.responsive.reset()
        else:self.splitter.setSizes([340,820,390]);self.result_sizes=None;self.saved_sizes=None;self.resizeDocks([self.browser_dock],[190],QtCore.Qt.Orientation.Vertical)
    def display_saved_result(self,result,record=None):
        self.emcd_result=result;self.selected_record=record
        if hasattr(self,'sync_result_capabilities'):self.sync_result_capabilities(result)
        for i,view in ((1,self.maps_view),(2,self.eels_view),(5,self.diffraction_view),(6,self.overview_view)):
            self.tabs.setTabEnabled(i,(i!=6 or len(result['methods'])==2) and (i!=1 or bool(result['maps'])));view.set_result(result)
        self.tabs.setTabEnabled(3,True);self.comparison.setPlainText(comparison_text(result));self.tabs.setCurrentIndex(2);self.emcd_stale()
        state=result.get('display_state',{})
        notes=[]
        if state:
            from .component_display import migrate_display_state
            state,notes=migrate_display_state(state)
            view=self.eels_view;prb=view.prb_benchmark
            for widget,value in ((view.component_mode,state.get('component_mode','raw')),(view.method,state.get('method',result['method'])),(prb.selection,state.get('selection','selected'))):
                index=widget.findData(value)
                if index>=0:
                    with QtCore.QSignalBlocker(widget):widget.setCurrentIndex(index)
            note=view.restore_zoom(state.get('zoom'),state.get('zoom_energy_ev'))
            if note:notes.append(note)
            with QtCore.QSignalBlocker(prb.energy):prb.energy.setValue(state.get('energy_ev',float(result['spectra']['energy_ev'][0])))
            with QtCore.QSignalBlocker(prb.fixed):prb.fixed.setChecked(bool(state.get('locked',False)))
            view.component_diagnostic.setCurrentIndex(1 if state.get('component_diagnostic')=='relative' else 0)
            self.maps_view.component_mode.setCurrentIndex(1 if state.get('map_signal_mode')=='asymmetry' else 0)
            if result['config'].model=='multisite':
                view.multisite_controls.restore_options(state.get('multisite_selection',{}))
            self.maps_view.restore_map_options(state.get('angular_selection',{}))
            view.advanced.setChecked(bool(state.get('advanced',False)));view.redraw()
            if notes:view.display_note.setText(' '.join(notes))
        sources=source_status(result);warnings=result.get('project_warnings',[])
        self.statusBar().showMessage('Viewing completed saved data; no recalculation. '+(' '.join(warnings))+' '+('Source unavailable/mismatched for rerun.' if any(not s['verified'] for s in sources.values()) else ''))
    def io_operation(self,operation,completed):
        if self.busy:return
        previous_result=self.emcd_result;previous_record=self.selected_record
        self.busy=True;self.run_outcome='running';self.inputs.setEnabled(False);self.run_button.setEnabled(False);self.emcd_button.setEnabled(False);self.cancel_button.setEnabled(True);self.progress.setRange(0,0);self._io_success=False
        self.browser.setEnabled(False)
        dialogs=[getattr(self,'mdff_dialog',None),getattr(self,'structure_viewer',None)]
        viewer=getattr(self,'structure_viewer',None)
        if viewer is not None:dialogs.extend(viewer.editor.mdff_dialogs.values())
        self._io_edit_dialogs=[(dialog,dialog.isEnabled()) for dialog in dialogs if dialog is not None]
        for dialog,_ in self._io_edit_dialogs:dialog.setEnabled(False)
        self.worker=IOWorker(operation);self.worker.stage.connect(self.statusBar().showMessage)
        def success(value):
            if self.worker.isInterruptionRequested():return
            try:completed(value)
            except Exception as exc:
                self.emcd_result=previous_result;self.selected_record=previous_record;self.run_outcome='failed';self.error('Project workspace update failed: '+str(exc));return
            self._io_success=True;self.run_outcome='completed'
        self.worker.result.connect(success);self.worker.failed.connect(self.preview_failed);self.worker.finished.connect(self.io_finished);self.worker.start()
    def io_finished(self):
        for dialog,enabled in getattr(self,'_io_edit_dialogs',[]):
            try:dialog.setEnabled(enabled)
            except RuntimeError:pass  # A restored editor may replace an old child dialog.
        self._io_edit_dialogs=[]
        cancelled=self.worker.isInterruptionRequested();self.busy=False;self.inputs.setEnabled(True);self.browser.setEnabled(True);self.progress.setRange(0,1);self.progress.setValue(int(self._io_success and not cancelled));self.cancel_button.setEnabled(False);self.refresh();self.project_ready.emit()
        self.statusBar().showMessage('Project operation '+('cancelled; previous selected result preserved.' if cancelled else ('complete; no forward calculation.' if self._io_success else 'failed; previous result/project preserved.')))
        if getattr(self,'_saving_project',False):
            self._saving_project=False
            callback=self._after_project_save;self._after_project_save=None
            if not self._io_success or cancelled:self.set_project_status('Save Failed')
            elif callback:QtCore.QTimer.singleShot(0,callback)
    def _open_single_result_path(self,path,*,legacy=False,record=None,relocated=False):
        def loaded(result):
            # Loader-verified project attachments take precedence over browser
            # locations, which can be empty or stale after project relocation.
            overrides=dict((record or {}).get('source_overrides',{}))
            verified=result.get('source_overrides',{})
            statuses=source_status(result) if verified else {}
            for kind,source_path in verified.items():
                if not statuses.get(kind,{}).get('verified'):
                    raise ValueError('Conflicting verified project source identity: '+kind)
                overrides[kind]=source_path
            if record and relocated:record['path']=str(Path(path).resolve());self.browser.registry.persist()
            row=record or self.browser.register(result,path)
            if not record:
                overrides=dict(row.get('source_overrides',{}),**overrides)
            self.browser.cache[row['id']]=result;result['source_overrides']=overrides;self.browser.refresh();self.browser.select_id(row['id']);self.display_saved_result(result,row)
            if record is None:
                self.project_dirty=True;self.set_project_status('Unsaved Changes' if self.active_project_path else 'Unsaved Project')
        self.io_operation(lambda cancel,progress:load_project(path,legacy=legacy,cancelled=cancel,progress=progress),loaded)
    def open_project_dialog(self):
        path=QtWidgets.QFileDialog.getExistingDirectory(self,'Open complete EMCD project folder')
        if path:self.open_project_path(path)
    def import_result_dialog(self):
        path=QtWidgets.QFileDialog.getExistingDirectory(self,'Import existing Stage B/C result (read only) or project')
        if path:self._open_single_result_path(path,legacy=not (Path(path)/'project.json').exists())
    def _reset_project_inputs(self):
        if self.busy:return
        self._accepted_global_mdff=None;self._saved_global_config=None
        self.explicit_xmcd.setChecked(True);self.sync_xmcd_route()
        self.xmcd_scale.setText('1');self.xmcd_provenance.clear();self.xmcd_validity.clear()
        self.xmcd_status.setCurrentIndex(0);self.source_info=None;self.validated_path=None;self.declaration.setChecked(False)
        with QtCore.QSignalBlocker(self.elastic_provider_box):self.elastic_provider_box.setCurrentIndex(0)
        self.set_values(dict(kv=300,beam=2.5,potential=2.0))
        self.retire_post_edge();self._post_edge_disabled_on_restore=False;self.correction_notice.hide()
        self.worker_mode.setCurrentIndex(0);self.worker_count.setValue(1)
        self._manual_numerics=None;self._numerical_cache=None;self._restore_auto_once=False
        self._slice_step_override=None;self.set_values(dict(slice_step=2.))
        with QtCore.QSignalBlocker(self.numerical_mode):self.numerical_mode.setCurrentIndex(1)
        self.apply_numerical_visibility()
        self.clear_selected();self.input_source_requirements=[];self.default_structure()
        from .memory_budget import DEFAULT_BUDGET_MIB
        self.memory_budget.setCurrentIndex(self.memory_budget.findData(DEFAULT_BUDGET_MIB))
        if hasattr(self,'memory_mode'):
            self.memory_mode.setCurrentIndex(0);self.memory_budget.setEnabled(False)
        self.spin['grid'].setValue(97)
        self.sync_angular_resolution()
        if hasattr(self,'mdff_dialog'):
            self.mdff_dialog.hide();self.mdff_dialog._entry=self.mdff_dialog.snapshot()
            self.mdff_dialog._draft_configuration=None;self.mdff_dialog._ready_snapshot=None
    def clear_selected(self):
        if self.busy:return
        self.selected_record=None;self.emcd_result=None;self.browser.table.clearSelection()
        for i,view in ((1,self.maps_view),(2,self.eels_view),(5,self.diffraction_view),(6,self.overview_view)):
            view.result=None;view.figure.clear();view.canvas.draw_idle();self.tabs.setTabEnabled(i,False)
        self.tabs.setTabEnabled(3,False);self.comparison.clear();self.tabs.setCurrentIndex(0)
    def _restore_single_settings(self):
        if self.busy or self.emcd_result is None:return
        r=self.emcd_result;s=r['settings'];c=r['config']
        if c.model not in ('xmcd','atomic','imported'):
            self.error('Saved MDFF provider is unsupported; results remain viewable without migrating inputs.');return
        from .project_io import frame_rerun_reason,elastic_provider_reason
        provider_reason=elastic_provider_reason(r)
        if provider_reason:self.error(provider_reason);return
        frame_reason=frame_rerun_reason(r)
        if frame_reason:self.error(frame_reason);return
        if r.get('fft_recipe_error'):self.error(r['fft_recipe_error']);return
        from .parallel_resources import MAX_WORKERS
        if (c.worker_mode not in ('automatic','manual') or type(c.parallel_workers) is not int or c.parallel_workers<1
                or not hasattr(self,'memory_mode') and c.parallel_workers>MAX_WORKERS):
            self.error(f'Saved parallel-worker request is unsupported (Automatic/Manual, 1–{MAX_WORKERS}). Saved results remain viewable; inputs were not replaced or clamped.');return
        try:structure=restore_structure(r.get('structure_snapshot'))
        except Exception as exc:self.error(str(exc));return
        if self.model_box.currentIndex()==2:self._remember_manual_state()
        self.retire_post_edge(c.correction)
        c=replace(c,correction=False)
        self._restoring=True
        try:
            self.structure=structure;self.last_result=None;self.table.setRowCount(0)
            if r.get('source_overrides',{}).get('cif'):self.structure.source=r['source_overrides']['cif']
            controls={self.zone:' '.join(map(str,s.zone)),self.target:' '.join(map(str,s.target)),self.axis:' '.join(map(str,c.magnetization)),self.source_path:r.get('source_overrides',{}).get('xmcd',c.source)}
            for widget,value in controls.items():
                with QtCore.QSignalBlocker(widget):widget.setText(value)
            self.set_material_magnetization(c.magnetization)
            self._accepted_global_mdff=c
            for widget,index in ((self.model_box,('xmcd','atomic','imported').index(c.model)),(self.propagation_box,['bloch','fft-multislice','both'].index(c.propagation))):
                with QtCore.QSignalBlocker(widget):widget.setCurrentIndex(index)
            for widget,index in ((self.channeling_box,('single','double').index(c.channeling_model)),):
                with QtCore.QSignalBlocker(widget):widget.setCurrentIndex(index)
            self.restore_sampling_controls(c)
            with QtCore.QSignalBlocker(self.basis_mode):self.basis_mode.setCurrentIndex(self.basis_mode.findData(s.basis_mode))
            provider_index=self.elastic_provider_box.findData(s.elastic_provider)
            if provider_index<0:raise ValueError('Saved elastic provider is unavailable; inputs cannot be restored')
            with QtCore.QSignalBlocker(self.elastic_provider_box):self.elastic_provider_box.setCurrentIndex(provider_index)
            for widget,checked in ((self.row_projection,c.systematic_row),(self.angular_maps,c.angular_maps)):
                with QtCore.QSignalBlocker(widget):widget.setChecked(checked)
            self.mdff_stack.setCurrentIndex(self.model_box.currentIndex())
            self.restore_memory_budget(c.memory_budget_mib)
            if hasattr(self,'memory_mode') and r['metadata'].get('execution',{}).get('memory_policy',{}).get('mode')=='automatic':
                with QtCore.QSignalBlocker(self.memory_mode):self.memory_mode.setCurrentIndex(0)
                self.memory_budget.setEnabled(False)
            self.restore_worker_request(c.worker_mode,c.parallel_workers)
            values=dict(tx=s.tilt[0],ty=s.tilt[1],kv=s.voltage,thickness=s.thickness,beam=s.beam_cutoff,potential=s.potential_cutoff,b=s.b_factor,eta=c.eta,beta=c.beta,xl3=c.l3,xl2=c.l2,sigma=c.sigma,radial=c.radial if c.radial is not None else .05,energy=c.energy_points,grid=c.grid,depth=c.depth,subpixels=c.subpixels,halfwidth=c.halfwidth,radius=c.radius,window_lo=c.window[0],window_hi=c.window[1],fft_grid=c.fft_grid,slice_step=c.slice_step)
            values.update({'atomic_'+k:v for k,v in asdict(c.atomic).items()});self.set_values(values);self.detectors=np.asarray(c.centers);self.sync_detectors();self.sync_za()
            self.sync_angular_resolution()
            for widget,checked in ((self.radial_override,c.radial is not None),(self.declaration,c.axis_declared)):
                with QtCore.QSignalBlocker(widget):widget.setChecked(checked)
            self.source_info=None;self.validated_path=None
            if c.model=='xmcd':
                p=Path(self.source_path.text());expected=c.source_sha256 or (r['metadata'].get('source_audit') or {}).get('sha256')
                if expected and p.is_file() and sha256(p)==expected:self.source_info=inspect_source(p);self.validated_path=str(p);self.source_status.setText('Restored saved source, verified SHA256; native selected energies preserved.')
                else:
                    with QtCore.QSignalBlocker(self.declaration):self.declaration.setChecked(False)
                    self.source_status.setText('Saved data remains available. Rerun disabled: locate original XMCD and verify SHA256.')
            self.input_source_requirements=[]
            if c.model=='imported':self.restore_imported_settings(c,r.get('source_overrides',{}).get('mdff'))
            if hasattr(c,'provider_schema'):self.restore_provider_settings(c,r.get('source_overrides',{}).get('mdff'))
            else:
                with QtCore.QSignalBlocker(self.explicit_xmcd):self.explicit_xmcd.setChecked(False)
                with QtCore.QSignalBlocker(self.atomic_parameter_path):self.atomic_parameter_path.clear()
                self.atomic_provider_info=None
                with QtCore.QSignalBlocker(self.atomic_editor.use_editor):self.atomic_editor.use_editor.setChecked(False)
                self.atomic_editor.validated_path=None;self.atomic_editor.validated_sha256=None
                if c.model=='atomic':
                    from .saved_atomic_ui import restore
                    restore(self.atomic_editor,c,self.structure)
                for widget,value in ((self.xmcd_element,'Ni'),(self.xmcd_edge,'L2,3'),(self.xmcd_selected,'')):
                    with QtCore.QSignalBlocker(widget):widget.setText(value)
                for widget in self.xmcd_l23_controls:widget.setVisible(True)
            for name,status in source_status(r).items():
                if name=='cif':self.input_source_requirements.append(status)
        finally:self._restoring=False
        self._loaded_fft_recipe=(self.fft_cell_key(),c.fft_generators) if c.fft_generators is not None else None
        self.restore_numerical_selection(r['metadata'])
        self.refresh();self.statusBar().showMessage('Saved settings restored to Current Inputs. No calculation started. '+rerun_reason(r))
    def input_source_reason(self):
        reason=self.restored_source_reason()
        if reason:return reason
        for status in getattr(self,'input_source_requirements',[]):
            if self.structure.sha256==status['sha256'] and (not Path(status['path']).is_file() or sha256(status['path'])!=status['sha256']):return 'Saved CIF source unavailable or changed; locate original source before rerunning.'
        return ''
    def locate_source(self):
        if self.emcd_result is None:return
        r=self.emcd_result;statuses=source_status(r)
        choices=list(statuses)
        if not choices:self.error('No external source is recorded for this result.');return
        kind,ok=QtWidgets.QInputDialog.getItem(self,'Locate Original Source','Source to reconnect',choices,0,False)
        if not ok:return
        path,_=QtWidgets.QFileDialog.getOpenFileName(self,'Locate original '+kind+' (SHA256 must match)')
        if not path:return
        if sha256(path)!=statuses[kind]['sha256']:self.error('SHA256 mismatch. This file is not the original source.');return
        r.setdefault('source_overrides',{})[kind]=str(Path(path).resolve())
        if self.selected_record:self.selected_record['source_overrides']=r['source_overrides'];self.browser.registry.persist()
        self.statusBar().showMessage('Original source hash verified. Use These Settings to prepare a rerun.')
    def export_current_figure(self):
        widget=self.tabs.currentWidget();figure=getattr(widget,'figure',self.figure)
        self.export_figure_for(figure)
    def export_figure_for(self,figure):
        path,_=QtWidgets.QFileDialog.getSaveFileName(self,'Export currently displayed plot','','PNG (*.png);;SVG (*.svg)')
        if path:
            from .normalization_export import save_figure
            save_figure(figure,path)
    def export_selected_data(self):
        if self.emcd_result is None:return
        if self.emcd_result['config'].model=='multisite':self.eels_view.export_derived();return
        widget=self.tabs.currentWidget()
        if hasattr(widget,'export_derived'):widget.export_derived();return
        if hasattr(widget,'export_data'):widget.export_data();return
        from .compare_results import export_comparison_data
        parent=QtWidgets.QFileDialog.getExistingDirectory(self,'Data export parent (new folder)')
        if not parent:return
        r=self.emcd_result;label=self.selected_record['name'] if self.selected_record else 'Completed run'
        entries=[(label,dict(m,comparison=r.get('comparison',{})),name) for name,m in r['methods'].items()]
        path=Path(parent)/datetime.now(timezone.utc).strftime('data_%Y%m%d_%H%M%S_%fZ')
        self.io_operation(lambda cancel,progress:export_comparison_data(entries,path),lambda _:None)
