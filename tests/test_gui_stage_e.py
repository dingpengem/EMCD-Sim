"""Release-candidate resource boundary checks; scientific round trips are in D."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4
from unittest.mock import patch
from emcd_sim.gui import runtime
from emcd_sim import provenance as scientific_runtime


class RuntimeTests(unittest.TestCase):
    def test_source_reference(self):
        self.assertTrue(scientific_runtime.reference_source().is_file())
        self.assertEqual(scientific_runtime.reference_source().name, 'Ni_fm.xmcd')

    def test_frozen_resources_and_no_git(self):
        folder=Path('outputs')/('runtime_resources_'+uuid4().hex);folder.mkdir(parents=True)
        expected=dict(commit='fixed-build',implementation_sha256={},build_utc='2026-10-16')
        (folder/'build_info.json').write_text(json.dumps(expected))
        with patch.object(runtime.sys,'frozen',True,create=True), patch.object(runtime.sys,'_MEIPASS',str(folder),create=True), patch.object(scientific_runtime.subprocess,'check_output',side_effect=AssertionError('runtime Git')):
            self.assertEqual(scientific_runtime.build_info(),expected)
            self.assertEqual(scientific_runtime.reference_source(),folder/'data/wien2k_ni/Ni_fm.xmcd')

    def test_missing_git(self):
        with patch.object(scientific_runtime.subprocess,'check_output',side_effect=FileNotFoundError):
            info=scientific_runtime.build_info()
            self.assertEqual(info['commit'],'unknown')
            # Keep required coverage through the Phase 3C/3D owner moves;
            # additive future inventory entries do not break this behavior.
            required={'forward_pipeline.py','geometry.py','propagation.py',
                      'channeling.py','result_export.py','structure_geometry.py'}
            inventory=info['implementation_sha256']
            self.assertTrue(required<=inventory.keys())
            self.assertTrue(all(isinstance(value,str) and len(value)==64
                                and set(value)<=set('0123456789abcdef')
                                for value in inventory.values()))

    def test_user_workspace_outside_resources(self):
        with patch.dict(os.environ,{'LOCALAPPDATA':str(Path(tempfile.gettempdir())/'rc-user')}):
            with patch.dict(os.environ,clear=False):
                os.environ.pop('EMCD_GUI_WORKSPACE',None)
                self.assertEqual(runtime.workspace(),Path(tempfile.gettempdir())/'rc-user/EMCD-Sim/workspace')

    def test_workspace_override(self):
        with patch.dict(os.environ,{'EMCD_GUI_WORKSPACE':str(Path(tempfile.gettempdir())/'chosen-workspace')}):
            self.assertEqual(runtime.workspace(),Path(tempfile.gettempdir())/'chosen-workspace')


if __name__=='__main__':unittest.main()
