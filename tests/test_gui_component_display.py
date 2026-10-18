"""Raw/relative toggles are presentation only; all exports retain both."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import csv
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
from dataclasses import replace
import numpy as np
import pytest
from matplotlib.figure import Figure
from emcd_sim.gui.component_display import components,mirrored_angular_components
from emcd_sim.gui.emcd_forward import calculate,ForwardSettings,export_result
from emcd_sim.gui.geometry import Structure,Settings
from emcd_sim.gui.prb_benchmark import benchmark_readout,benchmark_spectra
from emcd_sim.gui.results import draw_eels,draw_maps


def example_spectra():
    return dict(I_A_plus=np.array([14.,0.]),I_A_minus=np.array([10.,0.]),
                I_B_plus=np.array([8.,0.]),I_B_minus=np.array([12.,0.]))


def test_signed_raw_common_denominator_and_distinct_prb():
    s=example_spectra();before={k:v.copy() for k,v in s.items()}
    raw,rm=components(s,'raw');relative,pm=components(s,'relative')
    np.testing.assert_array_equal(raw['Magnetic'],[4,0]);np.testing.assert_array_equal(raw['Nonmagnetic'],[2,0])
    assert relative['Magnetic'][0]==pytest.approx(100*4/22)
    assert relative['Nonmagnetic'][0]==pytest.approx(100*2/22)
    assert np.isnan(relative['Magnetic'][1]) and np.isnan(relative['Nonmagnetic'][1])
    assert benchmark_spectra(s)[0]['prb_relative_dichroism_percent'][0]==pytest.approx(100*6/22)
    assert rm['denominator'] is None and pm['denominator']=='N_A + N_B (one common denominator)'
    for k in s:np.testing.assert_array_equal(s[k],before[k])


def test_raw_and_relative_do_not_peak_scale_or_change_parity():
    s=example_spectra();s={k:v*7 for k,v in s.items()}
    raw,_=components(s);relative,_=components(s,'relative')
    assert raw['Magnetic'][0]==28 and raw['Nonmagnetic'][0]==14
    assert relative['Magnetic'][0]==pytest.approx(100*4/22)
    reversed_s={k:s[k.replace('plus','minus') if k.endswith('plus') else k.replace('minus','plus')] for k in s}
    rev,_=components(reversed_s)
    np.testing.assert_array_equal(rev['Magnetic'],-raw['Magnetic']);np.testing.assert_array_equal(rev['Nonmagnetic'],raw['Nonmagnetic'])


@pytest.fixture(scope='module')
def result():
    return calculate(Structure.nickel(),Settings(thickness=8,beam_cutoff=.9,potential_cutoff=1.8),
        ForwardSettings(axis_declared=True,channeling_model='double',propagation='both',energy_scope='edges',
            angular_maps=True,grid=9,depth=5,fft_grid=24,subpixels=16,correction=False))


def test_primary_two_panels_preserve_raw_eels_and_component_signs(result):
    s=result['spectra'];before={k:v.copy() for k,v in s.items()}
    with patch('emcd_sim.gui.emcd_forward.calculate',side_effect=AssertionError('Display must not calculate')):
        fig=Figure();draw_eels(fig,result)
        assert len(fig.axes)==2
        np.testing.assert_array_equal(next(l for l in fig.axes[0].lines if l.get_label()=='Detector A').get_ydata(),s['I_A_plus'])
        np.testing.assert_array_equal(next(l for l in fig.axes[0].lines if l.get_label()=='Detector B').get_ydata(),s['I_B_plus'])
        np.testing.assert_array_equal(next(l for l in fig.axes[1].lines if l.get_label()=='Magnetic').get_ydata(),s['D_mag'])
        draw_eels(fig,result,component_mode='relative')
        np.testing.assert_allclose(next(l for l in fig.axes[1].lines if l.get_label()=='Magnetic').get_ydata(),100*s['D_mag']/s['Sigma_ref'])
        assert fig.axes[0].get_ylabel()=='EELS intensity (a.u.)' and fig.axes[1].get_ylabel()=='Relative EMCD (%)'
    for k in s:np.testing.assert_array_equal(s[k],before[k])


def test_two_samples_are_points_and_uncomputed_energy_is_rejected(result):
    fig=Figure();draw_eels(fig,result)
    assert 'full EELS spectrum not calculated' in fig._suptitle.get_text()
    for ax in fig.axes:
        for line in ax.lines:
            if line.get_label() in ('Detector A','Detector B','Magnetic','Nonmagnetic'):assert line.get_linestyle()=='None'
    with pytest.raises(ValueError,match='not calculated'):benchmark_readout(result,selection='selected',energy_ev=838)


def test_default_angular_components_preserve_maps_and_share_scale(result):
    before={edge:{k:v.copy() for k,v in m.items()} for edge,m in result['maps'].items()}
    fig=Figure();draw_maps(fig,result,'L3')
    panels=[ax for ax in fig.axes if ax.images]
    assert len(panels)==2 and panels[0].images[0].get_clim()==panels[1].images[0].get_clim()
    values,meta=mirrored_angular_components(result,'L3')
    assert 'not finite-aperture' in fig._suptitle.get_text()
    assert 'point pairs' in meta['support']
    for edge,m in before.items():
        for k,v in m.items():np.testing.assert_array_equal(v,result['maps'][edge][k])


def test_both_modes_export_identical_raw_and_percent_arrays(result):
    roots=[Path('outputs')/('component_export_'+uuid4().hex) for _ in range(2)]
    before={k:v.copy() for k,v in result['spectra'].items()}
    for root,mode in zip(roots,('raw','relative')):export_result(result,root,component_mode=mode)
    with np.load(roots[0]/'virtual_detector_eels.npz',allow_pickle=False) as a,np.load(roots[1]/'virtual_detector_eels.npz',allow_pickle=False) as b:
        assert set(a.files)==set(b.files)
        for k in a.files:np.testing.assert_array_equal(a[k],b[k])
        for method in ('bloch','fft-multislice'):
            for key in ('D_mag','D_nonmag','Sigma_ref','magnetic_only_percent','nonmagnetic_imbalance_percent','prb_relative_dichroism_percent'):
                assert method+'__'+key in a
        assert str(a['channeling_model'])=='double'
    for root in roots:
        with (root/'bloch_spectra.csv').open(newline='') as f:rows=list(csv.DictReader(f))
        assert rows[0]['channeling_model']=='double' and 'D_mag' in rows[0] and 'magnetic_only_percent' in rows[0]
        assert (root/'virtual_detector_eels.png').exists() and (root/'virtual_detector_eels.svg').exists()
    for k,v in before.items():np.testing.assert_array_equal(v,result['spectra'][k])


def test_gui_toggle_keeps_results_and_legacy_diagnostics(result):
    from PySide6 import QtWidgets
    from emcd_sim.gui.app import MainWindow
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w=MainWindow(workspace=Path('outputs')/('component_ui_'+uuid4().hex))
    try:
        w.display_saved_result(result)
        view=w.eels_view;assert not view.advanced.isChecked() and view.advanced_body.isHidden()
        assert [view.component_mode.itemText(i) for i in range(2)]==['Raw EMCD (a.u.)','Relative EMCD (%)']
        source_id=id(result['spectra']['I_A_plus']);before=result['spectra']['I_A_plus'].copy()
        view.component_mode.setCurrentIndex(1);app.processEvents()
        assert view.figure._emcd_display_metadata['component_mode']=='relative'
        view.component_mode.setCurrentIndex(0);app.processEvents()
        assert id(result['spectra']['I_A_plus'])==source_id
        np.testing.assert_array_equal(result['spectra']['I_A_plus'],before)
        assert 'PRB' in view.prb_readout.text()
        view.advanced.setChecked(True);app.processEvents();assert len(view.figure.axes)==3
        np.testing.assert_allclose(view.figure.axes[-1].get_xlim(),result['spectra']['energy_ev'][[0,-1]])
        assert w.settings().beam_cutoff==3.2 and w.settings().potential_cutoff==2.2
        assert 'g=1/d' in w.spin['beam'].toolTip() and 'ionization' in w.spin['potential'].toolTip()
    finally:w.close();app.processEvents()
