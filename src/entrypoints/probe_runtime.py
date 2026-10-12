"""Probe interpreter dependencies without embedding Python code in shell arguments."""
import argparse
import importlib


DEPENDENCIES = {
    'gui': ('PySide6.QtPdfWidgets', 'pypdf', 'pypdfium2', 'PIL'),
    'pdf': ('pypdf', 'pypdfium2', 'PIL'),
    # FreeCAD must initialize before Part loads its native dependencies.
    'freecad': ('FreeCAD', 'Part'),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runtime', choices=DEPENDENCIES)
    args = parser.parse_args()
    for module in DEPENDENCIES[args.runtime]:
        importlib.import_module(module)
    print({'gui': 'GUI_RUNTIME_OK', 'pdf': 'PDF_RUNTIME_OK',
           'freecad': 'NATIVE_FREECAD_OK'}[args.runtime])


if __name__ == '__main__':
    main()
