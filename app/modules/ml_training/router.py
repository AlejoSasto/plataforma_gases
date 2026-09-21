"""Router de entrenamiento y registro de modelos."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.modules.ml_training import service as ml_service
from app.modules.ml_training.schemas import (
    ModelCompareItem,
    ModelRegistryResponse,
    TrainRequest,
    TrainResponse,
    TrainingJobResponse,
)
from app.shared.dependencies import CurrentUser, DbSession, require_permission
from app.shared.pagination import Page

router = APIRouter(prefix="/api/ml", tags=["ml"])

CanTrain = Annotated[object, Depends(require_permission("models.train"))]
CanPromote = Annotated[object, Depends(require_permission("models.promote"))]


@router.post("/train", response_model=TrainResponse)
def train_models(
    body: TrainRequest,
    db: DbSession,
    actor: CurrentUser,
    _: CanTrain,
) -> TrainResponse:
    result = ml_service.start_training(
        db,
        triggered_by=actor.id,
        dataset_version=body.dataset_version,
        params=dict(body.params or {}),
        scope=body.scope,
        task=body.task,
        algorithms=body.algorithms,
        lookback_steps=body.lookback_steps,
        horizon_minutes=body.horizon_minutes,
    )
    return TrainResponse(
        job=TrainingJobResponse(**result["job"]),
        models=[ModelRegistryResponse(**m) for m in result["models"]],
        best_model_id=result["best_model_id"],
    )


@router.get("/catalog")
def get_catalog(_: CanTrain) -> list[dict]:
    return ml_service.model_catalog()


@router.get("/jobs", response_model=Page[TrainingJobResponse])
def list_jobs(
    db: DbSession,
    _: CanTrain,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[TrainingJobResponse]:
    data = ml_service.list_jobs(db, page=page, page_size=page_size)
    return Page(
        items=[TrainingJobResponse(**i) for i in data["items"]],
        total=data["total"],
        page=data["page"],
        page_size=data["page_size"],
    )


@router.get("/models", response_model=list[ModelRegistryResponse])
def list_models(db: DbSession, _: CanTrain) -> list[ModelRegistryResponse]:
    return [ModelRegistryResponse(**m) for m in ml_service.list_models(db)]


@router.get("/models/compare", response_model=list[ModelCompareItem])
def compare_models(db: DbSession, _: CanTrain) -> list[ModelCompareItem]:
    return [ModelCompareItem(**m) for m in ml_service.compare_models(db)]


@router.post("/models/{model_id}/promote", response_model=ModelRegistryResponse)
def promote_model(
    model_id: int,
    db: DbSession,
    actor: CurrentUser,
    _: CanPromote,
) -> ModelRegistryResponse:
    return ModelRegistryResponse(
        **ml_service.promote_model(db, model_id, actor_id=actor.id)
    )
