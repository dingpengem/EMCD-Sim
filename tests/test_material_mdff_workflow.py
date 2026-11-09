"""Material draft acceptance and source validation only; no propagation."""
import pytest
from ase.build import bulk

from test_multisite_gui_run import app, window
from emcd_sim.gui.geometry import Structure
from emcd_sim.gui.emcd_forward import DEFAULT_SOURCE
from emcd_sim.gui.project_session import capture_configuration, restore_configuration
from emcd_sim.gui.project_configuration import save_configuration, load_configuration
from emcd_sim.mdff_providers import prepare_provider


def xmcd_draft(w, lattice=3.52):
    w._reset_project_inputs()
    w.structure=Structure(bulk('Ni','fcc',a=lattice,cubic=True))
    w.show_structure_viewer()
    w.model_box.setCurrentIndex(0)
    w.source_path.setText(str(DEFAULT_SOURCE))
    w.source_path.editingFinished.emit()
    w.declaration.setChecked(True)
    return w.structure_viewer


def test_visible_defaults_done_then_material_apply(window):
    w=window;v=xmcd_draft(w)
    assert w.explicit_xmcd.isChecked() and not w.reference_ni.isChecked()
    assert w.xmcd_scale.text()=='1' and w.numerical_mode.currentIndex()==1
    assert w.spin['beam'].value()==2.5 and w.spin['potential'].value()==2
    cfg=w.mdff_dialog.apply_configuration()
    assert cfg.provider_schema==1 and w._accepted_global_mdff is None
    assert w.mdff_dialog.draft_ready()
    with pytest.raises(ValueError,match='Apply or Cancel'):capture_configuration(w)
    v.apply_groups()
    assert not v.isVisible() and w._accepted_global_mdff is not None
    assert w.forward_settings().provider_schema==1
    assert not prepare_provider(w.forward_settings()).material_reason(w.structure)


def test_empty_active_reference_has_named_error(window):
    w=window;xmcd_draft(w);w.xmcd_scale.clear()
    assert w.mdff_dialog.apply_configuration() is None
    assert 'Relative tensor reference (A^2/eV)' in w.mdff_dialog.status.text()
    assert 'positive finite' in w.mdff_dialog.status.text()
    assert w._accepted_global_mdff is None


def test_failed_done_and_viewer_cancel_preserve_acceptance(window):
    w=window;v=xmcd_draft(w);assert w.mdff_dialog.apply_configuration() is not None;v.apply_groups()
    accepted=w._accepted_global_mdff
    w.show_structure_viewer();w.xmcd_scale.clear()
    assert w.mdff_dialog.apply_configuration() is None
    assert w._accepted_global_mdff is accepted
    v.reject()
    assert w.xmcd_scale.text()=='1' and w._accepted_global_mdff is accepted
    assert not w.mdff_dialog.has_unapplied_edits()


def test_inactive_fields_and_direction_display_are_not_numeric_inputs(window):
    w=window;v=xmcd_draft(w)
    w.axis.clear()  # Read-only MDFF display is not Material state.
    w.atomic_editor.fields['l3'].clear();w.manual_bounds.clear()
    cfg=w.mdff_dialog.apply_configuration()
    assert cfg is not None and cfg.magnetization==(0,0,1)
    w.validate_xmcd(show_error=False)
    assert w.declaration.isChecked()  # Unchanged source needs no repeated confirmation.
    v.reject();assert w._accepted_global_mdff is None


def test_generalized_configuration_roundtrip(window,tmp_path):
    w=window;v=xmcd_draft(w);assert w.mdff_dialog.apply_configuration() is not None;v.apply_groups()
    before=capture_configuration(w)
    save_configuration(before,tmp_path/'project')
    restore_configuration(w,load_configuration(tmp_path/'project'))
    after=capture_configuration(w)
    assert after['config']==before['config']
    assert w.explicit_xmcd.isChecked() and w.numerical_mode.currentIndex()==1
    assert w.structure.atoms.cell.lengths().tolist()==[3.52]*3


def test_saved_historical_configuration_keeps_reference_adapter(window,tmp_path):
    w=window;v=xmcd_draft(w,3.524);w.reference_ni.setChecked(True)
    assert not w.xmcd_scale.isEnabled()
    w.xmcd_scale.clear()  # Inactive generalized-only input must not be parsed.
    assert w.mdff_dialog.apply_configuration() is not None;v.apply_groups()
    cfg=w._accepted_global_mdff
    assert not hasattr(cfg,'provider_schema')
    before=capture_configuration(w);save_configuration(before,tmp_path/'legacy')
    restore_configuration(w,load_configuration(tmp_path/'legacy'))
    provider=prepare_provider(w.forward_settings())
    assert not provider.declared and w.reference_ni.isChecked()
    assert not provider.material_reason(w.structure)
    assert 'a=3.524' in provider.material_reason(Structure(bulk('Ni','fcc',a=3.52,cubic=True)))
