"""Opt-in bounded source/frozen GUI acceptance; writes only a new output folder."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback
from unittest.mock import patch

import numpy as np
from PySide6 import QtWidgets


def run(output,historical_project=None):
    from ase import Atoms
    from ase.io import write as write_cif
    from matplotlib.backend_bases import MouseEvent
    from .app import MainWindow
    from .geometry import Structure,elastic_model,indices
    from .emcd_forward import material_reason
    from .project_io import load_project,save_project,fingerprints,restore_structure,load_elastic_project
    from .runtime import build_info
    from ..adaptive_scattering import adaptive_factor,data_resource,COEFFICIENT_SHA256
    from ..elastic_providers import ADAPTIVE,LOBATO,LEGACY
    from ..geometry import electron_wavelength_angstrom

    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    report=dict(build=build_info(),frozen=bool(getattr(sys,'frozen',False)),qt_platform=app.platformName(),
        executable=sys.executable,checks=[],errors=[],clean_machine_tested=False)
    w=MainWindow(workspace=output/'workspace');errors=[];w.error=errors.append
    def record(name,**values):report['checks'].append(dict(name=name,passed=True,**values))
    def wait():
        deadline=time.monotonic()+90
        while w.busy and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
        assert not w.busy,'Worker timeout'
        assert not errors,errors
        assert w.run_outcome=='completed',w.run_outcome
        assert w.worker.wait(5000),'Worker failed to shut down'
    def capture(name):
        app.processEvents();w.grab().save(str(output/(name+'.png')))
        w.figure.savefig(output/(name+'_diffraction.png'),dpi=120,bbox_inches='tight')
    try:
        w.show();app.processEvents()
        from .. import __version__,__display_version__
        assert report['build']['application_version']==__version__
        assert __display_version__ in w.windowTitle()
        record('application_version',package=__version__,display=__display_version__,window_title=w.windowTitle())
        assert w.settings().elastic_provider==ADAPTIVE
        assert hashlib.sha256(data_resource('coefficients.json').read_bytes()).hexdigest()==COEFFICIENT_SHA256
        for name in ('LICENSE','NOTICE','provenance.json'):assert data_resource(name).read_bytes()
        for z in range(1,119):assert np.isfinite(adaptive_factor(z,[0.,1e-200,.001,1.,36.])).all()
        record('bundled_all118_and_notices',provider=ADAPTIVE,coefficient_sha256=COEFFICIENT_SHA256,
            h5py_imported='h5py' in sys.modules)
        w.start_preview();wait();assert w.last_result['elastic_provider']['provider']==ADAPTIVE
        capture('default_ni');record('default_ni_worker_preview',beams=len(w.last_result['beam_hkl']))
        saved=output/'saved';saved.mkdir()
        with patch.object(QtWidgets.QFileDialog,'getExistingDirectory',return_value=str(saved)):w.save_preview()
        path=next(saved.glob('elastic_*'));before=w.settings()
        with patch.object(QtWidgets.QFileDialog,'getExistingDirectory',return_value=str(path)):w.open_elastic_project_dialog()
        opened=w.dialogs[-1].saved_elastic_result
        assert w.settings()==before and opened['read_only_saved']
        np.testing.assert_array_equal(opened['amplitudes'],w.last_result['amplitudes'])
        assert load_elastic_project(path)['elastic_provider']['provider']==ADAPTIVE
        w.dialogs[-1].close();record('native_save_reopen_elastic',current_inputs_unchanged=True)

        if historical_project is None:raise ValueError('Native acceptance requires a genuine historical Ni project')
        original=Path(historical_project).resolve();manifest_sha=hashlib.sha256((original/'project.json').read_bytes()).hexdigest()
        r=load_project(original);before_hash=fingerprints(r)
        assert r['settings'].elastic_provider==LOBATO
        assert 'elastic_provider' not in r['metadata']['settings'],'Expected an unversioned historical control'
        model=elastic_model(restore_structure(r['structure_snapshot']),r['settings'])
        assert model.beams.hkl==tuple(map(tuple,r['metadata']['beam_hkl']))
        wave=model.amplitudes(r['depth_nm']);expected=r['methods']['bloch']['amplitudes']
        np.testing.assert_allclose(wave,expected,rtol=0,atol=2e-12)
        w.emcd_result=r;w.use_result_settings();assert not errors,errors
        assert w.elastic_provider_box.currentData()==LOBATO
        save_project(r,output/'historical_copy');again=load_project(output/'historical_copy')
        assert fingerprints(again)==before_hash and fingerprints(r)==before_hash
        assert hashlib.sha256((original/'project.json').read_bytes()).hexdigest()==manifest_sha
        record('genuine_historical_project',path=str(original),provider=LOBATO,
            project_manifest_sha256=manifest_sha,amplitude_max_error=float(np.max(abs(wave-expected))),
            saved_arrays_unchanged=True,physics_interpretation=r['project_convention_status'])

        w.numerical_mode.setCurrentIndex(1)
        w.elastic_provider_box.setCurrentIndex(w.elastic_provider_box.findData(ADAPTIVE))
        a,c=3.2495,5.2069;beta=np.deg2rad(107.)
        definitions=[('bcc_fe',Atoms('Fe2',scaled_positions=[[0,0,0],[.5,.5,.5]],cell=np.eye(3)*2.866,pbc=True),(0,0,1),(1,1,0),1.05),
            ('cscl',Atoms(['Cs','Cl'],scaled_positions=[[0,0,0],[.5,.5,.5]],cell=np.eye(3)*4.123,pbc=True),(0,0,1),(1,0,0),.72),
            ('hex_zno',Atoms(['Zn','Zn','O','O'],scaled_positions=[[1/3,2/3,0],[2/3,1/3,.5],[1/3,2/3,.382],[2/3,1/3,.882]],
                cell=[[a,0,0],[-a/2,np.sqrt(3)*a/2,0],[0,0,c]],pbc=True),(0,0,1),(1,0,0),.85),
            ('monoclinic',Atoms(['Si','O'],scaled_positions=[[.13,.27,.19],[.41,.07,.63]],
                cell=[[5.1,0,0],[0,6.3,0],[7.2*np.cos(beta),0,7.2*np.sin(beta)]],pbc=True),(0,1,0),(1,0,1),.55)]
        for name,atoms,zone,target,cutoff in definitions:
            cif=output/(name+'.cif');write_cif(cif,atoms)
            w.zone.setText(' '.join(map(str,zone)));w.target.setText(' '.join(map(str,target)))
            w.set_values(dict(kv=200,tx=0,ty=0,thickness=1,beam=cutoff,potential=cutoff))
            with patch.object(QtWidgets.QFileDialog,'getOpenFileName',return_value=(str(cif),'CIF')):w.load_cif()
            assert not errors,errors
            w.dialogs[-1].close();w.refresh();app.processEvents();w.canvas.draw()
            hs,g=w.current[2:4];cell=w.structure.atoms.cell.array
            aa,bb,cc=cell;reciprocal=np.array([np.cross(bb,cc),np.cross(cc,aa),np.cross(aa,bb)])/np.dot(aa,np.cross(bb,cc))
            z=np.asarray(zone)@cell;z/=np.linalg.norm(z)
            x=np.asarray(target)@reciprocal;x/=np.linalg.norm(x);frame=np.array([x,np.cross(z,x),z])
            expected_xy=np.asarray(hs)@reciprocal@frame[:2].T
            np.testing.assert_allclose(w._diffraction_spots.get_offsets(),expected_xy,atol=3e-14)
            assert all(str(h) in {v.get_text() for v in w.ax.texts} for h in hs)
            if name=='bcc_fe':assert (1,0,0) not in hs and (1,1,0) in hs
            if name=='cscl':assert (1,0,0) in hs
            negative=tuple(-v for v in target);xy=w.ax.transData.transform(g[hs.index(negative)])
            w.clicked(MouseEvent('button_press_event',w.canvas,*xy,button=1));assert indices(w.target.text())==negative
            w.align();q=w.current[3][w.current[2].index(negative)];s=w.settings()
            residual=abs(q@q+2*(np.asarray(s.tilt)*.001/electron_wavelength_angstrom(s.voltage))@q)
            assert residual<1e-10
            assert w.run_button.isEnabled() and not w.emcd_button.isEnabled() and material_reason(w.structure)
            w.start_preview();wait();capture(name)
            record(name,beams=len(hs),clicked_hkl=negative,bragg_residual=float(residual),ni_mdff_disabled=True,
                rendered_coordinate_max_error=float(np.max(abs(g-expected_xy))))

        # Missing external data are isolated from the two bundled providers.
        import os
        with patch.dict(os.environ,{'EMCD_SIM_LEGACY_ATOMIC_TABLE':str(output/'absent_table.py')}):
            w.elastic_provider_box.setCurrentIndex(w.elastic_provider_box.findData(LEGACY));w.refresh()
            assert not w.run_button.isEnabled() and 'EMCD_SIM_LEGACY_ATOMIC_TABLE' in w.structure_label.text()
            w.elastic_provider_box.setCurrentIndex(w.elastic_provider_box.findData(ADAPTIVE));w.refresh()
            assert w.run_button.isEnabled()
        record('missing_external_provider_diagnostic',bundled_provider_unaffected=True)

        w.structure=Structure.nickel();w.last_result=None
        w.zone.setText('0 1 7');w.target.setText('2 0 0')
        w.set_values(dict(kv=200,tx=-1000*electron_wavelength_angstrom(200)/3.524,ty=15,
            thickness=1,beam=.9,potential=1.8,grid=9,depth=9,subpixels=16))
        w.propagation_box.setCurrentIndex(0);w.channeling_box.setCurrentIndex(0)
        w.energy_scope.setCurrentIndex(1);w.angular_maps.setChecked(False);w.correction.setChecked(False)
        w.declaration.setChecked(True);w.worker_mode.setCurrentIndex(1);w.worker_count.setValue(1)
        # Reconnect the bundled source, never an old project's external path.
        from .runtime import reference_source
        w.source_path.setText(str(reference_source()));w.validate_xmcd();w.declaration.setChecked(True)
        w.correction.setChecked(False);w.refresh();w.emcd_stale()
        assert w.emcd_button.isEnabled(),w.emcd_button.toolTip()
        for index,channel in enumerate(('single','double')):
            w.channeling_box.setCurrentIndex(index);w.emcd_stale()
            assert w.emcd_button.isEnabled(),w.emcd_button.toolTip()
            w.start_emcd();wait();assert w.emcd_result['metadata']['elastic_provider']['provider']==ADAPTIVE
            spectra=w.emcd_result['spectra'];assert len(spectra['energy_ev'])==2
            assert all(np.isfinite(spectra[k]).all() for k in ('I_A_plus','I_A_minus','I_B_plus','I_B_minus'))
            ap,am,bp,bm=[spectra[k] for k in ('I_A_plus','I_A_minus','I_B_plus','I_B_minus')]
            np.testing.assert_allclose(spectra['D_raw'],spectra['D_mag']+spectra['D_nonmag'],rtol=1e-12,atol=1e-14)
            np.testing.assert_allclose(spectra['D_mag'],((ap-am)-(bp-bm))/2,rtol=1e-12,atol=1e-14)
            np.testing.assert_allclose(spectra['D_nonmag'],((ap+am)-(bp+bm))/2,rtol=1e-12,atol=1e-14)
            assert np.max(abs(ap-am))>1e-14,'Magnetization reversal smoke has no odd signal'
            save_project(w.emcd_result,output/('new_ni_emcd_'+channel));loaded=load_project(output/('new_ni_emcd_'+channel))
            assert loaded['settings'].elastic_provider==ADAPTIVE and fingerprints(loaded)==fingerprints(w.emcd_result)
            record('ni_native_mdff_and_full_project_roundtrip_'+channel,energy_samples=2,provider=ADAPTIVE,
                channeling=channel,raw_reversal={k:spectra[k].tolist() for k in ('I_A_plus','I_A_minus','I_B_plus','I_B_minus')},
                nonmagnetic_AB=((ap+am-bp-bm)/2).tolist(),flip_M_A=(ap-am).tolist())
        report['complete']=True
    except BaseException:
        report['complete']=False;report['errors'].append(traceback.format_exc())
    finally:
        if w.busy:w.cancel();w.worker.wait(15000);app.processEvents()
        for dialog in w.dialogs:dialog.close()
        w.close();app.processEvents()
        report['errors'].extend(errors)
        report['all_workers_stopped']=not bool(w.worker and w.worker.isRunning())
        (output/'acceptance.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
        app.quit()
    return 0 if report.get('complete') and not report['errors'] and report['all_workers_stopped'] else 2
