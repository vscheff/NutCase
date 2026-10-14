import copy
import json
import tempfile
import unittest
from pathlib import Path

from fastener_gui.state import ROOT, ConfigStore, ModelState, completion_status, read_json
from fastener_gui.outputs import load_release, load_history, history_entries, export_copy

from fixture import MANIFEST,TEST_TEMP,RELEASE,SOURCE,CATALOG,ANALYSIS


def model():
    state=ModelState();state.accept_analysis(SOURCE,copy.deepcopy(CATALOG),copy.deepcopy(ANALYSIS))
    return state


class StateTests(unittest.TestCase):
    def test_source_bound_selection_and_roundtrip(self):
        state=model();state.config['dimensioning']['mode']='custom'
        identity=CATALOG['candidates'][0]['stable_id'];state.set_selected(identity,True)
        with tempfile.TemporaryDirectory(dir=TEST_TEMP) as directory:
            store=ConfigStore(directory);store.save(SOURCE,state.checked_config())
            self.assertEqual(store.load(SOURCE),state.checked_config())
            self.assertTrue(all(x.startswith('g1-') for x in state.config['dimensioning']['include']))
            restored=model();restored.accept_analysis(SOURCE,CATALOG,ANALYSIS,store.load(SOURCE))
            self.assertEqual(sum(x['selected'] for x in restored.decisions().values()),1)

    def test_suppression_remains_explicit(self):
        state=model();key=CATALOG['candidates'][0]['stable_id'];state.set_selected(key,False)
        self.assertFalse(state.decisions()[CATALOG['candidates'][0]['candidate_id']]['selected'])
        state.set_selected(key,True)
        self.assertNotIn(key,state.config['dimensioning']['exclude'])

    def test_unknown_identity_is_not_remapped_by_equal_value(self):
        state=model()
        with self.assertRaises(ValueError):state.set_selected('g1-missing',True)

    def test_changed_source_preserves_policy_and_requires_explicit_fresh_start(self):
        original=model().checked_config();catalog=copy.deepcopy(CATALOG);catalog['geometry_id']='changed'
        state=ModelState();state.accept_analysis(SOURCE,catalog,ANALYSIS,original)
        self.assertEqual(state.config,original)
        with self.assertRaisesRegex(ValueError,'incompatible'):state.checked_config()
        state.fresh_configuration();self.assertEqual(state.config['source_binding']['geometry_id'],'changed')

    def test_replacing_policy_retains_readable_history(self):
        state=model()
        with tempfile.TemporaryDirectory(dir=TEST_TEMP) as directory:
            store=ConfigStore(directory);path=store.save(SOURCE,state.checked_config());old=path.read_bytes()
            state.config['dimensioning']['mode']='basic';store.save(SOURCE,state.checked_config())
            history=list(path.parent.joinpath('history').glob('*.json'))
            self.assertEqual(len(history),1);self.assertEqual(json.loads(history[0].read_bytes()),json.loads(old))

    def test_explicit_fresh_save_preserves_corrupt_old_configuration_bytes(self):
        with tempfile.TemporaryDirectory(dir=TEST_TEMP) as directory:
            store=ConfigStore(directory);path=store.save(SOURCE,model().checked_config())
            path.write_bytes(b'{invalid saved json')
            with self.assertRaises(ValueError):store.load(SOURCE)
            store.save(SOURCE,model().checked_config())
            self.assertEqual(next(path.parent.joinpath('history').glob('*.json')).read_bytes(),b'{invalid saved json')

    def test_backend_exit_codes(self):
        result={'status':'published_preliminary'}
        self.assertIn('Completed',completion_status(0,result))
        self.assertIn('Completed',completion_status(2,result))
        self.assertIn('Review',completion_status(2,result))
        self.assertIn('Failed',completion_status(1,result))
        self.assertIn('Cancelled',completion_status(3,None))
        self.assertIn('Failed',completion_status(0,None))


class OutputTests(unittest.TestCase):
    def test_current_release_and_preview_are_normalized_published_artifacts(self):
        result=load_release(MANIFEST,SOURCE,RELEASE['manifest']['run_id'])
        self.assertEqual(result['pdf_audit']['status'],'passed')
        self.assertTrue(Path(result['pdf']).is_relative_to(result['directory']))
        self.assertNotIn('/native/',result['pdf'].replace('\\','/'))

    def test_another_run_cannot_be_shown_as_new_result(self):
        with self.assertRaisesRegex(ValueError,'stale preview'):load_release(MANIFEST,SOURCE,'not-this-run')

    def test_invalid_or_missing_output_paths(self):
        from fastener_gui.outputs import validate_release
        for modification in ('missing','outside','checksum'):
            record=copy.deepcopy(RELEASE['manifest'])
            key=Path(RELEASE['pdf']).name
            if modification=='missing':del record['files'][key]
            elif modification=='outside':record['files'][key]['path']=str(ROOT/'input'/'missing.pdf')
            else:record['files'][key]['sha256']='bad'
            with self.assertRaises(ValueError):validate_release(record,MANIFEST.parent,SOURCE)

    def test_historical_selection_validates_same_artifacts(self):
        entries=history_entries(MANIFEST.parent,SOURCE);self.assertTrue(entries)
        result=load_history(entries[0][1],MANIFEST.parent,SOURCE)
        self.assertTrue(Path(result['pdf']).exists())

    def test_save_as_preserves_release_and_verifies_copy(self):
        from fastener_gui.outputs import sha256
        with tempfile.TemporaryDirectory(dir=TEST_TEMP) as directory:
            for key,suffix in [('pdf','.pdf'),('project','.FCStd')]:
                copied=export_copy(RELEASE,key,Path(directory)/('export'+suffix))
                self.assertEqual(sha256(copied),sha256(RELEASE[key]))
        with self.assertRaises(ValueError):export_copy(RELEASE,'pdf',RELEASE['pdf'])
        with self.assertRaises(ValueError):export_copy(RELEASE,'pdf',SOURCE)


if __name__=='__main__':unittest.main()
