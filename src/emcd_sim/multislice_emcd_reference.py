"""Independent projected-potential FFT/Bloch incident-wave EMCD comparison."""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
import platform
import subprocess

import numpy as np

from .benchmark import nickel_physical_benchmark
from .crystal import fcc_nickel
from .diffraction import select_diffraction_setup
from .elastic import BeamSet
from .elastic_reference import FourierCutoffPotential
from .mdff_tensor import DipoleTensor
from .multislice_reference import fft_multislice_ni
from .scattering import IndependentAtomPotential
from .single_channeling_tensor import run_tensor_with_coherence
from .wien2k_xmcd import load_wien2k_xmcd
from .xmcd_basis_convergence import selected_energy_grid
from .xmcd_effective_mdff import effective_tensor_from_xmcd
from .xmcd_geometry_decomposition import magnetic_contribution_metrics, _json_safe
from .xmcd_reversal import parity_spectra

CONDITIONS = ('zone-axis', 'near-2bc', 'symmetric-3bc')


@dataclass(frozen=True)
class MultisliceEMCDConfig:
    conditions: tuple[str, ...] = ('zone-axis', 'near-2bc')
    thickness_nm: tuple[float, ...] = (10., 30.)
    potential_cutoff: float = .75
    beam_cutoff: float = 2.2
    max_beams: int = 121
    fft_grid: int = 32
    slice_step_nm: float = .04
    depth_steps: int = 64
    detector_grid: int = 33
    acceleration_kv: float = 200.
    b_factor_angstrom2: float = 0.
    offzone_tilt_mrad: float = 25.
    energy_ev: float = 852.7
    eta: float = 1.
    beta: float = 1.
    max_kernel_mib: float = 512.
    leakage_warning: float = 1e-3

    def validate(self):
        if not self.conditions or len(set(self.conditions)) != len(self.conditions) or any(c not in CONDITIONS for c in self.conditions):
            raise ValueError(f'Conditions must be nonempty unique members of {CONDITIONS}')
        t = np.asarray(self.thickness_nm, float)
        if t.ndim != 1 or not len(t) or not np.isfinite(t).all() or np.any(t<=0) or np.any(np.diff(t)<=0):
            raise ValueError('Thicknesses must be positive finite and increasing')
        for v in (self.potential_cutoff,self.beam_cutoff,self.slice_step_nm,self.acceleration_kv,
                  self.energy_ev,self.max_kernel_mib):
            if not np.isfinite(v) or v<=0:
                raise ValueError('Cutoffs, slice step, voltage, energy and memory limit must be positive finite')
        for v in (self.eta,self.beta,self.b_factor_angstrom2,self.offzone_tilt_mrad,self.leakage_warning):
            if not np.isfinite(v):
                raise ValueError('Model settings must be finite')
        if min(self.beta,self.b_factor_angstrom2,self.offzone_tilt_mrad,self.leakage_warning)<0:
            raise ValueError('Require nonnegative beta, B, offzone tilt and leakage threshold')
        if any(not isinstance(v,int) for v in (self.max_beams,self.fft_grid,self.depth_steps,self.detector_grid)):
            raise ValueError('Beam, FFT, depth and detector sampling controls must be integers')
        if self.max_beams<3 or self.fft_grid<12 or self.fft_grid%2 or self.depth_steps<2 or self.detector_grid<9:
            raise ValueError('Require max beams >=3, even FFT grid >=12, depth steps >=2, detector grid >=9')


def project_fft_amplitudes(fft, beam_hkl):
    """Exact integer hkl lookup; no sign reversal, conjugation or rescaling."""
    if fft.amplitudes is None:
        raise ValueError('Request return_amplitudes=True from fft_multislice_ni')
    lookup = {tuple(h):i for i,h in enumerate(fft.beam_hkl)}
    try:
        indices = np.asarray([lookup[tuple(h)] for h in beam_hkl],dtype=int)
    except KeyError as exc:
        raise ValueError(f'Common beam outside FFT grid: {exc.args[0]}') from exc
    if len(set(indices)) != len(indices):
        raise ValueError('Common hkl basis must be unique')
    retained = np.zeros(len(fft.beam_hkl),dtype=bool)
    retained[indices] = True
    outside = fft.intensity[:,~retained].sum(axis=1)
    return fft.amplitudes[:,indices].copy(), outside


def coherence_from_amplitudes(depth_nm, amplitudes):
    """Same trapezoidal quadrature and C_gh=psi_g*conj(psi_h) as depth_coherence."""
    z, psi = np.asarray(depth_nm,float), np.asarray(amplitudes,complex)
    if (z.ndim!=1 or len(z)<2 or not np.isfinite(z).all() or z[0]!=0
            or np.any(np.diff(z)<=0) or psi.ndim!=2 or psi.shape[0]!=len(z)
            or not np.isfinite(psi).all()):
        raise ValueError('Require finite amplitudes on increasing depths from zero to t>0')
    pair = psi[:,:,None]*psi[:,None,:].conj()
    integral = np.trapezoid(pair,x=z,axis=0) if hasattr(np,'trapezoid') else np.trapz(pair,x=z,axis=0)
    return integral/z[-1]


def complex_wave_diagnostics(bloch, multislice):
    """Per-depth global-phase alignment for diagnostics only; no change to C."""
    overlap = np.sum(bloch.conj()*multislice,axis=1)
    valid = abs(overlap)>1e-14
    phase = np.where(valid,np.angle(overlap),np.nan)
    aligned = multislice*np.exp(-1j*phase[:,None])
    return dict(global_phase_ms_vs_bw=phase, phase_valid=valid,
        amplitude_max_abs_raw=np.max(abs(multislice-bloch),axis=1),
        amplitude_max_abs_aligned=np.max(abs(aligned-bloch),axis=1))


def scalar_discrepancy(bw, ms, floor):
    """Symmetric relative deviation, undefined near zero; sign checks use a floor."""
    absolute = abs(bw-ms)
    scale = max(abs(bw),abs(ms))
    return dict(absolute=float(absolute), relative=float(absolute/scale) if scale>floor else np.nan,
                sign_bw=int(np.sign(bw)) if abs(bw)>floor else 0,
                sign_ms=int(np.sign(ms)) if abs(ms)>floor else 0)


@dataclass
class MultisliceEMCDResult:
    records: list[dict]
    cases: list[dict]
    metadata: dict


def run_multislice_emcd_reference(xmcd_file, config=MultisliceEMCDConfig()):
    """Independent incident propagation, shared MDFF contraction, selected L3 only."""
    config.validate()
    source = load_wien2k_xmcd(xmcd_file)
    energy_grid, selected = selected_energy_grid(source.energy_ev,{'L3':config.energy_ev})
    energy = selected['L3']
    index = int(np.argmin(abs(energy_grid-energy)))
    tensors = []
    for sign in (1,-1):
        t = effective_tensor_from_xmcd(xmcd_file,energy_grid,eta=sign*config.eta,beta=config.beta)
        tensors.append(DipoleTensor(t.energy_ev[index:index+1],t.tensor_angstrom2_per_ev[index:index+1],t.source))
    crystal = fcc_nickel()
    beams = BeamSet.zolz(crystal,config.beam_cutoff,config.max_beams)
    if beams.hkl != BeamSet.zolz(crystal,config.beam_cutoff,config.max_beams+2).hkl:
        raise ValueError('Beam cap clips the requested common basis; increase --max-beams')
    # The kernel materializes detector-pixel x beam x beam arrays, never FFT_grid^4.
    estimate = 64.*config.detector_grid**2*len(beams.hkl)**2/2**20
    if estimate>config.max_kernel_mib:
        raise ValueError(f'Estimated pair-array working memory {estimate:.1f} MiB exceeds --max-kernel-mib')
    a = float(crystal.lattice_angstrom[0,0])
    safe_fft_g = (config.fft_grid//2-1)*2/a
    if max(config.beam_cutoff,config.potential_cutoff)>=safe_fft_g:
        raise ValueError('FFT grid cannot safely represent common beams/potential below Nyquist')
    original = IndependentAtomPotential(crystal,debye_waller_b_angstrom2=config.b_factor_angstrom2)
    potential = FourierCutoffPotential(original,config.potential_cutoff)
    records,cases,geometry = [],[],{}
    for condition in config.conditions:
        setup = select_diffraction_setup(condition,crystal,config.acceleration_kv,
                                         offzone_tilt_mrad=config.offzone_tilt_mrad)
        model = nickel_physical_benchmark(acceleration_kv=config.acceleration_kv,
            tilt_mrad_xy=setup.tilt_mrad_xy,beams_override=beams,diffraction_condition=condition)
        model = replace(model,elastic=replace(model.elastic,potential=potential))
        geometry[condition] = dict(tilt_mrad_xy=setup.tilt_mrad_xy,
            detectors={k:dict(center_q_xy=v.center_q_xy,radius_q=v.radius_q) for k,v in model.detectors.items()},
            chiral_groups=model.chiral_groups)
        for thickness in config.thickness_nm:
            depths = np.linspace(0.,thickness,config.depth_steps)
            bw = model.elastic.amplitudes(depths)
            fft = fft_multislice_ni(depths,acceleration_kv=config.acceleration_kv,
                tilt_mrad_xy=setup.tilt_mrad_xy,grid_points=config.fft_grid,
                slice_step_nm=config.slice_step_nm,potential_cutoff_inv_angstrom=config.potential_cutoff,
                b_factor_angstrom2=config.b_factor_angstrom2,return_amplitudes=True)
            ms,outside = project_fft_amplitudes(fft,beams.hkl)
            coherences = [coherence_from_amplitudes(depths,psi) for psi in (bw,ms)]
            cdelta = np.linalg.norm(coherences[0]-coherences[1])
            diag = complex_wave_diagnostics(bw,ms)
            tv = .5*(np.sum(abs(abs(bw)**2-abs(ms)**2),axis=1)+outside)
            case = dict(condition=condition,thickness_nm=thickness,depth_nm=depths,
                bw_amplitudes=bw,ms_amplitudes_projected=ms,fft_outside_intensity=outside,
                fft_total_norm=fft.intensity.sum(axis=1),bw_total_norm=np.sum(abs(bw)**2,axis=1),
                elastic_tv=tv,fft_beam_hkl=fft.beam_hkl,fft_exit_intensity=fft.intensity[-1],
                coherence_bw=coherences[0],coherence_ms=coherences[1],**diag,
                coherence_fro_abs=float(cdelta),
                coherence_fro_rel=float(cdelta/max(np.linalg.norm(c) for c in coherences)),
                ms_norm_error=fft.norm_error,
                coherence_min_eigenvalues=[float(np.linalg.eigvalsh(c).min()) for c in coherences],
                coherence_hermiticity_errors=[float(np.max(abs(c-c.conj().T))) for c in coherences])
            method_maps = []
            method_records = []
            for method,c in zip(('bloch','fft-multislice'),coherences):
                plus,minus = [run_tensor_with_coherence(model,t,c,thickness_nm=thickness,
                    grid_size=config.detector_grid,reference_energy_ev=energy) for t in tensors]
                s = {k:v[0].item() for k,v in parity_spectra(plus,minus).items()}
                metrics = {k:v.item() for k,v in magnetic_contribution_metrics(s['delta_odd'],s['delta_even'],s['sigma_ref']).items()}
                r = dict(case_index=len(cases),condition=condition,method=method,
                    thickness_nm=thickness,**s,**metrics)
                r.update(A_mag=r['A_odd'],A_nonmag=r['A_even'],Delta_mag=r['delta_odd'],
                         Delta_nonmag=r['delta_even'],Sigma_ref=r['sigma_ref'])
                records.append(r); method_records.append(r)
                ip = plus.nonmag_map_at_l3+plus.magnetic_map_at_l3
                im = minus.nonmag_map_at_l3+minus.magnetic_map_at_l3
                method_maps.append(dict(I_mag=(ip-im)/2,I_nonmag=(ip+im)/2,I_plus=ip,I_minus=im))
                case['qx_inv_angstrom'],case['qy_inv_angstrom'] = plus.qx_angstrom_inv,plus.qy_angstrom_inv
                geometry[condition]['aperture_grid_points'] = {k:int(v.sum()) for k,v in plus.detector_masks.items()}
            case['method_maps'] = method_maps
            case['scalar_discrepancies'] = {}
            for k in ('A_mag','A_nonmag','A_raw_plus','A_raw_minus','Delta_mag','Delta_nonmag','Sigma_ref','f_mag'):
                floor = 1e-10*max(r['Sigma_ref'] for r in method_records) if k in ('Delta_mag','Delta_nonmag','Sigma_ref') else 1e-8
                case['scalar_discrepancies'][k] = scalar_discrepancy(method_records[0][k],method_records[1][k],floor)
            case['map_discrepancies'] = {}
            for k in ('I_mag','I_nonmag'):
                x,y = [m[k] for m in method_maps]
                norm = max(np.linalg.norm(x),np.linalg.norm(y))
                case['map_discrepancies'][k] = dict(max_abs=float(np.max(abs(x-y))),
                    l2_abs=float(np.linalg.norm(x-y)), l2_relative=float(np.linalg.norm(x-y)/norm) if norm>1e-14 else np.nan)
            cases.append(case)
    try:
        root = Path(__file__).resolve().parents[2]
        commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,stderr=subprocess.DEVNULL).decode().strip()
        dirty = bool(subprocess.check_output(['git','status','--porcelain'],cwd=root).strip())
    except (OSError,subprocess.CalledProcessError):
        commit,dirty = None,None
    diagnostics = [dict(condition=c['condition'],thickness_nm=c['thickness_nm'],
        max_fft_outside_intensity=float(c['fft_outside_intensity'].max()),
        exit_fft_outside_intensity=float(c['fft_outside_intensity'][-1]),
        leakage_flag=bool(c['fft_outside_intensity'].max()>config.leakage_warning),
        max_elastic_tv=float(c['elastic_tv'].max()),exit_elastic_tv=float(c['elastic_tv'][-1]),
        max_amplitude_abs_raw=float(c['amplitude_max_abs_raw'].max()),
        max_amplitude_abs_phase_aligned=float(np.nanmax(c['amplitude_max_abs_aligned'])),
        coherence_fro_abs=c['coherence_fro_abs'],coherence_fro_rel=c['coherence_fro_rel'],
        coherence_min_eigenvalues=c['coherence_min_eigenvalues'],
        coherence_hermiticity_errors=c['coherence_hermiticity_errors'],
        bw_norm_error=float(np.max(abs(c['bw_total_norm']-1))),ms_norm_error=c['ms_norm_error'],
        scalar_discrepancies=c['scalar_discrepancies'],map_discrepancies=c['map_discrepancies']) for c in cases]
    metadata = dict(config=asdict(config),beam_hkl=beams.hkl,beam_count=len(beams.hkl),
        reciprocal_gxy=model.elastic.reciprocal_vectors_xy.tolist(),geometries=geometry,
        requested_energy_ev=config.energy_ev,selected_energy_ev=energy,
        tensor_sources=[t.source for t in tensors],source_peak_N=float(source.nonmagnetic.max()),
        xmcd_file=str(Path(xmcd_file).resolve()),xmcd_sha256=source.source_sha256,
        software_commit=commit,software_worktree_dirty=dirty,python_version=platform.python_version(),
        pair_array_memory_estimate_mib=estimate,pair_array_estimate_bytes_per_pixel_pair=64,
        detector_integration='Identical legacy circular hard masks times dq^2; no fractional aperture integration',
        depth_quadrature='Identical linspace(0,t,depth_steps); trapezoidal integral divided by t',
        fft_step_policy='Each interval subdivided into ceil(delta_z/slice_step_nm) equal Strang steps',
        fourier_convention='psi(r)=sum_g a_g exp(+2*pi*i*g.r); a=fft2(psi)/N^2; FFT (m,n)->hkl=(2m,2n,0)',
        phase_policy='No conjugation/sign reversal; per-depth global phase alignment for diagnostics only, never C',
        projection='Raw exact hkl selection; no renormalization; outside intensity retained at each depth',
        reciprocal_coordinate_units='cycles/angstrom; angular Q=2*pi*q inside shared MDFF kernel',
        model='XMCD-constrained effective MDFF; entrance-only; relative intensity; not quantitatively validated Ni EMCD',
        potential_model='Projected z-independent real IAM, U000=0; same explicit Fourier cutoff in both methods',
        comparison_scope='Independent elastic propagation; shared tensor, site phases, Coulomb factors and detector integration',
        diagnostics=diagnostics,absolute_cross_section=False,outgoing_channeling=False,quantitative_Ni=False,
        potential_converged=False,beam_basis_converged=False,fft_resolution_converged=False,
        slice_step_converged=False,depth_sampling_converged=False,aperture_sampling_converged=False,
        atom_layer_resolved_3d=False,independent_mdff_validation=False)
    return MultisliceEMCDResult(records,cases,metadata)


def check_propagation_controls(result, larger_beam_cutoff=None):
    """Two targeted wave-only checks on the last case; no enlarged MDFF kernel.

    Halve the FFT step, then enlarge only the Bloch propagation basis. Both
    coherences are selected onto the original common channels without rescaling.
    This diagnoses a residual, not potential/FFT/depth/basis convergence.
    """
    config = MultisliceEMCDConfig(**result.metadata['config'])
    case = result.cases[-1]
    cutoff = config.beam_cutoff+.4 if larger_beam_cutoff is None else larger_beam_cutoff
    crystal = fcc_nickel()
    if not np.isfinite(cutoff) or cutoff<=config.beam_cutoff:
        raise ValueError('Control beam cutoff must be finite and larger than the common cutoff')
    if cutoff >= (config.fft_grid//2-1)*2/float(crystal.lattice_angstrom[0,0]):
        raise ValueError('Control basis must remain safely inside FFT support')
    beams = BeamSet.zolz(crystal,cutoff,config.max_beams)
    if (beams.hkl != BeamSet.zolz(crystal,cutoff,config.max_beams+2).hkl
            or len(beams.hkl)<=result.metadata['beam_count']):
        raise ValueError('Control cutoff must select a larger basis without beam-cap clipping')
    common = tuple(map(tuple,result.metadata['beam_hkl']))
    indices = [beams.hkl.index(h) for h in common]
    tilt = tuple(result.metadata['geometries'][case['condition']]['tilt_mrad_xy'])
    fft = fft_multislice_ni(case['depth_nm'],acceleration_kv=config.acceleration_kv,
        tilt_mrad_xy=tilt,grid_points=config.fft_grid,slice_step_nm=config.slice_step_nm/2,
        potential_cutoff_inv_angstrom=config.potential_cutoff,
        b_factor_angstrom2=config.b_factor_angstrom2,return_amplitudes=True)
    psi,outside = project_fft_amplitudes(fft,common)
    fine = coherence_from_amplitudes(case['depth_nm'],psi)
    model = nickel_physical_benchmark(acceleration_kv=config.acceleration_kv,
        tilt_mrad_xy=tilt,beams_override=beams,diffraction_condition=case['condition'])
    potential = FourierCutoffPotential(IndependentAtomPotential(crystal,
        debye_waller_b_angstrom2=config.b_factor_angstrom2),config.potential_cutoff)
    elastic = replace(model.elastic,potential=potential)
    large = elastic.amplitudes(case['depth_nm'])
    projected = large[:,indices]
    enlarged = coherence_from_amplitudes(case['depth_nm'],projected)
    omitted = np.ones(len(beams.hkl),dtype=bool); omitted[indices] = False
    return dict(condition=case['condition'],thickness_nm=case['thickness_nm'],
        potential_cutoff=config.potential_cutoff,fft_grid=config.fft_grid,depth_steps=config.depth_steps,
        common_basis_count=len(common),larger_bloch_basis_count=len(beams.hkl),
        larger_bloch_cutoff=cutoff,slice_steps_nm=[config.slice_step_nm,config.slice_step_nm/2],
        coarse_ms_vs_bw_coherence_fro=float(np.linalg.norm(case['coherence_ms']-case['coherence_bw'])),
        fine_ms_vs_bw_coherence_fro=float(np.linalg.norm(fine-case['coherence_bw'])),
        coarse_vs_fine_ms_coherence_fro=float(np.linalg.norm(fine-case['coherence_ms'])),
        fine_ms_vs_larger_bw_projected_coherence_fro=float(np.linalg.norm(fine-enlarged)),
        larger_bw_projection='Raw selection onto original common hkl; no renormalization or larger MDFF contraction',
        larger_bw_excluded_intensity_max=float(np.sum(abs(large[:,omitted])**2,axis=1).max()),
        fine_ms_excluded_intensity_max=float(outside.max()))


def save_multislice_emcd_reference(result,output):
    output = Path(output)
    output.mkdir(parents=True,exist_ok=True)
    cases = result.cases
    shared = dict(condition=np.asarray([c['condition'] for c in cases]),
        thickness_nm=np.asarray([c['thickness_nm'] for c in cases]),
        beam_hkl=np.asarray(result.metadata['beam_hkl']),reciprocal_gxy=np.asarray(result.metadata['reciprocal_gxy']))
    keys = ('depth_nm','bw_amplitudes','ms_amplitudes_projected','fft_outside_intensity',
            'fft_total_norm','bw_total_norm','elastic_tv','global_phase_ms_vs_bw','phase_valid',
            'amplitude_max_abs_raw','amplitude_max_abs_aligned','fft_exit_intensity')
    np.savez_compressed(output/'elastic_complex_comparison.npz',**shared,
        fft_beam_hkl=cases[0]['fft_beam_hkl'],**{k:np.stack([c[k] for c in cases]) for k in keys})
    np.savez_compressed(output/'coherence_comparison.npz',**shared,
        coherence_bw=np.stack([c['coherence_bw'] for c in cases]),
        coherence_ms=np.stack([c['coherence_ms'] for c in cases]))
    with (output/'emcd_method_comparison.csv').open('w',encoding='utf-8',newline='') as f:
        writer = csv.DictWriter(f,fieldnames=list(result.records[0])); writer.writeheader(); writer.writerows(result.records)
    maps = [m for c in cases for m in c['method_maps']]
    np.savez_compressed(output/'emcd_method_comparison.npz',
        **{k:np.asarray([r[k] for r in result.records]) for k in result.records[0]},
        **{k:np.stack([m[k] for m in maps]) for k in ('I_mag','I_nonmag','I_plus','I_minus')},
        qx_inv_angstrom=cases[0]['qx_inv_angstrom'],qy_inv_angstrom=cases[0]['qy_inv_angstrom'])
    (output/'comparison_metadata.json').write_text(json.dumps(_json_safe(result.metadata),indent=2,allow_nan=False)+'\n',encoding='utf-8')
    if 'targeted_propagation_check' in result.metadata:
        (output/'targeted_propagation_check.json').write_text(
            json.dumps(_json_safe(result.metadata['targeted_propagation_check']),indent=2,allow_nan=False)+'\n',encoding='utf-8')


def plot_multislice_emcd_reference(result,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs = plt.subplots(3,2,figsize=(13,11),constrained_layout=True)
    x = np.arange(len(result.cases))
    labels = [f'{c["condition"]}\n{c["thickness_nm"]:g} nm' for c in result.cases]
    for method,name in enumerate(('Bloch','FFT multislice')):
        amps = [c['bw_amplitudes'] if method==0 else c['ms_amplitudes_projected'] for c in result.cases]
        axs[0,0].plot(x,[abs(a[-1,0])**2 for a in amps],'o-',label=name)
        for ax,key in ((axs[1,0],'A_mag'),(axs[1,1],'A_nonmag')):
            ax.plot(x,[result.records[2*i+method][key] for i in x],'o-',label=name)
    for key,label in [('amplitude_max_abs_aligned','Max phase-aligned amplitude error'),
                      ('elastic_tv','Max elastic TV')]:
        axs[0,1].plot(x,[float(np.nanmax(c[key])) for c in result.cases],'o-',label=label)
    axs[0,1].plot(x,[c['coherence_fro_abs'] for c in result.cases],'o-',label='Coherence Frobenius error')
    for key in ('A_mag','A_nonmag','A_raw_plus'):
        axs[2,0].plot(x,[c['scalar_discrepancies'][key]['absolute'] for c in result.cases],'o-',label=key)
    for key in ('I_mag','I_nonmag'):
        axs[2,1].plot(x,[c['map_discrepancies'][key]['l2_relative'] for c in result.cases],'o-',label=key+' relative L2 error')
    axs[2,1].plot(x,[c['fft_outside_intensity'].max() for c in result.cases],'o-',label='Max excluded FFT intensity')
    titles = ['Elastic transmitted intensity at exit','Complex/coherence/elastic discrepancies',
              'Magnetic-odd normalized asymmetry','Magnetization-even detector asymmetry',
              'Absolute asymmetry discrepancies','Map discrepancies and projected-basis leakage']
    for ax,title in zip(axs.flat,titles):
        ax.set_title(title); ax.set_xticks(x,labels,fontsize=8); ax.grid(alpha=.25); ax.legend(fontsize=7)
    fig.suptitle('Independent Bloch / FFT projected-potential propagation; shared XMCD-effective MDFF\n'
                 'Entrance-only relative intensity; not quantitatively validated Ni EMCD; no convergence certificate')
    output = Path(output); output.mkdir(parents=True,exist_ok=True)
    fig.savefig(output/'bloch_multislice_emcd_comparison.png',dpi=150)
    plt.close(fig)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--xmcd-file',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('outputs/ni_multislice_emcd_reference'))
    p.add_argument('--conditions',choices=CONDITIONS,nargs='+',default=['zone-axis','near-2bc'])
    p.add_argument('--thickness-nm',type=float,nargs='+',default=[10.,30.])
    for key,default in [('potential-cutoff',.75),('beam-cutoff',2.2),('slice-step-nm',.04),
        ('acceleration-kv',200.),('b-factor-angstrom2',0.),('offzone-tilt-mrad',25.),
        ('energy-ev',852.7),('eta',1.),('beta',1.),('max-kernel-mib',512.),('leakage-warning',1e-3)]:
        p.add_argument('--'+key,type=float,default=default)
    for key,default in [('max-beams',121),('fft-grid',32),('depth-steps',64),('detector-grid',33)]:
        p.add_argument('--'+key,type=int,default=default)
    p.add_argument('--check-propagation-controls',action='store_true',
                   help='On last case: halve FFT step and enlarge BW basis for wave-only residual diagnosis')
    args = vars(p.parse_args(argv)); check_controls = args.pop('check_propagation_controls')
    output,source = args.pop('output'),args.pop('xmcd_file')
    args['conditions'],args['thickness_nm'] = tuple(args['conditions']),tuple(args['thickness_nm'])
    try:
        result = run_multislice_emcd_reference(source,MultisliceEMCDConfig(**args))
        if check_controls:
            result.metadata['targeted_propagation_check'] = check_propagation_controls(result)
    except ValueError as exc:
        p.error(str(exc))
    save_multislice_emcd_reference(result,output); plot_multislice_emcd_reference(result,output)
    print(json.dumps(_json_safe(dict(output=str(output),beam_count=result.metadata['beam_count'],
        selected_energy_ev=result.metadata['selected_energy_ev'],diagnostics=result.metadata['diagnostics'])),indent=2,allow_nan=False))


if __name__ == '__main__':
    main()
