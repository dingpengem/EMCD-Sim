"""Configuration round trips only: synthetic sources, no elastic calculation."""
from emcd_sim.study_presets import nickel_geometry_settings
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pytest
from ase import Atoms
from ase.build import bulk

from emcd_sim.multisite import IonizationSiteGroup, MultiSiteIonization
from emcd_sim.multisite_spectrum import ModeledEdgeWindow
from emcd_sim.mdff_providers import load_provider
from emcd_sim.gui import project_io as io
from emcd_sim import structure_geometry as structure_data
from emcd_sim.structure_geometry import Structure, Settings
from emcd_sim.forward_settings import NiForwardSettings
from emcd_sim.cancellation import Cancelled
from emcd_sim.forward_settings import MultiSiteForwardSettings
from emcd_sim.mdff_providers import settings_for_source, settings_for_provider
from single_element_helpers import document


def tensor_source(tmp_path,name,element='Fe',axis=(0,0,1),shift=0.,scale=1.,manual=False,frame=None):
    doc = document(element);doc['magnetization_crystal'] = list(axis)
    doc['energy_ev'] = (np.asarray(doc['energy_ev'])+shift).tolist()
    doc['selected_ev'] = {key:value+shift for key,value in doc['selected_ev'].items()}
    if frame is not None:doc.update(basis='declared_local',frame_to_crystal=frame)
    for key in ('T_plus','T_minus','T_even'):
        if manual:
            matrix = np.array([[2,.1j,.03],[-.1j,1,0],[.03,0,1]],complex)
            other = matrix.copy();other[0,2] = other[2,0] = -.03
            value = {'T_plus':matrix,'T_minus':other,'T_even':(matrix+other)/2}[key]
            doc[key] = dict(real=np.repeat((scale*value.real)[None],len(doc['energy_ev']),axis=0).tolist(),
                            imag=np.repeat((scale*value.imag)[None],len(doc['energy_ev']),axis=0).tolist())
        else:
            for part in ('real','imag'):doc[key][part] = (scale*np.asarray(doc[key][part])).tolist()
    if manual:doc['manual_constant_pair_editor'] = 1
    path = tmp_path/(name+'.json');path.write_text(json.dumps(doc),encoding='utf-8')
    return settings_for_source(path)


def configuration(atoms,groups,**kwargs):
    sites = MultiSiteIonization(atoms,groups)
    return dict(structure=Structure(atoms,source='Synthetic ordered crystal'),settings=Settings(zone=(0,0,1),target=(1,0,0),tilt=(-5.5866881404, 0.0)),
        config=MultiSiteForwardSettings(propagation='fft-multislice',channeling_model='double',
            grid=9,depth=7,fft_grid=16,slice_step=.2,centers=((.2,.3),(.2,-.3)),radius=.07),
        site_groups=sites,magnetization_mode='local',reverse_magnetization=True,
        global_config=NiForwardSettings(model='atomic',magnetization=(1.,0.,0.)),
        energy_windows={g.group_id:ModeledEdgeWindow(tuple(load_provider(g.mdff_reference).energy_ev[[0,-1]])) for g in groups},**kwargs)


@pytest.fixture(autouse=True)
def no_physical_calculation(monkeypatch):
    def forbidden(*args,**kwargs):pytest.fail('Configuration IO called a numerical propagation/result loader')
    monkeypatch.setattr(io,'_read_npz',forbidden)
    monkeypatch.setattr('emcd_sim.structure_geometry.elastic_model',forbidden)
    monkeypatch.setattr('emcd_sim.forward_pipeline.calculate',forbidden)


def test_afm_cr_indices_structure_arrays_modes_and_numerics_roundtrip(tmp_path):
    atoms = bulk('Cr','bcc',a=2.88,cubic=True);atoms.positions[1] += atoms.cell[0]
    atoms.set_tags([8,3]);atoms.new_array('spacegroup_kinds',np.array([4,7]))
    atoms.info['occupancy'] = {'4':{'Cr':1.},'7':{'Cr':1.}}
    refs = [tensor_source(tmp_path,'Cr'+str(i),'Cr',axis=axis) for i,axis in enumerate(((0,0,1),(0,0,-1)))]
    groups = [IonizationSiteGroup(name,'Cr',(i,),ref,axis,1) for i,(name,ref,axis) in
              enumerate(zip(('Cr-up','Cr-down'),refs,((0,0,1),(0,0,-1))))]
    state = configuration(atoms,groups,labels={'Cr-up':'Sublattice A','Cr-down':'Sublattice B'})
    root = io.save_configuration(state,tmp_path/'afm');loaded = io.load_configuration(root)
    assert loaded['ready_for_calculation'] and loaded['magnetization_mode']=='local' and loaded['reverse_magnetization']
    assert loaded['group_records'][0]['label']=='Sublattice A'
    for key,value in asdict(state['config']).items():
        actual = asdict(loaded['config'])[key]
        if isinstance(value,float) and np.isnan(value):assert np.isnan(actual)
        else:assert actual==value
    assert loaded['config'].centers==state['config'].centers and loaded['settings']==state['settings']
    assert loaded['global_config'].magnetization==(1.,0.,0.)
    np.testing.assert_array_equal(loaded['structure'].atoms.positions,atoms.positions)
    for name in atoms.arrays:np.testing.assert_array_equal(loaded['structure'].atoms.arrays[name],atoms.arrays[name])
    assert loaded['structure'].atoms.info['occupancy']==atoms.info['occupancy']
    assert [g.indices for g in loaded['site_groups'].groups]==[(0,),(1,)]
    np.testing.assert_array_equal([g.magnetization for g in loaded['site_groups'].groups],[[0,0,1],[0,0,-1]])
    assert not any(root.glob('*.npz'))


@pytest.mark.parametrize('kind',['Ni','Fe','Fe3O4'])
def test_structure_snapshot_restore_without_qt_or_project_io(tmp_path,kind):
    fixtures=Path(__file__).parent/'fixtures'
    cif=None if kind=='Ni' else fixtures/('alpha_Fe_bcc_Im-3m.cif' if kind=='Fe' else 'Fe3O4_inverse_spinel.cif')
    structure=Structure.nickel() if cif is None else Structure.from_cif(cif)
    atoms=structure.atoms;atoms.set_tags(3*np.arange(len(atoms))+1)
    atoms.positions[1]+=atoms.cell[0]  # Configuration snapshots retain original unwrapped sites.
    element='Ni' if kind=='Ni' else 'Fe'
    indices=[i for i,a in enumerate(atoms) if a.symbol==element][:2]
    groups=[IonizationSiteGroup('site'+str(i),element,(index,),
        tensor_source(tmp_path,'site'+str(i),element,axis=axis),axis,1)
        for i,(index,axis) in enumerate(zip(indices,((0,0,1),(0,0,-1))))]
    state=configuration(atoms,groups);state['structure']=structure
    root=io.save_configuration(state,tmp_path/'geometry')
    program=r'''
import builtins, json, sys
from pathlib import Path
original_import=builtins.__import__
def headless_import(name,*args,**kwargs):
    if name.split('.')[0] in ('PySide6','PySide2','PyQt6','PyQt5') or name=='emcd_sim.gui' or name.startswith('emcd_sim.gui.') or name=='project_io':
        raise AssertionError('Neutral geometry imported GUI ownership or project I/O')
    return original_import(name,*args,**kwargs)
builtins.__import__=headless_import
import numpy as np
from emcd_sim.structure_geometry import Structure, Settings, structure_snapshot, restore_structure, structures_match, orientation, geometry, projected_geometry_from_oriented_crystal, align_bragg, excitation
original=Structure.nickel() if sys.argv[1]=='Ni' else Structure.from_cif(sys.argv[2])
snapshot=structure_snapshot(original)
restored=restore_structure(json.loads(json.dumps(snapshot)))
assert structures_match(snapshot,restored)
assert restored.atoms.get_chemical_symbols()==original.atoms.get_chemical_symbols()
assert restored.source==original.source and restored.sha256==original.sha256
assert restored.import_warnings==original.import_warnings
np.testing.assert_array_equal(restored.atoms.cell.array,original.atoms.cell.array)
np.testing.assert_array_equal(restored.atoms.pbc,original.atoms.pbc)
np.testing.assert_array_equal(orientation(original.atoms.cell.array,(0,0,1),(1,0,0)),
                              orientation(restored.atoms.cell.array,(0,0,1),(1,0,0)))
if 'spacegroup_kinds' in original.atoms.arrays:
    np.testing.assert_array_equal(restored.atoms.arrays['spacegroup_kinds'],original.atoms.arrays['spacegroup_kinds'])
target={'Ni':(2,0,0),'Fe':(1,1,0),'Fe3O4':(2,2,0)}[sys.argv[1]]
settings=Settings(zone=(0,0,1),target=target,beam_cutoff=.6,potential_cutoff=1.2)
a=geometry(original,settings);b=geometry(restored,settings)
assert a[2]==b[2] and len(a[2])>1
np.testing.assert_array_equal(a[1],b[1]);np.testing.assert_array_equal(a[3],b[3])
cell=projected_geometry_from_oriented_crystal(settings,a[0])
np.testing.assert_array_equal(cell.crystal.lattice_angstrom,a[0].lattice_angstrom)
spot=a[3][next(i for i,h in enumerate(a[2]) if h!=(0,0,0))]
assert abs(excitation(spot,align_bragg(spot,settings.tilt,settings.voltage),settings.voltage))<1e-12
from dataclasses import replace
try:geometry(original,replace(settings,voltage=-1.))
except ValueError:pass
else:raise AssertionError('Invalid physical geometry accepted')
full=json.loads(Path(sys.argv[3]).read_text(encoding='utf-8'))
rich=restore_structure(full)
assert rich.atoms.get_chemical_symbols()==full['species']
np.testing.assert_array_equal(rich.atoms.positions,full['cartesian_positions'])
np.testing.assert_array_equal(rich.atoms.get_tags(),3*np.arange(len(rich.atoms))+1)
for name,array in full['atom_arrays'].items():
    np.testing.assert_array_equal(rich.atoms.arrays[name],np.asarray(array['values'],dtype=array['dtype']))
for invalid in ({},dict(snapshot,atom_arrays={'numbers':dict(dtype='int64',values=[1]*len(original.atoms))})):
    try:restore_structure(invalid)
    except ValueError:pass
    else:raise AssertionError('Invalid snapshot accepted')
assert not any(n=='emcd_sim.gui' or n.startswith('emcd_sim.gui.') for n in sys.modules)
assert not any(n=='PySide6' or n.startswith('PySide6.') for n in sys.modules)
'''
    completed=subprocess.run([sys.executable,'-B','-c',program,kind,str(cif or ''),str(root/'structure.json')],
        capture_output=True,text=True,timeout=60)
    assert completed.returncode==0,completed.stdout+completed.stderr


def test_local_configuration_roundtrip_without_widget_dependencies(tmp_path):
    """Persistence must validate groups/providers without loading Qt editors."""
    atoms = bulk('Cr','bcc',a=2.88,cubic=True)
    reference = tensor_source(tmp_path,'Cr','Cr')
    group = IonizationSiteGroup('Cr-up','Cr',(0,),reference,(0,0,1),1)
    root = io.save_configuration(configuration(atoms,[group]),tmp_path/'headless')
    program = '''
import builtins
import sys
original_import = builtins.__import__
def without_widgets(name, *args, **kwargs):
    if name == 'PySide6' or name.startswith('PySide6.'):
        raise AssertionError('Configuration persistence imported a Qt editor')
    return original_import(name, *args, **kwargs)
builtins.__import__ = without_widgets
from emcd_sim.gui.project_io import load_configuration, save_configuration
state = load_configuration(sys.argv[1])
assert state['ready_for_calculation']
assert state['site_groups'].groups[0].indices == (0,)
again = load_configuration(save_configuration(state, sys.argv[2]))
assert again['ready_for_calculation']
assert again['config'].centers == state['config'].centers
assert not any(n == 'PySide6' or n.startswith('PySide6.') for n in sys.modules)
'''
    completed = subprocess.run([sys.executable,'-B','-c',program,str(root),str(tmp_path/'again')],
        capture_output=True,text=True,timeout=60)
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_fe3o4_manual_pair_portable_relocation_and_exact_amplitudes(tmp_path):
    atoms = Atoms('Fe3O4',scaled_positions=np.arange(21).reshape(7,3)/24,cell=[[8,0,0],[1,8,0],[0,1,8]],pbc=True)
    a = tensor_source(tmp_path,'Fe_A');b = tensor_source(tmp_path,'Fe_B',axis=(0,0,-1),scale=4.,manual=True,
        frame=[[1,0,0],[0,-1,0],[0,0,-1]])
    expected = load_provider(b)
    groups = [IonizationSiteGroup('Fe(A)','Fe',(0,),a,(0,0,1),1),IonizationSiteGroup('Fe(B)','Fe',(1,2),b,(0,0,-1),2)]
    state = configuration(atoms,groups,editor_drafts={'Fe(B)':{'pair':[['2','0.4j','0.12'],['-0.4j','4','0'],['0.12','0','4']],
        'frame':[[1,0,0],[0,-1,0],[0,0,-1]],'note':'Exact direct-entry draft'}})
    root = io.save_configuration(state,tmp_path/'original')
    original_bytes = Path(b.source).read_bytes();Path(b.source).unlink()
    shutil.copytree(root,tmp_path/'relocated');loaded = io.load_configuration(tmp_path/'relocated')
    assert loaded['ready_for_calculation']
    assert sum(g.multiplicity for g in loaded['site_groups'].groups)==3  # O is elastic-only.
    restored = loaded['site_groups'].groups[1].mdff_reference
    assert Path(restored.source).parent==tmp_path/'relocated' and Path(restored.source).read_bytes()==original_bytes
    assert loaded['source_states']['group:Fe(B)']['portable']
    assert loaded['group_records'][1]['mdff_reference']==b  # Saved source identity retained separately.
    actual = load_provider(restored)
    np.testing.assert_array_equal(actual.plus.tensor_angstrom2_per_ev,expected.plus.tensor_angstrom2_per_ev)
    np.testing.assert_array_equal(actual.minus.tensor_angstrom2_per_ev,expected.minus.tensor_angstrom2_per_ev)
    assert not np.allclose(actual.minus.tensor_angstrom2_per_ev,actual.plus.tensor_angstrom2_per_ev.conj())
    assert loaded['editor_drafts']==state['editor_drafts']
    # A relocated project can be saved again using the verified source overrides.
    again = io.load_configuration(io.save_configuration(loaded,tmp_path/'again'))
    assert again['ready_for_calculation'] and again['source_states']['group:Fe(B)']['portable']


def test_fe_ni_disjoint_windows_samples_and_noncollinear_frame(tmp_path):
    frame = [[0,0,1],[0,1,0],[-1,0,0]]
    fe = tensor_source(tmp_path,'Fe');ni = tensor_source(tmp_path,'Ni','Ni',axis=(1,0,0),shift=140.,frame=frame)
    atoms = Atoms('FeNi',scaled_positions=[[0,0,0],[.5,.5,.5]],cell=[3,4,5],pbc=True)
    state = configuration(atoms,[IonizationSiteGroup('Fe','Fe',(0,),fe,(0,0,1),1),IonizationSiteGroup('Ni','Ni',(1,),ni,(1,0,0),1)])
    state['energy_windows'] = {'Fe':ModeledEdgeWindow((704,730),(710,723)),'Ni':ModeledEdgeWindow((844,870),(850,863))}
    state['energy_ev'] = [710.,723.,850.,863.]
    loaded = io.load_configuration(io.save_configuration(state,tmp_path/'edges'))
    assert loaded['ready_for_calculation'] and loaded['energy_windows']==state['energy_windows']
    np.testing.assert_array_equal(loaded['energy_ev'],state['energy_ev'])
    assert loaded['group_records'][1]['mdff_reference']==ni
    assert load_provider(loaded['site_groups'].groups[1].mdff_reference).metadata['frame_to_crystal']==frame
    np.testing.assert_array_equal(loaded['site_groups'].groups[1].magnetization,[1,0,0])


@pytest.mark.parametrize('defect',['missing','changed'])
def test_external_source_unavailable_never_substitutes_global_or_provider(tmp_path,defect):
    ref = tensor_source(tmp_path,'external')
    state = configuration(Atoms('Fe',positions=[[0,0,0]],cell=[3,3,3],pbc=True),[IonizationSiteGroup('Fe','Fe',(0,),ref,(0,0,1),1)])
    root = io.save_configuration(state,tmp_path/'saved')
    if defect=='missing':Path(ref.source).unlink()
    else:Path(ref.source).write_text('{}',encoding='utf-8')
    loaded = io.load_configuration(root)
    assert not loaded['ready_for_calculation'] and loaded['site_groups'] is None
    assert loaded['magnetization_mode']=='local' and loaded['global_config'].magnetization==(1.,0.,0.)
    assert loaded['source_states']['group:Fe']['state']==defect
    assert loaded['group_records'][0]['mdff_reference']==ref
    # Unavailable declarations can be preserved again; no source is regenerated.
    assert not io.load_configuration(io.save_configuration(loaded,tmp_path/'still-unavailable'))['ready_for_calculation']


@pytest.mark.parametrize('mode',['local','global'])
def test_incomplete_local_drafts_survive_modes_without_inference(tmp_path,mode):
    atoms = Atoms('Fe2',positions=[[0,0,0],[1,1,1]],cell=[3,3,3],pbc=True)
    records = [dict(group_id=name,label=name,element='Fe',indices=(i,),magnetization=direction,
        multiplicity=1,normalization='mean_per_selected_atom',mdff_reference=None)
        for i,(name,direction) in enumerate((('A',(1.,0.,0.)),('B',(0.,1.,0.))))]
    cfg = MultiSiteForwardSettings() if mode=='local' else NiForwardSettings(model='atomic',magnetization=(0.,0.,-1.))
    state = dict(structure=Structure(atoms),settings=nickel_geometry_settings(),config=cfg,magnetization_mode=mode,group_records=records)
    loaded = io.load_configuration(io.save_configuration(state,tmp_path/'drafts'))
    assert loaded['magnetization_mode']==mode and loaded['site_groups'] is None
    assert loaded['ready_for_calculation']==(mode=='global')
    for original,restored in zip(records,loaded['group_records']):assert restored==original
    assert not loaded['reverse_magnetization']


def test_xmcd_declarations_scale_reversal_and_external_policy(tmp_path):
    from emcd_sim.imported_mdff import CONVENTION
    e = np.linspace(704,730,9);n = 1+np.exp(-((e-710)/2)**2);m = .05*np.exp(-((e-710)/2)**2)
    path = tmp_path/'Fe.xmcd';np.savetxt(path,np.column_stack((e,n+m,n-m,2*m,2*n)))
    declaration = dict(element='Fe',edge='L2,3',selected_ev=dict(L3=710,L2=723),magnetization_crystal=[0,0,1],
        handedness='RP_minus_LP_in_declared_axis',eta=1.,beta=.8,normalization='source_max_nonmagnetic',convention=CONVENTION,
        source='Synthetic configuration test',validity='Not physical spectra',status='synthetic',source_sha256=io.sha256(path),
        reference_tensor_scale_angstrom2_per_ev=3.,magnetic_state='uniform_fm',reversal_assumption='axisymmetric_XMCD_odd_shared_XAS')
    cfg = settings_for_provider(path,'xmcd',declaration)
    state = configuration(Atoms('Fe',positions=[[0,0,0]],cell=[3,3,3],pbc=True),[IonizationSiteGroup('Fe','Fe',(0,),cfg,(0,0,1),1)])
    root = io.save_configuration(state,tmp_path/'xmcd');loaded = io.load_configuration(root)
    assert loaded['ready_for_calculation'] and loaded['group_records'][0]['mdff_reference']==cfg
    assert not loaded['source_states']['group:Fe']['portable']
    assert not list(root.glob('mdff_*.json'))
    assert loaded['group_records'][0]['mdff_reference'].provider_declaration==declaration


@pytest.mark.parametrize('managed',[True,False])
def test_atomic_editor_source_parameters_are_portable_without_regeneration(tmp_path,managed):
    from PySide6 import QtWidgets
    from emcd_sim.gui.atomic_editor import AtomicParameterEditor
    from emcd_sim.gui.atomic_editor_model import persist_document
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    editor = AtomicParameterEditor(lambda:tmp_path)
    try:
        example = Path(__file__).resolve().parents[1]/'docs/examples/synthetic_fe_atomic_parameters.json'
        editor.load_document(example)
        doc = editor.document() if managed else json.loads(example.read_text(encoding='utf-8'))
        doc['energy_ev'] = [704.,710.,723.,730.]
        source,_ = persist_document(tmp_path,doc);cfg = settings_for_provider(source,'atomic')
        state = configuration(Atoms('Fe',positions=[[0,0,0]],cell=[3,3,3],pbc=True),[IonizationSiteGroup('Fe','Fe',(0,),cfg,(0,0,1),1)])
        root = io.save_configuration(state,tmp_path/'atomic');raw = source.read_bytes();source.unlink()
        loaded = io.load_configuration(root)
        assert loaded['ready_for_calculation']==managed and loaded['source_states']['group:Fe']['portable']==managed
        if managed:
            actual = loaded['site_groups'].groups[0].mdff_reference
            assert Path(actual.source).read_bytes()==raw
            assert json.loads(Path(actual.source).read_text(encoding='utf-8'))==doc
            assert io.portable_mdff_bytes(cfg,source,raw.decode('utf-8'))==raw  # Existing legacy result evidence fallback.
        else:assert loaded['source_states']['group:Fe']['state']=='missing'
    finally:editor.close();editor.deleteLater();app.processEvents()


def test_legacy_project_configuration_is_global_and_needs_no_result_arrays(tmp_path):
    root = tmp_path/'legacy';root.mkdir();cfg = NiForwardSettings(model='atomic',magnetization=(1.,0.,0.))
    snapshot = structure_data.structure_snapshot(Structure.nickel())
    io._json(root/'structure.json',snapshot)
    settings = asdict(nickel_geometry_settings());settings.pop('elastic_provider')
    io._json(root/'input_parameters.json',dict(settings=settings,mdff=asdict(cfg),structure_snapshot=snapshot))
    io._json(root/'project.json',dict(schema_version=1,complete=True,files={p.name:io.sha256(p) for p in root.iterdir()}))
    loaded = io.load_configuration(root)
    assert loaded['ready_for_calculation'] and loaded['config']==cfg
    assert loaded['magnetization_mode']=='global' and loaded['group_records']==[] and loaded['site_groups'] is None
    assert loaded['settings'].elastic_provider=='nickel-lobato-2014'


def test_legacy_xmcd_audit_identity_survives_configuration_save_as(tmp_path):
    root = tmp_path/'legacy-xmcd';root.mkdir()
    source = tmp_path/'legacy.xmcd';energy = np.linspace(830,860,5)
    np.savetxt(source,np.column_stack((energy,np.full(5,1.1),np.full(5,.9),np.full(5,.2),np.full(5,2.))))
    cfg = NiForwardSettings(source=str(source),source_sha256='',axis_declared=True)
    snapshot = structure_data.structure_snapshot(Structure.nickel())
    io._json(root/'structure.json',snapshot)
    io._json(root/'input_parameters.json',dict(settings=asdict(nickel_geometry_settings()),mdff=asdict(cfg),structure_snapshot=snapshot))
    io._json(root/'metadata.json',dict(source_audit={'sha256':io.sha256(source)},source_note='Original legacy audit'))
    io._json(root/'project.json',dict(schema_version=1,complete=True,files={p.name:io.sha256(p) for p in root.iterdir()}))
    old = io.load_configuration(root)
    assert old['ready_for_calculation'] and old['config']==cfg
    restored = io.load_configuration(io.save_configuration(old,tmp_path/'configuration-copy'))
    assert restored['ready_for_calculation'] and restored['config']==cfg
    assert restored['metadata']==old['metadata']
    assert restored['source_states']['config']['sha256']==io.sha256(source)
    source.write_bytes(source.read_bytes()+b' ')
    assert not io.load_configuration(tmp_path/'configuration-copy')['ready_for_calculation']


def test_global_manual_portable_source_exposes_verified_effective_settings(tmp_path):
    cfg = tensor_source(tmp_path,'Ni-manual',element='Ni',manual=True)
    state = dict(structure=Structure.nickel(),settings=nickel_geometry_settings(),config=cfg,magnetization_mode='global')
    root = io.save_configuration(state,tmp_path/'global-portable');Path(cfg.source).unlink()
    loaded = io.load_configuration(root)
    assert loaded['ready_for_calculation'] and loaded['config']==cfg
    assert loaded['site_groups'] is None and loaded['group_records']==[]
    effective = loaded['effective_config']
    assert Path(effective.source).parent==root and Path(effective.source).is_file()
    assert effective.source_sha256==cfg.source_sha256 and effective.magnetization==cfg.magnetization
    assert loaded['source_states']['config']['portable'] and loaded['effective_global_config'] is None


@pytest.mark.parametrize('defect',['duplicate','species','multiplicity','mode','frame','coverage'])
def test_invalid_assignments_or_scientific_declarations_are_not_executable(tmp_path,defect):
    ref = tensor_source(tmp_path,'Fe')
    state = configuration(Atoms('Fe2',positions=[[0,0,0],[1,1,1]],cell=[3,3,3],pbc=True),
        [IonizationSiteGroup('A','Fe',(0,),ref,(0,0,1),1),IonizationSiteGroup('B','Fe',(1,),ref,(0,0,1),1)])
    if defect in ('duplicate','species','multiplicity'):
        state['group_records'] = [dict(group_id=g.group_id,element=g.element,indices=g.indices,magnetization=g.magnetization,
            multiplicity=g.multiplicity,normalization=g.normalization,mdff_reference=g.mdff_reference) for g in state['site_groups'].groups]
        if defect=='duplicate':state['group_records'][1]['indices'] = (0,)
        elif defect=='species':state['group_records'][1]['element'] = 'Ni'
        else:state['group_records'][1]['multiplicity'] = 2
        with pytest.raises(ValueError):io.save_configuration(state,tmp_path/'invalid')
    else:
        if defect=='mode':state['magnetization_mode'] = 'guess'
        elif defect=='frame':
            doc = json.loads(Path(ref.source).read_text());doc['frame_to_crystal'] = [[1,0,0],[0,1,0],[0,0,2]]
            Path(ref.source).write_text(json.dumps(doc));bad = replace(ref,source_sha256=io.sha256(ref.source))
            state['site_groups'] = MultiSiteIonization(state['structure'],[replace(g,mdff_reference=bad) for g in state['site_groups'].groups])
        else:state['energy_windows']['A'] = ModeledEdgeWindow((700,730))
        if defect=='mode':
            with pytest.raises(ValueError,match='mode'):io.save_configuration(state,tmp_path/'invalid')
        else:
            loaded = io.load_configuration(io.save_configuration(state,tmp_path/'invalid-science'))
            assert not loaded['ready_for_calculation'] and loaded['site_groups'] is None and loaded['issues']


def test_existing_manifest_integrity_and_cancelled_save(tmp_path):
    state = dict(structure=Structure.nickel(),settings=nickel_geometry_settings(),config=NiForwardSettings(model='atomic'),magnetization_mode='global')
    with pytest.raises(Cancelled):io.save_configuration(state,tmp_path/'cancelled',cancelled=lambda:True)
    assert not (tmp_path/'cancelled').exists() and not list(tmp_path.glob('.cancelled.saving_*'))
    root = io.save_configuration(state,tmp_path/'saved')
    (root/'input_parameters.json').write_text('{}')
    with pytest.raises(ValueError,match='corrupted'):io.load_configuration(root)


def test_missing_energy_configuration_is_not_filled_from_provider_defaults(tmp_path):
    ref = tensor_source(tmp_path,'Fe')
    state = configuration(Atoms('Fe',positions=[[0,0,0]],cell=[3,3,3],pbc=True),[IonizationSiteGroup('Fe','Fe',(0,),ref,(0,0,1),1)])
    state['energy_windows'] = None
    root = io.save_configuration(state,tmp_path/'no-energy');loaded = io.load_configuration(root)
    assert not loaded['ready_for_calculation'] and loaded['site_groups'] is None
    assert loaded['energy_windows'] is None and loaded['energy_ev'] is None
    assert any('energy selection is unconfigured' in issue for issue in loaded['issues'])
    with pytest.raises(ValueError,match='Configuration-only'):io.load_project(root)
