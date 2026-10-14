"""Native dimension creation from discovered candidates; no fixed measurement list."""
import logging
from collections import defaultdict

from fastener_analysis.geometry import App
from fastener_paths import CACHE_ROOT
from . import feature_references as refs
from .dimensions import native_measurement, references_record, presentation_record, set_presentation
from .formatting import dimension_format_spec
from .references import MATCH_MM, UnresolvedDimension
from .selection import Selection
from .views import wait_for_views

LOG=logging.getLogger("fastener_drawing")


def presentation(dim,candidate,matching):
    set_presentation(dim,"",candidate.get("units","mm"))
    kind=candidate["kind"]
    prefix="⌀ " if kind in ("diameter","curve_diameter") else "R" if kind in ("radius","torus_radius") else ""
    if candidate.get("repeat_count",1)>1:prefix=f"{candidate['repeat_count']}X "+prefix
    suffix=" AF" if kind=="across_flats" else ""  # Native angular dimensions append their own degree symbol.
    dim.FormatSpec=dimension_format_spec(candidate.get("units","mm"),prefix,suffix)
    dim.ViewObject.StandardAndStyle="ASME Referencing" if kind in ("radius","torus_radius") else "ASME Inlined"
    if matching["native_dimension_type"]=="Diameter":dim.ViewObject.RenderingExtent="Expanded"
    if kind in ('plane_angle','cone_angle'):dim.ViewObject.Arrowsize=2.0


def position_dimension(dim,view,candidate,matching,layout,lanes):
    role=next(r for r,p in layout["positions"].items() if abs(p["x_mm"]-view.X.Value)<1e-6 and abs(p["y_mm"]-view.Y.Value)<1e-6)
    pos=layout["positions"][role];w,h=pos["expected_width_mm"]/2,pos["expected_height_mm"]/2
    kind=candidate["kind"]
    if kind in ("overall","axial_distance"):
        lane=lanes[(role,"axial")];lanes[(role,"axial")]+=1
        pts=[r.get("vertex_mm") for r in matching["projected_geometry"]]
        dim.X=sum(p[0] for p in pts)*view.Scale/2 if pts and all(pts) else 0
        dim.Y=h+12+lane*7
        if candidate["value"]*view.Scale<12:
            dim.X=w+18+lane*5
    elif kind=="plane_angle":
        lane=lanes[(role,'angle')];lanes[(role,'angle')]+=1
        dim.X,dim.Y=compact_angle_anchor(view,matching,candidate,max(12,22-lane*4))
    elif kind in ("radius","torus_radius","cone_angle","radial_offset"):
        lane=lanes[(role,"leader")];lanes[(role,"leader")]+=1
        dim.X=w+18+12*(lane%2);dim.Y=h+12-lane*13
        if role=='opening_detail':dim.Y=h-9-lane*10
    elif role=="section":
        lane=lanes[(role,"radial")];lanes[(role,"radial")]+=1
        dim.X=-w-16-lane*11;dim.Y=-h-12
    elif kind=="across_flats":
        dim.X=-w-16;dim.Y=0
    elif kind=="opening_extent":
        if candidate["extent_direction"]=="x":dim.X,dim.Y=0,-h-16
        else:dim.X,dim.Y=-w-20,0
    elif kind=="plane_gap":
        lane=lanes[(role,"gap")];lanes[(role,"gap")]+=1
        dim.X=-w-18;dim.Y=0
    else:
        lane=lanes[(role,"diameter")];lanes[(role,"diameter")]+=1
        dim.X=0;dim.Y=h+(26 if role=="right_end" else 16)+lane*10


def create(doc,page,source,views,discovery,layout,decisions=None):
    import TechDraw
    reports={};selection=Selection(discovery);lanes=defaultdict(int)
    inventories={r:refs.inventory(v) for r,v in views.items() if r!="isometric"}
    vertexes={r:refs.vertices(v) for r,v in views.items() if r!="isometric"}
    for c in sorted(discovery["dimension_candidates"],key=lambda c:(-c["priority"],c["id"])):
        base={"candidate":c,"feature_id":c["feature_id"]}
        if decisions is not None:
            base.update(decisions[c['id']])
            if not base['selected']:
                reports[c['id']]={**base,"status":"suppressed_by_configuration","reason":base['selection_reason']};continue
        if c["verification_status"] in ("unsupported","presentation_optional"):
            reports[c["id"]]={**base,"status":"unresolved" if c["verification_status"]=="unsupported" else "omitted_optional","reason":c["reason"]};continue
        reason=selection.reason(c)
        if reason:
            reports[c["id"]]={**base,"status":"omitted_redundant","reason":reason};continue
        failures=[];dim=None
        from .details import preferred_views
        for role in preferred_views(c,discovery,views):
            if role not in views:continue
            view=views[role]
            try:
                feature=refs.prepare(source.Shape,c,view)
                prepared_redundancy=selection.reason(c)
                if prepared_redundancy:
                    reports[c["id"]]={**base,"status":"omitted_redundant","reason":prepared_redundancy}
                    break
                matching=refs.match(source.Shape,view,feature,inventories[role],vertexes[role])
                if abs(matching["projection_value_mm"]-feature["expected_mm"])>MATCH_MM:raise UnresolvedDimension("Matched native projection disagrees with source")
                if matching["native_dimension_type"]=="extent":
                    dim=TechDraw.makeExtentDim(view,[] if c["kind"]=="overall" else matching["references"],matching.get("extent_direction",0))
                else:
                    dim=doc.addObject("TechDraw::DrawViewDimension","Dimension"+c["id"])
                    dim.Type=matching["native_dimension_type"];dim.MeasureType="Projected"
                    dim.References2D=[(view,matching["references"])];page.addView(dim)
                dim.Label=c["label"]
                presentation(dim,c,matching);position_dimension(dim,view,c,matching,layout,lanes)
                wait_for_views(doc,list(views.values()))
                checked=native_measurement(dim,feature,matching)
                reports[c["id"]]={**base,"status":"created","object_name":dim.Name,"view_role":role,
                    "source_feature":feature,"projection_match":matching,"references2d":references_record(dim),
                    "format_spec":dim.FormatSpec,"measure_type":dim.MeasureType,"native_type":dim.Type,
                    "presentation":presentation_record(dim),"position_relative_to_view_mm":[dim.X.Value,dim.Y.Value],
                    "verification":checked,"requires_engineering_verification":True}
                dim.addProperty("App::PropertyString","MeasuredCharacteristic","Provenance").MeasuredCharacteristic=c["id"]+" "+c["label"]
                selection.accept(c);LOG.info("%s %s: native %.6f %s on %s",c["id"],c["label"],dim.getRawValue(),c["units"],role)
                break
            except (UnresolvedDimension,RuntimeError,ValueError) as exc:
                if dim is not None:doc.removeObject(dim.Name);dim=None
                failures.append(role+": "+str(exc))
        else:
            reports[c["id"]]={**base,"status":"unresolved","reason":"; ".join(failures) or "Required view unavailable"}
            LOG.warning("%s unresolved: %s",c["id"],reports[c["id"]]["reason"])
    # Place the overall dimension outside the shorter axial baselines.
    for r in reports.values():
        if r["status"]=="created" and r["candidate"]["kind"]=="overall":
            view=views[r["view_role"]];dim=doc.getObject(r["object_name"])
            dim.Y=layout["positions"][r["view_role"]]["expected_height_mm"]/2+12+lanes[(r["view_role"],"axial")]*7
            r["position_relative_to_view_mm"]=[dim.X.Value,dim.Y.Value]
    wait_for_views(doc,list(views.values()))
    return reports


def settle_placement(doc,reports,layout,paper_boxes,views):
    """Check actual native text bounds and relocate datums into reserved lanes."""
    attempts=defaultdict(int)
    from .svg_placement import check, ArrowTextCollision
    import os
    import FreeCADGui as Gui
    import TechDrawGui
    CACHE_ROOT.mkdir(parents=True,exist_ok=True)
    svg=CACHE_ROOT/f'placement-scene-{os.getpid()}.svg'
    for _ in range(140):
        Gui.updateGui()
        TechDrawGui.exportPageAsSvg(doc.DrawingPage,str(svg))
        try:return check(doc,reports,layout,paper_boxes,svg)
        except RuntimeError as exc:
            key=str(exc).split(":",1)[0]
            if key not in reports or reports[key]["status"]!="created":raise
            r=reports[key];dim=doc.getObject(r["object_name"]);attempts[key]+=1
            if isinstance(exc,ArrowTextCollision) and not r.get('arrow_clearance_repair'):
                # FreeCAD auto-flips only when text exceeds the endpoints;
                # the native scene proves whether the arrowheads also fit.
                dim.ViewObject.FlipArrowheads=not dim.ViewObject.FlipArrowheads
                r['arrow_clearance_repair']={'native_arrowheads_flipped':True,
                    'basis':'Collision of rendered diameter text with native filled-arrow polygons',
                    'minimum_gap_mm':exc.minimum_gap_mm}
                r['presentation']=presentation_record(dim)
                wait_for_views(doc,list(views.values()))
                continue
            if attempts[key]>16 or "rendered dimension text was not found" in str(exc):
                raise RuntimeError('Layout requires a larger sheet or additional view; meaningful dimension retained: '+str(exc))
            # Deterministic exploration around the original datum anchor.
            original=r.setdefault("initial_position_mm",list(r["position_relative_to_view_mm"]))
            n=attempts[key];dx,dy=[(0,12),(0,-12),(16,0),(-16,0),(16,12),(-16,12),(30,0),(-30,0),
                                 (0,24),(0,-24),(30,24),(-30,24),(45,0),(-45,0),(45,24),(-45,24)][n-1]
            dim.X,dim.Y=original[0]+dx,original[1]+dy
            r["position_relative_to_view_mm"]=[dim.X.Value,dim.Y.Value]
            wait_for_views(doc,list(views.values()))
    raise RuntimeError("Dimension placement did not converge")


def compact_angle_anchor(view,matching,candidate,radius_mm=16):
    """Place the native arc close to its actual support-line intersection.

    TechDraw's angular datum X/Y use the same reflected coordinates as the
    native dimension reference getter (unlike a world-to-page point).
    The intersection locates the arc only; it is not a manufactured sharp corner.
    """
    p,q=[App.Vector(*r['points_mm'][0]) for r in matching['projected_geometry']]
    a,b=[App.Vector(*r['points_mm'][-1])-App.Vector(*r['points_mm'][0]) for r in matching['projected_geometry']]
    determinant=a.x*b.y-a.y*b.x
    if abs(determinant)<1e-10:raise UnresolvedDimension('Angular support lines are parallel')
    t=((q.x-p.x)*b.y-(q.y-p.y)*b.x)/determinant
    corner=p+a*t
    from .references import projected_point
    center=projected_point(view,App.Vector(*candidate['origin_mm']))
    inward=center-corner
    if inward.Length<1e-8:raise UnresolvedDimension('Cannot locate a cavity-side angular label')
    inward.normalize()
    anchor=corner*view.Scale+inward*radius_mm
    return anchor.x,anchor.y
