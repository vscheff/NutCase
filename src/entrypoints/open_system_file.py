"""A Windows file association may block; this helper never runs on the UI thread."""
import os
import sys

import _bootstrap
from nutcase_runtime import external_dll_search


def main():
    try:
        with external_dll_search():os.startfile(sys.argv[1])
    except Exception as error:
        print(str(error),file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
