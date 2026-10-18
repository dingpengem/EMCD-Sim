"""Actual GUI forward adapter against fixed-profile CLI checkpoints, no CLI rerun."""
import argparse,csv,hashlib,inspect,json,time
from dataclasses import asdict,replace
from pathlib import Path
import numpy as np
import ni_double_channeling_final_200kv as final
from emcd_sim.gui import emcd_forward as f,propagation,channeling,geometry
from emcd_sim.gui.project_io import save_project,load_project

ROOT=final.ROOT/'gui_validation'


def identity():
    # Display/export edits and the eventual commit do not invalidate physics.
    functions=(f.calculate,f._calculate,f._contract,f.energy_grid,f.tensors,
               propagation.propagate,propagation.numerical_info,geometry.geometry,geometry.elastic_model)
    source=''.join(inspect.getsource(fn) for fn in functions)+Path(channeling.__file__).read_text()
    # Only a diagnostic description was generalized to cover the new row
    # route. Numeric admission and all calculation code remain hash checked.
    source=source.replace('Actual oriented Ni [017] full 2D, or explicitly selected [001] (200) systematic row; exact common hkl, IAM, B and Fourier cutoff as BW',
        'Ni017Geometry; FFT(m,n) -> cubic (m,7n,-n); actual [017] cell and FCC extinctions; same IAM, B and Fourier cutoff as BW')
    # This variable is passed only to the historical metadata scalar. The
    # authoritative admission estimate above was already model-specific.
    source=source.replace("    memory=info['dense_working_estimate_mib']\n",'')
    return hashlib.sha256(source.encode()).hexdigest()


def configuration(zone,t,model):
    s=geometry.Settings(zone=(0,0,1) if zone=='001' else (0,1,7),tilt=(-7.116725439974256,35. if zone=='001' else 0.),
        thickness=t,beam_cutoff=4.6,potential_cutoff=6.2)
    provenance=json.loads((final.ROOT/'provenance.json').read_text())
    cfg=f.ForwardSettings(axis_declared=True,source_sha256=provenance['source_sha256'],l3=831.4778,l2=848.698,
        propagation='both',channeling_model=model,systematic_row=zone=='001',energy_scope='edges',angular_maps=False,
        grid=193,halfwidth=.5,depth=257,fft_grid=48,subpixels=64,slice_step=.04,correction=False)
    return s,cfg


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--example',action='store_true');args=parser.parse_args()
    assert json.loads((final.ROOT/'checkpoint_A.json').read_text())['checkpoint_A_passed']
    ROOT.mkdir(parents=True,exist_ok=True)
    with np.load(final.ROOT/'results.npz',allow_pickle=False) as a:
        reference={tuple(k):raw for k,raw in zip(json.loads(str(a['keys_json'])),a['raw'])}
    rows=[];solver_rows=[];fingerprint=identity()
    for zone in ('001','017'):
        for t in (8.,12.,30.):
            for im,model in enumerate(('single','double')):
                s,cfg=configuration(zone,t,model)
                params=dict(settings=asdict(s),config=asdict(cfg),adapter_sha256=fingerprint,
                    cores={p:final.study.base.digest(p) for p in final.study.base.CORE})
                path=ROOT/f'{zone}_{int(t):03}_{model}.npz'
                def producer():
                    result=f.calculate(geometry.Structure.nickel(),s,cfg,lambda stage:print(f'{zone} {t:g} {model}: {stage}',flush=True))
                    return dict(raw=np.stack([np.column_stack([result['methods'][m]['spectra'][k] for k in
                        ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')]) for m in ('bloch','fft-multislice')]))
                data=final.study.base.cached(path,params,producer)
                oa,ob=[final.study.base.study.base.observables(v) for v in data['raw']]
                for j,edge in enumerate(('L3','L2')):
                    a,b=data['raw'][:,j,:]
                    solver_rows.append(dict(zone=zone,thickness_nm=t,channeling_model=model,edge=edge,
                        raw_relative=float(np.max(abs(a-b)/np.maximum(abs(a),abs(b)))),
                        prb_difference_pp=float(ob['prb_relative_dichroism_percent'][j]-oa['prb_relative_dichroism_percent'][j]),
                        D_mag_difference=float(ob['D_mag'][j]-oa['D_mag'][j]),D_nonmag_difference=float(ob['D_even'][j]-oa['D_even'][j])))
                for ie,engine in enumerate(('bw','ms')):
                    a,b=reference[zone,t,engine][im],data['raw'][ie]
                    oa,ob=[final.study.base.study.base.observables(v) for v in (a,b)]
                    for j,edge in enumerate(('L3','L2')):
                        rows.append(dict(zone=zone,thickness_nm=t,channeling_model=model,solver=engine,edge=edge,
                            raw_relative=float(np.max(abs(a[j]-b[j])/np.maximum(abs(a[j]),abs(b[j])))),
                            D_mag_absolute=float(abs(oa['D_mag'][j]-ob['D_mag'][j])),
                            D_nonmag_absolute=float(abs(oa['D_even'][j]-ob['D_even'][j])),
                            prb_difference_pp=float(ob['prb_relative_dichroism_percent'][j]-oa['prb_relative_dichroism_percent'][j])))
                final.study.base.study.base.write_csv(ROOT/'reference_comparison.csv',rows)
                print(f'GUI checkpoint saved: {zone} {t:g} {model}',flush=True)
    final.study.base.study.base.write_csv(ROOT/'gui_bw_ms_comparison.csv',solver_rows)
    status=dict(checkpoint_B_passed=all(r['raw_relative']<=.001 and abs(r['prb_difference_pp'])<=.01 for r in rows+solver_rows),
        adapter_sha256=fingerprint,comparisons=len(rows),max_raw_relative=max(r['raw_relative'] for r in rows),
        max_prb_difference_pp=max(abs(r['prb_difference_pp']) for r in rows),
        max_gui_bw_ms_prb_pp=max(abs(r['prb_difference_pp']) for r in solver_rows),
        coverage='Actual GUI calculate, Both x Single/Double, [001]/[017], 8/12/30 nm, both fixed native edges; unchanged CLI checkpoints')
    final.study.base.study.base.write_json(ROOT/'checkpoint_B.json',status)
    print(json.dumps(status),flush=True)
    if not status['checkpoint_B_passed']:raise RuntimeError('GUI raw-reference validation failed')
    if args.example:
        path=ROOT/'native_eels_017_single_bw'
        s,cfg=configuration('017',8.,'single');cfg=replace(cfg,energy_scope='full',propagation='bloch')
        if not path.exists():
            result=f.calculate(geometry.Structure.nickel(),s,cfg,lambda stage:print(stage,flush=True))
            save_project(result,path)
        saved=load_project(path)
        if saved['settings']!=s or saved['config']!=cfg:raise ValueError('Full-spectrum example provenance mismatch')
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from emcd_sim.gui.results import draw_eels
        from emcd_sim.gui.prb_benchmark import benchmark_spectra
        fig=Figure(figsize=(10,7),layout='constrained');FigureCanvasAgg(fig);draw_eels(fig,saved)
        for ext in ('png','svg'):fig.savefig(final.ROOT/('representative_eels.'+ext),dpi=180)
        spectra=dict(saved['spectra'],**benchmark_spectra(saved['spectra'])[0])
        with (final.ROOT/'representative_eels.csv').open('w',newline='',encoding='utf-8') as stream:
            writer=csv.writer(stream);writer.writerow(['solver','channeling_model']+list(spectra))
            writer.writerows(('bloch','single',*row) for row in zip(*spectra.values()))
        print('Genuine native-grid EELS example:',path,flush=True)


if __name__=='__main__':main()
