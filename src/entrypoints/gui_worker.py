"""JSON-line desktop worker; FreeCAD and normalization remain separate processes."""
import json
import sys
import traceback
from pathlib import Path

import _bootstrap
from fastener_drawing.pipeline import generate
from fastener_drawing.process_control import Cancelled, ProcessControl, WindowsJob
from fastener_gui.outputs import load_release, load_history
from fastener_gui.state import read_json, atomic_json


def emit(kind, **fields):
    # ASCII framing also works when launched from a Windows legacy-codepage
    # console; JSON decoding restores diameter symbols and Unicode filenames.
    print(json.dumps({'type':kind, **fields}, ensure_ascii=True), flush=True)


def main():
    request = read_json(sys.argv[1])
    job = WindowsJob()
    try:
        # Descendants die if this worker crashes or its GUI disappears.
        job.assign()
        control = ProcessControl(request['cancel_path'], lambda message:emit('stage', message=message))
        if request['action'] in ('open_release', 'open_history'):
            control.stage('Validating The Selected Release And Checksums')
            release = (load_release(request['manifest'], request.get('source')) if request['action']=='open_release'
                       else load_history(request['history'], request['output'], request['source']))
            result = {'status':'release_loaded', 'release':release}
            code = 0
        else:
            result = generate(request['source'], request['output'], request['freecad_python'], request['poppler'],
                request.get('config'), catalog_only=request['action']=='analyze',
                fresh_config=request['action']=='analyze', control=control)
            if request['action'] == 'analyze':
                result['analysis'] = str(Path(result['catalog']).with_name(Path(request['source']).stem+'.analysis.json'))
                code = 0
            else:
                emit('stage', message='Checking The Published Manifest Before Preview')
                result['release'] = load_release(result['current_manifest'], request['source'], result['run_id'])
                code = 2 if result.get('geometry_requires_review') or result.get('unresolved_dimensions') else 0
        atomic_json(Path(sys.argv[1]).with_name('result.json'), result)
        emit('result', result=result)
        return code
    except Cancelled as error:
        emit('error', message=str(error), cancelled=True)
        return 3
    except Exception as error:
        emit('error', message=str(error), traceback=traceback.format_exc())
        return 1
    finally:
        # Closing a job containing this process would kill it before QProcess
        # receives its exit code. OS teardown closes it after normal exit.
        # The handle is deliberately retained for exactly this worker lifetime.
        pass


if __name__ == '__main__':
    raise SystemExit(main())
