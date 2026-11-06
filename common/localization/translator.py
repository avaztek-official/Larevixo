"""Per-application translation state."""
from __future__ import annotations

import json
from pathlib import Path


class Translator:
    def __init__(self, language_dir: Path, language: str = "en"):
        self.language_dir = Path(language_dir)
        self.language = "en"
        self.messages: dict[str, str] = {}
        self.set_language(language)

    def set_language(self, language: str) -> None:
        self.language = language if language in ("en", "fa") else "en"
        try:
            self.messages = json.loads(
                (self.language_dir / f"{self.language}.json").read_text(encoding="utf-8")
            ).get("messages", {})
        except (OSError, ValueError, TypeError):
            self.messages = {}

    def __call__(self, text):
        return self.messages.get(text, text) if isinstance(text, str) else text
