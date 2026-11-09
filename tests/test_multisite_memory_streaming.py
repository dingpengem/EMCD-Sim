"""Bounded Single Channeling storage, checked against the unbatched equations."""
from dataclasses import replace
import weakref

import numpy as np
import pytest
from ase.build import bulk

from emcd_sim.gui import forward_pipeline as forward, propagation, memory_budget
from emcd_sim.gui.geometry import Settings, Structure
from emcd_sim.gui.parallel_resources import require_supported
from emcd_sim.multisite import MultiSiteIonization
from emcd_sim import multisite_spectrum
from test_multisite_forward import system, configuration, RAW_KEYS, PARITY_KEYS


@pytest.mark.parametrize('angular_maps',[True,False])
def test_blocks_release_raw_arrays_and_match_unbatched_windows(tmp_path,monkeypatch,angular_maps):
    structure,settings,sites,_=system(tmp_path,'Cr')
    energy=np.unique(np.r_[np.linspace(710.,723.,35),716.])
    windows=dict(up=multisite_spectrum.ModeledEdgeWindow((710.,721.)),
                 down=multisite_spectrum.ModeledEdgeWindow((714.,723.)))
    cfg=configuration(angular_maps=angular_maps,selected_edges=(('first',710.),('middle',716.),('last',723.)))
    original=multisite_spectrum.contract_multisite_spectrum
    original_block=forward._multisite_single_block
    previous=[];sizes=[]

    def bounded(*args,**kwargs):
        assert all(ref() is None for ref in previous), 'Previous raw block is still resident'
        sizes.append(len(args[4]))
        raw=original_block(*args,**kwargs)
        previous[:]=[weakref.ref(raw['total']['plus']),weakref.ref(raw['groups']['up']['plus'])]
        return raw

    monkeypatch.setattr(forward,'_multisite_single_block',bounded)
    result=forward.calculate_multisite(structure,settings,sites,cfg,energy_ev=energy,
        energy_windows=windows,reverse_magnetization=True)
    assert len(sizes)>1 and max(sizes)<=propagation.MULTISITE_ENERGY_BATCH
    assert sum(sizes)==len(energy) and all(ref() is None for ref in previous)
    plan=multisite_spectrum.prepare_multisite_spectrum(sites,energy,windows)
    raw=original(result['model'],structure,sites,result['coherence'],plan,
        result['qx'].ravel(),result['qy'].ravel(),crystal_to_microscope=result['metadata']['frame'],
        thickness_nm=settings.thickness,reverse_magnetization=True)
    # Original full-grid fractional detector integration, including zero pixels.
    for actual,part in [(result,raw['total']),(result['weighted_sum'],raw['weighted_sum'])]+[
            (result['groups'][group.group_id],raw['groups'][group.group_id]) for group in sites.groups]:
        expected=forward._multisite_detector_data(part,cfg,energy,result['qx'],result['qy'],
            result['weights'],np.ones(result['qx'].size,bool))
        for key in RAW_KEYS+PARITY_KEYS:
            np.testing.assert_allclose(actual['spectra'][key],expected['spectra'][key],rtol=2e-13,atol=1e-17)
        assert set(actual['maps'])==set(expected['maps'])
        for label,maps in expected['maps'].items():
            for key,values in maps.items():np.testing.assert_allclose(actual['maps'][label][key],values,rtol=2e-13,atol=1e-17)
    assert result['metadata']['multisite']['selected_atom_count']==2
    np.testing.assert_array_equal(result['spectra']['energy_ev'],energy)
    assert result['metadata']['multisite']['channels']['down']['status_at_energy'][0]=='outside_modeled_window'


def test_full_native_accounting_is_bounded_without_allocating_the_spectrum(tmp_path,monkeypatch):
    _,_,sites,_=system(tmp_path)
    structure=Structure(bulk('Ni','fcc',a=3.520,cubic=True))
    sites=MultiSiteIonization(structure,sites.groups)
    settings=Settings(zone=(0,1,7),target=(2,0,0),voltage=200,thickness=10,
                      tilt=(-7.124812628,0),beam_cutoff=2.5,potential_cutoff=2.)
    cfg=configuration(grid=97,depth=64,subpixels=64,energy_points=4329,
                      selected_edges=(('L3',831.271),('L2',848.698)),memory_budget_mib=4096)
    monkeypatch.setattr(memory_budget,'memory_snapshot',lambda:dict(available_ram_mib=16282.9,process_rss_mib=370.9))
    info=propagation.numerical_info(structure,settings,cfg,ionization_sites=sites)
    assert info['bw_beams']==21 and not info['execution']['blocked']
    assert info['multisite_energy_batch_size']==16
    assert info['estimated_process_peak_mib']<4096
    assert sum(info['memory_breakdown_mib'].values())==pytest.approx(info['estimated_working_mib'])
    longer=propagation.numerical_info(structure,settings,replace(cfg,energy_points=8658),ionization_sites=sites)
    assert longer['memory_breakdown_mib']['multisite_energy_block']==info['memory_breakdown_mib']['multisite_energy_block']
    assert longer['memory_breakdown_mib']['group_detector_spectra']==2*info['memory_breakdown_mib']['group_detector_spectra']


def test_resource_rejection_does_not_claim_execution_is_allowed(tmp_path,monkeypatch):
    structure,settings,sites,_=system(tmp_path)
    monkeypatch.setattr(memory_budget,'memory_snapshot',lambda:dict(available_ram_mib=10.,process_rss_mib=64.))
    info=propagation.numerical_info(structure,settings,configuration(),ionization_sites=sites,enforce_execution=False)
    assert info['execution']['risk']=='RESOURCE REJECTED'
    with pytest.raises(ValueError,match='Largest array bounds:') as error:require_supported(info['execution'])
    assert 'execution allowed' not in str(error.value)
    assert 'Memory admission rejected' in str(error.value)
