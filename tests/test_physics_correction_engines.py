"""Actual corrected BW/MS engines against independent forward Born amplitudes.

Translated FCC motif supplies nontrivial site phases and non-real elastic
couplings. The explicit two-beam FFT Galerkin model matches the BW space.
This is a synthetic small-model validation, not a Ni convergence certificate.
"""
from dataclasses import replace
import numpy as np
import pytest
from numpy.testing import assert_allclose

from emcd_sim.crystal import Crystal, fcc_nickel
from emcd_sim.elastic import BeamSet
from emcd_sim.geometry import Microscope, characteristic_qz_angstrom_inv
from emcd_sim.physical_elastic import PhysicalElasticModel
from emcd_sim.benchmark import nickel_physical_benchmark
from emcd_sim.double_channeling import double_channeling_response, intensities_from_response, outgoing_elastic
from emcd_sim.multislice_double_channeling import (
    ProjectedFFT, incident_fields, multislice_double_channeling_response,
)
from emcd_sim.single_channeling_tensor import _tensor_angular_maps, historical_ni_site_phase_matrix
from emcd_sim.multislice_reference import coherence_from_amplitudes


def exp2(h,z):
    mean=np.trace(h).real/2;a=h-mean*np.eye(2)
    frequency=np.sqrt(np.trace(a@a).real/2)
    return np.exp(1j*mean*z)*(np.eye(2)*np.cos(frequency*z)+
                            1j*z*np.sinc(frequency*z/np.pi)*a)


@pytest.mark.parametrize('free_exit',[False,True])
def test_actual_corrected_bw_ms_and_single_against_born(free_exit):
    ni=fcc_nickel();shift=np.array([.137,.081,.019])
    crystal=Crystal(ni.lattice_angstrom,(ni.fractional_positions+shift)%1,ni.species)
    beams=BeamSet(((0,0,0),(2,0,0)))
    microscope=Microscope(200.,(-7.1,0.))
    elastic=PhysicalElasticModel(crystal,microscope,beams)
    hi=elastic.hamiltonian_nm_inv();assert abs(hi[0,1].imag)>.01
    thickness=1.3;energy=831.271;q=np.array([[.28,.25],[.28,-.25]])
    dipoles=np.array([[1.,.3j,.2],[.4-.2j,.6,.1j]])
    weights=np.array([.7,1.3])
    tensor=sum(w*np.outer(d,d.conj()) for w,d in zip(weights,dipoles))
    assert_allclose(tensor,tensor.conj().T);assert np.linalg.eigvalsh(tensor).min()>-1e-14
    reference=np.zeros((2,len(q)))
    x,wz=np.polynomial.legendre.leggauss(128)
    for pixel,point in enumerate(q):
        outgoing=outgoing_elastic(elastic,point,energy)
        ho=outgoing.hamiltonian_nm_inv()
        if free_exit:ho=np.diag(np.diag(ho))
        gi=elastic.reciprocal_vectors_xy;go=outgoing.reciprocal_vectors_xy
        transfer=np.empty((2,2,3));transfer[...,:2]=point+go[None,:,:]-gi[:,None,:]
        transfer[...,2]=-characteristic_qz_angstrom_inv(energy,200.)
        angular=2*np.pi*transfer;kernel=angular/np.sum(angular*angular,axis=-1)[...,None]
        for z,depth_weight in zip((x+1)*thickness/2,wz*thickness/2):
            a=exp2(hi,z)[:,0];bra=exp2(ho,thickness-z)[0]
            for site in crystal.fractional_positions:
                phase=np.exp(2j*np.pi*((np.asarray(beams.hkl)[:,None,:]-np.asarray(beams.hkl)[None,:,:])@site))
                for state,ds in enumerate((dipoles,dipoles.conj())):
                    for d,weight in zip(ds,weights):
                        amplitude=sum(a[g]*bra[h]*phase[g,h]*np.dot(kernel[g,h],d.conj())
                                      for g in range(2) for h in range(2))
                        reference[state,pixel]+=depth_weight*weight*abs(amplitude)**2/len(crystal.species)
    bw=double_channeling_response(elastic,energy,q,thickness,method='analytic',outgoing_potential=not free_exit)
    grid=ProjectedFFT.build(elastic,grid_points=16,potential_cutoff=.75,
        systematic_row=True,row_reduction=False,retained_hkl=beams.hkl,systematic_row_hkl=(2,0,0))
    fields,z,w,n,dz=incident_fields(grid,thickness,depth_steps=513,slice_step_nm=.005)
    ms,diagnostics=multislice_double_channeling_response(elastic,energy,q,thickness,
        prepared_grid=grid,prepared_incoming=(fields,z,w,n,dz),depth_steps=513,
        slice_step_nm=.005,outgoing_potential=not free_exit)
    for response,tolerance in ((bw,2e-13),(ms,2e-6)):
        assert_allclose(response,response.swapaxes(-1,-2).conj(),atol=2e-14)
        assert np.linalg.eigvalsh(response).min()>-1e-13
        actual=np.stack([intensities_from_response(response,t) for t in (tensor,tensor.conj())])
        assert np.min(actual)>0
        assert_allclose(actual,reference,rtol=tolerance,atol=1e-14)
        assert_allclose(actual.mean(axis=0),intensities_from_response(response,tensor.real),atol=2e-14)
        # Physically warranted row mirror for an axisymmetric z-magnetic tensor.
        axial=np.array([[1,.3j,0],[-.3j,1,0],[0,0,1]])
        plus=intensities_from_response(response,axial)
        minus=intensities_from_response(response,axial.conj())
        assert_allclose(plus,minus[::-1],rtol=2e-12,atol=2e-14)
    assert diagnostics['incoming_norm_error']<1e-12
    assert diagnostics['outgoing_norm_error']<1e-12
    if free_exit:
        model=replace(nickel_physical_benchmark(),elastic=elastic)
        selected=fields[:,grid.indices(beams.hkl)]
        coherence=coherence_from_amplitudes(z,selected)
        even,odd=_tensor_angular_maps(model,tensor,energy,coherence,historical_ni_site_phase_matrix(model),q[:,0],q[:,1])
        assert_allclose(thickness*(even+odd),intensities_from_response(ms,tensor),rtol=2e-12,atol=2e-14)
        # Independent high-order incoming coherence for the Single BW control.
        coherence=sum(weight*np.outer(exp2(hi,zi)[:,0],exp2(hi,zi)[:,0].conj())
            for zi,weight in zip((x+1)*thickness/2,wz/2))
        even,odd=_tensor_angular_maps(model,tensor,energy,coherence,historical_ni_site_phase_matrix(model),q[:,0],q[:,1])
        assert_allclose(thickness*(even+odd),reference[0],rtol=2e-13,atol=2e-14)
