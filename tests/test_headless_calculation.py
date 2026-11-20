"""Real canonical calculations with presentation imports forbidden at runtime.

Reuse the established Ni archived-kernel comparison and Cr independent-event
assertions. The Cr case is the existing synthetic ordered BCC benchmark, not a
claim to describe bulk Cr spin-density-wave order or calibrated spectroscopy.
"""
import importlib.abc
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

import pytest


ROOT = Path(__file__).resolve().parents[1]
PRESENTATION = {
    'app', 'atomic_editor', 'calculation_comparison', 'calculation_controls',
    'calculation_worker', 'cancellation_acceptance', 'compare_results',
    'compute_resources', 'desktop_acceptance', 'group_mdff', 'group_mdff_controls',
    'imported_tensor_ui', 'manual_l23_editor', 'mdff_usability', 'mdff_workspace',
    'normalization_controls', 'numerical_settings', 'parallel_acceptance',
    'parameter_wheel', 'prb_controls', 'project_session', 'provider_ui',
    'responsive', 'results', 'results_browser', 'result_presentation',
    'saved_atomic_ui', 'site_group_editor', 'structure_viewer',
    'tensor_spectrum_preview', 'unified_elastic_acceptance', 'xmcd_preview',
}


def forbidden(name):
    return (name.split('.')[0] in {'PySide6', 'PySide2', 'PyQt6', 'PyQt5'}
            or (name.startswith('matplotlib.backends.') and 'qt' in name.lower())
            or any(name == 'emcd_sim.gui.' + module
                   or name.startswith('emcd_sim.gui.' + module + '.')
                   for module in PRESENTATION))


@pytest.mark.parametrize('material', ['Ni', 'Cr'])
@pytest.mark.parametrize('method', ['bloch', 'fft-multislice'])
@pytest.mark.parametrize('channel', ['single', 'double'])
def test_canonical_calculation_without_presentation(tmp_path, material, method, channel):
    env = dict(os.environ)
    env.pop('QT_QPA_PLATFORM', None)
    env['PYTHONPATH'] = os.pathsep.join((str(ROOT / 'src'), str(ROOT / 'tests')))
    command = [sys.executable, '-X', 'utf8', '-B', str(Path(__file__).resolve()),
               material, method, channel, str(tmp_path)]
    child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, encoding='utf-8')
    try:
        output, _ = child.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        # Own only this child and its descendants, including any executor.
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            child.kill()
        output, _ = child.communicate()
        pytest.fail('Headless calculation timed out: ' + output[-4000:])
    assert child.returncode == 0, output[-6000:]
    assert 'HEADLESS CALCULATION PASSED' in output


def _verify_result(result, method, channel, source_paths):
    import hashlib
    import numpy as np

    assert set(result['methods']) == {method}
    entry = result['methods'][method]
    cfg, meta = entry['config'], entry['metadata']
    assert cfg.propagation == method and cfg.channeling_model == channel
    assert meta['channeling_model'] == channel
    assert method in meta['solver'] and channel in meta['solver'].lower()
    energy = entry['spectra']['energy_ev']
    assert energy.ndim == 1 and len(energy) >= 2
    assert np.isfinite(energy).all() and (np.diff(energy) > 0).all()
    assert entry['qx'].shape == entry['qy'].shape == (cfg.grid, cfg.grid)
    assert set(entry['weights']) == {'A', 'B'}
    for weights in entry['weights'].values():
        assert weights.shape == (cfg.grid, cfg.grid)
        assert np.isfinite(weights).all() and weights.sum() > 0
    beams = len(meta['beam_hkl'])
    assert entry['amplitudes'].shape == (cfg.depth, beams)
    assert entry['coherence'].shape == (beams, beams)
    assert np.isfinite(entry['amplitudes']).all()
    assert np.isfinite(entry['coherence']).all()
    for value in entry['spectra'].values():
        assert value.shape == energy.shape and np.isfinite(value).all()
    raw_maps = {'I_plus', 'I_minus', 'I_mag', 'I_nonmag'}
    for fields in entry['maps'].values():
        for key, value in fields.items():
            assert value.shape == (cfg.grid, cfg.grid)
            expected = np.ones(value.shape, bool) if key in raw_maps else entry['weights']['A'] > 0
            np.testing.assert_array_equal(np.isfinite(value), expected)
            assert not np.isinf(value).any()
    # Check existing provenance, without introducing new frozen identities.
    assert meta['physics_convention'] and meta['software_commit']
    serialized = json.dumps(meta, default=str)
    for path in source_paths:
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() in serialized
    owner = ROOT / 'src/emcd_sim/gui/channeling.py'
    assert meta['implementation_sha256']['channeling.py'] == hashlib.sha256(owner.read_bytes()).hexdigest()


def _child(material, method, channel, directory):
    attempts = []

    class RejectPresentation(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if forbidden(fullname):
                attempts.append(fullname)
                raise AssertionError('Presentation import during calculation: ' + fullname)

    assert 'QT_QPA_PLATFORM' not in os.environ
    assert not any(forbidden(name) for name in sys.modules)
    sys.meta_path.insert(0, RejectPresentation())
    import multiprocessing
    import numpy as np
    from unittest.mock import patch
    from emcd_sim.gui import channeling, forward_pipeline, memory_budget

    before_threads = set(threading.enumerate())
    assert not memory_budget._reservations
    if material == 'Ni':
        from emcd_sim.gui.forward_settings import NiForwardSettings
        from emcd_sim.gui.geometry import Structure, Settings
        from test_single_element_ni_compatibility import old_contract
        from numerical_roundoff import assert_bloch_observables

        settings = Settings(thickness=.3, beam_cutoff=.9, potential_cutoff=1.8)
        cfg = NiForwardSettings(model='xmcd', axis_declared=True,
            channeling_model=channel, propagation=method, energy_scope='edges',
            grid=9, depth=9, subpixels=8, fft_grid=16, slice_step=.01, halfwidth=.7,
            centers=((.2, .2), (.2, -.2)), radius=.12, correction=False,
            worker_mode='manual', parallel_workers=1)
        result = forward_pipeline.calculate(Structure.nickel(), settings, cfg)
        _verify_result(result, method, channel, [cfg.source])
        # Existing authenticated historical source and established roundoff
        # contract; original references, equations and tolerances are reused.
        with patch.object(channeling, 'calculate_detector_signals', old_contract.__wrapped__()):
            reference = forward_pipeline.calculate(Structure.nickel(), settings, cfg)
        a, b = result['methods'][method], reference['methods'][method]
        for key in ('amplitudes', 'coherence', 'depth_nm', 'qx', 'qy'):
            np.testing.assert_array_equal(a[key], b[key])
        if method == 'bloch' and channel == 'double':
            assert_bloch_observables(a, b, cfg)
        else:
            for key in a['spectra']:
                np.testing.assert_array_equal(a['spectra'][key], b['spectra'][key])
            for label, fields in a['maps'].items():
                for key, value in fields.items():
                    np.testing.assert_array_equal(value, b['maps'][label][key])
    else:
        import test_multisite_scientific_validation as scientific
        calculate = scientific.calculate
        completed = []

        def checked(*args, **kwargs):
            result = calculate(*args, **kwargs)
            sites = kwargs['sites']
            assert [g.indices for g in sites.groups] == [(0,), (1,)]
            assert [g.magnetization for g in sites.groups] == [(0, 0, 1), (0, 0, -1)]
            _verify_result(result, method, channel,
                           [g.mdff_reference.source for g in sites.groups])
            assert set(result['groups']) == {'up', 'down'}
            assert result['metadata']['multisite']['selected_atom_count'] == 2
            completed.append(result)
            return result

        # Run the existing independent-event, normalization and reversal
        # assertions in the blocked process, including the unequal MDFF case.
        with patch.object(scientific, 'calculate', checked):
            scientific.test_bcc_cr_independent_events_and_symmetry(
                Path(directory), method, channel, True)
        assert len(completed) == 2
    assert not attempts
    assert not any(forbidden(name) for name in sys.modules)
    assert not memory_budget._reservations
    assert not multiprocessing.active_children()
    assert set(threading.enumerate()) == before_threads
    assert channeling._windows_bw_lock.acquire(blocking=False)
    channeling._windows_bw_lock.release()
    print('HEADLESS CALCULATION PASSED', material, method, channel)


if __name__ == '__main__':
    _child(*sys.argv[1:])
