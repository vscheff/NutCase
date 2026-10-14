"""Independent embedded-font vector PDF; only temporary files contain fonts."""
from pathlib import Path
import os
from pypdf import PdfWriter, PdfReader
from pypdf.generic import ContentStream, DictionaryObject, NameObject

APP=None


def embedded_fixture(path, malformed=False):
    global APP
    from PySide6.QtGui import QGuiApplication, QPainter, QPdfWriter, QPageSize, QPageLayout, QFont, QPen, QFontDatabase
    from PySide6.QtCore import QSizeF, QMarginsF
    APP=QGuiApplication.instance() or QGuiApplication([])
    # Windows offscreen Qt may enumerate no fonts. Use the installed font's
    # actual bytes, as the native CAD runtime does; no font file is committed.
    if not QFontDatabase.families():
        font=Path(os.environ.get('SystemRoot','C:/Windows'))/'Fonts/arial.ttf'
        if not font.is_file() or QFontDatabase.addApplicationFontFromData(font.read_bytes())<0:
            raise RuntimeError('Independent PDF control requires an installed usable font')
    path=Path(path);raw=path.with_name(path.stem+'.qt.pdf')
    writer=QPdfWriter(str(raw));writer.setResolution(72)
    writer.setPageSize(QPageSize(QSizeF(612,396),QPageSize.Unit.Point))
    writer.setPageMargins(QMarginsF(0,0,0,0),QPageLayout.Unit.Point)
    painter=QPainter(writer);pen=QPen();pen.setWidthF(.7);painter.setPen(pen);painter.setFont(QFont('Arial',12))
    painter.drawRect(50,50,100,50);painter.drawEllipse(200,50,60,60)
    painter.drawText(50,150,'LINEAR 20.00');painter.drawText(50,180,'DIAMETER 10.00')
    painter.end();del painter,writer
    if not malformed:
        path.write_bytes(raw.read_bytes());return
    output=PdfWriter(clone_from=raw);page=output.pages[0]
    resources=page['/Resources']
    spaces=resources.get('/ColorSpace',DictionaryObject())
    spaces[NameObject('/TestRGB')]=NameObject('/DeviceRGB');resources[NameObject('/ColorSpace')]=spaces
    stream=ContentStream(page.get_contents(),output)
    # Independent, precisely bounded versions of the observed Qt defects.
    stream.operations += [([],b'q'),([],b'h'),([],b'f'),([],b'Q'),
                          ([NameObject('/TestRGB')],b'CS'),([],b'SCN')]
    page.replace_contents(stream);output.write(path)
