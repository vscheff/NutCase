"""Manifest validation and safe copying, independent of the preview widget."""
import hashlib
import os
import shutil
import uuid
from pathlib import Path

from .state import read_json


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_release(manifest_path, source=None, expected_run=None):
    manifest_path = Path(manifest_path).resolve()
    record = read_json(manifest_path)
    return validate_release(record, manifest_path.parent, source, expected_run, str(manifest_path))


def validate_release(record, output, source=None, expected_run=None, manifest_path=None):
    if record.get('schema_version') != 1 or record.get('status') != 'published_preliminary':
        raise ValueError('Manifest does not describe a complete preliminary release')
    if expected_run is not None and record.get('run_id') != expected_run:
        raise ValueError('Current manifest belongs to another run; refusing stale preview')
    if source is not None and Path(record['source']).resolve() != Path(source).resolve():
        raise ValueError('Release belongs to a different STEP source location')
    release = Path(record['release_directory']).resolve()
    if not release.is_relative_to(Path(output).resolve()/'releases') or release.name != record['run_id']:
        raise ValueError('Release directory is outside the expected version history')
    stem = Path(record['source']).stem
    required = [stem+ext for ext in ('.pdf', '.FCStd', '.config.json', '.catalog.json',
                                    '.drawing.json', '.review.json', '.review.md')]
    required += ['pdf.normalization.json', 'pdf.verification.json']
    files = record.get('files', {})
    if not all(name in files for name in required):
        raise ValueError('Release is missing expected drawing or review deliverables')
    for name, row in files.items():
        path = Path(row['path']).resolve()
        if Path(name).name != name or path != release/name or not path.is_file():
            raise ValueError('Missing or invalid release path: '+name)
        if sha256(path) != row['sha256']:
            raise ValueError('Release checksum mismatch: '+name)
    audit = read_json(release/'pdf.verification.json')
    report = read_json(release/(stem+'.drawing.json'))
    if audit.get('status') != 'passed' or not report.get('source_sha256_verified_unchanged'):
        raise ValueError('Release lacks successful PDF or source validation evidence')
    if not report.get('reopen_checks',{}).get('reopened_successfully'):
        raise ValueError('Release lacks native project reopen verification')
    # The published set has already passed the native and independent PDF gates.
    # Hash checking proves this is that set, not a substituted file.
    return {'manifest':record, 'manifest_path':manifest_path, 'directory':str(release),
            'pdf':str(release/(stem+'.pdf')), 'project':str(release/(stem+'.FCStd')),
            'review':read_json(release/(stem+'.review.json')),
            'report':report, 'pdf_audit':audit,
            'config':str(release/(stem+'.config.json')), 'catalog':str(release/(stem+'.catalog.json'))}


def history_entries(output, source):
    entries = []
    for path in (Path(output)/'runs').glob('*/pipeline.json'):
        try:
            row = read_json(path)
            if row.get('status') == 'published_preliminary' and Path(row['source']).resolve() == Path(source).resolve():
                entries.append((row['run_id'], str(path)))
        except (OSError, ValueError, KeyError):
            continue
    return sorted(entries, reverse=True)


def load_history(path, output, source):
    path = Path(path).resolve()
    if not path.is_relative_to(Path(output).resolve()/'runs'):
        raise ValueError('History entry is outside retained pipeline runs')
    row = read_json(path)
    record = {'schema_version':1, 'status':row['status'], 'source':row['source'],
              'run_id':row['run_id'], 'release_directory':row['release_directory'], 'files':row['deliverables']}
    return validate_release(record, output, source)


def export_copy(release, key, destination):
    source, destination = Path(release[key]).resolve(), Path(destination).resolve()
    directory = Path(release['directory']).resolve()
    history_root = directory.parent.parent
    suffix = '.pdf' if key == 'pdf' else '.fcstd'
    if destination.suffix.lower() != suffix:
        raise ValueError('Export destination must use '+suffix)
    if destination == Path(release['manifest']['source']).resolve() or destination.is_relative_to(history_root):
        raise ValueError('Export cannot overwrite the STEP source or immutable release')
    expected = release['manifest']['files'][source.name]['sha256']
    if sha256(source) != expected:
        raise ValueError('Published artifact has changed; export refused')
    temporary = destination.with_name(destination.name+'.'+uuid.uuid4().hex+'.pending')
    try:
        shutil.copyfile(source, temporary)
        if sha256(temporary) != expected:
            raise ValueError('Export copy failed checksum verification')
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination
