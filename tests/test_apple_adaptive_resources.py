"""Apple policy boundaries, project compatibility and explicit user controls."""
from dataclasses import replace
from unittest.mock import patch
import sys
import pytest
from emcd_sim.gui import macos_resources as mac
from emcd_sim.gui.memory_budget import assess_memory
from emcd_sim.gui.parallel_resources import worker_plan
from emcd_sim.gui.geometry import Settings
from emcd_sim.gui.emcd_forward import ForwardSettings

HW=dict(logical_cores=10,performance_cores=6,efficiency_cores=4,physical_memory_mib=16384)
NATIVE=dict(platform='darwin',cpu_count=10,hardware=HW,backend='Accelerate',version='test',
            threads=1,automatic_thread_control=True)
SNAP=dict(physical_memory_mib=16384.,available_ram_mib=8192.,process_rss_mib=400.,memory_pressure='normal',swap_used_mib=0.)


def test_named_core_discovery_does_not_guess_from_chip_name(monkeypatch):
    values={'hw.logicalcpu':10,'hw.memsize':16*2**30,'hw.nperflevels':2,
        'hw.perflevel0.name':'Efficiency','hw.perflevel0.logicalcpu':4,
        'hw.perflevel1.name':'Performance','hw.perflevel1.logicalcpu':6,'machdep.cpu.brand_string':'Unspecified Apple chip'}
    monkeypatch.setattr(mac,'_read',lambda name,kind='integer':values.get(name));mac.hardware_info.cache_clear()
    try:
        hw=mac.hardware_info();assert hw['performance_cores']==6 and hw['efficiency_cores']==4
        assert hw['physical_memory_mib']==16384
        values['hw.perflevel1.name']='Unidentified';mac.hardware_info.cache_clear()
        assert mac.hardware_info()['performance_cores'] is None
    finally:mac.hardware_info.cache_clear()


def test_mac_manual_range_exceeds_four_but_not_detected_hardware(monkeypatch):
    monkeypatch.setattr(mac.sys,'platform','darwin')
    cfg=ForwardSettings(channeling_model='double',worker_mode='manual',parallel_workers=8)
    plan=worker_plan(Settings(),cfg,21,native=NATIVE)
    assert plan['effective_workers']=={'bloch':8} and not plan['blocked']
    with pytest.raises(ValueError,match='1 to 10'):
        worker_plan(Settings(),replace(cfg,parallel_workers=11),21,native=NATIVE)
    single=worker_plan(Settings(),replace(cfg,channeling_model='single'),21,native=NATIVE)
    assert single['blocked'] and single['effective_workers']=={'bloch':1}


def test_auto_uses_work_and_p_cores_not_every_logical_core(monkeypatch):
    monkeypatch.setattr(mac.sys,'platform','darwin')
    cfg=ForwardSettings(channeling_model='double',grid=97,depth=64,energy_points=2)
    small=worker_plan(Settings(),replace(cfg,grid=9,angular_maps=False),2,native=NATIVE)
    large=worker_plan(Settings(),cfg,61,native=NATIVE)
    assert small['effective_workers']=={'bloch':1}
    assert large['effective_workers']=={'bloch':6}
    assert large['adaptive']['bloch']['cpu_capacity']==6
    unknown=dict(HW,performance_cores=None,efficiency_cores=None)
    count,details=mac.adaptive_worker_count(Settings(),cfg,61,unknown)
    assert count<=5 and details['cpu_capacity']==5


def test_auto_budget_pressure_reserve_and_manual_value(monkeypatch):
    monkeypatch.setattr(mac.sys,'platform','darwin')
    normal=mac.auto_memory_budget(SNAP)
    warning=mac.auto_memory_budget(dict(SNAP,memory_pressure='warning',swap_used_mib=1500))
    assert 0<warning['effective_budget_mib']<normal['effective_budget_mib']<8192
    assert normal['system_reserve_mib']>=1024
    assert assess_memory(1,777,snapshot=SNAP)['memory_budget_mib']==777
    critical=dict(SNAP,memory_pressure='critical')
    assert mac.auto_memory_budget(critical)['admission_rejected']
    with pytest.raises(ValueError,match='critical memory pressure'):assess_memory(1,2048,snapshot=critical)
    monkeypatch.setattr(mac,'hardware_info',lambda:dict(physical_memory_mib=None))
    with pytest.raises(ValueError,match='could not be determined'):
        mac.auto_memory_budget({k:v for k,v in SNAP.items() if k!='physical_memory_mib'})


def test_resource_changes_do_not_stale_scientific_results():
    from emcd_sim.gui.multisite_run import configuration_equal
    cfg=ForwardSettings()
    assert configuration_equal(cfg,replace(cfg,parallel_workers=8,worker_mode='manual',memory_budget_mib=777))
    assert not configuration_equal(cfg,replace(cfg,grid=17))


@pytest.mark.skipif(sys.platform!='darwin',reason='Mac Auto memory UI')
def test_auto_controls_and_resolved_budgets_round_trip(tmp_path,monkeypatch):
    from PySide6 import QtWidgets
    from emcd_sim.gui.app import MainWindow
    from test_material_mdff_workflow import xmcd_draft
    from emcd_sim.gui.project_session import capture_configuration,restore_configuration
    from emcd_sim.gui.project_configuration import save_configuration,load_configuration
    application=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setattr('emcd_sim.gui.memory_budget.memory_snapshot',lambda:dict(SNAP))
    w=MainWindow(tmp_path/'workspace');w.store_ui_preferences=lambda:None
    try:
        v=xmcd_draft(w);assert w.mdff_dialog.apply_configuration() is not None;v.apply_groups()
        assert w.memory_mode.currentIndex()==0 and not w.memory_budget.isEnabled()
        budget=w.resource_budget();assert budget==mac.auto_memory_budget(SNAP)['effective_budget_mib']
        state=capture_configuration(w);assert state['config'].memory_budget_mib==2048
        save_configuration(state,tmp_path/'saved');restored=load_configuration(tmp_path/'saved')
        w.memory_mode.setCurrentIndex(1);w.worker_mode.setCurrentIndex(1)
        restore_configuration(w,restored)
        assert w.memory_mode.currentIndex()==0 and w.worker_mode.currentIndex()==0
        assert w.resource_budget()==budget
        w.memory_mode.setCurrentIndex(1);w.restore_memory_budget(777)
        assert w.resource_budget()==777 and w.memory_budget.currentData()==777
        # Simulate moving a saved request from a larger Mac to a smaller one.
        w.restore_worker_request('manual',64)
        state=capture_configuration(w)
        from emcd_sim.gui import parallel_resources
        monkeypatch.setattr(parallel_resources,'MAX_WORKERS',4)
        restore_configuration(w,state)
        assert w.worker_mode.currentIndex()==1 and w.worker_count.value()==64
        assert w.memory_mode.currentIndex()==1 and w.resource_budget()==777
        state['config']=replace(state['config'],worker_mode='automatic')
        restore_configuration(w,state)
        assert w.worker_mode.currentIndex()==0 and w.worker_count.value()==64
    finally:
        w.project_dirty=False;w.close();w.deleteLater();application.processEvents()
