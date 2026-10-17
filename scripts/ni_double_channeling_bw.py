"""Four-point Ni BW double-channel benchmark; no previous outputs are modified."""
import argparse
from dataclasses import replace, asdict
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import ni_prb2007_geometry_validation as study
from emcd_sim.double_channeling import double_channeling_response, intensities_from_response
from emcd_sim.elastic import BeamSet

ROOT=Path('outputs/ni_double_channeling_bw')
ENERGIES=study.base.ENERGIES


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def calculate(context, detector, thickness, outgoing_beams=None):
    raw=np.zeros((2,4))
    for ie,e in enumerate(ENERGIES):
        response=double_channeling_response(context['model'].elastic,float(e),
            np.column_stack((detector.x,detector.y)),thickness,outgoing_beams=outgoing_beams)
        for rev in range(2):
            values=intensities_from_response(response,context['ts'][rev].tensor_angstrom2_per_ev[ie])
            assert values.min()>=-1e-12*max(float(abs(values).max()),1e-30)
            raw[ie,2*rev:2*rev+2]=np.einsum('dp,p->d',detector.w[0],values)*detector.dq2
    return raw


def rows_for(raw,t,method):
    obs=study.base.observables(raw)
    return [dict(method=method,thickness_nm=t,edge=edge,energy_ev=float(ENERGIES[i]),
        **{k:float(v[i]) for k,v in obs.items()}) for i,edge in enumerate(('L3','L2'))]


def main():
    ROOT.mkdir(exist_ok=True,parents=True)
    preserved=study.base.file_hashes(Path('outputs/ni_voltage_dependence_100_200_300kv'))
    saved=study.base.load_project('outputs/gui_stage_d/windows_20261016/reference_project')
    c=study.make_context(saved,(0,0,1),2048,systematic_row=True)
    assert digest(saved['config'].source)==saved['config'].source_sha256
    detector=study.DetectorGrid(c['centers'],(c['cfg'].radius,),193,.5,64)
    metadata=dict(base_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        source_sha256=saved['config'].source_sha256,settings=asdict(c['settings']),
        config=asdict(c['cfg']),hkl=c['hkl'],s_angstrom_inv=c['s'],energies_ev=ENERGIES,
        grid=193,halfwidth_cycles_angstrom=.5,subpixels=64,integration='fractional',
        detector_centers=c['centers'],detector_areas=detector.areas,
        method='finite-ZOLZ Bloch incoming+outgoing, analytic continuous-depth integral',
        memory_budget_mib=2048,postedge_normalized=False,
        python=study.base.platform.python_version(),numpy=np.__version__,
        implementation_sha256={str(p):digest(p) for p in
            (Path(__file__),Path('src/emcd_sim/double_channeling.py'),Path('src/emcd_sim/physical_elastic.py'),
             Path('src/emcd_sim/single_channeling_tensor.py'),Path('src/emcd_sim/xmcd_effective_mdff.py'))})
    study.base.write_json(ROOT/'configuration.json',metadata)
    rows=[];arrays={};differences=[]
    for t in (10.,12.,20.,30.):
        entrance=study.contract_detectors(c,study.analytic_bw_coherence(c['model'].elastic,t),t,detector)[0]
        double=calculate(c,detector,t)
        arrays[f'entrance_t{int(t)}']=entrance;arrays[f'double_t{int(t)}']=double
        for method,raw in (('entrance_only',entrance),('double_channeling',double)):
            rows.extend(rows_for(raw,t,method))
        a,b=study.base.observables(entrance),study.base.observables(double)
        for i,edge in enumerate(('L3','L2')):
            differences.append(dict(thickness_nm=t,edge=edge,
                **{k+'_double_minus_entrance':float(b[k][i]-a[k][i]) for k in a}))
        np.savez_compressed(ROOT/f't{int(t):02d}.npz',entrance=entrance,double=double,
            energies_ev=ENERGIES,thickness_nm=t,configuration_json=json.dumps(study.base.clean(metadata)))
        print(f'{t:g} nm: entrance {a["prb_relative_dichroism_percent"]}, double {b["prb_relative_dichroism_percent"]}',flush=True)
    study.base.write_csv(ROOT/'results.csv',rows)
    study.base.write_csv(ROOT/'differences.csv',differences)
    # Independent basis expansions at one representative point, both reversal states/edges.
    controls=[];baseline=arrays['double_t12']
    for ni,no in ((9,11),(11,9),(13,11),(11,13),(13,13)):
        basis=lambda n: BeamSet(tuple([(0,0,0)]+[(s*2*j,0,0) for j in range(1,(n-1)//2+1) for s in (1,-1)]))
        ci=dict(c,model=replace(c['model'],elastic=replace(c['model'].elastic,beams=basis(ni))))
        raw=calculate(ci,detector,12.,basis(no))
        arrays[f'basis_{ni}_{no}']=raw
        controls.append(dict(control='beam_basis',incoming_beams=ni,outgoing_beams=no,
            grid=193,max_raw_relative_change=float(np.max(abs(raw-baseline)/abs(baseline))),
            max_D_PRB_change_pp=float(np.max(abs(study.base.observables(raw)['prb_relative_dichroism_percent']-
                                                study.base.observables(baseline)['prb_relative_dichroism_percent'])))))
        print(f'Basis {ni}/{no}: {controls[-1]}',flush=True)
    fine=study.DetectorGrid(c['centers'],(c['cfg'].radius,),385,.5,64)
    raw=calculate(c,fine,12.)
    arrays['grid385_t12']=raw
    controls.append(dict(control='detector_grid',incoming_beams=11,outgoing_beams=11,grid=385,
        max_raw_relative_change=float(np.max(abs(raw-baseline)/abs(baseline))),
        max_D_PRB_change_pp=float(np.max(abs(study.base.observables(raw)['prb_relative_dichroism_percent']-
                                            study.base.observables(baseline)['prb_relative_dichroism_percent'])))))
    # Compare the underlying complex Cartesian matrices, not percentages, at A/B centers.
    depth=[]
    for energy in ENERGIES:
        exact=double_channeling_response(c['model'].elastic,float(energy),c['centers'],12.)
        arrays[f'response_analytic_{energy}']=exact
        for n in (257,513,1025):
            numerical=double_channeling_response(c['model'].elastic,float(energy),c['centers'],12.,
                method='numerical',depth_steps=n)
            arrays[f'response_depth{n}_{energy}']=numerical
            depth.append(dict(energy_ev=float(energy),depth_steps=n,
                relative_complex_response_error=float(np.linalg.norm(numerical-exact)/np.linalg.norm(exact))))
    np.savez_compressed(ROOT/'results.npz',**arrays,configuration_json=json.dumps(study.base.clean(metadata)))
    study.base.write_csv(ROOT/'convergence.csv',controls)
    study.base.write_csv(ROOT/'depth_convergence.csv',depth)
    fig=Figure(figsize=(9,4));FigureCanvasAgg(fig)
    for i,edge in enumerate(('L3','L2')):
        ax=fig.add_subplot(1,2,i+1)
        for method,style in (('entrance_only','o-'),('double_channeling','s--')):
            r=[v for v in rows if v['method']==method and v['edge']==edge]
            ax.plot([v['thickness_nm'] for v in r],[v['prb_relative_dichroism_percent'] for v in r],style,label=method)
        ax.set(xlabel='Thickness (nm)',ylabel='Signed PRB dichroism (%)',title=edge)
        ax.axhline(0,color='gray',lw=.5);ax.legend(fontsize=8)
    fig.tight_layout()
    from io import BytesIO
    for ext in ('png','svg'):
        buffer=BytesIO();fig.savefig(buffer,format=ext,dpi=180);(ROOT/f'comparison.{ext}').write_bytes(buffer.getvalue())
    assert study.base.file_hashes(Path('outputs/ni_voltage_dependence_100_200_300kv'))==preserved
    assert digest(saved['config'].source)==saved['config'].source_sha256
    study.base.write_json(ROOT/'preservation.json',dict(previous_voltage_results_unchanged=True,
        source_unchanged=True,reference_hashes=preserved))
    print('Completed four-point benchmark and independent raw/complex-response controls.',flush=True)


if __name__=='__main__':main()
