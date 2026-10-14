"""Acquire primary evidence. Downloads are evidence, never automatic approval."""
import concurrent.futures
import hashlib
import json
import re
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/licensing-materials'


def fetch(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return destination
    request = urllib.request.Request(url, headers={'User-Agent': 'NutCase-licensing-audit/0.6.0'})
    partial = destination.with_name(destination.name+'.partial')
    with urllib.request.urlopen(request, timeout=90) as response, partial.open('wb') as output:
        shutil.copyfileobj(response, output, length=1024*1024)
    partial.replace(destination)
    return destination


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    jobs = {}
    qt = 'https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/'
    for name in ('qtbase', 'qtsvg', 'qtimageformats', 'qttranslations'):
        filename = f'{name}-everywhere-src-6.12.0.tar.xz'
        jobs[filename] = qt + filename
    jobs['pyside-setup-everywhere-src-6.12.0.tar.xz'] = ('https://download.qt.io/official_releases/'
        'QtForPython/pyside6/PySide6-6.12.0-src/pyside-setup-everywhere-src-6.12.0.tar.xz')
    jobs['Python-3.13.16.tar.xz'] = 'https://www.python.org/ftp/python/3.13.16/Python-3.13.16.tar.xz'
    jobs['poppler-26.09.0.tar.xz'] = 'https://poppler.freedesktop.org/poppler-26.09.0.tar.xz'
    jobs['inno-is-7_1_0.tar.gz'] = 'https://api.github.com/repos/jrsoftware/issrc/tarball/is-7_1_0'
    jobs['poppler-windows-v26.09.0-0.tar.gz'] = ('https://api.github.com/repos/'
        'oschwartz10612/poppler-windows/tarball/v26.09.0-0')
    for name, version in (('pypdf','6.10.0'),('pypdfium2','5.14.0'),('Pillow','12.3.0'),
                          ('pyinstaller','6.22.3')):
        data = json.loads(fetch(f'https://pypi.org/pypi/{name}/{version}/json',
            OUT/'research'/f'{name}-{version}-pypi.json').read_text())
        for item in data['urls']:
            if item['packagetype'] == 'sdist':
                jobs[item['filename']] = item['url']
    jobs['poppler-26.09.0-h924501e_0.conda'] = ('https://conda.anaconda.org/conda-forge/'
        'win-64/poppler-26.09.0-h924501e_0.conda')
    records = []
    def download(item):
        filename, url = item
        try:
            path = fetch(url, OUT/'sources'/filename)
            return {'file':filename,'url':url,'sha256':digest(path),'size':path.stat().st_size,
                    'status':'ACQUIRED_NOT_YET_REVIEWED'}
        except Exception as error:
            return {'file':filename,'url':url,'status':'BLOCKED','error':str(error)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for record in pool.map(download, jobs.items()):
            records.append(record)
            print(record['file'], record['status'], record.get('error',''), flush=True)
    (OUT/'research/downloads.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    main()
