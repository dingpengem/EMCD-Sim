"""Provider contract and exact historical evaluation through common preparation."""
from dataclasses import replace
import numpy as np
import pytest
from emcd_sim.gui import emcd_forward, generalized_forward, forward_pipeline
from emcd_sim.gui.geometry import Structure
from emcd_sim.mdff_providers import prepare_provider
from test_part1c_refactor import accepted_module
from test_unified_mdff_providers import xmcd_source


def test_forward_entry_points_are_aliases_not_parallel_orchestration():
    from emcd_sim.gui import stage_b
    assert stage_b.calculate is forward_pipeline.calculate
    assert generalized_forward.calculate is forward_pipeline.calculate is emcd_forward.calculate


@pytest.mark.parametrize('model',['xmcd','atomic'])
@pytest.mark.parametrize('scope',['edges','full'])
def test_historical_provider_grid_and_direct_tensors_are_exact(model,scope):
    reference=accepted_module('gui/emcd_forward.py','_part1c_forward_reference')
    cfg=emcd_forward.ForwardSettings(model=model,axis_declared=True,energy_points=13,energy_scope=scope)
    if model=='atomic':cfg=replace(cfg,l3=cfg.atomic.l3_ev,l2=cfg.atomic.l2_ev)
    provider=prepare_provider(cfg)
    assert not provider.declared
    assert not provider.material_reason(Structure.nickel())
    expected=reference.energy_grid(cfg)
    np.testing.assert_array_equal(provider.energy_grid(),expected)
    rotation=np.array([[0.,1.,0.],[-1.,0.,0.],[0.,0.,1.]])
    for old,new in zip(reference.tensors(cfg,expected,rotation),provider.tensors(expected,rotation)):
        np.testing.assert_array_equal(new.tensor_angstrom2_per_ev,old.tensor_angstrom2_per_ev)
        assert new.source==old.source


def test_declared_xmcd_uses_same_preparation_interface(tmp_path):
    path,declaration=xmcd_source(tmp_path)
    cfg=generalized_forward.settings_for_provider(path,'xmcd',declaration,energy_scope='edges')
    provider=prepare_provider(cfg)
    assert provider.declared and provider.source.sha256==cfg.source_sha256
    np.testing.assert_array_equal(provider.energy_grid(),[710.])
    for a,b in zip(provider.tensors([710.],np.eye(3)),generalized_forward.tensors(cfg,[710.],np.eye(3))):
        np.testing.assert_array_equal(a.tensor_angstrom2_per_ev,b.tensor_angstrom2_per_ev)
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError,match='checksum changed'):provider.revalidate_source()
