"""Local Material transactions and MDFF previews; no propagation."""
import pytest
from ase.build import bulk
from PySide6 import QtCore

from test_multisite_gui_run import app, window, controls
from emcd_sim.gui.geometry import Structure
from emcd_sim.gui.emcd_forward import DEFAULT_SOURCE
from emcd_sim.gui.project_session import capture_configuration, restore_configuration
from emcd_sim.gui.project_configuration import save_configuration, load_configuration
from emcd_sim.gui.multisite_run import applied_inputs
from emcd_sim.crystallographic_sites import crystallographic_sites


def local_draft(w,model,*,direction=True):
    atoms=bulk('Ni','fcc',a=3.52,cubic=True)
    atoms.info['crystallographic_sites']=crystallographic_sites(atoms)
    controls(w,Structure(atoms,source='Synthetic Ni a=3.520 A'))
    w.show_structure_viewer();v=w.structure_viewer;e=v.editor
    e.mode.setCurrentIndex(1);e.groups.setCurrentItem(e.groups.topLevelItem(0))
    if direction:e.direction.setText('0 0 1');e.update_direction()
    w.set_material_magnetization((1,0,0))  # Inactive Global M must not override the group.
    d=w.open_mdff_context(e.rows()[0][0]);d.model.setCurrentIndex(0 if model=='xmcd' else 1)
    if model=='xmcd':
        d.source_path.setText(str(DEFAULT_SOURCE));d.source_path.editingFinished.emit()
        d.xmcd_conventions.setChecked(True)
    else:d.declaration.setChecked(True)
    return v,e,d


@pytest.mark.parametrize('model',['xmcd','atomic'])
def test_local_preview_done_cancel_and_roundtrip(window,tmp_path,model):
    w=window;v,e,d=local_draft(w,model)
    assert d.row[2]==(0,1,2,3) and d.row[3]==(0,0,1)
    assert not w.axis.isEnabled() and w._accepted_global_mdff is None
    d.preview_current_model()
    assert d.source_conventions_confirmed() if model=='xmcd' else d.declaration.isChecked()
    assert 'Preview ready' in d.status.text()
    if model=='xmcd':
        assert (d.spin['xl3'].value(),d.spin['xl2'].value())==(831.271,848.698)
        assert d.eta.value()==d.beta.value()==1 and not d.reference_ni.isVisibleTo(d)
        assert not d.xmcd_provenance.text() and not d.xmcd_validity.text()
    cfg=d.apply_configuration();assert cfg is not None,d.status.text()
    assert cfg.model==model and cfg.magnetization==(0,0,1) and cfg.provider_schema==1
    assert v.accepted_site_groups is None
    v.apply_groups();assert v.accepted_site_groups is not None
    original=v.accepted_site_groups.groups[0].mdff_reference
    request,sites,windows,reverse,signature=applied_inputs(w,w.forward_settings())
    assert request.model=='multisite' and request.energy_points==2
    assert sites.groups[0].indices==(0,1,2,3) and sites.groups[0].multiplicity==4
    assert sites.groups[0].mdff_reference.model==model and sites.groups[0].magnetization==(0,0,1)
    w.show_structure_viewer();d=w.open_mdff_context(e.rows()[0][0])
    if model=='xmcd':d.xmcd_scale.setText('2')
    else:d.atomic.fields['sigma'].setText('1.2')
    assert d.apply_configuration() is not None,d.status.text()
    v.reject()  # Reject the parent draft after Done; accepted provider is unchanged.
    assert v.accepted_site_groups.groups[0].mdff_reference==original
    state=capture_configuration(w);save_configuration(state,tmp_path/'saved')
    restore_configuration(w,load_configuration(tmp_path/'saved'))
    restored=applied_inputs(w,w.forward_settings())[1].groups[0]
    assert restored.indices==(0,1,2,3) and restored.magnetization==(0,0,1)
    assert restored.mdff_reference.model==model and restored.mdff_reference.source_sha256==original.source_sha256
    assert w._accepted_global_mdff is None


def test_changed_xmcd_source_does_not_silently_replace_acceptance(window,tmp_path):
    w=window;v,e,d=local_draft(w,'xmcd');path=tmp_path/'Ni.xmcd'
    path.write_bytes(DEFAULT_SOURCE.read_bytes());d.source_path.setText(str(path));d.source_path.editingFinished.emit();d.xmcd_conventions.setChecked(True)
    assert d.apply_configuration() is not None;v.apply_groups();accepted=v.accepted_site_groups
    w.show_structure_viewer();d=w.open_mdff_context(e.rows()[0][0])
    path.write_bytes(path.read_bytes()+b'\n# changed source identity\n')
    assert d.apply_configuration() is None
    assert not d.source_conventions_confirmed() and v.accepted_site_groups is accepted


def test_unconfigured_direction_stays_unconfigured(window):
    w=window;v,e,d=local_draft(w,'xmcd',direction=False)
    d.preview_current_model();assert 'Material direction' in d.status.text()
    assert d.apply_configuration() is None and 'Material direction' in d.status.text()
    assert e.rows()[0][3] is None and v.accepted_site_groups is None
    d.reject();v.reject()  # No rendering/Cancel exception for missing M.


def test_atomic_frame_validation_remains_strict(window):
    w=window;v,e,d=local_draft(w,'atomic')
    assert d.atomic.direction.isReadOnly() and d.atomic.direction.text() in ('0 0 1','0.0 0.0 1.0')
    d.atomic.frame.cellWidget(0,0).setText('2')
    assert d.apply_configuration() is None
    assert 'frame' in d.status.text().lower() or 'orthonormal' in d.status.text().lower()
    assert v.accepted_site_groups is None and w._accepted_global_mdff is None
