"""Feature discovery and measured candidates, independent of drawing/view APIs.

Roles are conservative geometric descriptions. Coordinates are native BRep
measurements tied to the import, never nominal specifications.
"""
import math

from .geometry import App, Part, bbox_record, middle_parameters, parallel, transverse, unit, xyz

EPS = 1e-5  # Numeric feature matching in mm; never a manufacturing tolerance.


def basis_matrix(axis, up=None):
    if up is None:
        reference = App.Vector(1, 0, 0) if abs(axis.x) < 0.9 else App.Vector(0, 1, 0)
        up = unit(transverse(reference, axis))
    x = unit(axis.cross(up))
    matrix = App.Matrix()
    for row, vector in enumerate((x, up, axis), 1):
        for col, value in enumerate(xyz(vector), 1):
            setattr(matrix, f"A{row}{col}", value)
    return matrix


def axial_bounds(shape, axis, origin):
    copy = shape.copy(True, False)
    copy.translate(-origin)
    copy.transformShape(basis_matrix(axis), False)
    box = copy.optimalBoundingBox(False, False)
    return [box.ZMin, box.ZMax]


def edge_number(shape, edge):
    return next(i + 1 for i, item in enumerate(shape.Edges) if item.isSame(edge))


def boundary_side(face):
    surface = face.Surface
    point = face.valueAt(*middle_parameters(face))
    radial = transverse(point - surface.Center, unit(surface.Axis))
    dot = face.normalAt(*middle_parameters(face)).dot(unit(radial))
    return "external" if dot > 0.5 else "internal" if dot < -0.5 else "unresolved"


def discover_features(shape, geometry, recognition, validation=None):
    result = {"schema_version": "3.0", "features": [], "dimension_candidates": [],
              "recognition_is_exhaustive": False, "numerical_threshold_mm": EPS,
              "coverage_notice": "Candidate coverage is not proof of dimensional completeness; unrecognized geometry still requires engineering review."}
    if geometry["axis"]["status"] != "identified":
        result["limitations"] = ["Axis unresolved: axial/radial feature discovery cannot establish a reliable frame."]
        result['axis'] = None
        result['unmapped_faces'] = [{'face':i,'surface_type':type(f.Surface).__name__,'reason':'Axis unresolved; no feature role assigned'} for i,f in enumerate(shape.Faces,1)]
        return result
    shape = shape.Solids[0]
    axis = unit(App.Vector(*geometry["axis"]["direction"]))
    origin = App.Vector(*geometry["axis"]["origin_mm"])
    extbands = [b for b in geometry["cylindrical_bands"] if b["boundary_side"] == "external" and b["complete_circular_band"]]
    if extbands:
        largest = max(extbands, key=lambda b: b["radius_mm"])
        length = geometry["axis_aligned_bounding_box"]["dimensions_mm"][2]
        midpoint = sum(largest["axial_range_mm"]) / 2
        if abs(midpoint) > length * 0.15 and largest["axial_span_mm"] < length * 0.5 and midpoint < 0:
            axis = -axis
    low, high = axial_bounds(shape, axis, origin)
    total = high - low
    faces, edges, covered = shape.Faces, shape.Edges, set()
    features, candidates = result["features"], result["dimension_candidates"]

    def feature(kind, ids, measured, note, **extra):
        obj = {"id": f"F{len(features)+1:03d}", "type": kind, "source_faces": sorted(ids),
               "measured_geometry": measured, "classification_basis": note, "candidate_ids": [], **extra}
        features.append(obj)
        covered.update(ids)
        return obj

    def candidate(f, kind, value, label, supports=None, priority=50, **extra):
        proposed={"overall":"Native horizontal extent","axial_distance":"DistanceX","diameter":"Diameter or section DistanceY",
                  "curve_diameter":"Diameter or section DistanceY","radius":"Radius","torus_radius":"Radius",
                  "cone_angle":"Angle","plane_angle":"Angle","across_flats":"DistanceY","plane_gap":"Distance",
                  "opening_extent":"Native subset extent","radial_offset":"Center distance","radial_gap":"DistanceY"}
        obj = {"id": f"D{len(candidates)+1:03d}", "feature_id": f["id"], "kind": kind,
               "value": value, "units": "deg" if kind in ("cone_angle","plane_angle") else "mm", "label": label,
               "source_faces": f["source_faces"], "source_supports": supports or [],
               "priority": priority, "verification_status": "source_measured", "proposed_dimension_type":proposed.get(kind,"Unresolved"), **extra}
        if validation and (not validation["basic_valid"] or not shape.isClosed()):
            obj.update(verification_status="unsupported", reason="Source is basically invalid or open")
        f["candidate_ids"].append(obj["id"])
        candidates.append(obj)
        return obj

    # Actual constant-station boundaries, not face UV ranges or tessellation.
    stations = []
    def station(value, support):
        found = next((s for s in stations if abs(s["station_mm"]-value) < EPS), None)
        if found is None:
            found = {"id": f"S{len(stations)+1:03d}", "station_mm": value, "supports": []}
            stations.append(found)
        if support not in found["supports"]:
            found["supports"].append(support)
        return found

    for i, face in enumerate(faces, 1):
        if isinstance(face.Surface, Part.Plane) and abs(unit(face.Surface.Axis).dot(axis)) > 1-1e-8:
            station((face.CenterOfMass-origin).dot(axis), {"type": "plane", "faces": [i]})
    for i, edge in enumerate(edges, 1):
        bound = axial_bounds(edge, axis, origin)
        if bound[1] - bound[0] < EPS and edge.Length > EPS:
            # Imported circle rims can be BSplines. Exact axial BRep extrema
            # establish a constant boundary without pretending the curve is a circle.
            station(sum(bound)/2, {"type": "rim" if isinstance(edge.Curve,Part.Circle) else "axial_edge", "edges": [i]})
    stations.sort(key=lambda s:s["station_mm"])
    terminal = [next((s for s in stations if abs(s["station_mm"]-value)<EPS), None) for value in (low,high)]
    overall = feature("axial_envelope", [], {"length_mm": total}, "Native extrema along recovered centerline")
    candidate(overall, "overall", total, "Overall axial length", terminal if all(terminal) else [], priority=100,
              axis=xyz(axis), origin_mm=xyz(origin), preferred_views=["longitudinal"],
              **({} if all(terminal) else {"verification_status":"unsupported", "reason":"No terminal constant-station support"}))

    # Group cylinders by actual axis, radius and boundary side. Split faces with
    # slightly different curved end trims must not become separate diameters.
    groups=[]
    for i, face in enumerate(faces, 1):
        surface=face.Surface
        if not isinstance(surface,Part.Cylinder) or not parallel(surface.Axis,axis):
            continue
        side=boundary_side(face)
        center=transverse(surface.Center-origin,axis)
        ranges=axial_bounds(face,axis,origin)
        group=next((g for g in groups if g["side"]==side and abs(g["radius"]-surface.Radius)<EPS
                    and (g["offset"]-center).Length<EPS
                    and min(g["range"][1],ranges[1])>=max(g["range"][0],ranges[0])-EPS),None)
        if group is None:
            group={"radius":surface.Radius,"side":side,"offset":center,"ids":[],"range":ranges,"area":0,"angles":0}
            groups.append(group)
        group["ids"].append(i)
        group["range"]=[min(group["range"][0],ranges[0]),max(group["range"][1],ranges[1])]
        group["area"]+=face.Area
        group["angles"]+=min(2*math.pi,abs(face.ParameterRange[1]-face.ParameterRange[0]))
    flange_ids=recognition["dimensions"]["flange_diameter"].get("evidence",{}).get("faces",[])
    datum=None
    round_groups=[]
    for g in groups:
        coaxial=g["offset"].Length<EPS
        complete=g["angles"]>=2*math.pi-1e-5
        bounds=g["range"]
        f=feature("cylindrical_region" if coaxial else "offset_cylindrical_patch",g["ids"],
                  {"radius_mm":g["radius"],"diameter_mm":2*g["radius"],"axial_range_mm":bounds,
                   "axial_span_mm":bounds[1]-bounds[0],"axis_offset_mm":xyz(g["offset"]),
                   "angular_coverage_rad":g["angles"]},"Native cylindrical surfaces grouped by radius, axis, side and overlapping axial support",
                  boundary_side=g["side"],complete_circumference=complete,coaxial=coaxial)
        g["feature"]=f
        if coaxial:
            label="Flange outside diameter" if set(g["ids"]) & set(flange_ids) else ("Internal bore diameter" if g["side"]=="internal" else "External body diameter")
            c=candidate(f,"diameter",2*g["radius"],label,priority=90 if "Flange" in label else 80,
                        preferred_views=["section","right_end","left_end"] if g["side"]=="internal" else ["left_end","right_end","section"],
                        radius_mm=g["radius"],axis=xyz(axis),origin_mm=xyz(origin),boundary_side=g["side"])
            if not complete:
                c["scope_note"]="Diameter of analytic cylindrical surface; trimmed ends may be irregular. No nominal round-shaft role assigned."
            ends=[next((s for s in stations if abs(s["station_mm"]-v)<EPS and any(
                (sup["type"]=="plane" and set(sup["faces"])&set(g["ids"])) or
                (sup["type"] in ("rim","axial_edge") and any(edges[e-1].isSame(fe) for fid in g["ids"] for fe in faces[fid-1].Edges for e in sup["edges"]))
                for sup in s["supports"])),None) for v in bounds]
            # Exact band length requires constant-station rims. Curved/tangent
            # limits are retained as diagnostics, not uniform shoulder locations.
            c=candidate(f,"axial_distance",bounds[1]-bounds[0],("Bore depth / cylindrical span" if g["side"]=="internal" else "Cylindrical region length"),
                        ends if all(ends) else [],priority=65,axis=xyz(axis),origin_mm=xyz(origin),preferred_views=["section","longitudinal"])
            if not all(ends):
                c.update(verification_status="unsupported",reason="At least one cylindrical end has a varying curved trim, not a unique constant axial boundary")
            if set(g["ids"])&set(flange_ids):
                bearing=next((s for s in stations if abs(s["station_mm"]-bounds[0])<EPS and any(sup["type"]=="plane" for sup in s["supports"])),None)
                if bearing and terminal[1]:
                    datum=bearing
                    enlargement=feature("terminal_enlargement",g["ids"],{"total_axial_thickness_mm":high-bearing["station_mm"]},"Annular perpendicular shoulder at the beginning of the largest supported terminal circular enlargement; datum is geometric, not design intent")
                    candidate(enlargement,"axial_distance",high-bearing["station_mm"],"Flange total thickness",[bearing,terminal[1]],priority=95,axis=xyz(axis),origin_mm=xyz(origin),preferred_views=["longitudinal","section"])
                    candidate(enlargement,"axial_distance",bearing["station_mm"]-low,"Body length below flange",[terminal[0],bearing] if terminal[0] else [],priority=40,axis=xyz(axis),origin_mm=xyz(origin),preferred_views=["longitudinal","section"],relation="overall_minus_flange")
        elif complete:
            candidate(f,"diameter",2*g["radius"],"Offset cylindrical region diameter",priority=80,
                      preferred_views=["right_end","left_end"],radius_mm=g["radius"],axis=xyz(axis),origin_mm=xyz(origin),boundary_side=g["side"])
            candidate(f,"radial_offset",g["offset"].Length,"Offset cylinder axis distance",priority=74,
                      preferred_views=["right_end","left_end"],axis=xyz(axis),origin_mm=xyz(origin),repeat_count=1)
        else:
            round_groups.append(g)
    # A reduced complete circular band between two larger circular bands is
    # a supported annular recess. Its production method is not inferred.
    for g in groups:
        if g["side"]!="external" or g["offset"].Length>EPS or g["angles"]<2*math.pi-EPS:continue
        neighbors=[next((h for h in groups if h is not g and h["side"]=="external" and h["offset"].Length<EPS
                         and h["radius"]>g["radius"]+EPS and abs(h["range"][endpoint]-g["range"][1-endpoint])<EPS),None)
                   for endpoint in (1,0)]
        if all(neighbors) and abs(neighbors[0]["radius"]-neighbors[1]["radius"])<EPS:
            f=feature("annular_reduced_region",g["ids"]+neighbors[0]["ids"]+neighbors[1]["ids"],
                      {"axial_width_mm":g["range"][1]-g["range"][0],"radial_depth_mm":neighbors[0]["radius"]-g["radius"]},
                      "Complete reduced coaxial circular band bounded by larger equal-radius bands; geometric recess, no manufacturing process assigned")
            candidate(f,"radial_gap",neighbors[0]["radius"]-g["radius"],"Annular recess radial depth",priority=60,
                      radius_faces=[g["ids"][0],neighbors[0]["ids"][0]],preferred_views=["section"],axis=xyz(axis))
    # Repeated native offset arcs: do not assert a fillet unless neighboring
    # planes are actually tangent. Radius remains directly measurable either way.
    repeated=[]
    for g in round_groups:
        group=next((r for r in repeated if abs(r[0]["radius"]-g["radius"])<EPS and r[0]["side"]==g["side"] and abs(r[0]["range"][1]-g["range"][1])<EPS),None)
        if group is None:
            group=[]; repeated.append(group)
        group.append(g)
    for group in repeated:
        ids=[i for g in group for i in g["ids"]]
        tangent=True
        tangent_plane_ids=set()
        for g in group:
            surface=faces[g["ids"][0]-1].Surface
            planes=[p for p in faces if isinstance(p.Surface,Part.Plane) and abs(unit(p.Surface.Axis).dot(axis))<1e-8
                    and abs(abs((surface.Center-p.Surface.Position).dot(unit(p.Surface.Axis)))-surface.Radius)<EPS
                    and any(a.isSame(b) for fid in g["ids"] for a in faces[fid-1].Edges for b in p.Edges)]
            tangent &= len(planes)>=2
            tangent_plane_ids.update(i for i,p in enumerate(faces,1) if any(p.isSame(t) for t in planes))
        f=feature("repeated_fillet" if tangent else "repeated_curved_patches",ids,
                  {"radius_mm":group[0]["radius"],"repeat_count":len(group)},
                  "Native cylindrical radius and distinct offset axes; tangent adjacent planes verified" if tangent else "Native equal-radius curved surfaces on distinct offset axes; manufacturing function not inferred",
                  boundary_side=group[0]["side"],member_feature_ids=[g["feature"]["id"] for g in group],
                  tangent_plane_ids=sorted(tangent_plane_ids))
        for g in group:g["feature"]["represented_by_feature"]=f["id"]
        c=candidate(f,"radius",group[0]["radius"],"Repeated corner/relief radius",priority=55,
                    preferred_views=["right_end","left_end"] if group[0]["side"]=="internal" else ["left_end","right_end"],
                    repeat_count=len(group),axis=xyz(axis),boundary_side=group[0]["side"])
        offsets=[g["offset"].Length for g in group]
        if max(offsets)-min(offsets)<EPS:
            candidate(f,"radial_offset",sum(offsets)/len(offsets),"Repeated curved-feature axis radial offset",priority=54,
                      preferred_views=["right_end","left_end"] if group[0]["side"]=="internal" else ["left_end","right_end"],
                      repeat_count=len(group),axis=xyz(axis),origin_mm=xyz(origin))
        if group[0]["radius"]<total*0.005:
            c.update(verification_status="presentation_optional",reason="Small local radius relative to part envelope; report retained to avoid clutter")

    # External AND internal regular support-plane regions. Rounded corners do
    # not license a theoretical sharp across-corners measurement.
    polygon_sets=[]
    eligible=[(i,f,(f.Surface.Position-origin).dot(unit(f.normalAt(*middle_parameters(f))))) for i,f in enumerate(faces,1)
              if isinstance(f.Surface,Part.Plane) and abs(unit(f.Surface.Axis).dot(axis))*total<EPS]
    for anchor,face,offset in eligible:
        ar=axial_bounds(face,axis,origin); mid=sum(ar)/2
        active=[(i,f,o) for i,f,o in eligible if (o>0)==(offset>0) and abs(abs(o)-abs(offset))<EPS
                and axial_bounds(f,axis,origin)[0]+EPS<mid<axial_bounds(f,axis,origin)[1]-EPS]
        ids=sorted(i for i,_,_ in active)
        if len(active)<3 or ids in polygon_sets:
            continue
        normals=[unit(f.normalAt(*middle_parameters(f))) for _,f,_ in active]
        up=normals[0]; cross=axis.cross(up)
        ordered=sorted(normals,key=lambda n:math.atan2(n.dot(cross),n.dot(up))%(2*math.pi))
        expected=math.cos(2*math.pi/len(active))
        if any(abs(ordered[i].dot(ordered[(i+1)%len(active)])-expected)>1e-5 for i in range(len(active))):
            continue
        polygon_sets.append(ids)
        f=feature("polygonal_region",ids,{"side_count":len(ids),"across_flats_mm":2*abs(offset),
                  "axial_range_mm":[max(axial_bounds(p,axis,origin)[0] for _,p,_ in active),min(axial_bounds(p,axis,origin)[1] for _,p,_ in active)]},
                  "Regular equal-offset supporting planes with common axial overlap and uniform normal spacing",boundary_side="external" if offset>0 else "internal")
        if len(ids)%2==0:
            candidate(f,"across_flats",2*abs(offset),f"{len(ids)}-sided region across flats",priority=85,
                      preferred_views=["right_end","left_end"] if offset<0 else ["left_end","right_end"],axis=xyz(axis))
        else:
            candidate(f,"polygon_width",None,"Odd-sided polygon support spacing",verification_status="unsupported",reason="No opposing parallel pair; no invented across-flats dimension")
        bounds=f["measured_geometry"]["axial_range_mm"]
        ends=[next((s for s in stations if abs(s["station_mm"]-v)<EPS),None) for v in bounds]
        c=candidate(f,"axial_distance",bounds[1]-bounds[0],"Polygonal region axial span",ends if all(ends) else [],priority=82 if offset<0 else 62,
                    axis=xyz(axis),origin_mm=xyz(origin),preferred_views=["section","longitudinal"])
        if not all(ends):c.update(verification_status="unsupported",reason="Polygon faces begin/end at curved varying intersections rather than uniform perpendicular boundaries")

    # Native cones grouped only when their actual axes and cone laws agree.
    cones=[]
    for i,face in enumerate(faces,1):
        s=face.Surface
        if not isinstance(s,Part.Cone): continue
        coax=parallel(s.Axis,axis) and transverse(s.Center-origin,axis).Length<EPS
        group=next((g for g in cones if (s.Apex-g["apex"]).Length<EPS and abs(s.SemiAngle-g["angle"])<1e-7),None)
        if group is None:
            group={"ids":[],"apex":s.Apex,"angle":s.SemiAngle,"coaxial":coax};cones.append(group)
        group["ids"].append(i)
    for g in cones:
        bounds=[min(axial_bounds(faces[i-1],axis,origin)[0] for i in g["ids"]),max(axial_bounds(faces[i-1],axis,origin)[1] for i in g["ids"])]
        f=feature("conical_transition" if g["coaxial"] else "oblique_conical_patch",g["ids"],
                  {"semi_angle_deg":math.degrees(abs(g["angle"])),"axial_range_mm":bounds,"axial_span_mm":bounds[1]-bounds[0]},
                  "Native analytic cone law; not automatically called a chamfer or countersink")
        ends=[next((s for s in stations if abs(s["station_mm"]-v)<EPS and any(sup["type"] in ("rim","axial_edge") and any(
            edges[e-1].isSame(fe) for fid in g["ids"] for fe in faces[fid-1].Edges for e in sup["edges"]) for sup in s["supports"])),None) for v in bounds]
        c=candidate(f,"axial_distance",bounds[1]-bounds[0],"Conical transition axial extent",ends if all(ends) else [],priority=60,axis=xyz(axis),origin_mm=xyz(origin),preferred_views=["section","longitudinal"])
        if not g["coaxial"] or not all(ends):
            c.update(verification_status="unsupported",reason="Cone is oblique or its trimmed end is not a constant complete axial rim; extrema alone do not establish a uniform chamfer length")
        c=candidate(f,"cone_angle",2*math.degrees(abs(g["angle"])),"Included taper angle",priority=55,axis=xyz(axis),origin_mm=xyz(origin),preferred_views=["section"])
        if not g["coaxial"]:
            c.update(verification_status="unsupported",reason="Local oblique cone is not a single coaxial taper; no uniform part taper assigned")
        for end in ends:
            if end:
                rimids=sorted({e for sup in end["supports"] if sup["type"] in ("rim","axial_edge") for e in sup["edges"] if any(edges[e-1].isSame(fe) for fid in g["ids"] for fe in faces[fid-1].Edges)})
                rs=[transverse(edges[e-1].valueAt(edges[e-1].FirstParameter+(edges[e-1].LastParameter-edges[e-1].FirstParameter)*t)-origin,axis).Length
                    for e in rimids for t in (0,.25,.5,.75,1)]
                if rs and max(rs)-min(rs)<EPS:
                    candidate(f,"curve_diameter",2*sum(rs)/len(rs),"Conical rim diameter",priority=70,source_edges=rimids,preferred_views=["right_end","left_end","section"],axis=xyz(axis),origin_mm=xyz(origin),station_mm=end["station_mm"])

    internal_planes=[(i,p,o) for i,p,o in eligible if o<0 and i not in covered]
    if len(internal_planes)>=2:
        bounds=[max(axial_bounds(p,axis,origin)[0] for _,p,_ in internal_planes),min(axial_bounds(p,axis,origin)[1] for _,p,_ in internal_planes)]
        if bounds[1]-bounds[0]>EPS:
            f=feature("nonregular_internal_planar_region",[i for i,_,_ in internal_planes],
                      {"axial_range_mm":bounds,"support_plane_offsets_mm":[abs(o) for _,_,o in internal_planes]},
                      "Internal parallel-to-axis planes with common axial overlap; normals do not establish a regular polygon")
            ends=[next((s for s in stations if abs(s["station_mm"]-v)<EPS),None) for v in bounds]
            c=candidate(f,"axial_distance",bounds[1]-bounds[0],"Noncircular internal region depth",ends if all(ends) else [],priority=84,
                        axis=xyz(axis),origin_mm=xyz(origin),preferred_views=["section","longitudinal"])
            if not all(ends):c.update(verification_status="unsupported",reason="Nonuniform internal planar region ends")
            pairs=[]
            for i,p,o in internal_planes:
                n=unit(p.Surface.Axis)
                for j,q,t in internal_planes:
                    if j<=i or abs(n.dot(unit(q.Surface.Axis)))<1-1e-8:continue
                    gap=abs((p.Surface.Position-q.Surface.Position).dot(n))
                    if gap>EPS:pairs.append({"faces":[i,j],"distance_mm":gap})
            spacing_groups=[]
            for pair in pairs:
                group=next((g for g in spacing_groups if abs(g[0]["distance_mm"]-pair["distance_mm"])<EPS),None)
                if group is None:group=[];spacing_groups.append(group)
                group.append(pair)
            for group in spacing_groups:
                candidate(f,"plane_gap",group[0]["distance_mm"],"Opposite internal planar wall spacing",priority=76,
                          supporting_pair=group[0]["faces"],repeat_supporting_pairs=[p["faces"] for p in group],
                          repeat_count=len(group),preferred_views=["right_end","left_end"],axis=xyz(axis))
            representatives=[pair["faces"][0] for pair in pairs]
            for first,second in zip(representatives,representatives[1:]):
                normals=[unit(faces[i-1].normalAt(*middle_parameters(faces[i-1]))) for i in (first,second)]
                angle=180-math.degrees(math.acos(max(-1,min(1,normals[0].dot(normals[1])))))
                c=candidate(f,"plane_angle",angle,"Included angle between internal wall planes",priority=58,
                            supporting_pair=[first,second],preferred_views=["right_end","left_end"],axis=xyz(axis),origin_mm=xyz(origin),
                            angle_basis="Included cavity-side angle; oriented wall normals point toward the recovered axis")
                c["units"]="deg"

    # Terminal inner wires are actual openings. Inner wires of an intermediate
    # shoulder are junction footprints, not automatically holes.
    for i,face in enumerate(faces,1):
        if not isinstance(face.Surface,Part.Plane) or abs(unit(face.Surface.Axis).dot(axis))<1-1e-8:
            continue
        st=(face.CenterOfMass-origin).dot(axis)
        if min(abs(st-low),abs(st-high))>EPS: continue
        for wire in face.Wires:
            if wire.isSame(face.OuterWire):continue
            radii=[transverse(e.valueAt(e.FirstParameter+(e.LastParameter-e.FirstParameter)*t)-origin,axis).Length for e in wire.Edges for t in (0,.25,.5,.75,1)]
            if max(radii)-min(radii)<EPS:continue
            if all(isinstance(e.Curve,Part.Circle) for e in wire.Edges):
                cs=[e.Curve for e in wire.Edges]
                if max(c.Radius for c in cs)-min(c.Radius for c in cs)<EPS and all((c.Center-cs[0].Center).Length<EPS for c in cs):continue
            ids=[edge_number(shape,e) for e in wire.Edges]
            f=feature("noncircular_terminal_opening",[i],{"source_edges":ids,"axial_station_mm":st},"Closed noncircular inner wire of a terminal perpendicular planar face; no drive/thread function inferred")
            for direction in ("x","y"):
                candidate(f,"opening_extent",None,"Noncircular opening " + ("width" if direction=="x" else "height"),priority=75,source_edges=ids,extent_direction=direction,preferred_views=["right_end","left_end"],axis=xyz(axis))

    # Native toroidal fillets are recorded explicitly, with measurable minor R.
    torigroups=[]
    for i,face in enumerate(faces,1):
        s=face.Surface
        if type(s).__name__ not in ("Toroid","ToroidalSurface"):continue
        group=next((g for g in torigroups if abs(g["radius"]-s.MinorRadius)<EPS and (g["center"]-s.Center).Length<EPS),None)
        if group is None: group={"ids":[],"radius":s.MinorRadius,"center":s.Center};torigroups.append(group)
        group["ids"].append(i)
    for g in torigroups:
        f=feature("toroidal_round",g["ids"],{"minor_radius_mm":g["radius"]},"Native toroidal surface minor radius; adjacent design function not inferred")
        c=candidate(f,"torus_radius",g["radius"],"Toroidal transition radius",priority=50,preferred_views=["section"])
        if g["radius"]<total*.005:c.update(verification_status="presentation_optional",reason="Small transition radius; retained in coverage rather than crowding the sheet")

    result["axis"]={"direction":xyz(axis),"origin_mm":xyz(origin),"range_mm":[low,high]}
    result["axial_stations"]=stations
    result["datum"]={"station":datum,"basis":"Annular enlargement shoulder; geometric baseline, not asserted functional design datum"} if datum else {"station":terminal[0],"basis":"Terminal plane/rim; no suitable enlargement shoulder established"}
    if datum:
        # Baselines to every other genuine rim/plane station are candidates.
        # Selection later rejects cycles and coordinates already implied.
        for s in stations:
            if abs(s["station_mm"]-datum["station_mm"])<EPS:continue
            f=feature("axial_boundary",sorted({i for sup in s["supports"] if sup["type"]=="plane" for i in sup["faces"]}),{"station_mm":s["station_mm"],"distance_from_datum_mm":abs(s["station_mm"]-datum["station_mm"])},"Actual perpendicular plane/circular rim; no tangency extrema promoted to a shoulder")
            candidate(f,"axial_distance",abs(s["station_mm"]-datum["station_mm"]),"Axial boundary from geometric datum",[datum,s],priority=70,axis=xyz(axis),origin_mm=xyz(origin),preferred_views=["longitudinal","section"],baseline=True)
    result["unmapped_faces"]=[{"face":i,"surface_type":type(face.Surface).__name__,"reason":"Planar connecting surface/complex patch not represented as a distinct recognized feature; review geometry"} for i,face in enumerate(faces,1) if i not in covered]
    result["limitations"]=["Surface seams are grouped; complex nonanalytic and oblique transitions may remain unresolved.","Repeat counts describe supported equal-radius occurrences, not a manufacturing pattern specification."]
    return result
