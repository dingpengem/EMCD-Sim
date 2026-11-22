"""Bounded packaged GUI memory matrix; native RSS/footprint, real workers."""
import ctypes,gc,json,os,subprocess,threading,time,traceback
from pathlib import Path
import numpy as np
from PySide6 import QtWidgets


def run(output):
    from emcd_sim.gui.app import MainWindow
    from emcd_sim.memory_budget import memory_snapshot,assess_memory
    from emcd_sim.provenance import build_info
    from emcd_sim.gui.project_io import save_project,load_project,fingerprints
    from emcd_sim.gui.result_export import export_result
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w=MainWindow(output/'workspace');w.show()
    report=dict(build=build_info(),pid=os.getpid(),cases=[],errors=[],snapshots=[],
        worker_model='QThread calculation and ThreadPoolExecutor detector threads in one process; no worker processes',
        sample_interval_seconds=.2,tree_rss_semantics='Conservative sum; shared pages can be counted more than once',
        native_platform=app.platformName(),dpr=w.devicePixelRatioF())
    state={'phase':'startup','case':'idle'};stop=threading.Event();samples=[]
    class Usage(ctypes.Structure):
        _fields_=[('uuid',ctypes.c_uint8*16)]+[(n,ctypes.c_uint64) for n in ('user','system','wakeups','interrupts','pageins','wired','resident','footprint','start','exit')]
    lib=ctypes.CDLL('/usr/lib/libproc.dylib');lib.proc_pid_rusage.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_void_p]
    def sample():
        while not stop.is_set():
            t=time.monotonic();row=dict(t=t,**state);usage=Usage()
            if lib.proc_pid_rusage(os.getpid(),0,ctypes.byref(usage))==0:
                row.update(parent_rss_mib=usage.resident/2**20,parent_footprint_mib=usage.footprint/2**20)
            # Discover the full descendant tree, including transient children.
            try:
                probe=subprocess.Popen(['/bin/ps','-axo','pid=,ppid=,rss='],stdout=subprocess.PIPE,text=True)
                raw=probe.communicate(timeout=2)[0]
                rows=[tuple(map(int,line.split())) for line in raw.splitlines()]
                pids={os.getpid()}
                for _ in range(8):
                    new=pids|{pid for pid,ppid,rss in rows if ppid in pids}
                    if new==pids:break
                    pids=new
                # ps itself is measurement overhead, not an app worker.
                children=[dict(pid=pid,rss_mib=rss/1024) for pid,ppid,rss in rows if pid in pids and pid not in (os.getpid(),probe.pid)]
                row.update(descendants=children,tree_rss_mib=row.get('parent_rss_mib',0)+sum(c['rss_mib'] for c in children))
            except Exception as exc:row['sampling_error']=str(exc)
            row['sampling_seconds']=time.monotonic()-t;samples.append(row)
            stop.wait(max(0,.2-(time.monotonic()-t)))
    thread=threading.Thread(target=sample,daemon=True);thread.start()
    def settle(seconds=.5):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:app.processEvents();time.sleep(.01)
    def wait():
        deadline=time.monotonic()+120
        while w.busy or (w.worker is not None and w.worker.isRunning()):
            app.processEvents();time.sleep(.005)
            if time.monotonic()>deadline:
                w.cancel();raise TimeoutError('Memory case timed out')
        settle(.25)
    w.error=lambda message:report['errors'].append(str(message))
    def configure(method,channel,mode,workers,larger=False):
        w.numerical_mode.setCurrentIndex(1)
        w.set_values(dict(thickness=1,beam=1.5 if larger else .9,potential=2 if larger else 1.8,
            grid=17 if larger else 9,depth=17 if larger else 9,energy=9,subpixels=8,
            fft_grid=48 if larger else 24,slice_step=.2,halfwidth=.7,radius=.12))
        w.zone.setText('0 0 1');w.target.setText('2 0 0');w.apply_orientation()
        w.propagation_box.setCurrentIndex(method);w.channeling_box.setCurrentIndex(channel)
        w.energy_scope.setCurrentIndex(w.energy_scope.findData('edges'));w.angular_maps.setChecked(True)
        w.worker_mode.setCurrentIndex(mode);w.worker_count.setValue(workers)
        w.memory_mode.setCurrentIndex(mode);w.memory_budget.setValue(2048)
        w.model_box.setCurrentIndex(0);w.validate_xmcd(show_error=False)
        w.reference_ni.setChecked(True);w.declaration.setChecked(True)
        w.show_structure_viewer()
        assert w.mdff_dialog.apply_configuration() is not None,w.mdff_dialog.status.text()
        w.structure_viewer.apply_groups();w.refresh();settle(.1)
    def calculate(label):
        state.update(case=label,phase='preparation');begin=len(samples);start=time.monotonic()
        info=w.compute_resources.info
        assert info is not None,w.compute_resources.estimate.text()
        record=dict(name=label,request=w.compute_resources.settings(),estimate=info,started=start)
        if info['execution']['blocked']:
            record.update(verdict='EXPECTED REJECTION' if w.channeling_box.currentIndex()==0 and w.worker_count.value()==2 else 'BLOCKED',elapsed=0)
            assert record['verdict']=='EXPECTED REJECTION',info
            report['cases'].append(record);return
        assert w.emcd_button.isEnabled(),w.emcd_button.toolTip()
        w.start_emcd();assert w.busy
        w.worker.stage.connect(lambda text:state.update(phase=str(text)))
        wait();assert w.run_outcome=='completed',report['errors']
        state['phase']='completed steady state';settle(.5)
        record.update(verdict='PASS',elapsed=time.monotonic()-start,execution=w.emcd_result['metadata']['execution'],
            memory_after=memory_snapshot(),samples=[begin,len(samples)])
        report['cases'].append(record)
    try:
        settle(1);report['idle']=memory_snapshot();report['snapshots'].append(report['idle'])
        report['safe_boundary_rejection']=assess_memory(1,1,reject=False)
        assert report['safe_boundary_rejection']['rejected']
        report['safe_boundary_admission']=assess_memory(1,2048)
        for method in (0,1):
            for channel in (0,1):
                for mode,workers in ((0,1),(1,1),(1,2)):
                    configure(method,channel,mode,workers)
                    calculate(f'{method}_{channel}_{mode}_{workers}')
        configure(1,1,1,2,True);calculate('larger_MS_double_2')
        # Reuse selected run through the supported replacement behavior.
        configure(0,0,1,1)
        report['repeated']=[]
        for i in range(10):
            calculate('repeat_'+str(i));gc.collect();settle(.3)
            report['repeated'].append(dict(index=i,**memory_snapshot(),registry_count=len(w.browser.registry.records)))
            if i in (2,7):
                dest=output/('roundtrip_'+str(i));before=fingerprints(w.emcd_result)
                save_project(w.emcd_result,dest);opened=load_project(dest)
                assert fingerprints(opened)==before
                w.display_saved_result(opened);w.use_result_settings()
                export_result(opened,output/('exports_'+str(i)))
        report['final']=memory_snapshot();report['complete']=True
    except Exception:report['errors'].append(traceback.format_exc());report['complete']=False
    finally:
        state['phase']='shutdown'
        if w.busy:w.cancel();wait()
        w.project_dirty=False
        for dialog in w.dialogs:dialog.close()
        w.mdff_dialog.close();w.close();settle(.5);stop.set();thread.join(2)
        (output/'samples.json').write_text(json.dumps(samples,indent=2))
        for record in report['cases']:
            if 'samples' not in record:continue
            a,b=record['samples'];subset=samples[a:b]
            record['peaks']={k:max((s.get(k,0) for s in subset),default=0) for k in ('parent_rss_mib','parent_footprint_mib','tree_rss_mib')}
        report['sampling_overhead_peak_seconds']=max((s['sampling_seconds'] for s in samples),default=0)
        report['closed_cleanly']=not w.isVisible() and not w.busy
        (output/'acceptance.json').write_text(json.dumps(report,indent=2,default=str))
    return 0 if report.get('complete') and not report['errors'] else 2
