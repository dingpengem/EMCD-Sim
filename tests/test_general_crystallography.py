"""Exact lattice/orientation controls, without any legacy geometry imports."""
from itertools import product
import numpy as np
import pytest
from emcd_sim.crystal import Crystal,fcc_nickel
from emcd_sim.crystallography import integer_plane,primitive_direction,CrystalOrientation,reciprocal_plane,row_coordinates,infer_zone
from emcd_sim.projected_geometry import ProjectedGeometry
from emcd_sim.projected_potential import prepare_projected_potential,potential_site_labels,interaction_parameter_volt_nm
from emcd_sim.scattering import IndependentAtomPotential


@pytest.mark.parametrize('zone',[(0,0,1),(0,1,7),(1,1,7),(1,1,1),(7,1,0),(-2,3,-5),(0,-4,6),(6,10,15)])
def test_integer_kernel_is_primitive_and_complete(zone):
    u=np.array(primitive_direction(zone));B=integer_plane(zone)
    np.testing.assert_array_equal(B@u,0)
    cross=np.cross(B[0],B[1]);assert np.array_equal(cross,u) or np.array_equal(cross,-u)
    for h in product(range(-3,4),repeat=3):
        if np.dot(h,u)==0:np.testing.assert_array_equal(row_coordinates(h,B)@B,h)


@pytest.mark.parametrize('zone,target',[( (0,0,1),(2,0,0)),((0,1,7),(2,0,0)),((1,1,7),(2,-2,0)),((1,1,1),(2,-2,0)),((7,1,0),(0,0,2))])
def test_fcc_translations_metric_and_complete_support(zone,target):
    geo=ProjectedGeometry.from_crystal(fcc_nickel(),zone,target)
    R=geo.frame;np.testing.assert_allclose(np.cross(R[0],R[1]),R[2],atol=1e-15)
    assert np.linalg.det(R)==pytest.approx(1)
    np.testing.assert_allclose(geo.crystal.g_vector(target)[1:],0,atol=1e-15)
    np.testing.assert_allclose(geo.real_cell_xy@geo.reciprocal_xy.T,np.eye(2),atol=1e-15)
    assert infer_zone(geo.crystal)==zone
    # Brute force independently verifies both FCC parities and negative hkl.
    actual=set(geo.hkl_within(3.2));expected=set()
    for h in product(range(-13,14),repeat=3):
        if np.dot(h,zone)==0 and (h[0]%2==h[1]%2==h[2]%2) and np.linalg.norm(geo.crystal.g_vector(h))<=3.2+1e-12:expected.add(h)
    assert actual==expected


def test_target_higher_order_does_not_delete_primitive_reflections():
    geo=ProjectedGeometry.from_crystal(fcc_nickel(),(0,0,1),(4,0,0))
    np.testing.assert_array_equal(geo.generators[0],(2,0,0))
    with pytest.raises(ValueError,match='omits'):
        ProjectedGeometry.from_crystal(fcc_nickel(),(0,0,1),(4,0,0),generators=((4,0,0),(0,2,0)))


def test_non_cubic_metric_and_tilt_independent_structure():
    source=Crystal(np.array([[3.5,0,0],[.4,4.1,0],[.2,.3,5.2]]),[[.13,.27,.31]],('Ni',))
    geo=ProjectedGeometry.from_crystal(source,(1,1,2),(2,-2,0))
    np.testing.assert_allclose(geo.crystal.g_vector((2,-2,0)),geo.frame@source.g_vector((2,-2,0)),atol=1e-15)
    np.testing.assert_allclose(geo.orientation.positions_local,source.fractional_positions@source.lattice_angstrom@geo.frame.T,atol=1e-15)
    np.testing.assert_array_equal(geo.crystal.fractional_positions,source.fractional_positions)
    assert np.linalg.norm(geo.crystal.g_vector((2,-2,0)))==pytest.approx(np.linalg.norm(source.g_vector((2,-2,0))))


def test_potential_site_properties_break_translations_without_losing_terms():
    c=fcc_nickel();p=IndependentAtomPotential(c,occupancies=(1.,.5,1.,1.))
    geo=ProjectedGeometry.from_crystal(c,(0,0,1),(2,0,0),labels=potential_site_labels(p))
    potential=IndependentAtomPotential(geo.crystal,occupancies=(1.,.5,1.,1.))
    field=prepare_projected_potential(geo,potential,200,32,1.8)
    lookup={tuple(h):i for i,h in enumerate(field.hkl)}
    assert abs(potential.structure_factor((1,0,0)))>0
    assert abs(field.phase_fourier_nm_inv.ravel()[lookup[(1,0,0)]])>0
    compressed=ProjectedGeometry.from_crystal(c,(0,0,1),(2,0,0))
    with pytest.raises(ValueError,match='omits'):
        prepare_projected_potential(compressed,p,200,32,1.8)


def test_phase_units_and_oblique_cell_fourier_normalization():
    geo=ProjectedGeometry.from_crystal(fcc_nickel(),(1,1,7),(2,-2,0));p=IndependentAtomPotential(geo.crystal,debye_waller_b_angstrom2=.2)
    field=prepare_projected_potential(geo,p,200,(32,40),3.8)
    assert field.phase_nm_inv.shape==(32,40)
    np.testing.assert_allclose(np.fft.fft2(field.phase_nm_inv)/field.phase_nm_inv.size,field.phase_fourier_nm_inv,atol=1e-16)
    i={tuple(h):j for j,h in enumerate(field.hkl)}[(2,-2,0)]
    assert field.phase_fourier_nm_inv.ravel()[i]==pytest.approx(interaction_parameter_volt_nm(200)*p.fourier_potential_volts((2,-2,0)),rel=2e-15)
    assert field.phase_fourier_nm_inv[0,0]==0
    with pytest.raises(ValueError,match='Nyquist|misses'):
        geo.harmonics(12,6.2)
    with pytest.raises(ValueError,match='512'):geo.harmonics(1024,3.8)
    with pytest.raises(ValueError,match='10000'):integer_plane((1,1,10001))


def test_new_axis_and_unimodular_cell_change_need_no_orientation_code():
    from emcd_sim.multislice_double_channeling import ProjectedFFT,incident_fields
    from emcd_sim.geometry import Microscope
    geo=ProjectedGeometry.from_crystal(fcc_nickel(),(1,2,3),(2,2,-2))
    changed=ProjectedGeometry.from_crystal(fcc_nickel(),(1,2,3),(2,2,-2),
        generators=np.array([[1,0],[1,1]])@geo.generators)
    fields=[]
    beams=geo.beams(2.2).hkl
    for cell in (geo,changed):
        p=IndependentAtomPotential(cell.crystal)
        grid=ProjectedFFT.from_potential(cell,p,Microscope(200,(.3,-.2)),grid_points=(48,48),potential_cutoff=2.2,beam_hkl=beams)
        wave=incident_fields(grid,.2,depth_steps=5,slice_step_nm=.01)[0]
        assert np.max(abs(np.sum(abs(wave)**2,axis=1)-1))<1e-13
        fields.append(wave[:,grid.indices(beams)])
    np.testing.assert_allclose(fields[0],fields[1],rtol=0,atol=2e-13)


def test_production_has_no_legacy_geometry_dependencies():
    import ast
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]/'src/emcd_sim'
    for p in root.rglob('*.py'):
        tree=ast.parse(p.read_text(encoding='utf-8-sig'))
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):assert node.module is None or not any(s in node.module for s in ('ni_017_geometry','ni_117_geometry'))
            elif isinstance(node,ast.Import):assert not any(any(s in n.name for s in ('ni_017_geometry','ni_117_geometry')) for n in node.names)
    assert not (root/'ni_017_geometry.py').exists()
    assert not (root/'ni_117_geometry.py').exists()
    # Shared orientation is independent of both projected geometry and GUI.
    text=(root/'crystallography.py').read_text(encoding='utf-8')
    assert 'from .projected' not in text and 'from .gui' not in text


def test_general_potential_cancellation_and_memory_admission():
    from emcd_sim.cancellation import Cancelled
    geo=ProjectedGeometry.from_crystal(fcc_nickel(),(1,1,1),(2,-2,0))
    p=IndependentAtomPotential(geo.crystal)
    with pytest.raises(Cancelled):prepare_projected_potential(geo,p,200,32,2.2,cancelled=lambda:True)
    with pytest.raises(ValueError,match='memory|MiB|budget'):
        prepare_projected_potential(geo,p,200,512,2.2,memory_budget_mib=1)
