"""External Qt controller for a fresh, unchanged published Cocoa application.

Launch contract is described in docs/MACOS_SC_DC_RESOURCE_BENCHMARK.md.
Only UI preferences are suppressed; no solver/resource functions are replaced.
"""
import csv, ctypes, hashlib, json, os, resource, shutil, time, traceback
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PySide6 import QtCore, QtWidgets
from emcd_sim.gui.runtime import build_info,resource_root
from emcd_sim.gui.memory_budget import memory_snapshot
from emcd_sim.gui.parallel_resources import native_backend_info
from emcd_sim.gui.project_io import fingerprints
from emcd_sim.gui.project_session import capture_configuration


def execute(app,w):
    out=Path(os.environ['EMCD_BENCHMARK_OUTPUT']);out.mkdir(parents=True,exist_ok=False)
    mode=os.environ.get('EMCD_BENCHMARK_MODE','bw-sc')
    request=os.environ.get('EMCD_BENCHMARK_WORKERS','1')
    limit=float(os.environ.get('EMCD_BENCHMARK_LIMIT_SECONDS','300'))
    report=dict(controller_version='native-event-loop-v2',case=mode,requested_workers=request,status='INCOMPLETE',build=build_info(),platform=app.platformName(),errors=[])
    lib=ctypes.CDLL(os.environ['EMCD_BENCHMARK_PROBE']);lib.emcd_probe_start.argtypes=[ctypes.c_char_p]
    lib.emcd_probe_start.restype=ctypes.c_int;lib.emcd_probe_stop.argtypes=[]
    sampling=False
    def write(): (out/'result.json').write_text(json.dumps(report,indent=2,default=str))
    def settle(ms=50):
        loop=QtCore.QEventLoop();QtCore.QTimer.singleShot(ms,loop.quit);loop.exec()
    def action(text):
        menu=next(a.menu() for a in w.menuBar().actions() if a.text()=='File')
        return next(a for a in menu.actions() if a.text()==text)
    def wait():
        end=time.monotonic()+60
        while w.busy and time.monotonic()<end:settle()
        assert not w.busy,'Project I/O timed out'
    def modal_check():
        for d in app.topLevelWidgets():
            if isinstance(d,QtWidgets.QMessageBox) and d.isVisible():
                report['errors'].append(d.windowTitle()+': '+d.text()+' '+d.informativeText());d.reject()
    timer=QtCore.QTimer();timer.timeout.connect(modal_check);timer.start(250)
    try:
        assert report['build']['commit']=='03dc8f8d1f0374984c9fc81866eaa32ce48008d0' and app.platformName()=='cocoa'
        w.store_ui_preferences=lambda:None
        seed=out/'seed-project';shutil.copytree(os.environ['EMCD_BENCHMARK_PROJECT'],seed)
        with patch.object(QtWidgets.QFileDialog,'getExistingDirectory',return_value=str(seed)):action('Open Project…').trigger()
        wait();assert w._accepted_global_mdff is not None
        w.propagation_box.setCurrentIndex(w.propagation_box.findData('fft-multislice') if mode.startswith('ms') else 0)
        # Some published controls use string labels rather than userData.
        if mode.startswith('ms'):
            idx=next(i for i in range(w.propagation_box.count()) if 'FFT' in w.propagation_box.itemText(i))
            w.propagation_box.setCurrentIndex(idx)
        w.channeling_box.setCurrentIndex(1 if mode.endswith('dc') else 0)
        w.worker_mode.setCurrentIndex(0 if request=='auto' else 1)
        if request!='auto':w.worker_count.setValue(int(request))
        w.memory_mode.setCurrentIndex(0 if request=='auto' else 1)
        if request!='auto':w.restore_memory_budget(int(os.environ.get('EMCD_BENCHMARK_BUDGET_MIB','1024')))
        diagnostic=os.environ.get('EMCD_BENCHMARK_DIAGNOSTIC')=='1'
        if diagnostic:
            w.energy_scope.setCurrentIndex(w.energy_scope.findData('selected'))
            if w.energy_scope.currentIndex()<0:
                w.energy_scope.setCurrentIndex(next(i for i in range(w.energy_scope.count()) if 'Selected' in w.energy_scope.itemText(i)))
            w.angular_maps.setChecked(False)
        w.emcd_stale();settle(300)
        cfg=w.forward_settings();settings=w.settings()
        assert len(w.structure.atoms)==4 and np.allclose(w.structure.atoms.cell.lengths(),3.520,atol=1e-12,rtol=0)
        assert w.structure.sha256==hashlib.sha256((resource_root()/'examples/Ni_FCC_a3.52.cif').read_bytes()).hexdigest()
        assert cfg.source_sha256==hashlib.sha256((resource_root()/'data/wien2k_ni/Ni_fm.xmcd').read_bytes()).hexdigest()
        report['input_identity']=dict(cif_sha256=w.structure.sha256,xmcd_sha256=cfg.source_sha256)
        assert cfg.grid==97 and cfg.depth==64 and cfg.subpixels==64 and cfg.energy_points==241
        assert cfg.propagation==('fft-multislice' if mode.startswith('ms') else 'bloch')
        assert cfg.channeling_model==('double' if mode.endswith('dc') else 'single')
        report.update(diagnostic=diagnostic,settings=asdict(settings),configuration=asdict(cfg),hardware=w.startup_resources['hardware'],environment_before=memory_snapshot(),blas_before=native_backend_info(),preview=w.resource_panel.preview)
        write()
        if os.environ.get('EMCD_BENCHMARK_MATRIX')=='1':
            from dataclasses import replace
            from emcd_sim.gui.propagation import numerical_info,resolve_fft_configuration
            from emcd_sim.gui.macos_resources import auto_memory_budget
            matrix=[]
            for backend in ('bloch','fft-multislice'):
                for channel in ('single','double'):
                    for count in (1,2,4,6,8,'auto'):
                        mode_cfg=replace(cfg,propagation=backend,channeling_model=channel,
                            worker_mode='automatic' if count=='auto' else 'manual',
                            parallel_workers=1 if count=='auto' else count,
                            memory_budget_mib=auto_memory_budget()['effective_budget_mib'] if count=='auto' else 1024)
                        mode_cfg=resolve_fft_configuration(w.structure,settings,mode_cfg)
                        begin=time.perf_counter()
                        info=numerical_info(w.structure,settings,mode_cfg,enforce_execution=False)
                        matrix.append(dict(backend=backend,channeling=channel,request=count,
                            assessment_seconds=time.perf_counter()-begin,info=info))
            (out/'preflight-matrix.json').write_text(json.dumps(matrix,indent=2,default=str))
        if os.environ.get('EMCD_BENCHMARK_PREFLIGHT_ONLY')=='1':
            report.update(status='PREFLIGHT',admission_text=w.memory_label.text());return
        if not w.emcd_button.isEnabled():
            report.update(status='REJECTED',admission_text=w.memory_label.text());return
        w.browser.table.clearSelection();w.browser.selection_timer.stop()
        report['baseline']=memory_snapshot();report['lifetime_peak_before_mib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20
        assert lib.emcd_probe_start(os.fsencode(out/'native-memory.csv'))==0;sampling=True
        started=time.perf_counter();w.start_emcd();assert w.busy,'Run did not start'
        def scientific_result(result):
            report['scientific_result_monotonic']=time.clock_gettime(time.CLOCK_MONOTONIC)
            report['blas_during']=native_backend_info()
        w.worker.result.connect(scientific_result,QtCore.Qt.ConnectionType.DirectConnection)
        report['admission_and_start_seconds']=time.perf_counter()-started
        report['final_resources']=w.resource_panel.finalized
        last=0;cancelled=False
        while w.busy:
            settle(25);elapsed=time.perf_counter()-started
            if elapsed-last>2:
                stage=getattr(w,'_emcd_stage_text','')
                (out/'progress.json').write_text(json.dumps(dict(elapsed_seconds=elapsed,stage=stage)))
                last=elapsed
            if elapsed>limit and not cancelled:
                report['bounded_stop_seconds']=elapsed;report['bounded_stop_stage']=getattr(w,'_emcd_stage_text','');w.cancel();cancelled=True
        report['run_and_display_seconds']=time.perf_counter()-started
        lib.emcd_probe_stop();sampling=False
        report.update(outcome=w.run_outcome,environment_after=memory_snapshot(),lifetime_peak_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20,blas_after=native_backend_info())
        rows=list(csv.DictReader((out/'native-memory.csv').open()))
        rss=np.array([int(r['rss_bytes'])/2**20 for r in rows]);foot=np.array([int(r['footprint_bytes'])/2**20 for r in rows]);times=np.array([float(r['monotonic_seconds']) for r in rows])
        class Timebase(ctypes.Structure):_fields_=[('numer',ctypes.c_uint32),('denom',ctypes.c_uint32)]
        tb=Timebase();system=ctypes.CDLL('/usr/lib/libSystem.B.dylib');system.mach_timebase_info(ctypes.byref(tb))
        report['cpu_counter_units']=dict(raw='Mach absolute ticks; early trial CSV labels said nanoseconds but were raw ticks',nanoseconds_per_tick=tb.numer/tb.denom,timebase_numer=tb.numer,timebase_denom=tb.denom)
        cpu=(int(rows[-1].get('user_ticks',rows[-1].get('user_nanoseconds')))+int(rows[-1].get('system_ticks',rows[-1].get('system_nanoseconds')))-int(rows[0].get('user_ticks',rows[0].get('user_nanoseconds')))-int(rows[0].get('system_ticks',rows[0].get('system_nanoseconds'))))*tb.numer/tb.denom/1e9
        report['measurement']=dict(sample_count=len(rows),first_rss_mib=float(rss[0]),peak_rss_mib=float(rss.max()),incremental_rss_mib=float(rss.max()-rss[0]),first_footprint_mib=float(foot[0]),peak_footprint_mib=float(foot.max()),process_cpu_seconds=cpu,average_logical_cpus=cpu/(times[-1]-times[0]),sample_interval_min_seconds=float(np.min(np.diff(times))),sample_interval_max_seconds=float(np.max(np.diff(times))))
        if cancelled:return
        if w.run_outcome!='completed':
            report['status']='FAIL';return
        r=w.emcd_result;s=r['spectra'];energy=s['energy_ev'];diags=r['metadata']['angular_evaluation']
        end=report['scientific_result_monotonic'];begin=end-r['metadata']['calculation_seconds']
        science=(times>=begin)&(times<=end);assert science.any()
        report['measurement'].update(scientific_peak_rss_mib=float(rss[science].max()),scientific_peak_footprint_mib=float(foot[science].max()),scientific_incremental_rss_mib=float(rss[science].max()-rss[0]),scientific_samples=int(science.sum()))
        expected=2 if diagnostic else 243
        assert len(energy)==expected and np.all(np.diff(energy)>0)
        if not diagnostic:np.testing.assert_array_equal(energy,np.unique(np.r_[np.linspace(823.625,882.521,241),831.271,848.698]))
        assert 831.271 in energy and 848.698 in energy
        for key,a in s.items():
            if isinstance(a,np.ndarray):assert a.shape==(expected,) and np.isfinite(a).all(),key
        scale=max(float(s['I_A_plus'].max()),float(s['I_B_plus'].max()))
        for d in ('A','B'):
            assert np.min(s[f'I_{d}_plus'])>=-scale*1e-12 and np.min(s[f'I_{d}_minus'])>=-scale*1e-12
            np.testing.assert_allclose(s[f'N_{d}'],(s[f'I_{d}_plus']+s[f'I_{d}_minus'])/2,rtol=1e-12,atol=scale*1e-14)
            np.testing.assert_allclose(s[f'M_{d}'],(s[f'I_{d}_plus']-s[f'I_{d}_minus'])/2,rtol=1e-12,atol=scale*1e-14)
        np.testing.assert_allclose(s['D_raw'],s['D_mag']+s['D_nonmag'],rtol=1e-10,atol=scale*1e-13)
        assert len(diags)==expected and all(d['evaluated_pixels']>0 and not d['checkpoint_reused'] for d in diags)
        assert r['qx'].shape==r['qy'].shape==(97,97)
        np.testing.assert_allclose(r['qx'][0],np.linspace(-1,1,97),atol=1e-15,rtol=0)
        np.testing.assert_allclose(r['qy'][:,0],np.linspace(-1,1,97),atol=1e-15,rtol=0)
        if not diagnostic:
            assert set(r['maps'])=={'L3','L2'}
            assert sum(d['full_field'] for d in diags)==2
            for edge,m in r['maps'].items():
                for name in ('I_plus','I_minus','I_mag','I_nonmag'):assert m[name].shape==(97,97) and np.isfinite(m[name]).all()
                ie=int(np.where(energy==({'L3':831.271,'L2':848.698}[edge]))[0][0]);dq2=(2/96)**2
                for state in ('plus','minus'):
                    for det in ('A','B'):
                        value=float(np.sum(m['I_'+state]*r['weights'][det])*dq2)
                        np.testing.assert_allclose(value,s[f'I_{det}_{state}'][ie],rtol=1e-11,atol=scale*1e-13)
        # Store local arrays for cross-worker checks; not committed.
        arrays={f'spectrum__{k}':v for k,v in s.items() if isinstance(v,np.ndarray)}
        for edge,m in r['maps'].items():
            for k in ('I_plus','I_minus','I_mag','I_nonmag'):arrays[f'{edge}__{k}']=m[k]
        np.savez_compressed(out/'numerical-arrays.npz',**arrays)
        report.update(calculation_seconds=r['metadata']['calculation_seconds'],metadata=r['metadata'],numeric_checks='PASS',actual_energies=len(energy),map_shape=[97,97] if r['maps'] else None)
        before=fingerprints(r);state=capture_configuration(w)
        with patch.object(QtWidgets.QFileDialog,'getSaveFileName',return_value=(str(out/'project'),'')):action('Save As…').trigger()
        wait();action('Close Project').trigger();settle()
        with patch.object(QtWidgets.QFileDialog,'getExistingDirectory',return_value=str(out/'project')):action('Open Project…').trigger()
        wait();assert fingerprints(w.emcd_result)==before
        assert asdict(capture_configuration(w)['settings'])==asdict(state['settings'])
        from emcd_sim.gui.multisite_run import configuration_equal
        assert configuration_equal(capture_configuration(w)['config'],state['config'])
        restored=capture_configuration(w)['config']
        assert restored.provider_declaration==state['config'].provider_declaration
        assert w.worker_mode.currentIndex()==(0 if request=='auto' else 1)
        assert w.memory_mode.currentIndex()==(0 if request=='auto' else 1)
        if request!='auto':
            assert w.worker_count.value()==int(request) and w.memory_budget.currentData()==1024
        assert w.structure.sha256==report['input_identity']['cif_sha256']
        report.update(project_restore='PASS',status='PASS')
    except Exception:
        report['status']='FAIL';report['exception']=traceback.format_exc()
    finally:
        if sampling:lib.emcd_probe_stop()
        write();(out/'finished.json').write_text(json.dumps({'status':report['status']}));timer.stop()
        if w.busy:
            w.cancel()
            while w.busy:settle()
        w.project_dirty=False;w.close();app.quit()


def await_window():
    app=QtWidgets.QApplication.instance()
    windows=[] if app is None else [w for w in app.topLevelWidgets() if type(w).__name__=='MainWindow' and w.isVisible() and hasattr(w,'emcd_button')]
    if windows:execute(app,windows[0])
    else:QtCore.QTimer.singleShot(500,await_window)
QtCore.QTimer.singleShot(500,await_window)
