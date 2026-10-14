"""Maintainer helper: regenerate a Windows lock only after reviewing wheel changes."""
import hashlib
import zipfile
from email.parser import Parser
from pathlib import Path

root=Path(__file__).resolve().parents[1]
rows=[]
for wheel in (root/'.build-tools/wheels').glob('*.whl'):
    with zipfile.ZipFile(wheel) as archive:
        name=next(item for item in archive.namelist() if item.endswith('.dist-info/METADATA'))
        metadata=Parser().parsestr(archive.read(name).decode())
    rows.append('%s==%s --hash=sha256:%s' % (metadata['Name'],metadata['Version'],hashlib.sha256(wheel.read_bytes()).hexdigest()))
(root/'packaging/windows.lock').write_text('# Windows x64 CPython 3.13.16; exact reviewed wheels.\n'+'\n'.join(sorted(rows,key=str.lower))+'\n')
