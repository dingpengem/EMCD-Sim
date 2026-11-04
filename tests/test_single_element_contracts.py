from copy import deepcopy
from dataclasses import replace
import json
import numpy as np
import pytest
from ase import Atoms
from ase.build import bulk
from emcd_sim.gui.geometry import Structure,Settings,elastic_model
from emcd_sim.ionization_sites import IonizationSites
from emcd_sim.imported_mdff import ImportedMDFF
from emcd_sim.gui.generalized_forward import settings_for_source,energy_grid,material_reason
from emcd_sim.single_channeling_tensor import _tensor_angular_maps,fcc_site_phase_matrix
from emcd_sim.geometry import characteristic_qz_angstrom_inv,VirtualDetector
from emcd_sim.simulation import EMCDSimulation
from emcd_sim.double_channeling import equivalent_site_phases
from single_element_helpers import document,write_source


def fe():return Structure(bulk('Fe','bcc',a=2.866,cubic=True),'Synthetic BCC Fe geometry')


def test_fe_coordinates_bcc_rules_and_independent_reciprocal_frame():
    from emcd_sim.gui.geometry import geometry
    s=fe();np.testing.assert_array_equal(s.atoms.get_scaled_positions(),[[0,0,0],[.5,.5,.5]])
    settings=Settings(zone=(0,0,1),target=(1,1,0),tilt=(0,0),beam_cutoff=.85,potential_cutoff=1.2)
    crystal,R,h,g,_=geometry(s,settings)
    assert (1,0,0) not in h and (1,1,0) in h
    assert all((sum(v)%2==0 and v[2]==0) for v in h)
    frame=np.array([[1,1,0],[-1,1,0],[0,0,np.sqrt(2)]])/np.sqrt(2)
    np.testing.assert_allclose(R,frame,atol=1e-15)
    np.testing.assert_allclose(g,np.asarray(h)@np.linalg.inv(s.atoms.cell.array).T@frame[:2].T,atol=1e-15)


def test_sites_single_reference_and_ni_compatibility():
    s=fe();sites=IonizationSites.from_structure(s,'Fe',(0,1))
    settings=Settings(zone=(0,0,1),target=(1,1,0),tilt=(0,0),beam_cutoff=.6,potential_cutoff=1.)
    elastic=elastic_model(s,settings);model=EMCDSimulation(elastic,{'A':VirtualDetector((.2,.2),.1),'B':VirtualDetector((.2,-.2),.1)})
    h=np.asarray(elastic.beams.hkl);rng=np.random.default_rng(41)
    wave=rng.normal(size=len(h))+1j*rng.normal(size=len(h));wave/=np.linalg.norm(wave)
    C=np.outer(wave,wave.conj());t=np.array([[1,.2j,.1],[-.2j,1.1,0],[.1,0,.8]])
    xy=np.array([[.13,.22],[-.2,.31]]);phase=sites.single_phase(elastic.crystal,h)
    even,odd=_tensor_angular_maps(model,t,710.,C,phase,xy[:,0],xy[:,1])
    expected=[]
    for q in xy:
        total=0.
        for p in sites.positions_for(elastic.crystal):
            v=np.zeros(3,complex)
            for i,g in enumerate(elastic.reciprocal_vectors_xy):
                Q=2*np.pi*np.r_[q-g,-characteristic_qz_angstrom_inv(710,settings.voltage)]
                v+=wave[i]*np.exp(2j*np.pi*h[i]@p)*Q/(Q@Q)
            total+=np.trace(np.outer(v,v.conj())@t).real/len(sites.indices)
        expected.append(total)
    np.testing.assert_allclose(even+odd,expected,rtol=3e-14,atol=1e-14)
    ni=Structure.nickel();en=elastic_model(ni,settings)
    model=replace(model,elastic=en)
    np.testing.assert_array_equal(IonizationSites.from_structure(ni,'Ni').single_phase(en.crystal,en.beams.hkl),fcc_site_phase_matrix(model))


def test_site_order_translation_and_independent_double_phases():
    s=fe();h=np.array([[0,0,0],[1,1,0],[1,0,0]]);o=np.array([[0,0,0],[1,0,1]])
    p=s.atoms.get_scaled_positions();ph,w=equivalent_site_phases(h,o,p)
    direct=np.array([[[np.exp(2j*np.pi*(g-j)@r) for j in o] for g in h] for r in p])
    np.testing.assert_allclose(np.sum(w[:,None,None]*ph,axis=0),direct.mean(axis=0),atol=1e-15)
    a=IonizationSites.from_structure(s,'Fe').single_phase(type('C',(),dict(species=('Fe','Fe'),fractional_positions=p,lattice_angstrom=s.atoms.cell.array))(),h)
    reversed_s=Structure(s.atoms[[1,0]])
    b=IonizationSites.from_structure(reversed_s,'Fe')
    fake=type('C',(),dict(species=('Fe','Fe'),fractional_positions=p[::-1],lattice_angstrom=s.atoms.cell.array))()
    np.testing.assert_allclose(a,b.single_phase(fake,h),atol=1e-15)


def test_reject_inequivalent_partial_and_invalid_selection():
    bad=Structure(Atoms('Fe2',scaled_positions=[[0,0,0],[.1,.2,.3]],cell=np.eye(3)*3,pbc=True))
    with pytest.raises(ValueError,match='Inequivalent'):IonizationSites.from_structure(bad,'Fe',(0,))
    s=fe();s.atoms.info['occupancy']={0:{'Fe':.5}}
    with pytest.raises(ValueError,match='Partial'):IonizationSites.from_structure(s,'Fe')
    with pytest.raises(ValueError,match='unique'):IonizationSites.from_structure(fe(),'Fe',(0,0))


def test_reject_site_dependent_moments_charges_and_inconsistent_axis(tmp_path):
    cfg=settings_for_source(write_source(tmp_path/'fm.json'))
    s=fe();s.atoms.set_initial_magnetic_moments([2.3,-2.3])
    assert 'Inequivalent magnetic/charge' in material_reason(s,cfg)
    s=fe();s.atoms.set_initial_charges([0,.2])
    assert 'Inequivalent magnetic/charge' in material_reason(s,cfg)
    s=fe();s.atoms.set_initial_magnetic_moments(None);s.atoms.set_initial_magnetic_moments([[2.3,0,0],[2.3,0,0]])
    assert 'disagree' in material_reason(s,cfg)
    s=fe();nm=settings_for_source(write_source(tmp_path/'nm.json',nonmagnetic=True))
    assert 'Nonmagnetic tensor conflicts' in material_reason(s,nm)


@pytest.mark.parametrize('nonmagnetic',[False,True])
def test_import_and_rotation_interpolation(tmp_path,nonmagnetic):
    source=ImportedMDFF.load(write_source(tmp_path/'tensor.json',nonmagnetic=nonmagnetic))
    R=np.array([[0,0,1],[0,1,0],[-1,0,0]])
    ts=source.tensors(np.array([710.,711.,723.]),R,[0,0,1])
    np.testing.assert_allclose(ts[0].tensor_angstrom2_per_ev[0],R@source.plus.tensor_angstrom2_per_ev[2]@R.T)
    assert np.linalg.eigvalsh(ts[0].tensor_angstrom2_per_ev).min()>=0
    if nonmagnetic:np.testing.assert_array_equal(ts[0].tensor_angstrom2_per_ev,ts[1].tensor_angstrom2_per_ev)
    else:assert not np.allclose(ts[1].tensor_angstrom2_per_ev,ts[0].tensor_angstrom2_per_ev.conj())
    with pytest.raises(ValueError,match='extrapolation'):source.tensors([703.,710.],R,[0,0,1])
    with pytest.raises(ValueError,match='axis'):source.tensors([710.,723.],R,[1,0,0])


@pytest.mark.parametrize('mutation',[
    lambda d:d.update(units='barn/eV'),lambda d:d.update(source=''),lambda d:d.update(edge='K'),
    lambda d:d.update(magnetic_state='afm'),lambda d:d.pop('T_minus'),
    lambda d:d.update(convention='legacy_same_index_R_ab_T_ab'),
    lambda d:d.update(frame_to_crystal=[[1,0,0],[0,1,0],[0,0,-1]]),
    lambda d:d['energy_ev'].__setitem__(2,707),lambda d:d['T_plus']['real'][0][0].__setitem__(0,-100),
    lambda d:d['T_plus']['real'][0][0].__setitem__(1,10),lambda d:d['T_even']['real'][0][0].__setitem__(0,5),
    lambda d:d['T_plus']['imag'][0][0].__setitem__(0,float('nan'))])
def test_reject_invalid_import(tmp_path,mutation):
    d=deepcopy(document());mutation(d);p=tmp_path/'bad.json';p.write_text(json.dumps(d))
    with pytest.raises((ValueError,TypeError)):ImportedMDFF.load(p)


def test_element_edge_checksum_and_no_ni_energy_inheritance(tmp_path):
    p=write_source(tmp_path/'tensor.json');cfg=settings_for_source(p,grid=9,depth=9,subpixels=8)
    assert material_reason(fe(),cfg)=='' and material_reason(Structure.nickel(),cfg)
    assert len(energy_grid(cfg))==243
    assert material_reason(fe(),replace(cfg,core_edge='K'))
    with pytest.raises(ValueError,match='calibration'):energy_grid(replace(cfg,l3=831.271,l2=848.698))
    p.write_text(p.read_text()+' ')
    with pytest.raises(ValueError,match='checksum'):energy_grid(cfg)


def test_declared_local_basis_matches_crystal_basis(tmp_path):
    d=document();p=tmp_path/'crystal.json';p.write_text(json.dumps(d))
    original=ImportedMDFF.load(p)
    a=np.array([[0.,0,1],[0,1,0],[-1,0,0]])
    local=deepcopy(d);local['basis']='declared_local';local['frame_to_crystal']=a.tolist()
    for key in ('T_plus','T_minus','T_even'):
        v=np.array(d[key]['real'])+1j*np.array(d[key]['imag']);v=np.einsum('ai,eab,bj->eij',a,v,a)
        local[key]=dict(real=v.real.tolist(),imag=v.imag.tolist())
    p=tmp_path/'local.json';p.write_text(json.dumps(local));rotated=ImportedMDFF.load(p)
    for left,right in zip(original.tensors([710,723],np.eye(3),[0,0,1]),rotated.tensors([710,723],np.eye(3),[0,0,1])):
        np.testing.assert_allclose(left.tensor_angstrom2_per_ev,right.tensor_angstrom2_per_ev,atol=1e-15)


def test_small_amplitude_nonhermitian_source_is_not_accepted_by_absolute_tolerance(tmp_path):
    d=document()
    for key in ('T_plus','T_minus','T_even'):
        for field in ('real','imag'):d[key][field]=(np.array(d[key][field])*1e-20).tolist()
    d['T_plus']['real'][0][0][1]=1e-20
    p=tmp_path/'bad_tiny.json';p.write_text(json.dumps(d))
    with pytest.raises(ValueError,match='Hermitian'):ImportedMDFF.load(p)


@pytest.mark.parametrize('component,shape',[('real',()),('imag',()),('imag',(3,3))])
def test_component_shapes_cannot_be_silently_broadcast(tmp_path,component,shape):
    d=document()
    for name in ('T_plus','T_minus','T_even'):
        d[name]={'real':np.ones((len(d['energy_ev']),3,3)).tolist(),
                 'imag':np.zeros((len(d['energy_ev']),3,3)).tolist()}
        d[name][component]=(np.ones(shape) if component=='real' else np.zeros(shape)).tolist()
    p=tmp_path/'broadcast.json';p.write_text(json.dumps(d))
    with pytest.raises(ValueError,match='shape'):ImportedMDFF.load(p)
