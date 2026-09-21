"""Schemas Pydantic de ML training."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field


class TrainRequest(BaseModel):
    dataset_version: str = "gas_readings"
    scope: str = "global"
    task: Literal["classification", "regression", "both"] = "classification"
    algorithms: Optional[Union[list[str], str]] = None
    lookback_steps: Optional[int] = None
    horizon_minutes: Optional[float] = None
    params: dict[str, Any] = Field(default_factory=dict)


class TrainingJobResponse(BaseModel):
    id: int
    model_registry_id: Optional[int] = None
    status: str
    dataset_version: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    triggered_by: Optional[int] = None
    params: dict[str, Any] = Field(default_factory=dict)
    log: Optional[str] = None


class ModelRegistryResponse(BaseModel):
    id: int
    name: str
    version: str
    algorithm: str
    params: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    mlflow_run_id: Optional[str] = None
    artifact_uri: Optional[str] = None
    status: str
    scope: str
    trained_by: Optional[int] = None
    trained_at: datetime


class TrainResponse(BaseModel):
    job: TrainingJobResponse
    models: list[ModelRegistryResponse]
    best_model_id: Optional[int] = None


class ModelCompareItem(BaseModel):
    id: int
    name: str
    algorithm: str
    status: str
    scope: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    trained_at: Optional[datetime] = None
    family: Optional[str] = None
    task: Optional[str] = None
    meets_thesis: Optional[bool] = None
