"""Historical Ni input/provider compatibility and CLI; no duplicate numerical loop.

NO DFT is performed. The orbital forms are normalized screened-hydrogenic
2p and 3d orbitals with user-supplied effective nuclear charges, a cubic
crystal-field splitting, exchange energy and hole populations. Core spin-orbit
angular states and complex dipole phases are calculated from angular algebra.

NOT an atomic multiplet/charge-transfer solver; neither Ni bands nor many-body
2p^5 3d^(n+1) states nor Ni absolute MDFF are predicted by this model.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from .mdff_tensor import TransitionDataset, DipoleTensor, dipole_tensor_from_transitions
from .wien2k_xmcd import load_wien2k_xmcd
from .xmcd_effective_mdff import effective_tensor_from_xmcd
from .ionization_sites import single_site_phase_matrix
from .mdff_orientation import axis_rotation
from .atomic_dipole import hydrogenic_radial_dipole_angstrom, radial_dipole_from_table


@dataclass(frozen=True)
class NiLocalConfig:
    """All material-dependent inputs are illustrative, *not Ni fitted data*."""
    l3_ev: float = 852.7
    l2_ev: float = 870.0
    zeff_2p: float = 25.0
    zeff_3d: float = 9.0
    crystal_field_10dq_ev: float = 0.8
    exchange_split_ev: float = 0.2
    eg_up_holes: float = 0.20
    eg_down_holes: float = 0.40
    t2g_up_holes: float = 0.20
    t2g_down_holes: float = 0.40

    def validate(self) -> None:
        values = np.asarray(list(asdict(self).values()), dtype=float)
        if not np.all(np.isfinite(values)) or not np.all(values[:4] > 0):
            raise ValueError("edge energies/effective charges must be positive finite; all fields finite")
        if self.l3_ev >= self.l2_ev:
            raise ValueError("L3 edge must be below L2")
        if self.crystal_field_10dq_ev < 0 or self.exchange_split_ev < 0:
            raise ValueError("crystal-field/exchange splittings must be nonnegative")
        holes = values[-4:]
        if not np.all((0 <= holes) & (holes <= 1)) or not np.any(holes > 0):
            raise ValueError("orbital/spin hole weights must be in [0,1] and nonzero")


def ni_local_transitions(config: NiLocalConfig = NiLocalConfig(), *,
                         radial_override_angstrom: float | None = None,
                         magnetization_sign: int = 1) -> TransitionDataset:
    """Historical Ni API over the shared 2p-to-3d transition generator.

    The shared generator has an explicit historical event-dropping policy for
    tiny radial integrals. Broadening remains the caller's responsibility.
    """
    config.validate()
    if magnetization_sign not in (-1, 1):
        raise ValueError('magnetization_sign must be +1 or -1')
    if radial_override_angstrom is not None and (not np.isfinite(radial_override_angstrom)
                                                 or abs(radial_override_angstrom) < 1e-14):
        raise ValueError('radial override must be finite and nonzero')
    radial = (hydrogenic_radial_dipole_angstrom(config.zeff_2p, config.zeff_3d)
              if radial_override_angstrom is None else abs(radial_override_angstrom))
    from .atomic_ionization import transitions_for_material
    from types import SimpleNamespace
    parameters = SimpleNamespace(validate=config.validate, element='Ni',
        edge_energies_ev=(config.l3_ev, config.l2_ev),
        radial_integral_angstrom=radial,
        crystal_field_ev=config.crystal_field_10dq_ev,
        exchange_ev=config.exchange_split_ev,
        spin_resolved_holes=tuple(
            (getattr(config, group+'_up_holes'), getattr(config, group+'_down_holes'))
            for group in ('eg', 'eg', 't2g', 't2g', 't2g')),
        source='Historical Ni compatibility inputs', radial_source='explicit Ni radial integral')
    transitions = transitions_for_material(parameters, magnetization_sign=magnetization_sign,
        amplitude_policy='historical_drop' if radial < 1e-12 else 'strict')
    return TransitionDataset(transitions.energy_ev, transitions.dipoles_angstrom,
        transitions.weights, transitions.edge,
        np.asarray(['Ni_local_atomic_model'] * len(transitions.energy_ev)),
        _ni_transition_source(config, radial_override_angstrom, magnetization_sign))


def _ni_transition_source(config, radial_override_angstrom, magnetization_sign):
    return ("NON_DFT_ILLUSTRATIVE_LOCAL_Ni_2p3d: normalized screened hydrogenic radial functions "
            f"(Zeff_2p={config.zeff_2p:g},Zeff_3d={config.zeff_3d:g}), "
            f"cubic field 10Dq={config.crystal_field_10dq_ev:g}eV, "
            f"exchange={config.exchange_split_ev:g}eV; M_sign={magnetization_sign}; "
            f"radial_source={'hydrogenic' if radial_override_angstrom is None else 'external_tabulated'}; "
            "NO many-body multiplets or Ni fit")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ni local atomic crystal-field MDFF (NON-DFT, NOT quantitative Ni)")
    parser.add_argument("--output", type=Path, default=Path("outputs/ni_local_atomic_mdff"))
    parser.add_argument("--zeff-2p", type=float, default=25.0)
    parser.add_argument("--zeff-3d", type=float, default=9.0)
    parser.add_argument("--ten-dq-ev", type=float, default=0.8)
    parser.add_argument("--exchange-ev", type=float, default=0.2)
    parser.add_argument("--sigma-ev", type=float, default=0.8)
    parser.add_argument("--radial-table", type=Path, default=None,
                        help="CSV: radius_angstrom,R_2p,R_3d (full normalized or unnormalized R(r))")
    args = parser.parse_args(argv)
    cfg = NiLocalConfig(zeff_2p=args.zeff_2p, zeff_3d=args.zeff_3d,
                        crystal_field_10dq_ev=args.ten_dq_ev,
                        exchange_split_ev=args.exchange_ev)
    try:
        table_radial = None
        if args.radial_table is not None:
            tab = np.genfromtxt(args.radial_table, names=True, delimiter=",", encoding="utf-8")
            required = ("radius_angstrom", "R_2p", "R_3d")
            if tab.dtype.names is None or any(k not in tab.dtype.names for k in required):
                raise ValueError("radial table must contain radius_angstrom,R_2p,R_3d")
            table_radial = radial_dipole_from_table(*(tab[k] for k in required))
        ds = ni_local_transitions(cfg, radial_override_angstrom=table_radial)
        e = np.linspace(cfg.l3_ev-10, cfg.l2_ev+10, 251)
        tensor = dipole_tensor_from_transitions(ds, e, args.sigma_ev)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    args.output.mkdir(parents=True, exist_ok=True)
    ds.save_npz(args.output / "transitions.npz")
    tensor.save_npz(args.output / "mdff_tensor.npz")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t = tensor.tensor_angstrom2_per_ev
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(e, np.trace(t, axis1=-2, axis2=-1).real/3, label="Tr(T)/3")
    ax.plot(e, t[:, 0, 1].imag, label="Im(Txy)")
    ax.set(xlabel="Energy loss (eV)", ylabel="Model tensor spectral weight (Å²/eV)",
           title="Non-DFT screened-hydrogenic Ni 2p → cubic 3d example")
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.output / "mdff_tensor.png", dpi=160)
    plt.close(fig)
    metadata = {
        "model": "screened_hydrogenic_independent_electron_cubic_3d",
        "quantitative_Ni": False,
        "is_dft": False,
        "is_atomic_multiplet": False,
        "no_automatic_emcd_coupling": True,
        "config": asdict(cfg),
        "sigma_ev": args.sigma_ev,
        "radial_source": "tabulated_full_R" if args.radial_table else "screened_hydrogenic",
        "radial_table": str(args.radial_table) if args.radial_table else None,
        "radial_dipole_angstrom": (abs(table_radial) if table_radial is not None
                                     else hydrogenic_radial_dipole_angstrom(cfg.zeff_2p, cfg.zeff_3d)),
        "num_transitions": len(ds.energy_ev),
        "missing_physics": ["real Ni radial potential", "2p-3d Coulomb multiplets", "core hole",
                            "ligand charge transfer", "band dispersion", "DFT", "absolute cross section", "outgoing channeling"],
    }
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "transitions": len(ds.energy_ev),
                      "radial_dipole_angstrom": metadata["radial_dipole_angstrom"],
                      "quantitative_Ni": False}, indent=2))



def material_reason(structure):
    from .gui.geometry import Structure
    # Conservative Stage B gate: arbitrary CIF inspection is not MDFF validation.
    ref=Structure.nickel().atoms;a=structure.atoms
    # Keep the original Ni-only material restriction independent of the wider
    # elastic capability. Matching coordinates/cell alone do not identify Ni.
    if set(a.get_chemical_symbols())!={'Ni'}:
        return 'Stage B MDFF requires Ni; general-material elastic factors do not provide general-material EMCD.'
    if structure.elastic_reason:return structure.elastic_reason
    if (len(a)!=len(ref) or not np.allclose(a.cell.array,ref.cell.array,atol=1e-7)
        or not np.allclose(a.get_scaled_positions()%1,ref.get_scaled_positions()%1,atol=1e-7)):
        return 'Stage B MDFF requires the verified conventional FCC Ni cell (a=3.524 A, equivalent sites). CIF inspection remains available.'
    return ''


def tensors(cfg,energy,R):
    if cfg.model=='xmcd':
        if not cfg.axis_declared:raise ValueError('Declare the XMCD magnetic-axis, RP/LP handedness and L3/L2 assignments before running')
        Q=axis_rotation(cfg.magnetization)
        source=[effective_tensor_from_xmcd(cfg.source,energy,eta=s*cfg.eta,beta=cfg.beta) for s in (1,-1)]
    elif cfg.model=='atomic':
        if not np.allclose(cfg.magnetization,(0,0,1)):raise ValueError('Atomic cubic-field model currently supports crystal [001] magnetization only')
        Q=np.eye(3)
        source=[dipole_tensor_from_transitions(ni_local_transitions(cfg.atomic,radial_override_angstrom=cfg.radial,magnetization_sign=s),energy,cfg.sigma) for s in (1,-1)]
    else:raise ValueError('Unknown MDFF model')
    out=[]
    for t in source:
        A=R@Q;v=np.einsum('ia,eab,jb->eij',A,t.tensor_angstrom2_per_ev,A)
        if np.linalg.eigvalsh(v).min() < -1e-12*max(float(abs(v).max()),1e-30):raise ValueError('MDFF tensor is not positive semidefinite')
        out.append(DipoleTensor(energy,v,t.source+';crystal_to_local_R_T_RT'))
    if not np.allclose(out[1].tensor_angstrom2_per_ev,out[0].tensor_angstrom2_per_ev.conj(),rtol=1e-10,atol=1e-13*max(abs(out[0].tensor_angstrom2_per_ev).max(),1e-30)):
        raise ValueError('This model does not pass even/odd reversal symmetry; decomposition disabled')
    return out


def energy_grid(cfg,requested=None):
    if cfg.model=='xmcd':
        s=load_wien2k_xmcd(cfg.source);lo,hi=s.energy_ev[[0,-1]]
        if cfg.source_sha256 and cfg.source_sha256!=s.source_sha256:raise ValueError('XMCD source changed since validation; validate again')
    else:lo,hi=cfg.atomic.l3_ev-10,cfg.atomic.l2_ev+10
    if not lo<=cfg.l3<cfg.l2<=hi:raise ValueError('Selected L3/L2 must be ordered inside the native model energy range')
    if cfg.channeling_model not in ('single','double'):raise ValueError('Unknown channeling model; no automatic substitution')
    if cfg.energy_scope not in ('full','edges'):raise ValueError('Unknown spectral energy coverage')
    if not 9<=cfg.energy_points<=501 or not 9<=cfg.grid<=193 or not 2<=cfg.depth<=1025 or not 4<=cfg.subpixels<=256:raise ValueError('Numerical sampling exceeds supported GUI bounds')
    if not np.isfinite([cfg.halfwidth,cfg.radius,*np.ravel(cfg.centers),*cfg.window]).all() or min(cfg.halfwidth,cfg.radius)<=0:raise ValueError('Invalid map/detector/window controls')
    if requested is not None:
        e=np.asarray(requested,float)
        if e.ndim!=1 or len(e)<2 or not np.isfinite(e).all() or np.any(np.diff(e)<=0):raise ValueError('Requested energies must be finite, increasing and contain at least two samples')
        if e[0]<lo or e[-1]>hi:raise ValueError('No MDFF energy extrapolation')
        if not all(np.any(np.isclose(e,v,rtol=0,atol=1e-9)) for v in (cfg.l3,cfg.l2)):raise ValueError('Requested grid must include the selected native L3/L2 energies')
        return e.copy()
    return np.array([cfg.l3,cfg.l2]) if cfg.energy_scope=='edges' else np.unique(np.r_[np.linspace(lo,hi,cfg.energy_points),cfg.l3,cfg.l2])


class HistoricalNiSites:
    """Original unwrapped positions and per-atom mean, after the legacy gate.

    Unlike declared IonizationSites, this adapter does not wrap coordinates or
    infer new equivalence. It preserves the accepted conventional Ni domain.
    """
    def positions_for(self, crystal):
        positions=np.asarray(crystal.fractional_positions,float)
        if not len(positions) or not all(s=='Ni' for s in crystal.species):
            raise ValueError('Historical Ni sites require only Ni atoms')
        return positions

    def single_phase(self, crystal, hkl):
        return single_site_phase_matrix(hkl,self.positions_for(crystal))


class HistoricalNiProvider:
    """Common provider interface with explicit historical numerical policies."""
    declared=False
    source=None
    simulation_magnetization=(0.,0.,1.)

    def __init__(self,cfg):
        self.cfg=cfg

    def material_reason(self,structure):
        return material_reason(structure)

    def energy_grid(self,requested=None):
        return energy_grid(self.cfg,requested)

    def tensors(self,energy,rotation):
        return tensors(self.cfg,energy,rotation)

    def sites(self,structure):
        return HistoricalNiSites()

    def revalidate_source(self):
        # Preserve historical source-validation timing; no new migration policy.
        pass


if __name__ == "__main__":
    main()
