"""Independent arithmetic diagnostics on observed data; not acceptance fixtures."""
import csv
from decimal import Decimal,localcontext
import json
import os
from pathlib import Path
import numpy as np
from contract_capture import metrics,plain

ROOT=Path(os.environ.get('SCI_REVIEW_ROOT','build/scientific-contract-review'));OUT=ROOT/'analysis';OUT.mkdir(parents=True,exist_ok=False)
U=np.finfo(float).eps/2
def gamma(n):return n*U/(1-n*U)
def D(x):return Decimal.from_float(float(x))
def C(x):return D(np.real(x)),D(np.imag(x))
def add(x,y):return x[0]+y[0],x[1]+y[1]
def mul(x,y):return x[0]*y[0]-x[1]*y[1],x[0]*y[1]+x[1]*y[0]
def conj(x):return x[0],-x[1]
ZERO=Decimal(0),Decimal(0)
def restore(v,layout):
    strides=layout['strides'];lo=sum(min(0,(n-1)*s) for n,s in zip(v.shape,strides));hi=sum(max(0,(n-1)*s) for n,s in zip(v.shape,strides))
    a=np.ndarray(v.shape,dtype=v.dtype,buffer=np.zeros(hi-lo+v.itemsize,np.uint8),offset=-lo,strides=strides);a[...]=v;return a
def numerical(a,b,k,t):
    v=np.einsum('zg,zh,gha->za',a,b,k,optimize=True)
    outer=v[:,:,None]*v[:,None,:].conj()
    return v,(outer[1:]+outer[:-1]).sum(axis=0)*t/(2*(len(a)-1))
def batched(a,b,k,t):
    ab=(a[:,:,None]*b[:,None,:]).reshape(len(a),-1)
    matrix=k[None,...].transpose(1,2,0,3).reshape(ab.shape[1],-1)
    v=(ab@matrix).reshape(len(a),1,3).transpose(1,0,2)
    outer=v[:,:,:,None]*v[:,:,None,:].conj()
    return v[0],((outer[:,1:]+outer[:,:-1]).sum(axis=1)*t/(2*(len(a)-1)))[0]
def decimal_response(a,b,k,t):
    # Exact complex products/sums on the input binary64 numbers, at 80 digits.
    with localcontext() as ctx:
        ctx.prec=80
        v=[];absolute=[]
        for z in range(len(a)):
            row=[];bound=[]
            for c in range(3):
                value=ZERO;s=Decimal(0)
                for g in range(a.shape[1]):
                    for h in range(b.shape[1]):
                        x,y,w=C(a[z,g]),C(b[z,h]),C(k[g,h,c]);value=add(value,mul(mul(x,y),w))
                        # Sum of magnitudes of all eight real expanded terms.
                        s+=(abs(x[0])+abs(x[1]))*(abs(y[0])+abs(y[1]))*(abs(w[0])+abs(w[1]))
                row.append(value);bound.append(float(s))
            v.append(row);absolute.append(bound)
        result=[];scale=D(t)/Decimal(2*(len(a)-1))
        for i in range(3):
            row=[]
            for j in range(3):
                s=ZERO
                for z in range(len(a)-1):s=add(s,add(mul(v[z][i],conj(v[z][j])),mul(v[z+1][i],conj(v[z+1][j]))))
                row.append((s[0]*scale,s[1]*scale))
            result.append(row)
        vr=np.array([[complex(float(x[0]),float(x[1])) for x in row] for row in v])
        rr=np.array([[complex(float(x[0]),float(x[1])) for x in row] for row in result])
        return vr,rr,np.array(absolute),[[[str(x[0]),str(x[1])] for x in row] for row in result]

case_rows=[];array_rows=[]
for case in ('a1','a2','a3','b1','c1','c2'):
    first=case+'-r1'+('-fixed' if case=='b1' else '')
    d=json.loads((ROOT/(first+'-capture')/'capture.json').read_text());a=np.load(ROOT/(first+'-capture')/'observed_arrays.npz');b=np.load(ROOT/(case+'-r2-capture')/'observed_arrays.npz')
    keys=[k for k in a.files if k.startswith(('current','reference','assertion'))]
    identical=all(a[k].dtype==b[k].dtype and a[k].shape==b[k].shape and a[k].tobytes()==b[k].tobytes() for k in keys)
    rows=[]
    for key in a.files:
        if not key.startswith('current'):continue
        ref=key.replace('current','reference',1)
        if case=='b1':ref=ref.replace('reference/spectra/','reference/')
        if ref in a:
            row=dict(case=case,array=key,**metrics(a[key],a[ref]));rows.append(row);array_rows.append(row)
    case_rows.append(dict(case=case,repeat_bitwise=identical,arrays_compared=len(rows),different_arrays=sum(not r['value_equal'] for r in rows),assertion=d['original_assertion']))
(OUT/'error_distributions.json').write_text(json.dumps(dict(cases=case_rows,arrays=array_rows),indent=2,default=plain)+'\n',encoding='utf-8')
with (OUT/'array_errors.csv').open('w',newline='',encoding='utf-8') as f:
    fields=['case','array','shape','actual_dtype','size','differing_elements','differing_fraction','max_absolute','max_relative','max_component_ulp','normwise_relative','bitwise_equal']
    w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(array_rows)

rounding=[]
for case in ('a1','a2','c1'):
    folder=ROOT/(case+'-layout-capture');d=json.loads((folder/'capture.json').read_text());v=np.load(folder/'observed_arrays.npz')
    new=next(x for x in d['operations'] if x['module']=='emcd_sim.double_channeling' and x['function']=='_numerical_site_responses')
    old=next(x for x in d['operations'] if x['module']!='emcd_sim.double_channeling' and x['function']=='depth_response')
    def get(op,name):return restore(v[op['prefix']+'/'+name],op['layouts'][name])
    ao,bo,ko=get(old,'a'),get(old,'b'),get(old,'k');an,bn,kn=get(new,'a'),get(new,'b'),get(new,'kernel');t=old['thickness_nm']
    assert np.array_equal(ao,an) and np.array_equal(ko,kn)
    vo,ro=numerical(ao,bo,ko,t);vn,rn=batched(an,bn,kn,t)
    vf,rf=batched(ao,bo,ko,t)
    vref,rref,absolute,exact=decimal_response(ao,bo,ko,t)
    amplitude_bound=gamma(4*ao.shape[1]*bo.shape[1]+8)*absolute
    # Conservative complex dot bound; four expanded real products per component,
    # two real multiplications per term, arbitrary linear summation/reassociation.
    row=dict(case=case,energy_ev=old['energy_ev'],query=old['query'],depth=len(ao),ni=ao.shape[1],no=bo.shape[1],
        original_operands_identical=dict(a=np.array_equal(ao,an),b=np.array_equal(bo,bn),kernel=np.array_equal(ko,kn)),
        field_difference=metrics(bn,bo),old_replay=metrics(ro,v[old['prefix']+'/returned']),
        new_replay=metrics(rn,v[new['prefix']+'/returned'][0]),
        contraction_only_change=metrics(rf,ro),field_only_change=metrics(numerical(an,bn,kn,t)[1],ro),
        old_vs_decimal=metrics(ro,rref),fixed_input_batch_vs_decimal=metrics(rf,rref),
        old_amplitude_error=float(np.max(abs(vo-vref))),new_fixed_input_amplitude_error=float(np.max(abs(vf-vref))),
        amplitude_bound_max=float(amplitude_bound.max()),amplitude_within_bound=bool(np.all(abs(vo-vref)<=np.sqrt(2)*amplitude_bound)&np.all(abs(vf-vref)<=np.sqrt(2)*amplitude_bound)),
        old_hermitian_residual=float(np.max(abs(ro-ro.conj().T))),new_hermitian_residual=float(np.max(abs(rn-rn.conj().T))),
        old_psd_eigenvalues=np.linalg.eigvalsh((ro+ro.conj().T)/2).tolist(),new_psd_eigenvalues=np.linalg.eigvalsh((rn+rn.conj().T)/2).tolist(),
        old_response_norm=float(np.linalg.norm(ro)),new_response_norm=float(np.linalg.norm(rn)),decimal_response=exact)
    rounding.append(row);print('ARITHMETIC',case,'oldReplay',row['old_replay']['bitwise_equal'],'newReplay',row['new_replay']['bitwise_equal'],'dotBound',row['amplitude_within_bound'],'Rerrors',row['old_vs_decimal']['max_absolute'],row['fixed_input_batch_vs_decimal']['max_absolute'],flush=True)
(OUT/'contraction_precision.json').write_text(json.dumps(rounding,indent=2,default=plain)+'\n',encoding='utf-8')

# Independent linear-form evaluation from observed per-group pixel intensities.
folder=ROOT/'b1-pixel-reduction-capture';d=json.loads((folder/'capture.json').read_text());v=np.load(folder/'observed_arrays.npz')
ops=[x for x in d['operations'] if x['function']=='integrate_detector_block']
assert len(ops)==4
total,weighted,up,down=ops
q=v[total['prefix']+'/qx'];dq2=(q[0,1]-q[0,0])**2
mask=v[total['prefix']+'/support'];weights={k:v[total['prefix']+'/weights/'+k].ravel()[mask] for k in ('A','B')}
def exact_forms(raw):
    ap,bp,am,bm=[raw[k] for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')]
    na,nb,ma,mb=(ap+am)/2,(bp+bm)/2,(ap-am)/2,(bp-bm)/2
    return dict(**raw,N_A=na,N_B=nb,M_A=ma,M_B=mb,D_mag=ma-mb,D_nonmag=na-nb,D_raw=ap-bp,Sigma_ref=na+nb)
cr=[]
with localcontext() as ctx:
    ctx.prec=80
    for ie in range(2):
        group_raw=[]
        for op in (up,down):
            raw={}
            for det in ('A','B'):
                for state in ('plus','minus'):
                    pixel=v[op['prefix']+'/raw/'+state][ie]
                    raw[f'I_{det}_{state}']=sum((D(x)*D(w) for x,w in zip(pixel,weights[det])),Decimal(0))*D(dq2)
            group_raw.append(raw)
        raw={key:sum(g[key] for g in group_raw)/2 for key in group_raw[0]}
        ideal=exact_forms(raw)
        current={key:D(v['current/spectra/'+key][ie]) for key in ideal}
        group_parity={key:sum(D(v['current/groups/'+g+'/spectra/'+key][ie]) for g in ('up','down'))/2 for key in ideal}
        current_given_raw=exact_forms({k:current[k] for k in raw})
        for key,target in ideal.items():
            actual=current[key];expected=group_parity[key]
            if key in raw:scale=abs(raw[key])
            elif key in ('M_A','N_A'):scale=(abs(raw['I_A_plus'])+abs(raw['I_A_minus']))/2
            elif key in ('M_B','N_B'):scale=(abs(raw['I_B_plus'])+abs(raw['I_B_minus']))/2
            else:scale=sum(abs(x) for x in raw.values())/2
            bound=gamma(2*q.size+2*len(group_raw)+10)*float(scale)
            cr.append(dict(energy_index=ie,key=key,actual=float(actual),weighted_group=float(expected),
                exact_pixel_reduction=str(target),actual_error_from_exact=str(actual-target),group_error_from_exact=str(expected-target),
                raw_order_contribution=str(current_given_raw[key]-target),postprocess_rounding=str(actual-current_given_raw[key]),
                absolute_difference=float(abs(actual-expected)),relative_difference=float(abs((actual-expected)/expected)) if expected else None,
                original_allowed=1e-18+3e-13*float(abs(expected)),original_residual=float(abs(actual-expected))-(1e-18+3e-13*float(abs(expected))),
                parent_scale=float(scale),cancellation_condition=float(scale/abs(target)) if target else None,
                propagated_roundoff_bound=bound,within_propagated_bound=bool(float(abs(actual-expected))<=bound),
                current_normalized_by_sigma=str(actual/ideal['Sigma_ref']),ideal_normalized_by_sigma=str(target/ideal['Sigma_ref'])))
(OUT/'cr_conditioning.json').write_text(json.dumps(dict(grid_points=int(q.size),supported_points=int(mask.sum()),unit_roundoff=U,
    bound_definition='gamma_(2*N+2*G+10) times absolute parent intensity scale; N=full aperture grid, G=groups; positive raw point terms, products/sums, two normalization/reversal paths.',rows=cr),indent=2)+'\n',encoding='utf-8')
for row in cr:
    if row['key'] in ('M_A','M_B','D_mag','Sigma_ref'):print('CR',row['energy_index'],row['key'],'diff',row['absolute_difference'],'condition',row['cancellation_condition'],'bound',row['propagated_roundoff_bound'],'passes',row['within_propagated_bound'],flush=True)
