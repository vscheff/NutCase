"""Run adversarial reference checks in an isolated GUI-backed native process."""
import json
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root/'src'))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["FREECAD_USER_HOME"] = str(root / "tmp/freecad-runtime")
from fastener_drawing.views import initialize_gui, wait_for_views
from fastener_drawing.dimensions import verify_dimensions
from fastener_drawing.references import UnresolvedDimension, edge_record, match_feature, projection_center
import FreeCAD as App
import Part

initialize_gui()
report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
doc = App.openDocument(report["exports"]["project"])
page = doc.DrawingPage
page.ViewObject.show()
wait_for_views(doc, [v for v in page.Views if v.TypeId == "TechDraw::DrawViewPart"])
records = report["dimensions"]
verify_dimensions(doc, records)
results = {}


def rejected(name, action):
    try:
        action()
    except (RuntimeError, ValueError):
        results[name] = True
    else:
        raise AssertionError(name + " was accepted")


bore = doc.getObject(records["bore_diameter"]["object_name"])
view = bore.References2D[0][0]
feature = records["bore_diameter"]["source_feature"]
curve = view.getEdgeBySelection(records["bore_diameter"]["projection_match"]["references"][0]).Curve
wrong = Part.makeCircle(curve.Radius, curve.Center + App.Vector(0.5, 0, 0))
rejected("equal_diameter_wrong_center", lambda: match_feature(doc.OriginalSTEP.Shape, view, feature,
    [{"name": "WrongCircle", "edge": wrong, "record": edge_record(wrong), "visible": True}]))
right = Part.makeCircle(curve.Radius, curve.Center)
rejected("hidden_only_reference", lambda: match_feature(doc.OriginalSTEP.Shape, view, feature,
    [{"name": "HiddenCircle", "edge": right, "record": edge_record(right), "visible": False}]))
rejected("missing_projected_geometry", lambda: match_feature(doc.OriginalSTEP.Shape, view, feature, []))

flange = doc.getObject(records["flange_diameter"]["object_name"])
original_refs = flange.References2D
flange.References2D = bore.References2D
doc.recompute()
rejected("wrong_native_circle_reference", lambda: verify_dimensions(doc, records))
flange.References2D = original_refs
doc.recompute()
flange.References2D = [(original_refs[0][0], ["Edge999999"])]
rejected("missing_native_reference", lambda: verify_dimensions(doc, records))
flange.References2D = original_refs
doc.recompute()
flange.Arbitrary = True
rejected("arbitrary_native_value_override", lambda: verify_dimensions(doc, records))
flange.Arbitrary = False
doc.recompute()
verify_dimensions(doc, records)
# Tessellating the source must not change the coordinate matching; this
# reproduces the fresh/reopened centroid-cache discrepancy seen on samples.
center_before = projection_center(view)
doc.OriginalSTEP.Shape.tessellate(0.5)
center_after = projection_center(view)
assert (center_before - center_after).Length < 1e-8
verify_dimensions(doc, records)
results["display_triangulation_does_not_change_matching"] = True
Path(sys.argv[2]).write_text(json.dumps(results, indent=2), encoding="utf-8")
App.closeDocument(doc.Name)
