"""Seed de permisos y roles v2 (Plan 19).

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
from app.modules.users import models as users_models  # noqa: F401
from app.shared.access import PERMISSIONS, ROLE_LABELS, grants_for

PERM_HELP: dict[str, str] = {
    "status.view": "Ver Hoy y zonas",
    "alerts.view": "Ver avisos",
    "alerts.acknowledge": "Marcar aviso como visto",
    "alerts.resolve": "Cerrar avisos",
    "history.view": "Ver historial",
    "reliability.view": "Ver confiabilidad",
    "reports.export": "Generar informes",
    "thresholds.manage": "Definir límites",
    "stakeholders.manage": "Gestionar contactos de aviso",
    "data.upload": "Cargar datos",
    "data.quality.view": "Ver calidad de los datos",
    "models.train": "Entrenar en el laboratorio",
    "models.promote": "Activar un cambio del laboratorio",
    "users.manage": "Gestionar equipo",
    "roles.manage": "Gestionar roles",
    "kiosk.manage": "Gestionar pantallas de sala",
    "audit.view": "Ver bitácora",
    "predictions.view": "Ver estado (compatibilidad)",
    "sensors.manage": "Cargar datos (compatibilidad)",
    "dashboard.view_all_sites": "Ver todas las zonas (compatibilidad)",
}


def seed(db: Session) -> None:
    needed = list(PERMISSIONS) + ["predictions.view", "sensors.manage", "dashboard.view_all_sites"]
    perms_by_code: dict[str, Permission] = {}
    for code in needed:
        existing = db.query(Permission).filter(Permission.code == code).first()
        if existing is None:
            existing = Permission(code=code, description=PERM_HELP.get(code, code))
            db.add(existing)
            db.flush()
        else:
            existing.description = PERM_HELP.get(code, existing.description)
        perms_by_code[code] = existing

    for name, label in ROLE_LABELS.items():
        role = db.query(Role).filter(Role.name == name).first()
        if role is None:
            role = Role(name=name, description=label)
            db.add(role)
            db.flush()
        else:
            role.description = label
        codes = grants_for(name)
        role.permissions = [perms_by_code[c] for c in sorted(codes) if c in perms_by_code]

    db.commit()
    print(f"Seed OK: {len(perms_by_code)} permisos, {len(ROLE_LABELS)} roles.")


def main() -> None:
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
