"""Reusable button reflecting the runner state for one local service."""
from PySide6.QtCore import QProcess, QSize, Qt
from PySide6.QtWidgets import QPushButton


class ServiceToggleButton(QPushButton):
    def __init__(self, service, context, translate, parent=None):
        super().__init__(translate("Start " + service.capitalize()), parent)
        self.service = service
        self.context = context
        self.translate = translate
        self.setProperty("kind", "primary")
        self.setProperty("iconName", "play")
        self.setIconSize(QSize(16, 16))
        self.setFixedHeight(42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._toggle)
        context.service_state_changed.connect(self.refresh)
        context.project_changed.connect(self.refresh)
        self.refresh()

    def _toggle(self, _checked=False):
        self.context.quick_action_requested.emit("toggle_service:" + self.service)

    def refresh(self, *_):
        current = self.context.current_project
        process = self.context.runner.services.get(f"{self.service}|{current}") if current else None
        running = bool(process and process.state() != QProcess.ProcessState.NotRunning)
        self.setText(self.translate(("Stop " if running else "Start ") + self.service.capitalize()))
        self.setProperty("kind", "danger" if running else "primary")
        self.setProperty("iconName", "square" if running else "play")
        self.style().unpolish(self)
        self.style().polish(self)


def service_toggle_button(service, context, translate, parent=None):
    return ServiceToggleButton(service, context, translate, parent)
