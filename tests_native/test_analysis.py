from local_samples import require_samples, samples
"""Native-kernel regression tests with known geometry, not mocked measurements."""
import contextlib
import io
import json
import math
import tempfile
import unittest
from pathlib import Path

import FreeCAD as App
import Part

from fastener_analysis.cli import build_report, main
from fastener_analysis.export import write_json
from fastener_analysis.geometry import analyze_geometry, comparison_tolerance, face_inventory
from fastener_analysis.importer import sha256, validate_shape
from fastener_analysis.recognition import detect_threads, recognize_features


def analyze(shape):
    if shape.ShapeType != "Solid" and len(shape.Solids) == 1:
        shape = shape.Solids[0]
    geometry, _ = analyze_geometry(shape)
    return geometry, recognize_features(shape, geometry, validate_shape(shape))


def hex_prism(across_flats, height, z):
    radius = across_flats / math.sqrt(3)
    points = [App.Vector(radius * math.cos(i * math.pi / 3), radius * math.sin(i * math.pi / 3), z) for i in range(6)]
    points.append(points[0])
    return Part.Face(Part.makePolygon(points)).extrude(App.Vector(0, 0, height))


def hex_bolt():
    return Part.makeCylinder(2.5, 20).fuse(hex_prism(10, 4, 20)).removeSplitter()


def moved(shape):
    result = shape.copy()
    result.rotate(App.Vector(), App.Vector(1, 2, -3), 73)
    result.translate(App.Vector(1500, -400, 1100))
    return result


def threaded_shaft():
    # Triangular helical groove in a continuous cylindrical shaft, six revolutions.
    helix = Part.makeHelix(1.5, 9, 5)
    helix.translate(App.Vector(0, 0, 1.5))
    points = [App.Vector(4.4, 0, 1.5), App.Vector(5.3, 0, 1.1),
              App.Vector(5.3, 0, 1.9), App.Vector(4.4, 0, 1.5)]
    cutter = Part.Wire(helix.Edges).makePipeShell([Part.Wire(Part.makePolygon(points).Edges)], True, True)
    return Part.makeCylinder(5, 12).cut(cutter)


class GeometryTests(unittest.TestCase):
    def test_rotated_translated_pin_extent_uses_intrinsic_axis(self):
        geometry, recognition = analyze(moved(Part.makeCylinder(3, 40)))
        self.assertEqual(geometry["axis"]["status"], "identified")
        self.assertAlmostEqual(recognition["dimensions"]["overall_length"]["value_mm"], 40, places=5)
        self.assertAlmostEqual(geometry["cylindrical_bands"][0]["diameter_mm"], 6, places=5)
        self.assertNotAlmostEqual(geometry["global_bounding_box"]["dimensions_mm"][2], 40, places=2)

    def test_hex_bolt_dimensions_have_independent_known_values(self):
        _, report = analyze(hex_bolt())
        expected = {"overall_length": 24, "length_under_head": 20, "head_height": 4,
                    "shank_diameter": 5, "across_flats": 10}
        for name, value in expected.items():
            self.assertEqual(report["dimensions"][name]["status"], "recognized", name)
            self.assertAlmostEqual(report["dimensions"][name]["value_mm"], value, places=5)
        self.assertIsNone(report["dimensions"]["head_diameter"]["value_mm"])

    def test_hex_bolt_recognition_survives_arbitrary_orientation(self):
        _, baseline = analyze(hex_bolt())
        _, rotated = analyze(moved(hex_bolt()))
        for name, dimension in baseline["dimensions"].items():
            self.assertEqual(dimension["status"], rotated["dimensions"][name]["status"], name)
            if dimension["value_mm"] is not None:
                self.assertAlmostEqual(dimension["value_mm"], rotated["dimensions"][name]["value_mm"], places=5, msg=name)

    def test_circular_head_has_geometry_supported_diameter(self):
        shape = Part.makeCylinder(2.5, 20).fuse(Part.makeCylinder(5, 4, App.Vector(0, 0, 20))).removeSplitter()
        _, report = analyze(moved(shape))
        self.assertAlmostEqual(report["dimensions"]["head_diameter"]["value_mm"], 10, places=5)
        self.assertEqual(report["dimensions"]["flange_diameter"]["status"], "unrecognized")

    def test_hollow_hex_body_does_not_become_a_bolt(self):
        shape = hex_bolt().cut(Part.makeCylinder(1, 30, App.Vector(0, 0, -1)))
        geometry, report = analyze(shape)
        self.assertAlmostEqual(geometry["hexagonal_regions"][0]["across_flats_mm"], 10, places=5)
        for name in ("length_under_head", "head_height", "head_diameter", "shank_diameter", "across_flats"):
            self.assertEqual(report["dimensions"][name]["status"], "unrecognized", name)

    def test_smooth_bore_is_not_a_thread_size(self):
        shape = Part.makeCylinder(5, 15).cut(Part.makeCylinder(3, 15))
        geometry, report = analyze(shape)
        bore = next(b for b in geometry["cylindrical_bands"] if b["boundary_side"] == "internal")
        self.assertEqual(bore["diameter_mm"], 6)
        self.assertEqual(report["threads"]["status"], "cannot_determine")
        self.assertIsNone(report["dimensions"]["thread_major_diameter"]["value_mm"])
        self.assertIsNone(report["dimensions"]["threaded_length"]["value_mm"])

    def test_terminal_annular_flange(self):
        shape = Part.makeCylinder(4, 12).fuse(Part.makeCylinder(8, 1, App.Vector(0, 0, 12)))
        shape = shape.cut(Part.makeCylinder(2, 13)).removeSplitter()
        _, report = analyze(moved(shape))
        self.assertAlmostEqual(report["dimensions"]["flange_diameter"]["value_mm"], 16, places=5)

    def test_plain_washer_has_no_invented_head_or_flange(self):
        shape = Part.makeCylinder(8, 1).cut(Part.makeCylinder(3, 1))
        _, report = analyze(shape)
        self.assertEqual(report["dimensions"]["flange_diameter"]["status"], "unrecognized")
        self.assertEqual(report["dimensions"]["head_height"]["status"], "unrecognized")

    def test_cube_does_not_have_a_longitudinal_axis(self):
        geometry, report = analyze(moved(Part.makeBox(10, 10, 10)))
        self.assertEqual(geometry["axis"]["status"], "unresolved")
        self.assertEqual(report["dimensions"]["overall_length"]["status"], "unrecognized")

    def test_regular_hex_prism_has_supported_inertia_axis(self):
        geometry, report = analyze(moved(hex_prism(10, 20, 0)))
        self.assertEqual(geometry["axis"]["status"], "identified")
        self.assertAlmostEqual(geometry["hexagonal_regions"][0]["across_flats_mm"], 10, places=5)
        self.assertAlmostEqual(report["dimensions"]["overall_length"]["value_mm"], 20, places=5)

    def test_cone_radius_is_not_promoted_to_head_diameter(self):
        geometry, report = analyze(moved(Part.makeCone(3, 5, 20)))
        self.assertEqual(geometry["surface_type_counts"]["Cone"], 1)
        self.assertEqual(report["dimensions"]["head_diameter"]["status"], "unrecognized")
        cone = next(f for f in geometry["faces"] if f["surface_type"] == "Cone")
        self.assertAlmostEqual(cone["trimmed_radius_range_mm"][0], 3, places=5)
        self.assertAlmostEqual(cone["trimmed_radius_range_mm"][1], 5, places=5)
        self.assertAlmostEqual(cone["surface_axis_trimmed_span_mm"], 20, places=5)

    def test_competing_perpendicular_cylinders_withhold_axis(self):
        first = Part.makeCylinder(2, 20, App.Vector(0, 0, -10))
        second = Part.makeCylinder(2, 20, App.Vector(-10, 0, 0), App.Vector(1, 0, 0))
        geometry, report = analyze(first.fuse(second))
        self.assertEqual(geometry["axis"]["status"], "unresolved")
        self.assertIsNone(report["dimensions"]["overall_length"]["value_mm"])

    def test_open_geometry_withholds_feature_dimensions(self):
        face = Part.Face(Part.makePolygon([App.Vector(0, 0, 0), App.Vector(1, 0, 0), App.Vector(0, 1, 0), App.Vector(0, 0, 0)]))
        geometry = {"axis": {"status": "unresolved"}, "faces": []}
        report = recognize_features(face, geometry, validate_shape(face))
        self.assertTrue(all(d["value_mm"] is None for d in report["dimensions"].values()))

    def test_external_thread_appearance_requires_native_helical_flanks(self):
        shape = threaded_shaft()
        self.assertTrue(shape.isValid())
        _, report = analyze(shape)
        self.assertEqual(report["threads"]["status"], "explicitly_modeled", report["threads"])
        self.assertGreaterEqual(len(report["threads"]["helical_edge_evidence"]), 2)
        self.assertAlmostEqual(report["dimensions"]["thread_major_diameter"]["value_mm"], 10, places=5)
        # Nominal endpoints and a nominal size are not guessed from the fitted helix.
        self.assertIsNone(report["dimensions"]["threaded_length"]["value_mm"])

    def test_rotated_thread_evidence_is_orientation_independent(self):
        _, report = analyze(moved(threaded_shaft()))
        self.assertEqual(report["threads"]["status"], "explicitly_modeled", report["threads"])

    def test_helical_coil_is_not_classified_as_thread(self):
        helix = Part.makeHelix(2, 8, 5)
        points = [App.Vector(4.6, 0, -0.3), App.Vector(5.4, 0, -0.3),
                  App.Vector(5.4, 0, 0.3), App.Vector(4.6, 0, 0.3), App.Vector(4.6, 0, -0.3)]
        profile = Part.Wire(Part.makePolygon(points).Edges)
        coil = Part.Wire(helix.Edges).makePipeShell([profile], True, True)
        # Known construction axis isolates the continuous-core guard. This coil
        # has paired, repeated helical faces, so helix detection alone would lie.
        geometry = {"faces": face_inventory(coil), "numerical_comparison_threshold_mm": comparison_tolerance(coil),
                    "axis": {"status": "identified", "direction": [0, 0, 1], "origin_mm": [0, 0, 0]}}
        threads = detect_threads(coil.Solids[0], geometry)
        self.assertEqual(threads["status"], "cannot_determine")
        self.assertGreaterEqual(len(threads["helical_chain_evidence"]), 2)

    def test_invalid_brep_withholds_recognition_even_when_envelope_available(self):
        solid = Part.makeCylinder(3, 20)
        geometry, _ = analyze_geometry(solid)
        validation = validate_shape(solid)
        validation["basic_valid"] = False
        report = recognize_features(solid, geometry, validation)
        self.assertTrue(all(d["value_mm"] is None for d in report["dimensions"].values()))

    def test_analysis_refuses_aggregate_assembly_geometry(self):
        compound = Part.makeCompound([Part.makeCylinder(2, 20), Part.makeCylinder(3, 10, App.Vector(30, 0, 0))])
        with self.assertRaisesRegex(ValueError, "single Solid"):
            analyze_geometry(compound)


class ImportExportTests(unittest.TestCase):
    @staticmethod
    def temporary_directory():
        root = Path(__file__).resolve().parents[1] / "output" / "test_work"
        root.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=root)

    def test_step_roundtrip_and_original_preservation(self):
        with self.temporary_directory() as directory:
            source = Path(directory) / "name with spaces; sample.step"
            moved(hex_bolt()).exportStep(str(source))
            original = sha256(source)
            report = build_report(source)
            self.assertTrue(report["source"]["unchanged"])
            self.assertEqual(original, sha256(source))
            self.assertAlmostEqual(report["components"][0]["recognition"]["dimensions"]["overall_length"]["value_mm"], 24, places=5)
            destination = Path(directory) / "analysis.json"
            write_json(report, destination)
            saved = json.loads(destination.read_text(encoding="utf-8"))
            self.assertTrue(saved["preliminary"])
            self.assertEqual(saved["source"]["sha256_before"], original)

    def test_assembly_is_reported_as_separate_components(self):
        with self.temporary_directory() as directory:
            source = Path(directory) / "assembly.stp"
            compound = Part.makeCompound([Part.makeCylinder(2, 20), Part.makeCylinder(3, 10, App.Vector(30, 0, 0))])
            compound.exportStep(str(source))
            report = build_report(source)
            self.assertEqual(len(report["components"]), 2)
            self.assertNotIn("dimensions", report)
            self.assertEqual(report["analysis_status"], "needs_review")

    def test_missing_file_produces_error_json_and_failure_exit(self):
        with self.temporary_directory() as directory:
            with contextlib.redirect_stderr(io.StringIO()):
                code = main([str(Path(directory) / "missing.stp"), "--output-dir", directory])
            self.assertEqual(code, 1)
            saved = json.loads((Path(directory) / "missing.analysis.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["analysis_status"], "failed")
            self.assertIn("error", saved)

    def test_malformed_step_does_not_claim_success(self):
        with self.temporary_directory() as directory:
            source = Path(directory) / "bad.step"
            source.write_text("This is not STEP geometry.", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                code = main([str(source), "--output-dir", directory])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
