"""Bundled-Python entry point; initialize isolated GUI resources before native imports."""
import os
import sys

import _bootstrap
from fastener_paths import native_runtime_home
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Keep batch preferences and document cache in NutCase's runtime cache.
# Never change an already running FreeCAD GUI's user directories.
if "FreeCAD" not in sys.modules:
    os.environ["FREECAD_USER_HOME"] = str(native_runtime_home())

from fastener_drawing.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
