"""GUI input preparation only; the accepted atomic generator remains authoritative."""
from importlib.resources import files
from pathlib import Path
import hashlib
import json
import copy
import sys
import numpy as np
from ase.data import atomic_numbers, chemical_symbols, atomic_names
from ..atomic_ionization import AtomicMaterialParameters, ORBITALS

MAX_SAMPLES = 4096  # Explicit GUI allocation limit, not a scientific convergence claim.
EDGE_SUBSET_SHA256 = 'c1148890893361165a8cdfbfd6bdf5b54dfd16a2b669e5620596b775e87fd9bb'
EDGE_PROVENANCE_SHA256 = '4acf973a9e150706ca0028e320e8686d78a1660e7e4af3c56890389894aea925'
EDITOR_TAG = '\nEMCD_EDITOR_REFERENCE_V1='
CAPABILITY = dict(model='independent_electron_cubic_2p3d_v1', elements=tuple(chemical_symbols[21:31]),
    transitions=('electric-dipole 2p->3d',), edges=('L2,3',),
    required_parameters=tuple(AtomicMaterialParameters.__dataclass_fields__),
    magnetic_state='explicit uniform-FM reversal pair; local M=(0,0,1)',
    frame='proper rigid rotation of the whole real cubic orbital/spin frame',
    limitations='Independent electron; cubic eg/t2g only; no multiplets, bands, chemical shifts, noncollinear spin or absolute cross sections.')
MODEL_CAPABILITIES = {'atomic_2p3d': CAPABILITY}


def capability_reason(element, edge='L2,3'):
    if element not in CAPABILITY['elements']:
        return 'Atomic 2p-to-3d model unavailable for this element. Choose another compatible MDFF provider.'
    if edge not in CAPABILITY['edges']:
        return 'This generator supports only the 2p-to-3d L2,3 transition family.'
    return ''


def crystal_elements(atoms):
    """Describe actual ASE sites, including occupancy annotations, without oxidation inference."""
    symbols = atoms.get_chemical_symbols()
    occupancy = atoms.info.get('occupancy', {})
    kinds=atoms.arrays.get('spacegroup_kinds',np.arange(len(atoms)))
    site_occupancies=[occupancy.get(str(int(kind)),occupancy.get(int(kind),{})) for kind in kinds]
    result = []
    # ASE can represent a mixed site by its majority species plus occupancy metadata.
    present = set(symbols)
    for values in site_occupancies:
        if isinstance(values, dict):
            present.update(k for k,v in values.items() if k in atomic_numbers and isinstance(v,(int,float)) and np.isfinite(v) and v>0)
    for symbol in sorted(present, key=atomic_numbers.get):
        indices = tuple(i for i,s in enumerate(symbols) if s==symbol or
            (isinstance(site_occupancies[i],dict) and isinstance(site_occupancies[i].get(symbol),(int,float)) and site_occupancies[i][symbol]>0))
        result.append(dict(symbol=symbol, atomic_number=atomic_numbers[symbol],
            name=atomic_names[atomic_numbers[symbol]], count=len(indices), site_indices=indices,
            occupancy=occupancy, site_occupancy_weights={i:site_occupancies[i].get(symbol,1. if symbols[i]==symbol else 0.) for i in indices},
            supported=not capability_reason(symbol)))
    return result


def edge_references(element):
    """Offline, pinned raw-eV subset; unavailable data never become invented numbers."""
    root = files('emcd_sim').joinpath('data/edge_references_v1')
    raw = root.joinpath('edges_subset.dat').read_bytes()
    if hashlib.sha256(raw).hexdigest() != EDGE_SUBSET_SHA256:
        raise ValueError('Edge-reference subset checksum mismatch; enter explicitly sourced energies manually')
    metadata = root.joinpath('provenance.json').read_bytes().replace(b'\r\n', b'\n')
    if hashlib.sha256(metadata).hexdigest() != EDGE_PROVENANCE_SHA256:
        raise ValueError('Edge-reference provenance checksum mismatch')
    provenance = json.loads(metadata)
    if provenance['subset_sha256'] != EDGE_SUBSET_SHA256 or provenance['units'] != 'eV':
        raise ValueError('Invalid edge-reference provenance/units')
    z = atomic_numbers.get(element)
    rows = {edge: float(value) for number, edge, value in (line.split() for line in raw.decode().splitlines()) if int(number) == z}
    if set(rows) != {'L3', 'L2'}:
        return {}
    return {edge: dict(element=element, atomic_number=z, edge=edge, energy_ev=rows[edge],
        origin='tabulated', **provenance) for edge in ('L3', 'L2')}


def reconcile_edge_origins(element, energies, edge_origins, parameter_origins, document_sha256):
    """Imported annotations are claims; only exact pinned rows confer table origin.

    Preserve energy values and unverified claims as evidence. Both provenance
    views must agree; do not let an independent parameter label bypass checking.
    """
    if not isinstance(edge_origins, dict) or not isinstance(parameter_origins, dict):
        raise ValueError('Malformed editor edge provenance')
    origins, parameters = copy.deepcopy(edge_origins), copy.deepcopy(parameter_origins)
    for key, edge, value in zip(('l3', 'l2'), ('L3', 'L2'), energies):
        claim, info = origins.get(key, {}), parameters.get(key, {})
        if not isinstance(claim, dict) or not isinstance(info, dict):
            raise ValueError('Malformed editor edge provenance')
        # Unknown imported strings must not impersonate a trusted display label.
        if (claim.get('origin') not in (None, 'tabulated', 'manual', 'imported',
                'synthetic_demonstration', 'imported_override_unverified')
            or info.get('origin') not in (None, 'tabulated_reference', 'user_entered',
                'synthetic_demonstration', 'imported_synthetic',
                'imported_physical_source', 'imported_override_unverified')):
            origins[key] = dict(origin='imported_override_unverified', claimed_reference=claim,
                document_sha256=document_sha256)
            parameters[key] = dict(origin='imported_override_unverified',
                citation='Unrecognized imported provenance; document SHA256 '+document_sha256)
            continue
        if claim.get('origin') == 'tabulated' or info.get('origin') == 'tabulated_reference':
            try: trusted = edge_references(element).get(edge)
            except (OSError, ValueError): trusted = None
            if trusted and claim == trusted and value == trusted['energy_ev']:
                parameters[key] = dict(origin='tabulated_reference', citation=trusted['url'], library=trusted['library'])
                continue
            origins[key] = dict(origin='imported_override_unverified', claimed_reference=claim,
                document_sha256=document_sha256)
        if origins.get(key, {}).get('origin') == 'imported_override_unverified':
            parameters[key] = dict(origin='imported_override_unverified',
                citation='Imported override; table provenance unverified; document SHA256 '+document_sha256)
        elif claim.get('origin') == 'manual':
            parameters[key] = dict(origin='user_entered', citation=info.get('citation', 'Imported manual override'))
    return origins, parameters


def explicit_grid(low, high, count):
    if isinstance(count, bool) or not np.isfinite(count) or int(count) != count or not 2 <= int(count) <= MAX_SAMPLES:
        raise ValueError(f'Explicit energy sample count must be an integer in [2,{MAX_SAMPLES}]')
    if not np.isfinite([low, high]).all() or not 0 < low < high:
        raise ValueError('Energy bounds must be positive finite and ascending')
    return np.linspace(low, high, int(count)).tolist()


def validate_document(document):
    if not isinstance(document, dict) or set(document) != {'schema', 'kind', 'parameters', 'energy_ev'}:
        raise ValueError('Expected exactly schema, kind, parameters and energy_ev')
    if type(document['schema']) is not int or document['schema'] != 1 or document['kind'] != 'atomic_2p3d':
        raise ValueError('Expected atomic_2p3d schema 1')
    try:p = AtomicMaterialParameters(**document['parameters'])
    except TypeError as exc:raise ValueError('Incomplete or unsupported atomic parameter fields') from exc
    reason = capability_reason(p.element)
    if reason:
        raise ValueError(reason)
    p.validate()  # No alternate transition algebra or physical parameter validation.
    e = np.asarray(document['energy_ev'])
    if e.dtype.kind not in 'fiu' or e.ndim != 1 or not 2 <= len(e) <= MAX_SAMPLES:
        raise ValueError(f'Energy grid must contain 2..{MAX_SAMPLES} real samples (GUI allocation limit)')
    if not np.isfinite(e).all() or np.any(e <= 0) or np.any(np.diff(e) <= 0):
        raise ValueError('Energy grid must be positive finite and strictly increasing')
    if e[0] > p.edge_energies_ev[0] or e[-1] < p.edge_energies_ev[1]:
        raise ValueError('Explicit energy grid must cover both reference edges; no automatic extension')
    return p


def persist_document(workspace, document):
    """Immutable visible content-addressed source; never write an empty installation path."""
    validate_document(document)
    if workspace is None or not str(workspace).strip():
        raise ValueError('Choose a writable user/project workspace')
    base=Path(workspace).resolve()
    directory = (base / 'atomic_inputs').resolve()
    if directory.parent!=base:raise ValueError('Managed atomic input directory must remain inside the user workspace')
    if getattr(sys, 'frozen', False):
        if any(directory.is_relative_to(p.resolve()) for p in (Path(sys._MEIPASS),Path(sys.executable).parent)):
            raise ValueError('Atomic input workspace must be outside the packaged installation resources')
    directory.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(document, indent=2, allow_nan=False) + '\n').encode('utf-8')
    digest = hashlib.sha256(raw).hexdigest()
    path = directory / (digest + '.json')
    try:
        with path.open('xb') as stream:
            stream.write(raw)
    except FileExistsError:
        if path.is_symlink() or path.read_bytes() != raw:
            raise ValueError('Managed atomic source changed; existing file will not be overwritten')
    return path, digest


def read_document(path):
    if not str(path).strip():
        raise ValueError('Select an atomic parameter JSON file; the path is empty')
    p = Path(path)
    if not p.is_file():
        raise ValueError('Atomic parameter source is missing or not a file')
    if p.stat().st_size > 8 * 1024 * 1024:
        raise ValueError('Atomic parameter document exceeds the 8 MiB GUI input bound')
    raw = p.read_bytes()
    document = json.loads(raw)
    validate_document(document)
    return document, hashlib.sha256(raw).hexdigest()
