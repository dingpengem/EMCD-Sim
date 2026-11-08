"""Separate reviewed extension; immutable earlier physics/unit snapshots stay intact."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[1]
EXTENSION_SHA256='0599a74e3b48d4182b34bd7f91c9ac7b62bf7e3cb4fb2817e348f288f343fc76'


ATOMIC_EXTENSION_SHA256='5bd0ecb4f65c7ca713179b8b9f652d8cc47e8ceae6f0e4ceaab5d492980ec302'
REFACTOR_SHA256='191974f2788dcfba74ce75cce3d9b4a3088615857b9c3338e27dbda57ea6fd51'
CONSOLIDATION_SHA256='e49f4392817744babe6dcca42ecf983f82f4d885f1356740e9e346775e7720d3'


def canonical(content):return content.decode('utf-8-sig').replace('\r\n','\n').encode('utf-8')


def extension():
    raw=(ROOT/'tests/fixtures/single_element_scope_v1.json').read_bytes()
    assert hashlib.sha256(canonical(raw)).hexdigest()==EXTENSION_SHA256,'Unreviewed single-element source scope'
    d=json.loads(raw)
    assert d['base']=='2f9c130099dce5df4e4609b521c42f53c5385518'
    assert d['physics_convention']=='forward_born_dagger_g_minus_h_v1'
    raw=(ROOT/'tests/fixtures/atomic_ionization_scope_v1.json').read_bytes()
    assert hashlib.sha256(canonical(raw)).hexdigest()==ATOMIC_EXTENSION_SHA256,'Unreviewed atomic-ionization source scope'
    atomic=json.loads(raw)
    assert atomic['schema']==1 and atomic['base']=='237944148151d784b6b2e3597e853dbc32779bd0'
    assert atomic['physics_convention']==d['physics_convention']
    raw=(ROOT/'tests/fixtures/unified_mdff_scope_v1.json').read_bytes()
    assert hashlib.sha256(canonical(raw)).hexdigest()==CONSOLIDATION_SHA256,'Unreviewed MDFF consolidation source scope'
    consolidation=json.loads(raw)
    assert consolidation['schema']==1 and consolidation['base']=='52b36ee41e20aed5a86fb37db56ca372fac936f8'
    assert consolidation['physics_convention']==d['physics_convention']
    # Additive Part 1C scope: historical manifests remain immutable.
    raw=(ROOT/'tests/fixtures/part1c_refactor_scope_v1.json').read_bytes()
    assert hashlib.sha256(canonical(raw)).hexdigest()==REFACTOR_SHA256,'Unreviewed Part 1C source scope'
    refactor=json.loads(raw)
    assert refactor['base']=='133c3da6e69d633b0e1ea61a4de8005820885bbb'
    reviewed=dict(d['canonical_sha256'],**dict(atomic['canonical_sha256'],
        **dict(consolidation['canonical_sha256'],**refactor['canonical_sha256'])))
    for path in refactor['removed_modules']:
        assert not (ROOT/path).exists(),'Retired production module reintroduced: '+path
        reviewed.pop(path,None)
    return reviewed



def legacy_kernel_source(path,content):
    """Remove only the exact opt-in site plumbing; hash the original default kernel.

    Full current-file hashes are checked separately. No formula, phase sign,
    conjugation, quadrature or accumulation expression is normalized here.
    """
    text=canonical(content).decode('utf-8')
    # Stages 3A/3B extracted the same event calculation behind single-group
    # wrappers. Reassemble that reviewed default path for the ORIGINAL pins;
    # current_sources independently pins the complete wrappers/group kernels.
    for name in ('double_channeling','multislice_double_channeling'):
        group='def '+name+'_group_responses('
        if path.endswith('/'+name+'.py') and group in text:
            wrapper=text.index('def '+name+'_response(')
            head=text[:text.index('    check_cancelled(cancelled)',wrapper)]
            body=text[text.index('    check_cancelled(cancelled)',text.index(group)):]
            text=head+body
            begin=text.index('    if not isinstance(positions_by_group,Mapping)')
            end=text.index('    # Mode-pair integral' if name=='double_channeling' else '    dense=96',begin)
            text=text[:begin]+('' if name=='double_channeling' else
                '    b=min(batch_pixels,len(q));sites=len(elastic.crystal.species)\n')+text[end:]
    if path.endswith('/double_channeling.py'):
        text=text.replace('from collections.abc import Mapping\n','')
        text=text.replace('144*len(q_xy)*len(positions_by_group)\n                     +64*ni*no*sum(len(p) for p in positions_by_group.values())',
                          '144*len(q_xy)')
        text=text.replace('        site_phases={key:equivalent_site_phases(elastic.beams.hkl,ob.hkl,positions)\n'
                          '                     for key,positions in positions_by_group.items()}',
            '        delta = np.asarray(elastic.beams.hkl)[:, None, :]-np.asarray(ob.hkl)[None, :, :]\n'
            "        if ionization_sites is None and not all(s == 'Ni' for s in elastic.crystal.species):\n"
            "            raise ValueError('Equivalent-site response currently supports Ni only')\n"
            '        positions = elastic.crystal.fractional_positions if ionization_sites is None else ionization_sites.positions_for(elastic.crystal)\n'
            '        if len(positions) == 0:\n'
            "            raise ValueError('At least one core site required')\n"
            '        phases,site_weights = equivalent_site_phases(elastic.beams.hkl,ob.hkl,positions)')
        text=text.replace('result = {key:np.empty((len(q_xy),3,3),complex) for key in positions_by_group}',
                          'result = np.empty((len(q_xy),3,3), complex)')
        text=text.replace('            for key,(phases,site_weights) in site_phases.items():\n'
                          '                check_cancelled(cancelled)\n'
                          '                result[key][p] = sum', '            result[p] = sum')
        text=text.replace('                    method=method, depth_steps=depth_steps, cancelled=cancelled) for phase,weight',
                          '                method=method, depth_steps=depth_steps, cancelled=cancelled) for phase,weight')
    if path.endswith('/multislice_double_channeling.py'):
        text=text.replace('32*len(q)*9*len(positions_by_group)','32*len(q)*9')
        text=text.replace('        site_phases={key:equivalent_site_phases(elastic.beams.hkl,ob.hkl,positions)\n'
                          '                     for key,positions in positions_by_group.items()}',
            '        phases,site_weights=equivalent_site_phases(elastic.beams.hkl,ob.hkl,elastic.crystal.fractional_positions if ionization_sites is None else ionization_sites.positions_for(elastic.crystal))\n'
            "        if not len(phases):raise ValueError('At least one localized Ni site required')")
        text=text.replace('responses={key:np.zeros((len(q),3,3),complex) for key in positions_by_group}',
                          'response=np.zeros((len(q),3,3),complex)')
        start=text.find('                for key,(phases,site_weights) in site_phases.items():\n')
        if start!=-1:
            end=text.index('                np.absolute(reciprocal,out=magnitude)',start)
            inner=text[start:end].splitlines(keepends=True)[1:]
            text=text[:start]+''.join(line[4:] for line in inner)+text[end:]
        text=text.replace('responses[key][sl]+=event','response[sl]+=event')
        text=text.replace('return responses,diagnostics','return response,diagnostics')
    if path.endswith('/single_channeling_tensor.py'):
        text=text.replace('historical_ni_site_phase_matrix','fcc_site_phase_matrix')
        text=text.replace('from .ionization_sites import single_site_phase_matrix\n','')
        text=text.replace('    return single_site_phase_matrix(hkl, positions)',
            '    phase = np.exp(2j * np.pi * (hkl[:, None, :] - hkl[None, :, :]) @ positions.T)\n    return phase.mean(axis=-1)')
    if path.endswith('/double_channeling.py'):
        text=text.replace('cancelled=None,ionization_sites=None):','cancelled=None):')
        text=text.replace("if ionization_sites is None and not all(s == 'Ni'", "if not all(s == 'Ni'")
        text=text.replace('elastic.crystal.fractional_positions if ionization_sites is None else ionization_sites.positions_for(elastic.crystal)','elastic.crystal.fractional_positions')
    if path.endswith('/multislice_double_channeling.py'):
        text=text.replace('else ProjectedFFT.build(', 'else ProjectedNiFFT.build(')
        text=text.replace('def incident_fields(',
            '# Historical public name; this is one generic implementation, not a Ni adapter.\nProjectedNiFFT=ProjectedFFT\n\n\ndef incident_fields(')
        text=text.replace('cancelled=None,ionization_sites=None):','cancelled=None):')
        text=text.replace('elastic.crystal.fractional_positions if ionization_sites is None else ionization_sites.positions_for(elastic.crystal)','elastic.crystal.fractional_positions')
    return text.encode('utf-8')


def assert_current_extension(overrides=None):
    from mdff_usability_source_scope import current_sources
    expected=current_sources(extension(),overrides,prefix='Unregistered physics change: ')
    for path,digest in expected.items():
        raw=(overrides or {}).get(path)
        if raw is None:raw=(ROOT/path).read_bytes()
        assert hashlib.sha256(canonical(raw)).hexdigest()==digest,'Unregistered physics change: '+path
