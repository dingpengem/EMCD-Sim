"""Required packaging bytes, provenance coverage and real application CIF loading."""
import importlib.util
import json
from pathlib import Path
import shutil
import zipfile
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('emcd_package_check', ROOT/'packaging/check_package_contents.py')
content = importlib.util.module_from_spec(spec)
spec.loader.exec_module(content)


def test_positive_content_and_upstream_provenance():
    entries = content.inputs()
    assert len(entries) >= 26
    provenance = json.loads((ROOT/'packaging/assets/qt-licenses/upstream-provenance.json').read_bytes())
    assert provenance['qt_version'] == '6.12.0' and provenance['pdf_version'] == '6.140.0'
    seen = set()
    for record in provenance['records']:
        assert record['url'].startswith(('https://raw.githubusercontent.com/qt/',
                                        'https://raw.githubusercontent.com/qtproject/',
                                        'https://api.github.com/repos/qt/',
                                        'https://api.github.com/repos/qtproject/',
                                        'https://doc.qt.io/'))
        with zipfile.ZipFile(ROOT/'packaging/assets/qt-licenses'/record['archive']) as archive:
            raw = archive.read(record['member'])
        assert len(raw) == record['bytes'] and content.sha(raw) == record['sha256']
        assert (record['archive'], record['member']) not in seen
        seen.add((record['archive'], record['member']))
    assert len(seen) == 302
    components = json.loads((ROOT/'packaging/assets/bundled-qt-components.json').read_bytes())
    assert len(components['components']) == 34 and len(components['wheel_provenance']) == 6
    for component in components['components']:
        assert component['notice_assets'] and component['license_options']
        assert all(path in entries for path in component['notice_assets'])
    assert len(components['translations']) == 99
    for catalog in components['translations']:
        assert all(path in entries for path in catalog['notice_assets'])
    translations = json.loads((ROOT/'packaging/assets/qt-licenses/qttranslations-provenance.json').read_bytes())
    assert translations['version'] == '6.12.0' and len(translations['records']) == 104
    with zipfile.ZipFile(ROOT/'packaging/assets/qt-licenses/qttranslations-upstream.zip') as archive:
        assert set(archive.namelist()) == {r['member'] for r in translations['records']}
        for record in translations['records']:
            assert content.sha(archive.read(record['member'])) == record['sha256']


@pytest.mark.skipif(__import__('sys').platform != 'win32', reason='Windows PE packaging')
def test_staged_numpy_imports_use_system_runtime_without_code_changes(tmp_path):
    import pefile
    import numpy
    spec = importlib.util.spec_from_file_location('windows_dependencies', ROOT/'packaging/windows_dependencies.py')
    deps = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(deps)
    numpy_root = Path(numpy.__file__).parent
    extensions = [next((numpy_root/subdir).glob(stem+'*.pyd')) for subdir, stem in
                  [('_core', '_multiarray_umath'), ('fft', '_pocketfft_umath')]]
    for original in extensions:
        before = original.read_bytes()
        target, changes = deps.normalize_runtime_imports(original, tmp_path/original.name)
        assert changes and all(new == 'msvcp140.dll' for old, new in changes)
        assert original.read_bytes() == before
        with pefile.PE(target) as revised, pefile.PE(data=before) as previous:
            assert b'msvcp140.dll' in [e.dll for e in revised.DIRECTORY_ENTRY_IMPORT]
            assert not any(b'msvcp140-' in e.dll for e in revised.DIRECTORY_ENTRY_IMPORT)
            for section in previous.sections:
                if section.Characteristics & 0x20000000:
                    start, size = section.PointerToRawData, section.SizeOfRawData
                    assert Path(target).read_bytes()[start:start+size] == before[start:start+size]
    entries = [(name, str(tmp_path/name), 'BINARY') for name in
               ['VCRUNTIME140.dll', 'numpy.libs/msvcp140-abc.dll', 'PySide6/Qt6Pdf.dll',
                'PySide6/plugins/imageformats/qpdf.dll', 'PySide6/Qt6Core.dll']]
    kept, deployment = deps.prepare_binaries(entries, tmp_path)
    assert [entry[0] for entry in kept] == ['PySide6/Qt6Core.dll']
    assert len(deployment['omitted']) == 4


@pytest.mark.parametrize('path', sorted(content.inputs()))
def test_required_asset_absence_rejected_after_positive_control(tmp_path, path):
    shutil.copytree(ROOT/'packaging/assets', tmp_path/'packaging/assets')
    content.inputs(tmp_path)
    original = (tmp_path/path).read_bytes()
    (tmp_path/path).unlink()
    with pytest.raises(ValueError, match=__import__('re').escape(path)):
        content.inputs(tmp_path)
    (tmp_path/path).write_bytes(original)
    content.inputs(tmp_path)


@pytest.mark.parametrize('name,element,a,positions', [
    ('Fe_BCC_a2.8665.cif', 'Fe', 2.8665, [(0,0,0),(.5,.5,.5)]),
    ('Ni_FCC_a3.52.cif', 'Ni', 3.52, [(0,0,0),(0,.5,.5),(.5,0,.5),(.5,.5,0)]),
])
def test_packaged_cif_uses_application_loader(name, element, a, positions):
    from emcd_sim.gui.geometry import Structure
    atoms = Structure.from_cif(ROOT/'packaging/assets/examples'/name).atoms
    assert atoms.get_chemical_symbols() == [element]*len(positions)
    np.testing.assert_allclose(atoms.cell.array, np.eye(3)*a, rtol=0, atol=1e-12)
    assert sorted(map(tuple, np.round(atoms.get_scaled_positions()%1,12))) == sorted(positions)


def test_manifest_is_not_its_own_trust_anchor(tmp_path):
    shutil.copytree(ROOT/'packaging/assets', tmp_path/'packaging/assets')
    content.inputs(tmp_path)
    file = tmp_path/'packaging/assets/examples/Fe_BCC_a2.8665.cif'
    file.write_bytes(file.read_bytes()+b'\n')
    manifest = tmp_path/content.MANIFEST
    changed = json.loads(manifest.read_bytes())
    changed['files']['packaging/assets/examples/Fe_BCC_a2.8665.cif']['sha256'] = content.sha(file.read_bytes())
    manifest.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match='required-content.json'):
        content.inputs(tmp_path)
