"""Preview eligibility and working settings only: no wave propagation."""
from dataclasses import replace
from pathlib import Path

import pytest
from PySide6 import QtWidgets

from test_multisite_gui_run import app, window, controls
from test_mdff_workspace_participation import configure_fe
from test_group_mdff import source
from emcd_sim.gui import app as gui
from emcd_sim.gui.geometry import Settings, Structure, geometry
from emcd_sim.gui.emcd_forward import ForwardSettings
from emcd_sim.gui.generalized_forward import settings_for_source
from emcd_sim.gui.numerical_settings import resolve_parameters
from emcd_sim.gui.project_session import capture_configuration, restore_configuration
from emcd_sim.gui.project_configuration import save_configuration, load_configuration
from emcd_sim.gui.multisite_run import applied_inputs


def test_manual_cutoff_refresh_and_absent_target_preview_request(window,monkeypatch):
    path=Path(__file__).parent/'fixtures/Fe3O4_inverse_spinel.cif'
    monkeypatch.setattr(QtWidgets.QFileDialog,'getOpenFileName',lambda *a,**k:(str(path),''))
    window.load_cif();window.numerical_mode.setCurrentIndex(1)
    window.spin['beam'].setValue(3.2)
    assert not window.run_button.isEnabled()
    assert '143 beams' in window.run_button.toolTip() and '121' in window.run_button.toolTip()
    window.spin['beam'].setValue(2.)  # Signal path, deliberately no explicit refresh.
    assert len(window.current[2])==59
    assert window.settings().beam_cutoff==2 and window.drawn_settings==window.settings()
    assert (2,0,0) not in window.current[2]  # Fe3O4 extinction, not invalid orientation.
    assert window.run_button.isEnabled(),window.run_button.toolTip()
    assert not window.align_button.isEnabled()
    assert all(r[3] is None and r[4] is None for r in window.structure_viewer.editor.rows())
    monkeypatch.setattr(gui.PreviewWorker,'start',lambda worker:None)
    window.start_preview()
    assert window.busy and window.worker.settings.beam_cutoff==2
    assert len(window.worker.structure.atoms)==56
    window.finished()
    window.numerical_mode.setCurrentIndex(0);window.numerical_mode.setCurrentIndex(1)
    assert window.run_button.isEnabled() and window.settings().beam_cutoff==2
    window.basis_mode.setCurrentIndex(1)
    assert not window.run_button.isEnabled()
    assert 'No nonzero ZOLZ reflections' in window.run_button.toolTip()
    window.basis_mode.setCurrentIndex(0);window.target.setText('0 1 7');window.apply_orientation()
    assert not window.run_button.isEnabled()  # Invalid target/zone geometry still rejected.


def test_fresh_reset_and_automatic_defaults(window):
    assert (Settings().beam_cutoff,Settings().potential_cutoff)==(2.5,2.)
    assert (window.settings().beam_cutoff,window.settings().potential_cutoff)==(2.5,2.)
    values,_=resolve_parameters(window.structure,window.settings(),ForwardSettings(model='atomic'))
    assert (values['beam'],values['potential'])==(2.5,2.)
    assert not window.correction.isChecked() and not window.correction.isVisible()
    window.set_values(dict(beam=2.1,potential=1.7));window.correction.setChecked(True)
    window._reset_project_inputs()
    assert (window.settings().beam_cutoff,window.settings().potential_cutoff)==(2.5,2.)
    assert not window.correction.isChecked()


def test_legacy_local_flag_retired_without_changing_saved_source(window,tmp_path):
    editor=configure_fe(window,tmp_path);window.set_values(dict(beam=2.1,potential=1.7))
    state=capture_configuration(window);state['config']=replace(state['config'],correction=True)
    path=tmp_path/'legacy-local';save_configuration(state,path)
    original=(path/'input_parameters.json').read_bytes()
    restored=load_configuration(path);restore_configuration(window,restored)
    assert restored['config'].correction and state['config'].correction
    assert (path/'input_parameters.json').read_bytes()==original
    assert not window.correction.isChecked() and not window.correction_notice.isHidden()
    assert (window.settings().beam_cutoff,window.settings().potential_cutoff)==(2.1,1.7)
    window.correction.setChecked(True)  # Even stale hidden state cannot re-enable it.
    cfg,sites,_,_,_=applied_inputs(window,window.forward_settings())
    assert not cfg.correction and sum(g.multiplicity for g in sites.groups)==24
    assert len(window.structure.atoms)==56 and len(window.structure_viewer.editor.excluded_groups)==1
    corrected=capture_configuration(window);assert not corrected['config'].correction
    save_configuration(corrected,tmp_path/'corrected');reopened=load_configuration(tmp_path/'corrected')
    assert not reopened['config'].correction and reopened['ready_for_calculation']
    rows=window.structure_viewer.editor.rows();fe=next(r for r in rows if r[1]=='Fe')
    editor=window.structure_viewer.editor
    editor.replace_rows(tuple(r[:4]+(None,) if r[0]==fe[0] else r for r in rows));editor.apply()
    with pytest.raises(ValueError,match='Enabled group'):
        applied_inputs(window,window.forward_settings())


def test_global_legacy_flag_cannot_override_new_requests(window,tmp_path,monkeypatch):
    controls(window,window.structure)
    reference=replace(settings_for_source(source(tmp_path,element='Ni')),correction=True)
    window._accepted_global_mdff=reference;window._saved_global_config=reference
    state=capture_configuration(window);state['config']=replace(state['config'],correction=True)
    restore_configuration(window,state)
    assert state['config'].correction and reference.correction  # Recorded originals untouched.
    assert not window._accepted_global_mdff.correction
    window.correction.setChecked(True)
    assert not window.forward_settings().correction
    original=window.imported_forward_settings;seen=[]
    def inspect(cfg,**kwargs):
        seen.append(cfg.correction)
        return original(cfg,**kwargs)
    monkeypatch.setattr(window,'imported_forward_settings',inspect)
    with pytest.raises(ValueError,match='Manual draft ready'):
        window.global_mdff_draft_settings(prepare=False)
    assert seen==[False]  # Retirement does not bypass the source's own validation.
    assert not capture_configuration(window)['config'].correction
