"""Export stored multi-site spectra, independently of project persistence."""
import csv
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path

import numpy as np

from .. import __version__
from .multisite_results import SPECTRAL_KEYS, QUANTITIES, material, spectral_series, selection_description


DEFINITIONS = {
    'I_A_plus': 'Raw detector A, active provider state',
    'I_B_plus': 'Raw detector B, active provider state',
    'I_A_minus': 'Raw detector A, globally reversed provider state',
    'I_B_minus': 'Raw detector B, globally reversed provider state',
    'N_A': '(I_A_plus + I_A_minus)/2; reversal-even at A',
    'N_B': '(I_B_plus + I_B_minus)/2; reversal-even at B',
    'M_A': '(I_A_plus - I_A_minus)/2; reversal-odd at A',
    'M_B': '(I_B_plus - I_B_minus)/2; reversal-odd at B',
    'D_raw': 'I_A_plus - I_B_plus; conventional detector difference',
    'D_mag': 'M_A - M_B; magnetic reversal-odd detector difference',
    'D_nonmag': 'N_A - N_B; nonmagnetic reversal-even detector difference',
    'Sigma_ref': 'N_A + N_B',
}


def _json_value(value):
    """Keep metadata JSON portable; unset numerical settings become null."""
    if is_dataclass(value):return _json_value(asdict(value))
    if isinstance(value, dict):return {str(k):_json_value(v) for k,v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):return [_json_value(v) for v in value]
    if isinstance(value, np.generic):return _json_value(value.item())
    if isinstance(value, float) and not np.isfinite(value):return None
    if isinstance(value, Path):return str(value)
    return value


def export_multisite_spectra(result, path, *, method=None, selection=('total',None),
                            normalization='weighted', compared=(), quantity=0, include_total=False):
    """Write the selected stored curves and all their linear signal components.

    One CSV row per series and original energy sample. Unsupported intensities
    are blank, never a fabricated zero. Active calculated zeros remain numeric.
    csv.writer's float representation round-trips binary64 values without a
    display-precision limit. No calculation, resampling or source IO occurs.
    """
    method = method or result.get('method','bloch')
    r = result.get('methods',{}).get(method,result)
    series = spectral_series(r,selection,normalization,compared,include_total)
    if not series:raise ValueError('Select at least one comparison group or include the total before exporting.')
    channels = r['metadata']['multisite']['channels']
    denominator = r['metadata']['multisite']['selected_atom_count']
    energy = r['spectra']['energy_ev']
    records = []
    for index,item in enumerate(series):
        kind = 'total' if item['normalization']=='total' else 'element' if selection[0]=='element' else 'group'
        identity = 'Total' if kind=='total' else selection[1] if kind=='element' else item['groups'][0]
        convention = {'total':'total_mean_per_selected_ionizing_atom', 'weighted':'additive_contribution_n_over_N',
                      'mean':'group_mean_per_atom_nonadditive'}[item['normalization']]
        records.append(dict(series_index=index,series_kind=kind,series_id=identity,label=item['label'],
            group_ids=item['groups'],normalization=convention,applied_scale=item['scale'],
            global_denominator=denominator,
            multiplicities={gid:r['groups'][gid]['metadata']['multiplicity'] for gid in item['groups']},
            declared_source_units={gid:r['groups'][gid]['metadata']['source'].get('units','undeclared') for gid in item['groups']}))

    crystal = r['model'].elastic.crystal
    metadata = dict(
        kind='Multi-site numerical spectra export (not a saved project)',
        spectrum_kind='modeled_partial_core_edge_spectrum',material=material(r),
        structure=dict(species=crystal.species,lattice_angstrom=crystal.lattice_angstrom,
                       fractional_positions=crystal.fractional_positions),
        method=method,settings=r['settings'],calculation_config=r['config'],
        software_version=r['metadata'].get('software_version',__version__),
        calculation_metadata=r['metadata'],groups={gid:g['metadata'] for gid,g in r['groups'].items()},
        selection=dict(mode=selection,compared=compared,include_total=include_total,
                       displayed_quantity=QUANTITIES[quantity][0]),
        series=records,normalization_description=selection_description(r,series),
        signal_definitions=DEFINITIONS,
        state_definition='plus is the active declared configuration; minus reverses every physical provider pair together. '
                         'If global_reversal is true, plus uses the declared -M states. No conjugation inference.',
        units=dict(energy_ev='eV',intensities='Relative provider intensity scale; declared source units recorded per group; no unit conversion or cross-element calibration.'),
        coverage=dict(modeled='At least one selected channel active; inactive channels listed separately.',
                      excluded='Every selected channel explicitly excluded by request.',
                      unmodeled='No selected channel modeled at this energy; intensities blank.',
                      note='No interpolation or extrapolation. Blank is not physical zero. Numeric zero is a calculated active value. '
                           'Load the long-form CSV by series_index and use coverage_state to break lines across unsupported gaps.'),
        limitations='Partial core-edge spectrum, not complete EELS. Provider amplitudes retained; no automatic peak/area scaling or absolute cross-element calibration.',
        metadata_note='JSON is written automatically for provenance; no JSON input is required. Unset/nonfinite metadata settings are null.')
    encoded = json.dumps(_json_value(metadata),indent=2,allow_nan=False)+'\n'
    root = Path(path);root.mkdir(parents=True,exist_ok=False)
    fields = ['solver','channeling_model','series_index','series_kind','series_id','label','normalization',
              'global_denominator','intensity_units','energy_ev','coverage_state',
              'active_group_ids','excluded_group_ids','unmodeled_group_ids',*SPECTRAL_KEYS]
    with (root/'spectra.csv').open('w',encoding='utf-8',newline='') as stream:
        writer = csv.DictWriter(stream,fields);writer.writeheader()
        for item,record in zip(series,records):
            for ie,loss in enumerate(energy):
                active = [];excluded = [];unmodeled = []
                for gid in item['groups']:
                    channel = channels[gid]
                    if channel['omitted_by_request']:excluded.append(gid)
                    elif channel['active_energy_mask'][ie]:active.append(gid)
                    else:unmodeled.append(gid)
                state = 'modeled' if active else 'excluded' if len(excluded)==len(item['groups']) else 'unmodeled'
                row = {key:record[key] for key in ('series_index','series_kind','series_id','label','normalization','global_denominator')}
                row.update(solver=method,channeling_model=r['config'].channeling_model,
                    intensity_units='relative_provider_scale',energy_ev=float(loss),coverage_state=state,
                    active_group_ids=json.dumps(active),excluded_group_ids=json.dumps(excluded),unmodeled_group_ids=json.dumps(unmodeled))
                row.update({key:float(item['spectra'][key][ie]) if active else '' for key in SPECTRAL_KEYS})
                writer.writerow(row)
    (root/'metadata.json').write_text(encoded,encoding='utf-8')
    return root
