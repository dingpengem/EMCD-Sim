"""Opt-in matched-source/frozen Ni reference; not a new scattering model."""
from dataclasses import asdict, replace
from pathlib import Path
import json
import sys
import time

import numpy as np


def run(output):
    from .geometry import Structure, Settings, geometry, align_bragg, excitation
    from .emcd_forward import ForwardSettings, calculate
    from .project_io import save_project
    from .runtime import build_info

    output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    structure=Structure.nickel()
    settings=Settings(thickness=10.,beam_cutoff=3.2,potential_cutoff=3.8)
    _,frame,hkl,g,_=geometry(structure,settings)
    tilt=align_bragg(g[hkl.index(settings.target)],(0.,15.),settings.voltage,lock='Y')
    settings=replace(settings,tilt=tuple(tilt))
    config=ForwardSettings(axis_declared=True,propagation='both',grid=17,depth=33,
        subpixels=32,fft_grid=32,slice_step=.04,angular_maps=False,
        energy_scope='edges',correction=False,worker_mode='manual',parallel_workers=1)
    energy=np.array([config.l3,config.l2])
    report=dict(protocol='ni017_matched_source_frozen_v1',build=build_info(),
        frozen=bool(getattr(sys,'frozen',False)),executable=sys.executable,
        scope='Bounded raw-intensity packaging reference, not numerical convergence certification',
        settings=asdict(settings),frame=frame.tolist(),hkl=hkl,
        s200=float(excitation(g[hkl.index(settings.target)],settings.tilt,settings.voltage)),
        energy_ev=energy.tolist(),cases={},complete=False)
    assert abs(report['s200'])<1e-10
    start=time.perf_counter()
    for channel in ('single','double'):
        cfg=replace(config,channeling_model=channel)
        result=calculate(structure,settings,cfg,energy_ev=energy)
        save_project(result,output/channel)
        rows={}
        for method,value in result['methods'].items():
            s=value['spectra']
            ap,bp,am,bm=[s[k] for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')]
            na,nb=(ap+am)/2,(bp+bm)/2
            ma,mb=(ap-am)/2,(bp-bm)/2
            assert np.allclose(ap-am,2*ma,rtol=1e-12,atol=1e-14), 'Flip-M identity'
            assert np.allclose(ap-bp,(ma-mb)+(na-nb),rtol=1e-12,atol=1e-14), 'Raw A/B decomposition'
            assert np.allclose(s['D_mag'],ma-mb,rtol=1e-12,atol=1e-14), 'Magnetic-odd decomposition'
            rows[method]=dict(metadata=value['metadata'],
                raw={k:s[k].tolist() for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')},
                N_A=na.tolist(),N_B=nb.tolist(),M_A=ma.tolist(),M_B=mb.tolist(),
                flip_M_A=(ap-am).tolist(),magnetic_AB=(ma-mb).tolist(),
                nonmagnetic_AB=(na-nb).tolist(),conventional_AB=(ap-bp).tolist(),
                magnetic_percent=(100*(ma-mb)/(na+nb)).tolist(),
                conventional_percent=(100*(ap-bp)/(ap+bp)).tolist())
        report['cases'][channel]=dict(config=asdict(cfg),methods=rows)
        (output/'scientific_acceptance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    report.update(complete=True,elapsed_seconds=time.perf_counter()-start)
    (output/'scientific_acceptance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return 0
