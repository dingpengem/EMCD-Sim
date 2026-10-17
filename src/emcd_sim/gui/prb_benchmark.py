"""PRB 75, 214425 Fig. 5 convention, derived only from original detector arrays.

Pure NumPy post-processing. No solver, tensor, correction or source-file read.
"""
import numpy as np
from .signal_normalization import EELS_FLOOR, divide_percent, default_windows
from ..geometry import electron_wavelength_angstrom

DEFINITION = '100 * (I_A_plus - I_B_plus) / (I_A_plus + I_B_plus); raw +M detectors; no factor 2, peak scaling or post-edge correction'
LIMITATION = ('PRB-compatible normalization does not imply full physical equivalence to Rusz et al. (2007). '
              'The current EMCD-Sim uses an approximate MDFF and may omit outgoing-electron channeling and other effects included in the reference theory.')
REFERENCE = ('Rusz, Rubino and Schattschneider, PRB 75, 214425 (2007), Fig. 5(c): fcc Ni, '
             'near [001], G=(200), two-beam systematic row; opposite top/bottom Thales positions. '
             'Optimal thickness about 6–10 nm; roughly 18% is a visual literature estimate, not a required result. '
             'DOI: 10.1103/PhysRevB.75.214425; arXiv:0704.1407.')


def relative_dichroism_percent(detector_a, detector_b):
    """Signed raw paired percentage; NaN for invalid or near-zero denominators."""
    a, b = np.broadcast_arrays(np.asarray(detector_a, float), np.asarray(detector_b, float))
    with np.errstate(over='ignore', invalid='ignore'):
        value, mask = divide_percent(a-b, a+b, EELS_FLOOR, support=(a >= 0) & (b >= 0))
    return value, dict(mask, definition=DEFINITION)


def benchmark_spectra(spectra):
    """Primary +M curve and separately labeled reversal diagnostics."""
    a, b = np.asarray(spectra['I_A_plus'], float), np.asarray(spectra['I_B_plus'], float)
    primary, mask = relative_dichroism_percent(a, b)
    curves = dict(prb_relative_dichroism_percent=primary)
    masks = dict(prb=mask)
    if all(k in spectra for k in ('I_A_minus', 'I_B_minus')):
        am, bm = np.asarray(spectra['I_A_minus'], float), np.asarray(spectra['I_B_minus'], float)
        if am.shape != a.shape or bm.shape != a.shape:
            raise ValueError('Reversal spectra must share the same saved energy sampling.')
        with np.errstate(over='ignore', invalid='ignore'):
            na, nb = (a+am)/2, (b+bm)/2
            ma, mb = (a-am)/2, (b-bm)/2
            support = (a >= 0) & (b >= 0) & (am >= 0) & (bm >= 0)
            curves['magnetic_only_percent'], masks['magnetic'] = divide_percent(ma-mb, na+nb, support=support)
            curves['nonmagnetic_imbalance_percent'], masks['even'] = divide_percent(na-nb, na+nb, support=support)
    return curves, masks


def data_origin(result):
    if 'prb_data_origin' in result:
        return result['prb_data_origin']
    if 'project_manifest' in result or result.get('read_only_legacy'):
        return 'saved result (legacy read-only)' if result.get('read_only_legacy') else 'saved project'
    return 'new calculation / in-memory result'


def _scalar(value):
    return float(value) if np.isfinite(value) else None


def benchmark_readout(result, *, selection='l3-peak', energy_ev=None, windows=None,
                      origin=None, project_path=None):
    """Select one common saved sample for A/B, never maximize dichroism.

    Selected mode uses nearest saved sample (lower energy wins a tie), as the
    existing scalar metrics do. Requested and actual energies are both retained.
    """
    s = result['spectra']
    e = np.asarray(s['energy_ev'], float)
    a, b = np.asarray(s['I_A_plus'], float), np.asarray(s['I_B_plus'], float)
    if (e.ndim != 1 or len(e) < 2 or not np.isfinite(e).all() or np.any(np.diff(e) <= 0)
            or a.shape != e.shape or b.shape != e.shape):
        raise ValueError('Benchmark needs original A/B spectra on one finite increasing saved energy axis.')
    cfg, settings = result['config'], result['settings']
    md = result.get('metadata', {})
    wavelength = electron_wavelength_angstrom(settings.voltage)
    condition = f'nominal {list(settings.zone)}, target {list(settings.target)}, absolute tilt ({settings.tilt[0]:+.8f}, {settings.tilt[1]:+.8f}) mrad'
    mismatches = ['Approximate MDFF and entrance-only ionization; reference theory is not fully reproduced.',
                  'Reference electron-energy/collection settings have not been matched; finite circular apertures are averaged.']
    if tuple(settings.zone) != (0, 0, 1):
        mismatches.insert(0, f'Current nominal {list(settings.zone)} is not the reference [001] systematic-row vicinity; equivalence is not assumed.')
    if tuple(settings.target) != (2, 0, 0):
        mismatches.append('Target reflection differs from reference G=(200).')
    g = None
    for h, xy in zip(md.get('beam_hkl', []), md.get('g', [])):
        if tuple(h) == tuple(settings.target):
            g = np.asarray(xy, float)[:2]
            break
    s_target = None
    if g is not None and np.linalg.norm(g) > 0:
        ideal = np.stack((g/2+np.array([-g[1], g[0]])/2, g/2-np.array([-g[1], g[0]])/2))
        if not (np.allclose(cfg.centers, ideal, atol=1e-8, rtol=0) or np.allclose(cfg.centers, ideal[::-1], atol=1e-8, rtol=0)):
            mismatches.append('A/B centres are not the opposite reference Thales positions for this target.')
        k = np.asarray(settings.tilt)*1e-3/wavelength
        s_target = float((np.dot(g, g)+2*np.dot(k, g))/(2/wavelength))
    else:
        mismatches.append('Saved target vector unavailable; Thales geometry cannot be checked.')
    record = dict(selected_edge='L3', selection=selection, definition=DEFINITION,
        denominator='I_A_plus(E) + I_B_plus(E)', units='percent', evaluation_energy_ev=None,
        requested_energy_ev=None, prb_relative_dichroism_percent=None, magnetic_only_percent=None,
        nonmagnetic_imbalance_percent=None, undefined_reason=None,
        diagnostic_definitions=dict(magnetic='100 * (M_A-M_B)/(N_A+N_B)', even='100 * (N_A-N_B)/(N_A+N_B)',
                                    reversal='N_J=(I_J_plus+I_J_minus)/2; M_J=(I_J_plus-I_J_minus)/2; diagnostics are not the primary PRB definition'),
        thickness_nm=float(settings.thickness), accelerating_voltage_kv=float(settings.voltage), electron_wavelength_angstrom=wavelength,
        nominal_zone_axis=list(settings.zone), target_hkl=list(settings.target), tilt_mrad=list(settings.tilt), diffraction_condition=condition,
        target_excitation_error_inv_angstrom=s_target, two_beam_wavefield='Not established by s_target=0; full finite diffraction basis retained.',
        detector_centres_cycles_per_angstrom=[list(p) for p in cfg.centers], aperture_radius_cycles_per_angstrom=float(cfg.radius),
        collection_half_angle_mrad=float(1000*wavelength*cfg.radius), collection_angle_convention='paraxial radius * wavelength; circular finite aperture',
        mdff_model=cfg.model, solver=result.get('method', 'not recorded'),
        magnetization_crystal=list(cfg.magnetization), eta=float(cfg.eta), beta=float(cfg.beta),
        potential_representation=md.get('potential_representation', 'Projected 2D (legacy IAM GUI result)'),
        data_origin=origin or data_origin(result), project_path=str(project_path or result.get('prb_project_path') or result.get('project_path') or ''),
        source_sha256=cfg.source_sha256 or (md.get('source_audit') or {}).get('sha256'),
        calculation_commit=md.get('software_commit'), limitation=LIMITATION, literature_reference=REFERENCE,
        comparison_status='Normalization-compatible readout only; not a physical Figure 5 reproduction', geometry_mismatches=mismatches)
    curves, masks = benchmark_spectra(s)
    record['masks'] = masks
    if selection == 'l3-peak':
        lo, hi = map(float, (windows or default_windows(result))['L3'])
        if (not np.isfinite([lo, hi]).all() or not e[0] <= lo < hi <= e[-1]
                or hi >= (cfg.l3+cfg.l2)/2):
            raise ValueError('L3 window must lie within the saved L3 region/range, excluding the other edge.')
        valid = (e >= lo) & (e <= hi) & np.isfinite(a) & np.isfinite(b) & (a >= 0) & (b >= 0)
        record['l3_window_ev'] = [lo, hi]
        if valid.sum() < 2:
            raise ValueError('L3 white-line selection needs at least two finite original A/B samples in the window.')
        with np.errstate(over='ignore', invalid='ignore'):
            total = a+b
        valid &= np.isfinite(total) & (total > 0)
        if not valid.any():
            record['undefined_reason'] = 'No finite positive +M summed-detector L3 peak.'
            return record
        ids = np.flatnonzero(valid)
        index = int(ids[np.argmax(total[ids])])
        record['energy_selection_definition'] = 'argmax in L3 window of ORIGINAL I_A_plus + I_B_plus; common A/B energy, not maximum dichroism or even/white-line scaling'
    elif selection == 'selected':
        energy = cfg.l3 if energy_ev is None else float(energy_ev)
        if not np.isfinite(energy) or not e[0] <= energy <= e[-1]:
            raise ValueError('Selected benchmark energy must lie inside the saved native energy range.')
        index = int(np.argmin(abs(e-energy)))
        record['requested_energy_ev'] = energy
        record['energy_selection_definition'] = 'Nearest original saved sample to requested energy; no interpolation or maximization; lower energy at a tie'
    else:
        raise ValueError('Benchmark selection must be l3-peak or selected.')
    record.update(evaluation_energy_ev=float(e[index]), saved_sample_index=index,
                  selected_edge='L3' if e[index] < (cfg.l3+cfg.l2)/2 else 'L2',
                  I_A_plus=_scalar(a[index]), I_B_plus=_scalar(b[index]))
    for key, values in curves.items():
        record[key] = _scalar(values[index])
    if record['prb_relative_dichroism_percent'] is None:
        record['undefined_reason'] = 'Invalid, nonpositive or near-zero original +M detector sum (or invalid detector intensity); see mask policy.'
    if len(curves) == 1:
        record['diagnostic_unavailable_reason'] = 'Original magnetization-reversal spectra unavailable.'
    return record
