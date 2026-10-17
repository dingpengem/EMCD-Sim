"""Fixed-reciprocal-acceptance Ni [001] row study at 100/200/300 kV.

Existing BW/FFT/tensor engines and memory admission are reused. The coarse
200 kV reference is preserved; five compatible fine-grid points are reused.
"""
import argparse
import csv
from dataclasses import asdict, replace
import hashlib
from io import BytesIO
import json
from pathlib import Path
import subprocess

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

import ni_prb2007_geometry_validation as study
from emcd_sim.geometry import electron_beta, electron_wavelength_angstrom, characteristic_qz_angstrom_inv
from emcd_sim.elastic import BeamSet

base=study.base
VOLTAGES=(100,200,300)
COLORS={100:'#2166ac',200:'#d95f02',300:'#238b45'}
REFERENCE=Path('outputs/ni_prb2007_geometry_validation')


def voltage_physics(context):
    """Use the solver's own Fourier-potential/phase convention, plus SI check."""
    elastic=context['model'].elastic; kv=context['settings'].voltage
    gamma=1+1000*kv/510998.95; beta=electron_beta(kv)
    wavelength=electron_wavelength_angstrom(kv); velocity=beta*299792458.
    H=elastic.hamiltonian_nm_inv(); j=elastic.beams.hkl.index((2,0,0))
    V=elastic.potential.original.fourier_potential_volts((2,0,0))
    sigma=abs(H[0,j])/(10*abs(V))  # rad/(V Angstrom); H is per nm
    sigma_si=1.602176634e-19/((6.62607015e-34/(2*np.pi))*velocity)*1e-10
    xi=elastic.extinction_distance_nm((2,0,0))
    assert np.isclose(sigma,sigma_si,rtol=1e-7)
    assert np.isclose(xi,np.pi/abs(H[0,j]),rtol=1e-13)
    values,vectors=np.linalg.eigh(H)
    ideal=replace(elastic,beams=BeamSet(((0,0,0),(2,0,0))))
    ideal_values=np.linalg.eigvalsh(ideal.hamiltonian_nm_inv())
    period=2*np.pi/np.diff(ideal_values)[0]
    assert np.isclose(period,xi,rtol=1e-13)
    psi=ideal.amplitudes(np.array([0.,xi/2,xi]))
    np.testing.assert_allclose(abs(psi[:,1])**2,[0,1,0],atol=1e-12)
    info=dict(voltage_kv=kv,gamma=gamma,beta=beta,electron_velocity_m_per_s=velocity,
        wavelength_angstrom=wavelength,interaction_constant_rad_per_V_angstrom=sigma,
        interaction_constant_rad_per_V_nm=10*sigma,independent_SI_interaction_constant=sigma_si,
        xi_200_nm=xi,H_000_200_magnitude_per_nm=abs(H[0,j]),V_200_volts_real=V.real,
        V_200_volts_imag=V.imag,ideal_eigenvalue_gap_period_nm=period,
        tilt_x_mrad=context['settings'].tilt[0],tilt_y_mrad=context['settings'].tilt[1],
        target_beam_index=j,transmitted_beam_index=elastic.beams.hkl.index((0,0,0)),
        s_200_inv_angstrom=context['s'][j],collection_semiangle_mrad=1000*wavelength*context['cfg'].radius,
        qz_magnitude_cycles_per_angstrom=[float(characteristic_qz_angstrom_inv(e,kv)) for e in base.ENERGIES])
    arrays=dict(hamiltonian_nm_inv=H,eigenvalues_nm_inv=values,eigenvectors=vectors,
        entrance_eigenmode_coefficients=vectors[0].conj(),beam_hkl=np.asarray(context['hkl']),g=context['g'],
        excitation_errors=context['s'],ideal_sample_thickness_nm=base.thickness_sequence(),
        ideal_sample_200_intensity=abs(ideal.amplitudes(base.thickness_sequence())[:,1])**2)
    return info,arrays


def inspect_reference(context, detector):
    """Gate reuse on actual physical/numerical settings, not just file labels."""
    meta=json.loads((REFERENCE/'configuration.json').read_text())
    old=meta['geometry']['001']; cfg=context['cfg']
    assert old['systematic_row_projection'] is True
    assert old['settings']==base.clean(asdict(context['settings']))
    assert old['config']['source_sha256']==cfg.source_sha256
    for name in ('model','eta','beta','radius','depth','fft_grid','slice_step','subpixels'):
        assert old['config'][name]==getattr(cfg,name),name
    np.testing.assert_array_equal(old['beam_hkl'],context['hkl'])
    np.testing.assert_allclose(old['frame'],context['R'],atol=1e-14)
    np.testing.assert_allclose(old['centers'],context['centers'],atol=1e-14)
    np.testing.assert_array_equal(meta['fixed_energies_ev'],base.ENERGIES)
    for path,digest in meta['implementation_sha256'].items():
        assert hashlib.sha256((Path('src/emcd_sim')/path).read_bytes()).hexdigest()==digest,path
    return dict(physical_settings_match=True,coarse_reference_grid=33,primary_grid=detector.grid,
        reason_for_fine_grid='Earlier validation: 12 nm L3 changes from -11.775709% (33x33, halfwidth 1) to -11.853783% (193x193, halfwidth 0.5). Fine primary grid avoids under-resolved intensity-field quadrature.',
        reusable_193_grid_thicknesses_nm=list(study.REPRESENTATIVE),
        reused_coarse_full_curve=True,coarse_full_curve_recalculated=False)


def reuse_fine_200(t,context,detector):
    if detector.grid==193 and t in study.REPRESENTATIVE:
        path=REFERENCE/'checkpoints'/f'B_001_t{int(t):03d}_d64_g193_row.npz'
    elif detector.grid==385 and t==12:
        path=REFERENCE/'checkpoints/B-grid_001_t012_d64_g385_row.npz'
    else:
        return None
    with np.load(path,allow_pickle=False) as f:
        parameters=json.loads(str(f['parameters_json']))
        assert parameters['grid']==detector.grid and parameters['halfwidth']==detector.halfwidth
        assert parameters['depth']==64 and parameters['systematic_row_hkl']==[2,0,0]
        assert parameters['source_sha256']==context['cfg'].source_sha256
        assert parameters['settings']==base.clean(asdict(context['settings']))
        ir=parameters['radii'].index(context['cfg'].radius)
        np.testing.assert_array_equal(f['areas'][ir],detector.areas[0])
        result={k:f[k] for k in f.files if k!='parameters_json'}
    for method in base.METHODS:
        result[method+'__raw']=result[method+'__raw'][ir:ir+1].copy()
    result['areas']=detector.areas
    result['reused_source_path']=np.array(str(path))
    return result


def rows_for_voltage(context,physics,t,detector,point,origin):
    rows=study.rows_for_point('primary','001',context,t,64,detector,point)
    for row in rows:
        row.update(physics,normalized_thickness=t/physics['xi_200_nm'],data_origin=origin)
        row['qz_magnitude_cycles_per_angstrom']=physics['qz_magnitude_cycles_per_angstrom'][base.EDGES.index(row['edge'])]
    return rows


def peak_indices(y):
    y=np.asarray(y)
    return np.flatnonzero((y[1:-1]>y[:-2])&(y[1:-1]>=y[2:]))+1


def compare_controls(root,rows,controls):
    comparisons=[]
    for r in controls:
        kv=int(r['accelerating_voltage_kv'])
        main=next(x for x in rows if x['voltage_kv']==kv and x['solver']==r['solver'] and x['edge']==r['edge'] and x['thickness_nm']==r['thickness_nm'])
        floor=.05*max(abs(x['D_mag']) for x in rows if x['voltage_kv']==kv and x['solver']==r['solver'] and x['edge']==r['edge'])
        comparisons.append(dict(voltage_kv=kv,control=r['stage'],solver=r['solver'],edge=r['edge'],thickness_nm=r['thickness_nm'],
            primary_grid=193,reference_grid=r['detector_grid'],reference_integration=r['coherence_integration'],
            prb_primary_minus_reference_pp=main[base.METRICS[0]]-r[base.METRICS[0]],
            magnetic_primary_minus_reference_pp=main[base.METRICS[1]]-r[base.METRICS[1]],
            I_A_relative_difference=main['I_A_plus']/r['I_A_plus']-1,I_B_relative_difference=main['I_B_plus']/r['I_B_plus']-1,
            D_mag_absolute_difference=main['D_mag']-r['D_mag'],
            D_mag_relative_difference=(main['D_mag']/r['D_mag']-1) if abs(r['D_mag'])>=floor else np.nan,
            relative_signal_floor=floor,relative_signal_valid=abs(r['D_mag'])>=floor))
    base.write_csv(root/'numerical_control_errors.csv',comparisons)
    return dict(max_grid_control_prb_difference_pp=max(abs(x['prb_primary_minus_reference_pp']) for x in comparisons if x['control']=='grid-control'),
        max_100nm_BW_depth_error_pp=max(abs(x['prb_primary_minus_reference_pp']) for x in comparisons if x['control']=='depth-control'),
        acceptance='Local trend checks: grid <0.001 pp at 12 nm; 64-node depth error <0.01 pp at 100 nm. Not full convergence or a bound at every thickness.')


def summarize(root,rows,physics,elastic):
    summaries=[]; periods=[]; crossings=[]
    for kv in VOLTAGES:
        xi=physics[kv]['xi_200_nm']
        for method in base.METHODS:
            l3=sorted([r for r in rows if r['voltage_kv']==kv and r['solver']==method and r['edge']=='L3'],key=lambda r:r['thickness_nm'])
            l2=sorted([r for r in rows if r['voltage_kv']==kv and r['solver']==method and r['edge']=='L2'],key=lambda r:r['thickness_nm'])
            peak=max(l3[1:],key=lambda r:abs(r[base.METRICS[0]])); i=int(peak['thickness_nm']/2)
            peak2=max(l2[1:],key=lambda r:abs(r[base.METRICS[0]]))
            summaries.append(dict(voltage_kv=kv,solver=method,xi_200_nm=xi,
                maximum_absolute_L3_percent=abs(peak[base.METRICS[0]]),signed_L3_percent=peak[base.METRICS[0]],
                thickness_at_L3_max_nm=peak['thickness_nm'],normalized_thickness_at_L3_max=peak['thickness_nm']/xi,
                L2_at_L3_max_percent=l2[i][base.METRICS[0]],magnetic_only_at_L3_max_percent=peak[base.METRICS[1]],
                maximum_absolute_L2_percent=abs(peak2[base.METRICS[0]]),signed_L2_at_own_max_percent=peak2[base.METRICS[0]],thickness_at_L2_max_nm=peak2['thickness_nm']))
            for edge,values in zip(base.EDGES,(l3,l2)):
                for a,b in zip(values[1:-1],values[2:]):
                    if a[base.METRICS[0]]*b[base.METRICS[0]]<0:
                        crossings.append(dict(voltage_kv=kv,solver=method,edge=edge,
                            lower_thickness_nm=a['thickness_nm'],upper_thickness_nm=b['thickness_nm'],
                            lower_normalized_thickness=a['thickness_nm']/xi,upper_normalized_thickness=b['thickness_nm']/xi))
            t=base.thickness_sequence(); pop=elastic[kv][method][:,physics[kv]['target_beam_index']]
            ids=peak_indices(pop); ideal_ids=peak_indices(elastic[kv]['ideal_200'])
            periods.append(dict(voltage_kv=kv,solver=method,xi_200_nm=xi,
                ideal_population_period_nm=physics[kv]['ideal_eigenvalue_gap_period_nm'],
                ideal_sampled_200_peak_thicknesses_nm=t[ideal_ids].tolist(),
                multibeam_200_peak_thicknesses_nm=t[ids].tolist(),
                multibeam_sampled_peak_spacings_nm=np.diff(t[ids]).tolist(),
                multibeam_peak_spacings_over_xi=(np.diff(t[ids])/xi).tolist(),
                note='Discrete 2 nm extrema; no fitting, interpolation or smoothing. Multibeam peak spacings are not an extinction-distance definition.'))
    differences=[]
    for kv in VOLTAGES:
        for edge in base.EDGES:
            b=sorted([r for r in rows if r['voltage_kv']==kv and r['solver']=='bloch' and r['edge']==edge],key=lambda r:r['thickness_nm'])
            m=sorted([r for r in rows if r['voltage_kv']==kv and r['solver']=='fft-multislice' and r['edge']==edge],key=lambda r:r['thickness_nm'])
            for x,y in zip(b,m):
                differences.append(dict(voltage_kv=kv,edge=edge,thickness_nm=x['thickness_nm'],
                    **{key:x[key]-y[key] for key in base.METRICS},
                    I_A_plus_difference=x['I_A_plus']-y['I_A_plus'],I_B_plus_difference=x['I_B_plus']-y['I_B_plus']))
    base.write_csv(root/'summary.csv',summaries)
    bw_peaks=[s for s in summaries if s['solver']=='bloch']
    landmark=dict(peak_locations_over_own_xi={str(s['voltage_kv']):s['normalized_thickness_at_L3_max'] for s in bw_peaks},
        physical_peak_spread_over_fixed_200kv_xi=(max(s['thickness_at_L3_max_nm'] for s in bw_peaks)-min(s['thickness_at_L3_max_nm'] for s in bw_peaks))/physics[200]['xi_200_nm'],
        normalized_peak_spread=max(s['normalized_thickness_at_L3_max'] for s in bw_peaks)-min(s['normalized_thickness_at_L3_max'] for s in bw_peaks),
        note='Sampled 2 nm landmark comparison only; no interpolation, fitted amplitude factors or imposed curve collapse.')
    base.write_json(root/'summary.json',dict(voltages=summaries,elastic_periods=periods,sign_change_brackets=crossings,extinction_scaling_landmarks=landmark,
        xi_ratios_to_200={str(k):physics[k]['xi_200_nm']/physics[200]['xi_200_nm'] for k in VOLTAGES},
        velocity_ratios_to_200={str(k):physics[k]['electron_velocity_m_per_s']/physics[200]['electron_velocity_m_per_s'] for k in VOLTAGES},
        bw_ms_max_abs_prb_difference_pp={str(k):{e:max(abs(r[base.METRICS[0]]) for r in differences if r['voltage_kv']==k and r['edge']==e and r['thickness_nm']>0) for e in base.EDGES} for k in VOLTAGES}))
    base.write_csv(root/'bw_ms_differences.csv',differences)
    base.write_json(root/'elastic_periods.json',periods)
    if crossings:base.write_csv(root/'sign_change_brackets.csv',crossings)
    return differences


def make_figures(root,rows,physics,elastic,differences):
    def create(shape=(1,1),size=(9,5)):
        fig=Figure(figsize=size,layout='constrained');FigureCanvasAgg(fig)
        return fig,np.asarray(fig.subplots(*shape)).reshape(shape)
    def save(fig,number):
        # Render in memory so PIL need not reopen an existing Windows image
        # with read/write mode while Explorer/preview handlers are inspecting it.
        for ext in ('png','svg'):
            buffer=BytesIO();fig.savefig(buffer,format=ext,dpi=175)
            (root/f'figure_{number}.{ext}').write_bytes(buffer.getvalue())
    for number,edge,key,normalized in ((1,'L3',base.METRICS[0],False),(2,'L2',base.METRICS[0],False),(3,'L3',base.METRICS[1],False),(4,'L3',base.METRICS[0],True)):
        fig,axes=create();ax=axes[0,0]
        for kv in VOLTAGES:
            for method,ls in zip(base.METHODS,('-','--')):
                selected=sorted([r for r in rows if r['voltage_kv']==kv and r['solver']==method and r['edge']==edge],key=lambda r:r['thickness_nm'])
                ax.plot([r['normalized_thickness'] if normalized else r['thickness_nm'] for r in selected],
                    [r[key] for r in selected],ls,color=COLORS[kv],label=f'{kv} kV '+('BW' if method=='bloch' else 'MS'),lw=1.4)
        ax.axhline(0,color='.45',lw=.7);ax.grid(alpha=.2);ax.legend(ncols=2,fontsize=8)
        ax.set(xlabel='Normalized thickness t / xi_200(V), at each voltage' if normalized else 'Thickness (nm)',ylabel='Signed dichroism (%)',
            title=f'Ni [001] (200) systematic row | {edge} {base.ENERGIES[base.EDGES.index(edge)]:.4f} eV\n'+('Magnetic-only diagnostic' if number==3 else 'Raw PRB paired dichroism')+' | fixed reciprocal-space apertures')
        if not normalized:ax.set_xlim(0,100)
        save(fig,number)
    fig,axes=create((3,1),(9,10))
    for ax,kv in zip(axes.flat,VOLTAGES):
        for j,beam,color in ((physics[kv]['transmitted_beam_index'],'000','#444444'),(physics[kv]['target_beam_index'],'200',COLORS[kv])):
            for method,ls in zip(base.METHODS,('-','--')):
                ax.plot(base.thickness_sequence(),elastic[kv][method][:,j],ls,color=color,label=beam+' '+method,lw=1.1)
        ax.plot(base.thickness_sequence(),elastic[kv]['ideal_200'],':',color='.55',lw=1.,label='Ideal two-beam 200 (diagnostic)')
        ax.axhline(0,color='.6',lw=.6);ax.set(xlim=(0,100),ylabel='Incident intensity fraction',title=f'{kv} kV | ideal xi_200={physics[kv]["xi_200_nm"]:.4f} nm')
        ax.legend(fontsize=7,loc='center left',bbox_to_anchor=(1.01,.5));ax.grid(alpha=.2)
    ax.set_xlabel('Thickness (nm)');save(fig,5)
    fig,axes=create((2,1),(9,8))
    for ax,edge in zip(axes.flat,base.EDGES):
        for kv in VOLTAGES:
            selected=sorted([r for r in differences if r['voltage_kv']==kv and r['edge']==edge],key=lambda r:r['thickness_nm'])
            ax.plot([r['thickness_nm'] for r in selected],[r[base.METRICS[0]] for r in selected],color=COLORS[kv],label=f'{kv} kV')
        ax.axhline(0,color='.4',lw=.7);ax.set(xlim=(0,100),ylabel='BW - MS (percentage points)',title=edge+' raw PRB difference');ax.legend();ax.grid(alpha=.2)
    ax.set_xlabel('Thickness (nm)');save(fig,6)
    fig,axes=create();ax=axes[0,0]
    scaling=[physics[200]['xi_200_nm']*physics[k]['electron_velocity_m_per_s']/physics[200]['electron_velocity_m_per_s'] for k in VOLTAGES]
    ax.plot(VOLTAGES,scaling,'--',color='.4',label='Velocity scaling anchored at computed 200 kV')
    for kv in VOLTAGES:ax.plot(kv,physics[kv]['xi_200_nm'],'o',color=COLORS[kv],label=f'{kv} kV computed')
    ax.set(xlabel='Accelerating voltage (kV)',ylabel='Ideal two-beam xi_200 (nm)',title='Same Ni IAM potential: xi_200 scales with electron velocity')
    ax.grid(alpha=.2);ax.legend(fontsize=8);save(fig,7)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('outputs/ni_voltage_dependence_100_200_300kv'))
    parser.add_argument('--memory-budget-mib',type=int,choices=study.BUDGETS_MIB,default=2048)
    args=parser.parse_args();root=args.output;root.mkdir(parents=True,exist_ok=True)
    preserved=base.file_hashes(REFERENCE)
    saved=base.load_project('outputs/gui_stage_d/windows_20261016/reference_project')
    assert base.load_wien2k_xmcd(saved['config'].source).source_sha256==saved['config'].source_sha256
    contexts={kv:study.make_context(dict(saved,settings=replace(saved['settings'],voltage=float(kv))),
        (0,0,1),args.memory_budget_mib,systematic_row=True) for kv in VOLTAGES}
    detectors={kv:study.DetectorGrid(c['centers'],(c['cfg'].radius,),193,.5) for kv,c in contexts.items()}
    reuse_audit=inspect_reference(contexts[200],detectors[200])
    with (REFERENCE/'results.csv').open(newline='',encoding='utf-8') as f:
        coarse_reference=[r for r in csv.DictReader(f) if r['stage']=='A' and r['geometry']=='001']
    assert len(coarse_reference)==204
    base.write_csv(root/'reference_200kv_coarse33.csv',coarse_reference)
    physics={};coefficients={};metadata=dict(reference_reuse_audit=reuse_audit,geometry={},
        source_sha256=saved['config'].source_sha256,fixed_energies_ev=base.ENERGIES,eta=1.,beta=1.,
        primary_definition=base.DEFINITION,limitation=base.LIMITATION,
        post_edge_correction_applied=False,
        potential_model='Projected-2D IAM, explicit (200) systematic-row Fourier projection; not atomic-3D',
        memory_budget_mib=args.memory_budget_mib,base_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        worktree_dirty=bool(subprocess.check_output(['git','status','--porcelain'],text=True)),
        python=base.platform.python_version(),numpy=np.__version__,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        implementation_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path(study.__file__),Path(base.__file__),Path('src/emcd_sim/geometry.py'),Path('src/emcd_sim/physical_elastic.py'),Path('src/emcd_sim/multislice_reference.py'),Path('src/emcd_sim/single_channeling_tensor.py'))},
        numerical_sampling='193x193 [-0.5,0.5] cycles/Angstrom; 64 aperture subpixels; 64 trapezoidal depth nodes; FFT 32, max step 0.04 nm; float64/complex128; pixel batches 64',
        paper_voltage_status='Not independently established; no claim that PRB 2007 used any tested voltage.',
        extinction_convention='xi=pi/|H_000,200| in nm; ideal Bragg I200=sin^2(pi*t/xi), population period xi; not a multibeam effective period')
    for kv,c in contexts.items():
        physics[kv],arrays=voltage_physics(c)
        coefficients.update({f'{kv}kv__'+k:v for k,v in arrays.items()})
        np.testing.assert_array_equal(c['centers'],contexts[200]['centers'])
        np.testing.assert_array_equal(c['hkl'],contexts[200]['hkl'])
        np.testing.assert_array_equal(c['ts'][0].tensor_angstrom2_per_ev,contexts[200]['ts'][0].tensor_angstrom2_per_ev)
        c['ts']=contexts[200]['ts']
        metadata['geometry'][str(kv)]=dict(settings=asdict(c['settings']),config=asdict(c['cfg']),frame=c['R'],
            hkl=c['hkl'],g=c['g'],excitation_errors=c['s'],detector_centers=c['centers'],physics=physics[kv],
            ZA_q=-c['model'].elastic.microscope.incident_k_xy,detector_areas=detectors[kv].areas)
    base.write_json(root/'configuration.json',metadata)
    rows=[];elastic={};elastic_rows=[];controls=[];origins=[];diagnostics={}
    for kv,c in contexts.items():
        work=root/f'{kv}kv';work.mkdir(exist_ok=True);d=detectors[kv]
        (work/'completed_points.csv').write_text('',encoding='utf-8')
        elastic[kv]={m:np.empty((51,len(c['hkl']))) for m in base.METHODS}
        elastic[kv]['ideal_200']=coefficients[f'{kv}kv__ideal_sample_200_intensity']
        diagnostics[str(kv)]=dict(max_fft_norm_error=0.,max_excluded_population=0.)
        for t in (10.,12.,14.,30.,100.)+tuple(t for t in base.thickness_sequence() if t not in (10.,12.,14.,30.,100.)):
            point=reuse_fine_200(t,c,d) if kv==200 else None
            origin='reused existing fine-grid 200 kV checkpoint' if point is not None else 'calculated with existing engines'
            if point is None:point=study.calculate_point(work,'voltage','001',c,float(t),64,d)
            else:np.savez_compressed(work/f'reused_t{int(t):03d}.npz',**point)
            new=rows_for_voltage(c,physics[kv],float(t),d,point,origin);rows.extend(new)
            diagnostics[str(kv)]['max_fft_norm_error']=max(diagnostics[str(kv)]['max_fft_norm_error'],float(point.get('fft_norm_error',0.)))
            diagnostics[str(kv)]['max_excluded_population']=max(diagnostics[str(kv)]['max_excluded_population'],float(point.get('fft_excluded_population_max',0.)))
            origins.append(dict(voltage_kv=kv,thickness_nm=t,data_origin=origin))
            for method in base.METHODS:
                elastic[kv][method][int(t/2)]=point[method+'__exit']
                for j,h in enumerate(c['hkl']):
                    elastic_rows.append(dict(voltage_kv=kv,thickness_nm=t,solver=method,h=h[0],k=h[1],l=h[2],
                        excitation_error=c['s'][j],exit_intensity_fraction=point[method+'__exit'][j],
                        depth_average_intensity_fraction=point[method+'__average'][j]))
            with (work/'completed_points.csv').open('a',newline='',encoding='utf-8') as f:
                writer=csv.DictWriter(f,list(new[0]))
                if f.tell()==0:writer.writeheader()
                writer.writerows(new)
            del point
        for stage,t,grid,analytic in (('grid-control',12.,385,False),('depth-control',100.,193,True)):
            control_d=study.DetectorGrid(c['centers'],(c['cfg'].radius,),grid,.5)
            point=reuse_fine_200(t,c,control_d) if kv==200 and not analytic else None
            if point is None:point=study.calculate_point(work,stage,'001',c,t,64,control_d,analytic=analytic)
            control_rows=study.rows_for_point(stage,'001',c,t,64,control_d,point)
            for r in control_rows:r['coherence_integration']='analytic finite-BW integral' if analytic else '64-node trapezoidal'
            controls.extend(control_rows);del point
    # One matched coarse reference check, never a repeat of its full curve.
    d33=study.DetectorGrid(contexts[200]['centers'],(saved['config'].radius,),33,1.)
    point=study.calculate_point(root/'200kv','reference33','001',contexts[200],12.,64,d33)
    path=REFERENCE/'checkpoints/A_001_t012_d64_g33_row.npz'
    with np.load(path) as old:
        reference={m:float(abs(point[m+'__raw']-old[m+'__raw']).max()) for m in base.METHODS}
        for m in base.METHODS:np.testing.assert_allclose(point[m+'__raw'],old[m+'__raw'],rtol=1e-12,atol=1e-14)
    base.write_json(root/'reference_reproduction.json',dict(raw_max_absolute_difference=reference,**reuse_audit))
    del point
    differences=summarize(root,rows,physics,elastic)
    metadata['numerical_checks']=compare_controls(root,rows,controls)
    base.write_json(root/'configuration.json',metadata)
    base.write_csv(root/'results.csv',rows);base.write_csv(root/'elastic_populations.csv',elastic_rows)
    base.write_csv(root/'numerical_controls.csv',controls);base.write_csv(root/'data_origins.csv',origins)
    base.write_csv(root/'voltage_physics.csv',list(physics.values()))
    base.write_json(root/'propagation_diagnostics.json',diagnostics)
    np.savez_compressed(root/'results.npz',**{k:np.array([r[k] for r in rows]) for k in rows[0]},
        **{f'{k}kv__{m}__elastic_exit':a for k,d in elastic.items() for m,a in d.items()},
        configuration_json=np.array(json.dumps(base.clean(metadata))))
    np.savez_compressed(root/'dynamical_coefficients.npz',**coefficients)
    make_figures(root,rows,physics,elastic,differences)
    assert base.file_hashes(REFERENCE)==preserved
    assert base.load_wien2k_xmcd(saved['config'].source).source_sha256==saved['config'].source_sha256
    base.write_json(root/'preservation.json',dict(reference_200_files_unchanged=True,source_unchanged=True,reference_hashes=preserved))
    print('Voltage study complete; original 200 kV study unchanged.',flush=True)


if __name__=='__main__':main()
