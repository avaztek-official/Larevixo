"""Laravel and PHP version compatibility helpers."""
from __future__ import annotations
import re

DEFAULT_PACKAGES_13 = [
    ('laravel/tinker', False, 'Interactive PHP REPL'),
    ('fakerphp/faker', True, 'Factories & fake test data'),
    ('laravel/pail', True, 'Log viewer'),
    ('laravel/pao', True, 'Laravel development companion'),
    ('laravel/pint', True, 'PHP code formatter'),
    ('mockery/mockery', True, 'Mocking for tests'),
    ('nunomaduro/collision', True, 'Console error output'),
    ('phpunit/phpunit', True, 'Unit and feature tests'),
]

DEFAULT_PACKAGES_BY_MAJOR = {
    '10': [
        ('laravel/sanctum', False, 'API authentication'),
        ('laravel/tinker', False, 'Interactive PHP REPL'),
        ('fakerphp/faker', True, 'Factories & fake test data'),
        ('laravel/pint', True, 'PHP code formatter'),
        ('laravel/sail', True, 'Docker development environment'),
        ('mockery/mockery', True, 'Mocking for tests'),
        ('nunomaduro/collision', True, 'Console error output'),
        ('phpunit/phpunit', True, 'Unit and feature tests'),
        ('spatie/laravel-ignition', True, 'Debug error pages'),
    ],
    '11': [
        ('laravel/tinker', False, 'Interactive PHP REPL'),
        ('fakerphp/faker', True, 'Factories & fake test data'),
        ('laravel/pail', True, 'Log viewer'),
        ('laravel/pint', True, 'PHP code formatter'),
        ('laravel/sail', True, 'Docker development environment'),
        ('mockery/mockery', True, 'Mocking for tests'),
        ('nunomaduro/collision', True, 'Console error output'),
        ('phpunit/phpunit', True, 'Unit and feature tests'),
    ],
    '12': [
        ('laravel/tinker', False, 'Interactive PHP REPL'),
        ('fakerphp/faker', True, 'Factories & fake test data'),
        ('laravel/pail', True, 'Log viewer'),
        ('laravel/pint', True, 'PHP code formatter'),
        ('laravel/sail', True, 'Docker development environment'),
        ('mockery/mockery', True, 'Mocking for tests'),
        ('nunomaduro/collision', True, 'Console error output'),
        ('phpunit/phpunit', True, 'Unit and feature tests'),
    ],
    '13': DEFAULT_PACKAGES_13,
}

LARAVEL_MIN_PHP = {'10': (8, 1), '11': (8, 2), '12': (8, 2), '13': (8, 3)}

OPTIONAL_PACKAGES = [
    ('laravel/sanctum', False, 'API authentication'),
    ('laravel/horizon', False, 'Redis queue dashboard'),
    ('laravel/telescope', True, 'Request debugging'),
    ('laravel/boost', True, 'AI development integration'),
    ('spatie/laravel-permission', False, 'Roles and permissions'),
]

def php_version_tuple(version: str) -> tuple[int, int]:
    match = re.match(r'^\s*(\d+)\.(\d+)', str(version))
    if not match:
        raise ValueError('Could not determine the PHP version.')
    return int(match.group(1)), int(match.group(2))

def latest_laravel_major(php_version: str) -> str:
    for major in ('13', '12', '10'):
        if laravel_php_compatible(php_version, major):
            return major
    raise ValueError('No supported Laravel skeleton matches this PHP version; Laravel 10–13 require PHP 8.1 through 8.x.')

def laravel_php_compatible(php_version: str, major: str) -> bool:
    current = php_version_tuple(php_version)
    return current[0] == 8 and current >= LARAVEL_MIN_PHP[major]

def default_packages_for_major(major: str) -> list[tuple[str, bool, str]]:
    try:
        return DEFAULT_PACKAGES_BY_MAJOR[major]
    except KeyError as exc:
        raise ValueError(f'Unsupported Laravel version: {major}') from exc
