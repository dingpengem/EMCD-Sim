"""Phenomenological integrated L2,3 dipole tensors with analytical line profiles.

Strength matrices have relative per-atom Angstrom^2 units. Profiles integrate
to one on R (not a finite/positive-energy window); density is Angstrom^2/eV.
No branching ratio, magnetic moment, or atomic multiplet model is implied.
"""
import numpy as np
from .imported_mdff import ImportedMDFF, CONVENTION, proper_frame, psd_tensor


def lorentzian(energy, peak, fwhm):
    energy=np.asarray(energy,float)
    if not np.isfinite(energy).all() or not np.isfinite([peak,fwhm]).all() or peak<=0 or fwhm<=0:
        raise ValueError('Require finite energy, positive peak energy and positive FWHM (eV)')
    half=fwhm/2
    with np.errstate(over='ignore',divide='ignore',invalid='ignore'):
        height=(2/np.pi)/fwhm
        if half<=0 or not np.isfinite(height) or height<=0:raise ValueError('FWHM is outside the finite spectral-density range')
        distance=np.abs(energy-peak)
        near=distance<=half
        result=np.empty_like(energy)
        result[near]=height/(1+(distance[near]/half)**2)
        far=(~near)&np.isfinite(distance)
        ratio=half/distance[far]
        result[far]=((ratio/np.pi)/distance[far])/(1+ratio**2)
        overflow=(~near)&(~np.isfinite(distance))
        if np.any(overflow):
            scale=np.maximum(abs(energy[overflow]),peak)
            inverse=(1/scale)/abs(energy[overflow]/scale-peak/scale)
            ratio=half*inverse
            result[overflow]=((ratio/np.pi)*inverse)/(1+ratio**2)
        return result


def window_fraction(low,high,peak,fwhm):
    def angle(bound):
        with np.errstate(over='ignore'):
            delta=bound-peak
        if np.isfinite(bound) and not np.isfinite(delta):
            scale=max(abs(bound),peak,fwhm/2)
            return np.arctan2(bound/scale-peak/scale,(fwhm/2)/scale)
        return np.arctan2(delta,fwhm/2)
    return float((angle(high)-angle(low))/np.pi)


def strength_matrix(value):
    a=np.asarray(value,complex)
    if a.shape!=(3,3):raise ValueError('Each edge requires a complete 3 by 3 strength matrix')
    psd_tensor(np.array([1.,2.]),np.repeat(a[None],2,axis=0),'Integrated manual edge strength')
    return a


def simple_strength(amplitude,anisotropy,fraction):
    a,r,p=map(float,(amplitude,anisotropy,fraction))
    if not np.isfinite([a,r,p]).all() or a<0 or r<0 or abs(p)>1:
        raise ValueError('Require transverse strength A >= 0, anisotropy r >= 0, and signed magnetic fraction |p| <= 1')
    return strength_matrix([[a,1j*a*p,0],[-1j*a*p,a,0],[0,0,a*r]])


def simple_parameters(matrix):
    a=strength_matrix(matrix);scale=max(float(abs(a).max()),1e-300);amplitude=float(a[0,0].real)
    if amplitude==0:
        return (0.,1.,0.) if not a.any() else None
    r=float(a[2,2].real/amplitude);p=float(a[0,1].imag/amplitude)
    if r<0 or abs(p)>1:return None
    expected=simple_strength(amplitude,r,p)
    return (amplitude,r,p) if abs(a-expected).max()<=1e-12*scale else None


def unpack(edge):
    return strength_matrix(np.asarray(edge['real'],float)+1j*np.asarray(edge['imag'],float))


def validate_model(model):
    if not isinstance(model,dict) or set(model)!={'schema','profile','edges','frame_to_crystal','strength_units','origin'}:
        raise ValueError('Incomplete or unsupported manual L2,3 model declaration')
    if model['schema']!=1 or model['profile']!='lorentzian_full_real_domain' or model['strength_units']!='relative_per_atom_angstrom^2':
        raise ValueError('Unsupported manual L2,3 profile or integrated-strength units')
    if not isinstance(model['origin'],str) or not model['origin'].strip():raise ValueError('Declare model/default provenance')
    frame=proper_frame(model['frame_to_crystal'])
    if not isinstance(model['edges'],dict) or set(model['edges'])!={'L3','L2'}:raise ValueError('Both independent L3 and L2 edges are required')
    peaks=[]
    for key in ('L3','L2'):
        edge=model['edges'][key]
        if set(edge)!={'energy_ev','fwhm_ev','real','imag'}:raise ValueError('Incomplete edge declaration: '+key)
        lorentzian([edge['energy_ev']],edge['energy_ev'],edge['fwhm_ev']);unpack(edge);peaks.append(edge['energy_ev'])
    if not 0<peaks[0]<peaks[1]:raise ValueError('Require positive ascending L3 and L2 peak energies')
    return frame


def evaluate(model,energy):
    """Apply each full-domain unit-area profile to its integrated strength once."""
    energy=np.asarray(energy,float);result=np.zeros((len(energy),3,3),complex)
    for key in ('L3','L2'):
        edge=model['edges'][key]
        result+=lorentzian(energy,edge['energy_ev'],edge['fwhm_ev'])[:,None,None]*unpack(edge)[None]
    return result


def document(element,model,energy,editor):
    frame=validate_model(model);energy=np.asarray(energy,float)
    plus=evaluate(model,energy);minus=evaluate(model,energy).conj()
    packed=lambda a:dict(real=a.real.tolist(),imag=a.imag.tolist())
    return dict(schema=1,element=element,edge='L2,3',energy_ev=energy.tolist(),
        selected_ev={key:model['edges'][key]['energy_ev'] for key in ('L3','L2')},
        units='angstrom^2/eV',normalization='per_atom_relative',basis='declared_local',frame_to_crystal=frame.tolist(),
        magnetic_state='uniform_fm',magnetization_crystal=frame[:,2].tolist(),reversal='explicit_pair_shared_even',
        source='Manual phenomenological L2,3 dipole tensor; '+model['origin'],
        validity='Lorentzian profiles normalized on the full real energy axis; finite positive windows omit weight and are never renormalized. Independent edge strengths; no universal branching/sign ratio or moment inference. Explicit conjugation reversal in the fixed model frame, followed by the same real proper rotation. Not first principles or an atomic multiplet calculation.',
        status='synthetic',convention=CONVENTION,T_plus=packed(plus),T_minus=packed(minus),T_even=packed((plus+minus)/2),
        manual_l23_model=model,manual_l23_editor=editor)


class AnalyticalL23MDFF(ImportedMDFF):
    def tensors(self,energy,crystal_to_microscope,magnetization):
        e=np.asarray(energy,float)
        if e.ndim!=1 or not len(e) or not np.isfinite(e).all() or np.any(np.diff(e)<=0) or e[0]<self.energy_ev[0] or e[-1]>self.energy_ev[-1]:
            raise ValueError('No manual L2,3 energy extrapolation; require ascending samples within the declared window')
        m=np.asarray(magnetization,float);native=np.asarray(self.metadata['magnetization_crystal'],float)
        if m.shape!=(3,) or not np.isfinite(m).all() or not np.isfinite(np.linalg.norm(m)) or np.linalg.norm(m)<1e-12 or not np.allclose(m/np.linalg.norm(m),native/np.linalg.norm(native),rtol=0,atol=1e-10):
            raise ValueError('Manual L2,3 magnetic axis differs from the declared crystal frame')
        rotation=proper_frame(crystal_to_microscope)@proper_frame(self.metadata['frame_to_crystal'])
        plus=evaluate(self.metadata['manual_l23_model'],e)
        return [psd_tensor(e,np.einsum('ia,eab,jb->eij',rotation,a,rotation),self.metadata['source']) for a in (plus,plus.conj())]

    def provenance(self):
        return dict(super().provenance(),manual_l23_model=self.metadata['manual_l23_model'],manual_l23_editor=self.metadata['manual_l23_editor'])


def analytical_source(source):
    """Authenticate sampled evidence against the complete analytical declaration."""
    metadata=source.metadata;model=metadata['manual_l23_model'];frame=validate_model(model)
    if metadata['edge']!='L2,3' or metadata['basis']!='declared_local' or metadata['magnetic_state']!='uniform_fm' or metadata['reversal']!='explicit_pair_shared_even':
        raise ValueError('Manual L2,3 basis, edge or reversal declaration conflicts with model')
    if not np.array_equal(frame,metadata['frame_to_crystal']) or not np.array_equal(frame[:,2],metadata['magnetization_crystal']):
        raise ValueError('Manual L2,3 coordinate declarations conflict')
    if metadata['selected_ev']!={key:model['edges'][key]['energy_ev'] for key in ('L3','L2')}:
        raise ValueError('Manual L2,3 selected energies differ from model peaks')
    editor=metadata['manual_l23_editor']
    if not isinstance(editor,dict) or set(editor)!={'view','drafts'} or editor['view'] not in ('simple','full') or not isinstance(editor['drafts'],dict):
        raise ValueError('Invalid manual L2,3 editor restoration state')
    plus=evaluate(model,source.energy_ev)
    for actual,expected in ((source.plus.tensor_angstrom2_per_ev,plus),(source.minus.tensor_angstrom2_per_ev,plus.conj()),(source.even.tensor_angstrom2_per_ev,(plus+plus.conj())/2)):
        scale=max(float(abs(expected).max()),1e-300)
        if not np.allclose(actual,expected,rtol=1e-12,atol=1e-13*scale):raise ValueError('Manual L2,3 sampled tensors differ from analytical model')
    return AnalyticalL23MDFF(**source.__dict__)
