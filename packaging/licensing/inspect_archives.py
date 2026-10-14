"""Inspect acquired archives without executing their contents."""
import io
import hashlib
import json
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'artifacts/licensing-materials'
sys.path.insert(0, str(OUT/'audit-tools'))


def conda_members(path, section='info'):
    import zstandard
    with zipfile.ZipFile(path) as archive:
        name = next(n for n in archive.namelist() if n.startswith(section+'-') and n.endswith('.tar.zst'))
        with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(archive.read(name))) as stream:
            data = stream.read()
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        return {m.name: archive.extractfile(m).read() for m in archive if m.isfile()}


def main():
    for path in sorted((OUT/'sources').iterdir()):
        if path.suffix in ('.partial','.7z'):continue
        if (OUT/'research'/(path.name+'-extracted-paths.json')).exists():continue
        print(path.name, path.stat().st_size)
        if path.suffix == '.conda':
            members = conda_members(path)
        elif zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                members={n:archive.read(n) for n in archive.namelist() if not n.endswith('/') and selected(n)}
        else:
            with tarfile.open(path) as archive:
                members = {m.name: archive.extractfile(m).read() for m in archive if m.isfile() and selected(m.name)}
        target = OUT/'extracted-evidence'/path.name
        mapping={}
        for name, data in members.items():
            destination = target/name
            if not destination.resolve().is_relative_to(target.resolve()):
                raise ValueError('Unsafe archive member: '+name)
            if len(str(destination.resolve()))>225:
                destination=target/'_long'/(hashlib.sha256(name.encode()).hexdigest()[:20]+'-'+Path(name).name[:45])
            mapping[name]=destination.relative_to(target).as_posix()
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        (OUT/'research'/(path.name+'-members.json')).write_text(json.dumps(list(members),indent=2))
        (OUT/'research'/(path.name+'-extracted-paths.json')).write_text(json.dumps(mapping,indent=2))
    print('Evidence extracted; no source scripts executed')


def selected(name):
    return (any(t in name.lower() for t in ('license','copying','notice','sbom','build_info','coin/','qt_attribution'))
            or name.endswith(('README.md','DEPS','BUILD.gn','.gitmodules','README','CMakeLists.txt',
                              'README.chromium','README.pdfium','REUSE.toml','version.json')))


if __name__ == '__main__':
    main()
