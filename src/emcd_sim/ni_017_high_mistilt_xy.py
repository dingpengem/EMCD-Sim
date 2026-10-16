"""Checkpointed [017] X/Y scan using the existing BW/MS and MDFF contraction."""
from __future__ import annotations
import argparse,hashlib,json,subprocess
from dataclasses import asdict
from pathlib import Path
import numpy as np
from .ni_017_geometry import Ni017Geometry,rotated_tensor,energy_audit
from .ni_017_mistilt import Config,initial,feature_windows,prepare_spectra,geometry,csv_write
from .ni_mistilt_series import calculate_case,validate_checkpoint,write_json,MAP_KEYS,METHODS,EDGES
from .ni_mistilt_eels import validate_map_integrals
from .multislice_reference import fft_multislice_ni
from .multislice_emcd_reference import coherence_from_amplitudes,project_fft_amplitudes
from .geometry import electron_wavelength_angstrom

GEO=Ni017Geometry()
ROOT=Path('outputs/ni_017_high_mistilt_xy')
SOURCE=Path('data/wien2k_ni/Ni_fm.xmcd')


def scans(kv=200.,mode='all',xs=None,ys=None):
    b=GEO.bragg_tilt(kv)
    horizontal=sorted(set(np.arange(-10.,11.,2.).tolist()+[b,-b]))
    vertical=np.arange(-30.,31.,5.).tolist()
    gridx=[-10.,-5.,0.,5.,10.];gridy=[-25.,-10.,0.,10.,25.]
    groups={}
    if mode in ('all','x'):groups['x']=[(x,0.) for x in (horizontal if xs is None else xs)]
    if mode in ('all','y'):groups['y']=[(0.,y) for y in (vertical if ys is None else ys)]
    if mode in ('all','xy'):groups['xy']=[(x,y) for y in (gridy if ys is None else ys) for x in (gridx if xs is None else xs)]
    if not groups or any(not np.isfinite(pair).all() for group in groups.values() for pair in group):raise ValueError('Invalid scan coordinates')
    unique=list(dict.fromkeys(p for group in groups.values() for p in group))
    return groups,unique


def tag(x,y):
    def number(v):return ('m' if v<0 else 'p')+format(abs(v),'.12g').replace('.','p')
    return 'x_'+number(x)+'_y_'+number(y)


def model(cfg,x,y):
    return GEO.model(x,y_offset=y,kv=cfg.acceleration_kv,beam_cutoff=cfg.beam_cutoff,potential_cutoff=cfg.potential_cutoff)


def geometry_xy(cfg,x,y,m):
    g=geometry(cfg,x,m);h=m.elastic.beams.hkl;s=g['excitation_errors_inv_angstrom']
    g.update(delta_y_mrad=float(y),s400_inv_angstrom=float(s[h.index((4,0,0))]),
        acceleration_kv=cfg.acceleration_kv,electron_wavelength_angstrom=electron_wavelength_angstrom(cfg.acceleration_kv),
        axes_convention='q relative to transmitted beam; ZA=-incident_k_xy; fixed physical apertures')
    return g


def propagate(*args,**kwargs):return fft_multislice_ni(*args,**kwargs,projected_geometry=GEO)


def setup(source,cfg):
    energy,selected,prov,_,memory=initial(source,cfg)
    # Plotting and summary code is deliberately outside the numerical checkpoint signature.
    files=('ni_017_high_mistilt_xy','ni_017_geometry','ni_017_mistilt','ni_710_geometry','ni_mistilt_series',
           'ni_mistilt_eels','multislice_reference','multislice_emcd_reference','single_channeling_tensor',
           'physical_elastic','scattering','geometry','xmcd_effective_mdff','xmcd_postedge_normalization','postedge_emcd_maps')
    prov['implementation_sha256']={f:hashlib.sha256(Path(__file__).with_name(f+'.py').read_bytes()).hexdigest() for f in files}
    prov['audit_inputs_sha256']=energy_audit(source)['input_sha256']
    prov['python_numpy']=[__import__('platform').python_version(),np.__version__]
    signature=hashlib.sha256(json.dumps(prov,sort_keys=True).encode()).hexdigest()
    return energy,selected,prov,signature,memory


def diffraction(data,m):
    h=m.elastic.beams.hkl;pair=[h.index(t) for t in ((0,0,0),(2,0,0))];other=[j for j in range(len(h)) if j not in pair]
    offrow=[j for j,t in enumerate(h) if t[2]!=0];out=[]
    for method,ak,ck in zip(METHODS,('bw_amplitudes','ms_amplitudes_projected'),('coherence_bw','coherence_ms')):
        pop=abs(data[ak])**2;avg=np.diag(data[ck]).real;dominant=max(other,key=lambda j:avg[j])
        out.append(dict(method=method,exit_populations=pop[-1].tolist(),depth_average_populations=avg.tolist(),
            max_sampled_populations=pop.max(axis=0).tolist(),pair_exit=float(pop[-1,pair].sum()),pair_depth_average=float(avg[pair].sum()),
            outside_pair_max=float(np.max(pop[:,other].sum(axis=1))),outside_pair_depth_average=float(avg[other].sum()),
            offrow_exit=float(pop[-1,offrow].sum()),offrow_depth_average=float(avg[offrow].sum()),
            dominant_competing_hkl=h[dominant],dominant_competing_depth_average=float(avg[dominant]),
            dominant_competing_exit=float(pop[-1,dominant]),total_projected_exit=float(pop[-1].sum())))
    return out


def export_case(folder,data,meta,cfg):
    spectra,checks=prepare_spectra(data,cfg)
    spectra['I_A_postedge']=spectra['I_A_plus'].copy()
    spectra['I_B_postedge']=spectra['alpha'][:,None]*spectra['I_B_plus']
    np.testing.assert_allclose(spectra['I_A_postedge']-spectra['I_B_postedge'],spectra['D_corrected'],atol=1e-14)
    error=validate_map_integrals(data,spectra)
    meta.update(map_eels_reconstruction_max_abs=error,normalization_validation=checks)
    np.savez_compressed(folder/'virtual_detector_eels.npz',energy_ev=data['energy_ev'],method_labels=np.asarray(METHODS),**spectra)
    np.savez_compressed(folder/'angular_maps.npz',qx=data['qx'],qy=data['qy'],weights_A=data['weights_A'],weights_B=data['weights_B'],
        method_labels=np.asarray(METHODS),edge_labels=np.asarray(EDGES),selected_energy_ev=data['selected_energy_ev'],
        **{k:data['map__'+k] for k in MAP_KEYS})
    write_json(folder/'metadata.json',meta)


def run(source=SOURCE,root=ROOT,cfg=Config(),mode='all',xs=None,ys=None,plot_only=False,no_plots=False,skip_convergence=False):
    root=Path(root);source=Path(source)
    groups,pairs=scans(cfg.acceleration_kv,mode,xs,ys)
    energy,selected,prov,signature,memory=setup(source,cfg)
    root.mkdir(parents=True,exist_ok=True);settings=root/'run_settings.json'
    if settings.exists():
        if json.loads(settings.read_text())['signature']!=signature:raise ValueError('Source/code/config mismatch; preserve existing results and use another output directory')
    elif plot_only:raise ValueError('Plot-only requires existing results')
    else:write_json(settings,dict(signature=signature,provenance=prov,config=asdict(cfg),execution_head_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
    manifest=root/'scan_manifest.json'
    previous=json.loads(manifest.read_text())['scans'] if manifest.exists() else {}
    previous.update({k:[list(p) for p in v] for k,v in groups.items()})
    write_json(manifest,dict(scans=previous,unique_pairs=[list(p) for p in dict.fromkeys(tuple(p) for v in previous.values() for p in v)],
        coordinate_definition='theta_x=theta_Bragg200+delta_x; theta_y=delta_y; mrad',special_offsets=dict(bragg400=GEO.bragg_tilt(cfg.acceleration_kv),zone_axis=-GEO.bragg_tilt(cfg.acceleration_kv))))
    write_json(root/'energy_alignment.json',energy_audit(source))
    write_json(root/'geometry_validation.json',dict(frame=GEO.frame.tolist(),determinant=float(np.linalg.det(GEO.frame)),magnetization_cubic=[0,0,1],
        magnetization_local=(GEO.frame@np.array([0,0,1])).tolist(),reference=geometry_xy(cfg,0,0,model(cfg,0,0)),dense_pair_array_estimate_mib=memory,
        zolz='k+7l=0; FCC parity; complete radial finite basis',projected_IAM=True,energy_shift_ev=0))
    print(f'{len(pairs)} unique requested cases; dense pair estimate {memory:.2f} MiB',flush=True)
    for x,y in pairs:
        folder=root/'cases'/tag(x,y);path=folder/'checkpoint.npz';info=folder/'metadata.json'
        if path.exists() and info.exists():
            meta=json.loads(info.read_text())
            if hashlib.sha256(path.read_bytes()).hexdigest()!=meta['npz_sha256']:raise ValueError('Corrupt checkpoint')
            with np.load(path,allow_pickle=False) as f:data={k:f[k] for k in f.files}
            validate_checkpoint(data,meta,signature,x)
            if meta['geometry']['delta_y_mrad']!=y:raise ValueError('Y coordinate mismatch')
            print(f'({x:+.6g},{y:+.6g}) validated checkpoint reused',flush=True)
        elif plot_only:raise ValueError('Missing requested case '+str((x,y)))
        else:
            folder.mkdir(parents=True,exist_ok=True)
            print(f'RUN ({x:+.6g},{y:+.6g})',flush=True)
            data,meta,rows=calculate_case(source,cfg,x,energy,selected,model_factory=lambda c,d:model(c,d,y),propagator=propagate,
                geometry_factory=lambda c,d,m:geometry_xy(c,d,y,m),tensor_factory=rotated_tensor,edge_windows=feature_windows(cfg))
            for r in rows:r['delta_y_mrad']=float(y)
            meta.update(signature=signature,rows=rows,diffraction=diffraction(data,model(cfg,x,y)))
            validate_checkpoint(data,meta,signature,x)
            temp=folder/'checkpoint.partial.npz';np.savez_compressed(temp,**data);temp.replace(path)
            meta['npz_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            export_case(folder,data,meta,cfg)
    from .ni_017_high_mistilt_analysis import summarize,plots
    summarize(root,cfg)
    if not skip_convergence and not plot_only:
        from .ni_017_high_mistilt_convergence import controls
        controls(source,root,cfg)
    if not no_plots:plots(root,cfg)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=SOURCE);p.add_argument('--output',type=Path,default=ROOT)
    p.add_argument('--scan',choices=('all','x','y','xy'),default='all')
    p.add_argument('--x-list',type=float,nargs='+');p.add_argument('--y-list',type=float,nargs='+')
    p.add_argument('--plot-only',action='store_true');p.add_argument('--no-plots',action='store_true');p.add_argument('--skip-convergence',action='store_true')
    p.add_argument('--resume',action='store_true',help='Validated resume is always enabled')
    for key in ('potential_cutoff','beam_cutoff','fft_grid','slice_step_nm','thickness_nm','depth_steps','detector_grid','energy_points'):
        v=getattr(Config(),key);p.add_argument('--'+key.replace('_','-'),type=type(v),default=v)
    a=p.parse_args();cfg=Config(**{k:getattr(a,k) for k in ('potential_cutoff','beam_cutoff','fft_grid','slice_step_nm','thickness_nm','depth_steps','detector_grid','energy_points')})
    run(a.source,a.output,cfg,a.scan,a.x_list,a.y_list,a.plot_only,a.no_plots,a.skip_convergence)


if __name__=='__main__':main()
