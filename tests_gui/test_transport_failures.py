"""New actual QProcess protocol and startup-failure controls."""
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from fastener_gui.controller import BackendController
from fixture import TEST_TEMP

APP=QApplication.instance() or QApplication([])


class TransportFailureTests(unittest.TestCase):
    def exercise(self,program,args):
        with tempfile.TemporaryDirectory(dir=TEST_TEMP) as directory:
            backend=BackendController();events=[];stages=[]
            backend.completed.connect(lambda code,result:events.append((code,result)))
            backend.stage.connect(stages.append)
            with patch('fastener_gui.controller.invocation',return_value=(program,args)):
                backend.start({'action':'generate','output':directory})
                deadline=time.monotonic()+10
                while not events and time.monotonic()<deadline:QTest.qWait(20)
            if backend.busy:
                backend.process.kill();backend.process.waitForFinished(1000)
            self.assertEqual(len(events),1);self.assertFalse(backend.busy)
            return events[0],stages,backend.last_error

    def test_missing_program_finishes_once_and_restores_idle_state(self):
        result,stages,error=self.exercise(str(TEST_TEMP/'absent-runtime.exe'),[])
        self.assertEqual(result,(1,None));self.assertTrue(error)

    def test_utf8_character_split_across_pipe_reads_is_preserved(self):
        with tempfile.TemporaryDirectory(dir=TEST_TEMP) as directory:
            worker=Path(directory)/'split Ω & worker.py'
            message=json.dumps({'type':'stage','message':'⌀ Ω & intact'},ensure_ascii=False).encode()+b'\n'
            at=message.index('Ω'.encode())+1
            worker.write_text('import sys,time\n'
                f'sys.stdout.buffer.write({message[:at]!r});sys.stdout.buffer.flush();time.sleep(.1)\n'
                f'sys.stdout.buffer.write({message[at:]!r});sys.stdout.buffer.flush()\n'
                'print(\'{"type":"result","result":{"status":"published_preliminary"}}\',flush=True)\n',encoding='utf-8')
            result,stages,error=self.exercise(sys.executable,[str(worker)])
            self.assertEqual(result,(0,{'status':'published_preliminary'}))
            self.assertEqual(stages,['⌀ Ω & intact']);self.assertEqual(error,'')

    def test_worker_failure_reports_error_without_a_fake_result(self):
        code='import json,sys;print(json.dumps({"type":"error","message":"native export failed"}),flush=True);sys.exit(1)'
        result,stages,error=self.exercise(sys.executable,['-c',code])
        self.assertEqual(result,(1,None));self.assertEqual(error,'native export failed')
