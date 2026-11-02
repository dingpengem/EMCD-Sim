"""Version, package provenance and legacy interpretation; no kernel changes."""
import copy
from pathlib import Path
import re
import ast
import subprocess

from emcd_sim import __version__, __display_version__
from emcd_sim.gui.runtime import PHYSICS_CONVENTION, build_info, result_convention_status

ROOT=Path(__file__).resolve().parents[1]


def test_forward_computation_ast_is_unchanged_except_three_metadata_keys():
    path='src/emcd_sim/gui/emcd_forward.py'
    old=ast.parse(subprocess.check_output(['git','show','4f57815646d023957a81ad15fdaa684c02a54442:'+path],cwd=ROOT).decode('utf-8-sig'))
    current=ast.parse((ROOT/path).read_text(encoding='utf-8-sig'))
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


def test_v070_windows_and_workflow_metadata_match_source():
    assert (__version__,__display_version__)==('0.7.0b1','v0.7.0-beta.1')
    text=(ROOT/'packaging/windows_version_info.txt').read_text()
    assert 'filevers=(0, 7, 0, 1), prodvers=(0, 7, 0, 1)' in text
    assert "'FileVersion', '0.7.0.1'" in text and "'ProductVersion', 'v0.7.0-beta.1'" in text
    workflow=(ROOT/'.github/workflows/windows-build.yml').read_text()
    assert 'EMCD-Sim-v0.7.0-beta.1-Windows' in workflow
    assert 'build/windows-v0.7.0-beta.1' in workflow
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
