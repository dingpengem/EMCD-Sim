"""Matched full finite ZOLZ elastic audit; no inelastic calculation.

The GUI's 121-beam interactive preview cap is not an elastic physics limit.
Enumerate the complete requested disk here, with process memory admission.
"""
import csv,hashlib,json,subprocess
from dataclasses import asdict
from itertools import product
from pathlib import Path
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import LogNorm
from emcd_sim.crystal import Crystal
from emcd_sim.elastic import BeamSet
from emcd_sim.physical_elastic import PhysicalElasticModel
from emcd_sim.scattering import IndependentAtomPotential
from emcd_sim.elastic_reference import FourierCutoffPotential
from emcd_sim.geometry import Microscope,electron_wavelength_angstrom
from emcd_sim.diffraction import excitation_errors_angstrom_inv
from emcd_sim.gui.geometry import orientation
from emcd_sim.gui.project_io import load_project
from emcd_sim.gui.memory_budget import reserve_memory
from ni_double_channeling_spectral_report import folder,write_csv

ROOT=Path('outputs/ni_two_beam_geometry_comparison')
CORES=('src/emcd_sim/physical_elastic.py','src/emcd_sim/scattering.py','src/emcd_sim/elastic_reference.py','src/emcd_sim/crystal.py')


def enumerate_zolz(crystal,zone,cutoff,*,row=False):
    bounds=np.ceil(cutoff*np.linalg.norm(crystal.lattice_angstrom,axis=1)).astype(int)
    found=[]
    for h in product(*(range(-v,v+1) for v in bounds)):
        if np.dot(h,zone) or (row and (h[1] or h[2])) or not crystal.is_allowed(h):continue
        length=np.linalg.norm(crystal.g_vector(h))
        if length<=cutoff+1e-10:found.append((length,h))
    found.sort(key=lambda p:(round(p[0],12),p[1]))
    return tuple(h for _,h in found)


def groups(hkl):
    h=np.asarray(hkl);two=np.all(h==[0,0,0],axis=1)|np.all(h==[2,0,0],axis=1)
    off=(h[:,1]!=0)|(h[:,2]!=0)
    return two,off,~(two|off)


def populations(values,vectors,t):
    """Exact finite-interval coherence average of the unchanged BW solution."""
    weights=vectors*vectors[0].conj()[None,:]
    phase=np.exp(1j*t*values)
    psi=weights@phase
    delta=values[:,None]-values[None,:]
    integral=np.exp(.5j*t*delta)*np.sinc(.5*t*delta/np.pi)
    coherence=(weights@integral)@weights.conj().T
    return psi,coherence


def fractions(intensity,hkl):
    total=float(np.sum(intensity));a,b,c=groups(hkl)
    return dict(I_total=total,normalization_error=abs(total-1),
        I_2beam=float(np.sum(intensity[a])),I_offrow=float(np.sum(intensity[b])),I_other_row=float(np.sum(intensity[c])),
        P_2beam=float(100*np.sum(intensity[a])/total),P_offrow=float(100*np.sum(intensity[b])/total),
        P_other_row=float(100*np.sum(intensity[c])/total))


def execute(saved,zone,row):
    settings=saved['settings'];snapshot=saved['structure_snapshot']
    R=orientation(np.asarray(snapshot['lattice_angstrom']),settings.zone)
    crystal=Crystal(np.asarray(snapshot['lattice_angstrom'])@R.T,np.asarray(snapshot['fractional_positions']),tuple(snapshot['species']))
    hkl=enumerate_zolz(crystal,settings.zone,settings.beam_cutoff,row=row);n=len(hkl)
    potential=FourierCutoffPotential(IndependentAtomPotential(crystal,debye_waller_b_angstrom2=settings.b_factor),settings.potential_cutoff)
    model=PhysicalElasticModel(crystal,Microscope(settings.voltage,settings.tilt),BeamSet(hkl),potential)
    # Elastic eigensystem/coherences, not the much larger inelastic n^4 kernel.
    working=(256*n*n+128*4097*n)/2**20+16
    tag=zone+('_row' if row else '_full')
    path=ROOT/(tag+'.npz')
    provenance=dict(settings=asdict(settings),row_restricted=row,beam_hkl=hkl,
        source_project=str(folder(zone,8,'double','bloch')/'full'),
        core_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in CORES},
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    identity=json.dumps(provenance,sort_keys=True)
    with reserve_memory(working,2048) as admission:
        if path.exists():
            with np.load(path,allow_pickle=False) as cache:
                if str(cache['provenance_json'])!=identity:raise ValueError('Elastic checkpoint provenance mismatch: '+str(path))
                arrays={k:cache[k].copy() for k in cache.files if k!='provenance_json'}
        else:
            H=model.hamiltonian_nm_inv();values,vectors=np.linalg.eigh(H)
            states=[populations(values,vectors,t) for t in (8.,12.,30.)]
            arrays=dict(hkl=np.asarray(hkl),g=model.reciprocal_vectors_xy,s=excitation_errors_angstrom_inv(model),
                coupling_0g_nm_inv=abs(H[0]),structure_factor_0g=np.array([potential.structure_factor(h) for h in hkl]),
                thickness_nm=np.array([8.,12.,30.]),exit_amplitudes=np.stack([p for p,c in states]),
                depth_coherence=np.stack([c for p,c in states]),frame=R)
            np.savez_compressed(path,**arrays,provenance_json=np.array(identity))
    beam_rows=[];summary=[]
    saved_exit_error=None
    if np.array_equal(np.asarray(saved['metadata']['beam_hkl']),arrays['hkl']):
        saved_exit_error=float(abs(arrays['exit_amplitudes'][0]-saved['amplitudes'][-1]).max())
        np.testing.assert_allclose(arrays['exit_amplitudes'][0],saved['amplitudes'][-1],atol=1e-12,rtol=1e-12)
    for it,t in enumerate(arrays['thickness_nm']):
        exit_i=abs(arrays['exit_amplitudes'][it])**2;avg=arrays['depth_coherence'][it].diagonal().real
        assert min(exit_i.min(),avg.min())>=-1e-13
        for plane,I in (('exit',exit_i),('depth_average',avg)):
            record=fractions(I,hkl)
            assert record['normalization_error']<1e-10
            assert abs(sum(record[k] for k in ('P_2beam','P_offrow','P_other_row'))-100)<1e-10
            summary.append(dict(geometry=tag,thickness_nm=t,plane=plane,**record))
        for i,h in enumerate(hkl):
            beam_rows.append(dict(geometry=tag,thickness_nm=t,h=h[0],k=h[1],l=h[2],
                g_inv_angstrom=float(np.linalg.norm(arrays['g'][i])),s_inv_angstrom=float(arrays['s'][i]),
                coupling_0g_nm_inv=float(arrays['coupling_0g_nm_inv'][i]),
                structure_factor_abs_angstrom=float(abs(arrays['structure_factor_0g'][i])),
                exit_intensity=float(exit_i[i]),depth_average_intensity=float(avg[i]),
                exit_fraction=float(exit_i[i]/exit_i.sum()),depth_average_fraction=float(avg[i]/avg.sum()),
                group='000+200' if groups(hkl)[0][i] else 'offrow' if groups(hkl)[1][i] else 'other_row'))
    lam=electron_wavelength_angstrom(settings.voltage);ki=model.microscope.incident_k_xy
    local=np.r_[np.asarray(settings.tilt)*.001,1.];local/=np.linalg.norm(local)
    metadata=dict(geometry=tag,nominal_zone=list(settings.zone),actual_direction_local=local.tolist(),
        actual_direction_cubic=(R.T@local).tolist(),direction_convention='normalized paraxial (tilt_x_rad,tilt_y_rad,1)',
        absolute_tilt_mrad=list(settings.tilt),relative_to_nominal_zone_tilt_mrad=list(settings.tilt),
        tilt_vector_norm_mrad=float(np.linalg.norm(settings.tilt)),
        target=[2,0,0],s200_inv_angstrom=float(arrays['s'][hkl.index((2,0,0))]),
        laue_circle_center_inv_angstrom=(-ki).tolist(),projected_zone_axis_inv_angstrom=(-ki).tolist(),
        laue_circle_radius_inv_angstrom=float(np.linalg.norm(ki)),wavelength_angstrom=lam,voltage_kv=settings.voltage,
        beam_count=n,beam_cutoff_inv_angstrom=settings.beam_cutoff,potential_cutoff_inv_angstrom=settings.potential_cutoff,
        full_finite_zolz=not row,offrow_included=not row,frame=R.tolist(),memory_admission=admission,
        classification=('C: [001]-derived exact-(200)-Bragg, systematic-row-restricted' if row else
            'B: [001]-derived exact-(200)-Bragg with full finite ZOLZ' if zone=='001' else
            'Ni [017]-derived exact-(200)-Bragg with full finite ZOLZ'),
        depth_average='Analytic finite-interval coherence average of the same elastic BW eigenmodes; no depth discretization error',
        saved_8nm_incoming_exit_max_amplitude_error=saved_exit_error,
        commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
    (ROOT/(tag+'_metadata.json')).write_text(json.dumps(metadata,indent=2))
    print(tag,n,'beams',json.dumps(summary[:2]),flush=True)
    return arrays,metadata,beam_rows,summary


def figures(data,summary):
    fig=Figure(figsize=(11,5),layout='constrained');FigureCanvasAgg(fig);axes=fig.subplots(1,2)
    vmax=max(float(abs(data[z]['exit_amplitudes'][0]).max()**2) for z in ('001_full','017_full'))
    for ax,z in zip(axes,('001_full','017_full')):
        a=data[z];I=abs(a['exit_amplitudes'][0])**2
        sc=ax.scatter(*a['g'].T,c=I,s=16+110*np.sqrt(I/vmax),norm=LogNorm(vmin=1e-9,vmax=vmax),cmap='viridis')
        candidates=set(np.argsort(I)[-7:])|{0,list(map(tuple,a['hkl'])).index((2,0,0))}
        off=np.flatnonzero(groups(a['hkl'])[1]);candidates.update(off[np.argsort(I[off])[-2:]])
        for i in candidates:
            h=tuple(a['hkl'][i]);offset=(-24,-15) if h==(0,0,0) else (4,7) if h==(2,0,0) else (4,-13 if h[0]>0 else 5)
            ax.annotate('(%d %d %d)'%h,a['g'][i],xytext=offset,textcoords='offset points',fontsize=7)
        ax.set(xlim=(-4.8,4.8),ylim=(-4.8,4.8),aspect='equal',xlabel='qx (cycles/Angstrom)',ylabel='qy (cycles/Angstrom)',title=z[:3]+' full ZOLZ, 8 nm')
    fig.colorbar(sc,ax=axes,label='Incident-normalized elastic spot intensity')
    save(fig,'indexed_diffraction')
    fig=Figure(figsize=(9,5),layout='constrained');FigureCanvasAgg(fig);axes=fig.subplots(1,2)
    for ax,plane in zip(axes,('exit','depth_average')):
        for j,z in enumerate(('001_full','017_full')):
            r=next(r for r in summary if r['geometry']==z and r['thickness_nm']==8 and r['plane']==plane)
            a=data[z];I=abs(a['exit_amplitudes'][0])**2 if plane=='exit' else a['depth_coherence'][0].diagonal().real
            i=list(map(tuple,a['hkl'])).index((2,0,0));v=[I[0],I[i],r['I_other_row'],r['I_offrow']]
            ax.bar(np.arange(4)+(j-.5)*.35,v,width=.35,label=z[:3])
        ax.set(xticks=np.arange(4),xticklabels=['000','200','Other row','Off-row'],ylabel='Incident-normalized intensity',title=plane.replace('_',' '));ax.legend()
    save(fig,'beam_groups_8nm')
    fig=Figure(figsize=(9,5),layout='constrained');FigureCanvasAgg(fig);ax=fig.subplots()
    for z in ('001_full','017_full'):
        for plane,style in (('exit','o-'),('depth_average','s--')):
            rows=[r for r in summary if r['geometry']==z and r['plane']==plane]
            ax.plot([r['thickness_nm'] for r in rows],[r['P_2beam'] for r in rows],style,label=z[:3]+' '+plane)
    ax.set(xlabel='Thickness (nm)',ylabel='000+200 fraction of represented intensity (%)',xticks=[8,12,30]);ax.legend();ax.grid(alpha=.2)
    save(fig,'two_beam_fractions')
    fig=Figure(figsize=(7,5),layout='constrained');FigureCanvasAgg(fig);ax=fig.subplots()
    for z in ('001_full','017_full'):
        for t in (8,12,30):
            a,b=[next(r['P_2beam'] for r in summary if r['geometry']==z and r['thickness_nm']==t and r['plane']==p) for p in ('exit','depth_average')]
            ax.scatter(a,b,label=z[:3]+f' {t} nm');ax.annotate(z[:3]+f' {t}',(a,b),xytext=(4,3),textcoords='offset points',fontsize=8)
    ax.plot([0,100],[0,100],':',color='.6');ax.set(xlabel='Exit-plane 000+200 (%)',ylabel='Depth-average 000+200 (%)',xlim=(0,101),ylim=(0,101));ax.grid(alpha=.2)
    save(fig,'exit_vs_depth_average')


def save(fig,name):
    for ext in ('png','svg'):fig.savefig(ROOT/(name+'.'+ext),dpi=175)


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    # Complete the spectral milestone before this separate elastic study.
    status=json.loads(Path('outputs/ni_double_channeling_full_spectra/spectral_acceptance.json').read_text())
    assert status['passed']
    protected=list(Path('outputs/ni_double_channeling_full_spectra').rglob('*.npz'))+[Path('data/wien2k_ni/Ni_fm.xmcd')]
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    data={};summary=[];beams=[];metadata=[]
    for zone,row in (('001',True),('001',False),('017',False)):
        saved=load_project(folder(zone,8,'double','bloch')/'full')
        a,m,b,s=execute(saved,zone,row);data[m['geometry']]=a;metadata.append(m);beams.extend(b);summary.extend(s)
    write_csv(ROOT/'beam_populations.csv',beams);write_csv(ROOT/'population_summary.csv',summary)
    (ROOT/'geometry_audit.json').write_text(json.dumps(metadata,indent=2));figures(data,summary)
    differences=[]
    for t in (8,12):
        row,full=[data[k] for k in ('001_row','001_full')];it=list(row['thickness_nm']).index(t)
        hfull=list(map(tuple,full['hkl']));ix=[hfull.index(tuple(h)) for h in row['hkl']]
        for j,h in enumerate(row['hkl']):
            r=row['exit_amplitudes'][it,j];f=full['exit_amplitudes'][it,ix[j]]
            differences.append(dict(thickness_nm=t,h=int(h[0]),restricted_exit_intensity=float(abs(r)**2),full_exit_intensity=float(abs(f)**2),
                exit_complex_amplitude_absolute_change=float(abs(f-r)),
                restricted_coherence_000g_real=float(row['depth_coherence'][it,0,j].real),
                restricted_coherence_000g_imag=float(row['depth_coherence'][it,0,j].imag),
                full_coherence_000g_real=float(full['depth_coherence'][it,0,ix[j]].real),
                full_coherence_000g_imag=float(full['depth_coherence'][it,0,ix[j]].imag)))
    write_csv(ROOT/'row_restriction_effect.csv',differences)
    unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==value for p,value in before.items())
    (ROOT/'preservation.json').write_text(json.dumps(dict(passed=unchanged,protected_file_count=len(before),
        protected_sha256=before,scope='Existing full-spectrum NPZ files and active MDFF source'),indent=2))
    if not unchanged:raise RuntimeError('Protected full-spectrum data changed during geometry analysis')


if __name__=='__main__':main()
