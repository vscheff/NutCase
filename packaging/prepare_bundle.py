"""Stage read-only resources, dependency notices, provenance and release hashes."""
import argparse
import hashlib
import importlib.metadata as metadata
import json
import shutil
import struct
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / '.build-tools'
BUNDLE = ROOT / 'dist' / 'NutCase'
RUNTIME_PACKAGES = ('pypdf','pypdfium2','Pillow','PySide6','PySide6_Essentials','PySide6_Addons',
                    'PySide6_Pdf','shiboken6')


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_toolchain():
    if sys.version_info[:3] != (3,13,16) or struct.calcsize('P') != 8 or sys.platform != 'win32':
        raise RuntimeError('Build with the pinned Windows x64 CPython 3.13.16 toolchain')
    for line in (ROOT/'packaging/windows.lock').read_text().splitlines():
        if '==' not in line or line.startswith('#'):continue
        name,version=line.split()[0].split('==')
        if metadata.version(name) != version:raise RuntimeError('Build dependency version mismatch: '+name)
    compiler = TOOLS/'inno/ISCC.exe'
    if not compiler.is_file():raise RuntimeError('Inno Setup compiler is unavailable')
    for tool in json.loads((ROOT/'packaging/toolchain.json').read_text()).values():
        if sha256(TOOLS/tool['archive']) != tool['sha256']:raise RuntimeError('Build input checksum mismatch')


def copy_poppler():
    # Keep pdftoppm and its actual PE import closure. Do not bundle unrelated tools.
    import pefile
    source = TOOLS / 'poppler/poppler-26.09.0'
    binary_root = source/'Library/bin'
    available = {p.name.lower():p for p in binary_root.iterdir() if p.is_file()}
    selected = {}
    pending = [available['pdftoppm.exe']]
    while pending:
        path = pending.pop()
        if path.name.lower() in selected:continue
        selected[path.name.lower()] = path
        with pefile.PE(str(path), fast_load=True) as executable:
            executable.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT'],
                                                          pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT']])
            for imported in [*getattr(executable,'DIRECTORY_ENTRY_IMPORT',[]),
                             *getattr(executable,'DIRECTORY_ENTRY_DELAY_IMPORT',[])]:
                dependency = available.get(imported.dll.decode('ascii').lower())
                if dependency:pending.append(dependency)
    destination = BUNDLE/'vendor/poppler/Library/bin'
    destination.mkdir(parents=True,exist_ok=True)
    for path in selected.values():shutil.copy2(path,destination/path.name)
    for relative in ('Library/etc','Library/share','share'):
        if (source/relative).is_dir():shutil.copytree(source/relative,BUNDLE/'vendor/poppler'/relative,dirs_exist_ok=True)
    return [{'path':p.relative_to(BUNDLE).as_posix(),'sha256':sha256(p)}
            for p in sorted((BUNDLE/'vendor/poppler').rglob('*')) if p.is_file()]


def collect_notices():
    notices=BUNDLE/'licenses';notices.mkdir(exist_ok=True)
    shutil.copy2(TOOLS/'cpython/tools/LICENSE.txt',notices/'CPython-LICENSE.txt')
    shutil.copy2(TOOLS/'inno/license.txt',notices/'Inno-Setup-LICENSE.txt')
    shutil.copy2(ROOT/'LICENSE',notices/'GPL-3.0.txt')
    shutil.copytree(ROOT/'packaging/licenses',notices/'open-source',dirs_exist_ok=True)
    packages=[]
    for name in (*RUNTIME_PACKAGES,'pyinstaller','pyinstaller-hooks-contrib'):
        distribution=metadata.distribution(name)
        destination=notices/(distribution.metadata['Name']+'-'+distribution.version)
        count=0
        for item in distribution.files or ():
            if any(token in str(item).lower() for token in ('license','copying','notice')):
                source=Path(distribution.locate_file(item))
                if not source.is_file():continue
                target=destination/item;target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source,target);count+=1
        destination.mkdir(exist_ok=True)
        (destination/'METADATA.txt').write_text(distribution.read_text('METADATA') or '',encoding='utf-8')
        packages.append({'name':name,'version':distribution.version,'license':distribution.metadata.get('License-Expression')
                         or distribution.metadata.get('License'),'notice_files':count,
                         'project_urls':distribution.metadata.get_all('Project-URL')})
    return packages


def stage():
    check_toolchain()
    if not (BUNDLE/'NutCase.exe').is_file():raise RuntimeError('Build the frozen application first')
    from qt_policy import verify_payload
    verify_payload(BUNDLE)
    shutil.copytree(ROOT/'src',BUNDLE/'native-src',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copytree(ROOT/'config',BUNDLE/'examples/config',dirs_exist_ok=True)
    shutil.copytree(ROOT/'docs',BUNDLE/'docs',dirs_exist_ok=True,ignore=shutil.ignore_patterns('screenshots'))
    for name in ('VERSION','LICENSE','README.md'):
        shutil.copy2(ROOT/name,BUNDLE/name)
    if (ROOT/'PHASE6_REVIEW.md').exists():shutil.copy2(ROOT/'PHASE6_REVIEW.md',BUNDLE/'PHASE6_REVIEW.md')
    shutil.copy2(ROOT/'THIRD_PARTY_NOTICES.md',BUNDLE/'THIRD_PARTY_NOTICES.md')
    shutil.copytree(ROOT/'packaging/licensing/notices',BUNDLE/'licenses/audit',dirs_exist_ok=True)
    for name in ('BUILD_AND_REPLACEMENT.md','UPSTREAM_CLARIFICATIONS.md','MICROSOFT_RUNTIME_DECISION.md'):
        shutil.copy2(ROOT/'packaging/licensing'/name,BUNDLE/'licenses'/name)
    packages=collect_notices()
    # Collect all notices before creating their index, including a clean build's files.
    # A browser-readable local index works without a Markdown association or GUI redesign.
    import html
    links=['<!doctype html><html lang="en"><meta charset="utf-8"><title>NutCase Licenses</title><body>',
           '<h1>NutCase third-party licenses</h1><p>Dependencies retain their individual terms.</p><ul>']
    for path in sorted((BUNDLE/'licenses').rglob('*')):
        if path.is_file() and path.name!='index.html':
            relative=path.relative_to(BUNDLE/'licenses').as_posix()
            links.append('<li><a href="'+html.escape(relative,quote=True)+'">'+html.escape(relative)+'</a></li>')
    (BUNDLE/'licenses/index.html').write_text(''.join(links)+'</ul></body></html>',encoding='utf-8')
    poppler=copy_poppler()
    provenance={'application':'NutCase','version':(ROOT/'VERSION').read_text().strip(),
                'python':sys.version,'toolchain':json.loads((ROOT/'packaging/toolchain.json').read_text()),
                'packages':packages,'poppler_files':poppler,
                'publication_status':'candidate_only_pending_human_acceptance_and_licensing_review'}
    (BUNDLE/'nutcase-build.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
    files={p.relative_to(BUNDLE).as_posix():sha256(p) for p in sorted(BUNDLE.rglob('*'))
           if p.is_file() and p.name not in ('bundle-manifest.json','NutCaseVerify.exe')}
    (BUNDLE/'bundle-manifest.json').write_text(json.dumps({'schema_version':1,'files':files},indent=2)+'\n',encoding='utf-8')
    print('Staged NutCase resources, %d notices and %d Poppler files' % (sum(p['notice_files'] for p in packages),len(poppler)))


def release_artifacts(artifact_directory=None):
    version=(ROOT/'VERSION').read_text().strip()
    artifacts=artifact_directory or ROOT/'artifacts'
    artifacts.mkdir(parents=True,exist_ok=True)
    source=artifacts/('NutCase-'+version+'-source.zip')
    # Include the working source actually built, not merely the last Git commit.
    with zipfile.ZipFile(source,'w',zipfile.ZIP_DEFLATED) as archive:
        for name in ('src','packaging','scripts','tests','tests_gui','tests_native','tests_pdf','tests_launchers','tests_support','config','docs','.github'):
            for path in sorted((ROOT/name).rglob('*')):
                if path.is_file() and '__pycache__' not in path.parts and path.suffix!='.pyc':
                    archive.write(path,path.relative_to(ROOT).as_posix())
        for name in ('VERSION','LICENSE','README.md','PHASE6_REVIEW.md','requirements-build.txt',
                     'requirements-gui.txt','requirements-pipeline.txt','requirements-pdf.txt','NutCase.cmd','.gitignore'):
            archive.write(ROOT/name,name)
        for name in ('THIRD_PARTY_NOTICES.md','PHASE6_2_LICENSING_REVIEW.md','TEST_COVERAGE_RECOVERY.md','requirements-tests.txt'):
            if (ROOT/name).is_file():archive.write(ROOT/name,name)
    installer=artifacts/('NutCase-'+version+'-windows-x64-setup.exe')
    (artifacts/'SHA256SUMS.txt').write_text(''.join(sha256(path)+'  '+path.name+'\n' for path in (installer,source)),encoding='ascii')
    shutil.copy2(BUNDLE/'nutcase-build.json',artifacts/'nutcase-build.json')
    print('Candidate installer and exact application-source archive checksummed')


def installer_payload(destination,source=BUNDLE):
    """Copy the exact installer scope into a fresh directory; retain unknown files."""
    destination=Path(destination)
    if destination.exists():raise ValueError('Installer staging must use a new directory: '+str(destination))
    def exclude_verifier(directory,names):
        return ['NutCaseVerify.exe'] if Path(directory)==Path(source) and 'NutCaseVerify.exe' in names else []
    shutil.copytree(source,destination,ignore=exclude_verifier)
    print('Installer payload staged at',destination)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-toolchain',action='store_true')
    parser.add_argument('--release-artifacts',action='store_true')
    parser.add_argument('--artifact-directory',type=Path)
    parser.add_argument('--installer-payload',type=Path)
    args=parser.parse_args()
    if args.installer_payload:installer_payload(args.installer_payload)
    elif args.check_toolchain:check_toolchain()
    elif args.release_artifacts:release_artifacts(args.artifact_directory)
    else:stage()
