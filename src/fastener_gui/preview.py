"""Native Qt PDF preview of the final normalized file; never of a native intermediate."""
from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpinBox, QComboBox


class PdfPreview(QWidget):
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.path = None
        self.document = QPdfDocument(self)
        self.view = QPdfView(self)
        self.view.setDocument(self.document)
        self.view.setPageMode(QPdfView.PageMode.SinglePage)
        self.view.setZoomMode(QPdfView.ZoomMode.FitInView)
        self.message = QLabel('Generate A Drawing To Preview Its Verified PDF')
        self.message.setWordWrap(True)
        bar = QHBoxLayout()
        previous = QPushButton('Previous'); next_page = QPushButton('Next')
        self.page = QSpinBox(); self.page.setRange(1, 1); self.page.setPrefix('Page ')
        self.count = QLabel('/ 0')
        self.zoom = QComboBox(); self.zoom.setEditable(True)
        self.zoom.addItems(['Fit To Window', 'Fit To Width', '50%', '75%', '100%', '150%', '200%', '300%'])
        for widget in (previous, self.page, self.count, next_page, self.zoom): bar.addWidget(widget)
        bar.addStretch()
        layout = QVBoxLayout(self); layout.addWidget(self.message); layout.addLayout(bar); layout.addWidget(self.view, 1)
        self.page.valueChanged.connect(self.go_to_page)
        previous.clicked.connect(lambda:self.page.setValue(self.page.value()-1))
        next_page.clicked.connect(lambda:self.page.setValue(self.page.value()+1))
        self.zoom.currentTextChanged.connect(self.set_zoom)
        self.document.statusChanged.connect(self._status)

    def clear(self, message='No Drawing Selected'):
        self.document.close(); self.path = None
        self.message.setText(message); self.page.setRange(1, 1); self.count.setText('/ 0')

    def load(self, path):
        self.clear()
        if not Path(path).is_file(): raise ValueError('Published PDF is missing')
        self.path = str(path)
        self.message.setText('Verified Normalized PDF - Preliminary, Engineering Verification Required')
        error = self.document.load(self.path)
        if error != QPdfDocument.Error.None_:
            self.clear('Preview Failed: '+str(error)); self.failed.emit(self.message.text())
            return False
        self.set_zoom(self.zoom.currentText())
        return True

    def _status(self, status):
        if status == QPdfDocument.Status.Ready:
            self.page.setRange(1, max(1,self.document.pageCount()))
            self.count.setText('/ '+str(self.document.pageCount()))
            self.go_to_page(1)
        elif status == QPdfDocument.Status.Error:
            self.failed.emit('Qt PDF Preview Error: '+str(self.document.error()))

    def go_to_page(self, page):
        if self.document.pageCount():
            from PySide6.QtCore import QPointF
            self.view.pageNavigator().jump(page-1, QPointF(), self.view.zoomFactor())

    def set_zoom(self, text):
        if text == 'Fit To Window': self.view.setZoomMode(QPdfView.ZoomMode.FitInView)
        elif text == 'Fit To Width': self.view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        else:
            try:
                factor = float(text.rstrip('%'))/100
                if not 0.1 <= factor <= 8: return
                self.view.setZoomMode(QPdfView.ZoomMode.Custom); self.view.setZoomFactor(factor)
            except ValueError: return
