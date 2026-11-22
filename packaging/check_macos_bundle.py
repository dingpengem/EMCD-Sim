"""Check the actual local app payload for native ARM64 code and required resources."""
from pathlib import Path
import subprocess
import sys


def check(app):
    app=Path(app).resolve()
    executable=app/'Contents/MacOS/EMCD-Sim'
    if not executable.is_file():raise ValueError('Missing app executable')
    checked=0
    # Mach-O thin/fat magic, both byte orders. Inspect extensionless framework code too.
    magic={bytes.fromhex(v) for v in ('feedface','cefaedfe','feedfacf','cffaedfe','cafebabe','bebafeca','cafebabf','bfbafeca')}
    for path in app.rglob('*'):
        if not path.is_file() or path.is_symlink():continue
        if path.suffix.lower() in ('.dll','.exe'):raise ValueError('Windows binary in app: '+str(path))
        with path.open('rb') as stream:header=stream.read(4)
        if header not in magic:continue
        archs=subprocess.check_output(['/usr/bin/lipo','-archs',str(path)],text=True).split()
        if 'arm64' not in archs:raise ValueError('Non-ARM64 binary: '+str(path)+' '+str(archs))
        checked+=1
    required=('libqcocoa.dylib','Ni_fm.xmcd','Ni_FCC_a3.52.cif','Fe3O4_inverse_spinel.cif',
              'spacegroup.dat','build_info.json')
    for name in required:
        if not any(p.is_file() for p in app.rglob(name)):raise ValueError('Missing resource: '+name)
    if not checked:raise ValueError('No Mach-O code found')
    print(f'PASS: {checked} Mach-O files support ARM64; required resources present; no Windows binaries')
    return checked


if __name__=='__main__':check(sys.argv[1])
