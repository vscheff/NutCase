"""Independent PDF controls; run separately with pypdf, not FreeCAD Python."""
import io
import json
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject, ContentStream
from fastener_drawing.pdf_compatibility import normalize_pdf, digest, repaired_operations, UnsupportedPDF
from local_samples import require_samples, samples
import os

ROOT = Path(__file__).resolve().parents[1]


def fixture(path, defect=b''):
    """Independent vector rectangle/circle/text, with a defect before late text."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=396)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                             NameObject('/Subtype'): NameObject('/Type1'),
                             NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({
        NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)}),
        NameObject('/ColorSpace'): DictionaryObject({NameObject('/CSp'): NameObject('/DeviceRGB')})})
    stream = DecodedStreamObject()
    stream.set_data(b'q 0 0 0 RG 0.7 w 50 50 100 50 re S '
                    b'200 50 m 230 50 230 80 200 80 c 170 80 170 50 200 50 c h S '
                    b'BT /F1 12 Tf 50 150 Td (LINEAR 20.00) Tj ET ' + defect +
                    b'BT /F1 12 Tf 50 120 Td (DIAMETER 10.00) Tj ET Q')
    page[NameObject('/Contents')] = writer._add_object(stream)
    writer.write(path)


class PDFCompatibilityTests(unittest.TestCase):
    def setUp(self):
        directory = ROOT / 'tmp/pdf-tests'
        directory.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=directory)
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'original.pdf'
        self.target = Path(self.temp.name) / 'corrected.pdf'

    def test_independent_both_defects_keep_valid_paths_and_text(self):
        fixture(self.source, b'f q h f Q /CSp CS SCN ')
        before = digest(self.source)
        result = normalize_pdf(self.source, self.target, ['20.00', '10.00'])
        self.assertEqual([c['action'] for c in result['pages'][0]['changes']],
                         ['remove_close_without_subpath', 'explicit_DeviceRGB_initial_black'])
        self.assertEqual(before, digest(self.source))
        stream = ContentStream(PdfReader(self.target).pages[0].get_contents(), PdfReader(self.target))
        self.assertEqual(sum(op == b'h' for _, op in stream.operations), 1)  # Real circle close retained.
        self.assertTrue(result['valid_operators_and_positions_preserved'])

    def test_repeated_output_is_byte_deterministic_and_idempotent(self):
        fixture(self.source, b'/CSp CS SCN ')
        normalize_pdf(self.source, self.target)
        second = self.target.with_name('second.pdf')
        normalize_pdf(self.source, second)
        self.assertEqual(digest(self.target), digest(second))
        clean = normalize_pdf(self.target, second)
        self.assertEqual(clean['pages'][0]['changes'], [])

    def test_valid_pdf_needs_no_operator_changes(self):
        fixture(self.source)
        self.assertEqual(normalize_pdf(self.source, self.target)['pages'][0]['changes'], [])

    def test_missing_label_fails_before_output_publication(self):
        fixture(self.source)
        with self.assertRaisesRegex(RuntimeError, 'Missing expected'):
            normalize_pdf(self.source, self.target, ['99.99'])
        self.assertFalse(self.target.exists())

    def test_refuses_in_place_source_overwrite(self):
        fixture(self.source)
        with self.assertRaisesRegex(ValueError, 'separate output'):
            normalize_pdf(self.source, self.source)

    def test_unknown_color_defects_are_not_guessed(self):
        fixture(self.source, b'/CSp CS 0 SCN ')
        with self.assertRaisesRegex(UnsupportedPDF, 'Unknown malformed'):
            normalize_pdf(self.source, self.target)
        self.assertFalse(self.target.exists())

    def test_color_without_immediate_reset_is_rejected(self):
        fixture(self.source, b'/CSp CS 0.25 w SCN ')
        with self.assertRaises(UnsupportedPDF):
            normalize_pdf(self.source, self.target)

    def test_graphics_stack_and_clipping_are_not_suppressed(self):
        for defect in (b'Q Q ', b'q ', b'f W h n ', b'f h 0 0 m S '):
            with self.subTest(defect=defect):
                fixture(self.source, defect)
                with self.assertRaises(UnsupportedPDF):
                    normalize_pdf(self.source, self.target)

    @require_samples
    def test_actual_samples_keep_every_label_and_resource(self):
        # Explicit native intermediates of NEW matrix runs, never deleted archives.
        matrix = Path(os.environ['NUTCASE_TEST_RESULTS'])/'workflow-matrix.json'
        if not matrix.exists():self.skipTest('Run real native/GUI workflow matrix before optional sample PDF controls')
        sources = [Path(r['native_pdf']) for r in json.loads(matrix.read_text(encoding="utf-8")) if r['mode']=='comprehensive' and r['local_sample']]
        self.assertEqual(len(sources),2)
        for source in sources:
            with self.subTest(sample=source.name):
                report = json.loads(source.with_suffix('.drawing.json').read_text(encoding='utf-8'))
                labels = report['native_render_checks']['actual_dimension_labels']
                result = normalize_pdf(source, self.target, labels)
                self.assertGreater(len(result['pages'][0]['changes']),0)
                self.assertTrue(result['font_streams_and_glyph_mappings_preserved'])
                self.assertTrue(result['page_properties_preserved'])
                page = PdfReader(self.target).pages[0]
                self.assertEqual([float(page.mediabox.width), float(page.mediabox.height)], [1224, 792])
                self.assertIn('⌀', page.extract_text())

    def test_native_independent_unicode_control_preserves_both_text_paths(self):
        source = Path(os.environ.get('NUTCASE_TEST_NATIVE_CONTROL',str(Path(os.environ['NUTCASE_TEST_RESULTS'])/'native-control.pdf')))
        if not source.exists():self.skipTest('Native font/glyph integration control requires native suite in the same results directory')
        result = normalize_pdf(source, self.target, ['⌀ 9.5','ORDINARY TEXT'])
        self.assertTrue(result['font_streams_and_glyph_mappings_preserved'])
        text = PdfReader(self.target).pages[0].extract_text()
        self.assertGreaterEqual(text.count('⌀'),1)
        self.assertIn('ORDINARY TEXT',' '.join(text.split()))
        clean = normalize_pdf(self.target,self.source)
        self.assertEqual(clean['pages'][0]['changes'], [])


if __name__ == '__main__':
    unittest.main()
