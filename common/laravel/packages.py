"""Laravel package and Artisan preset catalogues."""
from __future__ import annotations
import re

ARTISAN_PRESETS = {
    'make:controller': ['name', '--resource?', '--api?', '--invokable?', '--model=?'],
    'make:model': ['name', '--migration?', '--factory?', '--controller?', '--resource?'],
    'make:migration': ['name', '--create=?', '--table=?'],
    'make:seeder': ['name'],
    'make:factory': ['name', '--model=?'],
    'make:middleware': ['name'],
    'make:request': ['name'],
    'make:command': ['name'],
    'make:job': ['name'],
    'make:event': ['name'],
    'make:listener': ['name'],
    'make:policy': ['name', '--model=?'],
    'make:notification': ['name'],
    'make:mail': ['name'],
    'make:observer': ['name', '--model=?'],
    'make:test': ['name', '--unit?'],
    'make:component': ['name'],
    'make:resource': ['name'],
    'make:provider': ['name'],
}
