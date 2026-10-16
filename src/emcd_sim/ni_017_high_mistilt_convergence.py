"""Targeted, selected-energy convergence controls; no full 43-case sweep."""
from dataclasses import replace
from pathlib import Path
import hashlib,json
import numpy as np
from .ni_017_high_mistilt_xy import GEO,propagate,tag,setup
from .ni_017_mistilt import selected_observables,csv_write
from .ni_mistilt_series import write_json
from .multislice_emcd_reference import coherence_from_amplitudes,project_fft_amplitudes


def controls(source,root,cfg):
    root=Path(root);findings=json.loads((root/'study_findings.json').read_text())
    poses=[(0.,0.),(0.,25.),(0.,-25.),(10.,25.),(-10.,-25.),(5.,25.),(5.,-25.)]
    for group in findings['extrema'].values():
        for key in ('magnetic_abs','magnetic_asymmetry','shot_noise_proxy'):
            r=group[key];poses.append((r['delta_x_mrad'],r['delta_y_mrad']))
    import csv
    rows=list(csv.DictReader((root/'high_mistilt_summary.csv').open()))
    r=max(rows,key=lambda r:abs(float(r['nonmagnetic_signal'])));poses.append((float(r['delta_x_mrad']),float(r['delta_y_mrad'])))
    r=max(rows,key=lambda r:float(r['bw_ms_magnetic_map_l2_relative']));poses.append((float(r['delta_x_mrad']),float(r['delta_y_mrad'])))
    poses=list(dict.fromkeys(poses));out=root/'convergence';out.mkdir(exist_ok=True)
    codehash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();parent=json.loads((root/'run_settings.json').read_text())['signature']
    if setup(source,cfg)[3]!=parent:raise ValueError('Convergence source/configuration differs from production')
    signature=hashlib.sha256((codehash+parent).encode()).hexdigest();records=[]
    z=np.linspace(0,cfg.thickness_nm,cfg.depth_steps)
    for x,y in poses:
        for pc in (2.2,3.2):
            variants=[('bloch',bc,0,cfg.slice_step_nm) for bc in (3.2,4.5,5.5,6.5)]
            variants += [('fft-multislice',4.5,grid,cfg.slice_step_nm) for grid in (32,64)]
            variants += [('fft-multislice',5.5,64,cfg.slice_step_nm)]
            # One halved-step control at each requested representative high-cutoff orientation.
            if pc==3.2:variants += [('fft-multislice',5.5,64,cfg.slice_step_nm/2)]
            for method,bc,grid,step in variants:
                key=f'{tag(x,y)}_p{pc}_b{bc}_{method}_g{grid}_s{step}'
                f=out/(key+'.json');checkpoint=out/(key+'.npz')
                if f.exists():
                    saved=json.loads(f.read_text())
                    if saved['signature']!=signature or hashlib.sha256(checkpoint.read_bytes()).hexdigest()!=saved['npz_sha256']:raise ValueError('Convergence provenance mismatch')
                    records.extend(saved['rows']);continue
                m=GEO.model(x,y_offset=y,kv=cfg.acceleration_kv,beam_cutoff=bc,potential_cutoff=pc)
                n=len(m.elastic.beams.hkl);memory=64*17**2*n*n/2**20
                if memory>cfg.max_kernel_mib:raise ValueError('Convergence kernel exceeds memory limit')
                bw=m.elastic.amplitudes(z);cbw=coherence_from_amplitudes(z,bw)
                if method=='bloch':psi=bw;outside=np.zeros(len(z));norm_error=0.
                else:
                    GEO.harmonics(grid,max(pc,bc))
                    ff=propagate(z,acceleration_kv=cfg.acceleration_kv,tilt_mrad_xy=m.elastic.microscope.tilt_mrad_xy,
                        grid_points=grid,slice_step_nm=step,potential_cutoff_inv_angstrom=pc,return_amplitudes=True)
                    psi,outside=project_fft_amplitudes(ff,m.elastic.beams.hkl);norm_error=ff.norm_error
                c=coherence_from_amplitudes(z,psi);obs=selected_observables(source,replace(cfg,potential_cutoff=pc,beam_cutoff=bc),m,c)
                result=[]
                for r in obs:
                    sig=r['detector_total'];mag=r['magnetic_difference'];non=r['nonmagnetic_difference']
                    result.append(dict(delta_x_mrad=x,delta_y_mrad=y,method=method,potential_cutoff=pc,beam_cutoff=bc,beam_count=n,fft_grid=grid,slice_step_nm=step,
                        detector_grid=17,depth_steps=cfg.depth_steps,kernel_mib=memory,coherence_bw_relative=float(np.linalg.norm(c-cbw)/np.linalg.norm(cbw)),
                        outside_common_max=float(outside.max()),fft_norm_error=float(norm_error),magnetic_asymmetry=mag/sig,
                        nonmagnetic_asymmetry=non/sig,shot_noise_proxy=abs(mag)/np.sqrt(sig),**r))
                np.savez_compressed(checkpoint,depth_nm=z,beam_hkl=m.elastic.beams.hkl,amplitudes=psi,coherence=c,fft_outside=outside)
                write_json(f,dict(signature=signature,npz_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),rows=result))
                records.extend(result);csv_write(root/'convergence_summary.csv',records)
                print(f'CONTROL ({x:g},{y:g}) p={pc} b={bc} {method} g={grid} step={step}',flush=True)
    csv_write(root/'convergence_summary.csv',records)
    write_json(root/'convergence_settings.json',dict(signature=signature,parent_signature=parent,implementation_sha256=codehash,orientations=poses,
        policy='Selected native features only; detector grid17; BW27/57/81/121, matched FFT32/64; both physical cutoffs; halved slice step at larger cutoff. No global convergence claim.'))
    from .ni_017_high_mistilt_analysis import convergence_findings
    convergence_findings(root)


if __name__=='__main__':
    from .ni_017_high_mistilt_xy import ROOT,SOURCE,Config
    controls(SOURCE,ROOT,Config())
