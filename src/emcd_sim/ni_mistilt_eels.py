"""Export individual mistilt EELS from validated checkpoints; no forward physics."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

from .ni_mistilt_series import MistiltConfig, METHODS, EDGES, setup, validate_checkpoint, write_json
from .xmcd_postedge_normalization import analyze_postedge_spectra


def case_name(offset):
    if abs(offset)<1e-12:return 'case_0p0_exact_bragg'
    value=np.format_float_positional(abs(float(offset)),trim='-')
    if '.' not in value:value+='.0'
    return 'case_'+('m' if offset<0 else 'p')+value.replace('.','p')


def prepare_spectra(data,cfg,*,edge_windows=None):
    energy=data['energy_ev'];methods=[];checks=[]
    for method in range(2):
        a,b,c,d=[data['spectra__'+k][method] for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')]
        analysis=analyze_postedge_spectra(energy,a,b,c,d,
            windows=((cfg.postedge_start_ev,cfg.postedge_end_ev),),edge_windows=edge_windows)
        s=analysis.spectra
        keys=('I_A_plus','I_B_plus','I_A_minus','I_B_minus','N_A','N_B','M_A','M_B',
              'D_raw','D_mag','D_nonmag','Sigma_ref','D_corrected','D_mag_processed_obs','D_nonmag_residual_obs')
        result={k:s[k][0].copy() if s[k].ndim==2 else s[k].copy() for k in keys}
        result['alpha']=float(s['alpha_obs'][0])
        result['D_raw_minus']=c-d
        for key in ('D_raw','D_mag','D_nonmag','D_corrected','D_mag_processed_obs','D_nonmag_residual_obs'):
            np.testing.assert_allclose(result[key],data['spectra__'+key][method],rtol=1e-12,atol=1e-14)
        np.testing.assert_allclose(result['alpha'],data['alpha'][method],rtol=1e-13)
        np.testing.assert_allclose(result['D_raw'],result['D_mag']+result['D_nonmag'],atol=1e-14)
        np.testing.assert_allclose(result['D_raw_minus'],-result['D_mag']+result['D_nonmag'],atol=1e-14)
        np.testing.assert_allclose(result['D_corrected'],result['D_mag_processed_obs']+result['D_nonmag_residual_obs'],atol=1e-14)
        floor=1e-10*float(np.max(result['Sigma_ref']))
        result['denominator_floor']=floor
        result['valid_intensity']=np.isfinite([a,b,c,d]).all(axis=0)&(np.min([a,b,c,d],axis=0)>=0)
        result['valid_alpha']=bool(np.isfinite(result['alpha']) and result['alpha']>0)
        result['valid_corrected']=np.isfinite(result['D_corrected'])&result['valid_intensity']&result['valid_alpha']
        for name,num,den in (('raw_asymmetry',a-b,a+b),('magnetic_asymmetry',result['D_mag'],result['Sigma_ref']),
                              ('nonmagnetic_asymmetry',result['D_nonmag'],result['Sigma_ref'])):
            valid=np.isfinite(num)&np.isfinite(den)&(den>floor)
            result['valid_'+name]=valid
            result[name]=np.divide(num,den,out=np.full_like(den,np.nan),where=valid)
        methods.append(result)
        checks.append(dict(method=METHODS[method],normalization=analysis.metadata,
                           undefined_counts={k:int((~v).sum()) for k,v in result.items() if k.startswith('valid_') and np.ndim(v)==1}))
    return {k:np.asarray([s[k] for s in methods]) for k in methods[0]},checks


def validate_map_integrals(data,spectra):
    dq2=float((data['qx'][0,1]-data['qx'][0,0])**2);maximum=0.
    for edge,energy in enumerate(data['selected_energy_ev']):
        i=int(np.argmin(abs(data['energy_ev']-energy)))
        for state in ('plus','minus'):
            field=data['map__I_'+state][:,edge]
            for group in ('A','B'):
                got=np.sum(field*data['weights_'+group],axis=(-2,-1))*dq2
                target=spectra['I_'+group+'_'+state][:,i]
                np.testing.assert_allclose(got,target,rtol=1e-11,atol=1e-14)
                maximum=max(maximum,float(np.max(abs(got-target))))
        for key in ('D_raw','D_mag','D_nonmag','D_corrected'):
            got=np.sum(np.nan_to_num(data['map__'+key][:,edge])*data['weights_A'],axis=(-2,-1))*dq2
            np.testing.assert_allclose(got,spectra[key][:,i],rtol=1e-11,atol=1e-14)
            maximum=max(maximum,float(np.max(abs(got-spectra[key][:,i]))))
    return maximum


def export(source,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    root=Path(output);main=json.loads((root/'mistilt_metadata.json').read_text());cfg=MistiltConfig(**main['config'])
    _,_,provenance=setup(source,cfg)
    if provenance['signature']!=main['provenance']['signature']:raise ValueError('Source/configuration/code differs from saved sweep')
    # Existing aggregate physical outputs and all checkpoints remain immutable.
    existing={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir() if p.is_file()}
    offsets=cfg.offsets();cases=[];records=[];script_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    for offset in offsets:
        path=root/'checkpoints'/f'{float(offset):+.6f}.npz';meta=json.loads(path.with_suffix('.json').read_text())
        if hashlib.sha256(path.read_bytes()).hexdigest()!=meta['npz_sha256']:raise ValueError('Checkpoint checksum mismatch')
        with np.load(path,allow_pickle=False) as f:data={k:f[k] for k in f.files}
        validate_checkpoint(data,meta,provenance['signature'],offset)
        spectra,checks=prepare_spectra(data,cfg);error=validate_map_integrals(data,spectra)
        cases.append((data,spectra,meta))
        records.append(dict(delta_x_mrad=float(offset),map_detector_reconstruction_max_abs=error,
            parity_and_corrected_identities=True,common_detector_weights_and_mdff=True,methods=checks))
    limits=[]
    for keys in (('I_A_plus','I_B_plus'),('D_raw','D_mag','D_nonmag'),('D_corrected','D_mag','D_nonmag_residual_obs')):
        lo=min(float(np.min(s[k])) for _,s,_ in cases for k in keys);hi=max(float(np.max(s[k])) for _,s,_ in cases for k in keys)
        margin=.06*max(hi-lo,1e-30);limits.append((min(lo,0)-margin,hi+margin))
    for index,(data,s,meta) in enumerate(cases):
        folder=root/case_name(offsets[index]);folder.mkdir(exist_ok=True)
        fingerprint=dict(checkpoint_sha256=meta['npz_sha256'],exporter_sha256=script_hash)
        info=folder/'metadata.json';npz=folder/'virtual_detector_eels.npz';png=folder/'virtual_detector_eels.png'
        if info.exists():
            old=json.loads(info.read_text())
            if old['fingerprint']!=fingerprint:raise ValueError(f'Existing individual export differs: {folder}; preserve it before replacing')
            if npz.exists() and png.exists() and old.get('npz_sha256')==hashlib.sha256(npz.read_bytes()).hexdigest() and old.get('figure_sha256')==hashlib.sha256(png.read_bytes()).hexdigest():
                print(folder.name+': reused validated complete export',flush=True);continue
        fig,axes=plt.subplots(2,3,figsize=(15,8),sharex=True,sharey='col',constrained_layout=True)
        e=data['energy_ev']
        for method in range(2):
            for k,label in (('I_A_plus','A +M'),('I_B_plus','B +M')):axes[method,0].plot(e,s[k][method],label=label)
            for k,label in (('D_raw','Raw A-B'),('D_mag','Magnetic odd'),('D_nonmag','Nonmagnetic even')):axes[method,1].plot(e,s[k][method],label=label)
            for k,label in (('D_corrected','Post-edge corrected'),('D_mag','Unprocessed magnetic odd'),('D_nonmag_residual_obs','Even residual')):axes[method,2].plot(e,s[k][method],label=label)
            for col,ax in enumerate(axes[method]):
                for edge,energy in zip(EDGES,data['selected_energy_ev']):
                    ax.axvline(energy,color='.4',ls=':',lw=.7)
                    ax.text(energy,.98,f'{edge}\n{energy:.3f}',transform=ax.get_xaxis_transform(),va='top',ha='right',fontsize=7)
                ax.axvspan(cfg.postedge_start_ev,cfg.postedge_end_ev,color='grey',alpha=.15)
                ax.set(xlabel='Energy loss (eV)',ylabel='Relative intensity (a.u.)',xlim=(e[0],e[-1]),ylim=limits[col],
                    title=METHODS[method]+(' | alpha='+f'{s["alpha"][method]:.6f}' if col==2 else ''))
                ax.legend(fontsize=7);ax.grid(alpha=.2);ax.ticklabel_format(axis='y',style='sci',scilimits=(0,0))
        g=meta['geometry']
        fig.suptitle(f"Delta x={offsets[index]:+.1f} mrad | absolute tilt=({g['theta_x_mrad']:.6f}, {g['theta_y_mrad']:+.1f}) mrad | "
            f"s200={g['s200_inv_angstrom']:+.7f} inverse A\nNative source energy axis; shaded 878-882 eV post-edge window; shared scales across all cases",fontsize=11)
        fig.savefig(png,dpi=160);plt.close(fig)
        np.savez_compressed(npz,energy_ev=e,method_labels=np.asarray(METHODS),selected_energy_ev=data['selected_energy_ev'],
            edge_labels=np.asarray(EDGES),postedge_window_ev=[cfg.postedge_start_ev,cfg.postedge_end_ev],
            postedge_window_mask=(e>=cfg.postedge_start_ev)&(e<=cfg.postedge_end_ev),**s)
        write_json(info,dict(fingerprint=fingerprint,geometry=g,config=main['config'],source_sha256=provenance['source_sha256'],
            committed_simulation_implementation=main.get('committed_implementation',main['software_commit']),
            export_execution_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            array_axes='method, energy; alpha/denominator_floor/valid_alpha: method',method_labels=METHODS,
            selected_energies_ev=main['selected_energies_ev'],validation=records[index],
            undefined_policy='NaN normalized metrics with matching valid_* masks; never zero-filled',
            spectral_scale='Existing common source-peak tensor scale; no individual L3-peak scaling or display offsets',
            intensity_state='Panel A shows +M; NPZ retains both reversal states',
            physical_limitations=main['physical_limitations'],npz_sha256=hashlib.sha256(npz.read_bytes()).hexdigest(),
            figure_sha256=hashlib.sha256(png.read_bytes()).hexdigest()))
        print(folder.name+': full BW/MS spectra and figure saved',flush=True)
    colors=plt.cm.viridis(np.linspace(0,1,len(cases)))
    def curve(ax,i,e,y,label):
        exact=abs(offsets[i])<1e-12
        ax.plot(e,y,color='black' if exact else colors[i],lw=2 if exact else 1,label=label,zorder=5 if exact else 2)
    for edge,window in zip(EDGES,((844.,862.),(864.,874.))):
        fig,axes=plt.subplots(1,2,figsize=(12,4),sharey=True,constrained_layout=True)
        for method,ax in enumerate(axes):
            for i,(d,s,_) in enumerate(cases):curve(ax,i,d['energy_ev'],s['D_mag'][method],f'{offsets[i]:+.1f} mrad')
            energy=cases[0][0]['selected_energy_ev'][EDGES.index(edge)];ax.axvline(energy,color='.4',ls=':')
            ax.set(xlim=window,xlabel='Energy loss (eV)',ylabel='Magnetic-odd difference (a.u.)',title=METHODS[method]);ax.grid(alpha=.2);ax.legend(fontsize=6,ncol=2)
        fig.suptitle(edge+' requested reference window, native source axis; exact Bragg black; no per-case rescaling')
        fig.savefig(root/f'{edge}_emcd_vs_mistilt.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12,8),sharex=True,sharey='col',constrained_layout=True)
    for method in range(2):
        for col,key in enumerate(('D_raw','D_corrected')):
            ax=axes[method,col]
            for i,(d,s,_) in enumerate(cases):curve(ax,i,d['energy_ev'],s[key][method],f'{offsets[i]:+.1f} mrad')
            ax.set(xlabel='Energy loss (eV)',ylabel='Relative intensity (a.u.)',title=METHODS[method]+' | '+key)
            ax.grid(alpha=.2);ax.legend(fontsize=6,ncol=2)
    fig.suptitle('Raw versus corrected EELS; exact Bragg black; original amplitudes, no offsets')
    fig.savefig(root/'raw_corrected_eels_vs_mistilt.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    for method in range(2):
        for edge,label in enumerate(EDGES):
            indices=[int(np.argmin(abs(d['energy_ev']-d['selected_energy_ev'][edge]))) for d,_,_ in cases]
            for ax,key in ((axes[0,0],'magnetic_asymmetry'),(axes[0,1],'raw_asymmetry'),(axes[1,1],'D_nonmag_residual_obs')):
                ax.plot(offsets,[s[key][method,i] for (_,s,_),i in zip(cases,indices)],
                    color='C'+str(edge),ls='-' if method==0 else '--',marker='o',ms=3,label=METHODS[method]+' '+label)
        axes[1,0].plot(offsets,[s['alpha'][method] for _,s,_ in cases],'-o' if method==0 else '--o',ms=3,label=METHODS[method])
    for ax,title in zip(axes.flat,('Magnetic asymmetry (fraction)','Raw asymmetry (fraction)','Observed post-edge factor alpha','Residual even difference (a.u.)')):
        ax.axvline(0,color='black',ls=':',label='Exact Bragg');ax.set(xlabel='Delta theta_x from Bragg (mrad)',title=title);ax.grid(alpha=.2);ax.legend(fontsize=7)
    fig.savefig(root/'eels_mistilt_summary.png',dpi=160);plt.close(fig)
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in existing.items()),'Existing aggregate output changed'
    write_json(root/'individual_eels_validation.json',dict(case_count=len(cases),methods=METHODS,cases=records,
        existing_aggregate_files_unchanged=True,forward_calculations=0,exporter_sha256=script_hash))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path('data/wien2k_ni/Ni_fm.xmcd'))
    parser.add_argument('--output',type=Path,default=Path('outputs/ni_continuous_mistilt'))
    args=parser.parse_args();export(args.source,args.output)
