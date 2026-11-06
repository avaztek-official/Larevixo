"""Larevixo application entry point and backwards-compatible exports."""
import sys

from PySide6.QtWidgets import QApplication

from app.application import App
from common.dialogs.artisan import ArtisanDialog
from common.dialogs.create_project import CreateDialog
from common.resources.theme import DARK, LIGHT

__all__ = ["App", "ArtisanDialog", "CreateDialog", "DARK", "LIGHT", "main"]


def main():
    application = QApplication(sys.argv)
    window = App()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
