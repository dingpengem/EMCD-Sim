"""Forward input settings and the supported single-provider calculation API.

calculate admits existing resource requests then delegates to forward_pipeline.
Material construction remains in providers; propagation and detector signals
have separate owners. Historical tensor/energy/orientation and export imports
remain aliases for saved projects, scripts and the public calculation surface.
"""
from dataclasses import dataclass, replace, field
from pathlib import Path
import numpy as np
from ..historical_ni import NiLocalConfig
from ..wien2k_xmcd import load_wien2k_xmcd

from .runtime import reference_source

DEFAULT_SOURCE = reference_source()


def inspect_source(path):
    """Basic import is independent of optional original WIEN2k companion audit."""
    s=load_wien2k_xmcd(path); n=s.nonmagnetic
    maxima=np.flatnonzero((n[1:-1]>n[:-2]) & (n[1:-1]>=n[2:]))+1
    peaks=[]
    for i in sorted(maxima,key=lambda i:n[i],reverse=True):
        if all(abs(s.energy_ev[i]-s.energy_ev[j])>8 for j in peaks):peaks.append(i)
        if len(peaks)==2:break
    selected=None
    if len(peaks)==2:
        selected={}
        for edge,i in zip(('L3','L2'),sorted(peaks)):
            ix=np.flatnonzero(abs(s.energy_ev-s.energy_ev[i])<=3)
            selected[edge]=float(s.energy_ev[ix[np.argmax(abs(s.dichroic[ix]))]])
    info=dict(sha256=s.source_sha256,bounds=[float(s.energy_ev[0]),float(s.energy_ev[-1])],
              selected=selected,provenance='Five-column validated. User must declare source magnetic axis, RP/LP convention and edge assignment.',audit=None)
    suffixes=('raw1','raw2','broad1','broad2','rawxmcd','inso','injoint','inc')
    if Path(path).resolve()==DEFAULT_SOURCE.resolve() and all(Path(path).with_suffix('.'+k).exists() for k in suffixes):
        from ..wien2k_source_audit import energy_audit
        info['audit']=energy_audit(path);info['selected']=info['audit']['selected_magnetic_energies_ev']
        info['provenance']='Original Ni companion audit passed; cubic [001], native unshifted L3/L2.'
    return info


@dataclass(frozen=True)
class ForwardSettings:
    """Existing material declaration, detector geometry and numerical requests.

    Source fields/atomic parameters describe the target response; propagation
    and channeling_model select existing elastic/inelastic approximations.
    centers/radius/halfwidth are cycles/Angstrom, energy values are eV,
    slice_step is nm and memory_budget_mib is MiB. Geometry/beam energy/depth
    belong to gui.geometry.Settings. Defaults and serialized field names are
    retained, including historical Ni compatibility inputs.
    """
    model: str='xmcd'
    source: str=str(DEFAULT_SOURCE)
    source_sha256: str=''
    axis_declared: bool=False
    magnetization: tuple=(0.,0.,1.)
    eta: float=1.
    beta: float=1.
    l3: float=831.271
    l2: float=848.698
    atomic: NiLocalConfig=field(default_factory=NiLocalConfig)
    sigma: float=.8
    radial: float|None=None
    energy_points: int=241
    grid: int=97
    depth: int=64
    subpixels: int=64
    halfwidth: float=1.
    centers: tuple=((.2837684449489217,.2837684449489217),(.2837684449489217,-.2837684449489217))
    radius: float=.0908059024
    correction: bool=True
    window: tuple=(878.,882.)
    propagation: str='bloch'
    fft_grid: int=32
    slice_step: float=2.
    memory_budget_mib: int=2048
    # Missing fields in historical projects retain their explicit fixed budget.
    memory_mode: str='manual'
    resource_allocation: dict|None=None
    channeling_model: str='single'
    energy_scope: str='full'
    energy_sampling: str='uniform'
    angular_maps: bool=True
    angular_evaluation: str='selected'
    systematic_row: bool=False
    worker_mode: str='automatic'
    parallel_workers: int=1
    fft_generators: tuple|None=None

    @property
    def calculation_memory_budget_mib(self):
        from .memory_budget import resource_budget
        return resource_budget(self)


# Historical imports remain aliases, not additional forward implementations.
from ..historical_ni import material_reason, tensors, energy_grid
from ..mdff_orientation import axis_rotation


from ..cancellation import Cancelled, check_cancelled


def calculate(structure,settings,cfg,progress=lambda s:None,cancelled=lambda:False,*,energy_ev=None,energy_checkpoint=None,execution_policy=None):
    check_cancelled(cancelled)
    if execution_policy is None:cfg=replace(cfg,resource_allocation=None)
    from .forward_pipeline import validate_before_resources
    validate_before_resources(structure,settings,cfg,energy_ev)
    from .propagation import numerical_info,resolve_fft_configuration
    cfg=resolve_fft_configuration(structure,settings,cfg)
    from .memory_budget import reserve_memory
    from ..mdff_providers import prepare_provider
    from .provider_preparation import provider_energy_grid
    actual_energy=provider_energy_grid(prepare_provider(cfg),cfg,energy_ev)
    info=numerical_info(structure,settings,replace(cfg,energy_points=len(actual_energy)))
    if execution_policy is not None and execution_policy['effective_workers']!=info['execution']['effective_workers']:
        raise ValueError('Resources changed since preflight; Run again to review the new effective worker counts.')
    execution_policy=info['execution']
    from .parallel_resources import bind_allocation
    cfg=bind_allocation(cfg,info)
    check_cancelled(cancelled)
    # Double kernels make their own concurrent reservations. Reserve retained
    # GUI arrays here, after admitting the complete estimated working set.
    reserved=info['retained_results_working_mib'] if cfg.channeling_model=='double' else info['estimated_working_mib']
    with reserve_memory(reserved,cfg.calculation_memory_budget_mib,dense_mib=info['dense_working_estimate_mib']) as admission:
        result=_calculate(structure,settings,cfg,progress,cancelled,energy_ev=energy_ev,energy_checkpoint=energy_checkpoint,execution_policy=execution_policy)
        result['metadata']['execution']=execution_policy
        check_cancelled(cancelled)
        result['metadata']['memory_admission']=admission
        for r in result['methods'].values():r['metadata']['memory_admission']=admission
        return result


def _calculate(structure,settings,cfg,progress,cancelled,*,energy_ev=None,energy_checkpoint=None,execution_policy=None):
    """Historical API delegates to the common production orchestration."""
    from .forward_pipeline import calculate_prepared
    return calculate_prepared(structure,settings,cfg,progress,cancelled,energy_ev=energy_ev,
        energy_checkpoint=energy_checkpoint,execution_policy=execution_policy)


# Supported historical imports delegate to the result owner.
from .forward_results import (assemble_forward_result,
    selected_edge_metrics as metrics, export_method_result as _export_single,
    export_result)


def _contract(structure,settings,cfg,model,R,hkl,g,memory,z,psi,C,energy,ts,stage,cancelled,*,prepared):
    """Compatibility for the former result assembler; no numerical contraction.

    ts/cancelled remain only to preserve the previous private call signature.
    """
    return assemble_forward_result(structure,settings,cfg,model,R,hkl,g,memory,z,psi,C,energy,stage,prepared=prepared)
