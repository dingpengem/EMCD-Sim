"""Display-only changes preserve computations and project values."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import ast,hashlib,subprocess,json,re,sys
from dataclasses import asdict
import numpy as np
import pytest
from PySide6 import QtWidgets
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
FILES=['gui/app.py','gui/geometry.py','gui/propagation.py','gui/emcd_forward.py','gui/project_io.py','gui/stage_b.py','gui/results.py','gui/prb_benchmark.py','scattering.py']
KERNELS={'single_channeling_tensor.py':'3c47bd37c8da7ec881441cb9cdee66c537b36b86dd2e5b0838251c04ce9e3d61','double_channeling.py':'713945ace6630f95f8b4f461e6c137a8806b60212f744a81aec51cc46fb8f3de','multislice_double_channeling.py':'9ec1ba6c071ff751540f9ef4ac4c864d139cb8a458eb85cddc9ad04ba0a880df'}

class Labels(ast.NodeTransformer):
    def visit_Constant(self,node):
        if isinstance(node.value,str):return ast.copy_location(ast.Constant(value='<label>'),node)
        return node

def test_only_string_literals_changed_no_numeric_or_execution_changes():
    for name in FILES:
        rel='src/emcd_sim/'+name
        old=subprocess.check_output(['git','show','cf8fa647d1cbe7457362f54fbd4ecdce5c65cea5:'+rel],cwd=ROOT).decode('utf-8')
        new=(ROOT/rel).read_text(encoding='utf-8')
        assert ast.dump(Labels().visit(ast.parse(old)))==ast.dump(Labels().visit(ast.parse(new))),name

def test_approved_physics_kernel_bytes_unchanged():
    for name,sha in KERNELS.items():assert hashlib.sha256((ROOT/'src/emcd_sim'/name).read_bytes()).hexdigest()==sha

def test_unit_changes_give_identical_bw_ms_single_double_numerical_arrays():
    d=Path(os.environ.get('EMCD_UNIT_IDENTITY_DIRECTORY',str(ROOT/'outputs/unit_labels')))
    if not all((d/name).is_file() for name in ('baseline.npz','standardized.npz')):
        pytest.skip('Optional external 160-array evidence unavailable; set EMCD_UNIT_IDENTITY_DIRECTORY')
    with np.load(d/'baseline.npz',allow_pickle=False) as old,np.load(d/'standardized.npz',allow_pickle=False) as new:
        assert set(old.files)==set(new.files) and len(old.files)==160
        for key in old.files:np.testing.assert_array_equal(new[key],old[key],err_msg=key)

def test_current_reciprocal_display_strings_and_legacy_project_keys():
    for name in FILES:
        tree=ast.parse((ROOT/'src/emcd_sim'/name).read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant) and isinstance(node.value,str):
                assert not re.search(r'cycles?\s*(?:/|per\s+)(?:angstrom|Å|A)',node.value,re.I),name
    from emcd_sim.gui.geometry import Settings
    import emcd_sim
    assert Path(emcd_sim.__file__).resolve().is_relative_to(ROOT/'src')
    from emcd_sim.gui.emcd_forward import ForwardSettings
    from emcd_sim.gui.project_io import settings_from_dict,config_from_dict
    s=Settings();cfg=ForwardSettings()
    assert settings_from_dict(json.loads(json.dumps(asdict(s))))==s
    assert config_from_dict(json.loads(json.dumps(asdict(cfg))))==cfg
    # Compatibility names are intentionally not renamed or numerically converted.
    src=(ROOT/'src/emcd_sim/gui/prb_benchmark.py').read_text(encoding='utf-8')
    assert 'detector_centres_cycles_per_angstrom=' in src and 'aperture_radius_cycles_per_angstrom=' in src

def test_gui_units_do_not_start_workers(tmp_path):
    from emcd_sim.gui.app import MainWindow,PreviewWorker
    from emcd_sim.gui.stage_b import EMCDWorker
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    with patch.object(PreviewWorker,'start') as elastic,patch.object(EMCDWorker,'start') as inelastic:
        w=MainWindow(workspace=tmp_path)
        assert [w.table.horizontalHeaderItem(i).text() for i in range(1,4)]==['qx (Å⁻¹)','qy (Å⁻¹)','s_g (Å⁻¹)']
        assert w.spin['kv'].value()==300 and w.spin['slice_step'].value()==2.
        w.refresh();elastic.assert_not_called();inelastic.assert_not_called();w.close();w.deleteLater();app.processEvents()

def test_current_guides_explain_reciprocal_conventions_without_rescaling():
    paths=['README.md','docs/USER_GUIDE.md','docs/QUICK_START.md','docs/ARCHITECTURE.md','docs/ROADMAP.md','docs/SINGLE_CHANNELING_QUANTITATIVE.md','docs/SINGLE_CHANNELING_TENSOR.md','docs/NI_017_CASE_STUDY_GUIDE.md','docs/PHYSICAL_UNITS.md']
    for name in paths:
        text=(ROOT/name).read_text(encoding='utf-8');assert not re.search(r'cycles?\s*(?:/|per\s+)(?:angstrom|Å|A)',text,re.I),name
    text=(ROOT/'docs/PHYSICAL_UNITS.md').read_text(encoding='utf-8')
    assert '|g_hkl| = 1/d_hkl' in text and 'Q = 2πg' in text and 'never adds another conversion' in text

def test_historical_windows_identity_and_original_units_preserved():
    rel='docs/WINDOWS_BETA_3.md'
    old=subprocess.check_output(['git','show','cf8fa647d1cbe7457362f54fbd4ecdce5c65cea5:'+rel],cwd=ROOT).decode('utf-8')
    new=(ROOT/rel).read_text(encoding='utf-8')
    for line in old.splitlines():
        if any(k in line for k in ('Package version:','Windows numeric','Defaults remain')):assert line in new
    assert 'not present in this executable' in new and 'separately approved' in new

@pytest.mark.parametrize('mutation',['number','call','branch','unapproved_label'])
def test_metadata_alias_guard_rejects_computational_or_unapproved_changes(mutation):
    import copy
    from unit_metadata_guard import normalize_unit_metadata,RECIPROCAL
    original=ast.parse((ROOT/'src/emcd_sim/gui/emcd_forward.py').read_text(encoding='utf-8'))
    changed=copy.deepcopy(original)
    if mutation=='number':
        node=next(n for n in ast.walk(changed) if isinstance(n,ast.Constant) and type(n.value) in (int,float))
        node.value+=123
    elif mutation=='call':
        node=next(n for n in ast.walk(changed) if isinstance(n,ast.Call));node.func=ast.Name(id='unapproved_call',ctx=ast.Load())
    elif mutation=='branch':
        node=next(n for n in ast.walk(changed) if isinstance(n,ast.If));node.test=ast.Constant(value=False)
    else:
        node=next(n for n in ast.walk(changed) if isinstance(n,ast.Constant) and n.value==RECIPROCAL[0]);node.value='unapproved unit convention'
    assert ast.dump(normalize_unit_metadata(changed))!=ast.dump(normalize_unit_metadata(original))
