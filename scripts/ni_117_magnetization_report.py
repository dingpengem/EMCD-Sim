"""Analysis only: tables/figures from completed magnetic-axis checkpoints."""
from pathlib import Path
import csv,json,os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from ni_117_magnetization import OUT,ENERGIES,sha,write_json,write_npz
from emcd_sim.gui.prb_benchmark import relative_dichroism_percent

AXES=('crystal001','incident')


def fraction(a,b):
    norm=np.linalg.norm(b)
    return float(np.linalg.norm(a)/norm) if norm else None


def load():
    records=[]
    for meta in sorted((OUT/'cases').glob('*/complete.json')):
        d=json.loads(meta.read_text(encoding='utf-8'));path=meta.with_name('arrays.npz')
        if sha(path)!=d['arrays_sha256']:raise ValueError('Checkpoint checksum mismatch: '+str(path))
        with np.load(path) as f:a={k:f[k].copy() for k in f.files}
        d['_checkpoint_directory']=str(meta.parent.resolve())
        records.append((d,a))
    return records


def tables(records):
    rows=[];circle_rows=[];archive={}
    for d,a in records:
        ident=d['identity'];p=ident['profile'];s=ident['settings'];label=d['label']
        archive[label+'__q']=a['q'];archive[label+'__angle']=a['angle'];archive[label+'__circle_q']=a['circle_q']
        for name in AXES:
            for ie,(edge,energy) in enumerate(zip(('L3','L2'),ENERGIES)):
                M=a[name+'__M'][ie];N=a[name+'__N'][ie];circle=M[a['circle_index']];cn=N[a['circle_index']]
                mirror=(-np.arange(len(circle)))%len(circle);even=(circle+circle[mirror])/2;odd=(circle-circle[mirror])/2
                mm=M[a['map_index']].reshape(p['map_grid'],p['map_grid']);nn=N[a['map_index']].reshape(mm.shape)
                raw=[a[name+'__'+sign][ie,a['detector_index']]@a['detector_weights'].T*float(a['dq2']) for sign in ('plus','minus')]
                na,nb=(raw[0]+raw[1])/2;ma,mb=(raw[0]-raw[1])/2;den=na+nb
                axis=d['magnetizations'][name]
                row=dict(case=label,profile=p['name'],support=s['basis_mode'],channeling=ident['channeling'],thickness_nm=s['thickness'],
                    method=ident['method'],axis=name,edge=edge,energy_ev=energy,beam_count=d['beam_count'],beam_cutoff=p['beam'],potential_cutoff=p['potential'],
                    fft_grid=p['fft'],depth=p['depth'],max_slice_nm=p['step'],map_grid=p['map_grid'],circle_samples=p['circle'],detector_grid=p['detector_grid'],subpixels=p['subpixels'],
                    local_mx=axis['local'][0],local_my=axis['local'][1],local_mz=axis['local'][2],longitudinal=axis['longitudinal'],transverse=axis['transverse'],angle_to_incident_deg=axis['angle_to_incident_deg'],
                    circle_even_fraction=fraction(even,circle),circle_odd_fraction=fraction(odd,circle),circle_magnetic_l2=float(np.linalg.norm(circle)),
                    circle_even_l2=float(np.linalg.norm(even)),circle_odd_l2=float(np.linalg.norm(odd)),
                    circle_magnetic_rms=float(np.sqrt(np.mean(circle**2))),circle_even_rms=float(np.sqrt(np.mean(even**2))),circle_odd_rms=float(np.sqrt(np.mean(odd**2))),
                    circle_nonmag_odd_fraction=fraction((cn-cn[mirror])/2,cn),map_even_fraction=fraction((mm+mm[::-1])/2,mm),
                    N_A=na,N_B=nb,M_A=ma,M_B=mb,I_A_plus=raw[0][0],I_B_plus=raw[0][1],I_A_minus=raw[1][0],I_B_minus=raw[1][1],
                    D_mag=ma-mb,D_nonmag=na-nb,Sigma_ref=den,A_mag_percent=100*(ma-mb)/den,A_nonmag_percent=100*(na-nb)/den,
                    PRB_percent=float(relative_dichroism_percent(raw[0][0],raw[0][1])[0]),
                    detector_area_A=float(a['detector_areas'][0]),detector_area_B=float(a['detector_areas'][1]),elapsed_seconds=d['elapsed_seconds'])
                rows.append(row)
                archive[label+'__'+name+'__'+edge+'__M']=mm;archive[label+'__'+name+'__'+edge+'__N']=nn
                archive[label+'__'+name+'__'+edge+'__I_plus']=a[name+'__plus'][ie,a['map_index']].reshape(mm.shape)
                archive[label+'__'+name+'__'+edge+'__I_minus']=a[name+'__minus'][ie,a['map_index']].reshape(mm.shape)
                archive[label+'__'+name+'__'+edge+'__mirror_even']=(mm+mm[::-1])/2
                archive[label+'__'+name+'__'+edge+'__mirror_odd']=(mm-mm[::-1])/2
                archive[label+'__'+name+'__'+edge+'__circle_M']=circle
                archive[label+'__'+name+'__'+edge+'__circle_N']=cn
                archive[label+'__'+name+'__'+edge+'__circle_total']=a[name+'__plus'][ie,a['circle_index']]
                archive[label+'__'+name+'__'+edge+'__circle_even']=even
                archive[label+'__'+name+'__'+edge+'__circle_odd']=odd
                for i,theta in enumerate(a['angle']):
                    circle_rows.append(dict(case=label,axis=name,edge=edge,theta_degrees=float(np.degrees(theta)),qx=a['circle_q'][i,0],qy=a['circle_q'][i,1],
                        M=circle[i],minus_M_mirror=-circle[mirror[i]],M_even=even[i],M_odd=odd[i],N=cn[i],total_plus=a[name+'__plus'][ie,a['circle_index'][i]]))
    for filename,values in [('comparison.csv',rows),('thales_circle.csv',circle_rows)]:
        with (OUT/filename).open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,list(values[0]));w.writeheader();w.writerows(values)
    write_npz(OUT/'comparison.npz',**archive)
    from emcd_sim.geometry import electron_wavelength_angstrom
    write_json(OUT/'cases_index.json',[dict(label=d['label'],metadata=str(Path(os.path.relpath(d['_checkpoint_directory'],OUT))/'complete.json'),identity=d['identity'],
        frame=d['frame'],magnetizations={k:v for k,v in d['magnetizations'].items() if k in AXES},
        wavelength_angstrom=electron_wavelength_angstrom(d['identity']['settings']['voltage']),
        za_q=(-np.asarray(d['identity']['settings']['tilt'])*.001/electron_wavelength_angstrom(d['identity']['settings']['voltage'])).tolist(),
        detector_centers=a['centers'],detector_radius=.16*np.sqrt(8)/3.524,integration='fractional') for d,a in records])
    return rows


def numerical(records,rows):
    lookup={d['label']:(d,a) for d,a in records};comparisons=[]
    for row in rows:
        if row['method']!='bloch':continue
        other=next((r for r in rows if r['case']==row['case'].replace('_bloch','_fft-multislice') and r['axis']==row['axis'] and r['edge']==row['edge']),None)
        if other:
            comparisons.append(dict(factor='BW_MS',profile=row['profile'],support=row['support'],channeling=row['channeling'],thickness_nm=row['thickness_nm'],axis=row['axis'],edge=row['edge'],
                delta_A_mag_pp=abs(row['A_mag_percent']-other['A_mag_percent']),raw_relative_max=max(abs(row[k]-other[k])/max(abs(row[k]),abs(other[k]),1e-30) for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')),
                delta_PRB_pp=abs(row['PRB_percent']-other['PRB_percent']),
                delta_circle_even_fraction=abs(row['circle_even_fraction']-other['circle_even_fraction'])))
    for method in ('bloch','fft-multislice'):
        first='refined_full_double_t8_'+method;second='combined_full_double_t8_'+method
        if second not in lookup:continue
        d,a=lookup[first];e,b=lookup[second]
        for name in AXES:
            for ie,edge in enumerate(('L3','L2')):
                x=next(r for r in rows if r['case']==first and r['axis']==name and r['edge']==edge)
                y=next(r for r in rows if r['case']==second and r['axis']==name and r['edge']==edge)
                circle=a[name+'__M'][ie,a['circle_index']];fine=b[name+'__M'][ie,b['circle_index']][::2]
                comparisons.append(dict(factor='combined',profile=method,support='full',channeling='double',thickness_nm=8,axis=name,edge=edge,
                    delta_A_mag_pp=abs(x['A_mag_percent']-y['A_mag_percent']),
                    delta_PRB_pp=abs(x['PRB_percent']-y['PRB_percent']),
                    raw_relative_max=max(abs(x[k]-y[k])/max(abs(x[k]),abs(y[k]),1e-30) for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')),
                    delta_circle_even_fraction=abs(x['circle_even_fraction']-y['circle_even_fraction']),circle_common_point_relative_l2=fraction(circle-fine,fine),
                    combined_circle_rms_relative_change=abs(np.linalg.norm(circle)/np.sqrt(len(circle))-np.linalg.norm(b[name+'__M'][ie,b['circle_index']])/np.sqrt(len(b['circle_index'])))/(np.linalg.norm(circle)/np.sqrt(len(circle)))))
    for row in comparisons:row['detector_gate_passed']=bool(row['delta_A_mag_pp']<=.01 and row['delta_PRB_pp']<=.01 and row['raw_relative_max']<=.001)
    keys=list(dict.fromkeys(k for r in comparisons for k in r))
    with (OUT/'numerical_comparisons.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,keys);w.writeheader();w.writerows(comparisons)
    write_json(OUT/'numerical_summary.json',dict(thresholds=dict(dichroism_pp=.01,relative_raw=.001),comparisons=comparisons,
        warning='Joint profile plus independent prior controls; not global spatial/thickness convergence. Circle fraction is an L2 norm fraction, not detector asymmetry.'))


def decorate(ax,a):
    g=np.sqrt(8)/3.524
    ax.add_patch(Circle((g/2,0),g/2,fill=False,ls=':',color='teal',label='Thales circle'))
    ax.plot(0,0,'kx',label='000');ax.plot(g,0,'rs',mfc='none',label='(2,-2,0)');ax.plot(g/2,0,'*',color='gold',mec='k',label='ZA [117]')
    for label,center in zip(('A','B'),a['centers']):
        ax.add_patch(Circle(center,.16*g,fill=False,color='black',ls='--'));ax.annotate(label,center,ha='center',va='center',fontsize=8)
    ax.set(xlabel='qx (cycles/Å)',ylabel='qy (cycles/Å)',aspect='equal')


def save(fig,name):
    for ext in ('png','svg'):fig.savefig(OUT/(name+'.'+ext),dpi=150)
    plt.close(fig)



if __name__=='__main__':
    data=load();rows=tables(data);numerical(data,rows)
    print('Analyzed',len(data),'completed response jobs;',len(rows),'magnetic-axis/edge rows')
