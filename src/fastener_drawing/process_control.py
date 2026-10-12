"""Cooperative cancellation and Windows descendant lifetime management.

Only the external worker uses this module. No Qt or FreeCAD imports.
"""
import ctypes
import os
import subprocess
import time
from pathlib import Path


class Cancelled(RuntimeError):
    pass


class WindowsJob:
    """Kill descendants when the owning worker exits, including abnormal exits."""
    def __init__(self):
        self.handle = None
        if os.name != 'nt':
            return
        from ctypes import wintypes as w
        class Limits(ctypes.Structure):
            _fields_ = [('ProcessTime', ctypes.c_int64), ('JobTime', ctypes.c_int64),
                        ('Flags', w.DWORD), ('MinWorkingSet', ctypes.c_size_t),
                        ('MaxWorkingSet', ctypes.c_size_t), ('ActiveProcesses', w.DWORD),
                        ('Affinity', ctypes.c_size_t), ('Priority', w.DWORD), ('Scheduling', w.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_uint64) for n in ('ReadOps','WriteOps','OtherOps','ReadBytes','WriteBytes','OtherBytes')]
        class Extended(ctypes.Structure):
            _fields_ = [('Basic', Limits), ('IO', IO), ('ProcessMemory', ctypes.c_size_t),
                        ('JobMemory', ctypes.c_size_t), ('PeakProcessMemory', ctypes.c_size_t),
                        ('PeakJobMemory', ctypes.c_size_t)]
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        k.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
        k.CreateJobObjectW.restype = w.HANDLE
        k.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
        k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        k.TerminateJobObject.argtypes = [w.HANDLE, w.UINT]
        k.CloseHandle.argtypes = [w.HANDLE]
        k.GetCurrentProcess.restype = w.HANDLE
        k.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        k.OpenProcess.restype = w.HANDLE
        self.kernel = k
        self.handle = k.CreateJobObjectW(None, None)
        info = Extended(); info.Basic.Flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.handle or not k.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            self.close()
            raise ctypes.WinError(ctypes.get_last_error())

    def assign(self, process=None):
        if self.handle:
            handle = self.kernel.GetCurrentProcess() if process is None else int(process._handle)
            if not self.kernel.AssignProcessToJobObject(self.handle, handle):
                raise ctypes.WinError(ctypes.get_last_error())

    def terminate(self):
        if self.handle and not self.kernel.TerminateJobObject(self.handle, 3):
            raise ctypes.WinError(ctypes.get_last_error())

    def assign_pid(self, pid):
        """Attach a Qt child without importing Qt into process management."""
        if self.handle:
            handle = self.kernel.OpenProcess(0x0101, False, pid)  # SET_QUOTA | TERMINATE
            if not handle:
                raise ctypes.WinError(ctypes.get_last_error())
            try:
                if not self.kernel.AssignProcessToJobObject(self.handle, handle):
                    raise ctypes.WinError(ctypes.get_last_error())
            finally:
                self.kernel.CloseHandle(handle)

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


class ProcessControl:
    def __init__(self, cancel_path, progress):
        self.cancel_path = Path(cancel_path)
        self.progress = progress

    def check(self):
        if self.cancel_path.exists():
            raise Cancelled('Cancelled before publication; previous release remains current')

    def stage(self, message):
        self.check()
        self.progress(message)

    def run(self, command, cwd, log, timeout=600):
        self.check()
        job = WindowsJob()
        process = None
        start = time.monotonic()
        try:
            process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace',
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            job.assign(process)
            while True:
                self.check()
                if time.monotonic()-start > timeout:
                    raise TimeoutError('Native processing exceeded '+str(timeout)+' seconds')
                try:
                    output, _ = process.communicate(timeout=0.25)
                    break
                except subprocess.TimeoutExpired:
                    continue
            Path(log).write_text(output, encoding='utf-8')
            if process.returncode not in (0, 2):
                raise RuntimeError(Path(command[1]).name+' failed; '+output[-2000:]+'; log: '+str(log))
            self.check()
            return process.returncode
        finally:
            if process is not None and process.poll() is None:
                if os.name == 'nt': job.terminate()
                else: process.kill()
                output, _ = process.communicate()
                Path(log).write_text(output, encoding='utf-8')
            job.close()
