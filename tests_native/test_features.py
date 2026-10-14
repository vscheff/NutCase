from local_samples import require_samples, samples
"""Independent native reference geometry for generalized feature discovery."""
import unittest
import FreeCAD as App
import Part
from fastener_analysis.features import discover_features
from fastener_analysis.importer import validate_shape
from test_analysis import analyze, moved, hex_prism


def discover(shape):
    g,r=analyze(shape)
    return discover_features(shape,g,r,validate_shape(shape))


def stepped_hollow(flange_thickness=2):
    outer=Part.makeCylinder(4,8).fuse(Part.makeCylinder(6,12,App.Vector(0,0,8))).fuse(Part.makeCylinder(10,flange_thickness,App.Vector(0,0,20)))
    inner=Part.makeCylinder(2,10).fuse(Part.makeCylinder(3,12+flange_thickness,App.Vector(0,0,10)))
    return outer.cut(inner).removeSplitter()


class FeatureDiscoveryTests(unittest.TestCase):
    def test_irregular_opening_groups_proved_equal_wall_spacings(self):
        import math
        angles=[0,55,125,180,235,305]
        normals=[(math.cos(math.radians(a)),math.sin(math.radians(a))) for a in angles]
        corners=[]
        for (a,b),(c,d) in zip(normals,normals[1:]+normals[:1]):
            determinant=a*d-b*c
            corners.append(App.Vector(5*(d-b)/determinant,5*(a-c)/determinant,-1))
        wire=Part.makePolygon(corners+[corners[0]])
        hole=Part.Face(wire).extrude(App.Vector(0,0,14))
        found=discover(moved(Part.makeCylinder(9,12).cut(hole)))
        candidates=[c for c in found['dimension_candidates'] if c['kind']=='plane_gap']
        self.assertEqual(len(candidates),1)
        self.assertEqual(candidates[0]['repeat_count'],3)
        self.assertEqual(len(candidates[0]['repeat_supporting_pairs']),3)
        self.assertAlmostEqual(candidates[0]['value'],10,places=5)
        self.assertFalse(any(f['type']=='polygonal_region' and f.get('boundary_side')=='internal' for f in found['features']))
        angles=[c['value'] for c in found['dimension_candidates'] if c['kind']=='plane_angle']
        self.assertEqual(sorted(round(a,5) for a in angles),[125,125])

    def test_multiple_external_and_internal_steps_measured_independently(self):
        found=discover(stepped_hollow())
        values=[c['value'] for c in found['dimension_candidates'] if c['kind']=='diameter']
        self.assertEqual(sorted(round(v,5) for v in values),[4,6,8,12,20])
        self.assertAlmostEqual(next(c['value'] for c in found['dimension_candidates'] if c['kind']=='overall'),22,places=6)
        self.assertFalse(found['recognition_is_exhaustive'])

    def test_variable_flange_thickness_is_not_cylinder_radius_or_nominal_size(self):
        for t in (.8,2,3.25):
            found=discover(stepped_hollow(t))
            self.assertAlmostEqual(next(c['value'] for c in found['dimension_candidates'] if c['label']=='Flange total thickness'),t,places=5)

    def test_rotation_translation_preserve_feature_dimensions(self):
        first=discover(stepped_hollow())
        second=discover(moved(stepped_hollow()))
        for kind in ('overall','diameter','axial_distance'):
            a=sorted(round(c['value'],5) for c in first['dimension_candidates'] if c['kind']==kind)
            b=sorted(round(c['value'],5) for c in second['dimension_candidates'] if c['kind']==kind)
            self.assertEqual(a,b)

    def test_non_circular_terminal_opening_is_not_forced_to_bore(self):
        shape=Part.makeCylinder(10,2).fuse(Part.makeCylinder(7,20,App.Vector(0,0,2))).cut(hex_prism(6,22,0))
        found=discover(shape)
        self.assertTrue(any(f['type']=='noncircular_terminal_opening' for f in found['features']))
        self.assertTrue(any(c['kind']=='opening_extent' for c in found['dimension_candidates']))
        self.assertFalse(any(c['kind']=='diameter' and c['label']=='Internal bore diameter' for c in found['dimension_candidates']))

    def test_conical_transition_keeps_measured_angle_and_axial_extent(self):
        shape=Part.makeCylinder(4,8).fuse(Part.makeCone(4,6,2,App.Vector(0,0,8))).fuse(Part.makeCylinder(6,10,App.Vector(0,0,10)))
        found=discover(shape)
        angle=next(c for c in found['dimension_candidates'] if c['kind']=='cone_angle')
        self.assertAlmostEqual(angle['value'],90,places=5)
        extent=next(c for c in found['dimension_candidates'] if c['label']=='Conical transition axial extent')
        self.assertAlmostEqual(extent['value'],2,places=5)

    def test_annular_recess_has_known_width_and_depth(self):
        outer=Part.makeCylinder(5,30)
        ring=Part.makeCylinder(6,3,App.Vector(0,0,10)).cut(Part.makeCylinder(4,3,App.Vector(0,0,10)))
        found=discover(outer.cut(ring).removeSplitter())
        recess=next(f for f in found['features'] if f['type']=='annular_reduced_region')
        self.assertAlmostEqual(recess['measured_geometry']['axial_width_mm'],3,places=6)
        self.assertAlmostEqual(recess['measured_geometry']['radial_depth_mm'],1,places=6)

    def test_native_toroidal_fillet_radius(self):
        shape=Part.makeCylinder(5,12)
        rim=next(e for e in shape.Edges if isinstance(e.Curve,Part.Circle) and e.Curve.Center.z>11)
        filleted=shape.makeFillet(.5,[rim])
        found=discover(filleted)
        self.assertTrue(any(c['kind']=='torus_radius' and abs(c['value']-.5)<1e-6 for c in found['dimension_candidates']))

    def test_nonconcentric_bore_is_not_coaxial_diameter(self):
        shape=Part.makeCylinder(10,25).cut(Part.makeCylinder(2,25,App.Vector(3,0,0)))
        found=discover(shape)
        offsets=[f for f in found['features'] if f['type']=='offset_cylindrical_patch' and f['complete_circumference']]
        self.assertTrue(offsets)
        self.assertTrue(any(c['kind']=='radial_offset' for c in found['dimension_candidates']))


if __name__=='__main__':unittest.main()
