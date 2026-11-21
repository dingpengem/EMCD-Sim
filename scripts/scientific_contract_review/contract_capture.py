"""Observe original failing assertions; never replace or suppress them."""
import csv
import dataclasses
import datetime
import inspect
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import threading
import numpy as np

OUT = Path(os.environ['SCI_CONTRACT_OUTPUT']) if 'SCI_CONTRACT_OUTPUT' in os.environ else None
if OUT is not None:OUT.mkdir(parents=True, exist_ok=False)
ROOT = Path(__file__).resolve().parents[2]
ARRAYS = {}
OPERATIONS = []
COUNTS = {}
PROFILE_LOCK=threading.RLock()
TARGETS = {'test_double_cancellation.py', 'test_single_element_ni_compatibility.py',
           'test_multisite_scientific_validation.py'}

def plain(v):
    if dataclasses.is_dataclass(v):
        return {f.name:plain(getattr(v,f.name)) for f in dataclasses.fields(v)}
    if isinstance(v, np.ndarray):return v.tolist()
    if isinstance(v, np.generic):return plain(v.item())
    if isinstance(v, complex):return {'real':v.real,'imag':v.imag}
    if isinstance(v, dict):return {str(k):plain(x) for k,x in v.items()}
    if isinstance(v, (list,tuple)):return [plain(x) for x in v]
    if isinstance(v, Path):return str(v)
    if v is None or isinstance(v,(str,bool,int,float)):return v
    return {'type':type(v).__module__+'.'+type(v).__name__}

def flatten(v, prefix, out, depth=0):
    if depth>10:return
    if isinstance(v,np.ndarray) and v.dtype.kind in 'biufc':out[prefix]=v.copy()
    elif isinstance(v,dict):
        for k,x in v.items():
            if k not in ('model','metadata','timings','diagnostics','execution','comparison'):
                flatten(x,prefix+'/'+str(k),out,depth+1)
    elif isinstance(v,(list,tuple)):
        for k,x in enumerate(v):flatten(x,prefix+'/'+str(k),out,depth+1)

def ulp(a,b):
    a=np.asarray(a,np.float64);b=np.asarray(b,np.float64)
    x=a.view(np.uint64);y=b.view(np.uint64);sign=np.uint64(1<<63)
    x=np.where((x&sign)!=0,~x,x|sign);y=np.where((y&sign)!=0,~y,y|sign)
    return np.maximum(x,y)-np.minimum(x,y)

def metrics(a,b,rtol=0.,atol=0.):
    a,b=np.broadcast_arrays(np.asarray(a),np.asarray(b))
    finite=np.isfinite(a)&np.isfinite(b);d=np.abs(a-b)
    allowed=atol+rtol*np.abs(b);residual=d-allowed
    different=(a!=b)&finite;bad=(residual>0)&finite
    rel=np.divide(d,np.abs(b),out=np.full(d.shape,np.inf),where=np.abs(b)>0)
    rel=np.where((d==0)&(np.abs(b)==0),0,rel)
    scale=float(np.max(np.abs(b))) if b.size else 0.
    components=[]
    for x,y in ((a.real,b.real),(a.imag,b.imag)) if np.iscomplexobj(a) or np.iscomplexobj(b) else ((a,b),):
        distances=ulp(x,y);mask=np.isfinite(x)&np.isfinite(y)&(x!=y)
        components.extend(int(v) for v in distances[mask].ravel())
    k=int(np.argmax(np.where(finite,d,-np.inf))) if a.size else 0
    return dict(shape=list(a.shape),actual_dtype=str(a.dtype),expected_dtype=str(b.dtype),size=a.size,
        differing_elements=int(different.sum()),differing_fraction=float(different.sum()/a.size) if a.size else 0.,
        bitwise_equal=bool(a.dtype==b.dtype and a.tobytes()==b.tobytes()),value_equal=bool(np.array_equal(a,b,equal_nan=True)),
        max_absolute=float(np.max(d[finite])) if finite.any() else None,
        max_relative=float(np.max(rel[finite])) if finite.any() else None,
        max_assertion_residual=float(np.max(residual[finite])) if finite.any() else None,
        failing_elements=int(bad.sum()),rtol=rtol,atol=atol,reference_scale=scale,
        normwise_relative=float(np.linalg.norm(a-b)/np.linalg.norm(b)) if np.linalg.norm(b)>0 else None,
        max_component_ulp=max(components,default=0),component_ulp_histogram={str(u):components.count(u) for u in sorted(set(components))},
        max_error_index=list(np.unravel_index(k,a.shape)),max_error_actual=plain(a.ravel()[k]),max_error_expected=plain(b.ravel()[k]),
        signed_error_at_max=plain((a-b).ravel()[k]),
        zero_reference_differences=int((different&(b==0)).sum()),nonfinite_elements=int((~finite).sum()))

def profile_unlocked(frame,event,arg):
    if event!='return':return
    name=frame.f_code.co_name;mod=frame.f_globals.get('__name__','')
    if name not in ('_numerical_site_responses','depth_response','equivalent_site_phases','prepare_outgoing_bloch',
                    'contract_multisite_bloch_double','integrate_detector_block'):
        return
    if not mod.startswith('emcd_sim'):return
    key=mod+':'+name;n=COUNTS.get(key,0);COUNTS[key]=n+1
    if n>=4:return
    prefix='operation/'+str(len(OPERATIONS));f=frame.f_locals
    array_names=('a','b','kernel','k','phases','positions','incoming_hkl','outgoing_hkl','paired_fields','reference_h','h','v','outer','matrix','ab','raw','weights','support','qx','qy')
    layouts={}
    for k in array_names:
        if k in f:flatten(f[k],prefix+'/'+k,ARRAYS)
        if isinstance(f.get(k),np.ndarray):
            layouts[k]=dict(shape=list(f[k].shape),strides=list(f[k].strides),c_contiguous=f[k].flags.c_contiguous,f_contiguous=f[k].flags.f_contiguous)
    for k in ('incoming','outgoing'):
        obj=f.get(k)
        if obj is not None:
            for field in ('values','vectors'):flatten(getattr(obj,field,None),prefix+'/'+k+'/'+field,ARRAYS)
    flatten(arg,prefix+'/returned',ARRAYS)
    caller=frame.f_back
    for _ in range(6):
        if caller is None or 'energy_ev' in caller.f_locals:break
        caller=caller.f_back
    OPERATIONS.append(dict(prefix=prefix,module=mod,function=name,ordinal=n,layouts=layouts,
        filename=frame.f_code.co_filename,thickness_nm=plain(f.get('thickness_nm',f.get('t'))),
        energy_ev=plain(f.get('energy_ev',caller.f_locals.get('energy_ev') if caller else None)),
        query=plain(caller.f_locals.get('q')) if caller else None,
        prepared_incoming=f.get('prepared_incoming') is not None))

def profile(frame,event,arg):
    with PROFILE_LOCK:profile_unlocked(frame,event,arg)

def pytest_runtest_call(item):
    threading.setprofile(profile)
    sys.setprofile(profile)

def capture_report(item,call):
    if call.when!='call':return
    sys.setprofile(None)
    threading.setprofile(None)
    from emcd_sim.parallel_resources import native_backend_info
    metadata=dict(node=item.nodeid,head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),python=sys.version,numpy=np.__version__,
        scipy=__import__('scipy').__version__,platform=platform.platform(),backend=native_backend_info(),
        threads={k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','OPENBLAS_CORETYPE','NPY_DISABLE_CPU_FEATURES')},
        numpy_cpu_features=getattr(np._core._multiarray_umath,'__cpu_features__',{}),
        epsilon=float(np.finfo(np.float64).eps),longdouble_bits=np.finfo(np.longdouble).nmant+1,
        diagnostic_only=True,original_assertion_preserved=True,operations=OPERATIONS)
    if call.excinfo is None:
        metadata['outcome']='passed'
    else:
        metadata.update(outcome='original failure',exception=str(call.excinfo.value))
        tb=call.excinfo.value.__traceback__;local=None;test_globals={};assert_local=None;assert_name=None
        while tb:
            frame=tb.tb_frame
            if Path(frame.f_code.co_filename).name in TARGETS:
                local=dict(frame.f_locals);test_globals=frame.f_globals
            if frame.f_code.co_name in ('assert_array_equal','assert_allclose') and 'actual' in frame.f_locals:
                assert_local=dict(frame.f_locals);assert_name=frame.f_code.co_name
            tb=tb.tb_next
        if local is not None:
            for k in ('cfg','settings','args','q','method','solver','model','channel','unequal','energy','key','worst'):
                if k in local:metadata[k]=plain(local[k])
            structure=local.get('structure');elastic=local.get('elastic')
            if structure is not None:
                metadata['structure']=dict(symbols=structure.atoms.get_chemical_symbols(),cell=structure.atoms.cell.array.tolist(),scaled_positions=structure.atoms.get_scaled_positions().tolist())
            if elastic is not None:
                metadata['elastic']=dict(hkl=plain(elastic.beams.hkl),microscope=plain(elastic.microscope),crystal=plain(elastic.crystal))
            if 'sites' in local:metadata['sites']=plain(local['sites'])
            if 'after' in local and 'before' in local:current,reference=local['after'],local['before']
            elif 'a' in local and 'b' in local:current,reference=local['a'],local['b']
            elif 'result' in local:
                current=local['result'];reference={}
                keys=tuple(test_globals['RAW_KEYS'])+tuple(test_globals['PARITY_KEYS'])
                metadata['linear_keys']=list(keys)
                for key in keys:
                    reference[key]=sum(g.multiplicity*current['groups'][g.group_id]['spectra'][key] for g in local['sites'].groups)/sum(g.multiplicity for g in local['sites'].groups)
                flatten(local.get('reverse',{}),'reverse',ARRAYS)
                flatten(local.get('declared',{}),'declared',ARRAYS)
            else:current,reference=local.get('actual'),local.get('expected')
            flatten(current,'current',ARRAYS);flatten(reference,'reference',ARRAYS)
        if assert_local is not None:
            a=np.asarray(assert_local['actual']);b=np.asarray(assert_local['desired'])
            ARRAYS['assertion/actual']=a;ARRAYS['assertion/expected']=b
            rtol=float(assert_local.get('rtol',0.));atol=float(assert_local.get('atol',0.))
            metadata['original_assertion']=dict(name=assert_name,**metrics(a,b,rtol,atol))
            with (OUT/'assertion_elements.csv').open('w',newline='',encoding='utf-8') as f:
                w=csv.writer(f);w.writerow(['index','actual_real','actual_imag','expected_real','expected_imag','signed_error_real','signed_error_imag','absolute_error','allowed','residual','ulp_real','ulp_imag'])
                for index in np.ndindex(a.shape):
                    x,y=a[index],b[index];err=x-y;d=abs(err);tol=atol+rtol*abs(y)
                    w.writerow([str(index),float(np.real(x)).hex(),float(np.imag(x)).hex(),float(np.real(y)).hex(),float(np.imag(y)).hex(),float(np.real(err)),float(np.imag(err)),d,tol,d-tol,int(ulp(np.real(x),np.real(y))),int(ulp(np.imag(x),np.imag(y)))])
    np.savez_compressed(OUT/'observed_arrays.npz',**ARRAYS)
    (OUT/'capture.json').write_text(json.dumps(metadata,indent=2,default=plain)+'\n',encoding='utf-8')

def pytest_runtest_makereport(item,call):
    try:
        capture_report(item,call)
    except Exception:
        import traceback
        sys.setprofile(None)
        (OUT/'capture_error.txt').write_text(traceback.format_exc(),encoding='utf-8')
        # An observation failure must never mask the original test outcome.

def pytest_sessionfinish(session,exitstatus):
    sys.setprofile(None)
    threading.setprofile(None)
