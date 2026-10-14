# Windows x64 directory bundle. Separate EXEs share replaceable native libraries.
from pathlib import Path
import os
import sys
sys.path.insert(0,str(Path(SPECPATH)))
from qt_policy import keep_binary, keep_data
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct

root = Path(SPECPATH).parent
version = (root / 'VERSION').read_text().strip()
numbers = tuple(map(int, version.split('.'))) + (0,)
paths = [str(root / 'src'), str(root / 'src' / 'entrypoints')]
pdf_data = collect_data_files('pypdfium2_raw')

def metadata(filename, description):
    return VSVersionInfo(ffi=FixedFileInfo(filevers=numbers, prodvers=numbers, mask=0x3f, flags=0,
        OS=0x40004, fileType=1, subtype=0, date=(0, 0)), kids=[StringFileInfo([StringTable('040904B0',[
        StringStruct('CompanyName','NutCase Contributors'), StringStruct('FileDescription',description),
        StringStruct('FileVersion',version),StringStruct('ProductName','NutCase'),StringStruct('ProductVersion',version),
        StringStruct('OriginalFilename',filename),StringStruct('LegalCopyright','NutCase contributors; GPL-3.0-or-later')])]),
        VarFileInfo([VarStruct('Translation',[1033,1200])])])

gui = Analysis([str(root/'packaging/gui_main.py')],pathex=paths,datas=pdf_data,
               excludes=['PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets','PySide6.QtQml','PySide6.QtQuick'])
worker = Analysis([str(root/'packaging/worker_main.py')],pathex=paths,datas=pdf_data,
                  excludes=['PySide6','FreeCAD','Part','TechDraw'])
verify = Analysis([str(root/'packaging/verify_frozen.py')],pathex=paths,datas=pdf_data,
                  excludes=['PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets','PySide6.QtQml','PySide6.QtQuick'])

# Filter the hook TOCs before COLLECT; never manually trim a built installation.
allowed=[root/'.venv-build',root/'.build-tools',Path(os.environ['SystemRoot'])]
for analysis in (gui,worker,verify):
    analysis.binaries=[row for row in analysis.binaries if keep_binary(row)]
    analysis.datas=[row for row in analysis.datas if keep_data(row)]
    for destination,source,kind in analysis.binaries:
        if not any(Path(source).resolve().is_relative_to(path.resolve()) for path in allowed):
            raise RuntimeError('Unpinned external binary captured during build: '+source)
for analysis,needed in ((gui,'fastener_gui.window'),(worker,'fastener_gui.outputs')):
    if needed not in {row[0] for row in analysis.pure}:
        raise RuntimeError('Frozen module graph lost required package: '+needed)

gui_exe = EXE(PYZ(gui.pure),gui.scripts,[],exclude_binaries=True,name='NutCase',console=False,
              version=metadata('NutCase.exe','NutCase'),icon='NONE')
worker_exe = EXE(PYZ(worker.pure),worker.scripts,[],exclude_binaries=True,name='NutCaseWorker',console=True,
                 version=metadata('NutCaseWorker.exe','NutCase background worker'),icon='NONE')
verify_exe = EXE(PYZ(verify.pure),verify.scripts,[],exclude_binaries=True,name='NutCaseVerify',console=True,
                 version=metadata('NutCaseVerify.exe','NutCase candidate verification'),icon='NONE')
bundle = COLLECT(gui_exe,worker_exe,verify_exe,gui.binaries,gui.datas,worker.binaries,worker.datas,
                 verify.binaries,verify.datas,name='NutCase')
