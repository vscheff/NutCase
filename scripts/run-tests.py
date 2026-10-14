"""Run isolated regression suites, with durable JSON and text results.

External Python: --suite fast|pdf|gui|launchers|packaging|full.
FreeCAD bundled Python: --suite native. full dispatches native to --freecad-python.
"""
import argparse
import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITES = {'native': 'tests_native', 'pdf': 'tests_pdf', 'gui': 'tests_gui',
          'launchers': 'tests_launchers', 'packaging': 'tests'}


class RecordedResult(unittest.TextTestResult):
    def startTest(self, test):
        if not hasattr(self, 'test_ids'): self.test_ids = []
        self.test_ids.append(test.id())
        super().startTest(test)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', choices=[*SUITES, 'fast', 'full'], default='fast')
    parser.add_argument('--freecad-python', type=Path, default=os.environ.get('NUTCASE_TEST_FREECAD'))
    parser.add_argument('--poppler', default=os.environ.get('NUTCASE_TEST_POPPLER'))
    parser.add_argument('--samples', action='store_true', help='Also exercise optional supplied local STEP assets')
    parser.add_argument('--results', type=Path, default=ROOT/'build/test-results')
    parser.add_argument('--pattern', default='test_*.py', help='Targeted test module pattern for diagnosis')
    args = parser.parse_args()
    results = args.results.resolve(); results.mkdir(parents=True, exist_ok=True)
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    os.environ['NUTCASE_TEST_RESULTS'] = str(results)
    if args.samples: os.environ['NUTCASE_TEST_SAMPLES'] = '1'
    if args.freecad_python: os.environ['NUTCASE_TEST_FREECAD'] = str(args.freecad_python.resolve())
    if args.poppler: os.environ['NUTCASE_TEST_POPPLER'] = str(Path(args.poppler).resolve())
    # Keep test preferences/cache outside the shipped runtime and user's settings.
    os.environ['NUTCASE_DATA_HOME'] = str(results/'data')
    os.environ['FREECAD_USER_HOME'] = str(results/'freecad-preferences')
    selected = ['pdf', 'gui', 'packaging'] if args.suite == 'fast' else (
        ['native','gui','pdf','launchers','packaging'] if args.suite == 'full' else [args.suite])
    if len(selected) > 1:
        records = []
        for suite in selected:
            python = args.freecad_python if suite == 'native' else sys.executable
            if not python:
                records.append({'suite': suite, 'status': 'unavailable', 'reason': '--freecad-python required'})
                continue
            command = [str(python), str(Path(__file__).resolve()), '--suite', suite, '--results', str(results)]
            if args.samples: command.append('--samples')
            with (results/(suite+'.log')).open('w', encoding='utf-8') as log:
                completed = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                           timeout=1800, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            record_path = results/(suite+'.json')
            record = json.loads(record_path.read_text(encoding='utf-8')) if record_path.exists() else {
                'suite': suite, 'status': 'failed_to_start', 'returncode': completed.returncode}
            records.append(record)
            print(f"{suite}: {record['status']} ({record.get('tests_run', 0)} tests, {len(record.get('skipped', []))} skipped)", flush=True)
        (results/(args.suite+'.json')).write_text(json.dumps(records, indent=2)+'\n', encoding='utf-8')
        return int(any(r['status'] != 'passed' for r in records))
    suite = selected[0]
    sys.path[:0] = [str(ROOT/'src'), str(ROOT/SUITES[suite]), str(ROOT/'tests_support')]
    if suite=='gui':
        from qt_test_runtime import initialize
        initialize()
    started = time.monotonic()
    tests = unittest.defaultTestLoader.discover(str(ROOT/SUITES[suite]), pattern=args.pattern)
    result = unittest.TextTestRunner(verbosity=2,resultclass=RecordedResult).run(tests)
    record = {'suite': suite, 'status': 'passed' if result.wasSuccessful() else 'failed',
              'tests_run': result.testsRun, 'elapsed_seconds': round(time.monotonic()-started, 3),
              'python': sys.executable, 'version': sys.version, 'samples_enabled': args.samples,
              'test_ids':getattr(result,'test_ids',[]),
              'failures': [{'test': str(t), 'traceback': s} for t, s in result.failures],
              'errors': [{'test': str(t), 'traceback': s} for t, s in result.errors],
              'skipped': [{'test': str(t), 'reason': s} for t, s in result.skipped]}
    (results/(suite+'.json')).write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    return int(not result.wasSuccessful())


if __name__ == '__main__':
    raise SystemExit(main())
