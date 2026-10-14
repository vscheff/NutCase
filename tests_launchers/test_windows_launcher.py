"""Local integration checks: prepared external GUI Python and installed FreeCAD required."""
import os
from pathlib import Path
import subprocess
import sys
import shutil
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == 'nt' and os.environ.get('NUTCASE_TEST_FREECAD'), 'Requires Windows and --freecad-python')
class WindowsLauncherTests(unittest.TestCase):
    def command_launcher(self, *arguments):
        # CMD requires an outer pair of quotes around a quoted batch-file path.
        command = subprocess.list2cmdline([str(ROOT/'NutCase.cmd'), *arguments])
        return subprocess.list2cmdline([shutil.which('cmd.exe') or 'cmd.exe', '/d', '/s', '/c'])+' "'+command+'"'

    def run_launcher(self, command, successful=True):
        result = subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=60)
        if successful:
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertIn('GUI_RUNTIME_OK', result.stdout)
            self.assertIn('GUI_STARTUP_OK', result.stdout)
            self.assertNotIn('Traceback', result.stderr)
        return result

    def test_windows_powershell_full_gui_startup(self):
        self.run_launcher(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                           '-File', str(ROOT/'scripts'/'launch-gui.ps1'), '-GuiPython',sys.executable,
                           '-FreeCADHome',str(Path(os.environ['NUTCASE_TEST_FREECAD']).parents[1]), '-StartupCheck'])

    def test_double_click_command_full_gui_startup(self):
        self.run_launcher(self.command_launcher('-GuiPython',sys.executable,'-FreeCADHome',
            str(Path(os.environ['NUTCASE_TEST_FREECAD']).parents[1]),'-StartupCheck'))

    def test_command_preserves_failure_status(self):
        result = self.run_launcher(
            self.command_launcher('-GuiPython', str(ROOT/'tmp'/'absent-runtime'/'python.exe'),
                                  '-StartupCheck'), successful=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Create .venv-gui', result.stderr)
        self.assertNotIn('GUI_STARTUP_OK', result.stdout)
