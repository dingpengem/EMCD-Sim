"""Provider contract and exact historical evaluation through common preparation."""
from emcd_sim.forward_pipeline import calculate
from emcd_sim.forward_settings import NiForwardSettings
from dataclasses import replace
import numpy as np
import pytest
from emcd_sim import forward_pipeline as forward_pipeline
from emcd_sim import mdff_providers as material_inputs
from emcd_sim.structure_geometry import Structure
from emcd_sim.mdff_providers import prepare_provider
from test_part1c_refactor import accepted_module
from test_unified_mdff_providers import xmcd_source


def test_worker_uses_canonical_production_entrypoint():
    from emcd_sim.gui import calculation_worker
    assert calculation_worker.calculate is forward_pipeline.calculate


@pytest.mark.parametrize('model',['xmcd','atomic'])
@pytest.mark.parametrize('scope',['edges','full'])
def test_historical_provider_grid_and_direct_tensors_are_exact(model,scope):
    reference=accepted_module('gui/emcd_forward.py','_part1c_forward_reference')
    cfg=NiForwardSettings(model=model,axis_declared=True,energy_points=13,energy_scope=scope)
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
    # Keep the aperture inputs formerly inherited before settings became neutral.
    cfg=material_inputs.settings_for_provider(path,'xmcd',declaration,energy_scope='edges',
        centers=((0.2837684449489217,0.2837684449489217),(0.2837684449489217,-0.2837684449489217)),radius=0.0908059024)
    provider=prepare_provider(cfg)
    assert provider.declared and provider.source.sha256==cfg.source_sha256
    np.testing.assert_array_equal(provider.energy_grid(),[710.])
    for a,b in zip(provider.tensors([710.],np.eye(3)),material_inputs.tensors(cfg,[710.],np.eye(3))):
        np.testing.assert_array_equal(a.tensor_angstrom2_per_ev,b.tensor_angstrom2_per_ev)
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError,match='checksum changed'):provider.revalidate_source()


def test_retired_modules_absent_and_no_production_imports():
    import ast
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]/'src/emcd_sim'
    assert not (root/'ni_local_mdff.py').exists()
    assert not (root/'gui/legacy_ni_provider.py').exists()
    for path in root.rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            if isinstance(node,ast.ImportFrom):assert node.module is None or not node.module.endswith('ni_local_mdff')


def test_obsolete_material_specific_numerical_aliases_are_absent():
    from emcd_sim import multislice_double_channeling as ms
    from emcd_sim import single_channeling_tensor as single
    from emcd_sim import historical_ni
    assert not hasattr(ms,'ProjectedNiFFT')
    assert not hasattr(single,'fcc_site_phase_matrix')
    assert not hasattr(historical_ni,'ni_2p_to_3d_dipole')
