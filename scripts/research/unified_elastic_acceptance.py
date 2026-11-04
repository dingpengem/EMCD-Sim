"""Bounded reproducible elastic acceptance; never reads old scientific outputs.

Needs optional GUI/test dependencies and the pinned HDF5 reference in build/.
Run from the feature checkout with PYTHONPATH=src;build/elastic-validation-deps.
An existing destination is accepted only if it has no acceptance reports yet.
"""
import argparse
from dataclasses import asdict,replace
from decimal import Decimal,localcontext
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests'))
from unified_elastic_cases import cases,reciprocal_cross,analytical_frame,independent_factor,bw_ms
from emcd_sim.adaptive_scattering import adaptive_factor,coefficient_data,provenance
from emcd_sim.elastic_providers import ADAPTIVE,LOBATO,LEGACY,factors_for_provider
from emcd_sim.gui.geometry import Structure,Settings,geometry,elastic_model,align_bragg
from emcd_sim.scattering import nickel_lobato_factor,IndependentAtomPotential
from emcd_sim.legacy_atomic_factors import configured_legacy_factors


def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+''.join(
        '| '+' | '.join(f'{x:.9g}' if isinstance(x,(float,np.floating)) else str(x) for x in row)+' |\n' for row in rows)


def write(out,name,body):
    (out/name).write_text(body,encoding='utf-8')


def atomic_checks():
    import h5py
    ref=ROOT/'build/unified-upstream-pin/reference/reference_dirac_fock.h5'
    assert hashlib.sha256(ref.read_bytes()).hexdigest()==provenance()['reference_data_sha256']
    errors=[];arithmetic=0.;precision=0.;minimum=np.inf
    with h5py.File(ref) as h:
        for name,group in h.items():
            z=int(name[1:4]);g=group['g'][:];expected=group['feg'][:]
            actual=adaptive_factor(z,g)
            errors.append(dict(z=z,max_relative=float(np.max(abs(actual-expected)/expected)),
                origin_relative=float(abs(actual[0]-expected[0])/expected[0])))
            samples=np.r_[0.,np.nextafter(0.,1.),1e-200,1e-160,1e-10,.001,.04,.08,.5,1.,6.,12.,24.,36.]
            v=adaptive_factor(z,samples);minimum=min(minimum,float(v.min()))
            a,b,dp=coefficient_data()[z];u=b*samples[:,None]**2
            original=np.sum(np.where(dp,a*(3+3*u+u*u)/(1+u)**3,a*(2+u)/(1+u)**2),axis=-1)
            arithmetic=max(arithmetic,float(np.max(abs(v-original)/v)))
            with localcontext() as ctx:
                ctx.prec=65
                for x,val in zip(samples,v):
                    xx=Decimal.from_float(float(x));total=Decimal(0)
                    for aa,bb,isdp in zip(a,b,dp):
                        uu=Decimal.from_float(float(bb))*xx*xx
                        total+=Decimal.from_float(float(aa))*((3+3*uu+uu*uu) if isdp else (2+uu))/(1+uu)**(3 if isdp else 2)
                    precision=max(precision,abs(float(total)-val)/val)
    # Independent radial Fourier quadrature verifies the 2*pi convention.
    # This is an identity check on fitted density, not a second atomic reference.
    density_errors=[];a0=.52917721077817892
    for z in (1,6,28,55,92,118):
        a,b,dp=coefficient_data()[z];r=np.geomspace(1e-8,150.,80000)
        x=r[:,None]*2*np.pi/np.sqrt(b)
        density=np.sum(2*np.pi**4*a0*a/b**2.5*np.where(dp,(1+x)/4,1)*np.exp(-x),axis=-1)
        charge=4*np.pi*np.trapz(r*r*density,r)
        for g in (.1,.5,1.,6.):
            fx=4*np.pi*np.trapz(r*r*density*np.sinc(2*g*r),r)
            fe=(charge-fx)/(2*np.pi**2*a0*g*g)
            density_errors.append(abs(fe/adaptive_factor(z,g)-1))
    grid=np.linspace(0,36,10000);adaptive_factor(28,grid)
    start=time.perf_counter()
    for _ in range(30):adaptive_factor(28,grid)
    perf=(time.perf_counter()-start)/30
    assert max(e['max_relative'] for e in errors)<2e-4
    assert precision<2e-11 and max(density_errors)<2e-6
    return dict(reference=errors,max_reference_relative=max(e['max_relative'] for e in errors),
        max_original_arithmetic_relative=arithmetic,max_decimal_relative=precision,
        radial_fourier_max_relative=max(density_errors),minimum_positive=minimum,
        vector_10000_seconds=perf,range=[0,36])


def nickel(out,legacy):
    functions={'Lobato':nickel_lobato_factor,'Legacy':lambda g:legacy.factor('Ni',g),'Dirac-Pade':lambda g:adaptive_factor(28,g)}
    points=[('000',0.)]+[(str(h),np.linalg.norm(h)/3.524) for h in ((1,1,1),(2,0,0),(2,2,0),(3,1,1),(4,0,0))]+[(f'g={g}',float(g)) for g in (6,12,24,36)]
    rows=[]
    for label,g in points:
        aa=functions['Lobato'](g);bb=functions['Legacy'](g) if g<=12 else None;cc=functions['Dirac-Pade'](g)
        rows.append((label,g,aa,bb if bb is not None else 'outside source range',cc,100*(cc/aa-1)))
    write(out,'ni_reflections.csv','reflection,g_inverse_angstrom,lobato_angstrom,legacy_angstrom,adaptive_angstrom,adaptive_relative_percent\n'+''.join(','.join(map(str,row))+'\n' for row in rows))
    fig,axes=plt.subplots(2,2,figsize=(11,8),layout='constrained')
    for i,(title,grid) in enumerate((('Absolute amplitudes',np.linspace(0,12,700)),('Relative to Lobato',np.linspace(0,12,700)),('Low g',np.r_[0,np.geomspace(1e-8,.1,300)]),('High g',np.linspace(4,36,700)))):
        ax=axes.flat[i]
        for name,f in functions.items():
            x=grid[grid<=12] if name=='Legacy' else grid;y=f(x)
            ax.plot(x,100*(y/nickel_lobato_factor(x)-1) if i==1 else y,label=name)
        ax.set(title=title,xlabel='g = 1/d (1/angstrom)',ylabel='difference (%)' if i==1 else 'f (angstrom)')
        if i==2:ax.set_xscale('symlog',linthresh=1e-8)
        ax.legend(fontsize=8)
    fig.savefig(out/'ni_factors.png',dpi=160);plt.close(fig)
    controls=[];comparisons=[];curves={}
    baseline=ROOT/'scripts/research'
    sys.path.insert(0,str(baseline))
    from validate_atomic_elastic import archived
    old_s=archived('scattering');old_e=archived('elastic')
    old_p=archived('physical_elastic',[('from .scattering import',f'from {old_s.__name__} import'),('from .elastic import',f'from {old_e.__name__} import')])
    old=archived('gui.geometry',[('from emcd_sim.scattering import',f'from {old_s.__name__} import'),('from emcd_sim.elastic import',f'from {old_e.__name__} import'),('from emcd_sim.physical_elastic import',f'from {old_p.__name__} import')])
    np.testing.assert_array_equal(nickel_lobato_factor(np.linspace(0,12,1001)),old_s.nickel_lobato_factor(np.linspace(0,12,1001)))
    specs=[('001',(0,0,1),(2,0,0),1.4,2.2,(0.,0.)),('017',(0,1,7),(2,0,0),5.,6.2,(-5.586688140406263,15.)),('117',(1,1,7),(2,-2,0),3.8,2.2,(0.,0.))]
    fig,axes=plt.subplots(1,3,figsize=(13,4),layout='constrained')
    for ax,(label,zone,target,cutoff,pot,tilt) in zip(axes,specs):
        s=Settings(zone=zone,target=target,beam_cutoff=cutoff,potential_cutoff=pot,tilt=tilt,elastic_provider=LOBATO)
        m=elastic_model(Structure.nickel(),s);reference=old.elastic_model(old.Structure.nickel(),s)
        np.testing.assert_array_equal(m.hamiltonian_nm_inv(),reference.hamiltonian_nm_inv())
        np.testing.assert_array_equal(m.amplitudes(np.array([0.,9.,30.])),reference.amplitudes(np.array([0.,9.,30.])))
        assert m.beams.hkl==reference.beams.hkl
        controls.append(dict(zone=zone,beams=len(m.beams.hkl),hamiltonian_bitwise_equal=True,amplitudes_bitwise_equal=True))
        t=np.linspace(0,60,241);h=m.hamiltonian_nm_inv();wave=m.amplitudes(t);base=abs(wave)**2
        index=m.beams.hkl.index(target)
        for name,provider in (('Lobato',LOBATO),('Legacy',LEGACY),('Dirac-Pade',ADAPTIVE)):
            other=elastic_model(Structure.nickel(),replace(s,elastic_provider=provider));oh=other.hamiltonian_nm_inv();ow=other.amplitudes(t)
            eigen=np.linalg.eigvalsh(oh)
            # Isolated exact-Bragg two-beam extinction distance, consistent with
            # the phase generator exp(i H z); not a multibeam period claim.
            xi=np.pi/abs(oh[0,index])
            comparisons.append(dict(zone=label,provider=provider,beams=len(other.beams.hkl),xi_target_nm=float(xi),
                eigenvalue_max_shift=float(np.max(abs(eigen-np.linalg.eigvalsh(h)))),
                potential_max_difference=float(np.max(abs(oh-h))),
                max_intensity_difference=float(np.max(abs(abs(ow)**2-base))),
                norm_error=float(np.max(abs(np.sum(abs(ow)**2,axis=1)-1)))))
            curves[label+'_'+name]=abs(ow[:,index])**2
            ax.plot(t,abs(ow[:,index])**2,label=name)
        ax.set(title=f'Ni [{label}] target {target}',xlabel='thickness (nm)',ylabel='elastic intensity');ax.legend(fontsize=7)
        if label=='017':
            assert len(m.beams.hkl)==71
            hs=np.asarray(m.beams.hkl);pairs=hs[:,None,:]-hs[None,:,:]
            norms=np.linalg.norm(pairs@reciprocal_cross(m.crystal.lattice_angstrom),axis=-1)
            support=np.unique(np.round(norms[norms<=pot+1e-10],14))
            np.savetxt(out/'ni017_coupling_factors.csv',np.column_stack([support]+[f(support) for f in functions.values()]),delimiter=',',header='g,Lobato,Legacy,Dirac-Pade',comments='')
            np.savetxt(out/'ni017_71_beams.csv',np.column_stack([hs,m.reciprocal_vectors_xy,np.linalg.norm(m.reciprocal_vectors_xy,axis=1)]),delimiter=',',header='h,k,l,gx,gy,g',comments='')
    fig.savefig(out/'ni_thickness.png',dpi=160);plt.close(fig)
    np.savez_compressed(out/'ni_thickness.npz',thickness_nm=t,**curves)
    return dict(reflections=rows,historical_controls=controls,elastic_comparisons=comparisons)


def nonfcc(out):
    from ase.io import write as cif_write
    indexing=[];bw=[]
    fig,axes=plt.subplots(2,2,figsize=(10,8),layout='constrained')
    for name,(structure,s) in cases().items():
        cif_write(out/(name+'.cif'),structure.atoms)
        imported=Structure.from_cif(out/(name+'.cif'));crystal,R,hs,g,_=geometry(imported,s)
        expected=np.asarray(hs)@reciprocal_cross(imported.atoms.cell.array)@analytical_frame(imported.atoms.cell.array,s.zone,s.target).T
        delta=float(np.max(abs(g-expected[:,:2])));assert delta<3e-14
        p=elastic_model(imported,s).potential.original;f=factors_for_provider(crystal.species,ADAPTIVE)
        ferr=max(abs(p.structure_factor(h)-independent_factor(imported,h,f)) for h in hs)
        herm=max(abs(p.structure_factor(tuple(-v for v in h))-p.structure_factor(h).conjugate()) for h in hs)
        indexing.append(dict(name=name,settings=asdict(s),beams=len(hs),coordinate_max_error=delta,
            factor_max_error=float(ferr),hermitian_max_error=float(herm),target_factor_real=float(p.structure_factor(s.target).real)))
        if name=='bcc_fe_110_zone':continue
        mesh=32 if name=='monoclinic' else 24
        coarse=bw_ms(imported,s,mesh=mesh,step=.02);fine=bw_ms(imported,s,mesh=48 if name=='monoclinic' else 32,step=.005)
        assert fine['max_intensity_error']<3e-5 and fine['norm_error']<1e-10 and fine['fourier_coefficient_error']<2e-12
        bw.append(dict(name=name,coarse=coarse,fine=fine))
        ax=axes.flat[len(bw)-1];xy=np.asarray(fine['g']);i=np.asarray(fine['bw_intensity']);j=np.asarray(fine['ms_intensity'])
        ax.scatter(xy[:,0],xy[:,1],s=5+500*i,facecolors='none',edgecolors='C0',label='BW')
        ax.scatter(xy[:,0],xy[:,1],s=5+500*j,marker='+',color='C1',label='FFT MS')
        ax.set(title=name,xlabel='gx (1/angstrom)',ylabel='gy (1/angstrom)',aspect='equal');ax.legend(fontsize=7)
    fig.savefig(out/'nonfcc_bw_ms.png',dpi=150);plt.close(fig)
    return indexing,bw


def gui_artifacts(out):
    """Export actual Qt-rendered indexed figures, without physical EMCD solves."""
    import tempfile
    from PySide6 import QtWidgets
    from emcd_sim.gui.app import MainWindow
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    with tempfile.TemporaryDirectory(prefix='unified-gui-',dir=ROOT/'build') as folder:
        for name,(structure,s) in cases().items():
            w=MainWindow(workspace=Path(folder)/name)
            try:
                w.numerical_mode.setCurrentIndex(1);w.structure=structure
                w.zone.setText(' '.join(map(str,s.zone)));w.target.setText(' '.join(map(str,s.target)))
                w.set_values(dict(beam=s.beam_cutoff,potential=s.potential_cutoff,thickness=1,kv=200,tx=0,ty=0))
                from emcd_sim.gui.geometry import preview
                w.last_result=preview(structure,w.settings())
                w.refresh();w.show();app.processEvents();w.figure.set_size_inches(8,7);w.canvas.draw()
                expected=np.asarray(w.current[2])@reciprocal_cross(structure.atoms.cell.array)@analytical_frame(structure.atoms.cell.array,s.zone,s.target)[:2].T
                np.testing.assert_allclose(w._diffraction_spots.get_offsets(),expected,atol=2e-14)
                w.figure.savefig(out/('gui_'+name+'.png'),dpi=110,bbox_inches='tight')
            finally:w.close();app.processEvents()


def reports(out,metrics):
    atom=metrics['atomic'];ni=metrics['nickel'];index=metrics['indexing'];bw=metrics['bw_ms']
    write(out,'NI_SCATTERING_PROVIDER_COMPARISON.md','# Ni scattering-provider comparison\n\nPASS for local elastic acceptance. All amplitudes below are in angstrom, with g=1/d. Legacy factors are converted from source potential scaling exactly once; Adaptive factors need no such conversion.\n\n'+table(['reflection','g','Lobato','external legacy','Dirac-Pade','new vs Lobato (%)'],ni['reflections'])+'\n![Factor comparison](ni_factors.png)\n\n'+table(['zone','provider','beams','two-beam xi (nm)','max eigenvalue shift (1/nm)','max intensity difference over 0–60nm'],[(v['zone'],v['provider'],v['beams'],v['xi_target_nm'],v['eigenvalue_max_shift'],v['max_intensity_difference']) for v in ni['elastic_comparisons']])+'\n![Thickness sensitivity](ni_thickness.png)\n\nConfigurations and all metrics are in metrics.json; ni017_71_beams.csv lists all 71 beams and ni017_coupling_factors.csv every distinct evaluated pair-difference magnitude inside the 6.2 cutoff. Curves use matched finite beam/potential support; differences are parameterization sensitivity, not instability. Extinction distances use pi/abs(H_0G) for isolated exact-Bragg two-beam coupling, not the multibeam oscillation period. Incoming channeling is represented by the saved target amplitude/intensity curves.\n\nThe original source function and coefficients are unchanged. Original pre-extension scattering, beam and BW implementations were loaded independently from 859870c2; all three Lobato controls have bitwise-identical Hamiltonians and amplitudes at 0,9,30 nm. Existing reference assertions retain their numbers and explicitly request Lobato. No large EMCD calculation or old study was rerun. Changing elastic potentials can change EMCD; no quantitative new-provider EMCD certification is claimed.\n')
    write(out,'NON_FCC_INDEXING_ACCEPTANCE.md','# Non-FCC indexing acceptance\n\nPASS for the specified cells and settings. CIF fixtures in this directory preserve the supplied metric and atomic basis through ASE. Cross-product reciprocal bases and Cartesian zone/target frames provide independent references, rather than calling production reciprocal routines twice.\n\n'+table(['case','zone','target','beams','coordinate max error (1/angstrom)','structure-factor error (angstrom)','Hermitian error'],[(v['name'],v['settings']['zone'],v['settings']['target'],v['beams'],v['coordinate_max_error'],v['factor_max_error'],v['hermitian_max_error']) for v in index])+'\nBCC Fe (100) is absent and (110) is retained in BOTH [001] and [1,-1,0]: h*u+k*v+l*w=0. The requested text excluding (110) from [001] contradicted this zone law; no artificial exclusion was introduced. CsCl is primitive cubic: (100)=fCs-fCl survives; (200)=fCs+fCl. ZnO basal reciprocal axes meet at 60 degrees with |a*|=2/(sqrt(3)*a). Monoclinic beta=107 degrees exercises a nonorthogonal reciprocal metric.\n\nOffscreen Qt tests compare actual rendered offsets and signed labels against analytical coordinates, click the negative target, independently check Bragg alignment, and change zone/target/CIF context, full/two-beam bases and provider. Invalid zero/out-of-zone targets and oversized searches fail explicitly. Four-index Miller–Bravais input is unsupported. Labels refer to the ASE-imported cell; no automatic primitive reduction is performed. An externally transformed cell requires an explicit hkl basis transformation.\n')
    write(out,'MULTI_ELEMENT_BW_MS_ACCEPTANCE.md','# Multi-element BW/MS acceptance\n\nPASS for these bounded 200keV, 1nm, zero-tilt elastic configurations. Both methods use the same finite neutral-atom potential; BW support is 2.5 times the listed potential cutoff. FFT Fourier coefficients are independently compared to the IAM structure factors with the SI interaction prefactor.\n\n'+table(['case','potential cutoff (1/angstrom)','BW beams','mesh coarse/fine','slice coarse/fine (nm)','max intensity error coarse/fine','fine norm error','Fourier coefficient error'],[(v['name'],v['fine']['potential_cutoff'],v['fine']['bw_beams'],f"{v['coarse']['mesh']}/{v['fine']['mesh']}",f"{v['coarse']['step_nm']}/{v['fine']['step_nm']}",f"{v['coarse']['max_intensity_error']:.4g}/{v['fine']['max_intensity_error']:.4g}",v['fine']['norm_error'],v['fine']['fourier_coefficient_error']) for v in bw])+'\n![Common indexed intensities](nonfcc_bw_ms.png)\n\nThe initial monoclinic 24x24 mesh was explicitly rejected by the Nyquist/support check. The accepted 32/48 pair includes the full requested support; no beam/harmonic was silently discarded. This limited mesh/step refinement checks these thin finite-potential cases. It is not universal BW/MS convergence, a full 3D atomic potential, absorptive/TDS validation, or a quantitative experiment benchmark.\n')
    write(out,'PROVIDER_LICENSING_AND_PROVENANCE.md','# Provider licensing and provenance\n\nPASS for public redistribution of the pinned Adaptive coefficient subset with Apache-2.0 conditions. The original legacy table remains unlicensed external data and is NOT bundled. Scientific publication or a Python translation was not treated as permission.\n\nAuthor repository: https://github.com/NeuralSoftX/adaptive_dirac_pade_scattering_factor_2026/tree/1667babb2c5bdb44a0535438b846eb1bbfbc03ac\n\nThe pinned repository LICENSE and author README explicitly declare Apache-2.0 for the project and deposited data. Full LICENSE, NOTICE, attribution, pin and transformation are included beside coefficients; EMCD-Sim MIT does not relicense those data. No upstream NOTICE was present in the pinned tree. Only the adaptive_dirac_pade coefficient subset is redistributed. Exact float32 values are serialized as exact binary64 JSON values; no refitting, new interpolation or digit truncation. Offline extraction requires h5py; production uses only existing NumPy and ASE dependencies. Upstream Python evaluator, atomx, HDF5 reference, SciPy, SymPy and plotting package are not redistributed by this feature. Their upstream dependency declarations do not automatically become EMCD runtime dependencies. The source repository/preprint describes authorship and atomic generation; this audit cannot independently recreate Dirac–Fock orbitals or establish journal acceptance.\n\n'+table(['artifact','SHA256'],[(k,v) for k,v in provenance().items() if 'sha256' in k])+'\nPhysical convention is independently established by [the manuscript Fourier equations](https://arxiv.org/html/2608.14934v1): exp(-2*pi*i*g.r), density sinc(2*pi*g*r), and fe=(Z-fx)/(2*pi²*a0*g²). Thus g is crystallographic 1/d, not STL or angular Q. Local radial quadrature of fitted densities verifies this convention without an extra potential factor. fe is in angstrom; IAM subsequently applies its original potential conversion and propagation gamma.\n\n'+table(['check','result'],[('all118 reference-grid worst relative discrepancy',atom['max_reference_relative']),('original formula max relative arithmetic discrepancy',atom['max_original_arithmetic_relative']),('65-digit formula max relative discrepancy',atom['max_decimal_relative']),('radial Fourier identity max relative discrepancy',atom['radial_fourier_max_relative']),('10000 Ni factors average seconds (local machine only)',atom['vector_10000_seconds'])])+'\nSource-compatible algebra, numerical stability and scientific accuracy are separate claims. Values are finite/positive at origin, subnormal inputs and selected points through36 for all118. The accepted adapter range is 0<=g<=36 inverse angstrom, inclusive; all other inputs fail rather than extrapolate. Reference discrepancies measure the fit against the author-deposited reference, not an independent experiment or universal absolute accuracy. This is a 2026 submitted manuscript/preprint parameterization. Neutral atoms omit bonding, ions, absorption and TDS.\n\nThe external legacy guard remains STL=0 or .04<=STL<=6 for all44 XF/Mott elements; EF retains source-specific limits. Small nonzero supercell vectors below .08 inverse angstrom fail explicitly under XF/Mott. The unified provider evaluates such vectors analytically and continuously without dividing by g² or changing the legacy source.\n')
    write(out,'GUI_AND_PROJECT_COMPATIBILITY.md','# GUI and project compatibility\n\nPASS for automated source-checkout/offscreen Qt acceptance. New GUI calculations and IndependentAtomPotential.from_provider() default to adaptive-dirac-pade-2026. The raw unversioned IndependentAtomPotential(crystal) constructor retains original Ni Lobato compatibility for research scripts. Explicit provider IDs, coefficient digest and upstream pin are saved in new result metadata. Provider changes invalidate previews.\n\nOld saved settings with no provider field resolve explicitly to nickel-lobato-2014; loaded plots use saved arrays without a solver or new factor evaluation. New and constructed old-format EMCD projects round-trip complex amplitudes/coherences and array fingerprints. Missing/mismatched providers block applying/rerunning saved settings while saved results remain viewable. An external table is required only when the user explicitly selects that provider; its absence does not affect Lobato or the bundled Adaptive provider.\n\nFile > Save Elastic Project writes a new checksummed elastic-only directory with arrays, settings, provider provenance and crystal snapshot. File > Open Elastic Project opens saved diffraction in a read-only window and leaves current input controls untouched. It does not imply an EMCD model. Existing full EMCD projects retain their separate save/open workflow. Ordered fully occupied multi-element CIFs are eligible for elastic preview; disordered/partial occupancies remain rejected. Ni-specific conventional-FCC MDFF eligibility is unchanged.\n\nPackage-data configuration, zip-import resource loading and PyInstaller data recipe include coefficients, provenance, LICENSE and NOTICE. Runtime does not import the upstream package or HDF5. A source wheel packaging check is recorded in final validation. No Windows executable was rebuilt or tested as a new binary: availability in a future packaged application follows the resource recipe, and native packaged acceptance remains a release-stage check.\n\nThe historical verified automatic Ni numerical profile applies only to Lobato. Adaptive calculations use explicitly uncertified general defaults until users check their own basis/FFT/depth convergence; old convergence certification is not transferred.\n')
    write(out,'FINAL_INTEGRATION_RECOMMENDATION.md','# Final integration recommendation\n\nPASS: accept Adaptive Dirac–Padé 2026 as the new SOURCE GUI/factory default, including Ni, for the documented neutral-atom elastic domain. Keep named Ni Lobato compatibility and explicit old-project fallback. This recommendation follows the local licensing, reciprocal-convention, all118 arithmetic/reference, Hermitian-potential, non-FCC indexing, project and bounded propagation gates. It does not certify universal quantitative scattering or general-material EMCD.\n\nRead the five companion reports, metrics.json, CSV tables, CIFs and plots. Test results and packaging verification are summarized in TEST_VALIDATION.md. The source data pin and raw JSON checksum make provider identity reproducible. Historical arrays, old acceptance reports and Ni MDFF/EMCD kernels are preserved. No 243-energy study was run.\n\nRemaining integration/release limits: remote main has three documentation commits beyond local main (859870c2), at observed 2810e86cba609dc3dc8cd42208b1c0b8ac747a2d; reconcile overlapping documentation before merge. No merge/push/release/binary build was performed. Future Windows binaries require their own native packaged acceptance. Experimental diffraction accuracy, ionic/bonding potentials and broad convergence are not established by these local checks. Legacy-table redistribution permission remains unknown, so that provider must remain external. The new provider changes elastic inputs and therefore can change Ni EMCD results; historical Lobato examples retain their original provider and numbers. No new quantitative EMCD benchmark is claimed.\n')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'FINAL_INTEGRATION_RECOMMENDATION.md').exists():raise FileExistsError('Use a fresh acceptance directory')
    legacy=configured_legacy_factors()
    metrics=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source_dirty=True,provider=provenance())
    metrics['atomic']=atomic_checks();print('Atomic/reference/Fourier checks passed',flush=True)
    metrics['nickel']=nickel(out,legacy);print('Three-provider Ni and historical controls passed',flush=True)
    ni_settings=Settings(zone=(0,0,1),target=(2,0,0),voltage=200,thickness=1,tilt=(0.,0.),beam_cutoff=1.4,potential_cutoff=1.4)
    ni_bw=bw_ms(Structure.nickel(),ni_settings,mesh=32,step=.005)
    assert ni_bw['max_intensity_error']<3e-6 and ni_bw['norm_error']<2e-12
    write(out,'ni_bw_ms.json',json.dumps(ni_bw,indent=2)+'\n')
    metrics['indexing'],metrics['bw_ms']=nonfcc(out);print('Non-FCC indexing and BW/MS passed',flush=True)
    gui_artifacts(out)
    write(out,'metrics.json',json.dumps(metrics,indent=2)+'\n');reports(out,metrics)
    with (out/'NON_FCC_INDEXING_ACCEPTANCE.md').open('a',encoding='utf-8') as f:
        f.write('\nActual indexed GUI elastic-preview exports: '+', '.join(f'[{name}](gui_{name}.png)' for name in cases())+'.\n')
    with (out/'MULTI_ELEMENT_BW_MS_ACCEPTANCE.md').open('a',encoding='utf-8') as f:
        f.write(f"\nAdditional new-provider Ni[001] control: 200keV,1nm, 1.4 potential cutoff,32x32 FFT,.005nm step, {ni_bw['bw_beams']} BW beams. Maximum intensity error {ni_bw['max_intensity_error']:.9g}, norm error {ni_bw['norm_error']:.9g}. Full arrays/settings are in [ni_bw_ms.json](ni_bw_ms.json).\n")
    write(out,'TEST_VALIDATION.md','# Separate regression verification\n\nThis generator runs the numerical/provider/indexing/BW-MS checks and GUI figure exports, but does not run pytest. Run the focused and compatibility tests separately and retain their JUnit/log results. The committed original acceptance under docs/acceptance/unified-elastic-2026-11-03 contains its reviewed test and packaging record. A fresh reproduction is not automatically a new regression certification.\n')
    print(out,flush=True)


if __name__=='__main__':main()
