"""Focused plots/widgets, geometry and compatibility; saved references first."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
from dataclasses import replace
import numpy as np
import pytest
from matplotlib.figure import Figure
from emcd_sim.gui.results import draw_eels,draw_maps
from emcd_sim.gui.component_display import primary_angular
from emcd_sim.gui.prb_benchmark import benchmark_spectra


@pytest.fixture(scope='module')
def result():
    from emcd_sim.gui.project_io import load_project
    saved=Path('outputs/windows_beta_acceptance/source_native/double_both_project')
    if (saved/'project.json').exists():return load_project(saved)
    from emcd_sim.gui.emcd_forward import calculate,ForwardSettings
    from emcd_sim.gui.geometry import Structure,Settings
    return calculate(Structure.nickel(),Settings(thickness=2,beam_cutoff=.9,potential_cutoff=1.8),
        ForwardSettings(axis_declared=True,channeling_model='double',propagation='both',energy_points=9,grid=9,depth=9,subpixels=16,fft_grid=24,angular_maps=True))


def test_eels_exact_two_panels_and_one_total_curve(result):
    s=result['spectra'];before={k:v.copy() for k,v in s.items()}
    for mode in ('raw','asymmetry','relative'):
        fig=Figure(layout='constrained');draw_eels(fig,result,component_mode=mode)
        assert len(fig.axes)==2
        np.testing.assert_array_equal(fig.axes[0].lines[0].get_ydata(),s['I_A_plus'])
        np.testing.assert_array_equal(fig.axes[0].lines[1].get_ydata(),s['I_B_plus'])
        if mode=='asymmetry':
            np.testing.assert_array_equal(fig.axes[1].lines[0].get_ydata(),benchmark_spectra(s)[0]['prb_relative_dichroism_percent'])
            assert fig.axes[1].lines[0].get_label()=='EMCD Asymmetry'
            assert fig.axes[1].get_ylabel()=='EMCD Asymmetry (%)'
        else:assert fig.axes[1].lines[1].get_label() in ('Nonmagnetic','Nonmagnetic Asymmetry')
    for key,value in before.items():np.testing.assert_array_equal(s[key],value)


def test_eels_widgets_modes_lock_and_no_calculation(result):
    from PySide6 import QtWidgets
    from emcd_sim.gui.app import MainWindow
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w=MainWindow(workspace=Path('outputs')/('v060_gui_'+uuid4().hex))
    try:
        with patch('emcd_sim.gui.stage_b.calculate',side_effect=AssertionError('Display must not calculate')):
            w.display_saved_result(result)
            for view in (w.eels_view,w.maps_view):
                assert [view.component_mode.itemText(i) for i in range(2)]==['Raw (a.u.)','EMCD Asymmetry (%)']
                assert view.component_mode.currentData()=='raw'
            view=w.eels_view
            assert view.prb_benchmark.title()=='EMCD Asymmetry'
            for mode in (1,0):
                view.component_mode.setCurrentIndex(mode)
                for index in (1,2,0):view.choice.setCurrentIndex(index);app.processEvents()
            prb=view.prb_benchmark;prb.selection.setCurrentIndex(1);prb.energy.setValue(result['config'].l2);prb.fixed.setChecked(True)
            view.component_mode.setCurrentIndex(1);assert prb.fixed.isChecked()
            assert 'L3' in view.prb_readout.text() and 'L2' in view.prb_readout.text()
            view.advanced.setChecked(True);view.component_diagnostic.setCurrentIndex(1)
            assert 'Magnetic-only' in view.figure.axes[1].lines[0].get_label()
            assert len(view.figure.axes)==2
    finally:w.close();app.processEvents()


def test_mirror_map_hand_reference_and_invalid_denominators(result):
    old=result['maps']['L3'];shape=result['qx'].shape
    plus=.55+.1*result['qy']/np.max(result['qy']);minus=np.full(shape,.55)
    maps=dict(old,I_plus=plus,I_minus=minus,I_mag=(plus-minus)/2,I_nonmag=(plus+minus)/2)
    r=dict(result,maps={'L3':maps})
    raw,_=primary_angular(r,'L3');asym,meta=primary_angular(r,'L3','asymmetry')
    np.testing.assert_allclose(raw['Magnetic paired difference'][-1],.1)
    np.testing.assert_allclose(raw['Nonmagnetic paired difference'][-1],.1)
    np.testing.assert_allclose(asym['EMCD Asymmetry'][-1],100*.2/1.1)
    np.testing.assert_allclose(asym['EMCD Asymmetry'][0],-100*.2/1.1)
    assert meta['mask']['relative_floor']==1e-6
    plus=plus.copy();minus=minus.copy();plus[[0,-1],0]=0;minus[[0,-1],0]=0
    r=dict(r,maps={'L3':dict(maps,I_plus=plus,I_minus=minus)})
    value,_=primary_angular(r,'L3','asymmetry');assert np.isnan(value['EMCD Asymmetry'][[0,-1],0]).all()
    invalid=dict(result,config=replace(result['config'],centers=((.1,.2),(.2,-.2))))
    with pytest.raises(ValueError,match='not y mirrors'):primary_angular(invalid,'L3')
    invalid=dict(result,qx=result['qx'][:,::-1])
    with pytest.raises(ValueError,match='regular increasing'):primary_angular(invalid,'L3')


def test_angular_raw_total_layout_shared_scale_overlays_and_immutability(result):
    before={edge:{k:v.copy() for k,v in fields.items()} for edge,fields in result['maps'].items()}
    for mode in ('raw','asymmetry'):
        fig=Figure(layout='constrained');draw_maps(fig,result,'L3',signal_mode=mode)
        axes=[a for a in fig.axes if a.images]
        assert len(axes)==(2 if mode=='raw' else 1)
        expected,_=primary_angular(result,'L3',mode)
        for a,value in zip(axes,expected.values()):
            np.testing.assert_array_equal(np.asarray(a.images[0].get_array().filled(np.nan)),value)
            assert a.images[0].get_clim()[0]==-a.images[0].get_clim()[1]
            assert len(a.lines)>0 and len(a.patches)>0
        if mode=='raw':assert axes[0].images[0].get_clim()==axes[1].images[0].get_clim()
    for edge,fields in before.items():
        for key,value in fields.items():np.testing.assert_array_equal(result['maps'][edge][key],value)


def test_detector_asymmetry_after_integration_not_average_of_percentages():
    from emcd_sim.gui.prb_benchmark import relative_dichroism_percent
    a=np.array([.65,.9]);b=np.array([.45,.1]);weights=np.array([1.,.01])
    integrated,_=relative_dichroism_percent(weights@a,weights@b)
    np.testing.assert_allclose(integrated,100*(weights@(a-b))/(weights@(a+b)))
    pixels,_=relative_dichroism_percent(a,b)
    assert not np.isclose(integrated,np.mean(pixels))


def test_exports_keep_legacy_arrays_and_explicit_signal_sidecars(result):
    import json,csv
    from emcd_sim.gui.emcd_forward import export_result
    from emcd_sim.gui.project_io import load_project
    before={name:{k:v.copy() for k,v in m['spectra'].items()} for name,m in result['methods'].items()}
    root=Path('outputs')/('v060_exports_'+uuid4().hex)
    for mode in ('raw','asymmetry'):
        path=root/mode;export_result(result,path,component_mode=mode)
        loaded=load_project(path)
        for name,m in loaded['methods'].items():
            for key,value in before[name].items():np.testing.assert_array_equal(value,m['spectra'][key])
        with np.load(path/'signal_display.npz',allow_pickle=False) as data:
            for name,m in result['methods'].items():
                np.testing.assert_array_equal(data[name+'__emcd_asymmetry_percent'],benchmark_spectra(m['spectra'])[0]['prb_relative_dichroism_percent'])
                with (path/(name+'_signal_display.csv')).open(newline='') as f:
                    rows=list(csv.DictReader(f))
                for key in rows[0]:np.testing.assert_allclose([float(r[key]) for r in rows],data[name+'__'+key],equal_nan=True,rtol=0,atol=0)
        meta=json.loads((path/'figure_display.json').read_text())
        assert meta['component_mode']==meta['map_signal_mode']==mode
        assert (path/'virtual_detector_eels.svg').exists() and (path/'L3_angular_maps.png').exists()
    for name,fields in before.items():
        for key,value in fields.items():np.testing.assert_array_equal(result['methods'][name]['spectra'][key],value)


def test_saved_display_migration_and_new_state_roundtrip(result):
    from PySide6 import QtWidgets
    from emcd_sim.gui.app import MainWindow
    from emcd_sim.gui.project_io import load_project
    import time
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    root=Path('outputs')/('v060_state_'+uuid4().hex);w=MainWindow(workspace=root/'workspace')
    try:
        legacy=dict(result,display_state=dict(component_mode='relative',advanced=False,locked=True,energy_ev=result['config'].l2,selection='selected'))
        with patch('emcd_sim.gui.stage_b.calculate',side_effect=AssertionError('Display must not calculate')):
            w.display_saved_result(legacy)
            view=w.eels_view
            assert view.component_mode.currentData()=='raw' and view.advanced.isChecked()
            assert view.component_diagnostic.currentData()=='relative' and 'Legacy Relative' in view.display_note.text()
            assert view.prb_benchmark.fixed.isChecked()
            view.advanced.setChecked(False);view.component_mode.setCurrentIndex(1);w.maps_view.component_mode.setCurrentIndex(1)
            w.save_to_path(root/'project');deadline=time.monotonic()+20
            while w.busy and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
            assert not w.busy
            loaded=load_project(root/'project');assert loaded['display_state']['signal_display_schema']==2
            view.component_mode.setCurrentIndex(0);w.maps_view.component_mode.setCurrentIndex(0)
            w.display_saved_result(loaded)
            assert view.component_mode.currentData()==w.maps_view.component_mode.currentData()=='asymmetry'
            assert view.prb_benchmark.fixed.isChecked()
    finally:w.close();app.processEvents()
