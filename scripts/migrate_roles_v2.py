"""Renombra roles v1 → v2 y vuelve a sembrar la matriz (idempotente).

  python scripts/migrate_roles_v2.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.modules.roles_permissions.models import Role
from app.shared.access import ROLE_MIGRATION
from scripts.seed_roles_permissions import seed


def migrate(db) -> dict[str, int]:
    moved = 0
    for old, new in ROLE_MIGRATION.items():
        old_role = db.query(Role).filter(Role.name == old).first()
        if old_role is None:
            continue
        new_role = db.query(Role).filter(Role.name == new).first()
        if new_role is None:
            old_role.name = new
            db.add(old_role)
            moved += 1
            continue
        from app.modules.users.models import UserRole

        rows = db.query(UserRole).filter(UserRole.role_id == old_role.id).all()
        for row in rows:
            exists = (
                db.query(UserRole)
                .filter(UserRole.user_id == row.user_id, UserRole.role_id == new_role.id)
                .first()
            )
            if exists is None:
                row.role_id = new_role.id
                db.add(row)
            else:
                db.delete(row)
            moved += 1
        db.flush()
        db.delete(old_role)
    seed(db)
    return {"moved": moved}


def main() -> None:
    db = SessionLocal()
    try:
        result = migrate(db)
        print(f"Migración de roles OK: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
