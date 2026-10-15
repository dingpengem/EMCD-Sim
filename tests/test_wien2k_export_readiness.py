"""Read-only format tests; no wavefunctions generated or physical calculation run."""
import importlib.util
import io
from pathlib import Path
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('readiness',Path(__file__).resolve().parents[1]/'scripts/wien2k_export_readiness.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


class ReadinessFormatTests(unittest.TestCase):
    def test_fortran_record_trailer_and_truncation(self):
        data=b'format-test';mark=struct.pack('<i',len(data))
        stream=io.BytesIO(mark+data+mark)
        self.assertEqual(audit.record(stream),data);self.assertIsNone(audit.record(stream))
        for malformed in (b'x',mark+data[:-1],mark+data+struct.pack('<i',1),struct.pack('<i',-1)):
            with self.subTest(malformed=malformed),self.assertRaises(ValueError):
                audit.record(io.BytesIO(malformed))

    def test_definition_units_preserve_absolute_scratch_and_relative_case(self):
        text="4, '/scratch/case.mommat2up', 'UNKNOWN', 'FORMATTED', 0\n5, 'case.inop', 'OLD', 'FORMATTED', 0\n"
        with patch.object(Path,'read_text',return_value=text),patch.object(Path,'exists',return_value=True),patch.object(Path,'stat',return_value=SimpleNamespace(st_size=32)):
            targets=audit.definition_targets(Path('/case'))
        self.assertEqual(targets[0]['unit'],4)
        self.assertEqual(Path(targets[0]['path']),Path('/scratch/case.mommat2up'))
        self.assertEqual(Path(targets[1]['path']),Path('/case/case.inop'))


if __name__=='__main__':unittest.main()
