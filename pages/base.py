"""Common page wiring; each page keeps its own widgets and local state."""
from PySide6.QtWidgets import QVBoxLayout, QWidget
import weakref

from common.dialogs.messages import alert as show_alert, confirm as show_confirm
from common.ui.widgets import btn as make_button, card as make_card, editable_table as make_table
from common.ui.widgets import label as make_label, page as make_page
from common.projects.registry import project_valid


class BasePage(QWidget):
    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self.context.project_changed.connect(self.on_project_changed)
        self._active = False
        self._job_buttons = {}
        self.runner.job_state_changed.connect(self._on_job_state_changed)

    def mount(self, builder):
        self._page_builder = builder
        layout = self.layout()
        if layout is None:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        layout.addWidget(builder())

    def before_rebuild(self):
        """Release page-local references to widgets before translating the UI."""

    def after_rebuild(self):
        """Restore any page-local data that the rebuilt widgets display."""

    def rebuild(self):
        self.before_rebuild()
        self.mount(self._page_builder)

    @property
    def current(self):
        return self.context.current_project

    @property
    def store(self):
        return self.context.registry

    @property
    def runner(self):
        return self.context.runner

    def tr(self, text):
        return self.context.translator(text)

    def btn(self, text, callback, kind="secondary", icon_name=None):
        button = make_button(text, lambda checked=False: self._invoke_button(button, callback, checked), self.context.translator, kind, icon_name)
        button._task_jobs = {}
        button._task_kind = kind
        button._task_icon = icon_name or ""
        return button

    def _invoke_button(self, button, callback, checked=False):
        if button._task_jobs:
            for job in tuple(button._task_jobs.values()):
                self.runner.cancel_job(job)
            return
        previous = getattr(self.context, "action_button", None)
        self.context.action_button = button
        try:
            callback()
        finally:
            self.context.action_button = previous

    def enqueue_job(self, job):
        button = getattr(self.context, "action_button", None)
        if button is not None:
            if not button._task_jobs:
                button._task_original_text = button.text()
                button._task_original_kind = button.property("kind")
                button._task_original_icon = button.property("iconName")
            button._task_jobs[id(job)] = job
            self._job_buttons[id(job)] = (weakref.ref(button), job)
            self._refresh_task_button(button)
            self._wrap_job_callback(job, "success", button)
            self._wrap_job_callback(job, "failure", button)
        self.runner.enqueue(job)
        return job

    def _wrap_job_callback(self, job, name, button):
        callback = getattr(job, name)
        if callback is None:
            return

        def invoke(*args):
            previous = getattr(self.context, "action_button", None)
            self.context.action_button = button
            try:
                callback(*args)
            finally:
                self.context.action_button = previous

        setattr(job, name, invoke)

    def _on_job_state_changed(self, job, state):
        if state not in ("succeeded", "failed", "cancelled"):
            return
        entry = self._job_buttons.pop(id(job), None)
        if entry is None:
            return
        button = entry[0]()
        if button is None:
            return
        button._task_jobs.pop(id(job), None)
        self._refresh_task_button(button)

    def _refresh_task_button(self, button):
        running = bool(button._task_jobs)
        button.setText(self.tr("Stop") if running else button._task_original_text)
        button.setProperty("kind", "danger" if running else button._task_original_kind)
        button.setProperty("iconName", "square" if running else button._task_original_icon)
        button.style().unpolish(button)
        button.style().polish(button)
        self.refresh_icons()

    def label(self, text, role="muted"):
        return make_label(text, self.context.translator, role)

    def card(self, title, subtitle=None):
        return make_card(title, self.context.translator, subtitle)

    def page(self, title, subtitle):
        return make_page(title, subtitle, self.context.translator)

    def editable_table(self, columns):
        return make_table(columns, self.context.translator)

    def alert(self, title, text, critical=False):
        return show_alert(self, title, text, self.context.translator, critical)

    def confirm(self, title, text, warning=False, default=None):
        if default is None:
            return show_confirm(self, title, text, self.context.translator, warning)
        return show_confirm(self, title, text, self.context.translator, warning, default)

    def require_project(self):
        if not self.current or not project_valid(self.current):
            self.alert("No Laravel project", "Import or create a Laravel project first.", True)
            return None
        return self.current

    def append_console(self, text):
        self.context.console_message.emit(text)

    def refresh_icons(self):
        self.context.icon_refresh_requested.emit()

    def configure_searchable_combo(self, combo):
        if self.context.combo_configurator is None:
            raise RuntimeError("The application has not configured searchable combos yet.")
        return self.context.combo_configurator(combo)

    def on_project_changed(self, _path):
        """Clear or refresh page-local data when the selected project changes."""

    def on_activated(self):
        """Load project data when the page becomes visible."""

    def activate(self, refresh=True):
        self._active = True
        if refresh:
            self.on_activated()

    def deactivate(self):
        self._active = False
