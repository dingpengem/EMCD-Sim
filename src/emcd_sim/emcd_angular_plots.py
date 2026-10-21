"""Reciprocal-map overlays and physical paired-aperture map algebra."""
import numpy as np

def decorate_reciprocal_map(ax, model, extent, *, target_hkl=(2,0,0), zone_axis=(0,0,1)):
    """Draw geometry only, in the existing transmitted-beam coordinates."""
    from matplotlib.patches import Circle
    from matplotlib.patheffects import withStroke
    stroke=[withStroke(linewidth=1.5,foreground='white')]
    # Thales circle has the transmitted and +200 beams as diameter endpoints.
    g=model.elastic.crystal.g_vector(target_hkl)[:2]
    target=''.join(map(str,target_hkl));zone=''.join(map(str,zone_axis))
    ax.add_patch(Circle(g/2,np.linalg.norm(g)/2,fill=False,ec='darkcyan',
                        ls=':',lw=1.3,label=f'Thales (000)-({target})',path_effects=stroke))
    for hkl,(gx,gy) in zip(model.elastic.beams.hkl,model.elastic.reciprocal_vectors_xy):
        if extent[0]<=gx<=extent[1] and extent[2]<=gy<=extent[3]:
            ax.plot(gx,gy,'k+',ms=4,mew=.7,path_effects=stroke)
            if hkl!=(0,0,0):
                ax.annotate(str(hkl),(gx,gy),xytext=(3,3),textcoords='offset points',fontsize=6,path_effects=stroke)
    for name,d in model.detectors.items():
        ax.add_patch(Circle(d.center_q_xy,d.radius_q,fill=False,ec='black',lw=1,
                           ls='-' if name=='A' else '--',path_effects=stroke))
        ax.annotate(name,d.center_q_xy,ha='center',va='center',fontsize=7,path_effects=stroke)
    ax.plot(0,0,'kx',ms=6,mew=1.2,label='(000)',path_effects=stroke)
    za=-model.elastic.microscope.incident_k_xy
    if extent[0]<=za[0]<=extent[1] and extent[2]<=za[1]<=extent[3]:
        ax.plot(*za,marker='*',ms=10,color='gold',mec='black',mew=.7,ls='',label=f'ZA [{zone}]')
        ax.annotate(f'ZA [{zone}]',za,xytext=(5,6),textcoords='offset points',fontsize=7,path_effects=stroke)
    else:
        ax.text(.02,.02,f'ZA [{zone}] = ({za[0]:.3f}, {za[1]:.3f}) Å⁻¹\n(outside view)',
                transform=ax.transAxes,fontsize=7,bbox=dict(facecolor='white',alpha=.8,edgecolor='none'))
    ax.legend(loc='upper right',fontsize=6,framealpha=.8)
    ax.set(xlabel='qx (Å⁻¹)',ylabel='qy (Å⁻¹)',aspect='equal',
           xlim=extent[:2],ylim=extent[2:])


def paired_geometry(model, qx, qy, *, mode='fractional', subpixels=64):
    """Validate physical aperture bijection before using the y-index reflection."""
    qx,qy=np.asarray(qx),np.asarray(qy)
    if (qx.ndim!=2 or qx.shape!=qy.shape or not np.allclose(qx,qx[::-1],rtol=0,atol=1e-14)
            or not np.allclose(qy,-qy[::-1],rtol=0,atol=1e-14)):
        raise ValueError('Pairing requires a reflection-symmetric Cartesian q grid')
    groups=model.chiral_groups or {'A':('A',),'B':('B',)}
    expected=[({'A'},{'B'}),({'RU','LD'},{'RD','LU'})]
    if (set(model.detectors)!=set(groups['A'])|set(groups['B'])
            or (set(groups['A']),set(groups['B'])) not in expected):
        raise ValueError('Unsupported detector grouping for qy reflection')
    weights={k:d.integration_weights(qx,qy,mode=mode,subpixels=subpixels) for k,d in model.detectors.items()}
    mapping={}
    for a in groups['A']:
        da=model.detectors[a];target=(da.center_q_xy[0],-da.center_q_xy[1])
        matches=[b for b in groups['B'] if np.allclose(model.detectors[b].center_q_xy,target,rtol=0,atol=1e-14)
                 and abs(model.detectors[b].radius_q-da.radius_q)<1e-14]
        if len(matches)!=1:raise ValueError('Physical A aperture has no unique reflected B aperture')
        b=matches[0];mapping[a]=b
        if not np.allclose(weights[a],weights[b][::-1],rtol=0,atol=1e-14):
            raise ValueError('Reflected fractional aperture weights do not match')
    if set(mapping.values())!=set(groups['B']):raise ValueError('Detector reflection is not bijective')
    for d in model.detectors.values():
        if not d.integration_info(qx,qy,mode=mode,subpixels=subpixels)['aperture_fully_covered']:
            raise ValueError('Paired apertures must be fully covered')
    wa=sum(weights[k] for k in groups['A']);wb=sum(weights[k] for k in groups['B'])
    if np.any((wa>0)&(wb>0)) or not wa.any():raise ValueError('Paired A/B supports overlap or are empty')
    return dict(weights_A=wa,weights_B=wb,valid=wa>0,physical_weights=weights,mapping=mapping,
                dq2=float((qx[0,1]-qx[0,0])*(qy[1,0]-qy[0,0])))

def paired_maps(plus, minus, alpha, geometry):
    """Keep intrinsic parity intensities separate from A-supported contrasts."""
    p,m=np.asarray(plus,float),np.asarray(minus,float)
    valid=geometry['valid']
    if p.shape!=valid.shape or m.shape!=p.shape or not np.isfinite([p,m]).all() or not np.isfinite(alpha):
        raise ValueError('Require finite matched maps and a finite scalar detector factor')
    n,mag=(p+m)/2,(p-m)/2
    maps=dict(I_plus=p.copy(),I_minus=m.copy(),I_mag=mag,I_nonmag=n)
    values=dict(I_A_plus=p,I_B_plus_paired=p[::-1],I_A_minus=m,I_B_minus_paired=m[::-1],
        D_raw=p-p[::-1],D_corrected=p-alpha*p[::-1],D_mag=mag-mag[::-1],
        D_nonmag=n-n[::-1],D_mag_processed=mag-alpha*mag[::-1],D_nonmag_residual=n-alpha*n[::-1])
    maps.update({k:np.where(valid,v,np.nan) for k,v in values.items()})
    scale=max(float(np.max(abs(p))),1e-30)
    for total,a,b in [('D_raw','D_mag','D_nonmag'),('D_corrected','D_mag_processed','D_nonmag_residual')]:
        if not np.allclose(maps[total][valid],(maps[a]+maps[b])[valid],rtol=1e-12,atol=1e-13*scale):
            raise ArithmeticError('Pointwise paired-map parity identity failed')
    return maps

def integrate_paired(field, geometry):
    return float(np.sum(np.where(geometry['valid'],field,0.)*geometry['weights_A'])*geometry['dq2'])
