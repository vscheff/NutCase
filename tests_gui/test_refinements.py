"""Coverage for desktop controls, selection and export refinements."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QAbstractItemView
from fastener_gui.window import MainWindow
from fastener_gui.outputs import export_copy, sha256
from fastener_drawing.configuration import normalize_metadata_date, read_config
from fastener_drawing.formatting import format_measurement, dimension_format_spec
from fixture import TEST_TEMP, SOURCE, CATALOG, ANALYSIS, RELEASE
from test_interface import FakeBackend

APP=QApplication.instance() or QApplication([])


class RefinementTests(unittest.TestCase):
    def setUp(self):
        discovery=patch('fastener_gui.window.find_freecad',return_value=('mock-native-python.exe',{},None))
        discovery.start();self.addCleanup(discovery.stop)
        renderer=patch('fastener_gui.window.find_poppler',return_value='mock-pdftoppm.exe')
        renderer.start();self.addCleanup(renderer.stop)
        self.temp=tempfile.TemporaryDirectory(dir=TEST_TEMP);self.addCleanup(self.temp.cleanup)
        self.backend=FakeBackend()
        self.window=MainWindow(output=self.temp.name,settings_directory=Path(self.temp.name)/'settings',controller=self.backend)
        self.addCleanup(self.window.close)
        self.window.set_source(SOURCE)
        self.window.model.accept_analysis(SOURCE,copy.deepcopy(CATALOG),copy.deepcopy(ANALYSIS))
        self.window._apply_config();self.window._busy_changed(False)

    def test_printed_precision_and_trimmed_zero_policy(self):
        for value,units,expected in [(129.81,'deg','129.8'),(90,'deg','90'),(9.567,'mm','9.57'),
                                     (9.5,'mm','9.5'),(6,'mm','6'),(.12367,'in','0.124'),
                                     (1.2,'in','1.2'),(-.00001,'mm','0')]:
            with self.subTest(value=value,units=units):self.assertEqual(format_measurement(value,units),expected)
        self.assertEqual(dimension_format_spec('deg'),'%.1w')
        self.assertEqual(dimension_format_spec('mm',prefix='⌀ '),'⌀ %.2w')
        self.assertEqual(dimension_format_spec('in'),'%.3w')
        for value in (float('nan'),float('inf')):
            with self.assertRaises(ValueError):format_measurement(value,'mm')

    def test_picker_uses_shared_precision_and_values_are_read_only(self):
        rows=self.window.model.catalog['candidates']
        for row in rows:
            if row['verification_status']=='unsupported':continue
            row['value']=129.81;row['units']='deg'
        self.window._populate_candidates()
        for i in range(self.window.table.rowCount()):
            self.assertEqual(self.window.table.item(i,2).text(),'129.8')
        self.assertEqual(self.window.table.editTriggers(),QAbstractItemView.EditTrigger.NoEditTriggers)

    def test_date_accepts_month_day_and_keeps_iso_hint(self):
        for entered,expected in [('10/13/2026','2026-10-13'),('02/03/2026','2026-02-03'),
                                 ('2024-02-29','2024-02-29'),('','')]:
            self.window.metadata['date'].setText(entered)
            c=self.window._read_controls()
            self.assertEqual(c['metadata']['date'],expected or None)
            self.assertEqual(self.window.metadata['date'].text(),expected)
        self.assertEqual(self.window.metadata['date'].placeholderText(),'YYYY-MM-DD')
        for invalid in ('13/10/2026','02/29/2026','2026-02-30',123):
            with self.assertRaises(ValueError):normalize_metadata_date(invalid)

    def test_browse_selects_step_without_starting_backend(self):
        with patch.object(QFileDialog,'getOpenFileName',return_value=(str(SOURCE),'STEP')):
            self.window.browse_source()
        self.assertEqual(self.window.model.source,SOURCE.resolve())
        self.assertIsNone(self.backend.request)

    def test_json_reload_preserves_explicit_exclusion_and_detects_stale_binding(self):
        config=self.window.model.checked_config();key=CATALOG['candidates'][0]['stable_id']
        config['dimensioning'].update(mode='custom',exclude=[key])
        from fastener_gui.state import atomic_json
        path=Path(self.temp.name)/'policy.json';atomic_json(path,config)
        with patch.object(QFileDialog,'getOpenFileName',return_value=(str(path),'JSON')):
            self.window.load_configuration()
        self.assertEqual(self.window.model.config['dimensioning']['exclude'],[key])
        config['source_binding']['geometry_id']='stale';atomic_json(path,config)
        with patch.object(QFileDialog,'getOpenFileName',return_value=(str(path),'JSON')):
            self.window.load_configuration()
        self.assertTrue(self.window.model.binding_problem)
        self.assertFalse(self.window.generate_button.isEnabled())

    def test_missing_export_extensions_and_wrong_extension_rejection(self):
        for key,suffix in [('pdf','.pdf'),('project','.FCStd')]:
            destination=Path(self.temp.name)/('drawing '+key)
            actual=export_copy(RELEASE,key,destination)
            self.assertEqual(actual.suffix,suffix)
            self.assertEqual(sha256(actual),sha256(RELEASE[key]))
            self.assertFalse(destination.exists())
            bad=Path(self.temp.name)/('drawing-'+key+'.txt');bad.write_bytes(b'keep existing')
            with self.assertRaises(ValueError):export_copy(RELEASE,key,bad)
            self.assertEqual(bad.read_bytes(),b'keep existing')

    def test_title_and_mode_tooltips_remain_explanatory(self):
        self.assertIn('NutCase',self.window.windowTitle())
        tooltip=self.window.mode.toolTip()
        for mode in ('Basic','Comprehensive','Custom'):self.assertIn(mode,tooltip)
