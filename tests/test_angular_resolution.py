"""Sampling controls and saved-data presentation; no production propagation."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from dataclasses import replace
from pathlib import Path
import numpy as np
import pytest
from PySide6 import QtWidgets
from matplotlib.figure import Figure
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.forward_settings import NiForwardSettings
from emcd_sim.gui.project_io import config_from_dict,load_project
from emcd_sim.gui.results import draw_maps


def test_defaults_and_legacy_memory():
    assert NiForwardSettings().grid==97
    assert NiForwardSettings().memory_budget_mib==config_from_dict({}).memory_budget_mib==2048
    assert config_from_dict(dict(memory_budget_mib=512,grid=33)).memory_budget_mib==512
    assert config_from_dict(dict(memory_budget_mib=512,grid=33)).grid==33


def test_presets_new_project_and_independent_fft_subpixels(tmp_path):
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w=MainWindow(workspace=tmp_path/'workspace')
    try:
        assert w.spin['grid'].value()==97 and w.angular_resolution.currentData()==97
        assert isinstance(w.memory_budget,QtWidgets.QSpinBox)
        assert (w.memory_budget.minimum(),w.memory_budget.maximum())==(1,2**31-1)
        assert w.memory_mode.currentIndex()==0 and w.memory_budget.value()==2048
        assert not w.memory_budget.isEnabled()
        w.memory_mode.setCurrentIndex(1)
        assert w.memory_budget.isEnabled()
        w.memory_budget.setValue(512)
        assert w.compute_resources.settings()['memory_budget_mib']==512
        before=(w.spin['fft_grid'].value(),w.spin['subpixels'].value(),w.spin['halfwidth'].value())
        for i,n in enumerate((33,97,193)):
            w.angular_resolution.setCurrentIndex(i);assert w.spin['grid'].value()==n
            assert before==(w.spin['fft_grid'].value(),w.spin['subpixels'].value(),w.spin['halfwidth'].value())
        w.spin['grid'].setValue(65)
        assert w.angular_resolution.currentData() is None
        assert w.angular_resolution.currentText().startswith('Custom')
        assert '65' in w.angular_resolution.currentText()
        path=Path('outputs/v060_release/source_native/single_both_project')
        if path.exists():
            saved=load_project(path)
            w.emcd_result=dict(saved,config=replace(saved['config'],grid=33,memory_budget_mib=512))
            w.use_result_settings()
            assert w.memory_budget.value()==512 and w.spin['grid'].value()==33
            assert w.angular_resolution.currentData()==33
        w.memory_budget.setValue(512);w.new_project()
        assert w.memory_mode.currentIndex()==0
        assert w.memory_budget.value()==2048 and w.spin['grid'].value()==97
    finally:w.close();app.processEvents()


def test_saved_dimensions_and_export_metadata_are_actual():
    path=Path('outputs/v060_release/source_native/single_both_project')
    if not path.exists():pytest.skip('Optional stored GUI reference')
    result=load_project(path);r=result['methods']['bloch']
    r=dict(r,config=replace(r['config'],grid=193))
    before=r['maps']['L3']['I_plus'].copy()
    fig=Figure(figsize=(10,7));draw_maps(fig,r,'L3',signal_mode='asymmetry')
    metadata=fig._emcd_display_metadata
    assert metadata['angular_grid_shape']==list(r['qx'].shape)==[9,9]
    assert metadata['display_interpolation']=='nearest'
    assert 'Angular Grid: 9 x 9' in fig._suptitle.get_text()
    assert metadata['q_spacing_inv_angstrom'][0]==r['qx'][0,1]-r['qx'][0,0]
    np.testing.assert_array_equal(before,r['maps']['L3']['I_plus'])
