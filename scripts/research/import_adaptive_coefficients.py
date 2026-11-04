"""Reproduce bundled JSON from the pinned Apache-2.0 HDF5 deposit.

HDF5 is an offline dependency only. Default mode verifies bytes; --write
explicitly regenerates JSON without fitting or interpolation.
"""
import argparse
import hashlib
import json
from pathlib import Path

SOURCE_SHA256='4d623613d3fe475211d1b78b7965d9604bb8748f9fcfe74700d0ffe3b345cc78'


def encoded_coefficients(path):
    import h5py
    if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=SOURCE_SHA256:
        raise ValueError('Pinned HDF5 SHA256 mismatch')
    data={}
    with h5py.File(path) as archive:
        for group in archive['adaptive_dirac_pade'].values():
            if group['a'].dtype.name!='float32' or group['b'].dtype.name!='float32':
                raise ValueError('Unexpected coefficient precision')
            data[str(int(group.attrs['Z']))]=dict(symbol=str(group.attrs['symbol']),
                a=group['a'][:].astype(float).tolist(),b=group['b'][:].astype(float).tolist(),
                types=[v.decode() if isinstance(v,bytes) else str(v) for v in group['type'][:]])
    if set(data)!=set(map(str,range(1,119))):raise ValueError('Incomplete element coverage')
    return (json.dumps(data,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('hdf5',type=Path);parser.add_argument('--write',action='store_true')
    args=parser.parse_args()
    target=Path(__file__).resolve().parents[2]/'src/emcd_sim/data/adaptive_dirac_pade_2026/coefficients.json'
    value=encoded_coefficients(args.hdf5)
    if args.write:target.write_bytes(value)
    elif target.read_bytes()!=value:raise ValueError('Bundled bytes differ from the pinned source')
    print('Verified coefficient SHA256:',hashlib.sha256(value).hexdigest())
