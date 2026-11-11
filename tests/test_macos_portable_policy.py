"""Simulated policy descriptions, NOT measurements on other Apple computers."""
from dataclasses import replace
from types import SimpleNamespace
import sys
import pytest
from emcd_sim.gui import macos_resources as mac,parallel_resources as resources,memory_budget as memory
from emcd_sim.gui.emcd_forward import ForwardSettings
from emcd_sim.gui.geometry import Settings,Structure
from emcd_sim.gui.propagation import numerical_info

HARDWARE=[('small-8GB',8,4,4,8),('medium-16GB',10,6,4,16),
          ('larger-32GB',16,12,4,32),('high-64GB',32,24,8,64),
          ('high-128GB',64,48,16,128),('unknown-topology',16,None,None,32)]


def description(row):
    name,logical,p,e,gib=row
    hw=dict(logical_cores=logical,performance_cores=p,efficiency_cores=e,physical_memory_mib=gib*1024.)
    state=dict(physical_memory_mib=gib*1024.,available_ram_mib=gib*1024*.6,
        process_rss_mib=300.,memory_pressure='normal',swap_used_mib=0.)
    return hw,state


@pytest.mark.parametrize('hardware',HARDWARE,ids=lambda r:r[0])
@pytest.mark.parametrize('method',['bloch','fft-multislice'])
@pytest.mark.parametrize('channel',['single','double'])
@pytest.mark.parametrize('size',['small','larger'])
def test_simulated_four_backend_matrix(monkeypatch,hardware,method,channel,size):
    monkeypatch.setattr(mac.sys,'platform','darwin')
    hw,state=description(hardware)
    native=dict(platform='darwin',hardware=hw,cpu_count=hw['logical_cores'],backend='Accelerate',
        threads=None,automatic_thread_control=True)
    monkeypatch.setattr(resources,'native_backend_info',lambda:native)
    monkeypatch.setattr(memory,'memory_snapshot',lambda:dict(state))
    settings=Settings(beam_cutoff=.9,potential_cutoff=1.8) if size=='small' else Settings(beam_cutoff=4.6,potential_cutoff=6.2)
    cfg=ForwardSettings(propagation=method,channeling_model=channel,grid=17 if size=='small' else 193,
        depth=9 if size=='small' else 257,fft_grid=24 if size=='small' else 48,energy_points=2)
    auto_budget=mac.auto_memory_budget(state)['effective_budget_mib']
    for mode in ('automatic','manual'):
        count=1 if channel=='single' else hw['logical_cores']
        budget=auto_budget if mode=='automatic' else int(hw['physical_memory_mib']/2)
        request=replace(cfg,worker_mode=mode,parallel_workers=count,memory_budget_mib=budget)
        info=numerical_info(Structure.nickel(),settings,request,enforce_execution=False)
        plan=info['execution'];effective=plan['effective_workers'][method]
        if mode=='manual':assert effective==count and info['memory_budget_mib']==budget
        else:
            cap=hw['performance_cores'] or hw['logical_cores']//2
            assert 1<=effective<=cap
        if channel=='single':assert effective==1
        if plan['blocked']:
            assert info['rejected'] and 'Memory admission rejected' in info['rejection_reason']
        else:
            assert info['estimated_process_peak_mib']<=min(budget,info['available_ram_limit_mib'])
            assert info['estimated_working_mib']>=0
        if size=='small':assert not plan['blocked']


@pytest.mark.parametrize('pressure',['normal','warning','critical','unavailable'])
def test_pressure_and_low_ram_rechecked_without_changing_manual_budget(monkeypatch,pressure):
    monkeypatch.setattr(mac.sys,'platform','darwin')
    _,state=description(HARDWARE[1]);state.update(available_ram_mib=2000.,memory_pressure=pressure)
    info=memory.assess_memory(10,4096,snapshot=state,reject=False)
    assert info['memory_budget_mib']==4096
    assert info.get('rejected',False)==(pressure!='normal')
    assert info['available_ram_limit_mib']<=.5*state['available_ram_mib']
    for available in (512.,128.):
        low=dict(state,available_ram_mib=available)
        assert memory.assess_memory(10,4096,snapshot=low,reject=False)['rejected']
    assert memory.assess_memory(100,128,snapshot=state,reject=False)['rejected']


def test_auto_memory_reads_new_snapshot_and_invalid_data_reject(monkeypatch):
    _,state=description(HARDWARE[1]);snapshots=iter([state,dict(state,available_ram_mib=2500.,memory_pressure='warning')])
    monkeypatch.setattr(memory,'memory_snapshot',lambda:next(snapshots))
    before=mac.auto_memory_budget();after=mac.auto_memory_budget()
    assert after['effective_budget_mib']<before['effective_budget_mib']
    for changes in ({'available_ram_mib':float('nan')},{'physical_memory_mib':-1},{'process_rss_mib':float('inf')}):
        with pytest.raises(ValueError,match='invalid'):mac.auto_memory_budget(dict(state,**changes))


def test_auto_portable_inactive_manual_count_and_available_cpu(monkeypatch):
    monkeypatch.setattr(mac.sys,'platform','darwin')
    hw,state=description(HARDWARE[0]);hw['available_logical_cores']=2
    native=dict(platform='darwin',hardware=hw,backend='Accelerate',threads=1,automatic_thread_control=True)
    cfg=ForwardSettings(channeling_model='double',grid=193,depth=257,parallel_workers=64)
    plan=resources.worker_plan(Settings(),cfg,61,native=native)
    assert plan['effective_workers']['bloch']<=2 and not plan['blocked']
    with pytest.raises(ValueError,match='1 to 8'):
        resources.worker_plan(Settings(),replace(cfg,worker_mode='manual'),61,native=native)
    missing=dict(native,hardware=None,cpu_count=2)
    assert resources.worker_plan(Settings(),cfg,61,native=missing)['manual_worker_limit']==2


def test_loaded_custom_openblas_and_guard_restoration(monkeypatch,tmp_path):
    paths=[tmp_path/'conda/lib/libopenblas.dylib',tmp_path/'custom/libscipy_openblas.dylib']
    counts=[8,3];libraries={}
    for i,path in enumerate(paths):
        libraries[str(path)]=SimpleNamespace(**{
            'openblas_get_num_threads':lambda i=i:counts[i],
            'openblas_set_num_threads':lambda value,i=i:counts.__setitem__(i,value),
            'openblas_get_parallel':lambda:1,'openblas_get_config':lambda:b'OpenBLAS simulated API'})
    monkeypatch.setattr(resources,'_loaded_openblas_paths',lambda:set(paths))
    monkeypatch.setattr(resources.ctypes,'CDLL',lambda path:libraries[path])
    monkeypatch.setattr(resources,'_accelerate_blas',lambda:None)
    monkeypatch.setattr(resources,'_declared_blas',lambda package:'openblas')
    rows=resources._blas_runtimes()
    assert len(rows)==2 and all(r[2]['backend']=='OpenBLAS' for r in rows)
    for error in (False,True):
        try:
            with resources.calculation_blas_guard():
                assert counts==[1,1]
                if error:raise RuntimeError('injected failure')
        except RuntimeError:assert error
        assert counts==[8,3]


def test_missing_accelerate_control_is_reported_not_unknown_or_unlimited(monkeypatch):
    monkeypatch.setattr(resources,'_numpy_blas',lambda:None)
    monkeypatch.setattr(resources,'_accelerate_blas',lambda:None)
    monkeypatch.setattr(resources,'_loaded_openblas_paths',lambda:set())
    monkeypatch.setattr(resources,'_declared_blas',lambda package:'accelerate')
    with monkeypatch.context() as m:
        m.setitem(sys.modules,'threadpoolctl',None)
        info=resources.native_backend_info()
    assert info['backend']=='Accelerate' and info['threads'] is None
    assert not info['automatic_thread_control'] and 'macOS 15+' in info['thread_control_unavailable_reason']
    plan=resources.worker_plan(Settings(),ForwardSettings(),21,native=info)
    assert plan['blocked'] and any('capability restriction' in text for text in plan['messages'])
    with pytest.raises(ValueError,match='thread control is unavailable'):
        with resources.calculation_blas_guard():pytest.fail('Uncontrolled dispatch')
