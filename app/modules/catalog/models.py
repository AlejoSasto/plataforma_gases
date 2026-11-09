"""ORM: gas_types, normative_thresholds, app_settings."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class GasType(Base):
    __tablename__ = "gas_types"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    plain_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    canonical_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    lel_percent_vol: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    physical_max: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    max_rate_per_min: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=99)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    thresholds: Mapped[list["NormativeThreshold"]] = relationship(back_populates="gas_type")


class NormativeThreshold(Base):
    __tablename__ = "normative_thresholds"
    __table_args__ = (
        UniqueConstraint(
            "gas_code",
            "level",
            "metric",
            "direction",
            "site_kind",
            "valid_from",
            name="uq_threshold_gas_level_metric_from",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    gas_code: Mapped[str] = mapped_column(
        String(10), ForeignKey("gas_types.code", ondelete="CASCADE"), nullable=False, index=True
    )
    level: Mapped[str] = mapped_column(String(16), nullable=False)  # vigilar|actuar|evacuar
    direction: Mapped[str] = mapped_column(String(8), nullable=False)  # above|below
    value: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    metric: Mapped[str] = mapped_column(
        String(16), nullable=False, default="instantaneo", server_default="instantaneo"
    )
    site_kind: Mapped[str] = mapped_column(
        String(16), nullable=False, default="cualquiera", server_default="cualquiera"
    )
    kind: Mapped[str] = mapped_column(
        String(24), nullable=False, default="normativo", server_default="normativo"
    )
    article: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    source_reference: Mapped[str] = mapped_column(Text, nullable=False, default="")
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    gas_type: Mapped[GasType] = relationship(back_populates="thresholds")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
