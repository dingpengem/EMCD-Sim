"""Existing source acceptance and request sampling; no propagation."""
from dataclasses import asdict

from test_multisite_gui_run import app,window,controls
from emcd_sim.gui.emcd_forward import energy_grid
from emcd_sim.gui.forward_pipeline import request_energy_grid
from emcd_sim.mdff_providers import prepare_provider
from emcd_sim.gui.project_session import capture_configuration,restore_configuration
from emcd_sim.gui.project_configuration import save_configuration,load_configuration


def test_global_xmcd_single_edge_acceptance_request_and_restore(window,tmp_path):
    controls(window,window.structure)
    window.model_box.setCurrentIndex(0);window.validate_xmcd(show_error=False)
    window.declaration.setChecked(True)
    accepted=window.mdff_dialog.apply_configuration()
    assert accepted is not None,window.mdff_dialog.status.text()
    source=accepted.source;identity=accepted.source_sha256
    native=dict(window.source_info['selected'])
    window.edge_sample.setCurrentIndex(window.edge_sample.findData('L3'))
    sc=window.forward_settings()
    assert sc.selected_edges==(('L3',native['L3']),)
    assert list(energy_grid(sc))==[native['L3'],native['L2']]  # Historical source validation unchanged.
    assert list(request_energy_grid(prepare_provider(sc),sc))==[native['L3']]
    assert sc.source==source and sc.source_sha256==identity
    assert window.source_info['selected']==native and sc.l2==native['L2']
    window.channeling_box.setCurrentIndex(1);dc=window.forward_settings()
    assert dc.channeling_model=='double'
    assert dict(asdict(dc),channeling_model='single')==asdict(sc)
    path=tmp_path/'project';save_configuration(capture_configuration(window),path)
    restored=load_configuration(path);restore_configuration(window,restored)
    assert window.edge_sample.currentData()=='L3'
    cfg=window.forward_settings()
    assert list(request_energy_grid(prepare_provider(cfg),cfg))==[native['L3']]
    window.edge_sample.setCurrentIndex(0)
    cfg=window.forward_settings()
    assert list(request_energy_grid(prepare_provider(cfg),cfg))==[native['L3'],native['L2']]
