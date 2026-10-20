"""Opt-in selected-edge BW reproduction; run in a disposable subprocess.

Reads an existing checksummed project without modifying it. Never runs a full
energy spectrum; keeps its other physical/numerical inputs exactly as saved.
"""
import argparse,json,os,sys,time
from dataclasses import replace,asdict
from pathlib import Path
import numpy as np


def run(args):
    from emcd_sim.gui.project_io import load_project,restore_structure
    from emcd_sim.gui.emcd_forward import calculate
    from emcd_sim.gui.channeling import worker_count
    from emcd_sim.gui.memory_budget import memory_snapshot
    from emcd_sim.gui.geometry import geometry
    from emcd_sim.gui.runtime import build_info
    baseline_workers=None
    if args.baseline:
        if os.environ.get('OPENBLAS_NUM_THREADS')!='1':
            raise ValueError('Safe baseline comparison requires OPENBLAS_NUM_THREADS=1 before startup')
        import subprocess,types
        import emcd_sim.gui.channeling as adapter
        old=types.ModuleType('emcd_sim.gui._crash_baseline');old.__package__='emcd_sim.gui'
        source=subprocess.check_output(['git','show','f947889252adc15da0413f7a97d03fb178bc8fa5:src/emcd_sim/gui/channeling.py'])
        exec(compile(source,'baseline_channeling.py','exec'),old.__dict__)
        adapter.contract=old.contract;baseline_workers=old.worker_count
    saved=load_project(args.project)
    raw=json.loads((args.project/'input_parameters.json').read_text())
    structure=restore_structure(raw['structure_snapshot'])
    settings=replace(saved['settings'],beam_cutoff=args.cutoff)
    cfg=replace(saved['config'],propagation='bloch',channeling_model=args.channel,
                energy_scope='edges',angular_maps=args.maps)
    args.output.mkdir(parents=True,exist_ok=False)
    report=dict(build=build_info(),pid=os.getpid(),executable=sys.executable,
                settings=asdict(settings),config=asdict(cfg),source_project=str(args.project),
                beams=len(geometry(structure,settings)[2]),stages=[],heartbeat_count=0,
                memory_before=memory_snapshot(),started=time.time())
    report['bw_workers']=(baseline_workers or worker_count)(report['beams'],'bloch')
    report['baseline']=args.baseline
    def record(message):
        report['stages'].append(message);print(message,flush=True)
        (args.output/'progress.json').write_text(json.dumps(report,indent=2))
    def finish(result):
        arrays={}
        method=result['methods']['bloch']
        arrays.update(method['spectra'])
        for edge,fields in method['maps'].items():
            arrays.update({edge+'__'+key:value for key,value in fields.items()})
        np.savez_compressed(args.output/'numerical.npz',**arrays)
        report.update(complete=True,elapsed_seconds=time.time()-report['started'],
                      memory_after=memory_snapshot(),method_metadata=method['metadata'])
        (args.output/'complete.json').write_text(json.dumps(report,indent=2,default=str))
    if not args.gui:
        result=calculate(structure,settings,cfg,record);finish(result);return 0
    from PySide6 import QtCore,QtWidgets
    from emcd_sim.gui.app import MainWindow
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w=MainWindow(workspace=args.output/'workspace');w.emcd_result=saved;w.use_result_settings()
    w.numerical_mode.setCurrentIndex(1);w.propagation_box.setCurrentIndex(0)
    w.channeling_box.setCurrentIndex(0 if args.channel=='single' else 1)
    w.spin['beam'].setValue(args.cutoff);w.energy_scope.setCurrentIndex(1)
    w.angular_maps.setChecked(args.maps);w.refresh()
    assert w.settings()==settings and w.forward_settings()==cfg
    w.error=lambda message:record('GUI error: '+message)
    w.show();w.start_emcd()
    if w.worker is None:raise RuntimeError('GUI did not start the verified configuration')
    w.worker.stage.connect(record)
    def tick():
        report['heartbeat_count']+=1
        if w.busy:return
        if w.run_outcome!='completed':
            record('Outcome: '+w.run_outcome);w.close();app.exit(2);return
        finish(w.emcd_result);w.grab().save(str(args.output/'gui.png'));w.close();app.quit()
    timer=QtCore.QTimer();timer.timeout.connect(tick);timer.start(25)
    return app.exec()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--cutoff',type=float,required=True);p.add_argument('--channel',choices=['single','double'],required=True)
    p.add_argument('--maps',action='store_true');p.add_argument('--gui',action='store_true')
    p.add_argument('--baseline',action='store_true',help='Safe original-adapter comparison, requires one BLAS thread')
    raise SystemExit(run(p.parse_args()))
