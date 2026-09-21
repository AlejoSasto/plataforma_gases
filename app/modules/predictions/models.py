"""Modelo ORM de predicciones."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.ml_training import models as _ml_models  # noqa: F401
from app.modules.sensors_ingestion import models as _sensors_models  # noqa: F401


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    gas_reading_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gas_readings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_registry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("model_registry.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_label: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
