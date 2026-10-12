"""Orientation-independent native BRep measurements and analytic feature evidence."""
import math
from collections import Counter

from .runtime import load_native_modules

App, Part = load_native_modules()
TAU = 2 * math.pi
ANGLE_EPS = math.radians(0.1)


def xyz(vector):
    return [float(vector.x), float(vector.y), float(vector.z)]


def unit(vector):
    return vector / vector.Length


def canonical(vector):
    result = unit(vector)
    values = xyz(result)
    largest = max(range(3), key=lambda index: abs(values[index]))
    return result if values[largest] >= 0 else -result


def parallel(a, b):
    return abs(unit(a).dot(unit(b))) >= math.cos(ANGLE_EPS)


def transverse(vector, axis):
    return vector - axis * vector.dot(axis)


def bbox_record(shape):
    # Native extrema on the BRep, without a tessellation and without tolerance inflation.
    bound = shape.optimalBoundingBox(False, False)
    return {"minimum_mm": [bound.XMin, bound.YMin, bound.ZMin],
            "maximum_mm": [bound.XMax, bound.YMax, bound.ZMax],
            "dimensions_mm": [bound.XLength, bound.YLength, bound.ZLength],
            "method": "TopoShape.optimalBoundingBox(useTriangulation=False, useShapeTolerance=False)"}


def middle_parameters(face):
    u0, u1, v0, v1 = face.ParameterRange
    return (u0 + u1) / 2, (v0 + v1) / 2


def comparison_tolerance(shape):
    # Recognition deliberately does not relax to a damaged edge's large BRep tolerance.
    # This is a numerical matching threshold, not an invented engineering tolerance.
    scale = max(shape.BoundBox.XLength, shape.BoundBox.YLength, shape.BoundBox.ZLength)
    return max(1e-5, scale * 1e-6)


def face_inventory(shape):
    records = []
    for index, face in enumerate(shape.Faces, 1):
        surface = face.Surface
        record = {"face": index, "surface_type": type(surface).__name__,
                  "area_mm2": face.Area, "orientation": face.Orientation,
                  "centroid_mm": xyz(face.CenterOfMass), "parameter_range": list(face.ParameterRange)}
        if isinstance(surface, (Part.Cylinder, Part.Cone)):
            record.update(axis_direction=xyz(unit(surface.Axis)), axis_point_mm=xyz(surface.Center),
                          reference_radius_mm=surface.Radius)
            if isinstance(surface, Part.Cylinder):
                record["diameter_mm"] = 2 * surface.Radius
            else:
                record.update(semi_angle_rad=surface.SemiAngle, apex_mm=xyz(surface.Apex),
                              radius_note="Cone radius is at its reference plane, not a head/body diameter.")
            # Measure the trimmed face along its own surface axis, independently
            # of whether that axis is selected as the model's common centerline.
            local_face = face.copy()
            local_face.translate(-surface.Center)
            local_face.transformShape(App.Rotation(surface.Axis, App.Vector(0, 0, 1)).toMatrix(), False)
            local_bounds = bbox_record(local_face)
            local_low, local_high = local_bounds["minimum_mm"][2], local_bounds["maximum_mm"][2]
            record["surface_axis_trimmed_range_mm"] = [local_low, local_high]
            record["surface_axis_trimmed_span_mm"] = local_high - local_low
            if isinstance(surface, Part.Cone):
                record["trimmed_radius_range_mm"] = sorted([
                    abs(surface.Radius + station * math.tan(surface.SemiAngle))
                    for station in (local_low, local_high)])
                record["trimmed_radius_basis"] = "Analytic cone law evaluated at native trimmed axial extrema"
        elif isinstance(surface, Part.Plane):
            record["normal_direction"] = xyz(unit(face.normalAt(*middle_parameters(face))))
            record["plane_point_mm"] = xyz(face.CenterOfMass)
        records.append(record)
    return records


def select_axis(shape, faces, eps):
    candidates = []
    for face in faces:
        if face["surface_type"] not in ("Cylinder", "Cone"):
            continue
        direction = canonical(App.Vector(*face["axis_direction"]))
        point = App.Vector(*face["axis_point_mm"])
        group = next((c for c in candidates if parallel(direction, c["direction"])
                      and transverse(point - c["point"], c["direction"]).Length <= eps), None)
        if group is None:
            group = {"direction": direction, "point": point, "faces": [], "area": 0.0,
                     "full_cylinder_area": 0.0}
            candidates.append(group)
        group["faces"].append(face["face"])
        group["area"] += face["area_mm2"]
        if face["surface_type"] == "Cylinder" and face["parameter_range"][1] - face["parameter_range"][0] >= TAU - 1e-6:
            group["full_cylinder_area"] += face["area_mm2"]
    candidates.sort(key=lambda c: c["area"], reverse=True)
    serialized = [{"direction": xyz(c["direction"]), "point_mm": xyz(c["point"]),
                   "supporting_faces": c["faces"], "analytic_area_mm2": c["area"],
                   "full_cylinder_area_mm2": c["full_cylinder_area"]} for c in candidates]
    if candidates:
        top = candidates[0]
        unambiguous = len(candidates) == 1 or top["area"] >= 1.5 * candidates[1]["area"]
        sufficient = top["area"] >= shape.Area * 0.15 and (
            top["full_cylinder_area"] > 0 or len(top["faces"]) >= 2)
        if unambiguous and sufficient:
            # Put the axis origin near the body, with exactly the selected analytic centerline.
            center = shape.CenterOfMass
            origin = top["point"] + top["direction"] * (center - top["point"]).dot(top["direction"])
            return {"status": "identified", "direction": xyz(top["direction"]), "origin_mm": xyz(origin),
                    "method": "Dominant common axis of coaxial analytic cylinders/cones",
                    "classification": "Common geometric axis; its longitudinal fastener role is inferred",
                    "supporting_faces": top["faces"], "candidates": serialized,
                    "sign_note": "Axis is unoriented; direction sign is only a deterministic convention."}
        return {"status": "unresolved", "reason": "Competing axes or insufficient coaxial analytic surface support", "candidates": serialized}
    # A regular hexagonal prism may have no cylindrical faces. Only use a distinct
    # inertia axis when the other two moments agree, with planar end-face support.
    principal = shape.PrincipalProperties
    moments = principal["Moments"]
    names = ("FirstAxisOfInertia", "SecondAxisOfInertia", "ThirdAxisOfInertia")
    for index in range(3):
        others = [i for i in range(3) if i != index]
        scale = max(abs(m) for m in moments)
        if (abs(moments[others[0]] - moments[others[1]]) <= scale * 0.002
                and abs(moments[index] - moments[others[0]]) > scale * 0.05):
            axis = canonical(principal[names[index]])
            end_faces = [f["face"] for f in faces if f["surface_type"] == "Plane"
                         and parallel(App.Vector(*f["normal_direction"]), axis)]
            if len(end_faces) >= 2:
                return {"status": "identified", "direction": xyz(axis), "origin_mm": xyz(shape.CenterOfMass),
                        "method": "Distinct principal inertia axis supported by planar end faces",
                        "classification": "Geometric symmetry-axis hypothesis; longitudinal role inferred",
                        "supporting_faces": end_faces, "candidates": serialized}
    return {"status": "unresolved", "reason": "No dominant analytic centerline or supported unique inertia axis", "candidates": serialized}


def aligned_shape(shape, axis_report):
    axis = App.Vector(*axis_report["direction"])
    origin = App.Vector(*axis_report["origin_mm"])
    rotation = App.Rotation(axis, App.Vector(0, 0, 1))
    copy = shape.copy()
    copy.translate(-origin)
    copy.transformShape(rotation.toMatrix(), False)
    return copy, rotation


def _angular_intervals(face, rotation, origin, axis):
    u0, u1, v0, v1 = face.ParameterRange
    span = min(TAU, u1 - u0)
    if span >= TAU - 1e-6:
        return [(0.0, TAU)]
    point = rotation.multVec(face.valueAt(u0, (v0 + v1) / 2) - origin)
    start = math.atan2(point.y, point.x)
    finish = start + (span if face.Surface.Axis.dot(axis) >= 0 else -span)
    low, high = sorted((start, finish))
    low %= TAU
    high = low + span
    return [(low, min(high, TAU))] + ([(0.0, high - TAU)] if high > TAU else [])


def merged_intervals(intervals, eps):
    merged = []
    for low, high in sorted(intervals):
        if merged and low <= merged[-1][1] + eps:
            merged[-1][1] = max(high, merged[-1][1])
        else:
            merged.append([low, high])
    return merged


def analyze_aligned_faces(shape, aligned, faces, axis_report, rotation, eps):
    origin = App.Vector(*axis_report["origin_mm"])
    axis = App.Vector(*axis_report["direction"])
    groups = []
    for record, face, local_face in zip(faces, shape.Faces, aligned.Faces):
        bounds = bbox_record(local_face)
        record["axial_range_mm"] = [bounds["minimum_mm"][2], bounds["maximum_mm"][2]]
        record["axial_span_mm"] = record["axial_range_mm"][1] - record["axial_range_mm"][0]
        if record["surface_type"] == "Plane":
            normal = App.Vector(*record["normal_direction"])
            record["relation_to_axis"] = "end_or_shoulder" if parallel(normal, axis) else "side_flat" if abs(normal.dot(axis)) <= math.sin(ANGLE_EPS) else "oblique"
            record["plane_offset_from_axis_origin_mm"] = normal.dot(face.CenterOfMass - origin)
        if record["surface_type"] != "Cylinder":
            continue
        surface = face.Surface
        coaxial = parallel(surface.Axis, axis) and transverse(surface.Center - origin, axis).Length <= eps
        record["coaxial_with_selected_axis"] = coaxial
        point = face.valueAt(*middle_parameters(face))
        radial = transverse(point - surface.Center, unit(surface.Axis))
        radial_dot = face.normalAt(*middle_parameters(face)).dot(unit(radial))
        record["boundary_side"] = "external" if radial_dot > 0.5 else "internal" if radial_dot < -0.5 else "unresolved"
        if not coaxial:
            continue
        low, high = record["axial_range_mm"]
        # Equal end stations allow split 180-degree faces to form one full band.
        group = next((g for g in groups if abs(g["radius_mm"] - surface.Radius) <= eps
                      and g["boundary_side"] == record["boundary_side"]
                      and abs(g["axial_range_mm"][0] - low) <= eps
                      and abs(g["axial_range_mm"][1] - high) <= eps), None)
        if group is None:
            group = {"radius_mm": surface.Radius, "diameter_mm": 2 * surface.Radius,
                     "axial_range_mm": [low, high], "axial_span_mm": high - low,
                     "boundary_side": record["boundary_side"], "faces": [], "area_mm2": 0.0,
                     "_angles": []}
            groups.append(group)
        group["faces"].append(record["face"])
        group["area_mm2"] += record["area_mm2"]
        group["_angles"].extend(_angular_intervals(face, rotation, origin, axis))
    for group in groups:
        intervals = merged_intervals(group.pop("_angles"), 1e-6)
        group["angular_coverage_rad"] = sum(high - low for low, high in intervals)
        expected = TAU * group["radius_mm"] * group["axial_span_mm"]
        group["rectangular_band_area_ratio"] = group["area_mm2"] / expected if expected > eps else None
        group["complete_circular_band"] = (
            group["angular_coverage_rad"] >= TAU - 1e-5 and expected > eps
            and abs(group["rectangular_band_area_ratio"] - 1) <= 0.001)
    return groups


def hexagonal_regions(faces, axis_report, eps):
    """Require six external supporting planes, three equal opposite spacings and 60-degree normals."""
    axis = App.Vector(*axis_report["direction"])
    eligible = [f for f in faces if f["surface_type"] == "Plane" and f.get("relation_to_axis") == "side_flat"
                and f["plane_offset_from_axis_origin_mm"] > eps]
    regions = []
    # Anchor on axial overlap, allowing chamfers and rounded corners.
    for anchor in eligible:
        station = sum(anchor["axial_range_mm"]) / 2
        active = [f for f in eligible if f["axial_range_mm"][0] + eps < station < f["axial_range_mm"][1] - eps]
        if len(active) != 6:
            continue
        ids = sorted(f["face"] for f in active)
        if any(r["faces"] == ids for r in regions):
            continue
        reference = unit(transverse(App.Vector(*active[0]["normal_direction"]), axis))
        cross = axis.cross(reference)
        ordered = sorted(active, key=lambda f: math.atan2(App.Vector(*f["normal_direction"]).dot(cross), App.Vector(*f["normal_direction"]).dot(reference)) % TAU)
        normals = [App.Vector(*f["normal_direction"]) for f in ordered]
        if any(abs(normals[i].dot(normals[(i + 1) % 6]) - 0.5) > 1e-4 for i in range(6)):
            continue
        offsets = [f["plane_offset_from_axis_origin_mm"] for f in ordered]
        if max(offsets) - min(offsets) > eps * 2:
            continue
        low = max(f["axial_range_mm"][0] for f in active)
        high = min(f["axial_range_mm"][1] for f in active)
        if high - low <= eps:
            continue
        spacings = [offsets[i] + offsets[i + 3] for i in range(3)]
        regions.append({"classification": "External region bounded by six regular hexagonal supporting planes",
                        "classification_basis": "Equal offsets, three opposite parallel pairs, 60-degree normal spacing, common axial overlap",
                        "across_flats_mm": sum(spacings) / 3, "opposite_plane_spacings_mm": spacings,
                        "axial_range_mm": [low, high], "faces": ids,
                        "semantic_role": "Head/body role not established by plane geometry alone"})
    return regions


def analyze_geometry(shape):
    """Analyze one solid, using its own native face numbering (not an assembly)."""
    if shape.ShapeType != "Solid":
        raise ValueError("analyze_geometry requires a single Solid; use shape.Solids component-by-component")
    # Some native operations return a generic Part.Shape wrapper around a Solid;
    # the specialized Solid wrapper exposes inertia and mass-center properties.
    shape = shape.Solids[0]
    eps = comparison_tolerance(shape)
    faces = face_inventory(shape)
    report = {"global_bounding_box": bbox_record(shape), "surface_type_counts": dict(Counter(f["surface_type"] for f in faces)),
              "volume_mm3": shape.Volume, "surface_area_mm2": shape.Area,
              "numerical_comparison_threshold_mm": eps,
              "threshold_note": "Algorithmic geometry-matching threshold, not a manufacturing tolerance",
              "faces": faces}
    axis = select_axis(shape, faces, eps)
    report["axis"] = axis
    if axis["status"] != "identified":
        report.update(cylindrical_bands=[], hexagonal_regions=[])
        return report, None
    aligned, rotation = aligned_shape(shape, axis)
    report["axis_aligned_bounding_box"] = bbox_record(aligned)
    report["cylindrical_bands"] = analyze_aligned_faces(shape, aligned, faces, axis, rotation, eps)
    report["hexagonal_regions"] = hexagonal_regions(faces, axis, eps)
    return report, aligned
