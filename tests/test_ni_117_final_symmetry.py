"""Source-[001] and transfer-branch symmetry checks, independent of plotting."""
from pathlib import Path
import numpy as np
import pytest
from emcd_sim.ni_117_geometry import Ni117Geometry
from emcd_sim.gui.emcd_forward import ForwardSettings,tensors
from emcd_sim.geometry import characteristic_qz_angstrom_inv


def test_wien2k_axis_is_independent_of_gui_default():
    data=Path(__file__).resolve().parents[1]/'data/wien2k_ni'
    if not all((data/name).is_file() for name in ('Ni_fm.inso','Ni_fm.outputopup')):
        pytest.skip('Optional local WIEN2k companion audit; original files are not distributed with the package')
    inso=(data/'Ni_fm.inso').read_text(encoding='utf-8')
    assert tuple(map(int,inso.splitlines()[3].split()[:3]))==(0,0,1)
    assert 'M||  0.00  0.00  1.00' in (data/'Ni_fm.outputopup').read_text(encoding='utf-8')


def test_tensor_sign_rotation_and_actual_beam_control():
    R=Ni117Geometry().frame;energy=np.array([831.271,848.698]);cfg=ForwardSettings(axis_declared=True)
    crystal=tensors(cfg,energy,np.eye(3))[0].tensor_angstrom2_per_ev
    plus,minus=tensors(cfg,energy,R);T=plus.tensor_angstrom2_per_ev
    np.testing.assert_allclose(T,np.einsum('ia,eab,jb->eij',R,crystal,R),atol=1e-15)
    np.testing.assert_allclose(minus.tensor_angstrom2_per_ev,T.conj(),atol=1e-15)
    assert np.linalg.eigvalsh(T).min()>=-1e-15
    local=R@np.array([0,0,1]);encoded=np.stack((T[:,1,2].imag,T[:,2,0].imag,T[:,0,1].imag),axis=1)
    np.testing.assert_allclose(encoded,crystal[:,0,1].imag[:,None]*local,atol=1e-15)
    kx=Ni117Geometry().bragg_tilt()*.001;beam=np.array([kx,0,np.sqrt(1-kx*kx)])
    from dataclasses import replace
    control=tensors(replace(cfg,magnetization=tuple(R.T@beam)),energy,R)[0].tensor_angstrom2_per_ev
    np.testing.assert_allclose(control[:,1,2].imag,crystal[:,0,1].imag*beam[0],atol=1e-15)
    np.testing.assert_allclose(control[:,2,0].imag,0,atol=1e-15)


def test_signed_single_kernel_prediction_and_mirror_parts():
    g=.8;z=-characteristic_qz_angstrom_inv(831.271,200);m=Ni117Geometry().frame@np.array([0,0,1])
    q=np.array([[.3,.2,z],[.3,-.2,z]])
    c=.17;T=1j*c*np.array([[0,m[2],-m[1]],[-m[2],0,m[0]],[m[1],-m[0],0]])
    C=np.array([[.6,.2+.1j],[.2-.1j,.4]])
    from emcd_sim.double_channeling import dipole_kernel
    vectors=np.stack((q,q-[g,0,0]),axis=1);k=dipole_kernel(vectors)
    calculated=np.einsum('ij,pia,ab,pjb->p',C,k,T,k).real
    factor=-2*c*C[0,1].imag/((2*np.pi)**2*np.sum(q*q,axis=1)*np.sum((q-[g,0,0])**2,axis=1))
    expected=factor*g*(m[2]*q[:,1]-m[1]*z)
    np.testing.assert_allclose(calculated,expected,rtol=1e-14,atol=1e-16)
    np.testing.assert_allclose((calculated+calculated[::-1])/2,factor*(-g*m[1]*z),atol=1e-16)
    np.testing.assert_allclose((calculated-calculated[::-1])/2,factor*g*m[2]*q[:,1],atol=1e-16)


def test_double_transfer_branches_row_and_full_expression():
    g=.8;q=np.array([.27,.31,-.06]);row=np.array([[0,0],[g,0]])
    # Exhaust actual incoming/outgoing branch offsets, including their signs.
    for beams in (row,np.array([[0,0],[g,0],[.4,2.8],[-.4,-2.8]])):
        offsets=(beams[None,:,:]-beams[:,None,:]).reshape(-1,2)
        for delta in offsets:
            for other in offsets:
                p=q+np.r_[delta,0];r=q+np.r_[other,0]
                expected=np.array([q[2]*(delta[1]-other[1]),q[2]*(other[0]-delta[0]),
                    q[0]*(other[1]-delta[1])+q[1]*(delta[0]-other[0])+delta[0]*other[1]-delta[1]*other[0]])
                np.testing.assert_allclose(np.cross(p,r),expected,atol=4e-15)
                if np.all(beams[:,1]==0):np.testing.assert_allclose(expected,(delta[0]-other[0])*np.array([0,-q[2],q[1]]),atol=1e-15)


def test_response_reuse_guard_matches_physical_configuration(monkeypatch):
    import importlib,copy
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'scripts'))
    module=importlib.import_module('ni_117_symmetry_controls')
    old=dict(settings={'tilt':[-10.,0.],'basis_mode':'full'},method='bloch',channeling='double',energies_ev=[831.271,848.698],
        source_sha256='source',physics_sha256={'core':'verified'},response_algorithm='cartesian_response_v1',
        profile=dict(beam=4.6,potential=6.2,fft=32,depth=129,step=.02,map_grid=33,circle=360,detector_grid=97))
    new=copy.deepcopy(old);new['profile']['detector_grid']=129
    assert module.compatible(old,new)  # Integration changes do not change R(q).
    for key,value in [('depth',257),('beam',5.4),('fft',48),('potential',5.4),('step',.04)]:
        changed=copy.deepcopy(new);changed['profile'][key]=value
        assert not module.compatible(old,changed)
    changed=copy.deepcopy(new);changed['settings']['tilt'][1]=.2
    assert not module.compatible(old,changed)
    changed=copy.deepcopy(new);changed['source_sha256']='different'
    assert not module.compatible(old,changed)
