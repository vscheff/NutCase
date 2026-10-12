"""Repair known native Qt PDF defects without redrawing or rasterization."""
import argparse
import json
from pathlib import Path

import _bootstrap


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True, help='Separate candidate PDF path')
    parser.add_argument('--drawing-report', type=Path, help='Check every existing native dimension label')
    parser.add_argument('--report', type=Path, required=True, help='JSON audit output')
    args = parser.parse_args()
    try:
        from fastener_drawing.pdf_compatibility import normalize_pdf
        from pypdf.errors import PdfReadError
    except ImportError:
        parser.error('This optional PDF stage needs pypdf in the executing Python environment')
    labels = []
    try:
        if args.report.resolve() in (args.source.resolve(), args.output.resolve()):
            raise ValueError('JSON report path must differ from both PDF paths')
        if args.drawing_report:
            if args.report.resolve() == args.drawing_report.resolve():
                raise ValueError('Do not overwrite the input drawing report with the audit')
            report = json.loads(args.drawing_report.read_text(encoding='utf-8'))
            labels = report['native_render_checks']['actual_dimension_labels']
        result = normalize_pdf(args.source, args.output, labels)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    except (ValueError, RuntimeError, OSError, KeyError, PdfReadError) as error:
        parser.exit(1, 'PDF normalization failed: ' + str(error) + '\n')
    print(f"Preserved {len(labels)} expected labels; repaired "
          f"{sum(len(p['changes']) for p in result['pages'])} operators. Audit: {args.report}")


if __name__ == '__main__':
    main()
