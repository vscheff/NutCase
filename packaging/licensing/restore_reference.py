"""Restore immutable licensing evidence into disposable workspace directories."""
import argparse
import hashlib
import shutil
import zipfile
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[2]
SCOPES={
    'materials':('materials/',ROOT/'artifacts/licensing-materials',
                 {'sources','research','extracted-evidence','mesa-binary-evidence','audit-tools'}),
    'candidate':('candidate/',ROOT/'artifacts/licensing-candidate',
                 {'candidate-final','research','baseline','release'}),
    'baseline':('materials/original-payload/',ROOT/'artifacts/licensing-materials/original-payload',None),
    'frozen':('frozen-build/',ROOT/'dist/NutCase',None),
}


def restore(archive_path,scope,destination=None):
    prefix,default,allowed=SCOPES[scope]
    destination=Path(destination or default).resolve()
    if not destination.is_relative_to(ROOT.resolve()):
        raise ValueError('Restore into a disposable directory inside the workspace')
    restored=0
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            if member.is_dir() or not member.filename.startswith(prefix):continue
            relative=member.filename[len(prefix):]
            parts=PurePosixPath(relative)
            if parts.is_absolute() or '..' in parts.parts or '\\' in relative or ':' in relative:
                raise ValueError('Unsafe reference path: '+relative)
            if allowed and (not parts.parts or parts.parts[0] not in allowed):continue
            path=(destination/relative).resolve()
            if not path.is_relative_to(destination):raise ValueError('Reference path escaped destination')
            if path.exists():
                with archive.open(member) as original,path.open('rb') as existing:
                    if hashlib.file_digest(original,'sha256').digest()!=hashlib.file_digest(existing,'sha256').digest():
                        raise ValueError('Existing evidence differs; refusing to overwrite: '+str(path))
            else:
                path.parent.mkdir(parents=True,exist_ok=True)
                temporary=path.with_name(path.name+'.restore-pending')
                try:
                    with archive.open(member) as original,temporary.open('xb') as output:
                        shutil.copyfileobj(original,output,1024*1024)
                    temporary.rename(path)
                finally:
                    if temporary.exists():temporary.unlink()
            restored+=1
    if not restored:raise ValueError('Requested reference scope is missing from archive')
    return restored


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,default=ROOT/'artifacts/licensing-history.zip')
    parser.add_argument('--scope',choices=SCOPES,required=True)
    parser.add_argument('--destination',type=Path)
    args=parser.parse_args()
    count=restore(args.archive,args.scope,args.destination)
    print(f'Restored/checked {count} immutable reference files')


if __name__=='__main__':main()
