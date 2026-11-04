"""Declared element-specific axisymmetric XMCD proxy; not a complete DFT MDFF."""
from pathlib import Path
import hashlib,json
from tempfile import TemporaryDirectory
import numpy as np
from ase.data import atomic_numbers
from .wien2k_xmcd import load_wien2k_xmcd
from .xmcd_effective_mdff import effective_tensor_from_xmcd
from .imported_mdff import CONVENTION,ImportedMDFF


def export_declared_xmcd(source_path,declaration,output):
    """Convert a five-column XAS/XMCD source into the explicit imported-pair schema.

    Source magnetic z is rotated into the declared crystal axis. All material,
    energy, handedness and scale assumptions are inputs; there are no Fe defaults.
    """
    keys={'element','edge','selected_ev','magnetization_crystal','handedness','eta','beta',
        'normalization','convention','source','validity','status','source_sha256','reference_tensor_scale_angstrom2_per_ev','reversal_assumption','magnetic_state'}
    if not isinstance(declaration,dict) or not keys<=declaration.keys():raise ValueError('Element-specific XMCD declarations are incomplete')
    d=declaration
    if d['element'] not in atomic_numbers or d['element']=='X' or d['edge']!='L2,3':raise ValueError('Declare source element and L2,3 edges')
    if d['handedness']!='RP_minus_LP_in_declared_axis' or d['convention']!=CONVENTION or d['normalization']!='source_max_nonmagnetic':
        raise ValueError('Explicit RP/LP handedness, corrected dipole convention and normalization assumptions required')
    if d['magnetic_state']!='uniform_fm' or d['reversal_assumption']!='axisymmetric_XMCD_odd_shared_XAS':
        raise ValueError('Declare uniform FM and the approximate axisymmetric XMCD-odd/shared-XAS reversal model')
    for key in ('source','validity'):
        if not isinstance(d[key],str) or not d[key].strip():raise ValueError('Explicit source provenance and validity assumptions must be nonempty')
    # Read/hash exactly once. The unchanged Ni evaluator reads paths, so give
    # both states the same private snapshot rather than rereading mutable input.
    raw_source=Path(source_path).read_bytes()
    if not d['source_sha256'] or hashlib.sha256(raw_source).hexdigest()!=d['source_sha256']:
        raise ValueError('Declared element-specific XMCD source checksum mismatch')
    from .gui.emcd_forward import axis_rotation
    axis=np.asarray(d['magnetization_crystal'],float)
    if axis.shape!=(3,) or not np.isfinite(axis).all() or not np.isfinite(np.linalg.norm(axis)) or np.linalg.norm(axis)<1e-12:
        raise ValueError('Declare a finite nonzero crystal Cartesian magnetic axis with finite norm')
    frame=axis_rotation(d['magnetization_crystal'])
    scale=d['reference_tensor_scale_angstrom2_per_ev']
    if not np.isfinite(scale) or scale<=0:raise ValueError('Declare a positive relative reference tensor amplitude in angstrom^2/eV; no automatic atomic calibration')
    with TemporaryDirectory(prefix='emcd-declared-xmcd-') as temporary:
        snapshot=Path(temporary)/'source.xmcd';snapshot.write_bytes(raw_source)
        source=load_wien2k_xmcd(snapshot)
        plus,minus=[effective_tensor_from_xmcd(snapshot,source.energy_ev,eta=s*d['eta'],beta=d['beta']) for s in (1,-1)]
    a,b=[scale*np.einsum('ia,eab,jb->eij',frame,t.tensor_angstrom2_per_ev,frame) for t in (plus,minus)]
    enc=lambda x:dict(real=x.real.tolist(),imag=x.imag.tolist())
    doc=dict(schema=1,element=d['element'],edge=d['edge'],energy_ev=source.energy_ev.tolist(),selected_ev=d['selected_ev'],
        units='angstrom^2/eV',normalization='per_atom_relative',basis='crystal_cartesian',frame_to_crystal=np.eye(3).tolist(),
        magnetic_state='uniform_fm',magnetization_crystal=d['magnetization_crystal'],reversal='explicit_pair_shared_even',
        source=d['source']+'; XMCD-effective NOT full DFT MDFF; native source SHA256='+source.source_sha256,
        validity=d['validity']+'; axisymmetric effective response may omit arbitrary-crystal anisotropy; source-maximum relative scale has no absolute dipole-length calibration',
        status=d['status'],convention=CONVENTION,T_plus=enc(a),T_minus=enc(b),T_even=enc((a+b)/2),
        xmcd_declarations=dict(d),xmcd_source_path=str(Path(source_path).resolve()))
    path=Path(output)
    if path.exists():raise ValueError('Preserve existing tensor files; choose a new output path')
    raw=(json.dumps(doc,indent=2)+'\n').encode('utf-8')
    # Exclusive creation preserves existing sources, including a concurrent writer.
    # Validate through the same import boundary; remove only our new invalid file.
    with path.open('xb') as stream:stream.write(raw)
    try:return ImportedMDFF.load(path,hashlib.sha256(raw).hexdigest())
    except BaseException:
        path.unlink();raise
