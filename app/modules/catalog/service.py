"""Servicios de catálogo."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.catalog import repository as repo
from app.modules.catalog.seed import seed_catalog
from app.shared.gas_catalog import apply_db_catalog


def hydrate_gas_catalog(db: Session) -> int:
    rows = repo.list_gas_types(db, active_only=False)
    apply_db_catalog(rows)
    return len(rows)


def ensure_catalog(db: Session) -> dict[str, int]:
    return seed_catalog(db, hydrate_cache=True)


def setting(db: Session, key: str, default: Any = None) -> Any:
    value = repo.get_setting(db, key)
    return default if value is None else value
