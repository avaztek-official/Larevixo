"""Small asynchronous package-name search for Packagist and npm."""
from __future__ import annotations

import json
from urllib.parse import quote

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QComboBox, QDialogButtonBox, QFormLayout, QLineEdit, QVBoxLayout

from common.dialogs.base import LocalizedDialog


class PackageSearchDialog(LocalizedDialog):
    def __init__(self, registry: str, parent=None, translator=None):
        super().__init__(parent, translator)
        self.registry = registry
        self.package_name = ''
        self.setWindowTitle(self.tr('Search {registry}').format(registry=registry))
        self.resize(610, 250)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText(self.tr('Package name or keyword'))
        self.results = QComboBox()
        form.addRow(self.tr('Search'), self.query)
        form.addRow(self.tr('Results'), self.results)
        layout.addLayout(form)

        self.search_button = self.btn('Search online', self.search, 'secondary')
        self.query.returnPressed.connect(self.search)
        layout.addWidget(self.search_button)
        self.actions = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        self.actions.button(QDialogButtonBox.StandardButton.Ok).setText(self.tr('Select package'))
        self.actions.button(QDialogButtonBox.StandardButton.Cancel).setText(self.tr('Cancel'))
        self.actions.accepted.connect(self.accept_selection)
        self.actions.rejected.connect(self.reject)
        layout.addWidget(self.actions)

        self.network = QNetworkAccessManager(self)
        self.reply = None
        self.timeout = QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.setInterval(20000)
        self.timeout.timeout.connect(self._abort_request)

    def search(self):
        query = self.query.text().strip()
        if not query:
            return
        if self.reply is not None:
            self.reply.abort()
        if self.registry == 'Packagist':
            url = QUrl(f'https://packagist.org/search.json?q={quote(query)}&type=library')
        else:
            url = QUrl(f'https://registry.npmjs.org/-/v1/search?text={quote(query)}&size=20')
        request = QNetworkRequest(url)
        request.setRawHeader(b'User-Agent', b'Larevixo')
        self.reply = self.network.get(request)
        self.reply.finished.connect(lambda reply=self.reply: self._search_finished(reply))
        self.timeout.start()
        self.search_button.setEnabled(False)

    def _abort_request(self):
        if self.reply is not None:
            self.reply.abort()

    def _search_finished(self, reply):
        if self.reply is not reply:
            reply.deleteLater()
            return
        self.reply = None
        self.timeout.stop()
        self.search_button.setEnabled(True)
        if reply is None:
            return
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                raise ValueError(reply.errorString())
            payload = json.loads(bytes(reply.readAll()).decode('utf-8'))
            if self.registry == 'Packagist':
                items = payload.get('results', [])
                rows = [(item.get('name', ''), item.get('description', '')) for item in items]
            else:
                items = payload.get('objects', [])
                rows = [
                    (item.get('package', {}).get('name', ''), item.get('package', {}).get('description', ''))
                    for item in items
                ]
            self.results.clear()
            for name, description in rows:
                if name:
                    self.results.addItem(name, name)
                    self.results.setItemData(self.results.count() - 1, description, Qt.ItemDataRole.ToolTipRole)
            if not self.results.count():
                self.alert('No packages found', 'No packages matched this search.', True)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.alert('Package search failed', str(exc), True)
        finally:
            reply.deleteLater()

    def accept_selection(self):
        self.package_name = self.results.currentData() or ''
        if self.package_name:
            self.accept()
