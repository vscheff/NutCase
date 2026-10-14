"""New competing-process lock regression; native CAD is deliberately injected."""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class ConcurrencyTests(unittest.TestCase):
    def test_two_processes_cannot_publish_into_the_same_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'part.step';source.write_bytes(b'mock CAD transport source')
            native=root/'native.exe';native.write_bytes(b'not executed')
            output=root/'drawings';output.mkdir();manifest=output/'part.current.json';manifest.write_bytes(b'previous release')
            worker=root/'contender.py';entered=root/'entered';gate=root/'release'
            worker.write_text('import sys,time\nfrom pathlib import Path\n'
                'from fastener_drawing import pipeline\n'
                'root=Path(sys.argv[1])\n'
                'def injected_native(python,script,args,log):\n'
                ' (root/"entered").touch()\n'
                ' while not (root/"release").exists():time.sleep(.02)\n'
                ' return 0\n'
                'pipeline.native_process=injected_native\n'
                'try:pipeline.generate(root/"part.step",root/"drawings",root/"native.exe",sys.executable,catalog_only=True,fresh_config=True)\n'
                'except FileExistsError:sys.exit(17)\n',encoding='utf-8')
            env={**os.environ,'PYTHONPATH':str(ROOT/'src')}
            first=subprocess.Popen([sys.executable,str(worker),str(root)],env=env,
                                   stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                deadline=time.monotonic()+10
                while not entered.exists() and first.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue(entered.exists(),'First worker never acquired its lock')
                second=subprocess.run([sys.executable,str(worker),str(root)],env=env,capture_output=True,timeout=10)
                self.assertEqual(second.returncode,17,second.stderr.decode(errors='replace'))
                self.assertTrue((output/'.generation.lock').exists())
                self.assertEqual(manifest.read_bytes(),b'previous release')
                gate.touch();stdout,stderr=first.communicate(timeout=10)
                self.assertEqual(first.returncode,0,stderr.decode(errors='replace'))
                self.assertFalse((output/'.generation.lock').exists());self.assertEqual(manifest.read_bytes(),b'previous release')
            finally:
                gate.touch()
                if first.poll() is None:first.kill();first.communicate(timeout=5)
