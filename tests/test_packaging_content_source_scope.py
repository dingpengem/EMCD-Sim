"""Positive-first target-specific mutations for the additive packaging boundary."""
from pathlib import Path
import pytest
import packaging_content_source_scope as scope
import mdff_editor_source_scope as editor
import physics_source_guard as physics
import unit_source_snapshots as units
from mdff_usability_source_scope import packaging_parent_scope

ROOT = Path(__file__).resolve().parents[1]


def positive():
    units.assert_reviewed_current_sources()
    physics.assert_registered_sources()
    packaging_parent_scope()


@pytest.mark.parametrize('path', [*scope.MODIFIED,
    'packaging/check_package_contents.py',
    'packaging/assets/examples/Fe_BCC_a2.8665.cif',
    'packaging/assets/examples/Ni_FCC_a3.52.cif',
    'packaging/assets/qt-licenses/qtvirtualkeyboard-NOTICES.txt',
    'packaging/assets/qt-licenses/qtpdf-6.140.0-upstream.zip',
    scope.MANIFEST_PATH, scope.ARCHIVE_PATH,
    'src/emcd_sim/double_channeling.py',
    'tests/fixtures/generalized_mdff_editor_scope_v1.json',
])
def test_additive_scope_rejects_target_mutation(path):
    positive()
    original = (ROOT/path).read_bytes()
    overrides = {path: original+b'\nunauthorized packaging mutation\n'}
    with pytest.raises(AssertionError, match=__import__('re').escape(path)):
        # Original evidence has its own explicit byte-injection API below.
        if path == editor.MANIFEST_PATH:
            editor.load_scope(manifest_bytes=overrides[path])
        else:
            units.assert_reviewed_current_sources(overrides)
    positive()


def test_historical_editor_maps_and_archive_are_still_independent():
    positive()
    historical, archive = editor.load_scope()
    amended = packaging_parent_scope()
    assert len(historical['candidate']) == 18 and len(historical['protected_parent']) == 93
    assert set(archive) == set(editor.MODIFIED)
    assert set(amended['modified']) & set(historical['candidate']) == {'packaging/emcd_gui.spec'}
    assert set(amended['modified']) & set(historical['protected_parent']) == {
        'packaging/BETA_README.txt', 'packaging/README.md', 'packaging/build_windows.ps1'}


def test_packaging_scope_cannot_authorize_a_kernel_even_with_new_manifest_pin(monkeypatch):
    import json
    positive()
    candidate = json.loads((ROOT/scope.MANIFEST_PATH).read_bytes())
    candidate['added']['src/emcd_sim/double_channeling.py'] = candidate['added']['packaging/check_package_contents.py']
    raw = json.dumps(candidate).encode()
    monkeypatch.setattr(scope, 'MANIFEST_SHA256', scope.digest(raw))
    with pytest.raises(AssertionError, match='Unauthorized packaging additions'):
        scope.load(ROOT, {scope.MANIFEST_PATH: raw})
