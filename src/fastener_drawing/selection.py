"""Geometry-aware redundancy decisions, independent of native dimension placement."""
import math
from .references import MATCH_MM


class Selection:
    def __init__(self, discovery):
        self.discovery = discovery
        self.parent = {}
        self.accepted = []

    def root(self, key):
        self.parent.setdefault(key,key)
        if self.parent[key]!=key:self.parent[key]=self.root(self.parent[key])
        return self.parent[key]

    def reason(self,candidate):
        supports=candidate.get("source_supports",[])
        if candidate["kind"]=="opening_extent" and candidate.get("extent_supporting_pair"):
            pair=set(candidate["extent_supporting_pair"])
            for previous in self.accepted:
                if previous["kind"]=="plane_gap" and any(pair==set(p) for p in previous.get("repeat_supporting_pairs",[previous["supporting_pair"]])):
                    return "The opening extrema lie on the actual opposing wall planes already covered by the verified spacing dimension"
        if candidate["kind"] in ("overall","axial_distance") and len(supports)==2:
            if self.root(supports[0]["id"])==self.root(supports[1]["id"]):
                return "Two axial stations are already related by placed dimensions; omitted to avoid a closed/redundant dimension chain"
        if candidate["kind"]=="curve_diameter":
            for previous in self.accepted:
                if previous["kind"]!="diameter" or abs(previous["value"]-candidate["value"])>MATCH_MM:continue
                region=next(f for f in self.discovery["features"] if f["id"]==previous["feature_id"])
                if not region.get("coaxial"):continue
                ends=region["measured_geometry"]["axial_range_mm"]
                if min(abs(candidate["station_mm"]-e) for e in ends)<MATCH_MM:
                    return "This cone rim meets an already dimensioned coaxial cylinder of the same measured diameter"
        if candidate["kind"]=="diameter":
            for previous in self.accepted:
                if (previous["kind"]=="diameter" and candidate.get("origin_mm")==previous.get("origin_mm")
                        and candidate.get("boundary_side")==previous.get("boundary_side")
                        and abs(previous["value"]-candidate["value"])<MATCH_MM):
                    # Offset cylinders must additionally share their actual axis;
                    # equality of radius alone never proves this.
                    first=next(f for f in self.discovery["features"] if f["id"]==candidate["feature_id"])
                    second=next(f for f in self.discovery["features"] if f["id"]==previous["feature_id"])
                    if first.get("coaxial") and second.get("coaxial"):
                        return "Same supported coaxial diameter already placed; separate region lengths/locations remain candidates"
        if candidate["kind"]=="radial_offset":
            f=next(f for f in self.discovery["features"] if f["id"]==candidate["feature_id"])
            radii=[c for c in self.accepted if c["feature_id"]==f["id"] and c["kind"]=="radius"]
            if f["type"]=="repeated_fillet" and radii:
                for c in self.accepted:
                    if c["kind"]!="across_flats":continue
                    polygon=next(f for f in self.discovery["features"] if f["id"]==c["feature_id"])
                    if not f.get("tangent_plane_ids") or not set(f["tangent_plane_ids"]).issubset(polygon["source_faces"]):continue
                    sides=polygon["measured_geometry"]["side_count"]
                    expected=(c["value"]/2-radii[0]["value"])/math.cos(math.pi/sides)
                    if abs(expected-candidate["value"])<MATCH_MM:
                        return "Verified regular polygon flats and tangent corner radius already determine this measured offset; no extra center-location dimension"
        if candidate["kind"]=="cone_angle":
            related=[c for c in self.discovery["dimension_candidates"] if c["feature_id"]==candidate["feature_id"]]
            span=next((c for c in related if c["kind"]=="axial_distance" and len(c["source_supports"])==2),None)
            rims=[c for c in related if c["kind"]=="curve_diameter"]
            if span and len(rims)==2 and self.root(span["source_supports"][0]["id"])==self.root(span["source_supports"][1]["id"]):
                if all(any(c["id"]==p["id"] for p in self.accepted) or self.reason(c) for c in rims):
                    return "Both supported rim diameters and their axial separation are already dimensioned; the analytic cone angle is dependent"
        return None

    def accept(self,candidate):
        supports=candidate.get("source_supports",[])
        if candidate["kind"] in ("overall","axial_distance") and len(supports)==2:
            self.parent[self.root(supports[0]["id"])]=self.root(supports[1]["id"])
        self.accepted.append(candidate)


def coverage(discovery,reports):
    features=[]
    for f in discovery["features"]:
        ids=f["candidate_ids"]
        if f.get("represented_by_feature"):
            ids=next(item["candidate_ids"] for item in discovery["features"] if item["id"]==f["represented_by_feature"])
        rows=[{"candidate_id":k, **reports[k]} for k in ids]
        features.append({**f,"dimensions":rows,"placed_dimensions":[r["candidate_id"] for r in rows if r["status"]=="created"],
                         "unresolved_dimensions":[r["candidate_id"] for r in rows if r["status"]=="unresolved"],
                         "redundant_dimensions":[r["candidate_id"] for r in rows if r["status"]=="omitted_redundant"]})
    counts={s:sum(r["status"]==s for r in reports.values()) for s in ("created","unresolved","omitted_redundant","omitted_optional","suppressed_by_configuration")}
    return {"recognition_is_exhaustive":False,"dimensional_completeness_claimed":False,"counts":counts,"features":features,
            "unmapped_faces":discovery["unmapped_faces"],"notice":discovery["coverage_notice"]}


def write_summary(path,report):
    cov=report["dimensional_coverage"]
    lines=["# Dimensional coverage", "", report["source"], "", cov["notice"], "",
           "Placed: {created}; unresolved: {unresolved}; redundant: {omitted_redundant}; optional: {omitted_optional}.".format(**cov["counts"]), ""]
    if cov['counts'].get('suppressed_by_configuration'):
        lines += [f"Suppressed by configuration: {cov['counts']['suppressed_by_configuration']}.", ""]
    for f in cov["features"]:
        if f["dimensions"]:
            lines.extend([f"## {f['id']} - {f['type']}","",f["classification_basis"],""])
            for row in f["dimensions"]:
                label=row.get("candidate",{}).get("label",row.get("source_feature",{}).get("candidate",{}).get("label",row["candidate_id"]))
                lines.append(f"- {row['candidate_id']} {label}: {row['status']}" + (f" on {row['view_role']}" if row["status"]=="created" else ": "+row.get("reason","")))
            lines.append("")
    lines += ["## Geometry still requiring review", "", "Extended Boolean failures are retained. No source healing, nominal thread assignments, tolerances, materials or finish specifications were added.", "",
              "Unmapped source faces: "+", ".join(str(r["face"]) for r in cov["unmapped_faces"])+".",
              "Complex trims, nonanalytic patches, unproved feature functions and undimensioned offsets/angles require engineering review."]
    hatch=report.get("section_diagnostics",{}).get("hatching",{})
    if hatch:
        lines += ["", "Axial cut hatching: "+hatch["status"]+". "+hatch["reason"]+"."]
        if hatch.get('association'):
            lines += ["", "Hatch update behavior: "+hatch['association']+"."]
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")
