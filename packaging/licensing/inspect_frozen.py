"""Inventory Python code embedded in the actual installed executables."""
import json
import argparse
import marshal
import hashlib
import zipfile
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader
from research import ROOT, OUT, digest


def classify(name):
    if name.startswith(('PIL','pypdfium2','pypdf','PySide6','shiboken6')):
        return name.split('.')[0]
    if name.startswith(('pyi','_pyi')):return 'PyInstaller runtime'
    if name.startswith(('fastener','nutcase','entrypoints','gui_main','worker_main','verify_frozen','runtime_probe')):return 'NutCase'
    return 'CPython standard library'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path)
    parser.add_argument('--include-verifier',action='store_true')
    parser.add_argument('--output',type=Path,default=ROOT/'packaging/licensing/embedded-python.json')
    args=parser.parse_args()
    rows=[]
    original=args.bundle or OUT/('original-payload' if (OUT/'original-payload/NutCase.exe').exists() else 'original-installed')
    for path in sorted(original.glob('NutCase*.exe')):
        if path.name=='NutCaseVerify.exe' and not args.include_verifier:continue
        archive=CArchiveReader(str(path))
        items=[]
        for name,entry in archive.toc.items():
            if name=='PYZ.pyz':
                pyz=archive.open_embedded_archive(name)
                for module in sorted(pyz.toc):
                    code=pyz.extract(module)
                    content=marshal.dumps(code) if code is not None else b''
                    items.append({'path':name+'/'+module,'module':module,'component':classify(module),
                                  'decoded_code_sha256':hashlib.sha256(content).hexdigest()})
            else:
                content=archive.extract(name)
                items.append({'path':name,'module':name,'component':classify(name),
                              'decoded_archive_member_sha256':hashlib.sha256(content).hexdigest()})
        rows.append({'executable':path.name,'sha256':digest(path),'members':items})
    base=original/'_internal/base_library.zip'
    with zipfile.ZipFile(base) as archive:
        rows.append({'archive':'_internal/base_library.zip','sha256':digest(base),
                     'members':[{'path':n,'sha256':hashlib.sha256(archive.read(n)).hexdigest(),
                                 'component':'CPython standard library'} for n in archive.namelist()]})
    lock=(ROOT/'packaging/windows.lock').read_text()
    build_only=[line.split()[0] for line in lock.splitlines() if '==' in line and any(
        line.lower().startswith(n+'==') for n in ('pip','setuptools','wheel','packaging','pefile','altgraph',
                                                'pywin32-ctypes','pyinstaller-hooks-contrib'))]
    value={'schema_version':1,'runtime_archives':rows,'build_only_packages':build_only,
        'not_applicable':['FreeCAD and its bundled dependencies','Nuitka','WiX','Qt WebEngine browser libraries'],
        'note':'PyInstaller compiler is build-only; bootloader, importer and runtime hooks are redistributed. Names/bytecode are decoded from actual installed EXEs, not requirements metadata.'}
    args.output.write_text(json.dumps(value,indent=2)+'\n')
    print('Frozen code inventoried:',[(r.get('executable',r.get('archive')),len(r['members'])) for r in rows])


if __name__=='__main__':main()
