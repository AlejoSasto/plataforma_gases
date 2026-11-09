"""Modelos ORM de sitios, sensores, lecturas y corridas ETL."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    desc,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# Registrar dependencias de FK / relationships para mappers
from app.modules.catalog import models as _catalog_models  # noqa: F401
from app.modules.roles_permissions import models as _roles_models  # noqa: F401
from app.modules.users import models as _users_models  # noqa: F401


class Instrument(Base):
    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    serial: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_seen: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_to: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    site_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True
    )

    sensors: Mapped[list["Sensor"]] = relationship(back_populates="instrument", lazy="selectin")


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
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    kind: Mapped[str] = mapped_column(
        String(16), nullable=False, default="desconocido", server_default="desconocido"
    )
    location_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    instrument_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("instruments.id", ondelete="SET NULL"), nullable=True, index=True
    )

    site: Mapped[Site] = relationship(back_populates="sensors")
    instrument: Mapped[Optional[Instrument]] = relationship(back_populates="sensors")
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
    steps: Mapped[list["EtlRunStep"]] = relationship(back_populates="etl_run", lazy="noload")


class GasReading(Base):
    __tablename__ = "gas_readings"
    __table_args__ = (
        UniqueConstraint("sensor_id", "tiempo_inicio", name="uq_gas_readings_sensor_tiempo"),
        Index("ix_gas_readings_sensor_tiempo_desc", "sensor_id", desc("tiempo_inicio")),
        CheckConstraint("is_synthetic = false", name="ck_gas_readings_no_synthetic"),
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
    value_canonical: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    unit_canonical: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    quality_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="ok", server_default="ok"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    sensor: Mapped[Sensor] = relationship(back_populates="readings")
    etl_run: Mapped[Optional[EtlRun]] = relationship(back_populates="readings")


class EtlRunStep(Base):
    __tablename__ = "etl_run_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    etl_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("etl_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step: Mapped[str] = mapped_column(String(8), nullable=False)
    rows_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    etl_run: Mapped[EtlRun] = relationship(back_populates="steps")


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    gas_reading_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("gas_readings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    sensor_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sensors.id", ondelete="SET NULL"), nullable=True, index=True
    )
    etl_run_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("etl_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="advertencia")
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)


class ReadingGrid(Base):
    __tablename__ = "reading_grid"

    sensor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sensors.id", ondelete="CASCADE"), primary_key=True
    )
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    value: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    is_imputed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_missing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    source_etl_run_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("etl_runs.id", ondelete="SET NULL"), nullable=True
    )
    twa_8h: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    stel_15min: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)


class ThresholdEvent(Base):
    __tablename__ = "threshold_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sensor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    gas_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    threshold_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("normative_thresholds.id", ondelete="SET NULL"), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    peak_value: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    peak_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    detected_by: Mapped[str] = mapped_column(String(16), nullable=False, default="etl")
