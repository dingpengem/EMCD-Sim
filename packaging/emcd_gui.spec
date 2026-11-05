from pathlib import Path
import json, subprocess, hashlib, sys, os, platform
from importlib.metadata import version
from datetime import datetime, timezone

root = Path(SPECPATH).parent
sys.path.insert(0, str(root / 'packaging'))
from check_windows_metadata import LICENSE_DISTRIBUTIONS, require_metadata
checked_distributions = require_metadata()
sys.path.insert(0, str(root / 'src'))
stage = root / os.environ.get('EMCD_GUI_BUILD_ROOT','build/windows-rc') / 'resources'
stage.mkdir(parents=True, exist_ok=True)
# Only the explicitly tracked example, never the modified working copy or companions.
reference = stage / 'Ni_fm.xmcd'
reference.write_bytes(subprocess.check_output(['git', '-C', str(root), 'show', 'HEAD:data/wien2k_ni/Ni_fm.xmcd']))
from emcd_sim.gui.runtime import build_info
info = build_info()
info['label']=os.environ.get('EMCD_GUI_BUILD_LABEL',info['label'])
info.update(build_utc=datetime.now(timezone.utc).isoformat(), reference_sha256=hashlib.sha256(reference.read_bytes()).hexdigest(),
            reference_provenance='Repository tracked five-column Ni example; MIT repository license; no WIEN2k code or companion audit included.')
info['versions']={name:version(name) for name in ('numpy','scipy','matplotlib','ase','PySide6','pyinstaller')}
info['build_environment']=dict(python_version=platform.python_version(),python_executable=sys.executable,
    python_prefix=sys.prefix,platform=platform.platform())
from emcd_sim import __version__
info['application_version']=__version__
info['runtime_source_sha256']={str(p.relative_to(root/'src')).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'src/emcd_sim').rglob('*.py')}
info['gui_source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'src/emcd_sim/gui').glob('*.py')}
from emcd_sim.adaptive_scattering import provenance as elastic_provenance
info['bundled_elastic_provider']=elastic_provenance()
info['new_gui_elastic_default']='adaptive-dirac-pade-2026'
(stage / 'build_info.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
# A venv over Conda needs the base runtime DLL search path explicitly.
base_dlls = Path(sys.base_prefix) / 'Library/bin'
if base_dlls.is_dir():
    os.environ['PATH'] = str(base_dlls) + os.pathsep + os.environ.get('PATH','')
runtime_binaries = [(str(base_dlls/name),'.') for name in
    ('libcrypto-3-x64.dll','libssl-3-x64.dll','libexpat.dll') if (base_dlls/name).is_file()]
licenses=[]
for package in LICENSE_DISTRIBUTIONS:
    dist=checked_distributions[package]
    for entry in dist.files or []:
        if any(token in str(entry).lower() for token in ('license','copying','notice')) and '.dist-info/' in str(entry):
            p=Path(dist.locate_file(entry))
            if p.is_file():licenses.append((str(p),'licenses/'+package+'/'+str(entry.parent).split('.dist-info/',1)[-1]))
a = Analysis([str(root/'packaging/launcher.py')], pathex=[str(root/'src')],
    binaries=runtime_binaries,
    datas=[(str(reference),'data/wien2k_ni'), (str(stage/'build_info.json'),'.'), (str(root/'LICENSE'),'.'),
           (str(root/'docs/examples/synthetic_fe_atomic_parameters.json'),'examples'),
           (str(checked_distributions['ase'].locate_file('ase/spacegroup/spacegroup.dat')),'ase/spacegroup'),
           (str(root/'src/emcd_sim/data/adaptive_dirac_pade_2026'),'emcd_sim/data/adaptive_dirac_pade_2026'),
           (str(root/'src/emcd_sim/data/edge_references_v1'),'emcd_sim/data/edge_references_v1')]+licenses,
    hiddenimports=['matplotlib.backends.backend_qtagg','matplotlib.backends.backend_svg','ase.io.cif','ase.io.jsonio','ase.io.extxyz'],
    hooksconfig={'matplotlib': {'backends': ['Agg', 'QtAgg', 'svg']}},
    excludes=['tkinter','PyQt5','PyQt6','PySide2','pytest','IPython','torch','tensorflow'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='EMCD-Sim', console=False,
          version=str(root/'packaging/windows_version_info.txt'))
coll = COLLECT(exe, a.binaries, a.datas, name='EMCD-Sim')
