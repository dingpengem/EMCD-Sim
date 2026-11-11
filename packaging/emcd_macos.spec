# Native macOS companion to emcd_gui.spec; shared launcher and scientific code.
from pathlib import Path
from importlib.metadata import distribution, version
import json
import platform
import sys
from datetime import datetime, timezone
from sysconfig import get_path
from PyInstaller.utils.hooks import collect_dynamic_libs

root = Path(SPECPATH).parent
if sys.platform != 'darwin' or platform.machine() != 'arm64':
    raise SystemExit('Build with native macOS ARM64 Python (no Rosetta).')
sys.path[:0] = [str(root/'src'), str(root/'packaging')]
from emcd_sim.gui.runtime import build_info
from check_windows_metadata import LICENSE_DISTRIBUTIONS
license_distributions=LICENSE_DISTRIBUTIONS+('PySide6_Pdf','PySide6_WebEngine','pyinstaller')
stage = Path(workpath)/'resources'
stage.mkdir(parents=True, exist_ok=True)
info = build_info()
info.update(build_utc=datetime.now(timezone.utc).isoformat(), build_platform=platform.platform(), python=platform.python_version(),
            architecture=platform.machine(), candidate='local macOS development candidate',
            versions={n: version(n) for n in license_distributions})
(stage/'build_info.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
datas = [(str(stage/'build_info.json'), '.'), (str(root/'LICENSE'), '.'),
         (str(root/'data/wien2k_ni/Ni_fm.xmcd'), 'data/wien2k_ni'),
         (str(root/'packaging/assets/examples'), 'examples'),
         (str(root/'tests/fixtures/Fe3O4_inverse_spinel.cif'), 'examples'),
         (str(root/'tests/fixtures/atomic_editor/NiFe2O4.cif'), 'examples'),
         (str(root/'docs/examples/synthetic_fe_atomic_parameters.json'), 'examples'),
         (str(root/'src/emcd_sim/data'), 'emcd_sim/data'),
         (str(distribution('ase').locate_file('ase/spacegroup/spacegroup.dat')), 'ase/spacegroup')]
# Include the interpreter/bootloader and Conda native-runtime notices too.
python_license=Path(get_path('stdlib'))/'LICENSE.txt'
if not python_license.is_file():raise ValueError('Python runtime LICENSE.txt is required')
datas.append((str(python_license),'licenses/python'))
for record_path in (Path(sys.base_prefix)/'conda-meta').glob('*.json'):
    record=json.loads(record_path.read_text())
    if record['name'] not in ('python','openssl','bzip2','libffi','libexpat','libzlib','zlib','sqlite','xz','readline'):continue
    package=Path(record.get('extracted_package_dir') or record.get('link',{}).get('source',''))
    notices=package/'info/licenses'
    if not notices.is_dir():raise ValueError('Missing native runtime notices: '+str(record_path))
    for notice in notices.rglob('*'):
        if notice.is_file():
            datas.append((str(notice),'licenses/native/'+record['name']+'/'+str(notice.parent.relative_to(notices))))
for name in license_distributions:
    dist = distribution(name)
    for entry in dist.files or ():
        if '.dist-info/' in str(entry) and any(s in str(entry).lower() for s in ('license','copying','notice')):
            path = Path(dist.locate_file(entry))
            if path.is_file():
                datas.append((str(path), 'licenses/'+name+'/'+str(entry.parent).split('.dist-info/', 1)[-1]))
# License texts are shared; the Windows component inventory is deliberately excluded.
for path in (root/'packaging/assets/qt-licenses').glob('*.txt'):
    if path.name != 'README.txt':
        datas.append((str(path), 'licenses/qt'))
a = Analysis([str(root/'packaging/launcher_macos.py')], pathex=[str(root/'src'), str(root/'packaging')],
    binaries=collect_dynamic_libs('spglib'), datas=datas,
    hiddenimports=['matplotlib.backends.backend_qtagg','matplotlib.backends.backend_svg',
                   'ase.io.cif','ase.io.jsonio','ase.io.extxyz'],
    hooksconfig={'matplotlib': {'backends': ['Agg','QtAgg','svg']}},
    excludes=['tkinter','PyQt5','PyQt6','PySide2','pytest','IPython','torch','tensorflow'],
    noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='EMCD-Sim', console=False,
          target_arch='arm64', codesign_identity=None)
coll = COLLECT(exe, a.binaries, a.datas, name='EMCD-Sim')
app = BUNDLE(coll, name='EMCD-Sim.app', bundle_identifier='org.emcd-sim.desktop',
             info_plist={'CFBundleShortVersionString':'0.9.0',
                         'CFBundleVersion':'0.9.0.1', 'NSHighResolutionCapable':True, 'LSMinimumSystemVersion':'15.0',
                         'NSHumanReadableCopyright':'EMCD-Sim contributors; local research candidate'})
