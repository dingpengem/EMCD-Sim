"""Bounded numerical validation, not a physical Cr/magnetite spectrum benchmark.

Only selected losses, grid9 detector quadrature, and serial small beam/FFT bases
are used. Matched Galerkin tests separate quadrature/Strang error from elastic
basis truncation; the unrestricted cutoff comparison does not impose a BW/MS
agreement threshold. No saved intensity baselines or reference hashes.
"""
from dataclasses import replace
import json

import numpy as np
import pytest
from ase import Atoms

from emcd_sim.double_channeling import prepare_incoming_bloch
from emcd_sim.geometry import VirtualDetector
from emcd_sim.gui.forward_pipeline import calculate_multisite, _multisite_detector_data
from emcd_sim.gui.generalized_forward import settings_for_source
from emcd_sim.gui.geometry import Structure, Settings, elastic_model, geometry
from emcd_sim.multisite import IonizationSiteGroup, MultiSiteIonization
from emcd_sim.multisite_double_channeling import contract_multisite_bloch_double
from emcd_sim.multisite_spectrum import ModeledEdgeWindow, prepare_multisite_spectrum
from emcd_sim.simulation import EMCDSimulation
from single_element_helpers import document
from test_multisite_forward import configuration, system as simple_system, RAW_KEYS


def case(tmp_path,name):
    if name in ('Ni','Cr'):
        structure,settings,sites,_=simple_system(tmp_path,name)
        return structure,replace(settings,basis_mode='two-beam',potential_cutoff=1.5),sites,[710.],None
    # Stoichiometry-only ordered geometry; these are NOT magnetite Wyckoff sites.
    positions=[(0,0,0),(.5,.5,.25),(.25,.75,.5),(.12,.3,.1),(.4,.17,.37),(.65,.46,.68),(.82,.8,.88)]
    structure=Structure(Atoms('Fe3O4',scaled_positions=positions,cell=[4.2]*3,pbc=True))
    settings=Settings(zone=(0,0,1),target=(1,0,0),tilt=(-5,7),voltage=200,thickness=2.,
        beam_cutoff=.55,potential_cutoff=1.2,basis_mode='two-beam')
    groups=[]
    for label,element,indices,scale,down in [('Fe(A)','Fe',(0,),1.,False),('Fe(B)','Fe',(1,2),1.8,True),('O','O',(3,4,5,6),1.,False)]:
        data=document(element,nonmagnetic=element=='O')
        if element=='O':
            data.update(edge='K',energy_ev=(np.asarray(data['energy_ev'])-180.).tolist(),selected_ev={'K':530.})
        if down:
            data['magnetization_crystal']=[0,0,-1]
            data['T_plus'],data['T_minus']=data['T_minus'],data['T_plus']
        for key in ('T','T_plus','T_minus','T_even'):
            if key in data:
                for part in ('real','imag'):data[key][part]=(scale*np.asarray(data[key][part])).tolist()
        path=tmp_path/(label+'.json')
        path.write_text(json.dumps(data),encoding='utf-8')
        cfg=settings_for_source(path)
        groups.append(IonizationSiteGroup(label,element,indices,cfg,cfg.magnetization,len(indices)))
    sites=MultiSiteIonization(structure,groups)
    windows={g.group_id:ModeledEdgeWindow((524.,550.),(530.,)) if g.element=='O'
             else ModeledEdgeWindow((704.,730.),(710.,)) for g in groups}
    return structure,settings,sites,None,windows


def run(inputs,method,*,thickness,depth=33,mesh=16,slice_step=.01,sites=None,windows=None,reverse=False):
    structure,settings,original_sites,energy,original_windows=inputs
    settings=replace(settings,thickness=thickness)
    cfg=configuration(propagation=method,channeling_model='double',angular_maps=False,
        depth=depth,fft_grid=mesh,slice_step=slice_step)
    return calculate_multisite(structure,settings,original_sites if sites is None else sites,cfg,
        energy_ev=energy,energy_windows=original_windows if windows is None else windows,
        reverse_magnetization=reverse)


def analytic_reference(inputs,thickness):
    structure,settings,sites,energy,windows=inputs
    settings=replace(settings,thickness=thickness)
    elastic=elastic_model(structure,settings)
    rotation=geometry(structure,settings)[1]
    cfg=configuration(channeling_model='double',angular_maps=False,depth=33)
    detectors={key:VirtualDetector(tuple(center),cfg.radius) for key,center in zip(('A','B'),cfg.centers)}
    model=EMCDSimulation(elastic,detectors)
    q=np.linspace(-cfg.halfwidth,cfg.halfwidth,cfg.grid);qx,qy=np.meshgrid(q,q)
    weights={key:detector.integration_weights(qx,qy,mode='fractional',subpixels=cfg.subpixels) for key,detector in detectors.items()}
    support=np.logical_or.reduce([w.ravel()>0 for w in weights.values()])
    plan=prepare_multisite_spectrum(sites,energy,windows)
    incoming=prepare_incoming_bloch(elastic,thickness,cfg.depth)
    raw=contract_multisite_bloch_double(model,sites,plan,qx.ravel()[support],qy.ravel()[support],
        crystal_to_microscope=rotation,thickness_nm=thickness,depth_steps=cfg.depth,method='analytic',prepared_incoming=incoming)
    result=_multisite_detector_data(raw['total'],cfg,plan['energy_ev'],qx,qy,weights,support)
    result['groups']={key:_multisite_detector_data(group,cfg,plan['energy_ev'],qx,qy,weights,support)
                      for key,group in raw['groups'].items()}
    return result


def components(result):
    entries=[result]+[result['groups'][key] for key in sorted(result['groups'])]
    return {kind:np.concatenate([entry['spectra'][key] for entry in entries for key in keys])
            for kind,keys in [('raw',RAW_KEYS),('even',('N_A','N_B')),('odd',('M_A','M_B'))]}


def errors(actual,reference):
    a,b=components(actual),components(reference)
    return {kind:float(np.linalg.norm(a[kind]-b[kind])/max(np.linalg.norm(b[kind]),1e-30)) for kind in a}


def decomposition(result,sites):
    spectra=result['spectra'];count=sum(g.multiplicity for g in sites.groups)
    assert result['metadata']['multisite']['selected_atom_count']==count
    for key in RAW_KEYS:
        weighted=sum(g.multiplicity*result['groups'][g.group_id]['spectra'][key] for g in sites.groups)
        np.testing.assert_allclose(spectra[key],weighted/count,rtol=3e-13,atol=1e-18)
        np.testing.assert_allclose(result['weighted_sum']['spectra'][key],weighted,rtol=3e-13,atol=1e-18)
        assert spectra[key].min()>=-1e-12*max(abs(spectra[key]).max(),1e-30)
    for entry in [result]+list(result['groups'].values()):
        s=entry['spectra']
        for detector in ('A','B'):
            np.testing.assert_allclose(s['N_'+detector],(s[f'I_{detector}_plus']+s[f'I_{detector}_minus'])/2,atol=1e-18)
            np.testing.assert_allclose(s['M_'+detector],(s[f'I_{detector}_plus']-s[f'I_{detector}_minus'])/2,atol=1e-18)


@pytest.mark.parametrize('name,thickness',[('Ni',2.),('Cr',.5),('Cr',2.),('Fe3O4',.5),('Fe3O4',2.)])
def test_matched_subspace_depth_convergence_and_multisite_decomposition(tmp_path,name,thickness):
    inputs=case(tmp_path,name)
    reference=analytic_reference(inputs,thickness)
    histories={method:[] for method in ('bloch','fft-multislice')}
    fine={}
    for depth in (9,17,33):
        for method in histories:
            result=run(inputs,method,thickness=thickness,depth=depth)
            decomposition(result,inputs[2])
            histories[method].append(errors(result,reference))
            fine[method]=result
    print(json.dumps(dict(case=name,thickness_nm=thickness,depth_nodes=[9,17,33],relative_errors=histories,
                         matched_fine_gap=errors(fine['fft-multislice'],fine['bloch']))))
    # Same finite elastic subspace/potential, so both approaches must converge
    # toward the analytic depth result. Include group odd signals: total AFM
    # cancellation alone would be an ill-conditioned relative error metric.
    for history in histories.values():
        for kind in ('raw','even','odd'):
            assert history[-1][kind]<history[0][kind]/5
    if name=='Cr' and thickness==.5:
        # The thin sublattice odd signal reaches the fixed split-step floor
        # before the depth floor. Diagnose it with a slice refinement rather
        # than demanding equality of two still-different approximations.
        refined=run(inputs,'fft-multislice',thickness=thickness,slice_step=.005)
        before=errors(fine['fft-multislice'],fine['bloch'])
        after=errors(refined,fine['bloch'])
        print(json.dumps(dict(thin_cr_split_step_gap=before,refined_gap=after)))
        assert after['odd']<before['odd']/2
    reverse=run(inputs,'fft-multislice',thickness=thickness,reverse=True)
    for key in fine['fft-multislice']['groups']:
        p=fine['fft-multislice']['groups'][key]['spectra'];m=reverse['groups'][key]['spectra']
        for detector in ('A','B'):
            np.testing.assert_allclose(p[f'I_{detector}_plus'],m[f'I_{detector}_minus'],rtol=3e-13)
    if name=='Cr':
        # Cancellation scale is the resolved sublattice signal, not a relative
        # tolerance against the near-zero total odd spectrum.
        odd_scale=max(abs(fine['fft-multislice']['groups']['up']['spectra']['M_A']).max(),1e-30)
        assert abs(fine['fft-multislice']['spectra']['M_A']).max()<1e-11*odd_scale
    if name=='Fe3O4' and thickness==2.:
        group=inputs[2].groups[1]
        split=MultiSiteIonization(inputs[0],[inputs[2].groups[0],replace(group,group_id='Fe(B1)',indices=(1,),multiplicity=1),
            replace(group,group_id='Fe(B2)',indices=(2,),multiplicity=1),inputs[2].groups[2]])
        windows=dict(inputs[4]);window=windows.pop('Fe(B)');windows.update({'Fe(B1)':window,'Fe(B2)':window})
        for method in fine:
            separate=run(inputs,method,thickness=thickness,sites=split,windows=windows)
            for key in RAW_KEYS:
                np.testing.assert_allclose(separate['spectra'][key],fine[method]['spectra'][key],rtol=3e-13,atol=1e-18)
        oxygen_only=run(inputs,'fft-multislice',thickness=thickness,windows={'O':inputs[4]['O']})
        for key in RAW_KEYS:
            np.testing.assert_allclose(oxygen_only['spectra'][key],fine['fft-multislice']['spectra'][key][:1],rtol=3e-13)
        assert oxygen_only['metadata']['multisite']['selected_atom_count']==7


@pytest.mark.parametrize('name',['Cr','Fe3O4'])
def test_matched_subspace_slice_and_fft_sampling(tmp_path,name):
    inputs=case(tmp_path,name)
    # Hold depth quadrature fixed to isolate split-step error from depth error.
    bw=run(inputs,'bloch',thickness=2.,depth=65)
    histories=[];fine=None
    for step in (.02,.01,.005):
        fine=run(inputs,'fft-multislice',thickness=2.,depth=65,slice_step=step)
        histories.append(errors(fine,bw))
    mesh=run(inputs,'fft-multislice',thickness=2.,depth=65,slice_step=.005,mesh=24)
    mesh_gap=errors(mesh,fine)
    print(json.dumps(dict(case=name,slice_steps_nm=[.02,.01,.005],relative_errors=histories,mesh16_to24_gap=mesh_gap)))
    for kind in ('raw','even','odd'):
        assert histories[-1][kind]<histories[0][kind]/5
        # The band-limited potential already fits both meshes. This is a
        # sampling-invariance check for the matched projected subspace.
        assert mesh_gap[kind]<1e-10


def test_bounded_unrestricted_cr_beam_cutoff_comparison(tmp_path):
    original=case(tmp_path,'Cr')
    settings=replace(original[1],basis_mode='full',potential_cutoff=1.5)
    observations=[]
    for cutoff in (.55,.75,1.05):
        inputs=(original[0],replace(settings,beam_cutoff=cutoff),*original[2:])
        bw=run(inputs,'bloch',thickness=2.,depth=65,slice_step=.005)
        ms=run(inputs,'fft-multislice',thickness=2.,depth=65,slice_step=.005)
        decomposition(bw,inputs[2]);decomposition(ms,inputs[2])
        observations.append(dict(cutoff=cutoff,beams=len(bw['metadata']['beam_hkl']),gap=errors(ms,bw),
            excluded_incoming=ms['metadata']['fft']['max_excluded_population'],
            excluded_outgoing=max(d['outgoing_max_excluded_population'] for d in ms['metadata']['angular_evaluation'])))
    print(json.dumps(dict(unrestricted_cr=observations)))
    # Diagnose the significant residual at the largest tested common MDFF
    # support. These two targeted refinements isolate MS discretization from
    # the finite-BW/unrestricted-MS elastic-subspace difference.
    mesh=run(inputs,'fft-multislice',thickness=2.,depth=65,slice_step=.005,mesh=24)
    step=run(inputs,'fft-multislice',thickness=2.,depth=65,slice_step=.0025)
    print(json.dumps(dict(unrestricted_finest_ms_mesh16_to24=errors(mesh,ms),
                         unrestricted_finest_ms_half_slice_step=errors(step,ms),
                         total_raw_gap=float(np.linalg.norm(ms['spectra']['I_A_plus']-bw['spectra']['I_A_plus'])/
                                             np.linalg.norm(bw['spectra']['I_A_plus'])),
                         group_odd_gaps={key:float(np.linalg.norm(ms['groups'][key]['spectra']['M_A']-bw['groups'][key]['spectra']['M_A'])/
                             max(np.linalg.norm(bw['groups'][key]['spectra']['M_A']),1e-30)) for key in bw['groups']})))
    assert observations[0]['beams']<observations[1]['beams']<observations[2]['beams']
    # These are different elastic approximations: BW is finite-basis whereas
    # MS retains unrestricted FFT fields and only truncates the MDFF paths.
    # Record the discrepancy/leakage rather than asserting arbitrary equality.
    assert all(np.isfinite(list(item['gap'].values())).all() for item in observations)
