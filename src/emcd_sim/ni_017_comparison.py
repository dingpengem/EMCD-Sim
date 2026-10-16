"""Compare saved [017]/[710] elasticity and separate magnetization conventions."""
from pathlib import Path
import hashlib,json
import numpy as np
from .ni_017_geometry import Ni017Geometry,rotated_tensor
from .ni_710_geometry import Ni710Geometry
from .ni_017_mistilt import Config,csv_write
from .ni_mistilt_series import write_json,METHODS,EDGES
from .ni_mistilt_eels import case_name
from .single_channeling_tensor import run_tensor_with_coherence


def export_normalized_pairs(root):
    """Explicit A and alpha*B spectra, derived only from saved detector EELS."""
    root=Path(root)
    for source in [root/'mistilt_eels.npz',*root.glob('case_*/virtual_detector_eels.npz')]:
        with np.load(source,allow_pickle=False) as s:
            a=s['I_A_plus'];b=s['alpha'][...,None]*s['I_B_plus']
            np.testing.assert_allclose(a-b,s['D_corrected'],atol=1e-14)
            arrays=dict(energy_ev=s['energy_ev'],method_labels=s['method_labels'],
                        I_A_postedge=a,I_B_postedge=b,alpha=s['alpha'],D_corrected=s['D_corrected'])
            if 'delta_x_mrad' in s:arrays['delta_x_mrad']=s['delta_x_mrad']
            np.savez_compressed(source.with_name('postedge_normalized_eels.npz'),**arrays)


def compare(source='data/wien2k_ni/Ni_fm.xmcd',root=Path('outputs/ni_017_minorzone_mistilt')):
    root=Path(root);oldroot=Path('outputs/ni_710_minorzone_mistilt')
    newmeta=json.loads((root/'comparison_metadata.json').read_text());oldmeta=json.loads((oldroot/'comparison_metadata.json').read_text())
    cfg=Config(**newmeta['config']);oldgeo=Ni710Geometry();newgeo=Ni017Geometry()
    for key in ('thickness_nm','acceleration_kv','potential_cutoff','beam_cutoff','fft_grid','slice_step_nm','depth_steps','detector_grid','aperture_subpixels'):
        if newmeta['config'][key]!=oldmeta['config'][key]:raise ValueError('Elastic/detector setting not matched: '+key)
    elastic=[];magnetic=[];energies=np.array([cfg.l3_energy_ev,cfg.l2_energy_ev])
    for offset in cfg.offsets():
        folder=case_name(offset);a=np.load(oldroot/folder/'checkpoint.npz',allow_pickle=False)
        b=np.load(root/folder/'checkpoint.npz',allow_pickle=False)
        old=oldgeo.model(offset);new=newgeo.model(offset)
        mapped=[(l,-k,-h) for h,k,l in old.elastic.beams.hkl]
        ix=[mapped.index(h) for h in new.elastic.beams.hkl]
        Herror=float(np.max(abs(old.elastic.hamiltonian_nm_inv()[np.ix_(ix,ix)]-new.elastic.hamiltonian_nm_inv())))
        for method,ak,ck in zip(METHODS,('bw_amplitudes','ms_amplitudes_projected'),('coherence_bw','coherence_ms')):
            wave_error=float(np.max(abs(a[ak][:,ix]-b[ak])))
            Cerror=float(np.linalg.norm(a[ck][np.ix_(ix,ix)]-b[ck]))
            elastic.append(dict(delta_x_mrad=float(offset),method=method,H_max_abs=Herror,
                amplitude_max_abs=wave_error,coherence_fro_abs=Cerror,
                exit_intensity_max_abs=float(np.max(abs(abs(a[ak][-1,ix])**2-abs(b[ak][-1])**2)))))
            # Correct crystal-[001] reference for [710], at the SAME verified energies.
            comparisons=[('710_corrected_crystal001',old,oldgeo.frame,a[ck]),
                         ('017_crystal001',new,newgeo.frame,b[ck])]
            if abs(offset)<1e-12:
                comparisons.extend([('710_historical_local_z_at_new_energies',old,np.eye(3),a[ck]),
                                    ('710_matched_local_017_tensor_control',old,newgeo.frame,a[ck])])
            for label,model,R,C in comparisons:
                p,m=[run_tensor_with_coherence(model,rotated_tensor(source,energies,eta=sign,beta=cfg.beta,frame=R),C,
                    thickness_nm=cfg.thickness_nm,grid_size=cfg.detector_grid,integration_mode=cfg.integration_mode,
                    aperture_subpixels=cfg.aperture_subpixels) for sign in (1,-1)]
                for i,edge in enumerate(EDGES):
                    ap,bp,am,bm=[r.chiral_spectrum(g)[i] for r,g in ((p,'A'),(p,'B'),(m,'A'),(m,'B'))]
                    magnetic.append(dict(delta_x_mrad=float(offset),method=method,configuration=label,edge=edge,
                        energy_ev=float(energies[i]),magnetic_difference=float((ap-bp-am+bm)/2),
                        nonmagnetic_difference=float((ap+am-bp-bm)/2),Sigma_ref=float((ap+bp+am+bm)/2)))
    csv_write(root/'elastic_710_017_comparison.csv',elastic);csv_write(root/'magnetic_710_017_comparison.csv',magnetic)
    info=dict(hkl_mapping_equal_local_xy='(h,k,l)_710 -> (l,-k,-h)_017; local projected coordinates identical',
        cubic_permutation='Swapping cubic x/z maps [710] to [017] while reversing local y. The equal-local-xy map also reverses the longitudinal axis; this is harmless for this z-independent centrosymmetric elastic projection, not a rule for rotating an axial magnetic tensor.',
        max_elastic_amplitude_error=max(r['amplitude_max_abs'] for r in elastic),max_coherence_error=max(r['coherence_fro_abs'] for r in elastic),
        magnetization_cubic=[0,0,1],magnetization_017=(newgeo.frame@np.array([0,0,1])).tolist(),
        corrected_magnetization_710=(oldgeo.frame@np.array([0,0,1])).tolist(),
        historical_710_magnetization_local=[0,0,1],historical_710_magnetization_cubic=oldgeo.frame[2].tolist(),
        interpretation='Historical [710] used M parallel local [710], not cubic [001]. Compare corrected [710] crystal001 separately at matched native energies. A matched-local-tensor control isolates elastic/indexing equivalence from physical magnetization differences.')
    write_json(root/'orientation_comparison.json',info)
    export_normalized_pairs(root)
    print(info)


if __name__=='__main__':compare()
