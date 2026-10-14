"""Launch boundaries shared by the frozen GUI, worker and native pipeline."""
import ctypes
import os
import sys
from contextlib import contextmanager
from pathlib import Path

from fastener_paths import ENTRYPOINTS, FROZEN


def worker_invocation(action, *arguments, python=None):
    if FROZEN and python is None:
        return str(Path(sys.executable).parent / 'NutCaseWorker.exe'), [action, *map(str, arguments)]
    scripts = {'gui-job': 'gui_worker.py', 'open-file': 'open_system_file.py'}
    return str(python or sys.executable), ['-u', str(ENTRYPOINTS / scripts[action]), *map(str, arguments)]


def clean_environment(environment=None):
    result = dict(os.environ if environment is None else environment)
    for key in ('PYTHONHOME', 'PYTHONPATH', 'QT_PLUGIN_PATH', 'QML2_IMPORT_PATH', 'QT_QPA_PLATFORM'):
        result.pop(key, None)
    result['PYTHONIOENCODING'] = 'utf-8'
    result['PYTHONDONTWRITEBYTECODE'] = '1'
    if FROZEN:
        root = Path(sys._MEIPASS).resolve()
        result['PATH'] = os.pathsep.join(value for value in result.get('PATH', '').split(os.pathsep)
                                        if value and not Path(value).resolve().is_relative_to(root))
        # Every helper is a fresh executable, never a recursive Python command.
        result['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    return result


@contextmanager
def external_dll_search():
    """Prevent PyInstaller's Qt DLLs from being inherited by native FreeCAD.

    Call on the launching thread and keep the reset around process creation only.
    Windows' DLL-directory setting is process-wide; do not use concurrently.
    """
    if os.name != 'nt' or not FROZEN:
        yield
        return
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.SetDllDirectoryW.argtypes = [ctypes.c_wchar_p]
    kernel.SetDllDirectoryW.restype = ctypes.c_int
    if not kernel.SetDllDirectoryW(None):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield
    finally:
        if not kernel.SetDllDirectoryW(str(sys._MEIPASS)):
            raise ctypes.WinError(ctypes.get_last_error())
