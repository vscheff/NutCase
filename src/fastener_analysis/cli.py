"""Command-line orchestration; import, measurement and recognition remain independent."""
import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .export import write_json
from .runtime import inspect_environment

LOG = logging.getLogger("fastener_analysis")


def build_report(path):
    from .geometry import analyze_geometry, bbox_record
    from .importer import import_step, sha256, validate_shape
    from .recognition import recognize_features
    from .features import discover_features

    environment = inspect_environment()
    LOG.info("FreeCAD %s; Python %s", ".".join(environment["freecad_version"][:3]), sys.version.split()[0])
    shape, source = import_step(path)
    LOG.info("Imported %s: %d solid(s), %d faces", path, len(shape.Solids), len(shape.Faces))
    validation = validate_shape(shape)
    for issue in validation["issues"]:
        LOG.warning(issue)
    report = {
        "schema_version": "1.1", "tool_version": __version__, "phase": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(), "units": "mm",
        "preliminary": True, "requires_engineering_verification": True,
        "notice": "PRELIMINARY GEOMETRY ANALYSIS. Requires engineering verification. No tolerances, material, finish or GD&T are assigned.",
        "source": source, "environment": environment, "validation": validation,
        "global_bounding_box": bbox_record(shape), "components": [],
        "evidence_indexing": "Face/edge numbers are one-based within each native Solid component; tied to this import and source hash, not guaranteed stable across readers/versions.",
    }
    # Do not assume an assembly's largest component is the fastener of interest.
    components = list(shape.Solids)
    if not components:
        report["analysis_status"] = "geometry_only"
        report["manual_review"] = ["No solid imported; global bounding box is diagnostic only."]
    for index, component in enumerate(components, 1):
        local_validation = validate_shape(component)
        geometry, _ = analyze_geometry(component)
        recognition = recognize_features(component, geometry, local_validation)
        features = discover_features(component, geometry, recognition, local_validation)
        report["components"].append({"component": index, "validation": local_validation,
                                     "geometry": geometry, "recognition": recognition, "feature_discovery": features})
        recognized = {k: v["value_mm"] for k, v in recognition["dimensions"].items() if v["status"] == "recognized"}
        LOG.info("Component %d: axis %s; recognized dimensions %s", index, geometry["axis"]["status"], recognized)
    source["sha256_after"] = sha256(source["path"])
    source["unchanged"] = source["sha256_before"] == source["sha256_after"]
    if not source["unchanged"]:
        raise RuntimeError("Source hash changed during analysis; source preservation check failed")
    report.setdefault("analysis_status", "needs_review" if validation["status"] != "passed" else "completed_preliminary")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Phase 1: preliminary STEP fastener geometry analysis using native FreeCAD")
    parser.add_argument("input", nargs="?", type=Path, help="Input .stp or .step file (read only)")
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--inspect-environment", action="store_true", help="Write environment.json without analyzing a file")
    args = parser.parse_args(argv)
    if not args.input and not args.inspect_environment:
        parser.error("Provide an input STEP file or --inspect-environment")
    if args.input and args.inspect_environment:
        parser.error("Use --inspect-environment without an input file; file reports already include runtime details")
    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"Cannot create output directory {args.output_dir}: {exc}", file=sys.stderr)
        return 1
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    stem = args.input.stem if args.input else "environment"
    try:
        file_handler = logging.FileHandler(args.output_dir / (stem + ".analysis.log"), encoding="utf-8", mode="w")
    except OSError as exc:
        print(f"Cannot open output log in {args.output_dir}: {exc}", file=sys.stderr)
        return 1
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    LOG.addHandler(file_handler)
    destination = args.output_dir / (stem + ".analysis.json" if args.input else "environment.json")
    try:
        report = build_report(args.input) if args.input else inspect_environment()
        write_json(report, destination)
        LOG.info("Wrote %s", destination.resolve())
        # Distinguish execution failure (1) from a completed report needing geometry review (2).
        return 2 if report.get("analysis_status") in ("needs_review", "geometry_only") else 0
    except Exception as exc:
        LOG.exception("Analysis failed: %s", exc)
        try:
            write_json({"phase": 1, "analysis_status": "failed", "preliminary": True,
                        "input": str(args.input), "error": {"type": type(exc).__name__, "message": str(exc)}}, destination)
        except OSError as write_error:
            LOG.error("Could not save error report to %s: %s", destination, write_error)
        return 1
    finally:
        LOG.removeHandler(file_handler)
        file_handler.close()
