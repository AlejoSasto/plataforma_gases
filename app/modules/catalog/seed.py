"""Semillas idempotentes de catálogo (Plan 16)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.modules.roles_permissions import models as _roles_models  # noqa: F401
from app.modules.users import models as _users_models  # noqa: F401
from app.modules.catalog.models import AppSetting, GasType, NormativeThreshold
from app.shared.gas_catalog import apply_db_catalog
from ml_core.domain.thresholds import MAX_RATE_PER_MIN, PHYSICAL_MAX, THRESHOLD_SEED, seed_key

GAS_TYPE_SEED: tuple[dict[str, Any], ...] = (
    {
        "code": "CH4",
        "display_name": "Metano",
        "plain_description": "Gas inflamable que se libera del carbón.",
        "canonical_unit": "%vol",
        "lel_percent_vol": 5.0,
        "physical_max": PHYSICAL_MAX["CH4"],
        "max_rate_per_min": MAX_RATE_PER_MIN["CH4"],
        "priority": 1,
        "is_active": True,
    },
    {
        "code": "CO",
        "display_name": "Monóxido de carbono",
        "plain_description": "Gas tóxico producto de combustión incompleta.",
        "canonical_unit": "ppm",
        "lel_percent_vol": None,
        "physical_max": PHYSICAL_MAX["CO"],
        "max_rate_per_min": MAX_RATE_PER_MIN["CO"],
        "priority": 2,
        "is_active": True,
    },
    {
        "code": "H2S",
        "display_name": "Sulfuro de hidrógeno",
        "plain_description": "Gas tóxico con olor a huevo podrido; puede anular el olfato.",
        "canonical_unit": "ppm",
        "lel_percent_vol": None,
        "physical_max": PHYSICAL_MAX["H2S"],
        "max_rate_per_min": MAX_RATE_PER_MIN["H2S"],
        "priority": 3,
        "is_active": True,
    },
    {
        "code": "O2",
        "display_name": "Oxígeno",
        "plain_description": "El aire de la mina debe mantener oxígeno suficiente para respirar.",
        "canonical_unit": "%vol",
        "lel_percent_vol": None,
        "physical_max": PHYSICAL_MAX["O2"],
        "max_rate_per_min": MAX_RATE_PER_MIN["O2"],
        "priority": 4,
        "is_active": True,
    },
    {
        "code": "CO2",
        "display_name": "Dióxido de carbono",
        "plain_description": "Gas que desplaza oxígeno en espacios cerrados.",
        "canonical_unit": "ppm",
        "lel_percent_vol": None,
        "physical_max": PHYSICAL_MAX["CO2"],
        "max_rate_per_min": MAX_RATE_PER_MIN["CO2"],
        "priority": 5,
        "is_active": True,
    },
    {
        "code": "NO2",
        "display_name": "Dióxido de nitrógeno",
        "plain_description": "Gas irritante asociado a explosivos y motores diésel.",
        "canonical_unit": "ppm",
        "lel_percent_vol": None,
        "physical_max": PHYSICAL_MAX["NO2"],
        "max_rate_per_min": MAX_RATE_PER_MIN["NO2"],
        "priority": 6,
        "is_active": True,
    },
)

SETTINGS_SEED: dict[str, Any] = {
    "grid_step_minutes": 6,
    "forecast_horizons_min": [6, 12, 18],
    "shift_hours": 8,
    "alert_persistence_steps": 2,
    "language_register_lint": True,
    "thesis_targets": {
        "recall_actuar_min": 0.95,
        "fn_max": 0.05,
        "precision_event_min": 0.90,
        "f1_event_min": 0.92,
        "rmse_ch4_max": 0.05,
        "lead_p50_min": 5,
        "fa_actuar_per_shift_max": 1.0,
        "fa_evacuar_per_shift_max": 0.25,
        "coverage_target": 0.90,
        "coverage_tol": 0.05,
    },
}


def seed_gas_types(db: Session) -> int:
    n = 0
    for row in GAS_TYPE_SEED:
        existing = db.get(GasType, row["code"])
        if existing is None:
            db.add(GasType(**row))
            n += 1
            continue
        for key, value in row.items():
            if key != "code":
                setattr(existing, key, value)
        n += 1
    db.flush()
    return n


def seed_thresholds(db: Session) -> int:
    n = 0
    now = datetime.now(timezone.utc)
    wanted = {seed_key(spec): spec for spec in THRESHOLD_SEED}
    for row in db.query(NormativeThreshold).all():
        if (row.kind or "normativo") != "normativo":
            continue
        key = (row.gas_code, row.level, row.metric or "instantaneo", row.direction, row.site_kind or "cualquiera")
        if key not in wanted:
            db.delete(row)
    db.flush()
    for spec in THRESHOLD_SEED:
        existing = (
            db.query(NormativeThreshold)
            .filter(
                NormativeThreshold.gas_code == spec.gas_code,
                NormativeThreshold.level == spec.level,
                NormativeThreshold.metric == spec.metric,
                NormativeThreshold.direction == spec.direction,
                NormativeThreshold.site_kind == spec.site_kind,
                NormativeThreshold.kind == "normativo",
            )
            .order_by(NormativeThreshold.valid_from.desc())
            .first()
        )
        if existing is not None:
            existing.value = spec.value
            existing.source_reference = spec.source_reference
            existing.article = spec.article
            existing.kind = spec.kind
            n += 1
            continue
        db.add(
            NormativeThreshold(
                gas_code=spec.gas_code,
                level=spec.level,
                direction=spec.direction,
                value=spec.value,
                source_reference=spec.source_reference,
                verified=spec.verified,
                valid_from=now,
                metric=spec.metric,
                site_kind=spec.site_kind,
                kind=spec.kind,
                article=spec.article,
            )
        )
        n += 1
    db.flush()
    return n


def seed_settings(db: Session) -> int:
    n = 0
    for key, value in SETTINGS_SEED.items():
        existing = db.get(AppSetting, key)
        if existing is None:
            db.add(AppSetting(key=key, value=value))
        else:
            existing.value = value
        n += 1
    db.flush()
    return n


def seed_catalog(db: Session, *, hydrate_cache: bool = True) -> dict[str, int]:
    counts = {
        "gas_types": seed_gas_types(db),
        "thresholds": seed_thresholds(db),
        "settings": seed_settings(db),
    }
    db.commit()
    if hydrate_cache:
        apply_db_catalog(list(db.query(GasType).all()))
    return counts
