"""Opt-in native Cocoa acceptance. Uses real controls, workers, and fresh projects."""
import json
from importlib.metadata import version
from dataclasses import asdict
from pathlib import Path
import platform
import sys
import time
import traceback
from unittest.mock import patch

import numpy as np
from PySide6 import QtCore, QtWidgets


def run(output, *, release=False):
    from ase.build import bulk
    from ase.io import write
    from ase.spacegroup import crystal
    from emcd_sim.gui.app import MainWindow, add_about_menu
    from emcd_sim.gui.runtime import resource_root, build_info
    from emcd_sim.gui.project_io import fingerprints, source_status
    from emcd_sim.gui.emcd_forward import export_result
    from emcd_sim.gui.normalization_export import save_figure

    out = Path(output).resolve();out.mkdir(parents=True, exist_ok=False)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    report = dict(build=build_info(), platform=platform.platform(), architecture=platform.machine(),
                  qt_platform=app.platformName(), frozen=bool(getattr(sys,'frozen',False)),
                  python=platform.python_version(),qt=QtCore.qVersion(),
                  versions=build_info().get('versions',{}) if getattr(sys,'frozen',False) else {name:version(name) for name in ('numpy','scipy','matplotlib','PySide6','ase','spglib')},
                  checks=[], cases={}, errors=[], complete=False,
                  scope='Automated native widgets and real bounded workers; file-dialog paths injected. Synthetic Cr/Fe/ferrite MDFF is software validation only.')
    assert app.platformName() == 'cocoa', 'Native Cocoa platform required'
    windows=[]
    modal_seen={}
    def inspect_modal():
        # Native Cocoa alerts need not appear as activeModalWidget().
        for modal in app.allWidgets():
            if not isinstance(modal,QtWidgets.QMessageBox) or id(modal) in modal_seen:continue
            modal_seen[id(modal)]=modal
            detail=dict(type=type(modal).__name__,title=modal.windowTitle(),text=modal.text(),informative=modal.informativeText())
            print('MODAL:',detail,flush=True)
            report.setdefault('modal_dialogs',[]).append(detail)
            modal.grab().save(str(out/('modal_'+str(len(modal_seen))+'.png')))
            if modal.windowTitle()=='Retain Calculation':
                keep=next(b for b in modal.buttons() if b.text()=='Keep as New Calculation')
                keep.click();continue
            report['errors'].append('Unexpected modal: '+str(detail))
            modal.reject()
    modal_timer=QtCore.QTimer();modal_timer.timeout.connect(inspect_modal);modal_timer.start(100)
    def record(name):
        report['checks'].append(name)
        print('PASS:',name,flush=True)
        (out/'acceptance.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
    def wait(w):
        deadline=time.monotonic()+180
        while w.busy and time.monotonic()<deadline:
            app.processEvents();time.sleep(.01)
        assert not w.busy, 'Worker timeout'
        assert not report['errors'], report['errors']
        app.processEvents()
    def window(name,cif):
        w=MainWindow(out/(name+'_workspace'));windows.append(w)
        w.error=lambda msg:report['errors'].append(str(msg))
        w.store_ui_preferences=lambda:None
        w.show();add_about_menu(w);app.processEvents()
        from emcd_sim.gui.responsive import CollapsibleSection
        sections=[s for s in w.findChildren(CollapsibleSection) if s.objectName().startswith('settings_')]
        assert len(sections)==7,len(sections)
        for section in sections:
            section.setChecked(True);app.processEvents();section.setChecked(False)
        record(name+': seven settings sections, native menus and resizing')
        w.resize(1092,720);app.processEvents()
        w.resize(1440,900);app.processEvents()
        with patch.object(QtWidgets.QFileDialog,'getOpenFileName',return_value=(str(cif),'')):
            w.load_cif()
        assert not report['errors'],report['errors']
        w.show_structure_viewer();app.processEvents()
        assert w.structure_viewer.isVisible()
        w.structure_viewer.grab().save(str(out/(name+'_structure.png')))
        return w
    def retire(*widgets):
        for w in widgets:
            w.project_dirty=False;w.close();w.deleteLater();windows.remove(w)
        app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
    def controls(w):
        w.numerical_mode.setCurrentIndex(1)
        w.zone.setText('0 0 1');w.target.setText('4 0 0' if len(w.structure.atoms)==56 else '2 0 0')
        w.basis_mode.setCurrentIndex(1);w.propagation_box.setCurrentIndex(0)
        w.channeling_box.setCurrentIndex(0)
        w.energy_scope.setCurrentIndex(w.energy_scope.findData('edges'))
        w.worker_mode.setCurrentIndex(1);w.worker_count.setValue(1)
        w.correction.setChecked(False);w.angular_maps.setChecked(True)
        w.set_values(dict(kv=200,thickness=.1,beam=.6,potential=1.2,grid=9,depth=3,
                          subpixels=4,fft_grid=16,slice_step=.02,halfwidth=.7,radius=.12,tx=-5,ty=7))
        w.detectors=np.array([[.2,.2],[.2,-.2]]);w.refresh()
    def calculate(w,name):
        print('Calculating:',name,flush=True)
        if release:
            w.worker_mode.setCurrentIndex(0);w.memory_mode.setCurrentIndex(0)
        w.refresh();w.emcd_stale()
        assert w.emcd_button.isEnabled(),w.emcd_button.toolTip()
        # No selected history row means the standard GUI retains a new run.
        # Native NSAlert retention sheets are reserved for human acceptance.
        w.browser.table.clearSelection();w.browser.selection_timer.stop()
        w.start_emcd();assert w.busy
        wait(w);assert w.run_outcome=='completed',w.run_outcome
        r=w.emcd_result
        if release:
            final=w.resource_panel.finalized['info']
            assert final['execution']['effective_workers']==r['metadata']['execution']['effective_workers']
            assert final['memory_budget_mib']==r['config'].memory_budget_mib
        for value in r['spectra'].values():
            if isinstance(value,np.ndarray):assert np.isfinite(value).all()
        if r['config'].model=='multisite':
            c=w.eels_view.multisite_controls
            for index in range(c.selection.count()):
                c.selection.setCurrentIndex(index)
                for norm in (0,1):c.normalization.setCurrentIndex(norm);w.eels_view.redraw()
            for index in range(w.maps_view.map_scope.count()):
                w.maps_view.map_scope.setCurrentIndex(index);w.maps_view.redraw()
            c.selection.setCurrentIndex(0)
            record(name+': total/element/group/comparison rendering and group means')
        export_result(r,out/(name+'_exports'))
        save_figure(w.eels_view.figure,out/(name+'_spectra.png'))
        w.grab().save(str(out/(name+'_window.png')))
        report['cases'][name]=dict(settings=asdict(r['settings']),config=asdict(r['config']),methods=list(r['methods']),execution=r.get('metadata',{}).get('execution'),
                                   fingerprints=fingerprints(r))
        if release:report['cases'][name]['final_allocation_notice']=w.resource_panel.run_allocation_text
        return r
    def save_reopen(w,name):
        w.emcd_stale()
        assert 'inputs match' in w.eels_view.label.text(),w.eels_view.label.text()
        thickness=w.spin['thickness'].value();w.spin['thickness'].setValue(thickness+.1)
        w.emcd_stale();assert 'STALE RESULT' in w.eels_view.label.text()
        w.spin['thickness'].setValue(thickness);w.emcd_stale()
        assert 'inputs match' in w.eels_view.label.text()
        record(name+': changed-input stale detection and exact revert')
        before=fingerprints(w.emcd_result)
        path=out/(name+'_project');w.save_to_path(path);wait(w)
        assert (path/'project.json').is_file()
        reopened=MainWindow(out/(name+'_reopen_workspace'));windows.append(reopened)
        reopened.error=lambda msg:report['errors'].append(str(msg));reopened.store_ui_preferences=lambda:None
        reopened.show();reopened.open_project_path(path);wait(reopened)
        assert fingerprints(reopened.emcd_result)==before
        assert all(s['verified'] for s in source_status(reopened.emcd_result).values())
        reopened.emcd_stale()
        assert reopened.emcd_button.isEnabled(),reopened.emcd_button.toolTip()
        assert len(reopened.browser.registry.records)==len(w.browser.registry.records)
        record(name+': collection save/reopen, settings and numerical arrays')
        return reopened
    try:
        root=resource_root()
        examples=root/'examples' if getattr(sys,'frozen',False) else root/'packaging/assets/examples'
        ni=window('Ni',examples/'Ni_FCC_a3.52.cif');controls(ni)
        assert len(ni.structure.atoms)==4
        ni.model_box.setCurrentIndex(0);ni.source_path.setText(str(root/'data/wien2k_ni/Ni_fm.xmcd'))
        ni.source_path.editingFinished.emit();ni.declaration.setChecked(True)
        if release:
            from PySide6 import QtTest
            d=ni.open_mdff_context();app.processEvents()
            QtTest.QTest.mouseClick(d.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Apply),QtCore.Qt.MouseButton.LeftButton)
            app.processEvents()
            assert ni.structure_viewer.isVisible() and ni.structure_viewer.isActiveWindow() and not d.isVisible()
            record('Ni: native MDFF Done click returns to active Viewer')
        else:assert ni.mdff_dialog.apply_configuration() is not None,ni.mdff_dialog.status.text()
        ni.structure_viewer.apply_groups()
        ni.start_preview();wait(ni);assert ni.last_result is not None
        record('Ni CIF import and diffraction worker')
        calculate(ni,'Ni_global_BW_single')
        ni.propagation_box.setCurrentIndex(2)
        both=calculate(ni,'Ni_global_BW_MS_comparison')
        assert set(both['methods'])=={'bloch','fft-multislice'}
        record('Ni: BW/MS result binding and comparison interface')
        ni.propagation_box.setCurrentIndex(0)
        # Supported Local Ni XMCD route through Material / site groups.
        ni.show_structure_viewer();e=ni.structure_viewer.editor;e.mode.setCurrentIndex(1)
        e.groups.setCurrentItem(e.groups.topLevelItem(0));e.direction.setText('0 0 1');e.update_direction()
        d=ni.open_mdff_context(e.rows()[0][0]);d.model.setCurrentIndex(0)
        d.source_path.setText(str(root/'data/wien2k_ni/Ni_fm.xmcd'));d.source_path.editingFinished.emit()
        d.xmcd_conventions.setChecked(True)
        assert d.apply_configuration() is not None,d.status.text()
        ni.structure_viewer.apply_groups();calculate(ni,'Ni_local_BW_single')
        reopened=save_reopen(ni,'Ni')
        from emcd_sim.gui.calculation_comparison import CalculationComparison
        comparison=CalculationComparison(reopened);comparison.show();app.processEvents()
        comparison.grab().save(str(out/'Ni_two_run_comparison.png'));comparison.close()
        record('Ni: two saved runs rendered in comparison dialog')
        saved=reopened.emcd_result
        recalculated=calculate(reopened,'Ni_reopened_recalculated')
        scale=max(np.max(np.abs(saved['spectra'][k])) for k in ('I_A_plus','I_A_minus','I_B_plus','I_B_minus'))
        for key,value in saved['spectra'].items():
            if isinstance(value,np.ndarray):
                np.testing.assert_allclose(recalculated['spectra'][key],value,rtol=2e-10,atol=scale*2e-12)
        record('Ni: reopened project recalculates equivalent spectra, rtol=2e-10 and atol=2e-12*raw intensity scale')

        retire(ni,reopened);ni=reopened=e=d=None
        import gc;gc.collect()

        # Full 56-atom fixture, preserving ASE indices and structural orbits.
        fe_path=root/'examples/Fe3O4_inverse_spinel.cif' if getattr(sys,'frozen',False) else root/'tests/fixtures/Fe3O4_inverse_spinel.cif'
        fe=window('Fe3O4',fe_path);controls(fe)
        assert len(fe.structure.atoms)==56
        provenance=fe.structure.atoms.info['crystallographic_sites']
        assert [(g['element'],g['atom_count']) for g in provenance['groups']]==[('Fe',8),('Fe',16),('O',32)]
        e=fe.structure_viewer.editor;e.mode.setCurrentIndex(1)
        for row in range(e.groups.topLevelItemCount()):
            e.groups.setCurrentItem(e.groups.topLevelItem(row))
            if e.rows()[row][1]=='O':
                e.groups.currentItem().setCheckState(0,QtCore.Qt.CheckState.Unchecked);continue
            e.direction.setText('0 0 -1' if row==0 else '0 0 1');e.update_direction()
            d=fe.open_mdff_context(e.rows()[row][0]);d.model.setCurrentIndex(2)
            d.manual_mode.setCurrentIndex(0);d.declaration.setChecked(True)
            assert d.apply_configuration() is not None,d.status.text()
        fe.structure_viewer.apply_groups();calculate(fe,'Fe3O4_local_synthetic')
        reopened=save_reopen(fe,'Fe3O4');retire(fe,reopened);fe=reopened=e=d=None;gc.collect();record('Fe3O4: 8a/16d/32e, Fe(A)/Fe(B), O elastic-only')

        cr_path=out/'Cr_two_site.cif';write(cr_path,bulk('Cr','bcc',a=2.88,cubic=True))
        cr=window('Cr',cr_path);controls(cr);cr.target.setText('1 1 0')
        e=cr.structure_viewer.editor;e.mode.setCurrentIndex(1)
        while e.rows():e.groups.setCurrentItem(e.groups.topLevelItem(0));e.delete_group()
        for index,direction in enumerate(('0 0 1','0 0 -1')):
            e.select_indices([index]);e.name.setText('Cr-'+str(index));e.direction.setText(direction);e.create_group()
            d=cr.open_mdff_context(e.rows()[-1][0]);d.model.setCurrentIndex(1);d.declaration.setChecked(True)
            assert d.apply_configuration() is not None,d.status.text()
        cr.structure_viewer.apply_groups()
        normal=calculate(cr,'Cr_atomic_BW_single')
        cr.show_structure_viewer();cr.structure_viewer.editor.flip_all()
        cr.structure_viewer.apply_groups();flipped=calculate(cr,'Cr_atomic_BW_reversed')
        for detector in ('A','B'):
            np.testing.assert_allclose(flipped['spectra']['N_'+detector],normal['spectra']['N_'+detector],rtol=2e-10,atol=1e-14)
            np.testing.assert_allclose(flipped['spectra']['M_'+detector],-normal['spectra']['M_'+detector],rtol=2e-10,atol=1e-14)
        cr.channeling_box.setCurrentIndex(1);cr.worker_count.setValue(2)
        calculate(cr,'Cr_atomic_BW_double_two_workers')
        cr.propagation_box.setCurrentIndex(1)
        calculate(cr,'Cr_atomic_MS_double');reopened=save_reopen(cr,'Cr');retire(reopened);reopened=None
        cr.channeling_box.setCurrentIndex(0);cr.worker_count.setValue(1)
        calculate(cr,'Cr_atomic_MS_single')
        cr.channeling_box.setCurrentIndex(1);cr.worker_count.setValue(2)
        cr.propagation_box.setCurrentIndex(0);cr.angular_maps.setChecked(False)
        calculate(cr,'Cr_atomic_detector_only_BW_double')
        record('Cr: completed detector-only spectrum calculation')
        preserved=fingerprints(cr.emcd_result);history=len(cr.browser.registry.records)
        cr.channeling_box.setCurrentIndex(1);cr.worker_count.setValue(2)
        cr.propagation_box.setCurrentIndex(0)
        cr.set_values(dict(grid=33,depth=33,subpixels=32,thickness=2))
        cr.angular_maps.setChecked(False);cr.refresh();cr.emcd_stale()
        cr.browser.table.clearSelection();cr.browser.selection_timer.stop()
        assert cr.emcd_button.isEnabled(),cr.emcd_button.toolTip()
        cr.start_emcd();assert cr.busy
        QtCore.QTimer.singleShot(100,cr.cancel);wait(cr)
        assert cr.run_outcome=='cancelled',cr.run_outcome
        assert fingerprints(cr.emcd_result)==preserved and len(cr.browser.registry.records)==history
        record('Cr: cooperative real-worker cancellation preserves prior result/history')
        if release:
            cr.set_values(dict(grid=9,depth=3,subpixels=4,thickness=.1))
            calculate(cr,'Cr_restart_after_cancel')
            record('Cr: completed restart after cancellation')
        record('Cr: manual magnetic subgroups, opposite M, reversal-even/odd identities')
        retire(cr);cr=e=d=None;gc.collect()

        # Existing ordered inverse-spinel construction (not the 7-atom catalogue fixture).
        atoms=crystal(['Fe','Fe','O'],basis=[(.125,)*3,(.5,)*3,(.255,)*3],
                      spacegroup=227,setting=2,cellpar=[8.34]*3+[90]*3)
        kinds=atoms.arrays['spacegroup_kinds'];b=np.flatnonzero(kinds==1)
        nickel=b[np.rint(4*atoms.get_scaled_positions()[b,0]).astype(int)%2==0]
        for i in nickel:atoms[i].symbol='Ni'
        atoms.info.pop('spacegroup',None)
        ferrite_path=out/'ordered_NiFe2O4.cif';write(ferrite_path,atoms)
        nf=window('NiFe2O4',ferrite_path);controls(nf)
        assert len(nf.structure.atoms)==56
        np.testing.assert_allclose(nf.structure.atoms.get_scaled_positions(),atoms.get_scaled_positions(),rtol=0,atol=1e-12)
        assert {symbol:nf.structure.atoms.get_chemical_symbols().count(symbol) for symbol in ('Ni','Fe','O')}=={'Ni':8,'Fe':16,'O':32}
        e=nf.structure_viewer.editor;e.mode.setCurrentIndex(1)
        for row in range(e.groups.topLevelItemCount()):
            e.groups.setCurrentItem(e.groups.topLevelItem(row));element=e.rows()[row][1]
            if element=='O':
                e.groups.currentItem().setCheckState(0,QtCore.Qt.CheckState.Unchecked);continue
            e.direction.setText('0 0 1');e.update_direction()
            d=nf.open_mdff_context(e.rows()[row][0]);d.model.setCurrentIndex(2);d.manual_mode.setCurrentIndex(0)
            edges=[('L3',855.),('L2',872.)] if element=='Ni' else [('L3',711.5),('L2',724.5)]
            d.manual_edges.set_rows(edges);d.constant_energy.low.setValue(edges[0][1]-5)
            d.constant_energy.high.setValue(edges[-1][1]+5);d.declaration.setChecked(True)
            assert d.apply_configuration() is not None,d.status.text()
        nf.structure_viewer.apply_groups();nf.energy_scope.setCurrentIndex(nf.energy_scope.findData('native'))
        calculate(nf,'NiFe2O4_independent_windows');save_reopen(nf,'NiFe2O4')
        record('NiFe2O4: ordered 56-atom CIF, independent Fe/Ni windows and providers')
        report['complete']=True
    except Exception:
        report['errors'].append(traceback.format_exc())
    finally:
        (out/'acceptance.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
        for w in windows:
            if w.busy:w.cancel();wait(w)
            w.project_dirty=False;w.close()
    return 0 if report['complete'] else 2


if __name__=='__main__':
    raise SystemExit(run(sys.argv[1]))
