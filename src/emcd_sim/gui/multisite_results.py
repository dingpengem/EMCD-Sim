"""Read-only total, site and element views of completed multi-site arrays."""
from collections import Counter
import json
import numpy as np


def material(result):
    counts = Counter(result['model'].elastic.crystal.species)
    return ''.join(symbol+(str(n) if n != 1 else '') for symbol,n in counts.items())


def description(result):
    meta = result['metadata'];sites = meta['multisite']
    return (f'{material(result)} | {meta["solver"]} | {meta["scientific_status"]}\nModeled partial core-edge spectrum; mean per selected ionizing atom '
            f'(fixed denominator {sites["selected_atom_count"]}). Provider amplitudes retained; no absolute cross-element calibration.\n'
            'Active state: all explicit provider '+('−M' if sites['global_reversal'] else '+M')+' states.')


def covered_segments(result, energy, group_ids=None):
    """Do not draw invented spectral tails across unmodeled inter-edge gaps."""
    channels = result['metadata']['multisite']['channels']
    selected = channels.values() if group_ids is None else (channels[gid] for gid in group_ids)
    intervals = sorted(channel['modeled_window_ev'] for channel in selected
                       if channel['modeled_window_ev'] is not None)
    merged = []
    for lo,hi in intervals:
        if merged and lo <= merged[-1][1]:merged[-1][1] = max(hi,merged[-1][1])
        else:merged.append([lo,hi])
    return [(energy>=lo)&(energy<=hi) for lo,hi in merged]


SPECTRAL_KEYS = ('I_A_plus','I_B_plus','I_A_minus','I_B_minus','N_A','N_B','M_A','M_B',
                 'D_raw','D_mag','D_nonmag','Sigma_ref')
PANELS = [
    ('Raw detector intensities', [('I_A_plus','A +state'),('I_B_plus','B +state'),('I_A_minus','A −state'),('I_B_minus','B −state')]),
    ('Global reversal-even', [('N_A','Even A'),('N_B','Even B')]),
    ('Global reversal-odd', [('M_A','Odd A'),('M_B','Odd B')]),
    ('Detector A − B differences', [('D_raw','Conventional +state A−B'),('D_mag','Magnetic odd A−B'),('D_nonmag','Nonmagnetic even A−B')])]
QUANTITIES = [
    ('EELS / magnetic and nonmagnetic components',None),('Raw EELS +state (A, B)',PANELS[0][1][:2]),
    ('Raw EELS −state (A, B)',PANELS[0][1][2:]),('Reversal-even (A, B)',PANELS[1][1]),
    ('Reversal-odd (A, B)',PANELS[2][1]),('Conventional A−B (+state)',PANELS[3][1][:1]),
    ('Magnetic A−B',PANELS[3][1][1:2]),('Nonmagnetic A−B',PANELS[3][1][2:])]


def spectral_series(result, selection=('total',None), normalization='weighted', compared=(), include_total=False):
    """Additive components are n_s I_s / N, never independently peak-scaled.

    Stored group spectra are means over that group's atoms. Their original
    arrays, including bookkeeping exclusions, are left untouched. Coverage is
    carried separately so an excluded channel is never plotted as a physical 0.
    """
    mode,value = selection;groups = result['groups'];denominator = result['metadata']['multisite']['selected_atom_count']
    if mode == 'total':return [dict(label='Total',spectra=result['spectra'],groups=tuple(groups),normalization='total',scale=1.)]
    if mode == 'element':
        ids = tuple(gid for gid,g in groups.items() if g['metadata']['element'] == value)
        if not ids:raise ValueError('Unknown ionizing element: '+str(value))
        spectra = dict(energy_ev=result['spectra']['energy_ev'])
        for key in SPECTRAL_KEYS:
            spectra[key] = sum(groups[gid]['metadata']['multiplicity']/denominator*np.asarray(groups[gid]['spectra'][key]) for gid in ids)
        return [dict(label='Element '+value,spectra=spectra,groups=ids,normalization='weighted',scale=None)]
    ids = (value,) if mode == 'group' else tuple(compared) if mode == 'compare' else ()
    if mode not in ('group','compare'):raise ValueError('Unknown spectral result selection')
    series = []
    for gid in ids:
        if gid not in groups:raise ValueError('Unknown site group: '+str(gid))
        entry = groups[gid];meta = entry['metadata']
        scale = 1. if normalization == 'mean' else meta['multiplicity']/denominator
        spectra = {key:scale*np.asarray(entry['spectra'][key]) for key in SPECTRAL_KEYS}
        spectra['energy_ev'] = result['spectra']['energy_ev']
        series.append(dict(label=gid+' · '+meta['element']+' '+meta['source']['edge'],spectra=spectra,
                           groups=(gid,),normalization='mean' if normalization == 'mean' else 'weighted',scale=scale))
    if mode == 'compare' and include_total:series.extend(spectral_series(result))
    return series


def selection_description(result, series):
    n = result['metadata']['multisite']['selected_atom_count']
    if not series:return 'No comparison groups selected. Choose groups below; no calculation is required.'
    parts = [item for item in series if item['normalization'] != 'total']
    total = f'Total normalized intensity: mean per selected ionizing atom (N={n}).'
    if not parts:return total
    names = ', '.join(item['label'] for item in parts)
    note = (names+' · per-atom mean within each group; these curves are not additive components of the total.'
            if parts[0]['normalization']=='mean' else
            names+f' · additive contribution: Σ n_s I_s / N, fixed N={n}; no peak or area rescaling.')
    return note+(' '+total if len(parts)<len(series) else '')


def comparison_text(result):
    meta = result['metadata'];sites = meta['multisite']
    lines = [description(result),'',
        'Raw detector states: I_A_plus, I_B_plus, I_A_minus, I_B_minus.',
        'Reversal-even N=(I_plus+I_minus)/2; reversal-odd M=(I_plus-I_minus)/2 at each detector.',
        'D_raw=I_A_plus-I_B_plus; D_mag=M_A-M_B; D_nonmag=N_A-N_B.',
        'A reversal-odd signal is not automatically conventional detector-difference EMCD.',
        'Active configuration: all provider '+('−M' if sites['global_reversal'] else '+M')+' states; reversal swaps every pair together.',
        'Omitted excitations and unmodeled tails are not physical zeros.','']
    for gid,entry in result['groups'].items():
        d = entry['metadata'];source = d['source']
        lines.append(f'{gid}: {d["element"]}, indices {d["indices"]}, multiplicity {d["multiplicity"]}, weight {d["contribution_weight"]:g}')
        lines.append(f'  {source["edge"]}; {source["units"]}; {source["normalization"]}; source {source["path"]}')
        lines.append(f'  {source.get("provider_identity","imported tensor")}; {source["status"]}; {source["source"][:300]}')
        lines.append(f'  Frame {source["frame_to_crystal"]}; declared M {d["magnetization_crystal"]}')
    lines += ['',meta['limitations'],'','BW/MS diagnostics: '+json.dumps(result.get('comparison',{}),default=str)]
    return '\n'.join(lines)


def draw_totals(figure, result, method, kind, choice, *, selection=('total',None),normalization='weighted',compared=(),quantity=0,include_total=False):
    """Compatibility entry point; presentation belongs to the shared Results view."""
    from .results import draw_eels,draw_maps,draw_diffraction
    if kind == 'eels':
        return draw_eels(figure,result,choice,method,selection=selection,normalization=normalization,
                         compared=compared,quantity=quantity,include_total=include_total)
    if kind == 'maps':return draw_maps(figure,result,choice,method)
    if kind == 'diffraction':return draw_diffraction(figure,result,method,choice=='Depth average')
    figure.clear();ax=figure.subplots();ax.axis('off')
    ax.text(.01,.98,comparison_text(result),va='top',fontsize=8,wrap=True)
    figure._emcd_display_metadata=dict(kind='multisite details',method=method)
    return []
