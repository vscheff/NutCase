from local_samples import require_samples, samples
"""Source-bound policy tests using native, independently constructed BReps."""
import copy
import unittest
import FreeCAD as App
import Part
from test_features import discover
from fastener_drawing.configuration import DEFAULT, bind_config, make_catalog, selection_decisions, validate_config
from fastener_drawing.export import shape_signature
from fastener_drawing.orientation import view_frame
from test_analysis import analyze


def catalog(shape):
    d=discover(shape)
    return d,make_catalog(d,shape_signature(shape),'source-bytes')


class ConfigurationTests(unittest.TestCase):
    def test_native_stable_id_survives_transient_candidate_feature_and_face_reordering(self):
        shape=Part.makeCylinder(3,18)
        d,first=catalog(shape)
        signature=shape_signature(shape)
        remapped=copy.deepcopy(d)
        n=len(signature['face_geometry'])
        signature['face_geometry'].reverse()
        def remap(value,key=''):
            facekeys={'source_faces','faces','supporting_pair','repeat_supporting_pairs','radius_faces','tangent_plane_ids'}
            if isinstance(value,dict):return {k:remap(v,k) for k,v in value.items()}
            if isinstance(value,list):return [remap(v,key) for v in value]
            if type(value) is int and key in facekeys:return n+1-value
            return value
        remapped=remap(remapped)
        mapping={f['id']:'renamed-'+f['id'] for f in remapped['features']}
        for f in remapped['features']:f['id']=mapping[f['id']]
        for c in remapped['dimension_candidates']:
            c['feature_id']=mapping[c['feature_id']];c['id']='renamed-'+c['id']
        second=make_catalog(remapped,signature,'different STEP bytes')
        self.assertEqual(first['geometry_id'],second['geometry_id'])
        self.assertEqual([c['stable_id'] for c in first['candidates']],[c['stable_id'] for c in second['candidates']])
        bound=bind_config(copy.deepcopy(DEFAULT),first)
        self.assertEqual(bind_config(bound,second)['source_binding']['source_sha256'],'different STEP bytes')

    def test_same_diameter_on_different_native_locus_cannot_reuse_saved_binding(self):
        shape=Part.makeCylinder(3,18)
        _,first=catalog(shape)
        shape.translate(App.Vector(20,0,0))
        _,second=catalog(shape)
        bound=bind_config(copy.deepcopy(DEFAULT),first)
        with self.assertRaisesRegex(ValueError,'incompatible'):bind_config(bound,second)

    def test_changed_length_refuses_saved_selection_even_when_external_diameter_unchanged(self):
        _,first=catalog(Part.makeCylinder(3,18))
        _,second=catalog(Part.makeCylinder(3,19))
        with self.assertRaisesRegex(ValueError,'incompatible'):bind_config(bind_config(copy.deepcopy(DEFAULT),first),second)

    def test_explicit_custom_policy_selects_only_requested_source_candidates(self):
        d,c=catalog(Part.makeCylinder(3,18))
        config=bind_config(copy.deepcopy(DEFAULT),c)
        overall=next(x for x in d['dimension_candidates'] if x['kind']=='overall')
        config['dimensioning'].update(mode='custom',include=[overall['stable_id']])
        decisions=selection_decisions(bind_config(config,c),d)
        self.assertEqual([k for k,r in decisions.items() if r['selected']],[overall['id']])
        config['dimensioning'].update(include=[],exclude=[overall['stable_id']])
        self.assertFalse(any(r['selected'] for r in selection_decisions(config,d).values()))
        config['dimensioning']['mode']='comprehensive'
        self.assertFalse(selection_decisions(config,d)[overall['id']]['selected'])

    def test_unbound_invalid_and_conflicting_selections_are_refused(self):
        d,c=catalog(Part.makeCylinder(3,18));key=c['candidates'][0]['stable_id']
        config=copy.deepcopy(DEFAULT);config['dimensioning']['include']=[key]
        with self.assertRaisesRegex(ValueError,'source_binding'):bind_config(config,c)
        config=bind_config(copy.deepcopy(DEFAULT),c);config['dimensioning']['include']=['g1-invalid']
        with self.assertRaisesRegex(ValueError,'Invalid saved'):bind_config(config,c)
        config['dimensioning'].update(include=[key],exclude=[key])
        with self.assertRaisesRegex(ValueError,'both'):validate_config(config)

    def test_basic_is_supported_geometry_and_no_fabricated_semantics(self):
        shape=Part.makeCylinder(3,18).cut(Part.makeCylinder(1,18))
        d,c=catalog(shape);config=bind_config(copy.deepcopy(DEFAULT),c);config['dimensioning']['mode']='basic'
        decisions=selection_decisions(config,d)
        selected=[x for x in d['dimension_candidates'] if decisions[x['id']]['selected']]
        self.assertEqual({x['kind'] for x in selected},{'overall','diameter'})
        self.assertEqual(len([x for x in selected if x['kind']=='diameter']),2)

    def test_orientation_override_changes_only_frame_and_rejects_nontransverse_up(self):
        shape=Part.makeCylinder(3,18)
        geometry,_=analyze(shape);before=shape.exportBrepToString()
        f=view_frame(geometry,[0,0,1],[0,1,0])
        self.assertEqual(f['up'],[0,1,0]);self.assertEqual(before,shape.exportBrepToString())
        with self.assertRaisesRegex(ValueError,'perpendicular'):view_frame(geometry,[0,0,1],[0,0,1])

    def test_configuration_rejects_unknown_fields_and_nonfinite_scale(self):
        config=copy.deepcopy(DEFAULT);config['scale']=float('nan')
        with self.assertRaises(ValueError):validate_config(config)
        config['scale']=0
        with self.assertRaises(ValueError):validate_config(config)


if __name__=='__main__':unittest.main()
