"""Modelos ORM de sitios, sensores, lecturas y corridas ETL."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# Registrar dependencias de FK / relationships para mappers
from app.modules.roles_permissions import models as _roles_models  # noqa: F401
from app.modules.users import models as _users_models  # noqa: F401


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    sensors: Mapped[list[Sensor]] = relationship(back_populates="site", lazy="selectin")


class Sensor(Base):
    __tablename__ = "sensors"
    __table_args__ = (UniqueConstraint("code", "gas_type", name="uq_sensors_code_gas"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    gas_type: Mapped[str] = mapped_column(String(64), nullable=False, default="UNKNOWN")
    unit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    site: Mapped[Site] = relationship(back_populates="sensors")
    readings: Mapped[list[GasReading]] = relationship(back_populates="sensor", lazy="noload")


class EtlRun(Base):
    __tablename__ = "etl_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running", index=True)
    rows_ingested: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_files: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    log: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    triggered_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    readings: Mapped[list[GasReading]] = relationship(back_populates="etl_run", lazy="noload")


class GasReading(Base):
    __tablename__ = "gas_readings"
    __table_args__ = (
        Index("ix_gas_readings_sensor_tiempo", "sensor_id", "tiempo_inicio"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sensor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    leyendo: Mapped[float] = mapped_column(Float, nullable=False)
    unidad: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    stel_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    twa_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    alarma: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    temperatura: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tiempo_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tiempo_fin: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    source_file: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    etl_run_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("etl_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    sensor: Mapped[Sensor] = relationship(back_populates="readings")
    etl_run: Mapped[Optional[EtlRun]] = relationship(back_populates="readings")
