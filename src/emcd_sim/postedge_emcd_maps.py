"""Paired-aperture post-edge contrast with matched independent BW/MS propagation."""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, asdict, replace
import json
from pathlib import Path
import platform
import subprocess

import numpy as np

from .benchmark import nickel_physical_benchmark
from .crystal import fcc_nickel
from .elastic import BeamSet
from .elastic_reference import FourierCutoffPotential
from .scattering import IndependentAtomPotential
from .multislice_emcd_reference import MultisliceEMCDConfig, run_multislice_emcd_reference, scalar_discrepancy
from .single_channeling_tensor import run_tensor_with_coherence
from .wien2k_xmcd import load_wien2k_xmcd
from .xmcd_basis_convergence import selected_energy_grid
from .xmcd_effective_mdff import effective_tensor_from_xmcd
from .xmcd_postedge_normalization import analyze_postedge_spectra, _window_nodes, LABEL
from .xmcd_postedge_robustness import normalization_bias_diagnostics
from .xmcd_geometry_decomposition import _json_safe

METHODS = ('bloch', 'fft-multislice')
PAIRED = ('D_raw','D_corrected','D_mag','D_nonmag','D_mag_processed','D_nonmag_residual')


@dataclass(frozen=True)
class MapConfig(MultisliceEMCDConfig):
    conditions: tuple[str, ...] = ('near-2bc','symmetric-3bc')
    thickness_nm: tuple[float, ...] = (30.,)
    integration_mode: str = 'fractional'
    energy_points: int = 185
    energy_start: float = 837.
    postedge_start: float = 878.
    postedge_end: float = 882.
    l2_energy_ev: float = 870.

    def validate(self):
        super().validate()
        if (len(self.thickness_nm)!=1 or any(c not in ('near-2bc','symmetric-3bc') for c in self.conditions)
                or not isinstance(self.energy_points,int) or self.energy_points<3):
            raise ValueError('Require one thickness, supported paired geometries, and >=3 spectral points')
        if not np.isfinite([self.energy_start,self.postedge_start,self.postedge_end,self.l2_energy_ev]).all():
            raise ValueError('Spectral controls must be finite')


def paired_geometry(model, qx, qy, *, mode='fractional', subpixels=64):
    """Validate physical aperture bijection before using the y-index reflection."""
    qx,qy=np.asarray(qx),np.asarray(qy)
    if (qx.ndim!=2 or qx.shape!=qy.shape or not np.allclose(qx,qx[::-1],rtol=0,atol=1e-14)
            or not np.allclose(qy,-qy[::-1],rtol=0,atol=1e-14)):
        raise ValueError('Pairing requires a reflection-symmetric Cartesian q grid')
    groups=model.chiral_groups or {'A':('A',),'B':('B',)}
    expected=[({'A'},{'B'}),({'RU','LD'},{'RD','LU'})]
    if (set(model.detectors)!=set(groups['A'])|set(groups['B'])
            or (set(groups['A']),set(groups['B'])) not in expected):
        raise ValueError('Unsupported detector grouping for qy reflection')
    weights={k:d.integration_weights(qx,qy,mode=mode,subpixels=subpixels) for k,d in model.detectors.items()}
    mapping={}
    for a in groups['A']:
        da=model.detectors[a];target=(da.center_q_xy[0],-da.center_q_xy[1])
        matches=[b for b in groups['B'] if np.allclose(model.detectors[b].center_q_xy,target,rtol=0,atol=1e-14)
                 and abs(model.detectors[b].radius_q-da.radius_q)<1e-14]
        if len(matches)!=1:raise ValueError('Physical A aperture has no unique reflected B aperture')
        b=matches[0];mapping[a]=b
        if not np.allclose(weights[a],weights[b][::-1],rtol=0,atol=1e-14):
            raise ValueError('Reflected fractional aperture weights do not match')
    if set(mapping.values())!=set(groups['B']):raise ValueError('Detector reflection is not bijective')
    for d in model.detectors.values():
        if not d.integration_info(qx,qy,mode=mode,subpixels=subpixels)['aperture_fully_covered']:
            raise ValueError('Paired apertures must be fully covered')
    wa=sum(weights[k] for k in groups['A']);wb=sum(weights[k] for k in groups['B'])
    if np.any((wa>0)&(wb>0)) or not wa.any():raise ValueError('Paired A/B supports overlap or are empty')
    return dict(weights_A=wa,weights_B=wb,valid=wa>0,physical_weights=weights,mapping=mapping,
                dq2=float((qx[0,1]-qx[0,0])*(qy[1,0]-qy[0,0])))


def paired_maps(plus, minus, alpha, geometry):
    """Keep intrinsic parity intensities separate from A-supported contrasts."""
    p,m=np.asarray(plus,float),np.asarray(minus,float)
    valid=geometry['valid']
    if p.shape!=valid.shape or m.shape!=p.shape or not np.isfinite([p,m]).all() or not np.isfinite(alpha):
        raise ValueError('Require finite matched maps and a finite scalar detector factor')
    n,mag=(p+m)/2,(p-m)/2
    maps=dict(I_plus=p.copy(),I_minus=m.copy(),I_mag=mag,I_nonmag=n)
    values=dict(I_A_plus=p,I_B_plus_paired=p[::-1],I_A_minus=m,I_B_minus_paired=m[::-1],
        D_raw=p-p[::-1],D_corrected=p-alpha*p[::-1],D_mag=mag-mag[::-1],
        D_nonmag=n-n[::-1],D_mag_processed=mag-alpha*mag[::-1],D_nonmag_residual=n-alpha*n[::-1])
    maps.update({k:np.where(valid,v,np.nan) for k,v in values.items()})
    scale=max(float(np.max(abs(p))),1e-30)
    for total,a,b in [('D_raw','D_mag','D_nonmag'),('D_corrected','D_mag_processed','D_nonmag_residual')]:
        if not np.allclose(maps[total][valid],(maps[a]+maps[b])[valid],rtol=1e-12,atol=1e-13*scale):
            raise ArithmeticError('Pointwise paired-map parity identity failed')
    return maps


def integrate_paired(field, geometry):
    return float(np.sum(np.where(geometry['valid'],field,0.)*geometry['weights_A'])*geometry['dq2'])


def map_error(a,b,geometry,intensity_scale):
    """Area-weighted L2 differences; detector-intensity floor avoids canceled ratios."""
    w=geometry['weights_A'];mask=geometry['valid'];dq2=geometry['dq2']
    def norm(x):return float(np.sqrt(np.sum(w[mask]*x[mask]**2)*dq2))
    delta=b-a;absolute=norm(delta);ref=max(norm(a),norm(b));floor=1e-10*intensity_scale
    return dict(max_abs=float(np.max(abs(delta[mask]))),l2_abs=absolute,
                l2_relative=absolute/ref if ref>floor else np.nan,relative_valid=bool(ref>floor),
                relative_floor=floor)


def run_map_comparison(source_path, config=MapConfig()):
    config.validate()
    source=load_wien2k_xmcd(source_path)
    if not source.energy_ev[0]<=config.energy_start<source.energy_ev[-1]:raise ValueError('Invalid spectral start; no extrapolation')
    energy=np.linspace(config.energy_start,source.energy_ev[-1],config.energy_points)
    _window_nodes(energy,(config.postedge_start,config.postedge_end))
    for interval in ((844.,862.),(864.,874.)):_window_nodes(energy,interval)
    map_energy,selected=selected_energy_grid(source.energy_ev,{'L3':config.energy_ev,'L2':config.l2_energy_ev})
    print('Calculating independent propagation and common-basis coherences',flush=True)
    reference=run_multislice_emcd_reference(source_path,config)
    crystal=fcc_nickel();beams=BeamSet.zolz(crystal,config.beam_cutoff,config.max_beams)
    potential=FourierCutoffPotential(IndependentAtomPotential(crystal,
        debye_waller_b_angstrom2=config.b_factor_angstrom2),config.potential_cutoff)
    tensors=[effective_tensor_from_xmcd(source_path,energy,eta=sign*config.eta,beta=config.beta) for sign in (1,-1)]
    # Actual source energies for maps, independently of interpolated spectral grid.
    mtensors=[effective_tensor_from_xmcd(source_path,map_energy,eta=sign*config.eta,beta=config.beta) for sign in (1,-1)]
    cases=[];rows=[]
    for case in reference.cases:
        condition=case['condition'];tilt=reference.metadata['geometries'][condition]['tilt_mrad_xy']
        model=nickel_physical_benchmark(acceleration_kv=config.acceleration_kv,tilt_mrad_xy=tilt,
            beams_override=beams,diffraction_condition=condition)
        model=replace(model,elastic=replace(model.elastic,potential=potential))
        qx,qy=case['qx_inv_angstrom'],case['qy_inv_angstrom']
        geometry=paired_geometry(model,qx,qy,mode=config.integration_mode,subpixels=config.aperture_subpixels)
        methods=[]
        for method,coherence in zip(METHODS,(case['coherence_bw'],case['coherence_ms'])):
            print(f'{condition} / {method}: detector spectra and selected maps',flush=True)
            opts=dict(thickness_nm=config.thickness_nm[0],grid_size=config.detector_grid,
                integration_mode=config.integration_mode,aperture_subpixels=config.aperture_subpixels)
            rp,rm=[run_tensor_with_coherence(model,t,coherence,**opts,reference_energy_ev=selected['L3']) for t in tensors]
            result=analyze_postedge_spectra(energy,rp.chiral_spectrum('A'),rp.chiral_spectrum('B'),
                rm.chiral_spectrum('A'),rm.chiral_spectrum('B'),windows=((config.postedge_start,config.postedge_end),))
            result.spectra.update(normalization_bias_diagnostics(result))
            alpha=float(result.spectra['alpha_obs'][0]);oracle=float(result.spectra['alpha_nonmag'][0])
            maps=[]
            for edge in ('L3','L2'):
                sp,sm=[run_tensor_with_coherence(model,t,coherence,**opts,reference_energy_ev=selected[edge]) for t in mtensors]
                p=sp.nonmag_map_at_l3+sp.magnetic_map_at_l3;m=sm.nonmag_map_at_l3+sm.magnetic_map_at_l3
                fields=paired_maps(p,m,alpha,geometry)
                ia,ib,ima,imb=[float(r.chiral_spectrum(g)[int(np.argmin(abs(map_energy-selected[edge])))])
                    for r,g in ((sp,'A'),(sp,'B'),(sm,'A'),(sm,'B'))]
                reconstructed=[integrate_paired(fields[k],geometry) for k in ('I_A_plus','I_B_plus_paired','I_A_minus','I_B_minus_paired')]
                if not np.allclose(reconstructed,[ia,ib,ima,imb],rtol=1e-12,atol=1e-14*max(ia,ib)):
                    raise ArithmeticError('Paired fields do not recover original detector spectra')
                sigma=(ia+ib+ima+imb)/2;mag=(ia-ib-ima+imb)/2;nonmag=(ia-ib+ima-imb)/2
                rows.append(dict(condition=condition,method=method,scope=edge,energy_ev=selected[edge],
                    A_raw=(ia-ib)/(ia+ib),A_mag=mag/sigma,A_nonmag=nonmag/sigma,Sigma_ref=sigma,
                    alpha_obs=alpha,alpha_nonmag=oracle,Delta_raw=ia-ib,Delta_mag=mag,Delta_nonmag=nonmag,
                    Delta_corrected=integrate_paired(fields['D_corrected'],geometry),
                    paired_detector_reconstruction_max_abs=float(np.max(abs(np.asarray(reconstructed)-[ia,ib,ima,imb])))))
                # Spatial norms do not permit cancellation across detector pixels.
                norm=lambda x:np.sqrt(np.sum(geometry['weights_A'][geometry['valid']]*fields[x][geometry['valid']]**2)*geometry['dq2'])
                floor=1e-10*np.sqrt(np.sum(geometry['weights_A']*p*p)*geometry['dq2'])
                nn,mn=norm('D_nonmag'),norm('D_mag')
                rows[-1].update(spatial_nonmag_suppression=1-norm('D_nonmag_residual')/nn if nn>floor else np.nan,
                    spatial_magnetic_scaling_change=norm('D_mag_processed')/mn-1 if mn>floor else np.nan,
                    spatial_corrected_reference_error=float(np.sqrt(np.sum(geometry['weights_A'][geometry['valid']]*(fields['D_corrected']-fields['D_mag'])[geometry['valid']]**2)*geometry['dq2'])/mn) if mn>floor else np.nan)
                maps.append(fields)
            for r in result.comparisons:
                if r['normalization']=='obs':rows.append(dict(r,condition=condition,method=method,scope='spectrum_'+r['scope']))
            methods.append(dict(spectra=result.spectra,maps=maps,normalization_metadata=result.metadata))
        # Primary errors use independently observed factors; secondary uses alpha_BW.
        errors=[];shared_alpha=float(methods[0]['spectra']['alpha_obs'][0])
        for j,edge in enumerate(('L3','L2')):
            a,b=[m['maps'][j] for m in methods]
            scale=max(np.sqrt(np.sum(geometry['weights_A']*m['I_plus']**2)*geometry['dq2']) for m in (a,b))
            shared=paired_maps(b['I_plus'],b['I_minus'],shared_alpha,geometry)
            b['D_corrected_shared_BW']=shared['D_corrected'];a['D_corrected_shared_BW']=a['D_corrected'].copy()
            error={k:map_error(a[k],b[k],geometry,scale) for k in ('D_raw','D_corrected','I_mag','D_nonmag_residual')}
            full_geometry=dict(geometry,weights_A=np.ones_like(geometry['weights_A']),valid=np.ones_like(geometry['valid']))
            full_scale=max(np.linalg.norm(m['I_plus'])*np.sqrt(geometry['dq2']) for m in (a,b))
            error['I_mag']=map_error(a['I_mag'],b['I_mag'],full_geometry,full_scale)
            error['D_corrected_shared_BW']=map_error(a['D_corrected'],shared['D_corrected'],geometry,scale)
            errors.append(error)
            for key,value in error.items():rows.append(dict(condition=condition,method='MS-BW',scope=edge,
                energy_ev=selected[edge],quantity=key,**value))
        for edge in ('L3','L2'):
            detector_rows=[next(r for r in rows if r['condition']==condition and r['scope']==edge and r['method']==method and 'A_raw' in r) for method in METHODS]
            for key in ('A_raw','A_mag','A_nonmag','Sigma_ref','alpha_obs','alpha_nonmag'):
                floor=1e-10*max(r['Sigma_ref'] for r in detector_rows) if key=='Sigma_ref' else 1e-8
                rows.append(dict(condition=condition,method='MS-BW',scope=edge,energy_ev=selected[edge],
                    quantity='detector_'+key,**scalar_discrepancy(detector_rows[0][key],detector_rows[1][key],floor)))
        cases.append(dict(condition=condition,qx=qx,qy=qy,geometry=geometry,methods=methods,map_errors=errors))
    metadata=dict(config=asdict(config),propagation=reference.metadata,source_sha256=source.source_sha256,
        selected_energies_ev=selected,actual_spectral_bounds_ev=[float(energy[0]),float(energy[-1])],
        spectral_sampling='linspace from energy_start to actual source end; exact-window interpolated endpoints and trapezoids',
        map_sampling='Actual nearest source samples; separate from spectral linspace; no extrapolation',
        map_axis_order='condition, method, selected_energy (L3,L2), qy, qx',method_labels=METHODS,
        paired_support='A-side fractional support; NaN outside; intrinsic intensity maps remain on full grid',
        pairing='R(qx,qy)=(qx,-qy); verified physical aperture bijection and reflected weights',
        error_norm='Paired contrasts: sqrt(sum_A w*delta^2*dq^2); intrinsic I_mag: full-grid unweighted area L2. Relative to max compared norm; floor=1e-10*matching intensity norm',
        primary_alpha='Each method uses its own plus-state detector-integrated post-edge factor',
        shared_alpha='Secondary only: apply BW observed factor to MS; never fitted for agreement',
        intrinsic_policy='I_mag=(I_plus-I_minus)/2 is unprocessed; corrected maps are paired contrasts, not intrinsic scattering',
        geometries={c['condition']:dict(mapping=c['geometry']['mapping'],dq2=c['geometry']['dq2']) for c in cases},
        normalization=[dict(condition=c['condition'],methods=[m['normalization_metadata'] for m in c['methods']]) for c in cases],
        map_discrepancies=[dict(condition=c['condition'],edges=c['map_errors']) for c in cases],
        python_version=platform.python_version(),model=LABEL,full_potential_comparison=False,convergence_established=False)
    return dict(cases=cases,rows=rows,metadata=metadata,propagation_cases=reference.cases)


def save_comparison(result, output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    cases=result['cases'];data=dict(method_labels=np.asarray(METHODS),conditions=np.asarray([c['condition'] for c in cases]),
        selected_energies_ev=np.asarray(list(result['metadata']['selected_energies_ev'].values())),edge_labels=np.asarray(['L3','L2']))
    for key in cases[0]['methods'][0]['maps'][0]:
        data[key]=np.asarray([[ [m[key] for m in method['maps']] for method in c['methods']] for c in cases])
    for key in ('weights_A','weights_B','valid'):
        data[key]=np.stack([c['geometry'][key] for c in cases])
    data['qx_inv_angstrom']=cases[0]['qx'];data['qy_inv_angstrom']=cases[0]['qy']
    for c in cases:
        for name,w in c['geometry']['physical_weights'].items():data[c['condition']+'__weight_'+name]=w
    for key in cases[0]['methods'][0]['spectra']:
        data['spectra__'+key]=np.asarray([[m['spectra'][key] for m in c['methods']] for c in cases])
    for key in ('coherence_bw','coherence_ms','depth_nm','fft_outside_intensity'):
        data[key]=np.stack([c[key] for c in result['propagation_cases']])
    np.savez_compressed(output/'map_comparison.npz',**data)
    columns=list(dict.fromkeys(k for row in result['rows'] for k in row))
    with (output/'method_comparison.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader();writer.writerows(result['rows'])
    metadata=result['metadata']
    try:
        root=Path(__file__).resolve().parents[2]
        metadata['software_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip()
        metadata['software_worktree_dirty']=bool(subprocess.check_output(['git','status','--porcelain'],cwd=root).strip())
    except (OSError,subprocess.CalledProcessError):pass
    (output/'comparison_metadata.json').write_text(json.dumps(_json_safe(metadata),indent=2,allow_nan=False)+'\n',encoding='utf-8')


def load_comparison(output):
    """Load pickle-free saved results for plotting without rerunning propagation."""
    output=Path(output)
    metadata=json.loads((output/'comparison_metadata.json').read_text(encoding='utf-8'))
    with (output/'method_comparison.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
    cases=[];propagation=[]
    with np.load(output/'map_comparison.npz',allow_pickle=False) as data:
        for i,condition in enumerate(data['conditions']):
            physical={k.split('__weight_')[1]:data[k].copy() for k in data.files if k.startswith(condition+'__weight_')}
            geometry={k:data[k][i].copy() for k in ('weights_A','weights_B','valid')}
            geometry.update(physical_weights=physical,**metadata['geometries'][condition])
            methods=[]
            keys=('I_plus','I_minus','I_mag','I_nonmag','I_A_plus','I_B_plus_paired','I_A_minus','I_B_minus_paired',*PAIRED,'D_corrected_shared_BW')
            for j in range(len(METHODS)):
                methods.append(dict(maps=[{k:data[k][i,j,e].copy() for k in keys} for e in range(2)],
                    spectra={k[len('spectra__'):]:data[k][i,j].copy() for k in data.files if k.startswith('spectra__')}))
            cases.append(dict(condition=str(condition),qx=data['qx_inv_angstrom'].copy(),qy=data['qy_inv_angstrom'].copy(),
                geometry=geometry,methods=methods,map_errors=metadata['map_discrepancies'][i]['edges']))
            propagation.append({k:data[k][i].copy() for k in ('coherence_bw','coherence_ms','depth_nm','fft_outside_intensity')})
    return dict(cases=cases,metadata=metadata,rows=rows,propagation_cases=propagation)


def plot_comparison(result, output):
    """Plot saved selected-energy fields only; no physics calculations."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    output=Path(output)
    for c in result['cases']:
        condition=c['condition'];half=np.sqrt(c['geometry']['dq2'])/2
        extent=(c['qx'].min()-half,c['qx'].max()+half,c['qy'].min()-half,c['qy'].max()+half)
        detectors=result['metadata']['propagation']['geometries'][condition]['detectors']
        view=max(abs(v)+d['radius_q'] for d in detectors.values() for v in d['center_q_xy'])+3*half
        for edge_index,edge in enumerate(('L3','L2')):
            maps=[m['maps'][edge_index] for m in c['methods']]
            def panels(keys,filename):
                fig,axs=plt.subplots(2,len(keys),figsize=(4*len(keys),7),squeeze=False,constrained_layout=True)
                vmax=max(max(float(np.nanmax(abs(m[k]))) for m in maps for k in keys),1e-30)
                for i in range(2):
                    for j,key in enumerate(keys):
                        ax=axs[i,j]
                        im=ax.imshow(maps[i][key],origin='lower',extent=extent,cmap='RdBu_r',vmin=-vmax,vmax=vmax,interpolation='nearest')
                        geometry=result['metadata']['propagation']['geometries'][condition]
                        for name,d in geometry['detectors'].items():
                            a=name in (('A',) if condition=='near-2bc' else ('RU','LD'))
                            ax.add_patch(Circle(d['center_q_xy'],d['radius_q'],fill=False,color='black',ls='-' if a else '--',lw=.8))
                        ax.set(xlabel='qx (cycles/A)',ylabel='qy (cycles/A)',xlim=(-view,view),ylim=(-view,view))
                        title=METHODS[i]+' | '+key
                        if key=='D_corrected':title+=f" | alpha={float(c['methods'][i]['spectra']['alpha_obs'][0]):.6f}"
                        ax.set_title(title,fontsize=9)
                fig.colorbar(im,ax=axs.ravel().tolist(),label='Relative intensity')
                fig.suptitle(condition+' | '+edge+f" {result['metadata']['selected_energies_ev'][edge]:.4f} eV\n"+LABEL,fontsize=10)
                fig.savefig(output/f'{condition}_{edge}_{filename}.png',dpi=180);plt.close(fig)
            panels(('D_raw','D_corrected'),'raw_corrected')
            panels(('D_mag','D_nonmag','D_mag_processed','D_nonmag_residual'),'decomposition')
            # One row per error type; avoid repeating identical discrepancy panels.
            fig,axs=plt.subplots(2,2,figsize=(10,8),constrained_layout=True)
            keys=('D_raw','D_corrected','I_mag','D_nonmag_residual')
            vmax=max(float(np.nanmax(abs(maps[1][k]-maps[0][k]))) for k in keys)
            for ax,key in zip(axs.flat,keys):
                delta=maps[1][key]-maps[0][key]
                im=ax.imshow(delta,origin='lower',extent=extent,cmap='RdBu_r',vmin=-max(vmax,1e-30),vmax=max(vmax,1e-30))
                err=c['map_errors'][edge_index][key]
                ax.set_title(f"{key}: abs L2={err['l2_abs']:.3g}; rel={err['l2_relative']:.3g}",fontsize=9)
                ax.set(xlabel='qx (cycles/A)',ylabel='qy (cycles/A)')
            fig.colorbar(im,ax=axs.ravel().tolist(),label='MS - BW relative intensity')
            fig.suptitle(condition+' | '+edge+' | independent normalization factors\n'+LABEL,fontsize=10)
            fig.savefig(output/f'{condition}_{edge}_method_errors.png',dpi=180);plt.close(fig)
        fig,axs=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
        for i,method in enumerate(c['methods']):
            s=method['spectra'];e=s['energy_ev']
            for key in ('I_A_plus','I_B_plus'):axs[i,0].plot(e,s[key],label=key)
            for key in ('D_raw','D_mag'):axs[i,1].plot(e,s[key],label=key)
            for key in ('D_corrected','D_nonmag_residual_obs'):axs[i,1].plot(e,s[key][0],label=key)
            for ax in axs[i]:
                ax.axvspan(result['metadata']['config']['postedge_start'],result['metadata']['config']['postedge_end'],color='grey',alpha=.2)
                ax.set(xlabel='Energy (eV)',ylabel='Relative intensity',title=METHODS[i]);ax.legend(fontsize=8);ax.grid(alpha=.2)
        fig.suptitle(condition+' | detector-integrated spectra\n'+LABEL,fontsize=10)
        fig.savefig(output/f'{condition}_detector_spectra.png',dpi=180);plt.close(fig)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--xmcd-file',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('outputs/ni_postedge_emcd_map_comparison'))
    p.add_argument('--conditions',nargs='+',choices=('near-2bc','symmetric-3bc'),default=['near-2bc','symmetric-3bc'])
    for name,default in [('potential-cutoff',.75),('beam-cutoff',2.2),('slice-step-nm',.04),('thickness-nm',30.),
        ('acceleration-kv',200.),('eta',1.),('beta',1.),('b-factor-angstrom2',0.),('offzone-tilt-mrad',25.),
        ('postedge-start',878.),('postedge-end',882.),('energy-start',837.),('energy-ev',852.7),('l2-energy-ev',870.),('max-kernel-mib',512.)]:
        p.add_argument('--'+name,type=float,default=default)
    for name,default in [('fft-grid',32),('depth-steps',64),('detector-grid',33),('energy-points',185),('max-beams',121),('aperture-subpixels',64)]:
        p.add_argument('--'+name,type=int,default=default)
    p.add_argument('--integration-mode',choices=('binary','fractional'),default='fractional')
    p.add_argument('--plot-only',action='store_true',help='Replot saved output; numerical CLI settings are ignored')
    args=vars(p.parse_args(argv));plot_only=args.pop('plot_only');source=args.pop('xmcd_file');output=args.pop('output')
    args['conditions']=tuple(args['conditions']);args['thickness_nm']=(args['thickness_nm'],)
    if plot_only:
        plot_comparison(load_comparison(output),output);return
    try:result=run_map_comparison(source,MapConfig(**args))
    except ValueError as exc:p.error(str(exc))
    save_comparison(result,output);plot_comparison(result,output)
    print(json.dumps(_json_safe(dict(output=str(output),map_discrepancies=result['metadata']['map_discrepancies'])),indent=2,allow_nan=False))


if __name__=='__main__':main()
