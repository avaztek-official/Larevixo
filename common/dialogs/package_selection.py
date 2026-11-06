"""Package search and version selection controls for the project wizard."""
from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLineEdit, QListWidget, QPushButton, QVBoxLayout, QWidget

from common.dialogs.package_search import PackageSearchDialog


class PackageSelectionWidget(QWidget):
    def __init__(self, registry: str, translator, parent=None):
        super().__init__(parent)
        self.registry = registry
        self.translator = translator
        self._translate = translator or (lambda text: text)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        fields = QHBoxLayout()
        self.package = QLineEdit()
        self.package.setPlaceholderText(self.tr('Package name'))
        self.version = QLineEdit()
        self.version.setPlaceholderText(self.tr('Version (blank for latest)'))
        self.search_button = QPushButton(self.tr('Search'))
        self.add_button = QPushButton(self.tr('Add package'))
        self.remove_button = QPushButton(self.tr('Remove selected'))
        fields.addWidget(self.package, 3)
        fields.addWidget(self.version, 2)
        fields.addWidget(self.search_button)
        fields.addWidget(self.add_button)
        layout.addLayout(fields)
        self.packages = QListWidget()
        self.packages.setMaximumHeight(90)
        layout.addWidget(self.packages)
        layout.addWidget(self.remove_button)

        self.search_button.clicked.connect(self.search)
        self.add_button.clicked.connect(self.add_package)
        self.remove_button.clicked.connect(self.remove_package)
        self.package.returnPressed.connect(self.add_package)

    def tr(self, text):
        return self._translate(text)

    def search(self):
        dialog = PackageSearchDialog(self.registry, self, self.translator)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.package_name:
            self.package.setText(dialog.package_name)
            self.version.setFocus()

    def add_package(self):
        name = self.package.text().strip()
        version = self.version.text().strip()
        if self.registry == 'Packagist':
            valid_name = re.fullmatch(r'[a-z0-9_.-]+/[a-z0-9_.-]+', name, re.I)
        else:
            valid_name = re.fullmatch(r'(?:@[a-z0-9_.-]+/)?[a-z0-9_.-]+', name, re.I)
        valid_version = not version or re.fullmatch(r'[a-zA-Z0-9@._+~^*|<>=,!:-]+', version)
        if not valid_name or not valid_version:
            from common.dialogs.messages import alert
            alert(self, 'Invalid package', 'Enter a valid package name and version constraint.', self.translator, True)
            return
        if any(self.packages.item(i).data(Qt.ItemDataRole.UserRole) == name for i in range(self.packages.count())):
            return
        self.packages.addItem(f'{name} · {version or self.tr("latest")}')
        row = self.packages.item(self.packages.count() - 1)
        row.setData(Qt.ItemDataRole.UserRole, name)
        row.setData(Qt.ItemDataRole.UserRole + 1, version)
        self.package.clear()
        self.version.clear()

    def remove_package(self):
        row = self.packages.currentRow()
        if row >= 0:
            self.packages.takeItem(row)

    def entries(self):
        return [
            (self.packages.item(i).data(Qt.ItemDataRole.UserRole),
             self.packages.item(i).data(Qt.ItemDataRole.UserRole + 1) or '')
            for i in range(self.packages.count())
        ]
