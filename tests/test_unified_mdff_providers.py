"""Independent Part 1B compatibility and element-independent source contracts."""
from dataclasses import asdict,replace
from pathlib import Path
import hashlib,json,subprocess,sys,types
import numpy as np
import pytest
from ase import Atoms
from emcd_sim.gui import generalized_forward as forward
from emcd_sim.gui.geometry import Structure,Settings
from emcd_sim.gui.project_io import config_from_dict,save_project,load_project,rerun_reason
from emcd_sim.imported_mdff import ImportedMDFF,CONVENTION
from emcd_sim.historical_ni import NiLocalConfig,ni_local_transitions
from emcd_sim.mdff_tensor import dipole_tensor_from_transitions
from single_element_helpers import write_source
from test_atomic_ionization import parameter_file


@pytest.mark.parametrize('sign',[1,-1])
@pytest.mark.parametrize('radial',[None,.04,-.04,1e-13])
def test_ni_atomic_against_immutable_part1_implementation(sign,radial):
    name='emcd_sim._part1_atomic_reference'
    module=types.ModuleType(name);module.__package__='emcd_sim';sys.modules[name]=module
    raw=subprocess.check_output(['git','show','52b36ee41e20aed5a86fb37db56ca372fac936f8:src/emcd_sim/ni_local_mdff.py'])
    exec(compile(raw.decode('utf-8-sig'),'immutable_part1_ni_atomic','exec'),module.__dict__)
    cfg=NiLocalConfig(crystal_field_10dq_ev=1.2,exchange_split_ev=.37,eg_up_holes=0,t2g_down_holes=.8)
    old=module.ni_local_transitions(module.NiLocalConfig(**asdict(cfg)),radial_override_angstrom=radial,magnetization_sign=sign)
    new=ni_local_transitions(cfg,radial_override_angstrom=radial,magnetization_sign=sign)
    for key in ('energy_ev','dipoles_angstrom','weights','edge','site'):
        np.testing.assert_array_equal(getattr(old,key),getattr(new,key))
    assert old.source==new.source
    e=np.linspace(840,882,121)
    np.testing.assert_array_equal(dipole_tensor_from_transitions(old,e,.8).tensor_angstrom2_per_ev,
                                  dipole_tensor_from_transitions(new,e,.8).tensor_angstrom2_per_ev)


def oxygen_source(path):
    original=write_source(path)
    d=json.loads(original.read_text());d.update(element='O',edge='K',selected_ev={'K':710.})
    original.write_text(json.dumps(d),encoding='utf-8')
    return original


@pytest.mark.parametrize('channel',['single','double'])
def test_non_3d_single_edge_shared_bw_ms_and_project(tmp_path,channel):
    path=oxygen_source(tmp_path/'synthetic_o_k.json')
    cfg=forward.settings_for_source(path,channeling_model=channel,propagation='both',energy_scope='edges',
        grid=9,depth=9,subpixels=8,fft_grid=16,slice_step=.01,halfwidth=.7,
        centers=((.2,.2),(.2,-.2)),radius=.12,worker_mode='manual',parallel_workers=1)
    structure=Structure(Atoms('O',cell=np.eye(3)*4,scaled_positions=[[0,0,0]],pbc=True),'Synthetic O K algebra test; energies not physical O spectroscopy')
    settings=Settings(zone=(0,0,1),target=(1,0,0),thickness=.2,beam_cutoff=.6,potential_cutoff=1.2)
    assert not forward.material_reason(structure,cfg)
    np.testing.assert_array_equal(forward.energy_grid(cfg),[710.])
    result=forward.calculate(structure,settings,cfg)
    assert set(result['maps'])=={'K'}
    assert set(result['comparison']['edges'])=={'K'}
    for r in result['methods'].values():
        assert np.isfinite(r['spectra']['I_A_plus']).all()
        assert r['spectra']['I_A_plus'].min()>=0
    save_project(result,tmp_path/'project')
    restored=load_project(tmp_path/'project')
    assert set(restored['maps'])=={'K'} and restored['config']==result['config']
    np.testing.assert_array_equal(restored['spectra']['I_A_plus'],result['spectra']['I_A_plus'])


def xmcd_source(tmp_path,element='O',edge='K'):
    e=np.linspace(704,730,17);n=.3+np.exp(-((e-710)/2)**2);m=.04*np.exp(-((e-710)/2)**2)
    path=tmp_path/'original.xmcd';np.savetxt(path,np.column_stack((e,n+m,n-m,2*m,2*n)))
    declaration=dict(element=element,edge=edge,selected_ev={'K':710.},magnetization_crystal=[0,0,1],
        handedness='RP_minus_LP_in_declared_axis',eta=1.,beta=1.,normalization='source_max_nonmagnetic',convention=CONVENTION,
        source='Original synthetic non-3d K-edge fixture',validity='Mathematical software test only; not material spectroscopy',status='synthetic',
        source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),reference_tensor_scale_angstrom2_per_ev=1.,
        magnetic_state='uniform_fm',reversal_assumption='axisymmetric_XMCD_odd_shared_XAS')
    return path,declaration


def test_xmcd_native_input_no_separate_tensor_and_no_global_l23_gate(tmp_path):
    path,declaration=xmcd_source(tmp_path)
    cfg=forward.settings_for_provider(path,'xmcd',declaration,energy_scope='edges')
    assert cfg.ionizing_element=='O' and cfg.core_edge=='K' and Path(cfg.source)==path
    assert config_from_dict(asdict(cfg))==cfg
    a,b=forward.tensors(cfg,[710.],np.eye(3))
    assert a.tensor_angstrom2_per_ev.shape==(1,3,3)
    assert np.linalg.eigvalsh(a.tensor_angstrom2_per_ev).min()>=0
    assert np.any(a.tensor_angstrom2_per_ev!=b.tensor_angstrom2_per_ev)
    path.write_text(path.read_text()+'\n')
    with pytest.raises(ValueError,match='checksum'):forward.source_for(cfg)
    path.unlink()
    with pytest.raises(ValueError,match='Missing'):forward.source_for(cfg)


def test_atomic_original_parameters_identity_and_rejection(tmp_path):
    path=parameter_file(tmp_path/'parameters.json')
    cfg=forward.settings_for_provider(path,'atomic')
    assert cfg.model=='atomic' and cfg.ionizing_element=='Fe'
    assert Path(cfg.source)==path
    assert cfg.source_sha256==hashlib.sha256(path.read_bytes()).hexdigest()
    assert config_from_dict(asdict(cfg))==cfg
    d=json.loads(path.read_text());d['parameters'].update(element='O',atomic_number=8)
    path.write_text(json.dumps(d))
    with pytest.raises(ValueError,match='checksum'):forward.source_for(cfg)
    with pytest.raises(ValueError,match='3d-series'):forward.settings_for_provider(path,'atomic')


@pytest.mark.parametrize('model',['xmcd','atomic'])
def test_imported_identity_cannot_fall_back_to_historical_ni(tmp_path,model):
    cfg=forward.settings_for_source(write_source(tmp_path/'declared.json'))
    changed=replace(cfg,model=model)
    with pytest.raises(ValueError,match='provider identity'):forward.source_for(changed)
    assert 'provider identity' in forward.material_reason(Structure.nickel(),changed)


def test_declared_identity_and_unsupported_edge_rejected(tmp_path):
    cfg=forward.settings_for_provider(parameter_file(tmp_path/'atomic.json'),'atomic')
    with pytest.raises(ValueError,match='identity'):forward.source_for(replace(cfg,model='imported'))
    p=write_source(tmp_path/'tensor.json');d=json.loads(p.read_text());d['edge']='M4,5'
    p.write_text(json.dumps(d))
    with pytest.raises(ValueError,match='Unsupported'):ImportedMDFF.load(p)
