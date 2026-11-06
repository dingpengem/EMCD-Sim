"""XMCD source/provider preview and three-model restoration workflows."""
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
from PySide6 import QtWidgets
from emcd_sim.gui.geometry import Settings, Structure
from emcd_sim.gui.forward_pipeline import calculate
from emcd_sim.gui.project_io import save_project, load_project
from emcd_sim.mdff_providers import prepare_provider
from test_mdff_usability import window


def declared_xmcd(w,tmp_path):
    e=np.linspace(695,740,91)
    n=.2+np.exp(-((e-709)/1.5)**2)+.6*np.exp(-((e-722)/1.5)**2)
    d=.05*np.exp(-((e-709)/1.5)**2)-.025*np.exp(-((e-722)/1.5)**2)
    path=tmp_path/'explicit-fe.xmcd';np.savetxt(path,np.column_stack((e,n+d,n-d,2*d,2*n)))
    w.model_box.setCurrentIndex(0);w.source_path.setText(str(path));w.validate_xmcd(show_error=False)
    w.explicit_xmcd.setChecked(True)
    for widget,text in ((w.xmcd_element,'Fe'),(w.xmcd_edge,'L2,3'),(w.xmcd_selected,''),
            (w.xmcd_provenance,'Synthetic Fe source for software test only'),(w.xmcd_validity,'Not material-calibrated'),(w.xmcd_scale,'2.5')):
        widget.setText(text)
    w.xmcd_status.setCurrentText('synthetic');w.declaration.setChecked(True)
    w.preview_mdff()
    assert w.xmcd_preview.snapshot is not None,w.xmcd_preview.status.text()
    return path


def test_actual_input_and_provider_tensors_all_views(window,tmp_path):
    w,_=window;path=declared_xmcd(w,tmp_path);p=w.xmcd_preview;s=p.snapshot
    expected=prepare_provider(s['config']).tensors(s['energy'],np.eye(3))
    for key,t in zip(('+M','−M'),expected):np.testing.assert_array_equal(s['states'][key],t.tensor_angstrom2_per_ev)
    raw=np.loadtxt(path)
    for line,column in zip(p.figure.axes[0].lines,(1,2,4,3)):
        np.testing.assert_allclose(line.get_ydata(),raw[:,column],rtol=1e-14,atol=1e-15)
        assert 'input' in line.get_label()
    for state_index in range(p.state.count()):
        p.state.setCurrentIndex(state_index)
        for component_index in range(p.component.count()):
            p.component.setCurrentIndex(component_index);p.part.setCurrentIndex(0)
            selected=('+M','−M') if state_index==4 else ('Even','Odd') if state_index==5 else (p.state.currentText(),)
            for index,key in enumerate(selected):
                t=s['states'][key];name=p.component.currentText()
                value=np.trace(t,axis1=-2,axis2=-1)/3 if name=='Trace/3' else t[:,'xyz'.index(name[1]),'xyz'.index(name[2])]
                np.testing.assert_array_equal(p.curves[index*2][1],value.real)
                np.testing.assert_array_equal(p.curves[index*2+1][1],value.imag)
    assert not p.is_stale and not w.errors


@pytest.mark.parametrize('setting',['eta','beta','axis','declaration','edge','scale','source_bytes'])
def test_relevant_changes_invalidate_snapshot(window,tmp_path,setting):
    w,_=window;path=declared_xmcd(w,tmp_path);p=w.xmcd_preview;old=p.snapshot
    if setting in ('eta','beta'):w.spin[setting].setValue(.7)
    elif setting=='axis':w.axis.setText('1 0 0')
    elif setting=='declaration':w.declaration.setChecked(False)
    elif setting=='edge':w.spin['xl3'].setValue(w.spin['xl3'].value()+.1)
    elif setting=='scale':w.xmcd_scale.setText('3')
    else:path.write_bytes(path.read_bytes()+b'\n');p.invalidate_if_changed()
    assert p.is_stale and 'STALE' in p.status.text()
    assert p.snapshot is old
    p.state.setCurrentIndex(3)
    assert 'STALE' in p.figure.axes[1].get_title()
    if setting=='source_bytes':
        p.update_preview();assert p.is_stale and 'checksum' in p.status.text()


def test_input_columns_are_shown_exactly_not_reconstructed(window,tmp_path):
    w,_=window;path=declared_xmcd(w,tmp_path)
    data=np.loadtxt(path);data[:,3:5]*=1+1e-6  # Within the existing loader's redundancy tolerance.
    np.savetxt(path,data);w.validate_xmcd(show_error=False);w.declaration.setChecked(True);w.preview_mdff()
    p=w.xmcd_preview;assert not p.is_stale,p.status.text()
    for line,column in zip(p.figure.axes[0].lines,(1,2,4,3)):np.testing.assert_array_equal(line.get_ydata(),data[:,column])


def test_missing_source_keeps_visible_preview_and_directs_to_main_input(window):
    w,app=window;w.model_box.setCurrentIndex(0);w.source_path.clear();w.mdff_dialog.show();app.processEvents()
    p=w.xmcd_preview;w.preview_mdff()
    assert p.isVisible() and p.is_stale and not hasattr(p,'select_source')
    assert 'main XMCD input' in p.status.text() and not w.errors


def test_main_source_selected_once_serves_preview_and_calculation(window,tmp_path):
    import time
    w,app=window;w.model_box.setCurrentIndex(0)
    path=tmp_path/'input.xmcd';energy=np.linspace(695,740,91)
    n=.2+np.exp(-((energy-709)/1.5)**2)+.6*np.exp(-((energy-722)/1.5)**2)
    d=.05*np.exp(-((energy-709)/1.5)**2)-.025*np.exp(-((energy-722)/1.5)**2)
    np.savetxt(path,np.column_stack((energy,n+d,n-d,2*d,2*n)))
    with patch.object(QtWidgets.QFileDialog,'getOpenFileName',return_value=(str(path),'')) as choose:
        w.browse_xmcd()  # The main input owns the only source selection.
        assert w.source_info and w.validated_path==str(path)
        w.explicit_xmcd.setChecked(True)
        for widget,text in ((w.xmcd_element,'Fe'),(w.xmcd_edge,'L2,3'),(w.xmcd_selected,''),
                (w.xmcd_provenance,'Synthetic single-selection software test'),(w.xmcd_validity,'Not material-calibrated'),(w.xmcd_scale,'2.5')):
            widget.setText(text)
        w.xmcd_status.setCurrentText('synthetic');w.declaration.setChecked(True)
        w.preview_mdff();preview=w.xmcd_preview
        assert preview.snapshot is not None and not preview.is_stale,preview.status.text()
        w.numerical_mode.setCurrentIndex(1);w.worker_mode.setCurrentIndex(1);w.worker_count.setValue(1)
        w.set_values(dict(beam=.6,potential=1.2,kv=200,thickness=.2,grid=9,depth=3,subpixels=4,energy=9,halfwidth=.7,radius=.12))
        w.propagation_box.setCurrentIndex(0);w.energy_scope.setCurrentIndex(1)
        w.start_emcd();deadline=time.monotonic()+90
        while w.busy and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
        assert not w.busy and not w.errors,w.errors
        assert w.run_outcome=='completed'
        cfg=w.emcd_result['config'];snapshot=preview.snapshot
        assert cfg.source==snapshot['config'].source==str(path)
        assert cfg.source_sha256==snapshot['config'].source_sha256==w.source_info['sha256']
        expected=prepare_provider(cfg).tensors(snapshot['energy'],np.eye(3))
        for state,tensor in zip(('+M','−M'),expected):
            np.testing.assert_array_equal(snapshot['states'][state],tensor.tensor_angstrom2_per_ev)
        assert choose.call_count==1
        assert '*.xmcd' in choose.call_args.args[-1] and '*.json' not in choose.call_args.args[-1]


def test_bundled_other_element_never_substituted(window):
    w,_=window;w.model_box.setCurrentIndex(0);w.declaration.setChecked(True);w.preview_mdff()
    assert w.xmcd_preview.snapshot is None
    assert 'Bundled Ni XMCD cannot be used for another element' in w.xmcd_preview.status.text()
    assert not w.errors


def test_legacy_preview_uses_calculation_provider(window):
    w,_=window;w.structure=Structure.nickel();w.model_box.setCurrentIndex(0);w.declaration.setChecked(True);w.preview_mdff()
    p=w.xmcd_preview;assert p.snapshot is not None,p.status.text()
    cfg=p.snapshot['config'];assert not hasattr(cfg,'provider_schema')
    expected=prepare_provider(cfg).tensors(p.snapshot['energy'],np.eye(3))
    np.testing.assert_array_equal(p.snapshot['states']['+M'],expected[0].tensor_angstrom2_per_ev)
    assert 'source-normalized' in p.identity.text()


def test_switching_models_preserves_drafts_axes_and_display_state(window,tmp_path):
    w,_=window;declared_xmcd(w,tmp_path);p=w.xmcd_preview
    w.axis.setText('1 0 0');w.declaration.setChecked(True);w.preview_mdff()
    p.state.setCurrentIndex(5);p.component.setCurrentText('Tzz');snapshot=p.snapshot
    w.model_box.setCurrentIndex(1);w.atomic_editor.fields['exchange'].setText('.83');w.atomic_editor.preview()
    w.model_box.setCurrentIndex(2);w.manual_tensor.cells.item(2,2).setText('.7');w.preview_mdff()
    for dialog in w.dialogs:dialog.hide()
    w.model_box.setCurrentIndex(0)
    assert w.axis.text()=='1 0 0' and p.snapshot is snapshot and not p.is_stale
    assert p.state.currentIndex()==5 and p.component.currentText()=='Tzz'
    w.model_box.setCurrentIndex(1);assert w.atomic_editor.fields['exchange'].text()=='.83'
    w.model_box.setCurrentIndex(2);assert w.manual_tensor.cells.item(2,2).text()=='.7'
    assert not w.errors


@pytest.mark.parametrize('mode',[0,1,2])
def test_three_model_project_restore_and_preview(window,tmp_path,mode):
    w,app=window;declared_xmcd(w,tmp_path)
    w.model_box.setCurrentIndex(mode)
    cfg=replace(w.forward_settings(),propagation='bloch',energy_scope='edges',grid=9,depth=3,subpixels=4,halfwidth=.7,
        radius=.12,centers=((.2,.2),(.2,-.2)),correction=False,worker_mode='manual',parallel_workers=1)
    settings=Settings(zone=(0,0,1),target=(1,1,0),voltage=200,thickness=.2,tilt=(-5,7),beam_cutoff=.6,potential_cutoff=1.2)
    original=calculate(w.structure,settings,cfg);folder=tmp_path/'project';save_project(original,folder)
    restored=load_project(folder)
    w.model_box.setCurrentIndex((mode+1)%3);w.emcd_result=restored;w.use_result_settings();app.processEvents()
    assert w.model_box.currentIndex()==mode and w.mdff_stack.currentIndex()==mode
    w.preview_mdff()
    if mode==0:
        p=w.xmcd_preview;assert not p.is_stale,p.status.text()
        assert p.snapshot['config'].source_sha256==cfg.source_sha256
        assert 'XMCD-constrained' in w.model_description.text()
    elif mode==1:assert 'CURRENT' in w.atomic_editor.preview_state.text()
    else:assert 'CURRENT' in w.manual_preview_state.text()
    actual=calculate(w.structure,settings,w.forward_settings())
    for key,value in original['spectra'].items():np.testing.assert_array_equal(actual['spectra'][key],value)
    assert not w.errors
