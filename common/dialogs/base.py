"""Base class for dialogs that receive the application's translator."""
from PySide6.QtWidgets import QDialog

from common.dialogs.messages import alert as show_alert
from common.ui.widgets import btn as make_button, label as make_label
from common.localization.translator import Translator
from common.resources.paths import LANG_DIR


class LocalizedDialog(QDialog):
    def __init__(self, parent=None, translator=None):
        super().__init__(parent)
        self.translator = translator or Translator(LANG_DIR)

    def tr(self, text):
        return self.translator(text)

    def label(self, text, role="muted"):
        return make_label(text, self.translator, role)

    def btn(self, text, callback, kind="secondary", icon_name=None):
        return make_button(text, callback, self.translator, kind, icon_name)

    def alert(self, title, text, critical=False):
        return show_alert(self, title, text, self.translator, critical)
