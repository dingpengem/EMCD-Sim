"""Opt-in native corrective acceptance; scripted Qt events, not human acceptance.

Reads existing Mac projects; all saves and exports go to a fresh output folder.
RSS includes native allocations. Sampling is not an exact allocator high-water mark.
"""
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
import gc,json,logging,sys,threading,time,traceback,resource
import numpy as np
from PySide6 import QtCore,QtWidgets,QtTest
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui import parallel_resources as pr
from emcd_sim.gui.memory_budget import memory_snapshot
from emcd_sim.gui.multisite_run import applied_inputs
from emcd_sim.gui.propagation import numerical_info


def arrays(result):
    values={}
    def visit(value,path):
        if isinstance(value,np.ndarray) and value.dtype.kind in 'fiucb':values[path]=value
        elif isinstance(value,dict):
            for key,item in value.items():
                if key not in ('metadata','diagnostics','fft','comparison','methods','structure_snapshot','configuration'):
                    visit(item,path+'/'+str(key))
    visit(result,'result');return values


def executors(value):
    if isinstance(value,dict):
        if 'max_concurrent_tasks' in value:yield value
        for item in value.values():yield from executors(item)
    elif isinstance(value,(list,tuple)):
        for item in value:yield from executors(item)


def wait(app,w,seconds=90):
    deadline=time.monotonic()+seconds
    while w.busy and time.monotonic()<deadline:
        app.processEvents();QtTest.QTest.qWait(5)
    timed_out=w.busy
    if timed_out:
        w.cancel();deadline=time.monotonic()+20
        while w.busy and time.monotonic()<deadline:
            app.processEvents();QtTest.QTest.qWait(10)
        if w.busy:raise RuntimeError('Worker did not stop after diagnostic time limit')
    app.processEvents();return timed_out


def dispose(app,w):
    w.project_dirty=False;w.close();w.deleteLater()
    app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete);app.processEvents();gc.collect()


def load(app,root,out,material,name):
    w=MainWindow(out/(name+'-workspace'));w.store_ui_preferences=lambda:None
    errors=[];w.error=errors.append;w.show()
    normal=dict(values={k:v.value() for k,v in w.spin.items()},zone=w.zone.text(),
                target=w.target.text(),scope=w.energy_scope.currentData())
    w.project_dirty=False;w.open_project_path(root/(material+'_project'));wait(app,w)
    assert not errors,errors
    return w,errors,normal


def click(app,button):
    QtTest.QTest.mouseClick(button,QtCore.Qt.MouseButton.LeftButton)
    app.processEvents();QtTest.QTest.qWait(150)


def dialog_checks(app,root,out):
    checks=[]
    for material,mode in [('Ni','global'),('Fe3O4','local'),('Cr','local')]:
        w,errors,_=load(app,root,out,material,material+'-dialog')
        w.show_structure_viewer();v=w.structure_viewer;v.set_magnetization_mode(mode);e=v.editor
        before=e._accepted_rows
        if mode=='local':
            e.replace_rows(tuple(r[:3]+(tuple(-x for x in r[3]),r[4]) if r[1]!='O' else r for r in e.rows()))
        ids=[r[0] for r in e.rows() if r[1]!='O'] if mode=='local' else [None]
        for identity in ids:
            d=w.open_mdff_context(identity);app.processEvents();QtTest.QTest.qWait(150)
            click(app,d.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Apply))
            assert v.isVisible() and v.isActiveWindow() and not d.isVisible(),d.status.text()
            assert e._accepted_rows==before,'Done accepted outer Material transaction'
            v.grab().save(str(out/(material+'-'+str(identity)+'-returned.png')))
            checks.append(dict(material=material,mode=mode,group=identity,done_returns=True,viewer_active=True,outer_unaccepted=True))
        d=w.open_mdff_context(ids[0]);declaration=d.declaration if mode=='local' else w.declaration
        ack=declaration.isChecked();declaration.setChecked(not ack)
        click(app,d.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel))
        assert declaration.isChecked()==ack and v.isVisible()
        draft=e.rows();click(app,v.dialog_buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Apply))
        assert not v.isVisible(),e.status.text()
        w.show_structure_viewer();assert e.rows()==draft
        checks[-1].update(cancel_restores=True,outer_apply_and_reopen=True)
        dispose(app,w)
    return checks


@contextmanager
def observe_blas(observations):
    detector_guard=pr.detector_blas_guard;calculation_guard=pr.calculation_blas_guard
    @contextmanager
    def measured(kind,guard,*args):
        runtime=pr._accelerate_blas();before=int(runtime[0]()) if runtime else None;during=None
        try:
            with guard(*args) as info:
                during=int(runtime[0]()) if runtime else None
                yield info
        finally:
            after=int(runtime[0]()) if runtime else None
            observations.append(dict(kind=kind,thread=threading.get_ident(),before=before,during=during,after=after))
    pr.detector_blas_guard=lambda:measured('detector',detector_guard)
    pr.calculation_blas_guard=lambda cancelled=None:measured('calculation',calculation_guard,cancelled)
    try:yield
    finally:pr.detector_blas_guard=detector_guard;pr.calculation_blas_guard=calculation_guard


def measure(app,w,errors,observations,seconds):
    # Settle pending initial/resized Qt paints before taking the baseline.
    app.processEvents();QtTest.QTest.qWait(150)
    memory_before=memory_snapshot();baseline=memory_before['process_rss_mib'];samples=[baseline];calculation_samples=[baseline]
    phase={'result_emitted':False};stop=threading.Event()
    def sample():
        while not stop.wait(.005):
            value=memory_snapshot()['process_rss_mib'];samples.append(value)
            if not phase['result_emitted']:calculation_samples.append(value)
    def emitted(*_):
        calculation_samples.append(memory_snapshot()['process_rss_mib']);phase['result_emitted']=True
    usage=resource.getrusage(resource.RUSAGE_SELF);cpu_before=usage.ru_utime+usage.ru_stime
    sampler=threading.Thread(target=sample);sampler.start();started=time.perf_counter();worker=None;timed_out=False
    try:
        w.start_emcd();worker=w.worker if w.busy else None
        if worker is not None:
            worker.result.connect(emitted,QtCore.Qt.ConnectionType.DirectConnection)
            worker.failed.connect(emitted,QtCore.Qt.ConnectionType.DirectConnection)
            timed_out=wait(app,w,seconds)
    finally:
        stop.set();sampler.join();samples.append(memory_snapshot()['process_rss_mib'])
    elapsed=time.perf_counter()-started;usage=resource.getrusage(resource.RUSAGE_SELF);cpu=usage.ru_utime+usage.ru_stime-cpu_before
    return dict(elapsed_seconds=elapsed,process_cpu_seconds=cpu,average_cpu_cores=cpu/elapsed,baseline_rss_mib=baseline,
        memory_before=memory_before,memory_after=memory_snapshot(),
        peak_rss_mib=max(samples),incremental_peak_mib=max(samples)-baseline,
        calculation_peak_rss_mib=max(calculation_samples),calculation_incremental_peak_mib=max(calculation_samples)-baseline,
        rss_samples=len(samples),errors=list(errors),time_limit_seconds=seconds,time_limit_reached=timed_out,
        outcome=w.run_outcome if worker else 'rejected',blas_observations=list(observations))


def validate_result(r):
    a=arrays(r);assert a
    for key in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus','N_A','N_B','M_A','M_B','D_raw','D_mag','D_nonmag'):
        assert np.isfinite(r['spectra'][key]).all(),key
    for maps in r['maps'].values():
        for key in ('I_plus','I_minus'):assert np.isfinite(maps[key]).all() and maps[key].shape==r['qx'].shape,key
    if r.get('groups'):
        for key in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus'):
            summed=sum(g['metadata']['contribution_weight']*g['spectra'][key] for g in r['groups'].values())
            np.testing.assert_allclose(summed,r['spectra'][key],rtol=2e-10,atol=max(np.max(abs(summed))*2e-12,1e-30))
    return a


def resource_ui_evidence(app,w,out,name):
    """Capture the real Cocoa panel, including compact-window scroll access."""
    from emcd_sim.gui.responsive import CollapsibleSection
    p=w.resource_panel
    for section in w.findChildren(CollapsibleSection):
        if section.objectName().startswith('settings_'):
            section.setChecked('Shared_Calculation' in section.objectName())
    section=w.shared_resources_group.presentation_section;section.setChecked(True)
    layouts=[]
    for width,height in ((1280,800),(1024,700)):
        w.resize(width,height);app.processEvents();QtTest.QTest.qWait(100)
        scroll=w.splitter.widget(0);scroll.ensureWidgetVisible(p.estimate);app.processEvents()
        section.grab().save(str(out/f'{name}-{width}-panel.png'))
        w.grab().save(str(out/f'{name}-{width}-window.png'))
        for label in (p.hardware,p.cpu_auto,p.memory_auto,p.estimate):
            if label.isVisible():
                assert label.height()>=label.heightForWidth(label.width()),(label.text(),label.size())
        layouts.append(dict(window=[w.width(),w.height()],panel_width=p.width(),device_pixel_ratio=w.devicePixelRatioF(),scroll_access=True))
    snap=p.preview;info=snap['info']
    return dict(hardware=p.hardware.text(),cpu=p.cpu_auto.text(),memory=p.memory_auto.text(),estimate=p.estimate.text(),
        manual_workers=w.worker_count.value(),manual_memory=p.memory_request.value(),
        manual_cpu_visible=not p.cpu_manual.isHidden(),manual_memory_visible=not p.memory_manual.isHidden(),
        effective_workers=info['execution']['effective_workers'],memory_budget_mib=info['memory_budget_mib'],layouts=layouts)


def run(root,output,profile='bounded'):
    if profile not in ('bounded','medium','defaults','dialogs','lifecycle','adaptive-small','adaptive-confirm','adaptive-medium','adaptive-scaling','adaptive-lifecycle','adaptive-portable','adaptive-resource-ui'):raise ValueError('Unknown corrective profile')
    root=Path(root).resolve();out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False)
    logger=logging.getLogger('emcd_sim.gui');logger.addHandler(logging.FileHandler(out/'gui.log'));logger.setLevel(logging.INFO)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([]);app.setQuitOnLastWindowClosed(False)
    assert app.platformName()=='cocoa'
    report=dict(profile=profile,gui_thread_id=threading.get_ident(),qt_platform=app.platformName(),
        frozen=bool(getattr(sys,'frozen',False)),native=pr.native_backend_info(),cases=[],complete=False)
    def record():(out/'report.json').write_text(json.dumps(report,indent=2,default=str))
    observations=[]
    try:
        if profile=='dialogs':report['dialogs']=dialog_checks(app,root,out)
        else:
            cases=([('Fe3O4','local')] if profile in ('adaptive-portable','adaptive-resource-ui') else
                [('NiFe2O4','local')] if profile=='adaptive-scaling' else
                [('Ni','global'),('Ni','local'),('Cr','local')] if profile in ('bounded','adaptive-small','adaptive-confirm') else
                [('Fe3O4','local'),('NiFe2O4','local')] if profile in ('medium','adaptive-medium') else [('Ni','global'),('Cr','local')])
            with observe_blas(observations):
                for material,mode in cases:
                    for method in ('bloch','fft-multislice'):
                        for channel in ('single','double'):
                            if profile=='adaptive-scaling' and (method!='fft-multislice' or channel!='double'):continue
                            name=f'{material}-{mode}-{method}-{channel}'
                            w,errors,normal=load(app,root,out,material,name)
                            w.show_structure_viewer();v=w.structure_viewer;v.set_magnetization_mode(mode)
                            if mode=='global':
                                d=w.open_mdff_context();assert d.apply_configuration() is not None,d.status.text();d.hide()
                            v.apply_groups();assert not v.isVisible(),v.editor.status.text()
                            w.propagation_box.setCurrentIndex(0 if method=='bloch' else 1)
                            w.channeling_box.setCurrentIndex(0 if channel=='single' else 1);w.worker_mode.setCurrentIndex(1)
                            if profile in ('medium','adaptive-medium','adaptive-scaling','adaptive-portable','adaptive-resource-ui'):
                                w.set_values(dict(grid=17,depth=9,fft_grid=24,beam=.65,potential=1.2));w.basis_mode.setCurrentIndex(0)
                            elif profile=='defaults':
                                w.set_values(normal['values']);w.zone.setText(normal['zone']);w.target.setText(normal['target']);w.basis_mode.setCurrentIndex(0)
                                w.energy_scope.setCurrentIndex(w.energy_scope.findData(normal['scope']))
                            if profile=='adaptive-small':
                                requests=['auto']+[n for n in (1,2,4,6,8,10) if n<=pr.MAX_WORKERS]
                            elif profile in ('adaptive-confirm','adaptive-portable','adaptive-resource-ui'):
                                requests=['auto',min(8,pr.MAX_WORKERS) if channel=='double' else 1]
                            elif profile in ('adaptive-medium','adaptive-scaling'):
                                requests=['auto',1]+([n for n in (6,8) if n<=pr.MAX_WORKERS] if channel=='double' else [])
                                if material=='NiFe2O4' and method=='fft-multislice' and channel=='double':requests=['auto']+[n for n in (1,2,4,6,8) if n<=pr.MAX_WORKERS]
                            elif profile=='adaptive-lifecycle':requests=['auto']
                            else:requests=(1,2,4) if profile=='bounded' else (1,)
                            for request in requests:
                                automatic=request=='auto';count=1 if automatic else request
                                errors.clear();observations.clear();w.worker_mode.setCurrentIndex(0 if automatic else 1)
                                if hasattr(w,'memory_mode'):w.memory_mode.setCurrentIndex(0 if automatic else 1)
                                w.worker_count.setValue(count);w.refresh();w.emcd_stale()
                                w.browser.table.clearSelection();w.browser.selection_timer.stop()
                                row=dict(material=material,mode=mode,method=method,channel=channel,requested='Automatic' if automatic else count,memory_mode='automatic' if automatic else 'manual')
                                if profile=='adaptive-resource-ui':
                                    row['resource_ui']=resource_ui_evidence(app,w,out,name+'-'+str(request))
                                try:
                                    cfg=w.forward_settings();sites=None
                                    if mode=='local':cfg,sites,windows,reverse,signature=applied_inputs(w,cfg)
                                    row.update(settings=asdict(w.settings()),config=asdict(cfg))
                                    row['preflight']=numerical_info(w.structure,w.settings(),cfg,enforce_execution=False,
                                        **({'ionization_sites':sites} if sites else {}))
                                except Exception as exc:
                                    row.update(outcome='validation_rejected',errors=[str(exc)],traceback=traceback.format_exc())
                                    report['cases'].append(row);record();continue
                                if profile in ('lifecycle','adaptive-lifecycle'):
                                    before={k:v.copy() for k,v in arrays(w.emcd_result).items()};runs=len(w.browser.registry.records)
                                    w.start_emcd();assert w.busy,errors
                                    QtCore.QTimer.singleShot(10,w.cancel);wait(app,w)
                                    assert w.run_outcome=='cancelled' and len(w.browser.registry.records)==runs,w.run_outcome
                                    for key,value in before.items():np.testing.assert_array_equal(arrays(w.emcd_result)[key],value)
                                    row['cancel_blas']=list(observations);observations.clear()
                                    row['cancelled_without_result_loss']=True
                                    w.worker_mode.setCurrentIndex(1);w.worker_count.setValue(2);w.channeling_box.setCurrentIndex(0);w.start_emcd()
                                    assert not w.busy and errors
                                    row['rejected_request']=list(errors);errors.clear()
                                    w.worker_mode.setCurrentIndex(0 if automatic else 1);w.worker_count.setValue(count);w.channeling_box.setCurrentIndex(0 if channel=='single' else 1)
                                row.update(measure(app,w,errors,observations,(120 if channel=='single' else 20) if profile=='defaults' else 90))
                                if profile=='adaptive-resource-ui':
                                    final=w.resource_panel.finalized['info']
                                    row['finalized_resource_ui']=dict(effective_workers=final['execution']['effective_workers'],
                                        memory_budget_mib=final['memory_budget_mib'],notice=w.resource_panel.run_allocation_text)
                                if row['outcome']=='completed' and not errors:
                                    r=w.emcd_result;a=validate_result(r);case_name=name+'-'+('auto' if automatic else str(count))
                                    if profile=='adaptive-resource-ui':
                                        assert final['execution']['effective_workers']==r['metadata']['execution']['effective_workers']
                                        assert final['memory_budget_mib']==r['config'].memory_budget_mib
                                    np.savez_compressed(out/(case_name+'.npz'),**a)
                                    row.update(array_shapes={k:list(v.shape) for k,v in a.items()},execution=r['metadata']['execution'],
                                        worker_memory=r['metadata']['numerics'],executors=list(executors(r['metadata'].get('angular_evaluation',[]))),
                                        actual_calculation_seconds=r['metadata'].get('calculation_seconds'),
                                        masked_array_nonfinite_counts={k:int((~np.isfinite(v)).sum()) for k,v in a.items() if not np.isfinite(v).all()})
                                    if profile in ('medium','lifecycle','adaptive-lifecycle') or profile.startswith('adaptive-') and (automatic or request==requests[-1]):
                                        w.save_to_path(out/(case_name+'-project'));wait(app,w)
                                        reopened=MainWindow(out/(case_name+'-reopen'));reopened.store_ui_preferences=lambda:None
                                        reopened.error=errors.append;reopened.project_dirty=False;reopened.open_project_path(out/(case_name+'-project'));wait(app,reopened)
                                        for key,value in a.items():np.testing.assert_array_equal(arrays(reopened.emcd_result)[key],value)
                                        reopened.emcd_stale();assert 'inputs match' in reopened.eels_view.label.text(),reopened.eels_view.label.text()
                                        row['save_reopen_arrays_and_freshness']=True
                                        if profile.startswith('adaptive-'):
                                            assert (reopened.memory_mode.currentIndex()==0)==automatic
                                            assert reopened.worker_mode.currentIndex()==(0 if automatic else 1)
                                        dispose(app,reopened)
                                report['cases'].append(row);record()
                                print(name,count,row['outcome'],row['errors'],round(row.get('elapsed_seconds',0),3),flush=True)
                            dispose(app,w)
        report['complete']=True;record();return 0
    except Exception:
        report['exception']=traceback.format_exc();record();raise


if __name__=='__main__':
    raise SystemExit(run(sys.argv[1],sys.argv[2],sys.argv[3] if len(sys.argv)>3 else 'bounded'))
