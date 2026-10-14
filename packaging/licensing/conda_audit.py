"""Match shipped Poppler closure by content to conda-forge packages."""
import concurrent.futures
import hashlib
import json
import re
from research import OUT, fetch, digest
from inspect_archives import conda_members


def main():
    base = OUT/'extracted-evidence/poppler-26.09.0-h924501e_0.conda/info'
    recipe = (base/'recipe/meta.yaml').read_text()
    pins = {m[0]:(m[1],m[2]) for m in re.findall(r'^    - ([\w-]+) ([\w.]+) ([\w.]+)$', recipe, re.M)}
    names = ['libdeflate','libfreetype6','icu','libjpeg-turbo','lcms2','lerc','openssl','libcurl',
             'liblzma','libpng','libssh2','openjpeg','libpsl','libtiff','libzlib','zstd','ucrt','vc14_runtime']
    def download(name):
        data = json.loads(fetch('https://api.anaconda.org/package/conda-forge/'+name,
            OUT/'research'/f'conda-{name}.json').read_text())
        version, build = pins[name]
        options = [f for f in data['files'] if f['basename'].startswith('win-64/') and
            f['version']==version and f.get('attrs',{}).get('build')==build]
        if not options:
            return {'name':name,'status':'BLOCKED','error':'Pinned package not found','version':version,'build':build}
        item = options[0]
        filename = item['basename'].split('/')[-1]
        url = 'https://conda.anaconda.org/conda-forge/'+item['basename']
        path = fetch(url, OUT/'sources'/filename)
        if digest(path) != item['sha256']:
            raise ValueError('Conda package checksum mismatch: '+filename)
        members = conda_members(path)
        target = OUT/'extracted-evidence'/filename
        for relative, content in members.items():
            destination = target/relative
            if not destination.resolve().is_relative_to(target.resolve()):
                raise ValueError('Unsafe conda member')
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(content)
        index=json.loads(members['info/index.json'])
        about=json.loads(members['info/about.json'])
        return {'name':name,'version':version,'build':build,'file':filename,'url':url,
                'sha256':digest(path),'license':index['license'],'home':about.get('home'),
                'feedstock':about.get('extra',{}),'status':'ACQUIRED_NOT_YET_REVIEWED'}
    records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for record in pool.map(download,names):
            records.append(record);print(record['name'],record['status'],flush=True)
    # poppler-data is an independently licensed data package; locate by content.
    name='poppler-data'
    data=json.loads(fetch('https://api.anaconda.org/package/conda-forge/'+name,
        OUT/'research'/f'conda-{name}.json').read_text())
    options=[f for f in data['files'] if f['basename'].startswith('noarch/') and f['version']=='0.4.12']
    for item in options:
        filename=item['basename'].split('/')[-1]
        path=fetch('https://conda.anaconda.org/conda-forge/'+item['basename'],OUT/'sources'/filename)
        if path.suffix=='.conda':
            members=conda_members(path)
        else:
            import tarfile
            with tarfile.open(path) as archive:
                members={m.name:archive.extractfile(m).read() for m in archive if m.isfile() and m.name.startswith('info/')}
        target=OUT/'extracted-evidence'/filename
        for relative,content in members.items():
            destination=target/relative
            if not destination.resolve().is_relative_to(target.resolve()):raise ValueError('Unsafe member')
            destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(content)
        records.append({'name':name,'file':filename,'version':'0.4.12','url':'https://conda.anaconda.org/conda-forge/'+item['basename'],
                        'sha256':digest(path),'license':json.loads(members['info/index.json'])['license']})
    records.append({'name':'poppler','version':'26.09.0','build':'h924501e_0','file':'poppler-26.09.0-h924501e_0.conda',
                    'sha256':digest(OUT/'sources/poppler-26.09.0-h924501e_0.conda'),'license':'GPL-2.0-or-later'})
    original=OUT/('original-payload' if (OUT/'original-payload/NutCase.exe').exists() else 'original-installed')
    shipped=original/'vendor/poppler'
    matches={}
    for record in records:
        directory=OUT/'extracted-evidence'/record['file']/'info'
        paths=json.loads((directory/'paths.json').read_text())['paths']
        by_hash={p.get('sha256'):p['_path'] for p in paths if p.get('sha256')}
        for path in shipped.rglob('*'):
            if path.is_file() and digest(path) in by_hash:
                matches[path.relative_to(shipped).as_posix()]={**record,'package_member':by_hash[digest(path)]}
    (OUT/'research/conda-packages.json').write_text(json.dumps(records,indent=2)+'\n')
    (OUT/'research/conda-file-matches.json').write_text(json.dumps(matches,indent=2)+'\n')
    unmatched=[p.relative_to(shipped).as_posix() for p in shipped.rglob('*') if p.is_file() and p.relative_to(shipped).as_posix() not in matches]
    (OUT/'research/conda-unmatched.json').write_text(json.dumps(unmatched,indent=2)+'\n')
    print('Matched',len(matches),'unmatched',len(unmatched),unmatched[:20])


if __name__=='__main__':main()
