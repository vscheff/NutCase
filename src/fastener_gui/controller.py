"""Nonblocking QProcess transport, immutable requests and cooperative cancellation."""
import codecs
import json
import os
import sys
import uuid
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal
from .state import ROOT, atomic_json
from fastener_drawing.process_control import WindowsJob
from fastener_paths import ENTRYPOINTS


def invocation(request_path, python=None):
    return str(python or sys.executable), ['-u', str(ENTRYPOINTS/'gui_worker.py'), str(request_path)]


class BackendController(QObject):
    stage = Signal(str)
    log = Signal(str)
    completed = Signal(int, object)
    busyChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None
        self.request = None
        self.result = None
        self.cancel_path = None
        self.last_error = ''
        self._buffer = ''
        self._job = None

    @property
    def busy(self):
        return self.process is not None

    def start(self, request):
        if self.busy:
            raise RuntimeError('A job is already running in this window')
        directory = Path(request['output'])/'gui-jobs'/uuid.uuid4().hex[:12]
        directory.mkdir(parents=True, exist_ok=False)
        self.cancel_path = directory/'cancel.requested'
        self.request = {**request, 'cancel_path':str(self.cancel_path)}
        file = directory/'request.json'; atomic_json(file, self.request)
        self.result = None; self.last_error = ''; self._buffer = ''
        self._decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        self._job = WindowsJob()
        process = self.process = QProcess(self)
        environment = QProcessEnvironment.systemEnvironment()
        # Never leak the interactive Qt plugin paths into FreeCAD's Qt runtime.
        for name in ('PYTHONPATH', 'PYTHONHOME', 'QT_PLUGIN_PATH', 'QML2_IMPORT_PATH', 'QT_QPA_PLATFORM'):
            environment.remove(name)
        environment.insert('PYTHONIOENCODING', 'utf-8')
        process.setProcessEnvironment(environment)
        process.setWorkingDirectory(str(ROOT))
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(self._read)
        process.finished.connect(self._finished)
        process.errorOccurred.connect(self._process_error)
        process.started.connect(self._started)
        self.busyChanged.emit(True)
        program, args = invocation(file)
        process.start(program, args)

    def _started(self):
        try:
            # The GUI owns this outer handle. OS teardown kills the worker on
            # a GUI crash; the worker's nested job owns its native descendants.
            self._job.assign_pid(self.process.processId())
        except OSError as error:
            self.last_error = 'Could Not Contain The Worker Process: '+str(error)
            self.log.emit(self.last_error)
            self.process.kill()

    def cancel(self):
        if self.busy and self.cancel_path is not None:
            self.cancel_path.write_text('Operator requested cancellation\n', encoding='utf-8')
            self.stage.emit('Cancellation Requested - Waiting For Safe Stop')

    def _read(self):
        self._buffer += self._decoder.decode(bytes(self.process.readAllStandardOutput()))
        while '\n' in self._buffer:
            line, self._buffer = self._buffer.split('\n', 1)
            try:
                message = json.loads(line)
                if message['type'] == 'stage': self.stage.emit(message['message'])
                elif message['type'] == 'result': self.result = message['result']
                elif message['type'] == 'error':
                    self.last_error = message['message']
                    self.log.emit(message.get('traceback', self.last_error))
            except (ValueError, KeyError, TypeError):
                if line.strip(): self.log.emit(line)

    def _process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.last_error = self.process.errorString()
            self.log.emit(self.last_error)
            self._finished(1, QProcess.ExitStatus.CrashExit)

    def _finished(self, code, status):
        if self.process is None: return
        self._read()
        if self._buffer.strip(): self.log.emit(self._buffer)
        process = self.process; self.process = None
        if self._job:
            self._job.close(); self._job = None
        if status == QProcess.ExitStatus.CrashExit:
            code = 1
            self.last_error = self.last_error or 'Backend process stopped unexpectedly; inspect the retained run and lock'
        process.deleteLater()
        self.busyChanged.emit(False)
        self.completed.emit(code, self.result)
