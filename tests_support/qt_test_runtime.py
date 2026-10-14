"""Initialize readable offscreen Qt controls using installed fonts, not boxes."""
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase

APP=None


def initialize():
    global APP
    APP=QApplication.instance() or QApplication([])
    if os.name=='nt':
        directory=Path(os.environ.get('SystemRoot','C:/Windows'))/'Fonts'
        for name in ('arial.ttf','arialbd.ttf','segoeui.ttf','segoeuib.ttf'):
            font=directory/name
            if font.is_file():QFontDatabase.addApplicationFontFromData(font.read_bytes())
    if not QFontDatabase.families():
        raise RuntimeError('Qt GUI regression requires usable fonts for meaningful layout checks')
    return APP
