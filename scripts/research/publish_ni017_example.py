"""Validate and render documentation from the completed Ni recalculation; no solver calls.

Run from the repository root with Python, NumPy, Matplotlib and Pillow installed.
Research outputs remain local; only compact previews and selected rows are published.
"""
from pathlib import Path
import csv
import hashlib
import json
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "outputs/ni_300kv_bragg_y15_full_recalculation/20261103T225908Z"
DEST = ROOT / "docs/images/ni017_flipm_recomputed"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    settings = json.loads((STUDY / "simulation_settings.json").read_text())
    manifest = json.loads((STUDY / "metadata/final_sha256.json").read_text())
    for name, digest in manifest.items():
        assert sha(STUDY / name.replace('\\', '/')) == digest, name
    for name, digest in settings['source_hashes'].items():
        assert sha(ROOT / name.replace('\\', '/')) == digest, name
    acceptance = json.loads((STUDY / "metadata/final_acceptance.json").read_text())
    assert acceptance["completed"] and acceptance["production_energies"] == 486
    assert settings["new_study_not_historical"]
    curves, checks, sources = {}, {}, {}
    for t in (9, 30):
        p = STUDY / f"data/full/t{t}nm.npz"
        sources[str(p.relative_to(STUDY))] = sha(p)
        z = np.load(p, allow_pickle=False)
        e, ap, am, bp, bm = [z[k] for k in
            ("energy_ev", "I_A_plus", "I_A_minus", "I_B_plus", "I_B_minus")]
        expected = np.unique(np.r_[np.linspace(823.625, 882.521, 241), 831.271, 848.698])
        np.testing.assert_allclose(e, expected, rtol=0, atol=1e-10)
        assert all(np.isfinite(a).all() and (a >= 0).all() for a in (ap, am, bp, bm))
        na, nb, ma, mb = (ap+am)/2, (bp+bm)/2, (ap-am)/2, (bp-bm)/2
        dc, dm, dn, df = ap-bp, ma-mb, na-nb, ap-am
        sab, sf = ap+bp, ap+am
        assert (sab > 1e-12*sab.max()).all() and (sf > 1e-12*sf.max()).all()
        ac, ag, an, af = 100*dc/sab, 100*dm/sab, 100*dn/sab, 100*df/sf
        np.testing.assert_allclose(dc, dm+dn, rtol=1e-12, atol=1e-14)
        np.testing.assert_allclose(ac, ag+an, rtol=1e-12, atol=1e-12)
        np.testing.assert_array_equal(df, 2*ma)
        assert np.ptp(dn) > 0 and (na > 0).all()
        meta = json.loads((STUDY / f"data/full/t{t}nm_metadata.json").read_text())
        assert meta["physics_convention"] == "forward_born_dagger_g_minus_h_v1"
        assert meta["settings"]["thickness"] == t
        np.testing.assert_allclose(meta["energy_ev"], e)
        # Compare every derived CSV column to independent four-spectrum algebra.
        rows = np.genfromtxt(STUDY / f"spectra_{t}nm.csv", delimiter=",", names=True)
        derived = dict(D_conventional=dc, D_magnetic=dm, D_nonmagnetic=dn,
                       D_flip_A=df, A_conventional=ac, A_magnetic=ag,
                       A_nonmagnetic=an, A_flip_A=af, S_AB=sab, S_flip_A=sf)
        for k, a in derived.items():
            np.testing.assert_allclose(rows[k], a, rtol=1e-12, atol=1e-14)
        curves[t] = (e, (dc, dm, dn, df), (ac, ag, an, af))
        checks[t] = dict(energy_count=len(e), minimum_eels=float(min(a.min() for a in (ap,am,bp,bm))),
            raw_identity_max_error=float(np.max(abs(dc-dm-dn))),
            percent_identity_max_error_pp=float(np.max(abs(ac-ag-an))),
            flip_raw_max_error=float(np.max(abs(df-2*ma))),
            flip_nonmagnetic_residual=0, flip_percent_nonmagnetic_residual=0,
            nonmagnetic_raw_range=[float(dn.min()),float(dn.max())],
            nonmagnetic_percent_range=[float(an.min()),float(an.max())],
            detector_and_reversal_metadata={k:meta[k] for k in ("integration","reversal","magnetization_crystal","magnetization_local","s_target")})
    np.testing.assert_array_equal(curves[9][0], curves[30][0])
    items = []
    # Existing primary figures were generated from this run; verify their physical sizes.
    for folder in ("raw_au", "asymmetry_percent"):
        for p in sorted((STUDY / folder).glob("*.png")):
            t = 30 if '30nm' in p.name else 9
            e = curves[t][0]
            dc, dm, dn, df = curves[t][1 if folder == 'raw_au' else 2]
            prefix, suffix = ('D', 'au') if folder == 'raw_au' else ('A', 'percent')
            plotted = np.genfromtxt(p.with_suffix('.csv'), delimiter=',', names=True)
            np.testing.assert_array_equal(plotted['energy_ev'], e)
            expected_curves = {f'{prefix}_conventional_{suffix}': dc,
                f'{prefix}_mag_AB_{suffix}': dm, f'{prefix}_nonmag_AB_{suffix}': dn,
                f'{prefix}_flip_A_{suffix}': df, f'{prefix}_flip_magnetic_A_{suffix}': df,
                f'{prefix}_flip_nonmagnetic_A_{suffix}': np.zeros_like(e)}
            for k in plotted.dtype.names[1:]:
                if k in expected_curves:
                    np.testing.assert_allclose(plotted[k], expected_curves[k], rtol=1e-12, atol=1e-14)
            with Image.open(p) as im:
                assert im.size == (1800,2100)
                assert all(abs(x-300)<1 for x in im.info["dpi"])
                im.thumbnail((900,1050))
                target = DEST / f"{folder}_{p.name}"
                im.save(target, optimize=True)
            svg = p.with_suffix(".svg")
            tree = ET.parse(svg).getroot()
            assert tree.attrib["width"] == "432pt" and tree.attrib["height"] == "504pt"
            # Render a new documentation edition from the independently derived arrays.
            # Keep the completed run's original figures and all scientific outputs intact.
            fig, ax = plt.subplots(figsize=(6,7))
            if 'conventional' in p.stem:
                series = [(dc,'black','-','Conventional total'),
                          (dm,'red','--','Magnetic A/B contribution'),
                          (dn,'green','-.','Nonmagnetic A/B contribution')]
                title = 'Conventional A/B'
            elif 'magcomponent' in p.stem:
                series = [(dm,'red','--','Magnetic-only A/B'),
                          (df,'blue','-','Fixed-detector A Flip-M')]
                title = 'Magnetic-only A/B vs Flip-M'
            else:
                series = [(df,'blue','-','Flip-M total'),
                          (df,'red','--','Magnetic (overlaps total)'),
                          (np.zeros_like(e),'green','-.','Nonmagnetic residual = 0')]
                title = 'Fixed-detector A Flip-M'
            for y,color,style,label in series:
                ax.plot(e,y,color=color,ls=style,lw=2 if color=='blue' else 1.5,label=label)
            ax.axhline(0,color='.6',lw=.7,zorder=0)
            for label,edge in [('L3',831.271),('L2',848.698)]:
                ax.axvline(edge,color='.65',ls=':',lw=.8)
                ax.text(edge+.4,.97,f'{label}\n{edge:.3f} eV',transform=ax.get_xaxis_transform(),
                        va='top',fontsize=9,color='.3')
            ax.set(xlim=(e[0],e[-1]),xlabel='Energy loss (eV)',
                   ylabel='Signed difference (a.u.)' if folder=='raw_au' else 'EMCD asymmetry (%)',
                   title=f'Ni [017], {t} nm\n{title}')
            ax.margins(y=.17);ax.legend(fontsize=9,loc='lower right')
            fig.tight_layout()
            edition = STUDY/'documentation_figures'/folder
            edition.mkdir(parents=True,exist_ok=True)
            full = edition/p.name
            fig.savefig(full,dpi=300);fig.savefig(full.with_suffix('.svg'))
            plt.close(fig)
            with Image.open(full) as im:
                assert im.size == (1800,2100)
                im.thumbnail((900,1050));im.save(target,optimize=True)
            items.append(dict(file=target.name, preview_sha256=sha(target),
                source=str(full.relative_to(STUDY)), source_sha256=sha(full),
                svg_sha256=sha(full.with_suffix('.svg')),
                original_figure_sha256=sha(p), plotted_csv_sha256=sha(p.with_suffix('.csv'))))
    assert len(items) == 12
    for unit, idx, ylabel in (("percent",2,"EMCD asymmetry (%)"),("raw",1,"Signed difference (a.u.)")):
        fig, axes = plt.subplots(2,2,figsize=(10,8),sharex=True,sharey=True)
        for row,t in enumerate((9,30)):
            e = curves[t][0]; dc,dm,dn,df = curves[t][idx]
            for col in (0,1):
                ax=axes[row,col]
                if col==0:
                    for y,c,label in ((dc,"black","Conventional total"),(dm,"#c62828","Magnetic A/B"),(dn,"#238b45","Nonmagnetic A/B")):
                        ax.plot(e,y,color=c,label=label,lw=1.4)
                else:
                    ax.plot(e,df,color="#1764c0",lw=2.5,label="Flip-M total")
                    ax.plot(e,df,color="#c62828",ls="--",lw=1.2,label="Magnetic (overlaps total)")
                    ax.plot(e,np.zeros_like(e),color="#238b45",ls=":",lw=1.7,label="Nonmagnetic residual = 0")
                ax.axhline(0,color="0.6",lw=.6,zorder=0)
                for edge in (831.271,848.698): ax.axvline(edge,color="0.65",ls=":",lw=.8)
                ax.set_title(f"{t} nm | {'Conventional A/B' if col==0 else 'Fixed-detector A Flip-M'}")
                ax.set_xlim(e[0],e[-1]);ax.legend(fontsize=8,loc="lower right")
                if col==0: ax.set_ylabel(ylabel)
                if row==1: ax.set_xlabel("Energy loss (eV)")
        fig.suptitle("Ni [017] | 300 kV | exact (200) Bragg | Y = +15 mrad\nDotted markers: native L3 831.271 / L2 848.698 eV",fontsize=12)
        fig.tight_layout(rect=(0,0,1,.93))
        # Add only new derived figures; never overwrite simulation arrays or reports.
        full=STUDY / f"documentation_summary_{unit}.png"
        fig.savefig(full,dpi=300);fig.savefig(full.with_suffix('.svg'))
        target=DEST / f"summary_{unit}.png"
        with Image.open(full) as im:
            im.thumbnail((1500,1200));im.save(target,optimize=True)
        plt.close(fig)
        items.append(dict(file=target.name,preview_sha256=sha(target),source=full.name,source_sha256=sha(full)))
    selected = list(csv.DictReader((STUDY / 'data/selected_native_L3_L2.csv').open()))
    for row in selected:
        t=int(row['thickness_nm']);e=curves[t][0];i=np.flatnonzero(e==float(row['energy_ev'])).item()
        for keys,idx in ((('D_conventional','D_magnetic','D_nonmagnetic','D_flip_A'),1),
                         (('A_conventional','A_magnetic','A_nonmagnetic','A_flip_A'),2)):
            for k,a in zip(keys,curves[t][idx]): np.testing.assert_allclose(float(row[k]),a[i],rtol=1e-12)
    (DEST/'selected_native_L3_L2.csv').write_text((STUDY/'data/selected_native_L3_L2.csv').read_text(),encoding='utf-8')
    config = dict(settings['config']);config['source']='data/wien2k_ni/Ni_fm.xmcd'
    controls = list(csv.DictReader((STUDY/'diagnostics/targeted_convergence.csv').open()))
    assert len(controls) == 8 and all(r['passed'] == 'True' for r in controls)
    assert all(float(r['max_raw_relative_error']) <= .001 and
               float(r['max_asymmetry_difference_pp']) <= .01 for r in controls)
    provenance=dict(study_relative_directory=str(STUDY.relative_to(ROOT)).replace('\\','/'),
        worktree_relative_to_original_workspace='build/v070b1-unit-clean-main',
        source_commit=settings['source_commit'],physics_convention='forward_born_dagger_g_minus_h_v1',
        physics_gui_source_sha256=settings['source_hashes'],
        xmcd_sha256=settings['mdff_file_sha256'],settings=settings['settings'],config=config,
        thicknesses_nm=[9,30],energy_grid=curves[9][0].tolist(),frame=settings['frame'],
        completion=acceptance,validation=checks,source_arrays_sha256=sources,figures=items,
        original_manifest_files_verified=len(manifest), targeted_convergence_controls=controls,
        source_report_sha256={str(p.relative_to(STUDY)):sha(p) for p in
            [STUDY/'simulation_settings.json',STUDY/'metadata/calculation_complete.json',
             STUDY/'metadata/final_acceptance.json',STUDY/'diagnostics/validation.json',
             STUDY/'diagnostics/targeted_convergence.csv']},
        selected_csv_sha256_lf=sha(DEST/'selected_native_L3_L2.csv'),
        processing='PNG previews resized with Pillow thumbnail only; spectral arrays never smoothed, interpolated or rescaled.',
        convergence_scope='8 selected-energy depth/grid controls only; no global basis, cutoff, spectral or experimental convergence')
    (DEST/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(checks,indent=2))


if __name__ == '__main__':
    main()
