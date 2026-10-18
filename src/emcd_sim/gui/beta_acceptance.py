"""Opt-in sequential source/frozen acceptance with real widgets and workers."""
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import csv,hashlib,json,os,platform,sys,time,traceback
import numpy as np
from PySide6 import QtCore,QtGui,QtWidgets
from .project_io import load_project,save_project,config_from_dict,rerun_reason
from .emcd_forward import export_result
from .runtime import build_info,reference_source
from .rc_acceptance import fingerprints


def run(output,source,production):
    from .app import MainWindow
    from .geometry import Structure,excitation
    from .compare_results import map_compatibility
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    if not QtGui.QFontDatabase.families():
        from matplotlib import get_data_path
        font=QtGui.QFontDatabase.addApplicationFont(str(Path(get_data_path())/'fonts/ttf/DejaVuSans.ttf'))
        app.setFont(QtGui.QFont(QtGui.QFontDatabase.applicationFontFamilies(font)[0],9))
    w=MainWindow(workspace=output/'workspace');w.resize(1600,1100);w.show()
    report=dict(build=build_info(),platform=platform.platform(),frozen=bool(getattr(sys,'frozen',False)),
        executable=sys.executable,working_directory=str(Path.cwd()),
        development_python_paths_removed=not any(s in os.environ.get('PATH','').lower() for s in ('conda','python')),
        qt_platform=app.platformName(),screen_dpr=app.primaryScreen().devicePixelRatio(),scale_environment=os.environ.get('QT_SCALE_FACTOR'),
        clean_machine='NOT TESTED',cases={},checks={},errors=[])
    def check(name,condition):
        if not condition:raise AssertionError(name)
        report['checks'][name]='PASS'
    def idle(timeout=240):
        deadline=time.monotonic()+timeout
        while w.busy:
            app.processEvents();time.sleep(.01)
            if time.monotonic()>deadline:raise TimeoutError('GUI worker timed out')
        app.processEvents()
    def screenshot(name):
        app.processEvents();w.grab().save(str(output/(name+'.png')))
    def error(message):report['errors'].append(message)
    w.error=error
    try:
        app.processEvents();screenshot('startup')
        check('default_fcc_ni',w.structure.atoms.get_chemical_formula()=='Ni4')
        cif=output/'Ni.cif';w.structure.atoms.write(cif);w.structure=Structure.from_cif(cif);w.refresh()
        check('cif_import',not w.structure.elastic_reason)
        w.reset_reference();w.source_path.setText(str(source));w.validate_xmcd();w.declaration.setChecked(True)
        w.set_values(dict(thickness=2,beam=.9,potential=1.8,xl3=831.4778,xl2=848.698,halfwidth=.5))
        for key,value in dict(energy=9,grid=9,depth=9,subpixels=16,fft_grid=24).items():w.spin[key].setValue(value)
        w.correction.setChecked(False);w.angular_maps.setChecked(True);w.energy_scope.setCurrentIndex(0);w.refresh()
        g=w.current[3][w.current[2].index((2,0,0))];w.align()
        check('exact_bragg_and_indexing',abs(excitation(g,w.settings().tilt,200))<1e-10)
        w.start_preview();idle();check('elastic_preview',w.run_outcome=='completed' and len(w.last_result['intensity'])>=3)
        screenshot('diffraction')
        for ci,channel in enumerate(('single','double')):
            for pi,solver in enumerate(('bloch','fft-multislice','both')):
                key=channel+'_'+solver;w.channeling_box.setCurrentIndex(ci);w.propagation_box.setCurrentIndex(pi)
                w.start_emcd();check(key+'_started',w.busy);idle()
                check(key+'_completed',w.run_outcome=='completed' and not report['errors'])
                r=w.emcd_result
                check(key+'_dispatch',r['config'].channeling_model==channel and set(r['methods'])==({'bloch','fft-multislice'} if solver=='both' else {solver}))
                before=fingerprints(r);view=w.eels_view
                for mode in (1,0):
                    view.component_mode.setCurrentIndex(mode);app.processEvents();check(key+'_two_panels',len(view.figure.axes)==2)
                for zoom in (1,2,0):view.choice.setCurrentIndex(zoom);app.processEvents()
                check(key+'_display_invariant',before==fingerprints(r))
                view.component_mode.setCurrentIndex(1);view.choice.setCurrentIndex(2)
                prb=view.prb_benchmark;prb.selection.setCurrentIndex(1);prb.energy.setValue(848.698);prb.fixed.setChecked(True)
                project=output/(key+'_project');w.save_to_path(project);idle()
                reopened=load_project(project);check(key+'_roundtrip',before==fingerprints(reopened))
                w.eels_view.component_mode.setCurrentIndex(0);prb.fixed.setChecked(False);w.display_saved_result(reopened)
                check(key+'_display_state_restored',view.component_mode.currentData()=='relative' and prb.fixed.isChecked() and abs(prb.energy.value()-848.698)<1e-6)
                record=w.browser.registry.register(reopened,project,key);w.browser.refresh()
                check(key+'_browser',record['channeling_model']==channel and record['propagation']==solver)
                export_result(reopened,output/(key+'_export'),component_mode='relative')
                with np.load(output/(key+'_export')/'virtual_detector_eels.npz',allow_pickle=False) as arrays:
                    for method,m in r['methods'].items():
                        for name,value in m['spectra'].items():np.testing.assert_array_equal(arrays[method+'__'+name],value)
                report['cases'][key]=dict(fingerprints=before,energy_ev=r['spectra']['energy_ev'].tolist(),raw={method:{name:m['spectra'][name].tolist() for name in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')} for method,m in r['methods'].items()},project=str(project),config=dict(beam=.9,potential=1.8,fft=24,depth=9,grid=9,thickness_nm=2))
                if channel=='double' and solver=='both':
                    view.method.setCurrentIndex(view.method.findData('overlay'))
                    check('both_spectra_overlay',len([line for line in view.figure.axes[0].lines if 'Detector A' in line.get_label()])==2)
                    for ext in ('png','svg'):view.figure.savefig(output/('bw_ms_spectra.'+ext),dpi=160)
                    w.browser_dock.hide();view.maximize();screenshot('double_both_relative')
                    view.component_mode.setCurrentIndex(0);screenshot('double_both_raw');view.maximize()
                    w.tabs.setCurrentWidget(w.maps_view);w.maps_view.maximize();screenshot('double_both_maps');w.maps_view.maximize()
                    for ext in ('png','svg'):w.maps_view.figure.savefig(output/('angular_maps.'+ext),dpi=160)
        previous=w.emcd_result;w.start_emcd();w.cancel();idle();check('cancel_preserves_previous',w.emcd_result is previous)
        w.spin['tx'].setValue(w.spin['tx'].value()+.1);check('stale_detection','STALE' in w.eels_view.label.text())
        w.spin['fft_grid'].setValue(13);check('invalid_fft_rejected',not w.emcd_button.isEnabled());w.spin['fft_grid'].setValue(24)
        from .memory_budget import BUDGETS_MIB,assess_memory
        check('memory_budgets',tuple(w.memory_budget.itemData(i) for i in range(w.memory_budget.count()))==BUDGETS_MIB)
        try:assess_memory(9000,512,snapshot=dict(available_ram_mib=10000,process_rss_mib=100))
        except ValueError as exc:check('clear_memory_rejection','dense kernel' in str(exc) and 'No simulation parameters were changed' in str(exc))
        else:raise AssertionError('Memory rejection missing')
        check('incompatible_comparison_flagged',not map_compatibility(previous,dict(previous,qx=previous['qx']+.1),'L3','I_mag')[0])
        check('compatible_comparison',map_compatibility(previous,previous,'L3','I_mag')[0])
        missing=dict(previous,config=replace(previous['config'],source=str(output/'absent.xmcd')))
        check('missing_external_source_rerun_blocked',bool(rerun_reason(missing)))
        w.source_path.setText(str(output/'absent.xmcd'));w.validate_xmcd(show_error=False);check('missing_source_no_fallback',not w.emcd_button.isEnabled())
        w.source_path.setText(str(reference_source()));w.validate_xmcd(show_error=False)
        check('distributable_example_import',w.source_info is not None)
        w.declaration.setChecked(True);w.channeling_box.setCurrentIndex(0);w.propagation_box.setCurrentIndex(0)
        w.start_emcd();idle();check('standalone_example_calculation',w.run_outcome=='completed')
        report['bundled_example_source_sha256']=w.emcd_result['metadata']['source_audit']['sha256']
        check('legacy_defaults_single',config_from_dict({}).channeling_model=='single')
        for engine in ('bloch','fft-multislice'):
            saved=load_project(Path(production)/f'001_008_double_{engine}/prepared_v1/full');before=fingerprints(saved)
            with patch('emcd_sim.gui.emcd_forward.calculate',side_effect=AssertionError('Saved spectra must not recalculate')):
                w.display_saved_result(saved);w.eels_view.maximize()
                for mode in (0,1):
                    w.eels_view.component_mode.setCurrentIndex(mode)
                    for zoom in (0,1,2):w.eels_view.choice.setCurrentIndex(zoom);app.processEvents()
                w.eels_view.choice.setCurrentIndex(0);screenshot('production_'+engine);w.eels_view.maximize()
            check('saved_242_'+engine,len(saved['spectra']['energy_ev'])==242 and fingerprints(saved)==before)
            report['cases']['saved_'+engine]=dict(fingerprints=before,source_sha256=saved['config'].source_sha256)
        w.resize(1000,750);app.processEvents();w.resize(1700,1150);app.processEvents();check('resize',w.width()>1000)
        report['outcome']='PASS';report['checkpoint_C']='PASS';report['checkpoint_D']='PASS'
    except Exception:
        report['outcome']='FAIL';report['failure']=traceback.format_exc()
    finally:
        if w.busy:w.cancel();idle()
        (output/'acceptance.json').write_text(json.dumps(report,indent=2),encoding='utf-8');w.close();app.processEvents()
    return 0 if report['outcome']=='PASS' else 2
