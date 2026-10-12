"""Windows desktop entry point, using external Python only."""
import argparse
import sys
import tempfile
from pathlib import Path

from _bootstrap import PROJECT_ROOT as ROOT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',nargs='?',type=Path)
    parser.add_argument('--freecad-python',default='')
    parser.add_argument('--poppler',default='')
    parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--settings-dir',type=Path)
    parser.add_argument('--startup-check',action='store_true',
                        help='Initialize the actual GUI and event loop, then exit without generation or saved-settings changes')
    args=parser.parse_args()
    # Import GUI libraries only in external Python, never via FreeCAD's runtime.
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    from fastener_gui.window import MainWindow
    from fastener_gui.theme import apply_theme
    app=QApplication(sys.argv);app.setApplicationName('Fastener Drawing Generator')
    app.setOrganizationName('FastenerDrawing');apply_theme(app)
    # Diagnostic startup must not alter the user's persisted GUI state.
    temporary_settings=None
    if args.startup_check:
        diagnostic_root=ROOT/'tmp'/'gui-startup'
        diagnostic_root.mkdir(parents=True,exist_ok=True)
        temporary_settings=tempfile.TemporaryDirectory(prefix='check-',dir=diagnostic_root)
    settings_dir=Path(temporary_settings.name) if temporary_settings else args.settings_dir
    window=MainWindow(args.freecad_python,args.poppler,args.output_dir,settings_dir)
    if args.input:window.set_source(args.input)
    window.show()
    if args.startup_check:
        def finish_check():
            print('GUI_STARTUP_OK',flush=True)
            window.close()
            app.quit()
        QTimer.singleShot(100,finish_check)
    try:
        return app.exec()
    finally:
        if temporary_settings:temporary_settings.cleanup()


if __name__=='__main__':raise SystemExit(main())
