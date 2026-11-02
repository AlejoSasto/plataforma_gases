from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_record(path: Path | str) -> dict[str, str]:
    p = Path(path)
    return {"name": p.name, "sha256": sha256_file(p)}


def already_loaded(source_files: list[Any] | None, sha256: str) -> bool:
    if not source_files:
        return False
    for item in source_files:
        if isinstance(item, dict) and item.get("sha256") == sha256:
            return True
    return False
