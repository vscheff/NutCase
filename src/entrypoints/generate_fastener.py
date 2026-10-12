"""External-Python entry point. Never run this in FreeCAD's bundled Python."""
import _bootstrap
from fastener_drawing.pipeline import main

if __name__=='__main__':
    raise SystemExit(main())
