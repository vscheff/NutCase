"""Portable mocked release; no prior generated output or FreeCAD runtime needed."""
import json
import tempfile
from pathlib import Path
from pypdf import PdfWriter
from fastener_gui.state import ROOT,atomic_json
from fastener_gui.outputs import load_release,sha256

TEST_TEMP=ROOT/'tmp'/'gui-tests';TEST_TEMP.mkdir(parents=True,exist_ok=True)
# Retain this small diagnostic fixture until Qt's render threads have exited.
# A TemporaryDirectory finalizer can race a still-mapped PDF during shutdown.
directory=Path(tempfile.mkdtemp(prefix='fixture-',dir=TEST_TEMP))
SOURCE=directory/'synthetic Ω & nut.step'
SOURCE.write_text('Mock GUI transport source; never passed to native import.',encoding='utf-8')
record=Path(__file__).with_name('fixtures').joinpath('synthetic_source.json').read_text(encoding='utf-8')
DATA=json.loads(record.replace('@SOURCE@',str(SOURCE).replace('\\','\\\\')))
run_id='mock-gui-release'
release=directory/'releases'/'fixture'/run_id;release.mkdir(parents=True)
stem=SOURCE.stem
for suffix,value in [('.catalog.json',DATA['catalog']),('.analysis.json',DATA['analysis']),
                     ('.config.json',DATA['config']),('.drawing.json',DATA['report']),('.review.json',DATA['review'])]:
    atomic_json(release/(stem+suffix),value)
(release/(stem+'.review.md')).write_text('Mock GUI release, not an engineering deliverable.')
(release/(stem+'.FCStd')).write_bytes(b'Mock project bytes for export checksum tests; no CAD data.')
writer=PdfWriter();writer.add_blank_page(width=792,height=612)
with (release/(stem+'.pdf')).open('wb') as file:writer.write(file)
atomic_json(release/'pdf.verification.json',{'status':'passed','fixture_only':True})
atomic_json(release/'pdf.normalization.json',{'fixture_only':True})
manifest={'schema_version':1,'status':'published_preliminary','source':str(SOURCE),
    'run_id':run_id,'release_directory':str(release),
    'files':{p.name:{'path':str(p),'sha256':sha256(p)} for p in release.iterdir()}}
MANIFEST=directory/(stem+'.current.json');atomic_json(MANIFEST,manifest)
atomic_json(directory/'runs'/run_id/'pipeline.json',{'status':'published_preliminary','source':str(SOURCE),
    'run_id':run_id,'release_directory':str(release),'deliverables':manifest['files']})
RELEASE=load_release(MANIFEST)
CATALOG=DATA['catalog'];ANALYSIS=DATA['analysis']
