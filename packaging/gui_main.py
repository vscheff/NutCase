"""Distinct module name prevents fastener_gui.py shadowing its source package."""
from entrypoints.fastener_gui import main

if __name__=='__main__':raise SystemExit(main())
