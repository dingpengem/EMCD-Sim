"""Indexed Ni angular maps and EELS presentation of the existing matched result."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np

from .postedge_emcd_maps import METHODS, map_error
from .geometry import Microscope, electron_wavelength_angstrom
from .xmcd_geometry_decomposition import _json_safe
from .xmcd_postedge_normalization import LABEL, _integral


def coordinate_markers(microscope):
    """000-centered q=k_f,perp-k_incident,perp; crystal [001] has k_f,perp=0."""
    return dict(nominal_zone_axis=[0,0,1],tilt_x_mrad=float(microscope.tilt_mrad_xy[0]),
        tilt_y_mrad=float(microscope.tilt_mrad_xy[1]),acceleration_kv=microscope.acceleration_kv,
        electron_wavelength_angstrom=electron_wavelength_angstrom(microscope.acceleration_kv),
        transmitted_q_cycles_per_angstrom=[0.,0.],
        zone_axis_q_cycles_per_angstrom=(-microscope.incident_k_xy).tolist(),
        convention='q_ZA=-k_incident,perp; transmitted beam at q=(0,0)')


def result_coordinate_markers(result):
    """One physical geometry shared by BW and MS; use saved actual tilt."""
    pg=result['metadata']['propagation']
    return {c['condition']:coordinate_markers(Microscope(pg['config']['acceleration_kv'],
        tuple(pg['geometries'][c['condition']]['tilt_mrad_xy']))) for c in result['cases']}


def draw_coordinate_markers(ax, markers):
    """Overlay positions without changing data or expanding a zoomed view."""
    from matplotlib.lines import Line2D
    from matplotlib.patheffects import withStroke
    xlim,ylim=ax.get_xlim(),ax.get_ylim()
    inside=lambda x,y:min(xlim)<=x<=max(xlim) and min(ylim)<=y<=max(ylim)
    origin=markers['transmitted_q_cycles_per_angstrom']
    za=markers['zone_axis_q_cycles_per_angstrom']
    style=dict(marker='*',ms=9,mfc='gold',mec='black',mew=.7,ls='none')
    if inside(*origin):ax.plot(*origin,marker='+',ms=6,color='black',mew=1.,ls='none',zorder=10)
    if inside(*za):
        ax.plot(*za,**style,zorder=9)
        offset=(8,9) if za[1]<min(ylim)+.15*abs(ylim[1]-ylim[0]) else (8,-15)
        ax.annotate('ZA [001]',za,xytext=offset,textcoords='offset points',fontsize=7,
            path_effects=[withStroke(linewidth=1.5,foreground='white')],zorder=11)
    else:
        ax.text(.02,.03,f'ZA [001] outside view\nq=({za[0]:+.5f}, {za[1]:+.5f}) cycles/A',
            transform=ax.transAxes,fontsize=7,bbox=dict(facecolor='white',alpha=.85,edgecolor='none'),zorder=11)
    ax.legend(handles=[Line2D([],[],marker='+',ms=6,color='black',ls='none',label='Transmitted (000)'),
        Line2D([],[],**style,label='ZA [001]')],loc='upper left',fontsize=6,framealpha=.85)
    ax.set_xlim(xlim);ax.set_ylim(ylim)


def angular_diagnostics(result):
    """Full-grid intensity and full-range spectral differences; no fitted gain."""
    diagnostics={}
    for c in result['cases']:
        g=dict(c['geometry'],weights_A=np.ones_like(c['qx']),valid=np.ones_like(c['qx'],dtype=bool))
        edges={}
        for j,edge in enumerate(('L3','L2')):
            a,b=[m['maps'][j] for m in c['methods']]
            scale=max(np.linalg.norm(m['I_plus'])*np.sqrt(g['dq2']) for m in (a,b))
            edges[edge]={k:map_error(a[k],b[k],g,scale) for k in ('I_mag','I_nonmag','I_plus')}
        a,b=[m['spectra'] for m in c['methods']];e=a['energy_ev']
        norm=lambda x:float(np.sqrt(max(_integral(x*x,e),0.)))
        floor=1e-10*max(norm(s['Sigma_ref']) for s in (a,b));spectra={}
        for k in ('I_A_plus','I_B_plus','D_raw','D_mag','D_nonmag','D_corrected','D_nonmag_residual_obs'):
            x,y=a[k],b[k]
            if x.ndim==2:x,y=x[0],y[0]
            absolute=norm(y-x);ref=max(norm(x),norm(y))
            spectra[k]=dict(max_abs=float(np.max(abs(y-x))),l2_abs=absolute,
                l2_relative=absolute/ref if ref>floor else np.nan,relative_valid=bool(ref>floor))
        diagnostics[c['condition']]=dict(map_differences=edges,spectral_differences=spectra)
    return diagnostics


def save_angular_outputs(result, output):
    """Export selected intrinsic arrays and spectra from the canonical result."""
    output=Path(output)
    result['metadata']['angular_diagnostics']=angular_diagnostics(result)
    result['metadata']['coordinate_markers']=result_coordinate_markers(result)
    for c in result['cases']:
        folder=output/c['condition'];folder.mkdir(parents=True,exist_ok=True)
        meta=result['metadata'];pmeta=meta['propagation'];geom=c['geometry']
        arrays=dict(qx_inv_angstrom=c['qx'],qy_inv_angstrom=c['qy'],
            beam_hkl=np.asarray(pmeta['beam_hkl']),reciprocal_gxy=np.asarray(pmeta['reciprocal_gxy']),
            method_labels=np.asarray(METHODS),edge_labels=np.asarray(['L3','L2']),
            selected_energies_ev=np.asarray([meta['selected_energies_ev'][e] for e in ('L3','L2')]),
            weights_A=geom['weights_A'],weights_B=geom['weights_B'],paired_valid=geom['valid'])
        for k in c['methods'][0]['maps'][0]:
            arrays[k]=np.asarray([[m[k] for m in method['maps']] for method in c['methods']])
        arrays.update({'weight_'+k:w for k,w in geom['physical_weights'].items()})
        case=result['propagation_cases'][list(meta['config']['conditions']).index(c['condition'])]
        arrays.update({k:case[k] for k in ('coherence_bw','coherence_ms','depth_nm','fft_outside_intensity')})
        np.savez_compressed(folder/'angular_maps.npz',**arrays)
        np.savez_compressed(folder/'virtual_detector_spectra.npz',method_labels=np.asarray(METHODS),
            **{k:np.asarray([m['spectra'][k] for m in c['methods']]) for k in c['methods'][0]['spectra']})
        local=dict(condition=c['condition'],config=meta['config'],source_sha256=meta['source_sha256'],
            selected_energies_ev=meta['selected_energies_ev'],geometry=pmeta['geometries'][c['condition']],
            diagnostics=meta['angular_diagnostics'][c['condition']],software_commit=meta.get('software_commit'),
            software_worktree_dirty=meta.get('software_worktree_dirty'),
            map_axes='method, edge (L3,L2), qy, qx',intrinsic_maps='I_mag, I_nonmag, I_plus (total plus-state intensity)',
            coordinate_markers=meta['coordinate_markers'][c['condition']],
            canonical_metadata='../comparison_metadata.json')
        (folder/'comparison_metadata.json').write_text(json.dumps(_json_safe(local),indent=2,allow_nan=False)+'\n',encoding='utf-8')


def plot_angular_comparison(result, output):
    """Five figure types per geometry, from saved selected maps and spectra only."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    from matplotlib.patheffects import withStroke
    diagnostics=angular_diagnostics(result)
    markers=result_coordinate_markers(result)
    for c in result['cases']:
        condition=c['condition'];folder=Path(output)/condition;folder.mkdir(parents=True,exist_ok=True)
        meta=result['metadata'];pg=meta['propagation'];half=np.sqrt(c['geometry']['dq2'])/2
        extent=(c['qx'].min()-half,c['qx'].max()+half,c['qy'].min()-half,c['qy'].max()+half)
        def decorate(ax):
            for hkl,(gx,gy) in zip(pg['beam_hkl'],pg['reciprocal_gxy']):
                if extent[0]<=gx<=extent[1] and extent[2]<=gy<=extent[3]:
                    ax.plot(gx,gy,'k+',ms=4,mew=.6,path_effects=[withStroke(linewidth=1.8,foreground='white')])
                    ax.annotate('('+','.join(map(str,hkl))+')',(gx,gy),xytext=(3,3),textcoords='offset points',fontsize=6,path_effects=[withStroke(linewidth=1.4,foreground='white')])
            geometry=pg['geometries'][condition]
            for name,d in geometry['detectors'].items():
                group=name in (('A',) if condition=='near-2bc' else ('RU','LD'))
                ax.add_patch(Circle(d['center_q_xy'],d['radius_q'],fill=False,ec='black',ls='-' if group else '--',lw=.8,path_effects=[withStroke(linewidth=2,foreground='white')]))
                ax.annotate(name,d['center_q_xy'],ha='center',va='center',fontsize=7,path_effects=[withStroke(linewidth=1.4,foreground='white')])
            ax.set(xlabel='qx (cycles/A)',ylabel='qy (cycles/A)',aspect='equal')
            draw_coordinate_markers(ax,markers[condition])
        title=lambda text:condition+' | '+text+'\n'+LABEL
        for j,edge in enumerate(('L3','L2')):
            maps=[m['maps'][j] for m in c['methods']]
            fig,axs=plt.subplots(2,3,figsize=(13,8),constrained_layout=True)
            for k,key in enumerate(('I_mag','I_nonmag','I_plus')):
                limit=max(max(float(np.max(abs(m[key]))) for m in maps),1e-30)
                for i in range(2):
                    im=axs[i,k].imshow(maps[i][key],origin='lower',extent=extent,interpolation='nearest',
                        cmap='RdBu_r' if k==0 else 'viridis',vmin=-limit if k==0 else 0,vmax=limit)
                    decorate(axs[i,k]);axs[i,k].set_title(METHODS[i]+' | '+('magnetic odd','nonmagnetic even','total +')[k],fontsize=10)
                fig.colorbar(im,ax=axs[:,k].tolist(),label='Relative intensity',shrink=.8)
            fig.suptitle(title(f"{edge} {meta['selected_energies_ev'][edge]:.3f} eV | intrinsic angular terms"),fontsize=10)
            fig.savefig(folder/f'{edge}_angular_maps.png',dpi=200);plt.close(fig)
        fig,axs=plt.subplots(2,3,figsize=(14,8),sharex=True,sharey='col',constrained_layout=True)
        for i,m in enumerate(c['methods']):
            s=m['spectra'];e=s['energy_ev']
            for k in ('I_A_plus','I_B_plus'):axs[i,0].plot(e,s[k],label=k)
            for k in ('D_raw','D_mag','D_nonmag'):axs[i,1].plot(e,s[k],label=k)
            axs[i,2].plot(e,s['D_corrected'][0],label='Corrected A - alpha B')
            axs[i,2].plot(e,s['D_mag'],label='Unscaled magnetic odd')
            axs[i,2].plot(e,s['D_nonmag_residual_obs'][0],label='Even residual',ls=':')
            for ax in axs[i]:
                for edge,energy in meta['selected_energies_ev'].items():
                    ax.axvline(energy,color='black',ls=':',lw=.7)
                    ax.text(energy,.98,edge,transform=ax.get_xaxis_transform(),ha='right',va='top',fontsize=7)
                ax.axvspan(meta['config']['postedge_start'],meta['config']['postedge_end'],color='grey',alpha=.2)
                ax.set(xlabel='Energy loss (eV)',ylabel='Relative intensity',title=METHODS[i],xlim=(e[0],e[-1]))
                ax.legend(fontsize=7);ax.grid(alpha=.2)
        fig.suptitle(title(f"Virtual-detector EELS | shaded {meta['config']['postedge_start']:g}-{meta['config']['postedge_end']:g} eV normalization"),fontsize=10)
        fig.savefig(folder/'virtual_detector_eels.png',dpi=200);plt.close(fig)
        # L3 primary four-panel comparison; L2 uses the identical presentation.
        for j,edge in enumerate(('L3','L2')):
            maps=[m['maps'][j] for m in c['methods']];keys=('D_raw','D_corrected')
            limit=max(max(float(np.nanmax(abs(m[k]))) for m in maps for k in keys),1e-30)
            fig,axs=plt.subplots(2,2,figsize=(10,8),constrained_layout=True)
            for i in range(2):
                for k,key in enumerate(keys):
                    im=axs[i,k].imshow(maps[i][key],origin='lower',extent=extent,cmap='RdBu_r',vmin=-limit,vmax=limit,interpolation='nearest')
                    decorate(axs[i,k]);axs[i,k].set_title(METHODS[i]+' | '+('Raw A - B','A - alpha B')[k],fontsize=10)
            fig.colorbar(im,ax=axs.ravel().tolist(),label='Relative intensity')
            fig.suptitle(title(edge+' | paired contrast (A support only; white = invalid)'),fontsize=10)
            name='raw_corrected_emcd_maps.png' if j==0 else 'L2_raw_corrected_emcd_maps.png'
            fig.savefig(folder/name,dpi=200);plt.close(fig)
        fig,axs=plt.subplots(2,2,figsize=(11,8),constrained_layout=True)
        for j,edge in enumerate(('L3','L2')):
            a,b=[m['maps'][j] for m in c['methods']]
            for k,key in enumerate(('I_mag','I_nonmag')):
                delta=b[key]-a[key];limit=max(float(np.max(abs(delta))),1e-30)
                im=axs[j,k].imshow(delta,origin='lower',extent=extent,cmap='RdBu_r',vmin=-limit,vmax=limit,interpolation='nearest')
                decorate(axs[j,k]);d=diagnostics[condition]['map_differences'][edge][key]
                axs[j,k].set_title(f"{edge} {key} | abs L2={d['l2_abs']:.3g}; rel={d['l2_relative']:.3g}",fontsize=9)
                fig.colorbar(im,ax=axs[j,k],label='MS - BW relative intensity',shrink=.8)
        fig.suptitle(title('Intrinsic angular-map residuals | panel-specific symmetric scales'),fontsize=10)
        fig.savefig(folder/'bloch_multislice_difference.png',dpi=200);plt.close(fig)
