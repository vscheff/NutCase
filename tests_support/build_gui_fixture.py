"""Construct public synthetic GUI data with native FreeCAD; no supplied STEP data.

The GUI publication flags and warning below are intentionally mocked. This data
tests UI branches, and is never evidence that a drawing has been verified.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import FreeCAD as App
import Part
from fastener_analysis.cli import build_report
from fastener_drawing.configuration import make_catalog, bind_config, read_config
from fastener_drawing.export import shape_signature
from fastener_drawing.review import build_review

work = ROOT/'build/test-fixtures'; work.mkdir(parents=True, exist_ok=True)
source = work/'synthetic hollow pin.step'
shape = Part.makeCylinder(5, 18).cut(Part.makeCylinder(2, 18)).Solids[0]
shape.exportStep(str(source))
analysis = build_report(source)
discovery = analysis['components'][0]['feature_discovery']
# Exercise an unsupported item independently of recognition. This is simulated
# data, not a discovered characteristic of the hollow pin.
discovery['features'].append({'id': 'mock-unsupported', 'type': 'mock_unknown', 'coaxial': False})
discovery['dimension_candidates'].append({'id': 'mock-unsupported', 'feature_id': 'mock-unsupported',
    'label': 'Mock Unsupported Characteristic', 'kind': 'mock', 'value': None, 'units': 'mm',
    'verification_status': 'unsupported'})
catalog = make_catalog(discovery, shape_signature(shape), analysis['source']['sha256_before'])
config = bind_config(read_config(), catalog)
validation = analysis['validation']
validation['boolean_check'] = {'status': 'failed', 'message': 'BOPAlgo MOCK warning for GUI branch coverage only'}
analysis['source']['path'] = '@SOURCE@'
report = {'fixture_only': True, 'source': '@SOURCE@', 'configuration': config,
          'source_analysis': analysis, 'geometry_requires_review': True, 'unresolved_dimensions': [],
          'source_sha256_verified_unchanged': True,
          'reopen_checks': {'reopened_successfully': True, 'dimension_checks': {}},
          'dimensions': {c['id']: {'status': 'unresolved' if c['verification_status'] == 'unsupported' else 'suppressed',
                                  'selected': False, 'selection_reason': 'Mock GUI fixture'}
                         for c in discovery['dimension_candidates']}}
data = {'provenance': 'New independently constructed hollow pin; native measurements, MOCK release verification flags and MOCK Boolean warning.',
        'catalog': catalog, 'analysis': analysis, 'config': config, 'report': report, 'review': build_review(report)}
(ROOT/'tests_gui/fixtures/synthetic_source.json').write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
print('Wrote independent GUI data; no actual drawing verification claimed')
