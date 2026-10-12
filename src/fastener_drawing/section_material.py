"""Exact section regions and a checked hatch fallback; never heal the source.

Only closed native Part.section wires are accepted. Boolean area and complete
segment checks against the original solid guard against hatching a cavity.
"""
import json
from pathlib import Path

from fastener_analysis.geometry import App, Part
from .sections import section_geometry
from .references import projection_center
from .views import wait_for_views

NUMERIC_MM = 1e-6  # Computational consistency, never a manufacturing tolerance.


def verified_regions(shape, frames, origin):
    origin = App.Vector(*origin)
    cut, diagnostic = section_geometry(shape, frames, origin)
    if diagnostic['open_trace_count']:
        raise ValueError('Open source section traces: material reconstruction refused')
    wires = [Part.Wire(e) for e in Part.sortEdges(cut.Edges)]
    # Bullseye establishes nesting (including holes), using the exact wires.
    regions = Part.makeFace(wires, 'Part::FaceMakerBullseye')
    if not regions.isValid() or not regions.Faces:
        raise ValueError('Exact section wires did not form valid planar regions')
    checks = []
    for face in regions.Faces:
        inside, outside = face.common(shape), face.cut(shape)
        error = abs(face.Area - inside.Area)
        if not inside.isValid() or not outside.isValid() or error > NUMERIC_MM or outside.Area > NUMERIC_MM:
            raise ValueError('Section region is not wholly verified as original solid material')
        checks.append({'area_mm2': face.Area, 'solid_common_area_mm2': inside.Area,
                       'outside_solid_area_mm2': outside.Area, 'area_difference_mm2': error})
    return regions, {**diagnostic, 'region_count': len(checks), 'region_checks': checks,
                     'material_area_mm2': regions.Area, 'material_verified': True,
                     'boundaries': 'Exact original-BRep section wires with native nesting; no gap bridging or approximation'}


def verified_hatch(shape, frames, origin, paper_scale, spacing_mm=2.0):
    import TechDraw
    regions, diagnostic = verified_regions(shape, frames, origin)
    origin = App.Vector(*origin)
    matrix = App.Matrix()
    for row, vector in enumerate((frames['axis'], frames['up'], frames['front_normal']), 1):
        vector = App.Vector(*vector)
        for column, value in enumerate(vector, 1):
            setattr(matrix, f'A{row}{column}', value)
        setattr(matrix, f'A{row}4', -vector.dot(origin))
    flat = regions.copy(True, False)
    flat.transformShape(matrix, False)  # Rigid coordinate change, no flattening.
    if max(abs(flat.BoundBox.ZMin), abs(flat.BoundBox.ZMax)) > NUMERIC_MM:
        raise ValueError('Section boundaries do not lie on the verified plane')
    pattern = str(Path(App.getResourceDir()) / 'Mod/TechDraw/PAT/FCPAT.pat')
    # Diagonal4's perpendicular pitch is 4 mm at pattern scale 1.
    lines = []
    for face in flat.Faces:
        lines.extend(TechDraw.makeGeomHatch(face, spacing_mm / (4 * paper_scale), 'Diagonal4', pattern).Edges)
    if not lines:
        raise ValueError('Native hatch engine returned no segments')
    world = Part.makeCompound(lines)
    world.transformShape(matrix.inverse(), False)
    maximum = 0.0
    for edge in world.Edges:
        common = edge.common(shape)
        error = abs(edge.Length - common.Length)
        maximum = max(maximum, error)
        if not common.isValid() or error > NUMERIC_MM:
            raise ValueError('A hatch segment is not wholly within original solid material')
    diagnostic.update(hatch_segment_count=len(lines), maximum_segment_length_difference_mm=maximum,
                      complete_segments_verified=True, paper_pitch_mm=spacing_mm,
                      engine='Native TechDraw.makeGeomHatch, Diagonal4', source_healed=False)
    return world, diagnostic


def add_verified_overlay(doc, page, section, frames, origin):
    import logging
    log=logging.getLogger('fastener_drawing')
    log.warning('Preparing independent verified material hatch')
    shape, diagnostic = verified_hatch(doc.OriginalSTEP.Shape, frames, origin, section.Scale)
    log.warning('Material regions and %s complete hatch segments verified',len(shape.Edges))
    feature = doc.addObject('Part::Feature', 'VerifiedSectionHatch')
    feature.Shape = shape
    feature.Label = 'Verified material hatch (regenerate after source edits)'
    feature.addProperty('App::PropertyLink', 'OriginalSource', 'Provenance').OriginalSource = doc.OriginalSTEP
    feature.addProperty('App::PropertyString', 'VerificationJSON', 'Provenance').VerificationJSON = json.dumps(diagnostic)
    feature.ViewObject.Visibility = False
    view = doc.addObject('TechDraw::DrawViewPart', 'SectionHatchOverlay')
    view.Source = [feature]
    view.Direction, view.XDirection = section.Direction, section.XDirection
    view.CoarseView, view.ScrubCount = False, 0
    view.ScaleType = 'Page'
    view.ViewObject.LineWidth = .18
    page.addView(view)
    log.warning('Projecting verified hatch segments')
    wait_for_views(doc, [view])
    # A line-only shape has its own centroid. Align in world coordinates,
    # rather than assuming its bounding box matches the cut solid's box.
    delta = projection_center(view) - projection_center(section)
    view.X = section.X.Value + delta.dot(section.XDirection) * section.Scale
    view.Y = section.Y.Value + delta.dot(section.Direction.cross(section.XDirection)) * section.Scale
    diagnostic.update(status='verified_geometry_hatch_rendered',
                      reason='Native section conversion failed; native hatch-engine segments trimmed to independently verified original-solid regions',
                      association='Cached derived hatch linked to original source; rerun generator after geometry changes',
                      original_geometry_unchanged=True, visual_verification_required=True,
                      overlay_object=view.Name)
    return view, diagnostic


def verify_overlay(doc):
    """Recheck cached line geometry against the persisted original solid."""
    feature = doc.getObject('VerifiedSectionHatch')
    if feature is None:
        return None
    if feature.OriginalSource != doc.OriginalSTEP:
        raise RuntimeError('Hatch provenance source link changed')
    view,section=doc.getObject('SectionHatchOverlay'),doc.Section
    if view is None or view.Source!=[feature] or view.ScaleType!='Page' or abs(view.Scale-section.Scale)>1e-8:
        raise RuntimeError('Hatch overlay lost its native view or stated scale')
    if (view.Direction-section.Direction).Length>1e-8 or (view.XDirection-section.XDirection).Length>1e-8:
        raise RuntimeError('Hatch overlay projection differs from section')
    delta=projection_center(view)-projection_center(section)
    x=section.X.Value+delta.dot(section.XDirection)*section.Scale
    y=section.Y.Value+delta.dot(section.Direction.cross(section.XDirection))*section.Scale
    if max(abs(view.X.Value-x),abs(view.Y.Value-y))>1e-8:
        raise RuntimeError('Hatch overlay no longer aligns with source section')
    for edge in feature.Shape.Edges:
        common = edge.common(doc.OriginalSTEP.Shape)
        if not common.isValid() or abs(common.Length - edge.Length) > NUMERIC_MM:
            raise RuntimeError('Persisted hatch segment no longer matches solid material')
    return {'segment_count': len(feature.Shape.Edges), 'complete_segments_verified_against_saved_source': True,
            'native_view_alignment_direction_and_scale_verified':True}


def native_hatch_material(svg_path,section):
    """Audit actual native strokes against material, accounting for SVG rounding.

    This diagnostic does not generate/approximate section boundaries. Exact
    BRep checks above govern the fallback; this checks exported native ink.
    """
    import re
    import xml.etree.ElementTree as ET
    from .svg_placement import multiply,transform_matrix
    from .feature_references import lift_section
    root=ET.parse(svg_path).getroot()
    ratio=float(root.attrib['viewBox'].split()[2])/float(root.attrib['width'].replace('mm',''))
    height=float(root.attrib['height'].replace('mm',''))
    center=[section.X.Value*ratio,(height-section.Y.Value)*ratio]
    errors=[]
    def visit(node,matrix,style):
        matrix=multiply(matrix,transform_matrix(node.attrib.get('transform','')))
        style={**style,**node.attrib}
        if (node.tag.endswith('path') and abs(float(style.get('stroke-width','0'))-.18*ratio)<.001
            and max(abs(matrix[i+4]-center[i]) for i in (0,1))<.01):
            match=re.fullmatch(r'M([-+\d.eE]+),([-+\d.eE]+) L([-+\d.eE]+),([-+\d.eE]+)',node.attrib.get('d',''))
            if match:
                x,y,p,q=map(float,match.groups())
                if abs(abs(p-x)-abs(q-y))<.01 and abs(p-x)>.1:
                    points=[]
                    for a,b in ((x,y),(p,q)):
                        px=(matrix[0]*a+matrix[2]*b+matrix[4])/ratio
                        py=(matrix[1]*a+matrix[3]*b+matrix[5])/ratio
                        points.append(lift_section(section,App.Vector((px-section.X.Value)/section.Scale,(py-height+section.Y.Value)/section.Scale,0)))
                    edge=Part.makeLine(*points)
                    errors.append(abs(edge.Length-edge.common(section.Source[0].Shape).Length))
        for child in node:visit(child,matrix,style)
    visit(root,(1,0,0,1,0,0),{})
    threshold=1e-4  # Exported SVG coordinate rounding only, not a dimension tolerance.
    return {'checked_stroke_count':len(errors),'maximum_outside_length_mm':max(errors,default=0),
            'svg_rounding_threshold_mm':threshold,'solid_material_verified':bool(errors) and max(errors)<threshold,
            'basis':'Complete exported hatch segments intersected with original native solid; cavities excluded'}
