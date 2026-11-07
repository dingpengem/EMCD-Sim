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


def main():
    parser=argparse.ArgumentParser(description='Opt-in native release acceptance; bounded synthetic tests only')
    parser.add_argument('output',type=Path);parser.add_argument('--historical-project',type=Path)
    args=parser.parse_args();return run(args.output,args.historical_project)


if __name__=='__main__':raise SystemExit(main())
