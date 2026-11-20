"""GUI index-text parsing and elastic-preview orchestration."""
from dataclasses import asdict
from math import gcd
from functools import reduce
import numpy as np
from ..structure_geometry import elastic_model, orientation, structure_snapshot
from ..elastic_providers import provider_provenance
from ..physical_elastic import excitation_errors_angstrom_inv


def indices(text,direction=False):
    cleaned=text.translate(str.maketrans({'[':' ',']':' ','(':' ',')':' ', ',':' ','−':'-'})).strip()
    fields=cleaned.split()
    if len(fields)==1 and len(fields[0])==3 and fields[0].isdigit():fields=list(fields[0])
    if len(fields)!=3:raise ValueError('Enter three integer indices, e.g. 0 1 7 or [017].')
    result=tuple(int(x) for x in fields)
    if result==(0,0,0) and direction:raise ValueError('A zone direction cannot be [000].')
    if direction:
        divisor=reduce(gcd,(abs(v) for v in result));result=tuple(v//divisor for v in result)
    return result


def preview(structure,settings,*,systematic_row=False):
    model=elastic_model(structure,settings,systematic_row=systematic_row);z=np.array([0.,settings.thickness]);psi=model.amplitudes(z)
    provider=provider_provenance(model.crystal.species,settings.elastic_provider)
    return dict(settings=asdict(settings),beam_hkl=np.array(model.beams.hkl),g=model.reciprocal_vectors_xy,
        s=excitation_errors_angstrom_inv(model),depth_nm=z,amplitudes=psi,intensity=abs(psi[-1])**2,
        frame=orientation(structure.atoms.cell.array,settings.zone,settings.target),source=structure.source,systematic_row=systematic_row,
        source_sha256=structure.sha256,structure_description=structure.description(),structure_snapshot=structure_snapshot(structure),elastic_provider=provider,
        model='Neutral-atom IAM, finite oriented ZOLZ BW; elastic only, no absorption/TDS or physical CBED disks')
