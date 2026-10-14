"""Controlled compatible PE-header change for an isolated installed-library probe.

This changes no executable code. It exercises modification/load mechanics and is
not a test of an independently rebuilt Qt library or an LGPL legal determination.
"""
import argparse
import json
import struct
from pathlib import Path
from research import ROOT,digest
from verify import confined

LIBRARIES=('_internal/PySide6/Qt6Core.dll','_internal/PySide6/Qt6Pdf.dll',
           '_internal/PySide6/QtCore.pyd','_internal/shiboken6/Shiboken.pyd')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--restore',action='store_true')
    args=parser.parse_args()
    installation=args.installed.resolve();evidence=args.evidence.resolve()
    if not installation.is_relative_to(ROOT/'artifacts') or not evidence.is_relative_to(ROOT/'artifacts'):
        raise ValueError('Probe must be confined to an isolated artifacts installation/evidence directory')
    report=evidence/'library-replacement.json'
    if args.restore:
        records=json.loads(report.read_text(encoding='utf-8'))['libraries']
        for row in records:
            path=confined(installation,row['path'])
            content=confined(evidence,row['backup']).read_bytes()
            path.write_bytes(content)
            if digest(path)!=row['original_sha256']:raise ValueError('Library restore failed')
        print('All four original library bytes restored')
        return
    evidence.mkdir(parents=True,exist_ok=True)
    records=[]
    for relative in LIBRARIES:
        path=confined(installation,relative);content=path.read_bytes()
        offset=struct.unpack_from('<I',content,0x3c)[0]
        if content[:2]!=b'MZ' or content[offset:offset+4]!=b'PE\0\0':raise ValueError('Invalid PE file')
        checksum=offset+24+64
        backup='library-backups/'+relative
        saved=confined(evidence,backup);saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(content)
        changed=bytearray(content);changed[checksum]^=1
        path.write_bytes(changed)
        records.append({'path':relative,'backup':backup,'original_sha256':digest(saved),
                        'modified_sha256':digest(path),'change':'One bit of OptionalHeader.CheckSum; no code change'})
        report.write_text(json.dumps({'scope':'PE header-only compatible modification; not rebuilt source',
            'libraries':records},indent=2)+'\n',encoding='utf-8')
    print('Four native libraries replaced with compatible header-modified copies')


if __name__=='__main__':main()
