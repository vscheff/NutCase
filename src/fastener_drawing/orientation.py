"""Right-handed viewing frames derived from original native geometry."""
import math

from fastener_analysis.geometry import App, Part, bbox_record, transverse, unit, xyz


def view_frame(geometry, manual_axis=None, manual_up=None):
    recovered = geometry["axis"]
    if manual_axis is None and recovered["status"] != "identified":
        raise ValueError("Longitudinal axis unresolved. Supply a reviewed --axis X Y Z; no global-axis assumption is made.")
    axis = unit(App.Vector(*(manual_axis or recovered["direction"])))
    sign_basis = "User-reviewed axis" if manual_axis is not None else recovered["method"]
    if manual_axis is None:
        bands = [b for b in geometry["cylindrical_bands"]
                 if b["boundary_side"] == "external" and b["complete_circular_band"]]
        if bands:
            largest = max(bands, key=lambda b: b["radius_mm"])
            extent = geometry["axis_aligned_bounding_box"]["dimensions_mm"][2]
            station = sum(largest["axial_range_mm"]) / 2
            if abs(station) > extent * 0.15 and largest["axial_span_mm"] < extent * 0.5:
                if station < 0:
                    axis = -axis
                sign_basis = "Positive direction faces the largest supported terminal circular enlargement; no head role assigned"
    # A real external flat fixes roll independently of the world's coordinate axes.
    flat_ids = geometry["hexagonal_regions"][0]["faces"] if geometry["hexagonal_regions"] else []
    normal = next((f["normal_direction"] for f in geometry["faces"] if f["face"] in flat_ids), None)
    if normal is not None and transverse(App.Vector(*normal), axis).Length > 0.1:
        up = unit(transverse(App.Vector(*normal), axis))
        roll_basis = "Outward normal of an external hexagonal supporting plane"
    else:
        cylinder = next((f for f in geometry["faces"] if f["surface_type"] == "Cylinder"
                         and abs(App.Vector(*f["axis_direction"]).dot(axis)) > 0.999), None)
        if cylinder:
            # Surface axes are geometry-based, unlike an arbitrary world-Z roll.
            up = unit(transverse(App.Rotation(App.Vector(0, 0, 1), App.Vector(*cylinder["axis_direction"])).multVec(App.Vector(1, 0, 0)), axis))
            roll_basis = "Deterministic radial frame; rotationally symmetric geometry has no unique roll"
        else:
            reference = App.Vector(1, 0, 0) if abs(axis.x) < 0.9 else App.Vector(0, 1, 0)
            up = unit(transverse(reference, axis))
            roll_basis = "Deterministic transverse reference; no meaningful radial feature established"
    if manual_up is not None:
        up = unit(App.Vector(*manual_up))
        if abs(up.dot(axis)) > 1e-8:
            raise ValueError('Reviewed up direction must be perpendicular to the viewing axis')
        roll_basis = 'User-reviewed transverse up direction; source geometry unchanged'
    toward_viewer = unit(axis.cross(up))
    frames = {
        "longitudinal": {"direction": xyz(toward_viewer), "x_direction": xyz(axis)},
        # Right end on the right, left end on the left: third-angle projection.
        "right_end": {"direction": xyz(axis), "x_direction": xyz(-toward_viewer)},
        "left_end": {"direction": xyz(-axis), "x_direction": xyz(toward_viewer)},
        "isometric": {"direction": xyz(unit(axis + up + toward_viewer)),
                      "x_direction": xyz(unit(axis - toward_viewer))},
    }
    return {"axis": xyz(axis), "up": xyz(up), "front_normal": xyz(toward_viewer),
            "axis_basis": sign_basis, "roll_basis": roll_basis,
            "projection_convention": "Third angle", "frames": frames,
            "handedness": axis.cross(up).dot(toward_viewer)}


def native_projected_envelope(shape, frame):
    """Native BRep extrema in the exact viewing basis; no replacement projector."""
    direction = unit(App.Vector(*frame["direction"]))
    x = unit(App.Vector(*frame["x_direction"]))
    y = unit(direction.cross(x))
    if abs(direction.dot(x)) > 1e-8:
        raise ValueError("View direction and horizontal direction must be perpendicular")
    matrix = App.Matrix()
    matrix.A11, matrix.A12, matrix.A13 = x.x, x.y, x.z
    matrix.A21, matrix.A22, matrix.A23 = y.x, y.y, y.z
    matrix.A31, matrix.A32, matrix.A33 = direction.x, direction.y, direction.z
    copy = shape.copy()
    # Recentering avoids numerical loss for parts stored far from the origin.
    copy.translate(-shape.BoundBox.Center)
    copy.transformShape(matrix, False)
    bounds = bbox_record(copy)
    return {"width_mm": bounds["dimensions_mm"][0], "height_mm": bounds["dimensions_mm"][1],
            "depth_mm": bounds["dimensions_mm"][2], "method": bounds["method"]}
