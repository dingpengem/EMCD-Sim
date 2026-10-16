"""Snapshot adapter: independent BW/FFT waves and one shared tensor contraction."""
from dataclasses import dataclass, asdict, replace, field
from pathlib import Path
import hashlib, json, platform, subprocess
import numpy as np
from .geometry import Structure, Settings, geometry, elastic_model, excitation, za_from_tilt
from ..benchmark import nickel_physical_benchmark
from ..geometry import VirtualDetector, electron_wavelength_angstrom
from ..mdff_tensor import DipoleTensor, dipole_tensor_from_transitions
from ..ni_local_mdff import NiLocalConfig, ni_local_transitions
from ..wien2k_xmcd import load_wien2k_xmcd
from ..xmcd_effective_mdff import effective_tensor_from_xmcd
from ..single_channeling_tensor import run_tensor_with_coherence
from ..multislice_emcd_reference import coherence_from_amplitudes
from ..postedge_emcd_maps import paired_geometry, paired_maps
from ..xmcd_postedge_normalization import analyze_postedge_spectra

DEFAULT_SOURCE = Path(__file__).resolve().parents[3]/'data/wien2k_ni/Ni_fm.xmcd'


def inspect_source(path):
    """Basic import is independent of optional original WIEN2k companion audit."""
    s=load_wien2k_xmcd(path); n=s.nonmagnetic
    maxima=np.flatnonzero((n[1:-1]>n[:-2]) & (n[1:-1]>=n[2:]))+1
    peaks=[]
    for i in sorted(maxima,key=lambda i:n[i],reverse=True):
        if all(abs(s.energy_ev[i]-s.energy_ev[j])>8 for j in peaks):peaks.append(i)
        if len(peaks)==2:break
    selected=None
    if len(peaks)==2:
        selected={}
        for edge,i in zip(('L3','L2'),sorted(peaks)):
            ix=np.flatnonzero(abs(s.energy_ev-s.energy_ev[i])<=3)
            selected[edge]=float(s.energy_ev[ix[np.argmax(abs(s.dichroic[ix]))]])
    info=dict(sha256=s.source_sha256,bounds=[float(s.energy_ev[0]),float(s.energy_ev[-1])],
              selected=selected,provenance='Five-column validated. User must declare source magnetic axis, RP/LP convention and edge assignment.',audit=None)
    suffixes=('raw1','raw2','broad1','broad2','rawxmcd','inso','injoint','inc')
    if Path(path).resolve()==DEFAULT_SOURCE.resolve() and all(Path(path).with_suffix('.'+k).exists() for k in suffixes):
        from ..ni_017_geometry import energy_audit
        info['audit']=energy_audit(path);info['selected']=info['audit']['selected_magnetic_energies_ev']
        info['provenance']='Original Ni companion audit passed; cubic [001], native unshifted L3/L2.'
    return info


@dataclass(frozen=True)
class ForwardSettings:
    model: str='xmcd'
    source: str=str(DEFAULT_SOURCE)
    source_sha256: str=''
    axis_declared: bool=False
    magnetization: tuple=(0.,0.,1.)
    eta: float=1.
    beta: float=1.
    l3: float=831.271
    l2: float=848.698
    atomic: NiLocalConfig=field(default_factory=NiLocalConfig)
    sigma: float=.8
    radial: float|None=None
    energy_points: int=241
    grid: int=33
    depth: int=64
    subpixels: int=64
    halfwidth: float=1.
    centers: tuple=((.2837684449489217,.2837684449489217),(.2837684449489217,-.2837684449489217))
    radius: float=.0908059024
    correction: bool=True
    window: tuple=(878.,882.)
    propagation: str='bloch'
    fft_grid: int=32
    slice_step: float=.04


def material_reason(structure):
    # Conservative Stage B gate: arbitrary CIF inspection is not MDFF validation.
    ref=Structure.nickel().atoms;a=structure.atoms
    if structure.elastic_reason:return structure.elastic_reason
    if (len(a)!=len(ref) or not np.allclose(a.cell.array,ref.cell.array,atol=1e-7)
        or not np.allclose(a.get_scaled_positions()%1,ref.get_scaled_positions()%1,atol=1e-7)):
        return 'Stage B MDFF requires the verified conventional FCC Ni cell (a=3.524 A, equivalent sites). CIF inspection remains available.'
    return ''


def axis_rotation(axis):
    m=np.asarray(axis,float)
    if m.shape!=(3,) or not np.isfinite(m).all() or np.linalg.norm(m)<1e-12:raise ValueError('Declare a nonzero finite crystal Cartesian magnetization axis')
    z=m/np.linalg.norm(m);x=np.array([1.,0,0]);x-=x.dot(z)*z
    if np.linalg.norm(x)<1e-8:x=np.array([0.,1,0]);x-=x.dot(z)*z
    x/=np.linalg.norm(x);return np.stack((x,np.cross(z,x),z),axis=1)


def tensors(cfg,energy,R):
    if cfg.model=='xmcd':
        if not cfg.axis_declared:raise ValueError('Declare the XMCD magnetic-axis, RP/LP handedness and L3/L2 assignments before running')
        Q=axis_rotation(cfg.magnetization)
        source=[effective_tensor_from_xmcd(cfg.source,energy,eta=s*cfg.eta,beta=cfg.beta) for s in (1,-1)]
    elif cfg.model=='atomic':
        if not np.allclose(cfg.magnetization,(0,0,1)):raise ValueError('Atomic cubic-field model currently supports crystal [001] magnetization only')
        Q=np.eye(3)
        source=[dipole_tensor_from_transitions(ni_local_transitions(cfg.atomic,radial_override_angstrom=cfg.radial,magnetization_sign=s),energy,cfg.sigma) for s in (1,-1)]
    else:raise ValueError('Unknown MDFF model')
    out=[]
    for t in source:
        A=R@Q;v=np.einsum('ia,eab,jb->eij',A,t.tensor_angstrom2_per_ev,A)
        if np.linalg.eigvalsh(v).min() < -1e-12*max(float(abs(v).max()),1e-30):raise ValueError('MDFF tensor is not positive semidefinite')
        out.append(DipoleTensor(energy,v,t.source+';crystal_to_local_R_T_RT'))
    if not np.allclose(out[1].tensor_angstrom2_per_ev,out[0].tensor_angstrom2_per_ev.conj(),rtol=1e-10,atol=1e-13*max(abs(out[0].tensor_angstrom2_per_ev).max(),1e-30)):
        raise ValueError('This model does not pass even/odd reversal symmetry; decomposition disabled')
    return out


def energy_grid(cfg):
    if cfg.model=='xmcd':
        s=load_wien2k_xmcd(cfg.source);lo,hi=s.energy_ev[[0,-1]]
        if cfg.source_sha256 and cfg.source_sha256!=s.source_sha256:raise ValueError('XMCD source changed since validation; validate again')
    else:lo,hi=cfg.atomic.l3_ev-10,cfg.atomic.l2_ev+10
    if not lo<=cfg.l3<cfg.l2<=hi:raise ValueError('Selected L3/L2 must be ordered inside the native model energy range')
    if not 9<=cfg.energy_points<=501 or not 9<=cfg.grid<=97 or not 2<=cfg.depth<=256 or not 4<=cfg.subpixels<=256:raise ValueError('Numerical sampling exceeds supported GUI bounds')
    if not np.isfinite([cfg.halfwidth,cfg.radius,*np.ravel(cfg.centers),*cfg.window]).all() or min(cfg.halfwidth,cfg.radius)<=0:raise ValueError('Invalid map/detector/window controls')
    return np.unique(np.r_[np.linspace(lo,hi,cfg.energy_points),cfg.l3,cfg.l2])


class Cancelled(Exception):pass


def calculate(structure,settings,cfg,progress=lambda s:None,cancelled=lambda:False):
    def stage(s):
        if cancelled():raise Cancelled()
        progress(s)
    stage('Validating structure and MDFF')
    reason=material_reason(structure)
    if reason:raise ValueError(reason)
    energy=energy_grid(cfg);elastic=elastic_model(structure,settings);_,R,hkl,g,_=geometry(structure,settings)
    if settings.target not in hkl or settings.target==(0,0,0):raise ValueError('Select a nonzero target in the finite diffraction basis')
    memory=64*cfg.grid**2*len(hkl)**2/2**20
    if memory>512:raise ValueError(f'Dense contraction estimate {memory:.1f} MiB exceeds 512 MiB. Lower grid or beam cutoff explicitly.')
    model=replace(nickel_physical_benchmark(),elastic=elastic,detectors={k:VirtualDetector(tuple(p),cfg.radius) for k,p in zip(('A','B'),cfg.centers)},chiral_groups=None)
    # Direct integration requires full physical aperture coverage as well.
    if any(max(abs(np.asarray(p)))+cfg.radius>cfg.halfwidth for p in cfg.centers):raise ValueError('Map halfwidth must fully cover both physical detector apertures')
    from .propagation import propagate, compare_methods, numerical_info
    info=numerical_info(structure,settings,cfg,hkl=hkl)
    stage('Generating common +M and -M tensors');ts=tensors(cfg,energy,R)
    z=np.linspace(0,settings.thickness,cfg.depth)
    waves,fft_info=propagate(elastic,settings,cfg,z,stage)
    methods={}
    for method,psi in waves.items():
        stage('Constructing '+method+' depth coherence');C=coherence_from_amplitudes(z,psi)
        stage('Calculating '+method+' EELS and EMCD')
        methods[method]=_contract(structure,settings,cfg,model,R,hkl,g,memory,z,psi,C,energy,ts,stage,cancelled)
        methods[method]['method']=method
        methods[method]['metadata'].update(solver=method+' depth-integrated entrance-only localized single ionization',numerics=info)
        if method=='fft-multislice':methods[method]['metadata']['fft']=fft_info['summary']
    stage('Comparing independent BW/MS propagations')
    comparison=compare_methods(methods,fft_info)
    primary=methods.get('bloch',next(iter(methods.values())))
    # Top-level Stage B arrays remain the primary method; method results do not
    # contain the enclosing collection, avoiding recursive/ambiguous dimensions.
    result=dict(primary,methods=methods,comparison=comparison,fft=fft_info)
    result['metadata']=dict(primary['metadata'],method_labels=list(methods),comparison=comparison)
    stage('Preparing result visualizations')
    return result


def _contract(structure,settings,cfg,model,R,hkl,g,memory,z,psi,C,energy,ts,stage,cancelled):
    """Stage B EELS/parity/post-edge implementation, shared by both coherences."""
    spectra={k:np.empty(len(energy)) for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')};maps={};qx=qy=None
    opts=dict(thickness_nm=settings.thickness,grid_size=cfg.grid,map_halfwidth_q=cfg.halfwidth,integration_mode='fractional',aperture_subpixels=cfg.subpixels)
    # One shared-kernel energy at a time provides cooperative cancellation;
    # expensive elastic propagation is reused across all states and energies.
    stage('Computing energy-resolved EELS and fractional detector integrals')
    indices={int(np.argmin(abs(energy-v))):edge for edge,v in (('L3',cfg.l3),('L2',cfg.l2))}
    for i,e in enumerate(energy):
        if cancelled():raise Cancelled()
        selected=[]
        for sign,t in zip(('plus','minus'),ts):
            one=DipoleTensor(np.array([e]),t.tensor_angstrom2_per_ev[i:i+1],t.source)
            r=run_tensor_with_coherence(model,one,C,reference_energy_ev=e,**opts)
            for d in ('A','B'):spectra['I_'+d+'_'+sign][i]=r.chiral_spectrum(d)[0]
            if i in indices:selected.append(r.nonmag_map_at_l3+r.magnetic_map_at_l3)
        if i in indices:maps[indices[i]]=dict(I_plus=selected[0],I_minus=selected[1],I_mag=(selected[0]-selected[1])/2,I_nonmag=(selected[0]+selected[1])/2)
    qx,qy=r.qx_angstrom_inv,r.qy_angstrom_inv
    stage('Computing L3/L2 map decomposition and post-edge diagnostics')
    ap,bp,am,bm=[spectra[k] for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')]
    na,nb,ma,mb=(ap+am)/2,(bp+bm)/2,(ap-am)/2,(bp-bm)/2
    spectra.update(energy_ev=energy,N_A=na,N_B=nb,M_A=ma,M_B=mb,D_mag=ma-mb,D_nonmag=na-nb,D_raw=ap-bp,Sigma_ref=na+nb)
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
    audit=inspect_source(cfg.source) if cfg.model=='xmcd' else None
    if audit and cfg.source_sha256 and audit['sha256']!=cfg.source_sha256:
        raise ValueError('XMCD source changed during calculation; result discarded')
    try:commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    except (OSError,subprocess.CalledProcessError):commit='unknown'
    try:dirty=bool(subprocess.check_output(['git','status','--porcelain'],text=True))
    except (OSError,subprocess.CalledProcessError):dirty=None
    meta=dict(settings=asdict(settings),mdff=asdict(cfg),structure=structure.description(),frame=R.tolist(),beam_hkl=[list(h) for h in hkl],g=g.tolist(),
        source_audit=audit,energy_ev=energy.tolist(),magnetization_crystal=(np.asarray(cfg.magnetization)/np.linalg.norm(cfg.magnetization)).tolist(),
        magnetization_local=(R@np.asarray(cfg.magnetization)/np.linalg.norm(cfg.magnetization)).tolist(),
        reversal='XMCD: eta reversed in crystal frame; atomic: swap spin holes and reverse exchange at transition level, fixed core-SOC amplitudes; then R T R^T',
        za_q=za_from_tilt(settings.tilt,settings.voltage).tolist(),transmitted_q=[0.,0.],wavelength_angstrom=electron_wavelength_angstrom(settings.voltage),
        s_target=float(excitation(g[hkl.index(settings.target)],settings.tilt,settings.voltage)),alpha=alpha,correction_reason=correction_reason,pair_reason=pair_reason,
        detector_areas={k:float(w.sum()*(qx[0,1]-qx[0,0])**2) for k,w in r.detector_weights.items()},integration='fractional',dense_estimate_mib=memory,
        solver='Bloch-wave depth-integrated entrance-only localized single ionization',software_commit=commit,software_worktree_dirty=dirty,
        implementation_sha256={name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ('emcd_forward.py','geometry.py','propagation.py')},
        python=platform.python_version(),numpy=np.__version__,
        limitations='Projected IAM; no outgoing/double channeling; XMCD-effective is not full DFT MDFF; atomic non-DFT not quantitative Ni; relative units, no absolute cross section; physical-potential cutoff convergence unresolved.')
    stage('Preparing result visualizations')
    return dict(metadata=meta,model=model,settings=settings,config=cfg,maps=maps,spectra=spectra,qx=qx,qy=qy,weights=r.detector_weights,coherence=C,depth_nm=z,amplitudes=psi)


def metrics(result):
    s=result['spectra'];rows={}
    for edge,e in (('L3',result['config'].l3),('L2',result['config'].l2)):
        i=int(np.argmin(abs(s['energy_ev']-e)));sigma=s['Sigma_ref'][i];floor=1e-10*max(float(s['Sigma_ref'].max()),1e-30)
        row={k:float(s[k][i]) if k in s else None for k in ('D_mag','D_nonmag','D_raw','D_corrected','magnetic_bias','D_nonmag_residual_obs','Sigma_ref')}
        row.update(A_mag=float(s['D_mag'][i]/sigma) if sigma>floor else None,A_nonmag=float(s['D_nonmag'][i]/sigma) if sigma>floor else None,alpha=result['metadata']['alpha'],energy_ev=float(s['energy_ev'][i]))
        rows[edge]=row
    return rows


def _export_single(result,path):
    from matplotlib.figure import Figure
    from .results import draw_maps,draw_eels
    root=Path(path);root.mkdir(parents=True,exist_ok=False)
    meta=dict(result['metadata'],edge_metrics=metrics(result))
    for name,value in (('input_parameters',dict(settings=meta['settings'],mdff=meta['mdff'],structure=meta['structure'])),('metadata',meta)):
        (root/(name+'.json')).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    np.savez_compressed(root/'virtual_detector_eels.npz',**result['spectra'])
    arrays=dict(qx=result['qx'],qy=result['qy'],coherence=result['coherence'],depth_nm=result['depth_nm'],amplitudes=result['amplitudes'])
    for edge,m in result['maps'].items():
        arrays.update({edge+'_'+k:v for k,v in m.items()})
        fig=Figure(figsize=(15,9),layout='constrained');draw_maps(fig,result,edge);fig.savefig(root/(edge+'_angular_maps.png'),dpi=145)
    arrays.update({'weight_'+k:v for k,v in result['weights'].items()});np.savez_compressed(root/'angular_maps.npz',**arrays)
    fig=Figure(figsize=(11,9),layout='constrained');draw_eels(fig,result);fig.savefig(root/'virtual_detector_eels.png',dpi=150)


def export_result(result,path):
    """Keep Stage B primary arrays; add explicitly labeled method exports."""
    _export_single(result,path)
    from .propagation import export_comparison
    export_comparison(result,Path(path),_export_single)
