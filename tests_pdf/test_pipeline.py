"""Publication failure controls use real retained PDFs, with native worker fault injection."""
import copy
import json
import tempfile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastener_drawing.configuration import DEFAULT, make_catalog, bind_config
from fastener_drawing.pipeline import ROOT, generate, publish_release, digest, write_json

from test_compatibility import fixture
DATA=json.loads((ROOT/'tests_gui/fixtures/synthetic_source.json').read_text(encoding='utf-8'))
# Fault-injected native workers never interpret this transport fixture as CAD.
FIXTURES=ROOT/'build/test-fixtures';FIXTURES.mkdir(parents=True,exist_ok=True)
SOURCE=FIXTURES/'publication Ω & fixture.step'
SOURCE.write_bytes(b'Independent publication transport fixture; mocked native input')
REPORT=copy.deepcopy(DATA['report'])
REPORT.update(drawing_status='generated_fixture',native_render_checks={'actual_dimension_labels':['20.00','10.00']})
REPORT['phase1_analysis']['source']['sha256_before']=digest(SOURCE)
FREECAD=Path(sys.executable).parent/'mock-native-python.exe'
FREECAD.write_bytes(b'Never executed: native worker injected by this suite')
PLACEHOLDER_RENDERER=sys.executable  # fault injection never executes the renderer


class PublicationTests(unittest.TestCase):
    def setUp(self):
        parent=ROOT/'tmp'/'pipeline-tests';parent.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.out=Path(self.temp.name)
        self.manifest=self.out/(SOURCE.stem+'.current.json')
        # Preserve an existing current manifest byte-for-byte on every injected failure.
        self.manifest.write_text('{"previous":"verified drawing set"}',encoding='utf-8')
        self.old=self.manifest.read_bytes()

    def fake_native(self,python,script,args,log):
        native=Path(args[args.index('--output-dir')+1]);native.mkdir(exist_ok=True)
        if script=='prepare_generation.py':
            catalog=copy.deepcopy(DATA['catalog'])
            catalog['source_sha256']=digest(SOURCE)
            write_json(native/(SOURCE.stem+'.config.json'),bind_config(copy.deepcopy(DEFAULT),catalog))
        else:
            write_json(native/(SOURCE.stem+'.drawing.json'),REPORT)
            # A real invalid exported PDF tests the normalizer's actual parser,
            # rather than a fake "failed" flag that can accidentally be ignored.
            (native/(SOURCE.stem+'.pdf')).write_bytes(b'%PDF-1.4\ntruncated exporter output')
        return 2

    def test_failed_native_export_never_changes_previous_manifest(self):
        with patch('fastener_drawing.pipeline.native_process',side_effect=RuntimeError('injected export failure')):
            with self.assertRaisesRegex(RuntimeError,'export failure'):
                generate(SOURCE,self.out,FREECAD,PLACEHOLDER_RENDERER,fresh_config=True)
        self.assertEqual(self.manifest.read_bytes(),self.old)
        self.assertFalse((self.out/'releases').exists())
        self.assertFalse((self.out/'.generation.lock').exists())
        states=list((self.out/'runs').glob('*/pipeline.json'))
        self.assertEqual(json.loads(states[0].read_text(encoding="utf-8"))['status'],'failed_not_published')

    def test_actual_truncated_native_pdf_aborts_before_publication(self):
        with patch('fastener_drawing.pipeline.native_process',side_effect=self.fake_native):
            with self.assertRaises(Exception):
                generate(SOURCE,self.out,FREECAD,PLACEHOLDER_RENDERER,fresh_config=True)
        self.assertEqual(self.manifest.read_bytes(),self.old)
        self.assertFalse((self.out/'releases').exists())
        self.assertTrue(list((self.out/'runs').glob('*/native/*.pdf')))

    def test_failed_independent_pdf_verification_cannot_publish(self):
        native_pdf=self.out/'independent-native.pdf';fixture(native_pdf)
        fake=self.fake_native
        def worker(python,script,args,log):
            result=fake(python,script,args,log)
            if script=='generate_drawing.py':
                native=Path(args[args.index('--output-dir')+1])
                (native/(SOURCE.stem+'.pdf')).write_bytes(native_pdf.read_bytes())
            return result
        with patch('fastener_drawing.pipeline.native_process',side_effect=worker),patch('fastener_drawing.pipeline.verify_pdf',side_effect=ValueError('renderer disagreement')):
            with self.assertRaisesRegex(ValueError,'renderer disagreement'):
                generate(SOURCE,self.out,FREECAD,PLACEHOLDER_RENDERER,fresh_config=True)
        self.assertEqual(self.manifest.read_bytes(),self.old)
        self.assertFalse((self.out/'releases').exists())
        self.assertTrue(list((self.out/'runs').glob('*/normalized.pdf')))

    def test_atomic_commit_failure_leaves_old_complete_release_current(self):
        ready=self.out/'ready';ready.mkdir()
        (ready/'part.pdf').write_bytes(b'verified candidate PDF')
        (ready/'part.FCStd').write_bytes(b'verified candidate project')
        release=self.out/'releases'/'new'
        from os import replace
        def replacement(src,dest):
            if Path(dest)==self.manifest:raise PermissionError('viewer holds current manifest')
            return replace(src,dest)
        with patch('fastener_drawing.pipeline.os.replace',side_effect=replacement):
            with self.assertRaises(PermissionError):publish_release(ready,release,self.manifest,SOURCE,'test')
        self.assertEqual(self.manifest.read_bytes(),self.old)
        self.assertEqual((release/'part.pdf').read_bytes(),b'verified candidate PDF')
        self.assertFalse(list(self.out.glob('*.pending')))

    def test_successful_manifest_points_to_complete_hash_verified_set(self):
        ready=self.out/'ready';ready.mkdir()
        for name in ('part.pdf','part.FCStd','part.review.json'):(ready/name).write_bytes(name.encode())
        release=self.out/'releases'/'new'
        result=publish_release(ready,release,self.manifest,SOURCE,'test')
        self.assertEqual(json.loads(self.manifest.read_text(encoding="utf-8")),result)
        self.assertEqual(len(result['files']),3)
        for row in result['files'].values():self.assertEqual(digest(row['path']),row['sha256'])

    def test_unreadable_final_child_paths_never_commit_manifest(self):
        ready=self.out/'ready';ready.mkdir()
        for name in ('part.pdf','part.FCStd'):(ready/name).write_bytes(name.encode())
        release=self.out/'releases'/'new'
        actual=digest
        def read_digest(path):
            if Path(path).parent==release:raise FileNotFoundError('Windows final child path exceeds runtime limit')
            return actual(path)
        with patch('fastener_drawing.pipeline.digest',side_effect=read_digest):
            with self.assertRaises(FileNotFoundError):publish_release(ready,release,self.manifest,SOURCE,'test')
        self.assertEqual(self.manifest.read_bytes(),self.old)
        self.assertTrue((release/'part.pdf').exists())

    def test_existing_generation_lock_refuses_concurrent_publisher(self):
        (self.out/'.generation.lock').write_text('another live process')
        with self.assertRaises(FileExistsError):generate(SOURCE,self.out,FREECAD,PLACEHOLDER_RENDERER,fresh_config=True)
        self.assertEqual(self.manifest.read_bytes(),self.old)


if __name__=='__main__':unittest.main()
