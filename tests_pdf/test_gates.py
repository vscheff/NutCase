"""New PDF structure/rendering and persistent configuration boundary controls."""
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, NameObject
from fastener_drawing.pdf_compatibility import normalize_pdf, UnsupportedPDF
from fastener_drawing.pdf_verification import verify_pdf
from fastener_drawing.configuration import read_config, normalize_metadata_date
from test_compatibility import fixture
from pdf_fixture import embedded_fixture


class PDFGateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source.pdf';self.target=self.root/'normalized.pdf'
        self.report={'layout':{'width_mm':612*25.4/72,'height_mm':396*25.4/72,'positions':{}},
                     'native_render_checks':{'actual_dimension_labels':['20.00','10.00']}}

    def test_normalization_preserves_prior_target_when_repair_is_ambiguous(self):
        self.target.write_bytes(b'previous valid output sentinel')
        fixture(self.source,b'/CSp CS 1 SCN ')
        with self.assertRaises(UnsupportedPDF):normalize_pdf(self.source,self.target)
        self.assertEqual(self.target.read_bytes(),b'previous valid output sentinel')

    def test_valid_rgb_and_real_closed_path_are_unchanged(self):
        fixture(self.source,b'/CSp CS .2 .3 .4 SCN ')
        report=normalize_pdf(self.source,self.target)
        self.assertEqual(report['pages'][0]['changes'],[])
        self.assertTrue(report['valid_operators_and_positions_preserved'])
        self.assertTrue(report['font_streams_and_glyph_mappings_preserved'])

    def test_encryption_annotations_and_xobjects_are_refused(self):
        for case in ('encrypted','annotation','xobject'):
            with self.subTest(case=case):
                fixture(self.source);writer=PdfWriter(clone_from=self.source)
                if case=='encrypted':writer.encrypt('secret')
                elif case=='annotation':writer.pages[0][NameObject('/Annots')]=ArrayObject([DictionaryObject()])
                else:writer.pages[0]['/Resources'][NameObject('/XObject')]=DictionaryObject({NameObject('/X1'):DictionaryObject()})
                writer.write(self.source)
                with self.assertRaises(UnsupportedPDF):normalize_pdf(self.source,self.target)
                self.assertFalse(self.target.exists())

    def test_structural_gate_rejects_wrong_sheet_missing_label_and_extra_page(self):
        fixture(self.source);normalize_pdf(self.source,self.target)
        wrong=copy.deepcopy(self.report);wrong['layout']['width_mm']+=1
        with self.assertRaisesRegex(ValueError,'sheet size'):verify_pdf(self.target,wrong,self.root/'check','not executed')
        wrong=copy.deepcopy(self.report);wrong['native_render_checks']['actual_dimension_labels']=['absent']
        with self.assertRaisesRegex(ValueError,'Missing verified'):verify_pdf(self.target,wrong,self.root/'check','not executed')
        writer=PdfWriter(clone_from=self.target);writer.add_blank_page(width=612,height=396);writer.write(self.target)
        with self.assertRaisesRegex(ValueError,'one verified'):verify_pdf(self.target,self.report,self.root/'check','not executed')

    def test_two_independent_renderers_verify_normalized_minimal_vector_fixture(self):
        poppler=os.environ.get('NUTCASE_TEST_POPPLER')
        if not poppler or not Path(poppler).is_file():self.skipTest('Set --poppler for real Poppler/PDFium integration')
        embedded_fixture(self.source,malformed=True)
        normalize_pdf(self.source,self.target,['20.00','10.00'])
        checked=verify_pdf(self.target,self.report,self.root/'renderers',poppler)
        self.assertEqual(checked['status'],'passed');self.assertTrue(checked['vector_only'])
        self.assertEqual(checked['poppler_warnings'],0)
        self.assertIn('Not performed',checked['nitro_review'])

    def test_json_dates_duplicate_fields_and_nonfinite_numbers(self):
        path=self.root/'config.json';path.write_text(json.dumps({'metadata':{'date':'10/13/2026'}}),encoding='utf-8')
        self.assertEqual(read_config(path)['metadata']['date'],'2026-10-13')
        for raw in ('{"scale":1,"scale":2}','{"scale":NaN}','{"views":{"section":1}}',
                    '{"dimensioning":{"include":["Edge12"]}}','{"manufacturing_tolerance":0.1}'):
            path.write_text(raw,encoding='utf-8')
            with self.subTest(raw=raw),self.assertRaises(ValueError):read_config(path)
