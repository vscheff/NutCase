"""Native Qt PDF preview of the final normalized file; never of a native intermediate."""
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QSignalBlocker
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
        # Qt's FitInView reserves pageSpacing vertically; reserve both page margins
        # so the fitted page remains fully visible with the scrollbars disabled.
        margins = self.view.documentMargins()
        self.view.setPageSpacing(margins.top() + margins.bottom())
        self.message = QLabel('Generate A Drawing To Preview Its Verified PDF')
        self.message.setWordWrap(True)
        bar = QHBoxLayout()
        previous = QPushButton('Previous'); next_page = QPushButton('Next')
        self.page = QSpinBox(); self.page.setRange(1, 1); self.page.setPrefix('Page ')
        self.count = QLabel('/ 0')
        self.zoom = QComboBox(); self.zoom.setEditable(True)
        self.zoom.addItems(['Fit To Window', 'Fit To Width', '50%', '75%', '100%', '150%', '200%', '300%'])
        self.page_controls = QWidget()
        pages = QHBoxLayout(self.page_controls)
        pages.setContentsMargins(0, 0, 0, 0)
        for widget in (previous, self.page, self.count, next_page): pages.addWidget(widget)
        self.page_controls.hide()
        bar.addStretch()
        bar.addWidget(self.page_controls)
        bar.addWidget(self.zoom)
        layout = QVBoxLayout(self); layout.addWidget(self.message); layout.addWidget(self.view, 1); layout.addLayout(bar)
        self.page.valueChanged.connect(self.go_to_page)
        previous.clicked.connect(lambda:self.page.setValue(self.page.value()-1))
        next_page.clicked.connect(lambda:self.page.setValue(self.page.value()+1))
        self.zoom.currentTextChanged.connect(self.set_zoom)
        self.view.zoomFactorChanged.connect(self._view_zoom_changed)
        self.view.zoomModeChanged.connect(self._sync_zoom)
        self.document.statusChanged.connect(self._status)
        self.set_zoom(self.zoom.currentText())

    def set_message(self, message):
        self.message.setText(message)
        self.message.setVisible(bool(message))

    def clear(self, message='No Drawing Selected'):
        self.document.close(); self.path = None
        self.set_message(message); self.page.setRange(1, 1); self.count.setText('/ 0')
        self.page_controls.hide()

    def load(self, path):
        self.clear()
        if not Path(path).is_file(): raise ValueError('Published PDF is missing')
        self.path = str(path)
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
            self.page_controls.setVisible(self.document.pageCount() > 1)
            self.set_message('')
            self.go_to_page(1)
        elif status == QPdfDocument.Status.Error:
            self.failed.emit('Qt PDF Preview Error: '+str(self.document.error()))

    def go_to_page(self, page):
        if self.document.pageCount():
            from PySide6.QtCore import QPointF
            self.view.pageNavigator().jump(page-1, QPointF(), self.view.zoomFactor())

    def _view_zoom_changed(self, factor):
        # Ctrl+wheel changes Qt's zoom factor without leaving its fit mode.
        self.view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._sync_zoom()

    def _sync_zoom(self, *args):
        mode = self.view.zoomMode()
        text = ('Fit To Window' if mode == QPdfView.ZoomMode.FitInView else
                'Fit To Width' if mode == QPdfView.ZoomMode.FitToWidth else
                f'{self.view.zoomFactor() * 100:.6g}%')
        # Reflect the native view without feeding rounded text back into it.
        with QSignalBlocker(self.zoom):
            self.zoom.setCurrentText(text)

    def set_zoom(self, text):
        # Automatic scrollbars can repeatedly change the width used for fitting,
        # invalidating the native page cache on every resize and starving the UI.
        if text == 'Fit To Window':
            self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.view.setZoomMode(QPdfView.ZoomMode.FitInView)
        elif text == 'Fit To Width':
            self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
            self.view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        else:
            try:
                factor = float(text.rstrip('%'))/100
                if not 0.1 <= factor <= 10: return
                self.view.setZoomMode(QPdfView.ZoomMode.Custom); self.view.setZoomFactor(factor)
                self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
                self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            except ValueError: return
