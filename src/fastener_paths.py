"""Shared source and project-data locations, independent of working directory."""
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = SOURCE_ROOT.parent
ENTRYPOINTS = SOURCE_ROOT / 'entrypoints'
