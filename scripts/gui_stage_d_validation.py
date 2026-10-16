"""Native Windows Stage D calculation/save and separate-process reopen acceptance."""
import argparse,json,hashlib
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
import numpy as np
from PySide6 import QtCore,QtWidgets
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.project_io import load_project


def fingerprints(r):
    values={}
    for method,m in r['methods'].items():
        arrays=dict(m['spectra'],coherence=m['coherence'],amplitudes=m['amplitudes'],qx=m['qx'],qy=m['qy'])
        arrays.update({edge+'__'+k:v for edge,fields in m['maps'].items() for k,v in fields.items()})
        for k,v in arrays.items():values[method+'__'+k]=hashlib.sha256(np.ascontiguousarray(v).tobytes()).hexdigest()
    return values


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--phase',choices=['calculate','reopen'],required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    app=QtWidgets.QApplication([]);app.setQuitOnLastWindowClosed(False);w=MainWindow(workspace=args.output/'workspace');w.resize(1700,1050);w.show();failed=[];state={};report={}
    def error(message):failed.append(message);print('ERROR: '+message,flush=True)
    w.error=error
    def idle(callback):
        if w.busy:QtCore.QTimer.singleShot(100,lambda:idle(callback));return
        if failed:app.exit(2);return
        callback()
    if args.phase=='calculate':
        cases=[('reference',0,2,0.),('mistilt',0,2,1.),('atomic_ms',1,1,0.)]
        def start():
            if not cases:
                (args.output/'calculated_fingerprints.json').write_text(json.dumps(report,indent=2)+'\n');w.close();app.quit();return
            key,model,method,offset=cases.pop(0);state['key']=key
            w.model_box.setCurrentIndex(model);w.propagation_box.setCurrentIndex(method);w.reset_reference()
            if offset:w.spin['tx'].setValue(w.spin['tx'].value()+offset)
            print('Actual native calculation: '+key,flush=True);w.start_emcd()
            if not w.busy:error('Calculation not started');app.exit(2)
        def calculated():
            def save():
                if w.run_outcome!='completed':error('Run failed');app.exit(2);return
                key=state['key'];report[key]=fingerprints(w.emcd_result);w.save_to_path(args.output/(key+'_project'))
            idle(save)
        def saved():
            if w.run_outcome!='completed':error('Save failed');app.exit(2);return
            QtCore.QTimer.singleShot(100,start)
        w.emcd_ready.connect(lambda:QtCore.QTimer.singleShot(100,calculated));w.project_ready.connect(saved);QtCore.QTimer.singleShot(300,start)
        code=app.exec()
        if code or failed:raise RuntimeError(f'Calculation/save acceptance failed: {failed}')
        print('Three real runs saved; GUI closed. Start separate reopen phase.',flush=True)
    else:
        expected=json.loads((args.output/'calculated_fingerprints.json').read_text());cases=list(expected);selected=[]
        def open_next():
            if not cases:compare();return
            key=cases.pop(0);state['key']=key;print('Reopening without solvers: '+key,flush=True);w.open_project_path(args.output/(key+'_project'))
        def opened():
            if w.run_outcome!='completed':error('Open failed');app.exit(2);return
            r=w.emcd_result;key=state['key'];assert fingerprints(r)==expected[key]
            report[key]=dict(exact_array_hashes=True,method_labels=list(r['methods']),za_q=r['metadata']['za_q'],source_hash=r['config'].source_sha256)
            QtCore.QTimer.singleShot(150,open_next)
        def compare():
            assert len(w.browser.registry.records)==3
            w.browser.table.clearSelection()
            for i in range(w.browser.table.rowCount()):
                record_id=w.browser.table.item(i,0).data(QtCore.Qt.ItemDataRole.UserRole)
                record=next(r for r in w.browser.registry.records if r['id']==record_id)
                if Path(record['path']).name in ('reference_project','mistilt_project'):
                    w.browser.table.selectionModel().select(w.browser.table.model().index(i,0),QtCore.QItemSelectionModel.SelectionFlag.Select|QtCore.QItemSelectionModel.SelectionFlag.Rows)
            w.project_ready.disconnect(opened);w.project_ready.connect(compared);w.compare_selected()
        def compared():
            widget=w.tabs.currentWidget();assert widget.__class__.__name__=='CompareResults';entries=widget.entries();assert len(entries)==2
            assert entries[0][1]['settings'].tilt!=entries[1][1]['settings'].tilt
            widget.maximize();widget.figure.savefig(args.output/'comparison.png',dpi=220);widget.figure.savefig(args.output/'comparison.svg')
            state['widget']=widget
            QtCore.QTimer.singleShot(900,capture)
        def capture():
            w.browser.table.scrollToTop()
            target=Path('docs/images/gui/stage_d_windows.png');target.parent.mkdir(parents=True,exist_ok=True);w.grab().save(str(target))
            before=w.settings();reference=next(r for r in w.browser.registry.records if Path(r['path']).name=='reference_project')
            w.display_saved_result(w.browser.cache[reference['id']],reference);assert w.settings()==before
            w.use_result_settings();assert not w.busy;assert abs(w.settings().tilt[0]+7.11672544)<1e-9
            report['acceptance']=dict(registered=3,compared=2,separate_process_reopen=True,no_solver_calls=True,settings_restore_without_run=True,
                exported_png_svg=True,screenshot=str(target),source_free_numeric_data=True)
            (args.output/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n');w.close();app.quit()
        with ExitStack() as guards:
            for name in ('emcd_sim.physical_elastic.PhysicalElasticModel.amplitudes','emcd_sim.multislice_reference.fft_multislice_ni','emcd_sim.gui.emcd_forward.calculate','emcd_sim.gui.emcd_forward.tensors'):
                guards.enter_context(patch(name,side_effect=AssertionError('Solver executed during reopen/compare')))
            w.project_ready.connect(opened);QtCore.QTimer.singleShot(300,open_next);code=app.exec()
        if code or failed:raise RuntimeError(f'Reopen acceptance failed: {failed}')
        print('Separate-process native reopen/compare/settings restore passed; 3 projects, 2 compared.',flush=True)


if __name__=='__main__':main()
