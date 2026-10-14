"""Read-only application resources and separate, durable per-user data."""
import os
import sys
from pathlib import Path

FROZEN = bool(getattr(sys, 'frozen', False))
SOURCE_ROOT = (Path(sys.executable).resolve().parent / 'native-src' if FROZEN
               else Path(__file__).resolve().parent)
PROJECT_ROOT = SOURCE_ROOT.parent
ENTRYPOINTS = SOURCE_ROOT / 'entrypoints'
INSTALLED = FROZEN or (PROJECT_ROOT / 'nutcase-build.json').is_file()


def user_data_root():
    # An explicit override supports isolated diagnostics/portable workspaces.
    override = os.environ.get('NUTCASE_DATA_HOME')
    if override:
        return Path(override).resolve()
    if INSTALLED:
        local = os.environ.get('LOCALAPPDATA')
        if not local:
            raise RuntimeError('Windows could not locate your local application-data directory')
        return Path(local) / 'NutCase'
    return PROJECT_ROOT / 'output'


DATA_ROOT = user_data_root()
SETTINGS_ROOT = DATA_ROOT / 'gui-state'
DRAWINGS_ROOT = DATA_ROOT / ('drawings' if INSTALLED else 'gui')
CACHE_ROOT = DATA_ROOT / 'cache' if INSTALLED or os.environ.get('NUTCASE_DATA_HOME') else PROJECT_ROOT / 'tmp'
LOGS_ROOT = DATA_ROOT / 'logs'
VERSION = (PROJECT_ROOT / 'VERSION').read_text(encoding='utf-8').strip()


def native_runtime_home():
    directory = CACHE_ROOT / 'freecad-runtime' / str(os.getpid())
    (directory / 'temp').mkdir(parents=True, exist_ok=True)
    return directory


def require_user_data_path(path):
    path = Path(path).resolve()
    if INSTALLED and path.is_relative_to(PROJECT_ROOT.resolve()):
        raise ValueError('Choose a data directory outside the NutCase installation folder. '
                         'The default is your local application-data directory.')
    return path


# Validate diagnostic overrides before any consumer creates logs or caches.
require_user_data_path(DATA_ROOT)
