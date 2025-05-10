import sys, os, base64, re
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

        self.default_font_size = 16
        self.current_font_size = self.default_font_size

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

        self.zoom_in_action = QAction("Zoom In", self)
        self.zoom_in_action.triggered.connect(lambda: self.adjust_font_size(2))
        self.zoom_out_action = QAction("Zoom Out", self)
        self.zoom_out_action.triggered.connect(lambda: self.adjust_font_size(-2))
        self.reset_zoom_action = QAction("Reset Zoom", self)
        self.reset_zoom_action.triggered.connect(self.reset_zoom)

        self.zoom_in_action.setVisible(False)
        self.zoom_out_action.setVisible(False)
        self.reset_zoom_action.setVisible(False)

        view_menu = menu_bar.addMenu("View")
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        view_menu.addAction(self.reset_zoom_action)

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
            self.zoom_in_action.setVisible(True)
            self.zoom_out_action.setVisible(True)
            self.reset_zoom_action.setVisible(True)
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
        self.apply_theme("custom")

    def select_custom_font(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Font", os.getcwd(), "Font Files (*.ttf *.otf)")
        if path:
            font_id = QFontDatabase.addApplicationFont(path)
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                self.set_font(families[0])

    def adjust_font_size(self, delta):
        self.current_font_size = max(6, self.current_font_size + delta)
        self.apply_theme("custom")

    def reset_zoom(self):
        self.current_font_size = self.default_font_size
        self.apply_theme("custom")

    def apply_theme(self, name):
        if name == "dark":
            bg = "#121212"; fg = "#DDDDDD"
        elif name == "sepia":
            bg = "#f4ecd8"; fg = "#5b4636"
        else:
            bg = "#ffffff"; fg = "#000000"

        self.content.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {bg};
                color: {fg};
                font-family: {self.current_font};
                font-size: {self.current_font_size}px;
            }}
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FB2Reader()
    window.show()
    sys.exit(app.exec())
