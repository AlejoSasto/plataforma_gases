"""Canales de notificación (patrón estrategia)."""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.alerts.models import Alert
from app.modules.sensors_ingestion.models import Sensor, Site
from app.modules.stakeholders.models import AlertNotification, Stakeholder

logger = logging.getLogger(__name__)


@dataclass
class NotificationResult:
    status: str  # enviado | fallido
    error: str | None = None


class NotificationChannel(Protocol):
    name: str

    def send(self, stakeholder: Stakeholder, alert: Alert, body: str) -> NotificationResult: ...


def _alert_body(db: Session, alert: Alert) -> str:
    sensor = db.query(Sensor).filter(Sensor.id == alert.sensor_id).first()
    site_name = "N/D"
    sensor_code = str(alert.sensor_id)
    if sensor is not None:
        sensor_code = sensor.code
        site = db.query(Site).filter(Site.id == sensor.site_id).first()
        if site is not None:
            site_name = site.name
    return (
        f"Alerta {alert.level}\n"
        f"Sitio: {site_name}\n"
        f"Sensor: {sensor_code}\n"
        f"Mensaje: {alert.message}\n"
        f"Recomendación: {alert.recommendation}\n"
        f"Estado: {alert.status}\n"
    )


class EmailChannel:
    name = "email"

    def send(self, stakeholder: Stakeholder, alert: Alert, body: str) -> NotificationResult:
        if not stakeholder.email:
            return NotificationResult(status="fallido", error="stakeholder_sin_email")
        if settings.notifications_dry_run or not settings.smtp_host:
            logger.info(
                "DRY-RUN email to=%s alert_id=%s\n%s",
                stakeholder.email,
                alert.id,
                body,
            )
            return NotificationResult(status="enviado", error=None)
        try:
            msg = EmailMessage()
            msg["Subject"] = f"[Plataforma Gases] Alerta {alert.level}"
            msg["From"] = settings.smtp_from or "noreply@plataforma-gases.local"
            msg["To"] = stakeholder.email
            msg.set_content(body)
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                if settings.smtp_user and settings.smtp_password:
                    smtp.starttls()
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(msg)
            return NotificationResult(status="enviado")
        except Exception as exc:  # noqa: BLE001
            return NotificationResult(status="fallido", error=str(exc))


class WhatsAppChannel:
    """Stub — listo para integrar proveedor (Twilio/Meta) sin tocar alerts/service."""

    name = "whatsapp"

    def send(self, stakeholder: Stakeholder, alert: Alert, body: str) -> NotificationResult:
        if not stakeholder.phone:
            return NotificationResult(status="fallido", error="stakeholder_sin_phone")
        if settings.notifications_dry_run or not settings.whatsapp_api_token:
            logger.info(
                "DRY-RUN whatsapp to=%s alert_id=%s", stakeholder.phone, alert.id
            )
            return NotificationResult(status="enviado")
        return NotificationResult(
            status="fallido",
            error="whatsapp_provider_not_implemented",
        )


CHANNEL_HANDLERS: dict[str, NotificationChannel] = {
    EmailChannel.name: EmailChannel(),
    WhatsAppChannel.name: WhatsAppChannel(),
}


def send_alert_notification(
    db: Session,
    stakeholder: Stakeholder,
    alert: Alert,
    *,
    channel: str,
) -> AlertNotification:
    handler = CHANNEL_HANDLERS.get(channel)
    body = _alert_body(db, alert)
    if handler is None:
        result = NotificationResult(status="fallido", error=f"canal_desconocido:{channel}")
    else:
        result = handler.send(stakeholder, alert, body)

    row = AlertNotification(
        alert_id=alert.id,
        stakeholder_id=stakeholder.id,
        channel=channel,
        status=result.status,
        sent_at=datetime.now(timezone.utc) if result.status == "enviado" else None,
        error=result.error,
    )
    db.add(row)
    db.flush()
    return row


def notify_alert_recipients(db: Session, alert: Alert, recipients: list[Stakeholder]) -> int:
    """Envía por cada canal configurado del stakeholder. Retorna notificaciones creadas."""
    count = 0
    for stakeholder in recipients:
        channels = stakeholder.notify_channels or ["email"]
        if isinstance(channels, str):
            channels = [channels]
        for channel in channels:
            send_alert_notification(db, stakeholder, alert, channel=str(channel))
            count += 1
    return count
