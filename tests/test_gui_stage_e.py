"""Release-candidate resource boundary checks; scientific round trips are in D."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from emcd_sim.gui import runtime


class RuntimeTests(unittest.TestCase):
    def test_source_reference(self):
        self.assertTrue(runtime.reference_source().is_file())
        self.assertEqual(runtime.reference_source().name, 'Ni_fm.xmcd')

    def test_frozen_resources_and_no_git(self):
        with tempfile.TemporaryDirectory() as folder:
            expected=dict(commit='fixed-build',implementation_sha256={},build_utc='2026-10-16')
            (Path(folder)/'build_info.json').write_text(json.dumps(expected))
            with patch.object(runtime.sys,'frozen',True,create=True), patch.object(runtime.sys,'_MEIPASS',folder,create=True), patch.object(runtime.subprocess,'check_output',side_effect=AssertionError('runtime Git')):
                self.assertEqual(runtime.build_info(),expected)
                self.assertEqual(runtime.reference_source(),Path(folder)/'data/wien2k_ni/Ni_fm.xmcd')

    def test_missing_git(self):
        with patch.object(runtime.subprocess,'check_output',side_effect=FileNotFoundError):
            self.assertEqual(runtime.build_info()['commit'],'unknown')
            self.assertEqual(len(runtime.build_info()['implementation_sha256']),3)

    def test_user_workspace_outside_resources(self):
        with patch.dict(os.environ,{'LOCALAPPDATA':str(Path(tempfile.gettempdir())/'rc-user')}):
            with patch.dict(os.environ,clear=False):
                os.environ.pop('EMCD_GUI_WORKSPACE',None)
                self.assertEqual(runtime.workspace(),Path(tempfile.gettempdir())/'rc-user/EMCD-Sim/workspace')

    def test_workspace_override(self):
        with patch.dict(os.environ,{'EMCD_GUI_WORKSPACE':str(Path(tempfile.gettempdir())/'chosen-workspace')}):
            self.assertEqual(runtime.workspace(),Path(tempfile.gettempdir())/'chosen-workspace')


if __name__=='__main__':unittest.main()
