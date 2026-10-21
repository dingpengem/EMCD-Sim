"""Focused local four-point study checks; skipped when local data are unavailable."""
import csv
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
import pytest
from numpy.testing import assert_allclose

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/ni_double_channeling_bw'
pytestmark=pytest.mark.skipif(not (OUT/'results.npz').exists(),reason='Local four-point benchmark not generated')


def test_saved_raw_observables_and_optimization_equivalence():
    rows=list(csv.DictReader((OUT/'results.csv').open()))
    assert len(rows)==16
    for r in rows:
        ap,bp,am,bm=[float(r[k]) for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')]
        assert min(ap,bp,am,bm)>0
        assert_allclose(float(r['prb_relative_dichroism_percent']),100*(ap-bp)/(ap+bp),rtol=1e-13)
        assert_allclose(float(r['magnetic_only_percent']),100*((ap-am)-(bp-bm))/(ap+am+bp+bm),rtol=1e-12)
        assert abs(float(r['nonmagnetic_imbalance_percent']))<1e-10
    if not (OUT/'unoptimized_reference.npz').exists():
        return  # Optional locally retained pre-optimization control.
    with np.load(OUT/'unoptimized_reference.npz') as old:
        for t in (10,12):
            assert_allclose(np.load(OUT/f't{t}.npz')['double'],old[f't{t}'],rtol=2e-13,atol=1e-15)


def test_raw_and_complex_response_convergence():
    controls=list(csv.DictReader((OUT/'convergence.csv').open()))
    for c in controls:
        assert float(c['max_raw_relative_change'])<.005
        if c['control']=='detector_grid':assert float(c['max_D_PRB_change_pp'])<.005
    depth=list(csv.DictReader((OUT/'depth_convergence.csv').open()))
    for e in (831.4778,848.698):
        errors=[float(r['relative_complex_response_error']) for r in depth if float(r['energy_ev'])==e]
        assert len(errors)==3
        assert errors[1]<errors[0]/3.9 and errors[2]<errors[1]/3.9
        assert errors[-1]<1e-5
    metadata=json.loads((OUT/'configuration.json').read_text())
    assert not metadata['postedge_normalized']
    assert metadata['config']['eta']==metadata['config']['beta']==1
