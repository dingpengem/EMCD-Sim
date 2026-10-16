"""Opt-in native RC acceptance: actual widgets, workers, arrays and screenshots."""
from pathlib import Path
import json, time, hashlib, platform, sys, traceback
from dataclasses import replace
import numpy as np
from PySide6 import QtCore, QtWidgets
from .project_io import save_project, load_project
from .emcd_forward import export_result
from .runtime import build_info


def fingerprints(result):
    return {method+'__'+key: hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()
            for method,m in result['methods'].items()
            for key,value in dict(m['spectra'], coherence=m['coherence'], amplitudes=m['amplitudes'],
                **{e+'__'+k:v for e,fields in m['maps'].items() for k,v in fields.items()}).items()}


def run(output, source, reopen=False):
    from .app import MainWindow
    from .compare_results import CompareResults
    start=time.perf_counter();output=Path(output);output.mkdir(parents=True,exist_ok=True)
    app=QtWidgets.QApplication([]);w=MainWindow(workspace=output/'workspace');w.resize(1700,1050);w.show()
    report=dict(build=build_info(),platform=platform.platform(),timings={},cases={});errors=[]
    def error(message):
        errors.append(message);report['errors']=errors
        (output/'failure.json').write_text(json.dumps(report,indent=2),encoding='utf-8');app.exit(2)
    w.error=error
    sys.excepthook=lambda typ,value,tb:error(''.join(traceback.format_exception(typ,value,tb)))
    def idle(callback):
        if w.busy:QtCore.QTimer.singleShot(50,lambda:idle(callback))
        else:callback()
    def screenshot(name):w.grab().save(str(output/name))
    def finish():
        report['timings']['total_s']=time.perf_counter()-start
        try:
            import ctypes
            from ctypes import wintypes
            class Counters(ctypes.Structure):
                _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(k,ctypes.c_size_t) for k in ('peak_ws','ws','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile')]
            c=Counters();c.cb=ctypes.sizeof(c)
            ctypes.windll.kernel32.GetCurrentProcess.restype=wintypes.HANDLE
            get_memory=ctypes.windll.psapi.GetProcessMemoryInfo
            get_memory.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
            if not get_memory(ctypes.windll.kernel32.GetCurrentProcess(),ctypes.byref(c),c.cb):raise OSError('Process memory counter unavailable')
            report['peak_working_set_mib']=c.peak_ws/2**20
        except Exception as exc:report['memory_error']=str(exc)
        (output/('reopen.json' if reopen else 'acceptance.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
        w.close();app.quit()
    def reopened():
        export_root=output/'reopen_exports'/str(time.time_ns());export_root.mkdir(parents=True)
        previous=json.loads((output/'acceptance.json').read_text())
        t=time.perf_counter();r=load_project(output/'xmcd_both_project');report['timings']['open_s']=time.perf_counter()-t
        assert fingerprints(r)==previous['cases']['xmcd_both']['fingerprints']
        w.display_saved_result(r);w.use_result_settings();assert not w.busy
        second=load_project(output/'mistilt_project')
        # Simulate unavailable original sources through isolated saved copies;
        # never rename or remove the user's real scientific inputs.
        missing=dict(r)
        missing['config']=replace(r['config'],source=str(output/'unavailable/Ni_fm.xmcd'))
        missing['structure_snapshot']=dict(r['structure_snapshot'],source=str(output/'unavailable/Ni.cif'),sha256='0'*64)
        if not (output/'missing_sources_project').exists():save_project(missing,output/'missing_sources_project')
        from .project_io import rerun_reason
        unavailable=load_project(output/'missing_sources_project')
        assert rerun_reason(unavailable)
        w.display_saved_result(unavailable);w.use_result_settings()
        assert not w.emcd_button.isEnabled()
        export_result(unavailable,export_root/'missing_sources_export')
        report['missing_sources_view_export_rerun_blocked']=True
        widget=CompareResults(w,[('reference',r),('mistilt',second)])
        w.tabs.addTab(widget,'Saved comparison');w.tabs.setCurrentWidget(widget)
        widget.maximize()
        widget.figure.savefig(output/'saved_comparison.png');widget.figure.savefig(output/'saved_comparison.svg')
        export_result(r,export_root/'reopened_export')
        report['saved_arrays_exact']=True;report['reopen_without_worker']=w.worker is None
        QtCore.QTimer.singleShot(1000,lambda:(screenshot('stage_e_results_browser.png'),finish()))
    if reopen:
        QtCore.QTimer.singleShot(300,reopened)
    else:
        cases=[(model,method) for model in range(2) for method in range(3)]+[(0,2)]
        state={}
        def next_case():
            if not cases:
                before=w.emcd_result
                w.start_emcd();assert w.busy
                w.cancel()
                def cancelled():
                    def check():
                        assert w.emcd_result is before
                        report['cancelled_worker_preserved_previous_result']=True
                        finish()
                    idle(check)
                w.worker.finished.connect(cancelled)
                return
            model,method=cases.pop(0);mistilt=len(cases)==0
            w.model_box.setCurrentIndex(model);w.propagation_box.setCurrentIndex(method);w.reset_reference()
            if source:
                w.source_path.setText(str(source));w.validate_xmcd();w.declaration.setChecked(True)
            w.correction.setChecked(model==0)
            if mistilt:w.spin['tx'].setValue(w.spin['tx'].value()+1)
            state.update(key='mistilt' if mistilt else ('xmcd' if model==0 else 'atomic')+'_'+('bloch','fft-multislice','both')[method],start=time.perf_counter())
            w.start_emcd()
            if not w.busy:error('Calculation did not start: '+state['key'])
        def completed():
            def capture():
                if w.run_outcome!='completed':error('Calculation failed');return
                key=state['key'];r=w.emcd_result
                report['timings'][key+'_s']=time.perf_counter()-state['start']
                report['cases'][key]=dict(fingerprints=fingerprints(r),comparison=r['comparison'])
                export_result(r,output/key)
                t=time.perf_counter();save_project(r,output/(key+'_project'));report['timings'][key+'_save_s']=time.perf_counter()-t
                w.browser.registry.register(r,output/(key+'_project'),key);w.browser.refresh()
                if key=='xmcd_both':
                    w.tabs.setCurrentIndex(6);w.browser_dock.hide();w.overview_view.canvas.setMinimumSize(900,420);w.overview_view.maximize()
                    def grabbed():
                        screenshot('stage_e_bw_ms.png');w.browser_dock.show();w.overview_view.maximize();next_case()
                    QtCore.QTimer.singleShot(700,grabbed)
                else:QtCore.QTimer.singleShot(50,next_case)
            idle(capture)
        def preview_done():
            def after():
                report['timings']['preview_s']=time.perf_counter()-state['preview_start']
                screenshot('stage_e_main.png');next_case()
            idle(after)
        def begin():
            report['timings']['startup_to_window_s']=time.perf_counter()-start
            from matplotlib.backend_bases import MouseEvent
            from .geometry import za_from_tilt, excitation, Structure
            w.structure.atoms.write(output/'native_ni.cif')
            assert not Structure.from_cif(output/'native_ni.cif').elastic_reason
            w.mode.setCurrentIndex(1);w.canvas.draw()
            point=np.array([.25,.02]);x,y=w.ax.transData.transform(point)
            w.canvas.callbacks.process('button_press_event',MouseEvent('button_press_event',w.canvas,x,y,button=1))
            np.testing.assert_allclose(za_from_tilt(w.settings().tilt,200),point,atol=1e-9)
            w.reset_reference();w.mode.setCurrentIndex(0);w.canvas.draw()
            g=w.current[3][w.current[2].index((2,0,0))];x,y=w.ax.transData.transform(g)
            w.canvas.callbacks.process('button_press_event',MouseEvent('button_press_event',w.canvas,x,y,button=1))
            w.align();assert abs(excitation(g,w.settings().tilt,200))<1e-10
            report['native_cif_and_viewer_events']=True
            if source:
                w.source_path.setText(str(source));w.validate_xmcd();w.declaration.setChecked(True)
            w.propagation_box.setCurrentIndex(2);w.zone.setText('0 0 1');w.refresh()
            assert not w.emcd_button.isEnabled()
            w.reset_reference();w.spin['fft_grid'].setValue(13)
            assert not w.emcd_button.isEnabled()
            w.spin['fft_grid'].setValue(32)
            report['unsupported_orientation_and_odd_fft_blocked']=True
            w.reset_reference();state['preview_start']=time.perf_counter();w.start_preview()
        w.emcd_ready.connect(completed);w.preview_ready.connect(preview_done);QtCore.QTimer.singleShot(300,begin)
    QtCore.QTimer.singleShot(1200000,lambda:app.exit(3))
    return app.exec()
