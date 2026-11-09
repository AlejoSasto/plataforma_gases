"""ORM: forecasts, cuantiles, explicaciones."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
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


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    commit_sha: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    data_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    seed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    g1_params: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_final_test: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    manifest: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    selection_report: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    promoted_algorithm: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class BacktestForecast(Base):
    __tablename__ = "backtest_forecasts"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "model_key",
            "fold_index",
            "sensor_id",
            "issued_at",
            "horizon_min",
            name="uq_backtest_point",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("benchmark_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    fold_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sensor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    horizon_min: Mapped[int] = mapped_column(Integer, nullable=False)
    q10: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    q50: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    q90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    q95: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    y_true: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    decided_level: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    train_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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
