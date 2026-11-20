"""Explicit model/geometry requests cannot fall through to an unrelated material."""
from types import SimpleNamespace

import pytest

from emcd_sim.forward_pipeline import calculate
from emcd_sim.forward_settings import MultiSiteForwardSettings
from emcd_sim.structure_geometry import Structure, Settings
from emcd_sim.mdff_providers import prepare_provider


@pytest.mark.parametrize('config',[None,object(),MultiSiteForwardSettings()])
def test_missing_model_or_assignments_fail_before_elastic_work(monkeypatch,config):
    def forbidden(*args,**kwargs):pytest.fail('Invalid request reached elastic preparation')
    monkeypatch.setattr('emcd_sim.forward_pipeline.elastic_model',forbidden)
    with pytest.raises(ValueError,match='Explicit material/model|Missing multi-site assignments'):
        calculate(Structure.nickel(),Settings(),config)


@pytest.mark.parametrize('model',['xmcd','atomic','imported','multisite'])
def test_unrecognized_input_object_never_selects_historical_ni(model):
    with pytest.raises(ValueError,match='declare a source-backed material'):
        prepare_provider(SimpleNamespace(model=model,source='unacknowledged-source'))


def test_supported_gui_entry_is_the_scientific_callable_and_result():
    import inspect
    import numpy as np
    from emcd_sim.gui.forward_pipeline import calculate as public_calculate
    from emcd_sim.forward_settings import NiForwardSettings

    assert public_calculate is calculate
    assert inspect.signature(public_calculate) == inspect.signature(calculate)
    assert calculate.__module__ == 'emcd_sim.forward_pipeline'
    settings = Settings(thickness=.3, beam_cutoff=.9, potential_cutoff=1.8)
    cfg = NiForwardSettings(model='xmcd', axis_declared=True, propagation='bloch',
        channeling_model='single', energy_scope='edges', grid=9, depth=9,
        subpixels=8, fft_grid=16, slice_step=.01, halfwidth=.7,
        centers=((.2, .2), (.2, -.2)), radius=.12, correction=False,
        worker_mode='manual', parallel_workers=1)
    public = public_calculate(Structure.nickel(), settings, cfg)['methods']['bloch']
    scientific = calculate(Structure.nickel(), settings, cfg)['methods']['bloch']
    for key in ('amplitudes', 'coherence', 'depth_nm', 'qx', 'qy'):
        np.testing.assert_array_equal(public[key], scientific[key])
    for key in public['spectra']:
        np.testing.assert_array_equal(public['spectra'][key], scientific['spectra'][key])
    for label, fields in public['maps'].items():
        for key, value in fields.items():
            np.testing.assert_array_equal(value, scientific['maps'][label][key])
