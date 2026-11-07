"""Bounded GUI-worker calculations against the production programmatic API."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from dataclasses import replace
import json
import sys
import time

import numpy as np
import pytest
from ase import Atoms
from ase.build import bulk
from PySide6 import QtCore,QtWidgets,QtTest

from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.geometry import Structure
from emcd_sim.gui.forward_pipeline import calculate,calculate_multisite
from emcd_sim.gui.generalized_forward import settings_for_source
from emcd_sim.gui.multisite_run import applied_inputs
from emcd_sim.gui.multisite_results import comparison_text,covered_segments
from emcd_sim.multisite import IonizationSiteGroup,MultiSiteIonization
from single_element_helpers import document

RAW = ('I_A_plus','I_B_plus','I_A_minus','I_B_minus','N_A','N_B','M_A','M_B','D_raw','D_mag','D_nonmag')


@pytest.fixture(scope='module')
def app():return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def window(tmp_path,app,monkeypatch):
    widget = MainWindow(workspace=tmp_path/'workspace');widget.test_errors = []
    monkeypatch.setattr(widget,'error',widget.test_errors.append)
    monkeypatch.setattr(widget,'store_ui_preferences',lambda:None)
    yield widget
    if widget.worker is not None and widget.worker.isRunning():
        widget.worker.requestInterruption();assert widget.worker.wait(10000)
    for child in widget.findChildren(QtWidgets.QDialog):child.close()
    widget.close();widget.deleteLater();app.processEvents()


def controls(window, structure, method='bloch', channel='single'):
    window.numerical_mode.setCurrentIndex(1);window.structure = structure
    with QtCore.QSignalBlocker(window.zone):window.zone.setText('0 0 1')
    target = '1 1 0' if set(structure.atoms.get_chemical_symbols()) == {'Cr'} else '2 0 0'
    with QtCore.QSignalBlocker(window.target):window.target.setText(target)
    for box,index in [(window.basis_mode,1),(window.propagation_box,0 if method=='bloch' else 1),
                      (window.channeling_box,0 if channel=='single' else 1),(window.energy_scope,1),(window.worker_mode,1)]:
        with QtCore.QSignalBlocker(box):box.setCurrentIndex(index)
    window.worker_count.setValue(1)
    from emcd_sim.elastic_providers import LOBATO,ADAPTIVE
    provider = LOBATO if set(structure.atoms.get_chemical_symbols()) == {'Ni'} else ADAPTIVE
    with QtCore.QSignalBlocker(window.elastic_provider_box):window.elastic_provider_box.setCurrentIndex(window.elastic_provider_box.findData(provider))
    with QtCore.QSignalBlocker(window.correction):window.correction.setChecked(False)
    with QtCore.QSignalBlocker(window.angular_maps):window.angular_maps.setChecked(True)
    window.set_values(dict(kv=200,thickness=.1,beam=.6,potential=1.2,grid=9,depth=3,subpixels=4,
        fft_grid=12,slice_step=.02,halfwidth=.7,radius=.12,tx=-5,ty=7))
    window.detectors = np.array([[.2,.2],[.2,-.2]])
    window.refresh()


def sites_for(tmp_path,kind='Cr'):
    if kind=='Cr':
        atoms = bulk('Cr','bcc',a=2.88,cubic=True);specs = [('Cr-up','Cr',(0,),False,1.,0.),('Cr-down','Cr',(1,),True,.8,0.)]
    elif kind=='Fe3O4':
        atoms = Atoms('Fe3O4',scaled_positions=[(i/7,(i*.23)%1,(i*.37)%1) for i in range(7)],cell=[5]*3,pbc=True)
        specs = [('Fe(A)','Fe',(0,),True,1.,0.),('Fe(B)','Fe',(1,2),False,2.,0.)]
    else:
        atoms = Atoms('FeNi',scaled_positions=[[.1,.1,.1],[.4,.4,.4]],cell=[5]*3,pbc=True)
        specs = [('Fe','Fe',(0,),False,1.,0.),('Ni','Ni',(1,),False,3.,140.)]
    structure = Structure(atoms);groups = []
    for name,element,indices,down,scale,shift in specs:
        d = document(element);d['magnetization_crystal'] = [0,0,-1 if down else 1]
        d['energy_ev'] = (np.asarray(d['energy_ev'])+shift).tolist()
        d['selected_ev'] = {k:v+shift for k,v in d['selected_ev'].items()}
        if down:d['T_plus'],d['T_minus'] = d['T_minus'],d['T_plus']
        for key in ('T_plus','T_minus','T_even'):
            for part in ('real','imag'):d[key][part] = (scale*np.asarray(d[key][part])).tolist()
        path = tmp_path/(name+'.json');path.write_text(json.dumps(d),encoding='utf-8')
        cfg = settings_for_source(path)
        groups.append(IonizationSiteGroup(name,element,indices,cfg,tuple(d['magnetization_crystal']),len(indices)))
    return structure,MultiSiteIonization(structure,groups)


def bind(window, sites):
    window.show_structure_viewer();viewer = window.structure_viewer
    viewer.set_magnetization_mode('local');viewer.set_site_groups(sites)
    viewer.editor.apply();window.emcd_stale()
    return viewer.editor


def finish(window,app,timeout=30000):
    deadline = time.monotonic()+timeout/1000
    while window.busy and time.monotonic()<deadline:app.processEvents();QtTest.QTest.qWait(10)
    assert not window.busy,'Owned GUI worker did not finish within the bounded test interval'
    app.processEvents()
    assert not window.test_errors,window.test_errors
    assert window.run_outcome == 'completed'
    return window.emcd_result


@pytest.mark.parametrize('method,channel',[('bloch','single'),('fft-multislice','single'),('bloch','double'),('fft-multislice','double')])
def test_afm_gui_modes_match_programmatic_api(window,tmp_path,app,method,channel):
    structure,sites = sites_for(tmp_path)
    controls(window,structure,method,channel);editor = bind(window,sites)
    # Disabled/invalid legacy M cannot override a valid local configuration.
    with QtCore.QSignalBlocker(window.axis):window.axis.setText('unused legacy global M')
    cfg,inputs,windows,reverse,signature = applied_inputs(window,window.forward_settings())
    expected = calculate_multisite(structure,window.settings(),inputs,cfg,energy_windows=windows,reverse_magnetization=reverse)
    assert window.emcd_button.isEnabled(),window.emcd_button.toolTip()
    window.start_emcd();assert window.busy
    stages = [];window.worker.stage.connect(stages.append)
    actual = finish(window,app)
    for key in RAW:np.testing.assert_allclose(actual['spectra'][key],expected['spectra'][key],rtol=2e-12,atol=1e-15)
    for gid,group in actual['groups'].items():
        for key in RAW:np.testing.assert_allclose(group['spectra'][key],expected['groups'][gid]['spectra'][key],rtol=2e-12,atol=1e-15)
    assert stages and not window.worker.isRunning()
    assert actual['metadata']['multisite']['selected_atom_count'] == 2
    assert len(window.eels_view.figure.axes) == 4
    assert 'reversal-odd' in window.comparison.toPlainText() and 'fixed denominator 2' in window.comparison.toPlainText()
    assert window.selected_record['material'] == 'Cr2'
    assert actual['gui_multisite_input'] == signature
    assert editor.accepted_site_groups is not None


@pytest.mark.parametrize('kind',['Fe3O4','FeNi'])
def test_group_weighting_windows_and_global_pair_reversal(window,tmp_path,app,kind):
    structure,sites = sites_for(tmp_path,kind);controls(window,structure);editor = bind(window,sites)
    if kind == 'FeNi':window.energy_scope.setCurrentIndex(0)  # Independent full provider grids, not legacy energy sampling.
    window.start_emcd();normal = finish(window,app)
    total = normal['spectra'];n = sum(g.multiplicity for g in sites.groups)
    for key in RAW:
        weighted = sum(g.multiplicity*normal['groups'][g.group_id]['spectra'][key] for g in sites.groups)/n
        np.testing.assert_allclose(total[key],weighted,rtol=2e-12,atol=1e-15)
    if kind=='Fe3O4':assert n == 3 and len(structure.atoms) == 7
    else:
        segments = covered_segments(normal,total['energy_ev'])
        assert len(segments) == 2 and not np.any(segments[0]&segments[1])
    refs = [g.mdff_reference for g in editor.accepted_site_groups.groups]
    directions = [g.magnetization for g in editor.accepted_site_groups.groups]
    editor.flip_all();editor.apply()
    assert editor.reverse_magnetization
    assert [g.magnetization for g in editor.accepted_site_groups.groups] == directions
    assert [g.mdff_reference for g in editor.accepted_site_groups.groups] == refs
    window.start_emcd();flipped = finish(window,app)
    for detector in ('A','B'):
        np.testing.assert_allclose(flipped['spectra'][f'I_{detector}_plus'],total[f'I_{detector}_minus'],rtol=2e-12,atol=1e-15)
        np.testing.assert_allclose(flipped['spectra'][f'N_{detector}'],total[f'N_{detector}'],rtol=2e-12,atol=1e-15)
        np.testing.assert_allclose(flipped['spectra'][f'M_{detector}'],-total[f'M_{detector}'],rtol=2e-12,atol=1e-15)
    assert flipped['metadata']['multisite']['global_reversal'] is True
    assert all(np.min(flipped['spectra'][key]) >= -1e-10*max(np.max(abs(flipped['spectra'][key])),1e-300) for key in RAW[:4])


@pytest.mark.parametrize('channel',['single','double'])
def test_legacy_global_ni_gui_matches_existing_calculation(window,app,channel):
    controls(window,Structure.nickel(),channel=channel)
    window.atomic_editor.use_editor.setChecked(False);window.atomic_parameter_path.clear()
    window.model_box.setCurrentIndex(1);window.emcd_stale()
    cfg = window.forward_settings();assert cfg.model == 'atomic' and not hasattr(cfg,'provider_schema')
    expected = calculate(window.structure,window.settings(),cfg)
    window.start_emcd();actual = finish(window,app)
    for key in RAW:np.testing.assert_allclose(actual['spectra'][key],expected['spectra'][key],rtol=2e-12,atol=1e-15)
    assert window.axis.isEnabled() and actual['config'].model != 'multisite'


def test_incomplete_stale_and_resource_errors_do_not_start_workers(window,tmp_path,monkeypatch):
    structure,sites = sites_for(tmp_path);controls(window,structure)
    window.show_structure_viewer();window.structure_viewer.set_magnetization_mode('local')
    window.start_emcd();assert window.worker is None and window.test_errors
    window.test_errors.clear();editor = bind(window,sites)
    original = sites.groups[0].mdff_reference.source
    from pathlib import Path
    path = Path(original);raw = path.read_bytes();path.write_bytes(raw+b'\n')
    window.start_emcd();assert window.worker is None and 'checksum' in window.test_errors[-1]
    path.write_bytes(raw);window.test_errors.clear()
    from emcd_sim.gui import parallel_resources
    monkeypatch.setattr(parallel_resources,'require_supported',lambda policy:(_ for _ in ()).throw(ValueError('Test resource admission blocked')))
    window.start_emcd();assert window.worker is None and 'admission' in window.test_errors[-1]
    assert not window.busy


def test_cancellation_and_mode_switching_keep_applied_configuration(window,tmp_path,app):
    structure,sites = sites_for(tmp_path);controls(window,structure);editor = bind(window,sites)
    references = editor.accepted_site_groups
    window.start_emcd();window.cancel()
    deadline = time.monotonic()+10
    while window.busy and time.monotonic()<deadline:app.processEvents();QtTest.QTest.qWait(10)
    assert not window.busy and window.run_outcome == 'cancelled'
    assert window.emcd_result is None and not window.worker.isRunning()
    assert window.worker.cancellation_times.get('stopped') is not None
    window.structure_viewer.set_magnetization_mode('global')
    assert window.axis.isEnabled() and editor.accepted_site_groups is references
    window.structure_viewer.set_magnetization_mode('local')
    assert not window.axis.isEnabled() and editor.accepted_site_groups is references


def test_pending_mdff_and_unsupported_controls_are_actionable(window,tmp_path):
    structure,sites = sites_for(tmp_path);controls(window,structure);editor = bind(window,sites)
    editor.groups.setCurrentItem(editor.groups.topLevelItem(0));dialog = editor.configure_mdff()
    dialog.import_path.setText('unfinished source')
    window.start_emcd()
    assert window.worker is None and 'pending MDFF' in window.test_errors[-1]
    dialog.reject();assert not dialog.has_unapplied_edits()
    assert applied_inputs(window,window.forward_settings())[1].groups
    window.correction.setChecked(True);window.start_emcd()
    assert window.worker is None and 'post-edge correction' in window.test_errors[-1]
    assert window.correction.isChecked()  # No automatic settings repair.
    window.correction.setChecked(False)
    with QtCore.QSignalBlocker(window.channeling_box):window.channeling_box.setCurrentIndex(1)
    with QtCore.QSignalBlocker(window.propagation_box):window.propagation_box.setCurrentIndex(2)
    window.start_emcd()
    assert window.worker is None and 'separate BW' in window.test_errors[-1]
    assert window.propagation_box.currentIndex() == 2 and window.channeling_box.currentIndex() == 1


@pytest.mark.skipif(sys.platform!='win32' or os.environ.get('QT_QPA_PLATFORM')!='windows',reason='Explicit native Windows GUI check')
def test_native_windows_complete_multisite_calculation(window,tmp_path,app):
    assert app.platformName() == 'windows'
    structure,sites = sites_for(tmp_path);controls(window,structure)
    window.show();editor = bind(window,sites)
    assert QtTest.QTest.qWaitForWindowExposed(window.windowHandle(),3000)
    window.structure_viewer.close()
    QtTest.QTest.mouseClick(window.emcd_button,QtCore.Qt.MouseButton.LeftButton)
    actual = finish(window,app)
    assert actual['config'].model == 'multisite' and len(actual['groups']) == 2
    assert window.tabs.currentIndex() == 2 and window.eels_view.result is actual
    assert 'mean per selected ionizing atom (N=2)' in window.eels_view.multisite_banner.text()
    assert 'per incident electron' in window.diffraction_view.multisite_banner.text()
    assert editor.accepted_site_groups is not None and not window.axis.isEnabled()
    QtTest.QTest.qWait(200);app.processEvents();window.eels_view.canvas.draw()
    if os.environ.get('EMCD_VIEWER_CHECK_IMAGE'):window.grab().save(os.environ['EMCD_VIEWER_CHECK_IMAGE'])
