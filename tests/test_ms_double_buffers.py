"""Strict pre-patch comparison for per-call MS buffer/temporary reuse."""
import subprocess,sys,types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
import pytest
from emcd_sim import multislice_double_channeling as ms
from emcd_sim.gui.geometry import Structure,Settings,elastic_model
from emcd_sim.ni_017_geometry import Ni017Geometry

BASE='39aafb6701f7cf84643c10366afac59401e8d91e'


@pytest.fixture(scope='module')
def old():
    name='emcd_sim._buffer_reference_test';module=types.ModuleType(name);module.__package__='emcd_sim';sys.modules[name]=module
    source=subprocess.check_output(['git','show',BASE+':src/emcd_sim/multislice_double_channeling.py']).decode('utf-8-sig')
    exec(compile(source,'baseline_multislice.py','exec'),module.__dict__);return module


@pytest.mark.parametrize('shape',[(16,),(12,12)])
@pytest.mark.parametrize('steps',[0,1,3])
@pytest.mark.parametrize('dz',[.13,-.13,0.])
def test_advance_exact_ownership_adjoint_and_cached_factors(old,shape,steps,dz):
    rng=np.random.default_rng(9301);size=int(np.prod(shape))
    u=rng.normal(size=shape)*.03;d=rng.normal(size=(3,)+shape)*.02
    # Deliberately strided and read-only input; every call must own its output.
    c=(rng.normal(size=(3,size*2))+1j*rng.normal(size=(3,size*2)))[:,::2];before=c.copy();c.flags.writeable=False
    a,b=old.FFTSplitStep(u,d),ms.FFTSplitStep(u,d)
    for distance in (dz,dz,-dz):
        expected=a.advance(c,steps,distance);actual=b.advance(c,steps,distance)
        np.testing.assert_array_equal(actual,expected)
        assert not np.shares_memory(actual,c)
        np.testing.assert_array_equal(c,before)


@pytest.mark.parametrize('thickness',[8.,30.])
def test_matched_reference_response_and_all_diagnostics_exact(old,thickness):
    # The same physical/numerical settings as the saved 300 kV case, on a
    # representative outgoing batch rather than another complete field.
    settings=Settings(voltage=300,thickness=thickness,tilt=(Ni017Geometry().bragg_tilt(300),0.),beam_cutoff=3.2,potential_cutoff=2.2)
    elastic=elastic_model(Structure.nickel(),settings)
    q=np.array([[0.,0.],[.25,.25],[.25,-.25],[-.75,.5]])
    results=[];incoming=[]
    for impl in (old,ms):
        grid=impl.ProjectedNiFFT.build(elastic,grid_points=32,potential_cutoff=2.2,projected_geometry=Ni017Geometry())
        fields=impl.incident_fields(grid,thickness,depth_steps=64,slice_step_nm=.5);incoming.append(fields)
        results.append(impl.multislice_double_channeling_response(elastic,831.271,q,thickness,
            fft_grid=32,potential_cutoff=2.2,projected_geometry=Ni017Geometry(),depth_steps=64,slice_step_nm=.5,prepared_grid=grid,prepared_incoming=fields))
    np.testing.assert_array_equal(incoming[0][0],incoming[1][0])
    np.testing.assert_array_equal(results[0][0],results[1][0])
    for name in ('incoming_norm_error','outgoing_norm_error','incoming_max_excluded_population','outgoing_max_excluded_population','actual_slice_step_nm','substeps_per_depth_interval'):
        assert results[0][1][name]==results[1][1][name]


def test_parallel_calls_keep_buffers_independent(old):
    elastic=elastic_model(Structure.nickel(),Settings(thickness=2,beam_cutoff=.9,potential_cutoff=1.8))
    kwargs=dict(fft_grid=24,potential_cutoff=1.8,projected_geometry=Ni017Geometry(),depth_steps=9,slice_step_nm=.04)
    batches=[np.array([[.2,.1+i*.05],[.2,-.1-i*.05]]) for i in range(4)]
    expected=[old.multislice_double_channeling_response(elastic,831.271,q,2,**kwargs)[0] for q in batches]
    with ThreadPoolExecutor(max_workers=4) as pool:
        actual=list(pool.map(lambda q:ms.multislice_double_channeling_response(elastic,831.271,q,2,**kwargs)[0],batches))
    for a,b in zip(actual,expected):np.testing.assert_array_equal(a,b)
