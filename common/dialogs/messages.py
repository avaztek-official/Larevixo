"""Localized message boxes shared by pages and the application shell."""
from PySide6.QtWidgets import QMessageBox


def localize_message_buttons(box, translate):
    for standard, text in (
        (QMessageBox.StandardButton.Ok, "OK"),
        (QMessageBox.StandardButton.Cancel, "Cancel"),
        (QMessageBox.StandardButton.Yes, "Yes"),
        (QMessageBox.StandardButton.No, "No"),
    ):
        button = box.button(standard)
        if button:
            button.setText(translate(text))


def alert(parent, title, text, translate, critical=False):
    icon = QMessageBox.Icon.Critical if critical else QMessageBox.Icon.Information
    box = QMessageBox(icon, translate(title), translate(text), QMessageBox.StandardButton.Ok, parent)
    localize_message_buttons(box, translate)
    box.exec()


def confirm(parent, title, text, translate, warning=False, default=QMessageBox.StandardButton.No):
    if translate.language == "en":
        show = QMessageBox.warning if warning else QMessageBox.question
        return show(parent, translate(title), translate(text),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, default)
    icon = QMessageBox.Icon.Warning if warning else QMessageBox.Icon.Question
    box = QMessageBox(icon, translate(title), translate(text),
                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, parent)
    box.setDefaultButton(default)
    localize_message_buttons(box, translate)
    return box.exec()
