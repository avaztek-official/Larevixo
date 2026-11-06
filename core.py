"""Compatibility exports for helpers now owned by :mod:`common`."""
import os  # Kept so existing monkeypatch targets such as ``core.os.replace`` work.
from common.projects.registry import APP_NAME, Registry, config_location, project_valid, laravel_version
from common.laravel.versions import (DEFAULT_PACKAGES_13, DEFAULT_PACKAGES_BY_MAJOR, LARAVEL_MIN_PHP, OPTIONAL_PACKAGES, php_version_tuple, latest_laravel_major, laravel_php_compatible, default_packages_for_major)
from common.laravel.packages import ARTISAN_PRESETS
from common.environment.env_file import ENV_KEY, parse_env, quote_env, update_env, read_env_file, atomic_write_env
from common.laravel.route_parser import parse_routes, parse_schedule_list, group_route_segments
from common.validation.commands import IDENT, PACKAGE, ARTISAN_NAME, safe_artisan_args, redacted

__all__ = [name for name in globals() if not name.startswith('_')]
