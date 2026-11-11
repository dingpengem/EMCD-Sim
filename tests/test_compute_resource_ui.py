"""Presentation and persistence checks; no propagation is needed for a preview."""
import sys
import pytest
from PySide6 import QtCore
from test_multisite_gui_run import app,window
from test_material_mdff_workflow import xmcd_draft
from emcd_sim.gui.compute_resources import hardware_text
from emcd_sim.gui.project_session import capture_configuration,restore_configuration
from emcd_sim.gui.project_configuration import save_configuration,load_configuration
from emcd_sim.gui.propagation import numerical_info


def test_unknown_hardware_is_explicit():
    text=hardware_text({'architecture':'arm64'})
    assert 'model unavailable' in text and 'topology unavailable' in text and 'RAM unavailable' in text
    assert 'Apple M2' not in text and '0 GiB' not in text


@pytest.fixture
def configured(window,monkeypatch):
    if sys.platform!='darwin':pytest.skip('macOS presentation')
    # Stable unit-test memory only; native packaged evidence uses live readings.
    from test_apple_adaptive_resources import SNAP
    monkeypatch.setattr('emcd_sim.gui.memory_budget.memory_snapshot',lambda:dict(SNAP))
    def forbidden(*args,**kwargs):raise AssertionError('Preview must not start a scientific calculation')
    monkeypatch.setattr('emcd_sim.gui.app.PreviewWorker.start',forbidden)
    monkeypatch.setattr('emcd_sim.gui.stage_b.EMCDWorker.start',forbidden)
    v=xmcd_draft(window);assert window.mdff_dialog.apply_configuration() is not None;v.apply_groups()
    window.set_values(dict(grid=17,depth=9,fft_grid=24,beam=.65,potential=1.2))
    window.refresh();window.emcd_stale()
    return window


def test_modes_preserve_dormant_requests_and_custom_memory(configured,tmp_path):
    w=configured;p=w.resource_panel
    w.worker_mode.setCurrentIndex(1);w.worker_count.setValue(4)
    w.memory_mode.setCurrentIndex(1);p.memory_request.setValue(3072)
    assert w.memory_budget.currentData()==3072 and p.memory_request.isEnabled()
    assert not p.cpu_manual.isHidden() and not p.memory_manual.isHidden()
    w.worker_mode.setCurrentIndex(0);w.memory_mode.setCurrentIndex(0)
    assert p.cpu_manual.isHidden() and p.memory_manual.isHidden()
    assert not p.cpu_auto.isHidden() and not p.memory_auto.isHidden()
    assert w.memory_budget.isHidden() and not w.memory_budget.isEnabled()
    state=capture_configuration(w);save_configuration(state,tmp_path/'project')
    w.worker_count.setValue(1);w.restore_memory_budget(777)
    restore_configuration(w,load_configuration(tmp_path/'project'))
    assert w.worker_mode.currentIndex()==w.memory_mode.currentIndex()==0
    assert w.worker_count.value()==4 and w.memory_budget.currentData()==3072
    w.worker_mode.setCurrentIndex(1);w.memory_mode.setCurrentIndex(1)
    assert p.memory_request.value()==3072 and w.worker_count.value()==4
    assert p.memory_request.isEnabled() and w.worker_count.isEnabled()
    w.project_dirty=False


@pytest.mark.parametrize('method',[0,1])
@pytest.mark.parametrize('channel',[0,1])
def test_preview_uses_exact_run_request(configured,method,channel):
    w=configured;w.propagation_box.setCurrentIndex(method);w.channeling_box.setCurrentIndex(channel)
    w.emcd_stale();p=w.resource_panel
    cfg=w.forward_settings();info=numerical_info(w.structure,w.settings(),cfg,enforce_execution=False)
    assert p.preview['config']==cfg
    assert p.preview['info']['execution']['effective_workers']==info['execution']['effective_workers']
    assert 'Effective workers:' in p.cpu_auto.text() and 'Pending' not in p.cpu_auto.text()
    assert 'Effective budget:' in p.memory_auto.text() and 'Pending' not in p.memory_auto.text()
    assert 'Estimated peak memory:' in p.estimate.text() and 'Backend: '+('BW','MS')[method] in p.estimate.text()
    assert ('Single','Double')[channel] in p.estimate.text()
    w.project_dirty=False


def test_final_allocation_difference_remains_visible(configured):
    w=configured;p=w.resource_panel;old=p.preview
    info=dict(old['info'],memory_budget_mib=old['info']['memory_budget_mib']+1)
    p.present(old['config'],info,final=True)
    assert 'Refreshed from preview' in p.notice.text()
    p.completed({'config':old['config'],'metadata':{'execution':info['execution']}})
    assert 'Completed run:' in p.notice.text() and 'Refreshed from preview' in p.notice.text()
    w.project_dirty=False


def test_insufficient_budget_has_explanation(configured):
    w=configured;w.memory_mode.setCurrentIndex(1);w.resource_panel.memory_request.setValue(1)
    w.emcd_stale()
    assert 'Admission: Insufficient resources' in w.resource_panel.estimate.text()
    assert w.resource_panel.preview['info']['rejected']
    assert not w.emcd_button.isEnabled()
    assert 'budget' in w.resource_panel.estimate.text().lower()
    w.project_dirty=False


def test_settings_organization_and_pending_state(window):
    if sys.platform!='darwin':pytest.skip('macOS presentation')
    from emcd_sim.gui.responsive import CollapsibleSection
    w=window
    sections=[s for s in w.findChildren(CollapsibleSection) if s.objectName().startswith('settings_')]
    assert len(sections)==7
    assert w.material_form.indexOf(w.spin['b'])>=0
    assert w.propagation_form.indexOf(w.row_projection)>=0
    assert w.shared_resources_group.layout().indexOf(w.spin['b'])<0
    w.emcd_stale()
    assert w.resource_panel.preview['info'] is None
    assert 'Admission: Pending' in w.resource_panel.estimate.text()
    assert 'MDFF' in w.resource_panel.estimate.text()
