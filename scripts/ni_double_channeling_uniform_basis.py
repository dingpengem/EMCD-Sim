"""Resumable matched-basis validation; reuse prior physics checkpoints read-only."""
import argparse,json,subprocess
from pathlib import Path
import numpy as np
import ni_double_channeling_cutoff_study as study

ROOT=Path('outputs/ni_double_channeling_uniform_basis_validation')
PRIOR=study.ROOT


def case(zone,t,basis,engine):
    tag=f'{zone}_{engine}_t{int(t):03}_p6.2_b{basis:g}_o{basis:g}_f48_d257_s0.04.npz'
    old=PRIOR/'checkpoints'/tag
    if old.exists():
        return study.run_case(zone,t,basis=basis,which=engine)
    previous=study.ROOT
    try:
        study.ROOT=ROOT
        return study.run_case(zone,t,basis=basis,which=engine)
    finally:
        study.ROOT=previous


def support():
    rows=[]
    for zone in ('001','017'):
        for basis in (3.8,4.6,5.4):
            c=study.context(zone,6.2,basis)
            grid=study.ProjectedNiFFT.build(c['model'].elastic,grid_points=48,
                potential_cutoff=6.2,systematic_row=c['systematic_row'],
                row_reduction=c['systematic_row'],projected_geometry=c['projected_geometry'])
            idx=grid.indices(c['hkl'])
            np.testing.assert_allclose(grid.g[idx],c['g'],atol=1e-12,rtol=0)
            n=len(idx);dense=80*n**4/2**20
            rows.append(dict(zone=zone,basis=basis,incoming_beams=n,outgoing_beams=n,
                fft_samples=grid.potential.size,matched_support=True,dense_kernel_mib=dense,
                dense_alone_within_2048_mib=dense<=2048))
    return rows


def passed(rows):
    return bool(rows) and all(abs(r['prb_change_pp'])<=.01 and r['raw_relative']<=.001 for r in rows)


def summarize(records):
    observations=[];comparisons=[]
    for (zone,t,basis,engine),(path,data,params) in records.items():
        for im,channel in enumerate(('entrance','double')):
            for r in study.base.rows_for(data['raw'][im],t,engine):
                observations.append(dict(zone=zone,basis=basis,channel=channel,checkpoint=str(path),**r))
    def compare(category,zone,t,label,a,b):
        for name,m in study.comparison(a['raw'],b['raw']).items():
            channel,edge=name.split('_')
            im=('entrance','double').index(channel);ie=('L3','L2').index(edge)
            oa=study.base.study.base.observables(a['raw'][im]);ob=study.base.study.base.observables(b['raw'][im])
            comparisons.append(dict(category=category,zone=zone,thickness_nm=t,label=label,
                channel=channel,edge=edge,D_even_change=float(ob['D_even'][ie]-oa['D_even'][ie]),
                reversal_even_imbalance_change_pp=float(100*(ob['D_even'][ie]/ob['diagnostic_denominator'][ie]-oa['D_even'][ie]/oa['diagnostic_denominator'][ie])),**m))
    points=sorted(set(k[1] for k in records))
    for zone in ('001','017'):
        for t in points:
            for basis in (3.8,4.6):
                compare('BW-MS',zone,t,str(basis),records[zone,t,basis,'bw'][1],records[zone,t,basis,'ms'][1])
            for engine in ('bw','ms'):
                compare('independent_basis',zone,t,engine,records[zone,t,3.8,engine][1],records[zone,t,4.6,engine][1])
    study.base.study.base.write_csv(ROOT/'observables.csv',observations)
    study.base.study.base.write_csv(ROOT/'comparisons.csv',comparisons)
    status={category:dict(passed=passed(rows),max_prb_change_pp=max(abs(r['prb_change_pp']) for r in rows),
        max_raw_relative=max(r['raw_relative'] for r in rows)) for category,rows in
        ((category,[r for r in comparisons if r['category']==category and (category!='BW-MS' or r['label']=='4.6')])
         for category in ('BW-MS','independent_basis'))}
    gate=all(v['passed'] for v in status.values())
    ordering=[]
    for zone in ('001','017'):
        for engine in ('bw','ms'):
            curves={t:[float(study.base.study.base.observables(records[zone,t,4.6,engine][1]['raw'][im])['prb_relative_dichroism_percent'][0]) for im in (0,1)] for t in points}
            ordering.append(dict(zone=zone,engine=engine,
                sampled_entrance_max_nm=max(points,key=lambda t:abs(curves[t][0])),
                sampled_double_max_nm=max(points,key=lambda t:abs(curves[t][1])),
                double_8nm_l3_percent=curves[8.][1]))
    status.update(thicknesses_nm=points,uniform_gate_passed=gate,full_curve_certified=False,
        sampled_ordering=ordering,peak_ordering_preserved=all(r['sampled_entrance_max_nm']==12 and r['sampled_double_max_nm']==8 for r in ordering))
    study.base.study.base.write_json(ROOT/'status.json',status)
    np.savez_compressed(ROOT/'comparison.npz',keys=np.array([json.dumps(k) for k in records]),raw=np.array([v[1]['raw'] for v in records.values()]))
    study.base.study.base.write_json(ROOT/'checkpoint_manifest.json',[
        dict(key=k,path=str(v[0]),sha256=study.base.digest(v[0]),reused=v[0].parent.parent==PRIOR) for k,v in records.items()])
    print(json.dumps(status),flush=True)
    return status


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--include-long',action='store_true');args=parser.parse_args()
    ROOT.mkdir(parents=True,exist_ok=True)
    provenance=ROOT/'provenance.json'
    if not provenance.exists():
        study.base.study.base.write_json(provenance,dict(start_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            prior_output_hashes=study.base.study.base.file_hashes(PRIOR),source_sha256=study.base.digest('data/wien2k_ni/Ni_fm.xmcd'),
            thresholds=study.TOLERANCES,potential_cutoff=6.2,fft=48,depth=257,step_nm=.04,memory_budget_mib=2048))
    study.base.study.base.write_json(ROOT/'support.json',support())
    records={}
    for t in (8.,12.,30.):
        for zone in ('001','017'):
            for basis in (3.8,4.6):
                for engine in ('bw','ms'):records[zone,t,basis,engine]=case(zone,t,basis,engine)
    status=summarize(records)
    if args.include_long and status['uniform_gate_passed']:
        for zone in ('001','017'):
            for basis in (3.8,4.6):
                for engine in ('bw','ms'):records[zone,100.,basis,engine]=case(zone,100.,basis,engine)
        summarize(records)
    original=json.loads(provenance.read_text())
    assert study.base.study.base.file_hashes(PRIOR)==original['prior_output_hashes']
    assert study.base.digest('data/wien2k_ni/Ni_fm.xmcd')==original['source_sha256']


if __name__=='__main__':main()
