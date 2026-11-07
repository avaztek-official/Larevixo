# Privacy Policy

This policy describes the privacy behavior of the Larevixo Windows desktop application. It applies to the application itself; third-party services and tools that you choose to use have their own privacy policies.

## Information Larevixo stores locally

Larevixo does not require an account. It stores application preferences and project registration data on your computer, including the theme, language, paths to registered Laravel projects, the selected project, and configured PHP, Composer, and npm executable paths. On Windows, these settings are stored in `%APPDATA%\Larevixo\settings.json`.

When you view or edit a Laravel `.env` file, its contents are read and written locally. Larevixo creates timestamped `.env` backups under `%LOCALAPPDATA%\Larevixo\env-backups\`. These files can contain credentials and other secrets. They remain on your computer, are not removed by uninstalling Larevixo, and should be protected and deleted when no longer needed.

Larevixo also displays output from commands and local services that you start. Such output can contain project paths, configuration, or other sensitive information. Review it before sharing logs or screenshots.

## Network connections and third-party tools

The application does not include telemetry, advertising trackers, crash-report uploads, or an automatic update checker. Its package-search dialog sends the search text you enter to the selected public registry: Packagist (`packagist.org`) for Composer packages or npm (`registry.npmjs.org`) for npm packages. Those services may receive ordinary connection information such as your IP address under their own policies.

Larevixo can run PHP, Composer, npm, Laravel Artisan, and related commands that you choose. Operations such as creating a project, installing or updating dependencies, auditing packages, or running npm commands may connect to the configured repositories or other destinations selected by those tools and the project configuration. Their network requests, logs, scripts, and data handling are governed by the relevant tool, package, repository, and service providers. Review packages and project scripts before running them. Larevixo does not upload `.env` backups as part of its own application behavior.

The optional Laravel and Vite development servers are started as local processes. When you choose to open the Laravel server, Larevixo opens its loopback address (`127.0.0.1`) in your browser.

## How project data is used

Larevixo reads selected project files to show information and perform actions you request. For example, it reads `composer.json` and `composer.lock` for package and version details, reads Laravel routes and schedules by running Artisan commands, and reads local Laravel logs in the log viewer. It may modify project files or data when you explicitly run operations such as editing `.env`, managing Composer dependencies, creating a project, or running Artisan commands. Review the selected project and command before starting an operation; database or other effects of Laravel commands depend on that project.

## Retention and your choices

Settings, registered project paths, and `.env` backups remain on your device until you remove them. You can forget a registered project in the Projects page without deleting its folder. To remove saved preferences, delete `%APPDATA%\Larevixo\settings.json` while Larevixo is closed. To remove backups, delete the relevant files under `%LOCALAPPDATA%\Larevixo\env-backups\` after confirming you no longer need them. Uninstalling the application does not remove these user data folders.

Network use for package search and external tool operations can be avoided by not using those features or by restricting network access through your system or network controls. Any data already received by a third-party provider is subject to that provider's retention and privacy practices.

## Children and sale of personal information

Larevixo is a local developer tool and is not designed to collect personal information from children. The application does not sell personal information.

## Changes and contact

This policy may be revised when Larevixo's behavior changes. The current copy is published with the source code and official releases. For privacy questions, use the contact channel on [AvazTek's Larevixo page](https://avaztek.ir/software/larevixo).

Larevixo is distributed under the MIT License. This privacy policy does not modify that license.
