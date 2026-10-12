"""Structured JSON serialization; future drawing export belongs in a separate module."""
import json
from pathlib import Path


def write_json(report, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as target:
        json.dump(report, target, indent=2, ensure_ascii=False, allow_nan=False)
        target.write("\n")
    temporary.replace(destination)
    return destination
