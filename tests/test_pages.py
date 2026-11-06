"""Page-level behavior checks using temporary Laravel fixtures and mocked commands."""
import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QPushButton
import pytest

from app.application import App
from common.dialogs.create_project import CreateDialog


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
        if path not in self.projects:
            self.projects.append(path)
        self.data["current"] = path

    def remove(self, path):
        path = str(Path(path).resolve())
        self.data["projects"] = [project for project in self.projects if project != path]
        if self.data["current"] == path:
            self.data["current"] = self.projects[0] if self.projects else ""


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def make_project(root, name="Laravel fixture"):
    project = root / name
    project.mkdir(parents=True)
    (project / "artisan").write_text("<?php // fixture\n", encoding="utf-8")
    (project / "composer.json").write_text(
        json.dumps({"require": {"laravel/framework": "^12.0", "vendor/unused": "^1.0"}}),
        encoding="utf-8",
    )
    (project / ".env").write_text("APP_NAME=Fixture\n", encoding="utf-8")
    return project.resolve()


def app_for(monkeypatch):
    monkeypatch.setattr("app.application.Registry", MemoryRegistry)
    return App()


def find_button(owner, label):
    matches = [button for button in owner.findChildren(QPushButton) if button.text() == label]
    assert len(matches) == 1, f"Expected one {label!r} button, found {len(matches)}"
    return matches[0]


def test_create_dialog_accepts_missing_parent_and_package_version_choices(qt_app, tmp_path):
    dialog = CreateDialog(None, '8.3.1')
    parent = tmp_path / 'new-parent' / 'nested'
    dialog.name.setText('new-app')
    dialog.parent_path.setText(str(parent))
    dialog.auth.setCurrentIndex(dialog.auth.findData('blade'))
    dialog.composer_packages.package.setText('spatie/laravel-permission')
    dialog.composer_packages.version.setText('^6.0')
    dialog.composer_packages.add_package()
    dialog.npm_packages.package.setText('@vitejs/plugin-vue')
    dialog.npm_packages.add_package()

    dialog.validate()
    try:
        assert dialog.result() == QDialog.DialogCode.Accepted
        assert not parent.exists(), 'The parent is created when project creation starts, after acceptance'
        settings = dialog.settings()
        assert settings[6:] == (
            'blade', [('spatie/laravel-permission', '^6.0')], [('@vitejs/plugin-vue', '')]
        )
    finally:
        dialog.close()


def test_project_table_selection_and_remove_only_forgets_path(qt_app, monkeypatch, tmp_path):
    window = app_for(monkeypatch)
    first = make_project(tmp_path, "Laravel first")
    second = make_project(tmp_path, "Laravel second")
    try:
        window.context.add_project(first)
        window.context.add_project(second)
        page = window.pages["Projects"]
        assert page.projects_table.rowCount() == 2

        page.projects_table.selectRow(0)
        page.select_project_table()
        assert window.current == str(first)

        page.projects_table.selectRow(1)
        monkeypatch.setattr(page, "confirm", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
        page.remove_project()
        assert window.store.projects == [str(first)]
        assert window.current == str(first)
        assert second.is_dir() and (second / "artisan").is_file()
    finally:
        window.close()


def test_overview_quick_actions_and_page_operations_enqueue_expected_jobs(qt_app, monkeypatch, tmp_path):
    window = app_for(monkeypatch)
    project = make_project(tmp_path)
    migration = project / "database" / "migrations" / "2026_01_01_000000_create_fixture.php"
    migration.parent.mkdir(parents=True)
    migration.write_text("<?php // fixture migration\n", encoding="utf-8")
    window.context.add_project(project)
    jobs = []
    monkeypatch.setattr(window.runner, "enqueue", jobs.append)
    try:
        overview = window.pages["Overview"]
        find_button(overview, "Migrate status").click()
        find_button(overview, "Refresh routes").click()
        find_button(overview, "Composer install").click()
        assert [job.label for job in jobs] == [
            "Migration status", "Load Laravel routes", "Composer install --no-interaction"
        ]
        assert jobs[0].args == ["artisan", "migrate:status", "--no-ansi"]
        assert jobs[1].args == ["artisan", "route:list", "--json"]
        queue_size = len(jobs)
        for _ in range(6):
            window.toggle_language()
        assert len(jobs) == queue_size, "Translating the shell must not enqueue the visible page's work again"

        jobs.clear()
        window.pages["Artisan"].artisan(["make:controller", "FixtureController"], "Create fixture controller")
        assert len(jobs) == 1 and jobs[0].args == ["artisan", "make:controller", "FixtureController"]

        jobs.clear()
        migrations = window.pages["Migrations"]
        monkeypatch.setattr(migrations, "confirm", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
        migrations.migration_op("migrate")
        migrations.run_migration("database/migrations/2026_01_01_000000_create_fixture.php")
        assert [job.args for job in jobs] == [
            ["artisan", "migrate", "--no-interaction"],
            ["artisan", "migrate", "--path=database/migrations/2026_01_01_000000_create_fixture.php", "--no-interaction", "--no-ansi"],
        ]

        jobs.clear()
        routes = window.pages["Routes"]
        routes.got_routes(json.dumps([{
            "uri": "admin/fixtures", "method": "GET", "name": "fixtures.index",
            "action": "FixtureController@index", "middleware": ["web", "auth"],
        }]))
        assert len(routes.routes) == 1
        assert routes.routes[0]["middleware"] == "web, auth"
        assert routes.routes_tree.topLevelItemCount() == 1
        assert routes.routes_tree.topLevelItem(0).text(0) == "admin/"
        window.switch("Routes")
        routes.route_filter.setText("fixtures.index")
        window.toggle_language()
        assert routes.route_filter.text() == "fixtures.index"
        assert routes.routes_tree.topLevelItemCount() == 1

        composer = window.pages["Composer"]
        composer.show_packages()
        assert composer.packages_table.rowCount() == 2
        composer.composer_simple(["install", "--no-interaction"])
        composer.packages_table.setCurrentCell(1, 0)
        monkeypatch.setattr(composer, "confirm", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
        composer.remove_package()
        assert [job.args for job in jobs] == [
            ["install", "--no-interaction"], ["remove", "vendor/unused", "--no-interaction"]
        ]
    finally:
        window.close()


def test_async_route_and_schedule_results_do_not_cross_projects(qt_app, monkeypatch, tmp_path):
    window = app_for(monkeypatch)
    first = make_project(tmp_path, "Laravel first")
    second = make_project(tmp_path, "Laravel second")
    window.context.add_project(first)
    jobs = []
    monkeypatch.setattr(window.runner, "enqueue", jobs.append)
    try:
        routes = window.pages["Routes"]
        scheduler = window.pages["Scheduler"]
        routes.fetch_routes()
        route_job = jobs[-1]
        scheduler.refresh_schedules()
        schedule_job = jobs[-1]
        assert route_job.cwd == str(first) and schedule_job.cwd == str(first)

        window.context.add_project(second)
        route_job.success('[{"method":"GET","uri":"old-project","name":"old.index"}]')
        schedule_job.success('[{"command":"php artisan old:task","expression":"* * * * *"}]')
        assert routes.routes == []
        assert scheduler.schedule_table.rowCount() == 0
    finally:
        window.close()


def test_migration_status_requests_remain_project_scoped(qt_app, monkeypatch, tmp_path):
    window = app_for(monkeypatch)
    first = make_project(tmp_path, "Laravel first")
    second = make_project(tmp_path, "Laravel second")
    window.context.add_project(first)
    jobs = []
    monkeypatch.setattr(window.runner, "enqueue", jobs.append)
    page = window.pages["Migrations"]
    try:
        page.migrate_status()
        first_job = jobs[-1]
        window.context.add_project(second)
        page.migrate_status()
        second_job = jobs[-1]
        assert first_job.cwd == str(first) and second_job.cwd == str(second)
        assert not page.migration_refresh_button.isEnabled()

        first_job.success("Ran 2026_01_01_000000_create_first")
        assert not page.migration_refresh_button.isEnabled(), "An old project's result must not clear the current request state"
        second_job.success("Ran 2026_01_01_000000_create_second")
        assert page.migration_refresh_button.isEnabled()
    finally:
        window.close()


def test_environment_page_reads_saves_and_backs_up_only_fixture(qt_app, monkeypatch, tmp_path):
    window = app_for(monkeypatch)
    project = make_project(tmp_path)
    env_file = project / ".env"
    original = b"\xef\xbb\xbf# preserved\r\nAPP_NAME=Fixture\r\nDB_PASSWORD=old-secret\r\n"
    env_file.write_bytes(original)
    backup_root = tmp_path / "local-app-data"
    monkeypatch.setenv("LOCALAPPDATA", str(backup_root))
    window.context.add_project(project)
    page = window.pages["Environment"]
    window.switch("Environment")
    alerts = []
    monkeypatch.setattr(page, "alert", lambda *args, **kwargs: alerts.append(args))
    try:
        assert page.active_env.startswith("\ufeff# preserved\r\n")
        assert page.env_table.rowCount() == 2
        assert page.env_table.item(1, 1).text() == "••••••••"
        assert page.env_table.item(1, 1).data(Qt.ItemDataRole.UserRole) == "old-secret"
        page.env_table.item(1, 1).setData(Qt.ItemDataRole.UserRole, "new secret")
        for _ in range(6):
            window.toggle_language()
            assert page.env_table.item(1, 1).data(Qt.ItemDataRole.UserRole) == "new secret"
        page.save_env()

        saved = env_file.read_bytes()
        assert saved.startswith(b"\xef\xbb\xbf# preserved\r\n")
        assert b'DB_PASSWORD="new secret"\r\n' in saved
        backups = list(backup_root.rglob("*.env.bak"))
        assert len(backups) == 1 and backups[0].read_bytes() == original
        assert backups[0].is_relative_to(backup_root) and not backups[0].is_relative_to(project)
        assert page.active_env == saved.decode("utf-8")
        assert alerts and alerts[-1][0] == "Saved"
    finally:
        window.close()


def test_servers_page_start_stop_and_tail_log_use_selected_fixture(qt_app, monkeypatch, tmp_path):
    window = app_for(monkeypatch)
    project = make_project(tmp_path)
    (project / "package.json").write_text('{"scripts":{"dev":"vite"}}', encoding="utf-8")
    logs = project / "storage" / "logs"
    logs.mkdir(parents=True)
    logfile = logs / "laravel.log"
    logfile.write_text("first log line\n", encoding="utf-8")
    window.context.add_project(project)
    page = window.pages["Servers & Logs"]
    starts, stops = [], []
    monkeypatch.setattr(window.runner, "service_start", lambda *args: starts.append(args))
    monkeypatch.setattr(window.runner, "service_stop", lambda *args: stops.append(args))
    try:
        page.php_port.setValue(8123)
        page.vite_port.setValue(5180)
        page.log_view.setPlainText("retained log line")
        window.switch("Servers & Logs")
        for _ in range(4):
            window.toggle_language()
        assert page.php_port.value() == 8123 and page.vite_port.value() == 5180
        assert page.log_view.toPlainText() == "retained log line"
        page.start_service("laravel")
        page.start_service("vite")
        assert starts == [
            (f"laravel|{project}", "php", ["artisan", "serve", "--host=127.0.0.1", "--port=8123"], str(project)),
            (f"vite|{project}", "npm", ["run", "dev", "--", "--host", "127.0.0.1", "--port", "5180"], str(project)),
        ]
        page.stop_service("laravel")
        page.stop_service("vite")
        assert stops == [(f"laravel|{project}",), (f"vite|{project}",)]

        page.tail_log()
        assert "first log line" in page.log_view.toPlainText()
        with logfile.open("a", encoding="utf-8") as stream:
            stream.write("second log line\n")
        page.tail_log()
        assert "second log line" in page.log_view.toPlainText()
    finally:
        window.close()


def test_global_settings_persist_tool_paths_and_queue_version_checks(qt_app, monkeypatch, tmp_path):
    window = app_for(monkeypatch)
    jobs = []
    monkeypatch.setattr(window.runner, "enqueue", jobs.append)
    page = window.pages["Global & Settings"]
    monkeypatch.setattr(page, "alert", lambda *args, **kwargs: None)
    try:
        page.tool_edits["php"].setText(str(tmp_path / "php.exe"))
        page.tool_edits["composer"].setText("composer.phar")
        page.tool_edits["npm"].setText("npm.cmd")
        window.switch("Global & Settings")
        window.toggle_language()
        assert page.tool_edits["php"].text() == str(tmp_path / "php.exe")
        assert page.tool_edits["composer"].text() == "composer.phar"
        assert page.tool_edits["npm"].text() == "npm.cmd"
        page.check_versions()
        assert window.store.data["tools"] == {
            "php": str(tmp_path / "php.exe"), "composer": "composer.phar", "npm": "npm.cmd"
        }
        assert window.runner.tools is window.store.data["tools"]
        assert [(job.tool, job.args) for job in jobs] == [
            ("php", ["--version"]), ("composer", ["--version"]), ("npm", ["--version"])
        ]
    finally:
        window.close()
