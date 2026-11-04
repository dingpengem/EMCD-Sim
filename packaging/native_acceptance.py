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
        w.model_box.setCurrentIndex({'xmcd':0,'ni-atomic':1,'imported':2,'atomic':2}[model])
        w.axis.setText('0 0 1');w.declaration.setChecked(True);w.correction.setChecked(False)
        w.detectors=np.array([[.2,.2],[.2,-.2]]);w.sync_detectors();w.show();app.processEvents()
        return w
    try:
        write(out/'synthetic_fe.cif',bulk('Fe','bcc',a=2.866,cubic=True),format='cif')
        parameters=resource_root()/'examples/synthetic_fe_atomic_parameters.json'
        if not parameters.exists():parameters=resource_root()/'docs/examples/synthetic_fe_atomic_parameters.json'
        assert parameters.is_file(),'Bundled explicit atomic example missing'
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
                            target=out/(name+'_generated.json')
                            with patch.object(QtWidgets.QFileDialog,'getOpenFileName',return_value=(str(parameters),'')),patch.object(QtWidgets.QFileDialog,'getSaveFileName',return_value=(str(target),'')):
                                w.generate_atomic_tensor()
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
                        original=w.imported_info
                        bad=out/'invalid_parameters.json';bad.write_text('{}',encoding='utf-8')
                        with patch.object(QtWidgets.QFileDialog,'getOpenFileName',return_value=(str(bad),'')),patch.object(QtWidgets.QFileDialog,'getSaveFileName',return_value=(str(out/'invalid_output.json'),'')):
                            w.generate_atomic_tensor()
                        assert w.imported_info is None and not w.imported_declaration.isChecked()
                        assert not w.emcd_button.isEnabled()
                        record('Failed generation invalidates stale GUI state')
                        raw=Path(original.path).read_bytes();Path(original.path).write_bytes(raw+b' ')
                        try:ImportedMDFF.load(original.path,original.sha256)
                        except ValueError:record('Source checksum rejects replacement')
                        else:raise AssertionError('Checksum bypass')
                        Path(original.path).write_bytes(raw)
                        d=json.loads(raw);d.pop('atomic_model');partial=out/'partial_provenance.json';partial.write_text(json.dumps(d))
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
        record('Clean startup, eight real GUI worker cases, exports/screenshots and shutdown')
        report['complete']=True
    except Exception:
        report['errors'].append(traceback.format_exc())
    finally:
        for w in windows:
            if w.busy:w.cancel();w.worker.wait(15000)
            for dialog in w.dialogs:dialog.close()
            w.close()
        app.processEvents();report['closed_cleanly']=all(not w.isVisible() and not w.busy for w in windows)
        (out/'acceptance.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
    return 0 if report['complete'] and report['closed_cleanly'] and not report['errors'] else 2


def main():
    parser=argparse.ArgumentParser(description='Opt-in native release acceptance; bounded synthetic tests only')
    parser.add_argument('output',type=Path);parser.add_argument('--historical-project',type=Path)
    args=parser.parse_args();return run(args.output,args.historical_project)


if __name__=='__main__':raise SystemExit(main())
