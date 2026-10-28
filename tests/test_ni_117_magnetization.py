"""Small independent checks for the fixed-spectrum magnetic-axis study."""
import importlib.util
from pathlib import Path
import numpy as np
from legacy_geometry import Ni117Geometry
from emcd_sim.gui.geometry import Structure,Settings,elastic_model
from emcd_sim.gui.emcd_forward import ForwardSettings,tensors
from emcd_sim.single_channeling_tensor import _tensor_angular_maps,fcc_site_phase_matrix
from emcd_sim.multislice_reference import coherence_from_amplitudes
from emcd_sim.simulation import EMCDSimulation
from emcd_sim.geometry import VirtualDetector

spec=importlib.util.spec_from_file_location('magnetic_study',Path(__file__).resolve().parents[1]/'scripts/ni_117_magnetization.py')
study=importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name]=study
spec.loader.exec_module(study)


def test_source001_components_actual_incident_and_single_rotation():
    R=Ni117Geometry().frame;tilt=(Ni117Geometry().bragg_tilt(),0)
    axes=study.axes(tilt);m=axes['crystal001']
    np.testing.assert_allclose(m['local'],[0,-2/np.sqrt(102),7/np.sqrt(51)],atol=1e-15)
    assert 11<m['angle_to_incident_deg']<12
    assert m['longitudinal']!=m['local'][2]
    np.testing.assert_allclose(axes['incident']['local'],axes['incident']['incident_local'],atol=1e-15)
    cfg=ForwardSettings(axis_declared=True,magnetization=(0,0,1))
    plus,minus=tensors(cfg,np.array(study.ENERGIES),R)
    T=plus.tensor_angstrom2_per_ev
    np.testing.assert_allclose(minus.tensor_angstrom2_per_ev,T.conj(),atol=1e-15)
    # Axial vector encoded by antisymmetric imaginary T must rotate once.
    encoded=np.stack((T[:,1,2].imag,T[:,2,0].imag,T[:,0,1].imag),axis=-1)
    encoded/=np.linalg.norm(encoded,axis=-1)[:,None]
    assert all(abs(v@m['local'])>1-1e-14 for v in encoded)


def test_two_beam_cross_product_even_odd_and_magnetization():
    g=.8;z=-.06;x=np.array([.2,.3]);y=np.array([.1,-.1])
    q=np.column_stack((x,y,np.full(2,z)));cross=np.cross(q,q-[g,0,0])
    for a in study.axes((Ni117Geometry().bragg_tilt(),0)).values():
        m=a['local'];np.testing.assert_allclose(cross@m,g*(m[2]*y-m[1]*z),atol=1e-15)
    assert abs(study.axes((0,0))['crystal001']['local'][1])>0


def test_cartesian_single_response_matches_original_kernel():
    s=Settings(zone=(1,1,7),target=(2,-2,0),tilt=(Ni117Geometry().bragg_tilt(),0),thickness=2,
        beam_cutoff=3.2,potential_cutoff=6.2)
    elastic=elastic_model(Structure.nickel(),s);z=np.linspace(0,2,17)
    C=coherence_from_amplitudes(z,elastic.amplitudes(z));q=np.array([[.2,.3],[.2,-.3],[.8,0]])
    response=study.single_response(elastic,C,831.271,q,2)
    model=EMCDSimulation(elastic,{'A':VirtualDetector((0,0),.1),'B':VirtualDetector((0,1),.1)})
    for axis in study.axes(s.tilt).values():
        cfg=ForwardSettings(axis_declared=True,magnetization=tuple(axis['crystal']))
        for tensor in tensors(cfg,np.array(study.ENERGIES),Ni117Geometry().frame):
            T=tensor.tensor_angstrom2_per_ev[0]
            n,m=_tensor_angular_maps(model,T,831.271,C,fcc_site_phase_matrix(model),q[:,0],q[:,1])
            np.testing.assert_allclose(study.intensities_from_response(response,T),2*(n+m),rtol=2e-14,atol=1e-16)


def test_circle_mirror_and_fractional_detector_support():
    s=study.supports(study.Profile());q=s['circle_q'];mirror=(-np.arange(len(q)))%len(q)
    np.testing.assert_array_equal(q[:,0],q[mirror,0]);np.testing.assert_array_equal(q[:,1],-q[mirror,1])
    np.testing.assert_allclose(s['centers'][0],[s['centers'][1,0],-s['centers'][1,1]],atol=1e-15)
    np.testing.assert_allclose(s['detector_areas'][0],s['detector_areas'][1],atol=1e-15)
    assert np.all((s['detector_weights']>=0)&(s['detector_weights']<=1))
    assert abs(s['detector_areas'][0]/(np.pi*(.16*np.sqrt(8)/3.524)**2)-1)<1e-4
