"""Retrieve pinned audit materials, checking the reviewed content hash."""
import argparse
import concurrent.futures
import json
from pathlib import Path
from research import fetch, digest
from verify import confined


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,default=Path(__file__).with_name('source-manifest.json'))
    parser.add_argument('--materials',type=Path,required=True)
    args=parser.parse_args()
    def work(record):
        path=confined(args.materials,record['path'])
        url=record['upstream']
        if not path.exists() and not url.startswith(('https://','http://')):
            raise ValueError('Missing exact retrieval URL: '+record['path'])
        fetch(url,path)
        if digest(path)!=record['sha256']:raise ValueError('Reviewed material checksum differs: '+record['path'])
        return record['path']
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for name in pool.map(work,json.loads(args.manifest.read_text(encoding='utf-8'))['materials']):
            print('Checked '+name,flush=True)


if __name__=='__main__':main()
