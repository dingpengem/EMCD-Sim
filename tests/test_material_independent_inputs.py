"""General inputs cannot acquire another material's provenance or response."""
from dataclasses import asdict, replace

import numpy as np
import pytest
from ase.build import bulk

from emcd_sim.structure_geometry import Structure, Settings, structure_snapshot, restore_structure, structures_match
from emcd_sim.forward_settings import ForwardSettings, NiForwardSettings, MultiSiteForwardSettings
from emcd_sim.material_inputs import ImportedSettings, ProviderSettings
from emcd_sim.mdff_providers import prepare_provider
from emcd_sim.study_presets import nickel_geometry_settings


@pytest.mark.parametrize('element,crystal,a', [('Cr','bcc',2.88), ('Fe','bcc',2.87), ('Ni','fcc',3.524)])
def test_arbitrary_atoms_keep_neutral_provenance_and_snapshot_identity(element,crystal,a):
    structure=Structure(bulk(element,crystal,a=a,cubic=True))
    assert structure.source=='In-memory ASE structure'
    saved=structure_snapshot(structure)
    restored=restore_structure(saved)
    assert structures_match(saved,restored)
    assert restored.source==saved['source'] and restored.sha256==saved['sha256']
    # Loading preserves recorded provenance, even a historically misleading label.
    saved['source']='Built-in FCC Ni, a=3.524 Å'
    assert restore_structure(saved).source==saved['source']
    assert Structure.nickel().source==saved['source']


def test_new_geometry_is_neutral_and_old_ni_geometry_is_explicit():
    assert Settings().zone==(0,0,1) and Settings().tilt==(0.,0.)
    old=nickel_geometry_settings()
    assert type(old) is Settings
    assert old.zone==(0,1,7) and old.target==(2,0,0)
    assert old.tilt==(-5.5866881404,0.)


@pytest.mark.parametrize('cls',[ForwardSettings,MultiSiteForwardSettings,ImportedSettings,ProviderSettings])
def test_generic_records_cannot_select_ni_physics(cls):
    cfg=cls()
    assert cfg.atomic is None and not cfg.source and not cfg.centers
    assert np.isnan(cfg.l3) and np.isnan(cfg.l2) and cfg.radius==0.
    assert not cfg.correction and not cfg.window
    with pytest.raises(ValueError):prepare_provider(cfg).revalidate_source()


def test_detector_signals_require_explicit_sites_before_numerics():
    from emcd_sim.channeling import calculate_detector_signals
    with pytest.raises(ValueError,match='Explicit ionization_sites'):
        calculate_detector_signals(None,None,None,None,None,None,None,None,None)


def test_loading_distinguishes_historical_defaults_from_general_inputs():
    from emcd_sim.gui.project_io import config_from_dict,settings_from_dict
    assert settings_from_dict({})==nickel_geometry_settings(elastic_provider='nickel-lobato-2014')
    assert settings_from_dict({},historical_ni=False)==Settings()
    ni=NiForwardSettings(model='atomic')
    assert asdict(config_from_dict(asdict(ni)))==asdict(ni)
    assert config_from_dict({'model':'atomic'}).l3==ni.atomic.l3_ev
    generic=config_from_dict({'model':'imported'})
    assert generic.atomic is None and not generic.source
    draft=config_from_dict(dict(asdict(ForwardSettings()),model='atomic'))
    assert type(draft) is ForwardSettings and draft.atomic is None
    for invalid in ({'model':'unknown'},{'model':'xmcd','provider_declaration':{}},
                    {'model':'atomic','ionizing_element':'Cr'}):
        with pytest.raises(ValueError):config_from_dict(invalid)


def test_non_ni_missing_source_or_element_never_activates_historical_ni(tmp_path,monkeypatch):
    from test_multisite_forward import system,configuration
    from emcd_sim.forward_pipeline import calculate,validate_before_resources
    from emcd_sim import channeling
    structure,settings,_,references=system(tmp_path,'Cr')
    # This negative test selects the source's uniform branch; an unrelated AFM
    # eligibility error must not satisfy missing-declaration assertions.
    structure.atoms.set_initial_magnetic_moments([1.,1.])
    def forbidden(*args,**kwargs):
        raise AssertionError('An incomplete material declaration reached propagation')
    controls=configuration()
    base=replace(references[0],**{k:getattr(controls,k) for k in ('grid','depth','subpixels','fft_grid','slice_step','halfwidth','centers','radius')})
    validate_before_resources(structure,settings,base)
    with monkeypatch.context() as guard:
        guard.setattr(channeling,'propagate',forbidden)
        guard.setattr('emcd_sim.mdff_providers.HistoricalNiProvider',forbidden)
        for cfg in (replace(base,source=''),replace(base,ionizing_element='')):
            with pytest.raises(ValueError):calculate(structure,settings,cfg)
        with pytest.raises(ValueError,match='detector'):
            calculate(structure,settings,references[0])
        with pytest.raises(ValueError,match='detector centers'):
            calculate(structure,settings,replace(references[0],radius=controls.radius))
