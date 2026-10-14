"""Create source/review download assets without changing reviewed evidence."""
import argparse
import json
import shutil
import zipfile
from pathlib import Path
from research import ROOT, OUT, digest
from verify import confined, review_path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUT/'release')
    parser.add_argument('--materials',type=Path,default=OUT)
    parser.add_argument('--supplemental-materials',type=Path)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    version=(ROOT/'VERSION').read_text().strip()
    review=ROOT/'packaging/licensing'
    manifest=json.loads((review/'source-manifest.json').read_text(encoding='utf-8'))
    required_evidence=['research/conda-file-matches.json','research/primary-reference-manifest.json']
    required_evidence.extend('extracted-evidence/'+Path(r['path']).name+'/info/index.json'
                            for r in manifest['materials'] if r['path'].endswith('.conda'))
    for relative in required_evidence:
        if not confined(args.materials,relative).is_file():
            raise ValueError('Source/evidence package needs the retained audit metadata: '+relative)
    archive_path=args.output/f'NutCase-{version}-dependency-source-evidence.zip'
    # Upstream compressed source archives are stored verbatim. Conda binary
    # packages and downloaded PDFium DLL archives remain local evidence only:
    # publishing them would introduce additional redistributed binary contents.
    with zipfile.ZipFile(archive_path,'w',zipfile.ZIP_STORED,allowZip64=True) as archive:
        for record in manifest['materials']:
            if not record.get('public_delivery',True):continue
            path=confined(args.materials,record['path'])
            if digest(path)!=record['sha256']:raise ValueError('Source evidence changed: '+str(path))
            archive.write(path,record['path'])
        for record in manifest.get('supplemental_materials',[]):
            if args.supplemental_materials is None:raise ValueError('Supplemental audit evidence root required')
            path=confined(args.supplemental_materials,record['path'])
            if digest(path)!=record['sha256']:raise ValueError('Supplemental evidence changed: '+str(path))
            if record.get('public_delivery',True):archive.write(path,'supplemental-research/'+record['path'])
        for folder in ('research','extracted-evidence'):
            for path in sorted((args.materials/folder).rglob('*')):
                if path.is_file() and path.suffix.lower() not in ('.dll','.pyd','.exe','.pyc'):
                    archive.write(path,path.relative_to(args.materials).as_posix())
        for name in ('source-manifest.json','COMPONENT_MATRIX.md','BUILD_AND_REPLACEMENT.md','UPSTREAM_CLARIFICATIONS.md','OUTSTANDING_OBLIGATIONS.md','obligations.json'):
            archive.write(review/name,'review/'+name)
        archive.write(ROOT/'docs/SOURCE_AVAILABILITY.md','SOURCE_AVAILABILITY.md')
    # Refresh the application source snapshot without touching historical assets.
    with zipfile.ZipFile(args.output/f'NutCase-{version}-source.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for directory in ('src','packaging','scripts','tests','tests_gui','tests_native','tests_pdf',
                          'tests_launchers','tests_support','config','docs','.github'):
            for path in sorted((ROOT/directory).rglob('*')):
                if path.is_file() and '__pycache__' not in path.parts and path.suffix!='.pyc':
                    archive.write(path,path.relative_to(ROOT).as_posix())
        for path in sorted(ROOT.iterdir()):
            if path.is_file() and (path.suffix in ('.md','.txt','.cmd') or path.name in ('VERSION','LICENSE','.gitignore')):
                archive.write(path,path.name)
    for name in ('source-manifest.json','binary-inventory.csv','COMPONENT_MATRIX.md','embedded-python.json'):
        shutil.copy2(review/name,args.output/name)
    inventory=review_path(review)
    if inventory.suffix=='.zip':
        with zipfile.ZipFile(inventory) as archived:
            for name in ('inventory.json','NutCase-0.6.0.spdx.json'):
                (args.output/name).write_bytes(archived.read(name))
    else:
        shutil.copy2(inventory,args.output/'inventory.json')
        shutil.copy2(review/'NutCase-0.6.0.spdx.json',args.output/'NutCase-0.6.0.spdx.json')
    shutil.copy2(review/'OUTSTANDING_OBLIGATIONS.md',args.output/'OUTSTANDING_OBLIGATIONS.md')
    checksums=''.join(digest(p)+'  '+p.name+'\n' for p in sorted(args.output.iterdir()) if p.is_file() and p.name!='SHA256SUMS.txt')
    (args.output/'SHA256SUMS.txt').write_text(checksums,encoding='ascii')
    print('Application source, dependency source/evidence and review assets retained at',args.output)


if __name__=='__main__':main()
