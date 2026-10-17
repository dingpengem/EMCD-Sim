"""Four-point matched BW/FFT double-channel Ni validation; compact checkpoints."""
from dataclasses import replace,asdict
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import time
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from io import BytesIO
import ni_prb2007_geometry_validation as study
from ni_double_channeling_bw import rows_for
from emcd_sim.multislice_double_channeling import (ProjectedNiFFT,incident_fields,
    multislice_double_channeling_response,transition_modes)
from emcd_sim.double_channeling import double_channeling_response,intensities_from_response
from emcd_sim.multislice_reference import fft_multislice_ni
from emcd_sim.multislice_emcd_reference import project_fft_amplitudes,coherence_from_amplitudes
from emcd_sim.elastic import BeamSet
from emcd_sim.emcd_angular_plots import decorate_reciprocal_map,coordinate_markers
from emcd_sim.geometry import electron_wavelength_angstrom
from emcd_sim.gui.memory_budget import memory_snapshot,reserve_memory

ROOT=Path('outputs/ni_double_channeling_ms_validation')
REFERENCE=Path('outputs/ni_double_channeling_bw')
ENERGIES=study.base.ENERGIES
THICKNESSES=(10.,12.,20.,30.)


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def verify_reference(c,detector):
    m=json.loads((REFERENCE/'configuration.json').read_text())
    assert m['source_sha256']==c['cfg'].source_sha256
    assert m['settings']==study.base.clean(asdict(c['settings']))
    assert m['hkl']==study.base.clean(c['hkl'])
    assert m['energies_ev']==list(ENERGIES)
    assert m['grid']==detector.grid and m['subpixels']==detector.subpixels
    assert m['halfwidth_cycles_angstrom']==detector.halfwidth
    assert m['config']['eta']==m['config']['beta']==1
    assert m['config']['radius']==c['cfg'].radius
    np.testing.assert_array_equal(m['detector_centers'],c['centers'])
    np.testing.assert_array_equal(m['detector_areas'],detector.areas)
    for path,sha in m['implementation_sha256'].items():assert digest(path)==sha,path
    assert abs(c['s'][c['hkl'].index((2,0,0))])<1e-12
    return dict(verified=True,reference_commit=json.loads((REFERENCE/'delivery_provenance.json').read_text())['commit'],
        primary_bw_reused=True,source_sha256=m['source_sha256'])


def cache(name,parameters,producer):
    folder=ROOT/'checkpoints';folder.mkdir(exist_ok=True)
    path=folder/(name+'.npz')
    params=dict(parameters,implementation_sha256=digest('src/emcd_sim/multislice_double_channeling.py'))
    encoded=json.dumps(study.base.clean(params),sort_keys=True)
    if path.exists():
        with np.load(path,allow_pickle=False) as data:
            assert str(data['parameters_json'])==encoded,f'Checkpoint settings changed: {name}'
            return {k:data[k].copy() for k in data.files if k!='parameters_json'}
    start=time.perf_counter();data=producer()
    data['elapsed_seconds']=np.array(time.perf_counter()-start)
    np.savez_compressed(path,parameters_json=np.array(encoded),**data)
    return data


def _calculate_ms(c,detector,t,*,depth=257,step=.04,fft=32,cutoff=2.2,basis=None):
    elastic=c['model'].elastic if basis is None else replace(c['model'].elastic,beams=basis)
    if hasattr(elastic.potential,'cutoff_inv_angstrom'):
        elastic=replace(elastic,potential=replace(elastic.potential,cutoff_inv_angstrom=cutoff))
    grid=ProjectedNiFFT.build(elastic,grid_points=fft,potential_cutoff=cutoff,systematic_row=True,row_reduction=True)
    incoming=incident_fields(grid,t,depth_steps=depth,slice_step_nm=step)
    q=np.column_stack((detector.x,detector.y));raw=np.empty((2,4));responses=[];diagnostics=[]
    for ie,e in enumerate(ENERGIES):
        response,info=multislice_double_channeling_response(elastic,float(e),q,t,fft_grid=fft,
            potential_cutoff=cutoff,systematic_row=True,row_reduction=True,depth_steps=depth,
            slice_step_nm=step,prepared_grid=grid,prepared_incoming=incoming)
        for rev in range(2):
            values=intensities_from_response(response,c['ts'][rev].tensor_angstrom2_per_ev[ie])
            assert values.min()>-1e-12
            raw[ie,2*rev:2*rev+2]=np.einsum('dp,p->d',detector.w[0],values)*detector.dq2
        responses.append(response);diagnostics.append(info)
    entrance=study.contract_detectors(c,coherence_from_amplitudes(incoming[1],incoming[0][:,grid.indices(c['hkl'])]),t,detector)[0]
    return dict(raw=raw,entrance=entrance,response=np.array(responses),
        diagnostics_json=np.array(json.dumps(study.base.clean(diagnostics))))


def calculate_ms(c,detector,t,*,depth=257,step=.04,fft=32,cutoff=2.2,basis=None):
    # Reserve retained incoming fields and potential before their construction.
    retained=(32*depth*fft+64*fft**2)/2**20+2
    with reserve_memory(retained,2048):
        return _calculate_ms(c,detector,t,depth=depth,step=step,fft=fft,cutoff=cutoff,basis=basis)


def relative_error(actual,reference):
    scale=np.maximum(abs(actual),abs(reference))
    return np.divide(abs(actual-reference),scale,out=np.full_like(scale,np.nan),where=scale>1e-12*scale.max())


def savefig(fig,name):
    fig.tight_layout()
    for ext in ('png','svg'):
        buffer=BytesIO();fig.savefig(buffer,format=ext,dpi=180);(ROOT/f'{name}.{ext}').write_bytes(buffer.getvalue())


def line_figures(rows,differences):
    colors={'bw_entrance':'tab:blue','ms_entrance':'tab:blue','bw_double':'tab:orange','ms_double':'tab:orange'}
    def plot(ax,edge,metric,methods):
        for method in methods:
            selected=[r for r in rows if r['method']==method and r['edge']==edge]
            ax.plot([r['thickness_nm'] for r in selected],[r[metric] for r in selected],
                'o-' if method.startswith('bw') else 'x--',color=colors[method],label=method)
        ax.set(xlabel='Thickness (nm)',title=edge);ax.axhline(0,color='.5',lw=.5);ax.legend(fontsize=7)
    for number,edge in enumerate(('L3','L2'),1):
        f=Figure(figsize=(6,4));FigureCanvasAgg(f);ax=f.add_subplot()
        plot(ax,edge,'prb_relative_dichroism_percent',('bw_double','ms_double'))
        ax.set_ylabel('Signed raw PRB dichroism (%)');savefig(f,f'figure_{number}_{edge}_double')
    f=Figure(figsize=(10,4));FigureCanvasAgg(f)
    for i,edge in enumerate(('L3','L2')):
        ax=f.add_subplot(1,2,i+1);plot(ax,edge,'prb_relative_dichroism_percent',colors)
        ax.set_ylabel('Signed raw PRB dichroism (%)')
    savefig(f,'figure_3_entrance_vs_double')
    f=Figure(figsize=(10,7));FigureCanvasAgg(f)
    for i,edge in enumerate(('L3','L2')):
        for j,metric in enumerate(('D_mag','D_even')):
            ax=f.add_subplot(2,2,i*2+j+1);plot(ax,edge,metric,('bw_double','ms_double'))
            ax.set_ylabel(metric+' (relative intensity units)')
            if metric=='D_even':
                ax.set_ylim(-1e-15,1e-15)
                ax.text(.03,.92,'Symmetry: roundoff only',transform=ax.transAxes,fontsize=8)
    savefig(f,'figure_4_reversal_components')
    f=Figure(figsize=(10,4));FigureCanvasAgg(f)
    for i,metric in enumerate(('max_raw_symmetric_relative','D_mag_relative')):
        ax=f.add_subplot(1,2,i+1)
        for edge in ('L3','L2'):
            r=[x for x in differences if x['edge']==edge and x['comparison']=='double']
            ax.plot([x['thickness_nm'] for x in r],[x[metric] for x in r],'o-',label=edge)
        ax.set(xlabel='Thickness (nm)',ylabel=metric,title='MS versus reused BW');ax.legend()
    savefig(f,'figure_7_discrepancies')


def make_maps(c,parameters):
    n=49;q=np.linspace(-.7,.7,n);qx,qy=np.meshgrid(q,q,indexing='xy')
    pixels=np.column_stack((qx.ravel(),qy.ravel()));arrays=dict(qx=qx,qy=qy,energy_ev=ENERGIES)
    diagnostics=[]
    for ie,e in enumerate(ENERGIES):
        def produce():
            ms,info=multislice_double_channeling_response(c['model'].elastic,float(e),pixels,12.,
                fft_grid=32,potential_cutoff=2.2,systematic_row=True,row_reduction=True,depth_steps=257)
            bw=double_channeling_response(c['model'].elastic,float(e),pixels,12.)
            return dict(ms=ms,bw=bw,diagnostics_json=np.array(json.dumps(study.base.clean(info))))
        data=cache(f'map_{ie}',dict(parameters,energy_ev=float(e),thickness_nm=12.,map_grid=n,map_halfwidth=.7),produce)
        diagnostics.append(json.loads(str(data['diagnostics_json'])))
        tensor=c['ts'][0].tensor_angstrom2_per_ev[ie]
        maps=[]
        for method in ('bw','ms'):
            r=data[method]
            even=np.einsum('pab,ab->p',r,tensor.real).real.reshape(n,n)
            odd=np.einsum('pab,ab->p',r,1j*tensor.imag).real.reshape(n,n)
            maps.append((odd,even,even+odd))
            for name,v in zip(('magnetic','nonmagnetic','total'),maps[-1]):arrays[f'{method}_{ie}_{name}']=v
        fig=Figure(figsize=(13,7));FigureCanvasAgg(fig)
        for row,method in enumerate(('BW','MS')):
            for col,name in enumerate(('Magnetic odd','Reversal even','Total +M')):
                ax=fig.add_subplot(2,3,row*3+col+1)
                limit=max(float(abs(maps[m][col]).max()) for m in (0,1))
                image=ax.imshow(maps[row][col],origin='lower',extent=(-.7,.7,-.7,.7),
                    cmap='RdBu_r' if col==0 else 'viridis',vmin=-limit if col==0 else 0,vmax=limit,
                    interpolation='nearest')
                ax.set(title=f'{method} {name}',xlabel='qx (cycles/A)',ylabel='qy (cycles/A)')
                decorate_reciprocal_map(ax,c['model'],(-.7,.7,-.7,.7))
                fig.colorbar(image,ax=ax,shrink=.75)
        edge=('L3','L2')[ie];fig.suptitle(f'Ni [001] (200), 200 kV, 12 nm | {edge} {e:.4f} eV | raw intrinsic components')
        savefig(fig,f'figure_{5+ie}_{edge}_maps')
    np.savez_compressed(ROOT/'angular_maps.npz',**arrays)
    return diagnostics


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    preserved={str(folder):study.base.file_hashes(folder) for folder in
        (REFERENCE,Path('outputs/ni_voltage_dependence_100_200_300kv'))}
    saved=study.base.load_project('outputs/gui_stage_d/windows_20261016/reference_project')
    c=study.make_context(saved,(0,0,1),2048,systematic_row=True)
    detector=study.DetectorGrid(c['centers'],(c['cfg'].radius,),193,.5,64)
    reference=verify_reference(c,detector)
    for tensor in c['ts']:
        for t in tensor.tensor_angstrom2_per_ev:transition_modes(t)
    parameters=dict(source_sha256=c['cfg'].source_sha256,settings=asdict(c['settings']),
        hkl=c['hkl'],energies_ev=ENERGIES,eta=1.,beta=1.,centers=c['centers'],radius=c['cfg'].radius,
        grid=193,halfwidth=.5,subpixels=64,depth_steps=257,slice_step_nm=.04,fft_grid=32,
        potential_cutoff=2.2,systematic_row=True,row_reduction=True,batch_pixels=32)
    metadata=dict(parameters=parameters,bw_reference=reference,base_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        source_sha256=c['cfg'].source_sha256,detector_areas=detector.areas,s_angstrom_inv=c['s'],
        qz_convention='-E_loss/(h*v_in), cycles/angstrom; frozen and identical to BW',
        outgoing_energy_kv=[200-float(e)/1000 for e in ENERGIES],
        outgoing_wavelength_angstrom=[electron_wavelength_angstrom(200-float(e)/1000) for e in ENERGIES],
        coordinate_markers=coordinate_markers(c['model'].elastic.microscope),postedge_normalized=False,
        software=dict(python=study.base.platform.python_version(),numpy=np.__version__),
        implementation_sha256={str(p):digest(p) for p in (Path(__file__),Path('src/emcd_sim/multislice_double_channeling.py'),
            Path('src/emcd_sim/double_channeling.py'),Path('src/emcd_sim/multislice_reference.py'))})
    study.base.write_json(ROOT/'configuration.json',metadata)
    old=list(csv.DictReader(Path('outputs/ni_voltage_dependence_100_200_300kv/results.csv').open()))
    legacy=[]
    # Reproduce every compatible entrance-only MS point before new double-channel production.
    for t in THICKNESSES:
        def reproduce():
            z=np.linspace(0,t,64)
            f=fft_multislice_ni(z,acceleration_kv=200,tilt_mrad_xy=c['settings'].tilt,grid_points=32,
                slice_step_nm=.04,potential_cutoff_inv_angstrom=2.2,return_amplitudes=True,systematic_row_hkl=(2,0,0))
            a,outside=project_fft_amplitudes(f,c['hkl'])
            raw=study.contract_detectors(c,coherence_from_amplitudes(z,a),t,detector)[0]
            return dict(raw=raw,norm_error=np.array(f.norm_error),max_outside=np.array(outside.max()))
        data=cache(f'legacy_t{int(t)}',dict(parameters,depth_steps=64,thickness_nm=t),reproduce)
        expected=np.array([[float(r[k]) for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')]
            for r in old if float(r['voltage_kv'])==200 and r['solver']=='fft-multislice' and float(r['thickness_nm'])==t])
        np.testing.assert_allclose(data['raw'],expected,rtol=1e-13,atol=1e-15)
        legacy.append(dict(thickness_nm=t,max_raw_abs_error=float(abs(data['raw']-expected).max())))
    study.base.write_csv(ROOT/'legacy_reproduction.csv',legacy)
    print('All four previous entrance-only MS raw points reproduced before double-channel production.',flush=True)
    rows=[];arrays={};performance=[]
    for t in THICKNESSES:
        data=cache(f'primary_t{int(t)}',dict(parameters,thickness_nm=t),lambda:calculate_ms(c,detector,t))
        prior=np.load(REFERENCE/f't{int(t):02d}.npz')
        for method,raw in (('bw_entrance',prior['entrance']),('bw_double',prior['double']),
                           ('ms_entrance',data['entrance']),('ms_double',data['raw'])):
            rows.extend(rows_for(raw,t,method));arrays[f'{method}_t{int(t)}']=raw
        diagnostics=json.loads(str(data['diagnostics_json']))
        performance.append(dict(thickness_nm=t,elapsed_seconds=float(data['elapsed_seconds']),diagnostics=diagnostics,
            memory_snapshot_after=memory_snapshot()))
        print(f'{t:g} nm MS double: {study.base.observables(data["raw"])["prb_relative_dichroism_percent"]}; {float(data["elapsed_seconds"]):.2f} s',flush=True)
        study.base.write_csv(ROOT/'results.csv',rows)
        study.base.write_json(ROOT/'performance.json',performance)
    differences=[]
    for t in THICKNESSES:
        for comp in ('entrance','double'):
            a=study.base.observables(arrays[f'bw_{comp}_t{int(t)}']);b=study.base.observables(arrays[f'ms_{comp}_t{int(t)}'])
            ra,rb=arrays[f'bw_{comp}_t{int(t)}'],arrays[f'ms_{comp}_t{int(t)}']
            for ie,edge in enumerate(('L3','L2')):
                diff=dict(thickness_nm=t,edge=edge,comparison=comp,max_raw_absolute=float(abs(ra[ie]-rb[ie]).max()),
                    max_raw_symmetric_relative=float(relative_error(ra[ie],rb[ie]).max()))
                for k in a:
                    diff[k+'_absolute']=float(abs(b[k][ie]-a[k][ie]));scale=max(abs(a[k][ie]),abs(b[k][ie]))
                    diff[k+'_relative']=float(abs(b[k][ie]-a[k][ie])/scale) if scale>1e-10 else np.nan
                    diff[k+'_signed_ms_minus_bw']=float(b[k][ie]-a[k][ie])
                differences.append(diff)
    study.base.write_csv(ROOT/'discrepancies.csv',differences)
    # Separate step, depth, FFT bandwidth, path-basis and physical potential controls at 12 nm.
    controls=[];baseline=arrays['ms_double_t12']
    for name,kwargs in (('slice_half',dict(step=.02)),('depth_double',dict(depth=513)),
        ('fft48',dict(fft=48)),('basis13',dict(basis=BeamSet(tuple([(0,0,0)]+[(s*2*j,0,0) for j in range(1,7) for s in (1,-1)])))),
        ('potential_1p8',dict(cutoff=1.8)),('potential_2p6',dict(cutoff=2.6))):
        p=dict(parameters,control=name,thickness_nm=12.,depth_steps=kwargs.get('depth',257),
            slice_step_nm=kwargs.get('step',.04),fft_grid=kwargs.get('fft',32),
            potential_cutoff=kwargs.get('cutoff',2.2),
            hkl=c['hkl'] if 'basis' not in kwargs else kwargs['basis'].hkl)
        data=cache(name,p,lambda kwargs=kwargs:calculate_ms(c,detector,12.,**kwargs))
        arrays[name]=data['raw']
        controls.append(dict(control=name,depth_steps=p['depth_steps'],maximum_slice_step_nm=p['slice_step_nm'],
            fft_grid=p['fft_grid'],beam_count=len(p['hkl']),potential_cutoff=p['potential_cutoff'],max_raw_symmetric_relative=float(relative_error(data['raw'],baseline).max()),
            max_prb_difference_pp=float(abs(study.base.observables(data['raw'])['prb_relative_dichroism_percent']-
                study.base.observables(baseline)['prb_relative_dichroism_percent']).max()),elapsed_seconds=float(data['elapsed_seconds'])))
        print(name,controls[-1],flush=True)
    study.base.write_csv(ROOT/'convergence.csv',controls)
    basis_comparisons=[]
    with np.load(REFERENCE/'results.npz',allow_pickle=False) as old_basis:
        for count,bw,ms in ((11,arrays['bw_double_t12'],arrays['ms_double_t12']),
                (13,old_basis['basis_13_13'],arrays['basis13'])):
            a,b=study.base.observables(bw),study.base.observables(ms)
            basis_comparisons.append(dict(beam_count=count,thickness_nm=12.,
                max_raw_relative=float(relative_error(bw,ms).max()),
                max_prb_difference_pp=float(abs(a['prb_relative_dichroism_percent']-b['prb_relative_dichroism_percent']).max()),
                max_D_mag_absolute=float(abs(a['D_mag']-b['D_mag']).max())))
    study.base.write_csv(ROOT/'controlled_basis_comparison.csv',basis_comparisons)
    np.savez_compressed(ROOT/'results.npz',**arrays,energy_ev=ENERGIES,thickness_nm=THICKNESSES,
        configuration_json=json.dumps(study.base.clean(metadata)))
    line_figures(rows,differences)
    metadata['map_diagnostics']=make_maps(c,parameters)
    study.base.write_json(ROOT/'configuration.json',metadata)
    for folder,hashes in preserved.items():assert study.base.file_hashes(Path(folder))==hashes
    assert digest(c['cfg'].source)==c['cfg'].source_sha256
    study.base.write_json(ROOT/'preservation.json',dict(previous_outputs_unchanged=True,source_unchanged=True,reference_hashes=preserved))
    print('Completed matched four-point validation, controlled convergence and angular maps.',flush=True)


if __name__=='__main__':main()
