"""Truthful, read-only presentation of retained historical Atomic settings.

This adapter does not migrate inputs or implement transition physics. The
historical provider remains responsible for calculation and numerical preview.
"""
import numpy as np
from PySide6 import QtCore
from ..atomic_dipole import hydrogenic_radial_dipole_angstrom


def set_read_only(editor,enabled):
    for field in editor.fields.values():field.setReadOnly(enabled)
    for table in (editor.holes,editor.frame):
        for i in range(table.rowCount()):
            for j in range(table.columnCount()):table.cellWidget(i,j).setReadOnly(enabled)
    editor.element.setEnabled(not enabled);editor.frame_mode.setEnabled(not enabled)
    editor.scientific_status.setEnabled(not enabled);editor.direction.setReadOnly(enabled)
    editor.apply_direction.setEnabled(not enabled);editor.generate_button.setEnabled(not enabled)
    editor.saved_model_notice.setVisible(enabled)


def restore(editor,cfg,structure):
    if editor.historical_config is None and editor._element:editor._states[editor._element]=editor.draft()
    editor.clear_historical()
    editor.set_crystal(structure,preserve_validation=True)
    p=cfg.atomic
    radial=cfg.radial if cfg.radial is not None else hydrogenic_radial_dipole_angstrom(p.zeff_2p,p.zeff_3d)
    fields=dict(l3=str(p.l3_ev),l2=str(p.l2_ev),cf=str(p.crystal_field_10dq_ev),exchange=str(p.exchange_split_ev),
        radial=str(radial),sigma=str(cfg.sigma),emin=str(max(.001,p.l3_ev-10)),emax=str(p.l2_ev+10),samples=str(cfg.energy_points),
        source='Explicitly saved screened-hydrogenic / cubic Atomic model; retained original provider and inputs',
        radial_source='Saved explicit integral' if cfg.radial is not None else f'Saved effective charges: 2p={p.zeff_2p:g}, 3d={p.zeff_3d:g}; original radial implementation',
        assumptions='Saved independent-electron cubic model; uniform collinear magnetization; no material calibration',
        validity='Retained historical numerical semantics; this is not a newly generated generalized source')
    holes=[[p.eg_up_holes,p.eg_down_holes]]*2+[[p.t2g_up_holes,p.t2g_down_holes]]*3
    editor._loading=True;editor.element.setCurrentIndex(editor.element.findData('Ni'));editor._element='Ni'
    editor.historical_config=cfg
    editor.restore_draft(dict(fields=fields,holes=holes,frame=np.eye(3).tolist(),frame_mode=1,status='synthetic',
        parameter_origins={key:dict(origin='saved_project',citation='Explicit saved value; no current reference replacement') for key in editor.fields},
        origins={key:dict(origin='imported',title='Explicitly saved edge energy; not a current tabulated default') for key in ('l3','l2')}))
    with QtCore.QSignalBlocker(editor.use_editor):editor.use_editor.setChecked(False)
    editor.validated_path=editor.validated_sha256=None
    editor.invalidate_preview('Saved Atomic settings restored; prior numerical spectrum is stale')
    editor.preview_state.setText('STALE numerical spectrum - preview the retained saved model.')
    editor.source_location.clear()
    editor.saved_model_notice.setText('Saved model inputs (read-only): the original calculation provider is retained. Reset defaults explicitly starts a new editable Atomic draft.')
    set_read_only(editor,True);editor.update_derived()
    editor.status.setText('Saved Atomic parameters restored exactly, including explicit zeros. No current edge references substituted.')


def preview(editor,cfg,energy,plus,minus):
    a,b=plus.tensor_angstrom2_per_ev,minus.tensor_angstrom2_per_ev
    editor.spectrum_figure.clear();ax=editor.spectrum_figure.subplots()
    for name,value in (('+M',a),('-M',b),('Even',(a+b)/2),('Odd',(a-b)/2)):
        ax.plot(energy,np.trace(value,axis1=-2,axis2=-1).real/3,label=name)
    ax.set(xlabel='Energy loss (eV)',ylabel='Tr(T)/3');ax.legend(fontsize=8);editor.spectrum_canvas.draw_idle()
    editor.historical_preview=dict(config=cfg,energy=energy.copy(),plus=a.copy(),minus=b.copy())
    editor.preview_state.setText('CURRENT retained saved-model tensor preview; original energies, splitting and radial convention. Calculation sampling is retained separately.')
