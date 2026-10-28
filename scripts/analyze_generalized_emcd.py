"""Analyze immutable parent references and new projected EMCD checkpoints."""
from pathlib import Path
from types import SimpleNamespace
import csv,hashlib,json
import numpy as np
from matplotlib.figure import Figure
from emcd_sim.geometry import VirtualDetector
from emcd_sim.gui.project_io import load_project
from emcd_sim.mirror_parity import row_mirror_diagnostics
from emcd_sim.emcd_angular_plots import decorate_reciprocal_map

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/generalized_multislice_emcd_validation'
OLD=ROOT/'outputs/general_zolz_multislice_validation'

def parent(label):
    paths=[p for p in OLD.glob('*/case.json') if json.loads(p.read_text())['rows'][0]['case']==label]
    if len(paths)!=1:raise ValueError('Missing/ambiguous parent '+label)
    p=paths[0];d=json.loads(p.read_text());npz=p.with_name('arrays.npz')
    if hashlib.sha256(npz.read_bytes()).hexdigest()!=d['arrays_sha256']:raise ValueError('Changed immutable reference')
    with np.load(npz,allow_pickle=False) as f:a={k:f[k] for k in f.files}
    return dict(config=SimpleNamespace(**d['identity']['config']),qx=a['qx'],qy=a['qy'],
        methods={method:dict(maps={edge:{k:a[method+'__'+edge+'__'+k] for k in ('I_plus','I_minus','I_mag','I_nonmag')} for edge in ('L3','L2')}) for method in ('bloch','fft-multislice')})

def reintegrate(r,subpixels):
    cfg=r['config'];qx,qy=r['qx'],r['qy'];dq2=float(qx[0,1]-qx[0,0])**2
    weights=[VirtualDetector(tuple(p),cfg.radius).integration_weights(qx,qy,mode='fractional',subpixels=subpixels) for p in cfg.centers]
    rows=[]
    for method,m in r['methods'].items():
        for edge,fields in m['maps'].items():
            raw=np.array([[np.sum(fields['I_'+sign]*w)*dq2 for w in weights] for sign in ('plus','minus')])
            ap,bp,am,bm=raw.ravel();na,nb=(ap+am)/2,(bp+bm)/2;ma,mb=(ap-am)/2,(bp-bm)/2
            rows.append(dict(method=method,edge=edge,I_A_plus=ap,I_B_plus=bp,I_A_minus=am,I_B_minus=bm,
                D_mag=ma-mb,D_nonmag=na-nb,Sigma_ref=na+nb,prb_pp=100*(ap-bp)/(ap+bp),magnetic_pp=100*(ma-mb)/(na+nb),
                area=float(np.sum(weights[0])*dq2),area_relative_error=float(np.sum(weights[0])*dq2/(np.pi*cfg.radius**2)-1)))
    return rows

def delta(a,b):
    raw=('I_A_plus','I_B_plus','I_A_minus','I_B_minus')
    v=dict(prb_pp=max(abs(x['prb_pp']-y['prb_pp']) for x,y in zip(a,b)),
        magnetic_pp=max(abs(x['magnetic_pp']-y['magnetic_pp']) for x,y in zip(a,b)),
        relative_raw=max(abs(x[k]-y[k])/max(abs(x[k]),abs(y[k])) for x,y in zip(a,b) for k in raw))
    v['pass']=bool(max(v['prb_pp'],v['magnetic_pp'])<=.01 and v['relative_raw']<=.001)
    return v

def main():
    samples={17:parent('111_double'),33:parent('111_angular')}
    for n in (65,97):samples[n]=load_project(OUT/f'cases/111_grid{n}/project')
    rows=[]
    for n,r in samples.items():
        for sub in (32,64,128,256):rows.extend(dict(grid=n,subpixels=sub,**v) for v in reintegrate(r,sub))
    with (OUT/'quadrature.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    np.savez_compressed(OUT/'quadrature.npz',**{k:np.array([r[k] for r in rows]) for k in rows[0]})
    checks={}
    for a,b in ((17,33),(33,65),(65,97)):checks[f'angular_{a}_{b}_sub128']=delta(reintegrate(samples[a],128),reintegrate(samples[b],128))
    for a,b in ((32,64),(64,128),(128,256)):checks[f'aperture_grid97_sub{a}_{b}']=delta(reintegrate(samples[97],a),reintegrate(samples[97],b))
    shared={}
    for n in (33,65,97):
        step=(n-1)//16
        shared[str(n)]=max(float(np.max(abs(m['maps'][e][k][::step,::step]-samples[17]['methods'][method]['maps'][e][k])))
            for method,m in samples[n]['methods'].items() for e in ('L3','L2') for k in ('I_plus','I_minus','I_mag','I_nonmag'))
    joint=load_project(OUT/'cases/111_joint/project')
    checks['joint_vs_grid65']=delta(reintegrate(samples[65],128),reintegrate(joint,128))
    matched={}
    for label,r in [('111_grid65',samples[65]),('111_grid97',samples[97]),('111_joint',joint)]:
        vals=reintegrate(r,128);matched[label]=delta(vals[:2],vals[2:])
    legacy_path=next((ROOT/'outputs/ni_117_emcd_validation/cases').glob('baseline_full_double_t8_*/arrays.npz'))
    legacy=load_project(OUT/'cases/117_legacy_t8/project');parity={};differences={}
    with np.load(legacy_path,allow_pickle=False) as f:
        for method,m in legacy['methods'].items():
            differences[method]={k:float(np.max(abs(m[k]-f[method+'__'+k]))) for k in ('amplitudes','coherence')}
            differences[method]['raw_map_max_abs']=max(float(np.max(abs(fields[k]-f[method+'__'+edge+'__'+k]))) for edge,fields in m['maps'].items() for k in ('I_plus','I_minus','I_mag','I_nonmag'))
            differences[method]['spectra_max_abs']=max(float(np.max(abs(v-f[method+'__spectrum__'+k]))) for k,v in m['spectra'].items() if method+'__spectrum__'+k in f.files)
            parity[method]={e:row_mirror_diagnostics(m['qx'],m['qy'],{k:m['maps'][e][k] for k in ('I_mag','I_nonmag','I_plus')})[0] for e in ('L3','L2')}
    outgoing={};outgoing_raw={}
    for p in (OUT/'outgoing').glob('*.npz'):
        with np.load(p,allow_pickle=False) as f:
            outgoing_raw[p.stem]={k:f[k] for k in f.files if k.endswith('_raw')}
        d=outgoing_raw[p.stem];outgoing[p.stem]=dict(relative_raw=max(float(np.max(abs(d[f'bloch_{i}_raw']-d[f'fft-multislice_{i}_raw'])/np.maximum(abs(d[f'bloch_{i}_raw']),abs(d[f'fft-multislice_{i}_raw'])))) for i in (0,1)))
    for label,d in outgoing_raw.items():
        base=outgoing_raw['in2.6_out2.6'];outgoing[label]['point_support_sensitivity_relative']=max(float(np.max(abs(d[k]-base[k])/np.maximum(abs(d[k]),abs(base[k])))) for k in d)
        def point_rows(data):
            rows=[]
            for method in ('bloch','fft-multislice'):
                for ie in (0,1):
                    raw=data[f'{method}_{ie}_raw']
                    for pair in (0,1):
                        ap,bp=raw[0,2*pair:2*pair+2];am,bm=raw[1,2*pair:2*pair+2]
                        n=(ap+bp+am+bm)/2;m=(ap-am-bp+bm)/2
                        rows.append(dict(I_A_plus=ap,I_B_plus=bp,I_A_minus=am,I_B_minus=bm,prb_pp=100*(ap-bp)/(ap+bp),magnetic_pp=100*m/n))
            return rows
        values=point_rows(d);outgoing[label]['bw_ms_point_check']=delta(values[:4],values[4:])
        outgoing[label]['support_point_check']=delta(point_rows(base),values)
    summary=dict(thresholds=dict(dichroism_pp=.01,relative_raw=.001),checks=checks,bw_ms=matched,
        shared_point_map_max_abs=shared,legacy_117_max_differences=differences,legacy_117_raw_parity=parity,outgoing_point_controls=outgoing,
        conclusion='Representative quadrature/support checks, not universal orientation or thickness convergence; retained failures must be reviewed')
    (OUT/'analysis.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    fig=Figure(figsize=(12,8),layout='constrained');axes=fig.subplots(2,2)
    for i,method in enumerate(('bloch','fft-multislice')):
        for edge,style in [('L3','-o'),('L2','--s')]:
            for key,ax in [('prb_pp',axes[0,i])]:
                ax.plot(list(samples),[next(v[key] for v in reintegrate(r,128) if v['method']==method and v['edge']==edge) for r in samples.values()],style,label=edge)
        axes[0,i].set(xlabel='Angular grid dimension',ylabel='Raw +M PRB dichroism (%)',title=method+' [111], 2 nm; 128 boundary subpixels');axes[0,i].legend()
    for sub in (32,128,256):axes[1,0].plot(list(samples),[abs(next(v['area_relative_error'] for v in rows if v['grid']==n and v['subpixels']==sub))*100 for n in samples],'-o',label=str(sub)+' subpixels')
    axes[1,0].set(xlabel='Angular grid dimension',ylabel='Absolute circle-area error (%)',yscale='log');axes[1,0].legend()
    r=legacy['methods']['fft-multislice'];m=r['maps']['L3']['I_mag'];even=(m+m[::-1])/2
    h=1+float(r['qx'][0,1]-r['qx'][0,0])/2;extent=(-h,h,-h,h)
    ax=axes[1,1];lim=float(np.max(abs(even)));im=ax.imshow(even,extent=extent,origin='lower',cmap='RdBu_r',vmin=-lim,vmax=lim)
    decorate_reciprocal_map(ax,r['model'],extent,zone_axis=r['settings'].zone,target_hkl=r['settings'].target)
    ax.plot(*r['model'].elastic.crystal.g_vector(r['settings'].target)[:2],'s',mfc='none',mec='crimson',ms=7)
    ax.set(title='[117] 8 nm raw magnetic mirror-even component',xlabel='qx (cycles/Å)',ylabel='qy (cycles/Å)');fig.colorbar(im,ax=ax,label='a.u.')
    fig.savefig(OUT/'validation.png',dpi=160);fig.savefig(OUT/'validation.svg')
    # Actual finite-field BW/MS maps, with shared color ranges per component.
    fig=Figure(figsize=(12,6),layout='constrained');axes=fig.subplots(2,3)
    for j,field in enumerate(('I_mag','I_nonmag','I_plus')):
        scale=max(float(np.max(abs(v['maps']['L3'][field]))) for v in samples[97]['methods'].values())
        for i,(method,r) in enumerate(samples[97]['methods'].items()):
            h=1+float(r['qx'][0,1]-r['qx'][0,0])/2;extent=(-h,h,-h,h)
            ax=axes[i,j];v=r['maps']['L3'][field];im=ax.imshow(v,extent=extent,origin='lower',cmap='RdBu_r' if field=='I_mag' else 'viridis',vmin=-scale if field=='I_mag' else 0,vmax=scale)
            decorate_reciprocal_map(ax,r['model'],extent,zone_axis=r['settings'].zone,target_hkl=r['settings'].target);ax.set_title(method+' '+field);fig.colorbar(im,ax=ax)
            ax.plot(*r['model'].elastic.crystal.g_vector(r['settings'].target)[:2],'s',mfc='none',mec='crimson',ms=7)
    fig.suptitle('[111], 2 nm: raw L3 fields on 97×97 grid; crystal M=[001]')
    fig.savefig(OUT/'bw_ms_maps.png',dpi=150);fig.savefig(OUT/'bw_ms_maps.svg')
    from emcd_sim.gui.results import draw_eels
    paths=[p for p in (OUT/'gui').glob('117_double_*/project') if (p.parent/'acceptance.json').exists()]
    if paths:
        demo=load_project(sorted(paths)[-1])
        for mode in ('raw','relative'):
            fig=Figure(figsize=(11,7),layout='constrained');draw_eels(fig,demo,method='overlay',component_mode=mode)
            fig.suptitle('[117] source-GUI workflow demonstration: 0.5 nm, 11 energy samples; quadrature not certified',fontsize=10)
            fig.savefig(OUT/('gui_eels_'+mode+'.png'),dpi=140)
    # Compact cross-method records, explicitly linking reused parent results.
    comparison=[];refs={}
    selected=json.loads((OLD/'summary.json').read_text())['selected']
    for label in selected:
        p=next(p for p in OLD.glob('*/case.json') if json.loads(p.read_text())['rows'][0]['case']==label)
        d=json.loads(p.read_text());comparison.extend(d['rows'])
        refs[label]=dict(status='Reused immutable Milestone-A result; not rerun',case_json=str(p.relative_to(ROOT)),arrays_sha256=d['arrays_sha256'],comparison=d['comparison'])
    for label in ('111_grid65','111_grid97','111_joint','117_legacy_t8'):
        r=load_project(OUT/'cases'/label/'project')
        from emcd_sim.gui.prb_benchmark import benchmark_spectra
        for method,m in r['methods'].items():
            sp=m['spectra'];curves,_=benchmark_spectra(sp)
            for edge,e in [('L3',r['config'].l3),('L2',r['config'].l2)]:
                i=int(np.argmin(abs(sp['energy_ev']-e)))
                row=dict(case=label,method=method,edge=edge,beams=len(m['metadata']['beam_hkl']),
                    prb_pp=float(curves['prb_relative_dichroism_percent'][i]),magnetic_pp=float(curves['magnetic_only_percent'][i]))
                row.update({k:float(sp[k][i]) for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus','D_mag','D_nonmag','Sigma_ref')});comparison.append(row)
    with (OUT/'comparison.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(comparison[0]));w.writeheader();w.writerows(comparison)
    np.savez_compressed(OUT/'comparison.npz',**{k:np.array([r[k] for r in comparison]) for k in comparison[0]})
    (OUT/'reference_reuse.json').write_text(json.dumps(refs,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
