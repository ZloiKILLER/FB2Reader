import sys, os, base64, re, json, zipfile
import xml.etree.ElementTree as ET
import requests

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QFileDialog, QVBoxLayout,
    QTextBrowser, QProgressBar, QPushButton, QSizePolicy, QInputDialog,
    QListWidget, QDialog, QMessageBox
)
from PySide6.QtGui import QPixmap, QFontDatabase, QAction
from PySide6.QtCore import Qt

class FB2Reader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FB2Reader")
        self.resize(1280, 720)

        self.default_font_size = 16
        self.current_font_size = self.default_font_size
        self.current_font = "Georgia"

        # Меню
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")

        open_action = QAction("Open FB2...", self)
        open_action.triggered.connect(self.open_fb2)
        file_menu.addAction(open_action)

        open_opds_action = QAction("Open from OPDS...", self)
        open_opds_action.triggered.connect(self.open_opds_catalog)
        file_menu.addAction(open_opds_action)

        close_action = QAction("Close Book", self)
        close_action.triggered.connect(self.close_book)
        file_menu.addAction(close_action)

        settings_menu = menu_bar.addMenu("Settings")
        for theme, name in [("dark", "Dark Theme"), ("sepia", "Sepia Theme"), ("light", "Light Theme")]:
            action = QAction(name, self)
            action.triggered.connect(lambda checked, t=theme: self.apply_theme(t))
            settings_menu.addAction(action)

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

        self.view_menu = menu_bar.addMenu("View")
        self.view_menu.addAction(self.zoom_in_action)
        self.view_menu.addAction(self.zoom_out_action)
        self.view_menu.addAction(self.reset_zoom_action)
        self.view_menu.menuAction().setVisible(False)

        # Виджеты
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)

        self.content = QTextBrowser()
        self.content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.content.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.content.setOpenExternalLinks(True)
        self.content.setReadOnly(True)
        self.content.setFocusPolicy(Qt.StrongFocus)
        self.content.verticalScrollBar().valueChanged.connect(self.update_progress)

        self.splash_label = QLabel()
        self.splash_label.setAlignment(Qt.AlignCenter)
        self.original_pixmap = QPixmap("C:/Users/1/Downloads/FB2Reader/data/background.png")
        scaled_pixmap = self.original_pixmap.scaled(
            self.original_pixmap.width() // 4,
            self.original_pixmap.height() // 4,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.splash_label.setPixmap(scaled_pixmap)

        self.splash_text = QLabel("Welcome to FB2Reader")
        self.splash_text.setAlignment(Qt.AlignCenter)
        self.splash_text.setStyleSheet("font-size: 24px; color: #5b4636; background-color: #f4ecd8;")

        self.open_button = QPushButton("Open Book")
        self.open_button.setFixedWidth(200)
        self.open_button.setStyleSheet("font-size: 18px; padding: 8px; background-color: #e3d1b3; color: #5b4636;")
        self.open_button.clicked.connect(self.open_fb2)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.splash_container = QWidget()
        splash_layout = QVBoxLayout()
        splash_layout.setAlignment(Qt.AlignCenter)
        splash_layout.addWidget(self.splash_label)
        splash_layout.addWidget(self.splash_text)
        splash_layout.addWidget(self.open_button, alignment=Qt.AlignHCenter)
        self.splash_container.setLayout(splash_layout)

        layout.addWidget(self.splash_container, stretch=1)
        layout.addWidget(self.content, stretch=10)
        layout.addWidget(self.progress)

        container = QWidget()
        container.setLayout(layout)
        container.setStyleSheet("background-color: #f4ecd8;")
        self.setCentralWidget(container)

        self.content.hide()
        self.progress.hide()
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
            binaries = {b.attrib["id"]: b.text.strip() for b in root.findall("fb2:binary", ns) if b.text}

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
            self.splash_container.hide()
            self.content.show()
            self.progress.show()
            self.zoom_in_action.setVisible(True)
            self.zoom_out_action.setVisible(True)
            self.reset_zoom_action.setVisible(True)
            self.view_menu.menuAction().setVisible(True)
            self.update_progress()

        except Exception as e:
            self.content.setPlainText(f"Error loading FB2: {e}")

    def close_book(self):
        self.content.clear()
        self.content.hide()
        self.progress.hide()
        self.splash_container.show()
        self.view_menu.menuAction().setVisible(False)

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
        if name == "dark": bg, fg = "#121212", "#DDDDDD"
        elif name == "sepia": bg, fg = "#f4ecd8", "#5b4636"
        else: bg, fg = "#ffffff", "#000000"
        self.content.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {bg};
                color: {fg};
                font-family: {self.current_font};
                font-size: {self.current_font_size}px;
            }}
        """)

    def open_opds_catalog(self):
        try:
            from opds import open_opds_dialog
            open_opds_dialog(self, self.load_fb2)
        except ImportError:
            QMessageBox.warning(self, "OPDS", "opds.py module not found.")
        except Exception as e:
            QMessageBox.critical(self, "OPDS Error", str(e))

    def download_selected(self, list_widget, book_map, dialog):
        selected = list_widget.currentItem()
        if not selected:
            return
        href = book_map[selected.text()]
        try:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Book As", f"{selected.text()}.fb2", "FB2 Files (*.fb2 *.fb2.zip)")
            if not file_path:
                return
            book_data = requests.get(href).content
            with open(file_path, "wb") as f:
                f.write(book_data)

            if file_path.endswith(".zip"):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    extracted_files = zip_ref.namelist()
                    fb2_name = next((f for f in extracted_files if f.endswith(".fb2")), None)
                    if fb2_name:
                        zip_ref.extract(fb2_name, os.path.dirname(file_path))
                        fb2_path = os.path.join(os.path.dirname(file_path), fb2_name)
                        self.load_fb2(fb2_path)
                        dialog.accept()
                        return
                QMessageBox.warning(self, "Error", "FB2 file not found in ZIP archive.")
            else:
                self.load_fb2(file_path)
                dialog.accept()
        except Exception as e:
            QMessageBox.warning(self, "Download Error", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FB2Reader()
    window.show()
    sys.exit(app.exec())
