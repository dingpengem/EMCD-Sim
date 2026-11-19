"""Serializable calculation inputs and the explicit historical Ni preset.

NiForwardSettings records the established Ni example defaults. It supplies
explicit inputs to the common forward_pipeline.calculate engine; it is not a
generic material fallback. Source-backed and multisite settings override its
material declaration, retaining historical serialized fields for project IO.
"""
from dataclasses import dataclass, field
from ..historical_ni import NiLocalConfig
from .runtime import reference_source

DEFAULT_NI_SOURCE = reference_source()


@dataclass(frozen=True)
class NiForwardSettings:
    """Historical Ni material preset, detector geometry and numerical requests.

    Source fields/atomic parameters describe the target response; propagation
    and channeling_model select existing elastic/inelastic approximations.
    centers/radius/halfwidth are cycles/Angstrom, energy values are eV,
    slice_step is nm and memory_budget_mib is MiB. Geometry/beam energy/depth
    belong to gui.geometry.Settings. Defaults and serialized field names are
    retained, including historical Ni compatibility inputs.
    """
    model: str='xmcd'
    source: str=str(DEFAULT_NI_SOURCE)
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


@dataclass(frozen=True)
class MultiSiteForwardSettings(NiForwardSettings):
    """Numerical/detector controls for the programmatic multi-site entry point.

    MDFF declarations belong exclusively to each site's provider reference.
    selected_edges optionally names exact map energies on the requested grid;
    otherwise use source selections present on that grid (or its endpoints).
    Post-edge correction is outside this entry point's current scope.
    """
    model: str = 'multisite'
    source: str = ''
    source_sha256: str = ''
    correction: bool = False
    l3: float = float('nan')
    l2: float = float('nan')
    selected_edges: tuple = ()
