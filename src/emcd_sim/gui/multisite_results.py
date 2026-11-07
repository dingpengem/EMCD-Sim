"""Total-only views of existing multi-site arrays; group comparisons wait for 4C."""
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


def covered_segments(result, energy):
    """Do not draw invented spectral tails across unmodeled inter-edge gaps."""
    intervals = sorted(channel['modeled_window_ev'] for channel in result['metadata']['multisite']['channels'].values()
                       if channel['modeled_window_ev'] is not None)
    merged = []
    for lo,hi in intervals:
        if merged and lo <= merged[-1][1]:merged[-1][1] = max(hi,merged[-1][1])
        else:merged.append([lo,hi])
    return [(energy>=lo)&(energy<=hi) for lo,hi in merged]


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


def draw_totals(figure, result, method, kind, choice):
    r = result.get('methods',{}).get(method,result)
    figure.clear();proxies = []
    if kind == 'eels':
        axes = figure.subplots(4,1,sharex=True);e = r['spectra']['energy_ev'];s = r['spectra']
        panels = [
            ('Raw detector intensities', [('I_A_plus','A +state'),('I_B_plus','B +state'),('I_A_minus','A −state'),('I_B_minus','B −state')]),
            ('Global reversal-even', [('N_A','Even A'),('N_B','Even B')]),
            ('Global reversal-odd', [('M_A','Odd A'),('M_B','Odd B')]),
            ('Detector A − B differences', [('D_raw','Raw +state A−B'),('D_mag','Odd A−B'),('D_nonmag','Even A−B')])]
        for ax,(title,curves) in zip(axes.flat,panels):
            for key,label in curves:
                color = None
                for number,mask in enumerate(covered_segments(r,e)):
                    points = r['config'].energy_scope == 'edges'
                    line, = ax.plot(e[mask],s[key][mask],marker='o' if points or len(e)<4 else None,
                        ls='none' if points else '-',label=label if number == 0 else None,color=color)
                    color = line.get_color()
            ax.set_title(title,fontsize=8);ax.set_ylabel('Relative I',fontsize=8)
            ax.tick_params(labelsize=7);ax.legend(fontsize=6,ncol=2);ax.grid(alpha=.15)
        axes[-1].set_xlabel('Energy loss (eV)',fontsize=8)
    elif kind == 'maps' and r['maps']:
        values = r['maps'][choice];extent = (r['qx'].min(),r['qx'].max(),r['qy'].min(),r['qy'].max())
        for ax,(key,title) in zip(figure.subplots(2,2).flat,[('I_plus','Total +state'),('I_minus','Total −state'),('I_nonmag','Reversal-even'),('I_mag','Reversal-odd')]):
            image = ax.imshow(values[key],origin='lower',extent=extent,cmap='RdBu_r' if key=='I_mag' else 'viridis')
            ax.set(title=title,xlabel='qx (Å⁻¹)',ylabel='qy (Å⁻¹)');figure.colorbar(image,ax=ax,shrink=.75)
    elif kind == 'diffraction':
        from .results import draw_diffraction
        draw_diffraction(figure,result,method,choice=='Depth average')
    else:
        ax = figure.subplots();ax.axis('off');ax.text(.01,.98,comparison_text(result),va='top',fontsize=8,wrap=True)
    sites = r['metadata']['multisite']
    figure.suptitle(f'{material(r)} | {method} {r["config"].channeling_model.title()} Channeling | partial core-edge spectrum\n'
        f'Mean per selected ionizing atom (n={sites["selected_atom_count"]}); active provider '+
        ('−M' if sites['global_reversal'] else '+M')+' states; relative scale\n'+r['metadata']['scientific_status'],fontsize=8)
    if kind=='diffraction':figure.suptitle(f'{material(r)} | {method} complete-crystal incoming elastic intensity; per incident electron',fontsize=8)
    figure._emcd_display_metadata = dict(kind='multisite totals',normalization='per_incident_electron' if kind=='diffraction' else 'mean_per_selected_ionizing_atom',
        spectrum_kind='modeled_partial_core_edge_spectrum',method=method)
    return proxies
