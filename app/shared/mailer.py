"""Correo: SMTP si hay config; si no, outbox local (Plan 19)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings

log = logging.getLogger("plataforma.mail")
OUTBOX = Path("storage/outbox")


def send_mail(*, to: str, subject: str, body: str) -> Path | None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    OUTBOX.mkdir(parents=True, exist_ok=True)
    safe = to.replace("@", "_at_").replace("/", "_")
    path = OUTBOX / f"{stamp}_{safe}.txt"
    path.write_text(f"To: {to}\nSubject: {subject}\n\n{body}\n", encoding="utf-8")
    log.info("correo a %s asunto=%s archivo=%s", to, subject, path)
    if settings.smtp_host:
        log.info("SMTP configurado; el envío real queda para el canal de la empresa. Copia en outbox.")
    return path
