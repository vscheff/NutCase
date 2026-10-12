"""Keep potentially blocking Windows file associations outside the Qt UI thread."""
import sys
from pathlib import Path
from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal
from fastener_paths import ENTRYPOINTS


def invocation(path):
    return sys.executable,[str(ENTRYPOINTS/'open_system_file.py'),str(path)]


class FileOpener(QObject):
    accepted=Signal(str)
    failed=Signal(str)

    def __init__(self,parent=None,timeout_ms=15000):
        super().__init__(parent);self.processes=set();self.timeout_ms=timeout_ms

    def open(self,path):
        if self.processes:raise ValueError('A System Viewer Request Is Already Pending')
        path=Path(path).resolve()
        if not path.is_file():raise ValueError('Published File Is Missing')
        process=QProcess(self);self.processes.add(process)
        environment=QProcessEnvironment.systemEnvironment()
        for key in ('PYTHONHOME','PYTHONPATH','QT_PLUGIN_PATH','QML2_IMPORT_PATH','QT_QPA_PLATFORM'):environment.remove(key)
        environment.insert('PYTHONIOENCODING','utf-8')
        process.setProcessEnvironment(environment)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        timer=QTimer(process);timer.setSingleShot(True)
        timed_out=[False]

        def timeout():
            timed_out[0]=True;process.kill()

        def finish(code,status):
            if process not in self.processes:return
            timer.stop();self.processes.remove(process)
            error=bytes(process.readAllStandardOutput()).decode('utf-8',errors='replace').strip()
            if timed_out[0]:self.failed.emit('System Viewer Did Not Respond Within 15 Seconds; Embedded Preview Remains Available')
            elif code or status==QProcess.ExitStatus.CrashExit:self.failed.emit('System Viewer Could Not Open The File: '+(error or process.errorString()))
            else:self.accepted.emit('PDF Open Request Accepted By Windows - Viewer Rendering Not Verified')
            process.deleteLater()

        process.finished.connect(finish)
        process.errorOccurred.connect(lambda error:finish(1,QProcess.ExitStatus.CrashExit)
            if error==QProcess.ProcessError.FailedToStart else None)
        timer.timeout.connect(timeout)
        process.start(*invocation(path))
        timer.start(self.timeout_ms)

    def stop_helpers(self):
        # Stop only our short-lived dispatch helpers; opened viewer applications
        # are intentionally independent and must not be closed with this GUI.
        for process in tuple(self.processes):
            process.kill();process.waitForFinished(100)
