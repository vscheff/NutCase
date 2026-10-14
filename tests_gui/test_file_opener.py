import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys
import time
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from fastener_gui.file_opener import FileOpener,invocation
from test_state import RELEASE

APP=QApplication.instance() or QApplication([])


class FileOpenerTests(unittest.TestCase):
    def exercise(self,code,timeout=1000):
        opener=FileOpener(timeout_ms=timeout);events=[];beats=[]
        opener.accepted.connect(lambda text:events.append(('accepted',text)))
        opener.failed.connect(lambda text:events.append(('failed',text)))
        timer=QTimer();timer.setInterval(10);timer.timeout.connect(lambda:beats.append(1));timer.start()
        with patch('fastener_gui.file_opener.invocation',return_value=(sys.executable,['-c',code])):
            opener.open(RELEASE['pdf'])
            with self.assertRaisesRegex(ValueError,'Already Pending'):opener.open(RELEASE['pdf'])
            start=time.monotonic()
            while not events and time.monotonic()-start<3:QTest.qWait(20)
        timer.stop();opener.stop_helpers()
        self.assertTrue(events);self.assertGreater(len(beats),4)
        return events[0]

    def test_launch_arguments_preserve_spaces_and_use_external_python(self):
        program,args=invocation('C:/space folder/drawing.pdf')
        self.assertEqual(program,sys.executable);self.assertEqual(args[-1],'C:/space folder/drawing.pdf')

    def test_dispatch_is_responsive_and_does_not_claim_viewer_rendering(self):
        kind,message=self.exercise('import time;time.sleep(.15)')
        self.assertEqual(kind,'accepted');self.assertIn('Rendering Not Verified',message)

    def test_default_viewer_failure_is_reported(self):
        kind,message=self.exercise("import time,sys;time.sleep(.15);print('missing handler');sys.exit(1)")
        self.assertEqual(kind,'failed');self.assertIn('missing handler',message)

    def test_hung_default_viewer_dispatch_is_bounded(self):
        kind,message=self.exercise('import time;time.sleep(20)',timeout=150)
        self.assertEqual(kind,'failed');self.assertIn('Did Not Respond',message)
