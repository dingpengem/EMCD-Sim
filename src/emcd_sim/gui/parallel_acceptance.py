"""Opt-in actual Qt/native selected-edge acceptance for a diagnostic build."""
import json,os,sys,time,faulthandler
from pathlib import Path
import numpy as np
from PySide6 import QtCore,QtWidgets
from .runtime import build_info
from .project_io import load_project,save_project
from .stage_f_acceptance import fingerprints
from .parallel_resources import native_backend_info
from .emcd_forward import export_result


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
    assert (w.settings().voltage,w.settings().beam_cutoff,w.settings().potential_cutoff)==(300,3,2)
    assert w.spin['grid'].value()==97 and w.memory_budget.currentData()==2048
    assert w.worker_mode.currentIndex()==0 and not w.shared_resources_group.isHidden()
    report['new_defaults']=dict(voltage=300,beam=3,potential=2,grid=97,memory_budget_mib=2048)
    if project:
        result=load_project(project);before=fingerprints(result);w.emcd_result=result;w.use_result_settings()
        assert w.settings()==result['settings'] and w.forward_settings()==result['config']
        assert fingerprints(result)==before;report['legacy_settings_preserved']=True
    else:
        w.declaration.setChecked(True)  # Explicit test declaration, never a source calibration.
    w.propagation_box.setCurrentIndex(0);w.channeling_box.setCurrentIndex(1)
    w.numerical_mode.setCurrentIndex(1);w.spin['beam'].setValue(3.)
    numeric=w.numerical_snapshot();w.worker_mode.setCurrentIndex(1);w.worker_count.setValue(4)
    assert w.numerical_snapshot()==numeric
    if report['native']['platform']=='win32' and report['native']['threads']!=1:
        assert not w.emcd_button.isEnabled()
        previous=w.worker;w.start_emcd();assert not w.busy and w.worker is previous
        report['parallel_request_blocked']=True;report['blocked_preview']=w.memory_label.text()
        w.spin['beam'].setValue(2.5);assert 'Retained beams: 21' in w.memory_label.text()
        w.spin['beam'].setValue(3.);assert 'Retained beams: 27' in w.memory_label.text()
    else:report['parallel_request_blocked']=False
    if workers is None:w.worker_mode.setCurrentIndex(0)
    else:w.worker_mode.setCurrentIndex(1);w.worker_count.setValue(workers)
    w.energy_scope.setCurrentIndex(1);w.angular_maps.setChecked(False)
    report['run_preview']=w.memory_label.text();report['requested_workers']=workers
    assert w.settings().beam_cutoff==3 and w.settings().potential_cutoff==2
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
    if not w.busy:failed('Approved bounded native run did not start');w.close();sys.excepthook=previous_hook;return 2
    w.worker.stage.connect(lambda text:report['stages'].append(text))
    def tick():
        report['heartbeats']+=1
        if w.busy:return
        try:
            assert w.run_outcome=='completed' and w.inputs.isEnabled()
            result=w.emcd_result;execution=result['metadata']['execution']
            assert execution['effective_workers']['bloch']==(workers or 1)
            assert execution['native']['threads']==report['native']['threads']==native_backend_info()['threads']
            assert result['settings'].beam_cutoff==3 and result['settings'].potential_cutoff==2
            before=fingerprints(result);destination=output/'saved_project';save_project(result,destination)
            assert fingerprints(load_project(destination))==before
            export_result(result,output/'exports')
            report.update(execution=execution,save_reopen=True,exports=True,arrays_unchanged=before==fingerprints(result),
                result_config=vars(result['config']).copy(),settings=vars(result['settings']).copy(),complete=True,
                elapsed_seconds=time.time()-report['start'])
            arrays=result['methods']['bloch']['spectra'];np.savez_compressed(output/'spectra.npz',**arrays)
            w.grab().save(str(output/'completed.png'))
            (output/'acceptance.json').write_text(json.dumps(report,indent=2,default=str));w.close();app.quit()
        except Exception as exc:failed(str(exc))
    timer=QtCore.QTimer();timer.timeout.connect(tick);timer.start(25)
    QtCore.QTimer.singleShot(180000,lambda:failed('Acceptance timeout'))
    code=app.exec();sys.excepthook=previous_hook
    return code
