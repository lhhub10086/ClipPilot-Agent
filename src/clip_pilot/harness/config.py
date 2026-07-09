from __future__ import annotations

from pathlib import Path
from typing import Any


def load_config(path: str = "config.yaml") -> dict[str, Any]:
    try:
        import yaml

        return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except ImportError:
        return _minimal_yaml_load(Path(path).read_text(encoding="utf-8"))


def _minimal_yaml_load(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    current_parent: str | None = None
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.strip().startswith("#"):
            continue
        if not raw_line.startswith(" "):
            key, value = _split(raw_line)
            if value == "":
                root[key] = {}
                current_parent = key
            else:
                root[key] = _coerce(value)
                current_parent = None
        else:
            if current_parent is None:
                continue
            key, value = _split(raw_line.strip())
            root[current_parent][key] = _coerce(value)
    return root


def _split(line: str) -> tuple[str, str]:
    key, _, value = line.partition(":")
    return key.strip(), value.strip()


def _coerce(value: str) -> Any:
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value.strip('"').strip("'")

