"""Inspect the runtime actually executing the analysis."""
import importlib.util
import platform
import sys
from pathlib import Path


def load_native_modules():
    try:
        # Loading FreeCAD initializes the installed module and DLL search paths.
        import FreeCAD as App
        import Part
    except ImportError as exc:
        raise RuntimeError(
            "FreeCAD/Part cannot be imported. Run with FreeCAD's bundled Python "
            "or use scripts/analyze-step.ps1 to discover it. " + str(exc)
        ) from exc
    return App, Part


def inspect_environment():
    App, Part = load_native_modules()
    binary_dir = Path(App.__file__).resolve().parent
    return {
        "freecad_version": App.Version(),
        "python_version": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "freecad_module": App.__file__,
        "part_module": Part.__file__,
        "opencascade_version": getattr(Part, "OCC_VERSION", None),
        "executables": {
            name: str(binary_dir / name) if (binary_dir / name).is_file() else None
            for name in ("freecad.exe", "freecadcmd.exe", "python.exe", "pythonw.exe")
        },
        "capabilities": {
            "headless_native_import": True,
            "geometry_bounding_without_triangulation": hasattr(Part.Shape(), "optimalBoundingBox"),
            "extended_boolean_check": hasattr(Part.Shape(), "check"),
            "techdraw_module_available": importlib.util.find_spec("TechDraw") is not None,
            "techdraw_execution_tested": False,
        },
        "execution_method": "Bundled python.exe importing FreeCAD before Part; no GUI required",
    }
