"""Bundled-Python entry point; initialize isolated GUI resources before native imports."""
import os
import sys

from _bootstrap import PROJECT_ROOT as project_root
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Keep this batch process's preferences and document cache inside the project.
# Never change an already running FreeCAD GUI's user directories.
if "FreeCAD" not in sys.modules:
    runtime_home = project_root / "tmp" / "freecad-runtime"
    (runtime_home / "temp").mkdir(parents=True, exist_ok=True)
    os.environ["FREECAD_USER_HOME"] = str(runtime_home)

from fastener_drawing.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
