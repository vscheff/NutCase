"""External-Python orchestration with immutable releases and atomic publication."""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .configuration import read_config
from .pdf_compatibility import normalize_pdf
from .pdf_verification import verify_pdf
from .review import build_review, write_review
from fastener_paths import PROJECT_ROOT as ROOT, ENTRYPOINTS


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path=Path(path)
    with path.open('w',encoding='utf-8') as f:
        json.dump(value,f,indent=2,ensure_ascii=False)
        f.write('\n');f.flush();os.fsync(f.fileno())


def native_process(python, script, arguments, log):
    completed=subprocess.run([str(python),str(ENTRYPOINTS/script),*map(str,arguments)],
        cwd=ROOT,capture_output=True,text=True,timeout=600,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    Path(log).write_text(completed.stdout+completed.stderr,encoding='utf-8')
    if completed.returncode not in (0,2):
        raise RuntimeError(script+' failed; '+completed.stderr[-2000:]+'; log: '+str(log))
    return completed.returncode


def publish_release(candidate, release, manifest, source, run_id):
    """A single atomic manifest is the commit point for the complete verified set.

    A crash before manifest replacement leaves the old set current, or no set
    current on first generation. An orphaned verified release is safe to retain.
    No legacy root PDF/project aliases are rewritten independently.
    """
    candidate,release,manifest=map(Path,(candidate,release,manifest))
    files={p.name:digest(p) for p in candidate.iterdir() if p.is_file()}
    if not any(x.endswith('.pdf') for x in files) or not any(x.endswith('.FCStd') for x in files):
        raise ValueError('Publication requires the complete verified PDF/project set')
    release.parent.mkdir(parents=True,exist_ok=True)
    os.replace(candidate,release)
    # Directory rename can make child paths unreadable on Windows even though
    # the rename itself succeeds. Verify the final locations before the commit.
    for name,expected in files.items():
        if digest(release/name)!=expected:
            raise ValueError('Release artifact changed or became unreadable: '+name)
    record={'schema_version':1,'status':'published_preliminary','run_id':run_id,'source':str(source),
            'release_directory':str(release),'files':{name:{'path':str(release/name),'sha256':sha} for name,sha in files.items()},
            'commit_protocol':'Immutable complete release; atomic current manifest replacement',
            'engineering_verification_required':True}
    pending=manifest.with_name(manifest.name+'.'+run_id+'.pending')
    try:
        write_json(pending,record)
        os.replace(pending,manifest)
    finally:
        if pending.exists():pending.unlink()
    return record


def generate(source, output, freecad_python, poppler, config_path=None, mode=None, catalog_only=False, fresh_config=False, control=None):
    def stage(message):
        if control: control.stage(message)

    def run_native(python, script, arguments, log):
        if control:
            return control.run([str(python),str(ENTRYPOINTS/script),*map(str,arguments)],ROOT,log)
        return native_process(python,script,arguments,log)
    source,output=Path(source).resolve(),Path(output).resolve()
    freecad_python=Path(freecad_python).resolve()
    if Path(sys.executable).resolve()==freecad_python:
        raise ValueError('Run the pipeline in external Python; normalization must remain outside FreeCAD')
    if not source.is_file() or source.suffix.lower() not in ('.stp','.step'):
        raise ValueError('Input must be an existing STEP file')
    if not freecad_python.is_file() or not poppler or not Path(poppler).is_file():
        raise ValueError('Working FreeCAD Python and pdftoppm paths are required')
    output.mkdir(parents=True,exist_ok=True)
    lock=output/'.generation.lock'
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    os.write(fd, f'pid={os.getpid()}\n'.encode());os.close(fd)
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:10]
    run=output/'runs'/run_id
    state={'phase':4,'status':'started','run_id':run_id,'source':str(source),'staging_directory':str(run),
           'external_python':sys.executable,'freecad_python':str(freecad_python),'steps':[]}
    manifest=output/(source.stem+'.current.json')
    try:
        run.mkdir(parents=True)
        native=run/'native';native.mkdir()
        source_hash=digest(source)
        if fresh_config and config_path is not None:
            raise ValueError('Choose either --config or --fresh-config, not both')
        if config_path is None and manifest.exists() and not fresh_config:
            prior=json.loads(manifest.read_text(encoding='utf-8'))
            config_path=Path(prior['release_directory'])/(source.stem+'.config.json')
        config=read_config(config_path) if not fresh_config else read_config()
        if mode:config['dimensioning']['mode']=mode
        requested=run/'requested.config.json';write_json(requested,config)
        stage('Analyzing STEP Geometry And Validating Saved References')
        run_native(freecad_python,'prepare_generation.py',[source,'--output-dir',native,'--config',requested],run/'analysis.log')
        state['steps'].append('geometry_analysis_and_saved_reference_validation')
        resolved=native/(source.stem+'.config.json')
        if catalog_only:
            state.update(status='catalog_ready',config=str(resolved),catalog=str(native/(source.stem+'.catalog.json')))
            return state
        stage('Generating Associative CAD Dimensions And Exporting Native PDF')
        run_native(freecad_python,'generate_drawing.py',[source,'--output-dir',native,'--config',resolved],run/'drawing.log')
        state['steps'].append('verified_native_drawing_and_native_pdf_export')
        report=json.loads((native/(source.stem+'.drawing.json')).read_text(encoding='utf-8'))
        if not report['drawing_status'].startswith('generated') or not report['source_sha256_verified_unchanged']:
            raise ValueError('Native drawing did not pass source/export validation')
        normalized=run/'normalized.pdf'
        labels=report['native_render_checks']['actual_dimension_labels']
        stage('Normalizing Native PDF In External Python')
        normalization=normalize_pdf(native/(source.stem+'.pdf'),normalized,labels)
        write_json(run/'normalization.json',normalization)
        state['steps'].append('external_pdf_normalization')
        stage('Verifying PDF Structure, Labels And Independent Renderers')
        verification=verify_pdf(normalized,report,run/'verification',poppler)
        state['steps'].append('independent_pdf_verification')
        if digest(source)!=source_hash or report['phase1_analysis']['source']['sha256_before']!=source_hash:
            raise ValueError('Source changed during pipeline; publication refused')
        # Repeating a long STEP filename as both directory and filename exceeds
        # MAX_PATH on this Windows runtime. Keep the full filenames, shorten only
        # their parent bucket, and always use the manifest for lookup.
        short=re.sub(r'[^a-zA-Z0-9_-]','-',source.stem)[:16].strip('-') or 'part'
        bucket=short+'-'+hashlib.sha256(source.stem.encode('utf-8')).hexdigest()[:12]
        release=output/'releases'/bucket/run_id
        if os.name=='nt' and len(str(release/(source.stem+'.drawing.json')))>=260:
            raise ValueError('Final artifact paths exceed this Windows runtime limit; choose a shorter output directory')
        stage('Assembling The Verified Release')
        candidate=run/'publish-ready';candidate.mkdir()
        for extension in ('.FCStd','.analysis.json','.config.json','.catalog.json','.coverage.md','.render.svg','.template.svg'):
            item=native/(source.stem+extension)
            if not item.is_file():raise ValueError('Missing deliverable: '+str(item))
            shutil.copy2(item,candidate/item.name)
        shutil.copy2(normalized,candidate/(source.stem+'.pdf'))
        if digest(candidate/(source.stem+'.pdf'))!=normalization['output_sha256']:
            raise ValueError('Normalized PDF changed during release assembly')
        if digest(candidate/(source.stem+'.FCStd'))!=digest(native/(source.stem+'.FCStd')):
            raise ValueError('Verified project changed during release assembly')
        review=build_review(report)
        write_review(candidate/(source.stem+'.review.json'),review)
        for name in ('poppler.png','pdfium.png'):
            shutil.copy2(run/'verification'/name,candidate/name)
        report['phase4']={'configuration_preserved':True,'review_report':str(release/(source.stem+'.review.json')),
                         'native_pdf_retained':str(native/(source.stem+'.pdf')),'staging_directory':str(run),
                         'normalization':normalization,'pdf_verification':verification}
        report['pdf_compatibility']=normalization
        for key,extension in (('project','.FCStd'),('pdf','.pdf'),('rendered_svg','.render.svg')):
            report['exports'][key]=str(release/(source.stem+extension))
        write_json(candidate/(source.stem+'.drawing.json'),report)
        write_json(candidate/'pdf.normalization.json',normalization)
        write_json(candidate/'pdf.verification.json',verification)
        if digest(source)!=source_hash:raise ValueError('Source changed before publication')
        # The final cancellation checkpoint precedes the single commit protocol.
        # A request arriving during commit cannot turn a published set into failure.
        stage('Publishing The Complete Release')
        published=publish_release(candidate,release,manifest,source,run_id)
        state.update(status='published_preliminary',current_manifest=str(manifest),release_directory=str(release),
                     geometry_requires_review=report['geometry_requires_review'],unresolved_dimensions=report['unresolved_dimensions'],
                     source_unchanged=True,deliverables=published['files'])
        state['steps'].append('atomic_complete_release_publication')
        return state
    except Exception as exc:
        state.update(status='failed_not_published',error={'type':type(exc).__name__,'message':str(exc)})
        raise
    finally:
        try:
            if run.exists():
                try:write_json(run/'pipeline.json',state)
                except OSError:
                    # Publication has a single commit point. A failed diagnostic
                    # write after that point must not misreport a failed release.
                    if state['status']!='published_preliminary':raise
        finally:lock.unlink()


def main(argv=None):
    p=argparse.ArgumentParser(description='STEP to verified native drawing and normalized PDF, with atomic complete release publication')
    p.add_argument('input',type=Path)
    p.add_argument('--output-dir',type=Path,default=ROOT/'output')
    p.add_argument('--freecad-python',required=True,type=Path)
    p.add_argument('--poppler',default=shutil.which('pdftoppm'))
    p.add_argument('--config',type=Path)
    p.add_argument('--mode',choices=('basic','comprehensive','custom'))
    p.add_argument('--catalog-only',action='store_true',help='Analyze and emit bound editable config/catalog without drawing or publication')
    p.add_argument('--fresh-config',action='store_true',help='Explicitly start a new default policy instead of reusing the current saved policy')
    a=p.parse_args(argv)
    try:
        result=generate(a.input,a.output_dir,a.freecad_python,a.poppler,a.config,a.mode,a.catalog_only,a.fresh_config)
        print(json.dumps({k:v for k,v in result.items() if k!='deliverables'},indent=2))
        return 2 if result.get('geometry_requires_review') or result.get('unresolved_dimensions') else 0
    except Exception as exc:
        print('Pipeline failed; previous release remains current: '+str(exc),file=sys.stderr)
        return 1
