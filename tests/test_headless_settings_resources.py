"""Fresh-process settings/resource behavior and the pinned-import state bridge."""
from emcd_sim.study_presets import nickel_geometry_settings
import importlib.abc
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('mode', ['settings', 'resources', 'kernel_bridge'])
def test_headless_settings_and_resources(tmp_path, mode):
    env = dict(os.environ)
    env.pop('QT_QPA_PLATFORM', None)
    env['PYTHONPATH'] = os.pathsep.join((str(ROOT/'src'), str(ROOT/'tests')))
    child = subprocess.Popen([sys.executable, '-X', 'utf8', '-B',
        str(Path(__file__).resolve()), mode, str(tmp_path)], cwd=ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
    try:
        output, _ = child.communicate(timeout=90)
    except subprocess.TimeoutExpired:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            child.kill()
        output, _ = child.communicate()
        pytest.fail('Owned resource test timed out: '+output[-4000:])
    assert child.returncode == 0, output[-6000:]
    assert 'HEADLESS SETTINGS/RESOURCES PASSED' in output


def _child(mode, directory):
    from test_headless_calculation import forbidden
    attempts = []
    allowed = {'emcd_sim.gui', 'emcd_sim.gui.memory_budget'} if mode == 'kernel_bridge' else set()

    class RejectGUI(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path=None, target=None):
            if forbidden(name) or ((name == 'emcd_sim.gui' or name.startswith('emcd_sim.gui.')) and name not in allowed):
                attempts.append(name)
                raise AssertionError('Unexpected GUI import: '+name)

    sys.meta_path.insert(0, RejectGUI())
    assert 'QT_QPA_PLATFORM' not in os.environ
    import json
    import threading
    from dataclasses import asdict, fields, replace
    from emcd_sim import memory_budget as memory
    from emcd_sim.forward_settings import ForwardSettings, NiForwardSettings, MultiSiteForwardSettings
    from emcd_sim.material_inputs import ImportedSettings, ProviderSettings
    from emcd_sim import mdff_providers

    threads = set(threading.enumerate())
    assert not memory._reservations
    if mode == 'settings':
        assert mdff_providers.NiForwardSettings is NiForwardSettings
        assert mdff_providers.ImportedSettings is ImportedSettings
        assert mdff_providers.ProviderSettings is ProviderSettings
        assert issubclass(MultiSiteForwardSettings, ForwardSettings)
        assert issubclass(ProviderSettings, ImportedSettings)
        assert issubclass(ImportedSettings, ForwardSettings)
        for cls in (MultiSiteForwardSettings, ImportedSettings, ProviderSettings):
            assert not issubclass(cls, NiForwardSettings)
            general = cls()
            assert general.atomic is None and not general.source
            assert not general.centers and not general.window
        first, second = NiForwardSettings(), NiForwardSettings()
        assert first.atomic is not second.atomic
        for cls in (NiForwardSettings, MultiSiteForwardSettings, ImportedSettings, ProviderSettings):
            record = cls()
            payload = asdict(record)
            assert list(payload) == [field.name for field in fields(cls)]
            assert json.loads(json.dumps(payload))['memory_budget_mib'] == 2048
            assert record.resource_allocation is None
            resolved = replace(record, resource_allocation={'memory_budget_mib':512})
            assert resolved.calculation_memory_budget_mib == 512
            assert resolved.memory_budget_mib == 2048
            assert record.calculation_memory_budget_mib == 2048
        from single_element_helpers import write_source
        source = write_source(Path(directory)/'Fe.json', element='Fe')
        cfg = mdff_providers.settings_for_source(source)
        assert type(cfg) is ImportedSettings and cfg.ionizing_element == 'Fe'
        assert mdff_providers.prepare_provider(cfg).declared
        with pytest.raises(ValueError):
            mdff_providers.source_for(replace(cfg, source_sha256='0'*64))
        with pytest.raises(ValueError):
            mdff_providers.load_provider(ProviderSettings(provider_schema=99))
    elif mode == 'resources':
        from emcd_sim import hardware_resources as hardware, parallel_resources as policy
        from emcd_sim.structure_geometry import Settings
        real = memory.memory_snapshot()
        assert real['available_ram_mib'] > 0 and real['process_rss_mib'] > 0
        # Established controlled-memory fixture; no physical parameters invented.
        memory.memory_snapshot = lambda: dict(available_ram_mib=32768., process_rss_mib=64.)
        assert not memory.assess_memory(32,512).get('rejected',False)
        with memory.reserve_memory(32,512):
            with memory.reserve_memory(16,512):
                assert len(memory._reservations) == 2
                assert memory.assess_memory(1,512)['concurrent_calculations'] == 2
        assert not memory._reservations
        with pytest.raises(ValueError, match='Memory admission rejected'):
            memory.assess_memory(512,512)
        from emcd_sim.cancellation import Cancelled
        for exception in (Cancelled(), RuntimeError('owned resource failure')):
            with pytest.raises(type(exception)):
                with memory.reserve_memory(32,512):
                    raise exception
            assert not memory._reservations
        with pytest.raises(ValueError, match='Memory allocation failed'):
            with memory.reserve_memory(32,512):
                raise MemoryError('owned allocation failure')
        assert not memory._reservations
        state = hardware.hardware_snapshot()
        native = policy.native_backend_info(hardware=state)
        settings = nickel_geometry_settings(thickness=.3,beam_cutoff=.9,potential_cutoff=1.8)
        cfg = NiForwardSettings(propagation='fft-multislice',channeling_model='double',
            worker_mode='manual',parallel_workers=1,grid=9,depth=9,fft_grid=16)
        manual = policy.worker_plan(settings,cfg,5,native=native,hardware=state)
        assert manual['effective_workers']['fft-multislice'] == 1 and not manual['blocked']
        auto = policy.worker_plan(settings,replace(cfg,worker_mode='automatic'),5,native=native,hardware=state)
        assert auto['effective_workers']['fft-multislice'] >= 1 and not auto['blocked']
        with pytest.raises(ValueError):
            policy.worker_plan(settings,replace(cfg,parallel_workers=0),5,native=native,hardware=state)
    else:
        from emcd_sim.gui import memory_budget as compatibility
        from emcd_sim import double_channeling as bw, multislice_double_channeling as ms
        assert compatibility.reserve_memory is bw.reserve_memory is ms.reserve_memory is memory.reserve_memory
        assert not hasattr(compatibility,'_reservations') and not hasattr(compatibility,'_lock')
        assert bw.reserve_memory.__wrapped__.__globals__['_reservations'] is memory._reservations
        assert ms.reserve_memory.__wrapped__.__globals__['_lock'] is memory._lock
        memory.memory_snapshot = lambda: dict(available_ram_mib=32768., process_rss_mib=64.)
        with bw.reserve_memory(32,512):
            assert len(memory._reservations) == 1
            with ms.reserve_memory(16,512):
                assert len(memory._reservations) == 2
                assert memory.assess_memory(1,512)['concurrent_reserved_working_mib'] == 48
        assert not memory._reservations
    assert not attempts
    assert not memory._reservations
    assert set(threading.enumerate()) == threads
    assert not any((n == 'emcd_sim.gui' or n.startswith('emcd_sim.gui.')) and n not in allowed for n in sys.modules)
    print('HEADLESS SETTINGS/RESOURCES PASSED',mode)


if __name__ == '__main__':
    _child(*sys.argv[1:])
