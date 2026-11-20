"""Frozen Git-source comparisons with original inputs, not new golden arrays."""
import ast
from dataclasses import asdict,replace
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import types
from unittest.mock import patch
import numpy as np
from contract_capture import flatten,metrics,plain
from reference_imports import relocate_reference_imports
from emcd_sim import channeling as channeling
from emcd_sim import forward_pipeline as forward_pipeline
from emcd_sim.forward_settings import NiForwardSettings
from emcd_sim.structure_geometry import Structure, Settings, elastic_model
from emcd_sim.historical_ni import HistoricalNiSites
from emcd_sim import double_channeling as bw
from test_single_element_ni_compatibility import old_contract
from test_multisite_scientific_validation import cr_case
from test_multisite_forward import configuration

ROOT=Path.cwd();EVIDENCE=Path(os.environ.get('SCI_REVIEW_ROOT', ROOT/'build/scientific-contract-review'))
OUT=EVIDENCE/'history-v2';OUT.mkdir(parents=True,exist_ok=False)
def source(rev,path):return subprocess.check_output(['git','show',rev+':'+path]).decode('utf-8-sig')
def archived_bw(rev):
    name='emcd_sim._contract_bw_'+rev;module=types.ModuleType(name);module.__package__='emcd_sim';sys.modules[name]=module
    exec(compile(source(rev,'src/emcd_sim/double_channeling.py'),rev+':double_channeling.py','exec'),module.__dict__)
    # Same software-type binding used by the original historical comparison.
    module.PreparedBlochIncoming=bw.PreparedBlochIncoming
    return module

def adapted(module):
    allowed=inspect.signature(module.double_channeling_response).parameters
    def call(*args,**kwargs):
        kw=dict(kwargs)
        if 'ionization_sites' not in allowed:
            sites=kw.pop('ionization_sites')
            assert isinstance(sites,HistoricalNiSites)
            np.testing.assert_array_equal(sites.positions_for(args[0].crystal),args[0].crystal.fractional_positions)
        for name in ('cancelled','prepared_outgoing','timings'):
            if name not in allowed:kw.pop(name,None)
        return module.double_channeling_response(*args,**kw)
    return call

def arrays(result):
    values={};flatten(result,'',values)
    return {k:v for k,v in values.items() if not k.startswith(('/fft','/cohorts'))}

def compare_results(a,b):
    x,y=arrays(a),arrays(b);assert x.keys()==y.keys()
    rows=[]
    for key in x:
        m=metrics(x[key],y[key]);
        if not m['bitwise_equal']:rows.append(dict(array=key,**m))
    return dict(arrays=len(x),different_arrays=len(rows),differences=rows)

def cases(calc,contract=None):
    results={}
    for solver in ('bloch','both'):
        cfg=NiForwardSettings(axis_declared=True,channeling_model='double',propagation=solver,
            energy_points=9,angular_maps=True,grid=9,depth=9,fft_grid=24,subpixels=16,correction=False)
        s=Settings(thickness=2,beam_cutoff=.9,potential_cutoff=1.8)
        results['a2' if solver=='bloch' else 'a3']=calc(Structure.nickel(),s,cfg)
    for model in ('xmcd','atomic'):
        cfg=NiForwardSettings(model=model,axis_declared=True,channeling_model='double',propagation='both',
            energy_scope='edges',grid=9,depth=9,subpixels=8,fft_grid=16,slice_step=.01,halfwidth=.7,
            centers=((.2,.2),(.2,-.2)),radius=.12,correction=False,worker_mode='manual',parallel_workers=1)
        if model=='atomic':cfg=replace(cfg,l3=cfg.atomic.l3_ev,l2=cfg.atomic.l2_ev)
        results['c1' if model=='xmcd' else 'c2']=calc(Structure.nickel(),Settings(thickness=.3,beam_cutoff=.9,potential_cutoff=1.8),cfg)
    return results

current=cases(forward_pipeline.calculate)
older_ni=old_contract.__wrapped__()
with patch.object(channeling,'calculate_detector_signals',older_ni):old_ni=cases(forward_pipeline.calculate)
baseline=archived_bw('7bebdce')
with patch.object(channeling,'double_channeling_response',adapted(baseline)):
    old7=cases(forward_pipeline.calculate)
elastic=elastic_model(Structure.nickel(),Settings(thickness=2,beam_cutoff=.9,potential_cutoff=1.8))
queries=np.array([[.15,.2],[.15,-.2]])
numeric7=baseline.double_channeling_response(elastic,831.4778,queries,2,method='numerical',depth_steps=9)
revisions=['7bebdce','f030556','5347f44','2f9c130','76deb65','a87f5df','ef54a53','e5b6e4a','cdb8836','91aff15','6d98694']
history=[];saved={}
for rev in revisions:
    module=archived_bw(rev)
    numeric=module.double_channeling_response(elastic,831.4778,queries,2,method='numerical',depth_steps=9)
    with patch.object(channeling,'double_channeling_response',adapted(module)):
        computed=cases(forward_pipeline.calculate)
    rows={'a1':metrics(numeric,numeric7)}
    for name,r in computed.items():rows[name]=compare_results(r,(old_ni if name.startswith('c') else old7)[name])
    h=dict(revision=subprocess.check_output(['git','rev-parse',rev],text=True).strip(),comparisons=rows)
    history.append(h);flatten(computed,rev,saved);saved[rev+'/numeric']=numeric
    (OUT/'kernel_history.json').write_text(json.dumps(history,indent=2,default=plain)+'\n',encoding='utf-8')
    checkpoint={};flatten(computed,'',checkpoint);checkpoint['numeric']=numeric
    np.savez_compressed(OUT/(rev+'-observed.npz'),**checkpoint)
    print('KERNEL_HISTORY',rev,{k:(v.get('different_arrays',v.get('differing_elements'))) for k,v in rows.items()},flush=True)

def frozen(rev):
    token=rev.replace('-','_');names={x:'emcd_sim.gui._contract_'+token+'_'+x for x in ('channeling','forward','pipeline')}
    def load(filename,role):
        name=names[role];m=types.ModuleType(name);m.__package__='emcd_sim.gui';sys.modules[name]=m
        text=source(rev,'src/emcd_sim/gui/'+filename)
        for old,owner in (('forward_pipeline','pipeline'),('emcd_forward','forward'),('channeling','channeling')):
            text=text.replace('from .'+old+' import','from .'+names[owner].rsplit('.',1)[-1]+' import')
        exec(compile(relocate_reference_imports(text),rev+':'+filename,'exec'),m.__dict__);return m
    ch=load('channeling.py','channeling')
    old_style=rev=='cdb8836'
    if old_style:fwd=load('emcd_forward.py','forward')
    pipe=load('forward_pipeline.py','pipeline')
    def calc(structure,settings,cfg,**kw):
        if old_style:
            if 'sites' in kw:
                sites=kw.pop('sites');return pipe.calculate_multisite(structure,settings,sites,pipe.MultiSiteForwardSettings(**asdict(cfg)),**kw)
            return fwd.calculate(structure,settings,cfg,**kw)
        return pipe.calculate(structure,settings,cfg,**kw)
    return calc

frozen_rows=[]
for rev in ('cdb8836','91aff15','6d98694'):
    calc=frozen(rev);results=cases(calc)
    folder=OUT/(rev+'-cr-inputs');folder.mkdir();structure,settings,sites,declared=cr_case(folder,True)
    cfg=configuration(propagation='bloch',channeling_model='double',depth=17,slice_step=.02,angular_maps=False)
    r=calc(structure,settings,cfg,energy_ev=np.array([710.,723.]),sites=sites)
    pair={name:compare_results(result,current[name]) for name,result in results.items()}
    weights=sum(g.multiplicity for g in sites.groups)
    expected=sum(g.multiplicity*r['groups'][g.group_id]['spectra']['M_A'] for g in sites.groups)/weights
    pair['b1']=metrics(r['spectra']['M_A'],expected,3e-13,1e-18)
    frozen_rows.append(dict(revision=rev,comparisons=pair));flatten(r,rev+'/cr',saved)
    (OUT/'frozen_sources.json').write_text(json.dumps(frozen_rows,indent=2,default=plain)+'\n',encoding='utf-8')
    print('FROZEN_SOURCE',rev,{k:v.get('different_arrays',v.get('max_absolute')) for k,v in pair.items()},flush=True)

np.savez_compressed(OUT/'observed_arrays.npz',**saved)
(OUT/'history.json').write_text(json.dumps(dict(kernel_history=history,frozen_sources=frozen_rows,
    adapters='Only import relocation, exact PreparedBlochIncoming type binding, and unsupported software arguments; legacy site positions explicitly certified.'),indent=2,default=plain)+'\n',encoding='utf-8')
