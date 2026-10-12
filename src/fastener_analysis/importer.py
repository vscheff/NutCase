"""Read-only STEP import and explicit basic/extended validation."""
import hashlib
from collections import Counter
from pathlib import Path

from .runtime import load_native_modules


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def import_step(path):
    _, Part = load_native_modules()
    # strict=True uses an extra Windows handle query that is blocked in some
    # restricted launch environments; ordinary stat/open below still verify input.
    path = Path(path).resolve()
    if path.suffix.lower() not in (".step", ".stp"):
        raise ValueError("Input must be a .stp or .step file")
    if not path.is_file():
        raise ValueError("Input is not a regular file")
    original_hash = sha256(path)
    shape = Part.Shape()
    try:
        shape.read(str(path))
    except Exception as exc:
        raise RuntimeError(f"FreeCAD could not read STEP file {path}: {exc}") from exc
    if shape.isNull() or not shape.Faces:
        raise ValueError("STEP import produced no usable boundary-representation faces")
    return shape, {
        "path": str(path), "size_bytes": path.stat().st_size,
        "sha256_before": original_hash, "import_method": "Part.Shape.read",
        "explicit_healing_applied": False,
        "note": "The native STEP reader may normalize geometry internally; no source file is written.",
    }


def _check(shape, extended):
    try:
        result = shape.check(extended)
        # Installed FreeCAD returns None on success and raises on errors.
        errors = [] if result is None else list(result) if isinstance(result, (list, tuple)) else [str(result)]
        return {"status": "passed" if not errors else "failed", "errors": errors}
    except Exception as exc:
        lines = str(exc).splitlines()
        counts = Counter(line for line in lines if line.startswith("Error"))
        return {
            "status": "failed", "exception_type": type(exc).__name__,
            "message": str(exc), "error_count": sum(counts.values()),
            "error_summary": dict(counts),
            "note": "This API's text diagnostic does not supply stable face/edge indices.",
        }


def validate_shape(shape):
    issues = []
    basic_valid = shape.isValid()
    solid_records = [
        {"solid": index, "valid": solid.isValid(), "closed": solid.isClosed(), "volume_mm3": solid.Volume}
        for index, solid in enumerate(shape.Solids, 1)
    ]
    if not basic_valid:
        issues.append("Native BRep validity check failed; feature dimensions are withheld.")
    if len(solid_records) != 1:
        issues.append("Model is not a single solid; analyze component reports separately, not as one fastener.")
    if shape.Solids and sum(len(s.Faces) for s in shape.Solids) < len(shape.Faces):
        issues.append("Additional non-solid faces are present; component recognition excludes them.")
    if not shape.isClosed():
        issues.append("Imported shape is not closed.")
    if any(not r["closed"] or r["volume_mm3"] <= 0 for r in solid_records):
        issues.append("At least one solid is open or has non-positive volume.")
    basic = _check(shape, False)
    extended = _check(shape, True)
    if basic["status"] != "passed":
        issues.append("Detailed BRep check failed; feature dimensions are withheld.")
    if extended["status"] != "passed":
        issues.append("Extended Boolean check failed; measured geometry requires engineering review.")
    return {
        "shape_type": shape.ShapeType, "basic_valid": basic_valid, "closed": shape.isClosed(),
        "counts": {name: len(getattr(shape, name)) for name in ("Solids", "Shells", "Faces", "Edges", "Vertexes")},
        "solids": solid_records, "brep_check": basic, "boolean_check": extended,
        "max_brep_tolerance_mm": shape.globalTolerance(1),
        "issues": issues, "status": "needs_review" if issues else "passed",
        "measurement_note": "BRep tolerance is native numerical geometry metadata, not a manufacturing tolerance.",
    }
