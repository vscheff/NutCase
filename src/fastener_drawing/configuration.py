"""User policy and conservative source bindings. No CAD or PDF dependencies."""
import copy
import hashlib
import json
import math
from pathlib import Path


DEFAULT = {
    "schema_version": 1,
    "dimensioning": {"mode": "comprehensive", "include": [], "exclude": []},
    "views": {"isometric": True, "opposite_end": True, "section": True, "opening_detail": True},
    "sheet": {"size": "auto"},
    "scale": "auto",
    "orientation": {"axis": None, "up": None},
    "metadata": {"title": "IMPORTED STEP GEOMETRY", "drawing_number": "", "revision": "", "date": None},
    "source_binding": None,
}


def normalize_metadata_date(value):
    """Accept ISO or month/day/year input and return canonical ISO text."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if not isinstance(value, str):
        raise ValueError("Date must be YYYY-MM-DD or MM/dd/yyyy")
    from datetime import date, datetime
    text=value.strip()
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        try:
            return datetime.strptime(text, "%m/%d/%Y").date().isoformat()
        except ValueError as exc:
            raise ValueError("Date must be a valid YYYY-MM-DD or MM/dd/yyyy date") from exc


def read_config(path=None):
    def unique_pairs(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate JSON configuration field: '+key)
            result[key]=value
        return result
    supplied = json.loads(Path(path).read_text(encoding="utf-8-sig"),object_pairs_hook=unique_pairs) if path else {}
    if not isinstance(supplied, dict):
        raise ValueError("Configuration must be a JSON object")
    result = copy.deepcopy(DEFAULT)
    for key, value in supplied.items():
        if key not in DEFAULT:
            raise ValueError("Unknown configuration field: " + key)
        if isinstance(DEFAULT[key], dict):
            if not isinstance(value, dict) or set(value) - set(DEFAULT[key]):
                raise ValueError("Unknown or invalid fields in " + key)
            result[key].update(value)
        else:
            result[key] = value
    result["metadata"]["date"] = normalize_metadata_date(result["metadata"]["date"])
    validate_config(result)
    return result


def validate_config(c):
    if type(c["schema_version"]) is not int or c["schema_version"] != 1:
        raise ValueError("Unsupported configuration schema")
    d = c["dimensioning"]
    if d["mode"] not in ("basic", "comprehensive", "custom"):
        raise ValueError("dimensioning.mode must be basic, comprehensive or custom")
    for key in ("include", "exclude"):
        if not isinstance(d[key], list) or any(not isinstance(x, str) or not x.startswith("g1-") for x in d[key]):
            raise ValueError(key + " must contain stable g1- source candidate identities from the catalog")
        if len(set(d[key])) != len(d[key]):
            raise ValueError("Duplicate dimension selection in " + key)
    if set(d["include"]) & set(d["exclude"]):
        raise ValueError("A dimension cannot be both included and excluded")
    if any(type(x) is not bool for x in c["views"].values()):
        raise ValueError("View selections must be JSON booleans")
    from .layout import SHEETS
    if c["sheet"]["size"] not in (*SHEETS, "auto"):
        raise ValueError("Unsupported sheet size")
    s = c["scale"]
    if s != "auto" and (type(s) not in (int, float) or not math.isfinite(s) or s <= 0):
        raise ValueError("scale must be auto or a finite positive paper/model ratio")
    for key, vector in c["orientation"].items():
        if vector is not None and (not isinstance(vector, list) or len(vector) != 3 or
                any(type(x) not in (float, int) or not math.isfinite(x) for x in vector) or
                sum(x*x for x in vector) < 1e-20):
            raise ValueError("orientation." + key + " must be a finite nonzero three-vector")
    m = c["metadata"]
    for key, limit in (("title", 65), ("drawing_number", 32), ("revision", 12)):
        if not isinstance(m[key], str) or len(m[key]) > limit or any(ord(x) < 32 for x in m[key]):
            raise ValueError("Invalid or overlong metadata." + key)
    if m["date"] is not None:
        normalize_metadata_date(m["date"])
    if c["source_binding"] is not None and (not isinstance(c["source_binding"], dict) or
            set(c["source_binding"]) != {"geometry_id", "source_sha256", "candidate_ids"}):
        raise ValueError("Invalid source_binding; use an emitted bound configuration")
    if c['source_binding'] is not None:
        b=c['source_binding']
        if not isinstance(b['geometry_id'],str) or not isinstance(b['source_sha256'],str) or not isinstance(b['candidate_ids'],list) or any(not isinstance(x,str) for x in b['candidate_ids']):
            raise ValueError('Invalid source binding values')


def canonical(value):
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Nonfinite source evidence")
        return round(value, 9)
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [canonical(x) for x in value]
    return value


def fingerprint(value):
    return hashlib.sha256(json.dumps(canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def make_catalog(discovery, signature, source_sha256):
    """Replace transient source face/edge numbering with native geometry evidence.

    UV/curve bounds and probes are validation fingerprints, not a mathematical
    equivalence proof. Changed pose, trim, topology or importer output is deliberately
    incompatible. Existing independent BRep measurement remains mandatory.
    """
    faces = [fingerprint(x) for x in signature["face_geometry"]]
    edges = [fingerprint(x) for x in signature["edge_geometry"]]
    face_keys = {"source_faces", "faces", "supporting_pair", "repeat_supporting_pairs", "radius_faces", "tangent_plane_ids", "extent_supporting_pair"}
    edge_keys = {"source_edges", "edges"}
    ignored = {"id", "feature_id", "candidate_ids", "member_feature_ids", "represented_by_feature", "preferred_views", "priority",
               "verification_status", "proposed_dimension_type", "reason", "stable_id"}

    def evidence(value, key=""):
        if isinstance(value, dict):
            return {k: evidence(v, k) for k, v in value.items() if k not in ignored}
        if isinstance(value, list):
            if key in face_keys | edge_keys:
                return sorted([evidence(v, key) for v in value],key=lambda x:json.dumps(x,sort_keys=True))
            items=[evidence(v) for v in value]
            return sorted(items,key=lambda x:json.dumps(x,sort_keys=True)) if key=='supports' else items
        if type(value) is int and key in face_keys | edge_keys:
            return (faces if key in face_keys else edges)[value-1]
        return value

    features = {f["id"]: f for f in discovery["features"]}
    rows = []
    for c in discovery["dimension_candidates"]:
        proof = evidence({"candidate": c, "feature": features[c["feature_id"]]})
        stable = "g1-" + fingerprint(proof)
        c["stable_id"] = stable
        rows.append({"stable_id": stable, "candidate_id": c["id"], "label": c["label"], "kind": c["kind"],
                     "value": c["value"], "units": c["units"], "verification_status": c["verification_status"],
                     "source_evidence": canonical(proof)})
    if len({r["stable_id"] for r in rows}) != len(rows):
        raise ValueError("Ambiguous source candidate identity; saved selection is refused")
    geometry = {k: v for k, v in signature.items() if k not in ("brep_sha256", "face_geometry", "edge_geometry")}
    geometry.update(faces=sorted(faces), edges=sorted(edges))
    return {"schema_version": 1, "geometry_id": fingerprint(geometry), "source_sha256": source_sha256,
            "candidates": rows, "binding_policy": "Conservative native geometry fingerprint; changed pose/trim/topology requires review, even at equal dimension values. 1e-9 rounding is numeric fingerprint resolution, never a manufacturing tolerance."}


def bind_config(config, catalog):
    c = copy.deepcopy(config)
    actual = {r["stable_id"] for r in catalog["candidates"]}
    d, binding = c["dimensioning"], c["source_binding"]
    wanted = set(d["include"] + d["exclude"])
    if wanted and binding is None:
        raise ValueError("Explicit selections require a source_binding from the emitted .config.json; review the new catalog")
    if binding is not None:
        if binding["geometry_id"] != catalog["geometry_id"] or set(binding["candidate_ids"]) != actual:
            raise ValueError("Saved source references are incompatible; review the new catalog and rebind explicitly")
    if wanted - actual:
        raise ValueError("Invalid saved candidate references: " + ", ".join(sorted(wanted-actual)))
    c["source_binding"] = {"geometry_id": catalog["geometry_id"], "source_sha256": catalog["source_sha256"], "candidate_ids": sorted(actual)}
    return c


def selection_decisions(config, discovery):
    d = config["dimensioning"]
    candidates = discovery["dimension_candidates"]
    features = {f["id"]: f for f in discovery["features"]}
    # Basic is geometric: do not relabel cylindrical bodies as heads/shanks.
    external = [c for c in candidates if c["kind"] == "diameter" and c.get("boundary_side") == "external" and features[c["feature_id"]].get("coaxial")]
    internal = [c for c in candidates if c["kind"] == "diameter" and c.get("boundary_side") == "internal" and features[c["feature_id"]].get("coaxial")]
    primary = {c["stable_id"] for c in external}  # distinct source-supported external regions, dedup still applies
    if internal:
        primary.add(min(internal, key=lambda x: (x["value"], x["stable_id"]))["stable_id"])
    for c in candidates:
        f = features[c["feature_id"]]
        if c["kind"] in ("overall", "across_flats") or f["type"] == "terminal_enlargement":
            primary.add(c["stable_id"])
    result = {}
    for c in candidates:
        key = c["stable_id"]
        selected = d["mode"] == "comprehensive" or (key in primary if d["mode"] == "basic" else False)
        reason = "Mode " + d["mode"]
        if key in d["include"]:
            selected, reason = True, "Explicit inclusion"
        if key in d["exclude"]:
            selected, reason = False, "Explicit exclusion"
        result[c["id"]] = {"selected": selected, "selection_reason": reason, "stable_id": key}
    return result
