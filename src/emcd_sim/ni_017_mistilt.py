"""True [017] projected-IAM controls and checkpointed (200) mistilt analysis."""
from __future__ import annotations
import argparse,csv,hashlib,json,subprocess
from dataclasses import dataclass,asdict,replace
from pathlib import Path
import numpy as np
from .ni_017_geometry import Ni017Geometry,rotated_tensor,energy_audit
from .ni_mistilt_series import MistiltConfig,calculate_case,validate_checkpoint,write_json,MAP_KEYS,METHODS,EDGES
from .ni_mistilt_eels import prepare_spectra as _prepare_spectra,validate_map_integrals,case_name
from .multislice_reference import fft_multislice_ni
from .multislice_emcd_reference import project_fft_amplitudes,coherence_from_amplitudes,complex_wave_diagnostics
from .diffraction import excitation_errors_angstrom_inv
from .emcd_angular_plots import decorate_reciprocal_map
from .wien2k_xmcd import load_wien2k_xmcd
from .xmcd_basis_convergence import selected_energy_grid
from .ni_017_geometry import rotated_tensor as effective_tensor_from_xmcd
from .single_channeling_tensor import run_tensor_with_coherence

GEO=Ni017Geometry()

@dataclass(frozen=True)
class Config(MistiltConfig):
    fixed_y_mrad: float=0.
    potential_cutoff: float=2.2
    beam_cutoff: float=3.2
    l3_energy_ev: float=831.271
    l2_energy_ev: float=848.698


def feature_windows(cfg):
    return {'L3':(cfg.l3_energy_ev-5,cfg.l3_energy_ev+5),'L2':(cfg.l2_energy_ev-5,cfg.l2_energy_ev+5)}


def prepare_spectra(data,cfg):return _prepare_spectra(data,cfg,edge_windows=feature_windows(cfg))


def model(cfg,offset):
    return GEO.model(offset,kv=cfg.acceleration_kv,beam_cutoff=cfg.beam_cutoff,potential_cutoff=cfg.potential_cutoff)


def propagate(*args,**kwargs):return fft_multislice_ni(*args,**kwargs,projected_geometry=GEO)


def geometry(cfg,offset,m):
    tx,ty=m.elastic.microscope.tilt_mrad_xy;ki=m.elastic.microscope.incident_k_xy
    s=excitation_errors_angstrom_inv(m.elastic);g=m.elastic.crystal.g_vector((2,0,0))
    return dict(delta_x_mrad=float(offset),theta_x_mrad=tx,theta_y_mrad=ty,total_tilt_mrad=float(np.hypot(tx,ty)),
        s200_inv_angstrom=float(s[m.elastic.beams.hkl.index((2,0,0))]),
        coordinate_markers=dict(nominal_zone_axis=[0,1,7],transmitted_q_cycles_per_angstrom=[0.,0.],
            zone_axis_q_cycles_per_angstrom=(-ki).tolist()),
        magnetization_cubic=[0,0,1],magnetization_local=(GEO.frame@np.array([0.,0.,1.])).tolist(),
        beam_hkl=m.elastic.beams.hkl,excitation_errors_inv_angstrom=s.tolist(),target_hkl=[2,0,0],
        thales_center_q_xy=(g[:2]/2).tolist(),thales_radius_inv_angstrom=float(np.linalg.norm(g)/2),
        detectors={k:dict(center_q_xy=d.center_q_xy,radius_q=d.radius_q) for k,d in m.detectors.items()})


def initial(source,cfg):
    cfg.validate()
    if cfg.fixed_y_mrad!=0:raise ValueError('The [017] horizontal scan requires fixed local y=0')
    audit=energy_audit(source)
    if not np.allclose([cfg.l3_energy_ev,cfg.l2_energy_ev],list(audit['selected_magnetic_energies_ev'].values()),atol=1e-6,rtol=0):raise ValueError('Map energies must match verified native magnetic features')
    s=load_wien2k_xmcd(source);edge,selected=selected_energy_grid(s.energy_ev,dict(L3=cfg.l3_energy_ev,L2=cfg.l2_energy_ev))
    energy=np.unique(np.r_[np.linspace(s.energy_ev[0],s.energy_ev[-1],cfg.energy_points),edge])
    m=model(cfg,0.);n=len(m.elastic.beams.hkl);estimate=64*cfg.detector_grid**2*n*n/2**20
    if estimate>cfg.max_kernel_mib:raise ValueError('Dense inelastic kernel exceeds memory limit')
    GEO.harmonics(cfg.fft_grid,max(cfg.potential_cutoff,cfg.beam_cutoff))
    files=('ni_710_geometry','ni_017_geometry','ni_017_mistilt','ni_mistilt_series','ni_mistilt_eels','multislice_reference',
           'single_channeling_tensor','physical_elastic','scattering','geometry','xmcd_effective_mdff')
    hashes={f:hashlib.sha256(Path(__file__).with_name(f+'.py').read_bytes()).hexdigest() for f in files}
    provenance=dict(config={k:v for k,v in asdict(cfg).items() if k not in ('start_mrad','stop_mrad','step_mrad')},
        source_sha256=s.source_sha256,frame_cubic_to_local=GEO.frame.tolist(),implementation_sha256=hashes,
        selected_energies_ev=selected,energy_ev=energy.tolist())
    signature=hashlib.sha256(json.dumps(provenance,sort_keys=True).encode()).hexdigest()
    return energy,selected,provenance,signature,estimate


def csv_write(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def selected_observables(source,cfg,m,c):
    energies,selected=selected_energy_grid(load_wien2k_xmcd(source).energy_ev,dict(L3=cfg.l3_energy_ev,L2=cfg.l2_energy_ev))
    p,n=[run_tensor_with_coherence(m,effective_tensor_from_xmcd(source,energies,eta=sign*cfg.eta,beta=cfg.beta),c,
         thickness_nm=cfg.thickness_nm,grid_size=17,integration_mode='fractional',aperture_subpixels=64) for sign in (1,-1)]
    rows=[]
    for edge in EDGES:
        i=int(np.argmin(abs(energies-selected[edge])));a,b,am,bm=[r.chiral_spectrum(g)[i] for r,g in ((p,'A'),(p,'B'),(n,'A'),(n,'B'))]
        rows.append(dict(edge=edge,energy_ev=selected[edge],nonmagnetic_difference=float((a+am-b-bm)/2),
            magnetic_difference=float((a-b-am+bm)/2),detector_total=float((a+b+am+bm)/2)))
    return rows


def controls(source,root,cfg):
    """Independent one-dimensional controls, not a Cartesian parameter sweep."""
    z=np.linspace(0,cfg.thickness_nm,cfg.depth_steps);common=GEO.beams(2.2).hkl
    def gather(m,psi,outside=None):
        c=coherence_from_amplitudes(z,psi);pop=abs(psi)**2;hkl=m.elastic.beams.hkl
        pair=[hkl.index(h) for h in ((0,0,0),(2,0,0))]
        return c,dict(pair_exit=float(pop[-1,pair].sum()),pair_depth_average=float(np.diag(c).real[pair].sum()),
                       max_other_sampled=float(np.max(1-pop[:,pair].sum(axis=1))))
    records=[];basis_waves=[]
    for cut in (2.2,3.2,4.5):
        m=GEO.model(beam_cutoff=cut,potential_cutoff=cfg.potential_cutoff)
        psi=m.elastic.amplitudes(z);c,purity=gather(m,psi)
        ix=[m.elastic.beams.hkl.index(h) for h in common]
        basis_waves.append((psi[:,ix],c[np.ix_(ix,ix)]))
        for row in selected_observables(source,cfg,m,c):records.append(dict(beam_cutoff=cut,beam_count=len(m.elastic.beams.hkl),potential_cutoff=cfg.potential_cutoff,**purity,**row))
    for i in range(3):
        wave,c=basis_waves[i];ref,cref=basis_waves[-1]
        diag=complex_wave_diagnostics(ref,wave)
        for r in records[i*2:i*2+2]:r.update(common_coherence_error=float(np.linalg.norm(c-cref)),
            common_amplitude_error=float(np.max(abs(wave-ref))),phase_aligned_error=float(np.max(diag['amplitude_max_abs_aligned'])))
    csv_write(root/'basis_convergence.csv',records)
    mesh_records=[];mesh=[];cm=GEO.model(beam_cutoff=2.2,potential_cutoff=cfg.potential_cutoff)
    for grid in (16,32,64):
        f=propagate(z,tilt_mrad_xy=cm.elastic.microscope.tilt_mrad_xy,grid_points=grid,
            slice_step_nm=cfg.slice_step_nm,potential_cutoff_inv_angstrom=cfg.potential_cutoff,return_amplitudes=True)
        psi,out=project_fft_amplitudes(f,common);c,purity=gather(cm,psi,out);mesh.append((psi,c))
        for row in selected_observables(source,cfg,cm,c):mesh_records.append(dict(fft_grid=grid,potential_cutoff=cfg.potential_cutoff,
            common_beam_count=len(common),projection_outside_max=float(out.max()),norm_error=f.norm_error,**purity,**row))
    for i,(wave,c) in enumerate(mesh):
        ref,cref=mesh[-1];diag=complex_wave_diagnostics(ref,wave)
        for r in mesh_records[i*2:i*2+2]:r.update(common_coherence_error=float(np.linalg.norm(c-cref)),
            common_amplitude_error=float(np.max(abs(wave-ref))),phase_aligned_error=float(np.max(diag['amplitude_max_abs_aligned'])))
    csv_write(root/'fft_mesh_convergence.csv',mesh_records)
    potential_rows=[]
    for cut in (.75,2.2,3.2):
        m=GEO.model(beam_cutoff=4.5,potential_cutoff=cut);c,purity=gather(m,m.elastic.amplitudes(z))
        for row in selected_observables(source,cfg,m,c):potential_rows.append(dict(potential_cutoff=cut,beam_cutoff=4.5,beam_count=len(m.elastic.beams.hkl),**purity,**row))
    csv_write(root/'potential_cutoff_convergence.csv',potential_rows)
    step_rows=[];ref_model=model(cfg,0.);bw=ref_model.elastic.amplitudes(z)
    for step in (.04,.02):
        f=propagate(z,tilt_mrad_xy=ref_model.elastic.microscope.tilt_mrad_xy,grid_points=32,
            slice_step_nm=step,potential_cutoff_inv_angstrom=cfg.potential_cutoff,return_amplitudes=True)
        psi,out=project_fft_amplitudes(f,ref_model.elastic.beams.hkl);c,purity=gather(ref_model,psi)
        for row in selected_observables(source,cfg,ref_model,c):step_rows.append(dict(slice_step_nm=step,
            coherence_bw_error=float(np.linalg.norm(c-coherence_from_amplitudes(z,bw))),outside_max=float(out.max()),**row))
    csv_write(root/'slice_step_convergence.csv',step_rows)
    ideal=GEO.model(ideal=True,potential_cutoff=cfg.potential_cutoff)
    ci=coherence_from_amplitudes(z,ideal.elastic.amplitudes(z))
    csv_write(root/'ideal_two_beam_reference.csv',[dict(model='Strict ideal 000/200 truncation, not full multibeam',**r) for r in selected_observables(source,cfg,ideal,ci)])
    # Numerical criterion chosen explicitly; failure does not cause beam suppression.
    full=model(cfg,0.);psi=full.elastic.amplitudes(z);c,purity=gather(full,psi)
    s=excitation_errors_angstrom_inv(full.elastic);reflection=[]
    for j,h in enumerate(full.elastic.beams.hkl):reflection.append(dict(h=h[0],k=h[1],l=h[2],s_g_inv_angstrom=float(s[j]),
        exit_intensity=float(abs(psi[-1,j])**2),depth_average_intensity=float(c[j,j].real),max_sampled_intensity=float(np.max(abs(psi[:,j])**2))))
    csv_write(root/'reference_competing_reflections.csv',reflection)
    write_json(root/'reference_two_beam_quality.json',dict(criterion='At most 5% outside 000/200 at every saved depth',
        passes_strict_criterion=purity['max_other_sampled']<=.05,**purity,
        interpretation='Exact Bragg candidate is retained as full multibeam even if the purity criterion fails'))


def run(source,root,cfg=Config(),plot_only=False):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    energy,selected,prov,signature,memory=initial(source,cfg)
    settings=root/'run_settings.json'
    if settings.exists() and json.loads(settings.read_text())['signature']!=signature:raise ValueError('Existing settings differ; preserve output and use a new directory')
    if not settings.exists():write_json(settings,dict(signature=signature,provenance=prov))
    m=model(cfg,0.)
    write_json(root/'energy_alignment.json',energy_audit(source))
    write_json(root/'geometry_validation.json',dict(frame_cubic_to_local=GEO.frame.tolist(),frame_determinant=float(np.linalg.det(GEO.frame)),
        frame_orthonormal=bool(np.allclose(GEO.frame@GEO.frame.T,np.eye(3))),nominal_zone_axis=[0,1,7],target_hkl=[2,0,0],
        zolz_condition='k+7l=0; FCC h,k,l same parity',fft_mapping='(m,n)->(m,7n,-n)',
        projected_rectangular_cell_lengths_angstrom=[GEO.a_angstrom,GEO.a_angstrom/np.sqrt(50)],
        reciprocal_steps_cycles_per_angstrom=[1/GEO.a_angstrom,np.sqrt(50)/GEO.a_angstrom],
        first_off_row_g_inv_angstrom=float(np.sqrt(51)/GEO.a_angstrom),reference=geometry(cfg,0.,m),
        dense_pair_array_estimate_mib=memory,potential='z-independent projected IAM, not atom-layer 3D multislice',
        magnetization_convention='Cubic [001] magnetization; eta reversal in cubic frame before R T R^T; beta preserved',magnetization_cubic=[0,0,1],magnetization_local=(GEO.frame@np.array([0.,0.,1.])).tolist()))
    if not plot_only and not (root/'slice_step_convergence.csv').exists():controls(source,root,cfg)
    cases=[];metas=[];rows=[]
    for offset in cfg.offsets():
        folder=root/case_name(offset);folder.mkdir(exist_ok=True);path=folder/'checkpoint.npz';info=folder/'metadata.json'
        if path.exists() and info.exists():
            meta=json.loads(info.read_text())
            if hashlib.sha256(path.read_bytes()).hexdigest()!=meta['npz_sha256']:raise ValueError('Checkpoint checksum differs')
            with np.load(path,allow_pickle=False) as f:data={k:f[k] for k in f.files}
            validate_checkpoint(data,meta,signature,offset);records=meta['rows']
            print(f'{offset:+.1f}: validated checkpoint reused',flush=True)
        elif plot_only:raise ValueError('Missing complete checkpoint')
        else:
            data,meta,records=calculate_case(source,cfg,offset,energy,selected,model_factory=model,
                propagator=propagate,geometry_factory=geometry,target_key='s200_inv_angstrom',tensor_factory=rotated_tensor,edge_windows=feature_windows(cfg))
            meta.update(signature=signature,rows=records)
            validate_checkpoint(data,meta,signature,offset)
            temp=folder/'checkpoint.partial.npz';np.savez_compressed(temp,**data);temp.replace(path)
            meta['npz_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();write_json(info,meta)
        spectra,checks=prepare_spectra(data,cfg);error=validate_map_integrals(data,spectra)
        if not plot_only:
            np.savez_compressed(folder/'virtual_detector_eels.npz',energy_ev=energy,method_labels=np.asarray(METHODS),**spectra)
            np.savez_compressed(folder/'angular_maps.npz',qx=data['qx'],qy=data['qy'],weights_A=data['weights_A'],weights_B=data['weights_B'],
                method_labels=np.asarray(METHODS),edge_labels=np.asarray(EDGES),selected_energy_ev=data['selected_energy_ev'],
                **{k:data['map__'+k] for k in MAP_KEYS})
        meta.update(map_eels_reconstruction_max_abs=error,normalization_validation=checks)
        cases.append(data);metas.append(meta);rows.extend(records)
    if not plot_only:
        np.savez_compressed(root/'mistilt_maps.npz',delta_x_mrad=cfg.offsets(),method_labels=np.asarray(METHODS),edge_labels=np.asarray(EDGES),
            selected_energy_ev=cases[0]['selected_energy_ev'],qx=cases[0]['qx'],qy=cases[0]['qy'],weights_A=cases[0]['weights_A'],weights_B=cases[0]['weights_B'],
            **{k:np.stack([c['map__'+k] for c in cases]) for k in MAP_KEYS})
        np.savez_compressed(root/'mistilt_eels.npz',energy_ev=energy,delta_x_mrad=cfg.offsets(),method_labels=np.asarray(METHODS),
            **{k:np.stack([prepare_spectra(c,cfg)[0][k] for c in cases]) for k in prepare_spectra(cases[0],cfg)[0]})
        csv_write(root/'mistilt_summary.csv',rows)
        write_json(root/'comparison_metadata.json',dict(config=asdict(cfg),signature=signature,provenance=prov,cases=metas,
            map_axes='mistilt, method, edge, qy, qx',spectral_axes='mistilt, method, energy',
            execution_head_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            limitations='Projected IAM; crystal-[001] XMCD-effective MDFF rotated by R T R^T; entrance-only; finite convergence controls, not quantitative Ni or full 3D multislice'))
    plots(root,cfg,cases,rows)


def plots(root,cfg,cases,rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    qx,qy=cases[0]['qx'],cases[0]['qy'];half=(qx[0,1]-qx[0,0])/2
    extent=(qx.min()-half,qx.max()+half,qy.min()-half,qy.max()+half);offsets=cfg.offsets()
    def decorate(ax,i):decorate_reciprocal_map(ax,model(cfg,offsets[i]),extent,target_hkl=(2,0,0),zone_axis=(0,1,7))
    limits={(key,edge):max(float(np.nanmax(abs(c['map__'+key][:,edge]))) for c in cases) for key in ('I_mag','I_nonmag','I_plus','D_raw','D_corrected') for edge in range(2)}
    for edge in range(2):
        limits['D_raw',edge]=limits['D_corrected',edge]=max(limits['D_raw',edge],limits['D_corrected',edge])
    for edge,label in enumerate(EDGES):
        for key,kind in (('I_mag','magnetic'),('I_nonmag','nonmagnetic'),('I_plus','total'),('D_corrected','corrected')):
            for method,name in enumerate(METHODS):
                cols=min(3,len(cases));nr=int(np.ceil(len(cases)/cols));fig,axes=plt.subplots(nr,cols,figsize=(4.1*cols,4.1*nr),squeeze=False,constrained_layout=True)
                limit=max(limits[key,edge],1e-30)
                for i,c in enumerate(cases):
                    ax=axes.flat[i];im=ax.imshow(c['map__'+key][method,edge],origin='lower',extent=extent,cmap='RdBu_r' if key in ('I_mag','D_corrected') else 'viridis',
                        vmin=-limit if key in ('I_mag','D_corrected') else 0,vmax=limit,interpolation='nearest')
                    decorate(ax,i);ax.set_title(f'Delta x={offsets[i]:+.1f} mrad\ntilt=({GEO.bragg_tilt()+offsets[i]:.3f}, 0) mrad',fontsize=8)
                for ax in list(axes.flat)[len(cases):]:ax.set_visible(False)
                fig.colorbar(im,ax=list(axes.flat)[:len(cases)],label='Relative intensity',shrink=.7)
                fig.suptitle(f'Ni [017], target (200) | {label} {cases[0]["selected_energy_ev"][edge]:.3f} eV | {kind} | {name}')
                fig.savefig(root/f'{label}_{kind}_{name}.png',dpi=140);plt.close(fig)
    for i,c in enumerate(cases):
        folder=root/case_name(offsets[i]);s,_=prepare_spectra(c,cfg);e=c['energy_ev']
        fig,axes=plt.subplots(2,3,figsize=(14,8),sharex=True,sharey='col',constrained_layout=True)
        for method in range(2):
            for col,keys in enumerate((('I_A_plus','I_B_plus'),('D_raw','D_mag','D_nonmag'),('D_corrected','D_mag','D_nonmag_residual_obs'))):
                ax=axes[method,col]
                for key in keys:ax.plot(e,s[key][method],label=key)
                for edge,energy in zip(EDGES,c['selected_energy_ev']):ax.axvline(energy,ls=':',color='.5');ax.text(energy,.96,f'{edge}\n{energy:.3f}',transform=ax.get_xaxis_transform(),va='top',fontsize=7)
                ax.axvspan(878,882,color='.5',alpha=.15);ax.set(xlabel='Energy (eV)',ylabel='Relative intensity',title=METHODS[method]);ax.legend(fontsize=7);ax.grid(alpha=.2)
        sg=geometry(cfg,offsets[i],model(cfg,offsets[i]))['s200_inv_angstrom']
        fig.suptitle(f'Ni [017] (200) | Delta x={offsets[i]:+.1f} mrad | absolute tilt=({GEO.bragg_tilt()+offsets[i]:.4f},0) mrad | s200={sg:+.7f} inverse A\nNative source energies; shaded 878-882 eV window; no peak rescaling')
        fig.savefig(folder/'virtual_detector_eels.png',dpi=140);plt.close(fig)
        for edge,label in enumerate(EDGES):
            fig,axes=plt.subplots(2,5,figsize=(18,7),constrained_layout=True)
            for col,key in enumerate(('I_mag','I_nonmag','I_plus','D_raw','D_corrected')):
                limit=max(limits[key,edge],1e-30);signed=key not in ('I_nonmag','I_plus')
                for method in range(2):
                    ax=axes[method,col];im=ax.imshow(c['map__'+key][method,edge],origin='lower',extent=extent,cmap='RdBu_r' if signed else 'viridis',vmin=-limit if signed else 0,vmax=limit,interpolation='nearest')
                    decorate(ax,i);ax.set_title(METHODS[method]+' '+key,fontsize=8)
                fig.colorbar(im,ax=axes[:,col].tolist(),shrink=.7)
            fig.suptitle(f'Ni [017], (200) | {label}, {c["selected_energy_ev"][edge]:.3f} eV | Delta x={offsets[i]:+.1f} mrad')
            fig.savefig(folder/f'{label}_angular_maps.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(14,8),constrained_layout=True)
    for ax,key in zip(axes.flat,('magnetic_asymmetry','nonmagnetic_asymmetry','raw_asymmetry','alpha','bw_ms_magnetic_map_l2_relative','bw_ms_coherence_relative')):
        for method in METHODS:
            for edge in EDGES:
                rs=[r for r in rows if r['method']==method and r['edge']==edge]
                ax.plot(offsets,[np.nan if r[key] is None else r[key] for r in rs],marker='o',ms=3,ls='-' if method==METHODS[0] else '--',label=method+' '+edge)
        ax.axvline(0,ls=':',color='.5');ax.set(title=key,xlabel='Delta x (mrad)');ax.legend(fontsize=6);ax.grid(alpha=.2)
    fig.savefig(root/'emcd_and_bw_ms_vs_mistilt.png',dpi=150);plt.close(fig)
    colors=plt.cm.viridis(np.linspace(0,1,len(cases)))
    for edge,label in enumerate(EDGES):
        fig,axes=plt.subplots(1,2,figsize=(12,4),sharey=True,constrained_layout=True)
        for method,ax in enumerate(axes):
            for i,c in enumerate(cases):
                exact=abs(offsets[i])<1e-12
                ax.plot(c['energy_ev'],c['spectra__D_mag'][method],color='black' if exact else colors[i],lw=2 if exact else 1,label=f'{offsets[i]:+.1f} mrad')
            center=cases[0]['selected_energy_ev'][edge];window=(center-5,center+5)
            ax.set(xlim=window,xlabel='Energy (eV), native source',ylabel='Magnetic difference (a.u.)',title=METHODS[method]);ax.legend(fontsize=6,ncol=2);ax.grid(alpha=.2)
            ax.axvline(cases[0]['selected_energy_ev'][edge],ls=':',color='.5')
        fig.suptitle(f'Ni [017] (200) | {label} requested reference window; no individual peak scaling')
        fig.savefig(root/f'{label}_emcd_vs_mistilt.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12,8),sharex=True,sharey='col',constrained_layout=True)
    for method in range(2):
        for col,key in enumerate(('D_raw','D_corrected')):
            for i,c in enumerate(cases):axes[method,col].plot(c['energy_ev'],c['spectra__'+key][method],color='black' if abs(offsets[i])<1e-12 else colors[i],label=f'{offsets[i]:+.1f} mrad')
            axes[method,col].set(xlabel='Energy (eV), native source',ylabel='Relative intensity',title=METHODS[method]+' '+key);axes[method,col].legend(fontsize=6,ncol=2);axes[method,col].grid(alpha=.2)
    fig.savefig(root/'raw_corrected_eels_vs_mistilt.png',dpi=150);plt.close(fig)
    for filename,xkey in (('basis_convergence.csv','beam_cutoff'),('fft_mesh_convergence.csv','fft_grid'),('potential_cutoff_convergence.csv','potential_cutoff')):
        records=list(csv.DictReader((root/filename).open()));fig,axes=plt.subplots(1,2,figsize=(10,4),constrained_layout=True)
        for edge in EDGES:
            rs=[r for r in records if r['edge']==edge]
            for ax,key in zip(axes,('nonmagnetic_difference','magnetic_difference')):ax.plot([float(r[xkey]) for r in rs],[float(r[key]) for r in rs],'-o',label=edge);ax.set(xlabel=xkey,title=key);ax.legend();ax.grid(alpha=.2)
        fig.savefig(root/(filename.replace('.csv','.png')),dpi=150);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('data/wien2k_ni/Ni_fm.xmcd'));p.add_argument('--output',type=Path,default=Path('outputs/ni_017_minorzone_mistilt'))
    p.add_argument('--plot-only',action='store_true');p.add_argument('--controls-only',action='store_true')
    defaults=Config()
    for name,value in asdict(defaults).items():p.add_argument('--'+name.replace('_','-'),type=type(value),default=value)
    args=vars(p.parse_args());source=args.pop('source');root=args.pop('output');po=args.pop('plot_only');co=args.pop('controls_only');cfg=Config(**args)
    if co:
        root.mkdir(parents=True,exist_ok=True);initial(source,cfg);controls(source,root,cfg)
    else:run(source,root,cfg,po)
