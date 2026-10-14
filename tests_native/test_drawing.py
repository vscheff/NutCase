from local_samples import require_samples, samples
"""Stage A regressions using native geometry and actual TechDraw subprocesses."""
import contextlib
import io
import json
import math
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import FreeCAD as App
import Part

from fastener_analysis.geometry import analyze_geometry
from fastener_analysis.importer import sha256
from fastener_drawing.cli import main
from fastener_drawing.export import compare_signatures, shape_signature
from fastener_drawing.layout import SHEETS, select_layout
from fastener_drawing.orientation import native_projected_envelope, view_frame
from fastener_drawing.template import make_template
from test_analysis import hex_bolt, moved

ROOT = Path(__file__).resolve().parents[1]


def temporary_directory():
    root = ROOT / "tmp" / "drawing-tests"
    root.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=root)


def run_generator(source, output, *options):
    return subprocess.run([sys.executable, str(ROOT / "src/entrypoints" / "generate_drawing.py"),
                           str(source), "--output-dir", str(output), *options],
                          cwd=ROOT, capture_output=True, text=True, timeout=300,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


class OrientationTests(unittest.TestCase):
    def test_known_pin_extents_survive_arbitrary_rotation_and_translation(self):
        shape = moved(Part.makeCylinder(3, 40))
        geometry, _ = analyze_geometry(shape)
        frame = view_frame(geometry)
        side = native_projected_envelope(shape, frame["frames"]["longitudinal"])
        end = native_projected_envelope(shape, frame["frames"]["right_end"])
        self.assertAlmostEqual(side["width_mm"], 40, places=5)
        self.assertAlmostEqual(side["height_mm"], 6, places=5)
        self.assertAlmostEqual(end["width_mm"], 6, places=5)
        self.assertAlmostEqual(end["height_mm"], 6, places=5)

    def test_hex_flat_fixes_roll_under_rigid_transformation(self):
        baseline, _ = analyze_geometry(hex_bolt().Solids[0])
        rotated, _ = analyze_geometry(moved(hex_bolt()).Solids[0])
        first, second = view_frame(baseline), view_frame(rotated)
        rotation = App.Rotation(App.Vector(1, 2, -3), 73)
        for key in ("axis", "up", "front_normal"):
            expected = rotation.multVec(App.Vector(*first[key]))
            self.assertLess((expected - App.Vector(*second[key])).Length, 1e-8, key)

    def test_third_angle_end_views_preserve_up_and_correct_handedness(self):
        geometry, _ = analyze_geometry(moved(hex_bolt()).Solids[0])
        orientation = view_frame(geometry)
        axis, up = App.Vector(*orientation["axis"]), App.Vector(*orientation["up"])
        front = App.Vector(*orientation["front_normal"])
        self.assertAlmostEqual(axis.cross(up).dot(front), 1, places=10)
        for role in ("longitudinal", "right_end", "left_end"):
            frame = orientation["frames"][role]
            direction, x = App.Vector(*frame["direction"]), App.Vector(*frame["x_direction"])
            self.assertAlmostEqual(direction.dot(x), 0, places=10)
            self.assertLess((direction.cross(x) - up).Length, 1e-10)
        self.assertLess((App.Vector(*orientation["frames"]["right_end"]["direction"]) - axis).Length, 1e-10)
        self.assertLess((App.Vector(*orientation["frames"]["left_end"]["direction"]) + axis).Length, 1e-10)

    def test_isometric_is_orthogonal_and_equally_inclined(self):
        geometry, _ = analyze_geometry(moved(hex_bolt()).Solids[0])
        orientation = view_frame(geometry)
        frame = orientation["frames"]["isometric"]
        direction, x = App.Vector(*frame["direction"]), App.Vector(*frame["x_direction"])
        self.assertAlmostEqual(direction.dot(x), 0, places=10)
        for key in ("axis", "up", "front_normal"):
            self.assertAlmostEqual(direction.dot(App.Vector(*orientation[key])), 1 / math.sqrt(3), places=10)

    def test_unresolved_axis_requires_explicit_reviewed_override(self):
        shape = Part.makeBox(10, 10, 10)
        geometry, _ = analyze_geometry(shape)
        with self.assertRaisesRegex(ValueError, "axis unresolved"):
            view_frame(geometry)
        orientation = view_frame(geometry, [1, 0, 0])
        self.assertEqual(orientation["axis"], [1, 0, 0])
        self.assertEqual(orientation["axis_basis"], "User-reviewed axis")


class LayoutAndIntegrityTests(unittest.TestCase):
    def test_supported_sheets_fit_spaced_views_and_captions(self):
        envelopes = {"longitudinal": {"width_mm": 40, "height_mm": 12},
                     "left_end": {"width_mm": 12, "height_mm": 12},
                     "right_end": {"width_mm": 12, "height_mm": 12},
                     "isometric": {"width_mm": 42, "height_mm": 32}}
        for sheet in SHEETS:
            with self.subTest(sheet=sheet):
                layout = select_layout(envelopes, sheet)
                area = layout["content_area_top_origin_mm"]
                previous_right = None
                for role in ("left_end", "longitudinal", "right_end", "isometric"):
                    p = layout["positions"][role]
                    left, right = p["x_mm"] - p["expected_width_mm"] / 2, p["x_mm"] + p["expected_width_mm"] / 2
                    top = layout["height_mm"] - p["y_mm"] - p["expected_height_mm"] / 2
                    bottom = top + p["expected_height_mm"]
                    self.assertGreaterEqual(left, area["left"])
                    self.assertLessEqual(right, area["right"])
                    self.assertGreaterEqual(top, area["top"])
                    self.assertLessEqual(bottom, area["bottom"])
                    self.assertGreater(layout["height_mm"] - p["label_y_mm"], bottom)
                    if role != "isometric":
                        if previous_right is not None:
                            self.assertGreaterEqual(left - previous_right, 24 - 1e-8)
                        previous_right = right

    def test_optional_views_allow_larger_scale_without_phantom_cells(self):
        two = {"longitudinal": {"width_mm": 16.24, "height_mm": 20},
               "right_end": {"width_mm": 20, "height_mm": 20}}
        four = {**two, "left_end": two["right_end"], "isometric": {"width_mm": 21.56, "height_mm": 19.90}}
        full, compact = select_layout(four), select_layout(two)
        self.assertEqual(full["scale"], 3)
        self.assertGreater(compact["scale"], full["scale"])
        self.assertEqual(set(compact["positions"]), {"longitudinal", "right_end"})

    def test_tiny_views_reserve_legible_caption_spacing(self):
        envelopes = {role: {"width_mm": 0.001, "height_mm": 0.001}
                     for role in ("longitudinal", "left_end", "right_end")}
        positions = select_layout(envelopes)["positions"]
        self.assertGreaterEqual(positions["longitudinal"]["x_mm"] - positions["left_end"]["x_mm"], 69)

    def test_native_signature_detects_changed_internal_geometry_with_same_envelope(self):
        shape = Part.makeCylinder(5, 20).cut(Part.makeCylinder(2, 20))
        changed = Part.makeCylinder(5, 20).cut(Part.makeCylinder(2.1, 20))
        with self.assertRaisesRegex(RuntimeError, "geometry differs"):
            compare_signatures(shape_signature(shape), shape_signature(changed))

    def test_native_signature_distinguishes_serialization_from_small_roundtrip_noise(self):
        shape = Part.makeCylinder(3, 20)
        original = shape_signature(shape)
        changed = shape.copy()
        changed.translate(App.Vector(1e-10, 0, 0))
        check = compare_signatures(original, shape_signature(changed))
        self.assertTrue(check["geometry_equivalent"])
        self.assertFalse(check["brep_serialization_identical"])
        changed.translate(App.Vector(0.01, 0, 0))
        with self.assertRaises(RuntimeError):
            compare_signatures(original, shape_signature(changed))

    def test_title_block_embeds_exact_source_and_no_invented_manufacturing_fields(self):
        envelopes = {"longitudinal": {"width_mm": 40, "height_mm": 12},
                     "right_end": {"width_mm": 12, "height_mm": 12}}
        with temporary_directory() as directory:
            file = Path(directory) / "template.svg"
            filename = "odd name & <special>.step"
            make_template(file, select_layout(envelopes), filename, "2026-10-09", True)
            root = ET.parse(file).getroot()
            text = " ".join(root.itertext())
            self.assertIn(filename, text)
            self.assertIn("THIRD ANGLE", text)
            self.assertIn("Extended Boolean check failed", text)
            self.assertIn("ENGINEERING VERIFICATION REQUIRED", text)
            self.assertNotIn("MATERIAL", text)
            self.assertNotIn("TOLERANCE", text)
            self.assertEqual(root.attrib["width"], "431.8mm")

    def test_dimension_template_marks_measured_geometry_and_no_manufacturing_approval(self):
        envelopes = {"longitudinal": {"width_mm": 40, "height_mm": 12},
                     "right_end": {"width_mm": 12, "height_mm": 12}}
        with temporary_directory() as directory:
            file = Path(directory) / "measured.svg"
            make_template(file, select_layout(envelopes, dimensions=True), "sample.step", "2026-10-09", False, True)
            text = " ".join(ET.parse(file).getroot().itertext())
            self.assertIn("Dimensions measure STEP geometry only", text)
            self.assertIn("Not approved manufacturing specifications", text)
            self.assertNotIn("No dimensions", text)


class NativeDrawingIntegrationTests(unittest.TestCase):
    @require_samples
    def test_both_original_samples_export_reopen_and_keep_validation_failures(self):
        local_inputs = samples()
        self.assertEqual(len(local_inputs), 2)
        with temporary_directory() as directory:
            for sample in local_inputs:
                with self.subTest(sample=sample.name):
                    before = sha256(sample)
                    result = run_generator(sample, directory)
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    report = json.loads((Path(directory) / (sample.stem + ".drawing.json")).read_text(encoding="utf-8"))
                    self.assertEqual(report["drawing_status"], "generated_pending_visual_review")
                    self.assertEqual(report["visual_review"]["status"], "pending")
                    self.assertTrue(report["source_analysis"]["validation"]["basic_valid"])
                    self.assertNotEqual(report["source_analysis"]["validation"]["boolean_check"]["status"], "passed")
                    self.assertEqual(report["layout"]["scale"], 3)
                    reopen = report["reopen_checks"]
                    self.assertTrue(reopen["reopened_successfully"])
                    self.assertTrue(reopen["source_geometry_check"]["geometry_equivalent"])
                    self.assertTrue(reopen["view_positions_verified"])
                    self.assertTrue(reopen["view_directions_verified"])
                    self.assertTrue(reopen["all_views_use_page_scale"])
                    self.assertTrue(reopen["validation_diagnostics_retained"])
                    self.assertEqual(reopen["native_view_count"], 4)
                    self.assertEqual(reopen["dimension_count"], 0)
                    self.assertEqual(reopen["projection_convention"], "Third angle")
                    self.assertAlmostEqual(reopen["template_width_mm"], 431.8)
                    self.assertAlmostEqual(reopen["template_height_mm"], 279.4)
                    for role, check in report["projection_checks"].items():
                        self.assertTrue(check["no_overlap_or_clipping"])
                        self.assertTrue(check["projection_matches_source_extents"])
                        self.assertFalse(check["coarse_view"])
                        self.assertEqual(check["hlr_scrub_count"], 0)
                        self.assertGreater(check["visible_edge_count"], 0)
                        if role != "isometric":
                            self.assertTrue(check["hidden_lines_enabled"])
                            self.assertGreater(check["hidden_edge_count"], 0)
                    self.assertTrue(report["source_sha256_verified_unchanged"])
                    self.assertEqual(before, sha256(sample))
                    pdf = Path(report["exports"]["pdf"])
                    self.assertEqual(pdf.name, sample.stem + ".pdf")
                    self.assertTrue(pdf.read_bytes().startswith(b"%PDF-"))
                    self.assertGreater(pdf.stat().st_size, 1000)
                    with zipfile.ZipFile(report["exports"]["project"]) as archive:
                        self.assertIn("Document.xml", archive.namelist())
                        self.assertTrue(any(name.endswith(".svg") for name in archive.namelist()))

    def test_native_two_view_a4_option_and_known_rotated_pin(self):
        with temporary_directory() as directory:
            source = Path(directory) / "pin.known dimensions.step"
            moved(Part.makeCylinder(3, 40)).exportStep(str(source))
            before = sha256(source)
            result = run_generator(source, directory, "--sheet-size", "A4", "--no-isometric", "--no-opposite-end")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads((Path(directory) / (source.stem + ".drawing.json")).read_text(encoding="utf-8"))
            self.assertEqual(report["reopen_checks"]["native_view_count"], 2)
            self.assertEqual(report["layout"]["sheet"], "A4")
            self.assertAlmostEqual(report["native_source_envelopes"]["longitudinal"]["width_mm"], 40, places=5)
            self.assertAlmostEqual(report["native_source_envelopes"]["longitudinal"]["height_mm"], 6, places=5)
            self.assertEqual(before, sha256(source))

    def test_native_unresolved_axis_writes_failure_report_without_pdf(self):
        with temporary_directory() as directory:
            source = Path(directory) / "cube.step"
            Part.makeBox(10, 10, 10).exportStep(str(source))
            result = run_generator(source, directory)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            report = json.loads((Path(directory) / "cube.drawing.json").read_text(encoding="utf-8"))
            self.assertEqual(report["drawing_status"], "failed")
            self.assertIn("axis unresolved", report["error"]["message"])
            self.assertFalse((Path(directory) / "cube.pdf").exists())


if __name__ == "__main__":
    unittest.main()
