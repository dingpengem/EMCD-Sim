"""End-to-end source editor tests; solver expressions remain unchanged."""
from dataclasses import replace
from pathlib import Path
import json
import numpy as np
import pytest
from PySide6 import QtWidgets
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.geometry import Structure, Settings
from emcd_sim.gui.mdff_usability import complex_cell
from emcd_sim.gui.generalized_forward import source_for
from emcd_sim.gui.forward_pipeline import calculate
from emcd_sim.gui.project_io import save_project, load_project, source_status

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def window(tmp_path,monkeypatch):
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def forbidden(*args,**kwargs):raise AssertionError('Normal workflow opened a file dialog')
    monkeypatch.setattr(QtWidgets.QFileDialog,'getOpenFileName',forbidden)
    monkeypatch.setattr(QtWidgets.QFileDialog,'getSaveFileName',forbidden)
    w=MainWindow(tmp_path/'workspace');w.errors=[];w.error=w.errors.append
    w.manual_model.setCurrentIndex(0)  # Explicitly exercise the unchanged constant option.
    w.structure=Structure.from_cif(ROOT/'tests/fixtures/alpha_Fe_bcc_Im-3m.cif')
    w.zone.setText('0 0 1');w.target.setText('1 1 0');w.sync_atomic_editor_structure()
    yield w,app
    for d in w.dialogs:d.close()
    if hasattr(w.atomic_editor,'preview_dialog'):w.atomic_editor.preview_dialog.close()
    w.close();app.processEvents()


@pytest.mark.parametrize('symbol',['Sc','Ti','V','Cr','Mn','Fe','Co','Ni','Cu','Zn'])
def test_complete_defaults(window,symbol):
    e=window[0].atomic_editor;e.element.setCurrentIndex(e.element.findData(symbol))
    doc=e.document()
    assert all(f.text() for f in e.fields.values())
    assert doc['parameters']['status']=='synthetic'
    assert np.isfinite(doc['parameters']['spin_resolved_holes']).all()
    assert not e.advanced_parameters.isChecked()


@pytest.mark.parametrize('text,expected',[('2',2),('0.2-0.1i',.2-.1j),('0.2-0.1j',.2-.1j),('-1e-3+2e-4i',-.001+.0002j)])
def test_safe_complex(text,expected):assert complex_cell(text)==expected


@pytest.mark.parametrize('text',['nan','inf','1e999','1+','__import__("os")','1;2','1+2ii','(1+2j)',''])
def test_bad_complex(text):
    with pytest.raises(ValueError):complex_cell(text)


def test_all_cells_delivery_and_invalid_draft_preserves_source(window):
    w,_=window;w.model_box.setCurrentIndex(2);e=w.manual_tensor
    a=np.array([[2,.2+.1j,.3-.2j],[.2-.1j,3,.1+.3j],[.3+.2j,.1-.3j,4]])
    for i in range(3):
        for j in range(3):e.cells.item(i,j).setText(str(a[i,j]).strip('()').replace('j','i'))
    cfg=w.forward_settings();source=source_for(cfg)
    np.testing.assert_array_equal(source.plus.tensor_angstrom2_per_ev[0],a)
    np.testing.assert_array_equal(source.minus.tensor_angstrom2_per_ev[0],a.conj())
    valid=Path(cfg.source).read_bytes()
    for bad in ('nan','1e999','1+','-100'):
        e.cells.item(0,0).setText(bad)
        with pytest.raises(ValueError):w.forward_settings()
        assert Path(cfg.source).read_bytes()==valid
    e.cells.item(0,0).setText('2');e.cells.item(0,1).setText('9i')
    with pytest.raises(ValueError,match='Hermitian'):w.forward_settings()


def test_drafts_reset_preview_and_schematics(window):
    w,app=window;e=w.atomic_editor;w.model_box.setCurrentIndex(1)
    e.fields['exchange'].setText('1.25');before=e.draft();e.preview();app.processEvents()
    assert e.draft()==before
    assert 'CURRENT' in e.preview_state.text()
    e.fields['sigma'].setText('1.7');assert 'STALE' in e.preview_state.text();assert e.preview_dialog.is_stale
    e.element.setCurrentIndex(e.element.findData('Co'));e.fields['exchange'].setText('.9')
    e.element.setCurrentIndex(e.element.findData('Fe'));assert e.fields['exchange'].text()=='1.25'
    e.reset_defaults();assert e.fields['exchange'].text()=='0.5';e.document()
    e.direction.setText('1 0 0')
    for button in e.findChildren(QtWidgets.QPushButton):
        if button.text()=='Apply direction':button.click()
    cfg=w.forward_settings();np.testing.assert_allclose(cfg.magnetization,[1,0,0])
    assert 'M/beam' in e.schematic.figure.axes[1].get_title()
    e.schematic.reversal.setCurrentIndex(1);assert e.schematic.reversal.currentIndex()==1
    e.fields['sigma'].setFocus();app.processEvents();e.schematic.key='sigma';e.schematic.draw()
    assert e.schematic.explain.text()


def test_missing_reference_is_explicit_complete_synthetic(window,monkeypatch):
    import emcd_sim.gui.atomic_editor as module
    monkeypatch.setattr(module,'edge_references',lambda element:{})
    e=window[0].atomic_editor;e.reset_defaults();e.document()
    assert 'Synthetic estimated' in e.reference_problem
    assert e.parameter_origins['l3']['origin']=='synthetic_demonstration'


@pytest.mark.parametrize('model',[1,2])
def test_calculation_save_reopen_portable_source(window,tmp_path,model):
    w,app=window;w.model_box.setCurrentIndex(model)
    cfg=w.forward_settings()
    cfg=replace(cfg,propagation='both',energy_scope='edges',grid=9,depth=3,subpixels=4,halfwidth=.7,radius=.12,
        centers=((.2,.2),(.2,-.2)),fft_grid=16,slice_step=.01,correction=False,worker_mode='manual',parallel_workers=1)
    settings=Settings(zone=(0,0,1),target=(1,1,0),voltage=200,thickness=.2,tilt=(-5,7),beam_cutoff=.6,potential_cutoff=1.2)
    original=calculate(w.structure,settings,cfg)
    folder=tmp_path/'project';save_project(original,folder)
    raw=Path(cfg.source).read_bytes();Path(cfg.source).unlink()
    reopened=load_project(folder);source=source_status(reopened)['mdff']
    assert source['verified'];assert Path(source['path']).read_bytes()==raw
    if model==2:
        w.restore_imported_settings(cfg,source['path'])
        assert not w.manual_tensor.external
    else:w.restore_provider_settings(cfg,source['path'])
    rerun=calculate(w.structure,settings,replace(cfg,source=source['path']))
    for method in original['methods']:
        for key,value in original['methods'][method]['spectra'].items():
            np.testing.assert_array_equal(value,rerun['methods'][method]['spectra'][key])
    Path(source['path']).write_bytes(raw+b' ')
    with pytest.raises(ValueError):load_project(folder)
    assert not w.errors


def test_no_compatibility_controls_in_normal_ui(window):
    w,_=window;w.show();w.model_box.setCurrentIndex(1);window[1].processEvents()
    assert w.legacy_atomic_section.isHidden()
    assert all('Ni' not in w.model_box.itemText(i) for i in range(w.model_box.count()))
    assert any(b.text()=='Open CIF…' for b in w.findChildren(QtWidgets.QPushButton))
    assert not any(b.isVisible() and ('JSON' in b.text() or 'Ni' in b.text()) for b in w.findChildren(QtWidgets.QPushButton))


def test_passive_edits_never_generate_and_external_source_never_substituted(window,monkeypatch):
    w,_=window;e=w.atomic_editor
    monkeypatch.setattr(e,'generate',lambda:pytest.fail('Passive edit generated a source'))
    e.fields['sigma'].setText('1.4');w.emcd_stale()
    assert not e.validated_path and 'STALE' in e.preview_state.text()
    w.model_box.setCurrentIndex(2);cfg=w.forward_settings()
    w.imported_path.setText('unvalidated-external-source.json')
    with pytest.raises(ValueError,match='Validate'):w.forward_settings()
    assert Path(cfg.source).is_file()


@pytest.mark.parametrize('scale',[1e-25,1,1e25])
def test_scale_relative_tensor_validation(window,scale):
    e=window[0].manual_tensor
    for i in range(3):
        for j in range(3):e.cells.item(i,j).setText(str(scale if i==j else 0))
    e.cells.item(0,1).setText(str(scale*1e-7)+'j')
    with pytest.raises(ValueError,match='Hermitian'):e.matrix()
    e.cells.item(0,1).setText('0');e.cells.item(0,0).setText(str(-scale*1e-6))
    with pytest.raises(ValueError,match='semidefinite'):e.matrix()
