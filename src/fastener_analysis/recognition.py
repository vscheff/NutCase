"""Conservative semantic hypotheses; dimensions are tied to explicit BRep evidence."""
import math

from .geometry import App, Part, TAU, parallel, transverse, unit

DIMENSION_NAMES = (
    "overall_length", "length_under_head", "head_height", "head_diameter",
    "flange_diameter", "shank_diameter", "thread_major_diameter", "threaded_length", "across_flats",
)


def unrecognized(reason):
    return {"status": "unrecognized", "value_mm": None, "reason": reason, "requires_manual_review": True}


def recognized(value, evidence, meaning, validation):
    return {"status": "recognized", "value_mm": value, "measurement_basis": "Native BRep geometry",
            "meaning": meaning, "evidence": evidence,
            "requires_manual_review": True,
            "geometry_quality": validation["status"],
            "review_note": "All outputs are preliminary; no manufacturing tolerance is assigned."}


def _circle_on_axis(edge, axis, origin, radius, eps):
    curve = edge.Curve
    return (isinstance(curve, Part.Circle) and parallel(curve.Axis, axis)
            and abs(curve.Radius - radius) <= eps
            and transverse(curve.Center - origin, axis).Length <= eps)


def _shoulder_rim(shape, face_record, geometry, radius):
    axis = App.Vector(*geometry["axis"]["direction"])
    origin = App.Vector(*geometry["axis"]["origin_mm"])
    eps = geometry["numerical_comparison_threshold_mm"]
    # STEP may split a circular rim into semicircular edges. A closed wire of
    # coaxial equal-radius arcs with full circumference is still a circular rim.
    return any(wire.isClosed()
               and all(_circle_on_axis(edge, axis, origin, radius, eps) for edge in wire.Edges)
               and abs(wire.Length - TAU * radius) <= eps * 10
               for wire in shape.Faces[face_record["face"] - 1].Wires)


def detect_threads(shape, geometry):
    """Helical curves are sampled only for classification diagnostics, never nominal dimensions.

    A smooth cylinder cannot establish either a simplified thread or an unthreaded part.
    Explicit-thread appearance requires paired helical boundaries on a shared nonanalytic
    face, two winding radii, repeated pitch, and material filling an axial shaft core.
    Internal and very short threads deliberately remain unresolved in this first version.
    """
    result = {"status": "cannot_determine", "classification_basis": "Inferred from geometry; STEP filenames are not used",
              "reason": "No sufficient repeated helical flank evidence. Smooth bores/shafts do not distinguish simplified threads from unthreaded geometry.",
              "helical_edge_evidence": [], "helical_chain_evidence": [], "limitations": [
                  "Semantic/cosmetic STEP thread annotations are not interpreted.",
                  "Internal threads, fewer than two turns, conical threads and faceted threads require manual review.",
                  "Absence of detected helices does not prove that modeled threads are absent.",
              ]}
    if geometry["axis"]["status"] != "identified":
        result["reason"] = "No reliable axis for helical analysis."
        return result
    axis = App.Vector(*geometry["axis"]["direction"])
    origin = App.Vector(*geometry["axis"]["origin_mm"])
    x = unit(transverse(App.Vector(1, 0, 0) if abs(axis.x) < 0.9 else App.Vector(0, 1, 0), axis))
    y = axis.cross(x)
    eps = geometry["numerical_comparison_threshold_mm"]
    for index, edge in enumerate(shape.Edges, 1):
        if isinstance(edge.Curve, (Part.Line, Part.Circle)):
            continue
        try:
            points = edge.discretize(Number=193)
        except Exception as exc:
            result.setdefault("diagnostic_errors", []).append(f"Edge {index} sampling failed: {exc}")
            continue
        radii, stations, angles = [], [], []
        for point in points:
            delta = point - origin
            radial = transverse(delta, axis)
            radii.append(radial.Length)
            stations.append(delta.dot(axis))
            angle = math.atan2(delta.dot(y), delta.dot(x))
            if angles:
                angle += TAU * round((angles[-1] - angle) / TAU)
            angles.append(angle)
        if not angles or min(radii) <= eps:
            continue
        winding = angles[-1] - angles[0]
        # STEP often splits a crest helix at every cylindrical seam. Short native
        # segments are diagnostics until they can be joined into a repeated chain.
        if abs(winding) < TAU * 0.15:
            continue
        radius = sum(radii) / len(radii)
        if max(radii) - min(radii) > max(eps * 10, radius * 0.001):
            continue
        mean_angle, mean_station = sum(angles) / len(angles), sum(stations) / len(stations)
        denominator = sum((a - mean_angle) ** 2 for a in angles)
        if denominator <= 1e-12:
            continue
        slope = sum((a - mean_angle) * (z - mean_station) for a, z in zip(angles, stations)) / denominator
        pitch = slope * TAU
        residual = max(abs(z - mean_station - slope * (a - mean_angle)) for a, z in zip(angles, stations))
        if abs(pitch) <= eps * 10 or residual > max(eps * 10, abs(pitch) * 0.005):
            continue
        monotone = sum((angles[i + 1] - angles[i]) * winding >= 0 for i in range(len(angles) - 1))
        if monotone < 0.99 * (len(angles) - 1):
            continue
        adjacent = [i for i, face in enumerate(shape.Faces, 1) if any(edge.isSame(e) for e in face.Edges)]
        result["helical_edge_evidence"].append({
            "edge": index, "supporting_faces": adjacent, "sample_count": len(points),
            "turns_observed": abs(winding) / TAU, "fitted_radius_mm": radius,
            "fitted_signed_pitch_mm": pitch, "max_fit_residual_mm": residual,
            "fitted_axial_phase_mm": mean_station - slope * mean_angle,
            "axial_range_mm": [min(stations), max(stations)],
            "value_note": "Sampled native-curve classification diagnostic; not a recognized drawing dimension",
        })
    segments = result["helical_edge_evidence"]
    chains = []
    for segment in sorted(segments, key=lambda h: h["axial_range_mm"][0]):
        group = None
        for chain in chains:
            pitch = chain["fitted_signed_pitch_mm"]
            phase_delta = segment["fitted_axial_phase_mm"] - chain["fitted_axial_phase_mm"]
            phase_delta -= abs(pitch) * round(phase_delta / abs(pitch))
            if (abs(segment["fitted_radius_mm"] - chain["fitted_radius_mm"]) <= eps * 10
                    and abs(segment["fitted_signed_pitch_mm"] - pitch) <= abs(pitch) * 0.01
                    and abs(phase_delta) <= max(eps * 10, abs(pitch) * 0.005)
                    and segment["axial_range_mm"][0] <= chain["axial_range_mm"][1] + eps * 10):
                group = chain
                break
        if group is None:
            group = {key: segment[key] for key in ("fitted_radius_mm", "fitted_signed_pitch_mm", "fitted_axial_phase_mm")}
            group.update(edges=[], supporting_faces=[], axial_range_mm=list(segment["axial_range_mm"]))
            chains.append(group)
        group["edges"].append(segment["edge"])
        group["supporting_faces"] = sorted(set(group["supporting_faces"]) | set(segment["supporting_faces"]))
        group["axial_range_mm"][1] = max(group["axial_range_mm"][1], segment["axial_range_mm"][1])
    for chain in chains:
        chain["turns_observed"] = (chain["axial_range_mm"][1] - chain["axial_range_mm"][0]) / abs(chain["fitted_signed_pitch_mm"])
        chain["value_note"] = "Joined sampled native curves; classification diagnostic only"
    helices = [chain for chain in chains if chain["turns_observed"] >= 1.75]
    result["helical_chain_evidence"] = helices
    nonanalytic = {f["face"] for f in geometry["faces"]
                   if f["surface_type"] not in ("Cylinder", "Cone", "Plane", "Sphere", "Toroid")}
    for i, first in enumerate(helices):
        for second in helices[i + 1:]:
            pitch = first["fitted_signed_pitch_mm"]
            common = set(first["supporting_faces"]) & set(second["supporting_faces"]) & nonanalytic
            low = max(first["axial_range_mm"][0], second["axial_range_mm"][0])
            high = min(first["axial_range_mm"][1], second["axial_range_mm"][1])
            if (not common or abs(pitch - second["fitted_signed_pitch_mm"]) > abs(pitch) * 0.01
                    or abs(first["fitted_radius_mm"] - second["fitted_radius_mm"]) < eps * 10
                    or high - low < abs(pitch) * 1.75):
                continue
            # A wire coil/spring has helical curves too. Require a solid, continuous core.
            core = all(shape.isInside(origin + axis * (low + (high - low) * j / 10), eps, True)
                       for j in range(1, 10))
            if core:
                result.update(status="explicitly_modeled", reason="Appears to contain external threads: repeated paired helical flank boundaries and continuous shaft core.",
                              supporting_edges=sorted(set(first["edges"] + second["edges"])), supporting_faces=sorted(common),
                              classification_confidence="Geometry-supported appearance; engineering function requires review")
                return result
    if segments:
        result["reason"] = "Helical geometry observed, but thread flanks and a continuous shaft core were not sufficiently established."
    return result


def _head_hypotheses(shape, geometry, bands, hexagons, internal_bands):
    if internal_bands:
        return [], "Coaxial internal cylindrical geometry is present; hollow-body geometry does not establish a screw/bolt head or shank."
    eps = geometry["numerical_comparison_threshold_mm"]
    bounds = geometry["axis_aligned_bounding_box"]
    end_low, end_high = bounds["minimum_mm"][2], bounds["maximum_mm"][2]
    heads = []
    shoulders = [f for f in geometry["faces"] if f.get("relation_to_axis") == "end_or_shoulder"
                 and f["axial_span_mm"] <= eps * 2]
    for shoulder in shoulders:
        station = sum(shoulder["axial_range_mm"]) / 2
        if not end_low + eps < station < end_high - eps:
            continue
        for shaft in bands:
            if shaft["boundary_side"] != "external" or not shaft["complete_circular_band"]:
                continue
            for sign in (-1, 1):
                shaft_near = shaft["axial_range_mm"][1 if sign == 1 else 0]
                shaft_far = shaft["axial_range_mm"][0 if sign == 1 else 1]
                end = end_low if sign == 1 else end_high
                if abs(shaft_near - station) > eps or abs(shaft_far - end) > eps:
                    continue
                if not _shoulder_rim(shape, shoulder, geometry, shaft["radius_mm"]):
                    continue
                for descriptor in [*bands, *hexagons]:
                    kind = "hexagonal" if "across_flats_mm" in descriptor else "circular"
                    if kind == "circular" and (descriptor["boundary_side"] != "external" or not descriptor["complete_circular_band"]):
                        continue
                    size = descriptor["across_flats_mm"] if kind == "hexagonal" else descriptor["diameter_mm"]
                    near = descriptor["axial_range_mm"][0 if sign == 1 else 1]
                    far = descriptor["axial_range_mm"][1 if sign == 1 else 0]
                    head_end = end_high if sign == 1 else end_low
                    # Initial implementation requires an unambiguous, unchamfered terminal head.
                    if (size <= shaft["diameter_mm"] + eps * 10 or abs(near - station) > eps
                            or abs(far - head_end) > eps):
                        continue
                    heads.append({"classification": "headed_shaft", "classification_basis": "Single solid with terminal enlarged region, annular bearing shoulder and complete circular shaft extending to opposite end",
                                  "head_shape": kind, "shoulder_face": shoulder["face"], "shoulder_station_mm": station,
                                  "head_end_station_mm": head_end, "shaft_end_station_mm": end,
                                  "head_faces": descriptor["faces"], "shaft_faces": shaft["faces"],
                                  "head_size_mm": size, "shank_diameter_mm": shaft["diameter_mm"]})
    # Multiple hypotheses are deliberately not resolved by assuming a standard fastener family.
    return heads, "No unique terminal head, circular shaft and bearing shoulder arrangement met the recognition rules."


def _flange_candidates(shape, geometry, bands, hexagons):
    eps = geometry["numerical_comparison_threshold_mm"]
    candidates = []
    end_low = geometry["axis_aligned_bounding_box"]["minimum_mm"][2]
    end_high = geometry["axis_aligned_bounding_box"]["maximum_mm"][2]
    external = [b for b in bands if b["boundary_side"] == "external" and b["complete_circular_band"]]
    for band in external:
        radius = band["radius_mm"]
        if band["axial_span_mm"] >= radius * 0.4:
            continue
        # Require enlargement over the body, including the hexagonal corner envelope.
        other_sizes = [b["diameter_mm"] for b in external if b is not band]
        other_sizes += [h["across_flats_mm"] * 2 / math.sqrt(3) for h in hexagons]
        if not other_sizes or band["diameter_mm"] <= max(other_sizes) + eps * 10:
            continue
        low, high = band["axial_range_mm"]
        for shoulder in geometry["faces"]:
            if shoulder.get("relation_to_axis") != "end_or_shoulder" or shoulder["axial_span_mm"] > eps * 2:
                continue
            station = sum(shoulder["axial_range_mm"]) / 2
            if min(abs(station - low), abs(station - high)) > eps:
                continue
            if not _shoulder_rim(shape, shoulder, geometry, radius):
                continue
            if min(abs(low - end_low), abs(high - end_high)) > radius * 0.4:
                continue
            # The annular shoulder must connect a narrower region on the other side.
            narrower = [f for f in [*external, *hexagons] if f is not band
                        and (f["axial_range_mm"][1] <= station + eps if abs(station - low) <= eps
                             else f["axial_range_mm"][0] >= station - eps)]
            if not narrower or len(shape.Faces[shoulder["face"] - 1].Wires) < 2:
                continue
            candidates.append({"diameter_mm": band["diameter_mm"], "faces": band["faces"],
                               "shoulder_face": shoulder["face"], "axial_range_mm": band["axial_range_mm"],
                               "classification": "Terminal annular flange-like enlargement",
                               "classification_basis": "Complete circular band, larger than the coaxial body, with annular shoulder and narrower body on the other side"})
    return candidates


def recognize_features(shape, geometry, validation):
    if shape.ShapeType == "Solid":
        shape = shape.Solids[0]
    dimensions = {name: unrecognized("Insufficient geometric evidence for this feature role.") for name in DIMENSION_NAMES}
    threads = detect_threads(shape, geometry)
    report = {"dimensions": dimensions, "feature_classifications": [], "threads": threads,
              "manual_review": [], "recognition_scope": "Conservative subset of circular shafts, terminal circular/hexagonal heads and annular flanges; no standard fastener sizes assumed"}
    usable = validation["basic_valid"] and validation["brep_check"]["status"] == "passed" and shape.isClosed() and shape.Volume > 0
    if not usable:
        for name in dimensions:
            dimensions[name] = unrecognized("Invalid, open or zero-volume geometry; repair/review before recognizing dimensions.")
        report["manual_review"].append("Geometry validation prevents recognition; raw geometry measurements are diagnostic only.")
        return report
    if geometry["axis"]["status"] != "identified":
        report["manual_review"].append("Longitudinal axis unresolved; global bounding box is not an overall fastener length.")
        return report
    bounds = geometry["axis_aligned_bounding_box"]
    dimensions["overall_length"] = recognized(bounds["dimensions_mm"][2],
        {"axis": geometry["axis"]["direction"], "end_stations_mm": [bounds["minimum_mm"][2], bounds["maximum_mm"][2]], "method": bounds["method"]},
        "Overall geometric extent along the selected common axis; fastener-axis role remains inferred", validation)
    bands = geometry["cylindrical_bands"]
    hexagons = geometry["hexagonal_regions"]
    internal = [b for b in bands if b["boundary_side"] == "internal"]
    if internal:
        report["feature_classifications"].append({"classification": "coaxial_hollow_body",
            "classification_basis": "Inward-facing coaxial cylindrical surfaces",
            "supporting_faces": [f for b in internal for f in b["faces"]],
            "semantic_note": "Does not establish nut type, thread size, head or shank."})
    heads, head_reason = _head_hypotheses(shape, geometry, bands, hexagons, internal)
    if len(heads) == 1:
        head = heads[0]
        report["feature_classifications"].append(head)
        evidence = {"shoulder_face": head["shoulder_face"], "head_faces": head["head_faces"], "shaft_faces": head["shaft_faces"]}
        dimensions["head_height"] = recognized(abs(head["head_end_station_mm"] - head["shoulder_station_mm"]), evidence, "Terminal head extent from bearing shoulder to outer end", validation)
        dimensions["length_under_head"] = recognized(abs(head["shoulder_station_mm"] - head["shaft_end_station_mm"]), evidence, "Bearing shoulder to opposite shaft end", validation)
        dimensions["shank_diameter"] = recognized(head["shank_diameter_mm"], {"faces": head["shaft_faces"]}, "Complete external circular shaft band; threaded/unthreaded function unresolved", validation)
        name = "across_flats" if head["head_shape"] == "hexagonal" else "head_diameter"
        dimensions[name] = recognized(head["head_size_mm"], {"faces": head["head_faces"]}, "Opposite head plane spacing" if name == "across_flats" else "Analytic circular head diameter", validation)
    else:
        for name in ("head_height", "length_under_head", "head_diameter", "across_flats", "shank_diameter"):
            dimensions[name] = unrecognized(head_reason if not heads else "Multiple possible head/shaft arrangements; no unique identification.")
        report["manual_review"].append(dimensions["head_height"]["reason"])
    flanges = _flange_candidates(shape, geometry, bands, hexagons)
    # A lone circular bolt head also resembles a flange. Only assign the generic flange
    # role here when a hollow body has been established and no headed shaft competes.
    if len(flanges) == 1 and internal and not heads:
        flange = flanges[0]
        report["feature_classifications"].append(flange)
        dimensions["flange_diameter"] = recognized(flange["diameter_mm"],
            {"faces": flange["faces"], "shoulder_face": flange["shoulder_face"]}, "Circular diameter of a terminal annular flange-like feature; engineering function inferred", validation)
    elif flanges:
        report["manual_review"].append("Radial enlargement detected, but flange/head role is ambiguous.")
    if hexagons and dimensions["across_flats"]["status"] != "recognized":
        report["manual_review"].append("External hexagonal supporting-plane spacing is measured in geometry.hexagonal_regions; its head role is unresolved.")
    if threads["status"] == "explicitly_modeled":
        edge_ids = set(threads["supporting_edges"])
        radius = max(h["fitted_radius_mm"] for h in threads["helical_edge_evidence"] if h["edge"] in edge_ids)
        crest_faces = []
        for record, face in zip(geometry["faces"], shape.Faces):
            if (record["surface_type"] == "Cylinder" and record.get("boundary_side") == "external"
                    and record.get("coaxial_with_selected_axis")
                    and abs(record["reference_radius_mm"] - radius) <= geometry["numerical_comparison_threshold_mm"] * 10
                    and any(shape.Edges[index - 1].isSame(edge) for index in edge_ids for edge in face.Edges)):
                crest_faces.append(record)
        radii = [f["reference_radius_mm"] for f in crest_faces]
        if radii and max(radii) - min(radii) <= geometry["numerical_comparison_threshold_mm"]:
            dimensions["thread_major_diameter"] = recognized(2 * radii[0], {"faces": [f["face"] for f in crest_faces], "helical_edges": sorted(edge_ids)}, "External analytic cylindrical thread crest diameter", validation)
        dimensions["threaded_length"] = unrecognized("Helical flank region observed, but nominal thread endpoints/runout are not established.")
    report["manual_review"].append(threads["reason"])
    if validation["boolean_check"]["status"] != "passed":
        report["manual_review"].append("Extended Boolean geometry check failed; inspect/repair the model before downstream drawing or manufacturing use.")
    return report
