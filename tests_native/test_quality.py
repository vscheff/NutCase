from local_samples import require_samples, samples
"""Independent geometry controls and drafting/section safety regressions."""
import json
import math
import unittest
from pathlib import Path

import FreeCAD as App
import Part

from test_analysis import analyze,moved
from test_features import discover
from test_drawing import ROOT,temporary_directory,run_generator
from fastener_drawing.orientation import view_frame
from fastener_drawing.section_material import verified_regions,verified_hatch
from fastener_drawing.comprehensive import compact_angle_anchor


def countersunk_pin():
    return Part.makeCylinder(2,24).fuse(Part.makeCone(2,5,3,App.Vector(0,0,24))).removeSplitter()


def shoulder_pin():
    shape=Part.makeCylinder(2,8).fuse(Part.makeCylinder(3.5,20,App.Vector(0,0,8))).fuse(Part.makeCylinder(6,3,App.Vector(0,0,28)))
    # Different axial structure, plus a transverse hole that must not become
    # a coaxial bore/head dimension by accident.
    return shape.cut(Part.makeCylinder(.8,10,App.Vector(-5,0,4),App.Vector(1,0,0))).removeSplitter()


def slotted_round_head():
    head=Part.makeCylinder(5,4,App.Vector(0,0,20))
    slot=Part.makeBox(12,1.4,1.2,App.Vector(-6,-.7,22.8))
    return Part.makeCylinder(2.5,20).fuse(head.cut(slot)).removeSplitter()


def grooved_dowel():
    body=Part.makeCylinder(3,35)
    groove=Part.makeCylinder(4,1.5,App.Vector(0,0,3)).cut(Part.makeCylinder(2.4,1.5,App.Vector(0,0,3)))
    return body.cut(groove).removeSplitter()


class GeometryQualityTests(unittest.TestCase):
    def test_independent_fastener_families_preserve_measured_lengths_under_rotation(self):
        for maker,length in ((countersunk_pin,27),(shoulder_pin,31),(slotted_round_head,24),(grooved_dowel,35)):
            with self.subTest(family=maker.__name__):
                original=maker();shape=moved(original)
                self.assertTrue(shape.isValid());shape.check(True)
                found=discover(shape)
                value=next(c['value'] for c in found['dimension_candidates'] if c['kind']=='overall')
                self.assertAlmostEqual(value,length,places=5)
                self.assertFalse(found['recognition_is_exhaustive'])

    def test_nested_section_material_excludes_bore_and_validates_complete_hatch_segments(self):
        # A through bore gives disjoint material regions. An enclosed void gives
        # genuinely nested section wires: its inner loop must remain a hole.
        for cavity,area_expected,regions_expected in ((Part.makeCylinder(2,18),108,2),
                (Part.makeCylinder(2,10,App.Vector(0,0,4)),140,1)):
            with self.subTest(region_count=regions_expected):
                shape=moved(Part.makeCylinder(5,18).cut(cavity))
                geometry,_=analyze(shape);frames=view_frame(geometry)
                regions,diagnostic=verified_regions(shape,frames,geometry['axis']['origin_mm'])
                self.assertAlmostEqual(regions.Area,area_expected,places=5)
                self.assertEqual(diagnostic['region_count'],regions_expected)
                if regions_expected==1:self.assertEqual(len(regions.Faces[0].Wires),2)
                hatch,checks=verified_hatch(shape,frames,geometry['axis']['origin_mm'],2)
                self.assertGreater(len(hatch.Edges),10)
                self.assertTrue(checks['complete_segments_verified'])
                self.assertLess(checks['maximum_segment_length_difference_mm'],1e-8)

    @require_samples
    def test_open_section_refuses_reconstruction_and_keeps_successful_native_case_separate(self):
        source=next((ROOT/'input').glob('*09748*.stp'));shape=Part.read(str(source))
        geometry,_=analyze(shape);frames=view_frame(geometry)
        with self.assertRaisesRegex(ValueError,'Open source section traces'):
            verified_regions(shape,frames,geometry['axis']['origin_mm'])

    def test_unresolved_axis_has_complete_diagnostic_schema(self):
        found=discover(Part.makeBox(8,8,8))
        self.assertIsNone(found['axis'])
        self.assertEqual(len(found['unmapped_faces']),6)
        self.assertEqual(found['dimension_candidates'],[])

    def test_compact_angles_use_actual_corner_and_physical_radius(self):
        class View:
            Scale=5
        # projected_point uses Source; supply it by mocking only that accessor.
        from unittest.mock import patch
        view=View();candidate={'origin_mm':[0,0,0]}
        geometry={'projected_geometry':[{'points_mm':[[1,2,0],[5,2,0]]},{'points_mm':[[5,2,0],[5,6,0]]}]}
        with patch('fastener_drawing.references.projected_point',return_value=App.Vector(0,0,0)):
            x,y=compact_angle_anchor(view,geometry,candidate,18)
        self.assertAlmostEqual(math.hypot(x-25,y-10),18,places=8)


class NewFamilyDrawingTests(unittest.TestCase):
    def test_new_independent_step_families_native_dimensioning_and_reopen(self):
        for maker,expected in ((countersunk_pin,27),(shoulder_pin,31)):
            with self.subTest(family=maker.__name__),temporary_directory() as directory:
                path=Path(directory)/(maker.__name__+'.step');moved(maker()).exportStep(str(path))
                result=run_generator(path,directory,'--dimensions')
                self.assertIn(result.returncode,(0,2),result.stdout+result.stderr)
                report=json.loads((Path(directory)/(path.stem+'.drawing.json')).read_text(encoding='utf-8'))
                created=[r for r in report['dimensions'].values() if r['status']=='created']
                overall=next(r for r in created if r['candidate']['kind']=='overall')
                self.assertAlmostEqual(overall['verification']['native_value_mm'],expected,places=5)
                self.assertTrue(report['source_sha256_verified_unchanged'])
                self.assertTrue(report['reopen_checks']['reopened_successfully'])
                self.assertFalse(report['dimensional_coverage']['dimensional_completeness_claimed'])
                self.assertFalse(any('no collision-free' in r.get('reason','') for r in report['dimensions'].values()))


if __name__=='__main__':unittest.main()
