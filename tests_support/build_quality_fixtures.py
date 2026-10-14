"""Recovered independent fixture constructors, adapted to isolated test output."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests_native'),str(ROOT/'tests_support')]
from test_quality import countersunk_pin,shoulder_pin,slotted_round_head,grooved_dowel
from test_analysis import moved
from fastener_analysis.importer import sha256


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    rows=[]
    for maker,length in ((countersunk_pin,27),(shoulder_pin,31),(slotted_round_head,24),(grooved_dowel,35)):
        path=args.output/(maker.__name__+'.step')
        if path.exists():raise ValueError('Refusing to overwrite a fixture from another run: '+str(path))
        moved(maker()).exportStep(str(path))
        rows.append({'file':str(path),'sha256':sha256(path),'construction':maker.__name__,
                     'known_overall_length_mm':length,'synthetic':True,'arbitrarily_rotated_and_translated':True})
    (args.output/'manifest.json').write_text(json.dumps({'fixtures':rows,
        'notice':'Independent synthetic constructions; additional independent real STEP samples remain necessary.'},indent=2),encoding='utf-8')


if __name__=='__main__':main()
