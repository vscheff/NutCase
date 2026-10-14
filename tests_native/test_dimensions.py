from local_samples import require_samples, samples
"""Stage B regressions against constructed geometry and persisted native references."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

import FreeCAD as App
import Part

from fastener_drawing.dimensions import overlaps
from fastener_drawing.layout import select_layout
from fastener_drawing.references import UnresolvedDimension, records_match, source_features
from fastener_drawing.orientation import native_projected_envelope, view_frame
from test_analysis import analyze, hex_prism, moved
from test_drawing import ROOT, run_generator, temporary_directory


def fixture():
    # Independently specified 21 length, 16 flange, 4 smooth bore, 10 AF.
    return hex_prism(10, 20, 0).fuse(Part.makeCylinder(8, 1, App.Vector(0, 0, 20))).cut(Part.makeCylinder(2, 21)).removeSplitter()


class DimensionGeometryTests(unittest.TestCase):
    def test_independent_fixture_measurements_survive_rigid_motion(self):
        for shape in (fixture(), moved(fixture())):
            geometry, recognition = analyze(shape)
            features = source_features(shape, geometry, recognition, view_frame(geometry))
            for key, value in zip(("overall_axial_length", "flange_diameter", "bore_diameter", "external_hex_across_flats"), (21, 16, 4, 10)):
                with self.subTest(feature=key):
                    self.assertAlmostEqual(features[key]["independent_source_value_mm"], value, places=6)

    def test_stepped_bore_is_not_arbitrarily_promoted_to_single_diameter(self):
        shape = fixture().cut(Part.makeCylinder(3, 3))
        geometry, recognition = analyze(shape)
        features = source_features(shape, geometry, recognition, view_frame(geometry))
        self.assertNotIn("bore_diameter", features)
        self.assertIn("overall_axial_length", features)

    def test_geometry_fingerprint_rejects_equal_radius_at_wrong_center(self):
        self.assertFalse(records_match({"radius": 3.0, "center": [0.0, 0.0]}, {"radius": 3.0, "center": [0.5, 0.0]}))
        self.assertFalse(records_match({"radius": float("nan")}, {"radius": float("nan")}))

    def test_collision_check_rejects_overlap_and_insufficient_clearance(self):
        box = {"left": 0, "right": 10, "top": 0, "bottom": 5}
        self.assertTrue(overlaps(box, {"left": 9, "right": 19, "top": 0, "bottom": 5}))
        self.assertTrue(overlaps(box, {"left": 10.5, "right": 20, "top": 0, "bottom": 5}))
        self.assertFalse(overlaps(box, {"left": 11, "right": 20, "top": 0, "bottom": 5}))

    def test_layout_reserves_dimension_lanes_and_reduces_scale(self):
        geometry, _ = analyze(moved(fixture()))
        frames = view_frame(geometry)
        envelopes = {role: native_projected_envelope(moved(fixture()), frame) for role, frame in frames["frames"].items()}
        plain = select_layout(envelopes)
        dimensioned = select_layout(envelopes, dimensions=True)
        self.assertLess(dimensioned["scale"], plain["scale"])
        self.assertTrue(dimensioned["dimension_lanes_reserved"])
        self.assertGreater(dimensioned["dimension_top_lane_mm"], 0)
        self.assertEqual(dimensioned["dimension_side_padding_mm"]["left_end"], [30, 30])


class NativeDimensionIntegrationTests(unittest.TestCase):
    def assert_dimensions(self, report, expected):
        self.assertEqual(report["stage"], "B")
        self.assertEqual(report["unresolved_dimensions"], [])
        self.assertEqual(report["reopen_checks"]["dimension_count"], 4)
        for key, value in expected.items():
            with self.subTest(feature=key):
                record = report["dimensions"][key]
                self.assertEqual(record["status"], "created")
                self.assertAlmostEqual(record["verification"]["native_value_mm"], value, places=5)
                self.assertAlmostEqual(record["source_feature"]["independent_source_value_mm"], value, places=5)
                reopened = report["reopen_checks"]["dimension_checks"][key]
                self.assertTrue(reopened["references_verified"])
                self.assertTrue(reopened["source_measurement_repeated"])
                self.assertTrue(reopened["geometry_fingerprint_verified"])
                self.assertFalse(reopened["arbitrary_value_override"])
                self.assertFalse(reopened["tolerances_assigned"])
                self.assertTrue(report["dimension_placement_checks"][key]["text_no_collision_or_clipping"])

    def test_independent_rotated_fixture_native_dimensions_and_vector_pdf(self):
        with temporary_directory() as directory:
            source = Path(directory) / "known hollow hex.step"
            moved(fixture()).exportStep(str(source))
            result = run_generator(source, directory, "--dimensions", "--dimension-scope", "basic")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads((Path(directory) / (source.stem + ".drawing.json")).read_text(encoding="utf-8"))
            self.assert_dimensions(report, dict(zip(("overall_axial_length", "flange_diameter", "bore_diameter", "external_hex_across_flats"), (21, 16, 4, 10))))
            self.assertTrue(report["source_sha256_verified_unchanged"])
            pdf = Path(report["exports"]["pdf"]).read_bytes()
            self.assertTrue(pdf.startswith(b"%PDF-"))
            self.assertNotIn(b"/Subtype /Image", pdf)
            # Native renderer embeds searchable computed labels; catches the
            # observed save/export race that dropped the entire extent view.
            self.assertTrue(report["native_render_checks"]["all_dimension_text_present"])
            check_path = Path(directory) / "adversarial.json"
            checked = subprocess.run([sys.executable, str(ROOT / "tests_native/native_reference_checks.py"),
                                      str(Path(directory) / (source.stem + ".drawing.json")), str(check_path)],
                                     capture_output=True, text=True, timeout=120,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            adversarial = json.loads(check_path.read_text(encoding="utf-8"))
            self.assertEqual(len(adversarial), 7)
            self.assertTrue(all(adversarial.values()))

    @require_samples
    def test_both_supplied_parts_native_dimensions_and_reopen(self):
        with temporary_directory() as directory:
            for sample, values in zip(samples(), ((16.24, 20, 6, 9.6), (18.9, 22, 9, 12.7))):
                with self.subTest(sample=sample.name):
                    result = run_generator(sample, directory, "--dimensions", "--dimension-scope", "basic")
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    report = json.loads((Path(directory) / (sample.stem + ".drawing.json")).read_text(encoding="utf-8"))
                    self.assert_dimensions(report, dict(zip(("overall_axial_length", "flange_diameter", "bore_diameter", "external_hex_across_flats"), values)))
                    self.assertNotEqual(report["phase1_analysis"]["validation"]["boolean_check"]["status"], "passed")

    def test_ambiguous_bore_is_omitted_in_native_sheet_and_reported(self):
        with temporary_directory() as directory:
            source = Path(directory) / "stepped bore.step"
            moved(fixture().cut(Part.makeCylinder(3, 3))).exportStep(str(source))
            result = run_generator(source, directory, "--dimensions", "--dimension-scope", "basic")
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            report = json.loads((Path(directory) / (source.stem + ".drawing.json")).read_text(encoding="utf-8"))
            self.assertEqual(report["dimensions"]["bore_diameter"]["status"], "unresolved")
            self.assertEqual(report["reopen_checks"]["dimension_count"], 3)
            self.assertIn("bore_diameter", report["unresolved_dimensions"])


if __name__ == "__main__":
    unittest.main()
