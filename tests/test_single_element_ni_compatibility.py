"""Numerical arrays versus immutable pre-feature source, not regenerated fixtures."""
import subprocess,sys,types,os,hashlib
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
import numpy as np
import pytest
from emcd_sim.gui import emcd_forward as ni,channeling
from emcd_sim.gui.geometry import Structure,Settings

BASE='2f9c130099dce5df4e4609b521c42f53c5385518'


def archived(path,name,package):
    module=types.ModuleType(name);module.__package__=package;sys.modules[name]=module
    source=subprocess.check_output(['git','show',BASE+':'+path]).decode('utf-8-sig')
    source=source.replace('..ni_local_mdff import','..historical_ni import')
    exec(compile(source,'immutable_pre_feature_'+path,'exec'),module.__dict__)
    return module


@pytest.fixture(scope='module')
def old_contract():
    bw=archived('src/emcd_sim/double_channeling.py','emcd_sim._single_element_bw_reference','emcd_sim')
    ms=archived('src/emcd_sim/multislice_double_channeling.py','emcd_sim._single_element_ms_reference','emcd_sim')
    ch=archived('src/emcd_sim/gui/channeling.py','emcd_sim.gui._single_element_channel_reference','emcd_sim.gui')
    ch.double_channeling_response=bw.double_channeling_response;ch.prepare_incoming_bloch=bw.prepare_incoming_bloch
    ch.multislice_double_channeling_response=ms.multislice_double_channeling_response
    return ch.contract


@pytest.mark.parametrize('model',['xmcd','atomic'])
@pytest.mark.parametrize('channel',['single','double'])
def test_original_ni_all_numeric_arrays_exact(old_contract,model,channel):
    settings=Settings(thickness=.3,beam_cutoff=.9,potential_cutoff=1.8)
    cfg=ni.ForwardSettings(model=model,axis_declared=True,channeling_model=channel,propagation='both',
        energy_scope='edges',grid=9,depth=9,subpixels=8,fft_grid=16,slice_step=.01,halfwidth=.7,
        centers=((.2,.2),(.2,-.2)),radius=.12,correction=False,worker_mode='manual',parallel_workers=1)
    if model=='atomic':cfg=replace(cfg,l3=cfg.atomic.l3_ev,l2=cfg.atomic.l2_ev)
    a=ni.calculate(Structure.nickel(),settings,cfg)
    with patch.object(channeling,'contract',old_contract):b=ni.calculate(Structure.nickel(),settings,cfg)
    count=0
    for method in a['methods']:
        x,y=a['methods'][method],b['methods'][method]
        for key in ('amplitudes','coherence','depth_nm','qx','qy'):
            np.testing.assert_array_equal(x[key],y[key]);count+=1
        for key in x['spectra']:
            np.testing.assert_array_equal(x['spectra'][key],y['spectra'][key]);count+=1
        for edge in x['maps']:
            for key in x['maps'][edge]:
                np.testing.assert_array_equal(x['maps'][edge][key],y['maps'][edge][key]);count+=1
    assert count>=50


def test_genuine_historical_ni_project_remains_read_only_lobato():
    from emcd_sim.gui.project_io import load_project,restore_structure
    from emcd_sim.gui.geometry import elastic_model
    path=Path(os.environ.get('EMCD_HISTORICAL_NI_PROJECT','__missing_optional_historical_project__'))
    if not (path/'project.json').is_file():pytest.skip('Optional genuine historical Ni project unavailable')
    before=hashlib.sha256((path/'project.json').read_bytes()).hexdigest()
    r=load_project(path)
    assert r['settings'].elastic_provider=='nickel-lobato-2014'
    assert 'elastic_provider' not in r['metadata']['settings']
    elastic=elastic_model(restore_structure(r['structure_snapshot']),r['settings'])
    np.testing.assert_allclose(elastic.amplitudes(r['depth_nm']),r['methods']['bloch']['amplitudes'],rtol=0,atol=2e-12)
    assert hashlib.sha256((path/'project.json').read_bytes()).hexdigest()==before
