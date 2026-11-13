"""Small, private, immutable-by-default artifact helpers."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


class TraceError(ValueError):
    pass


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise TraceError(f"Cannot read JSON {path}: {exc}") from exc


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental loss of prior analysis.
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
    except FileExistsError as exc:
        raise TraceError(f"Output exists; choose a new path: {path}") from exc


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def private_directory(path: Path) -> None:
    if path.exists():
        raise TraceError(f"Run directory exists; choose a new path: {path}")
    path.mkdir(parents=True, mode=0o700)
