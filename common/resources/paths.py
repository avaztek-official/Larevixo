"""Resolve bundled and source-tree resources from one stable location."""
from pathlib import Path
import sys

BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
ASSETS_DIR = BASE / "assets"
LOGO = ASSETS_DIR / "logo.png"
ICON = ASSETS_DIR / "larevixo.ico"
LANG_DIR = BASE / "lang"
