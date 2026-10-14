"""Actual Windows descendants, not mocked process-tree cancellation."""
import ctypes
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from fastener_drawing.process_control import ProcessControl, Cancelled
from fastener_gui.state import ROOT


def alive(pid):
    from ctypes import wintypes as w
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE
    kernel.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
    kernel.CloseHandle.argtypes=[w.HANDLE]
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:return False
    try:
        code=w.DWORD();kernel.GetExitCodeProcess(handle,ctypes.byref(code));return code.value==259
    finally:kernel.CloseHandle(handle)


@unittest.skipUnless(os.name=='nt','Windows job object integration')
class WindowsLifetimeTests(unittest.TestCase):
    def setUp(self):
        parent=ROOT/'tmp'/'gui-process-tests';parent.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=parent);self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)

    def test_cancellation_kills_native_worker_and_its_descendant(self):
        worker=self.directory/'native_stub.py';pid_file=self.directory/'pid.json'
        worker.write_text("import subprocess,sys,time,json,pathlib\n"
            "time.sleep(.1)\nchild=subprocess.Popen([sys.executable,'-c','import time;time.sleep(40)'])\n"
            "pathlib.Path(sys.argv[1]).write_text(str(child.pid))\nprint('native started',flush=True)\ntime.sleep(40)\n")
        cancel=self.directory/'cancel';control=ProcessControl(cancel,lambda x:None)
        def request_when_ready():
            deadline=time.monotonic()+10
            while not pid_file.exists() and time.monotonic()<deadline:time.sleep(.02)
            cancel.write_text('cancel')
        timer=threading.Timer(.01,request_when_ready);timer.start()
        try:
            with self.assertRaises(Cancelled):
                control.run([sys.executable,str(worker),str(pid_file)],ROOT,self.directory/'native.log',timeout=15)
        finally:timer.cancel();timer.join(11)
        self.assertTrue(pid_file.exists());pid=int(pid_file.read_text(encoding="utf-8"))
        for _ in range(30):
            if not alive(pid):break
            time.sleep(.03)
        self.assertFalse(alive(pid),'Native descendant survived cancellation')
        self.assertIn('native started',(self.directory/'native.log').read_text(encoding="utf-8"))

    def test_abnormal_worker_exit_kills_descendant_via_owning_job(self):
        worker=self.directory/'crash_stub.py';pid_file=self.directory/'pid.json'
        worker.write_text("import sys,os,subprocess,time,pathlib\n"
            "sys.path.insert(0,sys.argv[1])\nfrom fastener_drawing.process_control import WindowsJob\n"
            "job=WindowsJob();job.assign()\nchild=subprocess.Popen([sys.executable,'-c','import time;time.sleep(40)'])\n"
            "pathlib.Path(sys.argv[2]).write_text(str(child.pid))\ntime.sleep(.1)\nos._exit(9)\n")
        result=subprocess.run([sys.executable,str(worker),str(ROOT/"src"),str(pid_file)],timeout=10)
        self.assertEqual(result.returncode,9);pid=int(pid_file.read_text(encoding="utf-8"))
        for _ in range(30):
            if not alive(pid):break
            time.sleep(.03)
        self.assertFalse(alive(pid),'Descendant survived owning worker crash')

    def test_abrupt_gui_exit_kills_qprocess_worker_and_native_descendant(self):
        worker=self.directory/'worker.py';gui=self.directory/'gui.py';pids=self.directory/'pids.json'
        worker.write_text("import sys,os,subprocess,time,pathlib,json\n"
            "sys.path.insert(0,sys.argv[1])\nfrom fastener_drawing.process_control import WindowsJob\n"
            "job=WindowsJob();job.assign()\nchild=subprocess.Popen([sys.executable,'-c','import time;time.sleep(40)'])\n"
            "pathlib.Path(sys.argv[2]).write_text(json.dumps([os.getpid(),child.pid]))\ntime.sleep(40)\n")
        gui.write_text("import os,sys,pathlib\nos.environ['QT_QPA_PLATFORM']='offscreen'\n"
            "sys.path.insert(0,sys.argv[1])\nfrom PySide6.QtWidgets import QApplication\n"
            "from PySide6.QtCore import QTimer\nimport fastener_gui.controller as transport\n"
            "app=QApplication([])\ntransport.invocation=lambda _: (sys.executable,[sys.argv[2],sys.argv[1],sys.argv[3]])\n"
            "backend=transport.BackendController();backend.start({'output':sys.argv[4]})\n"
            "timer=QTimer();timer.timeout.connect(lambda:os._exit(9) if pathlib.Path(sys.argv[3]).exists() else None)\n"
            "timer.start(50)\napp.exec()\n")
        result=subprocess.run([sys.executable,str(gui),str(ROOT/"src"),str(worker),str(pids),str(self.directory/'out')],timeout=15)
        self.assertEqual(result.returncode,9)
        import json
        for pid in json.loads(pids.read_text(encoding="utf-8")):
            for _ in range(30):
                if not alive(pid):break
                time.sleep(.03)
            self.assertFalse(alive(pid),'Worker or native descendant survived GUI crash')


if __name__=='__main__':unittest.main()
