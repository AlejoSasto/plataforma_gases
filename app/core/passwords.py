"""Política de contraseñas (NIST SP 800-63B, Plan 19)."""

from __future__ import annotations

from pathlib import Path

MIN_LENGTH = 12
COMMON_FILE = Path(__file__).with_name("common_passwords.txt")


def load_common() -> set[str]:
    if not COMMON_FILE.exists():
        return set()
    lines = COMMON_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
    return {ln.strip().lower() for ln in lines if ln.strip()}


_COMMON: set[str] | None = None


def common_passwords() -> set[str]:
    global _COMMON
    if _COMMON is None:
        _COMMON = load_common()
    return _COMMON


def strength_phrase(password: str) -> str:
    n = len(password or "")
    if n < MIN_LENGTH:
        return "Demasiado corta: usa al menos 12 caracteres"
    if password.lower() in common_passwords():
        return "Esta contraseña es demasiado común"
    if n < 14:
        return "Aceptable. Un poco más larga sería más segura"
    if n < 16:
        return "Buena contraseña"
    return "Contraseña sólida"


def validate_password(password: str, *, email: str = "", full_name: str = "") -> str | None:
    """None si pasa; si no, mensaje para la persona."""
    raw = password or ""
    if len(raw) < MIN_LENGTH:
        return "La contraseña debe tener al menos 12 caracteres"
    lowered = raw.casefold()
    if lowered in common_passwords():
        return "Elige otra: esa contraseña es demasiado común"
    local = (email or "").split("@")[0].casefold()
    if local and len(local) >= 3 and local in lowered:
        return "No uses tu correo dentro de la contraseña"
    for part in (full_name or "").replace(".", " ").split():
        if len(part) >= 3 and part.casefold() in lowered:
            return "No uses tu nombre dentro de la contraseña"
    return None
