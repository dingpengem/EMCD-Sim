"""Frozen pre-generalization references; never imported by production code."""
from pathlib import Path
import sys,types

def load(name):
    module=types.ModuleType('emcd_sim._reviewed_'+name)
    module.__package__='emcd_sim';sys.modules[module.__name__]=module
    path=Path(__file__).parent/'fixtures'/'reviewed_geometry'/(name+'.py.txt')
    exec(compile(path.read_text(encoding='utf-8-sig'),str(path),'exec'),module.__dict__)
    return module

ni017=load('ni_017_geometry');ni117=load('ni_117_geometry')
Ni017Geometry=ni017.Ni017Geometry
Ni117Geometry=ni117.Ni117Geometry
rotated_tensor=ni017.rotated_tensor
energy_audit=ni017.energy_audit
