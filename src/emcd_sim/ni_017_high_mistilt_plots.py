"""Figures from saved X/Y arrays only; no scattering calculations."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .ni_017_high_mistilt_analysis import load_cases,metric_rows
from .ni_017_high_mistilt_xy import model,tag,GEO
from .ni_mistilt_series import METHODS,EDGES
from .emcd_angular_plots import decorate_reciprocal_map

FIELDS=('I_mag','I_nonmag','I_plus','D_raw','D_corrected','D_nonmag_residual')
NAMES=('Magnetic odd','Nonmagnetic even','Total +M','Raw paired difference','Corrected paired difference','Scaled even residual')


def plots(root,cfg):
    manifest,cases=load_cases(root);rows=metric_rows(cases);pairs=list(cases);first=cases[pairs[0]][0]
    half=(first['qx'][0,1]-first['qx'][0,0])/2
    extent=(first['qx'].min()-half,first['qx'].max()+half,first['qy'].min()-half,first['qy'].max()+half)
    limits={(key,ei):max(np.nanmax(abs(d['map__'+key][:,ei])) for d,s,m in cases.values()) for key in FIELDS for ei in range(2)}
    for ei in range(2):limits['D_raw',ei]=limits['D_corrected',ei]=max(limits['D_raw',ei],limits['D_corrected',ei])
    models={p:model(cfg,*p) for p in pairs}
    def draw(ax,p,mi,ei,key):
        signed=key not in ('I_nonmag','I_plus');lim=max(limits[key,ei],1e-30)
        im=ax.imshow(cases[p][0]['map__'+key][mi,ei],origin='lower',extent=extent,interpolation='nearest',
            cmap='RdBu_r' if signed else 'viridis',vmin=-lim if signed else 0,vmax=lim)
        decorate_reciprocal_map(ax,models[p],extent,target_hkl=(2,0,0),zone_axis=(0,1,7))
        ax.tick_params(labelsize=6);ax.xaxis.label.set_size(7);ax.yaxis.label.set_size(7)
        return im
    # Individual figures use the same global scale as every comparison series.
    for n,p in enumerate(pairs):
        d,s,meta=cases[p];folder=root/'cases'/tag(*p);g=meta['geometry']
        for ei,edge in enumerate(EDGES):
            fig,axes=plt.subplots(2,6,figsize=(20,7),layout='constrained')
            for col,key in enumerate(FIELDS):
                for mi in range(2):
                    im=draw(axes[mi,col],p,mi,ei,key);axes[mi,col].set_title(METHODS[mi]+'\n'+NAMES[col],fontsize=8)
                fig.colorbar(im,ax=axes[:,col].tolist(),shrink=.65)
            fig.suptitle(f'Ni [017] {edge} {d["selected_energy_ev"][ei]:.3f} eV | offsets ({p[0]:+.4g},{p[1]:+.4g}) mrad | absolute ({g["theta_x_mrad"]:.4f},{g["theta_y_mrad"]:.4f}) mrad')
            fig.savefig(folder/f'{edge}_angular_maps.png',dpi=105);plt.close(fig)
        fig,axes=plt.subplots(2,3,figsize=(14,8),sharex=True,sharey='col',layout='constrained')
        for mi in range(2):
            for col,keys in enumerate((('I_A_plus','I_B_plus','I_A_minus','I_B_minus'),('D_raw','D_mag','D_nonmag'),('D_corrected','D_mag','D_mag_processed_obs','D_nonmag_residual_obs'))):
                ax=axes[mi,col]
                for k in keys:ax.plot(d['energy_ev'],s[k][mi],label=k,lw=1)
                for edge,en in zip(EDGES,d['selected_energy_ev']):ax.axvline(en,ls=':',color='.5');ax.text(en,.98,edge,transform=ax.get_xaxis_transform(),va='top',fontsize=7)
                ax.axvspan(878,882,color='.5',alpha=.15);ax.set(xlabel='Native source energy (eV)',ylabel='Relative intensity',title=METHODS[mi]+(f' alpha={s["alpha"][mi]:.7f}' if col==2 else ''))
                ax.legend(fontsize=6);ax.grid(alpha=.2)
        fig.suptitle(f'Offsets ({p[0]:+.6g},{p[1]:+.6g}) mrad | absolute tilt ({g["theta_x_mrad"]:.6f},{g["theta_y_mrad"]:.6f}) mrad\ns200={g["s200_inv_angstrom"]:+.8f} inverse A; no energy calibration or peak rescaling')
        fig.savefig(folder/'virtual_detector_eels.png',dpi=110);plt.close(fig)
        fig,axes=plt.subplots(2,2,figsize=(11,8),layout='constrained')
        gv=models[p].elastic.reciprocal_vectors_xy;h=models[p].elastic.beams.hkl
        for mi,diag in enumerate(meta['diffraction']):
            for col,key in enumerate(('exit_populations','depth_average_populations')):
                ax=axes[mi,col];pop=np.array(diag[key]);im=ax.scatter(gv[:,0],gv[:,1],c=pop,s=10+300*pop,cmap='magma',vmin=0,vmax=1)
                for (gx,gy),hh in zip(gv,h):
                    if pop[h.index(hh)]>.005:ax.annotate(str(hh),(gx,gy),fontsize=6)
                bounds=(gv[:,0].min()-.2,gv[:,0].max()+.2,gv[:,1].min()-.2,gv[:,1].max()+.2)
                decorate_reciprocal_map(ax,models[p],bounds,target_hkl=(2,0,0),zone_axis=(0,1,7))
                ax.set(title=METHODS[mi]+' '+key);fig.colorbar(im,ax=ax,label='Incident-intensity fraction')
        fig.suptitle(f'Elastic diffraction: offsets {p} mrad; finite full 2D basis')
        fig.savefig(folder/'diffraction_pattern.png',dpi=110);plt.close(fig)
        print(f'Plots {n+1}/{len(pairs)}: {p}',flush=True)
    # One-dimensional angular mosaics and line plots.
    for scan in ('x','y'):
        if scan not in manifest['scans']:continue
        points=[tuple(p) for p in manifest['scans'][scan] if tuple(p) in cases];coord=[p[0 if scan=='x' else 1] for p in points]
        base=root/('scan_'+scan);summary=base/'summary_figures';summary.mkdir(parents=True,exist_ok=True)
        for ei,edge in enumerate(EDGES):
            for key in FIELDS:
                sub=base/('magnetic_maps' if key=='I_mag' else 'nonmagnetic_maps' if key=='I_nonmag' else 'summary_figures');sub.mkdir(parents=True,exist_ok=True)
                for mi,method in enumerate(METHODS):
                    nc=4;nr=int(np.ceil(len(points)/nc));fig,axes=plt.subplots(nr,nc,figsize=(12,3.3*nr),squeeze=False,layout='constrained')
                    for ax,p in zip(axes.flat,points):
                        im=draw(ax,p,mi,ei,key);label=''
                        if p==(0.,0.):label=' (200) reference'
                        if scan=='x' and abs(p[0]+GEO.bragg_tilt(cfg.acceleration_kv))<1e-8:label=' ZA incidence'
                        if scan=='x' and abs(p[0]-GEO.bragg_tilt(cfg.acceleration_kv))<1e-8:label=' (400) Bragg'
                        ax.set_title(f'offsets ({p[0]:+.4g},{p[1]:+.4g}) mrad'+label,fontsize=7)
                    for ax in list(axes.flat)[len(points):]:ax.set_visible(False)
                    fig.colorbar(im,ax=list(axes.flat)[:len(points)],shrink=.6,label='Relative intensity; common global scale')
                    fig.suptitle(f'Ni [017] {edge} {key} | {method} | {scan}-scan')
                    fig.savefig(sub/f'{edge}_{key}_{method}.png',dpi=100);plt.close(fig)
        keys=('magnetic_asymmetry','magnetic_abs','shot_noise_proxy','nonmagnetic_asymmetry','raw_asymmetry_sigma_ref','corrected_asymmetry','alpha','magnetic_processing_signed_change','bw_ms_magnetic_map_l2_relative')
        fig,axes=plt.subplots(3,3,figsize=(14,11),layout='constrained')
        for ax,key in zip(axes.flat,keys):
            for method in METHODS:
                for edge in EDGES:
                    vals=[next(r[key] for r in rows if (r['delta_x_mrad'],r['delta_y_mrad'])==p and r['method']==method and r['edge']==edge) for p in points]
                    ax.plot(coord,vals,'o-' if method==METHODS[0] else 'x--',ms=3,label=method+' '+edge)
            units='fraction' if 'asymmetry' in key or 'relative' in key else 'dimensionless' if key=='alpha' else 'relative shot-noise proxy' if key=='shot_noise_proxy' else 'relative intensity'
            ax.axvline(0,color='.5',ls=':');ax.set(xlabel='Bragg offset delta_'+scan+' (mrad)',ylabel=units,title=key);ax.grid(alpha=.2);ax.legend(fontsize=6)
            if scan=='x':
                for v in (GEO.bragg_tilt(cfg.acceleration_kv),-GEO.bragg_tilt(cfg.acceleration_kv)):ax.axvline(v,color='.7',ls=':')
        fig.savefig(summary/f'emcd_vs_{scan}_mistilt.png',dpi=130);fig.savefig(root/'aggregate'/f'emcd_vs_{scan}_mistilt.png',dpi=130);plt.close(fig)
        fig,axes=plt.subplots(2,2,figsize=(13,8),layout='constrained')
        colors=plt.cm.viridis(np.linspace(0,1,len(points)))
        for mi in range(2):
            for ei,edge in enumerate(EDGES):
                ax=axes[mi,ei]
                for color,p in zip(colors,points):
                    d,s,_=cases[p];ax.plot(d['energy_ev'],s['D_mag'][mi],color=color,label=f'{p[0 if scan=="x" else 1]:+.4g}')
                en=first['selected_energy_ev'][ei];ax.set(xlim=(en-5,en+5),xlabel='Native energy (eV)',ylabel='Magnetic odd difference (a.u.)',title=METHODS[mi]+' '+edge)
                ax.axvline(en,color='.5',ls=':');ax.legend(fontsize=6,ncol=3);ax.grid(alpha=.2)
        fig.suptitle('Full spectra, displayed in separate edge windows; no peak rescaling; delta_'+scan+' mrad')
        fig.savefig(summary/'magnetic_eels_overlay.png',dpi=120);plt.close(fig)
    if 'y' in manifest['scans']:
        pos=sorted([p for p in pairs if p[0]==0 and p[1]>0 and (0,-p[1]) in cases],key=lambda p:p[1]);fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
        for mi in range(2):
            for ei,edge in enumerate(EDGES):
                ax=axes[mi,ei]
                for sign in (1,-1):
                    v=[]
                    for p in pos:
                        d,s,_=cases[0,sign*p[1]];i=np.argmin(abs(d['energy_ev']-d['selected_energy_ev'][ei]));v.append(sign*s['D_nonmag'][mi,i])
                    ax.plot([p[1] for p in pos],v,'o-' if sign==1 else 'x--',label='D_even(+y)' if sign==1 else '-D_even(-y)')
                ax.set(xlabel='|delta_y| (mrad)',ylabel='Intrinsic even A-B',title=METHODS[mi]+' '+edge);ax.legend();ax.grid(alpha=.2)
        fig.savefig(root/'scan_y'/'summary_figures'/'mirror_symmetry.png',dpi=120);plt.close(fig)
    xy_plots(root)


def xy_plots(root):
    """Color only calculated orientations; leave unsampled space blank."""
    path=root/'aggregate'/'xy_metrics.npz'
    if not path.exists():return
    with np.load(path,allow_pickle=False) as f:metrics={k:f[k] for k in f.files}
    xs,ys=metrics['delta_x_mrad'],metrics['delta_y_mrad']
    specs=[('magnetic_asymmetry',0),('magnetic_asymmetry',1),('magnetic_abs',0),('magnetic_abs',1),('nonmagnetic_asymmetry',0),('nonmagnetic_asymmetry',1),('raw_asymmetry_sigma_ref',0),('corrected_asymmetry',0),('shot_noise_proxy',0),('shot_noise_proxy',1),('alpha',0),('dominant_competing_depth_average',0),('bw_ms_magnetic_map_l2_relative',0)]
    def heat(ax,key,ei,mi):
        a=metrics[key][:,:,mi,ei];signed=key.endswith('asymmetry') or key=='raw_asymmetry_sigma_ref';lim=max(np.nanmax(abs(metrics[key][...,ei])),1e-30)
        xx,yy=np.meshgrid(xs,ys)
        im=ax.scatter(xx.ravel(),yy.ravel(),c=a.ravel(),marker='s',s=650,cmap='RdBu_r' if signed else 'viridis',vmin=-lim if signed else np.nanmin(metrics[key][...,ei]),vmax=lim)
        ax.plot(xx.ravel(),yy.ravel(),'k.',ms=2);ax.plot(0,0,'kx',ms=7)
        unit='relative proxy' if key=='shot_noise_proxy' else 'dimensionless' if key=='alpha' else 'relative intensity' if key=='magnetic_abs' else 'fraction'
        ax.set(xlabel='delta_x (mrad)',ylabel='delta_y (mrad)',title=METHODS[mi]+' '+EDGES[ei]+'\n'+key,xlim=(xs.min()-3,xs.max()+3),ylim=(ys.min()-5,ys.max()+5));fig.colorbar(im,ax=ax,shrink=.8,label=unit)
    for key,ei in specs:
        category='detectability_maps' if key=='shot_noise_proxy' else 'nonmagnetic_2d_maps' if key=='nonmagnetic_asymmetry' else 'magnetic_2d_maps'
        dest=root/'scan_xy'/category;dest.mkdir(parents=True,exist_ok=True)
        fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
        for mi,ax in enumerate(axes):heat(ax,key,ei,mi)
        fig.suptitle('Calculated XY-grid point values only; no interpolation')
        fig.savefig(dest/f'{EDGES[ei]}_{key}.png',dpi=130);plt.close(fig)
    for filename,selected in [('emcd_xy_heatmaps',[('magnetic_asymmetry',0),('nonmagnetic_asymmetry',0),('shot_noise_proxy',0)]),('raw_corrected_xy',[('raw_asymmetry_sigma_ref',0),('corrected_asymmetry',0)]),('detectability_xy',[('shot_noise_proxy',0),('shot_noise_proxy',1)]),('bw_ms_xy',[('bw_ms_magnetic_map_l2_relative',0),('bw_ms_magnetic_map_l2_relative',1)])]:
        fig,axes=plt.subplots(2,len(selected),figsize=(5*len(selected),8),squeeze=False,layout='constrained')
        for mi in range(2):
            for col,(key,ei) in enumerate(selected):heat(axes[mi,col],key,ei,mi)
        fig.suptitle('Calculated XY-grid point values only; no interpolation')
        fig.savefig(root/'aggregate'/(filename+'.png'),dpi=130);plt.close(fig)
    if (root/'convergence_summary.csv').exists():
        import csv
        records=list(csv.DictReader((root/'convergence_summary.csv').open()))
        poses=list(dict.fromkeys((float(r['delta_x_mrad']),float(r['delta_y_mrad'])) for r in records))
        fig,axes=plt.subplots(2,3,figsize=(16,9),layout='constrained')
        for ei,edge in enumerate(EDGES):
            for col,key in enumerate(('magnetic_difference','nonmagnetic_difference','shot_noise_proxy')):
                ax=axes[ei,col]
                for pc in (2.2,3.2):
                    vals=[float(next(r[key] for r in records if (float(r['delta_x_mrad']),float(r['delta_y_mrad']))==p and r['edge']==edge and r['method']=='bloch' and float(r['beam_cutoff'])==6.5 and float(r['potential_cutoff'])==pc)) for p in poses]
                    ax.plot(range(len(poses)),vals,'o-',label=f'Potential cutoff {pc}; BW121')
                ax.set_xticks(range(len(poses)),[str(p) for p in poses],rotation=40,ha='right',fontsize=7)
                ax.set(xlabel='(delta_x,delta_y) mrad, categorical sampled cases',title=edge+' '+key,ylabel='Relative units');ax.legend(fontsize=7);ax.grid(alpha=.2)
        fig.suptitle('Physical potential sensitivity, common detector grid17; not global convergence')
        fig.savefig(root/'aggregate'/'potential_cutoff_controls.png',dpi=130);plt.close(fig)
