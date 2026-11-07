"""Explicit XMCD selections follow the visible controls after project reopen."""
from dataclasses import replace
import numpy as np
import pytest

from test_atomic_parameter_editor import window, iron
from emcd_sim.gui.generalized_forward import source_for, energy_grid, tensors
from emcd_sim.gui.forward_pipeline import calculate
from emcd_sim.gui.geometry import Settings
from emcd_sim.gui.project_io import save_project, load_project


def test_manual_fe_selections_preview_calculation_and_reopen(window, tmp_path):
    w, app = window
    iron(w)
    w.model_box.setCurrentIndex(0)
    energy = np.linspace(704, 730, 27)
    # No local maxima: users must still be able to declare native selections.
    n = np.linspace(.5, 1, len(energy))
    m = np.full_like(n, .02)
    path = tmp_path/'synthetic_fe.xmcd'
    np.savetxt(path, np.column_stack([energy, n+m, n-m, 2*m, 2*n]))
    w.source_path.setText(str(path))
    w.validate_xmcd()
    assert w.source_info['selected'] is None
    w.explicit_xmcd.setChecked(True)
    for widget, value in ((w.xmcd_element, 'Fe'), (w.xmcd_provenance, 'Synthetic software test'),
                          (w.xmcd_validity, 'Not measured Fe spectroscopy'), (w.xmcd_scale, '.3')):
        widget.setText(value)
    w.xmcd_status.setCurrentText('synthetic')
    w.set_values({'xl3': 710, 'xl2': 723})
    w.declaration.setChecked(True)
    cfg = w.forward_settings()
    assert source_for(cfg).metadata['selected_ev'] == {'L3': 710, 'L2': 723}
    w.preview_mdff()
    assert not w.errors
    cfg = replace(cfg, energy_scope='edges', grid=9, depth=5, subpixels=4,
                  halfwidth=.7, radius=.12, centers=((.2,.2),(.2,-.2)),
                  correction=False, worker_mode='manual', parallel_workers=1)
    np.testing.assert_array_equal(energy_grid(cfg), [710, 723])
    np.testing.assert_array_equal(tensors(cfg, [710,723], np.eye(3))[0].tensor_angstrom2_per_ev,
                                  source_for(cfg).tensors([710,723], np.eye(3), cfg.magnetization)[0].tensor_angstrom2_per_ev)
    settings = Settings(zone=(0,0,1), target=(1,1,0), voltage=200, thickness=.2,
                        tilt=(-5,7), beam_cutoff=.6, potential_cutoff=1.2)
    result = calculate(w.structure, settings, cfg)
    folder = tmp_path/'project'
    save_project(result, folder)
    opened = load_project(folder)
    w.restore_provider_settings(opened['config'])
    assert w.xmcd_selected.text() == ''
    assert not w.xmcd_selected.isEnabled()
    assert (w.spin['xl3'].value(), w.spin['xl2'].value()) == (710, 723)
    w.declaration.setChecked(True)
    assert w.forward_settings().provider_declaration['selected_ev'] == {'L3': 710, 'L2': 723}
    # Even leftover text from another edge cannot override visible L2,3 controls.
    w.xmcd_selected.setText('{"L3": 710, "L2": 723}')
    w.set_values({'xl3': 711, 'xl2': 724})
    w.declaration.setChecked(True)
    assert w.forward_settings().provider_declaration['selected_ev'] == {'L3': 711, 'L2': 724}
    w.set_values({'xl3': 831})
    w.declaration.setChecked(True)
    with pytest.raises(ValueError):
        w.forward_settings()
    w.xmcd_edge.setText('K')
    assert w.xmcd_selected.isEnabled()
    w.xmcd_selected.setText('{"K": 715}')
    w.declaration.setChecked(True)
    native = w.forward_settings()
    assert source_for(native).metadata['selected_ev'] == {'K': 715}
    w.restore_provider_settings(native)
    assert w.xmcd_selected.isEnabled()
    w.declaration.setChecked(True)
    assert w.forward_settings().provider_declaration['selected_ev'] == {'K': 715}
