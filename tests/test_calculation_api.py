"""Explicit model/geometry requests cannot fall through to an unrelated material."""
from types import SimpleNamespace

import pytest

from emcd_sim.gui.forward_pipeline import calculate
from emcd_sim.gui.forward_settings import MultiSiteForwardSettings
from emcd_sim.gui.geometry import Structure, Settings
from emcd_sim.mdff_providers import prepare_provider


@pytest.mark.parametrize('config',[None,object(),MultiSiteForwardSettings()])
def test_missing_model_or_assignments_fail_before_elastic_work(monkeypatch,config):
    def forbidden(*args,**kwargs):pytest.fail('Invalid request reached elastic preparation')
    monkeypatch.setattr('emcd_sim.gui.forward_pipeline.elastic_model',forbidden)
    with pytest.raises(ValueError,match='Explicit material/model|Missing multi-site assignments'):
        calculate(Structure.nickel(),Settings(),config)


@pytest.mark.parametrize('model',['xmcd','atomic','imported','multisite'])
def test_unrecognized_input_object_never_selects_historical_ni(model):
    with pytest.raises(ValueError,match='declare a source-backed material'):
        prepare_provider(SimpleNamespace(model=model,source='unacknowledged-source'))
