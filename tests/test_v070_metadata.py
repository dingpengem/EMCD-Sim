"""Version, package provenance and legacy interpretation; no kernel changes."""
import copy
from pathlib import Path
import re

from emcd_sim import __version__, __display_version__
from emcd_sim.provenance import PHYSICS_CONVENTION, build_info, result_convention_status

ROOT=Path(__file__).resolve().parents[1]


def test_registered_scientific_sources_keep_approved_identity_checks():
    from single_element_source_guard import assert_current_extension
    assert_current_extension()


def test_canonical_result_metadata_and_detector_flux(tmp_path):
    import numpy as np
    from dataclasses import asdict
    from emcd_sim.forward_pipeline import calculate
    from test_multisite_forward import system, configuration, ENERGY
    structure,settings,sites,_=system(tmp_path,'Cr')
    result=calculate(structure,settings,configuration(),sites=sites,energy_ev=ENERGY)
    metadata=result['metadata'];spectra=result['spectra']
    assert metadata['settings']==asdict(settings)
    assert metadata['software_version']==__version__
    assert metadata['software_display_version']==__display_version__
    assert metadata['physics_convention']==PHYSICS_CONVENTION
    assert metadata['software_commit']==build_info()['commit']
    np.testing.assert_array_equal(metadata['energy_ev'],ENERGY)
    dq2=(result['qx'][0,1]-result['qx'][0,0])**2
    for label,maps in result['maps'].items():
        loss=dict(result['config'].selected_edges)[label]
        index=int(np.flatnonzero(ENERGY==loss)[0])
        for state in ('plus','minus'):
            for detector in ('A','B'):
                integrated=np.sum(maps['I_'+state]*result['weights'][detector])*dq2
                np.testing.assert_array_equal(integrated,spectra[f'I_{detector}_{state}'][index])
    np.testing.assert_allclose(spectra['D_raw'],spectra['D_mag']+spectra['D_nonmag'],
        rtol=1e-10,atol=1e-13*max(spectra['I_A_plus'].max(),spectra['I_B_plus'].max()))
    np.testing.assert_array_equal(spectra['Sigma_ref'],spectra['N_A']+spectra['N_B'])


def test_current_windows_and_workflow_metadata_match_source():
    assert (__version__,__display_version__)==('0.9.0b2','v0.9.0-beta.2')
    text=(ROOT/'packaging/windows_version_info.txt').read_text()
    assert 'filevers=(0, 9, 0, 2), prodvers=(0, 9, 0, 2)' in text
    assert "'FileVersion', '0.9.0.2'" in text and "'ProductVersion', 'v0.9.0-beta.2'" in text
    workflow=(ROOT/'.github/workflows/windows-build.yml').read_text()
    assert 'EMCD-Sim-v0.9.0-beta.2-Windows' in workflow
    assert 'build/windows-v0.9.0-beta.2' in workflow
    assert not re.search(r'beta3|beta\.3|0\.6\.1b3',workflow)
    assert build_info()['physics_convention']==PHYSICS_CONVENTION


def test_missing_convention_is_unknown_and_metadata_is_not_rewritten():
    data={'software_version':'0.6.1b3','software_commit':'original','source_audit':{'sha256':'original-source'}}
    before=copy.deepcopy(data)
    status=result_convention_status(data)
    assert status['status']=='unknown-or-legacy-unverified' and status['identifier'] is None
    assert 'preserved' in status['warning'] and data==before


def test_explicit_old_convention_is_preserved_and_warned():
    data={'physics_convention':'legacy_same_index_h_minus_g','software_version':'0.6.1b3'}
    before=dict(data);status=result_convention_status(data)
    assert status['identifier']==data['physics_convention'] and status['status']=='recorded-other'
    assert status['warning'] and data==before


def test_explicit_corrected_convention_is_recorded_not_inferred_from_version():
    status=result_convention_status({'physics_convention':PHYSICS_CONVENTION,'software_version':'0.7.0b1'})
    assert status['status']=='recorded-corrected' and status['warning'] is None


def test_old_project_roundtrip_preserves_arrays_and_provenance(tmp_path):
    from emcd_sim.gui.project_io import load_project, save_project, fingerprints
    reference=ROOT/'outputs/v060_release/source_native/single_both_project'
    if not reference.exists():
        import pytest
        pytest.skip('Optional historical saved project is unavailable')
    result=load_project(reference);before=fingerprints(result);old=copy.deepcopy(result['metadata'])
    assert result['project_convention_status']['status']=='unknown-or-legacy-unverified'
    assert any('legacy-unverified' in v for v in result['project_warnings'])
    save_project(result,tmp_path/'legacy_copy');opened=load_project(tmp_path/'legacy_copy')
    assert fingerprints(opened)==before and opened['metadata']==old
    assert sum('legacy-unverified' in v for v in opened['project_warnings'])==1


def test_new_calculation_records_convention_and_roundtrips_without_relabeling(tmp_path):
    import numpy as np
    from emcd_sim.structure_geometry import Structure, Settings
    from emcd_sim.forward_settings import NiForwardSettings
    from emcd_sim.forward_pipeline import calculate
    from emcd_sim.gui.project_io import load_project, save_project, fingerprints
    settings=Settings(zone=(0,0,1),thickness=.5,beam_cutoff=.9,potential_cutoff=1.8,tilt=(-5.5866881404, 0.0))
    config=NiForwardSettings(axis_declared=True,grid=9,depth=5,subpixels=4,halfwidth=.5,
                           angular_maps=False,correction=False,energy_scope='edges')
    result=calculate(Structure.nickel(),settings,config,energy_ev=np.array([config.l3,config.l2]))
    assert result['metadata']['software_version']==__version__
    assert result['metadata']['physics_convention']==PHYSICS_CONVENTION
    before=fingerprints(result)
    save_project(result,tmp_path/'new_project')
    opened=load_project(tmp_path/'new_project')
    assert fingerprints(opened)==before
    assert opened['project_convention_status']['status']=='recorded-corrected'
