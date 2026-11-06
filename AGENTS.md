# Larevixo Agent Guide

Larevixo is a Windows desktop application built with Python 3.12 and PySide6 for managing local Laravel projects. Preserve the existing product behavior, UI, English/Persian localization, and project safety checks when making changes.

## Architecture

```text
main.py                  Application entry point
app/                     Main window, navigation, dependency context, lifecycle
pages/                   Ten page widgets and page-specific behavior
common/                  Shared services, UI components, dialogs, and pure helpers
assets/, lang/           Runtime resources and translations
tests/                   Unit, architecture, regression, and GUI smoke coverage
```

- `main.py` starts the application and should stay thin.
- `app/application.py` owns the application shell, navigation, page registration, global coordination, and shutdown. Keep page business behavior in its page module.
- `app/context.py` defines `ApplicationContext`, the lightweight dependency bundle shared with pages.
- `pages/base.py` defines `BasePage` and common page helpers/lifecycle hooks. Each page owns its UI, local state, and handlers:
  - `overview/`: workspace summary and quick actions
  - `projects/`: project list, import, selection, and removal
  - `artisan/`: Artisan commands and generators
  - `migrations/`: migration status and confirmed operations
  - `environment/`: `.env` view, masking, editing, and save actions
  - `routes/`: route loading and display
  - `composer/`: package operations
  - `scheduler/`: schedule inspection and worker controls
  - `servers_logs/`: Laravel/Vite services and logs
  - `global_settings/`: global tool and application settings
- `common/` owns reusable behavior: `processes/` (`TaskRunner`, `Job`), `projects/` (`Registry`), `environment/` (`.env` parsing and atomic writes), `laravel/` (route/schedule parsing, versions, and packages), `validation/`, `localization/`, `resources/`, `ui/`, and `dialogs/`.
- `core.py` and `runner.py` are compatibility export modules. Put new implementations in `common/` or the responsible page, not in these facades.

## Change Guidelines

- Inject shared dependencies through `ApplicationContext`; coordinate cross-page changes through explicit Qt signals or context events. A page must not reach into another page's private widgets.
- Keep `App` focused on the shell and lifecycle. Avoid moving page operations into a new central controller or service locator.
- Give `QObject`, `QTimer`, and `QProcess` instances clear ownership and lifecycle. Rebuilding UI for language changes must not duplicate signal connections or timers, retain deleted widgets, or discard intended page/process state.
- Keep the selected-project change flow consistent across project-dependent pages. Keep resource lookup compatible with source runs and PyInstaller builds.
- Preserve confirmation and validation for destructive commands and keep sensitive environment values masked. Use temporary fixtures and mocks for tests; do not run destructive operations against a user's Laravel project or database.
- Prefer focused changes. Do not add dependencies or abstraction layers without a concrete need.

## Verification

- Static/import check: `python -m compileall -q main.py app pages common`
- Unit/regression suite: `python -m pytest -q tests`
- GUI smoke: `python tests/smoke_gui.py` (requires a Windows desktop session and PySide6)
- Windows packaging is defined in `build-windows.ps1`, `build-installer.ps1`, and `.github/workflows/windows.yml`.

Run the narrowest relevant check during iteration, then the full suite and GUI/build checks when the change warrants them. Report checks that could not run as unverified rather than passed.
