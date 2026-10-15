"""Read-only inventory and limited intensity checks; never imports dipoles or runs WIEN2k."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import zipfile
import numpy as np


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def inventory(root):
    rows=[]
    for p in sorted(Path(root).rglob('*')):
        if not p.is_file():continue
        with p.open('rb') as f:sample=f.read(8192)
        kind='text' if b'\0' not in sample and all(x in (9,10,13) or x>=32 for x in sample) else 'binary'
        row=dict(filename=p.name,path=str(p.resolve()),bytes=p.stat().st_size,sha256=sha256(p),format=kind,directly_readable=True)
        if zipfile.is_zipfile(p):
            with zipfile.ZipFile(p) as z:row.update(format='zip',members=[dict(name=x.filename,bytes=x.file_size) for x in z.infolist()])
        elif p.suffix.lower() in ('.tar','.gz','.bz2','.xz','.tgz') and tarfile.is_tarfile(p):
            with tarfile.open(p) as t:row.update(format='tar',members=[dict(name=x.name,bytes=x.size) for x in t.getmembers()])
        rows.append(row)
    return rows


def symmat_summary(path):
    blocks=[];labels=set();minimum=float('inf');maximum=0.;rows=0
    with Path(path).open(encoding='ascii') as stream:
        header=next(stream).strip()
        if 'LEFT' not in header or 'RIGHT' not in header:raise ValueError('Unrecognized polarization header')
        current=None
        for line in stream:
            if not line.strip():continue
            kp=re.search(r'KP:\s*(\d+) NEMIN NEMAX\s*:\s*(\d+)\s+(\d+)',line)
            if kp:
                current=dict(kpoint=int(kp[1]),minimum_band=int(kp[2]),maximum_band=int(kp[3]),bands=[])
                blocks.append(current);continue
            parts=line.split()
            if current is None or len(parts)!=4:raise ValueError('Expected core label, band, two real intensities')
            label,band,a,b=parts;values=np.array([float(a),float(b)])
            if not np.isfinite(values).all() or np.any(values<0):raise ValueError('Invalid intensity record')
            current['bands'].append(int(band));labels.add(label);rows+=1
            minimum=min(minimum,float(values.min()));maximum=max(maximum,float(values.max()))
    for block in blocks:
        if block['bands']!=list(range(block['minimum_band'],block['maximum_band']+1)):raise ValueError('Band count/order mismatch')
    if [b['kpoint'] for b in blocks]!=list(range(1,len(blocks)+1)):raise ValueError('Kpoint count/order mismatch')
    counts=[len(b['bands']) for b in blocks]
    return dict(header=header,core_labels=sorted(labels),kpoints=len(blocks),band_records=rows,
        bands_per_kpoint_min=min(counts),bands_per_kpoint_max=max(counts),intensity_min=minimum,intensity_max=maximum,
        numeric_columns=2,energy_per_record=False,core_mj_per_record=False,complex_columns=False)


def discrepancy(predicted,actual):
    delta=predicted-actual;norm=float(np.linalg.norm(actual))
    return dict(max_absolute=float(np.max(abs(delta))),l2_absolute=float(np.linalg.norm(delta)),
        l2_relative=float(np.linalg.norm(delta)/norm) if norm>1e-20 else None)


def spectral_checks(root):
    root=Path(root);data={n:np.loadtxt(root/('Ni_fm.'+n)) for n in ('raw1','raw2','broad1','broad2','rawxmcd','xmcd')}
    identities={n:dict(rows=len(a),energy_start=float(a[0,0]),energy_end=float(a[-1,0]),
        difference=discrepancy(a[:,1]-a[:,2],a[:,3]),sum=discrepancy(a[:,1]+a[:,2],a[:,4])) for n,a in data.items()}
    config=(root/'Ni_fm.injoint').read_text().splitlines();core=np.array(list(map(float,config[4].split())))
    step_ry=float(config[1].split()[1]);ec=13.605698
    shift=int(abs(core[1]-core[0])/step_ry)
    recombined={}
    for a,b,total in (('raw1','raw2','rawxmcd'),('broad1','broad2','xmcd')):
        predicted=data[a][:,1:3].copy();predicted[shift:]+=data[b][:-shift,1:3]
        recombined[total]={name:discrepancy(predicted[:,i],data[total][:,i+1]) for i,name in enumerate(('RP','LP'))}
        recombined[total]['XMCD']=discrepancy(predicted[:,0]-predicted[:,1],data[total][:,3])
        recombined[total]['XAS']=discrepancy(predicted.sum(axis=1),data[total][:,4])
    if list(map(float,config[5].split()))!=[.6,1.] or float(config[6])!=.1:
        raise ValueError('Broadening check is restricted to audited .6/1.0 and .1 eV settings')
    broadening={}
    # Independently evaluate the archived finite-grid broadening prescription.
    # No source code is copied; normalized Lorentz-bin and Gaussian kernels.
    for edge,width in (('1',1.0),('2',.6)):
        raw,actual=data['raw'+edge],data['broad'+edge];n=len(raw)
        x=np.arange(-n+1,n)*step_ry*ec;half=step_ry*ec/2;sig=.1/2.35
        lorentz=(np.arctan((x+half)/width)-np.arctan((x-half)/width))/np.pi
        gaussian=step_ry*ec/(np.sqrt(2*np.pi)*sig)*np.exp(-x*x/(2*sig*sig))
        conv=lambda a,k:np.convolve(a,k,mode='full')[n-1:2*n-1]
        prediction=np.column_stack([conv(conv(raw[:,i],lorentz),gaussian) for i in (1,2)])
        broadening[edge]=dict(archive_width_ev=width,gaussian_sigma_ev=sig,
            **discrepancy(prediction,actual[:,1:3]))
    # This is an inferred alignment, not independently supplied EF or band energies.
    offsets=data['xmcd'][:,0]-data['broad1'][:,0]
    implied_ef=(offsets-step_ry*ec)/ec+core[0]
    return dict(identities=identities,recombined=recombined,archive_broadening_reconstruction=broadening,core_input_ry=core.tolist(),
        ry_to_ev_in_archive=ec,step_ry=step_ry,integer_edge_shift_samples=shift,
        true_core_splitting_ev=float(abs(core[1]-core[0])*ec),grid_edge_shift_ev=shift*step_ry*ec,
        energy_offset_range_ev=[float(offsets.min()),float(offsets.max())],
        inferred_ef_range_ry=[float(implied_ef.min()),float(implied_ef.max())],
        limitation='Recombines already integrated edge intensities, not independent symmat-to-JOINT integration; EF inferred from rounded axes only')


def archive_inventory(path):
    path=Path(path);result=dict(path=str(path.resolve()),bytes=path.stat().st_size,sha256=sha256(path))
    with tarfile.open(path) as outer:
        result['members']=[dict(name=m.name,bytes=m.size) for m in outer.getmembers()]
        result['inspected_source_members']=[]
        for archive in ('SRC_optic.tar.gz','SRC_joint.tar.gz','SRC_usersguide_html.tar.gz'):
            blob=outer.extractfile(archive).read()
            with tarfile.open(fileobj=io.BytesIO(blob),mode='r:gz') as inner:
                for m in inner.getmembers():
                    if m.isfile() and Path(m.name).name in ('opmain.f','sph-UPcor.frc','mmatcv.f','outmatABZ.f','readopx.f','joint.f','dich2.f','8Analysis_Properties.html'):
                        result['inspected_source_members'].append(dict(archive=archive,name=m.name,bytes=m.size,
                            sha256=hashlib.sha256(inner.extractfile(m).read()).hexdigest()))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path('data/wien2k_ni'))
    p.add_argument('--archive',type=Path);p.add_argument('--output',type=Path,default=Path('outputs/ni_wien2k_transition_audit'))
    a=p.parse_args()
    if a.output.resolve().is_relative_to(a.root.resolve()):
        p.error('Audit output must be outside the original data directory')
    a.output.mkdir(parents=True,exist_ok=True)
    before=inventory(a.root)
    result=dict(inventory=before,symmat={n:symmat_summary(a.root/('Ni_fm.'+n)) for n in ('symmat1up','symmat2up')},
        spectra=spectral_checks(a.root))
    if a.archive:result['distribution_archive']=archive_inventory(a.archive)
    assert inventory(a.root)==before,'Source inventory changed during read-only audit'
    (a.output/'audit_diagnostics.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(symmat=result['symmat'],spectra=result['spectra']),indent=2))


if __name__=='__main__':main()
