"""Selected spectral weighting and angular/EELS export of a small real-source run."""
from pathlib import Path
from dataclasses import replace
import numpy as np
from emcd_sim.postedge_emcd_maps import MapConfig,run_map_comparison,save_comparison,load_comparison
from emcd_sim.emcd_angular_plots import save_angular_outputs,plot_angular_comparison
from emcd_sim.wien2k_xmcd import load_wien2k_xmcd
from emcd_sim.benchmark import nickel_physical_benchmark
from emcd_sim.crystal import fcc_nickel
from emcd_sim.elastic import BeamSet
from emcd_sim.elastic_reference import FourierCutoffPotential
from emcd_sim.scattering import IndependentAtomPotential
from emcd_sim.xmcd_effective_mdff import effective_tensor_from_xmcd
from emcd_sim.single_channeling_tensor import run_tensor_with_coherence


def test_full_source_angular_terms_export_and_replot(tmp_path,monkeypatch):
    source=Path(__file__).resolve().parents[1]/'data/wien2k_ni/Ni_fm.xmcd';s=load_wien2k_xmcd(source)
    cfg=MapConfig(conditions=('near-2bc',),thickness_nm=(.5,),potential_cutoff=.6,
        beam_cutoff=1.2,fft_grid=16,depth_steps=4,detector_grid=17,energy_points=65,
        energy_start=float(s.energy_ev[0]))
    r=run_map_comparison(source,cfg);c=r['cases'][0];pg=r['metadata']['propagation']
    actual=np.array([s.energy_ev[np.argmin(abs(s.energy_ev-e))] for e in (852.7,870.)])
    np.testing.assert_array_equal(list(r['metadata']['selected_energies_ev'].values()),actual)
    model=nickel_physical_benchmark(tilt_mrad_xy=pg['geometries']['near-2bc']['tilt_mrad_xy'],
        beams_override=BeamSet.zolz(fcc_nickel(),cfg.beam_cutoff,cfg.max_beams),diffraction_condition='near-2bc')
    model=replace(model,elastic=replace(model.elastic,potential=FourierCutoffPotential(IndependentAtomPotential(fcc_nickel()),cfg.potential_cutoff)))
    tensor=effective_tensor_from_xmcd(source,actual,eta=1.,beta=1.)
    for im,method in enumerate(c['methods']):
        coherence=r['propagation_cases'][0]['coherence_bw' if im==0 else 'coherence_ms']
        for j,e in enumerate(actual):
            direct=run_tensor_with_coherence(model,tensor,coherence,thickness_nm=.5,grid_size=17,
                reference_energy_ev=e,integration_mode='fractional')
            fields=method['maps'][j]
            np.testing.assert_allclose(fields['I_mag'],direct.magnetic_map_at_l3,atol=1e-15)
            np.testing.assert_allclose(fields['I_nonmag'],direct.nonmag_map_at_l3,atol=1e-15)
            for key,group in [('I_A_plus','A'),('I_B_plus_paired','B')]:
                from emcd_sim.postedge_emcd_maps import integrate_paired
                np.testing.assert_allclose(integrate_paired(fields[key],c['geometry']),direct.chiral_spectrum(group)[j],atol=1e-15)
        np.testing.assert_array_equal(method['spectra']['energy_ev'][[0,-1]],s.energy_ev[[0,-1]])
    before=c['methods'][0]['maps'][0]['I_mag'].copy()
    save_comparison(r,tmp_path);save_angular_outputs(r,tmp_path)
    for name in ('angular_maps.npz','virtual_detector_spectra.npz'):
        with np.load(tmp_path/'near-2bc'/name,allow_pickle=False) as data:
            for k in data.files:assert data[k].dtype.kind!='O'
    with np.load(tmp_path/'near-2bc/angular_maps.npz') as data:
        np.testing.assert_array_equal(data['selected_energies_ev'],actual)
        np.testing.assert_array_equal(data['I_mag'][0,0],before)
        assert data['I_plus'].shape==(2,2,17,17)
    # Replotting reads arrays; a forward call would fail immediately.
    import emcd_sim.postedge_emcd_maps as workflow
    monkeypatch.setattr(workflow,'run_tensor_with_coherence',lambda *a,**k:(_ for _ in ()).throw(AssertionError('forward rerun')))
    plot_angular_comparison(load_comparison(tmp_path),tmp_path)
    for name in ('L3_angular_maps.png','L2_angular_maps.png','virtual_detector_eels.png',
                 'raw_corrected_emcd_maps.png','bloch_multislice_difference.png'):
        assert (tmp_path/'near-2bc'/name).stat().st_size>1000
