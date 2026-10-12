"""Associative native dimensions, geometry verification and paper placement checks."""
import logging
import math

from fastener_analysis.geometry import App
from .references import MATCH_MM, UnresolvedDimension, edge_record, inventory, match_feature, records_match, source_features, remeasure_source
from .views import wait_for_views

LOG = logging.getLogger("fastener_drawing")
CHARACTERISTICS = ("overall_axial_length", "flange_diameter", "bore_diameter", "external_hex_across_flats")


def references_record(dimension):
    return [{"view": obj.Name, "subelements": list(names)} for obj, names in dimension.References2D]


def same_circle_locus(first,second):
    return (first.get("curve_type")==second.get("curve_type")=="Circle"
            and records_match(first.get("center_mm"),second.get("center_mm"))
            and records_match(first.get("radius_mm"),second.get("radius_mm")))


def same_straight_locus(first,second):
    if "points_mm" not in first or "points_mm" not in second:return False
    a,b=App.Vector(*first["points_mm"][0]),App.Vector(*first["points_mm"][-1])
    direction=b-a
    if direction.Length<MATCH_MM or abs(first["length_mm"]-direction.Length)>MATCH_MM:return False
    p,q=App.Vector(*second["points_mm"][0]),App.Vector(*second["points_mm"][-1])
    if abs(second["length_mm"]-(q-p).Length)>MATCH_MM:return False
    return all((App.Vector(*point)-a).cross(direction).Length/direction.Length<MATCH_MM
               for point in first["points_mm"]+second["points_mm"])


def native_measurement(dimension, feature, matching):
    value = float(dimension.getRawValue())
    expected = feature["expected_mm"]
    if not math.isfinite(value) or any(not math.isfinite(candidate) or abs(value - candidate) > MATCH_MM for candidate in
           (expected, feature["independent_source_value_mm"], matching["projection_value_mm"])):
        raise UnresolvedDimension(f"Native dimension value {value} disagrees with source/analysis/projected measurement")
    if (dimension.Arbitrary or dimension.ArbitraryTolerances or dimension.TheoreticalExact or dimension.AngleOverride
            or dimension.OverTolerance.Value != 0 or dimension.UnderTolerance.Value != 0):
        raise UnresolvedDimension("Dimension contains a text override or unintended engineering specification")
    result = {"native_value_mm": value, "difference_from_phase1_mm": abs(value - expected),
            "difference_from_independent_source_mm": abs(value - feature["independent_source_value_mm"]),
            "difference_from_projected_geometry_mm": abs(value - matching["projection_value_mm"]),
            "numerical_validation_threshold_mm": MATCH_MM, "arbitrary_value_override": False,
            "tolerances_assigned": False, "measurement_verified": True}
    result["units"]=feature.get("units","mm")
    if result["units"]=="deg":
        result={k.replace("_mm","_deg"):v for k,v in result.items()}
    return result


def set_presentation(dim, key):
    dim.FormatSpec = ("⌀" if key in ("flange_diameter", "bore_diameter") else "") + "%.2f" + (" AF" if key == "external_hex_across_flats" else "")
    dim.ShowUnits = False
    dim.Arbitrary = False
    dim.ArbitraryTolerances = False
    dim.TheoreticalExact = False
    dim.OverTolerance = 0
    dim.UnderTolerance = 0
    dim.ViewObject.Font = "Arial"
    dim.ViewObject.Fontsize = 3.5
    dim.ViewObject.LineWidth = 0.25
    dim.ViewObject.Arrowsize = 2.5
    dim.ViewObject.Color = (0.0, 0.0, 0.0)
    dim.ViewObject.StandardAndStyle = "ASME Inlined" if key != "bore_diameter" else "ASME Referencing"
    dim.ViewObject.RenderingExtent = "Expanded" if key == "flange_diameter" else "Confined" if key == "bore_diameter" else "Normal"


def presentation_record(dim):
    values = {key: getattr(dim.ViewObject, key) for key in
              ("Font", "Fontsize", "LineWidth", "Arrowsize", "StandardAndStyle", "RenderingExtent")}
    return {key: value.Value if hasattr(value, "Value") else value for key, value in values.items()}


def create_dimensions(doc, page, source, views, geometry, recognition, frames, layout):
    import TechDraw
    features = source_features(source.Shape, geometry, recognition, frames)
    result, inventories = {}, {}
    for key in CHARACTERISTICS:
        if key not in features:
            result[key] = {"status": "unresolved", "reason": "No unique supported source feature with an independent native measurement"}
            continue
        feature = features[key]
        roles = ["longitudinal"] if key == "overall_axial_length" else ["left_end", "right_end"] if key == "external_hex_across_flats" else ["right_end", "left_end"]
        selected, matching, failures = None, None, []
        for role in roles:
            if role not in views:
                continue
            view = views[role]
            try:
                if feature["kind"] != "extent" and role not in inventories:
                    inventories[role] = inventory(view)
                matching = match_feature(source.Shape, view, feature, inventories.get(role))
                if abs(matching["projection_value_mm"] - feature["expected_mm"]) > MATCH_MM:
                    raise UnresolvedDimension("Matched projection disagrees with the feature measurement")
                selected = (role, view)
                break
            except UnresolvedDimension as exc:
                failures.append(f"{role}: {exc}")
        if selected is None:
            result[key] = {"status": "unresolved", "source_feature": feature, "reason": "; ".join(failures) or "No suitable orthographic view"}
            continue
        role, view = selected
        dim = None
        try:
            if feature["kind"] == "extent":
                dim = TechDraw.makeExtentDim(view, [], 0)
                dim.Label = "Overall axial extent"
            else:
                dim = doc.addObject("TechDraw::DrawViewDimension", "".join(word.title() for word in key.split("_")))
                dim.Type = "Diameter" if feature["kind"] == "circle" else "DistanceY"
                dim.MeasureType = "Projected"
                dim.References2D = [(view, matching["references"])]
                page.addView(dim)
            set_presentation(dim, key)
            position = layout["positions"][role]
            half_height, half_width = position["expected_height_mm"] / 2, position["expected_width_mm"] / 2
            # Dimension X/Y are paper millimeters relative to the source view.
            dim.X, dim.Y = {"overall_axial_length": (0, half_height + 10),
                           "flange_diameter": (0, half_height + 10),
                           "bore_diameter": (half_width + 14, -half_height - 10),
                           "external_hex_across_flats": (-half_width - 14, 0)}[key]
            wait_for_views(doc, list(views.values()))
            checked = native_measurement(dim, feature, matching)
            result[key] = {"status": "created", "object_name": dim.Name, "view_role": role,
                "source_feature": feature, "projection_match": matching, "references2d": references_record(dim),
                "format_spec": dim.FormatSpec, "measure_type": dim.MeasureType, "native_type": dim.Type,
                "presentation": presentation_record(dim),
                "position_relative_to_view_mm": [dim.X.Value, dim.Y.Value], "verification": checked,
                "requires_engineering_verification": True}
            dim.addProperty("App::PropertyString", "MeasuredCharacteristic", "Provenance").MeasuredCharacteristic = key
            LOG.info("%s: native %.6f mm, verified against independent source and Phase 1", key, checked["native_value_mm"])
        except (UnresolvedDimension, RuntimeError, ValueError) as exc:
            if dim is not None:
                doc.removeObject(dim.Name)
            result[key] = {"status": "unresolved", "source_feature": feature, "reason": str(exc)}
    wait_for_views(doc, list(views.values()))
    for key, record in result.items():
        if record["status"] == "unresolved":
            LOG.warning("%s omitted: %s", key, record["reason"])
    return result


def verify_dimensions(doc, reports, check_count=True):
    checked = {}
    source = doc.getObject("OriginalSTEP")
    for key, record in reports.items():
        if record["status"] != "created":
            continue
        dim = doc.getObject(record["object_name"])
        general=record["source_feature"]["kind"]=="general"
        if dim is not None and general and references_record(dim)!=record["references2d"]:
            from . import feature_references as feature_refs
            actual_refs=references_record(dim)
            old_refs=record["references2d"]
            names=[name for group in actual_refs for name in group["subelements"]]
            original_names=record["projection_match"]["references"]
            # Native SavedGeometry can renumber coincident projection geometry
            # on restore. Permit only a proven identity of that geometry, never
            # an equal dimension value or an assistant-applied reference repair.
            if (len(actual_refs)!=1 or actual_refs[0]["view"]!=old_refs[0]["view"] or len(names)!=len(original_names)
                    or not all(name.startswith(("Vertex","Edge")) for name in names+original_names)):
                raise RuntimeError(f"{key}: native references changed without a verifiable geometry remap")
            view=dim.References2D[0][0]
            actual_geometry=[feature_refs.reference_record(view,name) for name in names]
            circular=dim.Type in ("Diameter","Radius")
            linear=dim.Type in ("Distance","DistanceY")
            if not all(records_match(actual,expected) or (circular and same_circle_locus(actual,expected)) or (linear and same_straight_locus(actual,expected))
                       for actual,expected in zip(actual_geometry,record["projection_match"]["projected_geometry"])):
                raise RuntimeError(f"{key}: native restore remap changed referenced geometry")
            record.setdefault("native_restore_reference_remaps",[]).append({"before":old_refs,"after":actual_refs,
                "same_measured_geometry_verified":True,"document_repaired":False,
                "basis":"Identical vertex/edge fingerprints, or identical analytic circle center/radius with a native arc-trim change; source matching repeated separately",
                "geometry_before":record["projection_match"]["projected_geometry"],"geometry_after":actual_geometry})
            record["references2d"]=actual_refs
            record["projection_match"]["references"]=names
            record["projection_match"]["projected_geometry"]=actual_geometry
        if dim is None or references_record(dim) != record["references2d"] or dim.Type != record["native_type"]:
            raise RuntimeError(f"{key}: native dimension references/type changed after reopening: {references_record(dim) if dim else None}/{dim.Type if dim else None} versus {record['references2d']}/{record['native_type']}")
        if dim.FormatSpec != record["format_spec"] or dim.MeasureType != record["measure_type"]:
            raise RuntimeError(f"{key}: native formatting or measurement mode changed")
        if presentation_record(dim) != record["presentation"]:
            raise RuntimeError(f"{key}: dimension presentation changed")
        if any(abs(actual - expected) > 1e-8 for actual, expected in zip([dim.X.Value, dim.Y.Value], record["position_relative_to_view_mm"])):
            raise RuntimeError(f"{key}: dimension placement changed")
        view = dim.References2D[0][0]
        if general:
            from . import feature_references as feature_refs
            feature={**record["source_feature"],"independent_source_value_mm":feature_refs.remeasure(source.Shape,record["source_feature"])}
        else:
            feature = {**record["source_feature"], "independent_source_value_mm": remeasure_source(source.Shape, record["source_feature"])}
        names = record["projection_match"]["references"]
        entries = None if record["source_feature"]["kind"] == "extent" else [e for e in inventory(view) if e["name"] in names]
        # Revalidate the persisted references themselves. Equivalent coincident
        # line/spline traces can change longest-edge order by numerical noise;
        # that is no reason to switch the document's associative references.
        fresh = feature_refs.match(source.Shape,view,feature,entries,[v for v in feature_refs.vertices(view) if v["name"] in names]) if general else match_feature(source.Shape, view, record["source_feature"], entries)
        # Recheck the referenced geometry itself, even if another edge could
        # produce the same plausible measurement. No silent automatic repair.
        if record["source_feature"]["kind"] != "extent":
            for name, expected in zip(record["projection_match"]["references"], record["projection_match"]["projected_geometry"]):
                actual=feature_refs.reference_record(view,name) if general else edge_record(view.getEdgeBySelection(name))
                if not records_match(actual, expected) and not (general and ((dim.Type in ("Diameter","Radius") and same_circle_locus(actual,expected)) or (dim.Type in ("Distance","DistanceY") and same_straight_locus(actual,expected)))):
                    raise RuntimeError(f"{key}: referenced projected geometry changed")
            if fresh["references"] != record["projection_match"]["references"]:
                raise RuntimeError(f"{key}: source-to-projection matching changed")
        checked[key] = {**native_measurement(dim, feature, fresh),
                        "references_verified": True, "geometry_fingerprint_verified": True,
                        "source_projection_match_repeated": True, "source_measurement_repeated": True,
                        "position_verified": True, "presentation_verified": True}
    actual = [obj for obj in doc.Objects if obj.isDerivedFrom("TechDraw::DrawViewDimension")]
    if check_count and len(actual) != len(checked):
        raise RuntimeError("Unexpected extra/missing native dimensions in saved document")
    return checked


def overlaps(a, b, gap=1.0):
    return min(a["right"], b["right"]) + gap > max(a["left"], b["left"]) and min(a["bottom"], b["bottom"]) + gap > max(a["top"], b["top"])


def displayed_text(dim,record):
    return record["format_spec"].replace("%.2f",f"{dim.getRawValue():.2f}")+("°" if dim.Type in ("Angle","Angle3Pt") else "")


def check_text_placement(doc, reports, layout, paper_boxes, rendered_svg):
    """Validate the persisted native vector scene instead of stale live Qt groups."""
    from .svg_placement import check
    return check(doc, reports, layout, paper_boxes, rendered_svg)
