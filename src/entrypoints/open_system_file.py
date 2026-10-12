"""A Windows file association may block; this helper never runs on the UI thread."""
import os
import sys

if __name__=='__main__':
    try:os.startfile(sys.argv[1])
    except Exception as error:
        print(str(error),file=sys.stderr)
        raise SystemExit(1)
