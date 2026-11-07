"""Explicit modeled edge windows; source coverage is never a zero-padding rule.

Each site group retains its existing provider and declared core edge. For example,
pass energy_windows={'Fe': ModeledEdgeWindow((704., 730.), (710., 723.)),
'Ni': ModeledEdgeWindow((840., 866.), (846., 859.))} to calculate_multisite.
Without energy_ev, window samples define the union grid. A common energy_ev may
also be supplied; overlapping channels evaluate the same union samples inside
their windows, using only the providers' established interpolation.
"""
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from .cancellation import check_cancelled
from .mdff_providers import load_site_group_provider
from .multisite import MultiSiteIonization
from .multisite_single_channeling import run_multisite_with_coherence


def _samples(values):
    e = np.asarray(values, float)
    if (e.ndim != 1 or not len(e) or not np.isfinite(e).all()
            or np.any(e <= 0) or np.any(np.diff(e) <= 0)):
        raise ValueError('Require finite ascending positive spectral samples')
    return e


@dataclass(frozen=True)
class ModeledEdgeWindow:
    """Required modeled interval, optionally with its own requested samples.

    Bounds are inclusive and must BOTH be covered by the source, even if only
    interior points are sampled. Unlisted groups are explicitly omitted from
    this partial spectrum, but remain in its selected-atom denominator.
    """
    bounds_ev: tuple[float, float]
    energy_ev: tuple[float, ...] | None = None

    def __post_init__(self):
        bounds = np.asarray(self.bounds_ev, float)
        if (bounds.shape != (2,) or not np.isfinite(bounds).all()
                or bounds[0] <= 0 or bounds[1] < bounds[0]):
            raise ValueError('Modeled edge window requires finite ascending positive bounds')
        object.__setattr__(self, 'bounds_ev', tuple(map(float, bounds)))
        if self.energy_ev is not None:
            e = _samples(self.energy_ev)
            if e[0] < bounds[0] or e[-1] > bounds[1]:
                raise ValueError('Window samples must lie inside the declared modeled edge window')
            object.__setattr__(self, 'energy_ev', tuple(map(float, e)))


def prepare_multisite_spectrum(sites, energy_ev=None, energy_windows=None):
    """Validate declarations/coverage before geometry, resources or propagation."""
    ids = {group.group_id for group in sites.groups}
    grids = [] if energy_ev is None else [_samples(energy_ev)]
    if energy_windows is None:
        if not grids:
            raise ValueError('Provide a common energy grid or explicit modeled edge windows')
    else:
        if (not isinstance(energy_windows, Mapping) or not energy_windows
                or set(energy_windows) - ids
                or any(not isinstance(w, ModeledEdgeWindow) for w in energy_windows.values())):
            raise ValueError('Modeled edge windows must map known group identifiers to ModeledEdgeWindow values')
        grids.extend(np.asarray(w.energy_ev) for w in energy_windows.values() if w.energy_ev is not None)
        if not grids:
            raise ValueError('Provide common samples or independently sampled modeled edge windows')
    energy = np.unique(np.concatenate(grids))
    sources, channels, active = {}, {}, {}
    for group in sites.groups:
        source = load_site_group_provider(group)
        native = source.energy_ev[[0, -1]]
        window = None if energy_windows is None else energy_windows.get(group.group_id)
        omitted = energy_windows is not None and window is None
        bounds = None if omitted else (window.bounds_ev if window is not None else (energy[0], energy[-1]))
        mask = np.zeros(len(energy), bool) if omitted else (energy >= bounds[0]) & (energy <= bounds[1])
        if bounds is not None and (bounds[0] < native[0] or bounds[1] > native[1]):
            raise ValueError(f'Missing MDFF coverage within required modeled window for {group.group_id}')
        # Validate group axis, explicit states and frame even for omitted groups.
        # Window endpoints certify required coverage; no extrapolation or tails.
        required = native[:1] if omitted else np.unique(bounds)
        source.tensors(required, np.eye(3), group.magnetization)
        sources[group.group_id] = source.provenance()
        active[group.group_id] = mask
        channels[group.group_id] = dict(
            element=group.element, edge=source.metadata['edge'],
            native_coverage_ev=native.tolist(), modeled_window_ev=None if bounds is None else list(bounds),
            requested_energy_ev=None if window is None or window.energy_ev is None else list(window.energy_ev),
            evaluation_energy_ev=energy[mask].tolist(), active_energy_mask=mask.tolist(),
            status_at_energy=['omitted_by_request' if omitted else 'active' if flag else 'outside_modeled_window' for flag in mask],
            omitted_by_request=omitted, units=source.metadata['units'],
            source_normalization=source.metadata['normalization'], amplitude_multiplier=1.)
    metadata = dict(
        spectrum_kind='modeled_partial_core_edge_spectrum',
        coverage_mode='common_grid_all_providers' if energy_windows is None else 'explicit_modeled_edge_windows',
        channels=channels,
        active_channels_by_energy=[[gid for gid in active if active[gid][i]] for i in range(len(energy))],
        omitted_site_groups=[gid for gid, channel in channels.items() if channel['omitted_by_request']],
        omitted_excitation_channels='Unspecified core edges, unmodeled tails, continuum and other excitations are not included',
        inactive_value_meaning='Zero is a bookkeeping exclusion from the modeled partial sum, not a physical zero or missing-data replacement',
        sampling='Union of requested grids; overlapping channels reuse covered union samples',
        cross_element_calibration='None; provider amplitudes retained without peak or area rescaling',
        normalization_denominator='All selected atoms in the supplied MultiSiteIonization, including omitted groups')
    return dict(energy_ev=energy, sources=sources, active=active, metadata=metadata)


def _empty_group_intensities(sites, plan, query_shape):
    """Shared result storage; excluded channels remain explicitly labelled."""
    shape = (len(plan['energy_ev']),) + query_shape
    groups = {}
    for group in sites.groups:
        groups[group.group_id] = dict(
            plus=np.zeros(shape), minus=np.zeros(shape), element=group.element,
            indices=group.indices, multiplicity=group.multiplicity,
            magnetization_crystal=group.magnetization, source=plan['sources'][group.group_id],
            normalization=group.normalization, coverage=plan['metadata']['channels'][group.group_id])
    return groups, np.zeros((2,) + shape)


def _spectrum_result(sites, plan, groups, weighted, rotation, thickness_nm, reverse_magnetization):
    """Multiplicity is applied by callers; the denominator always uses ALL sites."""
    count = sum(group.multiplicity for group in sites.groups)
    plus, minus = weighted / count
    return dict(
        groups=groups, total=dict(plus=plus, minus=minus, even=(plus+minus)/2, odd=(plus-minus)/2),
        weighted_sum=dict(plus=weighted[0], minus=weighted[1]),
        metadata=dict(normalization='mean_per_selected_ionizing_atom', selected_atom_count=count,
            weighted_sum_normalization='sum_over_selected_atoms',
            crystal_to_microscope=np.asarray(rotation).tolist(), thickness_nm=float(thickness_nm),
            global_reversal=reverse_magnetization, parity='even=(I_plus+I_minus)/2; odd=(I_plus-I_minus)/2',
            intensity_convention='Declared provider amplitudes; relative, no absolute or cross-element calibration',
            **plan['metadata']))


def contract_multisite_spectrum(model, structure, sites, coherence, plan, qx, qy, *,
                                crystal_to_microscope, thickness_nm,
                                reverse_magnetization=False, cancelled=None):
    """Reuse Patch 2A for groups sharing an active grid, then add intensities."""
    energy = plan['energy_ev']
    cohorts = {}
    for group in sites.groups:
        indices = tuple(np.flatnonzero(plan['active'][group.group_id]))
        if indices:
            cohorts.setdefault(indices, []).append(group)
    groups, weighted = _empty_group_intensities(sites, plan, np.shape(qx))
    for indices, selected_groups in cohorts.items():
        check_cancelled(cancelled)
        selection = np.asarray(indices)
        subset = MultiSiteIonization(structure, selected_groups)
        raw = run_multisite_with_coherence(model, subset, coherence, energy[selection], qx, qy,
            crystal_to_microscope=crystal_to_microscope, thickness_nm=thickness_nm,
            reverse_magnetization=reverse_magnetization, cancelled=cancelled)
        for group in selected_groups:
            for state, label in enumerate(('plus', 'minus')):
                value = raw['groups'][group.group_id][label]
                groups[group.group_id][label][selection] = value
                weighted[state, selection] += group.multiplicity * value
        del raw
    check_cancelled(cancelled)
    return _spectrum_result(sites,plan,groups,weighted,crystal_to_microscope,thickness_nm,reverse_magnetization)
