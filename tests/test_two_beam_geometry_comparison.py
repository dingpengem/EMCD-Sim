"""Focused finite-ZOLZ geometry and population checks, no inelastic scan."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from ni_two_beam_geometry_comparison import enumerate_zolz,groups,populations,fractions
from emcd_sim.gui.geometry import Structure,Settings,orientation,elastic_model
from emcd_sim.crystal import Crystal
from emcd_sim.diffraction import excitation_errors_angstrom_inv
from emcd_sim.gui.results import geometry_description


@pytest.mark.parametrize('zone',[(0,0,1),(0,1,7)])
def test_full_zolz_enumeration_and_frame(zone):
    a=Structure.nickel().atoms;R=orientation(a.cell.array,zone)
    np.testing.assert_allclose(R@R.T,np.eye(3),atol=1e-14)
    np.testing.assert_allclose(R@(np.array(zone)/np.linalg.norm(zone)),[0,0,1],atol=1e-14)
    assert np.linalg.det(R)==pytest.approx(1)
    c=Crystal(a.cell.array@R.T,a.get_scaled_positions(),tuple(a.get_chemical_symbols()))
    hkl=enumerate_zolz(c,zone,4.6)
    assert hkl[0]==(0,0,0) and (2,0,0) in hkl
    for h in hkl:
        assert np.dot(h,zone)==0 and len(set(v%2 for v in h))==1
        assert c.is_allowed(h) and np.linalg.norm(c.g_vector(h))<=4.6+1e-10
        assert abs(c.g_vector(h)[2])<1e-12
    assert np.any(groups(hkl)[1])
    if zone==(0,0,1):
        for h in ((0,2,0),(2,2,0),(0,-2,0),(-2,-2,0)):assert h in hkl
        row=enumerate_zolz(c,zone,4.6,row=True)
        assert len(row)==17 and set(row)<set(hkl)
    else:
        assert (1,7,-1) in hkl and (0,7,-1) not in hkl
        assert len(hkl)==59


def test_exact_bragg_and_tilt_coordinate_convention():
    s=Settings(voltage=200,zone=(0,0,1),tilt=(-7.116725439974256,35),beam_cutoff=1.2,potential_cutoff=6.2)
    e=elastic_model(Structure.nickel(),s)
    assert excitation_errors_angstrom_inv(e)[e.beams.hkl.index((2,0,0))]==pytest.approx(0,abs=1e-14)
    assert e.microscope.incident_k_xy[0]<0 and e.microscope.incident_k_xy[1]>0
    np.testing.assert_allclose(np.diag(e.hamiltonian_nm_inv()).real,-20*np.pi*excitation_errors_angstrom_inv(e),atol=1e-13)


def test_exact_depth_average_and_incident_normalization():
    e=elastic_model(Structure.nickel(),Settings(beam_cutoff=1.2,potential_cutoff=2.2))
    values,vectors=np.linalg.eigh(e.hamiltonian_nm_inv());psi,C=populations(values,vectors,12)
    z=np.linspace(0,12,4097);waves=e.amplitudes(z)
    np.testing.assert_allclose(psi,waves[-1],atol=1e-13)
    np.testing.assert_allclose(C.diagonal().real,np.trapezoid(abs(waves)**2,z,axis=0)/12,atol=2e-8)
    np.testing.assert_allclose(C,C.conj().T,atol=1e-14)
    assert np.linalg.eigvalsh(C).min()>=-1e-14
    for I in (abs(psi)**2,C.diagonal().real):
        r=fractions(I,e.beams.hkl)
        assert r['I_total']==pytest.approx(1,abs=1e-13)
        assert sum(r[k] for k in ('P_2beam','P_offrow','P_other_row'))==pytest.approx(100,abs=1e-12)


def test_saved_display_explicitly_distinguishes_row_from_full():
    from types import SimpleNamespace
    s=Settings(zone=(0,0,1),tilt=(-7.116725439974256,35))
    for row,text in ((True,'systematic-row-restricted'),(False,'full finite ZOLZ')):
        result=dict(settings=s,config=SimpleNamespace(systematic_row=row))
        assert text in geometry_description(result)
        assert '35.0000' in geometry_description(result)


def test_complex_coherence_average_matches_direct_propagation():
    rng=np.random.default_rng(27);h=rng.normal(size=(5,5))+1j*rng.normal(size=(5,5));h=(h+h.conj().T)*.05
    values,vectors=np.linalg.eigh(h);psi,C=populations(values,vectors,8)
    z=np.linspace(0,8,4097);waves=(np.exp(1j*z[:,None]*values)*vectors[0].conj())@vectors.T
    direct=np.trapezoid(waves[:,:,None]*waves[:,None,:].conj(),z,axis=0)/8
    np.testing.assert_allclose(C,direct,atol=2e-8)
