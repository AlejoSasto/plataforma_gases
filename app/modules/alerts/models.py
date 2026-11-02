"""Modelo ORM de alertas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.forecasting import models as _forecast_models  # noqa: F401
from app.modules.sensors_ingestion import models as _sensors_models  # noqa: F401
from app.modules.users import models as _users_models  # noqa: F401


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (Index("ix_alerts_status_created", "status", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    forecast_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("forecasts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    gas_reading_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("gas_readings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    sensor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(
        String(16), nullable=False, default="confirmado", server_default="confirmado", index=True
    )
    level: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    threshold_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("normative_thresholds.id", ondelete="SET NULL"), nullable=True
    )
    expected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    plain_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plain_recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="abierta", server_default="abierta", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    acknowledged_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    outcome: Mapped[Optional["AlertOutcome"]] = relationship(
        back_populates="alert", uselist=False, cascade="all, delete-orphan"
    )


class AlertOutcome(Base):
    __tablename__ = "alert_outcomes"

    alert_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("alerts.id", ondelete="CASCADE"), primary_key=True
    )
    outcome: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pendiente", server_default="pendiente"
    )
    event_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("threshold_events.id", ondelete="SET NULL"), nullable=True
    )
    lead_minutes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    alert: Mapped[Alert] = relationship(back_populates="outcome")
