"""Final [001]-source validation, analysis-only; excludes superseded [110] work."""
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from ni_117_magnetization import OUT as CACHE,ROOT,ENERGIES,write_json,write_npz,sha
from emcd_sim.geometry import VirtualDetector,electron_wavelength_angstrom
from emcd_sim.study_geometry import StudyGeometry
Ni117Geometry=lambda a_angstrom=3.524: StudyGeometry((1,1,7),(2,-2,0),a_angstrom)
import ni_117_magnetization_report as report

OUT=ROOT/'outputs/ni_117_final_symmetry_validation'


def analytical(records):
    rows=[];branch_errors=[]
    for d,a in records:
        s=d['identity']['settings']
        if s['basis_mode']!='two-beam':continue
        g=np.linalg.norm(a['g'][1]);q=a['circle_q'];m=np.array(d['magnetizations']['crystal001']['local'])
        for ie,energy in enumerate(ENERGIES):
            z=d['qz_cycles_angstrom'][ie];q0=np.column_stack((q,np.full(len(q),z)));qg=q0-[g,0,0]
            geom=g*(m[2]*q[:,1]-m[1]*z)
            cross=np.cross(q0,qg)@m
            error=float(np.max(abs(cross-geom)))
            row=dict(case=d['label'],energy_ev=energy,cross_product_max_absolute_error=error)
            actual=a['crystal001__M'][ie,a['circle_index']]
            reflection=(-np.arange(len(q)))%len(q);even=(actual+actual[reflection])/2;odd=(actual-actual[reflection])/2
            keep=abs(q[:,1])>1e-12
            predicted_even=odd[keep]*(-m[1]*z)/(m[2]*q[keep,1])
            row['even_from_odd_relative_max']=float(np.max(abs(even[keep]-predicted_even))/np.max(abs(actual)))
            if d['identity']['channeling']=='single':
                T=a['crystal001__tensor_plus'][ie];encoded=np.array([T[1,2].imag,T[2,0].imag,T[0,1].imag]);coefficient=float(encoded@m)
                dynamical=-2*s['thickness']*coefficient*a['coherence'][0,1].imag/((2*np.pi)**2*np.sum(q0*q0,axis=1)*np.sum(qg*qg,axis=1))
                predicted=dynamical*geom;actual=a['crystal001__M'][ie,a['circle_index']]
                row['signed_prediction_relative_max']=float(np.max(abs(predicted-actual))/np.max(abs(actual)))
                row['signed_prediction_relative_l2']=report.fraction(predicted-actual,actual)
                row['coefficient_c']=coefficient;row['Im_C_0g']=float(a['coherence'][0,1].imag)
                write_npz(OUT/(d['label']+f'_analytical_{energy}.npz'),q=q,qz=np.asarray(z),M=actual,
                    predicted=predicted,odd_term=dynamical*g*m[2]*q[:,1],even_term=dynamical*(-g*m[1]*z))
            rows.append(row)
        # Check every pair of actual incoming/outgoing transfer offsets.
        offsets=(a['g'][None,:,:]-a['g'][:,None,:]).reshape(-1,2)
        for delta in offsets:
            for other in offsets:
                z=d['qz_cycles_angstrom'][0];p=np.r_[q[37]+delta,z];r=np.r_[q[37]+other,z]
                expected=(delta[0]-other[0])*np.array([0,-z,q[37,1]])
                branch_errors.append(float(np.max(abs(np.cross(p,r)-expected))))
    write_json(OUT/'analytical_sign_validation.json',dict(single_and_cross_checks=rows,
        maximum_two_beam_double_branch_cross_error=max(branch_errors),
        convention='T_ab=i*c*epsilon_abk*m_k (imaginary part); magnetic Single=-2*t*c*Im(C_0g)*cross/(angular Coulomb denominators).',
        double='Offsets delta=h_out-g_in: all two-beam offsets have delta_y=0. Each pair has cross=(delta_x-delta_x_prime)*(0,-qz,y). Full ZOLZ includes delta_y terms; use complete kernel, not one incoming pair.'))


def extra_numerical(records,rows):
    pairs=[];lookup={d['label']:(d,a) for d,a in records}
    agreement=[]
    for label,(d,a) in lookup.items():
        if not label.endswith('_bloch'):continue
        other=label[:-len('bloch')]+'fft-multislice'
        if other not in lookup:continue
        e,b=lookup[other];np.testing.assert_array_equal(a['circle_q'],b['circle_q'])
        for ie,edge in enumerate(('L3','L2')):
            for name in ('crystal001','incident'):
                m=a[name+'__M'][ie,a['circle_index']];n=b[name+'__M'][ie,b['circle_index']]
                nonmag=a[name+'__N'][ie,a['circle_index']];fn=b[name+'__N'][ie,b['circle_index']]
                agreement.append(dict(case=label,axis=name,edge=edge,magnetic_circle_relative_l2=report.fraction(m-n,n),
                    magnetic_circle_relative_max=float(np.max(abs(m-n))/np.max(abs(n))),nonmagnetic_circle_relative_l2=report.fraction(nonmag-fn,fn)))
    write_json(OUT/'bw_ms_circle_agreement.json',dict(comparisons=agreement,warning='Agreement alone is not independent convergence.'))
    for method in ('bloch','fft-multislice'):
        x='refined_full_double_t8_'+method;y='combined_full_double_t8_'+method
        if y not in lookup:continue
        d,a=lookup[x];e,b=lookup[y]
        for ie,edge in enumerate(('L3','L2')):
            for name in ('crystal001','incident'):
                m=a[name+'__M'][ie,a['circle_index']];n=b[name+'__M'][ie,b['circle_index']][::2]
                nonmag=a[name+'__N'][ie,a['circle_index']];fn=b[name+'__N'][ie,b['circle_index']][::2]
                # Compare actual A/B center directions, not grid-cell surrogates.
                indices=[len(m)//4,3*len(m)//4];fine=b[name+'__M'][ie,b['circle_index']]
                even=(m+m[(-np.arange(len(m)))%len(m)])/2;f_even=(fine+fine[(-np.arange(len(fine)))%len(fine)])/2
                fine_rms=np.sqrt(np.mean(fine**2));subset_rms=np.sqrt(np.mean(fine[::2]**2))
                row=dict(method=method,axis=name,edge=edge,profile_relative_l2=report.fraction(m-n,n),
                    profile_relative_max=float(np.max(abs(m-n))/np.max(abs(n))),
                    nonmag_profile_relative_l2=report.fraction(nonmag-fn,fn),
                    even_profile_relative_l2=report.fraction(even-f_even[::2],f_even[::2]) if name=='crystal001' else None,
                    M_A_center_refined=float(m[indices[0]]),M_B_center_refined=float(m[indices[1]]),
                    M_A_center_combined=float(n[indices[0]]),M_B_center_combined=float(n[indices[1]]),
                    pure_circle_sampling_rms_relative_error=float(abs(fine_rms-subset_rms)/fine_rms),
                    pure_circle_sampling_even_fraction_error=abs(report.fraction(f_even,fine)-report.fraction(f_even[::2],fine[::2])),
                    center_pair_relative_error=float(np.max(abs(m[indices]-n[indices]))/max(np.max(abs(n[indices])),1e-30)))
                for channel in ('M','N'):
                    xrow=next(r for r in rows if r['case']==x and r['axis']==name and r['edge']==edge)
                    yrow=next(r for r in rows if r['case']==y and r['axis']==name and r['edge']==edge)
                    row['delta_integrated_D_'+channel]=float(yrow['D_mag' if channel=='M' else 'D_nonmag']-xrow['D_mag' if channel=='M' else 'D_nonmag'])
                pairs.append(row)
    write_json(OUT/'raw_circle_convergence.json',dict(comparisons=pairs,
        note='Relative errors near a vanishing control even component are undefined. Raw magnetic profile errors use the whole profile scale; do not divide by individual zero crossings. Existing detector gates remain 0.01 pp and 0.001 relative raw intensity.'))


def tensor_components(records):
    """Linear terms of the SAME source tensor, not new physical configurations."""
    rows=[]
    for d,a in records:
        ii=a['circle_index'];mirror=(-np.arange(len(ii)))%len(ii)
        for ie,edge in enumerate(('L3','L2')):
            T=1j*a['crystal001__tensor_plus'][ie].imag
            y=np.zeros((3,3),complex);z=y.copy()
            y[0,2]=T[0,2];y[2,0]=T[2,0];z[0,1]=T[0,1];z[1,0]=T[1,0]
            response=a['response'][ie,ii]
            my=np.einsum('pab,ab->p',response,y).real;mz=np.einsum('pab,ab->p',response,z).real
            actual=a['crystal001__M'][ie,ii];even=(actual+actual[mirror])/2;odd=(actual-actual[mirror])/2
            scale=max(float(np.max(abs(actual))),1e-30)
            rows.append(dict(case=d['label'],edge=edge,source_term_sum_relative_max=float(np.max(abs(actual-my-mz))/scale),
                even_minus_My_term_relative_max=float(np.max(abs(even-my))/scale),odd_minus_Mz_term_relative_max=float(np.max(abs(odd-mz))/scale),
                My_term_odd_relative_max=float(np.max(abs(my-my[mirror]))/(2*scale)),
                Mz_term_even_relative_max=float(np.max(abs(mz+mz[mirror]))/(2*scale)),
                My_term_rms=float(np.sqrt(np.mean(my**2))),Mz_term_rms=float(np.sqrt(np.mean(mz**2)))))
    with (OUT/'source_tensor_components.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)


def aperture_sampling(records):
    """Reintegrate EXACT cached directions; no interpolation or propagation."""
    weights={};rows=[];g=np.sqrt(8)/3.524
    for grid,sub in ((17,32),(33,32),(33,128)):
        v=np.linspace(-1,1,grid);x,y=np.meshgrid(v,v)
        w=np.array([VirtualDetector((g/2,sign*g/2),.16*g).integration_weights(x,y,mode='fractional',subpixels=sub) for sign in (1,-1)])
        weights[grid,sub]=w*(v[1]-v[0])**2
    for d,a in records:
        if d['identity']['profile']['name']!='refined':continue
        if d['identity']['profile']['map_grid']!=33:continue
        for ie,edge in enumerate(('L3','L2')):
            actual=np.array([a['crystal001__'+s][ie,a['detector_index']]@a['detector_weights'].T*float(a['dq2']) for s in ('plus','minus')])
            N=actual.mean(axis=0);M=(actual[0]-actual[1])/2;reference=100*(M[0]-M[1])/N.sum()
            for (grid,sub),w in weights.items():
                stride=32//(grid-1)
                plane=np.array([a['crystal001__'+s][ie,a['map_index']].reshape(33,33)[::stride,::stride] for s in ('plus','minus')])
                integrated=np.einsum('sxy,dxy->sd',plane,w);n=integrated.mean(axis=0);m=(integrated[0]-integrated[1])/2
                value=100*(m[0]-m[1])/n.sum();delta=abs(value-reference);raw=float(np.max(abs(integrated-actual)/np.maximum(abs(actual),1e-30)))
                rows.append(dict(case=d['label'],edge=edge,grid=grid,subpixels=sub,reference_grid=97,A_mag_percent=value,reference_A_mag_percent=reference,
                    delta_A_mag_pp=delta,relative_raw_max=raw,detector_gate_passed=bool(delta<=.01 and raw<=.001)))
    with (OUT/'aperture_sampling_recheck.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)


def control_comparisons(rows,records):
    changes=[];lookup={d['label']:a for d,a in records}
    for row in rows:
        if row['axis']!='crystal001' or row['profile'] not in ('aperture129','mistilt_dx0.2','mistilt_dy0.2'):continue
        baseline=f"refined_full_double_t{row['thickness_nm']}_{row['method']}"
        old=next(r for r in rows if r['case']==baseline and r['axis']=='crystal001' and r['edge']==row['edge'])
        change=dict(control=row['profile'],method=row['method'],edge=row['edge'],thickness_nm=row['thickness_nm'],
            circle_even_fraction=row['circle_even_fraction'],delta_circle_even_fraction=row['circle_even_fraction']-old['circle_even_fraction'],
            delta_circle_odd_fraction=row['circle_odd_fraction']-old['circle_odd_fraction'],circle_nonmagnetic_odd_fraction=row['circle_nonmag_odd_fraction'],
            A_mag_percent=row['A_mag_percent'],delta_A_mag_pp=row['A_mag_percent']-old['A_mag_percent'],
            delta_PRB_pp=row['PRB_percent']-old['PRB_percent'],D_mag=row['D_mag'],D_nonmag=row['D_nonmag'],
            raw_relative_max=max(abs(row[k]-old[k])/max(abs(row[k]),abs(old[k]),1e-30) for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')))
        aa=lookup[row['case']];bb=lookup[baseline];ie=0 if row['edge']=='L3' else 1
        np.testing.assert_array_equal(aa['circle_q'],bb['circle_q'])
        m=aa['crystal001__M'][ie,aa['circle_index']];n=bb['crystal001__M'][ie,bb['circle_index']]
        change['raw_circle_profile_relative_change']=report.fraction(m-n,n)
        if row['profile']=='aperture129':change['detector_gate_passed']=bool(abs(change['delta_A_mag_pp'])<=.01 and abs(change['delta_PRB_pp'])<=.01 and change['raw_relative_max']<=.001)
        changes.append(change)
    write_json(OUT/'control_comparisons.json',changes)


def figures(records,rows):
    lookup={d['label']:(d,a) for d,a in records};key='refined_full_double_t8_bloch'
    if key not in lookup:return
    d,a=lookup[key];s=d['identity']['settings'];pop=abs(a['waves'][-1])**2
    fig,axs=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for index,ax in enumerate(axs):
        scatter=ax.scatter(a['g'][:,0],a['g'][:,1],s=30+400*pop,c=pop,cmap='viridis',norm=Normalize(0,1))
        for h,g in zip(a['hkl'],a['g']):
            if index==0 or (-.15<=g[0]<=1.05 and abs(g[1])<=.65):ax.annotate(str(tuple(map(int,h))),g,xytext=(4,4),textcoords='offset points',fontsize=6)
        report.decorate(ax,a);ax.axhline(0,color='grey',lw=.6,label='(2,-2,0) row');ax.legend(fontsize=6)
        if index:ax.set(xlim=(-.15,1.05),ylim=(-.65,.65))
        ax.set_title('Full finite basis' if index==0 else 'Actual Thales geometry (zoom)',fontsize=10)
    fig.colorbar(scatter,ax=axs.ravel().tolist(),label='BW elastic exit population',shrink=.8)
    fig.suptitle('Ni [117], 200 kV, 8 nm; exact target Bragg\nbeam4.6 / potential6.2 cycles/Å; source M=[001]',fontsize=10)
    report.save(fig,'indexed_diffraction')
    for ie,edge in enumerate(('L3','L2')):
        fig,axs=plt.subplots(2,3,figsize=(12,8),layout='constrained');limit=0
        for method in ('bloch','fft-multislice'):
            dd,aa=lookup['refined_full_double_t8_'+method]
            limit=max(limit,float(abs(aa['crystal001__M'][ie,aa['map_index']]).max()))
        for i,method in enumerate(('bloch','fft-multislice')):
            dd,aa=lookup['refined_full_double_t8_'+method];p=dd['identity']['profile'];m=aa['crystal001__M'][ie,aa['map_index']].reshape(p['map_grid'],p['map_grid'])
            for j,(title,values) in enumerate((('raw reversal-odd M',m),('mirror-odd',(m-m[::-1])/2),('mirror-even',(m+m[::-1])/2))):
                half=1/(p['map_grid']-1)
                image=axs[i,j].imshow(values,origin='lower',extent=(-1-half,1+half,-1-half,1+half),vmin=-limit,vmax=limit,cmap='RdBu_r',interpolation='nearest')
                report.decorate(axs[i,j],aa);axs[i,j].set_title(method+' | '+title,fontsize=10)
                axs[i,j].set(xlim=(-1,1),ylim=(-1,1))
                if i==0 and j==0:axs[i,j].legend(fontsize=6,loc='upper left')
        fig.colorbar(image,ax=axs.ravel().tolist(),shrink=.7,label='Raw intensity (a.u.); common scale')
        fig.suptitle(f'Ni [117], source crystal M=[001], 200 kV, 8 nm, {edge}={ENERGIES[ie]} eV\nFull ZOLZ Double; beam4.6, potential6.2, FFT32, depth129, max slice0.02 nm',fontsize=11)
        report.save(fig,'raw_mirror_decomposition_'+edge)
    # Same raw intensity scale for all methods and channeling/support models.
    fig,axs=plt.subplots(2,2,figsize=(12,8),layout='constrained',sharey=True)
    for i,mode in enumerate(('two-beam','full')):
        for j,channel in enumerate(('single','double')):
            for method in ('bloch','fft-multislice'):
                dd,aa=lookup[f'refined_{mode}_{channel}_t8_{method}'];m=aa['crystal001__M'][0,aa['circle_index']]
                theta=np.degrees(aa['angle']);mirror=(-np.arange(len(m)))%len(m)
                axs[i,j].plot(theta,m,'-' if method=='bloch' else '--',label=method+' M(θ)')
                axs[i,j].plot(theta,-m[mirror],':',label=method+' −M(−θ)',alpha=.8)
            axs[i,j].set(title=f'{mode}, {channel}',xlabel='Thales angle θ (degrees)',ylabel='Raw magnetic intensity (a.u.)');axs[i,j].legend(fontsize=7)
            for angle,label in ((90,'A'),(270,'B')):
                axs[i,j].axvline(angle,color='grey',ls=':',lw=.7);axs[i,j].text(angle,axs[i,j].get_ylim()[1],label,ha='center',va='top')
    fig.suptitle('Source crystal M=[001], Ni [117], 200 kV, 8 nm, native L3; exact target Bragg',fontsize=11)
    report.save(fig,'thales_models_bw_ms')
    # Detailed physical channels and actual center-direction values.
    fig,axs=plt.subplots(2,3,figsize=(13,7),layout='constrained')
    for ie,edge in enumerate(('L3','L2')):
        for method in ('bloch','fft-multislice'):
            dd,aa=lookup['refined_full_double_t8_'+method];ii=aa['circle_index'];m=aa['crystal001__M'][ie,ii];n=aa['crystal001__N'][ie,ii];theta=np.degrees(aa['angle']);mirror=(-np.arange(len(m)))%len(m);style='-' if method=='bloch' else '--'
            axs[ie,0].plot(theta,m+m[mirror],style,label=method+' M(θ)+M(−θ)')
            axs[ie,1].plot(theta,(m+m[mirror])/2,style,label=method+' mirror-even');axs[ie,1].plot(theta,(m-m[mirror])/2,':',label=method+' mirror-odd')
            axs[ie,2].plot(theta,n,style,label=method+' N');axs[ie,2].plot(theta,n+m,':',label=method+' total +M')
        for ax in axs[ie]:ax.set(xlabel='Thales angle θ (degrees)',ylabel=f'{edge} intensity (a.u.)');ax.legend(fontsize=7)
    fig.suptitle('Raw fields, full ZOLZ Double; source M=[001], 200 kV, 8 nm; no normalization',fontsize=11)
    report.save(fig,'thales_raw_components')
    fig,axs=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    for mode in ('two-beam','full'):
        for channel in ('single','double'):
            for method in ('bloch','fft-multislice'):
                selected=sorted([r for r in rows if r['profile']=='refined' and r['axis']=='crystal001' and r['edge']=='L3' and r['support']==mode and r['channeling']==channel and r['method']==method],key=lambda r:r['thickness_nm'])
                x=[r['thickness_nm'] for r in selected];label=mode+' '+channel+' '+method;style='o-' if method=='bloch' else 'x--'
                axs[0].plot(x,[r['circle_even_fraction'] for r in selected],style,label=label)
                axs[1].plot(x,[r['A_mag_percent'] for r in selected],style)
    axs[0].set(xlabel='Thickness (nm)',ylabel='Circle mirror-even norm fraction');axs[0].legend(fontsize=6,ncol=2)
    axs[1].set(xlabel='Thickness (nm)',ylabel='Magnetic-only detector asymmetry (%)')
    fig.suptitle('Ni [117], 200 kV, exact Bragg, source crystal M=[001]; representative thicknesses')
    report.save(fig,'model_thickness_comparison')
    combined=[r for r in rows if r['profile'] in ('refined','combined') and r['support']=='full' and r['channeling']=='double' and r['thickness_nm']==8 and r['axis']=='crystal001' and r['edge']=='L3']
    fig,axs=plt.subplots(1,3,figsize=(14,4),layout='constrained')
    for method in ('bloch','fft-multislice'):
        vals=sorted([r for r in combined if r['method']==method],key=lambda r:r['profile']=='combined')
        axs[0].plot(range(len(vals)),[r['circle_even_fraction'] for r in vals],'o-',label=method)
        for index,label in ((1,'A'),(3,'B')):
            signals=[]
            for row in vals:
                aa=lookup[row['case']][1];signals.append(aa['crystal001__M'][0,aa['circle_index'][index*len(aa['circle_index'])//4]])
            axs[1].plot(range(len(vals)),signals,'o-' if label=='A' else 'x--',label=method+' '+label)
        axs[2].plot(range(len(vals)),[r['A_mag_percent'] for r in vals],'o-',label=method)
    for ax in axs:ax.set_xticks([0,1],['refined','combined']);ax.legend(fontsize=8)
    axs[0].set_ylabel('Raw circle mirror-even norm fraction');axs[1].set_ylabel('Raw M at A/B center (a.u.)');axs[2].set_ylabel('L3 magnetic-only detector asymmetry (%)')
    from matplotlib.ticker import FormatStrFormatter
    axs[0].yaxis.set_major_formatter(FormatStrFormatter('%.6f'))
    fig.suptitle('Representative combined-parameter check: full Double, 8 nm, 200 kV, source M=[001]')
    report.save(fig,'combined_convergence')
    fig,axs=plt.subplots(1,2,figsize=(12,4),layout='constrained')
    for name in ('mistilt_dx0.2','mistilt_dy0.2'):
        for method in ('bloch','fft-multislice'):
            key=name+'_full_double_t8_'+method
            if key not in lookup:continue
            dd,aa=lookup[key];base=lookup['refined_full_double_t8_'+method][1];ii=aa['circle_index'];jj=base['circle_index']
            m=aa['crystal001__M'][0,ii];old=base['crystal001__M'][0,jj];n=aa['crystal001__N'][0,ii];mirror=(-np.arange(len(n)))%len(n)
            label=name.replace('mistilt_','')+' '+method;style='-' if method=='bloch' else '--';theta=np.degrees(aa['angle'])
            axs[0].plot(theta,m-old,style,label=label);axs[1].plot(theta,(n-n[mirror])/2,style,label=label)
    axs[0].set(xlabel='Circle angle θ (degrees)',ylabel='M(mistilt) − M(Bragg) (a.u.)');axs[1].set(xlabel='Circle angle θ (degrees)',ylabel='Raw N mirror-odd part (a.u.)')
    for ax in axs:ax.legend(fontsize=7)
    fig.suptitle('Ni [117], source [001], 200 kV, 8 nm, full Double L3; +0.2 mrad one-factor mistilts',fontsize=10)
    report.save(fig,'mistilt_physical_changes')


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    records=report.load()
    report.OUT=OUT;report.AXES=('crystal001','incident')
    rows=report.tables(records);report.numerical(records,rows)
    analytical(records);extra_numerical(records,rows);tensor_components(records);aperture_sampling(records);control_comparisons(rows,records);figures(records,rows)
    write_json(OUT/'provenance.json',dict(response_cache=str(CACHE),source_configuration='Verified WIEN2k M||[001]; unchanged XMCD coefficients',
        physical_axes=['crystal001'],control_axes=['incident'],records=len(records),source_sha256=sha(ROOT/'data/wien2k_ni/Ni_fm.xmcd'),
        inso_sha256=sha(ROOT/'data/wien2k_ni/Ni_fm.inso'),outputopup_sha256=sha(ROOT/'data/wien2k_ni/Ni_fm.outputopup'),
        common=dict(zone_axis=[1,1,7],target_hkl=[2,-2,0],frame=Ni117Geometry().frame,
            voltage_kv=200,wavelength_angstrom=electron_wavelength_angstrom(200),
            transmitted_q=[0,0],detector_centers=[[np.sqrt(8)/3.524/2,np.sqrt(8)/3.524/2],[np.sqrt(8)/3.524/2,-np.sqrt(8)/3.524/2]],detector_radius=.16*np.sqrt(8)/3.524,
            integration='fractional',eta=1,beta=1,q_units='cycles/angstrom',energy_units='native eV, no absolute calibration',intensity_units='a.u., fixed common source scale',
            operator='XMCD-effective Hermitian dipole tensor; T_local=R T_crystal R^T, angular transfers Q=2*pi*q; qz=-E/(h*v_in)',numpy_version=np.__version__),
        explanation='No [110] configuration is used in this final validation. Prior superseded tensor products, if present in the response cache, are not part of the final analysis.'))
    print('Final source-[001] analysis:',len(records),'response jobs;',len(rows),'axis/edge rows')
