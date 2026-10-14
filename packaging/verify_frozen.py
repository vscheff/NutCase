"""Candidate regression harness frozen with the same GUI, outside the installer.

Runs real QProcess workers, native verification, both PDF renderers and Qt preview.
No development Python is used while this executable runs.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QFileDialog
from PySide6.QtPdf import QPdfDocument
from fastener_gui.window import MainWindow
from fastener_gui.state import read_json, atomic_json
from fastener_gui.outputs import sha256, load_release
from fastener_gui.theme import apply_theme
from fastener_paths import DATA_ROOT, FROZEN, VERSION


def wait_job(window, launch, timeout=240000):
    loop=QEventLoop();result=[]
    def finish(code,value):result.append((code,value));loop.quit()
    window.backend.completed.connect(finish)
    timer=QTimer();timer.setSingleShot(True);timer.timeout.connect(loop.quit)
    try:
        launch()
        if not window.backend.busy:raise AssertionError('GUI did not launch a worker: '+window.status.text())
        timer.start(timeout);loop.exec()
        if not result:
            window.backend.cancel()
            raise TimeoutError('Packaged worker exceeded verification timeout')
        return result[0]
    finally:
        timer.stop();window.backend.completed.disconnect(finish)


def open_external(window):
    code,result=wait_job(window,window.open_current)
    assert code==0 and window.release
    loop=QEventLoop();accepted=[]
    window.file_opener.accepted.connect(lambda message:(accepted.append(message),loop.quit()))
    window.file_opener.failed.connect(lambda message:(accepted.append('FAILED: '+message),loop.quit()))
    window.open_artifact('pdf');QTimer.singleShot(20000,loop.quit);loop.exec()
    assert accepted and not accepted[0].startswith('FAILED:'),accepted
    assert (Path(window.runtime_values['freecad_python']).parent/'freecad.exe').is_file()
    assert window.open_project(),window.status.text()
    return {'pdf':accepted[0],'freecad':'Detached launch accepted; interactive viewing unverified'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models',type=Path)
    parser.add_argument('--runtime-probe',action='store_true')
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--worker',type=Path)
    parser.add_argument('--open-external',action='store_true')
    parser.add_argument('--open-existing',action='store_true',help='Check only retained current release and external viewer dispatch')
    args=parser.parse_args()
    if not FROZEN:raise RuntimeError('Run NutCaseVerify.exe, not the development interpreter')
    if not os.environ.get('NUTCASE_DATA_HOME'):raise RuntimeError('Set NUTCASE_DATA_HOME to an isolated verification directory')
    if args.worker:
        import fastener_gui.controller as controller
        import fastener_gui.file_opener as file_opener
        controller.invocation=lambda request_path,python=None:(str(args.worker),['gui-job',str(request_path)])
        file_opener.invocation=lambda path:(str(args.worker),['open-file',str(path)])
    installed_poppler=(args.worker.parent/'vendor/poppler/Library/bin/pdftoppm.exe') if args.worker else None
    if installed_poppler and not installed_poppler.is_file():raise RuntimeError('Installed Poppler is missing')
    def create_window():return MainWindow(poppler=str(installed_poppler) if installed_poppler else '')
    app=QApplication(sys.argv);app.setApplicationName('NutCase');app.setApplicationVersion(VERSION);apply_theme(app)
    report={'version':VERSION,'frozen':FROZEN,'executable':sys.executable,'data_root':str(DATA_ROOT),'checks':[],
            'limitations':['Not a clean Windows VM','External viewer rendering and interactive FreeCAD inspection need human acceptance',
                           'Scripted checks do not establish all interactive behavior']}
    window=None
    try:
        source_directory=DATA_ROOT/'import Ω & space';source_directory.mkdir(parents=True,exist_ok=True)
        exports=DATA_ROOT/'export Ω & space';exports.mkdir(exist_ok=True)
        window=create_window();window.show()
        if args.runtime_probe:
            from runtime_probe import run
            report=run(app,window,args.report)
            return 0
        report['worker']=str(args.worker or Path(sys.executable).parent/'NutCaseWorker.exe')
        report['poppler']=window.runtime_values['poppler']
        if args.open_existing:
            report['external_open']=open_external(window)
            report['status']='passed'
            print('Existing release and external viewer dispatch PASSED',flush=True)
            return 0
        assert window.runtime_values['freecad_python'],window.status.text()
        assert window.runtime_values['poppler'],window.status.text()
        assert window.store.directory.is_relative_to(DATA_ROOT)
        report['native']=window.native_runtime;report['runtime']=window.runtime_values
        if args.models is None:raise ValueError('--models is required for CAD regression')
        models=sorted([*args.models.glob('*.stp'),*args.models.glob('*.step')])
        assert len(models)==2,'The two supplied STEP models are required'
        original_hashes={str(path):sha256(path) for path in models}
        for index,original in enumerate(models):
            source=source_directory/('model %d Ω & nut.step' % index);shutil.copy2(original,source)
            window.set_source(source)
            code,result=wait_job(window,window.analyze)
            assert code==0 and window.model.catalog and not window.model.binding_problem,window.status.text()
            report['checks'].append({'model':original.name,'action':'analysis','code':code,'candidates':len(window.model.catalog['candidates'])})
            for mode in ('Basic','Comprehensive','Custom'):
                window.mode.setCurrentText(mode)
                if mode=='Custom':
                    # Select a candidate already verified by the Comprehensive native run.
                    prior=load_release(Path(window.runtime_values['output'])/(source.stem+'.current.json'),source)
                    created=[row for row in prior['report']['dimensions'].values() if row['status']=='created']
                    assert created
                    stable=created[0]['stable_id']
                    window.model.set_selected(stable,True);window._apply_config()
                code,result=wait_job(window,window.generate)
                assert code==2 and window.release,window.status.text()
                release=window.release
                assert release['pdf_audit']['status']=='passed'
                assert window.preview.document.status()==QPdfDocument.Status.Ready
                assert window.preview.document.pageCount()==1
                image=window.preview.document.render(0,window.preview.view.size())
                assert not image.isNull()
                assert any(image.pixelColor(x,y).lightness()<200
                           for y in range(0,image.height(),4) for x in range(0,image.width(),4)), 'Qt PDF rendered an empty sheet'
                # QPdfView paints asynchronously. Let its tile cache finish before
                # capturing the widget instead of grabbing a just-cleared canvas.
                paint_loop=QEventLoop();QTimer.singleShot(800,paint_loop.quit);paint_loop.exec()
                assert release['report']['source_sha256_verified_unchanged']
                assert release['report']['reopen_checks']['reopened_successfully']
                assert release['report']['configuration']['dimensioning']['mode']==mode.lower()
                destination_pdf=exports/('%d %s Ω.pdf' % (index,mode))
                destination_project=exports/('%d %s Ω.FCStd' % (index,mode))
                original_dialog=QFileDialog.getSaveFileName
                try:
                    for key,destination in (('pdf',destination_pdf),('project',destination_project)):
                        QFileDialog.getSaveFileName=lambda *a, target=destination, **k:(str(target),'')
                        window.export_artifact(key)
                        assert destination.is_file() and sha256(destination)==sha256(release[key])
                finally:QFileDialog.getSaveFileName=original_dialog
                screenshot=args.report.parent/('%d-%s.png' % (index,mode.lower()))
                window.grab().save(str(screenshot))
                report['checks'].append({'model':original.name,'action':'generation','mode':mode,'code':code,
                    'pdf_preview':'Qt PDF ready and render passed','pdf_verification':release['pdf_audit'],
                    'native_reopen':True,'export_hashes':True,'manifest':release['manifest_path'],
                    'dimensions':sum(row['status']=='created' for row in release['report']['dimensions'].values())})
                print(original.name+' '+mode+' PASSED',flush=True)
            # Save/restart must restore this exact source-bound custom policy.
            window.save_configuration();policy=window.store.load(source)
            window.close();window=create_window();window.show()
            assert window.model.source==source
            code,result=wait_job(window,window.analyze)
            assert code==0 and window.model.config==policy and not window.model.binding_problem
            report['checks'].append({'model':original.name,'action':'restart_source_bound_configuration','passed':True})
            code,result=wait_job(window,window.open_current)
            assert code==0 and window.release
            manifest=Path(window.release['manifest_path']);prior=manifest.read_bytes()
            cancelled=[False]
            def on_stage(message):
                if message=='Generating Associative CAD Dimensions And Exporting Native PDF' and not cancelled[0]:
                    cancelled[0]=True;QTimer.singleShot(300,window.backend.cancel)
            window.backend.stage.connect(on_stage)
            try:code,result=wait_job(window,window.generate)
            finally:window.backend.stage.disconnect(on_stage)
            assert cancelled[0] and code==3 and window.release is None
            assert manifest.read_bytes()==prior
            assert not (Path(window.runtime_values['output'])/'.generation.lock').exists()
            report['checks'].append({'model':original.name,'action':'cancellation','code':code,'previous_manifest_unchanged':True})
            request=window._request('generate');request['freecad_python']=str(DATA_ROOT/'missing/python.exe')
            window.action='generate'
            code,result=wait_job(window,lambda:window.backend.start(request))
            assert code==1 and manifest.read_bytes()==prior and window.release is None
            report['checks'].append({'model':original.name,'action':'failed_generation','code':code,'previous_manifest_unchanged':True})
        assert all(sha256(path)==expected for path,expected in original_hashes.items())
        report['checks'].append({'action':'original_STEP_integrity','passed':True,'hashes':original_hashes})
        if args.open_external:
            report['external_open']=open_external(window)
        report['status']='passed'
        return 0
    except Exception:
        import traceback
        report['status']='failed';report['error']=traceback.format_exc()
        if window is not None:
            report['worker_error']=window.backend.last_error
            report['gui_log']=window.logs.toPlainText()
        print(report['error'],file=sys.stderr)
        return 1
    finally:
        args.report.parent.mkdir(parents=True,exist_ok=True);atomic_json(args.report,report)
        if window is not None:
            if window.backend.busy:window.backend.cancel()
            else:window.close()


if __name__=='__main__':raise SystemExit(main())
