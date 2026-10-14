"""Fail the build if the actual frozen GUI/worker cannot launch in isolation."""
import json
import os
import subprocess
from pathlib import Path

root=Path(__file__).resolve().parents[1]
bundle=root/'dist/NutCase'
evidence=root/'build/smoke-data';evidence.mkdir(parents=True,exist_ok=True)
env=dict(os.environ)
for name in ('PYTHONHOME','PYTHONPATH','QT_PLUGIN_PATH','QML2_IMPORT_PATH','QT_QPA_PLATFORM'):
    env.pop(name,None)
env.update(PATH=str(Path(os.environ['SystemRoot'])/'System32'),NUTCASE_DATA_HOME=str(evidence),
           PYINSTALLER_RESET_ENVIRONMENT='1',PYTHONDONTWRITEBYTECODE='1')
report=evidence/'startup.json'
report.unlink(missing_ok=True)
gui=subprocess.run([str(bundle/'NutCase.exe'),'--startup-check','--check-report',str(report)],env=env,timeout=60)
assert gui.returncode==0 and report.is_file(),'Frozen GUI failed; inspect build/smoke-data/logs'
startup=json.loads(report.read_text())
assert startup['status']=='GUI_STARTUP_OK' and startup['frozen'] and startup['title']=='NutCase'
assert Path(startup['runtime']['poppler']).is_file()
missing_report=evidence/'missing-freecad.json'
missing=subprocess.run([str(bundle/'NutCase.exe'),'--startup-check','--freecad-python',str(evidence/'absent/python.exe'),
                        '--check-report',str(missing_report)],env=env,timeout=60)
assert missing.returncode==0
missing_startup=json.loads(missing_report.read_text())
assert not missing_startup['runtime']['freecad_python'] and 'https://www.freecad.org/downloads.php' in missing_startup['status_text']
worker=subprocess.run([str(bundle/'NutCaseWorker.exe'),'diagnose'],env=env,capture_output=True,text=True,timeout=60,check=True)
diagnostic=json.loads(worker.stdout)
assert diagnostic['frozen'] and diagnostic['version']==startup['version']
(evidence/'worker.json').write_text(worker.stdout)
request=evidence/'request.json'
request.write_text(json.dumps({'action':'open_release','manifest':str(evidence/'nonexistent.current.json'),
                              'cancel_path':str(evidence/'cancel')}))
job=subprocess.run([str(bundle/'NutCaseWorker.exe'),'gui-job',str(request)],env=env,capture_output=True,text=True,timeout=30)
assert job.returncode==1
messages=[json.loads(line) for line in job.stdout.splitlines() if line.startswith('{')]
assert any(message['type']=='error' and 'FileNotFoundError' in message.get('traceback','') for message in messages),job.stdout+job.stderr
print('Frozen GUI, dependency discovery, JSON worker dispatch and expected failure PASSED')
