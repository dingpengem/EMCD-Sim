"""Focused investigation checks; never an application or acceptance entry point."""
from dataclasses import asdict, field, make_dataclass
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import types
from unittest.mock import patch

import numpy as np
from scipy.linalg import expm

from contract_capture import flatten, metrics, plain
from emcd_sim import double_channeling as bw, multisite_double_channeling as mdc
from emcd_sim.cancellation import Cancelled
from emcd_sim.gui.geometry import Settings, Structure, elastic_model
from emcd_sim.gui.forward_pipeline import calculate
from reference_imports import relocate_reference_imports
from test_multisite_forward import configuration
from test_multisite_scientific_validation import cr_case

ROOT = Path.cwd()
EVIDENCE = Path(os.environ.get('SCI_REVIEW_ROOT', ROOT / 'build/scientific-contract-review'))
output_name = sys.argv[1] if len(sys.argv)>1 else 'resolution-v1'
assert Path(output_name).name == output_name
OUT = EVIDENCE / output_name
OUT.mkdir(parents=True,exist_ok=False)
observed = {}
results = {}


def save():
    (OUT / 'checks.json').write_text(json.dumps(results, indent=2, default=plain)+'\n', encoding='utf-8')
    np.savez_compressed(OUT / 'observed_arrays.npz', **observed)


def git_source(rev, path):
    return subprocess.check_output(['git', 'show', rev+':'+path]).decode('utf-8-sig')


def archived_bw(rev):
    name = 'emcd_sim._review_'+rev
    module = types.ModuleType(name)
    module.__package__ = 'emcd_sim'
    sys.modules[name] = module
    exec(compile(git_source(rev, 'src/emcd_sim/double_channeling.py'), name, 'exec'), module.__dict__)
    module.PreparedBlochIncoming = bw.PreparedBlochIncoming
    return module


def check_current():
    # Reuse captured forward/reverse outputs; check assertions that the default
    # failing test could not reach. These are checks of physical consistency, not
    # a claim to have made the original test pass.
    data = np.load(EVIDENCE/'b1-r2-capture/observed_arrays.npz')
    invariants = []
    for owner in ('', '/groups/up', '/groups/down'):
        spectra = {}
        for direction in ('current', 'reverse'):
            prefix = direction+owner+'/spectra/'
            s = {key[len(prefix):]: data[key] for key in data.files if key.startswith(prefix)}
            spectra[direction] = s
            forms = {
                'N_A': (s['I_A_plus']+s['I_A_minus'])/2,
                'N_B': (s['I_B_plus']+s['I_B_minus'])/2,
                'M_A': (s['I_A_plus']-s['I_A_minus'])/2,
                'M_B': (s['I_B_plus']-s['I_B_minus'])/2,
                'D_mag': s['M_A']-s['M_B'],
                'D_nonmag': s['N_A']-s['N_B'],
                'D_raw': s['I_A_plus']-s['I_B_plus'],
                'Sigma_ref': s['N_A']+s['N_B'],
            }
            for key, value in forms.items():
                invariants.append(dict(owner=owner, direction=direction, check=key,
                                       **metrics(s[key], value, 3e-13, 1e-18)))
        f, r = spectra['current'], spectra['reverse']
        for det in ('A', 'B'):
            for name, x, y in (
                ('reversal_I_'+det, f['I_'+det+'_plus'], r['I_'+det+'_minus']),
                ('reversal_N_'+det, f['N_'+det], r['N_'+det]),
                ('reversal_M_'+det, f['M_'+det], -r['M_'+det]),
            ):
                invariants.append(dict(owner=owner, check=name, **metrics(x, y, 3e-13, 1e-18)))
    results['captured_cr_invariants'] = invariants
    results['cr_independent_raw_events_worst_relative'] = json.loads(
        (EVIDENCE/'b1-r2-capture/capture.json').read_text(encoding='utf-8'))['worst']
    save()
    print('CR_CAPTURED_INVARIANTS', len(invariants), 'failures', sum(x['failing_elements'] for x in invariants), flush=True)

    # The historical test mixes bitwise preservation with an old internal hook.
    # Check cancellation behavior without changing its original assertions.
    elastic = elastic_model(Structure.nickel(), Settings(thickness=2, beam_cutoff=.9, potential_cutoff=1.8))
    queries = np.array([[.15, .2], [.15, -.2]])
    cancel_rows = []
    for method in ('analytic', 'numerical'):
        args = dict(method=method, depth_steps=9)
        a = bw.double_channeling_response(elastic, 831.4778, queries, 2, **args)
        b = bw.double_channeling_response(elastic, 831.4778, queries, 2, cancelled=lambda:False, **args)
        event = threading.Event()
        original = bw.depth_response
        calls = []
        def depth(*a, **kw):
            calls.append(True)
            event.set()
            return original(*a, **kw)
        raised = False
        with patch.object(bw, 'depth_response', side_effect=depth):
            try:
                bw.double_channeling_response(elastic, 831.4778, queries, 2, cancelled=event.is_set, **args)
            except Cancelled:
                raised = True
        count = [0]
        def during_work():
            count[0] += 1
            return count[0] == 12
        immediate = during = False
        try:
            bw.double_channeling_response(elastic, 831.4778, queries, 2, cancelled=lambda:True, **args)
        except Cancelled:
            immediate = True
        try:
            bw.double_channeling_response(elastic, 831.4778, queries, 2, cancelled=during_work, **args)
        except Cancelled:
            during = True
        cancel_rows.append(dict(method=method, no_callback_vs_false=metrics(a, b),
            original_depth_hook_calls=len(calls), original_depth_hook_cancelled=raised,
            immediate_cancelled=immediate, during_work_cancelled=during, callback_calls=count[0]))
    results['cancellation_scope'] = cancel_rows
    save()
    print('CANCELLATION_SCOPE', [(x['method'], x['original_depth_hook_calls'], x['during_work_cancelled']) for x in cancel_rows], flush=True)

    # Independent matrix exponential: valid for the finite, Hermitian,
    # absorption-free Bloch model; it is not an independent scattering model.
    wave_rows = []
    hamiltonian_rows = []
    for name, thickness, energy, query in (
        ('a1', 2., 831.4778, (.15, .2)),
        ('a2', 2., 831.271, (-.7, -.7)),
        ('c1', .3, 831.271, (-.7, -.7)),
    ):
        incoming = bw.prepare_incoming_bloch(elastic, thickness, 9)
        prepared = bw.prepare_outgoing_bloch(elastic, energy, prepared_incoming=incoming)
        direct = bw.outgoing_elastic(elastic, query, energy).hamiltonian_nm_inv()
        shifted = prepared.hamiltonian + np.diag(-20*np.pi*prepared.wavelength*(prepared.g@query))
        hamiltonian_rows.append(dict(case=name, direct_vs_cached=metrics(direct, shifted),
            hermitian_direct=float(np.max(abs(direct-direct.conj().T))),
            hermitian_cached=float(np.max(abs(shifted-shifted.conj().T)))))
        for label, h in (('direct_outgoing', direct), ('cached_outgoing', shifted), ('incoming', incoming.hamiltonian)):
            index = elastic.beams.hkl.index((0,0,0))
            states = bw.BlochStates.solve(h, index)
            z = np.linspace(-thickness, 0, 9) if label!='incoming' else np.linspace(0, thickness, 9)
            actual = states.ket(z)
            boundary = np.eye(len(h), dtype=complex)[:,index]
            reference = np.array([expm(1j*h*distance)@boundary for distance in z])
            wave_rows.append(dict(case=name, state=label, expm_difference=metrics(actual, reference),
                norm_residual=float(np.max(abs(np.sum(abs(actual)**2, axis=-1)-1))),
                eigensystem_residual=float(np.linalg.norm(h@states.vectors-states.vectors*states.values)),
                h_norm=float(np.linalg.norm(h))))
            observed[name+'/'+label+'/h'] = h
            observed[name+'/'+label+'/ket'] = actual
            observed[name+'/'+label+'/expm'] = reference
    results['hamiltonian_algebra'] = hamiltonian_rows
    results['independent_matrix_exponential'] = wave_rows
    save()
    print('MATRIX_EXPONENTIAL', 'max wavefield error', max(x['expm_difference']['max_absolute'] for x in wave_rows), flush=True)


# Execute actual older orchestration and BW multisite sources in private
# namespaces. Dependencies with unchanged physical roles are shared and named
# explicitly; this is not a full historical installation reconstruction.
def frozen_cr(rev):
    token = rev.replace('-', '_')
    names = {x:'emcd_sim.gui._resolution_'+token+'_'+x for x in ('channeling','forward','pipeline')}
    def load(filename, role):
        m = types.ModuleType(names[role]);m.__package__='emcd_sim.gui';sys.modules[m.__name__]=m
        text=git_source(rev, 'src/emcd_sim/gui/'+filename)
        for old, owner in (('forward_pipeline','pipeline'),('emcd_forward','forward'),('channeling','channeling')):
            text=text.replace('from .'+old+' import', 'from .'+names[owner].rsplit('.',1)[-1]+' import')
        exec(compile(relocate_reference_imports(text), rev+':'+filename, 'exec'), m.__dict__)
        return m
    ch = load('channeling.py', 'channeling')
    fwd = load('emcd_forward.py', 'forward')
    pipe = load('forward_pipeline.py', 'pipeline')
    old_bw = archived_bw(rev)
    old_mdc = types.ModuleType('emcd_sim._resolution_mdc_'+token)
    old_mdc.__package__='emcd_sim';sys.modules[old_mdc.__name__]=old_mdc
    mdc_source=git_source(rev, 'src/emcd_sim/multisite_double_channeling.py')
    mdc_source=mdc_source.replace('from .gui.generalized_forward import',
                                  'from emcd_sim.mdff_providers import')
    exec(compile(mdc_source, old_mdc.__name__, 'exec'), old_mdc.__dict__)
    old_mdc.double_channeling_group_responses = old_bw.double_channeling_group_responses
    folder=OUT/(rev+'-inputs');folder.mkdir()
    structure, settings, sites, declared = cr_case(folder, True)
    cfg=configuration(propagation='bloch', channeling_model='double', depth=17, slice_step=.02, angular_maps=False)
    values=asdict(cfg)
    allowed=inspect.signature(pipe.MultiSiteForwardSettings).parameters
    omitted={key:value for key,value in values.items() if key not in allowed}
    assert set(omitted)<= {'memory_mode','resource_allocation','energy_sampling','angular_evaluation'}, omitted
    # Energy values are explicit and angular maps are disabled. Carry the
    # newer resource/scheduling fields for shared modern diagnostics only.
    assert not cfg.angular_maps
    kwargs={key:value for key,value in values.items() if key in allowed}
    # Dataclass fields survive the archived pipeline's dataclasses.replace;
    # ad-hoc attributes would be lost in that operation.
    cfg_type=make_dataclass('ReviewLegacySettings',
        [(key,object,field(default=value)) for key,value in omitted.items()],
        bases=(pipe.MultiSiteForwardSettings,),frozen=True)
    legacy_cfg=cfg_type(**kwargs)
    with patch.object(mdc, 'contract_multisite_bloch_double', old_mdc.contract_multisite_bloch_double):
        r=pipe.calculate_multisite(structure, settings, sites, legacy_cfg, energy_ev=np.array([710.,723.]))
    expected=sum(g.multiplicity*r['groups'][g.group_id]['spectra']['M_A'] for g in sites.groups)/2
    flatten(r, rev, observed)
    keys=('I_A_plus','I_B_plus','I_A_minus','I_B_minus','N_A','N_B','M_A','M_B',
          'D_mag','D_nonmag','D_raw','Sigma_ref')
    linear={key:metrics(r['spectra'][key],
        sum(g.multiplicity*r['groups'][g.group_id]['spectra'][key] for g in sites.groups)/2,
        3e-13,1e-18) for key in keys}
    return dict(revision=subprocess.check_output(['git','rev-parse',rev],text=True).strip(),
                omitted_software_fields=omitted, M_A=linear['M_A'], linear_assertions=linear)

if '--history-only' not in sys.argv:
    check_current()

history=[]
for rev in ('db9c2cd', '35a8e81', 'ef54a53'):
    try:
        row=frozen_cr(rev)
    except Exception as error:
        import traceback
        row=dict(revision=rev, adapter_error=repr(error), traceback=traceback.format_exc())
    history.append(row)
    results['earlier_cr_orchestration'] = history
    save()
    print('CR_SOURCE', rev, row.get('adapter_error', row['M_A'] if 'M_A' in row else None), flush=True)
