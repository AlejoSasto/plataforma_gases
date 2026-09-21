"""Seed de permisos base y roles RBAC.

Uso:
  python scripts/seed_roles_permissions.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.roles_permissions.models import Permission, Role
from app.modules.users import models as users_models  # noqa: F401 — registra user_roles

BASE_PERMISSIONS: list[tuple[str, str]] = [
    ("users.manage", "Gestionar usuarios"),
    ("roles.manage", "Gestionar roles y permisos"),
    ("sensors.manage", "Gestionar sensores e ingesta"),
    ("models.train", "Entrenar modelos ML"),
    ("models.promote", "Promover modelos a producción"),
    ("predictions.view", "Ver predicciones"),
    ("alerts.view", "Ver alertas"),
    ("alerts.resolve", "Resolver alertas"),
    ("stakeholders.manage", "Gestionar stakeholders"),
    ("reports.export", "Exportar reportes"),
    ("dashboard.view_all_sites", "Ver dashboard de todos los sitios"),
    ("audit.view", "Ver auditoría"),
]

# name -> list of permission codes (empty list means none; "*" means all)
ROLE_DEFINITIONS: dict[str, tuple[str, list[str] | str]] = {
    "admin": ("Administrador del sistema", "*"),
    "ingeniero_datos": (
        "Ingeniero de datos / ML",
        [
            "sensors.manage",
            "models.train",
            "models.promote",
            "predictions.view",
            "alerts.view",
            "reports.export",
        ],
    ),
    "operador_mina": (
        "Operador de mina",
        ["alerts.view", "alerts.resolve", "predictions.view"],
    ),
    "interesado": (
        "Parte interesada",
        ["alerts.view", "reports.export"],
    ),
    "auditor": (
        "Auditor (solo lectura)",
        [
            "predictions.view",
            "alerts.view",
            "reports.export",
            "dashboard.view_all_sites",
            "audit.view",
        ],
    ),
}


def seed(db: Session) -> None:
    perms_by_code: dict[str, Permission] = {}
    for code, description in BASE_PERMISSIONS:
        existing = db.query(Permission).filter(Permission.code == code).first()
        if existing is None:
            existing = Permission(code=code, description=description)
            db.add(existing)
            db.flush()
        else:
            existing.description = description
        perms_by_code[code] = existing

    all_perms = list(perms_by_code.values())

    for name, (description, perm_spec) in ROLE_DEFINITIONS.items():
        role = db.query(Role).filter(Role.name == name).first()
        if role is None:
            role = Role(name=name, description=description)
            db.add(role)
            db.flush()
        else:
            role.description = description

        if perm_spec == "*":
            role.permissions = list(all_perms)
        else:
            role.permissions = [perms_by_code[c] for c in perm_spec]  # type: ignore[index]

    db.commit()
    print(f"Seed OK: {len(perms_by_code)} permisos, {len(ROLE_DEFINITIONS)} roles.")


def main() -> None:
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
