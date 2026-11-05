"""Explicit reviewed editor scope; historical maps remain independently meaningful."""
from pathlib import Path, PurePosixPath
import hashlib
import io
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PARENT = 'c0f7b70157de269114161a6ad14ad6da721b3f9a'
SCOPE_ID = 'generalized-mdff-editor-v1'
MANIFEST_PATH = 'tests/fixtures/generalized_mdff_editor_scope_v1.json'
ARCHIVE_PATH = 'tests/fixtures/generalized_mdff_editor_parent_v1.zip'
MANIFEST_SHA256 = '92e28f88fb969ec9a151c8acf0fae0663e82e76200d85a3a6027f94423b1cab6'
ARCHIVE_SHA256 = '70f4167ce42551052d42a262b64ba3dc97dd9d4d478e5e15444018edaebda1a7'
MODIFIED = ('packaging/emcd_gui.spec', 'pyproject.toml', 'src/emcd_sim/gui/project_io.py', 'src/emcd_sim/gui/provider_ui.py', 'src/emcd_sim/gui/results_browser.py', 'src/emcd_sim/gui/stage_b.py')
ADDED = ('docs/ATOMIC_PARAMETER_EDITOR.md', 'src/emcd_sim/data/edge_references_v1/.gitattributes', 'src/emcd_sim/data/edge_references_v1/LICENSE', 'src/emcd_sim/data/edge_references_v1/edges_subset.dat', 'src/emcd_sim/data/edge_references_v1/provenance.json', 'src/emcd_sim/gui/atomic_editor.py', 'src/emcd_sim/gui/atomic_editor_help.py', 'src/emcd_sim/gui/atomic_editor_model.py', 'src/emcd_sim/gui/tensor_spectrum_preview.py', 'tests/fixtures/atomic_editor/Fe3O4.cif', 'tests/fixtures/atomic_editor/NiFe2O4.cif', 'tests/test_atomic_parameter_editor.py')
PROTECTED = ('data/wien2k_ni/Ni_fm.xmcd', 'packaging/BETA_README.txt', 'packaging/README.md', 'packaging/build_windows.ps1', 'packaging/check_windows_metadata.py', 'packaging/launcher.py', 'packaging/native_acceptance.py', 'packaging/requirements-windows.txt', 'packaging/windows_version_info.txt', 'src/emcd_sim/__init__.py', 'src/emcd_sim/__main__.py', 'src/emcd_sim/adaptive_scattering.py', 'src/emcd_sim/atomic_dipole.py', 'src/emcd_sim/atomic_ionization.py', 'src/emcd_sim/benchmark.py', 'src/emcd_sim/cancellation.py', 'src/emcd_sim/crystal.py', 'src/emcd_sim/crystallography.py', 'src/emcd_sim/data/adaptive_dirac_pade_2026/LICENSE', 'src/emcd_sim/data/adaptive_dirac_pade_2026/NOTICE', 'src/emcd_sim/data/adaptive_dirac_pade_2026/coefficients.json', 'src/emcd_sim/data/adaptive_dirac_pade_2026/provenance.json', 'src/emcd_sim/double_channeling.py', 'src/emcd_sim/elastic.py', 'src/emcd_sim/elastic_providers.py', 'src/emcd_sim/emcd_angular_plots.py', 'src/emcd_sim/generalized_xmcd.py', 'src/emcd_sim/geometry.py', 'src/emcd_sim/gui/__init__.py', 'src/emcd_sim/gui/__main__.py', 'src/emcd_sim/gui/cancellation_acceptance.py', 'src/emcd_sim/gui/channeling.py', 'src/emcd_sim/gui/compare_results.py', 'src/emcd_sim/gui/component_display.py', 'src/emcd_sim/gui/desktop_acceptance.py', 'src/emcd_sim/gui/emcd_forward.py', 'src/emcd_sim/gui/forward_pipeline.py', 'src/emcd_sim/gui/generalized_forward.py', 'src/emcd_sim/gui/geometry.py', 'src/emcd_sim/gui/imported_tensor_ui.py', 'src/emcd_sim/gui/memory_budget.py', 'src/emcd_sim/gui/normalization_controls.py', 'src/emcd_sim/gui/normalization_export.py', 'src/emcd_sim/gui/numerical_settings.py', 'src/emcd_sim/gui/parallel_acceptance.py', 'src/emcd_sim/gui/parallel_resources.py', 'src/emcd_sim/gui/prb_benchmark.py', 'src/emcd_sim/gui/prb_controls.py', 'src/emcd_sim/gui/propagation.py', 'src/emcd_sim/gui/provider_preparation.py', 'src/emcd_sim/gui/responsive.py', 'src/emcd_sim/gui/results.py', 'src/emcd_sim/gui/runtime.py', 'src/emcd_sim/gui/scientific_acceptance.py', 'src/emcd_sim/gui/signal_normalization.py', 'src/emcd_sim/gui/unified_elastic_acceptance.py', 'src/emcd_sim/historical_ni.py', 'src/emcd_sim/imported_mdff.py', 'src/emcd_sim/ionization_sites.py', 'src/emcd_sim/legacy_atomic_factors.py', 'src/emcd_sim/mdff_edges.py', 'src/emcd_sim/mdff_orientation.py', 'src/emcd_sim/mdff_providers.py', 'src/emcd_sim/mdff_tensor.py', 'src/emcd_sim/mirror_parity.py', 'src/emcd_sim/multislice_double_channeling.py', 'src/emcd_sim/multislice_reference.py', 'src/emcd_sim/physical_elastic.py', 'src/emcd_sim/projected_geometry.py', 'src/emcd_sim/projected_potential.py', 'src/emcd_sim/scattering.py', 'src/emcd_sim/simulation.py', 'src/emcd_sim/single_channeling_tensor.py', 'src/emcd_sim/study_geometry.py', 'src/emcd_sim/transition_csv.py', 'src/emcd_sim/wien2k_source_audit.py', 'src/emcd_sim/wien2k_xmcd.py', 'src/emcd_sim/xmcd_effective_mdff.py', 'src/emcd_sim/xmcd_postedge_normalization.py', 'tests/fixtures/Ni_fm_historical_full_benchmark.xmcd', 'tests/fixtures/UNIT_LABEL_SNAPSHOTS.md', 'tests/fixtures/atomic_ionization_scope_v1.json', 'tests/fixtures/build_unit_label_sources.py', 'tests/fixtures/ni_xmcd_provenance_v1.json', 'tests/fixtures/part1c_refactor_scope_v1.json', 'tests/fixtures/physics_source_manifest_v1.json', 'tests/fixtures/reviewed_geometry/ni_017_geometry.py.txt', 'tests/fixtures/reviewed_geometry/ni_117_geometry.py.txt', 'tests/fixtures/single_element_scope_v1.json', 'tests/fixtures/unified_elastic_current_scope_v1.json', 'tests/fixtures/unified_mdff_scope_v1.json', 'tests/fixtures/unit_label_sources_v1.json', 'tests/fixtures/unit_label_sources_v1.zip')
HISTORY = ('tests/fixtures/unit_label_sources_v1.json', 'tests/fixtures/unit_label_sources_v1.zip', 'tests/fixtures/unified_elastic_current_scope_v1.json', 'tests/fixtures/single_element_scope_v1.json', 'tests/fixtures/atomic_ionization_scope_v1.json', 'tests/fixtures/unified_mdff_scope_v1.json', 'tests/fixtures/part1c_refactor_scope_v1.json', 'tests/fixtures/bcc_fe_gui_scope_v1.json', 'tests/fixtures/bcc_fe_gui_baseline_v1.py.txt', 'tests/fixtures/physics_source_manifest_v1.json')


def canonical(raw):
    # Same documented rule as the historical guard helpers.
    return raw.decode('utf-8-sig').replace('\r\n', '\n').encode('utf-8')


def digest(raw, mode='canonical'):
    return hashlib.sha256(raw if mode == 'raw' else canonical(raw)).hexdigest()


def safe_name(path):
    assert isinstance(path, str) and path and '\\' not in path and ':' not in path, 'Unsafe scope path: '+repr(path)
    p = PurePosixPath(path)
    assert not p.is_absolute() and str(p) == path and not any(x in ('.', '..') for x in p.parts), 'Unsafe scope path: '+path
    return path


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, 'Duplicate scope key: '+key
        result[key] = value
    return result


def read_source(path, overrides=None, prefix='Unreviewed current source: '):
    safe_name(path)
    if overrides is not None and path in overrides:
        return overrides[path]
    file = ROOT/path
    assert file.resolve().is_relative_to(ROOT.resolve()), prefix+path+' (outside root)'
    try:
        return file.read_bytes()
    except OSError as exc:
        raise AssertionError(prefix+path+' (missing/unreadable)') from exc


def validate_archive(raw, scope):
    assert hashlib.sha256(raw).hexdigest() == ARCHIVE_SHA256, 'Unreviewed editor parent archive: '+ARCHIVE_PATH
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)), 'Duplicate editor parent archive entry'
        for name in names: safe_name(name)
        assert set(names) == set(MODIFIED), 'Unauthorized/missing editor parent archive entry'
        contents = {name: archive.read(name) for name in names}
    for path, raw in contents.items():
        entry = scope['parent_archive']['files'][path]
        assert digest(raw, 'raw') == entry['raw_sha256'] and digest(raw) == entry['canonical_sha256'], 'Editor parent identity mismatch: '+path
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == entry['git_blob'], 'Editor parent Git blob mismatch: '+path
    return contents


def load_scope(*, manifest_bytes=None, archive_bytes=None):
    raw = read_source(MANIFEST_PATH) if manifest_bytes is None else manifest_bytes
    assert digest(raw) == MANIFEST_SHA256, 'Unreviewed editor scope manifest: '+MANIFEST_PATH
    scope = json.loads(raw, object_pairs_hook=unique_object)
    assert set(scope) == {'schema','scope_id','parent_commit','reviewed_candidate_patch_sha256','reviewed_candidate_manifest_sha256','canonicalization','parent_archive','historical_evidence','candidate','protected_parent'}, 'Unsupported editor scope schema'
    assert type(scope['schema']) is int and scope['schema'] == 1 and scope['scope_id'] == SCOPE_ID, 'Unsupported editor scope schema/identity'
    assert scope['parent_commit'] == PARENT, 'Editor scope parent mismatch'
    assert scope['reviewed_candidate_patch_sha256'] == '8bc6eecf926130379444b3e48bbd4946fe69ebc10a23eaf2dc5343394577e240', 'Superseded editor candidate'
    assert scope['canonicalization'] == 'UTF-8-sig decode; CRLF to LF; UTF-8 encode; no other whitespace normalization; binary and edge table raw', 'Unsupported canonicalization'
    assert set(scope['candidate']) == set(MODIFIED+ADDED), 'Unauthorized editor scope paths'
    assert set(scope['protected_parent']) == set(PROTECTED), 'Unauthorized protected parent paths'
    assert set(scope['historical_evidence']) == set(HISTORY), 'Unauthorized historical evidence paths'
    parent = scope['parent_archive']
    assert set(parent) == {'path','sha256','files'} and parent['path'] == ARCHIVE_PATH and parent['sha256'] == ARCHIVE_SHA256, 'Editor parent archive identity mismatch'
    assert set(parent['files']) == set(MODIFIED), 'Unauthorized editor parent paths'
    for path, entry in scope['candidate'].items():
        safe_name(path)
        assert set(entry) == {'kind','canonical_sha256','raw_sha256','mode'}, 'Unsupported candidate entry: '+path
        assert entry['kind'] == ('modified' if path in MODIFIED else 'added'), 'Wrong path origin: '+path
        assert entry['mode'] == ('raw' if path.endswith('/edges_subset.dat') else 'canonical'), 'Wrong candidate canonicalization: '+path
        for key in ('canonical_sha256','raw_sha256'):
            value = entry[key]
            assert isinstance(value, str) and len(value) == 64 and all(x in '0123456789abcdef' for x in value), 'Invalid candidate digest: '+path
    # Existing authenticated evidence is loaded unchanged, never reinterpreted.
    from unit_source_snapshots import load_snapshots, load_gui_scope
    from single_element_source_guard import extension
    load_snapshots(); load_gui_scope(); historical = extension()
    for path, entry in scope['historical_evidence'].items():
        safe_name(path)
        assert digest(read_source(path), entry['mode']) == entry['sha256'], 'Historical evidence modified: '+path
    raw = read_source(ARCHIVE_PATH) if archive_bytes is None else archive_bytes
    contents = validate_archive(raw, scope)
    for path in MODIFIED:
        if path in historical:
            assert historical[path] == parent['files'][path]['canonical_sha256'], 'Historical editor parent disagreement: '+path
    return scope, contents


def current_sources(parent_sources, overrides=None, *, prefix='Unreviewed current source: '):
    scope, _ = load_scope()
    expected = dict(parent_sources)
    for path, entry in scope['protected_parent'].items():
        if path in expected and entry['mode'] == 'canonical':
            assert expected[path] == entry['sha256'], 'Historical parent disagreement: '+path
        assert digest(read_source(path, overrides, prefix), entry['mode']) == entry['sha256'], prefix+path
    for path, entry in scope['candidate'].items():
        if path in MODIFIED and path in expected:
            assert expected[path] == scope['parent_archive']['files'][path]['canonical_sha256'], 'Editor scope ordering/parent mismatch: '+path
        raw = read_source(path, overrides, prefix)
        key = 'raw_sha256' if entry['mode'] == 'raw' else 'canonical_sha256'
        assert digest(raw, entry['mode']) == entry[key], prefix+path
        expected[path] = entry['canonical_sha256']
    return expected
