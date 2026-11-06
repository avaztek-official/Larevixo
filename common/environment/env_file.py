"""Lossless .env parsing, updates, and atomic writes."""
from __future__ import annotations
import os
import re
import tempfile
from pathlib import Path

ENV_KEY = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

def parse_env(text: str) -> list[tuple[str, str, int]]:
    """Return keys, unquoted values, and their line indices. Keep untouched lines on write."""
    result = []
    for i, line in enumerate(text.splitlines()):
        line = line.removeprefix('\ufeff')
        m = re.match(r'^\s*(?:export\s+)?([A-Za-z_][\w]*)\s*=\s*(.*)$', line)
        if not m:
            continue
        raw = m.group(2).strip()
        if len(raw) >= 2 and raw[0] in ('"', "'") and raw[-1] == raw[0]:
            raw = raw[1:-1]
            if line.strip().find('="') >= 0:
                raw = raw.replace('\\"', '"').replace('\\\\', '\\')
        else:
            raw = re.split(r'\s+#', raw, maxsplit=1)[0]
        result.append((m.group(1), raw, i))
    return result

def quote_env(value: str) -> str:
    if '\n' in value or '\r' in value or '\x00' in value:
        raise ValueError('Environment values must be single-line.')
    if re.search(r'[\s#"\'\\]', value) or value == '':
        # Laravel dotenv accepts double quoted escaped backslashes and quotes
        return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return value

def update_env(text: str, pairs: list[tuple[str, str]]) -> str:
    bom = text.startswith('\ufeff')
    if bom:
        text = text[1:]
    seen = set()
    updates = {}
    for key, value in pairs:
        if not ENV_KEY.fullmatch(key) or key in seen:
            raise ValueError(f'Invalid or duplicate .env key: {key}')
        seen.add(key)
        updates[key] = value
    endings = '\r\n' if '\r\n' in text else '\n'
    original = text.splitlines()
    present = set()
    for i, line in enumerate(original):
        m = re.match(r'^(\s*(?:export\s+)?)([A-Za-z_]\w*)(\s*=).*$', line)
        if m and m.group(2) in updates:
            key = m.group(2)
            if key not in present:
                original[i] = f'{m.group(1)}{key}{m.group(3)}{quote_env(updates[key])}'
            else:
                original[i] = '# duplicate key removed by Larevixo: ' + line
            present.add(key)
    for key, value in pairs:
        if key not in present:
            original.append(f'{key}={quote_env(value)}')
    # Keys explicitly deleted by the GUI are removed; retain comments and non-key lines.
    result = []
    for line in original:
        m = re.match(r'^\s*(?:export\s+)?([A-Za-z_]\w*)\s*=', line)
        if m and m.group(1) not in updates:
            continue
        result.append(line)
    return ('\ufeff' if bom else '') + endings.join(result) + (endings if result else '')

def read_env_file(path: str | Path) -> str:
    """Read a UTF-8 .env without normalizing line endings or discarding its BOM."""
    data = Path(path).read_bytes()
    bom = data.startswith(b'\xef\xbb\xbf')
    text = data[3:] if bom else data
    return ('\ufeff' if bom else '') + text.decode('utf-8')

def atomic_write_env(path: str | Path, text: str, mode: int | None = None) -> None:
    """Replace a .env through a unique same-directory temporary file."""
    target = Path(path)
    fd, temp_name = tempfile.mkstemp(prefix=f'.{target.name}.larevixo-', suffix='.tmp', dir=target.parent)
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        if mode is not None:
            os.chmod(temp, mode)
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)
