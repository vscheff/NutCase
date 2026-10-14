"""Release-gate adversarial cases; no approval by regenerating a manifest."""
import copy
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('licensing_verify',ROOT/'packaging/licensing/verify.py')
verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)


class LicensingGateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'build')
        self.root=Path(self.temp.name);self.bundle=self.root/'bundle';self.bundle.mkdir()
        self.materials=self.root/'materials';self.materials.mkdir()
        (self.bundle/'reviewed.dll').write_bytes(b'reviewed native content')
        (self.bundle/'LICENSE.txt').write_text('copyright and complete terms')
        self.review={'schema_version':1,'files':[{'path':p.name,'sha256':verify.sha256(p),
            'component':'test-runtime','provenance':[{'archive':'pinned upstream package'}]} for p in self.bundle.iterdir()],
            'components':[{'id':'test-runtime','status':'VERIFIED','evidence':['reviewed package/hash/source mapping'],
                           'notice_files':['LICENSE.txt']}],'materials':[],'obligations':[]}

    def tearDown(self):self.temp.cleanup()

    def findings(self):return verify.verify(self.bundle,self.review,self.materials)

    def codes(self):return {row['code'] for row in self.findings()}

    def test_reviewed_fixture_passes(self):
        self.assertTrue(all(f['status']=='VERIFIED' for f in self.findings()))

    def test_unknown_pe_with_unusual_extension_is_rejected(self):
        (self.bundle/'unexpected.dat').write_bytes(b'MZunknown executable')
        self.assertIn('unexpected_file',self.codes())

    def test_modified_reviewed_binary_is_rejected(self):
        (self.bundle/'reviewed.dll').write_bytes(b'new version')
        self.assertIn('changed_file',self.codes())

    def test_missing_notice_is_rejected(self):
        (self.bundle/'LICENSE.txt').unlink()
        self.assertIn('missing_file',self.codes())

    def test_human_decision_stays_a_release_blocker(self):
        self.review['obligations']=[{'id':'authorization','status':'REQUIRES HUMAN/LEGAL REVIEW','detail':'Owner rights unresolved'}]
        self.assertEqual(self.findings()[0]['status'],'REQUIRES HUMAN/LEGAL REVIEW')

    def test_supplemental_evidence_requires_explicit_root(self):
        self.review['supplemental_materials']=[{'path':'build.json','sha256':'0'*64}]
        self.assertIn('missing_material_root',self.codes())

    def test_changed_supplemental_build_evidence_is_rejected(self):
        evidence=self.root/'evidence';evidence.mkdir();path=evidence/'build.json';path.write_text('reviewed build')
        self.review['supplemental_materials']=[{'path':'build.json','sha256':verify.sha256(path)}]
        path.write_text('different build')
        findings=verify.verify(self.bundle,self.review,self.materials,supplemental_materials=evidence)
        self.assertIn('changed_material',{f['code'] for f in findings})

    def test_reviewed_supplemental_build_evidence_passes(self):
        evidence=self.root/'evidence';evidence.mkdir();path=evidence/'build.json';path.write_text('reviewed build')
        self.review['supplemental_materials']=[{'path':'build.json','sha256':verify.sha256(path)}]
        self.assertTrue(all(f['status']=='VERIFIED' for f in verify.verify(
            self.bundle,self.review,self.materials,supplemental_materials=evidence)))

    def test_license_only_archive_cannot_satisfy_source_obligation(self):
        archive=self.materials/'sources.zip'
        with zipfile.ZipFile(archive,'w') as stream:
            stream.writestr('LICENSE','terms');stream.writestr('README','not source')
        self.review['materials']=[{'path':'sources.zip','sha256':verify.sha256(archive),'role':'corresponding-source',
            'completeness_evidence':'reviewed complete source','required_members':['LICENSE'],'source_members':['src/runtime.c']}]
        self.assertIn('source_members_missing',self.codes())

    def test_source_without_completeness_review_is_rejected(self):
        archive=self.materials/'sources.zip'
        with zipfile.ZipFile(archive,'w') as stream:stream.writestr('LICENSE','terms')
        self.review['materials']=[{'path':'sources.zip','sha256':verify.sha256(archive),'role':'corresponding-source'}]
        self.assertIn('source_completeness_unreviewed',self.codes())

    def test_corrupt_and_missing_source_are_rejected(self):
        self.review['materials']=[{'path':'source.zip','sha256':'0'*64,'role':'corresponding-source'}]
        self.assertIn('missing_material',self.codes())
        (self.materials/'source.zip').write_bytes(b'invalid archive')
        self.review['materials'][0]['sha256']=verify.sha256(self.materials/'source.zip')
        self.assertIn('source_archive_invalid',self.codes())

    def test_unsupported_verification_is_rejected(self):
        self.review['components'][0]['evidence']=[]
        self.assertIn('unsupported_verification',self.codes())

    def test_installer_change_requires_new_payload_review(self):
        installer=self.root/'setup.exe';installer.write_bytes(b'changed installer')
        self.review['installer']={'sha256':'0'*64}
        findings=verify.verify(self.bundle,self.review,self.materials,installer)
        self.assertIn('installer_changed',{f['code'] for f in findings})

    def test_manifest_cannot_escape_materials_directory(self):
        self.review['materials']=[{'path':'../outside.zip','sha256':'0'*64}]
        with self.assertRaisesRegex(ValueError,'Unsafe manifest path'):self.findings()

    def test_generated_installer_runtime_cannot_be_silently_replaced(self):
        runtime=self.bundle/'unins000.exe';runtime.write_bytes(b'exact generated runtime')
        self.review['installer_generated_files']=[{'path':runtime.name,'sha256':verify.sha256(runtime)}]
        self.assertNotIn('unexpected_file',self.codes())
        runtime.write_bytes(b'different runtime')
        self.assertIn('generated_runtime_changed',self.codes())

    def test_required_notice_must_belong_to_reviewed_inventory(self):
        self.review['components'][0]['notice_files'].append('not-reviewed.txt')
        self.assertIn('notice_unreviewed',self.codes())


if __name__=='__main__':unittest.main()
