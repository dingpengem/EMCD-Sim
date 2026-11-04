"""Part 1C equivalence against immutable accepted source, not regenerated fixtures."""
from dataclasses import asdict
import subprocess, sys, types
import numpy as np
import pytest
from emcd_sim.ni_local_mdff import NiLocalConfig, ni_local_transitions
from emcd_sim.atomic_ionization import transitions_for_material
from emcd_sim.atomic_dipole import dipole_2p_to_3d
from emcd_sim.ionization_sites import single_site_phase_matrix


def accepted_module(path, name):
    package='emcd_sim.gui' if path.startswith('gui/') else 'emcd_sim'
    module=types.ModuleType(package+'.'+name)
    module.__package__=package;sys.modules[module.__name__]=module
    raw=subprocess.check_output(['git','show','98570c62cc205fa82f855a4033a4d683faf80837:src/emcd_sim/'+path])
    exec(compile(raw.decode('utf-8-sig'),path,'exec'),module.__dict__)
    return module


@pytest.mark.parametrize('radial',[1e-14,2e-14,3e-14,5e-14,1e-13,5e-13,9.99e-13,1e-12,2e-12,.04,-.04,None])
@pytest.mark.parametrize('sign',[1,-1])
def test_atomic_policy_matches_accepted_ni(radial,sign):
    reference=accepted_module('ni_local_mdff.py','_part1c_ni_reference')
    cfg=NiLocalConfig(crystal_field_10dq_ev=1.2,exchange_split_ev=.37,eg_up_holes=0,t2g_down_holes=.8)
    old_cfg=reference.NiLocalConfig(**asdict(cfg))
    kwargs=dict(radial_override_angstrom=radial,magnetization_sign=sign)
    try: old=reference.ni_local_transitions(old_cfg,**kwargs)
    except ValueError:
        with pytest.raises(ValueError):ni_local_transitions(cfg,**kwargs)
        return
    new=ni_local_transitions(cfg,**kwargs)
    for key in ('energy_ev','dipoles_angstrom','weights','edge','site'):
        np.testing.assert_array_equal(getattr(old,key),getattr(new,key))
    assert old.source==new.source


def test_unknown_amplitude_policy_is_rejected():
    with pytest.raises(ValueError,match='policy'):
        transitions_for_material(None,amplitude_policy='invented')


def test_moved_angular_algebra_is_exact():
    reference=accepted_module('ni_local_mdff.py','_part1c_angular_reference')
    for j in (1,3):
        for mj in range(-j,j+1,2):
            for spin in (-1,1):
                for m in range(-2,3):
                    np.testing.assert_array_equal(dipole_2p_to_3d(j,mj,m,spin,.04),reference.ni_2p_to_3d_dipole(j,mj,m,spin,.04))


def test_shared_phase_preserves_unwrapped_positions_and_order():
    h=np.array([[2,0,0],[0,0,0],[-1,2,1]])
    p=np.array([[1.125,-.25,2.5],[.625,.25,.5]])
    expected=np.exp(2j*np.pi*(h[:,None,:]-h[None,:,:])@p.T).mean(axis=-1)
    np.testing.assert_array_equal(single_site_phase_matrix(h,p),expected)
