"""Opt-in release QA: actual widgets/workers, never production defaults or solvers."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time
import traceback
from unittest.mock import patch
import numpy as np
from PySide6 import QtWidgets, QtGui


def run(output, historical_project=None):
    from ase.build import bulk
    from ase.io import write
    from emcd_sim.gui.app import MainWindow
    from emcd_sim.gui.geometry import Structure, elastic_model
    from emcd_sim.gui.runtime import build_info, resource_root
    from emcd_sim.gui.project_io import save_project, load_project, source_status, restore_structure
    from emcd_sim.atomic_ionization import export_atomic_parameters
    from emcd_sim.imported_mdff import ImportedMDFF
    from emcd_sim.gui.results import mdff_label
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    if not QtGui.QFontDatabase.families():
        from matplotlib import get_data_path
        font=QtGui.QFontDatabase.addApplicationFont(str(Path(get_data_path())/'fonts/ttf/DejaVuSans.ttf'))
        families=QtGui.QFontDatabase.applicationFontFamilies(font)
        if families:app.setFont(QtGui.QFont(families[0],9))
    app.setQuitOnLastWindowClosed(False)
    report=dict(build=build_info(),frozen=bool(getattr(sys,'frozen',False)),executable=sys.executable,
        qt_platform=app.platformName(),cases=[],checks=[],errors=[],complete=False,closed_cleanly=False)
    windows=[]
    def record(name):report['checks'].append(name)
    def wait(w):
        deadline=time.monotonic()+180
        while w.busy and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
        assert not w.busy,'Native worker timeout'
        assert not report['errors'],report['errors']
        app.processEvents()
    def window(element,model,channel):
        w=MainWindow(out/('workspace_'+element+'_'+model+'_'+channel));windows.append(w)
        w.error=lambda message:report['errors'].append(str(message))
        w.numerical_mode.setCurrentIndex(1)
        w.structure=Structure.nickel() if element=='Ni' else Structure.from_cif(out/'synthetic_fe.cif')
        w.zone.setText('0 0 1');w.target.setText('2 0 0' if element=='Ni' else '1 1 0')
        w.set_values(dict(kv=200,tx=-5,ty=7,thickness=.2,beam=.6,potential=1.2,grid=9,depth=9,
            subpixels=8,fft_grid=16,slice_step=.01,halfwidth=.7,radius=.12))
        w.propagation_box.setCurrentIndex(2);w.channeling_box.setCurrentIndex(channel=='double')
        w.energy_scope.setCurrentIndex(1);w.angular_maps.setChecked(True)
        w.worker_mode.setCurrentIndex(1);w.worker_count.setValue(1)
        w.model_box.setCurrentIndex({'xmcd':0,'ni-atomic':1,'imported':2,'atomic':1}[model])
        if model=='xmcd':
            w.validate_xmcd(show_error=False)
        elif model=='ni-atomic':
            from emcd_sim.gui.saved_atomic_ui import restore
            from emcd_sim.gui.emcd_forward import ForwardSettings
            restore(w.atomic_editor,ForwardSettings(model='atomic',l3=852.7,l2=870.0),w.structure)
        elif model=='imported':
            w.manual_model.setCurrentIndex(0);w.constant_input_mode.setCurrentIndex(1)
        w.axis.setText('0 0 1');w.declaration.setChecked(True);w.correction.setChecked(False)
        w.detectors=np.array([[.2,.2],[.2,-.2]]);w.sync_detectors();w.show();app.processEvents()
        return w
    try:
        write(out/'synthetic_fe.cif',bulk('Fe','bcc',a=2.866,cubic=True),format='cif')
        parameters=resource_root()/'examples/synthetic_fe_atomic_parameters.json'
        if not parameters.exists():parameters=resource_root()/'docs/examples/synthetic_fe_atomic_parameters.json'
        assert parameters.is_file(),'Bundled explicit atomic example missing'
        supplied_parameters=parameters
        parameters=out/'synthetic_fe_parameters.json';parameters.write_bytes(supplied_parameters.read_bytes())
        source=export_atomic_parameters(parameters,out/'declared_pair.json')
        # A declared, independent synthetic imported tensor pair is produced by
        # the atomic generator; import and generation routes are exercised separately.
        record('CIF import and declared-source generation')
        for element,models in (('Ni',('xmcd','ni-atomic')),('Fe',('imported','atomic'))):
            for model in models:
                for channel in ('single','double'):
                    name=element+'_'+model+'_'+channel;w=window(element,model,channel)
                    if element=='Fe':
                        if model=='atomic':
                            w.atomic_parameter_path.setText(str(parameters));w.validate_atomic_parameters()
                            assert w.atomic_provider_info is not None
                            w.atomic_declaration.setChecked(True)
                            assert w.forward_settings().ionizing_element=='Fe'
                        else:
                            w.imported_path.setText(source.path);w.validate_imported_mdff()
                            assert w.imported_info is not None
                            w.imported_declaration.setChecked(True)
                            assert w.ionizing_element.text()=='Fe'
                            w.ionizing_element.setText('Co');w.emcd_stale();assert not w.emcd_button.isEnabled()
                            w.ionizing_element.setText('Fe')
                    w.refresh();w.emcd_stale()
                    assert w.emcd_button.isEnabled(),w.emcd_button.toolTip()
                    w.start_preview();wait(w);assert w.last_result is not None
                    w.start_emcd();wait(w);r=w.emcd_result
                    assert set(r['methods'])=={'bloch','fft-multislice'}
                    for v in r['methods'].values():
                        assert set(v['maps'])=={'L3','L2'}
                        for key in ('I_A_plus','I_A_minus','I_B_plus','I_B_minus'):
                            assert np.isfinite(v['spectra'][key]).all() and v['spectra'][key].min()>=0
                    if element=='Fe':
                        assert r['metadata']['scientific_status']=='SYNTHETIC TEST ONLY'
                        assert 'SYNTHETIC' in mdff_label(r)
                        assert r['comparison']['spectra']['I_A_plus']['l2_relative']<.015
                    folder=out/(name+'_project');save_project(r,folder);opened=load_project(folder)
                    np.testing.assert_array_equal(opened['spectra']['D_mag'],r['spectra']['D_mag'])
                    w.emcd_result=opened;w.use_result_settings()
                    if element=='Fe':assert source_status(opened)['mdff']['verified']
                    w.grab().save(str(out/(name+'.png')))
                    report['cases'].append(dict(name=name,project_roundtrip=True,methods=list(r['methods']),
                        comparison=r['comparison']['spectra']['I_A_plus']['l2_relative'],label=mdff_label(r)))
                    if model=='atomic' and channel=='double':
                        from emcd_sim.gui.emcd_forward import export_result
                        export_result(opened,out/(name+'_exports'))
                        record('Scientific PNG/SVG/CSV exports from completed generalized result')
                        original=w.forward_settings()
                        bad=out/'invalid_parameters.json';bad.write_text('{}',encoding='utf-8')
                        w.atomic_parameter_path.setText(str(bad));w.validate_atomic_parameters()
                        assert w.atomic_provider_info is None and not w.atomic_declaration.isChecked()
                        assert not w.emcd_button.isEnabled()
                        record('Failed generation invalidates stale GUI state')
                        from emcd_sim.gui.generalized_forward import source_for
                        raw=Path(original.source).read_bytes();Path(original.source).write_bytes(raw+b' ')
                        try:source_for(original)
                        except ValueError:record('Source checksum rejects replacement')
                        else:raise AssertionError('Checksum bypass')
                        Path(original.source).write_bytes(raw)
                        d=json.loads(Path(source.path).read_bytes());d.pop('atomic_model');partial=out/'partial_provenance.json';partial.write_text(json.dumps(d))
                        try:ImportedMDFF.load(partial)
                        except ValueError:record('Partial atomic provenance rejected')
                        else:raise AssertionError('Partial provenance bypass')
                    w.close();app.processEvents()
        if historical_project:
            historical=Path(historical_project);before=hashlib.sha256((historical/'project.json').read_bytes()).hexdigest()
            r=load_project(historical)
            assert r['settings'].elastic_provider=='nickel-lobato-2014'
            np.testing.assert_allclose(elastic_model(restore_structure(r['structure_snapshot']),r['settings']).amplitudes(r['depth_nm']),r['methods']['bloch']['amplitudes'],rtol=0,atol=2e-12)
            assert hashlib.sha256((historical/'project.json').read_bytes()).hexdigest()==before
            record('Genuine historical Lobato project and archived elastic control')
        else:record('Historical project not supplied; run local release acceptance with --historical-project')
        # Real nonmagnetic import, with no manufactured magnetic state.
        d=json.loads(Path(source.path).read_bytes());d={k:v for k,v in d.items() if not k.startswith('atomic_')}
        d['magnetic_state']='nonmagnetic';d['reversal']='identical_nonmagnetic';d['T']=d.pop('T_even')
        d.pop('T_plus');d.pop('T_minus');d['T']['imag']=np.zeros_like(d['T']['imag']).tolist()
        path=out/'nonmagnetic.json';path.write_text(json.dumps(d))
        nm=ImportedMDFF.load(path);np.testing.assert_array_equal(nm.plus.tensor_angstrom2_per_ev,nm.minus.tensor_angstrom2_per_ev)
        record('Explicit nonmagnetic imported state')
        _additional_provider_cases(out,app,windows,report,wait)
        _additional_provider_cases(out/'full-k',app,windows,report,wait,coverage='full',only_element='O')
        _manual_spectral_cases(out,app,windows,report,wait,window)
        record('Clean startup, all real GUI worker cases, exports/screenshots and shutdown')
        report['complete']=True
    except Exception:
        report['errors'].append(traceback.format_exc())
    finally:
        for w in windows:
            if w.busy:w.cancel();w.worker.wait(15000)
            for dialog in w.dialogs:dialog.close()
            w.mdff_dialog.close()
            w.close()
        app.processEvents();report['closed_cleanly']=all(not w.isVisible() and not w.busy for w in windows)
        (out/'acceptance.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
    return 0 if report['complete'] and report['closed_cleanly'] and not report['errors'] else 2


def _manual_spectral_cases(out,app,windows,report,wait,window):
    """Exercise the accepted energy-dependent manual model in the frozen app."""
    from emcd_sim.gui.project_io import save_project,load_project,source_status
    for channel in ('single','double'):
        w=window('Ni','xmcd',channel)
        w.model_box.setCurrentIndex(2);w.manual_model.setCurrentIndex(1)
        w.preview_mdff();cfg=w.forward_settings()
        assert not w.manual_spectral.is_stale
        assert w.manual_spectral.snapshot['source'].sha256==cfg.source_sha256
        w.mdff_dialog.show();app.processEvents()
        w.mdff_scroll.ensureWidgetVisible(w.manual_spectral.heat_canvas);app.processEvents()
        assert w.manual_spectral.heat_canvas.isVisible()
        w.mdff_dialog.grab().save(str(out/('Ni_manual-spectral_'+channel+'_preview.png')))
        w.mdff_dialog.close()
        w.emcd_stale();assert w.emcd_button.isEnabled(),w.emcd_button.toolTip()
        w.start_emcd();wait(w);r=w.emcd_result
        assert r is not None and r['config'].source_sha256==cfg.source_sha256
        assert set(r['methods'])=={'bloch','fft-multislice'}
        for result in r['methods'].values():
            for key in ('I_A_plus','I_A_minus','I_B_plus','I_B_minus'):
                assert np.isfinite(result['spectra'][key]).all() and result['spectra'][key].min()>=0
        name='Ni_manual-spectral_'+channel
        folder=out/(name+'_project');save_project(r,folder);opened=load_project(folder)
        np.testing.assert_array_equal(opened['spectra']['D_mag'],r['spectra']['D_mag'])
        assert source_status(opened)['mdff']['verified']
        w.emcd_result=opened;w.use_result_settings();w.preview_mdff()
        assert w.manual_model.currentIndex()==1 and not w.manual_spectral.is_stale
        w.grab().save(str(out/(name+'.png')))
        report.setdefault('manual_spectral_cases',[]).append(dict(name=name,project_roundtrip=True,methods=list(r['methods']),source_sha256=cfg.source_sha256))
        w.close();app.processEvents()


def _additional_provider_cases(out,app,windows,report,wait,*,coverage='edges',only_element=None):
    """Direct XMCD and a non-3d single edge through complete native GUI flows."""
    from ase import Atoms
    from ase.build import bulk
    from emcd_sim.gui.app import MainWindow
    from emcd_sim.gui.geometry import Structure
    from emcd_sim.gui.emcd_forward import export_result
    from emcd_sim.gui.project_io import save_project,load_project
    models=['XMCD-constrained MDFF','Atomic Ionization MDFF','Manual tensor']
    out.mkdir(parents=True,exist_ok=True)
    e=np.linspace(704,730,17);n=.3+np.exp(-((e-710)/2)**2);m=.04*np.exp(-((e-710)/2)**2)
    for element,edge in (('Fe','L2,3'),('O','K')):
        if only_element and element!=only_element:continue
        path=out/('synthetic_'+element+'.xmcd')
        np.savetxt(path,np.column_stack((e,n+m,n-m,2*m,2*n)))
        for channel in ('single','double'):
            name=element+'_declared-xmcd_'+channel
            w=MainWindow(out/('workspace_'+name));windows.append(w)
            w.error=lambda message:report['errors'].append(str(message))
            w.numerical_mode.setCurrentIndex(1)
            w.structure=(Structure(bulk('Fe','bcc',a=2.866,cubic=True),'Synthetic Fe XMCD software test') if element=='Fe'
                else Structure(Atoms('O',cell=np.eye(3)*4,scaled_positions=[[0,0,0]],pbc=True),'Synthetic O K; not physical O spectroscopy'))
            w.zone.setText('0 0 1');w.target.setText('1 1 0' if element=='Fe' else '1 0 0')
            w.set_values(dict(kv=200,tx=-5,ty=7,thickness=.2,beam=.6,potential=1.2,grid=9,depth=9,
                subpixels=8,fft_grid=16,slice_step=.01,halfwidth=.7,radius=.12,energy=9))
            w.propagation_box.setCurrentIndex(2);w.channeling_box.setCurrentIndex(channel=='double')
            w.energy_scope.setCurrentIndex(coverage=='edges');w.worker_mode.setCurrentIndex(1);w.worker_count.setValue(1)
            w.detectors=np.array([[.2,.2],[.2,-.2]]);w.sync_detectors()
            w.model_box.setCurrentIndex(0);w.explicit_xmcd.setChecked(True)
            w.xmcd_element.setText(element);w.xmcd_edge.setText(edge)
            w.xmcd_selected.setText(json.dumps({'K':710.} if edge=='K' else {'L3':710.,'L2':723.}))
            w.xmcd_provenance.setText('Original synthetic source for native workflow acceptance')
            w.xmcd_validity.setText('Software test only; no material accuracy claim')
            w.xmcd_scale.setText('1');w.xmcd_status.setCurrentText('synthetic')
            with patch.object(QtWidgets.QFileDialog,'getOpenFileName',return_value=(str(path),'')) as select:
                w.browse_xmcd();select.assert_called_once()
            w.declaration.setChecked(True);w.correction.setChecked(False)
            if edge=='L2,3':w.set_values(dict(xl3=710.,xl2=723.))
            w.refresh();w.emcd_stale()
            assert w.structure.atoms.get_chemical_formula() in w.mdff_material.text()
            with patch.object(QtWidgets.QFileDialog,'getOpenFileName',side_effect=AssertionError('Preview must reuse the main XMCD selection')):
                w.preview_mdff()
            assert w.xmcd_preview.snapshot is not None and not w.xmcd_preview.is_stale
            shared_preview=w.xmcd_preview.snapshot['config']
            assert shared_preview.source==str(path.resolve()) and shared_preview.source_sha256==w.source_info['sha256']
            if edge=='L2,3':assert (w.spin['xl3'].value(),w.spin['xl2'].value())==(shared_preview.l3,shared_preview.l2)
            w.show();w.mdff_dialog.show();app.processEvents()
            w.mdff_scroll.ensureWidgetVisible(w.xmcd_preview.canvas);app.processEvents()
            assert w.xmcd_preview.isVisible()
            w.mdff_dialog.grab().save(str(out/(name+'_source-preview.png')))
            w.mdff_dialog.close()
            assert [w.model_box.itemText(i) for i in range(w.model_box.count())]==models
            w.refresh();w.emcd_stale();assert w.emcd_button.isEnabled(),w.emcd_button.toolTip()
            w.show();app.processEvents();w.start_emcd();wait(w)
            r=w.emcd_result;assert r is not None and set(r['maps'])==({'K'} if edge=='K' else {'L3','L2'})
            assert r['config'].source==shared_preview.source and r['config'].source_sha256==shared_preview.source_sha256
            assert (r['config'].l3,r['config'].l2)==(shared_preview.l3,shared_preview.l2)
            report['checks'].append(name+': one main source selection supplies preview and calculation')
            assert w.eels_view.figure._suptitle is not None
            if edge=='K':
                assert 'L3' not in w.eels_view.figure._suptitle.get_text()
                assert [w.maps_view.choice.itemText(i) for i in range(w.maps_view.choice.count())]==['K']
                export_result(r,out/(name+'_exports'))
                assert (out/(name+'_exports')/'K_angular_maps.svg').is_file()
            folder=out/(name+'_project');save_project(r,folder);opened=load_project(folder)
            np.testing.assert_array_equal(opened['spectra']['D_mag'],r['spectra']['D_mag'])
            w.emcd_result=opened;w.use_result_settings();w.emcd_stale();assert w.emcd_button.isEnabled(),w.emcd_button.toolTip()
            w.grab().save(str(out/(name+'.png')))
            report['cases'].append(dict(name=name,coverage=coverage,project_roundtrip=True,methods=list(r['methods']),edge=edge,
                status=r['metadata']['scientific_status']))
            for symbol,lattice in (('Co','hcp'),('Cr','bcc')):
                w.structure=Structure(bulk(symbol,lattice),'Menu visibility only')
                assert [w.model_box.itemText(i) for i in range(w.model_box.count())]==models
                w.emcd_stale();assert not w.emcd_button.isEnabled()
            w.close();app.processEvents()
    report['checks'].append('Fixed three-model menu for Ni/Fe/Co/Cr; direct Fe XMCD and non-3d K-edge Single/Double BW/MS, maps/exports/reopen')


def run_multisite(output):
    """Bounded v0.9 acceptance through real widgets/workers in the same EXE.

    Synthetic BCC Cr and seven-atom Fe3O4 motifs reuse the application tests'
    ordered-site fixtures; constant PSD pairs are software checks, not spectra.
    File-dialog choices/confirmation answers are automated, not the solvers.
    """
    from ase import Atoms
    from ase.io import write
    from PySide6 import QtCore
    from emcd_sim.gui.app import MainWindow
    from emcd_sim.gui.runtime import build_info, resource_root
    from emcd_sim.gui.project_collection import load_collection
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    report=dict(build=build_info(),frozen=bool(getattr(sys,'frozen',False)),executable=sys.executable,
        qt_platform=app.platformName(),cases=[],checks=[],errors=[],complete=False,closed_cleanly=False)
    w=MainWindow(out/'workspace');w.error=lambda message:report['errors'].append(str(message))
    w.store_ui_preferences=lambda:None
    def wait():
        deadline=time.monotonic()+180
        while w.busy and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
        assert not w.busy,'Native worker timeout'
        app.processEvents();assert not report['errors'],report['errors']
    def capture(name,widget=None):
        app.processEvents();time.sleep(.1);app.processEvents()
        assert (widget or w).grab().save(str(out/(name+'.png')))
    def controls(material,method='bloch',channel='single'):
        w.numerical_mode.setCurrentIndex(1);w.zone.setText('0 0 1')
        w.target.setText('1 1 0' if material=='Cr' else '2 0 0')
        w.basis_mode.setCurrentIndex(0);w.row_projection.setChecked(True)
        w.propagation_box.setCurrentIndex(0 if method=='bloch' else 1)
        w.channeling_box.setCurrentIndex(0 if channel=='single' else 1)
        w.energy_scope.setCurrentIndex(1);w.correction.setChecked(False);w.angular_maps.setChecked(True)
        w.worker_mode.setCurrentIndex(1);w.worker_count.setValue(1)
        w.set_values(dict(kv=200,thickness=.1,beam=.6,potential=1.2,grid=9,depth=3,
            subpixels=4,fft_grid=16,slice_step=.02,halfwidth=.7,radius=.12,tx=-5,ty=7))
        w.detectors=np.array([[.2,.2],[.2,-.2]]);w.sync_detectors();w.refresh()
    def calculate(material,method,channel):
        controls(material,method,channel);w.emcd_button.click();wait()
        assert w.run_outcome=='completed' and w.emcd_result is not None
        r=w.emcd_result;s=r['spectra']
        for key in ('I_A_plus','I_A_minus','I_B_plus','I_B_minus'):assert np.isfinite(s[key]).all()
        np.testing.assert_allclose(s['M_A'],(s['I_A_plus']-s['I_A_minus'])/2,rtol=1e-12,atol=1e-14)
        np.testing.assert_allclose(s['N_A'],(s['I_A_plus']+s['I_A_minus'])/2,rtol=1e-12,atol=1e-14)
        report['cases'].append(dict(material=material,solver=method,channel=channel,
            groups=list(r.get('groups',{})),energy_ev=s['energy_ev'].tolist(),settings=r['metadata'].get('settings')))
        return r
    def save_as(path):
        with patch.object(QtWidgets.QFileDialog,'getSaveFileName',return_value=(str(path),'')):
            w.save_project_action(save_as=True);wait()
        assert w.project_save_status=='Saved' and not w.project_dirty
        assert w.active_project_path==str(path)
    execute=QtWidgets.QMessageBox.exec
    def retain(dialog):
        if dialog.windowTitle()=='Retain Calculation':dialog.defaultButton().click();return 0
        return execute(dialog)
    try:
        assert app.platformName()=='windows','Native Windows platform required'
        assert build_info()['application_version']=='0.9.0b2'
        with (patch.object(QtWidgets.QMessageBox,'exec',retain),
              patch.object(QtWidgets.QMessageBox,'warning',return_value=QtWidgets.QMessageBox.StandardButton.Discard),
              patch.object(QtWidgets.QMessageBox,'question',return_value=QtWidgets.QMessageBox.StandardButton.Yes)):
            w.show();exposure_deadline=time.monotonic()+5
            while not w.windowHandle().isExposed() and time.monotonic()<exposure_deadline:
                app.processEvents();time.sleep(.01)
            assert w.isVisible() and w.windowHandle().isExposed()
            assert w.splitter.count()==3 and w.browser_dock.isVisible()
            assert w.axis.isEnabled() and w.magnetization_mode=='global'
            # Bundled Ni source, the established Global M path, actual workers.
            w.validate_xmcd(show_error=False);w.declaration.setChecked(True)
            for channel in ('single','double'):calculate('Ni','bloch',channel)
            capture('Ni-results');save_as(out/'Ni-project')
            ni_before={key:value.copy() for key,value in w.emcd_result['spectra'].items()}
            w.close_project();w.open_project_path(out/'Ni-project');wait()
            assert len(w.browser.registry.records)==2 and w.magnetization_mode=='global'
            w.browser.select_id(w.browser.registry.records[-1]['id']);w.browser.view()
            for key,value in ni_before.items():np.testing.assert_array_equal(w.emcd_result['spectra'][key],value)
            report['checks'].append('Legacy Ni BW Single/Double; bundled MDFF; EELS/EMCD; project Save/Open')
            for material in ('Cr','Fe3O4'):
                w.new_project();assert w.project_save_status=='Unsaved Project'
                atoms=(Atoms('Cr2',scaled_positions=[[0,0,0],[.5,.5,.5]],cell=[2.88]*3,pbc=True) if material=='Cr' else
                    Atoms('Fe3O4',scaled_positions=[[0,0,0],[.25,.25,.25],[.75,.75,.75],
                        [.2,.2,.2],[.8,.8,.2],[.8,.2,.8],[.2,.8,.8]],cell=[5]*3,pbc=True))
                cif=out/(material+'.cif');write(cif,atoms,format='cif')
                with patch.object(QtWidgets.QFileDialog,'getOpenFileName',return_value=(str(cif),'')):w.load_cif()
                w.show_structure_viewer();viewer=w.structure_viewer;editor=viewer.editor
                viewer.tabs.setCurrentWidget(editor);editor.mode.setCurrentIndex(1)
                assert not w.axis.isEnabled() and w.magnetization_mode=='local'
                groups=[('Cr(A)' if material=='Cr' else 'Fe(A)',[0],1.,1.),
                        ('Cr(B)' if material=='Cr' else 'Fe(B)',[1] if material=='Cr' else [1,2],-1.,1. if material=='Cr' else 2.)]
                for gid,indices,sign,scale in groups:
                    editor.select_indices(indices);editor.name.setText(gid);editor.direction.setText('0 0 '+str(sign));editor.create_group()
                    dialog=editor.configure_mdff();dialog.model.setCurrentIndex(2);dialog.manual_mode.setCurrentIndex(2)
                    dialog.constant_energy.low.setValue(700);dialog.constant_energy.high.setValue(740);dialog.constant_energy.count.setValue(2)
                    dialog.manual_edges.set_rows([('L3',710.),('L2',723.)])
                    for tensor,odd in zip(dialog.pair,(sign,-sign)):
                        a=np.eye(3,dtype=complex)*scale;a[0,1]=.1j*odd*scale;a[1,0]=-.1j*odd*scale
                        with QtCore.QSignalBlocker(tensor.cells):
                            for i in range(3):
                                for j in range(3):tensor.cells.item(i,j).setText(str(a[i,j]).strip('()').replace('j','i'))
                        tensor.edited()
                    dialog.declaration.setChecked(True)
                    dialog.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Apply).click()
                    assert editor.mdff_status(editor.rows()[-1])=='Configured and valid',dialog.status.text()
                    if indices==[0]:capture(material+'-manual-pair',dialog)
                    dialog.close()
                editor.apply();assert editor.accepted_site_groups is not None
                references=tuple(row[4] for row in editor.rows())
                editor.mode.setCurrentIndex(0);assert w.axis.isEnabled()
                editor.mode.setCurrentIndex(1);assert not w.axis.isEnabled()
                assert tuple(row[4] for row in editor.rows())==references
                editor.flip_all();editor.apply();assert editor.reverse_magnetization
                editor.flip_all();editor.apply();assert not editor.reverse_magnetization
                viewer.tabs.setCurrentIndex(0);viewer.color_mode.setCurrentIndex(1);viewer.magnetic_arrows.setChecked(True)
                viewer.set_repetitions((2,2,2));capture(material+'-viewer',viewer)
                assert len(viewer._atoms)==len(atoms)  # replicas do not replace the original structure
                viewer.close()
                for channel in ('single','double'):
                    for method in ('bloch','fft-multislice'):calculate(material,method,channel)
                r=w.emcd_result;denominator=r['metadata']['multisite']['selected_atom_count']
                assert denominator==(2 if material=='Cr' else 3)
                for key in ('I_A_plus','I_A_minus','I_B_plus','I_B_minus'):
                    expected=sum(g['metadata']['multiplicity']*g['spectra'][key] for g in r['groups'].values())/denominator
                    np.testing.assert_allclose(r['spectra'][key],expected,rtol=1e-12,atol=1e-14)
                c=w.eels_view.multisite_controls
                for index in range(c.selection.count()):c.selection.setCurrentIndex(index);app.processEvents()
                c.include_total.setChecked(True);c.quantity.setCurrentIndex(6);w.eels_view.canvas.draw();capture(material+'-results')
                export=out/(material+'-csv');export.mkdir()
                with patch.object(QtWidgets.QFileDialog,'getExistingDirectory',return_value=str(export)):w.eels_view.export_derived()
                assert list(export.rglob('*.csv')),'Displayed comparison CSV missing'
                project=out/(material+'-project');save_as(project)
                assert len(load_collection(project)['runs'])==4
                first,second=[row['id'] for row in w.browser.registry.records[:2]]
                w.browser.select_id(first);w.browser.view();w.use_result_settings();assert not w.axis.isEnabled()
                assert w.settings().thickness==.1
                w.compare_selected();comparison=w.dialogs[-1]
                assert comparison.first.currentData()!=comparison.second.currentData() and comparison.rows
                assert {record['id'] for record,_ in comparison.runs}=={row['id'] for row in w.browser.registry.records}
                comparison.second.setCurrentIndex(comparison.first.currentIndex());assert not comparison.rows
                comparison.second.setCurrentIndex(1);assert comparison.rows;capture(material+'-compare',comparison);comparison.close()
                w.browser.select_id(first);w.delete_selected_calculation();assert len(w.browser.registry.records)==3
                w.save_project_action();wait();assert len(load_collection(project)['runs'])==3
                copied=out/(material+'-save-as');save_as(copied)
                w.close_project();assert not w.browser.registry.records
                w.open_project_path(copied);wait();assert len(w.browser.registry.records)==3
                assert w.magnetization_mode=='local' and not w.axis.isEnabled() and w.project_save_status=='Saved'
                w.spin['thickness'].setValue(.2);assert w.project_save_status=='Unsaved Changes'
                report['checks'].append(material+': CIF/viewer/replicas; local M lock; explicit Manual pairs; four solvers; selected-atom normalization; group/element/total/even/odd; CSV; history/restore/compare/delete/SaveAs/reopen')
            report['checks'].append('Four-region layout: Settings / Diffraction Preview / Results / lower Project Management')
            report['complete']=True
    except Exception:
        report['errors'].append(traceback.format_exc())
    finally:
        if w.busy:w.cancel();w.worker.wait(15000);app.processEvents()
        for dialog in w.findChildren(QtWidgets.QDialog):dialog.close()
        w.project_dirty=False;w.close();w.deleteLater();app.processEvents();report['closed_cleanly']=not w.busy
        (out/'acceptance.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
    return 0 if report['complete'] and not report['errors'] and report['closed_cleanly'] else 1


def run_grouping(output, historical_project=None):
    """Compact packaged grouping/pair-persistence acceptance, one calculation."""
    from ase.build import bulk
    from ase.io import write
    from PySide6 import QtCore
    from emcd_sim.gui.app import MainWindow
    from emcd_sim.gui.runtime import build_info, resource_root
    from emcd_sim.gui.generalized_forward import source_for
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    report=dict(build=build_info(),frozen=bool(getattr(sys,'frozen',False)),executable=sys.executable,
        qt_platform=app.platformName(),cases=[],checks=[],errors=[],complete=False,closed_cleanly=False)
    w=MainWindow(out/'workspace');w.error=lambda message:report['errors'].append(str(message))
    w.store_ui_preferences=lambda:None
    w.inspect_structure=lambda:None
    def wait():
        deadline=time.monotonic()+180
        while w.busy and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
        assert not w.busy,'Native worker timeout'
        app.processEvents();assert not report['errors'],report['errors']
    def capture(name,widget):
        app.processEvents();time.sleep(.15);app.processEvents()
        assert widget.grab().save(str(out/(name+'.png')))
    def load_cif(path):
        with patch.object(QtWidgets.QFileDialog,'getOpenFileName',return_value=(str(path),'')):w.load_cif()
        w.show_structure_viewer();v=w.structure_viewer
        v.showMaximized();v.tabs.setCurrentWidget(v.editor);app.processEvents()
        return v,v.editor
    def save_open(name):
        project=out/name
        with patch.object(QtWidgets.QFileDialog,'getSaveFileName',return_value=(str(project),'')):
            w.save_project_action(save_as=True);wait()
        assert w.project_save_status=='Saved' and not w.project_dirty
        w.close_project();w.open_project_path(project);wait();w.show_structure_viewer()
        return w.structure_viewer,w.structure_viewer.editor
    execute=QtWidgets.QMessageBox.exec
    def retain(dialog):
        if dialog.windowTitle()=='Retain Calculation':dialog.defaultButton().click();return 0
        return execute(dialog)
    try:
        assert report['frozen'] and app.platformName()=='windows','Packaged native Windows EXE required'
        with (patch.object(QtWidgets.QMessageBox,'exec',retain),
              patch.object(QtWidgets.QMessageBox,'warning',return_value=QtWidgets.QMessageBox.StandardButton.Discard),
              patch.object(QtWidgets.QMessageBox,'question',return_value=QtWidgets.QMessageBox.StandardButton.Yes)):
            w.show();app.processEvents()
            assert w.splitter.count()==3 and w.browser_dock.isVisible()
            v,e=load_cif(resource_root()/'examples/Fe3O4_inverse_spinel.cif')
            rows=e.rows();provenance=e.crystallographic_provenance
            assert [(r[0],len(r[2])) for r in rows]==[('Fe(A)',8),('Fe(B)',16),('O',32)]
            assert all(r[3] is None and r[4] is None for r in rows)
            assert [e.groups.topLevelItem(i).text(5) for i in range(3)]==['8a','16d','32e']
            assert provenance['setting']=='2' and provenance['spglib_version']==report['build']['versions']['spglib']
            atoms=w.structure.atoms;distances=atoms.get_all_distances(mic=True)
            oxygen=np.array(rows[2][2])
            for row,coordination in zip(rows[:2],(4,6)):
                assert all(atoms[i].symbol=='Fe' and np.count_nonzero(distances[i,oxygen]<2.3)==coordination for i in row[2])
            assert not v.view.scene.directions.any()
            e.groups.setCurrentItem(e.groups.topLevelItem(0))
            assert 'Fe(A)' in e.group_summary.text() and '8 atoms' in e.group_summary.text()
            capture('Fe3O4-structural-groups',v)
            v.dialog_buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Apply).click()
            v.close();v,e=save_open('Fe3O4-structural-project')
            assert e.rows()==rows and e.crystallographic_provenance==provenance and e.accepted_site_groups is None
            report['checks'].append('Fe3O4: actual ASE indices; 8/16/32, 8a/16d/32e; coordination 4/6; unset M/MDFF; structural Save/Open')
            v.close();w.new_project()
            cif=out/'Cr.cif';write(cif,bulk('Cr','bcc',a=2.88,cubic=True),format='cif')
            v,e=load_cif(cif)
            while e.rows():e.groups.setCurrentItem(e.groups.topLevelItem(0));e.delete_group()
            e.mode.setCurrentIndex(1);assert not w.axis.isEnabled()
            fractional=w.structure.atoms.get_scaled_positions()
            indices=[int(np.flatnonzero(np.linalg.norm(fractional-p,axis=1)<1e-8)[0]) for p in ([0,0,0],[.5,.5,.5])]
            for gid,index,sign in zip(('Cr-up','Cr-down'),indices,(1,-1)):
                e.select_indices([index]);e.name.setText(gid);e.direction.setText(f'0 0 {sign}');e.create_group()
                dialog=e.configure_mdff();dialog.model.setCurrentIndex(2);dialog.manual_mode.setCurrentIndex(2)
                dialog.constant_energy.low.setValue(700);dialog.constant_energy.high.setValue(740);dialog.constant_energy.count.setValue(2)
                dialog.manual_edges.set_rows([('L3',710.),('L2',723.)])
                for tensor,state in zip(dialog.pair,(sign,-sign)):
                    a=np.eye(3,dtype=complex);a[0,1]=.1j*state;a[1,0]=-.1j*state
                    a[0,2]=a[2,0]=.02*state
                    with QtCore.QSignalBlocker(tensor.cells):
                        for i in range(3):
                            for j in range(3):tensor.cells.item(i,j).setText(str(a[i,j]).strip('()').replace('j','i'))
                    tensor.edited()
                dialog.declaration.setChecked(True)
                dialog.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Apply).click()
                assert e.mdff_status(e.rows()[-1])=='Configured and valid',dialog.status.text()
                dialog.close()
            v.dialog_buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Apply).click()
            assert e.accepted_site_groups is not None,e.status.text()
            other=e.rows()[1];e.groups.setCurrentItem(e.groups.topLevelItem(0))
            e.direction.setText('0 0 -1');e.buttons['Update direction'].click()
            assert 'Draft M (unapplied)' in e.group_summary.text() and 'Accepted M' in e.group_summary.text()
            capture('Cr-pair-direction-draft',v)
            v.dialog_buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Apply).click()
            assert e.rows()[0][4].pair_reversed and e.rows()[1]==other,e.status.text()
            e.requested_energy_ev=np.array([710.,723.])
            accepted=e.rows();frames=[source_for(r[4]).metadata['frame_to_crystal'] for r in accepted]
            v.close();v,e=save_open('Cr-configured-project')
            for row,before,frame in zip(e.rows(),accepted,frames):
                assert row[:4]==before[:4] and row[4].pair_reversed==before[4].pair_reversed
                assert row[4].source_sha256==before[4].source_sha256
                assert source_for(row[4]).metadata['frame_to_crystal']==frame
            assert not w.axis.isEnabled()
            e.groups.setCurrentItem(e.groups.topLevelItem(0));v.magnetic_arrows.setChecked(True)
            capture('Cr-restored-pair',v);v.close()
            w.numerical_mode.setCurrentIndex(1);w.zone.setText('0 0 1');w.target.setText('1 1 0')
            w.basis_mode.setCurrentIndex(0);w.row_projection.setChecked(True)
            w.propagation_box.setCurrentIndex(0);w.channeling_box.setCurrentIndex(0);w.energy_scope.setCurrentIndex(1)
            w.correction.setChecked(False);w.angular_maps.setChecked(True);w.worker_mode.setCurrentIndex(1);w.worker_count.setValue(1)
            w.set_values(dict(kv=200,thickness=.1,beam=.6,potential=1.2,grid=9,depth=3,subpixels=4,
                fft_grid=16,slice_step=.02,halfwidth=.7,radius=.12,tx=-5,ty=7))
            w.detectors=np.array([[.2,.2],[.2,-.2]]);w.sync_detectors();w.refresh()
            w.emcd_button.click();wait();assert w.run_outcome=='completed'
            r=w.emcd_result;s=r['spectra']
            assert r['groups']['Cr-up']['metadata']['source']['direction_binding']['pair_state']=='minus'
            for key in ('I_A_plus','I_A_minus','I_B_plus','I_B_minus'):
                assert np.isfinite(s[key]).all()
                np.testing.assert_allclose(s[key],sum(g['metadata']['multiplicity']*g['spectra'][key] for g in r['groups'].values())/2,rtol=1e-12,atol=1e-14)
            np.testing.assert_allclose(s['M_A'],(s['I_A_plus']-s['I_A_minus'])/2,rtol=1e-12,atol=1e-14)
            capture('Cr-restored-calculation',w)
            report['cases'].append(dict(material='synthetic Cr',solver='bloch',channel='single',energy_ev=s['energy_ev'].tolist()))
            w.show_structure_viewer();v=w.structure_viewer;e=v.editor;v.tabs.setCurrentWidget(e)
            accepted=e.accepted_site_groups;before=e._accepted_rows
            e.groups.setCurrentItem(e.groups.topLevelItem(0));e.direction.setText('1 0 0');e.buttons['Update direction'].click()
            v.dialog_buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Apply).click()
            assert e.accepted_site_groups is accepted and e._accepted_rows==before
            assert 'requested' in e.status.text() and 'source axis' in e.status.text() and 'MDFF Editor' in e.status.text()
            capture('Cr-unsupported-direction-rejected',v)
            v.dialog_buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).click()
            assert e.rows()==before
            report['checks'].append('Cr: native Manual PSD pair; independent group; accepted/draft status; reversal Apply/Save/Open/restored BW Single; fixed-source X rejected atomically; Cancel; Global M lock')
            if historical_project:
                w.close_project();w.open_project_path(historical_project);wait()
                assert w.magnetization_mode=='global' and w.axis.isEnabled() and w.browser.registry.records
                w.browser.select_id(w.browser.registry.records[-1]['id']);w.browser.view()
                assert w.emcd_result is not None and not w.emcd_result.get('groups')
                capture('legacy-Ni-project',w)
                report['checks'].append('Existing legacy-workflow Ni saved project opened without recalculation')
            report['complete']=True
    except Exception:report['errors'].append(traceback.format_exc())
    finally:
        if w.busy:w.cancel();w.worker.wait(15000);app.processEvents()
        for dialog in w.findChildren(QtWidgets.QDialog):dialog.close()
        w.project_dirty=False;w.close();w.deleteLater();app.processEvents();report['closed_cleanly']=not w.busy
        (out/'acceptance.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
    return 0 if report['complete'] and not report['errors'] and report['closed_cleanly'] else 1


def main():
    parser=argparse.ArgumentParser(description='Opt-in native release acceptance; bounded synthetic tests only')
    parser.add_argument('output',type=Path);parser.add_argument('--historical-project',type=Path)
    parser.add_argument('--multisite',action='store_true',help='Bounded v0.9 native multi-site/project acceptance')
    parser.add_argument('--grouping',action='store_true',help='Compact packaged crystallographic grouping and physical-pair persistence check')
    args=parser.parse_args()
    if args.grouping:return run_grouping(args.output,args.historical_project)
    return run_multisite(args.output) if args.multisite else run(args.output,args.historical_project)


if __name__=='__main__':raise SystemExit(main())
