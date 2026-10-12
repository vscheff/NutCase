"""General source proofs and native view matching for Phase 3 candidates.

Projected vertices are measured native geometry, not cosmetic points. Every
match retains its source loci and fingerprints for a second check after reopen.
"""
import math

from fastener_analysis.features import axial_bounds
from fastener_analysis.geometry import App, Part, unit, xyz, middle_parameters
from .references import MATCH_MM, UnresolvedDimension, inventory, edge_record, projected_point, projection_center


def vertex_record(vertex):
    return {"vertex_mm": xyz(vertex.Point)}


def vertices(view):
    visible = [App.Vector(p.x / view.Scale, -p.y / view.Scale, p.z / view.Scale)
               for p in view.getVisibleVertexes()]
    result = []
    count = len(visible) + len(view.getHiddenVertexes())
    for i in range(count):
        name = f"Vertex{i}"
        vertex = view.getVertexBySelection(name)
        result.append({"name": name, "point": vertex.Point, "record": vertex_record(vertex),
                       "visible": any((vertex.Point-p).Length < MATCH_MM for p in visible)})
    return result


def frame_matrix(view):
    d, x = unit(view.Direction), unit(view.XDirection)
    y = d.cross(x)
    matrix = App.Matrix()
    for row, v in enumerate((x, -y, d), 1):
        for col, value in enumerate(xyz(v), 1):
            setattr(matrix, f"A{row}{col}", value)
    return matrix


def projected_wire(shape, ids, view):
    copy = Part.makeCompound([shape.Solids[0].Edges[i-1] for i in ids]).copy(True, False)
    copy.translate(-projection_center(view))
    copy.transformShape(frame_matrix(view), False)
    box = copy.optimalBoundingBox(False, False)
    if box.ZLength > MATCH_MM:
        raise UnresolvedDimension("Opening wire is not normal to this end view")
    copy.translate(App.Vector(0, 0, -box.Center.z))
    return copy


def station_value(shape, station, axis, origin):
    values = []
    solid = shape.Solids[0]
    for support in station["supports"]:
        for i in support.get("faces", []):
            face = solid.Faces[i-1]
            if not isinstance(face.Surface, Part.Plane) or abs(unit(face.Surface.Axis).dot(axis)) < 1-1e-8:
                raise UnresolvedDimension("Axial station plane support changed")
            values.append((face.Surface.Position-origin).dot(axis))
        for i in support.get("edges", []):
            bounds = axial_bounds(solid.Edges[i-1], axis, origin)
            if bounds[1]-bounds[0] > MATCH_MM:
                raise UnresolvedDimension("Axial station boundary is no longer constant")
            values.append(sum(bounds)/2)
    if not values or max(values)-min(values) > MATCH_MM:
        raise UnresolvedDimension("No consistent native axial support")
    return sum(values)/len(values)


def remeasure(shape, feature):
    c = feature["candidate"]
    solid = shape.Solids[0]
    kind = c["kind"]
    faces = [solid.Faces[i-1] for i in c["source_faces"]]
    if kind in ("overall", "axial_distance"):
        axis, origin = App.Vector(*c["axis"]), App.Vector(*c["origin_mm"])
        values = [station_value(shape, s, axis, origin) for s in c["source_supports"]]
        if len(values) != 2:
            raise UnresolvedDimension("Axial distance lacks two supported stations")
        return abs(values[1]-values[0])
    if kind in ("diameter", "radius"):
        if not all(isinstance(f.Surface, Part.Cylinder) for f in faces):
            raise UnresolvedDimension("Native cylindrical supports changed")
        values = [f.Surface.Radius for f in faces]
        if max(values)-min(values) > MATCH_MM:
            raise UnresolvedDimension("Repeated cylindrical radii disagree")
        return values[0] * (2 if kind == "diameter" else 1)
    if kind == "torus_radius":
        return faces[0].Surface.MinorRadius
    if kind == "cone_angle":
        if not all(isinstance(f.Surface, Part.Cone) for f in faces):
            raise UnresolvedDimension("Native conical support changed")
        return 2*math.degrees(abs(faces[0].Surface.SemiAngle))
    if kind == "curve_diameter":
        # An independent cone-law measurement, rather than averaging the
        # same sampled rim radii used to discover the candidate.
        s = faces[0].Surface
        point = solid.Edges[c["source_edges"][0]-1].Vertexes[0].Point
        if not isinstance(s, Part.Cone):
            raise UnresolvedDimension("Rim's analytic cone support changed")
        return 2*abs((point-s.Apex).dot(unit(s.Axis))*math.tan(s.SemiAngle))
    if kind in ("across_flats", "plane_gap", "plane_angle"):
        pair = feature["supporting_pair"]
        first, second = [solid.Faces[i-1].Surface for i in pair]
        if not isinstance(first, Part.Plane) or not isinstance(second, Part.Plane):
            raise UnresolvedDimension("Opposing plane supports changed")
        if kind=="plane_angle":
            normals=[]
            for fid,surface in zip(pair,(first,second)):
                face=solid.Faces[fid-1]
                normal=unit(surface.Axis)
                if normal.dot(face.normalAt(*middle_parameters(face)))<0:normal=-normal
                normals.append(normal)
            return 180-math.degrees(math.acos(max(-1,min(1,normals[0].dot(normals[1])))))
        value=abs((first.Position-second.Position).dot(unit(first.Axis)))
        if kind=="plane_gap":
            for pair in c.get("repeat_supporting_pairs",[]):
                a,b=[solid.Faces[i-1].Surface for i in pair]
                if (not isinstance(a,Part.Plane) or not isinstance(b,Part.Plane)
                    or abs(unit(a.Axis).dot(unit(b.Axis)))<1-1e-8
                    or abs(abs((a.Position-b.Position).dot(unit(a.Axis)))-value)>MATCH_MM):
                    raise UnresolvedDimension("Repeated source plane spacings are no longer equal/opposed")
        return value
    if kind=="radial_offset":
        axis,origin=App.Vector(*c["axis"]),App.Vector(*c["origin_mm"])
        values=[(s.Surface.Center-origin-axis*(s.Surface.Center-origin).dot(axis)).Length for s in faces]
        if max(values)-min(values)>MATCH_MM:raise UnresolvedDimension("Repeated radial offsets disagree")
        return values[0]
    if kind=="radial_gap":
        radii=[solid.Faces[i-1].Surface.Radius for i in c["radius_faces"]]
        return abs(radii[1]-radii[0])
    if kind == "opening_extent":
        # Native BRep extrema of the actual terminal inner wire in the saved
        # drawing frame. No theoretical sharp polygon or nominal size.
        d = App.Vector(*feature["view_direction"])
        x = App.Vector(*feature["view_x_direction"])
        matrix = App.Matrix()
        for row, v in enumerate((x, -d.cross(x), d), 1):
            for col, value in enumerate(xyz(v), 1):setattr(matrix,f"A{row}{col}",value)
        copy = Part.makeCompound([solid.Edges[i-1] for i in c["source_edges"]]).copy(True,False)
        copy.transformShape(matrix, False)
        b = copy.optimalBoundingBox(False,False)
        return b.XLength if c["extent_direction"] == "x" else b.YLength
    raise UnresolvedDimension("No independent source proof for candidate kind " + kind)


def prepare(shape, candidate, view):
    feature = {"kind":"general", "candidate":candidate, "expected_mm":candidate["value"],
               "units":candidate["units"], "measurement_basis":"Native source BRep support; independent projected measurement follows"}
    if candidate["kind"] in ("across_flats", "plane_gap", "plane_angle"):
        if "supporting_pair" in candidate:
            feature["supporting_pair"] = candidate["supporting_pair"]
        else:
            y = unit(view.Direction).cross(unit(view.XDirection))
            faces = shape.Solids[0].Faces
            pairs = [(i,j) for i in candidate["source_faces"] for j in candidate["source_faces"] if j>i
                     and abs(unit(faces[i-1].Surface.Axis).dot(y)) > 1-1e-8
                     and abs(unit(faces[j-1].Surface.Axis).dot(y)) > 1-1e-8]
            if len(pairs)!=1:raise UnresolvedDimension("No opposing flats aligned with this view")
            feature["supporting_pair"] = list(pairs[0])
    if candidate["kind"] == "opening_extent":
        feature.update(view_direction=xyz(view.Direction), view_x_direction=xyz(view.XDirection))
        wire=projected_wire(shape,candidate["source_edges"],view)
        box=wire.optimalBoundingBox(False,False)
        component="x" if candidate["extent_direction"]=="x" else "y"
        direction=unit(view.XDirection) if component=="x" else -unit(view.Direction).cross(unit(view.XDirection))
        ends=[box.XMin,box.XMax] if component=="x" else [box.YMin,box.YMax]
        pairs=[]
        solid=shape.Solids[0]
        for end in ends:
            supported=[]
            for i,f in enumerate(solid.Faces,1):
                if not isinstance(f.Surface,Part.Plane) or abs(unit(f.Surface.Axis).dot(direction))<1-1e-8:continue
                point=projected_point(view,f.CenterOfMass)
                if abs(getattr(point,component)-end)>MATCH_MM:continue
                if any(e.isSame(solid.Edges[j-1]) for e in f.Edges for j in candidate["source_edges"]):supported.append(i)
            pairs.append(supported)
        if all(len(p)==1 for p in pairs):candidate["extent_supporting_pair"]=[p[0] for p in pairs]
    feature["independent_source_value_mm"] = remeasure(shape,feature)
    if feature["expected_mm"] is None:
        feature["expected_mm"] = feature["independent_source_value_mm"]
        candidate.update(value=feature["expected_mm"],measurement_frame={"direction":xyz(view.Direction),"x_direction":xyz(view.XDirection)},
                         measurement_basis="Actual terminal inner-wire BRep extrema in recorded drawing frame")
    if abs(feature["expected_mm"]-feature["independent_source_value_mm"]) > MATCH_MM:
        raise UnresolvedDimension("Independent source proof disagrees with discovery")
    return feature


def record_match(selected, value, basis, native_type, **extra):
    return {"references":[e["name"] for e in selected],"projected_geometry":[e["record"] for e in selected],
            "projection_value_mm":value,"match_basis":basis,"native_dimension_type":native_type,**extra}


def straight(entry):
    points=[App.Vector(*p) for p in entry["record"]["points_mm"]]
    direction=points[-1]-points[0]
    length=direction.Length
    return (length>MATCH_MM and abs(entry["edge"].Length-length)<MATCH_MM
            and all((p-points[0]).cross(direction).Length/length<MATCH_MM for p in points))


def lift_section(view, point):
    center = projection_center(view)
    # Projection centroid's depth may differ from SectionOrigin. Use the
    # actual saved cut plane to lift a 2D point to its unique 3D cut location.
    direction = unit(view.Direction)
    center += direction*(view.SectionOrigin-center).dot(direction)
    return center + unit(view.XDirection)*point.x - direction.cross(unit(view.XDirection))*point.y


_section_bounds={}


def on_section_faces(shape, view, entry, ids):
    if not view.isDerivedFrom("TechDraw::DrawViewSection"):return False
    faces = [shape.Solids[0].Faces[i-1] for i in ids]
    for p in entry["record"]["points_mm"]:
        point=lift_section(view,App.Vector(*p));supported=False
        for face in faces:
            key=(view.Document.Name,view.Name,face.hashCode())
            if key not in _section_bounds:
                copy=face.copy(True,False);copy.translate(-projection_center(view));copy.transformShape(frame_matrix(view),False)
                _section_bounds[key]=copy.optimalBoundingBox(False,False)
            bounds=_section_bounds[key]
            if not(bounds.XMin-MATCH_MM<=p[0]<=bounds.XMax+MATCH_MM and bounds.YMin-MATCH_MM<=p[1]<=bounds.YMax+MATCH_MM):continue
            if face.distToShape(Part.Vertex(point))[0]<MATCH_MM:
                supported=True;break
        if not supported:return False
    return True


def match(shape, view, feature, entries=None, vertex_entries=None):
    c, kind = feature["candidate"], feature["candidate"]["kind"]
    expected = feature["independent_source_value_mm"]
    entries = entries if entries is not None else inventory(view)
    vertex_entries = vertex_entries if vertex_entries is not None else vertices(view)
    solid = shape.Solids[0]
    if kind in ("axial_distance","overall"):
        axis, origin = App.Vector(*c["axis"]), App.Vector(*c["origin_mm"])
        if abs(unit(view.XDirection).dot(axis))<1-1e-8:raise UnresolvedDimension("Axis is not horizontal in view")
        selected=[]
        for station in c["source_supports"]:
            st=station_value(shape,station,axis,origin)
            target=projected_point(view,origin+axis*st).x
            options=[v for v in vertex_entries if v["visible"] and abs(v["point"].x-target)<MATCH_MM]
            if view.isDerivedFrom("TechDraw::DrawViewSection"):
                supports=[solid.Faces[i-1] for sup in station["supports"] for i in sup.get("faces",[])] + [solid.Edges[i-1] for sup in station["supports"] for i in sup.get("edges",[])]
                options=[v for v in options if min(s.distToShape(Part.Vertex(lift_section(view,v["point"])))[0] for s in supports)<MATCH_MM]
            if not options:raise UnresolvedDimension("No visible native vertex on supported axial station " + station["id"])
            selected.append(min(options,key=lambda v:v["point"].y))
        return record_match(selected,abs(selected[1]["point"].x-selected[0]["point"].x),"Two native vertices at independent source-supported axial stations","DistanceX")
    if kind in ("diameter","curve_diameter","radius"):
        circles=[]
        for entry in entries:
            r=entry["record"]
            if not entry["visible"] or r["curve_type"]!="Circle":continue
            radius=expected/(2 if kind!="radius" else 1)
            if abs(r["radius_mm"]-radius)>MATCH_MM:continue
            if abs(unit(view.Direction).dot(App.Vector(*c["axis"])))<1-1e-8:continue
            for fid in c["source_faces"]:
                s=solid.Faces[fid-1].Surface
                center=s.Center if kind!="curve_diameter" else App.Vector(*c["origin_mm"])+App.Vector(*c["axis"])*c["station_mm"]
                if (projected_point(view,center)-App.Vector(*r["center_mm"])).Length<MATCH_MM:
                    circles.append(entry);break
        if circles:
            selected=max(circles,key=lambda e:e['record']['bounds_mm'][2]-e['record']['bounds_mm'][1]) if kind=='radius' else max(circles,key=lambda e:e["record"]["length_mm"])
            return record_match([selected],selected["record"]["radius_mm"]*(1 if kind=="radius" else 2),"Native analytic circular trace matching source axis, center and radius", "Radius" if kind=="radius" else "Diameter")
        if not view.isDerivedFrom("TechDraw::DrawViewSection") or kind=="radius":
            raise UnresolvedDimension("No exact visible circular trace matches source center and radius")
        if kind=="diameter":
            lines=[e for e in entries if e["visible"] and straight(e)
                   and abs(e["record"]["bounds_mm"][3]-e["record"]["bounds_mm"][1])<MATCH_MM
                   and on_section_faces(shape,view,e,c["source_faces"])]
            pairs=[(a,b) for a in lines for b in lines if a["name"]<b["name"]
                   and abs(abs(a["record"]["bounds_mm"][1]-b["record"]["bounds_mm"][1])-expected)<MATCH_MM]
            if not pairs:raise UnresolvedDimension("No opposite section generatrices on this cylinder")
            a,b=max(pairs,key=lambda pair:sum(e["record"]["length_mm"] for e in pair))
            return record_match([a,b],abs(a["record"]["bounds_mm"][1]-b["record"]["bounds_mm"][1]),"Opposite section traces verified on original cylindrical faces","DistanceY")
        target=projected_point(view,App.Vector(*c["origin_mm"])+App.Vector(*c["axis"])*c["station_mm"]).x
        rim=Part.makeCompound([solid.Edges[i-1] for i in c["source_edges"]])
        options=[v for v in vertex_entries if v["visible"] and abs(v["point"].x-target)<MATCH_MM
                 and rim.distToShape(Part.Vertex(lift_section(view,v["point"])))[0]<MATCH_MM]
        if len(options)<2:raise UnresolvedDimension("No opposing section vertices on actual cone rim")
        a,b=min(options,key=lambda v:v["point"].y),max(options,key=lambda v:v["point"].y)
        return record_match([a,b],b["point"].y-a["point"].y,"Section vertices on original cone rim, independent cone-law diameter","DistanceY")
    if kind in ("across_flats","plane_gap","plane_angle"):
        if kind=="across_flats":
            from .references import match_flats
            matched=match_flats(shape,view,{"faces":feature["supporting_pair"]},entries)
            matched["native_dimension_type"]="DistanceY"
            return matched
        refs=[];norm=None
        for fid in feature["supporting_pair"]:
            face=solid.Faces[fid-1];s=face.Surface
            normal=frame_matrix(view).multVec(unit(s.Axis));normal.z=0
            if normal.Length<.99:raise UnresolvedDimension("Plane is not edge-on to view")
            normal=unit(normal);norm=normal
            point=projected_point(view,face.CenterOfMass)
            options=[e for e in entries if e["visible"] and straight(e)
                     and all(abs((App.Vector(*p)-point).dot(normal))<MATCH_MM for p in e["record"]["points_mm"])]
            if not options:raise UnresolvedDimension("No visible trace on specified opposing plane")
            refs.append(max(options,key=lambda e:e["record"]["length_mm"]))
        p,q=[App.Vector(*e["record"]["points_mm"][0]) for e in refs]
        if kind=="plane_angle":
            directions=[unit(App.Vector(*e["record"]["points_mm"][-1])-App.Vector(*e["record"]["points_mm"][0])) for e in refs]
            center=projected_point(view,App.Vector(*c["origin_mm"]))
            normals=[]
            for entry,direction in zip(refs,directions):
                normal=App.Vector(-direction.y,direction.x,0)
                point=App.Vector(*entry["record"]["points_mm"][0])
                if normal.dot(center-point)<0:normal=-normal
                normals.append(normal)
            value=180-math.degrees(math.acos(max(-1,min(1,normals[0].dot(normals[1])))))
            return record_match(refs,value,"Native planar trace halfspaces facing the recovered axis; independent included wall angle","Angle")
        value=abs((p-q).dot(norm))
        return record_match(refs,value,"Native straight traces on actual opposing support-plane loci", "DistanceY" if abs(norm.y)>1-1e-8 else "Distance")
    if kind=="opening_extent":
        wire=projected_wire(shape,c["source_edges"],view);b=wire.optimalBoundingBox(False,False)
        selected=[e for e in entries if e["visible"] and all(wire.distToShape(Part.Vertex(App.Vector(*p)))[0]<MATCH_MM for p in e["record"]["points_mm"])]
        if not selected:raise UnresolvedDimension("No visible projection of actual closed inner wire")
        bb=Part.makeCompound([e["edge"] for e in selected]).optimalBoundingBox(False,False)
        value=bb.XLength if c["extent_direction"]=="x" else bb.YLength
        return record_match(selected,value,"Native subset extent of projected terminal inner wire verified against original BRep", "extent",extent_direction=0 if c["extent_direction"]=="x" else 1)
    if kind=="radial_offset":
        if abs(unit(view.Direction).dot(App.Vector(*c["axis"])))<1-1e-8:raise UnresolvedDimension("Axis offset requires end view")
        center=projected_point(view,App.Vector(*c["origin_mm"]))
        circles=[e for e in entries if e["visible"] and e["record"]["curve_type"]=="Circle"]
        origins=[e for e in circles if (App.Vector(*e["record"]["center_mm"])-center).Length<MATCH_MM]
        offsets=[e for e in circles if any((App.Vector(*e["record"]["center_mm"])-projected_point(view,solid.Faces[i-1].Surface.Center)).Length<MATCH_MM
                                          and abs(e["record"]["radius_mm"]-solid.Faces[i-1].Surface.Radius)<MATCH_MM for i in c["source_faces"])]
        if not origins or not offsets:raise UnresolvedDimension("No pair of exact visible source-matched circles supplies origin and offset centers")
        a,b=max(origins,key=lambda e:e["edge"].Length),max(offsets,key=lambda e:e["edge"].Length)
        distance=(App.Vector(*a["record"]["center_mm"])-App.Vector(*b["record"]["center_mm"])).Length
        return record_match([a,b],distance,"Centers of native circles verified against source axis loci","Distance")
    if kind=="radial_gap":
        groups=[]
        for fid in c["radius_faces"]:
            options=[e for e in entries if e["visible"] and straight(e)
                     and abs(e["record"]["bounds_mm"][3]-e["record"]["bounds_mm"][1])<MATCH_MM
                     and on_section_faces(shape,view,e,[fid])]
            groups.append(options)
        pairs=[(a,b) for a in groups[0] for b in groups[1] if abs(abs(a["record"]["bounds_mm"][1]-b["record"]["bounds_mm"][1])-expected)<MATCH_MM]
        if not pairs:raise UnresolvedDimension("No same-side section traces support recess depth")
        a,b=max(pairs,key=lambda p:p[0]["edge"].Length+p[1]["edge"].Length)
        return record_match([a,b],abs(a["record"]["bounds_mm"][1]-b["record"]["bounds_mm"][1]),"Original-face section traces for annular recess depth","DistanceY")
    if kind in ("cone_angle","torus_radius"):
        options=[e for e in entries if e["visible"] and on_section_faces(shape,view,e,c["source_faces"])]
        if kind=="torus_radius":
            options=[e for e in options if e["record"]["curve_type"]=="Circle" and abs(e["record"]["radius_mm"]-expected)<MATCH_MM]
            if not options:raise UnresolvedDimension("No analytic section arc on original toroidal surface")
            e=max(options,key=lambda e:e["record"]["length_mm"])
            return record_match([e],e["record"]["radius_mm"],"Native cut arc on original toroidal surface","Radius")
        options=[e for e in options if straight(e)]
        pairs=[]
        for a in options:
            for b in options:
                if a["name"]>=b["name"]:continue
                directions=[]
                for e in (a,b):
                    v=App.Vector(*e["record"]["points_mm"][-1])-App.Vector(*e["record"]["points_mm"][0])
                    if v.x<0:v=-v
                    directions.append(unit(v))
                angle=math.degrees(math.acos(max(-1,min(1,directions[0].dot(directions[1])))))
                if abs(angle-expected)<MATCH_MM:pairs.append((a,b,angle))
        if not pairs:raise UnresolvedDimension("No independent pair of cut generatrices supports included cone angle")
        a,b,value=max(pairs,key=lambda p:p[0]["edge"].Length+p[1]["edge"].Length)
        return record_match([a,b],value,"Angle of two original-face cut generatrices, separately checked against native cone law","Angle")
    raise UnresolvedDimension("No native matcher for "+kind)


def reference_record(view,name):
    return vertex_record(view.getVertexBySelection(name)) if name.startswith("Vertex") else edge_record(view.getEdgeBySelection(name))
