"""Modelos ORM de model_registry y training_jobs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.roles_permissions import models as _roles_models  # noqa: F401
from app.modules.users import models as _users_models  # noqa: F401


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    family: Mapped[str] = mapped_column(
        String(32), nullable=False, default="tabular", server_default="tabular", index=True
    )
    params: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    metrics: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    problem_spec: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    calibration: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    selection_score: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    mlflow_run_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    artifact_uri: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="staging", index=True
    )
    scope: Mapped[str] = mapped_column(
        String(64), nullable=False, default="global", server_default="global", index=True
    )
    trained_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_registry_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("model_registry.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", index=True
    )
    dataset_version: Mapped[str] = mapped_column(String(128), nullable=False, default="gas_readings")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    triggered_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    params: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ModelEvaluation(Base):
    __tablename__ = "model_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("model_registry.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fold_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fold_spec: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    gas_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    horizon_min: Mapped[int] = mapped_column(Integer, nullable=False)
    forecast_metrics: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    event_metrics: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    is_final_test: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
