from local_samples import require_samples, samples
"""Feature selection and actual native section/dimension/persistence regressions."""
import json
import unittest
from pathlib import Path

import FreeCAD as App
import Part

from fastener_analysis.importer import sha256
from fastener_drawing.layout import comprehensive_layout
from fastener_drawing.orientation import native_projected_envelope,view_frame
from fastener_drawing.sections import section_geometry
from fastener_drawing.selection import Selection
from test_analysis import moved,analyze
from test_features import discover,stepped_hollow
from test_drawing import ROOT,run_generator,temporary_directory


class SelectionTests(unittest.TestCase):
    def test_native_locus_checks_reject_wrong_centers_and_parallel_offsets(self):
        from fastener_drawing.dimensions import same_circle_locus,same_straight_locus
        circle={"curve_type":"Circle","center_mm":[0,0,0],"radius_mm":3}
        self.assertFalse(same_circle_locus(circle,{**circle,"center_mm":[1,0,0]}))
        self.assertFalse(same_circle_locus(circle,{**circle,"radius_mm":4}))
        line={"points_mm":[[0,0,0],[1,0,0],[2,0,0]],"length_mm":2}
        self.assertTrue(same_straight_locus(line,{"points_mm":[[.5,0,0],[1,0,0]],"length_mm":.5}))
        self.assertFalse(same_straight_locus(line,{"points_mm":[[0,1,0],[2,1,0]],"length_mm":2}))
        self.assertFalse(same_straight_locus(line,{"points_mm":[[0,0,0],[1,1,0],[2,0,0]],"length_mm":2}))

    def test_corner_offset_dedup_requires_the_actual_tangent_polygon(self):
        import math
        fillet={"id":"f","type":"repeated_fillet","tangent_plane_ids":[1,2]}
        polygon={"id":"p","source_faces":[3,4,5,6,7,8],"measured_geometry":{"side_count":6}}
        selection=Selection({"features":[fillet,polygon]})
        selection.accept({"id":"r","feature_id":"f","kind":"radius","value":.5})
        selection.accept({"id":"af","feature_id":"p","kind":"across_flats","value":10})
        c={"feature_id":"f","kind":"radial_offset","value":4.5/math.cos(math.pi/6)}
        self.assertIsNone(selection.reason(c))
        polygon["source_faces"]=[1,2,3,4,5,6]
        self.assertIsNotNone(selection.reason(c))

    def test_cone_rim_dedup_rejects_an_offset_cylinder_with_equal_diameter(self):
        region={"id":"c","coaxial":False,"measured_geometry":{"axial_range_mm":[0,2]}}
        selection=Selection({"features":[region]})
        selection.accept({"id":"d","feature_id":"c","kind":"diameter","value":6})
        self.assertIsNone(selection.reason({"kind":"curve_diameter","value":6,"station_mm":2}))

    def test_axial_selection_is_spanning_baselines_not_closed_chain(self):
        found=discover(stepped_hollow())
        selected=Selection(found);accepted=[];rejected=[]
        for c in sorted(found['dimension_candidates'],key=lambda c:-c['priority']):
            if c['verification_status']!='source_measured':continue
            reason=selected.reason(c)
            if reason:rejected.append((c,reason))
            else:selected.accept(c);accepted.append(c)
        axial=[c for c in accepted if c['kind'] in ('overall','axial_distance')]
        nodes={s['id'] for c in axial for s in c['source_supports']}
        self.assertEqual(len(axial),len(nodes)-1)
        self.assertTrue(any(c['label']=='Body length below flange' for c,_ in rejected))
        self.assertTrue(any('chain' in reason for _,reason in rejected))

    def test_equal_diameter_and_flats_are_distinct_measurements(self):
        found={'features':[]};selection=Selection(found)
        c={'kind':'diameter','value':10,'source_supports':[]}
        selection.accept(c)
        self.assertIsNone(selection.reason({'kind':'across_flats','value':10,'source_supports':[]}))

    def test_source_plane_intersection_is_native_and_unmodified(self):
        shape=moved(stepped_hollow())
        geometry,_=analyze(shape);frames=view_frame(geometry);before=shape.exportBrepToString()
        cut,checks=section_geometry(shape,frames,geometry['axis']['origin_mm'])
        self.assertTrue(cut.isValid())
        self.assertGreater(checks['closed_loop_count'],0)
        self.assertEqual(before,shape.exportBrepToString())
        self.assertFalse(checks['source_healed'])

    def test_expanded_layout_reserves_axial_lanes_and_can_enlarge(self):
        shape=moved(stepped_hollow());geometry,_=analyze(shape);frames=view_frame(geometry);found=discover(shape)
        envelopes={r:native_projected_envelope(shape,f) for r,f in frames['frames'].items()}
        envelopes['section']=envelopes['longitudinal']
        layout=comprehensive_layout(envelopes,found)
        self.assertTrue(layout['dimension_lanes_reserved'])
        self.assertIn('section',layout['positions'])
        self.assertGreaterEqual(layout['scale'],2)
        self.assertGreater(layout['dimension_top_lane_mm'],25)


class ComprehensiveIntegrationTests(unittest.TestCase):
    def test_rotated_hollow_steps_known_measurements_native_section_and_reopen(self):
        with temporary_directory() as directory:
            source=Path(directory)/'independent stepped hollow.step'
            moved(stepped_hollow(2.5)).exportStep(str(source));before=sha256(source)
            result=run_generator(source,directory,'--dimensions','--dimension-scope','comprehensive')
            self.assertIn(result.returncode,(0,2),result.stdout+result.stderr)
            report=json.loads((Path(directory)/(source.stem+'.drawing.json')).read_text(encoding='utf-8'))
            self.assertEqual(report['operation'],'comprehensive_dimensioning')
            self.assertEqual(report['reopen_checks']['native_view_count'],5)
            placed=[r for r in report['dimensions'].values() if r['status']=='created']
            diameters=sorted(round(r['verification']['native_value_mm'],5) for r in placed if r['candidate']['kind']=='diameter')
            self.assertEqual(diameters,[4,6,8,12,20])
            self.assertAlmostEqual(next(r['verification']['native_value_mm'] for r in placed if r['candidate']['kind']=='overall'),22.5,places=5)
            self.assertGreaterEqual(len(placed),8)
            for key,r in report['reopen_checks']['dimension_checks'].items():
                self.assertTrue(r['geometry_fingerprint_verified'],key)
                self.assertTrue(r['source_measurement_repeated'],key)
                self.assertFalse(r['arbitrary_value_override'],key)
            self.assertFalse(report['dimensional_coverage']['dimensional_completeness_claimed'])
            self.assertTrue(report['native_render_checks']['no_raster_images_in_native_scene'])
            self.assertTrue(all(c['text_no_collision_or_clipping'] for c in report['dimension_placement_checks'].values()))
            self.assertEqual(before,sha256(source))

    @require_samples
    def test_supplied_models_increase_coverage_and_report_unresolved(self):
        with temporary_directory() as directory:
            for sample,minimum in zip(samples(),(11,23)):
                before=sha256(sample)
                result=run_generator(sample,directory,'--dimensions','--dimension-scope','comprehensive')
                self.assertEqual(result.returncode,2,result.stdout+result.stderr)
                r=json.loads((Path(directory)/(sample.stem+'.drawing.json')).read_text(encoding='utf-8'))
                self.assertGreaterEqual(r['reopen_checks']['dimension_count'],minimum)
                self.assertTrue(r['unresolved_dimensions'])
                self.assertTrue(all(v.get('reason') for v in r['dimensions'].values() if v['status']!='created'))
                self.assertEqual(before,sha256(sample))
                self.assertNotEqual(r['source_analysis']['validation']['boolean_check']['status'],'passed')
                self.assertEqual(r['layout']['sheet'],'ANSI-B')
                self.assertEqual(r['layout']['scale'],2)
                self.assertEqual(r['reopen_checks']['native_drafting_centerlines_verified'],6)
                hatch=r['section_diagnostics']['hatching']
                if '13125' in sample.name:
                    self.assertEqual(hatch['status'],'verified_geometry_hatch_rendered')
                    self.assertTrue(hatch['complete_segments_verified'])
                    self.assertEqual(r['reopen_checks']['native_view_count'],6)
                    positions=r['layout']['positions']
                    profile_top=positions['opening_detail']['y_mm']+positions['opening_detail']['expected_height_mm']/2
                    self.assertGreaterEqual(positions['right_end']['label_y_mm']-profile_top,8-1e-8)
                    self.assertTrue(r['reopen_checks']['hatch_material_recheck']['native_view_alignment_direction_and_scale_verified'])
                    angles=[v for v in r['dimensions'].values() if v['status']=='created' and v['candidate']['kind']=='plane_angle']
                    self.assertEqual(len(angles),2)
                    self.assertTrue(all(v['view_role']=='opening_detail' for v in angles))
                else:self.assertEqual(hatch['status'],'native_hatch_strokes_rendered')


if __name__=='__main__':unittest.main()
