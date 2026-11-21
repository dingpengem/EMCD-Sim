"""Scientific result assembly, completed-method views and selected-edge metrics.

assemble_forward_result receives detector signals already evaluated by the
channeling kernels. It constructs reversal parity and optional post-edge/paired
map diagnostics, validates source identity and records existing provenance.
File exports and rendering belong to gui.result_export and gui.result_presentation.
"""
from dataclasses import asdict

import platform
import numpy as np
from .detector_signals import reversal_components
from .emcd_angular_plots import paired_geometry, paired_maps
from .geometry import electron_wavelength_angstrom
from .xmcd_postedge_normalization import analyze_postedge_spectra
from emcd_sim.structure_geometry import excitation, za_from_tilt
from .provenance import build_info


def assemble_forward_result(structure,settings,cfg,model,R,hkl,g,memory,z,psi,C,energy,stage,*,prepared):
    """Assemble completed detector signals, derived maps and source provenance.

    prepared supplies spectra (energy,), maps (qy,qx), grid and fractional
    weights; psi is (depth,beam) and C is its depth-averaged beam coherence.
    R rotates crystal Cartesian vectors to beam axes. Depth is nm; q/g are
    cycles/Angstrom; energy is eV. No propagation or tensor contraction runs
    here. Preserve the established result keys, source checks and parity guard.
    """
    from .xmcd_source import inspect_xmcd_source
    stage('Computing energy-resolved EELS and fractional detector integrals')
    spectra,maps,qx,qy,weights=[prepared[k] for k in ('spectra','maps','qx','qy','weights')]
    stage('Computing selected-edge map decomposition and post-edge diagnostics')
    ap,bp,am,bm=[spectra[k] for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')]
    spectra.update(reversal_components(spectra,energy))
    from .detector_signals import benchmark_spectra
    spectra.update(benchmark_spectra(spectra)[0])
    alpha=None;correction_reason='Correction disabled by user.'
    if cfg.correction:
        try:
            post=analyze_postedge_spectra(energy,ap,bp,am,bm,windows=(cfg.window,),edge_windows={})
            alpha=float(post.spectra['alpha_obs'][0]);correction_reason='Observed +M A/B post-edge integral ratio; corrected contrast is not intrinsically magnetic.'
            for key in ('D_corrected','D_mag_processed_obs','D_nonmag_residual_obs'):spectra[key]=post.spectra[key][0]
            spectra['magnetic_bias']=spectra['D_mag_processed_obs']-spectra['D_mag']
        except ValueError as exc:correction_reason='Correction disabled: '+str(exc)
    try:pg=paired_geometry(model,qx,qy,subpixels=cfg.subpixels);pair_reason='Validated y-reflected physical aperture pair.'
    except ValueError as exc:pg=None;pair_reason='Mirrored maps disabled: '+str(exc)
    if pg is not None:
        for edge,m in maps.items():
            m.update(paired_maps(m['I_plus'],m['I_minus'],alpha if alpha is not None else 1.,pg))
            if alpha is None:
                for key in ('D_corrected','D_mag_processed','D_nonmag_residual'):m.pop(key)
    if not np.allclose(spectra['D_raw'],spectra['D_mag']+spectra['D_nonmag'],rtol=1e-10,atol=1e-13*max(ap.max(),bp.max())):raise ArithmeticError('Detector parity identity failed')
    audit=inspect_xmcd_source(cfg.source) if cfg.model=='xmcd' else None
    if audit and cfg.source_sha256 and audit['sha256']!=cfg.source_sha256:
        raise ValueError('XMCD source changed during calculation; result discarded')
    build=build_info();commit=build['commit'];dirty=build.get('dirty')
    from .elastic_providers import provider_provenance
    meta=dict(settings=asdict(settings),elastic_provider=provider_provenance(model.elastic.crystal.species,settings.elastic_provider),mdff=asdict(cfg),structure=structure.description(),frame=R.tolist(),beam_hkl=[list(h) for h in hkl],g=g.tolist(),
        source_audit=audit,energy_ev=energy.tolist(),magnetization_crystal=(np.asarray(cfg.magnetization)/np.linalg.norm(cfg.magnetization)).tolist(),
        magnetization_local=(R@np.asarray(cfg.magnetization)/np.linalg.norm(cfg.magnetization)).tolist(),
        reversal='XMCD: eta reversed in crystal frame; atomic: swap spin holes and reverse exchange at transition level, fixed core-SOC amplitudes; then R T R^T',
        za_q=za_from_tilt(settings.tilt,settings.voltage).tolist(),transmitted_q=[0.,0.],wavelength_angstrom=electron_wavelength_angstrom(settings.voltage),
        s_target=float(excitation(g[hkl.index(settings.target)],settings.tilt,settings.voltage)),alpha=alpha,correction_reason=correction_reason,pair_reason=pair_reason,
        detector_areas={k:float(w.sum()*(qx[0,1]-qx[0,0])**2) for k,w in weights.items()},integration='fractional',dense_estimate_mib=memory,
        channeling_model=cfg.channeling_model,angular_maps_calculated=cfg.angular_maps,spectral_coverage=cfg.energy_scope,
        outgoing_energy_ev=(1000*settings.voltage-energy).tolist() if cfg.channeling_model=='double' else None,
        longitudinal_transfer='q_z=-E_loss/(h*v_in), evaluated at each loss; frozen across branches, not across energy; no new branch or angular corrections',
        systematic_row=cfg.systematic_row,incoming_hkl=[list(h) for h in hkl],outgoing_hkl=[list(h) for h in hkl] if cfg.channeling_model=='double' else None,
        outgoing_energy='incident energy minus actual energy loss' if cfg.channeling_model=='double' else None,
        normalization=dict(raw_components='D_mag=M_A-M_B; D_nonmag=N_A-N_B (a.u.)',components_percent='100 * signed component / (N_A+N_B)',prb='100 * (I_A_plus-I_B_plus)/(I_A_plus+I_B_plus)'),
        precision='float64/complex128',reciprocal_convention='Crystallographic g=1/d (Å⁻¹); angular momentum transfer Q=2πg (Å⁻¹). Numerical values unchanged.',
        detector_evaluation='Full angular grid at selected L3/L2; nonzero fractional-aperture union at other energies' if cfg.angular_maps else 'Only nonzero fractional-aperture support on the unchanged grid; angular maps not calculated',
        angular_evaluation_policy=prepared.get('angular_evaluation_policy','legacy_full_grid_per_energy') if prepared is not None else 'legacy_full_grid_per_energy',
        angular_evaluation=prepared.get('diagnostics',[]) if prepared is not None else [],
        solver='Bloch-wave depth-integrated entrance-only localized single ionization',software_commit=commit,software_worktree_dirty=dirty,
        software_version=build['application_version'],software_display_version=build['display_version'],physics_convention=build['physics_convention'],
        implementation_sha256=build['implementation_sha256'],
        python=platform.python_version(),numpy=np.__version__,
        intensity_convention=('XMCD-effective; transverse source-maximum normalization; intensity in a.u.' if cfg.model=='xmcd' else 'Atomic length-gauge Å²/eV tensor; intensity in a.u.; no absolute cross-section calibration'),
        limitations='Projected IAM; '+('entrance-only, no outgoing channeling; ' if cfg.channeling_model=='single' else 'incoming and post-loss outgoing channeling; ')+ 'XMCD-effective is not full DFT MDFF; atomic non-DFT not quantitative Ni; arbitrary intensity units, no electron-count calibration; representative convergence controls do not certify all configurations.')
    stage('Preparing result visualizations')
    return dict(metadata=meta,model=model,settings=settings,config=cfg,maps=maps,spectra=spectra,qx=qx,qy=qy,weights=weights,coherence=C,depth_nm=z,amplitudes=psi)


def selected_edge_metrics(result):
    """Sample recorded edge observables with the existing denominator floor.

    Returns signed raw components and dimensionless component/Sigma_ref ratios,
    not percentage display values. Missing corrected components remain None.
    """
    s=result['spectra'];rows={}
    from .mdff_edges import selected_samples
    for edge,e in selected_samples(result['config']):
        i=int(np.argmin(abs(s['energy_ev']-e)));sigma=s['Sigma_ref'][i];floor=1e-10*max(float(s['Sigma_ref'].max()),1e-30)
        row={k:float(s[k][i]) if k in s else None for k in ('D_mag','D_nonmag','D_raw','D_corrected','magnetic_bias','D_nonmag_residual_obs','Sigma_ref')}
        row.update(A_mag=float(s['D_mag'][i]/sigma) if sigma>floor else None,A_nonmag=float(s['D_nonmag'][i]/sigma) if sigma>floor else None,alpha=result['metadata']['alpha'],energy_ev=float(s['energy_ev'][i]))
        rows[edge]=row
    return rows


def method_result(result,method):
    methods=result.get('methods',{result.get('method','bloch'):result})
    if method!='difference':return methods[method]
    b,m=[methods[k] for k in ('bloch','fft-multislice')]
    maps={edge:{k:b['maps'][edge][k]-m['maps'][edge][k] for k in b['maps'][edge] if k in m['maps'][edge]} for edge in b['maps'] if edge in m['maps']}
    metadata=dict(b['metadata'],pair_reason='BW-MS paired maps require validated physical pairing in both methods.',
        correction_reason='BW-MS corrected maps require valid correction in both methods. '+b['metadata']['correction_reason']+' / '+m['metadata']['correction_reason'])
    return dict(b,maps=maps,method='difference',metadata=metadata)
