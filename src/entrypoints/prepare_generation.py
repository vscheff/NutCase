"""Native analysis and configuration binding before any drawing is generated."""
import argparse
import sys
from pathlib import Path

import _bootstrap
from fastener_analysis.cli import build_report
from fastener_analysis.importer import import_step
from fastener_analysis.export import write_json
from fastener_drawing.export import shape_signature
from fastener_drawing.configuration import read_config, make_catalog, bind_config


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--config', type=Path)
    a = p.parse_args()
    a.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        analysis = build_report(a.input)
        write_json(analysis, a.output_dir/(a.input.stem+'.analysis.json'))
        if len(analysis['components']) != 1:
            raise ValueError('Drawing configuration requires one solid; no arbitrary assembly selection')
        shape, metadata = import_step(a.input)
        if metadata['sha256_before'] != analysis['source']['sha256_before']:
            raise ValueError('Source changed during preparation')
        catalog = make_catalog(analysis['components'][0]['feature_discovery'], shape_signature(shape), metadata['sha256_before'])
        write_json(catalog, a.output_dir/(a.input.stem+'.catalog.json'))
        config = bind_config(read_config(a.config), catalog)
        write_json(config, a.output_dir/(a.input.stem+'.config.json'))
        return 2 if analysis['analysis_status'] in ('needs_review', 'geometry_only') else 0
    except Exception as exc:
        write_json({'status':'requires_review', 'error':str(exc)}, a.output_dir/'preparation.failure.json')
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
