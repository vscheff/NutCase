"""Archived evidence stays exact; restoration refuses traversal and replacement."""
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def module(name,filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/'packaging/licensing'/filename)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


verify=module('archive_verify','verify.py')
restore=module('archive_restore','restore_reference.py')


class LicensingArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(dir=ROOT/'build')
        self.addCleanup(self.temporary.cleanup)
        self.directory=Path(self.temporary.name)
        self.archive=self.directory/'reference.zip'

    def test_reference_review_preserves_exact_bytes_and_unresolved_decisions(self):
        original=b'{"schema_version":1,"obligations":[{"status":"BLOCKED"}]}\n'
        with zipfile.ZipFile(self.archive,'w') as archive:archive.writestr('inventory.json',original)
        self.assertEqual(verify.review_bytes(self.archive),original)
        self.assertEqual(verify.load_review(self.archive),json.loads(original))

    def test_missing_review_is_rejected(self):
        with zipfile.ZipFile(self.archive,'w') as archive:archive.writestr('other.json','{}')
        with self.assertRaisesRegex(ValueError,'exactly one inventory'):
            verify.load_review(self.archive)

    def test_restore_rejects_traversal(self):
        with zipfile.ZipFile(self.archive,'w') as archive:archive.writestr('materials/../escape','unsafe')
        with self.assertRaisesRegex(ValueError,'Unsafe reference path'):
            restore.restore(self.archive,'materials',self.directory/'restored')
        self.assertFalse((self.directory/'escape').exists())

    def test_restore_preserves_bytes_and_refuses_changed_existing_evidence(self):
        with zipfile.ZipFile(self.archive,'w') as archive:archive.writestr('materials/sources/source.zip',b'original')
        destination=self.directory/'restored'
        self.assertEqual(restore.restore(self.archive,'materials',destination),1)
        path=destination/'sources/source.zip'
        self.assertEqual(path.read_bytes(),b'original')
        self.assertEqual(restore.restore(self.archive,'materials',destination),1)
        path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'refusing to overwrite'):
            restore.restore(self.archive,'materials',destination)
        self.assertEqual(path.read_bytes(),b'changed')


if __name__=='__main__':unittest.main()
