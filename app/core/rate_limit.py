"""Límite de intentos por IP y correo (Plan 19)."""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

_lock = Lock()
_hits: dict[str, list[float]] = defaultdict(list)


def too_many(key: str, *, limit: int = 10, window_s: int = 60) -> bool:
    now = time.monotonic()
    with _lock:
        bucket = [t for t in _hits[key] if now - t < window_s]
        if len(bucket) >= limit:
            _hits[key] = bucket
            return True
        bucket.append(now)
        _hits[key] = bucket
        return False


def reset(key: str | None = None) -> None:
    with _lock:
        if key is None:
            _hits.clear()
        else:
            _hits.pop(key, None)
