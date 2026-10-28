"""Small independent incoming/outgoing support controls on raw point signals."""
from dataclasses import replace
from pathlib import Path
import hashlib,json,time
import numpy as np
from emcd_sim.crystal import fcc_nickel
from emcd_sim.projected_geometry import ProjectedGeometry
from emcd_sim.gui.geometry import Structure,Settings,elastic_model
from emcd_sim.gui.emcd_forward import ForwardSettings,tensors
from emcd_sim.double_channeling import double_channeling_response,intensities_from_response
from emcd_sim.multislice_double_channeling import ProjectedFFT,incident_fields,multislice_double_channeling_response

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/generalized_multislice_emcd_validation/outgoing'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    geo=ProjectedGeometry.from_crystal(fcc_nickel(),(1,1,1),(2,-2,0));g=geo.crystal.g_vector((2,-2,0))[0]
    q=np.array([[g/2,g/2],[g/2,-g/2],[g/2+.04,g/2],[g/2+.04,-g/2]])
    energy=np.array([831.271,848.698]);ts=tensors(ForwardSettings(axis_declared=True),energy,geo.frame)
    code={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'src/emcd_sim').rglob('*.py'))}
    for incoming in (2.6,3.2):
        s=Settings(zone=(1,1,1),target=(2,-2,0),voltage=200,thickness=2,tilt=(geo.bragg_tilt(),0),beam_cutoff=incoming,potential_cutoff=3.8)
        elastic=elastic_model(Structure.nickel(),s)
        grid=ProjectedFFT.build(elastic,grid_points=48,potential_cutoff=3.8,projected_geometry=geo)
        fields=incident_fields(grid,2,depth_steps=65,slice_step_nm=.01)
        for outgoing in (2.6,3.2):
            label=f'in{incoming}_out{outgoing}';p=OUT/(label+'.npz');meta=OUT/(label+'.json')
            if meta.exists():
                d=json.loads(meta.read_text());assert d['code_sha256']==code and d['arrays_sha256']==hashlib.sha256(p.read_bytes()).hexdigest()
                print('REUSE',label,flush=True);continue
            print('RUN',label,flush=True);start=time.perf_counter();values={};diagnostics=[]
            beams=geo.beams(outgoing)
            for ie,e in enumerate(energy):
                bw=double_channeling_response(elastic,e,q,2,outgoing_beams=beams,method='numerical',depth_steps=65)
                ms,diag=multislice_double_channeling_response(elastic,e,q,2,outgoing_beams=beams,
                    prepared_grid=grid,prepared_incoming=fields,depth_steps=65,slice_step_nm=.01)
                for method,r in [('bloch',bw),('fft-multislice',ms)]:
                    values[f'{method}_{ie}_response']=r
                    values[f'{method}_{ie}_raw']=np.stack([intensities_from_response(r,t.tensor_angstrom2_per_ev[ie]) for t in ts])
                diagnostics.append(diag)
            values.update(q=q,energy_ev=energy,incoming_hkl=np.array(elastic.beams.hkl),outgoing_hkl=np.array(beams.hkl),frame=geo.frame)
            np.savez_compressed(p,**values)
            meta.write_text(json.dumps(dict(complete=True,code_sha256=code,arrays_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                diagnostics=diagnostics,seconds=time.perf_counter()-start,
                scope='Raw point intensities; not aperture-integrated convergence',potential_cutoff=3.8,thickness_nm=2,fft_grid=48,depth=65,slice_step=.01),indent=2),encoding='utf-8')
            print('DONE',label,flush=True)

if __name__=='__main__':main()
