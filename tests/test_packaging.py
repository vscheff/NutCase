"""Packaging boundaries and retained publication/data safety contracts."""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
TEST_ROOT=ROOT/'build/tests'
TEST_ROOT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'src'))
import nutcase_runtime as runtime
import fastener_paths as paths
from fastener_gui.state import ConfigStore, atomic_json, completion_status
from fastener_drawing.configuration import read_config
from fastener_drawing.pipeline import publish_release, generate, digest
from fastener_drawing.process_control import Cancelled, ProcessControl
from nutcase_discovery import find_freecad, find_poppler, FREECAD_GUIDANCE


class PackagingTests(unittest.TestCase):
    @unittest.skipUnless(os.name=='nt','Windows job-object contract')
    def test_worker_crash_terminates_native_process_and_descendant(self):
        with tempfile.TemporaryDirectory(dir=TEST_ROOT) as directory:
            root=Path(directory);native=root/'native.py';owner=root/'owner.py'
            gate=root/'gate';pidfile=root/'pids.json'
            native.write_text('import subprocess,sys,time,json,os\n'
                              'from pathlib import Path\n'
                              'while not Path(sys.argv[1]).exists():time.sleep(.02)\n'
                              'child=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"])\n'
                              'Path(sys.argv[2]).write_text(json.dumps([os.getpid(),child.pid]))\n'
                              'time.sleep(60)\n')
            owner.write_text('import os,subprocess,sys,time\n'
                             'from pathlib import Path\n'
                             'from fastener_drawing.process_control import WindowsJob\n'
                             'job=WindowsJob()\n'
                             'child=subprocess.Popen([sys.executable,sys.argv[1],sys.argv[2],sys.argv[3]])\n'
                             'job.assign(child);Path(sys.argv[2]).touch()\n'
                             'for _ in range(200):\n'
                             ' if Path(sys.argv[3]).exists():os._exit(23)\n'
                             ' time.sleep(.02)\n'
                             'job.terminate();sys.exit(1)\n')
            env={**os.environ,'PYTHONPATH':str(ROOT/'src')}
            result=subprocess.run([sys.executable,str(owner),str(native),str(gate),str(pidfile)],
                                  env=env,capture_output=True,timeout=10)
            self.assertEqual(result.returncode,23,result.stderr.decode(errors='replace'))
            import ctypes
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.OpenProcess.restype=ctypes.c_void_p
            kernel.CloseHandle.argtypes=[ctypes.c_void_p]
            kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
            for pid in json.loads(pidfile.read_text()):
                handle=kernel.OpenProcess(0x100000,False,pid)
                if handle:
                    try:self.assertEqual(kernel.WaitForSingleObject(handle,5000),0,'Crash left a contained descendant running')
                    finally:kernel.CloseHandle(handle)

    def test_installed_data_cannot_be_written_into_application_directory(self):
        with patch.object(paths,'INSTALLED',True):
            with self.assertRaisesRegex(ValueError,'outside the NutCase installation'):
                paths.require_user_data_path(ROOT/'drawings')
            self.assertEqual(paths.require_user_data_path(ROOT.parent/'NutCase User Data'),ROOT.parent/'NutCase User Data')
    @unittest.skipUnless(os.name=='nt','Windows job-object contract')
    def test_cancellation_terminates_native_process_and_descendant(self):
        with tempfile.TemporaryDirectory(dir=TEST_ROOT) as directory:
            root=Path(directory);script=root/'native_fixture.py';pidfile=root/'pids.json'
            script.write_text('import subprocess,sys,time,json,os\n'
                              'child=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"])\n'
                              'open(sys.argv[1],"w").write(json.dumps([os.getpid(),child.pid]))\n'
                              'print("NATIVE_STARTED",flush=True)\ntime.sleep(60)\n')
            cancel=root/'cancel';control=ProcessControl(cancel,lambda _:None)
            def request_cancel():
                for _ in range(100):
                    if pidfile.exists():cancel.touch();return
                    time.sleep(.02)
            timer=threading.Thread(target=request_cancel);timer.start()
            try:
                with self.assertRaises(Cancelled):control.run([sys.executable,str(script),str(pidfile)],root,root/'native.log',timeout=5)
            finally:timer.join(3)
            self.assertIn('NATIVE_STARTED',(root/'native.log').read_text())
            import ctypes
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.OpenProcess.restype=ctypes.c_void_p
            kernel.CloseHandle.argtypes=[ctypes.c_void_p]
            kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32)]
            for pid in json.loads(pidfile.read_text()):
                handle=kernel.OpenProcess(0x1000,False,pid)
                if handle:
                    try:
                        code=ctypes.c_uint32();self.assertTrue(kernel.GetExitCodeProcess(handle,ctypes.byref(code)))
                        self.assertNotEqual(code.value,259,'Contained descendant was still running')
                    finally:kernel.CloseHandle(handle)

    def test_frozen_worker_never_relaunches_gui_as_python(self):
        with patch.object(runtime,'FROZEN',True),patch.object(sys,'executable',str(ROOT/'NutCase.exe')):
            program,arguments=runtime.worker_invocation('gui-job',ROOT/'path & Ω'/'request.json')
            self.assertEqual(Path(program).name,'NutCaseWorker.exe')
            self.assertEqual(arguments,['gui-job',str(ROOT/'path & Ω'/'request.json')])

    def test_native_environment_drops_gui_contamination(self):
        env=runtime.clean_environment({'PYTHONHOME':'bad','PYTHONPATH':'bad','QT_PLUGIN_PATH':'bad',
                                       'QT_QPA_PLATFORM':'windows','PATH':os.defpath,'NUTCASE_DATA_HOME':'state'})
        self.assertFalse({'PYTHONHOME','PYTHONPATH','QT_PLUGIN_PATH','QT_QPA_PLATFORM'} & env.keys())
        self.assertEqual(env['NUTCASE_DATA_HOME'],'state')

    def test_installed_native_sources_use_same_user_data_as_frozen_gui(self):
        with tempfile.TemporaryDirectory(dir=TEST_ROOT) as directory:
            app=Path(directory)/'Read Only App';app.mkdir()
            (app/'native-src').mkdir();(app/'VERSION').write_text('0.6.0')
            import shutil
            shutil.copy2(ROOT/'src/fastener_paths.py',app/'native-src/fastener_paths.py')
            (app/'nutcase-build.json').write_text('{}')
            env={**os.environ,'PYTHONPATH':str(app/'native-src'),'LOCALAPPDATA':str(Path(directory)/'User Data')}
            env.pop('NUTCASE_DATA_HOME',None)
            result=subprocess.run([sys.executable,'-c',
                'import fastener_paths as p; print(p.SETTINGS_ROOT); print(p.DRAWINGS_ROOT); print(p.CACHE_ROOT)'],
                env=env,capture_output=True,text=True,check=True)
            self.assertTrue(all('User Data' in row and 'Read Only App' not in row for row in result.stdout.splitlines()))

    def test_missing_freecad_has_install_guidance(self):
        path,native,error=find_freecad(str(ROOT/'not-installed/python.exe'))
        self.assertEqual(path,'');self.assertIsNone(native)
        self.assertIn('https://www.freecad.org/downloads.php',error)

    def test_invalid_explicit_poppler_is_not_silently_replaced(self):
        self.assertEqual(find_poppler(str(ROOT/'not-installed/pdftoppm.exe')),'')

    def test_exit_two_is_success_with_engineering_warning(self):
        self.assertEqual(completion_status(2,{'status':'published_preliminary'}),'Completed - Engineering Review Required')
        self.assertIn('Failed',completion_status(1,{}))

    def test_configuration_restart_and_history_preserve_format(self):
        with tempfile.TemporaryDirectory(dir=TEST_ROOT) as directory:
            source=Path(directory)/'nut Ω.step';source.write_bytes(b'source')
            first=ConfigStore(Path(directory)/'settings');config=read_config()
            first.save(source,config)
            self.assertEqual(ConfigStore(first.directory).load(source),config)
            config['metadata']['revision']='B';first.save(source,config)
            self.assertEqual(len(list((first.path(source).parent/'history').glob('*.json'))),1)

    def test_publication_failure_retains_previous_manifest(self):
        with tempfile.TemporaryDirectory(dir=TEST_ROOT) as directory:
            root=Path(directory);candidate=root/'candidate';candidate.mkdir()
            (candidate/'part.pdf').write_bytes(b'pdf')
            manifest=root/'part.current.json';manifest.write_bytes(b'previous release')
            with self.assertRaises(ValueError):publish_release(candidate,root/'releases/new',manifest,root/'part.step','new')
            self.assertEqual(manifest.read_bytes(),b'previous release')

    def test_complete_publication_hashes_exact_artifacts(self):
        with tempfile.TemporaryDirectory(dir=TEST_ROOT) as directory:
            root=Path(directory);candidate=root/'candidate';candidate.mkdir()
            for name in ('part.pdf','part.FCStd'):(candidate/name).write_bytes(name.encode())
            manifest=root/'part.current.json'
            record=publish_release(candidate,root/'releases/new',manifest,root/'part.step','new')
            self.assertEqual(json.loads(manifest.read_text()),record)
            self.assertTrue(record['engineering_verification_required'])
            self.assertTrue(all(digest(row['path'])==row['sha256'] for row in record['files'].values()))

    def test_cancel_before_publication_preserves_prior_release(self):
        with tempfile.TemporaryDirectory(dir=TEST_ROOT) as directory:
            root=Path(directory);source=root/'part.step';source.write_bytes(b'STEP fixture')
            output=root/'drawings';output.mkdir();manifest=output/'part.current.json'
            manifest.write_bytes(b'previous release')
            cancel=root/'cancel';cancel.touch();control=ProcessControl(cancel,lambda _:None)
            native=root/'native-python.exe';native.write_bytes(b'never executed')
            with self.assertRaises(Cancelled):
                generate(source,output,native,sys.executable,fresh_config=True,control=control)
            self.assertEqual(manifest.read_bytes(),b'previous release')
            self.assertFalse((output/'.generation.lock').exists())


if __name__=='__main__':unittest.main()
