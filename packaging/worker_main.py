"""Analyze with src ahead of entrypoints, keeping fastener_gui a package."""
from entrypoints.nutcase_worker import main

if __name__=='__main__':raise SystemExit(main())
