"""Crea `proyecto_gases_test` si no existe (Plan 20 F1)."""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.db_urls import assert_isolated, load_urls


def _admin_url(db_url: str) -> str:
    raw = db_url.replace("postgresql+psycopg://", "postgresql://", 1)
    parsed = urlparse(raw)
    return urlunparse(parsed._replace(path="/postgres"))


def ensure(db_url: str) -> str:
    import psycopg

    parsed = urlparse(db_url.replace("postgresql+psycopg://", "postgresql://", 1))
    name = (parsed.path or "/proyecto_gases_test").lstrip("/")
    admin = _admin_url(db_url)
    with psycopg.connect(admin, autocommit=True) as conn:
        row = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone()
        if row is None:
            conn.execute(f'CREATE DATABASE "{name}"')
            print(f"Creada base {name}")
        else:
            print(f"Base {name} ya existía")
    return name


def main() -> int:
    dev, test = load_urls()
    assert_isolated(dev, test)
    ensure(test)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
