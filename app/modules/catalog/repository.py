"""Acceso ORM al catálogo. Único lugar con SQL de este módulo."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.modules.catalog.models import AppSetting, GasType, NormativeThreshold


def list_gas_types(db: Session, *, active_only: bool = True) -> list[GasType]:
    q = db.query(GasType)
    if active_only:
        q = q.filter(GasType.is_active.is_(True))
    return q.order_by(GasType.priority.asc(), GasType.code.asc()).all()


def get_setting(db: Session, key: str) -> Optional[Any]:
    row = db.get(AppSetting, key)
    return None if row is None else row.value


def thresholds_for_gas(
    db: Session,
    gas_code: str,
    *,
    at: datetime | None = None,
) -> list[NormativeThreshold]:
    when = at or datetime.now(timezone.utc)
    rows = (
        db.query(NormativeThreshold)
        .filter(
            NormativeThreshold.gas_code == gas_code,
            NormativeThreshold.valid_from <= when,
        )
        .order_by(NormativeThreshold.level.asc(), NormativeThreshold.valid_from.desc())
        .all()
    )
    latest: dict[str, NormativeThreshold] = {}
    for row in rows:
        latest.setdefault(row.level, row)
    return list(latest.values())
