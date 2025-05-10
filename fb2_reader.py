import sys, os, base64
import xml.etree.ElementTree as ET

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QFileDialog,
    QVBoxLayout, QTextBrowser, QScrollArea, QProgressBar, QPushButton
)
from PySide6.QtGui import QPixmap, QAction, QKeyEvent
from PySide6.QtCore import Qt

class FB2Reader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FB2Reader")
        self.resize(800, 600)

        # Меню
        menu = self.menuBar().addMenu("File")
        open_action = QAction("Open FB2...", self)
        open_action.triggered.connect(self.open_fb2)
        menu.addAction(open_action)

        # Прогресс
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)

        # Основной виджет (прокручиваемый)
        self.content = QTextBrowser()
        self.content.setOpenExternalLinks(True)
        self.content.setReadOnly(True)
        self.content.setFocusPolicy(Qt.StrongFocus)

        # Слой
        layout = QVBoxLayout()
        layout.addWidget(self.content)
        layout.addWidget(self.progress)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Клавиши
        self.content.installEventFilter(self)
        self.total_blocks = 1

    def open_fb2(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open FB2", os.getcwd(), "FB2 Files (*.fb2)"
        )
        if path:
            self.load_fb2(path)

    def load_fb2(self, filepath):
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            ns = {'fb2': 'http://www.gribuser.ru/xml/fictionbook/2.0'}

            # Обложка
            binaries = {
                b.attrib["id"]: b.text.strip()
                for b in root.findall("fb2:binary", ns)
                if b.text
            }
            html = ""

            cover_image_tag = root.find(".//fb2:coverpage/fb2:image", ns)
            if cover_image_tag is not None:
                href = cover_image_tag.attrib.get("{http://www.w3.org/1999/xlink}href", "")
                if href.startswith("#"):
                    cover_id = href[1:]
                    base64_data = binaries.get(cover_id)
                    if base64_data:
                        html += f'<img src="data:image/jpeg;base64,{base64_data}" width="300"/><br><br>'

            body = root.find("fb2:body", ns)
            sections = body.findall("fb2:section", ns)
            blocks = []

            for section in sections:
                title = section.find("fb2:title", ns)
                if title is not None:
                    for p in title.findall("fb2:p", ns):
                        html += f"<h2>{p.text}</h2>"

                for p in section.findall("fb2:p", ns):
                    if p.text:
                        html += f"<p>{p.text}</p>"

            self.content.setHtml(html)
            self.total_blocks = self.content.document().blockCount()
            self.update_progress()

        except Exception as e:
            self.content.setPlainText(f"Error loading FB2: {e}")

    def eventFilter(self, obj, event):
        if obj is self.content:
            if event.type() == event.Type.KeyPress:
                if event.key() in [Qt.Key_Down, Qt.Key_Up]:
                    self.update_progress()
        return super().eventFilter(obj, event)

    def update_progress(self):
        cursor = self.content.textCursor()
        current = cursor.blockNumber() + 1
        percent = int(current / self.total_blocks * 100)
        self.progress.setValue(percent)
        self.progress.setFormat(f"{percent}% — Paragraph {current}/{self.total_blocks}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FB2Reader()
    window.show()
    sys.exit(app.exec())
