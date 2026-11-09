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


_METRIC_PLAIN = {
    "instantaneo": "lectura del momento",
    "twa_8h": "promedio de 8 horas",
    "stel_15min": "promedio de 15 minutos",
    "valor": "lectura del momento",
}


def limits_for_assistant(db: Session, gas: str | None = None) -> list[dict[str, Any]]:
    from app.shared.copy import number_es, status_word
    from app.shared.gas_catalog import canonicalize_gas_type, display_gas

    rows = db.query(repo.NormativeThreshold).order_by(
        repo.NormativeThreshold.gas_code.asc(),
        repo.NormativeThreshold.level.asc(),
    )
    if gas:
        rows = rows.filter(repo.NormativeThreshold.gas_code == canonicalize_gas_type(gas))
    items: list[dict[str, Any]] = []
    for row in rows.all():
        items.append(
            {
                "gas": display_gas(row.gas_code),
                "gas_code": row.gas_code,
                "nivel": status_word(row.level),
                "valor": float(row.value),
                "valor_texto": number_es(float(row.value)),
                "metrica": _METRIC_PLAIN.get(row.metric, row.metric),
                "articulo": row.article or row.source_reference,
                "verificado": bool(row.verified),
                "direccion": "por debajo" if row.direction == "below" else "por encima",
            }
        )
    return items[:200]
