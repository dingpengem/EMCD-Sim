"""Opt-in actual Qt/native selected-edge acceptance for a diagnostic build."""
import json,os,sys,time,faulthandler
from dataclasses import replace
from pathlib import Path
import numpy as np
from PySide6 import QtCore,QtWidgets
from emcd_sim.provenance import build_info
from .project_io import load_project,save_project
from .project_io import fingerprints
from emcd_sim.parallel_resources import native_backend_info
from .result_export import export_result


def run(output,project=None,workers=None):
    from .app import MainWindow
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w=MainWindow(workspace=output/'workspace');w.resize(1550,1000)
    w.setWindowTitle(build_info()['label'])
    report=dict(build=build_info(),pid=os.getpid(),executable=sys.executable,
        frozen=bool(getattr(sys,'frozen',False)),native=native_backend_info(),fault_tracing=faulthandler.is_enabled(),
        stages=[],heartbeats=0,start=time.time(),errors=[])
    w.error=report['errors'].append
    w.new_project()
    assert (w.settings().voltage,w.settings().beam_cutoff,w.settings().potential_cutoff)==(300,2.5,2.0)
    assert w.spin['grid'].value()==97 and w.memory_budget.value()==2048
    assert w.worker_mode.currentIndex()==0 and not w.compute_resources.isHidden()
    report['new_defaults']=dict(voltage=300,beam=2.5,potential=2.0,grid=97,memory_budget_mib=2048)
    if project:
        result=load_project(project);before=fingerprints(result);w.emcd_result=result;w.use_result_settings()
        restored=w.forward_settings()
        assert w.settings()==result['settings']
        assert restored.source_sha256==result['config'].source_sha256
        assert restored==replace(result['config'],source=restored.source,resource_allocation=None)
        assert fingerprints(result)==before;report['legacy_settings_preserved']=True
    else:
        # This diagnostic explicitly selects the historical Ni example.
        w.model_box.setCurrentIndex(0);w.validate_xmcd(show_error=False)
        w.declaration.setChecked(True);w.reference_ni.setChecked(True)
    w.propagation_box.setCurrentIndex(0);w.channeling_box.setCurrentIndex(1)
    w.numerical_mode.setCurrentIndex(1)
    if not project:
        w.show_structure_viewer()
        assert w.mdff_dialog.apply_configuration() is not None,w.mdff_dialog.status.text()
        w.structure_viewer.apply_groups()
    if project:w.spin['beam'].setValue(3.)  # Retain the explicit historical crash profile.
    run_cutoffs=(w.settings().beam_cutoff,w.settings().potential_cutoff)
    numeric=w.numerical_snapshot();w.worker_mode.setCurrentIndex(1);w.worker_count.setValue(4)
    assert w.numerical_snapshot()==numeric
    if (report['native']['platform']=='win32' and report['native']['threads']!=1
            and not report['native'].get('automatic_thread_control')):
        assert not w.emcd_button.isEnabled()
        previous=w.worker;w.start_emcd();assert not w.busy and w.worker is previous
        report['parallel_request_blocked']=True;report['blocked_preview']=w.compute_resources.estimate.text()
        w.spin['beam'].setValue(2.5);assert 'Beams: 21' in w.compute_resources.estimate.text()
        w.spin['beam'].setValue(3.);assert 'Beams: 27' in w.compute_resources.estimate.text()
        w.spin['beam'].setValue(run_cutoffs[0])
    else:report['parallel_request_blocked']=False
    if workers is None:w.worker_mode.setCurrentIndex(0)
    else:
        w.worker_mode.setCurrentIndex(1);w.worker_count.setValue(workers)
        assert w.worker_count.value()==workers,'Unsupported diagnostic worker request'
    w.memory_mode.setCurrentIndex(1)  # Preserve the unchanged requested budget through I/O.
    w.energy_scope.setCurrentIndex(w.energy_scope.findData('edges'));w.angular_maps.setChecked(False)
    report['run_preview']=w.compute_resources.estimate.text();report['requested_workers']=workers
    assert (w.settings().beam_cutoff,w.settings().potential_cutoff)==run_cutoffs
    w.show();app.processEvents()
    for area in w.findChildren(QtWidgets.QScrollArea):
        if area.widget() is w.inputs:area.ensureWidgetVisible(w.worker_mode)
    app.processEvents();w.grab().save(str(output/'worker_controls.png'))
    def failed(message):
        report['failure']=message
        (output/'failure.json').write_text(json.dumps(report,indent=2,default=str));app.exit(2)
    previous_hook=sys.excepthook
    sys.excepthook=lambda typ,value,tb:failed(str(value))
    w.error=failed
    w.start_emcd()
    if not w.busy:failed('Approved bounded native run did not start');w.project_dirty=False;w.close();sys.excepthook=previous_hook;return 2
    admitted=w.worker.execution_policy
    w.worker.stage.connect(lambda text:report['stages'].append(text))
    def tick():
        report['heartbeats']+=1
        if w.busy:return
        try:
            timer.stop()
            assert w.run_outcome=='completed' and w.inputs.isEnabled()
            result=w.emcd_result;execution=result['metadata']['execution']
            assert execution['effective_workers']['bloch']==admitted['effective_workers']['bloch']
            if workers is not None:assert execution['effective_workers']['bloch']==workers
            else:assert 1<=execution['effective_workers']['bloch']<=execution['cpu_worker_limit']
            assert execution['native']['threads']==report['native']['threads']==native_backend_info()['threads']
            assert (result['settings'].beam_cutoff,result['settings'].potential_cutoff)==run_cutoffs
            before=fingerprints(result);destination=output/'saved_project';save_project(result,destination)
            assert fingerprints(load_project(destination))==before
            export_result(result,output/'exports')
            # Change the visible draft, then restore the actual computed request.
            # No calculation or result relabeling occurs with the temporary values.
            w.worker_mode.setCurrentIndex(0);w.worker_count.setValue(1)
            w.memory_mode.setCurrentIndex(0);w.memory_budget.setValue(512)
            opened=load_project(destination);w.display_saved_result(opened);w.use_result_settings()
            cfg=result['config']
            assert w.worker_mode.currentIndex()==(cfg.worker_mode=='manual')
            assert w.worker_count.value()==cfg.parallel_workers
            assert w.memory_mode.currentIndex()==1 and w.memory_budget.value()==cfg.memory_budget_mib
            assert fingerprints(opened)==before
            report.update(execution=execution,save_reopen=True,exports=True,arrays_unchanged=before==fingerprints(result),
                resource_settings_restored=True,
                result_config=vars(result['config']).copy(),settings=vars(result['settings']).copy(),complete=True,
                elapsed_seconds=time.time()-report['start'])
            arrays=result['methods']['bloch']['spectra'];np.savez_compressed(output/'spectra.npz',**arrays)
            w.grab().save(str(output/'completed.png'))
            (output/'acceptance.json').write_text(json.dumps(report,indent=2,default=str));w.project_dirty=False;w.close();app.quit()
        except Exception as exc:failed(str(exc))
    timer=QtCore.QTimer();timer.timeout.connect(tick);timer.start(25)
    QtCore.QTimer.singleShot(180000,lambda:failed('Acceptance timeout'))
    code=app.exec();sys.excepthook=previous_hook
    return code
