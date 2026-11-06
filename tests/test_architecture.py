"""Regression checks for page ownership and application-scoped state."""
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import shiboken6
from PySide6.QtCore import QEvent, QProcess
from PySide6.QtGui import QCloseEvent
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QPushButton
import pytest

from app.application import App
from common.processes.task_runner import Job
from pages.artisan.page import ArtisanPage
from pages.composer.page import ComposerPage
from pages.environment.page import EnvironmentPage
from pages.global_settings.page import GlobalSettingsPage
from pages.migrations.page import MigrationsPage
from pages.overview.page import OverviewPage
from pages.projects.page import ProjectsPage
from pages.routes.page import RoutesPage
from pages.scheduler.page import SchedulerPage
from pages.servers_logs.page import ServersLogsPage


class MemoryRegistry:
    def __init__(self):
        self.data = {
            "theme": "dark",
            "language": "en",
            "projects": [],
            "current": "",
            "tools": {"php": "php", "composer": "composer", "npm": "npm"},
        }

    @property
    def projects(self):
        return self.data["projects"]

    def save(self):
        pass

    def add(self, path):
        path = str(Path(path).resolve())
        if path not in self.data["projects"]:
            self.data["projects"].append(path)
        self.data["current"] = path

    def remove(self, path):
        path = str(Path(path).resolve())
        self.data["projects"] = [project for project in self.projects if project != path]
        if self.data["current"] == path:
            self.data["current"] = self.projects[0] if self.projects else ""


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def make_project(root, name):
    project = root / name
    project.mkdir(parents=True)
    (project / "artisan").write_text("<?php // fixture\n", encoding="utf-8")
    (project / "composer.json").write_text(
        '{"require":{"laravel/framework":"^12.0"}}', encoding="utf-8"
    )
    (project / ".env").write_text("APP_NAME=Fixture\n", encoding="utf-8")
    return project.resolve()


def test_application_registers_independent_pages_and_preserves_shared_lifecycle(qt_app, monkeypatch, tmp_path):
    monkeypatch.setattr("app.application.Registry", MemoryRegistry)
    window = App()
    expected = {
        "Overview": OverviewPage,
        "Projects": ProjectsPage,
        "Artisan": ArtisanPage,
        "Migrations": MigrationsPage,
        "Environment": EnvironmentPage,
        "Routes": RoutesPage,
        "Composer": ComposerPage,
        "Scheduler": SchedulerPage,
        "Servers & Logs": ServersLogsPage,
        "Global & Settings": GlobalSettingsPage,
    }
    try:
        assert list(window.pages) == list(expected)
        assert all(isinstance(window.pages[name], page_type) for name, page_type in expected.items())
        assert len({id(page) for page in window.pages.values()}) == 10
        assert all(page.context is window.context for page in window.pages.values())
        assert not hasattr(window, "load_env")
        assert not hasattr(window, "show_schedules_json")

        project = make_project(tmp_path, "Selected project")
        window.context.add_project(project)
        changes = []
        window.context.project_changed.connect(changes.append)
        window.context.select_project("fixture-project")
        assert changes == ["fixture-project"]
        assert window.pages["Environment"].active_env == ""
        assert window.pages["Routes"].routes == []

        window.pages["Environment"].active_env = "APP_NAME=page-local"
        window.pages["Routes"].routes = [{
            "uri": "fixture", "method": "GET", "name": "fixture.index",
            "action": "FixtureController@index", "middleware": "web",
        }]
        assert window.pages["Environment"].active_env != str(window.pages["Routes"].routes)

        page_ids = {name: id(page) for name, page in window.pages.items()}
        timer = window.log_timer
        old_projects_table = window.pages["Projects"].projects_table
        for index in range(6):
            window.toggle_language()
            qt_app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            qt_app.processEvents()
            assert window.translator.language == ("fa" if index % 2 == 0 else "en")
            assert window.current == "fixture-project"
            assert window.stack.count() == 10
            assert window.log_timer is timer and timer.isActive()
            assert {name: id(page) for name, page in window.pages.items()} == page_ids
            assert window.pages["Environment"].active_env == "APP_NAME=page-local"
            assert window.pages["Routes"].routes == [{
                "uri": "fixture", "method": "GET", "name": "fixture.index",
                "action": "FixtureController@index", "middleware": "web",
            }]
            if index == 0:
                assert not shiboken6.isValid(old_projects_table), "Replaced page widgets must be deleted"

        assert window.translator.language == "en"
    finally:
        window.close()


def _toolbar_button(window, label):
    matches = [button for button in window.findChildren(QPushButton) if button.text() == label]
    assert len(matches) == 1, f"Expected one toolbar button labelled {label!r}, found {len(matches)}"
    return matches[0]


def test_toolbar_import_and_create_actions_reach_projects_page_once(qt_app, monkeypatch, tmp_path):
    monkeypatch.setattr("app.application.Registry", MemoryRegistry)
    window = App()
    project = make_project(tmp_path, "Imported Laravel")
    page = window.pages["Projects"]
    try:
        for _ in range(6):
            window.toggle_language()
            qt_app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            qt_app.processEvents()

        import_calls = []
        monkeypatch.setattr(
            "pages.projects.page.QFileDialog.getExistingDirectory",
            lambda *args: (import_calls.append(args), str(project))[1],
        )
        import_spy = QSignalSpy(window.context.quick_action_requested)
        _toolbar_button(window, "Import").click()
        assert import_spy.count() == 1
        assert len(import_calls) == 1
        assert window.store.projects == [str(project)]
        assert window.current == str(project)
        assert page.projects_table.rowCount() == 1

        dialog_calls = []

        create_base = tmp_path / "not-created-yet" / "nested"

        class AcceptedCreateDialog:
            def __init__(self, *args):
                dialog_calls.append(args)

            def exec(self):
                return QDialog.DialogCode.Accepted

            def settings(self):
                return "created-app", create_base, "12", [], [], False

            def selected_major(self):
                return "12"

        monkeypatch.setattr("pages.projects.page.CreateDialog", AcceptedCreateDialog)
        jobs = []
        monkeypatch.setattr(page, "enqueue_job", jobs.append)
        create_spy = QSignalSpy(window.context.quick_action_requested)
        _toolbar_button(window, "New project").click()
        assert create_spy.count() == 1
        assert len(dialog_calls) == 0
        assert jobs[0].label == "Check PHP version"
        jobs[0].success("LAREVIXO_PHP_VERSION=8.3.1")
        assert len(dialog_calls) == 1
        assert create_base.is_dir(), "Missing parent folders should be created automatically"
        assert len(jobs) == 2
        assert jobs[0].args == [
            "-r", 'echo "LAREVIXO_PHP_VERSION=" . PHP_VERSION;'
        ]
        assert jobs[1].args == [
            "create-project", "laravel/laravel", str(create_base / "created-app"), "^12.0", "--no-interaction"
        ]
    finally:
        window.close()


def test_project_creation_queues_auth_and_selected_registry_packages(qt_app, monkeypatch, tmp_path):
    monkeypatch.setattr("app.application.Registry", MemoryRegistry)
    window = App()
    page = window.pages["Projects"]
    project = make_project(tmp_path, "auth-and-packages")

    class AcceptedCreateDialog:
        def __init__(self, *args):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def settings(self):
            return (
                project.name, tmp_path, "12", [], [], False,
                "blade", [("spatie/laravel-permission", "^6.0")],
                [("@vitejs/plugin-vue", "")],
            )

        def selected_major(self):
            return "12"

    monkeypatch.setattr("pages.projects.page.CreateDialog", AcceptedCreateDialog)
    jobs = []
    monkeypatch.setattr(page, "enqueue_job", jobs.append)
    try:
        page.show_create_project_dialog("8.3.1")
        assert len(jobs) == 1 and jobs[0].tool == "composer"
        jobs[0].success("")
        assert [job.tool for job in jobs[1:]] == ["composer", "composer", "npm"]
        assert jobs[1].args == ["require", "spatie/laravel-permission:^6.0", "--no-interaction"]
        assert jobs[2].args == ["require", "laravel/breeze", "--dev", "--no-interaction"]
        assert jobs[3].args == ["install", "--ignore-scripts", "@vitejs/plugin-vue"]
        jobs[2].success("")
        assert jobs[4].tool == "php"
        assert jobs[4].args == ["artisan", "breeze:install", "blade", "--no-interaction"]
    finally:
        window.close()


def test_active_services_survive_project_switch_and_rebuild_once(qt_app, monkeypatch, tmp_path):
    monkeypatch.setattr("app.application.Registry", MemoryRegistry)
    window = App()
    project_a = make_project(tmp_path, "Laravel A")
    project_b = make_project(tmp_path, "Laravel B")

    class RunningService:
        def state(self):
            return QProcess.ProcessState.Running

    key = f"laravel|{project_a}"
    service = RunningService()
    window.runner.services[key] = service
    page = window.pages["Servers & Logs"]
    stop_calls = []
    monkeypatch.setattr(window.runner, "service_stop", stop_calls.append)
    try:
        window.context.add_project(project_a)
        window.runner.running_changed.emit(key, True)
        assert page.service_buttons["laravel"][0].text() == window.tr("Stop Laravel")

        window.context.add_project(project_b)
        assert window.runner.services[key] is service
        assert page.service_buttons["laravel"][0].text() == window.tr("Start Laravel")
        assert project_a.name in page.service_status.text()

        window.context.select_project(str(project_a))
        window.switch("Servers & Logs")
        for _ in range(6):
            window.toggle_language()
            qt_app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            qt_app.processEvents()

        assert window.pages["Servers & Logs"] is page
        assert window.runner.services[key] is service
        assert project_a.name in page.service_status.text()
        assert page.service_buttons["laravel"][0].text() == window.tr("Stop Laravel")
        page.service_buttons["laravel"][0].click()
        assert stop_calls == [key], "One service click must dispatch one stop operation after repeated rebuilds"
    finally:
        window.runner.services.clear()
        window.close()


def test_close_prompt_handles_active_runner_services(qt_app, monkeypatch):
    monkeypatch.setattr("app.application.Registry", MemoryRegistry)
    window = App()
    window.runner.services["fixture-service"] = object()
    stop_calls = []
    monkeypatch.setattr(window.runner, "stop_all", lambda: stop_calls.append(True))
    try:
        monkeypatch.setattr(window, "confirm", lambda *args: QMessageBox.StandardButton.No)
        canceled = QCloseEvent()
        window.closeEvent(canceled)
        assert not canceled.isAccepted()
        assert stop_calls == []

        monkeypatch.setattr(window, "confirm", lambda *args: QMessageBox.StandardButton.Yes)
        accepted = QCloseEvent()
        window.closeEvent(accepted)
        assert accepted.isAccepted()
        assert stop_calls == [True]
    finally:
        window.runner.services.clear()
        window.close()


def test_active_qprocess_and_completion_survive_language_rebuilds(qt_app, monkeypatch, tmp_path):
    monkeypatch.setattr("app.application.Registry", MemoryRegistry)
    window = App()
    window.runner.tools["python"] = sys.executable
    completed = []
    job = Job(
        "Lifecycle fixture",
        "python",
        ["-c", "import time; time.sleep(60)"],
        str(tmp_path),
        failure=completed.append,
    )
    timer = window.log_timer
    try:
        window.runner.enqueue(job)
        process = window.runner.active
        assert process is not None and process.parent() is window.runner
        deadline = time.monotonic() + 3
        while process.state() != QProcess.ProcessState.Running and time.monotonic() < deadline:
            QTest.qWait(10)
        assert process.state() == QProcess.ProcessState.Running

        page_ids = {name: id(page) for name, page in window.pages.items()}
        for _ in range(4):
            window.toggle_language()
            qt_app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            qt_app.processEvents()
            assert window.runner.active is process
            assert window.runner.active_job is job
            assert process.parent() is window.runner
            assert window.log_timer is timer and timer.isActive()
            assert {name: id(page) for name, page in window.pages.items()} == page_ids

        process.kill()
        deadline = time.monotonic() + 5
        while window.runner.active is not None and time.monotonic() < deadline:
            QTest.qWait(20)
        assert len(completed) == 1
        assert window.runner.active is None
    finally:
        if window.runner.active is not None or window.runner.queue:
            if window.runner.active is not None:
                window.runner.active.kill()
            deadline = time.monotonic() + 5
            while window.runner.active is not None and time.monotonic() < deadline:
                QTest.qWait(20)
        for entry in list(window.operation_toasts):
            window.dismiss_operation_toast(entry)
        window.close()
