"""Fail-closed release checks against a separately reviewed inventory.

This checks evidence integrity and recorded decisions, not legal compliance.
It deliberately cannot create or approve the review it verifies.
"""
import argparse
import hashlib
import json
import tarfile
import zipfile
from pathlib import Path, PurePosixPath


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def confined(root, relative):
    value=PurePosixPath(relative)
    if value.is_absolute() or '..' in value.parts or '\\' in relative or ':' in relative:
        raise ValueError('Unsafe manifest path: '+relative)
    path=(root/relative).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('Manifest path escaped root')
    return path


def archive_members(path):
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            return {n for n in archive.namelist() if not n.endswith('/')}
    with tarfile.open(path) as archive:
        return {m.name for m in archive if m.isfile()}


def verify(bundle, review, materials, installer=None, supplemental_materials=None):
    findings=[]
    def finding(status,code,detail):findings.append({'status':status,'code':code,'detail':detail})
    if review.get('schema_version')!=1:
        finding('BLOCKED','schema','Unsupported reviewed inventory schema')
        return findings
    expected={row['path']:row for row in review['files']}
    # Inventory every file, including data and embedded-Python archives; never
    # allow an unknown resource because it lacks an .exe/.dll extension.
    actual={p.relative_to(bundle).as_posix():p for p in bundle.rglob('*') if p.is_file()}
    generated={r['path']:r for r in review.get('installer_generated_files',[])}
    ignored=set(generated)
    for name,row in generated.items():
        path=confined(bundle,name)
        if path.is_file() and sha256(path)!=row['sha256']:
            finding('BLOCKED','generated_runtime_changed',name)
    for name in sorted(set(actual)-set(expected)-ignored):
        finding('BLOCKED','unexpected_file',name)
    for name,row in expected.items():
        path=confined(bundle,name)
        if not path.is_file():finding('BLOCKED','missing_file',name)
        elif sha256(path)!=row['sha256']:finding('BLOCKED','changed_file',name)
        if not row.get('component') or not row.get('provenance'):
            finding('BLOCKED','unaccounted_origin',name)
    for component in review['components']:
        if component['status'] not in ('VERIFIED','NOT APPLICABLE'):
            finding(component['status'],'component_review',component['id']+': '+component['outstanding'])
        if component['status']=='VERIFIED' and not component.get('evidence'):
            finding('BLOCKED','unsupported_verification',component['id'])
        for required in component.get('notice_files',[]):
            if required not in expected:
                finding('BLOCKED','notice_unreviewed',component['id']+': '+required)
    material_rows=[(record,materials) for record in review.get('materials',[])]
    material_rows.extend((record,supplemental_materials) for record in review.get('supplemental_materials',[]))
    for record,material_root in material_rows:
        if material_root is None:
            finding('BLOCKED','missing_material_root',record['path']);continue
        path=confined(material_root,record['path'])
        if not path.is_file():
            finding('BLOCKED','missing_material',record['path']);continue
        if sha256(path)!=record['sha256']:
            finding('BLOCKED','changed_material',record['path']);continue
        required=record.get('required_members',[])
        if record.get('role')=='corresponding-source':
            # LICENSE/README presence is not source completeness evidence.
            if not record.get('completeness_evidence') or not required or not record.get('source_members'):
                finding('BLOCKED','source_completeness_unreviewed',record['path'])
            try:
                members=archive_members(path)
                missing=set(required+record.get('source_members',[]))-members
                if missing:finding('BLOCKED','source_members_missing',record['path']+': '+', '.join(sorted(missing)))
            except (ValueError,OSError,tarfile.TarError,zipfile.BadZipFile) as error:
                finding('BLOCKED','source_archive_invalid',record['path']+': '+str(error))
    if installer:
        recorded=review.get('installer')
        if not recorded or sha256(installer)!=recorded['sha256']:
            finding('BLOCKED','installer_changed','Installer requires payload inspection and a new review')
    for item in review.get('embedded_python',{}).get('runtime_archives',[]):
        relative=item.get('executable',item.get('archive'))
        if relative and relative in expected and expected[relative]['sha256']!=item['sha256']:
            finding('BLOCKED','embedded_inventory_stale',relative)
    for item in review.get('obligations',[]):
        if item['status'] not in ('VERIFIED','NOT APPLICABLE'):
            finding(item['status'],'obligation',item['id']+': '+item['detail'])
    if not findings:finding('VERIFIED','integrity','All recorded files, sources and decisions verified')
    return findings


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--review',type=Path,required=True)
    parser.add_argument('--materials',type=Path,required=True)
    parser.add_argument('--supplemental-materials',type=Path)
    parser.add_argument('--installer',type=Path)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    review=None
    try:
        review=json.loads(args.review.read_text(encoding='utf-8-sig'))
        findings=verify(args.bundle,review,args.materials,args.installer,args.supplemental_materials)
    except (ValueError,OSError,KeyError,TypeError,AttributeError) as error:
        review=None
        findings=[{'status':'BLOCKED','code':'invalid_review','detail':str(error)}]
    blocked=any(f['status'] not in ('VERIFIED','NOT APPLICABLE') for f in findings)
    integrity_passed=all(f['code'] in ('integrity','component_review','obligation') for f in findings)
    result={'schema_version':1,'release_ready':not blocked,'legal_certification':False,
            'technical_integrity_passed':integrity_passed,
            'review_sha256':sha256(args.review) if args.review.is_file() else None,
            'payload_files_checked':len(review.get('files',[])) if review else 0,
            'source_materials_checked':len(review.get('materials',[]))+len(review.get('supplemental_materials',[])) if review else 0,
            'installer_sha256':sha256(args.installer) if args.installer and args.installer.is_file() else None,
            'findings':findings}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    lines=['# NutCase release compliance evidence check','',f'Release ready: {not blocked}',
           f'File/source/installer integrity checks passed: {integrity_passed}',
           'Technical evidence and recorded decisions only; no legal certification.','']
    lines.extend(f"- **{f['status']}** `{f['code']}`: {f['detail']}" for f in findings)
    args.report.with_suffix('.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'{len(findings)} findings; release_ready={not blocked}; report={args.report}')
    return 2 if blocked else 0


if __name__=='__main__':raise SystemExit(main())
