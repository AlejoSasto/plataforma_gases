"""Router de stakeholders (API JSON)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.stakeholders import service as stake_service
from app.modules.stakeholders.schemas import (
    StakeholderCreate,
    StakeholderResponse,
    StakeholderUpdate,
    SubscriptionCreate,
    SubscriptionResponse,
)
from app.shared.dependencies import DbSession, require_permission

router = APIRouter(prefix="/api", tags=["stakeholders"])

ManageStakeholders = Annotated[object, Depends(require_permission("stakeholders.manage"))]


@router.get("/stakeholders", response_model=list[StakeholderResponse])
def list_stakeholders(db: DbSession, _: ManageStakeholders) -> list[StakeholderResponse]:
    return [
        StakeholderResponse(**stake_service.stakeholder_to_dict(s))
        for s in stake_service.list_stakeholders(db)
    ]


@router.post("/stakeholders", response_model=StakeholderResponse, status_code=201)
def create_stakeholder(
    body: StakeholderCreate, db: DbSession, _: ManageStakeholders
) -> StakeholderResponse:
    row = stake_service.create_stakeholder(db, body.model_dump())
    return StakeholderResponse(**stake_service.stakeholder_to_dict(row))


@router.get("/stakeholders/{stakeholder_id}", response_model=StakeholderResponse)
def get_stakeholder(
    stakeholder_id: int, db: DbSession, _: ManageStakeholders
) -> StakeholderResponse:
    row = stake_service.get_stakeholder(db, stakeholder_id)
    return StakeholderResponse(**stake_service.stakeholder_to_dict(row))


@router.patch("/stakeholders/{stakeholder_id}", response_model=StakeholderResponse)
def update_stakeholder(
    stakeholder_id: int,
    body: StakeholderUpdate,
    db: DbSession,
    _: ManageStakeholders,
) -> StakeholderResponse:
    row = stake_service.update_stakeholder(
        db, stakeholder_id, body.model_dump(exclude_unset=True)
    )
    return StakeholderResponse(**stake_service.stakeholder_to_dict(row))


@router.delete("/stakeholders/{stakeholder_id}", status_code=204)
def delete_stakeholder(
    stakeholder_id: int, db: DbSession, _: ManageStakeholders
) -> None:
    stake_service.delete_stakeholder(db, stakeholder_id)


@router.get(
    "/stakeholders/{stakeholder_id}/subscriptions",
    response_model=list[SubscriptionResponse],
)
def list_subscriptions(
    stakeholder_id: int, db: DbSession, _: ManageStakeholders
) -> list[SubscriptionResponse]:
    return [
        SubscriptionResponse(**stake_service.subscription_to_dict(s))
        for s in stake_service.list_subscriptions(db, stakeholder_id)
    ]


@router.post(
    "/stakeholders/{stakeholder_id}/subscriptions",
    response_model=SubscriptionResponse,
    status_code=201,
)
def create_subscription(
    stakeholder_id: int,
    body: SubscriptionCreate,
    db: DbSession,
    _: ManageStakeholders,
) -> SubscriptionResponse:
    sub = stake_service.add_subscription(db, stakeholder_id, body.model_dump())
    return SubscriptionResponse(**stake_service.subscription_to_dict(sub))


@router.delete("/subscriptions/{subscription_id}", status_code=204)
def delete_subscription(
    subscription_id: int, db: DbSession, _: ManageStakeholders
) -> None:
    stake_service.delete_subscription(db, subscription_id)
