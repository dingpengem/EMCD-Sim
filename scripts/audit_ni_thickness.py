"""Read-only production audit and reversal decomposition; never propagates waves."""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

SOURCE = Path('outputs/ni_emcd_asymmetry_thickness_200kv')
OUT = Path('outputs/ni_emcd_thickness_scientific_audit')


def components(raw):
    ap, bp, am, bm = np.moveaxis(np.asarray(raw), -1, 0)
    na, nb = (ap+am)/2, (bp+bm)/2
    ma, mb = (ap-am)/2, (bp-bm)/2
    magnetic, nonmagnetic = ma-mb, na-nb
    total = ap-bp
    np.testing.assert_allclose(total, magnetic+nonmagnetic, rtol=2e-14, atol=1e-16)
    def divide(a, b):
        # Relative numerical floor, no physical intensity rescaling.
        floor = np.finfo(float).eps*32*np.max(np.abs(b))
        return np.divide(a,b,out=np.full_like(a,np.nan),where=np.abs(b)>floor)
    return dict(D_mag=magnetic, D_nonmag=nonmagnetic, D_raw=total,
                A_raw_plus=100*divide(total,ap+bp),
                A_raw_even=100*divide(total,na+nb),
                A_mag=100*divide(magnetic,na+nb),
                A_nonmag=100*divide(nonmagnetic,na+nb),
                R_contam=divide(abs(nonmagnetic),abs(magnetic)))


def main():
    OUT.mkdir(exist_ok=True); figs=OUT/'figures';figs.mkdir(exist_ok=True)
    from emcd_sim.geometry import VirtualDetector
    detector_audit={}
    for zone,p in json.loads((SOURCE/'configuration.json').read_text()).items():
        q=np.linspace(-p['halfwidth'],p['halfwidth'],p['detector_grid']);qx,qy=np.meshgrid(q,q)
        weights=np.array([VirtualDetector(tuple(c),p['radius']).integration_weights(qx,qy,
            mode='fractional',subpixels=p['subpixels']) for c in p['centers']])
        areas=weights.sum(axis=(1,2))*(q[1]-q[0])**2
        np.testing.assert_array_equal(areas,np.asarray(p['areas'])[0])
        np.testing.assert_array_equal(weights[0],weights[1,::-1])
        assert weights.min()>=0 and weights.max()<=1
        detector_audit[zone]=dict(areas=areas.tolist(),integration='sum(weight*intensity)*dq2; no area division')
    (OUT/'detector_audit.json').write_text(json.dumps(detector_audit,indent=2))
    with np.load(SOURCE/'thickness_series.npz',allow_pickle=False) as f:
        keys=json.loads(str(f['keys_json'])); raw=f['raw'].copy()
        np.testing.assert_array_equal(f['energies_ev'],[831.4778,848.698])
    expected={(z,t,e) for z in ('001','017') for t in range(0,101,2) for e in ('bw','ms')}
    assert len(keys)==204 and set(map(tuple,keys))==expected
    assert raw.shape==(204,2,2,4) and raw.dtype==np.float64 and np.isfinite(raw).all() and raw.min()>=0
    lookup={tuple(k):v for k,v in zip(keys,raw)}
    original_hashes={}
    with (SOURCE/'thickness_series.csv').open(newline='') as f: saved=list(csv.DictReader(f))
    assert len(saved)==816
    assert len({(r['zone'],r['solver'],r['channeling_model'],r['edge'],r['thickness_nm']) for r in saved})==816
    profiles={}
    for row in saved:
        key=(row['zone'],int(float(row['thickness_nm'])),row['solver'])
        im=int(row['channeling_model']=='double');ie=('L3','L2').index(row['edge'])
        p=json.loads(row['numerical_configuration_json'])
        assert p['settings']['potential_cutoff']==6.2 and p['settings']['beam_cutoff']==4.6
        assert p['fft_grid']==48 and p['depth_steps']==257 and p['maximum_slice_step_nm']==.04
        assert p['eta']==p['beta']==1 and p['settings']['voltage']==200
        assert p['energies_ev']==[831.4778,848.698] and p['zone']==key[0]
        assert p['thickness_nm']==key[1] and p['engine']==key[2]
        common={n:p[n] for n in ('settings','frame','hkl','outgoing_hkl','tensor','source_sha256',
            'centers','radius','areas','eta','beta','subpixels','detector_grid','depth_steps','fft_grid','maximum_slice_step_nm')}
        profile_key=(key[0],key[1])
        if profile_key in profiles:assert profiles[profile_key]==common
        else:profiles[profile_key]=common
        states=np.array([float(row[n]) for n in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')])
        np.testing.assert_array_equal(states,lookup[key][im,ie])
        path=Path(row['checkpoint'])
        if str(path) not in original_hashes:
            original_hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
            with np.load(path,allow_pickle=False) as f:np.testing.assert_array_equal(f['raw'],lookup[key])
        value=components(states[None,:])
        for name,old in [('D_mag','D_mag'),('D_nonmag','D_nonmag'),('A_raw_plus','emcd_asymmetry_percent')]:
            np.testing.assert_allclose(value[name][0],float(row[old]),rtol=1e-13,atol=1e-15,equal_nan=True)
    rows=[]; extrema=[]; comparisons=[]; brackets=[]
    for z in ('017','001'):
        for solver in ('bw','ms'):
            for im,model in enumerate(('single','double')):
                for ie,edge in enumerate(('L3','L2')):
                    states=np.array([lookup[z,t,solver][im,ie] for t in range(0,101,2)])
                    np.testing.assert_array_equal(states[0],0)
                    c=components(states); ts=np.arange(0,101,2)
                    for i,t in enumerate(ts):
                        rows.append(dict(zone=z,solver=solver,model=model,edge=edge,thickness_nm=int(t),
                            **dict(zip(('I_A_plus','I_B_plus','I_A_minus','I_B_minus'),states[i])),
                            **{k:float(v[i]) for k,v in c.items()}))
                    for name in ('A_raw_plus','A_mag','D_mag','R_contam'):
                        i=int(np.nanargmin(c[name]) if name=='R_contam' else np.nanargmax(abs(c[name])))
                        extrema.append(dict(zone=z,solver=solver,model=model,edge=edge,observable=name,thickness_nm=int(ts[i]),value=float(c[name][i])))
                    for name in ('D_mag','D_nonmag','A_raw_plus'):
                        brackets.append(dict(zone=z,solver=solver,model=model,edge=edge,observable=name,
                            brackets_nm=[[int(ts[i]),int(ts[i+1])] for i in np.flatnonzero(c[name][:-1]*c[name][1:]<0)]))
        for ie,edge in enumerate(('L3','L2')):
            fig=Figure(figsize=(12,9),layout='constrained');FigureCanvasAgg(fig);axes=fig.subplots(2,2).ravel()
            for solver in ('bw','ms'):
                for im,model in enumerate(('single','double')):
                    c=components(np.array([lookup[z,t,solver][im,ie] for t in range(0,101,2)]))
                    kw=dict(color=('C0','C1')[im],ls='-' if solver=='bw' else '--',label=solver.upper()+' '+model,marker='.',ms=3)
                    for ax,name in zip(axes,('D_mag','D_nonmag','A_mag','R_contam')):ax.plot(range(0,101,2),c[name],**kw)
            for ax,label in zip(axes,('Raw magnetic difference (a.u.)','Raw nonmagnetic difference (a.u.)','Magnetic-only asymmetry (%)','|D_nonmag| / |D_mag|')):
                ax.set(xlabel='Thickness (nm)',ylabel=label);ax.axhline(0,color='.5',lw=.6);ax.grid(alpha=.2);ax.legend(fontsize=8)
            fig.suptitle(f'Ni [{z}] {edge} {[831.4778,848.698][ie]} eV | '+('main full finite ZOLZ reference' if z=='017' else 'restricted systematic-row comparison'))
            for ext in ('png','svg'):fig.savefig(figs/f'ni{z}_{edge}_components.{ext}',dpi=160)
            fig=Figure(figsize=(10,7),layout='constrained');FigureCanvasAgg(fig);axes=fig.subplots(2,2).ravel()
            for ax,(solver,im) in zip(axes,[(s,m) for s in ('bw','ms') for m in (0,1)]):
                c=components(np.array([lookup[z,t,solver][im,ie] for t in range(0,101,2)]))
                for name in ('A_raw_even','A_mag','A_nonmag','A_raw_plus'):ax.plot(range(0,101,2),c[name],label=name,ls='--' if name=='A_raw_plus' else '-')
                ax.set(title=solver.upper()+' '+('Single','Double')[im],xlabel='Thickness (nm)',ylabel='Signed asymmetry (%)');ax.axhline(0,color='.5',lw=.6);ax.legend(fontsize=8)
            fig.suptitle(f'Ni [{z}] {edge}: explicit denominators; even-normalized components add')
            for ext in ('png','svg'):fig.savefig(figs/f'ni{z}_{edge}_asymmetries.{ext}',dpi=160)
    for z in ('017','001'):
        for t in range(2,101,2):
            for im,model in enumerate(('single','double')):
                for ie,edge in enumerate(('L3','L2')):
                    b,m=[lookup[z,t,s][im,ie] for s in ('bw','ms')]
                    ab,am=[float(components(v[None,:])['A_raw_plus'][0]) for v in (b,m)]
                    comparisons.append(dict(zone=z,thickness_nm=t,model=model,edge=edge,BW_percent=ab,MS_percent=am,difference_pp=am-ab,
                        raw_relative=float(np.max(abs(b-m)/np.maximum(abs(b),abs(m)))),BW_states=b.tolist(),MS_states=m.tolist()))
    worst=max(comparisons,key=lambda r:abs(r['difference_pp']));worst_raw=max(comparisons,key=lambda r:r['raw_relative'])
    passed=all(abs(r['difference_pp'])<=.01 and r['raw_relative']<=.001 for r in comparisons)
    with (OUT/'components.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    np.savez_compressed(OUT/'components.npz',raw=raw,keys_json=np.array(json.dumps(keys)),rows_json=np.array(json.dumps(rows)),energies_ev=np.array([831.4778,848.698]))
    report=dict(passed=passed,worst_asymmetry=worst,worst_raw=worst_raw,extrema=extrema,sign_brackets=brackets,
        floor='32*float64 epsilon times maximum absolute denominator within each series; undefined is NaN',
        source_sha256=hashlib.sha256((SOURCE/'thickness_series.npz').read_bytes()).hexdigest())
    (OUT/'audit.json').write_text(json.dumps(report,indent=2))
    for path,digest in original_hashes.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
    (OUT/'production_hashes.json').write_text(json.dumps(original_hashes,indent=2))
    assert passed
    print(json.dumps(dict(passed=passed,worst_asymmetry=worst,worst_raw=worst_raw)),flush=True)


if __name__=='__main__':main()
