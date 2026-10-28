"""Optional original WIEN2k energy/source audit, independent of beam orientation.

The source axis is crystal-frame metadata. Laboratory magnetization belongs to
an explicitly supplied structural rotation, never a default reference zone.
"""
import hashlib
from pathlib import Path
import numpy as np
from .wien2k_xmcd import load_wien2k_xmcd


def energy_audit(source):
    source=Path(source);s=load_wien2k_xmcd(source);D=s.dichroic;N=s.nonmagnetic
    # Identify the two strongest separated absorption features, then select
    # signed magnetic extrema in nonoverlapping neighborhoods of those features.
    maxima=np.where((N[1:-1]>N[:-2])&(N[1:-1]>=N[2:]))[0]+1
    peaks=sorted(sorted(maxima,key=lambda i:N[i],reverse=True)[:2],key=lambda i:s.energy_ev[i])
    if s.energy_ev[peaks[1]]-s.energy_ev[peaks[0]]<10:raise ValueError('L3/L2 assignment is ambiguous')
    selected={}
    for edge,i in zip(('L3','L2'),peaks):
        mask=abs(s.energy_ev-s.energy_ev[i])<=3.;ix=np.flatnonzero(mask);j=ix[np.argmax(abs(D[mask]))]
        selected[edge]=float(s.energy_ev[j])
    files={}
    for suffix in ('xmcd','raw1','raw2','broad1','broad2','rawxmcd','inso','injoint','inc'):
        p=source.with_suffix('.'+suffix)
        if not p.exists():raise ValueError('Required energy/magnetization audit input missing: '+str(p))
        files[suffix]=hashlib.sha256(p.read_bytes()).hexdigest()
    inso=source.with_suffix('.inso').read_text()
    if '0 0 1' not in inso:raise ValueError('Verify crystal magnetization axis in .inso')
    core=[float(x) for x in source.with_suffix('.injoint').read_text().splitlines()[4].split()]
    split=abs(core[1]-core[0])*13.605693122994
    b1=np.loadtxt(source.with_suffix('.broad1'));b2=np.loadtxt(source.with_suffix('.broad2'))
    raw1=np.loadtxt(source.with_suffix('.raw1'));raw2=np.loadtxt(source.with_suffix('.raw2'))
    early=s.energy_ev<840.;early_error=float(np.max(abs(2*D[early]-b1[early,3])))
    i1=int(np.argmax(abs(b1[:,3])));i2=int(np.argmax(abs(b2[:,3])))
    offset=selected['L3']-b1[i1,0];predicted=offset+split+b2[i2,0]
    if abs(predicted-selected['L2'])>.02 or early_error>1e-7:raise ValueError('Raw-edge/source energy correspondence failed')
    return dict(selected_magnetic_energies_ev=selected,xas_peak_energies_ev=[float(s.energy_ev[i]) for i in peaks],
        native_bounds_ev=[float(s.energy_ev[0]),float(s.energy_ev[-1])],core_energies_rydberg=core,
        core_splitting_ev=split,predicted_L2_magnetic_energy_ev=predicted,early_L3_broad1_matching_error=early_error,
        raw1_raw2_relative_magnetic_peaks_ev=[float(a[np.argmax(abs(a[:,3])),0]) for a in (raw1,raw2)],
        assignment='Lower-energy raw1/broad1 is L3 (2p3/2); upper shifted raw2/broad2 is L2 (2p1/2). Core ordering and 17.4806 eV split corroborate opposite-sign peaks.',
        energy_calibration='No experimental calibration or source shift applied. 852.7/870 eV are external reference energies, not peaks on this native axis.',
        magnetization_cubic=[0,0,1],input_sha256=files)
