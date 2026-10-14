"""Windows prerequisite discovery without PowerShell or development paths."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from fastener_paths import PROJECT_ROOT, ENTRYPOINTS, DATA_ROOT, DRAWINGS_ROOT, SETTINGS_ROOT, CACHE_ROOT, VERSION
from nutcase_runtime import clean_environment, external_dll_search

FREECAD_GUIDANCE = ('NutCase needs the 64-bit FreeCAD 1.1 desktop application. '
                    'Install it from https://www.freecad.org/downloads.php, then restart NutCase. '
                    'For a portable installation, select its bin/python.exe in Settings.')


def registry_roots():
    if os.name != 'nt':
        return []
    import winreg
    roots = []
    key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(hive, key, 0, winreg.KEY_READ | view) as parent:
                    for index in range(winreg.QueryInfoKey(parent)[0]):
                        try:
                            with winreg.OpenKey(parent, winreg.EnumKey(parent, index)) as child:
                                if 'freecad' not in winreg.QueryValueEx(child, 'DisplayName')[0].lower():continue
                                for name in ('InstallLocation', 'DisplayIcon'):
                                    try:
                                        value = winreg.QueryValueEx(child, name)[0]
                                        if name == 'DisplayIcon':
                                            value = re.sub(r',-?\d+$', '', value).strip('"')
                                            value = str(Path(value).parent.parent)
                                        roots.append(Path(value))
                                    except OSError:pass
                        except OSError:pass
            except OSError:pass
    return roots


def freecad_candidates():
    roots = []
    if os.environ.get('FREECAD_HOME'):roots.append(Path(os.environ['FREECAD_HOME']))
    for command in ('freecad.exe', 'freecadcmd.exe'):
        path = shutil.which(command)
        if path:roots.append(Path(path).parent.parent)
    roots.extend(registry_roots())
    for key in ('ProgramW6432', 'ProgramFiles', 'LOCALAPPDATA'):
        if not os.environ.get(key):continue
        parent = Path(os.environ[key]) / 'Programs' if key == 'LOCALAPPDATA' else Path(os.environ[key])
        try:roots.extend(sorted(parent.glob('FreeCAD*'), reverse=True))
        except OSError:pass
    seen = set()
    for root in roots:
        python = (root / 'bin' / 'python.exe').resolve()
        if python not in seen and python.is_file():
            seen.add(python)
            yield python


def probe_freecad(python):
    with external_dll_search():
        result = subprocess.run([str(python), str(ENTRYPOINTS / 'probe_runtime.py'), 'freecad', '--json'],
                                cwd=Path(python).parent, env=clean_environment(),
                                capture_output=True, text=True, timeout=30,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise ValueError('The selected FreeCAD runtime could not load Part, TechDraw and its GUI. '+FREECAD_GUIDANCE)
    for line in result.stdout.splitlines():
        if line.startswith('NUTCASE_NATIVE_RUNTIME='):
            runtime = json.loads(line.split('=', 1)[1])
            version = tuple(map(int, runtime['freecad_version'][:2]))
            if version != (1, 1) or runtime['bits'] != 64:
                raise ValueError('This candidate is validated for 64-bit FreeCAD 1.1.x. '+FREECAD_GUIDANCE)
            return runtime
    raise ValueError('FreeCAD runtime check returned no version information. '+FREECAD_GUIDANCE)


def find_freecad(preferred=''):
    candidates = [Path(preferred)] if preferred else list(freecad_candidates())
    errors = []
    for python in candidates:
        try:
            if not python.is_file():raise ValueError('Configured FreeCAD Python was not found')
            return str(python.resolve()), probe_freecad(python), ''
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            errors.append(str(error))
    return '', None, ('\n'.join(errors) + '\n' if errors else '') + FREECAD_GUIDANCE


def find_poppler(preferred=''):
    if preferred:
        return str(Path(preferred).resolve()) if Path(preferred).is_file() else ''
    bundled = PROJECT_ROOT / 'vendor' / 'poppler' / 'Library' / 'bin' / 'pdftoppm.exe'
    if bundled.is_file():return str(bundled)
    candidate = os.environ.get('FASTENER_POPPLER') or shutil.which('pdftoppm.exe') or shutil.which('pdftoppm')
    return str(Path(candidate).resolve()) if candidate and Path(candidate).is_file() else ''


def diagnose():
    from fastener_paths import FROZEN, INSTALLED
    python, native, error = find_freecad()
    return {'application': 'NutCase', 'version': VERSION, 'frozen': FROZEN, 'installed_layout': INSTALLED,
            'executable': sys.executable, 'application_root': str(PROJECT_ROOT),
            'data_root': str(DATA_ROOT), 'drawings': str(DRAWINGS_ROOT), 'settings': str(SETTINGS_ROOT),
            'cache': str(CACHE_ROOT), 'freecad_python': python, 'native': native,
            'freecad_error': error, 'poppler': find_poppler()}
