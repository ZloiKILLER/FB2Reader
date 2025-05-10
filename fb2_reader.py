import sys, os, base64
import xml.etree.ElementTree as ET

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QFileDialog,
    QVBoxLayout, QTextBrowser, QProgressBar
)
from PySide6.QtGui import QPixmap, QFontDatabase, QAction
from PySide6.QtCore import Qt

class FB2Reader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FB2Reader")
        self.resize(800, 600)

        # Меню
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")
        open_action = QAction("Open FB2...", self)
        open_action.triggered.connect(self.open_fb2)
        file_menu.addAction(open_action)

        settings_menu = menu_bar.addMenu("Settings")
        theme_dark = QAction("Dark Theme", self)
        theme_dark.triggered.connect(lambda: self.apply_theme("dark"))
        settings_menu.addAction(theme_dark)

        theme_sepia = QAction("Sepia Theme", self)
        theme_sepia.triggered.connect(lambda: self.apply_theme("sepia"))
        settings_menu.addAction(theme_sepia)

        theme_light = QAction("Light Theme", self)
        theme_light.triggered.connect(lambda: self.apply_theme("light"))
        settings_menu.addAction(theme_light)

        font_menu = settings_menu.addMenu("Font")
        for family in sorted(QFontDatabase.families()):
            action = QAction(family, self)
            action.triggered.connect(lambda checked, fam=family: self.set_font(fam))
            font_menu.addAction(action)

        custom_font_action = QAction("Choose custom font (.ttf/.otf)", self)
        custom_font_action.triggered.connect(self.select_custom_font)
        font_menu.addAction(custom_font_action)

        # Виджеты
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)

        self.content = QTextBrowser()
        self.content.setOpenExternalLinks(True)
        self.content.setReadOnly(True)
        self.content.setFocusPolicy(Qt.StrongFocus)
        self.content.verticalScrollBar().valueChanged.connect(self.update_progress)

        layout = QVBoxLayout()
        layout.addWidget(self.content)
        layout.addWidget(self.progress)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.current_font = "Georgia"
        self.apply_theme("light")

    def open_fb2(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open FB2", os.getcwd(), "FB2 Files (*.fb2)")
        if path:
            self.load_fb2(path)

    def load_fb2(self, filepath):
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            ns = {'fb2': 'http://www.gribuser.ru/xml/fictionbook/2.0'}

            binaries = {
                b.attrib["id"]: b.text.strip()
                for b in root.findall("fb2:binary", ns)
                if b.text
            }

            html = ""
            cover = root.find(".//fb2:coverpage/fb2:image", ns)
            if cover is not None:
                href = cover.attrib.get("{http://www.w3.org/1999/xlink}href", "")
                if href.startswith("#"):
                    img_id = href[1:]
                    data = binaries.get(img_id)
                    if data:
                        html += f'<img src="data:image/jpeg;base64,{data}" width="300"/><br><br>'

            body = root.find("fb2:body", ns)
            for section in body.findall("fb2:section", ns):
                title = section.find("fb2:title", ns)
                if title is not None:
                    for p in title.findall("fb2:p", ns):
                        html += f"<h2>{p.text}</h2>"
                for p in section.findall("fb2:p", ns):
                    if p.text:
                        html += f"<p>{p.text}</p>"

            self.content.setHtml(html)
            self.update_progress()

        except Exception as e:
            self.content.setPlainText(f"Error loading FB2: {e}")

    def update_progress(self):
        bar = self.content.verticalScrollBar()
        max_val = bar.maximum() or 1
        percent = int(bar.value() / max_val * 100)
        self.progress.setValue(percent)
        self.progress.setFormat(f"{percent}%")

    def set_font(self, family):
        self.current_font = family
        current = self.content.styleSheet()
        updated = []
        for line in current.splitlines():
            if 'font-family' in line:
                updated.append(f"    font-family: {family};")
            else:
                updated.append(line)
        stylesheet = "\n".join(updated)
        self.content.setStyleSheet(stylesheet)

    def select_custom_font(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Font", os.getcwd(), "Font Files (*.ttf *.otf)")
        if path:
            font_id = QFontDatabase.addApplicationFont(path)
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                self.set_font(families[0])

    def apply_theme(self, name):
        if name == "dark":
            self.content.setStyleSheet(f"""
                QTextBrowser {{
                    background-color: #121212;
                    color: #DDDDDD;
                    font-family: {self.current_font};
                    font-size: 16px;
                }}
            """)
        elif name == "sepia":
            self.content.setStyleSheet(f"""
                QTextBrowser {{
                    background-color: #f4ecd8;
                    color: #5b4636;
                    font-family: {self.current_font};
                    font-size: 16px;
                }}
            """)
        else:
            self.content.setStyleSheet(f"""
                QTextBrowser {{
                    background-color: #ffffff;
                    color: #000000;
                    font-family: {self.current_font};
                    font-size: 16px;
                }}
            """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FB2Reader()
    window.show()
    sys.exit(app.exec())
