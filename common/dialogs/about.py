"""About dialog with application and publisher information."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialogButtonBox, QHBoxLayout, QLabel, QVBoxLayout

from common.dialogs.base import LocalizedDialog
from common.resources.paths import LOGO
from common.resources.version import APP_VERSION


class AboutDialog(LocalizedDialog):
    def __init__(self, parent=None, translator=None):
        super().__init__(parent, translator)
        self.setWindowTitle(self.tr("About Larevixo"))
        self.setModal(True)
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(12)

        if LOGO.is_file():
            logo = QLabel()
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo.setPixmap(QPixmap(str(LOGO)).scaled(
                72, 72, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            layout.addWidget(logo)

        title = self.label("Larevixo", "pageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)
        layout.addWidget(self.label("Laravel Development Manager"))
        version = self.label("Version: {version}")
        version.setText(version.text().format(version=APP_VERSION))
        layout.addWidget(version)
        layout.addWidget(self.label("Publisher: AvazTek"))

        website_row = QHBoxLayout()
        website_row.setContentsMargins(0, 0, 0, 0)
        website_row.addWidget(self.label("Website:"))
        theme = getattr(getattr(parent, "store", None), "data", {}).get("theme")
        link_color = "#ff553d" if theme == "dark" else "#f53003"
        website = self.label(
            f'<a href="https://avaztek.ir/" style="color:{link_color};">https://avaztek.ir/</a>'
        )
        website.setTextFormat(Qt.TextFormat.RichText)
        website.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        website.setOpenExternalLinks(True)
        website_row.addWidget(website)
        website_row.addStretch()
        layout.addLayout(website_row)

        download_row = QHBoxLayout()
        download_row.setContentsMargins(0, 0, 0, 0)
        download_row.addWidget(self.label("Download:"))
        download = self.label(
            f'<a href="https://avaztek.ir/software/larevixo" style="color:{link_color};">'
            'https://avaztek.ir/software/larevixo</a>'
        )
        download.setTextFormat(Qt.TextFormat.RichText)
        download.setWordWrap(False)
        download.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        download.setOpenExternalLinks(True)
        download_row.addWidget(download)
        download_row.addStretch()
        layout.addLayout(download_row)

        actions = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        actions.button(QDialogButtonBox.StandardButton.Close).setText(self.tr("Close"))
        actions.rejected.connect(self.reject)
        layout.addWidget(actions)
