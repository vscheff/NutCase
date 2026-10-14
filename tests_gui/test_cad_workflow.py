"""Real QProcess/CAD/PDF matrix, adapted from the frozen verification harness.

No generated-output baseline or supplied model is required for the synthetic
matrix. Local samples are separate optional evidence, never shipped fixtures.
"""
import json
import os
import shutil
import subprocess
import sys
import time
import unittest
import uuid
from pathlib import Path
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtPdf import QPdfDocument
from fastener_gui.window import MainWindow
from fastener_gui.state import read_json, atomic_json
from fastener_gui.outputs import sha256, load_release, export_copy
from local_samples import samples

ROOT=Path(__file__).resolve().parents[1]
APP=QApplication.instance() or QApplication([])


@unittest.skipUnless(os.environ.get('NUTCASE_TEST_FREECAD') and os.environ.get('NUTCASE_TEST_POPPLER'),
                     'Real integration requires --freecad-python and --poppler')
class CADWorkflowTests(unittest.TestCase):
    def wait_job(self,window,launch):
        loop=QEventLoop();result=[];beats=[]
        def finish(code,value):result.append((code,value));loop.quit()
        window.backend.completed.connect(finish)
        deadline=QTimer();deadline.setSingleShot(True);deadline.timeout.connect(loop.quit)
        heartbeat=QTimer();heartbeat.setInterval(50);heartbeat.timeout.connect(lambda:beats.append(1));heartbeat.start()
        try:
            launch();self.assertTrue(window.backend.busy,window.status.text())
            deadline.start(300000);loop.exec()
            if not result:
                window.backend.cancel()
                raise AssertionError('Real CAD worker timed out; inspect retained diagnostics')
            self.assertGreater(len(beats),1)
            return result[0]
        finally:
            deadline.stop();heartbeat.stop();window.backend.completed.disconnect(finish)

    def test_all_modes_publication_preview_persistence_and_failure_boundaries(self):
        results=Path(os.environ['NUTCASE_TEST_RESULTS'])
        directory=results/('workflow-'+uuid.uuid4().hex[:8]);directory.mkdir()
        fixtures=directory/'fixtures'
        native=os.environ['NUTCASE_TEST_FREECAD'];poppler=os.environ['NUTCASE_TEST_POPPLER']
        subprocess.run([native,str(ROOT/'tests_support/build_quality_fixtures.py'),'--output',str(fixtures)],
                       capture_output=True,text=True,check=True,timeout=60)
        models=[(fixtures/'countersunk_pin.step',False)]
        if os.environ.get('NUTCASE_TEST_SAMPLES')=='1':models += [(p,True) for p in samples()]
        rows=[]
        window=None
        try:
            for index,(original,local) in enumerate(models):
                with self.subTest(source=original.name):
                    expected_hash=sha256(original)
                    source=directory/f'model {index} Ω & nut.step';shutil.copy2(original,source)
                    output=directory/f'drawings-{index}';settings=directory/f'settings-{index}'
                    window=MainWindow(native,poppler,output,settings);window.show();window.set_source(source)
                    code,result=self.wait_job(window,window.analyze)
                    self.assertEqual(code,0,window.backend.last_error);self.assertIsNotNone(window.model.catalog)
                    chosen=None;excluded=None
                    for mode in ('Basic','Comprehensive','Custom'):
                        with self.subTest(mode=mode):
                            window.mode.setCurrentText(mode)
                            if mode=='Custom':
                                prior=window.release
                                created=[r for r in prior['report']['dimensions'].values() if r['status']=='created']
                                self.assertGreaterEqual(len(created),2)
                                chosen,excluded=created[0]['stable_id'],created[1]['stable_id']
                                window.model.set_selected(chosen,True);window.model.set_selected(excluded,False)
                                window.model.config['views'].update(isometric=False,opposite_end=False,section=False,opening_detail=False)
                                window._apply_config()
                            window.metadata['date'].setText('10/13/2026')
                            code,result=self.wait_job(window,window.generate)
                            self.assertIn(code,(0,2),window.backend.last_error);self.assertIsNotNone(window.release,window.status.text())
                            release=window.release;report=release['report']
                            self.assertTrue(report['source_sha256_verified_unchanged'])
                            self.assertTrue(report['reopen_checks']['reopened_successfully'])
                            self.assertEqual(release['pdf_audit']['status'],'passed')
                            self.assertEqual(release['pdf_audit']['poppler_warnings'],0)
                            self.assertTrue(release['pdf_audit']['vector_only'])
                            self.assertTrue(Path(report['publication']['native_pdf_retained']).is_file())
                            self.assertEqual(window.preview.document.status(),QPdfDocument.Status.Ready)
                            self.assertFalse(window.preview.document.render(0,window.preview.view.size()).isNull())
                            placed=[r for r in report['dimensions'].values() if r['status']=='created']
                            for key,proof in report['reopen_checks']['dimension_checks'].items():
                                self.assertTrue(proof['measurement_verified'],key);self.assertTrue(proof['references_verified'],key)
                                self.assertTrue(proof['source_measurement_repeated'],key);self.assertFalse(proof['arbitrary_value_override'],key)
                            if mode=='Custom':
                                self.assertEqual([r['stable_id'] for r in placed],[chosen])
                                self.assertNotIn(excluded,[r['stable_id'] for r in placed])
                                self.assertEqual(set(report['layout']['positions']),{'longitudinal','right_end'})
                            elif local and mode=='Comprehensive':
                                self.assertEqual(len(placed),11 if '09748' in original.name else 23)
                                self.assertEqual(report['layout']['sheet'],'ANSI-B');self.assertEqual(report['layout']['scale'],2)
                            for key,suffix in [('pdf','.pdf'),('project','.FCStd')]:
                                dest=export_copy(release,key,directory/f'copy {index} {mode} {key}')
                                self.assertEqual(dest.suffix,suffix);self.assertEqual(sha256(dest),sha256(release[key]))
                            rows.append({'source':original.name,'local_sample':local,'mode':mode.lower(),'exit_code':code,
                                'dimensions':len(placed),'native_pdf':report['publication']['native_pdf_retained'],
                                'project':release['project'],'pdf':release['pdf'],'source_sha256':expected_hash,
                                'pdf_verified':True,'native_reopened':True})
                    window.save_configuration();policy=window.store.load(source)
                    window.close();window=MainWindow(native,poppler,output,settings);window.show()
                    self.assertEqual(window.model.source,source)
                    code,_=self.wait_job(window,window.analyze)
                    self.assertEqual(code,0);self.assertEqual(window.model.config,policy)
                    # A real regeneration restores Custom selection and suppression.
                    code,_=self.wait_job(window,window.generate)
                    self.assertIn(code,(0,2),window.backend.last_error)
                    placed=[r['stable_id'] for r in window.release['report']['dimensions'].values() if r['status']=='created']
                    self.assertEqual(placed,[chosen]);self.assertNotIn(excluded,placed)
                    manifest=output/(source.stem+'.current.json');previous=manifest.read_bytes()
                    cancelled=[]
                    def cancel_on_native(message):
                        if message=='Generating Associative CAD Dimensions And Exporting Native PDF' and not cancelled:
                            cancelled.append(True);QTimer.singleShot(300,window.backend.cancel)
                    window.backend.stage.connect(cancel_on_native)
                    try:code,_=self.wait_job(window,window.generate)
                    finally:window.backend.stage.disconnect(cancel_on_native)
                    self.assertEqual(code,3);self.assertTrue(cancelled)
                    self.assertIsNone(window.release);self.assertIsNone(window.preview.path)
                    self.assertEqual(manifest.read_bytes(),previous);self.assertFalse((output/'.generation.lock').exists())
                    request=window._request('generate');request['freecad_python']=str(directory/'absent/python.exe')
                    code,_=self.wait_job(window,lambda:window.backend.start(request))
                    self.assertEqual(code,1);self.assertEqual(manifest.read_bytes(),previous)
                    self.assertEqual(sha256(source),expected_hash);self.assertEqual(sha256(original),expected_hash)
                    window.close();window=None
        finally:
            if window is not None and not window.backend.busy:window.close()
            (results/'workflow-matrix.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
