"""Frozen reviewed algorithms are controls, never production dependencies."""
import subprocess,types
import numpy as np
import pytest
from emcd_sim.crystal import fcc_nickel
from emcd_sim.projected_geometry import ProjectedGeometry
from emcd_sim.gui.geometry import Structure,Settings,elastic_model
from emcd_sim.multislice_double_channeling import ProjectedFFT,incident_fields,multislice_double_channeling_response

REVIEW='5652635'

def archived(filename):
    module=types.ModuleType('emcd_sim._frozen_'+filename);module.__package__='emcd_sim'
    source=subprocess.check_output(['git','show',REVIEW+':src/emcd_sim/'+filename+'.py']).decode('utf-8-sig')
    import sys
    sys.modules[module.__name__]=module
    exec(compile(source,'reviewed_'+filename+'.py','exec'),module.__dict__)
    return module

@pytest.mark.parametrize('zone,target,cutoff',[
    ((0,0,1),(2,0,0),1.8),((0,1,7),(2,0,0),2.2),((1,1,7),(2,-2,0),3.8)])
def test_reviewed_geometry_potential_waves_and_double_response(zone,target,cutoff):
    reference=archived('multislice_double_channeling')
    descriptor=(None if zone==(0,0,1) else getattr(archived('ni_'+('017' if zone==(0,1,7) else '117')+'_geometry'),'Ni017Geometry' if zone==(0,1,7) else 'Ni117Geometry')())
    general=ProjectedGeometry.from_crystal(fcc_nickel(),zone,target)
    if descriptor is not None:
        np.testing.assert_allclose(general.frame,descriptor.frame,atol=2e-16,rtol=0)
        assert general.beams(3.2).hkl==descriptor.beams(3.2).hkl
        old_h,old_g=descriptor.harmonics(32,max(3.2,cutoff))
        cell=np.array([old_h[32],old_h[1]])
    else:cell=general.generators
    matched=ProjectedGeometry.from_crystal(fcc_nickel(),zone,target,generators=cell)
    settings=Settings(zone=zone,target=target,voltage=200,thickness=2,tilt=(general.bragg_tilt(),0),beam_cutoff=3.2 if zone!=(0,0,1) else 1.4,potential_cutoff=cutoff)
    elastic=elastic_model(Structure.nickel(),settings)
    a=reference.ProjectedNiFFT.build(elastic,grid_points=32,potential_cutoff=cutoff,projected_geometry=descriptor)
    b=ProjectedFFT.build(elastic,grid_points=32,potential_cutoff=cutoff,projected_geometry=matched)
    np.testing.assert_array_equal(a.hkl,b.hkl)
    np.testing.assert_allclose(a.g,b.g,rtol=0,atol=3e-14)
    np.testing.assert_allclose(a.potential,b.potential,rtol=0,atol=2e-15)
    ia=reference.incident_fields(a,2,depth_steps=17,slice_step_nm=.04)
    ib=incident_fields(b,2,depth_steps=17,slice_step_nm=.04)
    np.testing.assert_allclose(ia[0],ib[0],rtol=0,atol=2e-13)
    np.testing.assert_allclose(abs(ia[0])**2,abs(ib[0])**2,rtol=0,atol=2e-13)
    q=np.array([[.2,.1],[.2,-.1],[.4,.3]])
    kwargs=dict(depth_steps=17,slice_step_nm=.04,prepared_grid=a,prepared_incoming=ia)
    old=reference.multislice_double_channeling_response(elastic,831.271,q,2,**kwargs)[0]
    kwargs.update(prepared_grid=b,prepared_incoming=ib)
    new=multislice_double_channeling_response(elastic,831.271,q,2,**kwargs)[0]
    np.testing.assert_allclose(new,old,rtol=2e-12,atol=2e-13)

def test_old_fft_cell_recovered_from_data_and_corruption_rejected():
    from emcd_sim.gui.project_io import saved_fft_generators
    g=ProjectedGeometry.from_crystal(fcc_nickel(),(0,1,7),(2,0,0),generators=((1,0,0),(0,7,-1)))
    h,_=g.harmonics(32,3.2)
    assert saved_fft_generators({'fft_full__beam_hkl':h},32)==((1,0,0),(0,7,-1))
    damaged=h.copy();damaged[3,0]+=1
    with pytest.raises(ValueError,match='disagree'):saved_fft_generators({'fft_full__beam_hkl':damaged},32)
    with pytest.raises(ValueError,match='cannot be verified'):saved_fft_generators({},32)


def test_saved_row_sampling_uses_verified_row_and_general_complement():
    from emcd_sim.gui.project_io import saved_fft_generators
    f=np.rint(np.fft.fftfreq(32)*32).astype(int)
    h=f[:,None]*np.array([2,0,0])
    assert saved_fft_generators({'fft_full__beam_hkl':h},32,row_complement=(0,2,0))==((2,0,0),(0,2,0))
    h[3,1]=1
    with pytest.raises(ValueError,match='inconsistent'):saved_fft_generators({'fft_full__beam_hkl':h},32,row_complement=(0,2,0))


def test_invalid_legacy_target_blocks_reuse_without_raising():
    from emcd_sim.gui.project_io import structure_snapshot,frame_rerun_reason
    result=dict(settings=Settings(zone=(1,1,1),target=(2,0,0)),metadata=dict(frame=np.eye(3)),structure_snapshot=structure_snapshot(Structure.nickel()))
    assert 'incompatible' in frame_rerun_reason(result)
