"""Input validation for Laravel and Composer commands."""
from __future__ import annotations
import re
from common.laravel.packages import ARTISAN_PRESETS

IDENT = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]{1,63}$')

PACKAGE = re.compile(r'^[a-z0-9_.-]+/[a-z0-9_.-]+$')

ARTISAN_NAME = re.compile(r'^[a-z][a-z0-9:_-]*$')

def safe_artisan_args(command: str, name: str, options: dict[str, str | bool]) -> list[str]:
    if command not in ARTISAN_PRESETS:
        raise ValueError('Unknown command preset')
    if not name.strip() or len(name) > 180 or name.startswith('-') or '\x00' in name or '\n' in name:
        raise ValueError('Invalid class / migration name')
    # Laravel nested class identifiers: Folder/Name, or migration snake_case
    if not re.fullmatch(r'[A-Za-z_][\w\\/.-]*', name):
        raise ValueError('Only letters, digits, _, -, /, \\ and . are allowed')
    allowed = ARTISAN_PRESETS[command][1:]
    args = [command, name]
    for opt in allowed:
        key = opt.split('?')[0].split('=')[0]
        value = options.get(key)
        if value is True and opt.endswith('?'):
            args.append(key)
        elif opt.endswith('=?') and isinstance(value, str) and value.strip():
            if not re.fullmatch(r'[A-Za-z_][\w\\/.-]*', value.strip()):
                raise ValueError(f'Invalid {key} value')
            args.append(f'{key}={value.strip()}')
    return args

def redacted(text: str) -> str:
    """Mask typical secrets in command-log output; never log .env values."""
    secret_key = r'[A-Z0-9_]*(?:PASSWORD|SECRET|TOKEN|API_KEY|APP_KEY|PRIVATE_KEY|CREDENTIAL)[A-Z0-9_]*'
    text = re.sub(rf'(?i)\b({secret_key})(\s*[=:]\s*)(?:"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[^\r\n]*)', r'\1\2[REDACTED]', text)
    return text
