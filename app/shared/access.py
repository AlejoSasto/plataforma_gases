"""Roles v2, matriz de permisos y alcance por zona (Plan 19)."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.modules.users.models import User, UserSiteScope

ROLE_LABELS: dict[str, str] = {
    "admin": "Administrador",
    "supervisor_seguridad": "Supervisor de seguridad",
    "operador": "Operador de sala",
    "gerencia": "Gerencia",
    "analista": "Analista de datos",
    "auditor": "Auditor",
}

ROLE_MIGRATION: dict[str, str] = {
    "ingeniero_datos": "analista",
    "operador_mina": "operador",
    "interesado": "gerencia",
}

OPERATOR_ROLES = {"operador", "operador_mina"}
TOTP_REQUIRED_ROLES = {"admin", "analista"}

# Permisos canónicos de la matriz §2.
PERMISSIONS: tuple[str, ...] = (
    "status.view",
    "alerts.view",
    "alerts.acknowledge",
    "alerts.resolve",
    "history.view",
    "reliability.view",
    "reports.export",
    "thresholds.manage",
    "stakeholders.manage",
    "data.upload",
    "data.quality.view",
    "models.train",
    "models.promote",
    "users.manage",
    "roles.manage",
    "kiosk.manage",
    "audit.view",
)

# Compatibilidad con routers previos a Plan 19.
PERMISSION_ALIASES: dict[str, tuple[str, ...]] = {
    "predictions.view": ("status.view", "history.view", "predictions.view"),
    "sensors.manage": ("data.upload", "sensors.manage"),
    "dashboard.view_all_sites": ("status.view", "dashboard.view_all_sites"),
}

MATRIX: dict[str, frozenset[str]] = {
    "admin": frozenset(PERMISSIONS),
    "supervisor_seguridad": frozenset(
        {
            "status.view",
            "alerts.view",
            "alerts.acknowledge",
            "alerts.resolve",
            "history.view",
            "reliability.view",
            "reports.export",
            "thresholds.manage",
            "stakeholders.manage",
            "kiosk.manage",
        }
    ),
    "operador": frozenset(
        {
            "status.view",
            "alerts.view",
            "alerts.acknowledge",
            "alerts.resolve",
            "history.view",
        }
    ),
    "gerencia": frozenset(
        {
            "status.view",
            "alerts.view",
            "history.view",
            "reliability.view",
            "reports.export",
        }
    ),
    "analista": frozenset(
        {
            "status.view",
            "alerts.view",
            "history.view",
            "reliability.view",
            "reports.export",
            "data.upload",
            "data.quality.view",
            "models.train",
            "models.promote",
        }
    ),
    "auditor": frozenset(
        {
            "status.view",
            "alerts.view",
            "history.view",
            "reliability.view",
            "reports.export",
            "data.quality.view",
            "audit.view",
        }
    ),
}

LEGACY_GRANTS: dict[str, tuple[str, ...]] = {
    "admin": ("predictions.view", "sensors.manage", "dashboard.view_all_sites"),
    "supervisor_seguridad": ("predictions.view", "dashboard.view_all_sites"),
    "operador": ("predictions.view",),
    "gerencia": ("predictions.view",),
    "analista": ("predictions.view", "sensors.manage"),
    "auditor": ("predictions.view", "dashboard.view_all_sites"),
}


def grants_for(role: str) -> frozenset[str]:
    base = set(MATRIX.get(role, frozenset()))
    base.update(LEGACY_GRANTS.get(role, ()))
    if role == "admin":
        base.update(PERMISSIONS)
        base.update(sum((list(v) for v in PERMISSION_ALIASES.values()), []))
    return frozenset(base)


def role_label(code: str) -> str:
    return ROLE_LABELS.get(code, code)


def canonical_role(code: str) -> str:
    return ROLE_MIGRATION.get(code, code)


def user_has_permission(user: User, code: str) -> bool:
    held = set(user.permission_codes)
    if code in held:
        return True
    for alias in PERMISSION_ALIASES.get(code, (code,)):
        if alias in held:
            return True
    # Si piden un alias viejo y el usuario tiene el canónico.
    for required, options in PERMISSION_ALIASES.items():
        if required == code:
            continue
        if code in options and any(o in held for o in options):
            return True
    return False


def scoped_site_ids(db: Session, user: User) -> set[int] | None:
    """None = todas las zonas. set vacío = ninguna (operador sin asignar)."""
    rows = db.query(UserSiteScope).filter(UserSiteScope.user_id == user.id).all()
    assigned = {r.site_id for r in rows}
    roles = {canonical_role(r) for r in user.role_names}
    if roles & OPERATOR_ROLES:
        return assigned
    if assigned:
        return assigned
    return None


def site_allowed(db: Session, user: User, site_id: int | None) -> bool:
    if site_id is None:
        return True
    scope = scoped_site_ids(db, user)
    if scope is None:
        return True
    return site_id in scope


def filter_site_ids(db: Session, user: User, site_ids: Iterable[int]) -> list[int]:
    scope = scoped_site_ids(db, user)
    if scope is None:
        return list(site_ids)
    return [s for s in site_ids if s in scope]
