"""Configuration-only acceptance: scientific propagation is forbidden throughout."""
import json
from contextlib import ExitStack
from dataclasses import asdict,replace
from pathlib import Path
from unittest.mock import patch,Mock
import numpy as np
import pytest
from PySide6 import QtWidgets
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.geometry import Settings,Structure
from emcd_sim.gui.emcd_forward import ForwardSettings
from emcd_sim.gui.numerical_settings import resolve_parameters,REFERENCE_SOURCE_SHA256
from emcd_sim.gui.project_io import load_project,save_project
from emcd_sim.gui.propagation import numerical_info


@pytest.fixture
def window(tmp_path):
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    with ExitStack() as stack:
        for name in ('emcd_sim.gui.emcd_forward.calculate','emcd_sim.gui.stage_b.calculate',
                     'emcd_sim.gui.app.PreviewWorker.run','emcd_sim.gui.stage_b.EMCDWorker.run',
                     'emcd_sim.gui.propagation.propagate','emcd_sim.gui.channeling.double_channeling_response',
                     'emcd_sim.gui.channeling.multislice_double_channeling_response'):
            stack.enter_context(patch(name,side_effect=AssertionError('Unexpected scientific solve')))
        w=MainWindow(workspace=tmp_path/'workspace');w.model_box.setCurrentIndex(1)
        yield w
        w.close();app.processEvents()


def reference_config(**kwargs):
    return replace(ForwardSettings(),source_sha256=REFERENCE_SOURCE_SHA256,axis_declared=True,l3=831.4778,**kwargs)


@pytest.mark.parametrize('minimum',[38,130])
def test_fft_selection_never_truncates_or_exceeds_supported_mesh(monkeypatch,minimum):
    calls=[]
    def support(structure,settings,cfg,**kwargs):
        calls.append((settings,cfg));assert kwargs['check_memory'] is False
        if cfg.fft_grid<minimum:raise ValueError('Unsafe FFT Nyquist boundary')
        return {}
    monkeypatch.setattr('emcd_sim.gui.propagation.numerical_info',support)
    cfg=replace(ForwardSettings(),propagation='both')
    if minimum>128:
        with pytest.raises(ValueError,match='Automatic FFT setup unavailable'):
            resolve_parameters(Structure.nickel(),Settings(),cfg)
    else:
        values,_=resolve_parameters(Structure.nickel(),Settings(),cfg)
        assert values['fft_grid']==minimum
    assert [c.fft_grid for s,c in calls]==list(range(32,min(minimum,128)+1,2))
    assert all(s.beam_cutoff==3.0 and s.potential_cutoff==2.0 and c.depth==64 and c.slice_step==.04 for s,c in calls)


def test_pure_resolution_never_calls_scientific_solvers():
    with ExitStack() as stack:
        for name in ('emcd_sim.gui.propagation.propagate','emcd_sim.gui.emcd_forward.calculate',
                     'emcd_sim.gui.channeling.double_channeling_response',
                     'emcd_sim.gui.channeling.multislice_double_channeling_response',
                     'numpy.linalg.eigh'):
            stack.enter_context(patch(name,side_effect=AssertionError('Unexpected scientific solve')))
        for method in ('bloch','fft-multislice','both'):
            resolve_parameters(Structure.nickel(),Settings(),reference_config(propagation=method))


@pytest.mark.parametrize('method',['bloch','fft-multislice','both'])
@pytest.mark.parametrize('channel',['single','double'])
def test_reference_selection_and_fft_support(method,channel):
    cfg=reference_config(propagation=method,channeling_model=channel)
    reference=replace(Settings(),voltage=200,tilt=(-7.116725439974256,0))
    values,meta=resolve_parameters(Structure.nickel(),reference,cfg)
    assert (values['beam'],values['potential'],values['fft_grid'],values['depth'],values['slice_step'])==(4.6,6.2,48,257,.04)
    assert meta['source']=='Matching reference configuration'
    s=replace(reference,beam_cutoff=values['beam'],potential_cutoff=values['potential'])
    numerical_info(Structure.nickel(),s,replace(cfg,fft_grid=48,depth=257),check_memory=False)


@pytest.mark.parametrize('settings,cfg',[
    (replace(Settings(),thickness=31),reference_config()),
    (replace(Settings(),voltage=300),reference_config()),
    (replace(Settings(),tilt=(-7,0)),reference_config()),
    (replace(Settings(),b_factor=.1),reference_config()),
    (Settings(),replace(reference_config(),source_sha256='other')),
    (Settings(),replace(reference_config(),magnetization=(1,0,0))),
    (Settings(),replace(reference_config(),centers=((0,0),(0,0)))),
    (Settings(),replace(reference_config(),radial=.05)),
    (Settings(),replace(reference_config(),l3=852.7)),
])
def test_unmatched_never_claims_convergence(settings,cfg):
    values,meta=resolve_parameters(Structure.nickel(),settings,cfg)
    assert values['beam']==3.0 and values['potential']==2.0
    assert 'convergence not established' in meta['status']


def test_unsupported_geometry_no_fallback():
    # The full basis admission cap can reject this geometry even before the
    # MS geometry gate; neither rejection may truncate beams or switch engines.
    with pytest.raises(ValueError,match='FFT EMCD supports verified|interactive limit'):
        resolve_parameters(Structure.nickel(),replace(Settings(),zone=(0,1,1)),replace(ForwardSettings(),propagation='both'))


def test_auto_defaults_display_and_no_solvers(window):
    w=window
    assert w.numerical_mode.currentIndex()==0
    assert w.shared_sampling_group.isHidden() and not w.shared_resources_group.isHidden()
    assert not w.spin['beam'].isEnabled() and not w.spin['fft_grid'].isEnabled()
    assert w.spin['grid'].value()==97 and w.memory_budget.currentData()==2048
    assert 'FFT grid' not in w.numerical_values.text()
    for index in (1,2,0):
        w.propagation_box.setCurrentIndex(index)
        assert not w._numerical_error
        cfg=w.forward_settings();actual=w.numerical_snapshot()
        assert cfg.depth==actual['depth'] and cfg.grid==actual['grid'] and cfg.fft_grid==actual['fft_grid']
        assert ('FFT grid' in w.numerical_values.text())==(index!=0)
        assert w.ms_settings_group.isHidden()
    w.new_project();assert w.numerical_mode.currentIndex()==0


def test_manual_roundtrip_preserves_physics_and_overrides(window):
    w=window;original=w.numerical_snapshot();physical=w.settings()
    w.numerical_mode.setCurrentIndex(1);assert w.numerical_snapshot()==original
    w.spin['beam'].setValue(2.8);w.spin['potential'].setValue(2.4);w.spin['depth'].setValue(33)
    w.spin['grid'].setValue(65);w.memory_budget.setCurrentIndex(0)
    manual=w.numerical_snapshot();cfg=w.forward_settings()
    for i in (1,2,0):w.propagation_box.setCurrentIndex(i)
    assert w.numerical_snapshot()==manual
    w.numerical_mode.setCurrentIndex(0)
    assert w.spin['grid'].value()==97 and w.spin['beam'].value()==3.0
    w.numerical_mode.setCurrentIndex(1)
    assert w.numerical_snapshot()==manual and w.forward_settings()==cfg
    assert replace(w.settings(),beam_cutoff=physical.beam_cutoff,potential_cutoff=physical.potential_cutoff)==physical
    assert w.spin['depth'].isEnabled()


def test_refresh_cache_and_invalid_text(window,monkeypatch):
    import emcd_sim.gui.numerical_settings as ns
    original=ns.resolve_parameters;calls=[]
    def capture(*args):calls.append(args);return original(*args)
    monkeypatch.setattr(ns,'resolve_parameters',capture)
    window.resolve_numerical_ui();window.resolve_numerical_ui();assert not calls
    window.spin['thickness'].setValue(31);assert len(calls)==1
    before=window.numerical_snapshot();window.zone.setText('0 ')
    assert window._numerical_error and 'unavailable' in window.numerical_status.text()
    assert window.numerical_snapshot()==before and not window.emcd_button.isEnabled()
    window.zone.setText('0 1 7');window.refresh();assert not window._numerical_error


@pytest.mark.parametrize('mode',['automatic','manual'])
def test_project_roundtrip_metadata_and_arrays(window,tmp_path,mode):
    from emcd_sim.gui.stage_f_acceptance import fingerprints
    path=Path('outputs/v060_release/source_native/single_both_project')
    if not path.exists():pytest.skip('Saved project fixture unavailable')
    result=load_project(path);before=fingerprints(result)
    # No solver: store UI provenance alongside an existing saved result.
    selection=dict(mode=mode,actual=dict(beam=result['settings'].beam_cutoff),
                   manual_overrides=window.numerical_snapshot(),provenance=dict(source='Saved configuration',status='Retained saved parameters'))
    result['metadata']['numerical_selection']=selection
    destination=tmp_path/'saved';save_project(result,destination)
    loaded=load_project(destination)
    assert loaded['metadata']['numerical_selection']==json.loads(json.dumps(selection))
    assert fingerprints(loaded)==before
    window.emcd_result=loaded;window.use_result_settings()
    assert window.numerical_mode.currentIndex()==(0 if mode=='automatic' else 1)
    assert window.settings()==loaded['settings'] and window.forward_settings()==loaded['config']


def test_legacy_keeps_explicit_manual(window):
    path=Path('outputs/v060_release/source_native/single_both_project')
    if not path.exists():pytest.skip('Saved project fixture unavailable')
    result=load_project(path);assert 'numerical_selection' not in result['metadata']
    window.emcd_result=result;window.use_result_settings()
    assert window.numerical_mode.currentIndex()==1
    assert window.settings()==result['settings'] and window.forward_settings()==result['config']


def test_memory_rejection_does_not_lower_settings(window,monkeypatch):
    import emcd_sim.gui.propagation as prop
    before=window.numerical_snapshot()
    monkeypatch.setattr(prop,'numerical_info',Mock(side_effect=ValueError('Estimated process peak exceeds 2048 MiB budget')))
    window.emcd_stale()
    assert not window.emcd_button.isEnabled() and '2048 MiB' in window.memory_label.text()
    assert window.numerical_snapshot()==before


def test_run_starts_one_worker_only(window,monkeypatch):
    import emcd_sim.gui.stage_b as sb
    worker=Mock();worker.isInterruptionRequested.return_value=False
    factory=Mock(return_value=worker);monkeypatch.setattr(sb,'EMCDWorker',factory)
    window.start_emcd();assert factory.call_count==1 and worker.start.call_count==1
    window.start_emcd();assert factory.call_count==1
    window.busy=False;window.worker=None
