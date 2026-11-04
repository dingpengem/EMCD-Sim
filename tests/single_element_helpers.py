"""Original synthetic data, deliberately not a measured or DFT-derived Fe MDFF."""
import json
import numpy as np
from emcd_sim.imported_mdff import CONVENTION


def document(element='Fe',nonmagnetic=False):
    e=np.array([704.,707.,710.,713.,716.,719.,723.,726.,730.])
    n=np.exp(-((e-710)/2)**2)+.55*np.exp(-((e-723)/2)**2)+.02
    m=.12*(np.exp(-((e-710)/2)**2)-.6*np.exp(-((e-723)/2)**2))
    even=n[:,None,None]*np.diag([1.2,1.,.8]);odd=np.zeros((len(e),3,3),complex)
    odd[:,0,1]=1j*m;odd[:,1,0]=-1j*m
    # A small real odd anisotropic component intentionally violates Ni's conjugation-only reversal.
    odd[:,0,2]=odd[:,2,0]=.025*m
    enc=lambda x:dict(real=x.real.tolist(),imag=x.imag.tolist())
    d=dict(schema=1,element=element,edge='L2,3',energy_ev=e.tolist(),selected_ev=dict(L3=710.,L2=723.),
        units='angstrom^2/eV',normalization='per_atom_relative',basis='crystal_cartesian',frame_to_crystal=np.eye(3).tolist(),
        magnetic_state='nonmagnetic' if nonmagnetic else 'uniform_fm',magnetization_crystal=[0,0,1],
        reversal='identical_nonmagnetic' if nonmagnetic else 'explicit_pair_shared_even',
        source='EMCD-Sim original synthetic PSD software fixture; no Fe-specific experimental/DFT data',
        validity='SYNTHETIC TEST ONLY; illustrative energy labels, relative units; not a quantitative Fe model',status='synthetic',convention=CONVENTION)
    d.update(dict(T=enc(even)) if nonmagnetic else dict(T_plus=enc(even+odd),T_minus=enc(even-odd),T_even=enc(even)))
    return d


def write_source(path,**kwargs):
    path.write_text(json.dumps(document(**kwargs)),encoding='utf-8');return path
