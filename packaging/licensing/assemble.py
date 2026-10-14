"""Assemble an explicitly incomplete, reviewable redistribution dossier.

Run only during a new audit, never from the release verification workflow.
The historical installer/payload is immutable input. No binary is rebuilt here.
"""
import ast
import csv
import hashlib
import html
import json
import re
import shutil
import tarfile
import zipfile
from collections import defaultdict
from pathlib import Path
from research import ROOT, OUT, digest

REVIEW=ROOT/'packaging/licensing'
QT_PDF_ARCHIVE='6.12.0-0-202609281005qtwebengine-everywhere-src-6.140.0.zip'
ORIGINAL=OUT/('original-payload' if (OUT/'original-payload/NutCase.exe').exists() else 'original-installed')


def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


def archive_index():
    origins=defaultdict(list)
    for path in sorted((ROOT/'.build-tools/wheels').glob('*.whl')):
        with zipfile.ZipFile(path) as archive:
            meta=next(n for n in archive.namelist() if n.endswith('.dist-info/METADATA'))
            value=archive.read(meta).decode()
            name=re.search(r'^Name: (.+)$',value,re.M)[1]
            version=re.search(r'^Version: (.+)$',value,re.M)[1]
            license_match=re.search(r'^License(?:-Expression)?: (.+)$',value,re.M)
            archive_hash=digest(path)
            for member in archive.namelist():
                if member.endswith('/'):continue
                content=archive.read(member)
                origins[hashlib.sha256(content).hexdigest()].append({'archive':path.relative_to(ROOT).as_posix(),
                    'archive_sha256':archive_hash,'member':member,'name':name,'version':version,
                    'declared_license':license_match[1] if license_match else 'NOASSERTION'})
    path=ROOT/'.build-tools/python.3.13.16.nupkg'
    with zipfile.ZipFile(path) as archive:
        archive_hash=digest(path)
        for member in archive.namelist():
            if member.endswith('/'):continue
            origins[hashlib.sha256(archive.read(member)).hexdigest()].append({'archive':path.relative_to(ROOT).as_posix(),
                'archive_sha256':archive_hash,'member':member,'name':'CPython','version':'3.13.16',
                'declared_license':'Python-2.0'})
    path=ROOT/'.build-tools/Release-26.09.0-0.zip'
    with zipfile.ZipFile(path) as archive:
        archive_hash=digest(path)
        for member in archive.namelist():
            if member.endswith('/'):continue
            origins[hashlib.sha256(archive.read(member)).hexdigest()].append({'archive':path.relative_to(ROOT).as_posix(),
                'archive_sha256':archive_hash,'member':member,'name':'poppler-windows','version':'26.09.0-0',
                'declared_license':'NOASSERTION'})
    return origins


def component_for(path,origins,conda,version):
    filename=Path(path).name.lower()
    if filename.startswith(('vcruntime','msvcp','api-ms-win-crt')):return 'microsoft-runtime'
    if filename=='opengl32sw.dll':return 'qt-mesa-rasterizer'
    if path.startswith('vendor/poppler/'):
        record=conda.get(path.removeprefix('vendor/poppler/'))
        if record:return 'conda-'+record['name']
        if '/share/poppler/' in path:return 'conda-poppler-data'
        return 'poppler-unmatched'
    if filename.startswith('unins'):return 'inno-runtime'
    if path in ('NutCase.exe','NutCaseWorker.exe','NutCaseVerify.exe'):return 'nutcase-frozen'
    if path.startswith('_internal/pypdfium2_raw/'):return 'pypdfium2-pdfium'
    if path.startswith('_internal/pypdfium2/'):return 'pypdfium2'
    if path.startswith('_internal/PySide6/'):
        if filename in ('qt6pdf.dll','qt6pdfwidgets.dll','qpdf.dll'):return 'qt-pdf'
        if filename.endswith('.pyd') or filename.startswith('pyside6'):return 'pyside6'
        if filename.endswith('.qm'):return 'qt-translations'
        if filename.endswith('.dll'):return 'qt-libraries-plugins'
    if path.startswith('_internal/shiboken6/'):return 'shiboken6'
    if path.startswith('_internal/PIL/'):return 'pillow'
    if path.startswith('_internal/'):
        if filename=='libffi-8.dll':return 'cpython-libffi'
        if filename in ('libssl-3.dll','libcrypto-3.dll'):return 'cpython-openssl'
        if filename.endswith(('.dll','.pyd','.zip')):return 'cpython'
    if origins:
        first=origins[0]['name'].lower().replace('_','-')
        if first=='pypdf':return 'pypdf'
        if first=='pypdfium2':return 'pypdfium2'
    if path.startswith('licenses/'):return 'notice-resources'
    if path.startswith(('native-src/','docs/','examples/')) or '/' not in path:return 'nutcase-source-resources'
    return 'unresolved-resource'


def file_rows(bundle,origins,conda,versions):
    rows=[]
    conda_hashes={digest(ORIGINAL/'vendor/poppler'/name):record for name,record in conda.items()}
    for path in sorted(bundle.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(bundle).as_posix();hash_value=digest(path)
        provenance=list(origins.get(hash_value,[]))
        match=conda.get(relative.removeprefix('vendor/poppler/')) if relative.startswith('vendor/poppler/') else None
        if match:provenance.append({'distributor':'conda-forge',**match})
        elif hash_value in conda_hashes:provenance.append({'distributor':'conda-forge','content_match_from_other_installed_path':True,**conda_hashes[hash_value]})
        component=component_for(relative,provenance,conda,versions)
        if not provenance:
            if component=='nutcase-frozen':provenance=[{'origin':'NutCase build/NutCase EXE/PYZ TOCs; PyInstaller bootloader with appended application archives'}]
            elif component=='microsoft-runtime':provenance=[{'origin':'Actual installed DLL; inspect build/NutCase/Analysis-*.toc for collection source; redistribution authorization unresolved'}]
            elif component=='inno-runtime':provenance=[{'origin':'Generated by exact Inno Setup 7.1.0 installer during isolated installation'}]
            elif component.startswith('nutcase') or component=='notice-resources':provenance=[{'origin':'NutCase staged source/documentation or preserved license resource'}]
            elif relative=='_internal/base_library.zip':provenance=[{'origin':'PyInstaller-generated CPython 3.13.16 standard-library bytecode ZIP'}]
            else:provenance=[{'origin':'UNRESOLVED: no exact binary/package hash match'}]
        row={'path':relative,'installed_path':'{app}/'+relative,'sha256':hash_value,'size':path.stat().st_size,
             'component':component,'provenance':provenance,'pe':versions.get(relative),
             'license_expression':'NOASSERTION','copyright':'See component notice files and PE copyright metadata',
             'status':'BLOCKED' if component in ('unresolved-resource','poppler-unmatched','qt-mesa-rasterizer') else 'REQUIRES HUMAN/LEGAL REVIEW'}
        rows.append(row)
    return rows


def source_materials():
    references={}
    for name in ('downloads.json','recipe-source-downloads.json','cpython-external-sources.json'):
        path=OUT/'research'/name
        if path.exists():
            for record in json.loads(path.read_text()):
                references[record['file']]=record
    references[QT_PDF_ARCHIVE]={'url':'https://download.qt.io/online/qtsdkrepository/windows_x86/extensions/qtwebengine/6120/61400/src_doc_examples/extensions.qtwebengine.6120.61400.src/'+QT_PDF_ARCHIVE}
    references['pdfium-binaries-build.tar.gz']={'url':'https://api.github.com/repos/bblanchon/pdfium-binaries/tarball/f2e9a1c45bb17b85b540abf1af30146ef65416ac'}
    references['pdfium-win-x64.tgz']={'url':'https://github.com/bblanchon/pdfium-binaries/releases/download/chromium/8076/pdfium-win-x64.tgz'}
    references['poppler-feedstock.tar.gz']={'url':'https://api.github.com/repos/conda-forge/poppler-feedstock/tarball/13d784d77510e73d6066a75a79cd8e6040a6a261'}
    references['poppler-windows-v26.09.0-0.tar.gz']={'url':'https://api.github.com/repos/oschwartz10612/poppler-windows/tarball/v26.09.0-0'}
    for record in json.loads((OUT/'research/conda-packages.json').read_text()):
        if record.get('file'):references[record['file']]={'url':record.get('url','https://conda.anaconda.org/conda-forge/win-64/'+record['file'])}
    for path in (OUT/'sources').glob('*.conda'):
        references.setdefault(path.name,{'url':'https://conda.anaconda.org/conda-forge/win-64/'+path.name})
    references['mesa-11.2.2.tar.xz']={'url':'https://archive.mesa3d.org/older-versions/11.x/11.2.2/mesa-11.2.2.tar.xz'}
    references['llvm-3.6.2.src.tar.xz']={'url':'https://releases.llvm.org/3.6.2/llvm-3.6.2.src.tar.xz'}
    for path in (OUT/'sources').glob('*.7z'):
        references[path.name]={'url':'https://download.qt.io/development_releases/prebuilt/llvmpipe/windows/'+path.name}
    records=[]
    required={
        'poppler-26.09.0.tar.xz':(['poppler-26.09.0/CMakeLists.txt','poppler-26.09.0/COPYING'],['poppler-26.09.0/utils/pdftoppm.cc','poppler-26.09.0/poppler/PDFDoc.cc']),
        QT_PDF_ARCHIVE:(['CMakeLists.txt','src/pdf/CMakeLists.txt','src/3rdparty/chromium/third_party/pdfium/DEPS'],
                        ['src/pdf/qpdfdocument.cpp','src/3rdparty/chromium/third_party/pdfium/fpdfsdk/fpdf_view.cpp']),
        'qtbase-everywhere-src-6.12.0.tar.xz':(['qtbase-everywhere-src-6.12.0/CMakeLists.txt'],['qtbase-everywhere-src-6.12.0/src/corelib/kernel/qobject.cpp']),
        'pyside-setup-everywhere-src-6.12.0.tar.xz':(['pyside-setup-everywhere-src-6.12.0/setup.py'],['pyside-setup-everywhere-src-6.12.0/sources/shiboken6/libshiboken/basewrapper.cpp']),
        'poppler-data-0.4.12.tar.gz':(['poppler-data-0.4.12/COPYING','poppler-data-0.4.12/Makefile'],['poppler-data-0.4.12/cidToUnicode/Adobe-Japan1']),
    }
    for path in sorted((OUT/'sources').iterdir()):
        if not path.is_file() or path.suffix=='.partial':continue
        record={'path':'sources/'+path.name,'sha256':digest(path),'size':path.stat().st_size,
                'role':'source-and-build-evidence','upstream':references.get(path.name,{}).get('url','See matching conda metadata / evidence manifest'),
                'status':'ACQUIRED; archive availability is not a compliance decision'}
        if path.suffix in ('.conda','.7z') or path.name=='pdfium-win-x64.tgz':
            record['role']='binary-provenance-evidence-local-only'
            record['public_delivery']=False
        else:record['public_delivery']=True
        if path.name in required:
            members=zipfile.ZipFile(path).namelist() if zipfile.is_zipfile(path) else tarfile.open(path).getnames()
            required_members,source_members=required[path.name]
            if not set(required_members+source_members)<=set(members):raise ValueError('Missing known source content in '+path.name)
            record.update(role='corresponding-source',required_members=required_members,source_members=source_members,
                completeness_evidence='Preserved entire versioned upstream archive, with source/build/interface entry points. Binary configuration/source-delivery obligations are separately recorded and not approved here.')
        records.append(record)
    return records


def notices():
    destination=REVIEW/'notices';destination.mkdir(exist_ok=True)
    records=[]
    # Keep verbatim notices and attribution metadata; shorten filenames so Windows
    # installation does not inherit Chromium's exceptionally long source paths.
    for path in sorted((OUT/'extracted-evidence').rglob('*')):
        if not path.is_file():continue
        name=path.name.lower()
        if not (any(t in name for t in ('license','copying','notice','qt_attribution','reuse.toml'))):continue
        if path.suffix.lower() in ('.cc','.cpp','.h','.c','.py','.gn','.cmake','.patch','.sh','.bat','.svg','.html'):continue
        relative=path.relative_to(OUT/'extracted-evidence').as_posix()
        identifier=hashlib.sha256(relative.encode()).hexdigest()[:20]
        target=destination/(identifier+'-'+path.name[:60].rstrip(' .'))
        shutil.copy2(path,target)
        records.append({'source_evidence':relative,'installed_notice':'licenses/audit/'+target.name,
                        'sha256':digest(target)})
    write_json(destination/'NOTICE_INDEX.json',records)
    return records


def components(rows,notice_records,materials):
    definitions={
      'nutcase-frozen':('NutCase/PyInstaller embedded runtime','0.6.0 / 6.22.3','GPL-3.0-or-later','VERIFIED',''),
      'nutcase-source-resources':('NutCase source and documentation','0.6.0','GPL-3.0-or-later','REQUIRES HUMAN/LEGAL REVIEW','Owner must confirm code/documentation/asset ownership. Model assets are excluded.'),
      'cpython':('CPython / Python standard library and native extensions','3.13.16','Python-2.0','VERIFIED',''),
      'cpython-openssl':('PSF-distributed OpenSSL','3.5.9','Apache-2.0','VERIFIED',''),
      'cpython-libffi':('PSF-distributed libffi','3.4.4','MIT','VERIFIED',''),
      'pyside6':('PySide6 bindings','6.12.0; Pdf wrappers 6.12.0.140','LGPL-3.0-only','BLOCKED','Need exact community wheel build configurations/patch confirmation, binary SBOM and source correlation; commercial-reference-file discrepancy requires upstream clarification.'),
      'shiboken6':('shiboken6 bindings','6.12.0','LGPL-3.0-only','BLOCKED','Matching source acquired; exact wheel build configuration/source correspondence remains unresolved with Qt.'),
      'qt-libraries-plugins':('Qt libraries and plugins','6.12.0','LGPL-3.0-only','BLOCKED','Module source/third-party notices retained; exact wheel configuration and compiled third-party component selection need upstream build evidence.'),
      'qt-pdf':('Qt PDF / PdfWidgets with embedded PDFium','6.140.0 (wheel 6.12.0.140)','LGPL-3.0-only','BLOCKED','Full Qt 6.140 source acquired; establish actual wheel build/patch correlation and compiled PDFium third-party notice set.'),
      'qt-translations':('Qt translation catalogs','6.12.0 / Pdf 6.140.0','NOASSERTION','BLOCKED','Trace every wheel-shipped catalog to applicable module source/license; acquired qttranslations may not cover all module catalogs.'),
      'qt-mesa-rasterizer':('Qt-supplied OpenGL software renderer','Banners: Mesa 11.2.2 / LLVM 3.6.2; exact build unresolved','NOASSERTION','BLOCKED','Wheel hash provenance and version banners known; three Qt Mesa archives do not match. Nominal Mesa/LLVM sources acquired, but exact patches/configuration, complete compiled notices and build correspondence remain unavailable.'),
      'pypdf':('pypdf','6.10.0','BSD-3-Clause','VERIFIED',''),
      'pypdfium2':('pypdfium2 binding','5.14.0','Apache-2.0 OR BSD-3-Clause','VERIFIED',''),
      'pypdfium2-pdfium':('pypdfium2 PDFium build','156.0.8076.0','BSD-3-Clause','REQUIRES HUMAN/LEGAL REVIEW','Exact pdfium.dll hash matches pdfium-binaries chromium/8076; notices and pinned build repo retained. Wheel records no source commit; confirm compiled dependency provenance/notice coverage.'),
      'pillow':('Pillow image extensions','12.3.0','MIT-CMU','REQUIRES HUMAN/LEGAL REVIEW','Preserved complete wheel LICENSE and SBOM; source SBOM lists optional dependencies. Confirm compiled codec selection/versions for shipped extensions, including libavif/dav1d.'),
      'microsoft-runtime':('Microsoft C++ runtime / Windows UCRT API-set DLLs','See each PE version','NOASSERTION','REQUIRES HUMAN/LEGAL REVIEW','Source-package origin and SDK/runtime terms preserved. Owner must establish applicable redistribution authorization; SDK open-source restrictions need review. Supported alternative: official x64 VC runtime prerequisite plus Windows 10/11 UCRT; rebuild/retest if removing app-local DLLs.'),
      'inno-runtime':('Inno Setup installer/uninstaller runtime','7.1.0','LicenseRef-Inno-Setup','VERIFIED',''),
      'notice-resources':('Preserved third-party licensing evidence','audit 2026-10-13','NOASSERTION','VERIFIED',''),
      'unresolved-resource':('Unresolved licensed resource','UNKNOWN','NOASSERTION','BLOCKED','No reviewed component mapping'),
      'poppler-unmatched':('Unmatched Poppler-distribution resource','UNKNOWN','NOASSERTION','BLOCKED','Must trace exact content to upstream package/source'),
    }
    conda=json.loads((OUT/'research/conda-file-matches.json').read_text())
    for record in conda.values():
        definitions['conda-'+record['name']]=(record['name'],record['version']+' '+record.get('build',''),
            'FTL' if record['name']=='libfreetype6' else record['license'],'VERIFIED','')
    result=[]
    for identifier in sorted({r['component'] for r in rows}|{'pypdf','pypdfium2','inno-runtime'}):
        name,version,license_expression,status,outstanding=definitions[identifier]
        matching=[r for r in rows if r['component']==identifier]
        notices_for_component=[]
        if identifier.startswith('conda-'):
            files={r['file'] for r in conda.values() if 'conda-'+r['name']==identifier}
            notices_for_component=[n['installed_notice'] for n in notice_records if any(n['source_evidence'].startswith(f+'/') for f in files)]
        else:
            hints={'qt-pdf':['6.140.0'],'qt-libraries-plugins':['qtbase-','qtsvg-','qtimageformats-'],
                   'pyside6':['pyside-setup-'],'shiboken6':['pyside-setup-'],'cpython':['Python-3.13.16'],
                   'cpython-libffi':['cpython-source-deps-libffi'],'cpython-openssl':['cpython-source-deps-openssl'],
                   'inno-runtime':['inno-is-7_1_0']}.get(identifier,[])
            if identifier=='microsoft-runtime':hints=['ucrt-','vc14_runtime-']
            if identifier=='pypdfium2-pdfium':hints=['pdfium-win-x64.tgz']
            notices_for_component=[n['installed_notice'] for n in notice_records if any(h in n['source_evidence'] for h in hints)]
        if identifier=='pypdf':notices_for_component=['licenses/pypdf-6.10.0/pypdf-6.10.0.dist-info/licenses/LICENSE']
        if identifier=='pypdfium2':notices_for_component=['licenses/pypdfium2-5.14.0/pypdfium2-5.14.0.dist-info/licenses/LICENSES/BSD-3-Clause.txt']
        if identifier=='pillow':notices_for_component=['licenses/pillow-12.3.0/pillow-12.3.0.dist-info/licenses/LICENSE']
        if identifier=='cpython':notices_for_component.append('licenses/CPython-LICENSE.txt')
        if identifier=='inno-runtime':notices_for_component.append('licenses/Inno-Setup-LICENSE.txt')
        if identifier=='nutcase-frozen':notices_for_component=['LICENSE','licenses/pyinstaller-6.22.3/pyinstaller-6.22.3.dist-info/licenses/COPYING.txt']
        result.append({'id':identifier,'name':name,'version':version,'license_expression':license_expression,
            'status':status,'outstanding':outstanding,'file_count':len(matching),'notice_files':notices_for_component,
            'evidence':['Full installed file hashes and package-member hash matches in inventory.json',
                        'Original installer, upstream source checksums where available, actual wheel notices and immutable conda recipes in artifacts/licensing-materials'],
            'upstream_and_distributor':'Per-file provenance and source-manifest.json; original distributor metadata retained',
            'copyright_and_notice_obligations':'Retain verbatim component notices, conditions and disclaimers. See notice_files / NOTICE_INDEX.json.',
            'corresponding_source':'source-manifest.json; conda recipes and source archives retained',
            'build_and_installation_information':'BUILD_AND_REPLACEMENT.md plus immutable archived upstream/conda recipes; unverified configurations remain blockers'})
        source_hints={
            'pyside6':['pyside-setup-'],'shiboken6':['pyside-setup-'],
            'qt-libraries-plugins':['qtbase-','qtsvg-','qtimageformats-'],
            'qt-pdf':[QT_PDF_ARCHIVE],'qt-translations':['qttranslations-'],
            'qt-mesa-rasterizer':['mesa-11.2.2','llvm-3.6.2'],
            'cpython':['Python-3.13.16','cpython-source-deps-'],
            'cpython-libffi':['cpython-source-deps-libffi-'],
            'cpython-openssl':['cpython-source-deps-openssl-'],
            'pypdf':['pypdf-6.10.0'],'pypdfium2':['pypdfium2-5.14.0'],
            'pypdfium2-pdfium':['pdfium-binaries-build','pdfium-win-x64'],
            'pillow':['pillow-12.3.0'],'inno-runtime':['inno-is-7_1_0']}.get(identifier,[])
        if identifier.startswith('conda-'):
            key=identifier.removeprefix('conda-')
            recipe_sources=json.loads((OUT/'research/recipe-source-downloads.json').read_text())
            source_hints.extend(r['file'] for r in recipe_sources if r['component']==key and r['status']=='ACQUIRED')
            source_hints.extend(r['file'] for r in conda.values() if r['name']==key)
        result[-1]['source_archives']=[{'path':m['path'],'sha256':m['sha256'],'url':m['upstream'],
                                      'role':m['role']} for m in materials if any(h in m['path'] for h in source_hints)]
        for row in matching:
            row.update(license_expression=license_expression,status=status,component_name=name,component_version=version,
                       corresponding_source='source-manifest.json',build_information='BUILD_AND_REPLACEMENT.md',outstanding=outstanding)
    return result


def sbom(review,path):
    packages=[];files=[];relationships=[]
    for i,c in enumerate(review['components']):
        identifier='SPDXRef-Package-'+str(i)
        packages.append({'SPDXID':identifier,'name':c['name'],'versionInfo':c['version'],
            'downloadLocation':'NOASSERTION','filesAnalyzed':False,'licenseDeclared':'NOASSERTION',
            'licenseConcluded':'NOASSERTION','copyrightText':'NOASSERTION',
            'comment':'Selected license option and review evidence: '+c['license_expression']+'; '+c['status']})
        relationships.append({'spdxElementId':'SPDXRef-DOCUMENT','relationshipType':'DESCRIBES','relatedSpdxElement':identifier})
        for row in review['files']:
            if row['component']!=c['id']:continue
            file_id='SPDXRef-File-'+hashlib.sha256(row['path'].encode()).hexdigest()[:24]
            files.append({'SPDXID':file_id,'fileName':'./'+row['path'],'checksums':[{'algorithm':'SHA256','checksumValue':row['sha256']}],
                'licenseConcluded':'NOASSERTION','licenseInfoInFiles':['NOASSERTION'],'copyrightText':'NOASSERTION',
                'comment':'See inventory.json for exact binary origin, selected licensing option, source and unresolved obligations'})
            relationships.append({'spdxElementId':identifier,'relationshipType':'CONTAINS','relatedSpdxElement':file_id})
    write_json(path,{'spdxVersion':'SPDX-2.3','dataLicense':'CC0-1.0','SPDXID':'SPDXRef-DOCUMENT','name':'NutCase 0.6.0 installed distribution inventory',
        'documentNamespace':'https://github.com/vscheff/NutCase/spdx/0.6.0/'+review['installer']['sha256'],
        'creationInfo':{'created':'2026-10-13T00:00:00Z','creators':['Tool: NutCase licensing audit assembler']},
        'packages':packages,'files':files,'relationships':relationships})


def main():
    original=ORIGINAL
    candidate=OUT/'candidate-bundle'
    candidate.mkdir(exist_ok=True)
    shutil.copytree(original,candidate,dirs_exist_ok=True,ignore=shutil.ignore_patterns('unins000.*'))
    origins=archive_index()
    conda=json.loads((OUT/'research/conda-file-matches.json').read_text())
    versions={r['path'].replace('\\','/'):r for r in json.loads((OUT/'research/pe-versions.json').read_text(encoding='utf-8-sig'))}
    notice_records=notices()
    shutil.copytree(REVIEW/'notices',candidate/'licenses/audit',dirs_exist_ok=True)
    for filename in ('THIRD_PARTY_NOTICES.md',):shutil.copy2(ROOT/filename,candidate/filename)
    for filename in ('SOURCE_AVAILABILITY.md','LICENSING_AUDIT.md','RELEASE_READINESS.md'):
        shutil.copy2(ROOT/'docs'/filename,candidate/'docs'/filename)
    for filename in ('BUILD_AND_REPLACEMENT.md','UPSTREAM_CLARIFICATIONS.md'):
        shutil.copy2(REVIEW/filename,candidate/'licenses'/filename)
    links=['<h1>NutCase 0.6.0 third-party licenses</h1>',
           '<p>Dependencies retain their individual licenses. This candidate has unresolved release obligations.</p>',
           '<p><a href="../THIRD_PARTY_NOTICES.md">Third-party notices</a> | <a href="../docs/SOURCE_AVAILABILITY.md">Source availability</a> | <a href="BUILD_AND_REPLACEMENT.md">Library replacement instructions</a></p>','<ul>']
    for path in sorted((candidate/'licenses').rglob('*')):
        if path.is_file() and path.name!='index.html':
            relative=path.relative_to(candidate/'licenses').as_posix()
            links.append('<li><a href="'+html.escape(relative,quote=True)+'">'+html.escape(relative)+'</a></li>')
    links.append('</ul>')
    (candidate/'licenses/index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>NutCase Licenses</title><body>'+''.join(links)+'</body></html>',encoding='utf-8')
    materials=source_materials()
    files={p.relative_to(candidate).as_posix():digest(p) for p in sorted(candidate.rglob('*'))
           if p.is_file() and p.name!='bundle-manifest.json'}
    write_json(candidate/'bundle-manifest.json',{'schema_version':1,'files':files})
    rows=file_rows(candidate,origins,conda,versions)
    component_records=components(rows,notice_records,materials)
    obligations=json.loads((REVIEW/'obligations.json').read_text())
    installer=OUT/'original/NutCase-0.6.0-windows-x64-setup.exe'
    review={'schema_version':1,'application':'NutCase','version':'0.6.0','scope':'Original installer inspected through isolated installation; documentation-only remediation candidate preserves all application/runtime PE bytes',
            'installer':{'path':installer.relative_to(ROOT).as_posix(),'sha256':digest(installer),'version':'0.6.0','compiler':'Inno Setup 7.1.0'},
            'files':rows,'components':component_records,'materials':materials,'obligations':obligations,'installer_generated_files':[]}
    review['embedded_python']=json.loads((REVIEW/'embedded-python.json').read_text())
    review['source_delivery']='See docs/SOURCE_AVAILABILITY.md; local-only binary packages are excluded from public dependency source ZIP.'
    write_json(REVIEW/'inventory.json',review)
    write_json(REVIEW/'source-manifest.json',{'materials':materials})
    sbom(review,REVIEW/'NutCase-0.6.0.spdx.json')
    original_rows=file_rows(original,origins,conda,versions)
    components(original_rows,notice_records,materials)
    original_review={**review,'files':original_rows,'scope':'Original installed payload, including generated Inno uninstaller'}
    write_json(OUT/'original/inventory.json',original_review)
    sbom(original_review,OUT/'original/NutCase-0.6.0.spdx.json')
    (REVIEW/'COMPONENT_MATRIX.md').write_text('# NutCase 0.6.0 component evidence matrix\n\nExact paths/hashes are in inventory.json; source hashes and upstream locations are in source-manifest.json. VERIFIED means the specific technical evidence described here, not universal legal compliance. Global human decisions remain release gates.\n\n| Component | Version | Selected license / evidence | Files | Status | Remaining work |\n|---|---|---|---:|---|---|\n'+''.join(
        f"| {c['name']} | {c['version']} | {c['license_expression']} | {c['file_count']} | {c['status']} | {c['outstanding'] or 'Technical provenance/source/notice evidence retained; global ownership/source-delivery review still applies.'} |\n" for c in component_records),encoding='utf-8')
    with (REVIEW/'binary-inventory.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=['path','sha256','component_name','component_version','license_expression','status','outstanding'])
        writer.writeheader();writer.writerows({k:r[k] for k in writer.fieldnames} for r in rows if Path(r['path']).suffix.lower() in ('.exe','.dll','.pyd'))
    write_json(OUT/'research/binary-preservation.json',{'all_runtime_pe_bytes_unchanged':all(digest(candidate/r['path'])==r['sha256'] for r in original_rows if Path(r['path']).suffix.lower() in ('.exe','.dll','.pyd') and not r['path'].startswith('unins'))})
    print('Files',len(rows),'components',len(component_records),'notice evidence files',len(notice_records),'source materials',len(materials))


if __name__=='__main__':main()
