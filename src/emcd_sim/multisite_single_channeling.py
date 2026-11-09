"""Programmatic site-resolved Single Channeling on a shared incoming coherence.

No propagation, detector integration or cross-element calibration is performed.
Independent localized events contribute intensities, while the existing tensor
kernel retains coherent elastic paths within each event.
"""
import numpy as np

from .imported_mdff import proper_frame
from .ionization_sites import single_site_phase_matrix
from .mdff_providers import prepare_site_group_providers
from .multisite import MultiSiteIonization
from .single_channeling_tensor import _tensor_angular_maps
from .cancellation import check_cancelled


def _group_intensity_pair(model,coherence,phase,energy,tensors,qx,qy,thickness_nm,cancelled):
    """Existing bounded tensor contraction, also used by the GUI scheduler."""
    raw=np.empty((2,len(energy))+qx.shape)
    flat_raw=raw.reshape(2,len(energy),-1)
    for state,tensor in enumerate(tensors):
        for ie,loss in enumerate(energy):
            for start in range(0,qx.size,64):
                check_cancelled(cancelled)
                sl=slice(start,start+64)
                real_part,imag_part=_tensor_angular_maps(model,tensor[ie],loss,coherence,
                    phase,qx.ravel()[sl],qy.ravel()[sl])
                flat_raw[state,ie,sl]=thickness_nm*(real_part+imag_part)
    if not np.isfinite(raw).all() or raw.min() < -1e-8*max(1.,float(np.max(abs(raw)))):
        raise ValueError('Invalid tensor-derived site intensity: check conventions/phase')
    return raw


def _validate_multisite_inputs(model,sites,coherence,energy_ev,qx,qy,crystal_to_microscope,thickness_nm,reverse_magnetization,cancelled):
    check_cancelled(cancelled)
    if not isinstance(sites, MultiSiteIonization):
        raise ValueError('An explicit MultiSiteIonization model is required')
    rotation = proper_frame(crystal_to_microscope)
    crystal = model.elastic.crystal
    positions = np.asarray(crystal.fractional_positions, float)
    if (tuple(crystal.species) != sites.species
            or positions.shape != (len(sites.species), 3)
            or not np.isfinite(positions).all()
            or not np.allclose(crystal.lattice_angstrom,
                               np.asarray(sites.cell) @ rotation.T, rtol=0, atol=1e-10)):
        raise ValueError('Site groups do not match the complete oriented elastic crystal')
    delta = positions - np.asarray(sites.fractional_positions)
    delta -= np.rint(delta)
    if not np.allclose(delta, 0, rtol=0, atol=1e-9):
        raise ValueError('Site groups do not match the ordered elastic crystal positions')
    energy = np.asarray(energy_ev, float)
    if (energy.ndim != 1 or not len(energy) or not np.isfinite(energy).all()
            or np.any(energy <= 0) or np.any(np.diff(energy) <= 0)
            or energy[-1] >= 1000 * model.elastic.microscope.acceleration_kv):
        raise ValueError('Require ascending positive losses below incident energy')
    if not np.isfinite(thickness_nm) or thickness_nm <= 0:
        raise ValueError('Thickness must be positive and finite')
    if not isinstance(reverse_magnetization, bool):
        raise ValueError('Global reversal must be a boolean')
    qx, qy = np.asarray(qx, float), np.asarray(qy, float)
    if qx.shape != qy.shape or not qx.size or not np.isfinite(qx).all() or not np.isfinite(qy).all():
        raise ValueError('Require matching finite nonempty detector query arrays')
    coherence = np.asarray(coherence, complex)
    n = len(model.elastic.beams.hkl)
    if (coherence.shape != (n, n) or not n or not np.isfinite(coherence).all()
            or not np.allclose(coherence, coherence.conj().T, rtol=1e-10, atol=1e-12)):
        raise ValueError('Coherence must be finite Hermitian and match the ordered beam basis')
    if np.linalg.eigvalsh(coherence).min() < -1e-10 * max(1., np.linalg.norm(coherence)):
        raise ValueError('Coherence must be positive semidefinite')

    return rotation,positions,energy,qx,qy,coherence


def run_multisite_with_coherence(model, sites, coherence, energy_ev, qx, qy, *,
                                crystal_to_microscope, thickness_nm=30.,
                                reverse_magnetization=False, cancelled=None):
    """Return query-point intensities with energy as the leading array axis.

    ``model`` contains the complete oriented elastic crystal and ordered beam
    basis. ``coherence`` is its depth-averaged incoming coherence (BW or MS),
    including any projection leakage; its trace is never renormalized.
    ``sites`` is the Stage 1 snapshot in the original crystal Cartesian frame.
    The supplied proper rotation maps that frame to the microscope frame.

    Every provider must cover every requested energy. Each group supplies its
    explicit plus/minus pair; global reversal exchanges ALL pairs, leaving the
    elastic state, detectors and local frames fixed. Real/imaginary tensor
    decomposition is only an internal kernel operation, not magnetic parity.

    Group arrays are means per group atom. Total arrays are means per selected
    ionizing atom; weighted_sum arrays are the unnormalized multiplicity sums.
    All retain declared source amplitudes and are relative, uncalibrated values.
    Query points are evaluated in bounded batches, with cancellation checkpoints.
    """
    rotation,positions,energy,qx,qy,coherence=_validate_multisite_inputs(
        model,sites,coherence,energy_ev,qx,qy,crystal_to_microscope,thickness_nm,reverse_magnetization,cancelled)

    prepared = prepare_site_group_providers(sites, energy, rotation)
    groups = {}
    weighted = np.zeros((2, len(energy)) + qx.shape)
    for group, tensors, source in prepared:
        phase = single_site_phase_matrix(model.elastic.beams.hkl, positions[list(group.indices)])
        pair=tensors[::-1] if reverse_magnetization else tensors
        raw=_group_intensity_pair(model,coherence,phase,energy,
            [tensor.tensor_angstrom2_per_ev for tensor in pair],qx,qy,thickness_nm,cancelled)
        weighted += group.multiplicity * raw
        groups[group.group_id] = dict(
            plus=raw[0], minus=raw[1], element=group.element,
            indices=group.indices, multiplicity=group.multiplicity,
            magnetization_crystal=group.magnetization, source=source,
            normalization=group.normalization)

    # Preserve existing source identity safeguards through calculation completion.
    from .gui.generalized_forward import source_for
    for group in sites.groups:
        check_cancelled(cancelled)
        source_for(group.mdff_reference)
    count = sum(group.multiplicity for group in sites.groups)
    plus, minus = weighted / count
    return dict(
        energy_ev=energy.copy(), qx_angstrom_inv=qx.copy(), qy_angstrom_inv=qy.copy(),
        groups=groups,
        total=dict(plus=plus, minus=minus, even=(plus + minus) / 2, odd=(plus - minus) / 2),
        weighted_sum=dict(plus=weighted[0], minus=weighted[1]),
        metadata=dict(normalization='mean_per_selected_ionizing_atom',
                      selected_atom_count=count, weighted_sum_normalization='sum_over_selected_atoms',
                      crystal_to_microscope=rotation.tolist(), thickness_nm=float(thickness_nm),
                      global_reversal=reverse_magnetization,
                      parity='even=(I_plus+I_minus)/2; odd=(I_plus-I_minus)/2',
                      intensity_convention='Declared provider amplitudes; relative, no absolute or cross-element calibration'))
