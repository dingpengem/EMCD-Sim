"""Five-column XMCD source inspection and optional original-Ni companion audit.

inspect_xmcd_source reports source identity, bounds and feature hints. It does
not construct a target tensor or select a material for the propagation engine.
The original bundled Ni companion audit is an explicitly identified preset.
"""
from pathlib import Path
import numpy as np
from .wien2k_xmcd import load_wien2k_xmcd
from .provenance import reference_source

DEFAULT_NI_SOURCE = reference_source()


def inspect_xmcd_source(path):
    """Basic import is independent of optional original WIEN2k companion audit."""
    s=load_wien2k_xmcd(path); n=s.nonmagnetic
    maxima=np.flatnonzero((n[1:-1]>n[:-2]) & (n[1:-1]>=n[2:]))+1
    peaks=[]
    for i in sorted(maxima,key=lambda i:n[i],reverse=True):
        if all(abs(s.energy_ev[i]-s.energy_ev[j])>8 for j in peaks):peaks.append(i)
        if len(peaks)==2:break
    selected=None
    if len(peaks)==2:
        selected={}
        for edge,i in zip(('L3','L2'),sorted(peaks)):
            ix=np.flatnonzero(abs(s.energy_ev-s.energy_ev[i])<=3)
            selected[edge]=float(s.energy_ev[ix[np.argmax(abs(s.dichroic[ix]))]])
    info=dict(sha256=s.source_sha256,bounds=[float(s.energy_ev[0]),float(s.energy_ev[-1])],
              selected=selected,provenance='Five-column validated. User must declare source magnetic axis, RP/LP convention and edge assignment.',audit=None)
    suffixes=('raw1','raw2','broad1','broad2','rawxmcd','inso','injoint','inc')
    if Path(path).resolve()==DEFAULT_NI_SOURCE.resolve() and all(Path(path).with_suffix('.'+k).exists() for k in suffixes):
        from .wien2k_source_audit import energy_audit
        info['audit']=energy_audit(path);info['selected']=info['audit']['selected_magnetic_energies_ev']
        info['provenance']='Original Ni companion audit passed; cubic [001], native unshifted L3/L2.'
    return info
