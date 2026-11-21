"""Serializable calculation inputs and the explicit historical Ni preset.

NiForwardSettings records the established Ni example defaults. It supplies
explicit inputs to the common forward_pipeline.calculate engine; it is not a
generic material fallback. Source-backed and multisite settings share the
neutral ForwardSettings base, retaining serialized field names for project IO.
"""
from dataclasses import dataclass, field
from .historical_ni import NiLocalConfig
from emcd_sim.provenance import reference_source

DEFAULT_NI_SOURCE = reference_source()


@dataclass(frozen=True)
class ForwardSettings:
    """Material-neutral numerical controls and explicitly supplied response inputs.

    Detector centers/radius are cycles/Angstrom, energies are eV, slice_step
    is nm and memory_budget_mib is MiB. A source/provider or sites, selected
    energies and detector geometry must be supplied before calculation.
    Geometry/beam energy/depth belong to structure_geometry.Settings.
    """
    model: str=''
    source: str=''
    source_sha256: str=''
    axis_declared: bool=False
    magnetization: tuple=(0.,0.,1.)
    eta: float=1.
    beta: float=1.
    l3: float=float('nan')
    l2: float=float('nan')
    atomic: NiLocalConfig|None=None
    sigma: float=.8
    radial: float|None=None
    energy_points: int=241
    grid: int=97
    depth: int=64
    subpixels: int=64
    halfwidth: float=1.
    centers: tuple=()
    radius: float=0.
    correction: bool=False
    window: tuple=()
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
        from emcd_sim.memory_budget import resource_budget
        return resource_budget(self)


@dataclass(frozen=True)
class NiForwardSettings(ForwardSettings):
    """Explicit historical Ni preset; old defaults and saved field order retained."""
    model: str='xmcd'
    source: str=str(DEFAULT_NI_SOURCE)
    l3: float=831.271
    l2: float=848.698
    atomic: NiLocalConfig=field(default_factory=NiLocalConfig)
    centers: tuple=((.2837684449489217,.2837684449489217),(.2837684449489217,-.2837684449489217))
    radius: float=.0908059024
    correction: bool=True
    window: tuple=(878.,882.)


@dataclass(frozen=True)
class MultiSiteForwardSettings(ForwardSettings):
    """Numerical/detector controls for the programmatic multi-site entry point.

    MDFF declarations belong exclusively to each site's provider reference.
    selected_edges optionally names exact map energies on the requested grid;
    otherwise use source selections present on that grid (or its endpoints).
    Post-edge correction is outside this entry point's current scope.
    """
    model: str = 'multisite'
    selected_edges: tuple = ()
