from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel, QApplication, QMenu
from PyQt5.QtGui import QPainter, QPixmap, QImage, QColor, QPen, QKeySequence
from PyQt5.QtCore import Qt, QRectF, QPoint, QSize
import fitz  # PyMuPDF

class SelectablePdfPage(QWidget):
    def __init__(self, doc: fitz.Document, page_index: int, zoom: float = 1.5, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.page_index = page_index
        self.zoom = zoom
        self.page = self.doc.load_page(page_index)
        self.words = []          # list[(x0,y0,x1,y1,word,block,line,word_no)]
        self.selection_active = False
        self.sel_anchor = QPoint()
        self.sel_current = QPoint()
        self.selection_rect = QRectF()
        self._pixmap = None
        self._render()

        # Shortcut: Ctrl+C to copy selected text
        self.shortcut_copy = QKeySequence(Qt.CTRL + Qt.Key_C)

    def sizeHint(self) -> QSize:
        if self._pixmap is not None:
            return self._pixmap.size()
        return super().sizeHint()

    def _render(self):
        # Render page pixmap
        m = fitz.Matrix(self.zoom, self.zoom)
        pix = self.page.get_pixmap(matrix=m)
        fmt = QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888
        img = QImage(bytes(pix.samples), pix.width, pix.height, pix.stride, fmt)
        self._pixmap = QPixmap.fromImage(img)

        # Extract word boxes (points) and cache scaled rects in device pixels
        # words: (x0, y0, x1, y1, word, block_no, line_no, word_no)
        self.words = self.page.get_text("words", sort=True) or []
        self._word_rects = []
        for (x0, y0, x1, y1, w, b, l, wn) in self.words:
            rx0 = x0 * self.zoom
            ry0 = y0 * self.zoom
            rx1 = x1 * self.zoom
            ry1 = y1 * self.zoom
            self._word_rects.append((QRectF(rx0, ry0, rx1 - rx0, ry1 - ry0), w, b, l, wn))

        self.setMinimumSize(self._pixmap.size())
        self.update()

    def set_zoom(self, zoom: float):
        if zoom <= 0:
            return
        self.zoom = zoom
        self.selection_rect = QRectF()
        self._render()

    def paintEvent(self, event):
        if not self._pixmap:
            return
        p = QPainter(self)
        p.drawPixmap(0, 0, self._pixmap)

        # Highlight selected words
        if not self.selection_rect.isNull():
            sel_pen = QPen(QColor(33, 150, 243, 180))
            sel_brush = QColor(33, 150, 243, 60)
            p.setPen(sel_pen)
            p.setBrush(sel_brush)
            for rect, *_ in self._word_rects:
                if rect.intersects(self.selection_rect):
                    p.drawRect(rect)

        # Draw the selection marquee
        if self.selection_active and not self.selection_rect.isNull():
            pen = QPen(QColor(25, 118, 210), 1, Qt.DashLine)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRect(self.selection_rect)

        p.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.selection_active = True
            self.sel_anchor = e.pos()
            self.sel_current = e.pos()
            self._update_selection_rect()
            self.update()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self.selection_active:
            self.sel_current = e.pos()
            self._update_selection_rect()
            self.update()
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.selection_active:
            self.selection_active = False
            self.sel_current = e.pos()
            self._update_selection_rect()
            self.update()
        super().mouseReleaseEvent(e)

    def _update_selection_rect(self):
        x1, y1 = self.sel_anchor.x(), self.sel_anchor.y()
        x2, y2 = self.sel_current.x(), self.sel_current.y()
        left, top = min(x1, x2), min(y1, y2)
        right, bottom = max(x1, x2), max(y1, y2)
        self.selection_rect = QRectF(left, top, right - left, bottom - top)

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        copy_act = menu.addAction("Copy")
        act = menu.exec_(e.globalPos())
        if act == copy_act:
            self.copy_selection()

    def keyPressEvent(self, e):
        if QKeySequence(e.modifiers() | e.key()) == self.shortcut_copy:
            self.copy_selection()
            return
        super().keyPressEvent(e)

    def selected_text(self) -> str:
        if self.selection_rect.isNull():
            return ""
        # Collect intersecting words and sort by block/line/word_no for reading order
        selected = []
        for (rect, w, b, l, wn) in self._word_rects:
            if rect.intersects(self.selection_rect):
                selected.append((b, l, wn, rect.y(), rect.x(), w))
        if not selected:
            return ""
        selected.sort(key=lambda t: (t[0], t[1], t[2], t[3], t[4]))
        # Join words with spaces, inserting newlines on line changes
        out = []
        last_key = None
        for (b, l, wn, _y, _x, w) in selected:
            key = (b, l)
            if last_key is not None and key != last_key:
                out.append("\n")
            elif out and not out[-1].endswith(("\n", " ")):
                out.append(" ")
            out.append(w)
            last_key = key
        return "".join(out).strip()

    def copy_selection(self):
        text = self.selected_text()
        if text:
            QApplication.clipboard().setText(text)

class SelectablePdfViewer(QWidget):
    def __init__(self, pdf_path: str, zoom: float = 1.5, parent=None):
        super().__init__(parent)
        self.zoom = zoom
        self.doc = fitz.open(pdf_path)

        self.container = QWidget(self)
        self.vbox = QVBoxLayout(self.container)
        self.vbox.setContentsMargins(0, 0, 0, 0)
        self.vbox.setSpacing(12)

        self.pages = []
        for i in range(self.doc.page_count):
            page_widget = SelectablePdfPage(self.doc, i, self.zoom, parent=self.container)
            self.vbox.addWidget(page_widget)
            self.pages.append(page_widget)

        self.vbox.addStretch(1)

        # Wrap in a scroll area for use in arbitrary layouts
        self.scroll = QScrollArea(self)
        self.scroll.setWidget(self.container)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QLabel.NoFrame)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.scroll)

    def set_zoom(self, zoom: float):
        if zoom <= 0:
            return
        self.zoom = zoom
        for p in self.pages:
            p.set_zoom(self.zoom)