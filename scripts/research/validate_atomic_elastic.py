"""Bounded elastic-only review probes; never reads historical study outputs."""
from pathlib import Path
import argparse
import csv
import difflib
import hashlib
import json
import subprocess
import sys
import types

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np

from emcd_sim.crystal import Crystal
from emcd_sim.elastic import BeamSet
from emcd_sim.geometry import Microscope, electron_wavelength_angstrom
from emcd_sim.scattering import IndependentAtomPotential, FourierCutoffPotential, nickel_lobato_factor
from emcd_sim.legacy_atomic_factors import configured_legacy_factors
from emcd_sim.physical_elastic import PhysicalElasticModel
from emcd_sim.projected_geometry import ProjectedGeometry
from emcd_sim.projected_potential import prepare_projected_potential, potential_site_labels
from emcd_sim.multislice_double_channeling import FFTSplitStep

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/elastic-mott-final-review'
BASE='859870c2cb6ee9034249aecc890703c571b4cbd4'
REVIEW_FILES = (
    'README.md', 'docs/INDEX.md', 'docs/USER_GUIDE.md',
    'docs/ELASTIC_ATOMIC_FACTORS.md', 'docs/ELASTIC_PROVIDER_REVIEW.md',
    'src/emcd_sim/scattering.py', 'src/emcd_sim/elastic.py',
    'src/emcd_sim/physical_elastic.py', 'src/emcd_sim/legacy_atomic_factors.py',
    'src/emcd_sim/gui/app.py', 'src/emcd_sim/gui/geometry.py',
    'src/emcd_sim/gui/emcd_forward.py', 'tests/test_gui_stage_a.py',
    'tests/test_species_weighted_elastic.py', 'tests/test_legacy_atomic_factors.py',
    'scripts/research/validate_atomic_elastic.py', 'scripts/research/audit_legacy_mott.py',
)


def archived(name, replacements=()):
    source=subprocess.check_output(['git','show',f'{BASE}:src/emcd_sim/{name.replace(".","/")}.py'],cwd=ROOT).decode('utf-8-sig')
    for before,after in replacements:source=source.replace(before,after)
    fullname='emcd_sim._elastic_audit_'+name.replace('.','_')
    module=types.ModuleType(fullname);module.__package__='emcd_sim.gui' if name.startswith('gui.') else 'emcd_sim'
    sys.modules[fullname]=module
    exec(compile(source,f'baseline:{name}', 'exec'),module.__dict__)
    return module


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    table=configured_legacy_factors()
    from audit_legacy_mott import audit, write_report
    mott_audit=audit(table)
    write_report(mott_audit,OUT)
    g=np.array([0.,2/3.524,1.,2.])
    with (OUT/'ni_provider_comparison.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['g_inverse_angstrom','lobato_angstrom','legacy_angstrom','relative_difference_percent'])
        writer.writerows(zip(g,nickel_lobato_factor(g),table.factor('Ni',g),100*(table.factor('Ni',g)/nickel_lobato_factor(g)-1)))
    from emcd_sim.gui.geometry import Structure,Settings,elastic_model
    # Use the original dependencies as well as the original GUI adapter.
    # Importing an old adapter against the modified solver is not an
    # independent numerical reference.
    old_scattering=archived('scattering')
    old_elastic=archived('elastic')
    old_physical=archived('physical_elastic', [
        ('from .scattering import',f'from {old_scattering.__name__} import'),
        ('from .elastic import',f'from {old_elastic.__name__} import'),
    ])
    old=archived('gui.geometry', [
        ('from emcd_sim.scattering import',f'from {old_scattering.__name__} import'),
        ('from emcd_sim.elastic import',f'from {old_elastic.__name__} import'),
        ('from emcd_sim.physical_elastic import',f'from {old_physical.__name__} import'),
    ])
    np.testing.assert_array_equal(nickel_lobato_factor(np.linspace(0,12,1001)),
                                 old_scattering.nickel_lobato_factor(np.linspace(0,12,1001)))
    baselines=[]
    for zone,target,cutoff in [((0,0,1),(2,0,0),1.4),((0,1,7),(2,0,0),2.2),((1,1,7),(2,-2,0),3.8)]:
        settings=Settings(zone=zone,target=target,beam_cutoff=cutoff,potential_cutoff=2.2,tilt=(0.,0.))
        reference=old.elastic_model(old.Structure.nickel(),settings)
        current=elastic_model(Structure.nickel(),settings)
        assert current.beams.hkl==reference.beams.hkl
        np.testing.assert_array_equal(current.hamiltonian_nm_inv(),reference.hamiltonian_nm_inv())
        np.testing.assert_array_equal(current.amplitudes(np.array([0.,9.,30.])),reference.amplitudes(np.array([0.,9.,30.])))
        baselines.append(dict(zone=zone,target=target,beam_count=len(current.beams.hkl),
                              beam_order_identical=True,hamiltonian_bitwise_equal=True,amplitudes_bitwise_equal=True))
    fig,axes=plt.subplots(3,2,figsize=(9,12),layout='constrained')
    comparisons=[]
    cases=[('CsCl',('Cs','Cl'),[[0,0,0],[.5,.5,.5]],4.1,(1,0,0),.55),
           ('FCC Cu',('Cu',)*4,[[0,0,0],[0,.5,.5],[.5,0,.5],[.5,.5,0]],3.615,(2,0,0),.85),
           ('BCC Mo',('Mo','Mo'),[[0,0,0],[.5,.5,.5]],3.147,(2,0,0),.85)]
    for row,(name,symbols,positions,a,target,cutoff) in enumerate(cases):
        crystal=Crystal(np.eye(3)*a,np.array(positions,float),symbols)
        potential=IndependentAtomPotential(crystal,atomic_factors=table.atomic_factors(symbols))
        geometry=ProjectedGeometry.from_oriented(crystal,(0,0,1),target,labels=potential_site_labels(potential))
        projected=prepare_projected_potential(geometry,potential,200.,24,cutoff)
        beam_cutoff=1.6 if name=='CsCl' else 2.2
        beams=BeamSet.zolz(crystal,beam_cutoff,401,potential=potential)
        bw=PhysicalElasticModel(crystal,Microscope(200),beams,FourierCutoffPotential(potential,cutoff))
        kinetic=(-10*np.pi*electron_wavelength_angstrom(200)*np.sum(projected.reciprocal_xy**2,axis=1)).reshape(24,24)
        plan=FFTSplitStep(projected.phase_nm_inv,kinetic)
        entrance=np.zeros(24**2,complex);entrance[0]=1.
        fine=plan.advance(entrance,200,.005);coarse=plan.advance(entrance,100,.01)
        lookup={tuple(h):i for i,h in enumerate(projected.hkl)}
        indices=np.array([lookup[h] for h in beams.hkl])
        ibw=abs(bw.amplitudes(np.array([1.]))[0])**2
        fine_error=float(np.max(abs(abs(fine[indices])**2-ibw)))
        coarse_error=float(np.max(abs(abs(coarse[indices])**2-ibw)))
        assert fine_error<2e-6 and fine_error<=coarse_error+1e-10
        np.testing.assert_allclose(np.sum(abs(fine)**2),1,atol=1e-12)
        h=bw.hamiltonian_nm_inv()
        np.testing.assert_allclose(h,h.conj().T,atol=1e-14)
        values=dict(material=name,zone=[0,0,1],voltage_kv=200,thickness_nm=1,
            lattice_angstrom=a,species=symbols,positions=positions,potential_cutoff=cutoff,
            beam_cutoff=beam_cutoff,beam_count=len(beams.hkl),fft_shape=[24,24],
            fine_step_nm=.005,coarse_step_nm=.01,max_intensity_error_fine=fine_error,
            max_intensity_error_coarse=coarse_error,fft_norm_error=float(abs(np.sum(abs(fine)**2)-1)),
            hamiltonian_hermiticity_error=float(np.max(abs(h-h.conj().T))),
            f100_angstrom=[potential.structure_factor((1,0,0)).real,potential.structure_factor((1,0,0)).imag])
        comparisons.append(values)
        for col,intensity in enumerate([ibw,abs(fine[indices])**2]):
            ax=axes[row,col];xy=bw.reciprocal_vectors_xy
            artist=ax.scatter(xy[:,0],xy[:,1],c=np.maximum(intensity,1e-12),s=55,
                norm=LogNorm(vmin=1e-10,vmax=1),cmap='viridis')
            ax.set(title=f'{name}: {"BW" if col==0 else "FFT multislice"}',
                   xlabel='gx (inverse angstrom)',ylabel='gy (inverse angstrom)',aspect='equal')
        fig.colorbar(artist,ax=list(axes[row]),label='Diffracted intensity / incident flux')
    fig.suptitle('Elastic-only controls | [001] | 200 kV | 1 nm | matched finite IAM potentials')
    fig.savefig(OUT/'elastic_patterns.png',dpi=180);plt.close(fig)
    report=dict(base_commit=BASE,provider=table.provenance(),ni_compatibility=baselines,
        original_ni_factor_samples_bitwise_equal=1001,
        bw_ms=comparisons,source_table_bundled=False,redistribution_status='unverified',
        restrictions='Ni-specific MDFF/EMCD unchanged in scope; no absorption, TDS or bonding model')
    report['mott_numerical_validity']={k:v for k,v in mott_audit.items()
        if k not in ('records','source_interval_checks','low_stl_samples')}
    protected=['src/emcd_sim/'+name+'.py' for name in ['mdff_tensor','ni_local_mdff',
        'xmcd_effective_mdff','double_channeling','single_channeling_tensor',
        'multislice_double_channeling','multislice_reference','projected_potential']]
    protected.append('data/wien2k_ni/Ni_fm.xmcd')
    protected.extend(['tests/test_physical_elastic.py', 'tests/test_elastic_reference.py',
        'tests/test_general_projected_equivalence.py',
        'docs/images/v070b1/provenance.json',
        'docs/images/ni017_flipm_recomputed/provenance.json',
        'docs/images/ni017_flipm_recomputed/selected_native_L3_L2.csv'])
    subprocess.run(['git','diff','--exit-code',BASE,'--',*protected],cwd=ROOT,check=True,capture_output=True)
    report['unchanged_kernel_and_input_sha256']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in protected}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    text='# Local elastic extension validation\n\n'
    text+=f'Base: `{BASE}`. Provider source SHA256: `{table.source_sha256}`.\n\n'
    text+='Original Ni Lobato defaults and beam order are retained. Three archived GUI-geometry controls ([001], [017], [117]) produce bitwise-identical Hamiltonians and amplitudes at 0, 9 and 30 nm; the propagation kernels and Ni factors are unchanged. The archived geometry is read from Git in memory; no archived output/checkpoint is loaded or modified.\n\n'
    text+='The adapter delegates interpolation to the pinned source. Tests cover all 98 elements on samples in the accepted operating domain plus usable native nodes, EF and Mott unit conversion, H bounds, invalid arguments, missing/rejected markers, CIF occupancy restrictions and independent Ni-only MDFF gating. All 44 XF/Mott rows have a separate complete interval audit.\n\n'
    text+='The baseline independently loads the original scattering, beam-selection and BW model modules from Git, as well as the original GUI geometry adapter. All 1,001 Ni factor samples on |g|=0..12 match bit for bit. Protected kernels, reference tests, XMCD input and historical figure provenance/selected values have no diff against the base.\n\n'
    text+='**XF/Mott numerical operating domain: STL=0 or 0.04<=STL<=6 (|g|=0 or 0.08<=|g|<=12 inverse angstrom).** Smaller positive inputs, including finite but unreliable source values and underflow cases, fail explicitly. The source algorithm/tables and separate zero behavior are preserved. The lower boundary is the common native knot after the last failed positivity/origin-bound/nonincrease interval among all 44 elements; Os determines it. See [all-element low-STL report](MOTT_LOW_STL_REPORT.md), [raw-source samples](mott_low_stl_samples.csv) and [80-digit interval audit](mott_low_stl_audit.json). These checks establish numerical operating limits and necessary physical consistency, not quantitative accuracy against independent atomic data.\n\n'
    text+='|Elastic control|BW beams|Fine BW/MS max intensity error|Coarse error|FFT norm error|\n|---|---:|---:|---:|---:|\n'
    for c in comparisons:text+=f"|{c['material']}|{c['beam_count']}|{c['max_intensity_error_fine']:.6g}|{c['max_intensity_error_coarse']:.6g}|{c['fft_norm_error']:.6g}|\n"
    text+='\nThese are bounded 1 nm elastic controls, not large EMCD studies or global convergence certification. [Elastic diffraction patterns](elastic_patterns.png), [numerical record](validation.json), [Ni provider comparison](ni_provider_comparison.csv), and [proposed diff](proposed.patch) accompany this report.\n\n'
    text+='The original Ni factor at (200), |g|=2/3.524 inverse angstrom, is 2.620741145906177 angstrom; the new provider gives 2.6041598997444053 angstrom (-0.632693%). At |g|=0 the values are 6.564900 and 6.569000 angstrom. These are separate parameterizations, not interchangeable numerical defaults.\n\n'
    results=OUT/'test_results.json'
    if results.exists():
        report['session_test_results']=json.loads(results.read_text(encoding='utf-8'))
        (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        for result in report['session_test_results']:
            text+=f"Observed {result['suite']}: **{result['passed']} passed**, {result['failed']} failed. Command: `{result['command']}`.\n\n"
    text+='The external table and Python translation have no established public redistribution permission in the supplied file. They remain outside Git; source hash, scaling and limits are recorded. This report precedes the authorized local feature-branch commit. No merge, push, Windows rebuild, release, MDFF-kernel edit or historical-data rewrite is part of this review.\n'
    (OUT/'VALIDATION_REPORT.md').write_text(text,encoding='utf-8')
    # Include new source/test/docs files without staging or changing Git's index.
    patch=subprocess.check_output(['git','diff','--binary','--no-ext-diff',BASE,'--',*REVIEW_FILES],cwd=ROOT)
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT).decode().splitlines()
    for name in untracked:
        if name not in REVIEW_FILES:
            continue  # Preserve and exclude unrelated user files.
        body=(ROOT/name).read_text(encoding='utf-8').splitlines(keepends=True)
        patch+=f'diff --git a/{name} b/{name}\nnew file mode 100644\n'.encode()
        patch+=''.join(difflib.unified_diff([],body,fromfile='/dev/null',tofile='b/'+name)).encode('utf-8')
    (OUT/'proposed.patch').write_bytes(patch)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUT,
                        help='Use a new outputs subdirectory to preserve earlier review artifacts')
    args=parser.parse_args()
    OUT=args.output.resolve()
    if not OUT.is_relative_to((ROOT/'outputs').resolve()):
        parser.error('--output must stay within this worktree outputs directory')
    main()
