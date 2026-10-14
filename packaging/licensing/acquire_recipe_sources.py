"""Retain source and feedstock archives specified by matched binary recipes."""
import concurrent.futures
import json
import sys
import urllib.parse
from research import OUT, fetch, digest
sys.path.insert(0,str(OUT/'audit-tools'))
import yaml


def main():
    jobs={}
    for directory in sorted((OUT/'extracted-evidence').glob('*.conda')):
        index=json.loads((directory/'info/index.json').read_text())
        if index['name'] in ('ucrt','vc14_runtime'):continue
        recipe=directory/'info/recipe/meta.yaml'
        if not recipe.is_file():recipe=directory/'info/recipe/rendered_recipe.yaml'
        if not recipe.is_file():continue
        data=yaml.safe_load(recipe.read_text())
        data=data.get('recipe',data)
        sources=data.get('source',[])
        if isinstance(sources,dict):sources=[sources]
        for source in sources:
            url=source.get('url')
            if isinstance(url,list):url=url[0]
            if not url:continue
            filename=source.get('fn') or urllib.parse.urlsplit(url).path.split('/')[-1]
            if filename in ('archive','download') or not filename:filename=index['name']+'-'+index['version']+'.tar.gz'
            jobs[url]={'file':filename,'url':url,'expected_sha256':source.get('sha256'),
                       'component':index['name'],'recipe':recipe.relative_to(OUT).as_posix()}
        about=json.loads((directory/'info/about.json').read_text()).get('extra',{})
        remote=about.get('remote_url');commit=about.get('sha')
        if remote and commit and remote.startswith('https://github.com/'):
            url='https://api.github.com/repos/'+remote.removeprefix('https://github.com/').removesuffix('.git')+'/tarball/'+commit
            jobs[url]={'file':index['name']+'-feedstock-'+commit+'.tar.gz','url':url,
                       'component':index['name'],'commit':commit}
    def work(record):
        try:
            path=fetch(record['url'],OUT/'sources'/record['file'])
            actual=digest(path)
            if record.get('expected_sha256') and actual!=record['expected_sha256']:
                raise ValueError('Source checksum differs from recipe')
            return {**record,'sha256':actual,'size':path.stat().st_size,'status':'ACQUIRED'}
        except Exception as error:
            return {**record,'status':'BLOCKED','error':str(error)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        records=list(pool.map(work,jobs.values()))
    (OUT/'research/recipe-source-downloads.json').write_text(json.dumps(records,indent=2)+'\n')
    for record in records:print(record['component'],record['file'],record['status'],record.get('error',''))


if __name__=='__main__':main()
