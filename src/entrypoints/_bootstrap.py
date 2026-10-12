"""Make src packages available to direct scripts in either Python environment."""
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

from fastener_paths import PROJECT_ROOT
