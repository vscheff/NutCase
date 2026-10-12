"""Source-bound GUI policy and durable, human-readable configuration storage."""
import copy
import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path

from fastener_drawing.configuration import bind_config, read_config, selection_decisions, validate_config
from fastener_paths import PROJECT_ROOT as ROOT


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def atomic_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.'+uuid.uuid4().hex+'.pending')
    try:
        with temporary.open('w', encoding='utf-8') as file:
            json.dump(value, file, ensure_ascii=False, indent=2)
            file.write('\n'); file.flush(); os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class ConfigStore:
    def __init__(self, directory):
        self.directory = Path(directory)

    def path(self, source):
        key = hashlib.sha256(os.path.normcase(str(Path(source).resolve())).encode()).hexdigest()[:24]
        return self.directory/'configurations'/(key+'.json')

    def load(self, source):
        path = self.path(source)
        return read_config(path) if path.exists() else None

    def save(self, source, config):
        validate_config(config)
        path = self.path(source)
        if path.exists():
            # Retain the old binding and selections when the operator starts anew.
            try: identical=read_json(path)==config
            except (ValueError,OSError):identical=False
            if not identical:
                history=path.parent/'history';history.mkdir(exist_ok=True)
                shutil.copyfile(path,history/(path.stem+'-'+uuid.uuid4().hex+'.json'))
        atomic_json(path, config)
        return path


class ModelState:
    def __init__(self):
        self.source = None
        self.catalog = None
        self.analysis = None
        self.config = read_config()
        self.binding_problem = None

    def accept_analysis(self, source, catalog, analysis, saved=None):
        self.source = Path(source).resolve()
        self.catalog, self.analysis = catalog, analysis
        self.binding_problem = None
        try:
            self.config = bind_config(saved or read_config(), catalog)
        except ValueError as error:
            # Keep the old policy exactly. Generation stays disabled until review.
            self.config = copy.deepcopy(saved)
            self.binding_problem = str(error)

    def fresh_configuration(self):
        if self.catalog is None:
            raise ValueError('Analyze the source before starting a configuration')
        self.config = bind_config(read_config(), self.catalog)
        self.binding_problem = None

    def checked_config(self):
        if self.binding_problem or self.catalog is None:
            raise ValueError(self.binding_problem or 'Analyze a STEP file first')
        validate_config(self.config)
        return bind_config(self.config, self.catalog)

    def decisions(self):
        discovery = self.analysis['components'][0]['feature_discovery']
        keys = {row['candidate_id']:row['stable_id'] for row in self.catalog['candidates']}
        discovery = copy.deepcopy(discovery)
        for candidate in discovery['dimension_candidates']:
            candidate['stable_id'] = keys[candidate['id']]
        return selection_decisions(self.checked_config(), discovery)

    def set_selected(self, stable_id, selected):
        self.checked_config()
        if stable_id not in {r['stable_id'] for r in self.catalog['candidates']}:
            raise ValueError('Dimension is absent from the current source catalog')
        policy = self.config['dimensioning']
        for key in ('include', 'exclude'):
            policy[key] = [x for x in policy[key] if x != stable_id]
        policy['include' if selected else 'exclude'].append(stable_id)


def completion_status(code, result):
    if code == 3:
        return 'Cancelled - Previous Release Preserved'
    if code not in (0, 2) or not result:
        return 'Failed - No New Drawing Published'
    if result.get('status') == 'catalog_ready':
        return 'Analysis Complete - Review Source Geometry'
    return 'Completed - Engineering Review Required' if code == 2 else 'Completed - Preliminary Drawing'
