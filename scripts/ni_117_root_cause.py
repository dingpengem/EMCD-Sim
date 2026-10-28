"""Read-only historical inventory and small non-GUI [117] symmetry controls.

Run worker under either main's pristine source or the development source.
No completed study checkpoint is overwritten. Historical matches are candidates,
not claims of reproducing the user's original figure.
"""
from pathlib import Path
from dataclasses import replace
import argparse, hashlib, json, os
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/ni_117_emcd_validation/root_cause'


def analytical_control():
    # T=I+i*m*epsilon_xy is Hermitian PSD; no GUI, XMCD loader or solver.
    a=np.linspace(0,2*np.pi,361);g=.8;qz=-.06
    q=np.column_stack((g/2+g/2*np.cos(a),g/2*np.sin(a),np.full(a.size,qz)))
    Q=np.stack((q,q-np.array([g,0,0])),axis=1)
    c=np.array([np.sqrt(.6),1j*np.sqrt(.4)]);C=c[:,None]*c.conj()[None,:]
    def intensity(T):
        mdff=np.einsum('pia,ab,pjb->pij',Q,T,Q)
        den=np.sum(Q*Q,axis=-1)
        return np.einsum('ij,pij->p',C,mdff/(den[:,:,None]*den[:,None,:])).real
    # Actual paraxial incident direction lies in the row plane, not exactly z.
    m=np.array([-.0100645696369,0,1.]);m/=np.linalg.norm(m)
    T=np.eye(3,dtype=complex)
    T+=.2j*np.array([[0,m[2],-m[1]],[-m[2],0,m[0]],[m[1],-m[0],0]])
    plus=intensity(T);minus=intensity(T.conj());N=(plus+minus)/2;M=(plus-minus)/2
    result=dict(hermitian=bool(np.allclose(T,T.conj().T)),minimum_eigenvalue=float(np.linalg.eigvalsh(T).min()),
        magnetic_mirror_residual=float(np.max(abs(M+M[::-1]))/np.max(abs(M))),
        nonmagnetic_mirror_residual=float(np.max(abs(N-N[::-1]))/np.max(abs(N))),
        reversal_odd_residual=float(np.max(abs(((minus-plus)/2)+M))),
        magnetic_upper_arc_min=float(M[1:180].min()),magnetic_upper_arc_max=float(M[1:180].max()))
    assert result['magnetic_mirror_residual']<1e-12 and result['nonmagnetic_mirror_residual']<1e-12
    assert plus.min()>=0 and minus.min()>=0
    np.savez_compressed(OUT/'analytical_circle.npz',angle=a,q=q,I_plus=plus,I_minus=minus,N=N,M=M,T=T,C=C)
    (OUT/'analytical_control.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def inventory():
    matches=[];errors=[];count=0
    def error(e):errors.append(str(e))
    # Search saved structured configurations, not incidental numeric '117'
    # in filenames. Exclude this study and transient tests, retain failures.
    def contains(v):
        if isinstance(v,dict):
            for k,x in v.items():
                if k in ('zone','zone_axis','zone_direction') and (x==[1,1,7] or x=='[117]' or x=='1 1 7'):return True
                if contains(x):return True
        elif isinstance(v,list):return any(contains(x) for x in v)
        return False
    for base,dirs,files in os.walk(ROOT/'outputs',onerror=error):
        dirs[:]=[d for d in dirs if d!='ni_117_emcd_validation' and 'tmp' not in d and 'pytest' not in d]
        for name in files:
            if not name.endswith('.json'):continue
            p=Path(base)/name
            try:
                if p.stat().st_size>20_000_000:continue
                obj=json.loads(p.read_text(encoding='utf-8-sig'));count+=1
                if contains(obj):matches.append(dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
            except (OSError,ValueError) as e:errors.append(str(p)+': '+str(e))
    result=dict(scope='Accessible local outputs JSON; excludes current study and temporary/pytest directories. Does not establish absence in external user folders.',
        files_parsed=count,candidates=matches,unreadable=errors)
    (OUT/'historical_inventory.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def worker(destination):
    from emcd_sim.gui.geometry import Structure,Settings,elastic_model,orientation,excitation
    from emcd_sim.gui.emcd_forward import ForwardSettings,tensors
    from emcd_sim.geometry import electron_wavelength_angstrom,VirtualDetector
    from emcd_sim.elastic import BeamSet
    from emcd_sim.simulation import EMCDSimulation
    from emcd_sim.multislice_reference import coherence_from_amplitudes
    from emcd_sim.single_channeling_tensor import _tensor_angular_maps,fcc_site_phase_matrix
    structure=Structure.nickel();R=orientation(structure.atoms.cell.array,(1,1,7))
    desired=np.array([[1,-1,0],[7,7,-2],[1,1,7]],float);desired/=np.linalg.norm(desired,axis=1)[:,None]
    S=R@desired.T;g=np.sqrt(8)/3.524;tx=-500*electron_wavelength_angstrom(200)*g
    a=np.linspace(0,2*np.pi,361);q=np.column_stack((g/2+g/2*np.cos(a),g/2*np.sin(a)))
    qold=q@S[:2,:2].T;out=dict(angle=a,q_desired=q,frame=R,rotation=S)
    for consistent in (True,False):
        tilt=S[:2,:2]@np.array([tx,0]) if consistent else np.array([tx,0])
        s=Settings(zone=(1,1,7),target=(2,-2,0),tilt=tuple(tilt),thickness=8,beam_cutoff=3.8,potential_cutoff=6.2)
        base=elastic_model(structure,s)
        out['s_target_'+str(consistent)]=excitation(base.crystal.g_vector(s.target)[:2],tilt,200)
        for mode in ('two','full'):
            model=replace(base,beams=BeamSet(((0,0,0),(2,-2,0)))) if mode=='two' else base
            z=np.linspace(0,8,65);C=coherence_from_amplitudes(z,model.amplitudes(z))
            sim=EMCDSimulation(model,{'A':VirtualDetector((0,0),.1),'B':VirtualDetector((0,1),.1)})
            beam_axis=desired.T@np.array([tx*.001,0,1.])
            for axis in ((0,0,1),(1,1,7),tuple(beam_axis)):
                cfg=ForwardSettings(axis_declared=True,magnetization=axis,source=str(ROOT/'data/wien2k_ni/Ni_fm.xmcd'))
                T=tensors(cfg,np.array([831.271,848.698]),R)[0].tensor_angstrom2_per_ev[0]
                N,M=_tensor_angular_maps(sim,T,831.271,C,fcc_site_phase_matrix(sim),qold[:,0],qold[:,1])
                axis_name='crystal001' if axis==(0,0,1) else ('zone117' if axis==(1,1,7) else 'incident')
                prefix=f'{consistent}_{mode}_{axis_name}'
                out[prefix+'_N']=N*8;out[prefix+'_M']=M*8
    np.savez_compressed(destination,**out)


def summarize():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    with np.load(OUT/'current_circle.npz') as new,np.load(OUT/'main_236_circle.npz') as old:
        rows=[]
        for mode in ('two','full'):
            for axis in ('crystal001','zone117','incident'):
                prefix=f'True_{mode}_{axis}';M=new[prefix+'_M'];N=new[prefix+'_N']
                rows.append(dict(mode=mode,magnetization=axis,
                    magnetic_mirror_even_fraction=float(np.linalg.norm((M+M[::-1])/2)/np.linalg.norm(M)),
                    nonmagnetic_mirror_odd_fraction=float(np.linalg.norm((N-N[::-1])/2)/np.linalg.norm(N)),
                    old_new_magnetic_relative_max=float(np.max(abs(M-old[prefix+'_M']))/np.max(abs(M))),
                    old_new_nonmagnetic_relative_max=float(np.max(abs(N-old[prefix+'_N']))/np.max(abs(N))),
                    old_untransformed_tilt_magnetic_relative_max=float(np.max(abs(M-old[f'False_{mode}_{axis}_M']))/np.max(abs(M)))))
        R=old['frame'];g=R@np.array([2,-2,0])/3.524
        result=dict(reference_commit='236893392838ab5bc17dcf1848fd127009f2f048',
            reproduction_status='Controlled equivalent; no identified original user figure/configuration',
            old_frame=R.tolist(),old_target_g=g.tolist(),old_row_angle_degrees=float(np.degrees(np.arctan2(g[1],g[0]))),
            old_covariant_tilt_mrad=(old['rotation'][:2,:2]@np.array([-10.064569636897227,0])).tolist(),
            s_target_old_covariant=float(old['s_target_True']),s_target_old_untransformed=float(old['s_target_False']),
            comparisons=rows)
        fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
        for ax,mode in zip(axes,('two','full')):
            for axis,label in [('crystal001','crystal [001]'),('zone117','zone [117]'),('incident','incident-aligned')]:
                ax.plot(np.degrees(new['angle']),new[f'True_{mode}_{axis}_M'],label=label)
            ax.plot(np.degrees(old['angle']),old[f'True_{mode}_crystal001_M'],'k:',label='main, covariant geometry')
            ax.set(xlabel='Thales circle angle (degrees)',ylabel='Raw reversal-odd intensity (a.u.)',title=f'{mode}, Single, 8 nm, L3')
            ax.axhline(0,color='grey',lw=.5);ax.legend(fontsize=7)
        for ext in ('png','svg'):fig.savefig(OUT/f'thales_circle_comparison.{ext}',dpi=170)
        plt.close(fig)
        (OUT/'old_current_comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result,indent=2))


def incident_controls():
    from ni_117_emcd_validation import configurations,run_case,sha,PHYSICS_FILES
    from emcd_sim.study_geometry import StudyGeometry
    Ni117Geometry=lambda a_angstrom=3.524: StudyGeometry((1,1,7),(2,-2,0),a_angstrom)
    hashes={p:sha(ROOT/'src/emcd_sim'/p) for p in PHYSICS_FILES};records=[]
    for label,s,cfg in configurations():
        if not label.startswith('axis_control_'):continue
        # Explicit paraxial incident direction; the original controls were z.
        m=Ni117Geometry().frame.T@np.array([s.tilt[0]*.001,s.tilt[1]*.001,1.])
        data,path=run_case(OUT,label.replace('axis_control','incident_control'),s,replace(cfg,magnetization=tuple(m)),hashes)
        records.append(dict(label=data['label'],case_json=str(path.with_name('case.json').relative_to(OUT)),
            methods={name:item['parity'] for name,item in data['methods'].items()}))
    (OUT/'incident_controls.json').write_text(json.dumps(records,indent=2),encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--worker');parser.add_argument('--summarize',action='store_true');parser.add_argument('--incident-controls',action='store_true');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if args.worker:worker(args.worker)
    elif args.summarize:summarize()
    elif args.incident_controls:incident_controls()
    else:
        print(json.dumps(analytical_control(),indent=2));r=inventory();print('Inventory:',r['files_parsed'],'JSON files;',len(r['candidates']),'candidates;',len(r['unreadable']),'inaccessible/errors')
