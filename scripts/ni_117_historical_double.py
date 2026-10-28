"""Small old/current coordinate-covariance check for Double BW, no GUI.

Run with the pristine main source via PYTHONPATH, then development source.
These are controlled equivalent geometries, not the unidentified original run.
"""
from pathlib import Path
from dataclasses import replace
import argparse
import numpy as np
from emcd_sim.gui.geometry import Structure,Settings,orientation,elastic_model
from emcd_sim.gui.emcd_forward import ForwardSettings,tensors
from emcd_sim.double_channeling import double_channeling_response,intensities_from_response,prepare_incoming_bloch
from emcd_sim.geometry import electron_wavelength_angstrom
from emcd_sim.elastic import BeamSet


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];structure=Structure.nickel();R=orientation(structure.atoms.cell.array,(1,1,7))
    target_frame=np.array([[1,-1,0],[7,7,-2],[1,1,7]],float);target_frame/=np.linalg.norm(target_frame,axis=1)[:,None]
    S=R@target_frame.T;g=np.sqrt(8)/3.524;tilt=S[:2,:2]@np.array([-500*electron_wavelength_angstrom(200)*g,0])
    s=Settings(zone=(1,1,7),target=(2,-2,0),tilt=tuple(tilt),thickness=8,beam_cutoff=3.8,potential_cutoff=6.2)
    model=elastic_model(structure,s);angle=np.arange(36)*2*np.pi/36
    q=np.column_stack((g/2+g/2*np.cos(angle),g/2*np.sin(angle)));query=q@S[:2,:2].T
    ts=tensors(ForwardSettings(axis_declared=True,source=str(root/'data/wien2k_ni/Ni_fm.xmcd')),np.array([831.271,848.698]),R)
    out=dict(q_target_frame=q,frame=R,tilt=tilt,angle=angle)
    for name in ('two','full'):
        elastic=replace(model,beams=BeamSet(((0,0,0),(2,-2,0)))) if name=='two' else model
        prepared=prepare_incoming_bloch(elastic,8,65)
        response=double_channeling_response(elastic,831.271,query,8,method='numerical',depth_steps=65,prepared_incoming=prepared)
        plus,minus=[intensities_from_response(response,t.tensor_angstrom2_per_ev[0]) for t in ts]
        out[name+'__M']=(plus-minus)/2;out[name+'__N']=(plus+minus)/2
    np.savez_compressed(args.output,**out)
