"""Bounded checks for a requested maximum, distinct from actual split steps."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from dataclasses import replace
import json
import numpy as np
import pytest
from PySide6 import QtWidgets
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.geometry import Structure, Settings, elastic_model
from emcd_sim.gui.emcd_forward import ForwardSettings, calculate, export_result
from emcd_sim.gui.propagation import numerical_info
from emcd_sim.gui.project_io import save_project, load_project, fingerprints
from emcd_sim.multislice_double_channeling import ProjectedFFT, incident_fields

STEPS = [.04, .5, 1., 2., 5., 10.]


@pytest.fixture(scope='module')
def small():
    structure = Structure.nickel()
    settings = Settings(zone=(0,0,1), target=(2,0,0), voltage=200,
                        thickness=.5, beam_cutoff=.9, potential_cutoff=1.8)
    cfg = ForwardSettings(model='atomic', propagation='fft-multislice',
        grid=9, depth=3, fft_grid=12, subpixels=4, energy_scope='edges',
        l3=852.7, l2=870., correction=False, centers=((.2,.2),(.2,-.2)))
    return structure, settings, cfg


@pytest.mark.parametrize('step', STEPS)
@pytest.mark.parametrize('mode', [0,1], ids=['automatic','manual'])
def test_manual_gui_preserves_requested_maximum(tmp_path, step, mode):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w = MainWindow(workspace=tmp_path/'workspace')
    try:
        assert w.spin['slice_step'].value() == ForwardSettings().slice_step == 2.
        assert (w.spin['slice_step'].minimum(), w.spin['slice_step'].maximum()) == (.001,10.)
        w.model_box.setCurrentIndex(1)
        w.numerical_mode.setCurrentIndex(mode)
        w.propagation_box.setCurrentIndex(1)
        before = w.numerical_snapshot()
        assert w.spin['slice_step'].isEnabled() and not w.spin['slice_step'].isHidden()
        w.spin['slice_step'].lineEdit().setText(str(step));w.spin['slice_step'].interpretText()
        assert w.spin['slice_step'].value() == w.forward_settings().slice_step == step
        assert all(v == w.numerical_snapshot()[k] for k,v in before.items() if k != 'slice_step')
        if step > .04:
            assert 'split-step errors' in w.memory_label.text()
        assert w.emcd_button.isEnabled(), w.emcd_button.toolTip()
        for numerical_mode in (1,0,1,0):
            w.numerical_mode.setCurrentIndex(numerical_mode)
            for solver in (0,1,2):
                w.propagation_box.setCurrentIndex(solver)
                assert w.spin['slice_step'].value()==w.forward_settings().slice_step==step
                assert w.spin['slice_step'].isEnabled()==(solver!=0)
        thickness=w.spin['thickness'].value()
        w.spin['thickness'].setValue(thickness+.5)
        assert w.settings().thickness==thickness+.5 and w.forward_settings().slice_step==step
        w.new_project();assert w.spin['slice_step'].value()==2.
    finally:
        w.close(); app.processEvents()


@pytest.mark.parametrize('step,substeps', list(zip(STEPS,[325,26,13,7,3,2])))
def test_actual_interval_steps_and_preflight(small, step, substeps):
    structure,s,c = small
    s = replace(s,thickness=26.)  # Two depth intervals of exactly 13 nm.
    c = replace(c,slice_step=step)
    info = numerical_info(structure,s,c,check_memory=False)
    grid = ProjectedFFT.build(elastic_model(structure,s),grid_points=12,potential_cutoff=1.8)
    fields,z,weights,n,dz = incident_fields(grid,26.,depth_steps=3,slice_step_nm=step)
    assert n == info['substeps_per_depth_interval'] == substeps
    assert dz == info['actual_slice_step_nm'] == 13/substeps
    assert info['requested_max_slice_step_nm'] == step
    assert dz <= step*(1+1e-14) and np.isfinite(fields).all()
    assert np.allclose(np.sum(abs(fields)**2,axis=1),1.,atol=1e-11)
    assert any('split-step errors' in w for w in info['numerical_warnings']) == (step>.04)
    assert c.depth == 3 and c.fft_grid == 12


@pytest.mark.parametrize('step', STEPS)
def test_project_and_export_metadata(small, tmp_path, step):
    structure,s,c = small
    c = replace(c,slice_step=step)
    result = calculate(structure,s,c)
    before = fingerprints(result)
    folder = save_project(result,tmp_path/'project')
    saved = load_project(folder)
    assert saved['config'].slice_step == step and fingerprints(saved) == before
    meta = json.loads((folder/'metadata.json').read_text())['numerics']
    assert meta['requested_max_slice_step_nm'] == step
    assert meta['actual_slice_step_nm'] <= step*(1+1e-14)
    assert meta['actual_slice_step_nm'] == .25/np.ceil(.25/step)
    # The ordinary export uses the same project metadata; exercise it once.
    if step == 10.:
        export_result(result,tmp_path/'export')
        exported = json.loads((tmp_path/'export/metadata.json').read_text())['numerics']
        assert exported == meta


@pytest.mark.parametrize('step', [0.,.0009,10.01,np.nan,np.inf])
def test_invalid_values_rejected(small, step):
    structure,s,c = small
    with pytest.raises(ValueError,match='0.001–10 nm'):
        numerical_info(structure,s,replace(c,slice_step=step),check_memory=False)


def test_safety_limit_and_zero_thickness(small):
    structure,s,c = small
    with pytest.raises(ValueError,match='200000 split steps'):
        numerical_info(structure,replace(s,thickness=201.),replace(c,depth=2,slice_step=.001),check_memory=False)
    grid = ProjectedFFT.build(elastic_model(structure,s),grid_points=12,potential_cutoff=1.8)
    with pytest.raises(ValueError,match='200000 split steps'):
        incident_fields(grid,201.,depth_steps=2,slice_step_nm=.001)
    # Existing GUI geometry requires positive thickness; the low-level
    # propagator separately supports its unchanged zero-thickness boundary.
    with pytest.raises(ValueError,match='Positive voltage, thickness'):
        numerical_info(structure,replace(s,thickness=0.),replace(c,slice_step=10.),check_memory=False)
    fields,z,weights,n,dz = incident_fields(grid,0.,depth_steps=3,slice_step_nm=10.)
    assert dz == n == 0


@pytest.mark.parametrize('channeling', ['single','double'])
def test_warning_is_nonblocking_for_both_channeling_modes(small, channeling):
    structure,s,c = small
    c = replace(c,propagation='both',channeling_model=channeling,slice_step=10.)
    info = numerical_info(structure,s,c)
    assert not info['execution']['blocked']
    assert any('elastic intensities' in w for w in info['numerical_warnings'])
