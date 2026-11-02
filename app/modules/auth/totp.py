"""TOTP y códigos de respaldo (Plan 19)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone

try:
    import pyotp
except ImportError:  # pragma: no cover
    pyotp = None  # type: ignore[assignment]


ISSUER = "Plataforma Gases"


def available() -> bool:
    return pyotp is not None


def new_secret() -> str:
    if pyotp is None:
        return secrets.token_hex(20)
    return pyotp.random_base32()


def provisioning_uri(secret: str, email: str) -> str:
    if pyotp is None:
        return f"otpauth://totp/{ISSUER}:{email}?secret={secret}&issuer={ISSUER}"
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=ISSUER)


def verify_code(secret: str, code: str, *, at: datetime | None = None) -> bool:
    clean = (code or "").replace(" ", "")
    if len(clean) != 6 or not clean.isdigit():
        return False
    if pyotp is None:
        return False
    totp = pyotp.TOTP(secret)
    if at is not None:
        ts = at.replace(tzinfo=timezone.utc).timestamp() if at.tzinfo is None else at.timestamp()
        return bool(totp.verify(clean, for_time=ts, valid_window=1))
    return bool(totp.verify(clean, valid_window=1))


def backup_codes(n: int = 8) -> list[str]:
    return [secrets.token_hex(4).upper() for _ in range(n)]


def hash_backup(code: str) -> str:
    return hashlib.sha256(code.strip().upper().encode("utf-8")).hexdigest()


def consume_backup(stored: list[str], code: str) -> list[str] | None:
    digest = hash_backup(code)
    for i, item in enumerate(stored or []):
        if hmac.compare_digest(item, digest):
            return list(stored[:i] + stored[i + 1 :])
    return None
