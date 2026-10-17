"""Analyze only calculated full-benchmark data; never synthesize voltage curves."""
from pathlib import Path
import csv,json,shutil
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from io import BytesIO
import ni_double_channeling_full_benchmark as run

ROOT=run.ROOT
METRIC='prb_relative_dichroism_percent'


def peaks(values):
    x=np.asarray(values)
    return np.flatnonzero((x[1:-1]>x[:-2])&(x[1:-1]>=x[2:]))+1


def analyze():
    summaries=[];brackets=[];differences=[];all_rows=[];elastic=[]
    for zone in ('001','017'):
        c=run.context(zone);xi=c['model'].elastic.extinction_distance_nm((2,0,0))
        rows=list(csv.DictReader((ROOT/zone/'results.csv').open()))
        for r in rows:
            for k in r:
                if k not in ('zone','method','edge'):r[k]=float(r[k])
        all_rows.extend(rows)
        for method in run.METHODS:
            for edge in ('L3','L2'):
                r=[v for v in rows if v['method']==method and v['edge']==edge]
                t=np.array([x['thickness_nm'] for x in r]);y=np.array([x[METRIC] for x in r])
                idx=int(np.nanargmax(abs(y)));tp=t[idx]
                other=next(v for v in rows if v['method']==method and v['edge']!=edge and v['thickness_nm']==tp)
                summaries.append(dict(zone=zone,method=method,edge=edge,maximum_absolute_percent=abs(y[idx]),
                    signed_percent_at_sampled_maximum=y[idx],thickness_nm=tp,other_edge_percent=other[METRIC],
                    xi_200_nm=xi,normalized_peak_thickness=tp/xi,
                    absolute_contrast_local_maxima_nm=json.dumps(t[peaks(np.nan_to_num(abs(y),nan=-np.inf))].tolist())))
                for i in range(1,len(t)-1):
                    if y[i]*y[i+1]<0:brackets.append(dict(zone=zone,method=method,edge=edge,left_nm=t[i],right_nm=t[i+1],left_percent=y[i],right_percent=y[i+1]))
        for t in run.THICKNESSES:
            for channel in ('entrance','double'):
                for edge in ('L3','L2'):
                    a=next(v for v in rows if v['method']=='bw_'+channel and v['edge']==edge and v['thickness_nm']==t)
                    b=next(v for v in rows if v['method']=='ms_'+channel and v['edge']==edge and v['thickness_nm']==t)
                    keys=('I_A_plus','I_B_plus','I_A_minus','I_B_minus')
                    scale=max(abs(a[k]) for k in keys)
                    differences.append(dict(zone=zone,thickness_nm=t,channeling=channel,edge=edge,
                        max_raw_absolute=max(abs(a[k]-b[k]) for k in keys),
                        max_raw_relative=max(abs(a[k]-b[k])/max(abs(a[k]),abs(b[k])) for k in keys) if scale>0 else np.nan,
                        prb_ms_minus_bw_pp=b[METRIC]-a[METRIC],D_mag_absolute=abs(b['D_mag']-a['D_mag']),
                        D_even_absolute=abs(b['D_even']-a['D_even'])))
        with np.load(ROOT/zone/'results.npz') as f:
            idx=list(map(tuple,f['hkl'])).index((2,0,0))
            zero=list(map(tuple,f['hkl'])).index((0,0,0))
            for method in ('bw','ms'):
                population=f['elastic_'+method][:,idx];local=peaks(population)
                elastic.append(dict(zone=zone,method=method,xi_200_nm=xi,
                    sampled_200_population_maxima_nm=f['thickness_nm'][local].tolist(),
                    sampled_peak_spacings_nm=np.diff(f['thickness_nm'][local]).tolist()))
    run.study.base.write_csv(ROOT/'summary.csv',summaries)
    run.study.base.write_json(ROOT/'sign_reversal_brackets.json',brackets)
    if brackets:run.study.base.write_csv(ROOT/'sign_reversal_brackets.csv',brackets)
    run.study.base.write_csv(ROOT/'bw_ms_discrepancies.csv',differences)
    run.study.base.write_json(ROOT/'elastic_periods.json',elastic)
    return all_rows,summaries,differences


def save(fig,name):
    fig.tight_layout()
    for ext in ('png','svg'):
        b=BytesIO();fig.savefig(b,format=ext,dpi=170);(ROOT/(name+'.'+ext)).write_bytes(b.getvalue())


def figures(rows):
    styles={'bw_entrance':('tab:blue','-'),'ms_entrance':('tab:blue','--'),
        'bw_double':('tab:orange','-'),'ms_double':('tab:orange','--')}
    for number,edge in ((1,'L3'),(2,'L2')):
        f=Figure(figsize=(11,4));FigureCanvasAgg(f)
        for col,zone in enumerate(('001','017')):
            ax=f.add_subplot(1,2,col+1)
            for method,(color,ls) in styles.items():
                r=[v for v in rows if v['zone']==zone and v['edge']==edge and v['method']==method]
                ax.plot([v['thickness_nm'] for v in r],[v[METRIC] for v in r],color=color,ls=ls,label=method)
            ax.set(xlabel='Thickness (nm)',ylabel='Signed raw PRB dichroism (%)',title=f'Ni [{zone}] {edge} | 200 kV',xlim=(0,100))
            ax.axhline(0,color='.5',lw=.6);ax.legend(fontsize=7)
        save(f,f'figure_{number}_{edge}_thickness')
    f=Figure(figsize=(11,7));FigureCanvasAgg(f)
    for iz,zone in enumerate(('001','017')):
        for ie,edge in enumerate(('L3','L2')):
            ax=f.add_subplot(2,2,iz*2+ie+1)
            for solver in ('bw','ms'):
                r=[v for v in rows if v['zone']==zone and v['edge']==edge and v['method']==solver+'_double']
                ax.plot([v['thickness_nm'] for v in r],[v[METRIC] for v in r],'-' if solver=='bw' else '--',label=solver)
            ax.set(xlabel='Thickness (nm)',ylabel='Raw PRB (%)',title=f'[{zone}] {edge} double');ax.legend()
    save(f,'figure_3_BW_MS_double')
    f=Figure(figsize=(11,7));FigureCanvasAgg(f)
    for iz,zone in enumerate(('001','017')):
        for ie,edge in enumerate(('L3','L2')):
            ax=f.add_subplot(2,2,iz*2+ie+1)
            for solver in ('bw','ms'):
                a=[v for v in rows if v['zone']==zone and v['edge']==edge and v['method']==solver+'_entrance']
                b=[v for v in rows if v['zone']==zone and v['edge']==edge and v['method']==solver+'_double']
                ax.plot([v['thickness_nm'] for v in a],[y[METRIC]-x[METRIC] for x,y in zip(a,b)],'-' if solver=='bw' else '--',label=solver)
            ax.set(xlabel='Thickness (nm)',ylabel='Double minus entrance (pp)',title=f'[{zone}] {edge}');ax.axhline(0,color='.5',lw=.6);ax.legend()
    save(f,'figure_4_double_minus_entrance')
    f=Figure(figsize=(11,7));FigureCanvasAgg(f)
    for iz,zone in enumerate(('001','017')):
        for col,key in enumerate(('D_mag','D_even')):
            ax=f.add_subplot(2,2,iz*2+col+1)
            for method in ('bw_double','ms_double'):
                r=[v for v in rows if v['zone']==zone and v['edge']=='L3' and v['method']==method]
                ax.plot([v['thickness_nm'] for v in r],[v[key] for v in r],'-' if method.startswith('bw') else '--',label=method)
            ax.set(xlabel='Thickness (nm)',ylabel=key+' (relative intensity)',title=f'[{zone}] L3 reversal components');ax.legend(fontsize=8)
            if key=='D_even':ax.set_ylim(-1e-14,1e-14);ax.text(.03,.9,'Symmetry: roundoff only',transform=ax.transAxes)
    save(f,'figure_5_magnetic_even')
    f=Figure(figsize=(11,4));FigureCanvasAgg(f)
    for iz,zone in enumerate(('001','017')):
        xi=run.context(zone)['model'].elastic.extinction_distance_nm((2,0,0));ax=f.add_subplot(1,2,iz+1)
        for method,(color,ls) in styles.items():
            r=[v for v in rows if v['zone']==zone and v['edge']=='L3' and v['method']==method]
            ax.plot([v['thickness_nm']/xi for v in r],[v[METRIC] for v in r],color=color,ls=ls,label=method)
        ax.set(xlabel='t / xi_200 (200 kV only)',ylabel='L3 raw PRB (%)',title=f'[{zone}] | xi={xi:.5f} nm');ax.legend(fontsize=7)
    save(f,'figure_7_normalized_thickness_200kv_only')
    f=Figure(figsize=(11,7));FigureCanvasAgg(f)
    for iz,zone in enumerate(('001','017')):
        with np.load(ROOT/zone/'results.npz') as data:
            hkl=list(map(tuple,data['hkl']));t=data['thickness_nm']
            for ib,h in enumerate(((0,0,0),(2,0,0))):
                ax=f.add_subplot(2,2,iz*2+ib+1)
                for solver in ('bw','ms'):ax.plot(t,data['elastic_'+solver][:,hkl.index(h)],'-' if solver=='bw' else '--',label=solver)
                ax.set(xlabel='Thickness (nm)',ylabel='Incoming elastic exit population',title=f'[{zone}] {h}');ax.legend()
    save(f,'figure_8_elastic_populations')
    if (ROOT/'convergence.csv').exists():
        controls=list(csv.DictReader((ROOT/'convergence.csv').open()));names=list(dict.fromkeys(v['control'] for v in controls))
        f=Figure(figsize=(12,7));FigureCanvasAgg(f)
        for iz,zone in enumerate(('001','017')):
            for col,key in enumerate(('prb_change_pp','raw_max_relative')):
                ax=f.add_subplot(2,2,iz*2+col+1)
                y=[max([abs(float(v[key])) for v in controls if v['zone']==zone and v['control']==n] or [np.nan]) for n in names]
                ax.bar(np.arange(len(names)),y);ax.set_xticks(np.arange(len(names)),names,rotation=35,ha='right')
                ax.set(ylabel=key,title=f'[{zone}] maximum over checked t/edges/methods')
                ax.axhline(.01 if col==0 else .001,color='red',ls=':',label='Screening tolerance');ax.legend(fontsize=7)
        save(f,'figure_10_convergence')


def angular_maps():
    from emcd_sim.emcd_angular_plots import decorate_reciprocal_map
    from emcd_sim.double_channeling import double_channeling_response
    from emcd_sim.multislice_double_channeling import multislice_double_channeling_response
    folder=ROOT/'angular_maps';folder.mkdir(exist_ok=True)
    reference=Path('outputs/ni_double_channeling_ms_validation')
    for i,edge in enumerate(('L3','L2')):
        for ext in ('png','svg'):
            shutil.copy2(reference/f'figure_{5+i}_{edge}_maps.{ext}',folder/f'figure_9_001_{edge}.{ext}')
    shutil.copy2(reference/'angular_maps.npz',folder/'001_maps.npz')
    c=run.context('017');q=np.linspace(-.7,.7,49);qx,qy=np.meshgrid(q,q,indexing='xy')
    query,inverse,sign=run.folded_pixels(qx.ravel(),qy.ravel())
    arrays=dict(qx=qx,qy=qy,energy_ev=run.ENERGIES);metadata=[]
    for ie,e in enumerate(run.ENERGIES):
        def produce():
            bw=run.detector_batches(lambda qq:double_channeling_response(c['model'].elastic,float(e),qq,12.,method='numerical',depth_steps=257),query,4)
            ms,info=run.detector_batches(lambda qq:multislice_double_channeling_response(c['model'].elastic,float(e),qq,12.,
                fft_grid=32,potential_cutoff=2.2,depth_steps=257,projected_geometry=c['projected_geometry']),query,4)
            return dict(bw=run.unfold(bw,inverse,sign),ms=run.unfold(ms,inverse,sign),
                diagnostics_json=np.array(json.dumps(run.study.base.clean(info))))
        params=run.parameters(c,run.detector_grid(c),12.)
        params.update(map_grid=49,map_halfwidth=.7,energy_ev=float(e))
        data=run.cached(folder/f'017_response_{ie}.npz',params,produce)
        t=c['ts'][0].tensor_angstrom2_per_ev[ie];maps=[]
        for method in ('bw','ms'):
            even=np.einsum('pab,ab->p',data[method],t.real).real.reshape(qx.shape)
            odd=np.einsum('pab,ab->p',data[method],1j*t.imag).real.reshape(qx.shape)
            maps.append((odd,even,even+odd))
            for key,v in zip(('magnetic','nonmagnetic','total'),maps[-1]):arrays[f'{method}_{ie}_{key}']=v
        fig=Figure(figsize=(13,7));FigureCanvasAgg(fig)
        for row,method in enumerate(('BW','MS')):
            for col,label in enumerate(('Magnetic odd','Reversal even','Total +M')):
                ax=fig.add_subplot(2,3,row*3+col+1)
                limit=max(float(abs(maps[j][col]).max()) for j in (0,1))
                im=ax.imshow(maps[row][col],origin='lower',extent=(-.7,.7,-.7,.7),interpolation='nearest',
                    cmap='RdBu_r' if col==0 else 'viridis',vmin=-limit if col==0 else 0,vmax=limit)
                ax.set(title=method+' '+label,xlabel='qx (cycles/A)',ylabel='qy (cycles/A)')
                decorate_reciprocal_map(ax,c['model'],(-.7,.7,-.7,.7),zone_axis=(0,1,7))
                fig.colorbar(im,ax=ax,shrink=.75)
        edge=('L3','L2')[ie];fig.suptitle(f'Ni [017] exact (200) | 200 kV, 12 nm | {edge} {e:.4f} eV')
        save(fig,f'figure_9_017_{edge}')
        metadata.append(json.loads(str(data['diagnostics_json'])))
    np.savez_compressed(folder/'017_maps.npz',**arrays)
    run.study.base.write_json(folder/'provenance.json',dict(secondary_diagnostics=metadata,
        primary_maps_reused_from=str(reference),primary_reproduction='reference_reproduction.csv',
        map_grid=49,map_halfwidth=.7,thickness_nm=12.))


def metadata():
    from emcd_sim.geometry import electron_wavelength_angstrom
    records={}
    for zone in ('001','017'):
        c=run.context(zone);d=run.detector_grid(c);e=c['model'].elastic
        records[zone]=dict(run.parameters(c,d,0.),
            magnetization_crystal=[0.,0.,1.],magnetization_local=c['R']@np.array([0.,0.,1.]),
            nominal_zone_axis=c['settings'].zone,tilt_mrad=c['settings'].tilt,
            transmitted_q_cycles_per_angstrom=[0.,0.],projected_ZA_q_cycles_per_angstrom=-e.microscope.incident_k_xy,
            wavelength_angstrom=electron_wavelength_angstrom(200.),xi_200_nm=e.extinction_distance_nm((2,0,0)),
            outgoing_energies_kv=[200.-float(x)/1000 for x in run.ENERGIES],
            outgoing_wavelengths_angstrom=[electron_wavelength_angstrom(200.-float(x)/1000) for x in run.ENERGIES],
            ionization='independent events, integrated raw intensities before percentages',
            raw_intensity_scale='relative per-atom units; not calibrated DDSCS')
    run.study.base.write_json(ROOT/'study_metadata.json',dict(geometries=records,
        voltage_status={'200':'calculated','100':'not calculated','300':'not calculated'},
        base_commit=json.loads((ROOT/'provenance.json').read_text())['base_commit'],
        software_commit='See delivery_provenance.json for final development commit',
        physical_model='projected IAM, finite ZOLZ, approximate XMCD dipole tensor, frozen longitudinal transfer'))


def main():
    assert json.loads((ROOT/'checkpoint_a.json').read_text())['complete']
    rows,summary,differences=analyze();figures(rows);angular_maps();metadata()
    gate=json.loads((ROOT/'convergence_gate.json').read_text()) if (ROOT/'convergence_gate.json').exists() else None
    if gate is not None and not gate['passed']:
        (ROOT/'figure_6_voltage_comparison_NOT_RUN.txt').write_text('100/300 kV double-channel scans were not run because the 200 kV convergence gate failed. No comparison figure is fabricated.\n')
    print('Analyzed only the completed 200 kV scans; voltage status:',gate,flush=True)


if __name__=='__main__':main()
