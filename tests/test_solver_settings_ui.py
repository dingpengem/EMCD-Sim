"""Configuration-level regression for shared/solver-specific UI; no propagation."""
import os,sys,types,subprocess,json,ast
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from contextlib import ExitStack
from dataclasses import asdict,replace
from pathlib import Path
from unittest.mock import patch
import pytest
from PySide6 import QtWidgets
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.project_io import config_from_dict,load_project
from emcd_sim.gui.propagation import numerical_info
from emcd_sim.gui.geometry import Structure,Settings
from emcd_sim.gui.emcd_forward import ForwardSettings

BASE='2ede25e63827830617b335a4df6d9d521ac65a9b'

@pytest.fixture(scope='module')
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

@pytest.fixture
def window(app,tmp_path):
    with ExitStack() as guards:
        for name in ('emcd_sim.gui.emcd_forward.calculate','emcd_sim.gui.app.PreviewWorker.run','emcd_sim.gui.stage_b.EMCDWorker.run','emcd_sim.gui.channeling.double_channeling_response','emcd_sim.gui.channeling.multislice_double_channeling_response'):
            guards.enter_context(patch(name,side_effect=AssertionError('No propagation allowed in presentation tests')))
        w=MainWindow(workspace=tmp_path/'workspace');w.numerical_mode.setCurrentIndex(1);w.model_box.setCurrentIndex(1)
        try:yield w
        finally:w.close();app.processEvents()

def baseline_window(path):
    # Execute the exact released GUI controls, with only their module names
    # isolated, to compare complete configs rather than selected values.
    modules=[]
    for name,filename in (('_baseline_stage_b','stage_b.py'),('_baseline_app','app.py')):
        source=subprocess.check_output(['git','show',BASE+':src/emcd_sim/gui/'+filename]).decode('utf-8-sig')
        if filename=='app.py':source=source.replace('from .stage_b import StageB','from ._baseline_stage_b import StageB')
        module=types.ModuleType('emcd_sim.gui.'+name);module.__package__='emcd_sim.gui';module.__file__=str(Path('src/emcd_sim/gui')/filename)
        sys.modules[module.__name__]=module;exec(compile(source,module.__file__,'exec'),module.__dict__);modules.append(module)
    return modules[-1].MainWindow(workspace=path)

@pytest.mark.parametrize('channeling',[0,1])
def test_released_configuration_exactly_preserved(window,tmp_path,app,channeling):
    old=baseline_window(tmp_path/'released');old.model_box.setCurrentIndex(1)
    try:
        # Defaults intentionally changed; compare the same explicit legacy inputs.
        legacy=old.settings()
        window.set_values(dict(kv=legacy.voltage,tx=legacy.tilt[0],ty=legacy.tilt[1],beam=legacy.beam_cutoff,potential=legacy.potential_cutoff));window.refresh()
        assert window.settings()==old.settings()
        assert window.forward_settings()==old.forward_settings()
        for w in (old,window):
            w.set_values(dict(beam=2.8,potential=2.4,b=.15,grid=65,depth=33,subpixels=24,halfwidth=.75,fft_grid=48,slice_step=.025,energy=51,window_lo=877,window_hi=881))
            w.memory_budget.setCurrentIndex(w.memory_budget.findData(4096));w.channeling_box.setCurrentIndex(channeling)
        for method in (0,1,0,2,1):
            old.propagation_box.setCurrentIndex(method);window.propagation_box.setCurrentIndex(method)
            assert window.settings()==old.settings()
            assert window.forward_settings()==old.forward_settings()
            cfg=window.forward_settings();assert config_from_dict(json.loads(json.dumps(asdict(cfg))))==cfg
    finally:old.close();app.processEvents()

@pytest.mark.parametrize('selection',[0,1,2])
def test_solver_visibility_and_classification(window,selection):
    window.propagation_box.setCurrentIndex(selection)
    assert window.ms_settings_group.isHidden()==(selection==0)
    assert window.ms_settings_group.isEnabled()==(selection!=0)
    for group in (window.shared_elastic_group,window.shared_sampling_group,window.shared_resources_group):assert not group.isHidden()
    assert 'No additional BW-only' in window.solver_note.text() if selection==0 else 'FFT controls' in window.solver_note.text()
    window.refresh()
    assert 'Additional FFT harmonics' in window.spin['beam'].toolTip()
    for key in ('beam','potential'):assert window.spin[key].parentWidget()==window.shared_elastic_group
    for key in ('energy','grid','depth','subpixels','halfwidth'):assert window.spin[key].parentWidget()==window.shared_sampling_group
    for key in ('fft_grid','slice_step'):assert window.ms_settings_group.isAncestorOf(window.spin[key])
    assert window.memory_budget.parentWidget()==window.shared_resources_group
    assert 'analytic' in window.spin['depth'].toolTip() and 'numerical' in window.spin['depth'].toolTip()
    assert 'not a required allocation' in window.memory_budget.toolTip()


def test_switching_updates_real_memory_estimates_without_mutating_settings(window,monkeypatch):
    import emcd_sim.gui.propagation as propagation
    original=propagation.numerical_info;calls=[]
    def capture(*args,**kwargs):
        cfg=args[2];value=original(*args,**dict(kwargs,check_memory=False));calls.append((cfg,value))
        value.update(estimated_process_peak_mib=value['estimated_working_mib']+128,available_ram_mib=32000)
        return value
    monkeypatch.setattr(propagation,'numerical_info',capture)
    expected=window.forward_settings();settings=window.settings()
    window.spin['fft_grid'].setValue(48);window.spin['slice_step'].setValue(.025);expected=window.forward_settings()
    for index,method in ((0,'bloch'),(1,'fft-multislice'),(0,'bloch'),(2,'both'),(1,'fft-multislice')):
        window.propagation_box.setCurrentIndex(index);window.emcd_stale()
        assert window.forward_settings()==replace(expected,propagation=method)
        assert window.settings()==settings
        assert calls[-1][0].propagation==method
        assert ('0 FFT harmonics' in window.memory_label.text())==(method=='bloch')
        assert 'Retained beams:' in window.memory_label.text()
    assert any(v['fft_storage_working_mib']>0 for c,v in calls if c.propagation!='bloch')


def test_invalid_ms_geometry_remains_rejected(window):
    # Stay below the independent interactive beam cap to reach the MS guard.
    window.spin['beam'].setValue(.9)
    window.zone.setText('0 1 1');window.propagation_box.setCurrentIndex(1);window.emcd_stale()
    assert 'FFT EMCD supports Ni [017], [117]' in window.memory_label.text()
    assert not window.emcd_button.isEnabled()
    assert window.forward_settings().propagation=='fft-multislice'
    with pytest.raises(ValueError,match='FFT EMCD supports Ni'):
        numerical_info(Structure.nickel(),replace(Settings(),zone=(0,1,1),beam_cutoff=.9),replace(ForwardSettings(),propagation='fft-multislice'),check_memory=False)


def test_saved_settings_and_arrays_preserved_without_solver(window):
    path=Path('outputs/v060_release/source_native/single_both_project')
    if not path.exists():pytest.skip('Optional saved GUI reference unavailable')
    from runtime_fixtures import fingerprints
    saved=load_project(path);before=fingerprints(saved)
    cfg=replace(saved['config'],propagation='fft-multislice',grid=65,memory_budget_mib=512,fft_grid=48,slice_step=.025)
    window.emcd_result=dict(saved,config=cfg);window.use_result_settings()
    assert not window.ms_settings_group.isHidden()
    assert window.forward_settings()==cfg
    for i in (0,2,1):window.propagation_box.setCurrentIndex(i)
    assert window.forward_settings()==cfg and fingerprints(saved)==before


def test_solver_configuration_and_physics_unchanged():
    current=ast.parse(Path('src/emcd_sim/gui/stage_b.py').read_text(encoding='utf-8-sig'))
    old=ast.parse(subprocess.check_output(['git','show',BASE+':src/emcd_sim/gui/stage_b.py']).decode('utf-8-sig'))
    find=lambda tree,name:next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name)
    method=find(current,'forward_settings')
    for node in ast.walk(method):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='ForwardSettings':
            node.keywords=[k for k in node.keywords if k.arg not in ('worker_mode','parallel_workers')]
    assert ast.dump(method)==ast.dump(find(old,'forward_settings'))
    # The energy-support scheduler is now intentionally in emcd_forward/channeling.
    # Protect configuration, tensor construction and energy selection independently
    # of that scheduling change, plus byte-identical propagation/physics modules.
    path='src/emcd_sim/gui/emcd_forward.py'
    current_forward=ast.parse(Path(path).read_text(encoding='utf-8-sig'))
    old_forward=ast.parse(subprocess.check_output(['git','show',BASE+':'+path]).decode('utf-8-sig'))
    for name in ('energy_grid','tensors','axis_rotation','material_reason'):
        assert ast.dump(find(current_forward,name))==ast.dump(find(old_forward,name))
    # MS advance/response buffer reuse is covered by strict baseline comparisons
    # in test_ms_double_buffers; retain AST guards on its unchanged formulation.
    path='src/emcd_sim/multislice_double_channeling.py'
    ms_current=ast.parse(Path(path).read_text(encoding='utf-8-sig'))
    ms_old=ast.parse(subprocess.check_output(['git','show',BASE+':'+path]).decode('utf-8-sig'))
    for name in ('transition_modes','depth_quadrature','propagate_slices','forward_event_amplitudes','incident_fields'):
        assert ast.dump(find(ms_current,name))==ast.dump(find(ms_old,name))
    # ProjectedNiFFT deliberately gained an opt-in two-beam subspace. Keep the
    # unchanged index mapping guard; default-plan arrays/diagnostics are compared
    # bit-for-bit with archived code in test_ms_double_buffers for [001]/[017].
    assert ast.dump(find(ms_current,'indices'))==ast.dump(find(ms_old,'indices'))
    path='src/emcd_sim/gui/propagation.py'
    now=ast.parse(Path(path).read_text(encoding='utf-8-sig'));before=ast.parse(subprocess.check_output(['git','show',BASE+':'+path]).decode('utf-8-sig'))
    for node in before.body:
        if isinstance(node,ast.FunctionDef) and node.name not in ('numerical_info','propagate'):assert ast.dump(find(now,node.name))==ast.dump(node)
    # Existing persistence is unchanged except the explicit old-[117] rerun guard.
    path='src/emcd_sim/gui/project_io.py'
    present=ast.parse(Path(path).read_text(encoding='utf-8-sig'))
    archived=ast.parse(subprocess.check_output(['git','show',BASE+':'+path]).decode('utf-8-sig'))
    additions=('fingerprints','frame_rerun_reason','rerun_reason')
    present.body=[n for n in present.body if not (isinstance(n,ast.FunctionDef) and n.name in additions)]
    archived.body=[n for n in archived.body if not (isinstance(n,ast.FunctionDef) and n.name=='rerun_reason')]
    assert ast.dump(present)==ast.dump(archived)
    for path in ('src/emcd_sim/double_channeling.py','src/emcd_sim/single_channeling_tensor.py'):
        assert Path(path).read_text(encoding='utf-8-sig').replace('\r\n','\n')==subprocess.check_output(['git','show',BASE+':'+path]).decode('utf-8-sig').replace('\r\n','\n')
