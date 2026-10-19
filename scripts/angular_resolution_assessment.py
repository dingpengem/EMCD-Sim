"""Small selected-energy sampling assessment; never a thickness scan."""
from dataclasses import replace
from pathlib import Path
import hashlib,json,time
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from emcd_sim.gui.project_io import load_project,restore_structure
from emcd_sim.gui.emcd_forward import calculate,export_result
from emcd_sim.gui.propagation import numerical_info
from emcd_sim.gui.results import draw_maps

ROOT=Path('outputs/angular_resolution_assessment')


def main():
    ROOT.mkdir(exist_ok=True)
    reference=load_project('outputs/v060_release/source_native/single_both_project')
    structure=restore_structure(reference['structure_snapshot']);settings=reference['settings']
    records=[]
    for n in (33,97):
        cfg=replace(reference['config'],grid=n,energy_scope='edges',correction=False)
        folder=ROOT/f'grid_{n}'
        if folder.exists():result=load_project(folder);elapsed=json.loads((ROOT/f'timing_{n}.json').read_text())['seconds']
        else:
            start=time.perf_counter();result=calculate(structure,settings,cfg);elapsed=time.perf_counter()-start
            export_result(result,folder)
            (ROOT/f'timing_{n}.json').write_text(json.dumps(dict(seconds=elapsed)))
        info=numerical_info(structure,settings,cfg)
        record=dict(grid=n,pixels=n*n,seconds=elapsed,estimated_process_peak_mib=info['estimated_process_peak_mib'],methods={})
        for method,r in result['methods'].items():
            assert r['qx'].shape==(n,n)
            np.testing.assert_allclose(r['qy'],-r['qy'][::-1],atol=1e-15)
            record['methods'][method]=dict(valid_L3=int(np.isfinite(r['maps']['L3']['I_plus']).sum()),
                spacing=float(r['qx'][0,1]-r['qx'][0,0]))
            fig=Figure(figsize=(10,7),layout='constrained');FigureCanvasAgg(fig)
            draw_maps(fig,r,'L3',signal_mode='asymmetry')
            for ext in ('png','svg'):fig.savefig(ROOT/f'{method}_{n}.{ext}',dpi=130)
        records.append(record)
    # Numerical estimates only: no new high-resolution double propagation.
    estimates=[]
    for n in (33,97,193):
        for channeling in ('single','double'):
            cfg=replace(reference['config'],grid=n,channeling_model=channeling,energy_scope='edges',correction=False)
            info=numerical_info(structure,settings,cfg,check_memory=False)
            estimates.append(dict(grid=n,channeling=channeling,pixels=n*n,working_mib=info['estimated_working_mib'],
                dense_mib=info['dense_working_estimate_mib']))
    original=json.loads(Path('outputs/ni_emcd_thickness_scientific_audit/production_hashes.json').read_text())
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==sha for p,sha in original.items())
    report=dict(measured=records,estimates=estimates,configuration=dict(reference['metadata']['settings']),
        source_sha256=reference['config'].source_sha256,
        scope='Small Ni [017] Single BW/MS selected L3/L2 energies only; not a production accuracy/convergence benchmark. Double/193 estimates only. Shared angular/detector grid intentionally changes integration sampling; FFT/subpixels unchanged.',
        production_checkpoints_unchanged=True)
    (ROOT/'assessment.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=='__main__':main()
