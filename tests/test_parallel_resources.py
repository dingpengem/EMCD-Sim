"""No-solver preflight, persisted worker settings and resource safety."""
from dataclasses import replace,asdict
from types import SimpleNamespace
from unittest.mock import Mock,patch
import json
import pytest
from PySide6 import QtWidgets
from emcd_sim.gui.geometry import Settings,Structure
from emcd_sim.gui.emcd_forward import ForwardSettings
from emcd_sim.gui.parallel_resources import worker_plan,IMPLICATED_DLL_SHA256,native_backend_info
from emcd_sim.gui.propagation import numerical_info
from emcd_sim.gui.project_io import config_from_dict


def native(threads=12):
    return dict(backend='OpenBLAS',version='tested',threads=threads,sha256=IMPLICATED_DLL_SHA256,
        platform='win32',numpy_version='2.4.6',cpu_count=12,machine='AMD64')


def primary():return replace(Settings(),thickness=8,tilt=(-7.11672544,0))


@pytest.mark.parametrize('method',['bloch','fft-multislice','both'])
@pytest.mark.parametrize('channel',['single','double'])
def test_automatic_counts(method,channel):
    cfg=replace(ForwardSettings(),propagation=method,channeling_model=channel)
    plan=worker_plan(primary(),cfg,27,native=native())
    assert not plan['blocked']
    for key,value in plan['effective_workers'].items():
        assert value==(4 if key=='fft-multislice' and channel=='double' else 1)


def test_known_unsafe_is_evidence_scoped_not_cutoff_rule():
    cfg=replace(ForwardSettings(),channeling_model='double',worker_mode='manual',parallel_workers=4)
    assert worker_plan(primary(),cfg,27,native=native())['risk']=='KNOWN UNSAFE'
    assert worker_plan(replace(primary(),beam_cutoff=2.5),cfg,21,native=native())['risk']=='UNVERIFIED COMBINATION'
    p=worker_plan(primary(),cfg,27,native=native(1))
    assert p['effective_workers']=={'bloch':4} and not p['blocked']
    p=worker_plan(primary(),cfg,27,native=native(None));assert p['blocked'] and p['risk']!='VALIDATED POLICY'
    assert not worker_plan(primary(),replace(cfg,parallel_workers=1),27,native=native(None))['blocked']


@pytest.mark.parametrize('count',[0,5,1.5,True])
def test_invalid_manual_count_never_clamped(count):
    with pytest.raises(ValueError):worker_plan(primary(),replace(ForwardSettings(),worker_mode='manual',parallel_workers=count),27,native=native())


def test_single_has_no_detector_parallelism_and_both_retains_request():
    cfg=replace(ForwardSettings(),worker_mode='manual',parallel_workers=4)
    assert worker_plan(primary(),cfg,27,native=native(1))['blocked']
    p=worker_plan(primary(),replace(cfg,channeling_model='double',propagation='both'),27,native=native())
    assert p['blocked'] and p['effective_workers']=={'bloch':4,'fft-multislice':4}


def test_backend_unknown_is_not_guessed_from_cpu(monkeypatch):
    import emcd_sim.gui.parallel_resources as module
    monkeypatch.setattr(module,'_numpy_blas',lambda:None)
    with patch.dict('sys.modules',{'threadpoolctl':None}):value=module.native_backend_info()
    assert value['backend']=='Unknown' and value['threads'] is None


def test_introspection_is_read_only_and_queries_actual_threads(monkeypatch):
    import emcd_sim.gui.parallel_resources as module
    count=[1];getter=Mock(side_effect=lambda:count[0])
    monkeypatch.setattr(module,'_numpy_blas',lambda:(object(),getter,dict(backend='OpenBLAS',version='test')))
    assert native_backend_info()['threads']==1
    count[0]=12;assert native_backend_info()['threads']==12 and getter.call_count==2


def test_memory_uses_actual_manual_concurrency_and_rejects_without_reduction(monkeypatch):
    import emcd_sim.gui.parallel_resources as module
    monkeypatch.setattr(module,'native_backend_info',lambda:native(1))
    monkeypatch.setattr('emcd_sim.gui.memory_budget.memory_snapshot',lambda:dict(available_ram_mib=32768,process_rss_mib=120))
    cfg=replace(ForwardSettings(),channeling_model='double',worker_mode='manual',parallel_workers=1)
    one=numerical_info(Structure.nickel(),primary(),cfg)
    four=numerical_info(Structure.nickel(),primary(),replace(cfg,parallel_workers=4))
    assert one['bw_beams']==four['bw_beams']==27
    assert four['estimated_process_peak_mib']>one['estimated_process_peak_mib']
    rejected=numerical_info(Structure.nickel(),primary(),replace(cfg,parallel_workers=4,memory_budget_mib=512),enforce_execution=False)
    assert rejected['execution']['risk']=='RESOURCE REJECTED' and rejected['execution']['effective_workers']['bloch']==4


def test_legacy_configuration_defaults_workers_without_overwriting_values():
    old=dict(model='atomic',grid=33,fft_grid=48,depth=129,slice_step=.025,memory_budget_mib=512)
    cfg=config_from_dict(old)
    assert cfg.worker_mode=='automatic' and cfg.parallel_workers==1
    for key,value in old.items():assert getattr(cfg,key)==value
    cfg=replace(cfg,worker_mode='manual',parallel_workers=3)
    assert config_from_dict(json.loads(json.dumps(asdict(cfg))))==cfg


def test_automatic_ms_reduces_only_workers_to_fit_ram(monkeypatch):
    monkeypatch.setattr('emcd_sim.gui.parallel_resources.native_backend_info',lambda:native(1))
    monkeypatch.setattr('emcd_sim.gui.memory_budget.memory_snapshot',lambda:dict(available_ram_mib=16384,process_rss_mib=64))
    cfg=replace(ForwardSettings(),propagation='fft-multislice',channeling_model='double',fft_grid=128,memory_budget_mib=512)
    info=numerical_info(Structure.nickel(),primary(),cfg)
    assert 1<=info['execution']['effective_workers']['fft-multislice']<4
    assert cfg.fft_grid==128 and cfg.depth==64
    manual=numerical_info(Structure.nickel(),primary(),replace(cfg,worker_mode='manual',parallel_workers=4),enforce_execution=False)
    assert manual['execution']['blocked'] and manual['execution']['effective_workers']['fft-multislice']==4


def test_execution_plan_change_rejected_before_solver(monkeypatch):
    from emcd_sim.gui import emcd_forward
    monkeypatch.setattr('emcd_sim.gui.parallel_resources.native_backend_info',lambda:native(1))
    solve=Mock();monkeypatch.setattr(emcd_forward,'_calculate',solve)
    cfg=replace(ForwardSettings(),model='atomic',channeling_model='double')
    with pytest.raises(ValueError,match='Resources changed'):
        emcd_forward.calculate(Structure.nickel(),primary(),cfg,execution_policy={'effective_workers':{'bloch':4}})
    assert not solve.called


def test_gui_defaults_worker_independence_and_blocked_run(tmp_path,monkeypatch):
    from emcd_sim.gui.app import MainWindow
    import emcd_sim.gui.parallel_resources as module
    monkeypatch.setattr(module,'native_backend_info',lambda:native())
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    with patch('numpy.linalg.eigh',side_effect=AssertionError('Preflight must not solve')),patch('emcd_sim.gui.stage_b.EMCDWorker') as factory:
        w=MainWindow(workspace=tmp_path/'workspace')
        try:
            w.model_box.setCurrentIndex(1);w.channeling_box.setCurrentIndex(1)
            assert (w.settings().voltage,w.settings().beam_cutoff,w.settings().potential_cutoff)==(300,3,2)
            assert w.settings()==Settings()
            assert w.spin['grid'].value()==97 and w.memory_budget.currentData()==2048
            assert not w.shared_resources_group.isHidden()
            original=w.numerical_snapshot();w.worker_mode.setCurrentIndex(1);w.worker_count.setValue(4)
            assert w.numerical_snapshot()==original and not w.emcd_button.isEnabled()
            errors=[];w.error=errors.append;w.start_emcd();assert errors and not factory.called and not w.busy
            w.worker_mode.setCurrentIndex(0);assert w.worker_count.value()==4
            w.numerical_mode.setCurrentIndex(1);w.spin['beam'].setValue(2.5)
            assert 'Retained beams: 21' in w.memory_label.text()
            w.spin['kv'].setValue(200);assert 'Voltage: 200' in w.memory_label.text()
            w.new_project()
            assert w.settings().voltage==300 and w.settings().beam_cutoff==3 and w.worker_mode.currentIndex()==0
        finally:w.close();app.processEvents()


def test_unsupported_saved_worker_request_is_not_clamped(tmp_path):
    from emcd_sim.gui.app import MainWindow
    from emcd_sim.gui.project_io import load_project
    from pathlib import Path
    fixture=Path('outputs/v060_release/source_native/single_both_project')
    if not fixture.exists():pytest.skip('Optional saved result fixture unavailable')
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w=MainWindow(workspace=tmp_path/'workspace');errors=[];w.error=errors.append
    try:
        saved=load_project(fixture);saved['config']=replace(saved['config'],worker_mode='manual',parallel_workers=5)
        old=w.settings();w.emcd_result=saved;w.use_result_settings()
        assert errors and 'not replaced or clamped' in errors[0] and w.settings()==old
        assert saved['config'].parallel_workers==5
    finally:w.close();app.processEvents()


def test_concurrent_native_ram_queries_are_well_typed():
    from concurrent.futures import ThreadPoolExecutor
    from emcd_sim.gui.memory_budget import memory_snapshot
    with ThreadPoolExecutor(max_workers=4) as pool:
        snapshots=list(pool.map(lambda _:memory_snapshot(),range(32)))
    assert all(s['available_ram_mib']>0 and s['process_rss_mib']>=0 for s in snapshots)
