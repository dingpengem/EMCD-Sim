"""Opt-in native source/frozen cancellation acceptance; real workers and kernels.

Controlled 180 ms work blocks at actual kernel checkpoints make requests
reproducible. Separate uninstrumented cancellation also exercises real work.
"""
from pathlib import Path
from unittest.mock import patch
import hashlib,json,os,sys,threading,time,traceback
from contextlib import ExitStack
import numpy as np
from PySide6 import QtCore,QtWidgets
from .. import double_channeling as bw,multislice_double_channeling as ms
from . import channeling,stage_b,memory_budget
from .project_io import save_project,load_project
from .rc_acceptance import fingerprints
from .runtime import build_info


def run(output,source):
    from .app import MainWindow
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w=MainWindow(workspace=output/'workspace');w.resize(1400,950);w.show()
    report=dict(build=build_info(),frozen=bool(getattr(sys,'frozen',False)),
        qt_platform=app.platformName(),screen_dpr=app.primaryScreen().devicePixelRatio(),
        clean_machine='NOT TESTED',controlled_block_seconds=.18,cases={},errors=[])
    w.error=lambda message:report['errors'].append(message)
    ticks=[];timer=QtCore.QTimer();timer.setInterval(10);timer.timeout.connect(lambda:ticks.append(time.perf_counter()));timer.start()
    def until(predicate,timeout=90):
        deadline=time.monotonic()+timeout
        while not predicate():
            app.processEvents();time.sleep(.005)
            if time.monotonic()>deadline:raise TimeoutError('Cancellation acceptance timed out')
        app.processEvents()
    def idle():until(lambda:not w.busy)
    def check(value,message):
        if not value:raise AssertionError(message)
    try:
        w.reset_reference();w.source_path.setText(str(source));w.validate_xmcd();w.declaration.setChecked(True)
        w.set_values(dict(thickness=2,beam=.9,potential=1.8,xl3=831.4778,xl2=848.698,halfwidth=.5))
        for key,value in dict(energy=9,grid=9,depth=17,subpixels=16,fft_grid=24).items():w.spin[key].setValue(value)
        w.correction.setChecked(False);w.angular_maps.setChecked(False);w.energy_scope.setCurrentIndex(0)
        w.channeling_box.setCurrentIndex(1);w.propagation_box.setCurrentIndex(0);w.align();w.refresh()
        w.start_emcd();idle();check(w.run_outcome=='completed','Initial real Double run')
        previous=w.emcd_result;before=fingerprints(previous)
        save_project(previous,output/'preserved_project')
        saved_hash=hashlib.sha256((output/'preserved_project'/'project.json').read_bytes()).hexdigest()
        browser_count=len(w.browser.registry.records)
        cases=[('bw_full','bloch','depth',True),('ms_outgoing','fft-multislice','outgoing',True),
            ('ms_depth','fft-multislice','depth',True),('both_first','both','depth',True),
            ('near_completion','bloch','completion',True),('repeat_cancel','bloch','depth',True),
            ('single','bloch','single',True),('bw_uninstrumented','bloch','depth',False),
            ('ms_uninstrumented','fft-multislice','outgoing',False)]
        for name,solver,target,controlled in cases:
            w.propagation_box.setCurrentIndex(['bloch','fft-multislice','both'].index(solver))
            w.channeling_box.setCurrentIndex(0 if target=='single' else 1)
            entered=threading.Event();lock=threading.Lock();second=[];tick_start=len(ticks)
            def work_boundary():
                with lock:
                    first=not entered.is_set();entered.set()
                if first and controlled:time.sleep(.18)
            def probe(original):
                def checked(cancelled=None):
                    frame=sys._getframe(1)
                    hit=(target=='depth' and (frame.f_code.co_name=='depth_response' or
                        (frame.f_code.co_name=='multislice_double_channeling_response' and 'iz' in frame.f_locals)))
                    hit=hit or (target=='outgoing' and frame.f_code.co_name=='advance' and frame.f_locals.get('dz',0)<0)
                    if hit:work_boundary()
                    return original(cancelled)
                return checked
            with ExitStack() as stack:
                for module in (bw,ms):stack.enter_context(patch.object(module,'check_cancelled',probe(module.check_cancelled)))
                original_ms=channeling.multislice_double_channeling_response
                def ms_response(*a,**kw):second.append(True);return original_ms(*a,**kw)
                stack.enter_context(patch.object(channeling,'multislice_double_channeling_response',ms_response))
                if target=='completion':
                    original=stage_b.calculate
                    def complete(*a,**kw):
                        result=original(*a,**kw);work_boundary();return result
                    stack.enter_context(patch.object(stage_b,'calculate',complete))
                if target=='single':
                    original_single=channeling._tensor_angular_maps
                    def single(*a,**kw):work_boundary();return original_single(*a,**kw)
                    stack.enter_context(patch.object(channeling,'_tensor_angular_maps',single))
                w.start_emcd();check(w.busy,name+' started')
                until(entered.is_set)
                # No processEvents in this interval: record request directly
                # while the numerical worker is still active.
                w.cancel_button.click()
                check(w.statusBar().currentMessage()=='Cancelling...','Immediate pending status')
                if name=='repeat_cancel':w.cancel_button.click();w.cancel()
                worker=w.worker
                idle();worker.wait(1000)
            t=worker.cancellation_times
            check(all(k in t for k in ('requested','acknowledged','stopped','idle')),name+' timing')
            check(t['idle']-t['requested']<2,name+' latency under 2 s in measured profile')
            check(w.run_outcome=='cancelled' and w.statusBar().currentMessage()=='Calculation cancelled.',name+' terminal state')
            check(w.emcd_result is previous and fingerprints(previous)==before,name+' previous arrays intact')
            check(len(w.browser.registry.records)==browser_count,name+' no incomplete registration')
            check(not memory_budget._reservations,name+' memory cleanup')
            check(not report['errors'],name+' no failure dialog')
            check(w.inputs.isEnabled() and not w.cancel_button.isEnabled(),name+' controls restored')
            if name=='both_first':check(not second,'Second Double solver must not start')
            active_ticks=[v for v in ticks[tick_start:] if t['requested']<=v<=t['idle']]
            if controlled:check(len(active_ticks)>=2,name+' GUI timer responsive')
            report['cases'][name]=dict(outcome='PASS',controlled=controlled,times=t,
                acknowledgement_seconds=t['acknowledged']-t['requested'],
                stop_seconds=t['stopped']-t['requested'],idle_seconds=t['idle']-t['requested'],gui_ticks=len(active_ticks))
        # Force the result signal to remain queued until Cancel has been
        # requested. This race test intentionally withholds GUI event delivery;
        # it is not used as a responsiveness measurement.
        w.propagation_box.setCurrentIndex(0);w.start_emcd()
        check(w.worker.wait(90000),'Queued completion worker stopped')
        w.cancel();idle()
        check(w.run_outcome=='cancelled' and w.emcd_result is previous,'Queued result suppressed')
        check(len(w.browser.registry.records)==browser_count,'Queued result not registered')
        report['queued_completion']='PASS'
        # A real immediate rerun after cancellation, then checksummed I/O.
        w.channeling_box.setCurrentIndex(1);w.propagation_box.setCurrentIndex(0)
        w.start_emcd();idle();check(w.run_outcome=='completed','Restart succeeds')
        check(fingerprints(w.emcd_result)==before,'Restart scientific arrays unchanged')
        save_project(w.emcd_result,output/'restarted_project')
        loaded=load_project(output/'restarted_project')
        check(fingerprints(loaded)==before,'Restart project integrity')
        check(hashlib.sha256((output/'preserved_project'/'project.json').read_bytes()).hexdigest()==saved_hash,'Old project preserved')
        check(fingerprints(load_project(output/'preserved_project'))==before,'Old project arrays preserved')
        report['completed_solver_fingerprints']={'bloch':before}
        w.propagation_box.setCurrentIndex(1);w.start_emcd();idle()
        check(w.run_outcome=='completed','MS completes after cancellation')
        report['completed_solver_fingerprints']['fft-multislice']=fingerprints(w.emcd_result)
        save_project(w.emcd_result,output/'completed_ms_project')
        check(fingerprints(load_project(output/'completed_ms_project'))==fingerprints(w.emcd_result),'MS project integrity')
        report.update(outcome='PASS',restart='PASS',integrity='PASS',fingerprints=before,
            worst_idle_seconds=max(c['idle_seconds'] for c in report['cases'].values()))
        w.grab().save(str(output/'restarted.png'))
    except Exception:
        report['outcome']='FAIL';report['traceback']=traceback.format_exc()
    finally:
        if w.busy:w.cancel();idle()
        timer.stop();w.close();app.processEvents()
        (output/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if report.get('outcome')=='PASS' else 1
