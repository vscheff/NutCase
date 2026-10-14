"""Probe interpreter dependencies without embedding Python code in shell arguments."""
import argparse
import importlib
import json
import struct


DEPENDENCIES = {
    'gui': ('PySide6.QtPdfWidgets', 'pypdf', 'pypdfium2', 'PIL'),
    'pdf': ('pypdf', 'pypdfium2', 'PIL'),
    # FreeCAD must initialize before Part loads its native dependencies.
    'freecad': ('FreeCAD', 'Part', 'FreeCADGui', 'TechDraw'),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runtime', choices=DEPENDENCIES)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    for module in DEPENDENCIES[args.runtime]:
        importlib.import_module(module)
    if args.json and args.runtime == 'freecad':
        import FreeCAD
        print('NUTCASE_NATIVE_RUNTIME='+json.dumps({'freecad_version':FreeCAD.Version(), 'bits':struct.calcsize('P')*8}))
    print({'gui': 'GUI_RUNTIME_OK', 'pdf': 'PDF_RUNTIME_OK',
           'freecad': 'NATIVE_FREECAD_OK'}[args.runtime])


if __name__ == '__main__':
    main()
