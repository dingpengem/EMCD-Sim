"""Version, package provenance and legacy interpretation; no kernel changes."""
import copy
from pathlib import Path
import re
import ast
import subprocess

from emcd_sim import __version__, __display_version__
from emcd_sim.gui.runtime import PHYSICS_CONVENTION, build_info, result_convention_status

ROOT=Path(__file__).resolve().parents[1]


def test_forward_computation_ast_is_unchanged_except_approved_metadata_and_prior_material_gate():
    path='src/emcd_sim/gui/emcd_forward.py'
    old=ast.parse(subprocess.check_output(['git','show','4f57815646d023957a81ad15fdaa684c02a54442:'+path],cwd=ROOT).decode('utf-8-sig'))
    current=ast.parse((ROOT/path).read_text(encoding='utf-8-sig'))
    # Part 1C relocates compatibility functions, retaining each body exactly.
    # The new wrappers and complete current scope are checked independently.
    accepted=ast.parse(subprocess.check_output(['git','show','98570c62:'+path],cwd=ROOT).decode('utf-8-sig'))
    relocated=ast.parse((ROOT/'src/emcd_sim/historical_ni.py').read_text(encoding='utf-8-sig'))
    orientation=ast.parse((ROOT/'src/emcd_sim/mdff_orientation.py').read_text(encoding='utf-8-sig'))
    moved=('material_reason','axis_rotation','tensors','energy_grid')
    for name in moved:
        find_function=lambda tree:next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
        actual=copy.deepcopy(find_function(orientation if name=='axis_rotation' else relocated))
        if name=='material_reason':
            expected_import=ast.parse('from .gui.geometry import Structure').body[0]
            assert ast.dump(actual.body[0])==ast.dump(expected_import)
            actual.body.pop(0)
        assert ast.dump(actual)==ast.dump(find_function(accepted))
    # Aliases replace the four functions. Restore only these reviewed moves and
    # the import inventory before applying the earlier complete computation guard.
    remaining=[n for n in current.body if not isinstance(n,(ast.Import,ast.ImportFrom))]
    current.body=[];it=iter(remaining)
    for n in accepted.body:
        if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in moved:
            current.body.append(copy.deepcopy(n))
        else:current.body.append(next(it))
    assert list(it)==[]

    # Retain the complete computation guard: allow only the exact new metadata
    # import/expression, plus the already approved d1c93ba Ni species gate.
    previous=ast.parse(subprocess.check_output(['git','show','d1c93ba:'+path],cwd=ROOT).decode('utf-8-sig'))
    find=lambda tree,name:next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    # Part 1B moves orchestration, not contraction physics. Check the exact
    # compatibility wrapper and the complete new source scope independently,
    # then retain this earlier metadata-only guard on all remaining functions.
    part1=ast.parse(subprocess.check_output(['git','show','52b36ee41e20aed5a86fb37db56ca372fac936f8:'+path],cwd=ROOT).decode('utf-8-sig'))
    wrapper=ast.parse('''def _calculate(structure,settings,cfg,progress,cancelled,*,energy_ev=None,energy_checkpoint=None,execution_policy=None):
    """Historical API delegates to the common production orchestration."""
    from .forward_pipeline import calculate_prepared
    return calculate_prepared(structure,settings,cfg,progress,cancelled,energy_ev=energy_ev,
        energy_checkpoint=energy_checkpoint,execution_policy=execution_policy)
''').body[0]
    assert ast.dump(find(current,'_calculate'))==ast.dump(wrapper)
    from single_element_source_guard import assert_current_extension
    assert_current_extension()
    # The dynamic selection change is separately tested end to end for K and
    # L2,3; enforce its exact body rather than dropping the metrics guard.
    expected_metrics=copy.deepcopy(find(part1,'metrics'))
    expected_metrics.body.insert(2,ast.parse('from ..mdff_edges import selected_samples').body[0])
    loop=next(n for n in expected_metrics.body if isinstance(n,ast.For))
    loop.iter=ast.parse("selected_samples(result['config'])",mode='eval').body
    assert ast.dump(find(current,'metrics'))==ast.dump(expected_metrics)
    expected_calculate=copy.deepcopy(find(part1,'calculate'))
    expected_calculate.body[1:1]=ast.parse('from .forward_pipeline import validate_before_resources\nvalidate_before_resources(structure,settings,cfg,energy_ev)').body
    assert ast.dump(find(current,'calculate'))==ast.dump(expected_calculate)
    for name in ('_calculate','metrics','calculate'):
        current.body[current.body.index(find(current,name))]=copy.deepcopy(find(part1,name))
    assert ast.dump(find(current,'material_reason'))==ast.dump(find(previous,'material_reason'))
    current.body[current.body.index(find(current,'material_reason'))]=copy.deepcopy(find(old,'material_reason'))
    contract=find(current,'_contract')
    stages=[n for n in ast.walk(contract) if isinstance(n,ast.Constant) and n.value=='Computing selected-edge map decomposition and post-edge diagnostics']
    assert len(stages)==1
    stages[0].value='Computing L3/L2 map decomposition and post-edge diagnostics'
    imports=[n for n in contract.body if isinstance(n,ast.ImportFrom) and n.module=='elastic_providers']
    expected_import=ast.parse('from ..elastic_providers import provider_provenance').body[0]
    assert len(imports)==1 and ast.dump(imports[0])==ast.dump(expected_import)
    contract.body.remove(imports[0])
    provider_keys=[(n,k) for n in ast.walk(contract) if isinstance(n,ast.Call) for k in n.keywords if k.arg=='elastic_provider']
    assert len(provider_keys)==1
    call,key=provider_keys[0]
    expected=ast.parse('provider_provenance(model.elastic.crystal.species,settings.elastic_provider)',mode='eval').body
    assert isinstance(call.func,ast.Name) and call.func.id=='dict' and ast.dump(key.value)==ast.dump(expected)
    call.keywords.remove(key)
    removed=[]
    for node in ast.walk(current):
        if isinstance(node,ast.Call):
            retained=[]
            for item in node.keywords:
                if item.arg in {'software_version','software_display_version','physics_convention'}:
                    removed.append(item.arg)
                else:retained.append(item)
            node.keywords=retained
    assert sorted(removed)==['physics_convention','software_display_version','software_version']
    from unit_metadata_guard import normalize_unit_metadata
    assert ast.dump(normalize_unit_metadata(current))==ast.dump(old)


def test_current_windows_and_workflow_metadata_match_source():
    assert (__version__,__display_version__)==('0.8.1b2','v0.8.1-beta.2')
    text=(ROOT/'packaging/windows_version_info.txt').read_text()
    assert 'filevers=(0, 8, 1, 2), prodvers=(0, 8, 1, 2)' in text
    assert "'FileVersion', '0.8.1.2'" in text and "'ProductVersion', 'v0.8.1-beta.2'" in text
    workflow=(ROOT/'.github/workflows/windows-build.yml').read_text()
    assert 'EMCD-Sim-v0.8.1-beta.2-Windows' in workflow
    assert 'build/windows-v0.8.1-beta.2' in workflow
    assert not re.search(r'beta3|beta\.3|0\.6\.1b3',workflow)
    assert build_info()['physics_convention']==PHYSICS_CONVENTION


def test_missing_convention_is_unknown_and_metadata_is_not_rewritten():
    data={'software_version':'0.6.1b3','software_commit':'original','source_audit':{'sha256':'original-source'}}
    before=copy.deepcopy(data)
    status=result_convention_status(data)
    assert status['status']=='unknown-or-legacy-unverified' and status['identifier'] is None
    assert 'preserved' in status['warning'] and data==before


def test_explicit_old_convention_is_preserved_and_warned():
    data={'physics_convention':'legacy_same_index_h_minus_g','software_version':'0.6.1b3'}
    before=dict(data);status=result_convention_status(data)
    assert status['identifier']==data['physics_convention'] and status['status']=='recorded-other'
    assert status['warning'] and data==before


def test_explicit_corrected_convention_is_recorded_not_inferred_from_version():
    status=result_convention_status({'physics_convention':PHYSICS_CONVENTION,'software_version':'0.7.0b1'})
    assert status['status']=='recorded-corrected' and status['warning'] is None


def test_old_project_roundtrip_preserves_arrays_and_provenance(tmp_path):
    from emcd_sim.gui.project_io import load_project, save_project, fingerprints
    reference=ROOT/'outputs/v060_release/source_native/single_both_project'
    if not reference.exists():
        import pytest
        pytest.skip('Optional historical saved project is unavailable')
    result=load_project(reference);before=fingerprints(result);old=copy.deepcopy(result['metadata'])
    assert result['project_convention_status']['status']=='unknown-or-legacy-unverified'
    assert any('legacy-unverified' in v for v in result['project_warnings'])
    save_project(result,tmp_path/'legacy_copy');opened=load_project(tmp_path/'legacy_copy')
    assert fingerprints(opened)==before and opened['metadata']==old
    assert sum('legacy-unverified' in v for v in opened['project_warnings'])==1


def test_new_calculation_records_convention_and_roundtrips_without_relabeling(tmp_path):
    import numpy as np
    from emcd_sim.gui.geometry import Structure, Settings
    from emcd_sim.gui.emcd_forward import ForwardSettings, calculate
    from emcd_sim.gui.project_io import load_project, save_project, fingerprints
    settings=Settings(zone=(0,0,1),thickness=.5,beam_cutoff=.9,potential_cutoff=1.8)
    config=ForwardSettings(axis_declared=True,grid=9,depth=5,subpixels=4,halfwidth=.5,
                           angular_maps=False,correction=False,energy_scope='edges')
    result=calculate(Structure.nickel(),settings,config,energy_ev=np.array([config.l3,config.l2]))
    assert result['metadata']['software_version']==__version__
    assert result['metadata']['physics_convention']==PHYSICS_CONVENTION
    before=fingerprints(result)
    save_project(result,tmp_path/'new_project')
    opened=load_project(tmp_path/'new_project')
    assert fingerprints(opened)==before
    assert opened['project_convention_status']['status']=='recorded-corrected'
