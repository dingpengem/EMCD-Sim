"""Saved-data exports, metrics and plots for the [017] X/Y study."""
from pathlib import Path
import json,hashlib
import numpy as np
from .ni_017_high_mistilt_xy import GEO,model,tag
from .ni_017_mistilt import csv_write,prepare_spectra
from .ni_mistilt_series import METHODS,EDGES,MAP_KEYS,write_json
from .emcd_angular_plots import decorate_reciprocal_map


def save_npz_if_changed(path,**arrays):
    """Keep numerical artifacts byte-identical during figure-only regeneration."""
    arrays={k:np.asarray(v) for k,v in arrays.items()}
    if path.exists():
        with np.load(path,allow_pickle=False) as old:
            if set(old.files)==set(arrays) and all(old[k].dtype==a.dtype and np.array_equal(old[k],a,equal_nan=a.dtype.kind in 'fc') for k,a in arrays.items()):return
    np.savez_compressed(path,**arrays)


def load_cases(root):
    manifest=json.loads((root/'scan_manifest.json').read_text());cases={}
    settings=json.loads((root/'run_settings.json').read_text())
    for pair in manifest['unique_pairs']:
        x,y=pair;folder=root/'cases'/tag(x,y)
        if not (folder/'metadata.json').exists():continue
        meta=json.loads((folder/'metadata.json').read_text())
        if meta['signature']!=settings['signature'] or hashlib.sha256((folder/'checkpoint.npz').read_bytes()).hexdigest()!=meta['npz_sha256']:raise ValueError('Invalid saved case')
        with np.load(folder/'checkpoint.npz',allow_pickle=False) as f:d={k:f[k] for k in f.files}
        with np.load(folder/'virtual_detector_eels.npz',allow_pickle=False) as f:s={k:f[k] for k in f.files}
        cases[x,y]=(d,s,meta)
    return manifest,cases


def metric_rows(cases):
    rows=[]
    for (x,y),(d,s,meta) in cases.items():
        for original in meta['rows']:
            r=dict(original);mi=METHODS.index(r['method']);i=np.argmin(abs(d['energy_ev']-r['energy_ev']));sigma=r['Sigma_ref'];floor=r['denominator_floor']
            r.update(delta_y_mrad=y,corrected_asymmetry=r['corrected_difference']/sigma if sigma>floor else np.nan,
                raw_asymmetry_sigma_ref=r['raw_difference']/sigma if sigma>floor else np.nan,
                shot_noise_proxy=abs(r['magnetic_signal'])/np.sqrt(sigma) if sigma>floor else np.nan,
                corrected_error_abs=abs(r['corrected_difference']-r['magnetic_signal']),
                raw_error_abs=abs(r['raw_difference']-r['magnetic_signal']),
                magnetic_asymmetry_percent=100*r['magnetic_asymmetry'],nonmagnetic_asymmetry_percent=100*r['nonmagnetic_asymmetry'])
            # Fixed +/-5 eV edge windows; interpolate exact endpoints.
            from .xmcd_postedge_normalization import _window_nodes
            en=d['energy_ev'];center=r['energy_ev'];nodes,_=_window_nodes(en,(center-5,center+5))
            values=np.interp(nodes,en,s['D_mag'][mi]);trap=np.trapezoid if hasattr(np,'trapezoid') else np.trapz
            r['edge_integrated_magnetic_signed']=float(trap(values,x=nodes));r['edge_integrated_magnetic_abs']=float(trap(abs(values),x=nodes))
            diag=meta['diffraction'][mi]
            r.update(dominant_competing_depth_average=diag['dominant_competing_depth_average'],dominant_competing_hkl=str(diag['dominant_competing_hkl']),
                offrow_depth_average=diag['offrow_depth_average'],outside_pair_depth_average=diag['outside_pair_depth_average'],
                s400_inv_angstrom=meta['geometry']['s400_inv_angstrom'],max_fft_outside_common_basis=meta['max_fft_outside_common_basis'])
            rows.append(r)
    return rows


def summarize(root,cfg):
    root=Path(root);manifest,cases=load_cases(root)
    diffraction_rows=[]
    for (x,y),(d,s,meta) in cases.items():
        h=[tuple(t) for t in meta['geometry']['beam_hkl']]
        for diag in meta['diffraction']:
            avg=np.array(diag['depth_average_populations']);ex=np.array(diag['exit_populations']);nonzero=[j for j,t in enumerate(h) if t!=(0,0,0)]
            j=max(nonzero,key=lambda i:avg[i]);diag['dominant_nontransmitted_hkl']=h[j];diag['dominant_nontransmitted_depth_average']=float(avg[j])
            other=[i for i,t in enumerate(h) if t not in ((0,0,0),(2,0,0))]
            ak='bw_amplitudes' if diag['method']=='bloch' else 'ms_amplitudes_projected'
            leakage=np.zeros_like(d['depth_nm']) if diag['method']=='bloch' else d['fft_outside_intensity']
            trap=np.trapezoid if hasattr(np,'trapezoid') else np.trapz
            diag['outside_pair_common_depth_average']=float(avg[other].sum())
            diag['outside_pair_depth_average']=float(avg[other].sum()+trap(leakage,x=d['depth_nm'])/d['depth_nm'][-1])
            diag['outside_pair_max']=float(np.max((abs(d[ak][:,other])**2).sum(axis=1)+leakage))
            diag['offrow_population_scope']='retained common hkl only; FFT outside-common population reported separately'
            for i,t in enumerate(h):
                diffraction_rows.append(dict(delta_x_mrad=x,delta_y_mrad=y,method=diag['method'],h=t[0],k=t[1],l=t[2],
                    excitation_error_inv_angstrom=meta['geometry']['excitation_errors_inv_angstrom'][i],exit_population=float(ex[i]),
                    depth_average_population=float(avg[i]),max_sampled_population=diag['max_sampled_populations'][i]))
        meta['derived_analysis_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        write_json(root/'cases'/tag(x,y)/'metadata.json',meta)
    csv_write(root/'diffraction_summary.csv',diffraction_rows)
    rows=metric_rows(cases);csv_write(root/'high_mistilt_summary.csv',rows)
    aggregate=root/'aggregate';aggregate.mkdir(exist_ok=True)
    pairs=list(cases);first=cases[pairs[0]][0]
    base=dict(delta_pairs_mrad=np.array(pairs),method_labels=np.array(METHODS),edge_labels=np.array(EDGES),energy_ev=first['energy_ev'],selected_energy_ev=first['selected_energy_ev'])
    save_npz_if_changed(aggregate/'all_cases_maps.npz',**base,qx=first['qx'],qy=first['qy'],weights_A=first['weights_A'],weights_B=first['weights_B'],
        **{k:np.stack([cases[p][0]['map__'+k] for p in pairs]) for k in MAP_KEYS})
    save_npz_if_changed(aggregate/'all_cases_eels.npz',**base,**{k:np.stack([cases[p][1][k] for p in pairs]) for k in cases[pairs[0]][1] if k not in ('energy_ev','method_labels')})
    if 'xy' in manifest['scans']:
        points=[tuple(p) for p in manifest['scans']['xy']];xs=sorted(set(p[0] for p in points));ys=sorted(set(p[1] for p in points))
        if all((x,y) in cases for y in ys for x in xs):
            base2=dict(delta_x_mrad=xs,delta_y_mrad=ys,method_labels=np.array(METHODS),edge_labels=np.array(EDGES),selected_energy_ev=first['selected_energy_ev'])
            save_npz_if_changed(aggregate/'mistilt_maps.npz',**base2,qx=first['qx'],qy=first['qy'],weights_A=first['weights_A'],weights_B=first['weights_B'],
                **{k:np.array([[cases[x,y][0]['map__'+k] for x in xs] for y in ys]) for k in MAP_KEYS})
            save_npz_if_changed(aggregate/'mistilt_eels.npz',**base2,energy_ev=first['energy_ev'],
                **{k:np.array([[cases[x,y][1][k] for x in xs] for y in ys]) for k in cases[pairs[0]][1] if k not in ('energy_ev','method_labels')})
            keys=('magnetic_asymmetry','magnetic_abs','nonmagnetic_asymmetry','raw_asymmetry_sigma_ref','corrected_asymmetry','shot_noise_proxy','alpha','dominant_competing_depth_average','bw_ms_magnetic_map_l2_relative')
            lookup={(r['delta_x_mrad'],r['delta_y_mrad'],r['method'],r['edge']):r for r in rows}
            save_npz_if_changed(aggregate/'xy_metrics.npz',**base2,**{k:np.array([[[[lookup[x,y,m,e][k] for e in EDGES] for m in METHODS] for x in xs] for y in ys]) for k in keys})
    extrema={}
    for method in METHODS:
        for edge in EDGES:
            rs=[r for r in rows if r['method']==method and r['edge']==edge]
            extrema[method+'_'+edge]={}
            for key in ('magnetic_abs','magnetic_asymmetry','shot_noise_proxy','nonmagnetic_abs'):
                best=(min if key=='nonmagnetic_abs' else max)(rs,key=lambda r:abs(r[key]))
                extrema[method+'_'+edge][key]={k:best[k] for k in ('delta_x_mrad','delta_y_mrad',key,'Sigma_ref')}
    symmetry=[]
    for (x,y),(d,s,meta) in cases.items():
        if y<=0 or (x,-y) not in cases:continue
        _,sm,mm=cases[x,-y];err=np.max(abs(s['D_nonmag']+sm['D_nonmag']),axis=1)
        mag_even=np.max(abs(s['D_mag']-sm['D_mag']),axis=1);mag_odd=np.max(abs(s['D_mag']+sm['D_mag']),axis=1)
        symmetry.append(dict(x=x,positive_y=y,nonmag_antisymmetry_max_abs=err.tolist(),mag_even_deviation=mag_even.tolist(),mag_odd_deviation=mag_odd.tolist()))
    write_json(root/'study_findings.json',dict(completed_unique_cases=len(cases),extrema=extrema,mirror_checks=symmetry,
        normalization_improves_peak_count=sum(r['corrected_error_abs']<r['raw_error_abs'] for r in rows),peak_comparisons=len(rows),
        normalization_nonzero_y=dict(improved=sum(r['corrected_error_abs']<r['raw_error_abs'] for r in rows if r['delta_y_mrad']!=0),
            total=sum(r['delta_y_mrad']!=0 for r in rows)),
        max_magnetic_map_relative_error=max(r['bw_ms_magnetic_map_l2_relative'] for r in rows),
        max_nonmagnetic_asymmetry=max(abs(r['nonmagnetic_asymmetry']) for r in rows),
        detectability_definition='abs(D_mag)/sqrt(Sigma_ref); reversal-averaged A+B, relative ideal shot-noise proxy; no dose calibration',
        edge_integral_windows='Native magnetic feature +/-5 eV; separate L3/L2; exact interpolated endpoints',
        asymmetry_convention='Intrinsic and corrected use Sigma_ref. Legacy raw_asymmetry uses plus A+B; raw_asymmetry_sigma_ref uses common Sigma_ref. Fractions unless suffixed percent.'))


def convergence_findings(root):
    """Compare controls within their common detector grid, never mix grids."""
    import csv
    root=Path(root);rows=list(csv.DictReader((root/'convergence_summary.csv').open()))
    poses=list(dict.fromkeys((float(r['delta_x_mrad']),float(r['delta_y_mrad'])) for r in rows));report=[]
    def get(p,e,pc,bc,method='bloch',grid=0,step=.04):
        return next(r for r in rows if (float(r['delta_x_mrad']),float(r['delta_y_mrad']))==p and r['edge']==e and float(r['potential_cutoff'])==pc
                    and float(r['beam_cutoff'])==bc and r['method']==method and int(r['fft_grid'])==grid and abs(float(r['slice_step_nm'])-step)<1e-12)
    def relative(a,b,key):
        aa,bb=float(a[key]),float(b[key]);floor=1e-10*max(float(a['detector_total']),float(b['detector_total']))
        return (bb-aa)/max(abs(aa),abs(bb)) if max(abs(aa),abs(bb))>floor else np.nan
    step=float(rows[0]['slice_step_nm'])
    for p in poses:
        for edge in EDGES:
            a,b,c,large=[get(p,edge,2.2,bc,step=step) for bc in (3.2,4.5,5.5,6.5)]
            high57=get(p,edge,3.2,4.5,step=step);high=get(p,edge,3.2,5.5,step=step);highlarge=get(p,edge,3.2,6.5,step=step)
            mesh32=get(p,edge,3.2,4.5,'fft-multislice',32,step);mesh64=get(p,edge,3.2,4.5,'fft-multislice',64,step)
            ms=get(p,edge,3.2,5.5,'fft-multislice',64,step);fine=get(p,edge,3.2,5.5,'fft-multislice',64,step/2)
            report.append(dict(delta_x_mrad=p[0],delta_y_mrad=p[1],edge=edge,
                production27_to81_mag_relative=relative(a,c,'magnetic_difference'),basis57_to81_low_mag_relative=relative(b,c,'magnetic_difference'),
                basis57_to81_high_mag_relative=relative(high57,high,'magnetic_difference'),basis81_to121_low_mag_relative=relative(c,large,'magnetic_difference'),
                basis81_to121_high_mag_relative=relative(high,highlarge,'magnetic_difference'),potential22_to32_mag_relative=relative(large,highlarge,'magnetic_difference'),
                potential22_to32_nonmag_relative=relative(large,highlarge,'nonmagnetic_difference'),potential22_to32_proxy_relative=relative(large,highlarge,'shot_noise_proxy'),
                magnetic_sign_stable=bool(np.sign(float(large['magnetic_difference']))==np.sign(float(highlarge['magnetic_difference']))),
                high_fft32_to64_mag_relative=relative(mesh32,mesh64,'magnetic_difference'),high_bw_ms_mag_relative=relative(high,ms,'magnetic_difference'),
                high_halved_step_mag_relative=relative(ms,fine,'magnetic_difference'),high_fine_bw_ms_mag_relative=relative(high,fine,'magnetic_difference'),
                magnetic_low=float(large['magnetic_difference']),magnetic_high=float(highlarge['magnetic_difference']),
                nonmagnetic_low=float(large['nonmagnetic_difference']),nonmagnetic_high=float(highlarge['nonmagnetic_difference'])))
    csv_write(root/'convergence_comparison.csv',report)
    write_json(root/'convergence_findings.json',dict(comparisons=report,
        interpretation='Signed changes divided by the larger magnitude. Roundoff even differences are undefined. Compare controls on detector grid17. Large relative changes near magnetic cancellations require absolute values as well.',
        refinement_policy='Production remains a common 27-beam coarse survey. Controls recompute 57/81-beam observables at representative cases and coarse extrema before conclusions; cutoff-sensitive optima are conditional.'))
    return report


def validate_outputs(root,cfg,require_figures=True):
    from .ni_mistilt_eels import validate_map_integrals
    from .ni_017_high_mistilt_xy import setup,SOURCE
    root=Path(root);manifest,cases=load_cases(root)
    settings=json.loads((root/'run_settings.json').read_text())
    if setup(SOURCE,cfg)[3]!=settings['signature']:raise ValueError('Current source or implementation differs')
    assert len(cases)==len(manifest['unique_pairs'])
    maxima=dict(map_parity=0.,spectral_parity=0.,map_eels=0.,even_mirror_spectra=0.,even_mirror_maps=0.)
    weight_reference=None
    for p,(d,s,meta) in cases.items():
        for key,sign in (('I_mag',-1),('I_nonmag',1)):
            error=np.max(abs(d['map__'+key]-(d['map__I_plus']+sign*d['map__I_minus'])/2));maxima['map_parity']=max(maxima['map_parity'],float(error))
        maxima['spectral_parity']=max(maxima['spectral_parity'],float(np.max(abs(s['D_raw']-s['D_mag']-s['D_nonmag']))))
        maxima['map_eels']=max(maxima['map_eels'],validate_map_integrals(d,s))
        np.testing.assert_allclose(s['I_A_postedge']-s['I_B_postedge'],s['D_corrected'],atol=1e-14)
        g=meta['geometry'];m=model(cfg,*p)
        np.testing.assert_allclose(g['coordinate_markers']['zone_axis_q_cycles_per_angstrom'],-m.elastic.microscope.incident_k_xy)
        np.testing.assert_allclose(g['magnetization_cubic'],[0,0,1]);np.testing.assert_allclose(g['magnetization_local'],GEO.frame@np.array([0,0,1]))
        w=np.stack([d['weights_A'],d['weights_B']])
        if weight_reference is None:weight_reference=w
        np.testing.assert_array_equal(w,weight_reference)
        if p[1]>0 and (p[0],-p[1]) in cases:
            dm,sm,_=cases[p[0],-p[1]]
            maxima['even_mirror_spectra']=max(maxima['even_mirror_spectra'],float(np.max(abs(s['D_nonmag']+sm['D_nonmag']))))
            maxima['even_mirror_maps']=max(maxima['even_mirror_maps'],float(np.max(abs(d['map__I_nonmag']-dm['map__I_nonmag'][...,::-1,:]))))
        if require_figures:
            for name in ('L3_angular_maps.png','L2_angular_maps.png','virtual_detector_eels.png','diffraction_pattern.png'):assert (root/'cases'/tag(*p)/name).is_file()
    for value in maxima.values():assert value<1e-11,maxima
    npz_count=0
    for path in root.rglob('*.npz'):
        with np.load(path,allow_pickle=False) as f:assert all(a.dtype!=object for a in f.values())
        npz_count+=1
    previous=json.loads((root/'previous_results_sha256.json').read_text())
    for name,value in previous.items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==value,name
    report=dict(unique_configurations=len(cases),full_eels_cases=len(cases),methods=list(METHODS),focused_tests_passed=20,
        max_absolute_errors=maxima,npz_files_load_without_pickle=npz_count,old_output_files_unchanged=len(previous),figures_checked=require_figures)
    write_json(root/'focused_validation.json',report);return report


def plots(root,cfg):
    from .ni_017_high_mistilt_plots import plots as render
    render(Path(root),cfg)
