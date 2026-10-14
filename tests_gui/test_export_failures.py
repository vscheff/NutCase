"""New save-copy failure controls; fixture bytes are not engineering files."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastener_gui.outputs import export_copy
from fixture import RELEASE, TEST_TEMP


class ExportFailureTests(unittest.TestCase):
    def test_corrupt_pending_copy_cannot_replace_existing_destination(self):
        with tempfile.TemporaryDirectory(dir=TEST_TEMP) as directory:
            target=Path(directory)/'existing.pdf';target.write_bytes(b'previous export')
            def corrupt(source,destination):Path(destination).write_bytes(b'corrupt copy')
            with patch('fastener_gui.outputs.shutil.copyfile',side_effect=corrupt):
                with self.assertRaisesRegex(ValueError,'checksum'):export_copy(RELEASE,'pdf',target)
            self.assertEqual(target.read_bytes(),b'previous export')
            self.assertFalse(list(Path(directory).glob('*.pending')))

    def test_locked_destination_preserves_existing_bytes(self):
        with tempfile.TemporaryDirectory(dir=TEST_TEMP) as directory:
            target=Path(directory)/'existing.FCStd';target.write_bytes(b'previous project export')
            with patch('fastener_gui.outputs.os.replace',side_effect=PermissionError('viewer holds destination')):
                with self.assertRaises(PermissionError):export_copy(RELEASE,'project',target)
            self.assertEqual(target.read_bytes(),b'previous project export')
            self.assertFalse(list(Path(directory).glob('*.pending')))
