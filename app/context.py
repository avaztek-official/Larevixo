"""Application-scoped services and cross-page event contracts."""
from PySide6.QtCore import QObject, Signal


class ApplicationContext(QObject):
    project_changed = Signal(str)
    projects_changed = Signal()
    service_state_changed = Signal(str, bool)
    console_message = Signal(str)
    icon_refresh_requested = Signal()
    navigate_requested = Signal(str)
    quick_action_requested = Signal(str)
    language_changed = Signal(str)
    theme_changed = Signal(str)

    def __init__(self, registry, runner, translator, parent=None):
        super().__init__(parent)
        self.registry = registry
        self.runner = runner
        self.translator = translator
        self.combo_configurator = None

    @property
    def current_project(self):
        return str(self.registry.data.get("current", "") or "")

    def select_project(self, path):
        path = str(path or "")
        if path == self.current_project:
            return False
        self.registry.data["current"] = path
        self.registry.save()
        self.project_changed.emit(path)
        return True

    def add_project(self, path):
        previous = self.current_project
        self.registry.add(path)
        self.projects_changed.emit()
        if previous != self.current_project:
            self.project_changed.emit(self.current_project)

    def remove_project(self, path):
        previous = self.current_project
        self.registry.remove(path)
        self.projects_changed.emit()
        if previous != self.current_project:
            self.project_changed.emit(self.current_project)
