"""Project registry and Laravel project discovery."""
from __future__ import annotations
import json
import os
from pathlib import Path

APP_NAME = 'Larevixo'

def config_location() -> Path:
    if os.name == 'nt':
        base = Path(os.environ.get('APPDATA') or str(Path.home() / 'AppData/Roaming'))
    else:
        base = Path(os.environ.get('XDG_CONFIG_HOME') or str(Path.home() / '.config'))
    return base / APP_NAME / 'settings.json'

def project_valid(path: str | Path) -> bool:
    p = Path(path)
    return p.is_dir() and (p / 'artisan').is_file() and (p / 'composer.json').is_file()

def laravel_version(path: str | Path) -> str:
    """Read installed version from composer.lock; no CLI process and no network."""
    p = Path(path)
    try:
        lock = json.loads((p / 'composer.lock').read_text(encoding='utf-8'))
        for pkg in lock.get('packages', []) + lock.get('packages-dev', []):
            if pkg.get('name') == 'laravel/framework':
                return pkg.get('version', '?').lstrip('v')
        conf = json.loads((p / 'composer.json').read_text(encoding='utf-8'))
        return conf.get('require', {}).get('laravel/framework', 'Not installed')
    except (OSError, ValueError, TypeError):
        return 'Unknown'

class Registry:
    def __init__(self, filename: Path | None = None):
        self.filename = filename or config_location()
        self.data = {'theme': 'dark', 'language': 'en', 'projects': [], 'current': '', 'tools': {
            'php': 'php', 'composer': 'composer', 'npm': 'npm'}}
        try:
            supplied = json.loads(self.filename.read_text(encoding='utf-8'))
            if isinstance(supplied, dict):
                self.data.update({k: supplied[k] for k in ('theme', 'language', 'projects', 'current', 'tools') if k in supplied})
            if self.data.get('language') not in ('en', 'fa'):
                self.data['language'] = 'en'
            if not isinstance(self.data['projects'], list):
                self.data['projects'] = []
            if not isinstance(self.data['tools'], dict):
                self.data['tools'] = {}
        except (OSError, ValueError, TypeError):
            pass

    def save(self):
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.filename.with_name(self.filename.name + '.tmp')
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding='utf-8')
        os.replace(tmp, self.filename)

    @property
    def projects(self) -> list[str]:
        return self.data['projects']

    def add(self, path: str | Path):
        p = str(Path(path).resolve())
        if not project_valid(p):
            raise ValueError('This folder must contain artisan and composer.json.')
        if not any(os.path.normcase(v) == os.path.normcase(p) for v in self.projects):
            self.projects.append(p)
        self.data['current'] = p
        self.save()

    def remove(self, path: str):
        self.data['projects'] = [p for p in self.projects if p != path]
        if self.data['current'] == path:
            self.data['current'] = self.projects[0] if self.projects else ''
        self.save()
