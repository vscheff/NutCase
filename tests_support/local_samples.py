"""Private development STEP files are optional, never required for public tests."""
import os
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def samples():
    found = []
    for code in ('09748', '13125'):
        matches = sorted(p for p in (ROOT/'input').glob('*')
                         if code in p.name and p.suffix.lower() in ('.stp', '.step'))
        if len(matches) != 1:
            raise unittest.SkipTest('Optional local supplied STEP pair is unavailable or ambiguous')
        found.extend(matches)
    return found


def require_samples(test):
    def wrapped(self, *args, **kwargs):
        if os.environ.get('NUTCASE_TEST_SAMPLES') != '1':
            self.skipTest('Optional local samples: pass --samples; no redistribution assumed')
        samples()
        return test(self, *args, **kwargs)
    wrapped.__name__, wrapped.__doc__ = test.__name__, test.__doc__
    return wrapped
