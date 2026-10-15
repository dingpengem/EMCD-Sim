"""Stdlib-only parser checks; no electronic-structure or scattering calculation."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('wien2k_audit',Path(__file__).resolve().parents[1]/'scripts/wien2k_transition_audit.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


class ReadOnlyAuditTests(unittest.TestCase):
    def test_two_intensity_columns_are_not_complex_amplitudes(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            p=Path(folder)/'example.symmat'
            p.write_text('T L23 LEFT RIGHT ALL\nKP: 1 NEMIN NEMAX : 1 2\n2p 1 0.01 0.02\n2p 2 0.03 0.04\n',encoding='ascii')
            before=p.read_bytes();r=audit.symmat_summary(p)
            self.assertEqual((r['band_records'],r['kpoints'],r['core_labels']),(2,1,['2p']))
            self.assertEqual(r['numeric_columns'],2)
            self.assertFalse(r['complex_columns']);self.assertFalse(r['core_mj_per_record'])
            inv=audit.inventory(folder)
            self.assertEqual(inv[0]['sha256'],audit.sha256(p));self.assertEqual(inv[0]['format'],'text')
            self.assertEqual(p.read_bytes(),before)

    def test_missing_or_malformed_data_are_not_invented(self):
        for record in ('2ps 2 .1 .2','2ps 1 .1 .2 .3','2ps 1 -.1 .2','2ps 1 nan .2'):
            with self.subTest(record=record),tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
                p=Path(folder)/'bad.symmat'
                p.write_text('T L23 LEFT RIGHT ALL\nKP: 1 NEMIN NEMAX : 1 1\n'+record+'\n',encoding='ascii')
                with self.assertRaises(ValueError):audit.symmat_summary(p)


if __name__=='__main__':unittest.main()
