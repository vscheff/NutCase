"""Deployment-policy tests protect PDF/native integrations and reject broad hook output."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('qt_policy',ROOT/'packaging/qt_policy.py')
policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)


class QtDeploymentTests(unittest.TestCase):
    def test_catalogs_are_excluded_without_removing_other_data(self):
        for path in ('PySide6/translations/qtbase_de.qm','_internal/PySide6/translations/qt_fr.qm'):
            self.assertFalse(policy.keep_data((path,)))
        self.assertTrue(policy.keep_data(('PySide6/support/signature/typing.py',)))

    def test_required_platform_style_icons_and_pdf_are_preserved(self):
        for path in ('Qt6Pdf.dll','Qt6PdfWidgets.dll','opengl32sw.dll','plugins/platforms/qwindows.dll',
                     'plugins/platforms/qoffscreen.dll','plugins/styles/qmodernwindowsstyle.dll',
                     'plugins/imageformats/qjpeg.dll','plugins/iconengines/qsvgicon.dll'):
            self.assertTrue(policy.keep_binary(('PySide6/'+path,)),path)

    def test_optional_plugin_families_are_excluded(self):
        for path in ('platforms/qdirect2d.dll','platforms/qminimal.dll','generic/qtuiotouchplugin.dll',
                     'imageformats/qpdf.dll','imageformats/qtiff.dll','imageformats/qwebp.dll',
                     'imageformats/qicns.dll','imageformats/qtga.dll','imageformats/qwbmp.dll'):
            self.assertFalse(policy.keep_binary(('PySide6/plugins/'+path,)),path)

    def test_unknown_plugins_cannot_silently_enter_distribution(self):
        self.assertFalse(policy.keep_binary(('PySide6/plugins/newfamily/newcodec.dll',)))
        self.assertTrue(policy.keep_binary(('vendor/poppler/Library/bin/libtiff.dll',)))

    def test_stale_catalog_is_rejected_by_staging(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as directory:
            bundle=Path(directory);catalog=bundle/'_internal/PySide6/translations/qtbase_de.qm'
            catalog.parent.mkdir(parents=True);catalog.write_bytes(b'stale catalog')
            with self.assertRaisesRegex(RuntimeError,'policy violation'):policy.verify_payload(bundle)


if __name__=='__main__':unittest.main()
