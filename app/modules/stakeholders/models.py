"""Modelos ORM de stakeholders, suscripciones y notificaciones."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.sensors_ingestion import models as _sensors_models  # noqa: F401
from app.modules.users import models as _users_models  # noqa: F401


class Stakeholder(Base):
    __tablename__ = "stakeholders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False, default="interno")
    organization: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    notify_channels: Mapped[Optional[list[Any]]] = mapped_column(
        JSONB, nullable=True
    )  # ej. ["email", "whatsapp"]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    subscriptions: Mapped[list[StakeholderSubscription]] = relationship(
        back_populates="stakeholder", cascade="all, delete-orphan", lazy="selectin"
    )
    user_links: Mapped[list[StakeholderUser]] = relationship(
        back_populates="stakeholder", cascade="all, delete-orphan", lazy="selectin"
    )


class StakeholderUser(Base):
    __tablename__ = "stakeholder_user"
    __table_args__ = (UniqueConstraint("stakeholder_id", "user_id"),)

    stakeholder_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stakeholders.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    stakeholder: Mapped[Stakeholder] = relationship(back_populates="user_links")


class StakeholderSubscription(Base):
    __tablename__ = "stakeholder_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stakeholder_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stakeholders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    site_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=True, index=True
    )
    sensor_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sensors.id", ondelete="CASCADE"), nullable=True, index=True
    )
    min_level: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ALERTA", server_default="ALERTA"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    stakeholder: Mapped[Stakeholder] = relationship(back_populates="subscriptions")


class AlertNotification(Base):
    __tablename__ = "alert_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stakeholder_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stakeholders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
