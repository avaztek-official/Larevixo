<img width="1672" height="941" alt="Larevixo Neon Tech Showcase" src="https://github.com/user-attachments/assets/a62eb708-2b37-4c00-b03c-cbf9ba180495" />

# Larevixo

**Windows Laravel Development Manager · by AvazTek (unofficial)**

Larevixo is an independent, Qt-based Windows GUI for local Laravel projects. It is not affiliated with Laravel LLC. Its original logo is inspired by the geometric Laravel ecosystem and AvazTek's developer-tooling identity without copying an official trademark.

## Quick start · Windows

You need Windows 10/11, Python 3.12 and preinstalled PHP + Composer. For Vite features you additionally need Node.js and npm. Laravel 13 applications themselves need PHP 8.3+ according to the current skeleton; older Laravel projects may require other versions.

1. Unzip the project to any directory.
2. Double-click **`run.bat`**. It installs PySide6 and starts Larevixo.
3. Configure the PHP, Composer and npm executables under **Global & Settings** when they are not on your PATH.
4. Select **Import** to register an existing Laravel project, or **New project** to create one.

To build your own single-file Windows executable, open PowerShell in the unpacked folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
```

Your output will be `dist\Larevixo.exe`. Alternatively, push this folder as a GitHub repo and run the `Windows executable` GitHub Actions workflow; its artifact will contain the EXE. **EXE builds must run on Windows** and require downloading PySide6 Essentials and PyInstaller; the source archive is not a precompiled EXE.

To build the standard Windows installer, install Inno Setup 6.5.2 or newer separately and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\build-installer.ps1
```

The setup package is written to `dist\Larevixo-Setup-<version>.exe`. Setup supports per-user and all-users installation and leaves settings in `%APPDATA%\Larevixo` and `.env` backups in `%LOCALAPPDATA%\Larevixo` in place when uninstalled. It installs only Larevixo's executable and shortcuts; it does not modify Laravel project folders.

## What works

| Area | Capabilities |
|---|---|
| Projects | Import, select, forget (never delete), persist paths, read Laravel versions from `composer.lock` |
| Creation | Composer `create-project`, optional framework version, default package checkboxes checked, optional package selection, npm installation |
| Artisan | 18+ named generators with parameter dialogs; optimize:clear, tests, key generation with warning |
| Migrations | `migrate:status`, migrate, rollback, fresh (dangerous operations require typing the project folder name) |
| `.env` | Mask secrets; view/add/edit/delete keys; check for external file changes; automatic backup outside project |
| Routes | Fetch actual routes via `php artisan route:list --json`; hierarchical tree by URI path; search |
| Composer | Install, validate, audit, outdated, update, add/remove packages; inspect require and require-dev |
| Global tools | Install/update/list the global Laravel installer; check PHP, npm and Composer tool versions; Composer diagnostics |
| Servers | Start/stop Laravel's `artisan serve` and npm Vite server; show stdout/stderr; open site |
| Log viewer | Tail `storage/logs/laravel.log` or latest daily Laravel log |
| Appearance | Two themes; light #ffffff and #f53003, dark #171717 and #f61500; matching custom icon |

### Default packages

The checkbox list follows the selected official skeleton: Laravel 10 includes its `sanctum`, `sail`, and `laravel-ignition` defaults; Laravel 11 and 12 include their `pail` and `sail` defaults; Laravel 13 includes `pail` and `pao` but not `sail`. The lists were checked against the Laravel 10.3.3, 11.6.1, 12.12.2, and 13.11.0 skeleton manifests. `laravel/framework` is mandatory and is not removable. “Latest compatible” uses the configured PHP version to select the newest supported major; the wizard disables versions whose PHP minimum is not met. Larevixo still checks the generated `composer.json` and removes an unchecked default only if it is present. Extra packages selected in the wizard are added in later Composer operations. A failure in a later optional package installation does not automatically roll back the new project; consult the console and Composer configuration.

## Important operational notes

- All commands target **the selected local project**. The app is not intended for production database administration. Confirm the `.env` connection before running migrations.
- `.env` backup location on Windows: `%LOCALAPPDATA%\Larevixo\env-backups\<path-hash>\<timestamp>.env.bak`. Backups remain on disk; protect that directory, and delete backups only when no longer needed. The program never uploads these files.
- Routes are grouped by **URL path**, not the physical PHP route file or controller folder. This is intentional and works with framework-generated routes.
- PHP, Composer, Node/npm must be compatible with the target Laravel release, and `composer create-project` needs network access. Some Composer packages may run installation hooks; install only packages you trust.
- `npm run dev` requires a functional package.json, node_modules and Vite script. Run `npm install` first if needed.
- Composer paths on Windows can be `.bat`, `.cmd`, `.exe`, or a `.phar` file. Shell metacharacters are rejected for batch wrapper arguments to reduce injection risk.
- Logs are local and can contain user data. Never publish or share diagnostic log output without reviewing it.
- This is a **functional source-code release**; compilation and full integration testing with PHP/Composer/npm require a Windows machine. Unit tests for pure Python helpers pass. No Windows EXE is included in this source ZIP.

## Tests

```powershell
py -3 -m pip install pytest
py -3 -m pytest -q tests
```

## Code signing policy

Larevixo is preparing an application to the [SignPath Foundation free code-signing program](https://signpath.org/terms.html); the project has not been accepted, and the current [v1.0.0 release](https://github.com/avaztek-official/Larevixo/releases/tag/v1.0.0) does not have a SignPath Foundation signature. The intended program attribution is: “Free code signing provided by [SignPath.io](https://signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).”

For future releases, check a downloaded `.exe` in PowerShell with `Get-AuthenticodeSignature .\Larevixo.exe` and confirm `Status` is `Valid` and the signer matches the publisher stated for that release. See the [Code Signing Policy](CODE_SIGNING.md) for details and the [Privacy Policy](PRIVACY.md) for privacy information. A valid signature does not guarantee that Windows SmartScreen warnings will be absent.

## Project contents

```
main.py                         Lightweight application entry point
app/application.py              Main window, navigation, shared lifecycle
app/context.py                  Registry, runner, translator, page event contracts
pages/overview/page.py          Dashboard and quick actions
pages/projects/page.py          Import, selection, creation, and project list
pages/artisan/page.py           Artisan commands and generator actions
pages/migrations/page.py        Migration status and confirmed operations
pages/environment/page.py       .env editing, masking, backups, and save actions
pages/routes/page.py            Route list and tree UI
pages/composer/page.py          Dependency UI and Composer operations
pages/scheduler/page.py         Schedule list, tests, and worker controls
pages/servers_logs/page.py      Laravel/Vite services and log viewer
pages/global_settings/page.py   Global Composer and executable settings
common/                         Shared processes, project data, parsers, UI, dialogs, resources
core.py, runner.py              Compatibility exports for existing imports
assets/                         Icons, styles, and logo artwork
lang/                           English and Persian translations
tests/                          Unit, architecture, and GUI smoke checks
run.bat                         Install dependency and run from source
build-windows.ps1               Generate portable Windows executable
.github/workflows/              Windows executable build on GitHub Actions
```

## Referenced Laravel documentation

- https://laravel.com/docs/13.x/installation
- https://laravel.com/docs/13.x/starter-kits
- https://github.com/laravel/laravel/blob/13.x/composer.json

Larevixo v0.1.0 — Windows MVP. The name showed no obvious exact-match results in an initial web search; this does **not** establish trademark, domain, or universal search-engine uniqueness.
