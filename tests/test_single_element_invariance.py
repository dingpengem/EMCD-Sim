from dataclasses import replace
import numpy as np
import pytest
from scipy.linalg import expm
from ase.build import bulk
from emcd_sim.gui.geometry import Structure,Settings,elastic_model
from emcd_sim.gui.generalized_forward import calculate,settings_for_source
from emcd_sim.double_channeling import BlochStates,depth_response,equivalent_site_phases,double_channeling_response,intensities_from_response
from emcd_sim.single_channeling_tensor import _tensor_angular_maps
from emcd_sim.ionization_sites import IonizationSites
from emcd_sim.simulation import EMCDSimulation
from emcd_sim.geometry import VirtualDetector
from emcd_sim.multislice_reference import coherence_from_amplitudes
from single_element_helpers import write_source


def test_double_independent_local_event_exponentials_and_origin():
    hi=np.array([[.1,.03+.02j],[.03-.02j,-.07]])
    ho=np.array([[.02,.04j],[-.04j,.12]])
    incoming=BlochStates.solve(hi,0);outgoing=BlochStates.solve(ho,0)
    h=np.array([[0,0,0],[1,0,0]]);o=np.array([[0,0,0],[0,1,0]])
    p=np.array([[0.,0,0],[.5,.5,.5]])
    rng=np.random.default_rng(123);k=rng.normal(size=(2,2,3))
    t=.7;z=np.linspace(0,t,129)
    def direct(hi,ho,positions):
        curves=[]
        for x in z:
            a=expm(1j*hi*x)[:,0];b=expm(1j*ho*(t-x))[0,:]
            event=np.zeros((3,3),complex)
            for r in positions:
                v=np.zeros(3,complex)
                for g in range(2):
                    for j in range(2):v+=a[g]*b[j]*k[g,j]*np.exp(2j*np.pi*(h[g]-o[j])@r)
                event+=np.outer(v,v.conj())/len(positions)
            curves.append(event)
        return np.trapezoid(curves,z,axis=0)
    phases,w=equivalent_site_phases(h,o,p)
    response=sum(weight*depth_response(incoming,outgoing,k*ph[...,None],t,method='numerical',depth_steps=len(z)) for ph,weight in zip(phases,w))
    np.testing.assert_allclose(response,direct(hi,ho,p),rtol=2e-14,atol=2e-15)
    analytic=sum(weight*depth_response(incoming,outgoing,k*ph[...,None],t) for ph,weight in zip(phases,w))
    np.testing.assert_allclose(analytic,response,rtol=1e-5,atol=1e-7)
    shift=np.array([.137,.211,.07]);di=np.diag(np.exp(-2j*np.pi*h@shift));do=np.diag(np.exp(-2j*np.pi*o@shift))
    np.testing.assert_allclose(direct(di@hi@di.conj().T,do@ho@do.conj().T,p+shift),response,rtol=2e-14,atol=3e-15)
    np.testing.assert_allclose(direct(hi,ho,p[::-1]),response,rtol=2e-14,atol=3e-15)


@pytest.mark.parametrize('channel',['single','double'])
def test_primitive_conventional_origin_and_site_normalization(tmp_path,channel):
    conventional=Structure(bulk('Fe','bcc',a=2.866,cubic=True))
    primitive=Structure(bulk('Fe','bcc',a=2.866,cubic=False))
    shifted=Structure(conventional.atoms.copy());shifted.atoms.set_scaled_positions(shifted.atoms.get_scaled_positions()+[.25,0,0])
    settings=Settings(zone=(0,0,1),target=(1,1,0),tilt=(-5,7),voltage=200,thickness=.2,beam_cutoff=.6,potential_cutoff=1.2)
    cfg=settings_for_source(write_source(tmp_path/'tensor.json'),energy_scope='edges',grid=9,depth=9,subpixels=8,fft_grid=16,slice_step=.01,
        halfwidth=.7,centers=((.2,.2),(.2,-.2)),radius=.12,propagation='both',channeling_model=channel,worker_mode='manual',parallel_workers=1)
    a=calculate(conventional,settings,cfg)
    b=calculate(primitive,replace(settings,zone=(1,1,0),target=(0,0,1)),cfg)
    c=calculate(shifted,settings,cfg)
    d=calculate(conventional,settings,replace(cfg,site_indices=(0,)))
    for other in (b,c,d):
        for method in ('bloch','fft-multislice'):
            for key in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus','D_mag','D_nonmag'):
                np.testing.assert_allclose(other['methods'][method]['spectra'][key],a['methods'][method]['spectra'][key],rtol=1e-10,atol=2e-14)


def test_no_outgoing_potential_reduces_to_entrance_event_reference():
    s=Structure(bulk('Fe','bcc',a=2.866,cubic=True));sites=IonizationSites.from_structure(s,'Fe')
    settings=Settings(zone=(0,0,1),target=(1,1,0),tilt=(-5,7),voltage=200,thickness=.3,beam_cutoff=.6,potential_cutoff=1.2)
    elastic=elastic_model(s,settings);z=np.linspace(0,.3,33);C=coherence_from_amplitudes(z,elastic.amplitudes(z))
    model=EMCDSimulation(elastic,{'A':VirtualDetector((.2,.2),.1),'B':VirtualDetector((.2,-.2),.1)})
    tensor=np.array([[1,.2j,0],[-.2j,1.2,.03],[0,.03,.9]])
    q=np.array([[.2,.2],[.2,-.2]])
    even,odd=_tensor_angular_maps(model,tensor,710,C,sites.single_phase(elastic.crystal,elastic.beams.hkl),q[:,0],q[:,1])
    r=double_channeling_response(elastic,710,q,.3,method='numerical',depth_steps=33,outgoing_potential=False,ionization_sites=sites)
    np.testing.assert_allclose(intensities_from_response(r,tensor),.3*(even+odd),rtol=2e-13,atol=1e-15)
