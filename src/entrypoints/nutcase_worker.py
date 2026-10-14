"""Explicit frozen worker dispatch: never interpret arguments as Python code."""
import argparse
import json
import sys

import _bootstrap


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('gui-job', 'pipeline', 'open-file', 'diagnose'))
    args, remaining = parser.parse_known_args()
    sys.argv = [sys.argv[0], *remaining]
    if args.action == 'gui-job':
        from gui_worker import main as run
        return run()
    if args.action == 'pipeline':
        from fastener_drawing.process_control import WindowsJob
        job = WindowsJob();job.assign()  # Retain until OS teardown kills descendants.
        from fastener_drawing.pipeline import main as run
        return run(remaining)
    if args.action == 'open-file':
        from open_system_file import main as run
        return run()
    from nutcase_discovery import diagnose
    print(json.dumps(diagnose(), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
