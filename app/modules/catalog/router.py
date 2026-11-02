"""API de catálogo (gases y umbrales)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.catalog import repository as repo
from app.modules.catalog.schemas import GasTypeOut, ThresholdOut
from app.shared.dependencies import DbSession, require_permission

router = APIRouter(prefix="/api/catalog", tags=["catalog"])
CanView = Annotated[object, Depends(require_permission("dashboard.view_all_sites"))]


@router.get("/gases", response_model=list[GasTypeOut])
def list_gases(db: DbSession, _: CanView) -> list[GasTypeOut]:
    return [GasTypeOut.model_validate(g) for g in repo.list_gas_types(db)]


@router.get("/gases/{gas_code}/thresholds", response_model=list[ThresholdOut])
def list_thresholds(gas_code: str, db: DbSession, _: CanView) -> list[ThresholdOut]:
    return [ThresholdOut.model_validate(t) for t in repo.thresholds_for_gas(db, gas_code.upper())]
