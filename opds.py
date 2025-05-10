import os, json, zipfile
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QPushButton, QFileDialog,
    QMessageBox, QInputDialog, QWidget, QHBoxLayout
)
from PySide6.QtCore import Qt

def open_opds_dialog(parent: QWidget, on_book_downloaded):
    opds_file = os.path.join(os.getcwd(), "opds_catalogs.json")
    try:
        with open(opds_file, "r", encoding="utf-8") as f:
            catalogs = json.load(f)
    except Exception:
        catalogs = [("Flibusta", "https://flibusta.is/opds")]

    if isinstance(catalogs, dict):
        catalogs = list(catalogs.items())

    urls = [f"{name} - {url}" for name, url in catalogs] + ["<Enter custom URL>", "<Remove existing catalog>"]
    selected, ok = QInputDialog.getItem(parent, "Select OPDS Catalog", "Choose or enter OPDS URL:", urls, editable=False)
    if not ok:
        return

    if selected == "<Enter custom URL>":
        url, ok = QInputDialog.getText(parent, "Custom OPDS URL", "Enter OPDS feed URL:")
        if not ok or not url:
            return
        name, ok = QInputDialog.getText(parent, "Catalog Name", "Give this catalog a name:")
        if not ok or not name:
            return
        catalogs.append((name, url))
        try:
            with open(opds_file, "w", encoding="utf-8") as f:
                json.dump(catalogs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(parent, "Save Error", str(e))
        return

    elif selected == "<Remove existing catalog>":
        names = [name for name, _ in catalogs]
        name_to_remove, ok = QInputDialog.getItem(parent, "Remove Catalog", "Select catalog to remove:", names, editable=False)
        if ok and name_to_remove:
            catalogs = [entry for entry in catalogs if entry[0] != name_to_remove]
            try:
                with open(opds_file, "w", encoding="utf-8") as f:
                    json.dump(catalogs, f, ensure_ascii=False, indent=2)
                QMessageBox.information(parent, "Removed", f"Catalog '{name_to_remove}' removed.")
            except Exception as e:
                QMessageBox.warning(parent, "Error", str(e))
        return

    base_url = selected.split(" - ", 1)[1]
    try:
        response = requests.get(base_url)
        response.raise_for_status()
        tree = ET.fromstring(response.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}

        entries = tree.findall("atom:entry", ns)
        if not entries:
            QMessageBox.information(parent, "No Entries", "No entries found in catalog.")
            return

        subcatalogs = {}
        for entry in entries:
            title = entry.findtext("atom:title", namespaces=ns)
            link_el = entry.find("atom:link", ns)
            if title and link_el is not None:
                href = link_el.attrib.get("href")
                full_href = urljoin(base_url, href)
                subcatalogs[title] = full_href

        dialog = QDialog(parent)
        dialog.setWindowTitle("Select Subcatalog")
        layout = QVBoxLayout(dialog)
        list_widget = QListWidget()
        for title in subcatalogs:
            list_widget.addItem(title)
        layout.addWidget(list_widget)
        select_button = QPushButton("Select")
        layout.addWidget(select_button)

        def load_selected_subcatalog():
            selected_item = list_widget.currentItem()
            if not selected_item:
                return
            subcatalog_url = subcatalogs[selected_item.text()]
            load_books_from_feed(parent, subcatalog_url, on_book_downloaded)
            dialog.accept()

        select_button.clicked.connect(load_selected_subcatalog)
        dialog.exec()

    except Exception as e:
        QMessageBox.critical(parent, "OPDS Error", str(e))


def load_books_from_feed(parent: QWidget, url: str, on_book_downloaded):
    try:
        while url:
            response = requests.get(url)
            response.raise_for_status()
            tree = ET.fromstring(response.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}

            entries = tree.findall("atom:entry", ns)

            books = []
            subcatalogs = {}
            for entry in entries:
                title = entry.findtext("atom:title", namespaces=ns)
                fb2_link = next((l for l in entry.findall("atom:link", ns) if 'fb2' in l.attrib.get('type', '')), None)
                nav_link = entry.find("atom:link", ns)
                if fb2_link and title:
                    href = urljoin(url, fb2_link.attrib.get("href"))
                    books.append((title, href))
                elif nav_link is not None and title:
                    href = urljoin(url, nav_link.attrib.get("href"))
                    subcatalogs[title] = href

            if not books and subcatalogs:
                sub_dialog = QDialog(parent)
                sub_dialog.setWindowTitle("Select Subcatalog")
                layout = QVBoxLayout(sub_dialog)
                list_widget = QListWidget()
                for title in subcatalogs:
                    list_widget.addItem(title)
                layout.addWidget(list_widget)
                open_button = QPushButton("Open")
                layout.addWidget(open_button)

                def open_selected():
                    item = list_widget.currentItem()
                    if not item:
                        return
                    sub_url = subcatalogs[item.text()]
                    sub_dialog.accept()
                    load_books_from_feed(parent, sub_url, on_book_downloaded)

                open_button.clicked.connect(open_selected)
                sub_dialog.exec()
                return

            if not books:
                QMessageBox.information(parent, "No Books", "No books or subcatalogs found.")
                return

            dialog = QDialog(parent)
            dialog.setWindowTitle("Select Book")
            layout = QVBoxLayout(dialog)
            list_widget = QListWidget()
            book_map = {title: href for title, href in books}
            for title in book_map:
                list_widget.addItem(title)
            layout.addWidget(list_widget)

            button_layout = QHBoxLayout()
            download_button = QPushButton("Download")
            next_button = QPushButton("Next Page")
            cancel_button = QPushButton("Close")
            button_layout.addWidget(download_button)
            button_layout.addWidget(next_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            def download_selected():
                selected = list_widget.currentItem()
                if not selected:
                    return
                href = book_map[selected.text()]
                try:
                    file_path, _ = QFileDialog.getSaveFileName(parent, "Save Book As", f"{selected.text()}.fb2", "FB2 Files (*.fb2 *.fb2.zip)")
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
                                on_book_downloaded(fb2_path)
                                dialog.accept()
                                return
                        QMessageBox.warning(parent, "Error", "FB2 file not found in ZIP archive.")
                    else:
                        on_book_downloaded(file_path)
                        dialog.accept()
                except Exception as e:
                    QMessageBox.warning(parent, "Download Error", str(e))

            def next_page():
                nonlocal url
                next_link = tree.find("atom:link[@rel='next']", ns)
                if next_link is not None:
                    url = urljoin(url, next_link.attrib.get("href"))
                    dialog.accept()
                else:
                    QMessageBox.information(parent, "End", "No more pages.")

            download_button.clicked.connect(download_selected)
            next_button.clicked.connect(next_page)
            cancel_button.clicked.connect(dialog.reject)

            result = dialog.exec()
            if result == 0:
                break

    except Exception as e:
        QMessageBox.critical(parent, "Feed Error", str(e))
