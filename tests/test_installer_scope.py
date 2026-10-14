"""The installer tool exclusion must not hide unknown runtime content."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('prepare_bundle',ROOT/'packaging/prepare_bundle.py')
prepare=importlib.util.module_from_spec(spec);spec.loader.exec_module(prepare)


class InstallerScopeTests(unittest.TestCase):
    def test_exclusion_keeps_unknown_binaries_and_data_for_the_gate(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as folder:
            base=Path(folder);source=base/'source';source.mkdir()
            for name in ('NutCase.exe','NutCaseVerify.exe','unknown.dll','unknown.dat'):
                (source/name).write_bytes(name.encode())
            target=base/'installer';prepare.installer_payload(target,source)
            self.assertFalse((target/'NutCaseVerify.exe').exists())
            self.assertEqual({p.name for p in target.iterdir()},{'NutCase.exe','unknown.dll','unknown.dat'})
            self.assertEqual((target/'unknown.dll').read_bytes(),b'unknown.dll')

    def test_existing_candidate_is_preserved(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as folder:
            base=Path(folder);source=base/'source';source.mkdir();target=base/'installer';target.mkdir()
            (target/'retained.txt').write_text('historical evidence')
            with self.assertRaises(ValueError):prepare.installer_payload(target,source)
            self.assertEqual((target/'retained.txt').read_text(),'historical evidence')
