import contextlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, call

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT/'src/entrypoints'/'probe_runtime.py'
spec = importlib.util.spec_from_file_location('runtime_probe', PROBE)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class RuntimeProbeTests(unittest.TestCase):
    def test_dependency_order_and_success_markers(self):
        for runtime, marker in [('gui', 'GUI_RUNTIME_OK'), ('pdf', 'PDF_RUNTIME_OK'),
                                ('freecad', 'NATIVE_FREECAD_OK')]:
            with self.subTest(runtime=runtime):
                output = io.StringIO()
                with patch.object(sys, 'argv', ['probe_runtime.py', runtime]), \
                     patch.object(probe.importlib, 'import_module') as importer, \
                     contextlib.redirect_stdout(output):
                    probe.main()
                self.assertEqual(importer.call_args_list,
                                 [call(name) for name in probe.DEPENDENCIES[runtime]])
                self.assertEqual(output.getvalue().strip(), marker)

    def test_failed_import_does_not_print_success(self):
        output = io.StringIO()
        with patch.object(sys, 'argv', ['probe_runtime.py', 'gui']), \
             patch.object(probe.importlib, 'import_module', side_effect=ImportError('missing Qt PDF')), \
             contextlib.redirect_stdout(output):
            with self.assertRaisesRegex(ImportError, 'missing Qt PDF'):
                probe.main()
        self.assertEqual(output.getvalue(), '')

    @unittest.skipUnless(os.name == 'nt' and shutil.which('powershell.exe'),
                         'Requires Windows PowerShell 5.1')
    def test_windows_powershell_invokes_real_external_dependency_probes(self):
        directory = ROOT/'tmp'/'runtime-probe-tests'
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='space folder ', dir=directory) as folder:
            wrapper = Path(folder)/'probe wrapper.ps1'
            wrapper.write_text(
                'param([string]$Python,[string]$Probe,[string]$Runtime)\n'
                '& $Python $Probe $Runtime\nexit $LASTEXITCODE\n', encoding='utf-8')
            for runtime in ['gui', 'pdf']:
                with self.subTest(runtime=runtime):
                    result = subprocess.run(
                        ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                         '-File', str(wrapper), '-Python', sys.executable,
                         '-Probe', str(PROBE), '-Runtime', runtime],
                        capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                    self.assertEqual(result.stdout.strip(), runtime.upper()+'_RUNTIME_OK')
