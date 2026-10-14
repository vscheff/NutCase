import copy
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QObject, Signal, QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from fastener_gui.window import MainWindow
from fastener_gui.controller import BackendController, invocation
from test_state import CATALOG, ANALYSIS, SOURCE, RELEASE, TEST_TEMP

APP=QApplication.instance() or QApplication([])


class FakeBackend(QObject):
    stage=Signal(str);log=Signal(str);completed=Signal(int,object);busyChanged=Signal(bool)
    def __init__(self):
        super().__init__();self.busy=False;self.last_error='Injected Export Failure';self.request=None
    def start(self,request):
        self.request=request;self.busy=True;self.busyChanged.emit(True);self.stage.emit('Working')
    def cancel(self):self.finish(3,None)
    def finish(self,code,result):self.busy=False;self.busyChanged.emit(False);self.completed.emit(code,result)


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        discovery=patch('fastener_gui.window.find_freecad',return_value=('mock-native-python.exe',{},None))
        discovery.start();self.addCleanup(discovery.stop)
        renderer=patch('fastener_gui.window.find_poppler',return_value='mock-pdftoppm.exe')
        renderer.start();self.addCleanup(renderer.stop)
        self.temp=tempfile.TemporaryDirectory(dir=TEST_TEMP);self.addCleanup(self.temp.cleanup)
        self.backend=FakeBackend()
        self.window=MainWindow(output=self.temp.name,settings_directory=Path(self.temp.name)/'settings',controller=self.backend)
        self.window.set_source(SOURCE)
        self.window.model.accept_analysis(SOURCE,copy.deepcopy(CATALOG),copy.deepcopy(ANALYSIS))
        self.window._apply_config();self.window._busy_changed(False);self.window.show()
        self.addCleanup(self.window.close)

    def test_configuration_controls_serialize_existing_schema(self):
        self.window.mode.setCurrentText('Basic');self.window.scale.setCurrentText('2.5')
        self.window.views['isometric'].setChecked(False)
        self.window.metadata['drawing_number'].setText('DESKTOP-TEST')
        config=self.window._read_controls()
        self.assertEqual(config['scale'],2.5);self.assertFalse(config['views']['isometric'])
        self.assertEqual(config['dimensioning']['mode'],'basic')
        self.assertEqual(config['source_binding']['geometry_id'],CATALOG['geometry_id'])

    def test_checkbox_selection_uses_stable_source_identity(self):
        self.window.mode.setCurrentText('Custom')
        item=self.window.table.item(0,0);item.setCheckState(Qt.CheckState.Checked)
        self.assertEqual(self.window.model.config['dimensioning']['include'],[item.data(Qt.ItemDataRole.UserRole)])
        item.setCheckState(Qt.CheckState.Unchecked)
        self.assertFalse(self.window.model.config['dimensioning']['include'])
        self.assertTrue(self.window.model.config['dimensioning']['exclude'])

    def test_generate_passes_bound_config_and_prevents_concurrent_edit(self):
        self.window.generate()
        self.assertEqual(self.backend.request['action'],'generate')
        self.assertTrue(Path(self.backend.request['config']).is_file())
        self.assertFalse(self.window.generate_button.isEnabled())
        self.assertFalse(self.window.config_tabs.isEnabled())
        self.backend.finish(1,None)

    def test_failed_generation_clears_preview_and_preserves_old_manifest(self):
        prior=Path(self.temp.name)/(SOURCE.stem+'.current.json');prior.write_bytes(b'previous release')
        self.window.release=RELEASE;self.window.preview.load(RELEASE['pdf'])
        self.window._show_release_review()
        self.window.generate();self.assertIsNone(self.window.preview.path)
        self.backend.finish(1,None)
        self.assertIsNone(self.window.release);self.assertFalse(self.window.pdf_button.isEnabled())
        self.assertEqual(prior.read_bytes(),b'previous release');self.assertIn('Failed',self.window.status.text())
        self.assertNotIn('CAD Dimension Measurement And Associativity:',self.window.review_text.toPlainText())
        self.assertIn('Cancelled Or Failed',self.window.review_text.toPlainText())

    def test_review_exit_is_success_and_exposes_boolean_warnings(self):
        self.window.action='generate';self.backend.finish(2,{'status':'published_preliminary','release':RELEASE})
        self.assertIn('Completed',self.window.status.text());self.assertTrue(self.window.pdf_button.isEnabled())
        self.assertIn('BOPAlgo',self.window.review_text.toPlainText())
        self.assertIn('ENGINEERING APPROVAL NOT ASSIGNED',self.window.review_text.toPlainText())
        self.assertEqual(self.window.preview.path,RELEASE['pdf'])

    def test_invalid_metadata_cannot_start_generation(self):
        self.window.metadata['date'].setText('2026-02-30');self.window.generate()
        self.assertIsNone(self.backend.request);self.assertIn('Requires Review',self.window.status.text())

    def test_source_change_disables_generation_and_clears_old_candidates(self):
        self.window.set_source(Path(self.temp.name)/'other.step')
        self.assertFalse(self.window.generate_button.isEnabled());self.assertEqual(self.window.table.rowCount(),0)

    def test_changed_binding_preserves_configuration_until_explicit_reset(self):
        saved=self.window.model.checked_config();changed=copy.deepcopy(CATALOG);changed['geometry_id']='changed'
        self.window.model.accept_analysis(SOURCE,changed,ANALYSIS,saved)
        self.window._apply_config();self.window._busy_changed(False)
        self.assertFalse(self.window.generate_button.isEnabled());self.assertEqual(self.window.model.config,saved)
        self.window.fresh_configuration();self.assertTrue(self.window.generate_button.isEnabled())

    def test_preview_zoom_fit_and_page_controls(self):
        preview=self.window.preview;self.assertTrue(preview.load(RELEASE['pdf']))
        QTest.qWait(100);self.assertEqual(preview.document.pageCount(),1)
        preview.zoom.setCurrentText('200%');self.assertEqual(preview.view.zoomFactor(),2)
        preview.zoom.setCurrentText('Fit To Window');preview.go_to_page(1)
        self.assertEqual(preview.document.pageCount(),1)

    def test_dimension_picker_fills_tab_and_hides_unsupported_items(self):
        self.window.resize(960,720);self.window.config_tabs.setCurrentIndex(1)
        self.window.table.selectRow(0);QTest.qWait(30)
        self.assertEqual(self.window.table.columnCount(),4)
        self.assertFalse(hasattr(self.window,'candidate_detail'))
        expected=[r for r in CATALOG['candidates'] if r['verification_status']!='unsupported']
        self.assertEqual(self.window.table.rowCount(),len(expected))
        panel=self.window.config_tabs.widget(1)
        self.assertEqual(panel.layout().count(),1)
        self.assertIs(panel.layout().itemAt(0).widget(),self.window.table)
        self.assertGreater(self.window.table.height(),100)
        self.assertTrue(self.window.generate_button.isVisible())


class TransportTests(unittest.TestCase):
    def test_invocation_uses_external_worker_arguments_without_shell(self):
        program,args=invocation('C:/space folder/request.json')
        self.assertEqual(program,sys.executable);self.assertEqual(args[-1],'C:/space folder/request.json')
        self.assertTrue(args[-2].endswith('gui_worker.py'))

    def test_actual_qprocess_keeps_event_loop_responsive_and_handles_review_exit(self):
        with tempfile.TemporaryDirectory(dir=TEST_TEMP) as directory:
            worker=Path(directory)/'fake_worker.py'
            worker.write_text("import json,time\nprint(json.dumps({'type':'stage','message':'Waiting'}),flush=True)\ntime.sleep(.4)\nprint(json.dumps({'type':'result','result':{'status':'published_preliminary'}}),flush=True)\nraise SystemExit(2)\n")
            backend=BackendController();finished=[];beats=[]
            backend.completed.connect(lambda code,result:finished.append((code,result)))
            timer=QTimer();timer.setInterval(15);timer.timeout.connect(lambda:beats.append(1));timer.start()
            with patch('fastener_gui.controller.invocation',return_value=(sys.executable,['-u',str(worker)])):
                backend.start({'output':directory,'action':'generate'})
                with self.assertRaises(RuntimeError):backend.start({'output':directory})
                start=time.monotonic()
                while not finished and time.monotonic()-start<5:QTest.qWait(20)
            timer.stop()
            self.assertTrue(finished);self.assertEqual(finished[0][0],2);self.assertGreater(len(beats),10)
            self.assertFalse(backend.busy)

    def test_cancel_is_a_cooperative_marker_not_a_process_kill(self):
        with tempfile.TemporaryDirectory(dir=TEST_TEMP) as directory:
            backend=BackendController();backend.process=object();backend.cancel_path=Path(directory)/'cancel'
            backend.cancel();self.assertTrue(backend.cancel_path.exists());backend.process=None


if __name__=='__main__':unittest.main()
