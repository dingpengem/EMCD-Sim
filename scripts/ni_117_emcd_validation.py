"""Bounded, resumable [117] raw-map parity and numerical-support study.

Run with emcd-python; no GUI, releases or production checkpoint writes.
Every finished Both-method case is atomically checkpointed before continuing.
"""
from dataclasses import asdict, replace
from pathlib import Path
import argparse, csv, hashlib, json, time
import numpy as np
from emcd_sim.study_geometry import StudyGeometry
Ni117Geometry=lambda a_angstrom=3.524: StudyGeometry((1,1,7),(2,-2,0),a_angstrom)
from emcd_sim.gui.geometry import Structure, Settings, geometry, excitation
from emcd_sim.gui.emcd_forward import ForwardSettings, DEFAULT_SOURCE, calculate, metrics
from emcd_sim.mirror_parity import row_mirror_diagnostics

ROOT=Path(__file__).resolve().parents[1]
PHYSICS_FILES=['projected_geometry.py','crystallography.py','projected_potential.py','multislice_double_channeling.py','double_channeling.py',
    'single_channeling_tensor.py','physical_elastic.py','mdff_tensor.py','scattering.py',
    'gui/geometry.py','gui/propagation.py','gui/channeling.py','gui/emcd_forward.py']


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compatible_identity(previous,current,proof):
    """Only permit the explicitly verified input-ownership-only kernel change."""
    previous=json.loads(json.dumps(previous));current=json.loads(json.dumps(current))
    if previous==current:return True
    if not proof.get('bitwise_equal') or proof.get('arrays_compared',0)<52:return False
    old=previous.get('physics_sha256',{});new=current.get('physics_sha256',{})
    if {k for k in old.keys()|new.keys() if old.get(k)!=new.get(k)}!={'multislice_double_channeling.py'}:return False
    if old['multislice_double_channeling.py']!=proof.get('prior_kernel_sha256') or new['multislice_double_channeling.py']!=proof.get('final_kernel_sha256'):return False
    return {k:v for k,v in previous.items() if k!='physics_sha256'}=={k:v for k,v in current.items() if k!='physics_sha256'}


def configurations():
    geo=Ni117Geometry();g=geo.crystal.g_vector((2,-2,0))[0]
    base=Settings(zone=(1,1,7),target=(2,-2,0),tilt=(geo.bragg_tilt(),0),voltage=200,
                  thickness=8,beam_cutoff=3.8,potential_cutoff=6.2)
    cfg=ForwardSettings(axis_declared=True,propagation='both',energy_scope='edges',grid=17,depth=65,
        subpixels=32,fft_grid=32,slice_step=.04,centers=((g/2,g/2),(g/2,-g/2)),radius=.16*g,
        correction=False,worker_mode='manual',parallel_workers=1,source_sha256=sha(DEFAULT_SOURCE))
    cases=[]
    for basis in ('two-beam','full'):
        for channel in ('single','double'):
            for thickness in (8,12,30):
                cases.append((f'baseline_{basis}_{channel}_t{thickness}',replace(base,basis_mode=basis,thickness=thickness),replace(cfg,channeling_model=channel)))
            for dx,dy in ((-.2,0),(.2,0),(0,-.2),(0,.2)):
                cases.append((f'mistilt_{basis}_{channel}_x{dx}_y{dy}',replace(base,basis_mode=basis,tilt=(geo.bragg_tilt()+dx,dy)),replace(cfg,channeling_model=channel)))
    # One factor at a time. The common high-cutoff basis reference is reused.
    ref=replace(base,beam_cutoff=4.6);dc=replace(cfg,channeling_model='double')
    cases.extend([
        ('basis_b4.6_t8',ref,dc),('basis_b5.4_t8',replace(ref,beam_cutoff=5.4),dc),
        ('basis_b4.6_t30',replace(ref,thickness=30),dc),
        ('potential_p4.6',replace(ref,potential_cutoff=4.6),dc),
        ('potential_p5.4',replace(ref,potential_cutoff=5.4),dc),
        ('fft_f24',ref,replace(dc,fft_grid=24)),('fft_f48',ref,replace(dc,fft_grid=48)),
        ('slice_s0.08',ref,replace(dc,slice_step=.08)),('slice_s0.02',ref,replace(dc,slice_step=.02)),
        ('depth_d33',ref,replace(dc,depth=33)),('depth_d129',ref,replace(dc,depth=129)),
        ('depth_d33_fixed_slice',ref,replace(dc,depth=33,slice_step=.03125)),
        ('angular_g33',ref,replace(dc,grid=33)),
        ('two_beam_slice_s0.02',replace(base,basis_mode='two-beam'),replace(dc,slice_step=.02)),
    ])
    for grid in (33,65,97,129):
        cases.append((f'detector_g{grid}_sub128',ref,replace(dc,grid=grid,subpixels=128,angular_maps=False)))
    # Explicit hypothetical control, never substituted for crystal [001] M.
    for basis in ('two-beam','full'):
        for channel in ('single','double'):
            cases.append((f'axis_control_{basis}_{channel}',replace(base,basis_mode=basis),
                replace(cfg,channeling_model=channel,magnetization=(1.,1.,7.))))
    return cases


def run_case(root,label,s,cfg,code_hashes):
    identity=dict(settings=asdict(s),config=asdict(cfg),source_sha256=sha(cfg.source),physics_sha256=code_hashes)
    digest=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:12]
    proof_path=root/'projection_ownership_check.json'
    proof=json.loads(proof_path.read_text(encoding='utf-8')) if proof_path.exists() else {}
    for saved in sorted((root/'cases').glob(label+'_*/case.json')):
        data=json.loads(saved.read_text(encoding='utf-8'));arrays=saved.with_name('arrays.npz')
        if (data.get('label')==label and data.get('complete') and compatible_identity(data['identity'],identity,proof)
            and arrays.exists() and data['arrays_sha256']==sha(arrays)):
            print('REUSE',label,flush=True);return data,arrays
    folder=root/'cases'/(label+'_'+digest);folder.mkdir(parents=True,exist_ok=True)
    meta_path=folder/'case.json';arrays_path=folder/'arrays.npz'
    if meta_path.exists() and arrays_path.exists():
        data=json.loads(meta_path.read_text())
        if data.get('complete') and data['arrays_sha256']==sha(arrays_path):
            print('REUSE',label,flush=True);return data,arrays_path
    print('RUN',label,flush=True);start=time.perf_counter()
    result=calculate(Structure.nickel(),s,cfg)
    crystal,R,hkl,g,microscope=geometry(Structure.nickel(),s)
    arrays=dict(qx=result['qx'],qy=result['qy'],hkl=np.asarray(hkl),g=g,depth_nm=result['depth_nm'])
    methods={}
    for name,r in result['methods'].items():
        fields={}
        for edge,values in r['maps'].items():
            stats,parts=row_mirror_diagnostics(r['qx'],r['qy'],dict(magnetic=values['I_mag'],nonmagnetic=values['I_nonmag'],total=values['I_plus']))
            fields[edge]=stats
            arrays.update({name+'__'+edge+'__'+k:v for k,v in parts.items()})
            for key in ('I_plus','I_minus','I_mag','I_nonmag'):
                arrays[name+'__'+edge+'__'+key]=values[key]
        arrays.update({name+'__spectrum__'+k:v for k,v in r['spectra'].items()})
        arrays[name+'__amplitudes']=r['amplitudes'];arrays[name+'__coherence']=r['coherence']
        methods[name]=dict(metrics=metrics(r),parity=fields,detector_areas=r['metadata']['detector_areas'],
            source_audit=r['metadata']['source_audit'],angular_evaluation=r['metadata']['angular_evaluation'],
            exit_populations=abs(r['amplitudes'][-1])**2,settings=asdict(s))
        assert not any(d['mirror_reuse'] for d in r['metadata']['angular_evaluation'])
    temporary=folder/'arrays.tmp'
    with temporary.open('wb') as f:np.savez_compressed(f,**arrays)
    temporary.replace(arrays_path)
    data=dict(label=label,complete=True,identity=identity,elapsed_seconds=time.perf_counter()-start,
        beam_count=len(hkl),frame=R.tolist(),magnetization_crystal=result['metadata']['magnetization_crystal'],
        magnetization_local=result['metadata']['magnetization_local'],s_target=result['metadata']['s_target'],
        za_q=result['metadata']['za_q'],wavelength_angstrom=result['metadata']['wavelength_angstrom'],
        hkl=[list(h) for h in hkl],excitation_errors=excitation(g,s.tilt,s.voltage).tolist(),
        methods=methods,comparison=result['comparison'],fft=result['fft']['summary'],
        software_commit=result['metadata']['software_commit'],software_worktree_dirty=result['metadata']['software_worktree_dirty'],
        arrays_sha256=sha(arrays_path))
    # Convert numerical scalar/array diagnostics without weakening NPZ precision.
    temporary=folder/'case.tmp';temporary.write_text(json.dumps(data,indent=2,default=lambda v:v.tolist() if isinstance(v,np.ndarray) else float(v)),encoding='utf-8');temporary.replace(meta_path)
    print('DONE',label,round(data['elapsed_seconds'],2),'seconds',flush=True)
    return json.loads(meta_path.read_text()),arrays_path


def export_summary(root,records):
    rows=[]
    for data,path in records:
        s=data['identity']['settings'];cfg=data['identity']['config']
        for method,item in data['methods'].items():
            for edge,values in item['metrics'].items():
                parity=item['parity'].get(edge,{name:dict(even_fraction='',odd_fraction='') for name in ('magnetic','nonmagnetic','total')})
                row=dict(case=data['label'],basis=s['basis_mode'],channeling=cfg['channeling_model'],method=method,edge=edge,
                    thickness_nm=s['thickness'],tilt_x_mrad=s['tilt'][0],tilt_y_mrad=s['tilt'][1],s_target=data['s_target'],
                    beam_count=data['beam_count'],beam_cutoff=s['beam_cutoff'],potential_cutoff=s['potential_cutoff'],
                    fft_grid=cfg['fft_grid'],depth_nodes=cfg['depth'],slice_step_nm=cfg['slice_step'],angular_grid=cfg['grid'],
                    angular_maps=cfg['angular_maps'],aperture_subpixels=cfg['subpixels'],
                    magnetic_even_fraction=parity['magnetic']['even_fraction'],nonmagnetic_odd_fraction=parity['nonmagnetic']['odd_fraction'],
                    total_odd_fraction=parity['total']['odd_fraction'],elapsed_seconds=data['elapsed_seconds'],
                    Sigma_ref=values['Sigma_ref'],D_mag=values['D_mag'],D_nonmag=values['D_nonmag'],D_raw=values['D_raw'],
                    A_mag_percent=100*values['A_mag'],A_nonmag_percent=100*values['A_nonmag'],
                    bw_ms_A_mag_pp=100*data['comparison']['edges'][edge]['detector']['A_mag']['absolute'],
                    incoming_excluded_population=data['fft']['max_excluded_population'],arrays_path=str(path.relative_to(root)))
                with np.load(path) as arrays:
                    energy=arrays[method+'__spectrum__energy_ev'];i=int(np.argmin(abs(energy-values['energy_ev'])))
                    for key in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus','N_A','N_B','M_A','M_B','prb_relative_dichroism_percent'):
                        row[key]=float(arrays[method+'__spectrum__'+key][i])
                row['detector_area_A']=item['detector_areas']['A']
                row['aperture_relative_area_error']=(item['detector_areas']['A']/(np.pi*cfg['radius']**2)-1)
                row['bw_ms_raw_A_l2_relative']=data['comparison']['spectra']['I_A_plus']['l2_relative']
                if method=='fft-multislice':
                    row['outgoing_excluded_population']=max(d.get('outgoing_max_excluded_population',0) for d in item['angular_evaluation']) if cfg['channeling_model']=='double' else ''
                rows.append(row)
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with (root/'comparison.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,keys);writer.writeheader();writer.writerows(rows)
    np.savez_compressed(root/'comparison.npz',**{k:np.asarray([r.get(k,'') for r in rows]) for k in keys})
    (root/'cases_index.json').write_text(json.dumps([dict(label=d['label'],case_json=str(p.with_name('case.json').relative_to(root))) for d,p in records],indent=2),encoding='utf-8')
    diffraction=[]
    for data,path in records:
        with np.load(path) as arrays:
            for method,item in data['methods'].items():
                for h,g,s,power in zip(data['hkl'],arrays['g'],data['excitation_errors'],item['exit_populations']):
                    diffraction.append(dict(case=data['label'],method=method,h=h[0],k=h[1],l=h[2],qx=g[0],qy=g[1],s_inv_A=s,exit_intensity=power))
    with (root/'diffraction.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,list(diffraction[0]));writer.writeheader();writer.writerows(diffraction)


def figures(root,records):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    selected=[(d,p) for d,p in records if d['label'] in ('baseline_two-beam_double_t8','baseline_full_double_t8','axis_control_full_double','mistilt_full_double_x0_y0.2')]
    for data,path in selected:
        with np.load(path) as arrays:
            extent=[arrays['qx'].min(),arrays['qx'].max(),arrays['qy'].min(),arrays['qy'].max()]
            fig,axes=plt.subplots(2,3,figsize=(12,8),layout='constrained')
            for i,method in enumerate(('bloch','fft-multislice')):
                values=[arrays[method+'__L3__magnetic__'+part] for part in ('raw','mirror_odd','mirror_even')]
                limit=max(abs(v).max() for v in values)
                for j,(ax,value) in enumerate(zip(axes[i],values)):
                    image=ax.imshow(value,origin='lower',extent=extent,cmap='RdBu_r',vmin=-limit,vmax=limit,interpolation='nearest')
                    ax.axhline(0,color='k',lw=.6);ax.plot(0,0,'kx',label='000');ax.plot(*data['za_q'],marker='*',color='gold',mec='k',label='ZA [117]')
                    target=np.array([np.sqrt(8)/3.524,0]);ax.plot(*target,'rs',mfc='none',label='(2,-2,0)')
                    from matplotlib.patches import Circle
                    ax.add_patch(Circle(target/2,np.linalg.norm(target)/2,fill=False,ls=':',color='teal'))
                    for center in data['identity']['config']['centers']:ax.add_patch(Circle(center,data['identity']['config']['radius'],fill=False,ls='--',color='black'))
                    ax.set(xlabel='qx (cycles/Angstrom)',ylabel='qy (cycles/Angstrom)',title=method+' | '+('raw magnetic odd','row-mirror odd part','row-mirror even part')[j])
                    ax.title.set_fontsize(9)
                    fig.colorbar(image,ax=ax,shrink=.7,label='Relative intensity (a.u.)')
                    if i==0 and j==0:ax.legend(fontsize=6,loc='upper left')
            fig.suptitle(data['label']+' | crystal M='+str(data['magnetization_crystal'])+'\nLocal M='+str(np.round(data['magnetization_local'],6)))
            for suffix in ('png','svg'):fig.savefig(root/(data['label']+'.'+suffix),dpi=160)
            plt.close(fig)
            fig,axes=plt.subplots(2,4,figsize=(14,7),layout='constrained')
            for i,method in enumerate(('bloch','fft-multislice')):
                for j,(field,part) in enumerate((('nonmagnetic','raw'),('nonmagnetic','mirror_odd'),('total','raw'),('total','mirror_odd'))):
                    raw=arrays[method+'__L3__'+field+'__raw'];value=arrays[method+'__L3__'+field+'__'+part]
                    image=axes[i,j].imshow(value,origin='lower',extent=extent,cmap='RdBu_r',vmin=-abs(raw).max(),vmax=abs(raw).max(),interpolation='nearest')
                    fraction=data['methods'][method]['parity']['L3'][field]['odd_fraction']
                    axes[i,j].set(title=method+' '+field+' '+part+'\nodd fraction %.3g'%fraction,xlabel='qx',ylabel='qy')
                    axes[i,j].title.set_fontsize(8)
                    axes[i,j].axhline(0,color='k',lw=.6);fig.colorbar(image,ax=axes[i,j],shrink=.7)
            fig.suptitle(data['label']+' | nonmagnetic/total raw maps and row-mirror odd residuals; common scale within each field')
            for suffix in ('png','svg'):fig.savefig(root/(data['label']+'_nonmag_total.'+suffix),dpi=160)
            plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    for method in ('bloch','fft-multislice'):
        for channel in ('single','double'):
            chosen=[d for d,p in records if d['label'].startswith('baseline_full_'+channel)]
            chosen.sort(key=lambda d:d['identity']['settings']['thickness'])
            x=[d['identity']['settings']['thickness'] for d in chosen]
            axes[0].plot(x,[100*d['methods'][method]['metrics']['L3']['A_mag'] for d in chosen],'o-',label=method+' '+channel)
            axes[1].plot(x,[d['methods'][method]['parity']['L3']['magnetic']['even_fraction'] for d in chosen],'o-')
    axes[0].set(xlabel='Thickness (nm)',ylabel='L3 magnetic-only detector asymmetry (%)');axes[0].legend(fontsize=8)
    axes[1].set(xlabel='Thickness (nm)',ylabel='Raw magnetic map mirror-even L2 fraction')
    for suffix in ('png','svg'):fig.savefig(root/('thickness_parity_comparison.'+suffix),dpi=160)
    plt.close(fig)


def convergence(root,records):
    """Compare matched controls; agreement is a separate numerical question."""
    lookup={d['label']:(d,p) for d,p in records};ref='basis_b4.6_t8'
    pairs=[('basis_8','baseline_full_double_t8',ref),('basis_8',ref,'basis_b5.4_t8'),
        ('basis_30','baseline_full_double_t30','basis_b4.6_t30'),
        ('potential','potential_p4.6','potential_p5.4'),('potential','potential_p5.4',ref),
        ('fft','fft_f24',ref),('fft',ref,'fft_f48'),
        ('slice','slice_s0.08',ref),('slice',ref,'slice_s0.02'),
        ('depth_fixed_step','depth_d33_fixed_slice',ref),('depth_fixed_step',ref,'depth_d129'),
        ('coarse_angular',ref,'angular_g33'),
        ('boundary_subpixels','angular_g33','detector_g33_sub128'),
        ('detector_grid','detector_g33_sub128','detector_g65_sub128'),
        ('detector_grid','detector_g65_sub128','detector_g97_sub128'),
        ('detector_grid','detector_g97_sub128','detector_g129_sub128')]
    rows=[]
    for factor,first,second in pairs:
        if first not in lookup or second not in lookup:continue
        da,pa=lookup[first];db,pb=lookup[second]
        with np.load(pa) as a,np.load(pb) as b:
            for method in ('bloch','fft-multislice'):
                for edge in ('L3','L2'):
                    ma,mb=[d['methods'][method]['metrics'][edge] for d in (da,db)]
                    energy=a[method+'__spectrum__energy_ev'];i=int(np.argmin(abs(energy-ma['energy_ev'])))
                    raw=[]
                    for key in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus'):
                        x,y=[arr[method+'__spectrum__'+key][i] for arr in (a,b)]
                        raw.append(abs(x-y)/max(abs(x),abs(y),1e-30))
                    prb=abs(a[method+'__spectrum__prb_relative_dichroism_percent'][i]-b[method+'__spectrum__prb_relative_dichroism_percent'][i])
                    magnetic=100*abs(ma['A_mag']-mb['A_mag'])
                    rows.append(dict(factor=factor,first=first,second=second,method=method,edge=edge,
                        delta_magnetic_pp=magnetic,delta_prb_pp=float(prb),raw_relative_error_max=float(max(raw)),
                        pass_observable_gate=bool(magnetic<=.01 and prb<=.01 and max(raw)<=.001)))
    with (root/'convergence.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary=[]
    for factor,first,second in pairs:
        selected=[r for r in rows if r['first']==first and r['second']==second]
        if selected:summary.append(dict(factor=factor,first=first,second=second,
            max_magnetic_pp=max(r['delta_magnetic_pp'] for r in selected),
            max_prb_pp=max(r['delta_prb_pp'] for r in selected),
            max_relative_raw_error=max(r['raw_relative_error_max'] for r in selected),
            passed=all(r['pass_observable_gate'] for r in selected)))
    (root/'convergence_summary.json').write_text(json.dumps(dict(
        thresholds=dict(dichroism_absolute_pp=.01,raw_relative_error=.001),
        scope='Representative detector-observable checks only, not full physical convergence or uniform thickness/mistilt certification',
        comparisons=summary),indent=2),encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    reference='basis_b4.6_t8'
    groups=[('Beam cutoff',[('baseline_full_double_t8',3.8),(reference,4.6),('basis_b5.4_t8',5.4)]),
        ('Potential cutoff',[('potential_p4.6',4.6),('potential_p5.4',5.4),(reference,6.2)]),
        ('FFT grid',[('fft_f24',24),(reference,32),('fft_f48',48)]),
        ('Depth nodes',[('depth_d33_fixed_slice',33),(reference,65),('depth_d129',129)]),
        ('Slice step (nm)',[('slice_s0.02',.02),(reference,.04),('slice_s0.08',.08)]),
        ('Angular grid',[(reference,17),('angular_g33',33)])]
    lookup={d['label']:d for d,p in records};fig,axes=plt.subplots(2,3,figsize=(12,7),layout='constrained')
    for ax,(title,labels) in zip(axes.ravel(),groups):
        for method in ('bloch','fft-multislice'):
            available=[(lookup[label],x) for label,x in labels if label in lookup]
            ax.plot([x for d,x in available],[100*d['methods'][method]['metrics']['L3']['A_mag'] for d,x in available],'o-',label=method)
        ax.set(xlabel=title,ylabel='L3 magnetic-only asymmetry (%)');ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=8);fig.suptitle('Independent numerical controls at 8 nm; all other settings fixed within each panel')
    for suffix in ('png','svg'):fig.savefig(root/('numerical_controls.'+suffix),dpi=160)
    plt.close(fig)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'outputs/ni_117_emcd_validation')
    parser.add_argument('--only',nargs='*');parser.add_argument('--figures-only',action='store_true');args=parser.parse_args()
    root=args.output;root.mkdir(parents=True,exist_ok=True)
    if args.figures_only:
        records=[]
        for item in json.loads((root/'cases_index.json').read_text()):
            if args.only and item['label'] not in args.only:continue
            path=root/item['case_json'];records.append((json.loads(path.read_text()),path.with_name('arrays.npz')))
        export_summary(root,records);convergence(root,records);figures(root,records);return
    code_hashes={p:sha(ROOT/'src/emcd_sim'/p) for p in PHYSICS_FILES}
    records=[];cases=configurations()
    if args.only:cases=[c for c in cases if c[0] in args.only]
    print('Cases:',len(cases),flush=True)
    for label,s,cfg in cases:
        data,path=run_case(root,label,s,cfg,code_hashes);records.append((data,path));export_summary(root,records)
    convergence(root,records);figures(root,records)
    print('COMPLETE',len(records),'Both-method cases',flush=True)


if __name__=='__main__':main()
