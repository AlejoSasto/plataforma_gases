"""ORM: forecasts, cuantiles, explicaciones."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.ml_training import models as _ml  # noqa: F401
from app.modules.sensors_ingestion import models as _sens  # noqa: F401


class Forecast(Base):
    __tablename__ = "forecasts"
    __table_args__ = (
        UniqueConstraint("sensor_id", "model_id", "issued_at", name="uq_forecast_sensor_model_issued"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sensor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("model_registry.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status_level: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    exceed_prob: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="media")
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    quantiles: Mapped[list["ForecastQuantile"]] = relationship(
        back_populates="forecast", cascade="all, delete-orphan"
    )
    explanations: Mapped[list["ForecastExplanation"]] = relationship(
        back_populates="forecast", cascade="all, delete-orphan"
    )


class ForecastQuantile(Base):
    __tablename__ = "forecast_quantiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    forecast_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("forecasts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    horizon_min: Mapped[int] = mapped_column(Integer, nullable=False)
    q10: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    q50: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    q90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    q95: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    forecast: Mapped[Forecast] = relationship(back_populates="quantiles")


class ForecastExplanation(Base):
    __tablename__ = "forecast_explanations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    forecast_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("forecasts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    method: Mapped[str] = mapped_column(String(64), nullable=False)
    factors: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    plain_text: Mapped[str] = mapped_column(String(2000), nullable=False, default="")

    forecast: Mapped[Forecast] = relationship(back_populates="explanations")
