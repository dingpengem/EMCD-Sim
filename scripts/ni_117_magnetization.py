"""Fixed-spectrum Ni [117] magnetic-axis comparison, using existing solvers.

Cartesian scattering responses do not depend on the MDFF/magnetization. Save
them in small resumable chunks, then contract source [001] and its beam-aligned control without repeating
elastic calculations. No mirror folding, interpolation, fitted scale or new MDFF.
"""
from dataclasses import asdict,dataclass
from pathlib import Path
import argparse,hashlib,json,subprocess,time
import numpy as np
from emcd_sim.ni_117_geometry import Ni117Geometry
from emcd_sim.gui.geometry import Structure,Settings,elastic_model,excitation
from emcd_sim.gui.emcd_forward import ForwardSettings,tensors
from emcd_sim.geometry import characteristic_qz_angstrom_inv,VirtualDetector
from emcd_sim.double_channeling import dipole_kernel,prepare_incoming_bloch,double_channeling_response,intensities_from_response
from emcd_sim.multislice_double_channeling import ProjectedNiFFT,incident_fields,multislice_double_channeling_response
from emcd_sim.multislice_reference import coherence_from_amplitudes
from emcd_sim.single_channeling_tensor import fcc_site_phase_matrix
from emcd_sim.simulation import EMCDSimulation

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/ni_117_magnetization_comparison'
ENERGIES=(831.271,848.698)
SOURCE=ROOT/'data/wien2k_ni/Ni_fm.xmcd'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write_json(p,obj):
    temp=p.with_suffix('.tmp');temp.write_text(json.dumps(obj,indent=2,default=lambda x:x.tolist() if isinstance(x,np.ndarray) else float(x)),encoding='utf-8');temp.replace(p)
def write_npz(p,**arrays):
    temp=p.with_suffix('.tmp')
    with temp.open('wb') as f:np.savez_compressed(f,**arrays)
    temp.replace(p)


@dataclass(frozen=True)
class Profile:
    name:str='refined'
    beam:float=4.6
    potential:float=6.2
    fft:int=32
    depth:int=129
    step:float=.02
    map_grid:int=33
    circle:int=360
    detector_grid:int=97
    subpixels:int=128


def axes(tilt):
    R=Ni117Geometry().frame
    transverse=np.asarray(tilt)*.001
    incident=np.r_[transverse,np.sqrt(1-np.dot(transverse,transverse))]
    crystal=dict(crystal001=np.array([0.,0,1]),incident=R.T@incident)
    result={}
    for name,m in crystal.items():
        local=R@m;parallel=float(local@incident)
        result[name]=dict(crystal=m,local=local,incident_local=incident,
            longitudinal=parallel,transverse=float(np.sqrt(max(0,1-parallel**2))),
            angle_to_incident_deg=float(np.degrees(np.arccos(np.clip(parallel,-1,1)))))
    return result


def supports(p):
    g=np.sqrt(8)/3.524
    v=np.linspace(-1,1,p.map_grid);x,y=np.meshgrid(v,v)
    a=np.arange(p.circle)*2*np.pi/p.circle
    circle=np.column_stack((g/2+g/2*np.cos(a),g/2*np.sin(a)))
    circle[p.circle//2:,0]=circle[np.arange(p.circle//2,0,-1),0]
    circle[p.circle//2:,1]=-circle[np.arange(p.circle//2,0,-1),1]
    circle[0,1]=circle[p.circle//2,1]=0
    dv=np.linspace(-1,1,p.detector_grid);dx,dy=np.meshgrid(dv,dv)
    detectors={k:VirtualDetector((g/2,sign*g/2),.16*g) for k,sign in (('A',1),('B',-1))}
    weights=np.array([d.integration_weights(dx,dy,mode='fractional',subpixels=p.subpixels) for d in detectors.values()])
    keep=np.any(weights>0,axis=0)
    allq=np.concatenate((np.column_stack((x.ravel(),y.ravel())),circle,np.column_stack((dx[keep],dy[keep]))))
    q,inverse=np.unique(allq,axis=0,return_inverse=True)
    n=x.size;nc=len(circle)
    return dict(q=q,map_index=inverse[:n],circle_index=inverse[n:n+nc],detector_index=inverse[n+nc:],
        qx=x,qy=y,angle=a,circle_q=circle,detector_q=np.column_stack((dx[keep],dy[keep])),
        detector_weights=weights[:,keep],dq2=(dv[1]-dv[0])**2,
        detector_areas=weights.sum(axis=(1,2))*(dv[1]-dv[0])**2,centers=np.array([d.center_q_xy for d in detectors.values()]))


def single_response(elastic,C,energy,q,thickness):
    transfer=np.empty((len(q),len(elastic.beams.hkl),3))
    transfer[...,:2]=q[:,None,:]-elastic.reciprocal_vectors_xy[None,:,:]
    transfer[...,2]=-characteristic_qz_angstrom_inv(energy,elastic.microscope.acceleration_kv)
    k=dipole_kernel(transfer)
    dummy=EMCDSimulation(elastic,{'A':VirtualDetector((0,0),.1),'B':VirtualDetector((0,1),.1)})
    return thickness*np.einsum('ij,pia,pjb->pab',C*fcc_site_phase_matrix(dummy),k,k,optimize=True)


def identities(profile,s,method,channel):
    files=['ni_117_geometry.py','double_channeling.py','multislice_double_channeling.py',
        'single_channeling_tensor.py','physical_elastic.py','scattering.py','gui/geometry.py','gui/emcd_forward.py',
        'xmcd_effective_mdff.py','mdff_tensor.py','geometry.py','multislice_reference.py']
    return dict(profile=asdict(profile),settings=asdict(s),method=method,channeling=channel,
        energies_ev=ENERGIES,source_sha256=sha(SOURCE),physics_sha256={f:sha(ROOT/'src/emcd_sim'/f) for f in files},
        analysis_sha256=sha(__file__),commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())


def run(profile,mode,channel,thickness,method):
    label=f'{profile.name}_{mode}_{channel}_t{thickness}_{method}'
    s=Settings(zone=(1,1,7),target=(2,-2,0),tilt=(Ni117Geometry().bragg_tilt(),0),voltage=200,thickness=thickness,
        beam_cutoff=profile.beam,potential_cutoff=profile.potential,basis_mode=mode)
    identity=identities(profile,s,method,channel)
    # Analysis edits do not invalidate already calculated response checkpoints:
    # version the response algorithm explicitly; keep the initial script hash.
    identity.pop('analysis_sha256');identity['response_algorithm']='cartesian_response_v1'
    digest=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:12]
    folder=OUT/'cases'/(label+'_'+digest);folder.mkdir(parents=True,exist_ok=True)
    if (folder/'complete.json').exists():
        meta=json.loads((folder/'complete.json').read_text(encoding='utf-8'))
        if meta['arrays_sha256']==sha(folder/'arrays.npz'):
            print('REUSE',label,flush=True);return folder
    start=time.perf_counter();support=supports(profile);q=support['q'];elastic=elastic_model(Structure.nickel(),s)
    z=np.linspace(0,thickness,profile.depth);grid=incoming=prepared=None
    if method=='bloch':
        waves=elastic.amplitudes(z)
        if channel=='double':prepared=prepare_incoming_bloch(elastic,thickness,profile.depth)
    else:
        grid=ProjectedNiFFT.build(elastic,grid_points=profile.fft,potential_cutoff=profile.potential,projected_geometry=Ni117Geometry(),
            retained_hkl=elastic.beams.hkl if mode=='two-beam' else None)
        incoming=incident_fields(grid,thickness,depth_steps=profile.depth,slice_step_nm=profile.step)
        waves=incoming[0][:,grid.indices(elastic.beams.hkl)]
    C=coherence_from_amplitudes(z,waves);responses=[];diagnostics=[]
    for energy in ENERGIES:
        chunks=[]
        for i in range(0,len(q),32):
            p=folder/f'response_{energy}_{i:05d}.npz';qb=q[i:i+32]
            if p.exists():
                with np.load(p) as a:
                    np.testing.assert_array_equal(a['q'],qb);r=a['response'].copy()
            else:
                if channel=='single':r=single_response(elastic,C,energy,qb,thickness)
                elif method=='bloch':
                    r=double_channeling_response(elastic,energy,qb,thickness,method='numerical',depth_steps=profile.depth,
                        memory_budget_mib=2048,prepared_incoming=prepared)
                else:
                    r,diag=multislice_double_channeling_response(elastic,energy,qb,thickness,
                        fft_grid=profile.fft,potential_cutoff=profile.potential,depth_steps=profile.depth,slice_step_nm=profile.step,
                        prepared_grid=grid,prepared_incoming=incoming,projected_geometry=Ni117Geometry(),memory_budget_mib=2048)
                    diagnostics.append(diag)
                write_npz(p,q=qb,response=r)
            chunks.append(r)
        responses.append(np.concatenate(chunks))
        print('EDGE',label,energy,'seconds',round(time.perf_counter()-start,1),flush=True)
    arrays=dict(**support,response=np.array(responses),depth_nm=z,waves=waves,coherence=C,hkl=np.array(elastic.beams.hkl),g=elastic.reciprocal_vectors_xy)
    orientation=axes(s.tilt);R=Ni117Geometry().frame
    for name,axis in orientation.items():
        cfg=ForwardSettings(axis_declared=True,source=str(SOURCE),magnetization=tuple(axis['crystal']),eta=1,beta=1)
        plus,minus=tensors(cfg,np.array(ENERGIES),R)
        values=np.array([[intensities_from_response(response,t.tensor_angstrom2_per_ev[e]) for e,response in enumerate(responses)] for t in (plus,minus)])
        if values.min()<-1e-12:raise ValueError('Negative raw intensity')
        arrays[name+'__plus']=values[0];arrays[name+'__minus']=values[1]
        arrays[name+'__N']=(values[0]+values[1])/2;arrays[name+'__M']=(values[0]-values[1])/2
        arrays[name+'__tensor_plus']=plus.tensor_angstrom2_per_ev
    write_npz(folder/'arrays.npz',**arrays)
    write_json(folder/'complete.json',dict(label=label,identity=identity,magnetizations=orientation,
        elapsed_seconds=time.perf_counter()-start,points=len(q),beam_count=len(elastic.beams.hkl),frame=R,
        s_target=float(excitation(elastic.crystal.g_vector(s.target)[:2],s.tilt,200)),
        wavelength_angstrom=elastic.microscope.wavelength_angstrom if hasattr(elastic.microscope,'wavelength_angstrom') else __import__('emcd_sim.geometry',fromlist=['electron_wavelength_angstrom']).electron_wavelength_angstrom(200),
        qz_cycles_angstrom=[-characteristic_qz_angstrom_inv(e,200) for e in ENERGIES],
        script_sha256=sha(__file__),diagnostics=diagnostics,arrays_sha256=sha(folder/'arrays.npz')))
    print('DONE',label,round(time.perf_counter()-start,1),flush=True)
    return folder


def jobs():
    base=Profile()
    for mode in ('two-beam','full'):
        for channel in ('single','double'):
            for thickness in (8,12,30):
                for method in ('bloch','fft-multislice'):yield base,mode,channel,thickness,method
    # Joint beam/FFT/depth + circle/aperture refinement. Potential remains at
    # the previously tested 6.2 plateau; prior independent slice checks stand.
    high=Profile('combined',beam=5.4,potential=6.2,fft=48,depth=257,step=.02,map_grid=33,circle=720,detector_grid=129,subpixels=256)
    for method in ('bloch','fft-multislice'):yield high,'full','double',8,method


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--only',default='');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    for p,mode,channel,t,method in jobs():
        label=f'{p.name}_{mode}_{channel}_t{t}_{method}'
        if args.only and args.only not in label:continue
        run(p,mode,channel,t,method)


if __name__=='__main__':main()
