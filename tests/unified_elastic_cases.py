"""Explicit acceptance cells and analytical references, independent of engine geometry."""
import numpy as np
from ase import Atoms
from emcd_sim.gui.geometry import Structure,Settings


def cases():
    a,c=3.2495,5.2069
    beta=np.deg2rad(107.)
    definitions=[
        ('bcc_fe',np.eye(3)*2.866,('Fe','Fe'),[[0,0,0],[.5,.5,.5]],(0,0,1),(1,1,0),1.05),
        ('bcc_fe_110_zone',np.eye(3)*2.866,('Fe','Fe'),[[0,0,0],[.5,.5,.5]],(1,-1,0),(1,1,0),1.05),
        ('cscl',np.eye(3)*4.123,('Cs','Cl'),[[0,0,0],[.5,.5,.5]],(0,0,1),(1,0,0),.72),
        ('hex_zno',np.array([[a,0,0],[-a/2,np.sqrt(3)*a/2,0],[0,0,c]]),('Zn','Zn','O','O'),
            [[1/3,2/3,0],[2/3,1/3,.5],[1/3,2/3,.382],[2/3,1/3,.882]],(0,0,1),(1,0,0),.85),
        ('monoclinic',np.array([[5.1,0,0],[0,6.3,0],[7.2*np.cos(beta),0,7.2*np.sin(beta)]]),('Si','O'),
            [[.13,.27,.19],[.41,.07,.63]],(0,1,0),(1,0,1),.55),
    ]
    return {name:(Structure(Atoms(symbols,scaled_positions=positions,cell=cell,pbc=True),source=name),
        Settings(zone=zone,target=target,tilt=(0.,0.),voltage=200,thickness=1.,beam_cutoff=cutoff,potential_cutoff=cutoff))
        for name,cell,symbols,positions,zone,target,cutoff in definitions}


def reciprocal_cross(cell):
    """Cross-product reciprocal basis; no production inv(cell).T or g_vector."""
    a,b,c=np.asarray(cell,float);volume=np.dot(a,np.cross(b,c))
    return np.array([np.cross(b,c),np.cross(c,a),np.cross(a,b)])/volume


def analytical_frame(cell,zone,target):
    reciprocal=reciprocal_cross(cell)
    z=np.asarray(zone)@cell;z=z/np.linalg.norm(z)
    x=np.asarray(target)@reciprocal;x=x/np.linalg.norm(x)
    y=np.cross(z,x)
    return np.array([x,y,z])


def independent_factor(structure,hkl,factors,b=0.):
    positions=structure.atoms.get_scaled_positions()
    g=np.linalg.norm(np.asarray(hkl)@reciprocal_cross(structure.atoms.cell.array))
    return sum(factors[s](g)*complex(np.cos(2*np.pi*np.dot(hkl,r)),-np.sin(2*np.pi*np.dot(hkl,r)))
        *np.exp(-b*g*g/4) for s,r in zip(structure.atoms.get_chemical_symbols(),positions))


def bw_ms(structure,settings,mesh=32,step=.005,beam_cutoff=None):
    from emcd_sim.gui.geometry import geometry
    from emcd_sim.scattering import IndependentAtomPotential,FourierCutoffPotential,elastic_reflection_allowed
    from emcd_sim.elastic_providers import factors_for_provider
    from emcd_sim.elastic import BeamSet
    from emcd_sim.physical_elastic import PhysicalElasticModel
    from emcd_sim.projected_geometry import ProjectedGeometry
    from emcd_sim.projected_potential import prepare_projected_potential,potential_site_labels
    from emcd_sim.geometry import electron_wavelength_angstrom
    from emcd_sim.multislice_double_channeling import FFTSplitStep
    crystal,frame,_,_,microscope=geometry(structure,settings)
    potential=IndependentAtomPotential(crystal,atomic_factors=factors_for_provider(crystal.species,settings.elastic_provider))
    projected=ProjectedGeometry.from_oriented(crystal,settings.zone,settings.target,labels=potential_site_labels(potential))
    cutoff=beam_cutoff or 2.5*settings.potential_cutoff
    hs=[h for h in projected.hkl_within(cutoff) if elastic_reflection_allowed(crystal,h,potential)]
    model=PhysicalElasticModel(crystal,microscope,BeamSet(tuple(hs)),FourierCutoffPotential(potential,settings.potential_cutoff))
    prepared=prepare_projected_potential(projected,potential,settings.voltage,mesh,settings.potential_cutoff,support_cutoff=cutoff)
    g=prepared.reciprocal_xy;kxy=microscope.incident_k_xy
    kinetic=(-10*np.pi*electron_wavelength_angstrom(settings.voltage)*(np.sum((g+kxy)**2,axis=1)-kxy@kxy)).reshape(mesh,mesh)
    engine=FFTSplitStep(prepared.phase_nm_inv,kinetic)
    entrance=np.zeros(mesh*mesh,complex);entrance[0]=1.
    steps=int(np.ceil(settings.thickness/step));wave=engine.advance(entrance,steps,settings.thickness/steps)
    lookup={tuple(h):i for i,h in enumerate(prepared.hkl)}
    indices=[lookup[h] for h in model.beams.hkl]
    bw=model.amplitudes(np.array([settings.thickness]))[0]
    intensity_error=float(np.max(abs(abs(wave[indices])**2-abs(bw)**2)))
    # Independently compare Fourier coefficients against Cartesian IAM units.
    coefficients=np.fft.fft2(prepared.phase_nm_inv)/mesh**2
    prefactor=10*(1+1000*settings.voltage/510998.95)*electron_wavelength_angstrom(settings.voltage)/potential.cell_volume_angstrom3
    fourier_error=0.
    for i,h in enumerate(prepared.hkl):
        gnorm=np.linalg.norm(crystal.g_vector(h))
        if not any(h) or gnorm>settings.potential_cutoff:continue
        fourier_error=max(fourier_error,abs(coefficients.flat[i]-prefactor*potential.structure_factor(tuple(h))))
    return dict(max_intensity_error=intensity_error,norm_error=float(abs(np.sum(abs(wave)**2)-1)),
        fourier_coefficient_error=float(fourier_error),mesh=mesh,step_nm=settings.thickness/steps,
        bw_beams=len(hs),beam_cutoff=cutoff,potential_cutoff=settings.potential_cutoff,
        hkl=list(model.beams.hkl),g=model.reciprocal_vectors_xy.tolist(),bw_intensity=(abs(bw)**2).tolist(),ms_intensity=(abs(wave[indices])**2).tolist())
