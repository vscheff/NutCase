"""Native document/PDF export and reopen checks, without a separate drawing engine."""
import hashlib
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from fastener_analysis.geometry import App, bbox_record
from .views import wait_for_views


def shape_signature(shape):
    faces, edges = [], []
    for face in shape.Faces:
        u0, u1, v0, v1 = face.ParameterRange
        faces.append({"surface_type": type(face.Surface).__name__, "orientation": face.Orientation,
                      "parameter_range": list(face.ParameterRange), "area_mm2": face.Area,
                      "native_surface_probes_mm": [[*face.valueAt(u0 + (u1 - u0) * u, v0 + (v1 - v0) * v)]
                                                   for u in (0.0, 0.5, 1.0) for v in (0.0, 0.5, 1.0)]})
    for edge in shape.Edges:
        first, last = edge.FirstParameter, edge.LastParameter
        edges.append({"curve_type": type(edge.Curve).__name__, "orientation": edge.Orientation,
                      "length_mm": edge.Length, "parameter_range": [first, last],
                      "native_curve_probes_mm": [[*edge.valueAt(first + (last - first) * t)] for t in (0, 0.25, 0.5, 0.75, 1)]})
    return {"brep_sha256": hashlib.sha256(shape.exportBrepToString().encode("utf-8")).hexdigest(),
            "volume_mm3": shape.Volume, "area_mm2": shape.Area, "bounding_box": bbox_record(shape),
            "counts": {name: len(getattr(shape, name)) for name in ("Solids", "Faces", "Edges", "Vertexes")},
            "face_geometry": faces, "edge_geometry": edges}


def compare_signatures(expected, actual, numerical_threshold=1e-8):
    """Native persistence may add identity locations and round quaternion/knots.

    Compare topology, types, extents, areas, volume and per-face/edge native
    geometry probes; retain serialization hashes without treating them as geometry.
    This threshold is a numerical roundtrip check, not a manufacturing tolerance.
    """
    maximum = 0.0

    def compare(before, after, path):
        nonlocal maximum
        if isinstance(before, dict):
            if set(before) != set(after):
                raise RuntimeError(f"Geometry signature keys differ at {path}")
            for key in before:
                if key != "brep_sha256":
                    compare(before[key], after[key], path + "." + key)
        elif isinstance(before, list):
            if len(before) != len(after):
                raise RuntimeError(f"Geometry signature list length differs at {path}")
            for index, (first, second) in enumerate(zip(before, after)):
                compare(first, second, f"{path}[{index}]")
        elif isinstance(before, (int, float)):
            delta = abs(before - after)
            maximum = max(maximum, delta)
            if delta > numerical_threshold:
                raise RuntimeError(f"Saved/reopened geometry differs at {path}: {delta}")
        elif before != after:
            raise RuntimeError(f"Saved/reopened geometry differs at {path}")

    compare(expected, actual, "source")
    return {"geometry_equivalent": True, "brep_serialization_identical": expected["brep_sha256"] == actual["brep_sha256"],
            "maximum_numeric_deviation": maximum, "numerical_roundtrip_threshold": numerical_threshold,
            "comparison_basis": "Native topology/types, bounding extrema, area/volume, UV bounds, 9 surface probes per face and 5 curve probes per edge"}


def export_native(doc, page, destination, TechDrawGui):
    """Save, close, then render the persisted native drawing; owns doc lifetime."""
    name = doc.Name
    try:
        return _export_native(doc, page, destination, TechDrawGui)
    finally:
        if name in App.listDocuments():
            App.closeDocument(name)


def _export_native(doc, page, destination, TechDrawGui):
    destination = Path(destination)
    project = Path(str(destination) + ".FCStd")
    pdf = Path(str(destination) + ".pdf")
    # No offscreen OpenGL thumbnail is needed for an editable technical drawing.
    preferences = App.ParamGet("User parameter:BaseApp/Preferences/Document")
    thumbnail = preferences.GetBool("SaveThumbnail", True)
    try:
        preferences.SetBool("SaveThumbnail", False)
        doc.saveAs(str(project))
    finally:
        preferences.SetBool("SaveThumbnail", thumbnail)
    # Extent creation/save can leave the initial Qt scene without its base
    # view. Render a fresh native scene from the persisted project, rather than
    # accepting a PDF that omitted geometry while retaining valid raw values.
    name = doc.Name
    App.closeDocument(name)
    from .views import flush_gui_deletions
    flush_gui_deletions()
    reopened = App.openDocument(str(project))
    temporary_pdf = pdf.with_name(pdf.stem + ".pending.pdf")
    if temporary_pdf.exists():
        temporary_pdf.unlink()
    try:
        page = reopened.getObject("DrawingPage")
        page.ViewObject.show()
        wait_for_views(reopened, [v for v in page.Views if v.isDerivedFrom("TechDraw::DrawViewPart")])
        dimensions = json.loads(page.DimensionVerificationJSON) if "DimensionVerificationJSON" in page.PropertiesList else {}
        from .dimensions import verify_dimensions,displayed_text
        verify_dimensions(reopened, dimensions)
        from .section_material import verify_overlay
        verify_overlay(reopened)
        rendered_svg = Path(str(destination) + ".render.svg")
        TechDrawGui.exportPageAsSvg(page, str(rendered_svg))
        root = ET.parse(rendered_svg).getroot()
        # Qt can split one datum into several SVG text runs (e.g. the
        # diameter glyph and digits). Join sibling runs of the same item.
        actual_text = ["".join("".join(child.itertext()) for child in element
                              if child.tag.rsplit("}", 1)[-1] == "text").strip()
                       for element in root.iter()]
        expected_text = [displayed_text(reopened.getObject(record['object_name']),record)
                         for record in dimensions.values() if record["status"] == "created"]
        if any(text not in actual_text for text in expected_text):
            raise RuntimeError("Persisted native drawing scene omitted dimension text before PDF export")
        if any(element.tag.rsplit("}", 1)[-1] == "image" for element in root.iter()):
            raise RuntimeError("Native drawing scene unexpectedly contains raster images")
        render_checks = {"all_dimension_text_present": True, "actual_dimension_labels": expected_text,
                         "no_raster_images_in_native_scene": True,
                         "basis": "Native SVG scene export from reopened FCStd immediately before native PDF export; PDF still needs independent rendering review"}
        TechDrawGui.exportPageAsPdf(page, str(temporary_pdf))
    finally:
        App.closeDocument(reopened.Name)
    if not temporary_pdf.is_file() or temporary_pdf.stat().st_size < 1000 or temporary_pdf.read_bytes()[:5] != b"%PDF-":
        raise RuntimeError("Native TechDraw PDF export produced no valid PDF; GUI-backed page rendering must be available")
    temporary_pdf.replace(pdf)
    if not project.is_file() or not zipfile.is_zipfile(project):
        raise RuntimeError("FreeCAD document export did not produce a readable FCStd archive")
    with zipfile.ZipFile(project) as archive:
        embedded = [name for name in archive.namelist() if name.lower().endswith(".svg")]
    if not embedded:
        raise RuntimeError("FCStd does not contain its drawing template; standalone reopen is not verified")
    return {"project": str(project), "pdf": str(pdf), "rendered_svg": str(rendered_svg),
            "template_embedded": embedded, "native_render_checks": render_checks}


def verify_reopen(project, original_signature, expected_scale, expected_views, layout, frames, dimension_reports=None):
    reopened = App.openDocument(str(project))
    try:
        source = reopened.getObject("OriginalSTEP")
        page = reopened.getObject("DrawingPage")
        if source is None or page is None:
            raise RuntimeError("Reopened document is missing source geometry or TechDraw page")
        geometry_check = compare_signatures(original_signature, shape_signature(source.Shape))
        from .section_material import verify_overlay
        overlay_check=verify_overlay(reopened)
        from .drafting import verify_centerlines
        centerline_count=verify_centerlines(reopened,json.loads(page.DraftingCenterlinesJSON)) if 'DraftingCenterlinesJSON' in page.PropertiesList else 0
        views = [obj for obj in page.Views if obj.isDerivedFrom("TechDraw::DrawViewPart") and obj.Name!='SectionHatchOverlay']
        if len(views) != expected_views or abs(page.Scale - expected_scale) > 1e-10:
            raise RuntimeError("Saved/reopened native views or page scale differ from the generated sheet")
        wait_for_views(reopened, views)
        for role, position in layout["positions"].items():
            view = reopened.getObject(role.title().replace("_", ""))
            if view is None or abs(view.X.Value - position["x_mm"]) > 1e-8 or abs(view.Y.Value - position["y_mm"]) > 1e-8:
                raise RuntimeError("Saved/reopened native view placement differs from the sheet layout")
            expected_frame = frames["frames"][role]
            if any(abs(actual - expected) > 1e-8
                   for actual, expected in zip([*view.Direction, *view.XDirection],
                                              expected_frame["direction"] + expected_frame["x_direction"])):
                raise RuntimeError("Saved/reopened projection directions differ from the geometric viewing frame")
            if role=="section":
                if not view.isDerivedFrom("TechDraw::DrawViewSection") or view.BaseView!=reopened.RightEnd or view.SectionSymbol!="A" or view.CutSurfaceDisplay!="PatHatch" or view.NameGeomPattern!="Diagonal4":
                    raise RuntimeError("Saved/reopened native section definition or hatch changed")
                definition=json.loads(page.DrawingSectionJSON)
                if (any(abs(a-b)>1e-8 for a,b in zip(view.SectionOrigin,definition["origin_mm"]))
                    or any(abs(a-b)>1e-8 for a,b in zip(view.SectionNormal,definition["normal"]))
                    or view.SectionDirection!=definition["direction"] or abs(view.HatchScale-definition["hatch_scale"])>1e-8
                    or not view.FileGeomPattern or not Path(view.FileGeomPattern).is_file()):
                    raise RuntimeError("Saved/reopened section plane, direction or embedded hatch definition changed")
            label = reopened.getObject(view.Name + "Label")
            if label is None or abs(label.X.Value - position["label_x_mm"]) > 1e-8 or abs(label.Y.Value - position["label_y_mm"]) > 1e-8:
                raise RuntimeError("Saved/reopened view caption placement differs from the sheet layout")
        detail=reopened.getObject('OpeningDetail')
        if detail:
            binder=reopened.getObject('OpeningBoundary')
            if detail.Source!=[binder] or len(binder.Support)!=1 or binder.Support[0][0]!=source:
                raise RuntimeError('Opening detail lost native association with original source edges')
            expected_edges=json.loads(page.DrawingSectionJSON).get('opening_detail_source_edges',[])
            if list(binder.Support[0][1])!=['Edge'+str(i) for i in expected_edges]:
                raise RuntimeError('Opening detail source-edge subset changed')
        if any((view.Source != [source] and view!=detail) or view.CoarseView or view.Perspective for view in views):
            raise RuntimeError("Reopened views are not orthographic native projections of the saved source BRep")
        if any(view.ScaleType != ('Custom' if view==detail else "Page") or abs(view.Scale - (layout['positions']['opening_detail']['scale'] if view==detail else expected_scale)) > 1e-8 for view in views):
            raise RuntimeError("Reopened views do not share the stated page scale")
        if page.ProjectionType != "Third angle" or page.DrawingUnits != "mm" or not page.ValidationDiagnosticsJSON:
            raise RuntimeError("Reopened page is missing its projection convention, units or validation diagnostics")
        if not dimension_reports and any(obj.isDerivedFrom("TechDraw::DrawViewDimension") for obj in reopened.Objects):
            raise RuntimeError("Stage A document unexpectedly contains dimensions")
        from .dimensions import verify_dimensions
        dimension_checks = verify_dimensions(reopened, dimension_reports or {})
        return {"reopened_successfully": True, "source_geometry_check": geometry_check,
                "scale_verified": page.Scale, "native_view_count": len(views), "dimension_count": len(dimension_checks),
                'native_hatch_overlay_view_count':1 if overlay_check else 0,'total_native_view_count':len(views)+(1 if overlay_check else 0),
                "dimension_checks": dimension_checks,
                "view_positions_verified": True, "view_directions_verified": True,
                "caption_positions_verified": True, "all_views_use_page_scale": detail is None,
                'detail_scale_verified':detail.Scale if detail else None,'hatch_material_recheck':overlay_check,
                'native_drafting_centerlines_verified':centerline_count,
                "projection_convention": page.ProjectionType, "validation_diagnostics_retained": True,
                "template_width_mm": page.Template.Width.Value, "template_height_mm": page.Template.Height.Value}
    finally:
        App.closeDocument(reopened.Name)
