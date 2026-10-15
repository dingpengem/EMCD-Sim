"""Read-only WSL Ni/OPTIC readiness inventory; does not execute any WIEN2k program."""
import argparse
import datetime
import hashlib
import io
import math
import tarfile
import json
from pathlib import Path
import re
import struct


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def inventory(roots):
    records={}
    for root in roots:
        root=Path(root)
        if not root.exists():continue
        for p in sorted(root.rglob('*')):
            if not p.is_file():continue
            st=p.stat()
            records[str(p)]=dict(path=str(p),bytes=st.st_size,
                mtime_utc=datetime.datetime.fromtimestamp(st.st_mtime,datetime.timezone.utc).isoformat(),
                sha256=digest(p),symlink_target=str(p.resolve()) if p.is_symlink() else None)
    return list(records.values())


def definition_targets(case):
    rows=[]
    for line in (case/'upoptic.def').read_text().splitlines():
        m=re.match(r"\s*(\d+)\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'",line)
        if not m:raise ValueError('Unrecognized definition line')
        p=Path(m[2]);p=p if p.is_absolute() else case/p
        rows.append(dict(unit=int(m[1]),path=str(p),status=m[3],form=m[4],exists=p.exists(),
            bytes=p.stat().st_size if p.exists() else None))
    return rows


def record(stream):
    mark=stream.read(4)
    if not mark:return None
    if len(mark)!=4:raise ValueError('Truncated record marker')
    n=struct.unpack('<i',mark)[0]
    if n<0 or n>128*1024*1024:raise ValueError('Unsupported Fortran record size/endian')
    body=stream.read(n);trailer=stream.read(4)
    if len(body)!=n or trailer!=mark:raise ValueError('Truncated/mismatched Fortran record')
    return body


def vector_headers(path):
    """Validate this installed compiler's sequential records; discard amplitudes."""
    blocks=[]
    with Path(path).open('rb') as f:
        record(f);record(f)  # one Ni atom: radial energy and LO-parameter records
        while True:
            header=record(f)
            if header is None:break
            if len(header)!=50:raise ValueError('Expected 50-byte SOC vector header')
            x,y,z,name,n,ne,weight=struct.unpack('<3d10s2id',header)
            if len(record(f))!=12*n:raise ValueError('G-basis record mismatch')
            energies=[]
            for band in range(1,ne+1):
                item=record(f)
                if len(item)!=12:raise ValueError('Band-energy record mismatch')
                index,energy=struct.unpack('<id',item)
                if index!=band:raise ValueError('Nonsequential band index')
                if len(record(f))!=16*n:raise ValueError('Complex spinor coefficient record mismatch')
                energies.append(energy)
            blocks.append(dict(kxy_z=[x,y,z],name=name.decode('ascii').strip(),basis=n,energies=energies))
    return blocks


def energy_headers(path):
    blocks=[]
    with Path(path).open() as f:
        next(f);next(f)
        while True:
            line=f.readline()
            if not line:break
            fields=[line[i:i+19] for i in (0,19,38)]+line[57:].split()
            if len(fields)!=7:raise ValueError('Unexpected SOC energy header')
            ne=int(fields[5]);energies=[]
            for index in range(1,ne+1):
                band,e=f.readline().split()
                if int(band)!=index:raise ValueError('Bad energy band sequence')
                energies.append(float(e))
            blocks.append(dict(kxy_z=list(map(float,fields[:3])),name=fields[3],basis=int(fields[4]),energies=energies))
    return blocks


def weight_blocks(path):
    blocks=[]
    with Path(path).open() as f:
        ef=float(next(f).split()[0]);declared=int(next(f).split()[0])
        for line in f:
            m=re.match(r'K-PNT\s+(\d+):\s+(\d+) BANDS',line)
            if not m:raise ValueError('Unexpected weight block')
            values=[]
            for band in range(1,int(m[2])+1):
                k,b,e,w=next(f).split()
                if int(k)!=int(m[1]) or int(b)!=band:raise ValueError('Bad weight indices')
                values.append((float(e),float(w)))
            blocks.append(values)
    if len(blocks)!=declared:raise ValueError('Weight k count mismatch')
    return ef,blocks


def consistency(case,scratch):
    vu,vd=[vector_headers(scratch/('Ni_fm.'+n)) for n in ('vectorsoup','vectorsodn')]
    eu,ed=[energy_headers(case/('Ni_fm.'+n)) for n in ('energysoup','energysodn')]
    ef,weights=weight_blocks(case/'Ni_fm.weightup');efdn,wd=weight_blocks(case/'Ni_fm.weightdn')
    if not len(vu)==len(vd)==len(eu)==len(ed)==len(weights)==len(wd):raise ValueError('Mismatched k counts')
    max_e=0.;max_k=0.;states=0;ratios=[]
    klist=[l.split() for l in (case/'Ni_fm.klist').read_text().splitlines() if l.strip() and not l.lstrip().startswith('END')]
    if len(klist)!=len(vu):raise ValueError('Klist length mismatch')
    for i,(a,b,c,d,w,wdown,kl) in enumerate(zip(vu,vd,eu,ed,weights,wd,klist)):
        if not len(a['energies'])==len(b['energies'])==len(c['energies'])==len(d['energies'])==len(w)==len(wdown):raise ValueError('Band counts mismatch')
        states+=len(w)
        coords=[float(kl[j])/float(kl[4]) for j in (1,2,3)]
        for block in (a,b,c,d):
            if int(block['name'])!=i+1:raise ValueError('Kpoint label mismatch')
            max_k=max(max_k,max(abs(x-y) for x,y in zip(block['kxy_z'],coords)))
        for band,energy in enumerate(a['energies']):
            max_e=max(max_e,*(abs(energy-block['energies'][band]) for block in (b,c,d)),
                abs(energy-w[band][0]),abs(energy-wdown[band][0]))
            ratios.append(w[band][1]/w[0][1])
    return dict(kpoints=len(vu),bands=states,max_energy_discrepancy_ry=max_e,
        max_k_coordinate_discrepancy=max_k,fermi_energy_ry=ef,fermi_dn_ry=efdn,
        min_weight_to_filled_band_ratio=min(ratios),max_weight_to_filled_band_ratio=max(ratios),
        first_band_weight_sum=sum(w[0][1] for w in weights),
        minimum_band_energy_ry=min(e for v in vu for e in v['energies']),
        maximum_band_energy_ry=max(e for v in vu for e in v['energies']),
        bands_per_k_min=min(len(v['energies']) for v in vu),bands_per_k_max=max(len(v['energies']) for v in vu),
        binary_format='little-endian 4-byte Fortran record markers; complex128 coefficient records')


def compare_archive(installation,archive):
    """Hash comparison only; never extract or redistribute licensed source."""
    rows=[]
    with tarfile.open(archive) as outer:
        with tarfile.open(fileobj=io.BytesIO(outer.extractfile('SRC_optic.tar.gz').read()),mode='r:gz') as inner:
            for member in inner.getmembers():
                if not member.isfile() or Path(member.name).suffix.lower() not in ('.f','.frc','.inc','.h'):continue
                local=installation/member.name
                expected=hashlib.sha256(inner.extractfile(member).read()).hexdigest()
                actual=digest(local) if local.is_file() else None
                rows.append(dict(member=member.name,archive_sha256=expected,installed_sha256=actual,match=expected==actual))
    return dict(path=str(archive),sha256=digest(archive),members=rows,
        identical=sum(r['match'] for r in rows),total=len(rows))


def core_headers(case):
    points=int(re.search(r'NPT=\s*(\d+)',(case/'Ni_fm.struct').read_text())[1])
    result={}
    for spin in ('up','dn'):
        lines=(case/('Ni_fm.corewf'+spin)).read_text().splitlines()
        declared=int(lines[0].split()[0]);states=[]
        for line in lines[1:]:
            match=re.search(r'CORE STATES =\s*(\S+)\s+CORE ENERGY=\s*([-+0-9.]+)',line)
            if match:states.append(dict(label=match[1],energy_ry=float(match[2]),radial_values=0));continue
            values=[float(x.replace('D','E')) for x in re.findall(r'[-+]?\d*\.\d+(?:[EDed][-+]?\d+)?',line)]
            if not states or not all(math.isfinite(x) for x in values):raise ValueError('Malformed core radial data')
            states[-1]['radial_values']+=len(values)
        if len(states)!=declared or any(s['radial_values']!=2*points for s in states):raise ValueError('Core radial mesh/count mismatch')
        result[spin]=states
    return dict(radial_points=points,states=result)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',type=Path,default=Path('/home/peng863/Ni_fm'))
    p.add_argument('--scratch',type=Path,default=Path('/home/peng863/wien_scratch'))
    p.add_argument('--installation',type=Path,default=Path('/home/peng863/WIEN2k'))
    p.add_argument('--archive',type=Path)
    a=p.parse_args();roots=[a.case,a.scratch]
    before=inventory(roots)
    sources=['WIEN2k_VERSION','optic','opticc','SRC_optic/optic','SRC_optic/opticc','SRC_optic/opmain.f',
        'SRC_optic/outmatABZ.f','SRC_optic/sph-UPcor.frc','SRC_optic/mmatcv.f','SRC_optic/Makefile','SRC_optic/compile.msg','x_lapw']
    installed=[]
    for name in sources:
        path=a.installation/name
        if path.exists():installed.append(dict(path=str(path),bytes=path.stat().st_size,sha256=digest(path)))
    data=dict(inventory=before,installed=installed,version=(a.installation/'WIEN2k_VERSION').read_text().strip(),
        definition_targets=definition_targets(a.case),consistency=consistency(a.case,a.scratch),core_wavefunctions=core_headers(a.case))
    if a.archive:data['source_archive_comparison']=compare_archive(a.installation,a.archive)
    after=inventory(roots)
    if before!=after:raise RuntimeError('Input files changed during readiness inspection')
    data['source_inventory_unchanged']=True
    print(json.dumps(data,indent=2,allow_nan=False))


if __name__=='__main__':main()
