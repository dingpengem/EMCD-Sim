"""Checkpointed, matched BW/FFT Ni (200) x-mistilt analysis; existing physics only."""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass, replace
import hashlib
import json
from pathlib import Path
import platform
import subprocess

import numpy as np

from .benchmark import nickel_physical_benchmark
from .crystal import fcc_nickel
from .diffraction import bragg_tilt_mrad, excitation_errors_angstrom_inv
from .elastic import BeamSet
from .elastic_reference import FourierCutoffPotential
from .emcd_angular_plots import coordinate_markers, decorate_reciprocal_map
from .multislice_emcd_reference import (MultisliceEMCDConfig, coherence_from_amplitudes,
                                       project_fft_amplitudes)
from .multislice_reference import fft_multislice_ni
from .postedge_emcd_maps import paired_geometry, paired_maps, integrate_paired, map_error
from .scattering import IndependentAtomPotential
from .single_channeling_tensor import run_tensor_with_coherence
from .wien2k_xmcd import load_wien2k_xmcd
from .xmcd_basis_convergence import selected_energy_grid
from .xmcd_effective_mdff import effective_tensor_from_xmcd
from .xmcd_geometry_decomposition import _json_safe
from .xmcd_postedge_normalization import analyze_postedge_spectra, _window_nodes

METHODS=('bloch','fft-multislice')
EDGES=('L3','L2')
MAP_KEYS=('I_plus','I_minus','I_mag','I_nonmag','D_raw','D_corrected',
          'D_mag','D_nonmag','D_mag_processed','D_nonmag_residual')
SPECTRAL_KEYS=('I_A_plus','I_B_plus','I_A_minus','I_B_minus','D_raw','D_mag',
               'D_nonmag','Sigma_ref','D_corrected','D_mag_processed_obs','D_nonmag_residual_obs')


@dataclass(frozen=True)
class MistiltConfig:
    start_mrad: float=-2.
    stop_mrad: float=2.
    step_mrad: float=.5
    fixed_y_mrad: float=25.
    thickness_nm: float=30.
    acceleration_kv: float=200.
    potential_cutoff: float=.75
    beam_cutoff: float=2.2
    max_beams: int=121
    fft_grid: int=32
    slice_step_nm: float=.04
    depth_steps: int=64
    detector_grid: int=33
    energy_points: int=241
    integration_mode: str='fractional'
    aperture_subpixels: int=64
    eta: float=1.
    beta: float=1.
    max_kernel_mib: float=512.
    l3_energy_ev: float=852.7
    l2_energy_ev: float=870.
    postedge_start_ev: float=878.
    postedge_end_ev: float=882.

    def offsets(self):
        controls=[self.start_mrad,self.stop_mrad,self.step_mrad,self.fixed_y_mrad]
        if not np.isfinite(controls).all() or self.step_mrad<=0 or self.stop_mrad<self.start_mrad:
            raise ValueError('Require finite ordered offsets and positive step')
        count=(self.stop_mrad-self.start_mrad)/self.step_mrad
        if not np.isclose(count,round(count),rtol=0,atol=1e-9):
            raise ValueError('Offset range must contain an integer number of steps')
        return self.start_mrad+self.step_mrad*np.arange(int(round(count))+1)

    def validate(self):
        self.offsets()
        MultisliceEMCDConfig(conditions=('near-2bc',),thickness_nm=(self.thickness_nm,),
            potential_cutoff=self.potential_cutoff,beam_cutoff=self.beam_cutoff,max_beams=self.max_beams,
            fft_grid=self.fft_grid,slice_step_nm=self.slice_step_nm,depth_steps=self.depth_steps,
            detector_grid=self.detector_grid,acceleration_kv=self.acceleration_kv,
            offzone_tilt_mrad=abs(self.fixed_y_mrad),eta=self.eta,beta=self.beta,
            max_kernel_mib=self.max_kernel_mib,integration_mode=self.integration_mode,
            aperture_subpixels=self.aperture_subpixels).validate()
        if not isinstance(self.energy_points,int) or self.energy_points<3:
            raise ValueError('Require at least three spectral samples')


def model_for_offset(config, offset):
    crystal=fcc_nickel()
    tx=-bragg_tilt_mrad(crystal,(2,0,0),config.acceleration_kv)+float(offset)
    beams=BeamSet.zolz(crystal,config.beam_cutoff,config.max_beams)
    model=nickel_physical_benchmark(acceleration_kv=config.acceleration_kv,
        tilt_mrad_xy=(tx,config.fixed_y_mrad),beams_override=beams,diffraction_condition='near-2bc')
    potential=FourierCutoffPotential(IndependentAtomPotential(crystal),config.potential_cutoff)
    return replace(model,elastic=replace(model.elastic,potential=potential))


def geometry_record(config,offset,model):
    tx,ty=model.elastic.microscope.tilt_mrad_xy
    index=model.elastic.beams.hkl.index((2,0,0))
    g=model.elastic.crystal.g_vector((2,0,0))[:2]
    return dict(delta_x_mrad=float(offset),theta_x_mrad=tx,theta_y_mrad=ty,
        total_tilt_mrad=float(np.hypot(tx,ty)),
        s200_inv_angstrom=float(excitation_errors_angstrom_inv(model.elastic)[index]),
        coordinate_markers=coordinate_markers(model.elastic.microscope),
        thales_center_q_xy=(g/2).tolist(),thales_radius_inv_angstrom=float(np.linalg.norm(g)/2),
        detectors={k:dict(center_q_xy=d.center_q_xy,radius_q=d.radius_q) for k,d in model.detectors.items()})


def setup(source_path,config):
    config.validate();source=load_wien2k_xmcd(source_path)
    edge_energy,selected=selected_energy_grid(source.energy_ev,dict(L3=config.l3_energy_ev,L2=config.l2_energy_ev))
    # Include actual selected source samples in the common full spectrum, so map/spectrum
    # reconstruction compares identical energies, rather than interpolated references.
    energy=np.unique(np.r_[np.linspace(source.energy_ev[0],source.energy_ev[-1],config.energy_points),edge_energy])
    _window_nodes(energy,(config.postedge_start_ev,config.postedge_end_ev))
    for interval in ((844.,862.),(864.,874.)):_window_nodes(energy,interval)
    model=model_for_offset(config,0.)
    if model.elastic.beams.hkl!=BeamSet.zolz(fcc_nickel(),config.beam_cutoff,config.max_beams+2).hkl:
        raise ValueError('Beam cap clips requested basis')
    estimate=64.*config.detector_grid**2*len(model.elastic.beams.hkl)**2/2**20
    if estimate>config.max_kernel_mib:
        raise ValueError(f'Estimated dense kernel {estimate:.1f} MiB exceeds memory limit')
    safe=(config.fft_grid//2-1)*2/float(model.elastic.crystal.lattice_angstrom[0,0])
    if max(config.beam_cutoff,config.potential_cutoff)>=safe:
        raise ValueError('FFT grid cannot safely represent potential/common beams')
    defaults=MistiltConfig()
    physics={k:float(v) if isinstance(getattr(defaults,k),float) else v
             for k,v in asdict(config).items() if k not in ('start_mrad','stop_mrad','step_mrad')}
    module_names=('ni_mistilt_series','single_channeling_tensor','physical_elastic','multislice_reference',
                  'multislice_emcd_reference','scattering','geometry','xmcd_effective_mdff',
                  'postedge_emcd_maps','xmcd_postedge_normalization','benchmark','diffraction')
    hashes={name:hashlib.sha256(Path(__file__).with_name(name+'.py').read_bytes()).hexdigest() for name in module_names}
    provenance=dict(physics=physics,source_sha256=source.source_sha256,energy_ev=energy.tolist(),
        selected_energies_ev=selected,implementation_sha256=hashes)
    signature=hashlib.sha256(json.dumps(provenance,sort_keys=True).encode()).hexdigest()
    return energy,selected,dict(provenance,signature=signature,pair_array_memory_estimate_mib=estimate)


def safe_ratio(num,den,floor):
    return float(num/den) if np.isfinite([num,den]).all() and abs(den)>floor else np.nan


def calculate_case(source_path,config,offset,energy,selected,*,model_factory=None,
                   propagator=None,geometry_factory=None,target_key='s200_inv_angstrom',
                   tensor_factory=None,edge_windows=None):
    model=(model_for_offset if model_factory is None else model_factory)(config,offset)
    record_geometry=geometry_record if geometry_factory is None else geometry_factory
    propagate=fft_multislice_ni if propagator is None else propagator
    z=np.linspace(0.,config.thickness_nm,config.depth_steps)
    print(f'offset {offset:+.3f} mrad: independent BW and FFT propagation',flush=True)
    bw=model.elastic.amplitudes(z)
    fft=propagate(z,acceleration_kv=config.acceleration_kv,
        tilt_mrad_xy=model.elastic.microscope.tilt_mrad_xy,grid_points=config.fft_grid,
        slice_step_nm=config.slice_step_nm,potential_cutoff_inv_angstrom=config.potential_cutoff,
        return_amplitudes=True)
    ms,outside=project_fft_amplitudes(fft,model.elastic.beams.hkl)
    cs=[coherence_from_amplitudes(z,p) for p in (bw,ms)]
    arrays=dict(depth_nm=z,coherence_bw=cs[0],coherence_ms=cs[1],fft_outside_intensity=outside,
        bw_amplitudes=bw,ms_amplitudes_projected=ms,energy_ev=energy,
        selected_energy_ev=np.array([selected[e] for e in EDGES]),method_labels=np.asarray(METHODS))
    make_tensor=effective_tensor_from_xmcd if tensor_factory is None else tensor_factory
    tensors=[make_tensor(source_path,energy,eta=sign*config.eta,beta=config.beta) for sign in (1,-1)]
    map_energy=np.asarray(sorted(set(selected.values())))
    mtensors=[make_tensor(source_path,map_energy,eta=sign*config.eta,beta=config.beta) for sign in (1,-1)]
    opts=dict(thickness_nm=config.thickness_nm,grid_size=config.detector_grid,
              integration_mode=config.integration_mode,aperture_subpixels=config.aperture_subpixels)
    method_fields=[];spectra=[];rows=[];norm_meta=[]
    for method,c in zip(METHODS,cs):
        print(f'offset {offset:+.3f}: {method}, {len(energy)} energies, +/-M',flush=True)
        rp,rm=[run_tensor_with_coherence(model,t,c,reference_energy_ev=selected['L3'],**opts) for t in tensors]
        analysis=analyze_postedge_spectra(energy,rp.chiral_spectrum('A'),rp.chiral_spectrum('B'),
            rm.chiral_spectrum('A'),rm.chiral_spectrum('B'),windows=((config.postedge_start_ev,config.postedge_end_ev),),edge_windows=edge_windows)
        s=analysis.spectra;alpha=float(s['alpha_obs'][0]);spectra.append(s);norm_meta.append(analysis.metadata)
        geom=paired_geometry(model,rp.qx_angstrom_inv,rp.qy_angstrom_inv,
                             mode=config.integration_mode,subpixels=config.aperture_subpixels)
        fields=[]
        for edge in EDGES:
            p,m=(rp,rm) if edge=='L3' else [run_tensor_with_coherence(model,t,c,
                             reference_energy_ev=selected[edge],**opts) for t in mtensors]
            field=paired_maps(p.nonmag_map_at_l3+p.magnetic_map_at_l3,
                              m.nonmag_map_at_l3+m.magnetic_map_at_l3,alpha,geom)
            i=int(np.argmin(abs(energy-selected[edge])));mi=int(np.argmin(abs(p.energy_ev-selected[edge])))
            for result,state in ((p,'plus'),(m,'minus')):
                for group in ('A','B'):
                    np.testing.assert_allclose(result.chiral_spectrum(group)[mi],s['I_'+group+'_'+state][i],rtol=1e-12,atol=1e-14)
            for key in ('D_raw','D_mag','D_nonmag','D_corrected'):
                target=s[key][0,i] if key=='D_corrected' else s[key][i]
                np.testing.assert_allclose(integrate_paired(field[key],geom),target,rtol=1e-11,atol=1e-14)
            sigma=float(s['Sigma_ref'][i]);floor=1e-10*float(np.max(s['Sigma_ref']))
            mag=float(s['D_mag'][i]);nonmag=float(s['D_nonmag'][i])
            processed=float(s['D_mag_processed_obs'][0,i]);resid=float(s['D_nonmag_residual_obs'][0,i])
            ap,bp=s['I_A_plus'][i],s['I_B_plus'][i]
            recovery=next(r for r in analysis.comparisons if r['scope']==edge and r['normalization']=='obs')
            record=record_geometry(config,offset,model)
            za=record['coordinate_markers']['zone_axis_q_cycles_per_angstrom']
            rows.append(dict(delta_x_mrad=float(offset),method=method,edge=edge,energy_ev=selected[edge],
                theta_x_mrad=record['theta_x_mrad'],theta_y_mrad=record['theta_y_mrad'],
                total_tilt_mrad=record['total_tilt_mrad'],**{target_key:record[target_key]},
                za_qx=za[0],za_qy=za[1],I_A_plus=float(ap),I_B_plus=float(bp),Sigma_ref=sigma,
                magnetic_signal=mag,magnetic_abs=abs(mag),nonmagnetic_signal=nonmag,nonmagnetic_abs=abs(nonmag),
                raw_difference=float(s['D_raw'][i]),raw_asymmetry=safe_ratio(ap-bp,ap+bp,floor),
                magnetic_asymmetry=safe_ratio(mag,sigma,floor),nonmagnetic_asymmetry=safe_ratio(nonmag,sigma,floor),
                corrected_difference=float(s['D_corrected'][0,i]),alpha=alpha,
                nonmagnetic_residual=resid,nonmagnetic_suppression=1-safe_ratio(abs(resid),abs(nonmag),floor),
                magnetic_processed=processed,magnetic_processing_signed_change=processed-mag,
                magnetic_processing_change=safe_ratio(abs(processed)-abs(mag),abs(mag),floor),
                denominator_floor=floor,edge_window_nonmag_suppression=recovery['nonmag_suppression'],
                edge_window_magnetic_amplitude_change=recovery['magnetic_amplitude_change']))
            fields.append(field)
        method_fields.append(fields)
    arrays.update({'map__'+k:np.asarray([[f[k] for f in method] for method in method_fields]) for k in MAP_KEYS})
    for key in SPECTRAL_KEYS:
        arrays['spectra__'+key]=np.asarray([s[key][0] if s[key].ndim==2 else s[key] for s in spectra])
    arrays.update(alpha=np.asarray([s['alpha_obs'][0] for s in spectra]),qx=rp.qx_angstrom_inv,qy=rp.qy_angstrom_inv,
                  weights_A=geom['weights_A'],weights_B=geom['weights_B'],paired_valid=geom['valid'])
    discrepancies=[]
    full_geometry=dict(geom,weights_A=np.ones_like(geom['weights_A']),valid=np.ones_like(geom['valid']))
    for i,edge in enumerate(EDGES):
        a,b=[fields[i] for fields in method_fields]
        scale=max(np.sqrt(np.sum(f['I_plus']**2)*geom['dq2']) for f in (a,b))
        error=map_error(a['I_mag'],b['I_mag'],full_geometry,scale)
        discrepancies.append(error)
        for row in rows:
            if row['edge']==edge:row.update(bw_ms_magnetic_map_l2_abs=error['l2_abs'],
                bw_ms_magnetic_map_l2_relative=error['l2_relative'])
    meta=dict(geometry=record_geometry(config,offset,model),normalization=norm_meta,
        coherence_relative_error=float(np.linalg.norm(cs[0]-cs[1])/max(np.linalg.norm(c) for c in cs)),
        coherence_absolute_error=float(np.linalg.norm(cs[0]-cs[1])),fft_norm_error=float(fft.norm_error),
        max_fft_outside_common_basis=float(outside.max()),magnetic_map_discrepancies=discrepancies,
        aperture_integration={k:d.integration_info(rp.qx_angstrom_inv,rp.qy_angstrom_inv,
            mode=config.integration_mode,subpixels=config.aperture_subpixels) for k,d in model.detectors.items()})
    for row in rows:row['bw_ms_coherence_relative']=meta['coherence_relative_error']
    return arrays,meta,rows


def write_json(path,data):
    path.write_text(json.dumps(_json_safe(data),indent=2,allow_nan=False)+'\n',encoding='utf-8')


def validate_checkpoint(data,meta,signature,offset):
    if meta['signature']!=signature or meta['geometry']['delta_x_mrad']!=float(offset):
        raise ValueError('Checkpoint configuration/source mismatch; choose a separate output directory')
    for key in ('spectra__I_A_plus','spectra__I_B_plus','spectra__I_A_minus','spectra__I_B_minus'):
        if not np.isfinite(data[key]).all() or np.min(data[key]) < -1e-12:
            raise ValueError('Invalid checkpoint detector spectra')
    np.testing.assert_allclose(data['spectra__D_raw'],data['spectra__D_mag']+data['spectra__D_nonmag'],atol=1e-13)
    np.testing.assert_allclose(data['map__I_plus'],data['map__I_nonmag']+data['map__I_mag'],atol=1e-12)
    for key in MAP_KEYS:
        if key.startswith('D_') and not np.isfinite(data['map__'+key][:,:,data['paired_valid']]).all():
            raise ValueError('Invalid checkpoint paired map')


def run_series(source_path,output,config=MistiltConfig(),plot_only=False):
    source_path=Path(source_path);output=Path(output)
    energy,selected,provenance=setup(source_path,config)
    signature=provenance['signature'];cases=[];metadata=[];rows=[]
    output.mkdir(parents=True,exist_ok=True);checkpoints=output/'checkpoints';checkpoints.mkdir(exist_ok=True)
    manifest=output/'run_settings.json'
    if manifest.exists():
        if json.loads(manifest.read_text())['signature']!=signature:
            raise ValueError('Output settings/source/code mismatch; existing results were not overwritten')
    elif plot_only:
        raise ValueError('Plot-only requires existing validated checkpoints')
    else:write_json(manifest,provenance)
    print(f'Dense pair-array estimate {provenance["pair_array_memory_estimate_mib"]:.1f} MiB; {len(energy)} energies',flush=True)
    for offset in config.offsets():
        tag=f'{float(offset):+.6f}';path=checkpoints/(tag+'.npz');info=path.with_suffix('.json')
        if path.exists() and info.exists():
            meta=json.loads(info.read_text())
            if hashlib.sha256(path.read_bytes()).hexdigest()!=meta['npz_sha256']:
                raise ValueError('Checkpoint hash mismatch; refusing reuse/overwrite')
            with np.load(path,allow_pickle=False) as saved:data={k:saved[k] for k in saved.files}
            validate_checkpoint(data,meta,signature,offset)
            case_rows=meta['rows'];print(f'offset {offset:+.3f}: reused validated checkpoint',flush=True)
        elif plot_only:
            raise ValueError(f'Missing completed checkpoint for {offset:+.3f}')
        else:
            data,meta,case_rows=calculate_case(source_path,config,offset,energy,selected)
            meta.update(signature=signature,rows=case_rows)
            validate_checkpoint(data,meta,signature,offset)
            temporary=path.with_suffix('.partial.npz');np.savez_compressed(temporary,**data);temporary.replace(path)
            meta['npz_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();write_json(info,meta)
            print(f'offset {offset:+.3f}: checkpoint saved and validated',flush=True)
        cases.append(data);metadata.append(meta);rows.extend(case_rows)
    maps={k:np.stack([c['map__'+k] for c in cases]) for k in MAP_KEYS}
    spectra={k:np.stack([c['spectra__'+k] for c in cases]) for k in SPECTRAL_KEYS}
    common=dict(delta_x_mrad=config.offsets(),method_labels=np.asarray(METHODS),edge_labels=np.asarray(EDGES))
    if not plot_only:
        np.savez_compressed(output/'mistilt_maps.npz',qx=cases[0]['qx'],qy=cases[0]['qy'],
            selected_energy_ev=cases[0]['selected_energy_ev'],weights_A=cases[0]['weights_A'],
            weights_B=cases[0]['weights_B'],paired_valid=cases[0]['paired_valid'],**common,**maps)
        np.savez_compressed(output/'mistilt_eels.npz',energy_ev=energy,
            alpha=np.stack([c['alpha'] for c in cases]),**common,**spectra)
        with (output/'mistilt_summary.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        write_json(output/'mistilt_metadata.json',dict(config=asdict(config),provenance=provenance,
            software_commit=commit,software_worktree_dirty=bool(subprocess.check_output(['git','status','--porcelain'],text=True).strip()),
            python_version=platform.python_version(),cases=metadata,map_axes='mistilt, method, edge, qy, qx',
            spectral_axes='mistilt, method, energy',methods=METHODS,edges=EDGES,
            selected_energies_ev=selected,source_energy_axis='Native unshifted source; requested 852.7/870.0 eV are reference samples, not native peak locations',
            paired_support='A fractional support only, NaN outside; R(qx,qy)=(qx,-qy)',
            normalization='Per-case, per-method plus-state alpha=int_878^882 A / int_878^882 B; exact endpoint interpolation; same alpha applied to odd/even processed terms',
            asymmetry='raw=(Aplus-Bplus)/(Aplus+Bplus); magnetic=D_mag/Sigma_ref; Sigma_ref=(Aplus+Bplus+Aminus+Bminus)/2',
            undefined_policy='NaN/validity in NPZ and CSV; null JSON; denominator floor=1e-10 times peak Sigma_ref',
            physical_limitations='XMCD-effective dipole MDFF; IAM Fourier-truncated projected [001] ZOLZ potential; entrance-only, no exit channeling; relative units; potential/basis/global convergence unverified'))
    plot_series(output,config,cases,rows)
    return cases,metadata,rows


def plot_series(output,config,cases,rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    count=len(cases);offsets=config.offsets();ncol=min(3,count);nrow=int(np.ceil(count/ncol))
    qx,qy=cases[0]['qx'],cases[0]['qy'];half=(qx[0,1]-qx[0,0])/2
    extent=(qx.min()-half,qx.max()+half,qy.min()-half,qy.max()+half)
    models=[model_for_offset(config,d) for d in offsets]
    def decorate(ax,i):decorate_reciprocal_map(ax,models[i],extent)
    def panel_title(i):
        tx,ty=models[i].elastic.microscope.tilt_mrad_xy
        return f'Delta x = {offsets[i]:+.1f} mrad\nabsolute tilt=({tx:.3f}, {ty:+.1f}) mrad'
    for edge,label in enumerate(EDGES):
        for key,kind in (('I_mag','magnetic'),('I_nonmag','nonmagnetic'),('I_plus','total'),('D_corrected','corrected')):
            limit=max(float(np.nanmax(abs(c['map__'+key][:,edge]))) for c in cases)
            signed=key in ('I_mag','D_corrected');limit=max(limit,1e-30)
            for method,method_name in enumerate(METHODS):
                fig,axes=plt.subplots(nrow,ncol,figsize=(4.1*ncol,4.1*nrow),squeeze=False,constrained_layout=True)
                for i,c in enumerate(cases):
                    ax=axes.flat[i];im=ax.imshow(c['map__'+key][method,edge],origin='lower',extent=extent,
                        vmin=-limit if signed else 0,vmax=limit,cmap='RdBu_r' if signed else 'viridis',interpolation='nearest')
                    decorate(ax,i);ax.set_title(panel_title(i),fontsize=8)
                for ax in list(axes.flat)[count:]:ax.set_visible(False)
                fig.colorbar(im,ax=list(axes.flat)[:count],label='Relative intensity',shrink=.7)
                fig.suptitle(f'{label} {cases[0]["selected_energy_ev"][edge]:.3f} eV | {kind} | {method_name}\n'
                             'Fixed y tilt; shared color scale across mistilts and methods',fontsize=11)
                suffix='' if method==0 else '_multislice'
                fig.savefig(output/f'{label}_{kind}_mistilt_series{suffix}.png',dpi=150);plt.close(fig)
    reps=[i for i,d in enumerate(offsets) if any(np.isclose(d,v) for v in (-1.,0.,1.))]
    if not reps:reps=[0]
    for edge,label in enumerate(EDGES):
        fig,axes=plt.subplots(len(reps),4,figsize=(16,4*len(reps)),squeeze=False,constrained_layout=True)
        limit=max(float(np.nanmax(abs(cases[i]['map__'+key][:,edge]))) for i in reps for key in ('D_raw','D_corrected'))
        for row,i in enumerate(reps):
            for method in range(2):
                for col,key in enumerate(('D_raw','D_corrected')):
                    ax=axes[row,method*2+col]
                    im=ax.imshow(cases[i]['map__'+key][method,edge],origin='lower',extent=extent,
                        cmap='RdBu_r',vmin=-limit,vmax=limit,interpolation='nearest')
                    decorate(ax,i);ax.set_title(f'{offsets[i]:+.1f} mrad | {METHODS[method]} | {key}',fontsize=8)
        fig.colorbar(im,ax=axes.ravel().tolist(),label='Paired contrast, A support only',shrink=.7)
        fig.suptitle(label+' raw versus post-edge-corrected (white = outside A support)')
        fig.savefig(output/('raw_corrected_mistilt.png' if edge==0 else 'L2_raw_corrected_mistilt.png'),dpi=150);plt.close(fig)
    fig,axes=plt.subplots(2,4,figsize=(17,8),constrained_layout=True)
    colors=plt.cm.viridis(np.linspace(0,1,count))
    for method in range(2):
        for i,c in enumerate(cases):
            e=c['energy_ev'];label=f'{offsets[i]:+.1f} mrad'
            for col,key in enumerate(('I_A_plus','I_B_plus','D_raw')):
                axes[method,col].plot(e,c['spectra__'+key][method],color=colors[i],label=label,lw=.9)
            axes[method,3].plot(e,c['spectra__D_mag'][method],color=colors[i],lw=.9,label=label)
            axes[method,3].plot(e,c['spectra__D_corrected'][method],color=colors[i],ls='--',lw=.9)
        for col,ax in enumerate(axes[method]):
            for edge,e0 in zip(EDGES,cases[0]['selected_energy_ev']):
                ax.axvline(e0,color='.4',ls=':',lw=.6)
                ax.text(e0,.98,edge,transform=ax.get_xaxis_transform(),va='top',fontsize=7)
            ax.set(xlabel='Energy loss (eV)',ylabel='Relative intensity',
                title=METHODS[method]+' | '+('A +M','B +M','Raw A-B','Odd solid; corrected dashed')[col])
            ax.ticklabel_format(axis='y',style='sci',scilimits=(0,0));ax.grid(alpha=.2)
        axes[method,0].legend(fontsize=6,ncol=2)
    fig.suptitle('Virtual-detector EELS evolution: no curve rescaling or vertical display offsets')
    fig.savefig(output/'virtual_detector_eels_mistilt.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(15,9),constrained_layout=True)
    for col,key in enumerate(('D_raw','D_mag','D_corrected')):
        amplitude=max(float(np.max(abs(c['spectra__'+key]))) for c in cases)
        spacing=max(2.2*amplitude,1e-30)
        for method in range(2):
            ax=axes[method,col]
            for i,c in enumerate(cases):
                ax.plot(c['energy_ev'],c['spectra__'+key][method]+i*spacing,
                        color=colors[i],lw=1,label=f'{offsets[i]:+.1f} mrad')
            for e0 in cases[0]['selected_energy_ev']:ax.axvline(e0,color='.4',ls=':',lw=.6)
            ax.set(xlabel='Energy loss (eV)',ylabel=f'Intensity + index x {spacing:.3g} (display only)',
                   title=METHODS[method]+' | '+key)
            ax.ticklabel_format(axis='y',style='sci',scilimits=(0,0));ax.grid(alpha=.2)
            if col==0:ax.legend(fontsize=6,ncol=2)
    fig.suptitle('Stacked spectra: constant vertical plotting offsets only; original amplitudes retained\n'
                 'See virtual_detector_eels_mistilt.png for quantitative unoffset curves')
    fig.savefig(output/'virtual_detector_eels_stacked.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(13,8),constrained_layout=True)
    selections=[('magnetic_asymmetry','L3 magnetic asymmetry','L3'),
                ('magnetic_asymmetry','L2 magnetic asymmetry','L2'),
                ('raw_asymmetry','Raw asymmetry',None),('alpha','Post-edge alpha','L3'),
                ('nonmagnetic_residual','Nonmagnetic residual',None),
                ('magnetic_processing_change','Magnetic magnitude processing change',None)]
    for ax,(key,title,only_edge) in zip(axes.flat,selections):
        for method in METHODS:
            for edge in (EDGES if only_edge is None else (only_edge,)):
                subset=[r for r in rows if r['method']==method and r['edge']==edge]
                values=[np.nan if r[key] is None else r[key] for r in subset]
                ax.plot([r['delta_x_mrad'] for r in subset],values,marker='o',ms=3,
                        ls='-' if method==METHODS[0] else '--',label=method+' '+edge)
        ax.axvline(0,color='.4',ls=':');ax.set(xlabel='Delta theta_x from Bragg (mrad)',title=title)
        ax.grid(alpha=.2);ax.legend(fontsize=6)
    fig.savefig(output/'emcd_vs_mistilt.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4),constrained_layout=True)
    for edge in EDGES:
        subset=[r for r in rows if r['method']==METHODS[0] and r['edge']==edge]
        for ax,key in zip(axes,('bw_ms_magnetic_map_l2_relative','bw_ms_magnetic_map_l2_abs')):
            ax.plot(offsets,[np.nan if r[key] is None else r[key] for r in subset],'-o',label=edge)
    for ax,title in zip(axes,('Relative magnetic-map L2 error (fraction)','Absolute magnetic-map L2 error')):
        ax.axvline(0,color='.4',ls=':');ax.set(xlabel='Delta theta_x from Bragg (mrad)',title=title)
        ax.grid(alpha=.2);ax.legend()
    fig.suptitle('Independent FFT multislice versus BW; numerical comparison, not convergence')
    fig.savefig(output/'bloch_multislice_vs_mistilt.png',dpi=150);plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('data/wien2k_ni/Ni_fm.xmcd'))
    p.add_argument('--output',type=Path,default=Path('outputs/ni_continuous_mistilt'))
    p.add_argument('--plot-only',action='store_true')
    defaults=MistiltConfig()
    for name,value in asdict(defaults).items():
        p.add_argument('--'+name.replace('_','-'),type=type(value),default=value)
    args=p.parse_args();values=vars(args);source=values.pop('source');output=values.pop('output');plot_only=values.pop('plot_only')
    run_series(source,output,MistiltConfig(**values),plot_only)


if __name__=='__main__':main()
