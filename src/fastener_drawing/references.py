"""Match source features to measured native HLR geometry, never fixed edge indices."""
import math

from fastener_analysis.geometry import App, Part, unit, xyz

MATCH_MM = 1e-5  # Numerical geometry matching; not imported or manufacturing tolerance.


class UnresolvedDimension(ValueError):
    pass


def edge_record(edge):
    curve = edge.Curve
    box = edge.optimalBoundingBox(False, False)
    first, last = edge.FirstParameter, edge.LastParameter
    record = {"curve_type": type(curve).__name__, "length_mm": edge.Length,
              "bounds_mm": [box.XMin, box.YMin, box.XMax, box.YMax],
              "points_mm": [xyz(edge.valueAt(first + (last - first) * t)) for t in (0, 0.25, 0.5, 0.75, 1)]}
    if isinstance(curve, Part.Circle):
        record.update(radius_mm=curve.Radius, center_mm=xyz(curve.Center))
    return record


def records_match(first, second, threshold=MATCH_MM):
    if type(first) is not type(second):
        return False
    if isinstance(first, dict):
        return first.keys() == second.keys() and all(records_match(first[k], second[k], threshold) for k in first)
    if isinstance(first, list):
        return len(first) == len(second) and all(records_match(a, b, threshold) for a, b in zip(first, second))
    if isinstance(first, (int, float)):
        return math.isfinite(first) and math.isfinite(second) and abs(first - second) <= threshold
    return first == second


def projection_center(view):
    # TechDraw centers a geometry copy without its display triangulation.
    # getGeometricCenter() instead examines the source's current mesh cache,
    # which can disagree after GUI tessellation. Reproduce native centering
    # on a mesh-free BRep copy, with the actual native viewing basis.
    direction, x = unit(view.Direction), unit(view.XDirection)
    y = direction.cross(x)
    matrix = App.Matrix()
    matrix.A11, matrix.A12, matrix.A13 = x.x, x.y, x.z
    matrix.A21, matrix.A22, matrix.A23 = y.x, y.y, y.z
    matrix.A31, matrix.A32, matrix.A33 = direction.x, direction.y, direction.z
    shape = view.Source[0].Shape.copy(True, False)
    shape.transformShape(matrix, False)
    center = shape.optimalBoundingBox(True, False).Center
    return matrix.inverse().multVec(center)


def projected_point(view, world_point):
    return view.projectPoint(world_point - projection_center(view), True)


def inventory(view):
    visible = []
    # On the inspected API, True matches getEdgeBySelection's reflected Y
    # coordinates. This is verified against source projections in regressions.
    for edge in view.getVisibleEdges(True):
        normalized = edge.copy()
        normalized.scale(1 / view.Scale)
        visible.append(edge_record(normalized))
    entries = []
    for index in range(len(visible) + len(view.getHiddenEdges(False))):
        edge = view.getEdgeByIndex(index)
        record = edge_record(edge)
        name = f"Edge{index}"
        # Verify the API's name/index correspondence instead of assuming it.
        if not records_match(record, edge_record(view.getEdgeBySelection(name))):
            raise UnresolvedDimension("Installed TechDraw edge naming does not match measured getter geometry")
        entries.append({"name": name, "edge": edge, "record": record,
                        "visible": any(records_match(record, item) for item in visible)})
    return entries


def source_features(shape, geometry, recognition, frames):
    """Analysis supplies roles; source BRep supplies independent measurements."""
    solid = shape.Solids[0]
    axis, up = App.Vector(*frames["axis"]), App.Vector(*frames["up"])
    result = {}
    overall = recognition["dimensions"]["overall_length"]
    if overall["status"] == "recognized":
        planes = [(index + 1, face.CenterOfMass.dot(axis)) for index, face in enumerate(solid.Faces)
                  if isinstance(face.Surface, Part.Plane) and abs(unit(face.Surface.Axis).dot(axis)) > 1 - 1e-8]
        if len(planes) >= 2:
            low, high = min(planes, key=lambda p: p[1]), max(planes, key=lambda p: p[1])
            value = high[1] - low[1]
            if abs(value - overall["value_mm"]) <= MATCH_MM:
                result["overall_axial_length"] = {"kind": "extent", "expected_mm": overall["value_mm"],
                    "independent_source_value_mm": value, "faces": [low[0], high[0]],
                    "source_measurement_direction": xyz(axis),
                    "measurement_basis": "Separation of native perpendicular terminal planes along the reviewed axis"}
    flange = recognition["dimensions"]["flange_diameter"]
    if flange["status"] == "recognized":
        ids = flange["evidence"]["faces"]
        radii = [solid.Faces[i - 1].Surface.Radius for i in ids
                 if isinstance(solid.Faces[i - 1].Surface, Part.Cylinder)]
        if len(radii) == len(ids) and max(radii) - min(radii) <= MATCH_MM:
            result["flange_diameter"] = {"kind": "circle", "faces": ids, "expected_mm": flange["value_mm"],
                "independent_source_value_mm": 2 * radii[0], "measurement_basis": "Native cylindrical flange-like surface radius",
                "semantic_note": "Flange-like geometry; engineering function remains inferred"}
    bores = [b for b in geometry["cylindrical_bands"] if b["boundary_side"] == "internal" and b["complete_circular_band"]]
    if bores and max(b["diameter_mm"] for b in bores) - min(b["diameter_mm"] for b in bores) <= MATCH_MM:
        ids = sorted({i for b in bores for i in b["faces"]})
        result["bore_diameter"] = {"kind": "circle", "faces": ids, "expected_mm": bores[0]["diameter_mm"],
            "independent_source_value_mm": 2 * solid.Faces[ids[0] - 1].Surface.Radius,
            "measurement_basis": "Native internal cylindrical surface radius; one supported bore diameter",
            "semantic_note": "Measured smooth cylindrical bore; no thread role assigned"}
    if len(geometry["hexagonal_regions"]) == 1:
        region = geometry["hexagonal_regions"][0]
        plus = [f for f in geometry["faces"] if f["face"] in region["faces"] and App.Vector(*f["normal_direction"]).dot(up) > 1 - 1e-8]
        minus = [f for f in geometry["faces"] if f["face"] in region["faces"] and App.Vector(*f["normal_direction"]).dot(up) < -1 + 1e-8]
        if len(plus) == len(minus) == 1:
            ids = [plus[0]["face"], minus[0]["face"]]
            value = abs((solid.Faces[ids[0] - 1].Surface.Position - solid.Faces[ids[1] - 1].Surface.Position).dot(up))
            result["external_hex_across_flats"] = {"kind": "flats", "faces": ids, "expected_mm": region["across_flats_mm"],
                "source_measurement_direction": xyz(up),
                "independent_source_value_mm": value, "measurement_basis": "Perpendicular separation of two native opposing support planes",
                "semantic_note": "External hex region; no head role assigned"}
    for key, feature in list(result.items()):
        if abs(feature["independent_source_value_mm"] - feature["expected_mm"]) > MATCH_MM:
            del result[key]
    return result


def remeasure_source(shape, feature):
    faces = [shape.Solids[0].Faces[i - 1] for i in feature["faces"]]
    if feature["kind"] == "circle":
        if not all(isinstance(f.Surface, Part.Cylinder) for f in faces):
            raise UnresolvedDimension("Source cylinder support changed")
        radii = [f.Surface.Radius for f in faces]
        if max(radii) - min(radii) > MATCH_MM:
            raise UnresolvedDimension("Source cylinder radii disagree")
        return 2 * radii[0]
    direction = App.Vector(*feature["source_measurement_direction"])
    if not all(isinstance(f.Surface, Part.Plane) and abs(unit(f.Surface.Axis).dot(direction)) > 1 - 1e-8 for f in faces):
        raise UnresolvedDimension("Source planar support changed")
    return abs((faces[0].Surface.Position - faces[1].Surface.Position).dot(direction))


def match_circle(shape, view, feature, entries):
    boundaries = []
    direction = unit(view.Direction)
    for face_id in feature["faces"]:
        face = shape.Solids[0].Faces[face_id - 1]
        if not isinstance(face.Surface, Part.Cylinder) or abs(unit(face.Surface.Axis).dot(direction)) < 1 - 1e-8:
            raise UnresolvedDimension("Supporting cylindrical axis is not normal to the end view")
        for edge in face.Edges:
            if isinstance(edge.Curve, Part.Circle) and abs(2 * edge.Curve.Radius - feature["independent_source_value_mm"]) <= MATCH_MM:
                boundaries.append({"face": face_id, "center_mm": xyz(projected_point(view, edge.Curve.Center)),
                    "source_center_mm": xyz(edge.Curve.Center), "radius_mm": edge.Curve.Radius})
    matches = []
    for entry in entries:
        r = entry["record"]
        if not entry["visible"] or r["curve_type"] != "Circle":
            continue
        support = [b for b in boundaries if abs(b["radius_mm"] - r["radius_mm"]) <= MATCH_MM
                   and (App.Vector(*b["center_mm"]) - App.Vector(*r["center_mm"])).Length <= MATCH_MM]
        if support:
            matches.append((entry, support))
    if not matches:
        raise UnresolvedDimension("No visible analytic circular edge matches the source cylinder's actual boundary center and radius")
    # Coaxial boundary rims/arc splits can project onto the same measured circle.
    # Choose the longest visible arc, with all equivalent candidates recorded.
    selected, support = max(matches, key=lambda pair: pair[0]["record"]["length_mm"])
    if any((App.Vector(*e["record"]["center_mm"]) - App.Vector(*selected["record"]["center_mm"])).Length > MATCH_MM for e, _ in matches):
        raise UnresolvedDimension("Multiple spatially distinct circular projections match this feature")
    return {"references": [selected["name"]], "projected_geometry": [selected["record"]],
            "projection_value_mm": 2 * selected["record"]["radius_mm"], "source_boundary_support": support,
            "equivalent_projected_candidates": [e["name"] for e, _ in matches],
            "match_basis": "Visible analytic circle/arc; radius AND projected source-boundary center AND supporting cylindrical axis"}


def match_flats(shape, view, feature, entries):
    refs, records, evidence = [], [], []
    for face_id in feature["faces"]:
        face = shape.Solids[0].Faces[face_id - 1]
        point = projected_point(view, face.CenterOfMass)
        # Independent exact native face extrema in the viewing frame.
        direction, x = unit(view.Direction), unit(view.XDirection)
        y = direction.cross(x)
        matrix = App.Matrix()
        matrix.A11, matrix.A12, matrix.A13 = x.x, x.y, x.z
        matrix.A21, matrix.A22, matrix.A23 = y.x, y.y, y.z
        matrix.A31, matrix.A32, matrix.A33 = direction.x, direction.y, direction.z
        copy = face.copy()
        copy.translate(-projection_center(view))
        copy.transformShape(matrix, False)
        bounds = copy.optimalBoundingBox(False, False)
        if bounds.YLength > MATCH_MM:
            raise UnresolvedDimension("Supporting plane does not project to a horizontal flat")
        matches = []
        for entry in entries:
            b = entry["record"]["bounds_mm"]
            span = b[2] - b[0]
            if (entry["visible"] and span > MATCH_MM and b[3] - b[1] <= MATCH_MM
                    and abs(b[1] - point.y) <= MATCH_MM and abs(entry["edge"].Length - span) <= MATCH_MM
                    and b[0] >= bounds.XMin - MATCH_MM and b[2] <= bounds.XMax + MATCH_MM):
                matches.append(entry)
        if not matches:
            raise UnresolvedDimension("No visible straight projected trace matches the actual hex support plane and its trimmed extent")
        selected = max(matches, key=lambda e: e["edge"].Length)
        refs.append(selected["name"])
        records.append(selected["record"])
        evidence.append({"face": face_id, "projected_support_y_mm": point.y,
                         "projected_face_x_range_mm": [bounds.XMin, bounds.XMax],
                         "equivalent_plane_trace_candidates": [e["name"] for e in matches]})
    if refs[0] == refs[1]:
        raise UnresolvedDimension("Opposing flats collapsed onto one reference")
    return {"references": refs, "projected_geometry": records,
            "projection_value_mm": abs(evidence[0]["projected_support_y_mm"] - evidence[1]["projected_support_y_mm"]),
            "source_plane_support": evidence, "match_basis": "Visible straight traces on two actual opposing planar loci, within their native trimmed extrema"}


def match_feature(shape, view, feature, entries=None):
    if feature["kind"] == "extent":
        edges = view.getVisibleEdges(True)
        box = Part.makeCompound(edges).optimalBoundingBox(False, False)
        return {"references": [""], "projected_geometry": [], "projection_value_mm": box.XLength / view.Scale,
                "match_basis": "Native horizontal extent of the complete axis-horizontal longitudinal view",
                "projected_extent_mm": [box.XMin / view.Scale, box.XMax / view.Scale]}
    entries = entries if entries is not None else inventory(view)
    return match_circle(shape, view, feature, entries) if feature["kind"] == "circle" else match_flats(shape, view, feature, entries)
