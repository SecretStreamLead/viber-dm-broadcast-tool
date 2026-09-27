"""Template engine — `{name}` style interpolation over flat var dicts."""

from __future__ import annotations

import re
from pathlib import Path

_TOKEN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class TemplateError(ValueError):
    pass


class TemplateEngine:
    """Loads .txt templates from a directory. Renders with strict missing-var checks."""

    def __init__(self, templates: dict[str, str]) -> None:
        self._templates = templates

    @classmethod
    def from_dir(cls, path: Path) -> TemplateEngine:
        if not path.exists():
            return cls({})
        out: dict[str, str] = {}
        for f in sorted(path.glob("*.txt")):
            out[f.stem] = f.read_text(encoding="utf-8").strip()
        return cls(out)

    def names(self) -> list[str]:
        return sorted(self._templates)

    def render(self, name: str, vars: dict[str, str]) -> str:
        if name not in self._templates:
            raise TemplateError(f"unknown template: {name!r}")
        body = self._templates[name]

        missing: list[str] = []

        def _sub(match: re.Match[str]) -> str:
            key = match.group(