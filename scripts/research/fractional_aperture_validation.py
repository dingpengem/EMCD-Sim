"""Small area/near-2BC/Bloch-FFT validation of shared aperture weights."""
from __future__ import annotations

import argparse
import csv
from dataclasses import replace
import json
from pathlib import Path
import numpy as np

from emcd_sim.benchmark import nickel_apertures
from emcd_sim.multislice_emcd_reference import MultisliceEMCDConfig, run_multislice_emcd_reference
from emcd_sim.xmcd_geometry_decomposition import A, GeometryDecompositionConfig, run_geometry_decomposition, _json_safe

METRICS = ('Sigma_ref','A_mag','A_nonmag','A_raw_plus','f_mag')


def run_fractional_aperture_validation(xmcd_file, *, grids=(65,97), subpixels=64):
    """Selected L3 only; fixed physical settings, no scan of beam/depth controls."""
    if len(grids)<2 or any(not isinstance(g,int) or g<9 for g in grids) or np.any(np.diff(grids)<=0):
        raise ValueError('Require at least two increasing integer detector grids >=9')
    area_rows, rows, geometry_runs, method_runs = [],[],[],[]
    detectors,_ = nickel_apertures('near-2bc')
    for grid in (33,65,97):
        q=np.linspace(-1.,1.,grid); qx,qy=np.meshgrid(q,q,indexing='xy')
        for mode in ('binary','fractional'):
            for label,det in detectors.items():
                area_rows.append(dict(grid=grid,detector=label,
                    **det.integration_info(qx,qy,mode=mode,subpixels=subpixels)))
    base=GeometryDecompositionConfig(conditions=('near-2bc',),finer_grid=None)
    for mode in ('binary','fractional'):
        previous=None
        for grid in grids:
            result=run_geometry_decomposition(xmcd_file,replace(base,grid=grid,
                integration_mode=mode,aperture_subpixels=subpixels))
            record=next(r for r in result.records if r['group']==A)
            r=dict(scenario='ni-near-2bc',method='bloch',integration_mode=mode,
                   grid=grid,aperture_subpixels=subpixels,energy_ev=record['energy_ev'],
                   detectors_json=record['detectors_json'],**{k:record[k] for k in METRICS})
            for key in METRICS:
                r[key+'_change_previous']=r[key]-previous[key] if previous else np.nan
            r['Sigma_ref_relative_change_previous']=(r['Sigma_ref']/previous['Sigma_ref']-1) if previous else np.nan
            rows.append(r); previous=r
            geometry_runs.append(result.metadata)
    # Respect the existing memory guard: 45 common beams on only a 33x33 grid.
    config=MultisliceEMCDConfig(conditions=('near-2bc',),thickness_nm=(30.,))
    previous_method=None
    for mode in ('binary','fractional'):
        result=run_multislice_emcd_reference(xmcd_file,replace(config,
            integration_mode=mode,aperture_subpixels=subpixels))
        if previous_method is not None:
            for key in ('coherence_bw','coherence_ms','bw_amplitudes','ms_amplitudes_projected'):
                if not np.array_equal(result.cases[0][key],previous_method.cases[0][key]):
                    raise RuntimeError('Changing aperture integration unexpectedly changed incident propagation')
        previous_method=result
        info=result.metadata['geometries']['near-2bc']
        for record in result.records:
            r=dict(scenario='bw-ms-common-potential',method=record['method'],integration_mode=mode,
                grid=config.detector_grid,aperture_subpixels=subpixels,energy_ev=record['energy_ev'],
                detectors_json=json.dumps(info['aperture_integration']),**{k:record[k] for k in METRICS})
            r.update({k+'_change_previous':np.nan for k in METRICS})
            r['Sigma_ref_relative_change_previous']=np.nan
            rows.append(r)
        method_runs.append(result.metadata)
    metadata=dict(model='XMCD-constrained effective MDFF; entrance-only; relative intensity; not quantitative Ni',
        grids=list(grids),aperture_subpixels=subpixels,
        geometry_runs=geometry_runs,method_runs=method_runs,
        xmcd_sha256=geometry_runs[0]['xmcd_sha256'],software_commit=geometry_runs[0]['software_commit'],
        area_units='(cycles/angstrom)^2',pixel_model='Constant intensity at grid center; geometric boundary midpoint subpixels',
        weights='Cached per physical aperture, exact grid axes, mode and subpixel resolution; no area rescaling',
        same_wave_and_coherence_across_modes=True,absolute_cross_section=False,outgoing_channeling=False,
        quantitative_Ni=False,field_sampling_converged=False,beam_basis_converged=False)
    return area_rows,rows,metadata


def save_fractional_aperture_validation(area_rows,rows,metadata,output):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    for name,records in [('aperture_area_comparison',area_rows),('emcd_comparison',rows)]:
        with (output/(name+'.csv')).open('w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    arrays={prefix+k:np.asarray([r[k] for r in records])
            for prefix,records in [('area_',area_rows),('emcd_',rows)] for k in records[0]}
    np.savez_compressed(output/'fractional_aperture_comparison.npz',**arrays)
    (output/'validation_metadata.json').write_text(json.dumps(_json_safe(metadata),indent=2,allow_nan=False)+'\n',encoding='utf-8')


def plot_fractional_aperture_validation(area_rows,rows,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(11,8),constrained_layout=True)
    for mode in ('binary','fractional'):
        areas=[r for r in area_rows if r['integration_mode']==mode and r['detector']=='A']
        data=[r for r in rows if r['integration_mode']==mode and r['scenario']=='ni-near-2bc']
        x=[r['grid'] for r in data]
        axes[0,0].plot([r['grid'] for r in areas],[100*abs(r['relative_area_error']) for r in areas],'o-',label=mode)
        axes[0,1].plot(x,[r['Sigma_ref'] for r in data],'o-',label=mode)
        for key,marker in [('A_mag','o'),('A_nonmag','s'),('A_raw_plus','x')]:
            axes[1,0].plot(x,[r[key]-data[0][key] for r in data],marker+'-',label=mode+' '+key)
        axes[1,1].plot(x,[r['f_mag'] for r in data],'o-',label=mode)
    axes[0,0].set_yscale('log')
    for ax,title in zip(axes.flat,('Uniform-field absolute area error (%)','Collected Sigma_ref (relative intensity)',
                                  'Asymmetry change from first grid (absolute units)','Magnetic contribution index')):
        ax.set(xlabel='Reciprocal grid size',title=title); ax.legend(fontsize=8); ax.grid(alpha=.25)
    fig.suptitle('Shared binary / fractional circular apertures | XMCD-effective, entrance-only\n'
                 'Relative intensity; area agreement is not intensity-field convergence or quantitative Ni validation')
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    fig.savefig(output/'fractional_aperture_validation.png',dpi=150); plt.close(fig)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--xmcd-file',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('outputs/ni_fractional_aperture_validation'))
    p.add_argument('--grids',type=int,nargs='+',default=[65,97])
    p.add_argument('--aperture-subpixels',type=int,default=64)
    args=p.parse_args(argv)
    try:
        areas,rows,meta=run_fractional_aperture_validation(args.xmcd_file,grids=tuple(args.grids),subpixels=args.aperture_subpixels)
    except ValueError as exc:
        p.error(str(exc))
    save_fractional_aperture_validation(areas,rows,meta,args.output)
    plot_fractional_aperture_validation(areas,rows,args.output)
    for r in rows:
        print(json.dumps(_json_safe({k:v for k,v in r.items() if k!='detectors_json'}),allow_nan=False))
    print(f'Output: {args.output}; spatial-field, depth and beam convergence remain unverified.')


if __name__=='__main__':
    main()
