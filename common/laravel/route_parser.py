"""Laravel route and scheduler output parsers."""
from __future__ import annotations
import json
import re
from typing import Any

def parse_routes(raw: str) -> list[dict[str, Any]]:
    raw = raw.lstrip('\ufeff')
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as original_error:
        data = None
        # PHP startup warnings or package output can precede route:list's JSON.
        decoder = json.JSONDecoder()
        for match in re.finditer(r'(?m)^\s*\[', raw):
            try:
                candidate, _ = decoder.raw_decode(raw, match.start() + len(match.group()) - 1)
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, list):
                data = candidate
                break
        if data is None:
            raise ValueError('route:list did not return a valid JSON array') from original_error
    if not isinstance(data, list):
        raise ValueError('route:list must return a JSON array')
    routes = []
    for r in data:
        if not isinstance(r, dict):
            continue
        uri = str(r.get('uri', '/')).strip('/')
        routes.append({
            'method': str(r.get('method', '')),
            'uri': uri or '/',
            'name': str(r.get('name') or ''),
            'action': str(r.get('action') or ''),
            'middleware': ', '.join(r.get('middleware', [])) if isinstance(r.get('middleware'), list) else str(r.get('middleware') or ''),
        })
    return routes

def parse_schedule_list(raw: str) -> list[dict[str, str | None]]:
    """Parse the human-readable output from Laravel's schedule:list command."""
    ansi = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
    rows: list[dict[str, str | None]] = []
    for line in raw.splitlines():
        line = ansi.sub('', line).strip('\r')
        if not line.strip():
            continue
        due = re.search(r'(?:\.{3,}\s*|\s+)Next Due:\s*(.*?)\s*$', line, re.IGNORECASE)
        if not due:
            continue
        left = line[:due.start()].rstrip(' .\t')
        columns = re.match(r'^\s*(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s{2,}(.+?)\s*$', left)
        if not columns:
            continue
        expression = ' '.join(columns.group(i) for i in range(1, 6))
        command = columns.group(6).strip()
        if not command:
            continue
        if re.match(r'^Closure at:', command, re.IGNORECASE):
            test_name = None
        else:
            test_name = re.sub(r'^(?:.*?php(?:\.exe)?\s+)?artisan\s+', '', command, flags=re.IGNORECASE)
        rows.append({
            'expression': expression,
            'command': command,
            'next_due_date_human': due.group(1).strip(),
            'description': '',
            'test_name': test_name,
        })

    counts: dict[str, int] = {}
    for row in rows:
        name = row['test_name']
        if name:
            counts[name] = counts.get(name, 0) + 1
    for row in rows:
        name = row['test_name']
        if name and counts[name] > 1:
            row['test_name'] = None
    return rows

def group_route_segments(uri: str) -> list[str]:
    segments = [p for p in uri.strip('/').split('/') if p]
    return segments[:-1] if len(segments) > 1 else ['(root)']
