"""Crea el superusuario inicial con rol admin.

Requiere variables de entorno:
  SUPERADMIN_EMAIL
  SUPERADMIN_PASSWORD
  SUPERADMIN_FULL_NAME (opcional)

Uso:
  set SUPERADMIN_EMAIL=admin@example.com
  set SUPERADMIN_PASSWORD=********
  python scripts/create_superadmin.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.roles_permissions.models import Role
from app.modules.users.models import User


def main() -> None:
    email = os.environ.get("SUPERADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("SUPERADMIN_PASSWORD", "")
    full_name = os.environ.get("SUPERADMIN_FULL_NAME", "Super Admin").strip()

    if not email or not password:
        print(
            "ERROR: define SUPERADMIN_EMAIL y SUPERADMIN_PASSWORD "
            "(nunca hardcodear en el código).",
            file=sys.stderr,
        )
        sys.exit(1)
    if len(password) < 8:
        print("ERROR: SUPERADMIN_PASSWORD debe tener al menos 8 caracteres.", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role is None:
            print(
                "ERROR: rol 'admin' no encontrado. "
                "Ejecuta primero: python scripts/seed_roles_permissions.py",
                file=sys.stderr,
            )
            sys.exit(1)

        existing = db.query(User).filter(User.email == email).first()
        if existing is not None:
            existing.password_hash = hash_password(password)
            existing.full_name = full_name
            existing.is_active = True
            if admin_role not in existing.roles:
                existing.roles = list({*existing.roles, admin_role})
            db.add(existing)
            db.commit()
            print(f"Superadmin actualizado: {email} (id={existing.id})")
            return

        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            is_active=True,
            roles=[admin_role],
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Superadmin creado: {email} (id={user.id})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
