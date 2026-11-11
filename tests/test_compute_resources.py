"""Windows allocation policy/GUI tests; simulated machines are not native PCs."""
from dataclasses import replace
from types import SimpleNamespace
import numpy as np
import pytest

from emcd_sim.gui.emcd_forward import ForwardSettings
from emcd_sim.gui.geometry import Settings,Structure
from emcd_sim.gui.memory_budget import assess_memory,selected_memory_budget
from emcd_sim.gui.parallel_resources import worker_plan,bind_allocation
from emcd_sim.gui.propagation import numerical_info
from emcd_sim.gui.hardware_resources import summarize_cpu_sets


def machine(gib=32,logical=32,physical=16,*,available=None,commit=None,classes=None):
    return dict(installed_ram_mib=gib*1024,total_ram_mib=gib*1024,
        available_ram_mib=gib*1024*.7 if available is None else available,
        commit_available_mib=gib*1024*.6 if commit is None else commit,
        virtual_available_mib=2**30,process_rss_mib=256.,logical_processors=logical,
        system_logical_processors=logical,physical_cores=physical,available_physical_cores=physical,
        efficiency_classes=classes or {},hybrid=bool(classes),cpu_model='Simulated x64 CPU',notes=[])


def native(state):
    return dict(platform='win32',backend='OpenBLAS',version='test fixture',threads=1,
        sha256=None,numpy_version=np.__version__,cpu_count=state['logical_processors'],hardware=state,
        automatic_thread_control=True,runtimes=[dict(threads=1,library='simulated-numpy'),dict(threads=1,library='simulated-scipy')])


@pytest.mark.parametrize('gib',[8,16,32,64,128])
def test_auto_budget_uses_current_headroom_not_installed_ram(gib):
    state=machine(gib)
    info=assess_memory(128,2048,mode='automatic',snapshot=state)
    assert info['memory_budget_mib']==int(state['process_rss_mib']+.5*state['commit_available_mib'])
    assert info['memory_budget_mib']<state['installed_ram_mib']
    assert info['additional_allocation_mib']==128+1.25*128
    assert assess_memory(128,3072,snapshot=state)['memory_budget_mib']==3072


@pytest.mark.parametrize('logical,physical',[(1,1),(2,1),(8,4),(64,32),(128,64),(16,None)])
def test_cpu_policy_scales_and_keeps_small_bw_jobs_serial(logical,physical):
    state=machine(128,logical,physical)
    cfg=ForwardSettings(channeling_model='double',grid=97,depth=64)
    plan=worker_plan(Settings(),cfg,59,native=native(state))
    count=plan['effective_workers']['bloch']
    assert 1<=count<=logical and (logical==1 or count<logical)
    if physical is not None and physical>=16:assert count>4
    small=worker_plan(Settings(),replace(cfg,grid=9,depth=17),5,native=native(state))
    assert small['effective_workers']['bloch']==1
    single=worker_plan(Settings(),replace(cfg,channeling_model='single'),59,native=native(state))
    assert single['effective_workers']['bloch']==1


def test_hybrid_and_manual_cpu_requests_are_not_silently_substituted():
    state=machine(64,32,24,classes={0:16,1:8})
    cfg=ForwardSettings(channeling_model='double',grid=97)
    plan=worker_plan(Settings(),cfg,59,native=native(state))
    assert plan['effective_workers']['bloch']==15
    manual=worker_plan(Settings(),replace(cfg,worker_mode='manual',parallel_workers=40),59,native=native(state))
    assert manual['blocked'] and manual['effective_workers']['bloch']==40


def test_affinity_and_cpu_set_allocation_filter_original_core_ids():
    rows=[dict(id=i,group=i//8,logical=i%8,core=(i%8)//2,efficiency=(i%8)//4,
               allocated=i==2,allocated_to_process=False) for i in range(16)]
    info=summarize_cpu_sets(rows,groups={1},selected={8,9,10,12},affinity={(1,0),(1,2),(1,4)})
    assert info['logical_processors']==3 and info['available_physical_cores']==3
    assert info['physical_cores']==8 and info['affinity_restricted']
    with pytest.raises(ValueError,match='No processors'):summarize_cpu_sets(rows,selected=set())


@pytest.mark.parametrize('constraint,value',[('available_ram_mib',100),('commit_available_mib',100),('virtual_available_mib',100)])
def test_real_insufficiency_rejects_auto_without_forcing_one_worker(constraint,value):
    state=machine();state[constraint]=value
    cfg=ForwardSettings(channeling_model='double',memory_mode='automatic',grid=9,depth=17)
    info=numerical_info(Structure.nickel(),Settings(),cfg,enforce_execution=False,resource_snapshot=state,native=native(state))
    assert info['execution']['blocked'] and info['execution']['effective_workers']['bloch']==0
    assert info['rejected'] and info['rejection_reason']
    assert cfg.grid==9 and cfg.memory_budget_mib==2048


def test_auto_workers_fit_budget_but_manual_values_never_change():
    state=machine(32,32,16)
    cfg=ForwardSettings(channeling_model='double',memory_budget_mib=440,grid=97,depth=64)
    structure=Structure.nickel();settings=Settings()
    auto=numerical_info(structure,settings,cfg,enforce_execution=False,resource_snapshot=state,native=native(state))
    manual=numerical_info(structure,settings,replace(cfg,worker_mode='manual',parallel_workers=15),
        enforce_execution=False,resource_snapshot=state,native=native(state))
    assert auto['execution']['effective_workers']['bloch']<15
    assert manual['execution']['effective_workers']['bloch']==15 and manual['execution']['blocked']
    assert cfg.memory_budget_mib==440


def test_run_allocation_preserves_manual_requests_and_rechecks_changed_resources():
    state=machine(32,16,8);cfg=ForwardSettings(channeling_model='double',memory_mode='automatic',grid=9,depth=17)
    info=numerical_info(Structure.nickel(),Settings(),cfg,resource_snapshot=state,native=native(state))
    accepted=bind_allocation(cfg,info)
    assert accepted.memory_budget_mib==2048 and accepted.parallel_workers==1
    assert accepted.calculation_memory_budget_mib==info['memory_budget_mib']
    changed=dict(state,available_ram_mib=100)
    rejected=numerical_info(Structure.nickel(),Settings(),accepted,enforce_execution=False,resource_snapshot=changed,native=native(changed))
    assert rejected['rejected'] and accepted.resource_allocation==bind_allocation(cfg,info).resource_allocation


def test_new_auto_controls_restore_legacy_manual_and_preserve_requests(tmp_path):
    from PySide6 import QtWidgets
    from emcd_sim.gui.compute_resources import ComputeResourcesPanel
    from emcd_sim.gui.project_io import config_from_dict
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    panel=ComputeResourcesPanel();assert panel.settings()['memory_mode']=='automatic'
    legacy=config_from_dict(dict(memory_budget_mib=4096,worker_mode='manual',parallel_workers=4))
    panel.restore(legacy)
    assert panel.settings()['memory_mode']=='manual' and panel.memory_budget.value()==4096
    for mode in (0,1,0,1):panel.memory_mode.setCurrentIndex(mode);panel.worker_mode.setCurrentIndex(mode)
    assert panel.memory_budget.value()==4096 and panel.worker_count.value()==4
    panel.memory_budget.setValue(3072);assert panel.settings()['memory_budget_mib']==3072
    panel.restore(replace(legacy,memory_mode='automatic'))
    assert panel.memory_budget.value()==4096 and panel.settings()['memory_mode']=='automatic'
    panel.close();app.processEvents()


@pytest.mark.parametrize('mode',['automatic','manual'])
def test_project_roundtrip_retains_modes_and_remembered_manual_values(tmp_path,mode):
    from ase.build import bulk
    from emcd_sim.multisite import IonizationSiteGroup
    from emcd_sim.gui import project_io as io
    from test_multisite_configuration import configuration,tensor_source
    atoms=bulk('Cr','bcc',a=2.88,cubic=True)
    ref=tensor_source(tmp_path,'Cr-source','Cr')
    state=configuration(atoms,[IonizationSiteGroup('Cr','Cr',(0,1),ref,(0,0,1),2)])
    state['config']=replace(state['config'],memory_mode=mode,memory_budget_mib=3072,
        worker_mode=mode,parallel_workers=7)
    loaded=io.load_configuration(io.save_configuration(state,tmp_path/'project'))
    cfg=loaded['config']
    assert (cfg.memory_mode,cfg.memory_budget_mib,cfg.worker_mode,cfg.parallel_workers)==(mode,3072,mode,7)
    assert loaded['ready_for_calculation']


def test_no_maps_uses_detector_support_for_cpu_tasks():
    state=machine();cfg=ForwardSettings(channeling_model='double',angular_maps=False,angular_evaluation='all')
    info=numerical_info(Structure.nickel(),Settings(),cfg,resource_snapshot=state,native=native(state))
    assert info['execution']['detector_task_pixels']==info['detector_support_pixels']<cfg.grid**2


@pytest.mark.parametrize('method',['bloch','fft-multislice'])
def test_single_full_maps_fit_budget_without_hypothetical_full_field_scratch(method):
    state=machine();state['process_rss_mib']=64.
    settings=Settings();structure=Structure.nickel()
    cfg=ForwardSettings(propagation=method,grid=97,depth=64,memory_budget_mib=256,
        worker_mode='manual',parallel_workers=1)
    info=numerical_info(structure,settings,cfg,resource_snapshot=state,native=native(state))
    assert not info.get('rejected') and info['estimated_process_peak_mib']<256
    assert cfg.grid==97 and cfg.angular_maps and cfg.depth==64
    small=numerical_info(structure,settings,replace(cfg,grid=9),resource_snapshot=state,native=native(state))
    assert info['dense_working_estimate_mib']==small['dense_working_estimate_mib']
    assert info['retained_results_working_mib']>small['retained_results_working_mib']


def test_gui_run_submits_displayed_allocation_without_replacing_manual_requests(tmp_path,monkeypatch):
    from PySide6 import QtWidgets
    from emcd_sim.gui.app import MainWindow
    from emcd_sim.gui.stage_b import EMCDWorker
    from test_material_mdff_workflow import xmcd_draft
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setattr(EMCDWorker,'start',lambda self:None) # Inspect submission; no propagation.
    w=MainWindow(tmp_path/'workspace');errors=[];w.error=errors.append
    try:
        viewer=xmcd_draft(w)
        assert w.mdff_dialog.apply_configuration() is not None
        viewer.apply_groups()
        w.memory_mode.setCurrentIndex(0);w.worker_mode.setCurrentIndex(0)
        w.memory_budget.setValue(3072);w.worker_count.setValue(7)
        w.start_emcd()
        assert not errors and w.busy
        shown=w.compute_resources.info;submitted=w.worker.config
        assert submitted.resource_allocation['effective_workers']==shown['execution']['effective_workers']==w.worker.execution_policy['effective_workers']
        assert submitted.calculation_memory_budget_mib==shown['memory_budget_mib']
        assert submitted.memory_budget_mib==3072 and submitted.parallel_workers==7
    finally:
        if w.busy:w.run_outcome='cancelled';w.emcd_finished()
        w.project_dirty=False;w.close();app.processEvents()


@pytest.mark.parametrize('width',[1065,905])
def test_wrapped_resource_information_remains_readable_without_changing_parameters(tmp_path,width):
    from PySide6 import QtWidgets,QtTest
    from emcd_sim.gui.app import MainWindow
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w=MainWindow(tmp_path/'workspace');panel=w.compute_resources
    panel.presentation_section.setChecked(True)
    panel.presentation_section.parentWidget().parentWidget().setChecked(True)
    original=w.numerical_snapshot()
    state=machine();state['cpu_model']='A dynamically reported CPU model with a long name that needs several wrapped lines'
    w.resize(width,669);w.show()
    try:
        for mode in ('automatic','manual'):
            cfg=ForwardSettings(channeling_model='double',memory_mode=mode,worker_mode=mode,parallel_workers=2)
            panel.restore(cfg)
            panel.show_estimate(cfg,numerical_info(w.structure,w.settings(),cfg,resource_snapshot=state,native=native(state)))
            QtTest.QTest.qWait(300);app.processEvents()
            assert panel.worker_mode.isVisible() and panel.memory_mode.isVisible()
            for label in panel._labels:
                assert label.height()>=label.heightForWidth(label.width())
            assert w.numerical_snapshot()==original
        panel.presentation_section.setChecked(False)
        w.apply_numerical_visibility();app.processEvents()
        assert not panel.isVisible() and not panel.presentation_section.isChecked()
    finally:w.project_dirty=False;w.close();app.processEvents()
