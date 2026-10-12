"""Entry point for FreeCAD's bundled Python (also usable from its Python console)."""
import _bootstrap

from fastener_analysis.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
